from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextEdit, QLabel, QLineEdit)
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont

from dockym.models.project import Service


class ExecWorker(QThread):
    output = Signal(str)
    finished = Signal()

    def __init__(self, service: Service, command: str):
        super().__init__()
        self.service = service
        self.command = command

    def run(self):
        import asyncio
        from dockym.engine.compose import exec_run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                exec_run(self.service.project_path, self.service.name, self.command)
            )
            self.output.emit(result)
        except Exception as e:
            self.output.emit(f"Error: {e}")
        finally:
            loop.close()
            self.finished.emit()


class ExecDialog(QDialog):
    def __init__(self, service: Service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle(f"Exec — {service.name}")
        self.resize(700, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Ejecutar comando en {self.service.name}:"))

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Ej: ls -la /app")
        self.cmd_input.returnPressed.connect(self._run_cmd)
        layout.addWidget(self.cmd_input)

        btn_run = QPushButton("▶ Ejecutar")
        btn_run.clicked.connect(self._run_cmd)
        layout.addWidget(btn_run)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.output_area.setFont(mono)
        layout.addWidget(self.output_area)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _run_cmd(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.output_area.setPlainText("Ejecutando...")
        self._worker = ExecWorker(self.service, cmd)
        self._worker.output.connect(self.output_area.setPlainText)
        self._worker.start()
