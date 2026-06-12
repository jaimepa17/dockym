from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import docker as docker_sdk
from docker.errors import APIError, DockerException, NotFound

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thread-safe singleton state
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_client: docker_sdk.DockerClient | None = None
_last_health_check: float = 0.0
_last_connection_attempt: float = 0.0
_connection_failed: bool = False

# ---------------------------------------------------------------------------
# Tuning knobs
# ---------------------------------------------------------------------------
HEALTH_CHECK_TTL: float = 30.0      # seconds between automatic health checks
RETRY_BASE_INTERVAL: float = 5.0    # initial backoff before retrying
RETRY_MAX_INTERVAL: float = 60.0    # cap for exponential backoff
CONNECT_TIMEOUT: float = 5.0        # seconds for connection establishment
READ_TIMEOUT: float = 30.0          # seconds for API call reads
MAX_POOL_SIZE: int = 10             # max keep-alive connections

# ---------------------------------------------------------------------------
# Candidate Docker socket paths (BUG-002 fix)
# ---------------------------------------------------------------------------
# Checked in order; first reachable path wins.
_candidaate_sockets: list[str] = [
    "/var/run/docker.sock",                                  # standard
    "/var/snap/docker/run/docker.sock",                      # Snap-installed Docker
    "/run/user/{uid}/docker.sock",                           # rootless Docker
    "/run/user/{uid}/podman/podman.sock",                    # Podman rootless
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _close_client_safely(client: docker_sdk.DockerClient | None) -> None:
    """Best-effort close of a Docker client to release connection-pool resources."""
    if client is None:
        return
    try:
        client.close()
    except Exception:
        pass  # swallow — cleanup is best-effort


def _backoff_remaining() -> float:
    """Compute seconds remaining in the current exponential backoff window."""
    elapsed = time.monotonic() - _last_connection_attempt
    backoff = min(
        RETRY_BASE_INTERVAL * (2 ** int(elapsed / RETRY_BASE_INTERVAL)),
        RETRY_MAX_INTERVAL,
    )
    return max(0.0, backoff - elapsed)


def _candidate_socket_urls() -> list[str]:
    """Build a list of reachable Docker socket URLs to try.

    DOCKER_HOST from the environment is already tried by ``docker.from_env()``
    in the primary connection path.  Here we expand the per-user paths (using
    the current ``uid``) and filter to sockets that actually exist on disk.
    """
    uid = os.getuid()
    urls: list[str] = []
    for tmpl in _candidaate_sockets:
        path = tmpl.format(uid=uid)
        if os.path.exists(path):
            urls.append(f"unix://{path}")
    return urls


def _create_client() -> docker_sdk.DockerClient:
    """Try to create a new Docker client, trying environment then unix sockets.

    Returns the connected client or raises DockerException.
    """
    global _client

    # Attempt 1: environment variables (DOCKER_HOST, etc.)
    try:
        _client = docker_sdk.from_env(
            timeout=int(CONNECT_TIMEOUT),
            max_pool_size=MAX_POOL_SIZE,
        )
        _client.ping()
        logger.info("Connected to Docker daemon via environment")
        return _client
    except Exception as exc:
        logger.debug("docker.from_env() failed: %s", exc)
        _close_client_safely(_client)
        _client = None

    # Attempt 2: try each candidate socket that exists on disk (BUG-002 fix)
    for url in _candidate_socket_urls():
        try:
            _client = docker_sdk.DockerClient(
                base_url=url,
                timeout=int(CONNECT_TIMEOUT),
                max_pool_size=MAX_POOL_SIZE,
            )
            _client.ping()
            logger.info("Connected to Docker daemon via %s", url)
            return _client
        except Exception as exc:
            logger.debug("Socket %s failed: %s", url, exc)
            _close_client_safely(_client)
            _client = None

    # All attempts exhausted
    raise DockerException(
        "Cannot connect to Docker daemon: no reachable socket found"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_client() -> docker_sdk.DockerClient:
    """Return a thread-safe cached Docker client with health checks and retry.

    Behaviour:
    * If a healthy cached client exists and was pinged less than
      ``HEALTH_CHECK_TTL`` seconds ago, return it immediately (no network).
    * If the TTL has expired, ping to validate; reconnect on failure.
    * After a failed connection, apply exponential backoff before retrying.
    """
    global _client, _last_health_check, _last_connection_attempt, _connection_failed

    now = time.monotonic()

    with _lock:
        # --- Fast path: cached client still within health-check TTL ---
        if _client is not None and (now - _last_health_check) < HEALTH_CHECK_TTL:
            return _client

        # --- TTL expired or first call: validate with a ping ---
        if _client is not None:
            try:
                _client.ping()
                _last_health_check = now
                return _client
            except Exception:
                logger.warning("Docker client health check failed; reconnecting")
                _close_client_safely(_client)
                _client = None

        # --- Backoff guard ---
        if _connection_failed:
            remaining = _backoff_remaining()
            if remaining > 0:
                raise DockerException(
                    f"Docker not available; retrying in {remaining:.1f}s"
                )
            _connection_failed = False

        # --- Establish new connection ---
        _last_connection_attempt = now
        _last_health_check = now

        try:
            client = _create_client()
            _connection_failed = False
            return client
        except DockerException:
            _connection_failed = True
            raise


def close_client() -> None:
    """Explicitly close the cached client and release resources.

    Call this during application shutdown to avoid dangling connections.
    Safe to call multiple times or when no client exists.
    """
    global _client, _connection_failed
    with _lock:
        _close_client_safely(_client)
        _client = None
        _connection_failed = False
        logger.debug("Docker client closed")


def containers_by_project() -> dict[str, list[dict]]:
    """Get containers grouped by compose project with error handling."""
    try:
        client = get_client()
    except DockerException:
        return {}

    try:
        containers = client.containers.list(all=True)
    except (DockerException, APIError) as exc:
        logger.warning("Failed to list containers: %s", exc)
        return {}

    projects: dict[str, list[dict]] = {}
    for c in containers:
        try:
            attrs = c.attrs
            labels = attrs.get("Config", {}).get("Labels", {}) or {}
            project_name = labels.get("com.docker.compose.project", "")
            service_name = labels.get("com.docker.compose.service", c.name)

            state = attrs.get("State", {})
            status = state.get("Status", "unknown")

            ports_map = attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            ports_str = ", ".join(
                f"{p}:{info[0]['HostPort']}" if info else p
                for p, info in ports_map.items()
            )

            # Safely get image tag
            try:
                image = c.image.tags[0] if c.image.tags else attrs["Config"]["Image"]
            except (IndexError, KeyError):
                image = attrs.get("Config", {}).get("Image", "unknown")

            svc = {
                "name": service_name,
                "container_name": c.name,
                "image": image,
                "status": status,
                "ports": ports_str,
                "project": project_name,
                "id": c.short_id,
            }

            key = project_name or "_standalone"
            projects.setdefault(key, []).append(svc)
        except Exception as exc:
            logger.debug("Skipping problematic container: %s", exc)
            continue

    return projects


def get_container_status(container_name: str) -> str | None:
    """Get status of a specific container."""
    try:
        client = get_client()
        c = client.containers.get(container_name)
        return c.attrs["State"]["Status"]
    except (DockerException, NotFound, APIError) as exc:
        logger.debug("Failed to get status for %s: %s", container_name, exc)
        return None


def container_stats(container_name: str) -> dict[str, Any] | None:
    """Get CPU/memory stats for a container."""
    try:
        client = get_client()
        c = client.containers.get(container_name)
        stats = c.stats(stream=False)
        return stats
    except (DockerException, NotFound, APIError) as exc:
        logger.debug("Failed to get stats for %s: %s", container_name, exc)
        return None


def is_docker_available() -> bool:
    """Check if Docker daemon is reachable.

    Uses the same cached client and health-check logic as get_client(),
    so this does NOT perform a redundant second ping.
    """
    try:
        get_client()
        return True
    except DockerException:
        return False


def docker_system_info() -> dict[str, Any]:
    """Get Docker system information (daemon status, images, disk usage)."""
    client = None
    try:
        client = get_client()
    except DockerException:
        return {"available": False}
    assert client is not None

    info: dict[str, Any] = {"available": True}

    try:
        daemon_info = client.info()
        info["server_version"] = daemon_info.get("ServerVersion", "unknown")
        info["containers"] = daemon_info.get("Containers", 0)
        info["containers_running"] = daemon_info.get("ContainersRunning", 0)
        info["containers_stopped"] = daemon_info.get("ContainersStopped", 0)
        info["images"] = daemon_info.get("Images", 0)
    except Exception:
        info["server_version"] = "unknown"
        info["containers"] = 0
        info["containers_running"] = 0
        info["containers_stopped"] = 0
        info["images"] = 0

    try:
        df = client.disk_usage()
        total_bytes = 0
        for kind in ("Containers", "Images", "Volumes", "BuildCache"):
            for item in df.get(kind, []):
                total_bytes += item.get("Size", 0) or item.get("Active", 0) or 0
        info["disk_usage_bytes"] = total_bytes
    except Exception:
        info["disk_usage_bytes"] = 0

    return info


def batch_start_containers(container_names: list[str]) -> tuple[int, int, list[str]]:
    """Start multiple containers. Returns (success_count, fail_count, errors)."""
    client = None
    try:
        client = get_client()
    except DockerException as e:
        return 0, len(container_names), [f"Docker not available: {e}"]
    assert client is not None

    ok = 0
    fail = 0
    errors: list[str] = []
    for name in container_names:
        try:
            c = client.containers.get(name)
            c.start()
            ok += 1
        except NotFound:
            fail += 1
            errors.append(f"{name}: no encontrado")
        except APIError as e:
            fail += 1
            errors.append(f"{name}: {e}")
        except Exception as e:
            fail += 1
            errors.append(f"{name}: {e}")
    return ok, fail, errors


def batch_stop_containers(container_names: list[str]) -> tuple[int, int, list[str]]:
    """Stop multiple containers. Returns (success_count, fail_count, errors)."""
    client = None
    try:
        client = get_client()
    except DockerException as e:
        return 0, len(container_names), [f"Docker not available: {e}"]
    assert client is not None

    ok = 0
    fail = 0
    errors: list[str] = []
    for name in container_names:
        try:
            c = client.containers.get(name)
            c.stop(timeout=5)
            ok += 1
        except NotFound:
            fail += 1
            errors.append(f"{name}: no encontrado")
        except APIError as e:
            fail += 1
            errors.append(f"{name}: {e}")
        except Exception as e:
            fail += 1
            errors.append(f"{name}: {e}")
    return ok, fail, errors


def batch_restart_containers(container_names: list[str]) -> tuple[int, int, list[str]]:
    """Restart multiple containers. Returns (success_count, fail_count, errors)."""
    client = None
    try:
        client = get_client()
    except DockerException as e:
        return 0, len(container_names), [f"Docker not available: {e}"]
    assert client is not None

    ok = 0
    fail = 0
    errors: list[str] = []
    for name in container_names:
        try:
            c = client.containers.get(name)
            c.restart(timeout=5)
            ok += 1
        except NotFound:
            fail += 1
            errors.append(f"{name}: no encontrado")
        except APIError as e:
            fail += 1
            errors.append(f"{name}: {e}")
        except Exception as e:
            fail += 1
            errors.append(f"{name}: {e}")
    return ok, fail, errors


def batch_remove_containers(container_names: list[str], force: bool = False) -> tuple[int, int, list[str]]:
    """Remove multiple containers. Returns (success_count, fail_count, errors)."""
    client = None
    try:
        client = get_client()
    except DockerException as e:
        return 0, len(container_names), [f"Docker not available: {e}"]
    assert client is not None

    ok = 0
    fail = 0
    errors: list[str] = []
    for name in container_names:
        try:
            c = client.containers.get(name)
            c.remove(force=force, v=True)
            ok += 1
        except NotFound:
            fail += 1
            errors.append(f"{name}: no encontrado")
        except APIError as e:
            fail += 1
            errors.append(f"{name}: {e}")
        except Exception as e:
            fail += 1
            errors.append(f"{name}: {e}")
    return ok, fail, errors


def restart_all_running() -> tuple[int, int, list[str]]:
    """Restart all running containers. Returns (success, fail, errors)."""
    client = None
    try:
        client = get_client()
    except DockerException as e:
        return 0, 0, [f"Docker not available: {e}"]
    assert client is not None

    try:
        running = client.containers.list(filters={"status": "running"})
    except Exception as e:
        return 0, 0, [f"Failed to list containers: {e}"]

    ok = 0
    fail = 0
    errors: list[str] = []
    for c in running:
        try:
            c.restart(timeout=5)
            ok += 1
        except Exception as e:
            fail += 1
            errors.append(f"{c.name}: {e}")
    return ok, fail, errors


def pull_latest_images() -> tuple[int, int, list[str]]:
    """Pull latest versions of all images used by running/stopped containers."""
    client = None
    try:
        client = get_client()
    except DockerException as e:
        return 0, 0, [f"Docker not available: {e}"]
    assert client is not None

    # Collect unique image references from all containers
    try:
        all_containers = client.containers.list(all=True)
    except Exception as e:
        return 0, 0, [f"Failed to list containers: {e}"]

    images: set[str] = set()
    for c in all_containers:
        try:
            img = c.image
            if img is not None and img.tags:
                for tag in img.tags:
                    images.add(tag)
            else:
                images.add(c.attrs.get("Config", {}).get("Image", ""))
        except Exception:
            pass

    ok = 0
    fail = 0
    errors: list[str] = []
    for img_ref in images:
        if not img_ref:
            continue
        try:
            client.images.pull(img_ref)
            ok += 1
        except Exception as e:
            fail += 1
            errors.append(f"{img_ref}: {e}")
    return ok, fail, errors
