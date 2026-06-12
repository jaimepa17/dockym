"""Toast notification system for Dockym.

Provides non-intrusive toast-style notifications that stack in the
bottom-right corner of the main window. Supports different notification
types (success, error, warning, info), auto-dismiss with configurable
timeout, click-to-dismiss, and slide animations.

Also keeps a persistent history of every notification (read/unread state)
so a notification center popup in the title bar can show recent activity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QParallelAnimationGroup, Signal, QObject, Slot,
    QMetaObject, Q_ARG, QThread,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel,
    QGraphicsOpacityEffect,
)


class NotificationType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class NotificationRecord:
    """A historical entry stored in the notification center."""
    message: str
    ntype: NotificationType
    timestamp: datetime = field(default_factory=datetime.now)
    read: bool = False


# Icon characters (Unicode, no external dependencies needed)
_NOTIFICATION_ICONS = {
    NotificationType.SUCCESS: "✓",
    NotificationType.ERROR: "✗",
    NotificationType.WARNING: "⚠",
    NotificationType.INFO: "●",
}

_NOTIFICATION_COLORS = {
    NotificationType.SUCCESS: "#3fb950",
    NotificationType.ERROR: "#f85149",
    NotificationType.WARNING: "#d29922",
    NotificationType.INFO: "#58a6ff",
}


class ToastNotification(QWidget):
    """A single toast notification widget."""

    clicked = Signal()
    dismissed = Signal()

    def __init__(
        self,
        message: str,
        ntype: NotificationType = NotificationType.INFO,
        timeout_ms: int = 4000,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._ntype = ntype
        self._timeout_ms = timeout_ms
        self._opacity_effect: QGraphicsOpacityEffect | None = None
        self._slide_anim: QPropertyAnimation | None = None
        self._fade_anim: QPropertyAnimation | None = None
        self._dismissed = False

        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # Render as a child overlay inside the parent window (no Tool/top-level
        # window so the WM cannot reposition it). The parent's layout doesn't
        # manage us — we move() ourselves manually.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFixedWidth(340)
        self.setMinimumHeight(48)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._setup_ui(message)
        self._setup_effect()

    def _setup_ui(self, message: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # Icon
        icon_char = _NOTIFICATION_ICONS.get(self._ntype, "●")
        color = _NOTIFICATION_COLORS.get(self._ntype, "#58a6ff")
        icon_label = QLabel(icon_char)
        icon_label.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: 700;"
            f"background-color: transparent; min-width: 18px;"
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(
            "color: #e6edf3; font-size: 12px; font-weight: 500;"
            "background-color: transparent;"
        )
        layout.addWidget(msg_label, 1)

        # Close button (×)
        close_label = QLabel("×")
        close_label.setStyleSheet(
            "color: #484f58; font-size: 14px; font-weight: 600;"
            "background-color: transparent; padding: 0 2px;"
        )
        close_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(close_label, 0, Qt.AlignmentFlag.AlignTop)

    def _setup_effect(self) -> None:
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.95)
        self.setGraphicsEffect(self._opacity_effect)

    def paintEvent(self, event) -> None:
        """Custom paint to draw background with rounded corners and subtle border."""
        from PySide6.QtGui import QPainter, QColor, QPen, QBrush
        from PySide6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = _NOTIFICATION_COLORS.get(self._ntype, "#58a6ff")
        bg = QColor("#161b22")
        border_color = QColor(color)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # Draw subtle left accent border
        accent_rect = QRectF(rect.x(), rect.y(), 3, rect.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(border_color))
        painter.drawRoundedRect(accent_rect, 2, 2)

        # Draw main background
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect.adjusted(3, 0, 0, 0), 6, 6)

        painter.end()

    def enterEvent(self, event) -> None:
        """Pause auto-dismiss on hover."""
        self._pause_autodismiss()

    def leaveEvent(self, event) -> None:
        """Resume auto-dismiss when mouse leaves."""
        self._resume_autodismiss()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        self.dismiss()

    def _pause_autodismiss(self) -> None:
        if hasattr(self, "_auto_dismiss_timer") and self._auto_dismiss_timer.isActive():
            self._auto_dismiss_timer.stop()

    def _resume_autodismiss(self) -> None:
        if hasattr(self, "_auto_dismiss_timer"):
            remaining = max(self._timeout_ms, 1000)
            self._auto_dismiss_timer.start(remaining)

    def start_autodismiss(self) -> None:
        """Start the auto-dismiss timer."""
        self._auto_dismiss_timer = QTimer(self)
        self._auto_dismiss_timer.setSingleShot(True)
        self._auto_dismiss_timer.timeout.connect(self.dismiss)
        self._auto_dismiss_timer.start(self._timeout_ms)

    def animate_in(self) -> None:
        """Slide in from the right with fade."""
        start_pos = QPoint(self.x() + 80, self.y())
        end_pos = self.pos()

        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(280)
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(280)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(0.95)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(self._slide_anim)
        group.addAnimation(self._fade_anim)
        group.start()

    def animate_out(self) -> None:
        """Fade out and slide right off-screen, then close."""
        end_pos = QPoint(self.x() + 120, self.y())

        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(260)
        self._slide_anim.setStartValue(self.pos())
        self._slide_anim.setEndValue(end_pos)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(260)
        self._fade_anim.setStartValue(0.95)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(self._slide_anim)
        group.addAnimation(self._fade_anim)
        group.finished.connect(self._on_animation_finished)
        group.start()

    def _on_animation_finished(self) -> None:
        self.dismissed.emit()
        self.hide()
        self.deleteLater()

    def dismiss(self) -> None:
        """Dismiss this notification."""
        if self._dismissed:
            return
        self._dismissed = True
        self.animate_out()


class NotificationManager(QObject):
    """Manages a stack of toast notifications and a persistent history.

    Signals:
        history_changed: emitted when a notification is added, marked read,
            or the history is cleared. Subscribers (like the notification
            center bell) can refresh their UI.
    """

    history_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._parent = parent
        self._notifications: list[ToastNotification] = []
        self._max_visible = 5
        self._spacing = 8
        self._toast_width = 340
        # Persistent history (newest last)
        self._history: list[NotificationRecord] = []
        self._max_history = 100

        # Re-anchor toasts whenever the parent window is resized
        if self._parent is not None:
            self._parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._parent and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Move,
        ):
            self._relayout()
        return super().eventFilter(obj, event)

    # ── Toast management ──────────────────────────────────────────

    def notify(
        self,
        message: str,
        ntype: NotificationType = NotificationType.INFO,
        timeout_ms: int = 4000,
    ) -> ToastNotification | None:
        """Show a notification toast and append it to history.

        Safe to call from any thread — if invoked from a non-GUI thread the
        call is re-dispatched onto the manager's thread (the GUI thread)
        so QWidget construction never happens off-thread.
        """
        # If called from a non-GUI thread, queue to GUI thread instead
        if QThread.currentThread() is not self.thread():
            QMetaObject.invokeMethod(
                self,
                "_notify_on_gui_thread",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, message),
                Q_ARG(str, ntype.value),
                Q_ARG(int, timeout_ms),
            )
            return None

        return self._notify_impl(message, ntype, timeout_ms)

    @Slot(str, str, int)
    def _notify_on_gui_thread(self, message: str, ntype_value: str, timeout_ms: int) -> None:
        """GUI-thread entry point used by cross-thread notify() invocations."""
        try:
            ntype = NotificationType(ntype_value)
        except ValueError:
            ntype = NotificationType.INFO
        self._notify_impl(message, ntype, timeout_ms)

    def _notify_impl(
        self,
        message: str,
        ntype: NotificationType,
        timeout_ms: int,
    ) -> ToastNotification:
        """Actual GUI work — only ever runs on the GUI thread."""
        # Append to history (newest at the end)
        record = NotificationRecord(message=message, ntype=ntype)
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        self.history_changed.emit()

        # Remove oldest visible toast if at max
        while len(self._notifications) >= self._max_visible:
            oldest = self._notifications.pop(0)
            oldest.dismiss()

        toast = ToastNotification(message, ntype, timeout_ms, parent=self._parent)
        toast.dismissed.connect(lambda t=toast: self._on_dismissed(t))
        self._notifications.append(toast)
        self._relayout()
        toast.show()
        toast.raise_()
        toast.animate_in()
        toast.start_autodismiss()
        return toast

    def success(self, message: str, timeout_ms: int = 4000) -> ToastNotification:
        return self.notify(message, NotificationType.SUCCESS, timeout_ms)

    def error(self, message: str, timeout_ms: int = 5000) -> ToastNotification:
        return self.notify(message, NotificationType.ERROR, timeout_ms)

    def warning(self, message: str, timeout_ms: int = 4500) -> ToastNotification:
        return self.notify(message, NotificationType.WARNING, timeout_ms)

    def info(self, message: str, timeout_ms: int = 4000) -> ToastNotification:
        return self.notify(message, NotificationType.INFO, timeout_ms)

    def _on_dismissed(self, toast: ToastNotification) -> None:
        if toast in self._notifications:
            self._notifications.remove(toast)
        self._relayout()

    def _relayout(self) -> None:
        """Stack toasts in the bottom-right corner of the parent window.

        Toasts are child widgets of the parent, positioned in *local*
        coordinates so the window manager never reinterprets them.
        """
        margin_right = 16
        margin_bottom = 16

        if self._parent is None:
            return

        parent_w = self._parent.width()
        parent_h = self._parent.height()

        # Stack upward (newest at the bottom, older above)
        y = parent_h - margin_bottom
        x = parent_w - self._toast_width - margin_right
        for toast in reversed(self._notifications):
            toast_height = toast.sizeHint().height() or 52
            y -= toast_height
            target = QPoint(x, y)
            toast.move(target)
            toast.show()
            toast.raise_()
            # If an entrance animation is running, retarget it so the toast
            # ends at the new (post-relayout) position instead of snapping back.
            anim = getattr(toast, "_slide_anim", None)
            if anim is not None and anim.state() == QPropertyAnimation.State.Running:
                # Preserve the horizontal entry offset, just retarget Y
                start = anim.startValue()
                anim.setStartValue(QPoint(start.x() - anim.endValue().x() + target.x(), target.y()))
                anim.setEndValue(target)
            y -= self._spacing

    # ── History API ───────────────────────────────────────────────

    def history(self) -> list[NotificationRecord]:
        """Return the history list (newest last)."""
        return list(self._history)

    def unread_count(self) -> int:
        return sum(1 for r in self._history if not r.read)

    def mark_all_read(self) -> None:
        changed = False
        for r in self._history:
            if not r.read:
                r.read = True
                changed = True
        if changed:
            self.history_changed.emit()

    def clear_history(self) -> None:
        if self._history:
            self._history.clear()
            self.history_changed.emit()


# ─────────────────────────────────────────────────────────────────
# NotificationCenter — popup that shows the history (bell dropdown)
# ─────────────────────────────────────────────────────────────────

def _humanize_time(ts: datetime) -> str:
    """Format a timestamp as 'hace 5s', 'hace 3m', etc."""
    delta = datetime.now() - ts
    s = int(delta.total_seconds())
    if s < 5:
        return "ahora"
    if s < 60:
        return f"hace {s}s"
    m = s // 60
    if m < 60:
        return f"hace {m}m"
    h = m // 60
    if h < 24:
        return f"hace {h}h"
    d = h // 24
    return f"hace {d}d"


class NotificationCenter(QWidget):
    """Frameless popup displaying the notification history list.

    Shown beneath the bell button in the title bar. Closes on focus-out.
    """

    cleared = Signal()

    def __init__(self, manager: NotificationManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._manager = manager

        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(360)
        self.setMinimumHeight(120)
        self.setMaximumHeight(480)

        self._setup_ui()
        self._manager.history_changed.connect(self.refresh)

    def _setup_ui(self) -> None:
        from PySide6.QtWidgets import (QVBoxLayout, QScrollArea, QFrame,
                                        QPushButton)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)

        self._container = QFrame(self)
        self._container.setObjectName("notifCenter")
        outer.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("notifCenterHeader")
        header.setFixedHeight(40)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 8, 0)
        hl.setSpacing(8)

        title = QLabel("Notificaciones")
        title.setObjectName("notifCenterTitle")
        hl.addWidget(title)
        hl.addStretch()

        self._clear_btn = QPushButton("Borrar todo")
        self._clear_btn.setObjectName("notifCenterClear")
        self._clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._clear_btn.clicked.connect(self._on_clear)
        hl.addWidget(self._clear_btn)

        layout.addWidget(header)

        # Scrollable list area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("notifCenterScroll")
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._list_widget = QWidget()
        self._list_widget.setObjectName("notifCenterList")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        layout.addWidget(self._scroll, 1)

        self._empty_label = QLabel("Sin notificaciones")
        self._empty_label.setObjectName("notifCenterEmpty")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label)

    def refresh(self) -> None:
        """Rebuild the list from the manager's history."""
        # Clear existing item widgets (preserve trailing stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.deleteLater()

        history = self._manager.history()
        if not history:
            self._empty_label.setVisible(True)
            self._scroll.setVisible(False)
            self._clear_btn.setEnabled(False)
            return

        self._empty_label.setVisible(False)
        self._scroll.setVisible(True)
        self._clear_btn.setEnabled(True)

        # Newest first
        for record in reversed(history):
            item = self._build_item(record)
            self._list_layout.insertWidget(self._list_layout.count() - 1, item)

    def _build_item(self, record: NotificationRecord):
        from PySide6.QtWidgets import QFrame, QVBoxLayout

        item = QFrame()
        item.setObjectName("notifItem")
        if not record.read:
            item.setProperty("unread", True)

        row = QHBoxLayout(item)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        icon_char = _NOTIFICATION_ICONS.get(record.ntype, "●")
        color = _NOTIFICATION_COLORS.get(record.ntype, "#58a6ff")

        icon = QLabel(icon_char)
        icon.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: 700;"
            "background-color: transparent; min-width: 16px;"
        )
        icon.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        row.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(2)

        msg = QLabel(record.message)
        msg.setObjectName("notifItemMsg")
        msg.setWordWrap(True)
        text_box.addWidget(msg)

        ts = QLabel(_humanize_time(record.timestamp))
        ts.setObjectName("notifItemTime")
        ts.setToolTip(record.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        text_box.addWidget(ts)

        row.addLayout(text_box, 1)
        return item

    def _on_clear(self) -> None:
        self._manager.clear_history()
        self.cleared.emit()

    def show_below(self, anchor: QWidget) -> None:
        """Show the popup positioned below the anchor widget (right-aligned)."""
        self.refresh()
        self._manager.mark_all_read()
        # Compute screen position
        global_top_right = anchor.mapToGlobal(QPoint(anchor.width(), anchor.height()))
        x = global_top_right.x() - self.width() + 8
        y = global_top_right.y() + 4
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
