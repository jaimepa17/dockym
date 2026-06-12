from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QCheckBox,
                               QTextEdit, QMessageBox)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from dockym.ui.icons import make_icon_button


class PruneWorker(QThread):
    output = Signal(str)
    finished = Signal()

    def __init__(self, prune_all: bool, containers: bool, images: bool, volumes: bool, networks: bool):
        super().__init__()
        self.prune_all = prune_all
        self.containers = containers
        self.images = images
        self.volumes = volumes
        self.networks = networks

    def run(self):
        import docker
        client = docker.from_env()
        results = []

        if self.prune_all or self.containers:
            try:
                r = client.containers.prune()
                freed = r.get("SpaceReclaimed", 0)
                results.append(f"Contenedores: {len(r.get('ContainersDeleted', []))} eliminados ({freed / 1e6:.1f}MB liberados)")
            except Exception as e:
                results.append(f"Contenedores: error — {e}")

        if self.prune_all or self.images:
            try:
                r = client.images.prune()
                freed = r.get("SpaceReclaimed", 0)
                results.append(f"Imágenes: {len(r.get('ImagesDeleted', []))} eliminadas ({freed / 1e6:.1f}MB liberados)")
            except Exception as e:
                results.append(f"Imágenes: error — {e}")

        if self.prune_all or self.volumes:
            try:
                r = client.volumes.prune()
                freed = r.get("SpaceReclaimed", 0)
                results.append(f"Volúmenes: {len(r.get('VolumesDeleted', []))} eliminados ({freed / 1e6:.1f}MB liberados)")
            except Exception as e:
                results.append(f"Volúmenes: error — {e}")

        if self.prune_all or self.networks:
            try:
                r = client.networks.prune()
                results.append(f"Redes: {len(r.get('NetworksDeleted', []))} eliminadas")
            except Exception as e:
                results.append(f"Redes: error — {e}")

        self.output.emit("\n".join(results) if results else "Nada que limpiar")
        self.finished.emit()


class PruneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Limpiar Docker — Prune")
        self.resize(550, 450)
        self._setup_ui()
        shortcut = QShortcut(QKeySequence("Escape"), self)
        shortcut.activated.connect(self.reject)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Selecciona qué limpiar:</b>"))

        self.chk_all = QCheckBox("Limpiar todo (contenedores, imágenes, volúmenes, redes)")
        self.chk_all.toggled.connect(self._on_all_toggled)
        layout.addWidget(self.chk_all)

        self.chk_containers = QCheckBox("  Contenedores detenidos")
        self.chk_images = QCheckBox("  Imágenes no usadas")
        self.chk_volumes = QCheckBox("  Volúmenes huérfanos")
        self.chk_networks = QCheckBox("  Redes no usadas")
        layout.addWidget(self.chk_containers)
        layout.addWidget(self.chk_images)
        layout.addWidget(self.chk_volumes)
        layout.addWidget(self.chk_networks)

        btn_layout = QHBoxLayout()
        btn_prune = make_icon_button("Ejecutar Prune", "broom", color="#f85149")
        btn_prune.setObjectName("btn-danger")
        btn_prune.clicked.connect(self._run_prune)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_prune)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.result_output.setFont(mono)
        layout.addWidget(self.result_output)

    def _on_all_toggled(self, checked: bool):
        for chk in (self.chk_containers, self.chk_images, self.chk_volumes, self.chk_networks):
            chk.setEnabled(not checked)

    def _run_prune(self):
        reply = QMessageBox.question(
            self, "Confirmar Prune",
            "¿Estás seguro? Esta operación eliminará recursos no usados de Docker.\n\n"
            "Los datos en volúmenes se perderán permanentemente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        self.result_output.setPlainText("Ejecutando prune...")
        self._worker = PruneWorker(
            self.chk_all.isChecked(),
            self.chk_all.isChecked() or self.chk_containers.isChecked(),
            self.chk_all.isChecked() or self.chk_images.isChecked(),
            self.chk_all.isChecked() or self.chk_volumes.isChecked(),
            self.chk_all.isChecked() or self.chk_networks.isChecked(),
        )
        self._worker.output.connect(self.result_output.setPlainText)
        self._worker.finished.connect(
            lambda: self.result_output.append("\n✅ Prune completado"),
            Qt.ConnectionType.QueuedConnection,
        )
        self._worker.start()
