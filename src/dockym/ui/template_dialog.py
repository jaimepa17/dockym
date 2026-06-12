from __future__ import annotations

import yaml
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QListWidget,
                               QListWidgetItem, QTextEdit, QMessageBox,
                               QDialogButtonBox, QGroupBox, QFileDialog)
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtCore import QSize

from dockym.engine.templates import TEMPLATES
from dockym.models.project import Project
from dockym.ui.icons import icon_pixmap


class TemplateDialog(QDialog):
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(f"Agregar servicio a {project.name}")
        self.resize(700, 500)
        self._setup_ui()
        self._load_templates()
        shortcut = QShortcut(QKeySequence("Escape"), self)
        shortcut.activated.connect(self.reject)

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("Servicios disponibles:"))
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        left.addWidget(self.template_list)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Vista previa del servicio:"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("monospace", 9))
        right.addWidget(self.preview)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Agregar al proyecto")
        btn_add.setIcon(icon_pixmap("play", color="#3fb950", size=14))
        btn_add.setIconSize(QSize(14, 14))
        btn_add.clicked.connect(self._add_template)
        btn_add.setObjectName("btn-start")
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_cancel)
        right.addLayout(btn_layout)

        layout.addLayout(right, 2)

    def _load_templates(self):
        for key, tmpl in TEMPLATES.items():
            item = QListWidgetItem(tmpl["name"])
            item.setData(32, key)
            item.setToolTip(tmpl["description"])
            # Render the template's icon as the list item's leading icon
            item.setIcon(icon_pixmap(tmpl["icon"], color="#58a6ff", size=18))
            self.template_list.addItem(item)

    def _on_template_selected(self, current, previous):
        if not current:
            self.preview.clear()
            return
        key = current.data(32)
        tmpl = TEMPLATES.get(key)
        if tmpl:
            preview = yaml.dump(
                {key: tmpl["service"]},
                default_flow_style=False,
                allow_unicode=True,
            )
            info = f"# {tmpl['name']}\n# {tmpl['description']}\n\n{preview}"
            self.preview.setPlainText(info)

    def _add_template(self):
        item = self.template_list.currentItem()
        if not item:
            return
        key = item.data(32)
        tmpl = TEMPLATES.get(key)
        if not tmpl:
            return

        compose_path = Path(self.project.path) / "docker-compose.yml"
        if not compose_path.exists():
            QMessageBox.warning(self, "Error", "No se encontró docker-compose.yml en este proyecto")
            return

        try:
            data = yaml.safe_load(compose_path.read_text()) or {}
        except yaml.YAMLError:
            QMessageBox.warning(self, "Error", "El archivo compose tiene formato inválido")
            return

        if not isinstance(data, dict):
            data = {}

        if "services" not in data or not isinstance(data.get("services"), dict):
            data["services"] = {}

        svc_name = key
        if svc_name in data["services"]:
            reply = QMessageBox.question(
                self, "Sobrescribir",
                f"El servicio '{svc_name}' ya existe. ¿Sobrescribir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        project_name = self.project.name.lower().replace(" ", "_")
        svc_config = tmpl["service"].copy()
        svc_config["container_name"] = svc_config.get(
            "container_name", f"{project_name}_{svc_name}"
        ).replace("${PROJECT_NAME}", project_name)

        if "environment" in svc_config and isinstance(svc_config["environment"], dict):
            svc_config["environment"] = [
                f"{k}={v}" for k, v in svc_config["environment"].items()
            ]

        data["services"][svc_name] = svc_config

        volumes = tmpl.get("volumes", {})
        if volumes:
            if "volumes" not in data or not isinstance(data.get("volumes"), dict):
                data["volumes"] = {}
            for vol_name, vol_config in volumes.items():
                if vol_name not in data["volumes"]:
                    data["volumes"][vol_name] = vol_config

        compose_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))
        QMessageBox.information(
            self, "Completado",
            f"Servicio '{tmpl['name']}' agregado a {self.project.name}\n"
            "Refresca la vista (F5) para ver los cambios."
        )
        self.accept()
