from __future__ import annotations

import asyncio
import logging
import shutil
from typing import List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compose command detection (BUG-003 fix)
# ---------------------------------------------------------------------------
# Docker Compose V2 ships as a ``docker`` CLI plugin invoked as
# ``docker compose …``.  V1 is the standalone ``docker-compose`` binary.
# We detect which one is available once and cache the result.

_compose_cmd: List[str] | None = None  # cached; None means "not yet detected"


def _detect_compose_command() -> List[str]:
    """Detect the available Docker Compose command and cache the result.

    Priority:
    1. ``docker compose``  (V2 plugin — preferred)
    2. ``docker-compose``  (V1 standalone — fallback)

    Returns the command prefix as a list, e.g. ["docker", "compose"].
    """
    global _compose_cmd

    if _compose_cmd is not None:
        return _compose_cmd

    # Try V2 plugin first
    if shutil.which("docker") is not None:
        try:
            proc = await_or_skip(
                ["docker", "compose", "version"],
                timeout=10,
            )
            if proc == 0:
                _compose_cmd = ["docker", "compose"]
                logger.info("Detected Docker Compose V2 plugin")
                return _compose_cmd
        except Exception as exc:
            logger.debug("docker compose version check failed: %s", exc)

    # Fall back to V1 standalone
    if shutil.which("docker-compose") is not None:
        _compose_cmd = ["docker-compose"]
        logger.info("Detected Docker Compose V1 standalone")
        return _compose_cmd

    # Nothing found — default to V2 so errors surface clearly
    logger.warning(
        "Neither 'docker compose' nor 'docker-compose' found; "
        "defaulting to V2 command prefix"
    )
    _compose_cmd = ["docker", "compose"]
    return _compose_cmd


def await_or_skip(cmd: list[str], timeout: int = 10) -> int:
    """Run a sync subprocess check for compose detection (blocking)."""
    import subprocess

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return result.returncode
    except FileNotFoundError:
        return 1
    except Exception as exc:
        logger.debug("Subprocess %s failed: %s", cmd, exc)
        return 1


# ---------------------------------------------------------------------------
# Compose operations
# ---------------------------------------------------------------------------

async def _run_compose(
    project_path: str,
    cmd_args: list[str],
    timeout: int = 60,
) -> tuple[str, str, int]:
    """Run a docker compose command with automatic V1/V2 detection."""
    cmd_prefix = _detect_compose_command()
    proc = await asyncio.create_subprocess_exec(
        *cmd_prefix,
        *cmd_args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_path,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        stdout, stderr = await proc.communicate()
        return stdout.decode(), stderr.decode(), -1

    return stdout.decode(), stderr.decode(), proc.returncode or 0


async def up(project_path: str, service: str | None = None, detach: bool = True) -> str:
    args = ["up", "--build"]
    if detach:
        args.append("-d")
    if service:
        args.append(service)
    stdout, stderr, rc = await _run_compose(project_path, args, timeout=120)
    return stdout + stderr


async def down(project_path: str) -> str:
    stdout, stderr, rc = await _run_compose(project_path, ["down"])
    return stdout + stderr


async def restart(project_path: str, service: str | None = None) -> str:
    args = ["restart"]
    if service:
        args.append(service)
    stdout, stderr, rc = await _run_compose(project_path, args)
    return stdout + stderr


async def logs(
    project_path: str,
    service: str | None = None,
    tail: int = 100,
    follow: bool = False,
) -> str:
    args = ["logs", "--tail", str(tail), "--no-color"]
    if follow:
        args.append("--follow")
    if service:
        args.append(service)
    stdout, stderr, rc = await _run_compose(project_path, args, timeout=30)
    return stdout + stderr


async def exec_run(
    project_path: str,
    service: str,
    command: str,
) -> str:
    args = ["exec", "-T", service, "sh", "-c", command]
    stdout, stderr, rc = await _run_compose(project_path, args, timeout=30)
    return stdout + stderr


async def stop(project_path: str, service: str | None = None) -> str:
    args = ["stop"]
    if service:
        args.append(service)
    stdout, stderr, rc = await _run_compose(project_path, args)
    return stdout + stderr


async def ps(project_path: str) -> str:
    stdout, stderr, rc = await _run_compose(project_path, ["ps"])
    return stdout + stderr
