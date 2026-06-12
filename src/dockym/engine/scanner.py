"""Scan filesystem paths for Docker Compose projects.

Provides caching of YAML parsing results keyed by file path and mtime,
with automatic invalidation when compose files change on disk.
"""

from __future__ import annotations

import copy
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import yaml

from dockym.engine.client import containers_by_project
from dockym.models.project import Project, Service

logger = logging.getLogger(__name__)

COMPOSE_FILES = ("docker-compose.yml", "docker-compose.yaml", "compose.yaml")

EXCLUDE_DIRS = {
    "node_modules", ".git", ".svn", "venv", ".venv", "env", ".env",
    "__pycache__", "vendor", "dist", "build", ".next", "target",
}

# ---------------------------------------------------------------------------
# YAML parse cache
# ---------------------------------------------------------------------------
# Keyed by stringified file path.  Each entry stores:
#   (mtime_at_cache_time, time_when_cached, list[Service])
# mtime_at_cache_time is the file's st_mtime when we parsed it.
# time_when_cached is when we stored the entry (used for TTL).
_CACHE_TTL: float = 30.0   # seconds
_CACHE_MAX_ENTRIES: int = 256

_yaml_cache: dict[str, tuple[float, float, list[Service]]] = {}
_yaml_lock = threading.Lock()


def _cache_key(path: Path) -> str:
    """Canonical cache key for a compose file path."""
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _cache_get(compose_file: Path) -> list[Service] | None:
    """Return cached services if the cache entry is still valid, else None.

    A cache entry is valid when:
      1. The file's mtime has not changed since we last parsed it.
      2. The entry is younger than _CACHE_TTL seconds.
    """
    key = _cache_key(compose_file)
    with _yaml_lock:
        entry = _yaml_cache.get(key)
    if entry is None:
        return None

    cached_mtime, cached_time, cached_services = entry

    try:
        current_mtime = compose_file.stat().st_mtime
    except OSError:
        return None  # file disappeared — treat as miss

    age = time.monotonic() - cached_time  # monotonic for TTL check
    if current_mtime == cached_mtime and age < _CACHE_TTL:
        # Return a deep copy so callers cannot corrupt the cache by mutating
        # the returned services (e.g. _enrich_with_docker_state).
        return copy.deepcopy(cached_services)

    return None


