from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QListWidget,
                               QListWidgetItem, QFileDialog, QSpinBox,
                               QComboBox, QGroupBox, QFormLayout,
                               QDialogButtonBox, QMessageBox, QCheckBox)

from dockym.models.config import Config


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Configuración — Dockym")
        self.resize(550, 420)
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ── Paths ──────────────────────────────────────────────
        paths_group = QGroupBox("Rutas de proyectos")
        paths_layout = QVBoxLayout(paths_group)

        self.paths_list = QListWidget()
        paths_layout.addWidget(self.paths_list)

        paths_buttons = QHBoxLayout()
        btn_add = QPushButton("➕ Agregar ruta")
        btn_add.clicked.connect(self._add_path)
        btn_remove = QPushButton("➖ Quitar seleccionada")
        btn_remove.clicked.connect(self._remove_path)
        paths_buttons.addWidget(btn_add)
        paths_buttons.addWidget(btn_remove)
        paths_buttons.addStretch()
        paths_layout.addLayout(paths_buttons)
        layout.addWidget(paths_group)

        # ── Options ────────────────────────────────────────────
        opts_group = QGroupBox("Opciones")
        opts_layout = QFormLayout(opts_group)

        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(1, 60)
        self.refresh_spin.setSuffix(" segundos")
        opts_layout.addRow("Auto-refresh:", self.refresh_spin)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["dev", "prod", "test"])
        opts_layout.addRow("Perfil activo:", self.profile_combo)

        self.minimize_check = QCheckBox("Minimizar a bandeja al cerrar")
        opts_layout.addRow("", self.minimize_check)

        layout.addWidget(opts_group)

        # ── Buttons ────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_config)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_config(self):
        self.paths_list.clear()
        for p in self.config.paths:
            item = QListWidgetItem(p)
            item.setToolTip(p)
            self.paths_list.addItem(item)

        self.refresh_spin.setValue(self.config.refresh_interval)
        idx = self.profile_combo.findText(self.config.active_profile)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)

        self.minimize_check.setChecked(self.config.minimize_to_tray)

    def _add_path(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de proyectos")
        if path:
            for i in range(self.paths_list.count()):
                if self.paths_list.item(i).text() == path:
                    QMessageBox.information(self, "Info", "Esa ruta ya está agregada")
                    return
            self.paths_list.addItem(path)

    def _remove_path(self):
        item = self.paths_list.currentItem()
        if item:
            self.paths_list.takeItem(self.paths_list.row(item))

    def _save_config(self):
        self.config.paths = [
            self.paths_list.item(i).text()
            for i in range(self.paths_list.count())
        ]
        self.config.refresh_interval = self.refresh_spin.value()
        self.config.active_profile = self.profile_combo.currentText()
        self.config.minimize_to_tray = self.minimize_check.isChecked()
        self.config.save()
        self.accept()
