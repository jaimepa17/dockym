"""Command palette (Ctrl+K) for Dockym.

A modal dialog that provides global search across services and projects,
with real-time filtering, keyboard navigation, and results shown with
status icons and context.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel, QModelIndex, QAbstractListModel
from PySide6.QtCore import QPersistentModelIndex
from PySide6.QtGui import QColor, QBrush, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListView,
    QWidget, QHBoxLayout, QLabel, QFrame, QApplication,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)

from dockym.models.project import Project, Service
from dockym.ui.icons import icon_pixmap

# Status colors matching service_table.py
_STATUS_COLOR = {
    "running": "#3fb950",
    "exited": "#8b949e",
    "paused": "#d29922",
    "restarting": "#d29922",
    "created": "#8b949e",
    "removing": "#8b949e",
    "dead": "#f85149",
}

_STATUS_ICON = {
    "running": "●",
    "exited": "○",
    "paused": "◐",
    "restarting": "↻",
    "created": "◌",
    "removing": "×",
    "dead": "✕",
}

_STATUS_LABEL = {
    "running": "En ejecución",
    "exited": "Detenido",
    "paused": "Pausado",
    "restarting": "Reiniciando",
    "created": "Creado",
    "removing": "Eliminando",
    "dead": "Muerto",
}


class SearchResult:
    """A single search result item."""

    def __init__(
        self,
        name: str,
        kind: str,  # "service" or "project"
        project_name: str = "",
        status: str = "",
        detail: str = "",
        service: Service | None = None,
        project: Project | None = None,
    ):
        self.name = name
        self.kind = kind
        self.project_name = project_name
        self.status = status
        self.detail = detail
        self.service = service
        self.project = project


class SearchResultModel(QAbstractListModel):
    """Model backing the search results list."""

    ROLE_DISPLAY = Qt.ItemDataRole.DisplayRole
    ROLE_SEARCH_TEXT = Qt.ItemDataRole.UserRole + 1
    ROLE_RESULT = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._results: list[SearchResult] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return len(self._results)

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        row = index.row()
        if not index.isValid() or row >= len(self._results):
            return None
        result = self._results[row]

        if role == self.ROLE_DISPLAY:
            return result.name
        elif role == self.ROLE_SEARCH_TEXT:
            parts = [result.name.lower(), result.kind.lower(), result.project_name.lower()]
            if result.detail:
                parts.append(result.detail.lower())
            return " ".join(parts)
        elif role == self.ROLE_RESULT:
            return result
        return None

    def set_results(self, results: list[SearchResult]) -> None:
        self.beginResetModel()
        self._results = results
        self.endResetModel()

    def result_at(self, row: int) -> SearchResult | None:
        if 0 <= row < len(self._results):
            return self._results[row]
        return None


class SearchItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering search results with icons and context."""

    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex):
        result = index.data(SearchResultModel.ROLE_RESULT)
        if not result:
            super().paint(painter, option, index)
            return

        painter.save()

        # Draw selection/hover background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#1f6feb33"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#1c2128"))

        x = option.rect.x() + 12
        y = option.rect.y()
        h = option.rect.height()

        # Status icon
        if result.kind == "service" and result.status:
            icon = _STATUS_ICON.get(result.status, "—")
            color = _STATUS_COLOR.get(result.status, "#8b949e")
            painter.setPen(QColor(color))
            painter.setFont(QFont("Inter", 13, QFont.Weight.Bold))
            painter.drawText(x, y, 24, h, Qt.AlignmentFlag.AlignCenter, icon)
            x += 28
        else:
            # Project icon (folder-like)
            folder_pix = icon_pixmap("folder", color="#58a6ff", size=16)
            icon_size = folder_pix.width()
            painter.drawPixmap(
                x + (24 - icon_size) // 2,
                y + (h - icon_size) // 2,
                folder_pix,
            )
            x += 28

        # Name
        painter.setPen(QColor("#e6edf3"))
        painter.setFont(QFont("Inter", 12))
        painter.drawText(x, y, 180, h, Qt.AlignmentFlag.AlignVCenter, result.name)
        x += 185

        # Status label (for services)
        if result.kind == "service" and result.status:
            label = _STATUS_LABEL.get(result.status, "")
            color = _STATUS_COLOR.get(result.status, "#8b949e")
            painter.setPen(QColor(color))
            painter.setFont(QFont("Inter", 11))
            painter.drawText(x, y, 100, h, Qt.AlignmentFlag.AlignVCenter, label)

        # Project name / detail
        if result.kind == "service" and result.project_name:
            painter.setPen(QColor("#484f58"))
            painter.setFont(QFont("Inter", 11))
            painter.drawText(
                option.rect.width() - 12, y, 120, h,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                result.project_name,
            )

        painter.restore()

    def sizeHint(self, option, index):
        return option.rect.adjusted(0, 6, 0, 6).size()