def _cache_put(compose_file: Path, services: list[Service]) -> None:
    """Store services in the cache, evicting oldest entries when full."""
    key = _cache_key(compose_file)
    try:
        mtime = compose_file.stat().st_mtime
    except OSError:
        return  # file disappeared — don't cache

    with _yaml_lock:
        # Evict oldest entries if the cache is full
        if len(_yaml_cache) >= _CACHE_MAX_ENTRIES and key not in _yaml_cache:
            _evict_oldest_entries(count=max(1, _CACHE_MAX_ENTRIES // 4))

        now = time.monotonic()
        _yaml_cache[key] = (mtime, now, services)


def _evict_oldest_entries(count: int = 1) -> None:
    """Remove the ``count`` oldest entries from the cache (by cached time)."""
    if not _yaml_cache:
        return
    # Sort by stored timestamp (second element) and remove the oldest
    sorted_keys = sorted(_yaml_cache, key=lambda k: _yaml_cache[k][1])
    for k in sorted_keys[:count]:
        _yaml_cache.pop(k, None)


def clear_cache() -> None:
    """Clear the YAML parsing cache."""
    with _yaml_lock:
        _yaml_cache.clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_paths(paths: list[str]) -> list[Project]:
    """Scan *paths* for Docker Compose projects, returning them sorted by name.

    Each compose file's services are parsed and cached.  Results from the
    Docker daemon are merged in via :func:`_enrich_with_docker_state`.
    """
    projects_map: dict[str, Project] = {}

    for base in paths:
        base_path = Path(base).expanduser().resolve()
        if not base_path.is_dir():
            continue
        _scan_dir(base_path, projects_map, depth=0, max_depth=5)

    _enrich_with_docker_state(projects_map)
    return sorted(projects_map.values(), key=lambda p: p.name.lower())


# ---------------------------------------------------------------------------
# Directory walking
# ---------------------------------------------------------------------------

def _scan_dir(
    path: Path,
    projects_map: dict[str, Project],
    depth: int,
    max_depth: int,
) -> None:
    """Recursively scan *path* for compose files up to *max_depth*."""
    if depth > max_depth:
        return

    _check_directory(path, projects_map)

    if depth >= max_depth:
        return

    try:
        with os.scandir(path) as it:
            for entry in it:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                name = entry.name
                if name.startswith(".") or name in EXCLUDE_DIRS:
                    continue
                _scan_dir(Path(entry.path), projects_map, depth + 1, max_depth)
    except PermissionError:
        pass


def _check_directory(dir_path: Path, projects_map: dict[str, Project]) -> None:
    """Register a project if *dir_path* contains a compose file."""
    for cf in COMPOSE_FILES:
        compose_file = dir_path / cf
        if compose_file.is_file():
            name = _read_compose_name(compose_file) or dir_path.name
            if name not in projects_map:
                services = _extract_services_cached(compose_file)
                projects_map[name] = Project(
                    name=name,
                    path=str(dir_path),
                    services=services,
                )
            return  # first compose file wins


def _read_compose_name(compose_file: Path) -> str | None:
    """Return the top-level ``name`` field from a compose YAML file, or None."""
    try:
        text = compose_file.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        data: dict[str, Any] | None = yaml.safe_load(text)
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    name = data.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


# ---------------------------------------------------------------------------
# YAML extraction (with cache)
# ---------------------------------------------------------------------------

def _extract_services_cached(compose_file: Path) -> list[Service]:
    """Extract services from *compose_file*, using the in-process cache."""
    cached = _cache_get(compose_file)
    if cached is not None:
        return cached

    services = _extract_services(compose_file)
    _cache_put(compose_file, services)
    return services


def _extract_services(compose_file: Path) -> list[Service]:
    """Parse a Docker Compose YAML file and return its services."""
    try:
        text = compose_file.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Cannot read %s: %s", compose_file, exc)
        return []

    try:
        data: dict[str, Any] | None = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        logger.warning("YAML parse error in %s: %s", compose_file, exc)
        return []

    if not isinstance(data, dict):
        return []

    svcs_raw = data.get("services")
    if not isinstance(svcs_raw, dict):
        return []

    result: list[Service] = []
    for name, svc_config in svcs_raw.items():
        if not isinstance(svc_config, dict):
            continue

        image = _coerce_str(svc_config.get("image", ""))
        ports = _format_ports(svc_config.get("ports", []))

        result.append(
            Service(
                name=name,
                image=image,
                ports=ports,
                project_path=str(compose_file.parent),
            )
        )
    return result


def _coerce_str(value: Any) -> str:
    """Safely coerce *value* to a trimmed string, returning '' for None."""
    if value is None:
        return ""
    return str(value).strip()


def _format_ports(ports: Any) -> str:
    """Format a compose ``ports`` list into a readable string.

    Handles both long-form dicts (``{host_port, container_port}``) and
    the short ``"8080:80"`` string format.
    """
    if not ports or not isinstance(ports, list):
        return ""

    parts: list[str] = []
    for entry in ports:
        if isinstance(entry, str):
            parts.append(entry)
        elif isinstance(entry, dict):
            host = entry.get("published", entry.get("target", ""))
            container = entry.get("target", entry.get("published", ""))
            parts.append(f"{host}:{container}" if host else str(container))
        else:
            parts.append(str(entry))
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Docker state enrichment
# ---------------------------------------------------------------------------

def _enrich_with_docker_state(projects_map: dict[str, Project]) -> None:
    """Merge live Docker container info into the projects in *projects_map*."""
    try:
        project_containers = containers_by_project()
    except Exception:
        return

    for proj_name, containers in project_containers.items():
        if proj_name not in projects_map:
            continue
        project = projects_map[proj_name]
        container_by_service: dict[str, dict[str, Any]] = {
            c["name"]: c for c in containers
        }
        for svc in project.services:
            info = container_by_service.get(svc.name)
            if info is not None:
                svc.status = info.get("status", svc.status)
                svc.container_name = info.get("container_name", svc.container_name)
                svc.image = info.get("image", svc.image)
                svc.ports = info.get("ports", svc.ports)
