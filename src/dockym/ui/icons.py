"""Dockym icon system.

Every icon is drawn with QPainter at the requested pixel size, so we get
crisp, theme-aware, scalable icons without external assets. Icons use a
single foreground color that can be passed in (or pulled from the current
text color) — that makes them work on any background, including light mode
and accent buttons.

Usage:
    from dockym.ui.icons import make_icon, Icons

    btn = QPushButton(make_icon("restart", color="#8b949e"), "Reiniciar todo")
    pix = icon_pixmap("play", color="white", size=14)
"""
from __future__ import annotations

import math as _math

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QSize
from PySide6.QtGui import (
    QColor, QIcon, QIconEngine, QImage, QPainter, QPainterPath,
    QPen, QPixmap, QPolygonF,
)


# Stroke width as a fraction of icon size — gives uniform visual weight
# whether the icon is rendered at 12px or 24px.
_STROKE = 1.6 / 16.0


def _setup(painter: QPainter, size: int, color: QColor) -> QPen:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color)
    pen.setWidthF(max(1.2, size * _STROKE))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _empty(size: int) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    return pix


# ─────────────────────────────────────────────────────────────────
# Individual icon drawing functions
#
# Each receives a QPainter already configured with antialiasing and the
# right pen color/width. Coordinates are in [0, 1] × [0, 1] logical space
# so the same code draws correctly at any size.
# ─────────────────────────────────────────────────────────────────


def _draw_play(p: QPainter, color: QColor, size: int) -> None:
    pen = _setup(p, size, color)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    # Triangle pointing right, centered, with 1px padding
    pad = size * 0.20
    poly = QPolygonF([
        QPointF(pad, pad),
        QPointF(size - pad, size / 2),
        QPointF(pad, size - pad),
    ])
    p.drawPolygon(poly)


def _draw_stop(p: QPainter, color: QColor, size: int) -> None:
    pen = _setup(p, size, color)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    pad = size * 0.22
    p.drawRect(QRectF(pad, pad, size - 2 * pad, size - 2 * pad))


def _draw_restart(p: QPainter, color: QColor, size: int) -> None:
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx = cy = size / 2
    r = size * 0.30
    # Open arc going clockwise, leaving a gap for the arrowhead
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPainterPath
    p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), 60 * 16, 280 * 16)
    # Arrowhead at the end of the arc
    path = QPainterPath()
    path.moveTo(cx + r * 0.30, cy - r * 0.95)
    path.lineTo(cx - r * 0.10, cy - r * 0.40)
    path.lineTo(cx + r * 0.55, cy - r * 0.30)
    path.closeSubpath()
    p.setBrush(color)
    p.drawPath(path)


def _draw_broom(p: QPainter, color: QColor, size: int) -> None:
    """Broom/cleanup — angled handle with brush base."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    # Diagonal handle from top-left to mid-bottom-right
    p.drawLine(QPointF(size * 0.18, size * 0.18),
               QPointF(size * 0.62, size * 0.62))
    # Brush base — a tilted fan shape at the bottom-right end
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(size * 0.50, size * 0.60)
    path.lineTo(size * 0.95, size * 0.60)
    path.lineTo(size * 0.78, size * 0.95)
    path.lineTo(size * 0.45, size * 0.78)
    path.closeSubpath()
    p.setBrush(color)
    p.drawPath(path)
    # Bristle lines
    p.setPen(pen)
    for offset in (0.0, 0.12, 0.24, 0.36):
        p.drawLine(QPointF(size * (0.55 + offset), size * (0.70 - offset * 0.4)),
                   QPointF(size * (0.65 + offset), size * (0.85 - offset * 0.4)))


def _draw_download(p: QPainter, color: QColor, size: int) -> None:
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    # Tray at the bottom
    tray_y = size * 0.80
    p.drawLine(QPointF(size * 0.18, tray_y), QPointF(size * 0.82, tray_y))
    p.drawLine(QPointF(size * 0.18, tray_y), QPointF(size * 0.18, size * 0.90))
    p.drawLine(QPointF(size * 0.82, tray_y), QPointF(size * 0.82, size * 0.90))
    # Arrow shaft + head
    p.drawLine(QPointF(size / 2, size * 0.15), QPointF(size / 2, size * 0.72))
    # Arrowhead triangle
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF([
        QPointF(size * 0.30, size * 0.58),
        QPointF(size / 2, size * 0.78),
        QPointF(size * 0.70, size * 0.58),
    ]))


def _draw_upload(p: QPainter, color: QColor, size: int) -> None:
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(size * 0.18, size * 0.18), QPointF(size * 0.82, size * 0.18))
    p.drawLine(QPointF(size / 2, size * 0.28), QPointF(size / 2, size * 0.85))
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF([
        QPointF(size * 0.30, size * 0.42),
        QPointF(size / 2, size * 0.22),
        QPointF(size * 0.70, size * 0.42),
    ]))


def _draw_save(p: QPainter, color: QColor, size: int) -> None:
    """Floppy-disk style save."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    pad = size * 0.15
    p.drawRoundedRect(QRectF(pad, pad, size - 2 * pad, size - 2 * pad),
                      size * 0.10, size * 0.10)
    # Label area on top half
    label_top = size * 0.22
    label_h = size * 0.25
    p.drawRoundedRect(QRectF(size * 0.32, label_top, size * 0.36, label_h),
                      size * 0.04, size * 0.04)
    # Bottom slot
    p.drawRoundedRect(QRectF(size * 0.30, size * 0.55, size * 0.40, size * 0.30),
                      size * 0.04, size * 0.04)


