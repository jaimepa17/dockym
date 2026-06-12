"""Service / project tree widget with a per-row action button.

Replaces the previous search-bar UI. Each service row gets a context button
(play/stop) rendered directly in the last column via a custom delegate-style
QToolButton. The tree emits ``action_requested`` whenever the user clicks
that button; ``MainWindow`` decides whether to start or stop based on the
service's current status.

The row hover/selection is painted by a custom ``paintEvent`` on the
QTreeWidget subclass — this guarantees a single, full-width rounded
rect across all columns, which is impossible to achieve via QSS alone
because Qt paints each cell background independently.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize, QEvent, QRect, QRectF, QObject, QModelIndex
from PySide6.QtGui import QColor, QBrush, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QLineEdit, QVBoxLayout, QWidget,
    QStyleOptionViewItem, QStyle, QToolButton, QHeaderView,
)
# Re-export QTreeWidgetItemIterator from QtWidgets (PySide6 6.7+)
from PySide6.QtWidgets import QTreeWidgetItemIterator

from dockym.models.project import Project, Service
from dockym.ui.icons import icon_pixmap

# Status colors - consistent with design system
STATUS_COLOR = {
    "running": QColor("#3fb950"),
    "exited": QColor("#8b949e"),
    "paused": QColor("#d29922"),
    "restarting": QColor("#d29922"),
    "created": QColor("#8b949e"),
    "removing": QColor("#8b949e"),
    "dead": QColor("#f85149"),
}

STATUS_ICON = {
    "running": "●",
    "exited": "○",
    "paused": "◐",
    "restarting": "↻",
    "created": "◌",
    "removing": "×",
    "dead": "✕",
}

STATUS_LABEL = {
    "running": "En ejecución",
    "exited": "Detenido",
    "paused": "Pausado",
    "restarting": "Reiniciando",
    "created": "Creado",
    "removing": "Eliminando",
    "dead": "Muerto",
}


# ─────────────────────────────────────────────────────────────────
# Row-level highlight is painted by the tree itself in its own
# paintEvent, after the default per-cell paint. This is the only way to
# guarantee a single, full-width rounded rect across all columns — QSS
# selectors and per-cell delegates can't do it because each cell
# repaints its own background independently.
# ─────────────────────────────────────────────────────────────────


class ServiceTree(QTreeWidget):
    service_selected = Signal(object)
    project_selected = Signal(str)
    selection_changed = Signal(int)  # emits count of selected services
    # Emitted when the user clicks the per-row action button. The recipient
    # uses the service's current status to decide whether to start or stop.
    action_requested = Signal(str, str)  # (project_name, service_name)

    # Column indices
    COL_NAME = 0
    COL_IMAGE = 1
    COL_STATUS = 2
    COL_PORTS = 3
    COL_ACTION = 4

    # Colours — refreshed by MainWindow._apply_theme() when the theme changes.
    # Defaults match the dark theme.
    HOVER_OVERLAY = QColor("#1c2128")
    SELECTED_OVERLAY = QColor(31, 111, 235, 36)   # accent @ ~14% alpha
    ACCENT_HOVER = QColor("#58a6ff")
    ACCENT_SELECTED = QColor("#1f6feb")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Servicio", "Ruta / Imagen", "Estado", "Puertos", ""])
        # Action column is visible (it holds the play/stop button) but its
        # header has no caption — we remove the text via the model.
        self.header().setSectionResizeMode(self.COL_ACTION, QHeaderView.ResizeMode.Fixed)
        self.header().resizeSection(self.COL_ACTION, 64)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(self.COL_PORTS, QHeaderView.ResizeMode.Stretch)
        # Make the action column's header blank (no text shown)
        self.model().setHeaderData(self.COL_ACTION, Qt.Orientation.Horizontal,
                                   "", Qt.ItemDataRole.DisplayRole)

        self.setIndentation(20)
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(True)
        # No alternating colors — uniform background across all rows so the
        # service list reads as a single panel instead of striped rows.
        self.setAlternatingRowColors(False)
        self.setExpandsOnDoubleClick(True)
        self.setItemsExpandable(True)
        self.setMinimumHeight(200)
        self.setColumnWidth(self.COL_NAME, 220)
        self.setColumnWidth(self.COL_IMAGE, 280)
        self.setColumnWidth(self.COL_STATUS, 130)

        # Track the row currently under the cursor — the actual highlight
        # is rendered by a transparent overlay widget that lives inside
        # the viewport (so the WM doesn't interfere).
        self._hovered_row: int | None = None
        self._row_overlay = _RowHighlightOverlay(self.viewport())
        self.viewport().installEventFilter(self)
        self.setMouseTracking(True)

        # Storage for buttons / items — initialised here (not at class body
        # level, which would be unreachable dead code after a return).
        self._project_items: dict[str, QTreeWidgetItem] = {}
        self._service_items: dict[tuple[str, str], QTreeWidgetItem] = {}
        self._row_buttons: dict[tuple[str, str], QToolButton] = {}
        self._all_items: list[QTreeWidgetItem] = []

        self.itemClicked.connect(self._on_item_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)

    def eventFilter(self, obj, event):
        """Track the hovered row; updates the overlay's row state."""
        if obj is not self.viewport():
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.MouseMove:
            idx = self.indexAt(event.pos())
            row = idx.row() if idx.isValid() else None
            if row != self._hovered_row:
                self._hovered_row = row
                self._row_overlay.set_row(row, False)
        elif event.type() in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress):
            if self._hovered_row is not None:
                self._hovered_row = None
                self._row_overlay.set_row(None, False)
        return super().eventFilter(obj, event)

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        if self._row_overlay is not None:
            sel_row = None
            for item in self.selectedItems():
                payload = item.data(0, Qt.ItemDataRole.UserRole)
                if payload and payload[0] == "service":
                    idx = self.indexFromItem(item)
                    if idx.isValid():
                        sel_row = idx.row()
                        break
            self._row_overlay.set_row(sel_row, True)

    def _ensure_overlay_position(self) -> None:
        """Reposition the overlay widget to cover the active row's geometry."""
        if self._row_overlay._row is None:
            self._row_overlay.hide()
            return
        rect = self._row_rect_for(self._row_overlay._row)
        if rect is None or rect.height() <= 0:
            self._row_overlay.hide()
            return
        self._row_overlay.setGeometry(rect)
        self._row_overlay.show()
        self._row_overlay.raise_()
        # Force a paint so the hover/selection state is reflected
        # immediately even if the rest of the viewport doesn't redraw.
        self._row_overlay.update()

    def set_palette(self, colors: dict) -> None:
        """Refresh the highlight colours from the active theme tokens."""
        self.HOVER_OVERLAY = QColor(colors.get("bg_hover", "#1c2128"))
        accent = QColor(colors.get("accent", "#58a6ff"))
        accent.setAlpha(56)   # 22% alpha — visible but not loud
        self.SELECTED_OVERLAY = accent
        self.ACCENT_HOVER = QColor(colors.get("accent", "#58a6ff"))
        self.ACCENT_SELECTED = QColor(colors.get("accent", "#58a6ff"))
        self.viewport().update()

    def _row_rect_for(self, row: int) -> QRect | None:
        """Combine column rectangles across all columns for *row*."""
        # Find the actual item matching the flat row index
        flat = -1
        target = None
        for it in QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.IteratorFlag.All):
            it_val = it.value()
            payload = it_val.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
            if payload and payload[0] == "service":
                flat += 1
                if flat == row:
                    target = it_val
                    break
        if target is None:
            return None
        visual_rect = self.visualItemRect(target)
        if visual_rect.isEmpty():
            return None
        # Find the rightmost visible column edge
        right = 0
        for c in range(self.header().count()):
            vp = self.columnViewportPosition(c)
            if vp >= 0:
                right = max(right, vp + self.columnWidth(c))
        if right == 0:
            right = self.viewport().width()
        return QRect(visual_rect.x(), visual_rect.y(),
                     max(0, right - visual_rect.x()),
                     visual_rect.height())

    def load_projects(self, projects: list[Project]) -> None:
        # Clear any row buttons so we don't leak widgets
        for btn in self._row_buttons.values():
            btn.setParent(None)
            btn.deleteLater()
        self._row_buttons.clear()
        self.clear()
        self._project_items.clear()
        self._service_items.clear()
        self._all_items.clear()

        if not projects:
            empty_item = QTreeWidgetItem(self)
            empty_item.setText(0, "  No se encontraron proyectos Docker")
            empty_item.setText(1, "Agrega rutas en Configuración (Ctrl+,)")
            empty_item.setForeground(0, QBrush(QColor("#484f58")))
            empty_item.setForeground(1, QBrush(QColor("#484f58")))
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)  # not selectable
            return

        for proj in projects:
            project_item = QTreeWidgetItem(self)
            # Compact project header
            project_item.setText(self.COL_NAME, f"  {proj.name}")
            project_item.setText(self.COL_IMAGE, proj.path)
            project_item.setData(self.COL_NAME, Qt.ItemDataRole.UserRole,
                                 ("project", proj.name))
            project_item.setFont(0, QFont("Inter", 12, QFont.Weight.DemiBold))
            project_item.setForeground(0, QBrush(QColor("#e6edf3")))
            project_item.setForeground(1, QBrush(QColor("#484f58")))
            for col in range(4):
                project_item.setBackground(col, QBrush(QColor("#161b22")))

            # Compact count display
            counts = f"{proj.running_count}/{proj.total_count}"
            project_item.setText(self.COL_PORTS, counts)
            project_item.setForeground(self.COL_PORTS, QBrush(QColor("#484f58")))
            self._project_items[proj.name] = project_item
            self._all_items.append(project_item)

            for svc in proj.services:
                svc_item = QTreeWidgetItem(project_item)
                self._apply_service_data(svc_item, svc, proj.name)
                self._attach_action_button(svc_item, proj.name, svc)

            project_item.setExpanded(True)

    def _attach_action_button(self, item: QTreeWidgetItem,
                              project_name: str, svc: Service) -> None:
        """Create / replace the row's play-stop button in the action column."""
        btn = QToolButton()
        btn.setProperty("class", "rowAction")
        btn.setIconSize(QSize(14, 14))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(True)
        btn.clicked.connect(
            lambda _checked=False, p=project_name, n=svc.name:
                self.action_requested.emit(p, n)
        )
        self.setItemWidget(item, self.COL_ACTION, btn)
        self._row_buttons[(project_name, svc.name)] = btn
        self._refresh_action_button(project_name, svc.name, svc.status)

    def _refresh_action_button(self, project_name: str, svc_name: str,
                              status: str) -> None:
        """Update the row button's icon + tooltip based on service status."""
        btn = self._row_buttons.get((project_name, svc_name))
        if btn is None:
            return
        is_running = status in ("running", "paused")
        is_transient = status in ("restarting", "removing")
        # Icon + color
        if is_transient:
            icon_name, color = "refresh", "#d29922"
        elif is_running:
            icon_name, color = "stop", "#f85149"
        else:
            icon_name, color = "play", "#3fb950"
        btn.setIcon(icon_pixmap(icon_name, color=color, size=14))
        if is_transient:
            btn.setEnabled(False)
        else:
            btn.setEnabled(True)
        # Tooltip
        if is_running:
            tip = "Detener servicio"
        elif is_transient:
            tip = "Operación en curso…"
        else:
            tip = "Iniciar servicio"
        btn.setToolTip(tip)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data[0] == "project":
            self.project_selected.emit(data[1])
        elif data[0] == "service":
            project_name, svc_name = data[1], data[2]
            for p in self._get_projects():
                if p.name == project_name:
                    for s in p.services:
                        if s.name == svc_name:
                            self.service_selected.emit(s)
                            return

    def _on_selection_changed(self) -> None:
        """Emit selection count when multi-selection changes."""
        count = len(self.get_selected_services())
        self.selection_changed.emit(count)

    def get_selected_services(self) -> list[Service]:
        """Return list of currently selected services (from tree selection)."""
        selected = []
        for item in self.selectedItems():
            data = item.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
            if not data or data[0] != "service":
                continue
            project_name, svc_name = data[1], data[2]
            for p in self._get_projects():
                if p.name == project_name:
                    for s in p.services:
                        if s.name == svc_name:
                            selected.append(s)
                            break
                    break
        return selected

    def get_selected_container_names(self) -> list[str]:
        """Return container names of selected services."""
        names = []
        for svc in self.get_selected_services():
            if svc.container_name:
                names.append(svc.container_name)
        return names

    def select_all_services(self) -> None:
        """Select all visible service items (Ctrl+A)."""
        self.clearSelection()
        for item in self._all_items:
            data = item.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
            if data and data[0] == "service" and not item.isHidden():
                item.setSelected(True)

    def _apply_service_data(self, item: QTreeWidgetItem, svc: Service, project_name: str) -> None:
        icon = STATUS_ICON.get(svc.status, "—")
        label = svc.status_label if hasattr(svc, 'status_label') else svc.status
        item.setText(self.COL_NAME, f"  {icon}  {svc.name}")
        item.setText(self.COL_IMAGE, svc.image or "—")
        item.setText(self.COL_STATUS, label)
        item.setText(self.COL_PORTS, svc.ports or "—")
        color = STATUS_COLOR.get(svc.status, QColor("#94a3b8"))
        item.setForeground(self.COL_STATUS, QBrush(color))
        item.setFont(self.COL_NAME, QFont("Inter", 12))
        item.setData(self.COL_NAME, Qt.ItemDataRole.UserRole,
                     ("service", project_name, svc.name))
        item.setToolTip(self.COL_NAME, (
            f"Servicio: {svc.name}\n"
            f"Imagen: {svc.image or '—'}\n"
            f"Estado: {svc.status_label}\n"
            f"Puertos: {svc.ports or '—'}\n"
            f"Contenedor: {svc.container_name or '—'}"
        ))
        self._service_items[(project_name, svc.name)] = item
        self._all_items.append(item)

    def update_service_status(self, project_name: str, svc_name: str, status: str) -> None:
        item = self._service_items.get((project_name, svc_name))
        if not item:
            return
        icon = STATUS_ICON.get(status, "—")
        label = STATUS_LABEL.get(status, "Sin contenedor")
        item.setText(self.COL_NAME, f"  {icon}  {svc_name}")
        item.setText(self.COL_STATUS, label)
        item.setForeground(self.COL_STATUS,
                           QBrush(STATUS_COLOR.get(status, QColor("#94a3b8"))))
        # Refresh the row's play/stop button to match the new status
        self._refresh_action_button(project_name, svc_name, status)

    def _get_projects(self) -> list[Project]:
        win = self.window()
        if hasattr(win, "projects"):
            return win.projects
        return []


