from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Qt


class DockerSignals(QObject):
    scan_finished = Signal(list)
    scan_error = Signal(str)
    operation_finished = Signal(str)
    operation_error = Signal(str)


class ScanTask(QRunnable):
    def __init__(self, paths: list[str], signals: DockerSignals):
        super().__init__()
        self.paths = paths
        self.signals = signals

    def run(self):
        try:
            from dockym.engine.scanner import scan_paths
            projects = scan_paths(self.paths)
            self.signals.scan_finished.emit(projects)
        except Exception as e:
            self.signals.scan_error.emit(str(e))


class ComposeTask(QRunnable):
    def __init__(self, method: str, project_path: str, signals: DockerSignals,
                 service_name: str | None = None):
        super().__init__()
        self.method = method
        self.project_path = project_path
        self.service_name = service_name
        self.signals = signals

    def run(self):
        try:
            from dockym.engine.compose import up, down, restart, stop

            match self.method:
                case "start_service":
                    asyncio.run(up(self.project_path, self.service_name))
                    msg = f"Service {self.service_name} started"
                case "stop_service":
                    asyncio.run(stop(self.project_path, self.service_name))
                    msg = f"Service {self.service_name} stopped"
                case "restart_service":
                    asyncio.run(restart(self.project_path, self.service_name))
                    msg = f"Service {self.service_name} restarted"
                case "project_up":
                    asyncio.run(up(self.project_path))
                    msg = "Project started"
                case "project_down":
                    asyncio.run(down(self.project_path))
                    msg = "Project stopped"
                case _:
                    msg = "Unknown operation"

            self.signals.operation_finished.emit(msg)
        except Exception as e:
            self.signals.operation_error.emit(str(e))


class DockerPool(QObject):
    """Owns the QThreadPool and keeps DockerSignals alive across worker
    boundaries so queued signals can never fire on a freed object.

    Each signals instance is parented to this pool (so Qt manages C++ lifetime)
    and held in a Python set until both its terminal signals have fired or the
    pool is destroyed.
    """

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pool = QThreadPool.globalInstance()
        # Strong Python refs so PySide6 wrappers stay alive until the signal
        # has been delivered on the GUI thread.
        self._inflight: set[DockerSignals] = set()

    def _make_signals(self) -> DockerSignals:
        sig = DockerSignals(self)  # Qt-parented to pool
        self._inflight.add(sig)
        # Drop the strong ref after either terminal signal fires
        sig.scan_finished.connect(
            lambda *_: self._release(sig), Qt.ConnectionType.QueuedConnection
        )
        sig.scan_error.connect(
            lambda *_: self._release(sig), Qt.ConnectionType.QueuedConnection
        )
        sig.operation_finished.connect(
            lambda *_: self._release(sig), Qt.ConnectionType.QueuedConnection
        )
        sig.operation_error.connect(
            lambda *_: self._release(sig), Qt.ConnectionType.QueuedConnection
        )
        return sig

    def _release(self, sig: DockerSignals) -> None:
        # Delayed discard so all sibling slots on the same signal still see it
        self._inflight.discard(sig)

    def scan(self, paths: list[str]) -> DockerSignals:
        sig = self._make_signals()
        self._pool.start(ScanTask(paths, sig))
        return sig

    def compose(self, method: str, project_path: str,
                service_name: str | None = None) -> DockerSignals:
        sig = self._make_signals()
        self._pool.start(ComposeTask(method, project_path, sig, service_name))
        return sig

    def batch_operation(self, method: str, container_names: list[str],
                        force: bool = False) -> DockerSignals:
        sig = self._make_signals()
        self._pool.start(BatchTask(method, container_names, sig, force))
        return sig

    def system_operation(self, method: str) -> DockerSignals:
        sig = self._make_signals()
        self._pool.start(SystemTask(method, sig))
        return sig


class BatchTask(QRunnable):
    """Background task for batch container operations."""
    def __init__(self, method: str, container_names: list[str],
                 signals: DockerSignals, force: bool = False):
        super().__init__()
        self.method = method
        self.container_names = container_names
        self.force = force
        self.signals = signals

    def run(self):
        try:
            from dockym.engine.client import (
                batch_start_containers, batch_stop_containers,
                batch_restart_containers, batch_remove_containers,
            )

            match self.method:
                case "batch_start":
                    ok, fail, errors = batch_start_containers(self.container_names)
                    msg = f"Iniciados {ok}/{ok + fail} contenedores"
                case "batch_stop":
                    ok, fail, errors = batch_stop_containers(self.container_names)
                    msg = f"Detenidos {ok}/{ok + fail} contenedores"
                case "batch_restart":
                    ok, fail, errors = batch_restart_containers(self.container_names)
                    msg = f"Reiniciados {ok}/{ok + fail} contenedores"
                case "batch_remove":
                    ok, fail, errors = batch_remove_containers(self.container_names, force=self.force)
                    msg = f"Eliminados {ok}/{ok + fail} contenedores"
                case _:
                    errors = ["Operación desconocida"]
                    msg = "Error"

            if errors:
                msg += f" ({'; '.join(errors[:3])})"
            self.signals.operation_finished.emit(msg)
        except Exception as e:
            self.signals.operation_error.emit(str(e))


class SystemTask(QRunnable):
    """Background task for Docker system operations (restart all, pull, system info)."""
    def __init__(self, method: str, signals: DockerSignals):
        super().__init__()
        self.method = method
        self.signals = signals

    def run(self):
        try:
            from dockym.engine.client import (
                restart_all_running, pull_latest_images, docker_system_info,
            )

            match self.method:
                case "restart_all":
                    ok, fail, errors = restart_all_running()
                    msg = f"Reiniciados {ok}/{ok + fail} contenedores"
                    if errors:
                        msg += f" ({'; '.join(errors[:3])})"
                    self.signals.operation_finished.emit(msg)
                case "pull_images":
                    ok, fail, errors = pull_latest_images()
                    msg = f"Actualizadas {ok}/{ok + fail} imágenes"
                    if errors:
                        msg += f" ({'; '.join(errors[:3])})"
                    self.signals.operation_finished.emit(msg)
                case "system_info":
                    info = docker_system_info()
                    self.signals.operation_finished.emit(str(info))
                case _:
                    self.signals.operation_error.emit("Operación desconocida")
        except Exception as e:
            self.signals.operation_error.emit(str(e))