def _draw_clipboard(p: QPainter, color: QColor, size: int) -> None:
    """Clipboard / preview."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    pad = size * 0.15
    p.drawRoundedRect(QRectF(pad, pad + size * 0.10, size - 2 * pad, size - 2 * pad - size * 0.10),
                      size * 0.08, size * 0.08)
    # Clip at the top
    clip_w = size * 0.36
    p.drawRoundedRect(QRectF((size - clip_w) / 2, pad, clip_w, size * 0.20),
                      size * 0.05, size * 0.05)


def _draw_folder(p: QPainter, color: QColor, size: int) -> None:
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    # Tab
    path.moveTo(size * 0.10, size * 0.32)
    path.lineTo(size * 0.10, size * 0.22)
    path.lineTo(size * 0.42, size * 0.22)
    path.lineTo(size * 0.50, size * 0.32)
    # Body
    path.lineTo(size * 0.92, size * 0.32)
    path.lineTo(size * 0.92, size * 0.84)
    path.lineTo(size * 0.10, size * 0.84)
    path.closeSubpath()
    p.drawPath(path)


def _draw_refresh(p: QPainter, color: QColor, size: int) -> None:
    """Circular arrow — same as restart but smaller arc and a clearer gap."""
    _draw_restart(p, color, size)


def _draw_database(p: QPainter, color: QColor, size: int) -> None:
    """Cylinder — for Adminer / db template icon."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx = size / 2
    rx = size * 0.32
    ry = size * 0.10
    p.drawEllipse(QPointF(cx, size * 0.22), rx, ry)
    p.drawLine(QPointF(cx - rx, size * 0.22), QPointF(cx - rx, size * 0.78))
    p.drawLine(QPointF(cx + rx, size * 0.22), QPointF(cx + rx, size * 0.78))
    p.drawArc(QRectF(cx - rx, size * 0.68, 2 * rx, 2 * ry),
              0, -180 * 16)


def _draw_mail(p: QPainter, color: QColor, size: int) -> None:
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    pad = size * 0.15
    p.drawRoundedRect(QRectF(pad, pad + size * 0.08, size - 2 * pad, size - 2 * pad - size * 0.08),
                      size * 0.05, size * 0.05)
    # Flap (V)
    p.drawLine(QPointF(pad, pad + size * 0.08), QPointF(size / 2, size * 0.55))
    p.drawLine(QPointF(size / 2, size * 0.55), QPointF(size - pad, pad + size * 0.08))


# ─────────────────────────────────────────────────────────────────
# Service template icons (Postgres / MySQL / Mongo / Redis / Nginx / Rabbit)
# Tiny abstract glyphs that still read clearly at 16px.
# ─────────────────────────────────────────────────────────────────


def _draw_elephant(p: QPainter, color: QColor, size: int) -> None:
    """Postgres — simple stylized elephant head silhouette."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(color)
    cx = size / 2
    cy = size * 0.50
    # Round head
    p.drawEllipse(QPointF(cx - size * 0.10, cy), size * 0.22, size * 0.22)
    # Trunk
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(cx + size * 0.05, cy + size * 0.04)
    path.cubicTo(cx + size * 0.30, cy + size * 0.20,
                 cx + size * 0.18, cy + size * 0.34,
                 cx + size * 0.02, cy + size * 0.30)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)


def _draw_dolphin(p: QPainter, color: QColor, size: int) -> None:
    """MySQL — dolphin arc shape."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(size * 0.15, size * 0.65)
    path.cubicTo(size * 0.15, size * 0.30,
                 size * 0.55, size * 0.30,
                 size * 0.85, size * 0.55)
    path.lineTo(size * 0.70, size * 0.45)
    path.lineTo(size * 0.85, size * 0.65)
    p.setBrush(color)
    p.drawPath(path)


def _draw_leaf(p: QPainter, color: QColor, size: int) -> None:
    """MongoDB — leaf shape."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(size * 0.20, size * 0.85)
    path.cubicTo(size * 0.50, size * 0.10,
                 size * 0.85, size * 0.20,
                 size * 0.80, size * 0.80)
    path.closeSubpath()
    p.setBrush(color)
    p.drawPath(path)
    # Vein
    path = QPainterPath()
    path.moveTo(size * 0.20, size * 0.85)
    path.lineTo(size * 0.80, size * 0.80)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)


def _draw_redis(p: QPainter, color: QColor, size: int) -> None:
    """Redis — stacked layers (cube stack)."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    pad = size * 0.18
    h = size * 0.22
    for i in range(3):
        y = pad + i * (h * 0.6)
        p.drawRoundedRect(QRectF(pad, y, size - 2 * pad, h), h * 0.3, h * 0.3)


