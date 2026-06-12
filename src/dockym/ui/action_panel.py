from __future__ import annotations

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                               QHBoxLayout, QComboBox, QFrame, QGridLayout,
                               QSizePolicy, QSpacerItem, QProgressBar)
from PySide6.QtCore import Signal, Qt

from dockym.models.project import Service
from dockym.ui.icons import make_icon_button


class ActionPanel(QWidget):
    action_start = Signal(object)
    action_stop = Signal(object)
    action_restart = Signal(object)
    action_logs = Signal(object)
    action_env = Signal(object)
    action_exec = Signal(object)

    # Quick actions signals
    action_restart_all = Signal()
    action_prune = Signal()
    action_pull_images = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service: Service | None = None
        self._active_operation: str | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── SECTION: Service Info Card ──────────────────────────
        self._service_section_label = self._make_section_label("SERVICIO")
        layout.addWidget(self._service_section_label)

        self.info_card = QFrame()
        self.info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(self.info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(6)

        self.lbl_name = QLabel("—")
        self.lbl_name.setObjectName("svcName")
        info_layout.addWidget(self.lbl_name)

        self.lbl_image = QLabel("—")
        self.lbl_image.setObjectName("svcDetail")
        info_layout.addWidget(self.lbl_image)

        self.lbl_status = QLabel("—")
        self.lbl_status.setObjectName("svcStatus")
        info_layout.addWidget(self.lbl_status)

        self.lbl_ports = QLabel("—")
        self.lbl_ports.setObjectName("svcDetail")
        info_layout.addWidget(self.lbl_ports)

        layout.addWidget(self.info_card)

        # ── Section Divider ─────────────────────────────────────
        divider1 = QFrame()
        divider1.setObjectName("sectionDivider")
        divider1.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider1)

        # ── SECTION: Primary Actions ────────────────────────────
        self._actions_label = self._make_section_label("ACCIONES")
        layout.addWidget(self._actions_label)

        self.btn_start = self._make_button("Iniciar", primary=True)
        self.btn_stop = self._make_button("Detener", danger=True)
        self.btn_restart = self._make_button("Reiniciar")

        action_card = QFrame()
        action_card.setObjectName("actionCard")
        action_grid = QGridLayout(action_card)
        action_grid.setContentsMargins(10, 8, 10, 8)
        action_grid.setSpacing(6)

        action_grid.addWidget(self.btn_start, 0, 0)
        action_grid.addWidget(self.btn_stop, 0, 1)
        action_grid.addWidget(self.btn_restart, 1, 0, 1, 2)

        for btn in (self.btn_start, self.btn_stop, self.btn_restart):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(action_card)

        # ── Section Divider ─────────────────────────────────────
        divider2 = QFrame()
        divider2.setObjectName("sectionDivider")
        divider2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider2)

        # ── SECTION: Tools ──────────────────────────────────────
        self._tools_label = self._make_section_label("HERRAMIENTAS")
        layout.addWidget(self._tools_label)

        self.btn_logs = self._make_button("Ver logs")
        self.btn_env = self._make_button("Editar .env")
        self.btn_exec = self._make_button("Ejecutar comando")

        tools_card = QFrame()
        tools_card.setObjectName("actionCard")
        tools_grid = QGridLayout(tools_card)
        tools_grid.setContentsMargins(10, 8, 10, 8)
        tools_grid.setSpacing(6)

        tools_grid.addWidget(self.btn_logs, 0, 0)
        tools_grid.addWidget(self.btn_env, 0, 1)
        tools_grid.addWidget(self.btn_exec, 1, 0, 1, 2)

        for btn in (self.btn_logs, self.btn_env, self.btn_exec):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(tools_card)

        # ── Section Divider ─────────────────────────────────────
        divider3 = QFrame()
        divider3.setObjectName("sectionDivider")
        divider3.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider3)

        # ── SECTION: Quick Actions ──────────────────────────────
        layout.addWidget(self._make_section_label("ACCIONES RÁPIDAS"))

        self.btn_restart_all = make_icon_button("Reiniciar todo", "restart")
        self.btn_prune = make_icon_button("Limpiar Docker", "broom")
        self.btn_pull = make_icon_button("Actualizar imágenes", "download")

        quick_card = QFrame()
        quick_card.setObjectName("actionCard")
        quick_grid = QGridLayout(quick_card)
        quick_grid.setContentsMargins(10, 8, 10, 8)
        quick_grid.setSpacing(6)

        quick_grid.addWidget(self.btn_restart_all, 0, 0)
        quick_grid.addWidget(self.btn_prune, 0, 1)
        quick_grid.addWidget(self.btn_pull, 1, 0, 1, 2)

        for btn in (self.btn_restart_all, self.btn_prune, self.btn_pull):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(quick_card)

        # ── Progress bar for long operations ────────────────────
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setMaximumHeight(4)
        layout.addWidget(self._progress)

        # Push content up
        layout.addStretch()

        # ── Signal connections ──────────────────────────────────
        self.btn_start.clicked.connect(lambda: self._emit_if_service(self.action_start))
        self.btn_stop.clicked.connect(lambda: self._emit_if_service(self.action_stop))
        self.btn_restart.clicked.connect(lambda: self._emit_if_service(self.action_restart))
        self.btn_logs.clicked.connect(lambda: self._emit_if_service(self.action_logs))
        self.btn_env.clicked.connect(lambda: self._emit_if_service(self.action_env))
        self.btn_exec.clicked.connect(lambda: self._emit_if_service(self.action_exec))

        # Quick action connections
        self.btn_restart_all.clicked.connect(self.action_restart_all.emit)
        self.btn_prune.clicked.connect(self.action_prune.emit)
        self.btn_pull.clicked.connect(self.action_pull_images.emit)

        self._set_buttons_enabled(False)

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _make_button(self, text: str, primary: bool = False, danger: bool = False) -> QPushButton:
        btn = QPushButton(text)
        if primary:
            btn.setObjectName("btn-primary")
        elif danger:
            btn.setObjectName("btn-danger")
        return btn

    # ── Properties / Setters ────────────────────────────────────

    @property
    def service(self) -> Service | None:
        return self._service

    @service.setter
    def service(self, svc: Service | None) -> None:
        self._service = svc
        self._active_operation = None
        if svc:
            self.lbl_name.setText(svc.name)
            self.lbl_image.setText(f"Imagen:  {svc.image or '—'}")
            self.lbl_status.setText(f"Estado:  {svc.status_icon}  {svc.status_label}")
            self.lbl_ports.setText(f"Puertos:  {svc.ports or '—'}")
            self._update_buttons_for_status(svc.status)
        else:
            self.lbl_name.setText("Selecciona un servicio")
            self.lbl_image.setText("—")
            self.lbl_status.setText("—")
            self.lbl_ports.setText("—")
            self._set_buttons_enabled(False)

    # ── Button state management ─────────────────────────────────

    def _update_buttons_for_status(self, status: str) -> None:
        """Update button enabled state, text, and tooltips based on service status."""
        is_running = status == "running"
        is_stopped = status in ("exited", "created", "dead")
        is_paused = status == "paused"
        is_transient = status in ("restarting", "removing")

        if is_transient:
            # During transient states, disable all action buttons
            for btn in (self.btn_start, self.btn_stop, self.btn_restart,
                         self.btn_logs, self.btn_env, self.btn_exec):
                btn.setEnabled(False)
            self.btn_start.setToolTip("Esperando operación en curso…")
            self.btn_stop.setToolTip("Esperando operación en curso…")
            self.btn_restart.setToolTip("Esperando operación en curso…")
            self.btn_logs.setToolTip("Ver logs del servicio (Ctrl+L)")
            self.btn_env.setToolTip("Editar archivo .env del servicio")
            self.btn_exec.setToolTip("Ejecutar comando en el contenedor (Ctrl+E)")
            return

        # Start button: enabled only if stopped, created, or paused
        self.btn_start.setEnabled(is_stopped or is_paused)
        if is_paused:
            self.btn_start.setText("Reanudar")
            self.btn_start.setToolTip("Reanudar servicio pausado")
        else:
            self.btn_start.setText("Iniciar")
            if is_stopped:
                self.btn_start.setToolTip("Iniciar el servicio")
            else:
                self.btn_start.setToolTip("El servicio ya está en ejecución")

        # Stop button: enabled only if running or paused
        self.btn_stop.setEnabled(is_running or is_paused)
        if is_running or is_paused:
            self.btn_stop.setToolTip("Detener el servicio")
        else:
            self.btn_stop.setToolTip("El servicio ya está detenido")

        # Restart: enabled if running
        self.btn_restart.setEnabled(is_running)
        if is_running:
            self.btn_restart.setToolTip("Reiniciar el servicio (Ctrl+R)")
        else:
            self.btn_restart.setToolTip("Solo disponible cuando el servicio está en ejecución")

        # Logs: always enabled when a service is selected
        self.btn_logs.setEnabled(True)
        self.btn_logs.setToolTip("Ver logs del servicio (Ctrl+L)")

        # Env: always enabled when a service is selected
        self.btn_env.setEnabled(True)
        self.btn_env.setToolTip("Editar archivo .env del servicio")

        # Exec: only enabled if running
        self.btn_exec.setEnabled(is_running)
        if is_running:
            self.btn_exec.setToolTip("Ejecutar comando en el contenedor (Ctrl+E)")
        else:
            self.btn_exec.setToolTip("Solo disponible cuando el servicio está en ejecución")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in (self.btn_start, self.btn_stop, self.btn_restart,
                     self.btn_logs, self.btn_env, self.btn_exec):
            btn.setEnabled(enabled)

    def set_loading(self, loading: bool, operation: str | None = None) -> None:
        """Show loading state for a specific operation.

        Args:
            loading: Whether the panel is in a loading state.
            operation: The operation name (start, stop, restart) for targeted
                       button text update.  When *None* the old behaviour of
                       resetting all buttons applies.
        """
        if loading:
            self._active_operation = operation
            # Disable all buttons during operation
            self._set_buttons_enabled(False)

            # Show loading text only on the affected button
            if operation == "start":
                self.btn_start.setText("Iniciando…")
                self.btn_start.setToolTip("Esperando inicio…")
            elif operation == "stop":
                self.btn_stop.setText("Deteniendo…")
                self.btn_stop.setToolTip("Esperando parada…")
            elif operation == "restart":
                self.btn_restart.setText("Reiniciando…")
                self.btn_restart.setToolTip("Esperando reinicio…")
        else:
            # Reset text and re-enable based on current status
            self._reset_button_texts()
            self._active_operation = None
            if self._service:
                self._update_buttons_for_status(self._service.status)
            else:
                self._set_buttons_enabled(False)

    def _reset_button_texts(self) -> None:
        self.btn_start.setText("Iniciar")
        self.btn_stop.setText("Detener")
        self.btn_restart.setText("Reiniciar")
        self.btn_logs.setText("Ver logs")
        self.btn_env.setText("Editar .env")
        self.btn_exec.setText("Ejecutar comando")

    # ── Batch mode ─────────────────────────────────────────────
    # (Removed — multi-selection no longer triggers a batch UI.)

    def set_quick_actions_loading(self, loading: bool, operation: str | None = None) -> None:
        """Show loading state for quick actions."""
        if loading:
            self._progress.setVisible(True)
            self.btn_restart_all.setEnabled(False)
            self.btn_prune.setEnabled(False)
            self.btn_pull.setEnabled(False)
            if operation == "restart_all":
                self.btn_restart_all.setText("Reiniciando…")
            elif operation == "pull_images":
                self.btn_pull.setText("Actualizando…")
            elif operation == "prune":
                self.btn_prune.setText("Limpiando…")
        else:
            self._progress.setVisible(False)
            self.btn_restart_all.setEnabled(True)
            self.btn_prune.setEnabled(True)
            self.btn_pull.setEnabled(True)
            self.btn_restart_all.setText("Reiniciar todo")
            self.btn_prune.setText("Limpiar Docker")
            self.btn_pull.setText("Actualizar imágenes")

    # ── Signal emitters ─────────────────────────────────────────

    def _emit_if_service(self, signal: Signal) -> None:
        if self._service and self._active_operation is None:
            signal.emit(self._service)
