"""Dockym dev runner.

Watches the ``src/dockym/`` tree and restarts the app on any Python file
change. No compile step — Python is interpreted; we just relaunch.

Usage:
    uv run python tools/dev.py
    uv run python tools/dev.py --offscreen    # headless smoke test loop
    uv run python tools/dev.py --once         # single run, no watcher

Requires: ``watchfiles`` (added to pyproject). All other deps already in
the project.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def _kill_existing() -> None:
    """Best-effort kill of any prior Dockym subprocesses from previous
    dev.py invocations so we never end up with stacked windows."""
    for cmd in ("tools/dev.py", "-m dockym"):
        try:
            subprocess.run(["pkill", "-9", "-f", cmd],
                           check=False,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass


def _spawn(extra_env: dict[str, str]) -> subprocess.Popen:
    """Launch the app as a child process. Returns the Popen handle."""
    env = os.environ.copy()
    env.update(extra_env)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(SRC)
    return subprocess.Popen(
        [sys.executable, "-u", "-m", "dockym"],
        env=env,
        cwd=str(ROOT),
        bufsize=0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Dockym dev runner with auto-reload")
    parser.add_argument("--offscreen", action="store_true",
                        help="Run headless (no window). Useful for CI / fast checks.")
    parser.add_argument("--once", action="store_true",
                        help="Run once without watching, exit with the app's status.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show every file change event.")
    args = parser.parse_args()

    env_extra: dict[str, str] = {}
    if args.offscreen:
        env_extra["QT_QPA_PLATFORM"] = "offscreen"

    if args.once:
        proc = _spawn(env_extra)
        return proc.wait()

    # Lazy import so --once works without the dep
    from watchfiles import watch

    # Don't leave an instance from a previous dev.py run holding the window hostage
    _kill_existing()
    print(f"[dev] Watching {SRC.relative_to(ROOT)}/ for changes…  (Ctrl-C to exit)")
    sys.path.insert(0, str(SRC))
    last_proc: subprocess.Popen | None = None
    try:
        while True:
            for changes in watch(str(SRC), step=200):
                if last_proc is not None:
                    if last_proc.poll() is None:
                        print("[dev] Change detected → restarting")
                        last_proc.send_signal(signal.SIGINT)
                        try:
                            last_proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            last_proc.kill()
                            last_proc.wait()
                    else:
                        code = last_proc.returncode
                        if code not in (0, -signal.SIGINT, 130):
                            print(f"[dev] App exited with code {code}")
                if args.verbose:
                    for change_type, path in changes:
                        rel = Path(path).relative_to(SRC)
                        print(f"[dev]   {change_type.name}: {rel}")
                last_proc = _spawn(env_extra)
                # Tell the user the app is up — feedback for an otherwise silent
                # relaunch.
                time.sleep(0.3)
                if last_proc.poll() is None:
                    print("[dev] Running — http://no-url, just open the window")
                break
    except KeyboardInterrupt:
        print("\n[dev] Interrupted")
        if last_proc is not None:
            last_proc.send_signal(signal.SIGINT)
            last_proc.wait(timeout=5)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
