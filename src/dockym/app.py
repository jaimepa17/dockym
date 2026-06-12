from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush

from dockym.ui.main_window import MainWindow
from dockym.ui.theme import get_theme_qss
from dockym.models.config import Config


# Brand colors — tuned for dark UI
_ICON_BG = QColor("#1f6feb")       # GitHub-blue accent (high contrast on dark)
_ICON_FG = QColor("#ffffff")       # White "D"


def _render_icon(size: int) -> QPixmap:
    """Render the Dockym mark at the requested size.

    Drawing per-size (instead of scaling a 64×64 master) gives crisp edges
    at 16/22/32/64 px and avoids the "white box" halo caused by antialiased
    downscaling.
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    # Background — rounded square, full bleed
    radius = max(2.0, size * 0.22)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(_ICON_BG))
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # Letter "D" — sized to the box, slightly raised to optically center
    font = QFont("Inter")
    font.setBold(True)
    # Cap height ≈ 70% of the box gives a balanced letterform
    font.setPixelSize(int(size * 0.72))
    painter.setFont(font)
    painter.setPen(QPen(_ICON_FG))
    # Nudge baseline up by ~1 px at small sizes for visual centering
    nudge = -1 if size <= 24 else 0
    painter.drawText(QRectF(0, nudge, size, size),
                     int(Qt.AlignmentFlag.AlignCenter), "D")

    painter.end()
    return pix


def _create_app_icon() -> QIcon:
    """Build a multi-resolution QIcon so Qt picks the crispest size."""
    icon = QIcon()
    for size in (16, 22, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_render_icon(size))
    return icon


class DockymApp(QApplication):
    def __init__(self, argv: list[str]):
        super().__init__(argv)
        self.setApplicationName("Dockym")
        self.setApplicationVersion("0.1.0")
        self.setOrganizationName("dockym")
        self.setStyle("Fusion")

        # BUG-019: HiDPI support — round to nearest integer to avoid fractional scaling artifacts
        self.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Apply theme from config
        config = Config.load()
        theme_qss = get_theme_qss(config.theme, config.font_family)
        self.setStyleSheet(theme_qss)

        self.setWindowIcon(_create_app_icon())


def run() -> None:
    app = DockymApp(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
