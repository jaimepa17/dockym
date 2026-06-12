from __future__ import annotations

import json
import threading
from PySide6.QtCore import QThread, Signal


class DockerEventsWorker(QThread):
    event_occurred = Signal(str, str)  # action, container_name
    error_occurred = Signal(str)
    connected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = threading.Event()
        self._client = None
        self._client_lock = threading.Lock()

    def run(self):
        self._running.set()
        try:
            import docker
            with self._client_lock:
                self._client = docker.from_env()
            self.connected.emit()
            for raw in self._client.events(decode=True, filters={"type": "container"}):
                if not self._running.is_set():
                    break
                action = raw.get("Action", "")
                actor = raw.get("Actor", {})
                attrs = actor.get("Attributes", {})
                name = attrs.get("name", actor.get("ID", "")[:12])
                if action in ("start", "stop", "die", "kill", "pause", "unpause", "destroy", "restart"):
                    self.event_occurred.emit(action, name)
        except Exception as e:
            if self._running.is_set():
                self.error_occurred.emit(str(e))
        finally:
            with self._client_lock:
                self._client = None

    def stop(self):
        self._running.clear()
        with self._client_lock:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
