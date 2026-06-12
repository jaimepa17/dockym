from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextEdit, QLabel)
from PySide6.QtGui import QFont

from dockym.models.project import Service
from dockym.ui.icons import make_icon_button


class EnvDialog(QDialog):
    def __init__(self, service: Service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle(f".env — {service.name}")
        self.resize(600, 500)
        self._env_path = Path(service.project_path) / ".env"
        self._setup_ui()
        self._load_env()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Editando .env para {self.service.name}"))

        self.env_editor = QTextEdit()
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.env_editor.setFont(mono)
        layout.addWidget(self.env_editor)

        btn_layout = QHBoxLayout()
        btn_save = make_icon_button("Guardar", "save", color="#3fb950")
        btn_save.clicked.connect(self._save_env)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _load_env(self):
        if self._env_path.exists():
            self.env_editor.setPlainText(self._env_path.read_text())
        else:
            self.env_editor.setPlainText("# No existe archivo .env en este proyecto\n# Crea uno y usa el formato CLAVE=valor")

    def _save_env(self):
        self._env_path.write_text(self.env_editor.toPlainText())
        from PySide6.QtWidgets import QMainWindow
        parent = self.parent()
        if isinstance(parent, QMainWindow):
            parent.statusBar().showMessage(".env guardado", 3000)
