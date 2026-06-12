"""Custom frameless title bar for Dockym.

Uses QWindow.startSystemMove() for proper cross-platform dragging
(instead of manual mouse tracking which fails on Linux).
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QPoint, QEvent, QRect, QRectF
from PySide6.QtGui import QMouseEvent, QCursor, QPainter, QColor, QPen, QBrush, QFont


# ---------- Window control button ----------

class _WindowButton(QPushButton):
    """Minimal flat button for minimize / maximize / close."""

    def __init__(self, text: str, *, tooltip: str = "", object_name: str = ""):
        super().__init__(text)
        self.setFixedSize(36, 32)
        self.setToolTip(tooltip)
        if object_name:
            self.setObjectName(object_name)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


# ---------- Bell button with painted icon + unread badge ----------

class _BellButton(QPushButton):
    """Notification bell button. Draws a bell via QPainter and a count
    badge in the top-right corner when there are unread items."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(36, 32)
        self.setObjectName("titleBarBell")
        self.setToolTip("Notificaciones")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._unread = 0

    def set_unread(self, count: int) -> None:
        if count != self._unread:
            self._unread = max(0, count)
            self.update()

    def paintEvent(self, event) -> None:
        # Let QPushButton paint the background/hover state via QSS first
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Bell color follows current foreground (use QSS palette)
        fg = self.palette().windowText().color()
        # Hover/pressed uses brighter — already handled by stylesheet on bg

        # Draw bell centered
        cx = self.width() / 2
        cy = self.height() / 2 - 1
        # Bell dome (rounded top, flat bottom)
        pen = QPen(fg, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Bell body path: dome with curled bottom
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        # Top knob
        path.addEllipse(QRectF(cx - 1.2, cy - 7.5, 2.4, 2.4))
        # Dome
        path.moveTo(cx - 5.5, cy + 2.5)
        path.cubicTo(cx - 5.5, cy - 4.5, cx + 5.5, cy - 4.5, cx + 5.5, cy + 2.5)
        # Rim
        path.lineTo(cx + 6.5, cy + 4.0)
        path.lineTo(cx - 6.5, cy + 4.0)
        path.lineTo(cx - 5.5, cy + 2.5)
        painter.drawPath(path)
        # Clapper
        painter.setBrush(QBrush(fg))
        painter.drawEllipse(QRectF(cx - 1.1, cy + 4.8, 2.2, 2.2))

        # Unread badge
        if self._unread > 0:
            label = "9+" if self._unread > 9 else str(self._unread)
            badge_color = QColor("#f85149")
            text_color = QColor("#ffffff")
            radius = 7
            # Anchor in top-right
            bx = self.width() - radius * 2 - 4
            by = 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(badge_color))
            painter.drawEllipse(QRectF(bx, by, radius * 2, radius * 2))
            painter.setPen(QPen(text_color))
            f = QFont(self.font())
            f.setPointSizeF(7.5)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(QRectF(bx, by, radius * 2, radius * 2),
                             Qt.AlignmentFlag.AlignCenter, label)

        painter.end()


# ---------- Title bar widget ----------

class TitleBar(QWidget):
    """Custom frameless title bar using QWindow.startSystemMove() for dragging.

    Layout:  [icon] [title]  ----stretch----  [bell] [events] [count] [min] [max] [close]
    """

    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
    bell_clicked = Signal()

    HEIGHT = 40

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(self.HEIGHT)
        self._drag_pos: QPoint | None = None
        self._is_dragging: bool = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(4)

        # ---- Left side: icon + title ----
        self._icon_label = QLabel()
        self._icon_label.setObjectName("titleBarIcon")
        self._icon_label.setFixedSize(22, 22)
        layout.addWidget(self._icon_label)
        layout.addSpacing(6)

        self._title_label = QLabel("Dockym")
        self._title_label.setObjectName("titleBarTitle")
        layout.addWidget(self._title_label)

        layout.addStretch()

        # ---- Right side: bell, events, count, controls ----
        self._bell_btn = _BellButton(self)
        self._bell_btn.clicked.connect(self.bell_clicked)
        layout.addWidget(self._bell_btn)

        self._events_indicator = QLabel("●")
        self._events_indicator.setObjectName("titleBarEvents")
        self._events_indicator.setToolTip("Docker events: connecting…")
        layout.addWidget(self._events_indicator)

        self._count_label = QLabel("0/0")
        self._count_label.setObjectName("titleBarCount")
        layout.addWidget(self._count_label)

        layout.addSpacing(4)

        self._min_btn = _WindowButton("─", tooltip="Minimizar",
                                       object_name="titleBarMin")
        self._min_btn.clicked.connect(self.minimize_clicked)
        layout.addWidget(self._min_btn)

        self._max_btn = _WindowButton("☐", tooltip="Maximizar",
                                       object_name="titleBarMax")
        self._max_btn.clicked.connect(self.maximize_clicked)
        layout.addWidget(self._max_btn)

        self._close_btn = _WindowButton("✕", tooltip="Cerrar",
                                         object_name="titleBarClose")
        self._close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(self._close_btn)

    # ---------- Public helpers ----------

    def set_icon(self, icon):
        from PySide6.QtGui import QIcon
        if isinstance(icon, QIcon):
            self._icon_label.setPixmap(icon.pixmap(22, 22))
        else:
            self._icon_label.setPixmap(icon.scaled(22, 22,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def set_events_connected(self, connected: bool) -> None:
        if connected:
            self._events_indicator.setStyleSheet(
                "color: #3fb950; font-weight: 600; font-size: 12px;")
            self._events_indicator.setToolTip("Docker events: connected")
        else:
            self._events_indicator.setStyleSheet(
                "color: #f85149; font-weight: 600; font-size: 12px;")
            self._events_indicator.setToolTip("Docker events: disconnected")

    def set_events_connecting(self) -> None:
        self._events_indicator.setStyleSheet(
            "color: #58a6ff; font-weight: 600; font-size: 12px;")
        self._events_indicator.setToolTip("Docker events: connecting…")

    def set_events_error(self, error: str) -> None:
        self._events_indicator.setStyleSheet(
            "color: #f85149; font-weight: 600; font-size: 12px;")
        self._events_indicator.setToolTip(f"Events: {error}")

    def set_count(self, text: str) -> None:
        self._count_label.setText(text)

    def set_unread_notifications(self, count: int) -> None:
        """Update the bell badge with the number of unread notifications."""
        self._bell_btn.set_unread(count)

    def bell_button(self) -> QPushButton:
        """Return the bell button — used as anchor for the notification popup."""
        return self._bell_btn

    def update_maximize_button(self, maximized: bool) -> None:
        if maximized:
            self._max_btn.setText("❐")
            self._max_btn.setToolTip("Restaurar")
        else:
            self._max_btn.setText("☐")
            self._max_btn.setToolTip("Maximizar")

    # ---------- Event handling for dragging ----------

    def event(self, event: QEvent) -> bool:
        """Override event() for dragging using QWindow.startSystemMove()."""
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QMouseEvent):
            return super().event(event)

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                # Use Qt's native system move — works on all platforms
                win = self.window()
                handle = win.windowHandle()
                if handle:
                    # Start system move — Qt handles everything
                    handle.startSystemMove()
                    # After system move completes, handle maximize on release
                    self._drag_pos = None
                    return True

        elif event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                self.maximize_clicked.emit()
                return True

        return super().event(event)
