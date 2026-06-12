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
    QStyledItemDelegate,
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
    HOVER_TEXT = QColor("#e6edf3")
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

        # Track hovered and selected rows independently. The row background
        # is painted by _RowHighlightDelegate (per cell) BEFORE the cell
        # contents, so the highlight spans the full row but the text and
        # icons stay visible on top.
        self._hovered_row: int | None = None
        self._selected_row: int | None = None
        self._row_delegate = _RowHighlightDelegate(self)
        self.setItemDelegate(self._row_delegate)
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
        """Track the hovered row; updates the delegate state and repaints."""
        if obj is not self.viewport():
            return super().eventFilter(obj, event)
        if event.type() == QEvent.Type.MouseMove:
            row = self._flat_row_at(event.pos())
            if row != self._hovered_row:
                self._hovered_row = row
                self._schedule_repaint()
        elif event.type() == QEvent.Type.Leave:
            if self._hovered_row is not None:
                self._hovered_row = None
                self._schedule_repaint()
        elif event.type() == QEvent.Type.MouseButtonPress:
            if self._hovered_row is not None:
                self._hovered_row = None
                self._schedule_repaint()
        return super().eventFilter(obj, event)

    def _flat_row_at(self, viewport_pos) -> int | None:
        """Return the flat service-row index under *viewport_pos*, or None."""
        item = self.itemAt(viewport_pos)
        if item is None:
            return None
        payload = item.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
        if not payload or payload[0] != "service":
            return None
        return self._flat_row_of(item)

    def _flat_row_of(self, target_item) -> int | None:
        """Flat 0-based index of *target_item* among all service items."""
        flat = 0
        for it in QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.IteratorFlag.All):
            item = it.value()
            payload = item.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
            if payload and payload[0] == "service":
                if item is target_item:
                    return flat
                flat += 1
        return None

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        self._selected_row = None
        for item in self.selectedItems():
            payload = item.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
            if payload and payload[0] == "service":
                self._selected_row = self._flat_row_of(item)
                break
        # The delegate reads _hovered_row / _selected_row at paint time, so
        # any redraw will pick up the new state. Force a repaint of the
        # relevant rows so the change is visible without a mouse move.
        self._schedule_repaint()

    def _schedule_repaint(self) -> None:
        """Trigger a repaint of the viewport so the delegate repaints."""
        self.viewport().update()

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
        """Return the full-row rect for the *row*-th service (0-based flat index)."""
        # Iterate to find the Nth service item, matching _flat_row_of().
        target = None
        flat = 0
        for it in QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.IteratorFlag.All):
            item = it.value()
            payload = item.data(self.COL_NAME, Qt.ItemDataRole.UserRole)
            if payload and payload[0] == "service":
                if flat == row:
                    target = item
                    break
                flat += 1
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


class _RowHighlightDelegate(QStyledItemDelegate):
    """Paints a single rounded-rect highlight that spans the entire row.

    Qt's per-cell painting would otherwise show a separate pill behind each
    cell. This delegate inspects the current cell's row, computes the row's
    full visual rect across all visible columns, and paints the highlight
    BEFORE delegating to the default cell painter — so the cell's own text
    and icon stay on top.
    """

    def __init__(self, tree: "ServiceTree"):
        super().__init__(tree)
        self._tree = tree

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        # Resolve the item first; QModelIndex.data() takes only a role
        # (the column is fixed in the index itself).
        item = self._tree.itemFromIndex(index)
        if item is None:
            super().paint(painter, option, index)
            return
        payload = item.data(self._tree.COL_NAME, Qt.ItemDataRole.UserRole)
        if not payload or payload[0] != "service":
            super().paint(painter, option, index)
            return
        flat = self._tree._flat_row_of(item)
        if flat is None:
            super().paint(painter, option, index)
            return

        is_selected = flat == self._tree._selected_row
        is_hovered = flat == self._tree._hovered_row
        # When something is selected, that wins; otherwise show the hover.
        if is_selected or is_hovered:
            self._paint_row_bg(painter, option, item, is_selected)

        super().paint(painter, option, index)

    def _paint_row_bg(
        self, painter: QPainter, option: QStyleOptionViewItem, item, is_selected: bool
    ) -> None:
        visual_rect = self._tree.visualItemRect(item)
        if visual_rect.isEmpty():
            return
        # Extend to the rightmost visible column edge
        right = 0
        for c in range(self._tree.header().count()):
            vp = self._tree.columnViewportPosition(c)
            if vp >= 0:
                right = max(right, vp + self._tree.columnWidth(c))
        if right == 0:
            right = self._tree.viewport().width()
        full_row = QRect(visual_rect.x(), visual_rect.y(),
                         max(0, right - visual_rect.x()),
                         visual_rect.height())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        if is_selected:
            painter.setBrush(self._tree.SELECTED_OVERLAY)
            painter.drawRoundedRect(QRectF(full_row).adjusted(2, 1, -2, -1), 6, 6)
            bar = QRectF(full_row.x() + 1, full_row.y() + 4,
                         3, full_row.height() - 8)
            painter.setBrush(self._tree.ACCENT_SELECTED)
            painter.drawRoundedRect(bar, 2, 2)
        else:
            painter.setBrush(self._tree.HOVER_OVERLAY)
            painter.drawRoundedRect(QRectF(full_row).adjusted(2, 1, -2, -1), 6, 6)
            bar = QRectF(full_row.x() + 1, full_row.y() + 4,
                         2, full_row.height() - 8)
            painter.setBrush(self._tree.ACCENT_HOVER)
            painter.drawRoundedRect(bar, 1, 1)
        painter.restore()