class ServiceTable(QWidget):
    service_selected = Signal(object)
    selection_changed = Signal(int)  # emits count of selected services
    # Forwarded from the tree when a row's play/stop button is clicked.
    action_requested = Signal(str, str)  # (project_name, service_name)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.tree = ServiceTree()
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.tree, 1)

        self.tree.service_selected.connect(self.service_selected.emit)
        self.tree.project_selected.connect(self._on_project_selected)
        self.tree.selection_changed.connect(self.selection_changed.emit)
        self.tree.action_requested.connect(self.action_requested.emit)

    def load_projects(self, projects: list[Project]) -> None:
        self.tree.load_projects(projects)

    def update_service_status(self, project_name: str, svc_name: str, status: str) -> None:
        self.tree.update_service_status(project_name, svc_name, status)

    def get_selected_services(self) -> list[Service]:
        return self.tree.get_selected_services()

    def get_selected_container_names(self) -> list[str]:
        return self.tree.get_selected_container_names()

    def select_all_services(self) -> None:
        self.tree.select_all_services()

    def _on_project_selected(self, project_name: str) -> None:
        win = self.window()
        if hasattr(win, "projects"):
            for p in win.projects:
                if p.name == project_name:
                    if hasattr(win, "panel"):
                        win.panel.project = p
                    if hasattr(win, "_selected_project"):
                        win._selected_project = p
                    if hasattr(win, "_selected_service"):
                        win._selected_service = None
                        win.panel.service = None
                    break


