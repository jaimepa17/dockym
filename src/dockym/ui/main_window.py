from __future__ import annotations

from time import time
from PySide6.QtWidgets import (QMainWindow, QSplitter, QStatusBar,
                               QLabel, QMessageBox, QWidget, QVBoxLayout,
                               QHBoxLayout, QFrame, QSizePolicy, QApplication,
                               QPushButton, QMenu, QMenuBar)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, QEvent, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut, QMouseEvent

from dockym.ui.title_bar import TitleBar
from dockym.ui.service_table import ServiceTable
from dockym.ui.action_panel import ActionPanel
from dockym.ui.tray_manager import TrayManager
from dockym.ui.notification import NotificationManager, NotificationType, NotificationCenter
from dockym.ui.command_palette import CommandPalette, SearchResult
from dockym.models.config import Config
from dockym.models.project import Project, Service
from dockym.workers.docker_worker import DockerPool
from dockym.engine.events import DockerEventsWorker
from dockym.ui.logs_dialog import LogsDialog
from dockym.ui.env_dialog import EnvDialog
from dockym.ui.exec_dialog import ExecDialog
from dockym.ui.settings_dialog import SettingsDialog
from dockym.ui.appearance_dialog import AppearanceDialog
from dockym.ui.export_dialog import ExportImportDialog
from dockym.ui.prune_dialog import PruneDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dockym")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # NOTE: We NEVER call self.menuBar() here — it creates a native
        # QMenuBar that shows ⋮ dots on Linux and takes layout space even
        # when hidden. Our custom QMenuBar is created in _setup_menubar()
        # and added to the root layout directly.

        self.resize(1300, 850)
        self.setMinimumSize(1000, 600)

        self.config = Config.load()
        self.projects: list[Project] = []
        self._selected_project: Project | None = None
        self._selected_service: Service | None = None
        self._pool = DockerPool(self)
        self._events_worker: DockerEventsWorker | None = None
        self._tray: TrayManager | None = None
        self._minimize_to_tray = True
        self._quitting = False
        self._closing_animation: QPropertyAnimation | None = None
        self._notifications: NotificationManager | None = None
        self._command_palette: CommandPalette | None = None
        self._project_scan_cache: tuple[float, list[Project]] = (0.0, [])
        self._container_status_cache: dict[str, tuple[float, str]] = {}
        self._cache_ttl = 2.0
        self._selected_container_names: list[str] = []

        # Frameless resize tracking
        self._resize_edge: Qt.Edge | None = None
        self._resize_start_rect: QRect | None = None
        self._resize_start_pos: QPoint | None = None

        # Custom title bar
        self._title_bar = TitleBar(self)
        self._title_bar.minimize_clicked.connect(self._on_title_minimize)
        self._title_bar.maximize_clicked.connect(self._on_title_maximize)
        self._title_bar.close_clicked.connect(self._on_title_close)
        self._title_bar.bell_clicked.connect(self._on_bell_clicked)
        self._title_bar.set_icon(self.windowIcon())
        self._notif_center: NotificationCenter | None = None

        # Layout widgets (references to keep alive)
        self._splitter: QSplitter | None = None
        self.table = ServiceTable()
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.panel = ActionPanel()
        self.panel.setMinimumWidth(260)
        self.panel.setMinimumHeight(200)

        # Header widgets (simplified — events & count moved to title bar)
        self.title_label: QLabel
        self.subtitle_label: QLabel

        self._setup_menubar()
        self._setup_header()
        self._setup_ui()
        self._setup_status_bar()
        self._setup_tray()
        self._setup_events()
        self._connect_signals()
        # Sync the row-highlight colours with the active theme so the
        # hover/selection visuals are themed correctly.
        from dockym.ui.theme import get_theme_colors
        self.table.tree.set_palette(get_theme_colors(self.config.theme))

    def _setup_menubar(self):
        """Create a custom menu bar widget using QMenuBar with nativeMenuBar=False."""
        self._menu_bar = QMenuBar()
        self._menu_bar.setNativeMenuBar(False)
        self._menu_bar.setFixedHeight(36)

        # File menu
        file_menu = self._menu_bar.addMenu("Archivo")
        act_refresh = QAction("Refrescar", self)
        act_refresh.setShortcut(QKeySequence("F5"))
        act_refresh.setStatusTip("Actualizar la lista de proyectos Docker")
        act_refresh.triggered.connect(self.refresh_state)
        file_menu.addAction(act_refresh)

        act_export = QAction("Exportar / Importar…", self)
        act_export.triggered.connect(self._open_export)
        file_menu.addAction(act_export)

        file_menu.addSeparator()
        act_prune = QAction("Limpiar Docker…", self)
        act_prune.triggered.connect(self._open_prune)
        file_menu.addAction(act_prune)

        file_menu.addSeparator()
        act_quit = QAction("Salir", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.setStatusTip("Salir de Dockym")
        act_quit.triggered.connect(self._quit_app)
        file_menu.addAction(act_quit)

        # Edit menu
        edit_menu = self._menu_bar.addMenu("Editar")
        act_settings = QAction("Configuración…", self)
        act_settings.setShortcut(QKeySequence("Ctrl+,"))
        act_settings.setStatusTip("Abrir configuración de Dockym")
        act_settings.triggered.connect(self._open_settings)
        edit_menu.addAction(act_settings)

        act_appearance = QAction("Apariencia…", self)
        act_appearance.setShortcut(QKeySequence("Ctrl+Shift+A"))
        act_appearance.setStatusTip("Configurar apariencia, tema y fuentes")
        act_appearance.triggered.connect(self._open_appearance)
        edit_menu.addAction(act_appearance)

        # View menu
        view_menu = self._menu_bar.addMenu("Ver")
        act_toggle_tray = QAction("Bandeja del sistema", self)
        act_toggle_tray.setCheckable(True)
        act_toggle_tray.setChecked(True)
        view_menu.addAction(act_toggle_tray)

        # Help menu
        help_menu = self._menu_bar.addMenu("Ayuda")
        act_about = QAction("Acerca de Dockym", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

        # Store ref for layout
        self._menu_widget = self._menu_bar

        # Global keyboard shortcuts
        shortcut_f = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_f.activated.connect(self._open_command_palette)
        shortcut_e = QShortcut(QKeySequence("Ctrl+E"), self)
        shortcut_e.activated.connect(self._exec_service)
        shortcut_l = QShortcut(QKeySequence("Ctrl+L"), self)
        shortcut_l.activated.connect(self._view_logs)
        shortcut_r = QShortcut(QKeySequence("Ctrl+R"), self)
        shortcut_r.activated.connect(self._on_restart)
        shortcut_a = QShortcut(QKeySequence("Ctrl+A"), self)
        shortcut_a.activated.connect(self._select_all)

    def _setup_header(self):
        """Build the compact header bar below the menu."""
        header_bar = QFrame()
        header_bar.setObjectName("headerBar")
        header_bar.setFixedHeight(36)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(6)

        self.title_label = QLabel("Proyectos")
        self.title_label.setObjectName("headerTitle")
        header_layout.addWidget(self.title_label)

        # Separator dot
        sep = QLabel("·")
        sep.setObjectName("headerSep")
        header_layout.addWidget(sep)

        # Subtitle - brief description
        self.subtitle_label = QLabel("Docker services")
        self.subtitle_label.setObjectName("headerSubtitle")
        header_layout.addWidget(self.subtitle_label)

        header_layout.addStretch()

        # Selection count badge (hidden by default)
        self.selection_label = QLabel("")
        self.selection_label.setObjectName("countLabel")
        self.selection_label.setVisible(False)
        header_layout.addWidget(self.selection_label)

        # Store header reference for layout rebuild
        self._header_bar = header_bar

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        self._root_layout = QVBoxLayout(central)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Title bar at the very top
        self._root_layout.addWidget(self._title_bar)
        # Menu bar below title bar
        self._root_layout.addWidget(self._menu_widget)
        self._root_layout.addWidget(self._header_bar)
        self._rebuild_layout()
        self._setup_notifications()
        self._setup_command_palette()

    # ── Layout rebuild ───────────────────────────────────────────

    def _rebuild_layout(self):
        """Rebuild the main splitter layout based on panel position config."""
        # Remove old splitter if present
        if self._splitter is not None:
            self._root_layout.removeWidget(self._splitter)
            self._splitter.setParent(None)
            self._splitter.deleteLater()
            self._splitter = None

        position = self.config.panel_position

        self._splitter = QSplitter()
        self._splitter.setObjectName("mainSplitter")

        if position == "left":
            self._splitter.setOrientation(Qt.Orientation.Horizontal)
            self.panel.setMaximumWidth(400)
            self.panel.setMaximumHeight(16777215)
            self._splitter.addWidget(self.panel)
            self._splitter.addWidget(self.table)
            self._splitter.setSizes([280, 1020])
        elif position == "bottom":
            self._splitter.setOrientation(Qt.Orientation.Vertical)
            self.panel.setMaximumWidth(16777215)
            self.panel.setMaximumHeight(500)
            self._splitter.addWidget(self.table)
            self._splitter.addWidget(self.panel)
            self._splitter.setSizes([550, 300])
        else:  # "right" (default)
            self._splitter.setOrientation(Qt.Orientation.Horizontal)
            self.panel.setMaximumWidth(400)
            self.panel.setMaximumHeight(16777215)
            self._splitter.addWidget(self.table)
            self._splitter.addWidget(self.panel)
            self._splitter.setSizes([1020, 280])

        self._splitter.setHandleWidth(1)
        self._root_layout.addWidget(self._splitter, 1)

    # ── Status bar ───────────────────────────────────────────────

    def _setup_status_bar(self):
        """Create a compact status bar at the bottom."""
        status = QStatusBar(self)
        status.setObjectName("statusBar")
        self.setStatusBar(status)
        status.showMessage("Dockym listo", 3000)

    # ── System tray ──────────────────────────────────────────────

    def _setup_tray(self):
        """Create and configure the system tray icon."""
        self._tray = TrayManager(self)
        self._tray.show_requested.connect(self._on_tray_show)
        self._tray.quit_requested.connect(self._quit_app)

    def _on_tray_show(self):
        """Show the window from tray activation."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    # ── Docker events ────────────────────────────────────────────

    def _setup_events(self):
        """Start the Docker events listener thread."""
        self._title_bar.set_events_connecting()
        self._events_worker = DockerEventsWorker(self)
        self._events_worker.event_occurred.connect(self._on_docker_event)
        self._events_worker.connected.connect(self._on_events_connected)
        self._events_worker.error_occurred.connect(self._on_events_error)
        self._events_worker.start()

    def _on_docker_event(self, action: str, container_name: str):
        """Handle a Docker container event (start, stop, die, etc.)."""
        QTimer.singleShot(300, self.refresh_state)

    def _on_events_connected(self):
        """Mark the events indicator as connected."""
        self._title_bar.set_events_connected(True)
        if self._notifications:
            self._notifications.info("Docker events conectados")

    def _on_events_error(self, error: str):
        """Handle events connection error."""
        self._title_bar.set_events_error(error)

    # ── Signal wiring ────────────────────────────────────────────

    def _connect_signals(self):
        """Wire up signals from table, panel, and other widgets."""
        # Table signals
        self.table.service_selected.connect(self._on_service_selected)
        self.table.selection_changed.connect(self._on_selection_changed)
        self.table.action_requested.connect(self._on_row_action_requested)

        # Panel action signals
        self.panel.action_start.connect(self._on_start)
        self.panel.action_stop.connect(self._on_stop)
        self.panel.action_restart.connect(self._on_restart)
        self.panel.action_logs.connect(self._view_logs)
        self.panel.action_env.connect(self._edit_env)
        self.panel.action_exec.connect(self._exec_service)
        self.panel.action_restart_all.connect(self._on_restart_all)
        self.panel.action_prune.connect(self._open_prune)
        self.panel.action_pull_images.connect(self._on_pull_images)

        # Auto-refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._fast_refresh)
        self._refresh_timer.start(self.config.refresh_interval * 1000)

        # Initial load
        QTimer.singleShot(100, self.refresh_state)

    # ── Title bar handlers ───────────────────────────────────────

    def _on_title_minimize(self):
        """Minimize the window."""
        self.showMinimized()

    def _on_title_maximize(self):
        """Toggle maximize/restore."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._title_bar.update_maximize_button(self.isMaximized())

    def _on_title_close(self):
        """Close to tray or quit depending on config."""
        if self._minimize_to_tray and self._tray:
            self.hide()
        else:
            self._quit_app()

    def _on_bell_clicked(self):
        """Toggle the notification center popup beneath the bell button."""
        if self._notif_center is None:
            return
        if self._notif_center.isVisible():
            self._notif_center.hide()
            return
        self._notif_center.show_below(self._title_bar.bell_button())

    # ── Refresh / scan ───────────────────────────────────────────

    def refresh_state(self):
        """Full refresh: rescan projects and update the UI."""
        self._load_projects()

    def _load_projects(self):
        """Scan for Docker Compose projects in configured paths."""
        signals = self._pool.scan(self.config.paths)
        signals.scan_finished.connect(self._on_scan_finished)
        signals.scan_error.connect(self._on_scan_error)

    def _on_scan_finished(self, projects: list[Project]):
        """Handle scan results: update projects and table."""
        self.projects = projects
        self._project_scan_cache = (time(), projects)
        self._refresh_services()
        # Update subtitle with counts
        total = sum(p.total_count for p in projects)
        running = sum(p.running_count for p in projects)
        self.subtitle_label.setText(
            f"{len(projects)} proyectos · {running}/{total} servicios activos"
        )
        self._title_bar.set_count(f"{running}/{total}")
        # Update command palette index
        if self._command_palette:
            self._command_palette.set_projects(projects)

    def _on_scan_error(self, error: str):
        """Handle scan error."""
        if self._notifications:
            self._notifications.error(f"Error escaneando: {error}")

    def _refresh_services(self):
        """Reload the service table with current projects."""
        self.table.load_projects(self.projects)

    def _fast_refresh(self):
        """Quick periodic refresh — rescan projects silently."""
        self._load_projects()

    # ── Project / service selection ──────────────────────────────

    def _on_project_clicked(self, project: Project):
        """Handle a project being clicked in the tree."""
        self._selected_project = project
        self._selected_service = None
        self.panel.service = None

    def _on_service_selected(self, service: Service):
        """Handle a service being selected — update the action panel."""
        self._selected_service = service
        # Find the parent project
        for p in self.projects:
            for s in p.services:
                if s is service or s.name == service.name:
                    self._selected_project = p
                    break
        self.panel.service = service

    def _on_row_action_requested(self, project_name: str, svc_name: str):
        """User clicked the play/stop button on a service row.

        Decides which compose operation to run based on the service's
        current status: running/paused → stop, anything else → start.
        """
        for p in self.projects:
            if p.name != project_name:
                continue
            for s in p.services:
                if s.name == svc_name:
                    self._selected_service = s
                    self._selected_project = p
                    self.panel.service = s
                    if s.status in ("running", "paused"):
                        self._run_compose("stop_service")
                    else:
                        self._run_compose("start_service")
                    return

    # ── Compose operations ───────────────────────────────────────

    def _run_compose(self, method: str):
        """Run a compose operation for the selected project/service."""
        svc = self._selected_service
        if not svc:
            return

        project_path = svc.project_path
        if not project_path and self._selected_project:
            project_path = self._selected_project.path
        if not project_path:
            if self._notifications:
                self._notifications.error("No hay ruta de proyecto seleccionada")
            return

        self.panel.set_loading(True, method.replace("service_", ""))
        signals = self._pool.compose(method, project_path, svc.name)
        signals.operation_finished.connect(
            lambda msg: self._on_compose_finished(method, msg),
            Qt.ConnectionType.QueuedConnection,
        )
        signals.operation_error.connect(
            lambda err: self._on_compose_error(method, err),
            Qt.ConnectionType.QueuedConnection,
        )

    def _on_compose_finished(self, method: str, message: str):
        """Handle compose operation completion."""
        self.panel.set_loading(False)
        if self._notifications:
            self._notifications.success(message)
        QTimer.singleShot(500, self.refresh_state)

    def _on_compose_error(self, method: str, error: str):
        """Handle compose operation error."""
        self.panel.set_loading(False)
        if self._notifications:
            self._notifications.error(f"Error: {error}")

    def _on_start(self, service: Service):
        """Start a service."""
        self._run_compose("start_service")

    def _on_stop(self, service: Service):
        """Stop a service."""
        self._run_compose("stop_service")

    def _on_restart(self):
        """Restart the currently selected service."""
        if self._selected_service:
            self._run_compose("restart_service")

    # ── Tool dialogs ─────────────────────────────────────────────

    def _view_logs(self, service: Service | None = None):
        """Open the logs dialog for the given (or selected) service."""
        svc = service or self._selected_service
        if not svc:
            if self._notifications:
                self._notifications.warning("Selecciona un servicio primero")
            return
        dialog = LogsDialog(svc, parent=self)
        dialog.exec()

    def _edit_env(self, service: Service | None = None):
        """Open the .env editor for the given (or selected) service."""
        svc = service or self._selected_service
        if not svc:
            if self._notifications:
                self._notifications.warning("Selecciona un servicio primero")
            return
        dialog = EnvDialog(svc, parent=self)
        dialog.exec()

    def _exec_service(self):
        """Open the exec dialog for the selected service."""
        svc = self._selected_service
        if not svc:
            if self._notifications:
                self._notifications.warning("Selecciona un servicio primero")
            return
        if not svc.is_running:
            if self._notifications:
                self._notifications.warning("El servicio no está en ejecución")
            return
        dialog = ExecDialog(svc, parent=self)
        dialog.exec()

    # ── Settings / config dialogs ────────────────────────────────

    def _open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.config, parent=self)
        if dialog.exec():
            # Apply changed settings
            self.config = Config.load()
            self._minimize_to_tray = self.config.minimize_to_tray
            self._refresh_timer.setInterval(self.config.refresh_interval * 1000)
            self._rebuild_layout()
            self.refresh_state()

    def _open_appearance(self):
        """Open the appearance / theme dialog."""
        dialog = AppearanceDialog(self.config, parent=self)
        if dialog.exec():
            self.config = Config.load()
            self._apply_theme()
            self._rebuild_layout()

    def _apply_theme(self):
        """Regenerate and apply the QSS stylesheet from the current config.

        Called after the appearance dialog saves so theme / font changes take
        effect without a restart.
        """
        from dockym.ui.theme import get_theme_qss, get_theme_colors
        app = QApplication.instance()
        if app is None:
            return
        app.setStyleSheet(get_theme_qss(self.config.theme, self.config.font_family))
        # Refresh the row-highlight colours (hover/selection overlay + accent
        # bars) from the active theme tokens so the continuous-row highlight
        # adapts when the user switches themes.
        colors = get_theme_colors(self.config.theme)
        self.table.tree.set_palette(colors)
        # Repaint everything so cached palettes/styles are flushed
        for w in app.allWidgets():
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def _open_export(self):
        """Open the export/import dialog."""
        dialog = ExportImportDialog(self.projects, self.config, parent=self)
        dialog.exec()

    def _open_prune(self):
        """Open the Docker prune dialog."""
        dialog = PruneDialog(parent=self)
        dialog.exec()

    # ── About / quit ─────────────────────────────────────────────

    def _show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "Acerca de Dockym",
            "<h2>Dockym</h2>"
            "<p>Versión 0.1.0</p>"
            "<p>Administrador de servicios Docker con interfaz gráfica.</p>"
            "<p>Construido con PySide6 / Qt.</p>",
        )

    def _quit_app(self):
        """Quit the application cleanly."""
        self._quitting = True
        if self._events_worker:
            self._events_worker.stop()
        if self._tray:
            self._tray.hide()
        QApplication.quit()

    # ── Command palette ──────────────────────────────────────────

    def _open_command_palette(self):
        """Show the command palette (Ctrl+F / Ctrl+K)."""
        if self._command_palette:
            self._command_palette.show_palette()

    def _select_all(self):
        """Select all services in the tree (Ctrl+A)."""
        self.table.select_all_services()

    # ── Notifications setup ──────────────────────────────────────

    def _setup_notifications(self):
        """Initialize the toast notification manager and the bell-anchored center."""
        self._notifications = NotificationManager(parent=self)
        self._notif_center = NotificationCenter(self._notifications, parent=self)
        # Refresh badge whenever history changes
        self._notifications.history_changed.connect(self._refresh_bell_badge)
        self._refresh_bell_badge()

    def _refresh_bell_badge(self):
        if self._notifications:
            self._title_bar.set_unread_notifications(
                self._notifications.unread_count()
            )

    # ── Command palette setup ────────────────────────────────────

    def _setup_command_palette(self):
        """Initialize the command palette dialog."""
        self._command_palette = CommandPalette(parent=self)
        self._command_palette.set_projects(self.projects)
        self._command_palette.result_selected.connect(self._on_command_result)

    def _on_command_result(self, result: SearchResult):
        """Handle a selection from the command palette."""
        if result.kind == "service" and result.service:
            self._on_service_selected(result.service)
        elif result.kind == "project" and result.project:
            self._on_project_clicked(result.project)

    # ── Selection ────────────────────────────────────────────────

    def _on_selection_changed(self, count: int):
        """Handle multi-selection change in the tree (display-only)."""
        if count > 0:
            self.selection_label.setText(f"{count} seleccionados")
            self.selection_label.setVisible(True)
        else:
            self.selection_label.setVisible(False)
        self._selected_container_names = []

    # ── System-wide actions ──────────────────────────────────────

    def _on_restart_all(self):
        """Restart all running containers."""
        self.panel.set_quick_actions_loading(True, "restart_all")
        signals = self._pool.system_operation("restart_all")
        signals.operation_finished.connect(self._on_system_finished)
        signals.operation_error.connect(self._on_system_error)

    def _on_pull_images(self):
        """Pull latest images for all containers."""
        self.panel.set_quick_actions_loading(True, "pull_images")
        signals = self._pool.system_operation("pull_images")
        signals.operation_finished.connect(self._on_system_finished)
        signals.operation_error.connect(self._on_system_error)

    def _refresh_docker_system_info(self):
        """Refresh Docker system information."""
        signals = self._pool.system_operation("system_info")
        signals.operation_finished.connect(
            lambda msg: self.statusBar().showMessage(f"Docker: {msg[:80]}", 5000),
            Qt.ConnectionType.QueuedConnection,
        )
        signals.operation_error.connect(
            lambda err: self.statusBar().showMessage(f"Error: {err}", 5000),
            Qt.ConnectionType.QueuedConnection,
        )

    def _on_system_finished(self, message: str):
        """Handle system operation completion."""
        self.panel.set_quick_actions_loading(False)
        if self._notifications:
            self._notifications.success(message)
        QTimer.singleShot(500, self.refresh_state)

    def _on_system_error(self, error: str):
        """Handle system operation error."""
        self.panel.set_quick_actions_loading(False)
        if self._notifications:
            self._notifications.error(f"Error: {error}")

    # ── Window events ────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent):
        """Handle window close — minimize to tray or quit."""
        if self._quitting:
            event.accept()
            return

        if self._minimize_to_tray and self._tray:
            event.ignore()
            self.hide()
            return

        # Clean up before quitting
        self._quitting = True
        if self._events_worker:
            self._events_worker.stop()
        if self._tray:
            self._tray.hide()
        event.accept()

    def changeEvent(self, event: QEvent):
        """Handle window state changes (maximize/restore button update)."""
        if event.type() == QEvent.Type.WindowStateChange:
            self._title_bar.update_maximize_button(self.isMaximized())
        super().changeEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for frameless window resize edges."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edge = self._hit_test_edges(pos)
            if edge is not None:
                self._resize_edge = edge
                self._resize_start_rect = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for frameless window resize."""
        if self._resize_edge is not None and self._resize_start_pos is not None:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            r = self._resize_start_rect
            if r is None:
                return
            new_geom = QRect(r)
            edges = self._resize_edge

            if edges & Qt.Edge.LeftEdge:
                new_geom.setLeft(r.left() + delta.x())
            if edges & Qt.Edge.RightEdge:
                new_geom.setRight(r.right() + delta.x())
            if edges & Qt.Edge.TopEdge:
                new_geom.setTop(r.top() + delta.y())
            if edges & Qt.Edge.BottomEdge:
                new_geom.setBottom(r.bottom() + delta.y())

            min_w = self.minimumWidth()
            min_h = self.minimumHeight()
            if new_geom.width() < min_w:
                if edges & Qt.Edge.LeftEdge:
                    new_geom.setLeft(new_geom.right() - min_w + 1)
            if new_geom.height() < min_h:
                if edges & Qt.Edge.TopEdge:
                    new_geom.setTop(new_geom.bottom() - min_h + 1)

            self.setGeometry(new_geom)
            event.accept()
            return

        # Update cursor shape when hovering near edges
        pos = event.position().toPoint()
        edge = self._hit_test_edges(pos)
        if edge is not None:
            if edge & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
                if edge & Qt.Edge.LeftEdge:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                else:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                if edge & Qt.Edge.TopEdge:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif edge & Qt.Edge.BottomEdge:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif edge & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end resize."""
        if self._resize_edge is not None:
            self._resize_edge = None
            self._resize_start_rect = None
            self._resize_start_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _hit_test_edges(self, pos: QPoint) -> Qt.Edge | None:
        """Return which edge(s) the mouse position is near, or None."""
        margin = 6
        geom = self.rect()
        x, y = pos.x(), pos.y()

        edges = Qt.Edge(0)
        if x < margin:
            edges |= Qt.Edge.LeftEdge
        elif x > geom.width() - margin:
            edges |= Qt.Edge.RightEdge

        if y < margin:
            edges |= Qt.Edge.TopEdge
        elif y > geom.height() - margin:
            edges |= Qt.Edge.BottomEdge

        return edges if edges else None