def _draw_globe(p: QPainter, color: QColor, size: int) -> None:
    """Nginx — globe with meridian."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx = cy = size / 2
    r = size * 0.36
    p.drawEllipse(QPointF(cx, cy), r, r)
    # Vertical meridian
    p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))
    # Horizontal equator
    p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))


def _draw_rabbit(p: QPainter, color: QColor, size: int) -> None:
    """RabbitMQ — stylized rabbit silhouette."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    # Body
    p.drawEllipse(QPointF(size * 0.55, size * 0.65), size * 0.20, size * 0.20)
    # Ears (two ovals at top)
    p.drawEllipse(QPointF(size * 0.55, size * 0.25), size * 0.06, size * 0.18)
    p.drawEllipse(QPointF(size * 0.70, size * 0.25), size * 0.06, size * 0.18)


def _draw_node(p: QPainter, color: QColor, size: int) -> None:
    """Node.js — hexagon (the Node logo's defining shape) with a dot in the middle."""
    pen = _setup(p, size, color)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx = cy = size / 2
    r = size * 0.38
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    for i in range(6):
        angle = (60 * i - 30) * 3.14159265 / 180  # pointy-top hexagon
        x = cx + r * _math.cos(angle)
        y = cy + r * _math.sin(angle)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)
    # Small dot in the middle
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(cx, cy), size * 0.05, size * 0.05)


# Registry of icon name → drawing function
ICONS: dict[str, callable] = {
    "play": _draw_play,
    "stop": _draw_stop,
    "restart": _draw_restart,
    "refresh": _draw_refresh,
    "broom": _draw_broom,
    "download": _draw_download,
    "upload": _draw_upload,
    "save": _draw_save,
    "clipboard": _draw_clipboard,
    "folder": _draw_folder,
    "database": _draw_database,
    "mail": _draw_mail,
    "elephant": _draw_elephant,
    "dolphin": _draw_dolphin,
    "leaf": _draw_leaf,
    "redis": _draw_redis,
    "globe": _draw_globe,
    "rabbit": _draw_rabbit,
    "node": _draw_node,
}


def _render(name: str, color: QColor, size: int) -> QPixmap:
    pix = _empty(size)
    if size <= 0:
        return pix
    draw_fn = ICONS.get(name)
    if draw_fn is None:
        return pix
    p = QPainter(pix)
    try:
        draw_fn(p, color, size)
    finally:
        p.end()
    return pix


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────


def icon_pixmap(name: str, color: str | QColor = "#e6edf3",
                size: int = 16) -> QPixmap:
    """Return a single QPixmap of the icon at *size*×*size*."""
    if isinstance(color, str):
        color = QColor(color)
    return _render(name, color, size)


def make_icon(name: str, color: str | QColor = "#e6edf3",
              size: int = 16) -> QIcon:
    """Return a QIcon (with a single pixmap entry) for use on QPushButton etc."""
    pix = icon_pixmap(name, color, size)
    # Use a custom engine that returns a properly-sized pixmap regardless
    # of the requested size, so the button scales it nicely.
    return QIcon(_IconEngine(pix, name, color, size))


class _IconEngine(QIconEngine):
    """Custom engine that re-renders at the requested size on demand."""

    def __init__(self, base_pix: QPixmap, name: str, color: QColor, size: int):
        super().__init__()
        self._base = base_pix
        self._name = name
        self._color = QColor(color)
        self._size = size

    def paint(self, painter, rect, mode, state):
        # Recolor for disabled state
        color = self._color
        if state == QIcon.State.Off:
            color = QColor("#484f58")
        target = _render(self._name, color, max(8, int(rect.width())))
        # Center within the target rect
        x = rect.x() + (rect.width() - target.width()) / 2
        y = rect.y() + (rect.height() - target.height()) / 2
        painter.drawPixmap(QPointF(x, y), target)

    def pixmap(self, size, mode, state):
        color = self._color
        if state == QIcon.State.Off:
            color = QColor("#484f58")
        return _render(self._name, color, size.width() or self._size)

    def clone(self):
        return _IconEngine(self._base, self._name, self._color, self._size)


# ─────────────────────────────────────────────────────────────────
# Convenience: create a labelled button with an icon
# ─────────────────────────────────────────────────────────────────

def make_icon_button(text: str, icon_name: str, *,
                     color: str = "#8b949e", icon_size: int = 14) -> "QPushButton":
    """Factory so callers don't have to import QPushButton just for this."""
    from PySide6.QtWidgets import QPushButton
    btn = QPushButton(text)
    btn.setIcon(make_icon(icon_name, color=color, size=icon_size))
    btn.setIconSize(QSize(icon_size, icon_size))
    return btn


# Quick smoke test: `python -m dockym.ui.icons` writes a few icons as PNGs.
if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path("/tmp/dockym_icons")
    out.mkdir(exist_ok=True)
    for name in ICONS:
        pix = icon_pixmap(name, "#e6edf3", 32)
        pix.save(str(out / f"{name}.png"))
    print(f"Wrote {len(ICONS)} icons to {out}")