class _RowHighlightOverlay(QWidget):
    """Transparent overlay painted on top of a ServiceTree's viewport.

    Lives as a child of the viewport so the WM can't intervene in its
    positioning. The tree tells it which row to highlight via set_row().
    """

    def __init__(self, parent_viewport):
        super().__init__(parent_viewport)
        self._tree = parent_viewport.parent()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.hide()
        self._row: int | None = None
        self._is_selected: bool = False

    def set_row(self, row: int | None, is_selected: bool) -> None:
        if row is None:
            self._row = None
            self.hide()
            return
        # Reposition only if changed
        if self._row != row or self._is_selected != is_selected:
            self._row = row
            self._is_selected = is_selected
            self._tree._ensure_overlay_position()
        else:
            self._tree._ensure_overlay_position()

    def paintEvent(self, event):
        if self._row is None:
            return
        # The overlay's geometry = the row's rect in viewport space, so its
        # local 0,0 is the top-left of the row. Use local coordinates here.
        row_rect = QRectF(2, 1, self.width() - 4, self.height() - 2)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        if self._is_selected:
            painter.setBrush(self._tree.SELECTED_OVERLAY)
            painter.drawRoundedRect(row_rect, 6, 6)
            bar = QRectF(row_rect.x() + 1, row_rect.y() + 4,
                         3, row_rect.height() - 8)
            painter.setBrush(self._tree.ACCENT_SELECTED)
            painter.drawRoundedRect(bar, 2, 2)
        else:
            painter.setBrush(self._tree.HOVER_OVERLAY)
            painter.drawRoundedRect(row_rect, 6, 6)
            bar = QRectF(row_rect.x() + 1, row_rect.y() + 4,
                         2, row_rect.height() - 8)
            painter.setBrush(self._tree.ACCENT_HOVER)
            painter.drawRoundedRect(bar, 1, 1)
        painter.end()
