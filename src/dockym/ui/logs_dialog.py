from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtGui import QFont

from dockym.engine.compose import logs
from dockym.models.project import Service


class LogsWorker(QThread):
    log_line = Signal(str)
    finished = Signal()

    def __init__(self, service: Service):
        super().__init__()
        self.service = service

    def run(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            output = loop.run_until_complete(
                logs(self.service.project_path, self.service.name, tail=200)
            )
            self.log_line.emit(output or "Sin logs disponibles")
        except Exception as e:
            self.log_line.emit(f"Error: {e}")
        finally:
            loop.close()
            self.finished.emit()


class LogsDialog(QDialog):
    def __init__(self, service: Service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle(f"Logs — {service.name}")
        self.resize(800, 600)
        self._setup_ui()
        self._load_logs()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.log_output.setFont(mono)
        layout.addWidget(self.log_output)

        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("↻ Refrescar")
        btn_refresh.clicked.connect(self._load_logs)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _load_logs(self):
        self.log_output.setPlainText("Cargando logs...")
        self._worker = LogsWorker(self.service)
        self._worker.log_line.connect(self.log_output.setPlainText)
        self._worker.start()