class CommandPalette(QDialog):
    """A Ctrl+K command palette dialog for global search."""

    result_selected = Signal(object)  # emits SearchResult

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Popup
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(560)
        self.setMinimumHeight(300)
        self.setMaximumHeight(480)

        self._projects: list[Project] = []
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        # Container frame with background
        self._container = QFrame(self)
        self._container.setObjectName("paletteContainer")
        self._container.setStyleSheet("""
            QFrame#paletteContainer {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._container)

        inner = QVBoxLayout(self._container)
        inner.setContentsMargins(12, 12, 12, 12)
        inner.setSpacing(8)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar servicios, proyectos…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                selection-background-color: #1f6feb;
            }
            QLineEdit:focus {
                border: 1px solid #58a6ff;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.returnPressed.connect(self._on_select)
        inner.addWidget(self.search_input)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #21262d; border: none; max-height: 1px;")
        inner.addWidget(divider)

        # Results list
        self._model = SearchResultModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterRole(SearchResultModel.ROLE_SEARCH_TEXT)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self._list = QListView()
        self._list.setModel(self._proxy)
        self._delegate = SearchItemDelegate(self._list)
        self._list.setItemDelegate(self._delegate)
        self._list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self._list.setSelectionBehavior(QListView.SelectionBehavior.SelectRows)
        self._list.setUniformItemSizes(True)
        self._list.setSpacing(2)
        self._list.setStyleSheet("""
            QListView {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 4px 0;
            }
            QListView::item {
                padding: 4px 8px;
                border-radius: 6px;
                margin: 1px 0;
                min-height: 36px;
            }
            QListView::item:selected {
                background-color: #1f6feb33;
                color: #e6edf3;
            }
            QListView::item:hover {
                background-color: #1c2128;
            }
        """)
        self._list.clicked.connect(self._on_list_clicked)
        inner.addWidget(self._list, 1)

        # Hint bar
        hint_bar = QHBoxLayout()
        hint_bar.setContentsMargins(4, 0, 4, 0)
        hints = QLabel("↑↓ navegar  ·  Enter seleccionar  ·  Esc cerrar")
        hints.setStyleSheet("color: #484f58; font-size: 11px; background-color: transparent;")
        hint_bar.addWidget(hints)
        hint_bar.addStretch()
        self._count_label = QLabel("0 resultados")
        self._count_label.setStyleSheet("color: #484f58; font-size: 11px; background-color: transparent;")
        hint_bar.addWidget(self._count_label)
        inner.addLayout(hint_bar)

    def _setup_shortcuts(self) -> None:
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.close)

    def set_projects(self, projects: list[Project]) -> None:
        """Update the search index with current projects."""
        self._projects = projects

    def show_palette(self) -> None:
        """Show and focus the command palette."""
        self._refresh_results("")
        self.search_input.clear()
        self.show()
        self.search_input.setFocus()

        # Center on parent
        if self.parent():
            parent_rect = self.parent().geometry()  # type: ignore[attr-defined]
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 3
            self.move(x, y)

    def _on_search_changed(self, text: str) -> None:
        self._refresh_results(text)

    def _refresh_results(self, filter_text: str) -> None:
        """Build and filter search results."""
        results: list[SearchResult] = []

        for project in self._projects:
            # Add project as searchable item
            results.append(SearchResult(
                name=project.name,
                kind="project",
                project_name="",
                status="",
                detail=project.path,
                service=None,
                project=project,
            ))

            for service in project.services:
                results.append(SearchResult(
                    name=service.name,
                    kind="service",
                    project_name=project.name,
                    status=service.status,
                    detail=service.image or "",
                    service=service,
                    project=project,
                ))

        self._model.set_results(results)

        if filter_text:
            self._proxy.setFilterFixedString(filter_text)
        else:
            self._proxy.setFilterFixedString("")

        count = self._proxy.rowCount()
        self._count_label.setText(f"{count} resultado{'s' if count != 1 else ''}")

        # Auto-select first result
        if count > 0:
            self._list.setCurrentIndex(self._proxy.index(0, 0))
        else:
            self._list.setCurrentIndex(QModelIndex())

    def _on_list_clicked(self, index: QModelIndex) -> None:
        source_index = self._proxy.mapToSource(index)
        result = self._model.result_at(source_index.row())
        if result:
            self.result_selected.emit(result)
            self.close()

    def _on_select(self) -> None:
        """Handle Enter key — select the current item."""
        index = self._list.currentIndex()
        if index.isValid():
            source_index = self._proxy.mapToSource(index)
            result = self._model.result_at(source_index.row())
            if result:
                self.result_selected.emit(result)
                self.close()

    def keyPressEvent(self, event) -> None:
        """Handle keyboard navigation."""
        key = event.key()

        if key == Qt.Key.Key_Down:
            current = self._list.currentIndex()
            if current.row() < self._proxy.rowCount() - 1:
                self._list.setCurrentIndex(self._proxy.index(current.row() + 1, 0))
            event.accept()
        elif key == Qt.Key.Key_Up:
            current = self._list.currentIndex()
            if current.row() > 0:
                self._list.setCurrentIndex(self._proxy.index(current.row() - 1, 0))
            event.accept()
        else:
            super().keyPressEvent(event)
