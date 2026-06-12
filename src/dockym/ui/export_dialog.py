from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QTextEdit,
                               QFileDialog, QMessageBox, QCheckBox)
from PySide6.QtGui import QFont

from dockym.models.config import Config
from dockym.models.project import Project
from dockym.ui.icons import make_icon_button


class ExportImportDialog(QDialog):
    def __init__(self, projects: list[Project], config: Config, parent=None):
        super().__init__(parent)
        self.projects = projects
        self.config = config
        self.setWindowTitle("Exportar / Importar configuración")
        self.resize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        export_group = QLabel("<b>Exportar</b> — Guarda rutas, perfil y proyectos como JSON")
        layout.addWidget(export_group)

        btn_export = make_icon_button("Exportar configuración...", "upload")
        btn_export.clicked.connect(self._export)
        layout.addWidget(btn_export)

        layout.addSpacing(16)

        import_group = QLabel("<b>Importar</b> — Carga una configuración guardada")
        layout.addWidget(import_group)

        btn_import = make_icon_button("Importar configuración...", "download")
        btn_import.clicked.connect(self._import)
        layout.addWidget(btn_import)

        layout.addStretch()

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("monospace", 9))
        self.preview.setMaximumHeight(200)
        layout.addWidget(self.preview)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _export(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Guardar configuración",
            str(Path.home() / f"dockym-config-{datetime.now().strftime('%Y%m%d')}.json"),
            "Dockym Config (*.json)"
        )
        if not filepath:
            return

        data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "config": {
                "paths": self.config.paths,
                "active_profile": self.config.active_profile,
                "refresh_interval": self.config.refresh_interval,
            },
            "projects": [
                {
                    "name": p.name,
                    "path": p.path,
                    "services": [{"name": s.name, "image": s.image} for s in p.services],
                }
                for p in self.projects
            ],
        }

        Path(filepath).write_text(json.dumps(data, indent=2))
        self.preview.setPlainText(f"✅ Exportado a:\n{filepath}\n\n{json.dumps(data, indent=2)[:500]}...")
        QMessageBox.information(self, "Exportado", f"Configuración guardada en:\n{filepath}")

    def _import(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Cargar configuración",
            str(Path.home()),
            "Dockym Config (*.json)"
        )
        if not filepath:
            return

        try:
            data = json.loads(Path(filepath).read_text())
            imported_config = data.get("config", {})
            paths = imported_config.get("paths", [])
            profile = imported_config.get("active_profile", "dev")
            refresh = imported_config.get("refresh_interval", 5)

            preview_text = (
                f"Vista previa de: {Path(filepath).name}\n\n"
                f"Rutas ({len(paths)}):\n" + "\n".join(f"  • {p}" for p in paths) +
                f"\n\nPerfil: {profile}\n"
                f"Refresh: {refresh}s\n"
                f"Proyectos: {len(data.get('projects', []))}"
            )
            self.preview.setPlainText(preview_text)

            reply = QMessageBox.question(
                self, "Confirmar importación",
                "¿Aplicar esta configuración?\n\n"
                "Se reemplazarán las rutas, perfil y refresh actuales.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

            self.config.paths = paths
            self.config.active_profile = profile
            self.config.refresh_interval = refresh
            self.config.save()

            QMessageBox.information(
                self, "Importado",
                f"Configuración importada. Refresca (F5) para aplicar."
            )
            self.accept()

        except (json.JSONDecodeError, KeyError, Exception) as e:
            QMessageBox.warning(self, "Error", f"Archivo inválido:\n{e}")
