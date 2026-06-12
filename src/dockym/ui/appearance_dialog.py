from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox,
                               QGroupBox, QFormLayout, QDialogButtonBox,
                               QFrame, QWidget, QScrollArea)
from PySide6.QtCore import Qt, Signal

from dockym.models.config import Config, PANEL_POSITIONS, THEMES, FONTS

POSITION_LABELS = {
    "right": "Derecha",
    "left": "Izquierda",
    "bottom": "Abajo",
}

THEME_LABELS = {
    "dark": "Dark (Default)",
    "dark_vscode": "Dark VS Code",
    "dark_claude": "Dark Claude",
    "light": "Light",
}

PREVIEW_COLORS = {
    "dark": {"bg": "#0f1115", "surface": "#14171c", "text": "#d4d8de", "accent": "#4a8eff"},
    "dark_vscode": {"bg": "#1e1e1e", "surface": "#252526", "text": "#d4d4d4", "accent": "#007acc"},
    "dark_claude": {"bg": "#1a1a2e", "surface": "#16213e", "text": "#e0e0e0", "accent": "#d4a574"},
    "light": {"bg": "#ffffff", "surface": "#f4f4f5", "text": "#18181b", "accent": "#2563eb"},
}


class AppearanceDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Apariencia — Dockym")
        self.setMinimumSize(420, 450)
        self.setMaximumSize(520, 650)
        self._selected_theme = config.theme
        self._setup_ui()
        self._load_config()
        self._update_preview()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # ── Scroll Area ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        # ── Layout Section ─────────────────────────────────────
        layout_group = QGroupBox("Layout del panel")
        layout_form = QFormLayout(layout_group)

        self.position_combo = QComboBox()
        for pos in PANEL_POSITIONS:
            self.position_combo.addItem(POSITION_LABELS[pos], pos)
        layout_form.addRow("Posición:", self.position_combo)

        layout.addWidget(layout_group)

        # ── Theme Section ──────────────────────────────────────
        theme_group = QGroupBox("Tema")
        theme_form = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        for theme in THEMES:
            self.theme_combo.addItem(THEME_LABELS[theme], theme)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_form.addRow("Tema:", self.theme_combo)

        layout.addWidget(theme_group)

        # ── Font Section ───────────────────────────────────────
        font_group = QGroupBox("Tipografía")
        font_form = QFormLayout(font_group)

        self.font_combo = QComboBox()
        for font in FONTS:
            self.font_combo.addItem(font, font)
        self.font_combo.currentIndexChanged.connect(self._update_preview)
        font_form.addRow("Fuente:", self.font_combo)

        layout.addWidget(font_group)

        # ── Preview ────────────────────────────────────────────
        preview_group = QGroupBox("Vista previa")
        preview_inner = QVBoxLayout(preview_group)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("previewFrame")
        self.preview_frame.setMinimumHeight(80)

        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setSpacing(6)

        self.preview_title = QLabel("Dockym")
        self.preview_title.setObjectName("previewTitle")
        self.preview_body = QLabel("Administra los servicios Docker")
        self.preview_body.setObjectName("previewBody")
        self.preview_muted = QLabel("● En ejecución  |  3/5 activos")
        self.preview_muted.setObjectName("previewMuted")

        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_body)
        preview_layout.addWidget(self.preview_muted)

        preview_inner.addWidget(self.preview_frame)
        layout.addWidget(preview_group)

        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        # ── Buttons (outside scroll) ───────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_config)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def _on_theme_changed(self, index: int):
        self._selected_theme = self.theme_combo.currentData()
        self._update_preview()

    def _load_config(self):
        idx = self.position_combo.findData(self.config.panel_position)
        if idx >= 0:
            self.position_combo.setCurrentIndex(idx)

        idx = self.theme_combo.findData(self.config.theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self._selected_theme = self.config.theme

        idx = self.font_combo.findData(self.config.font_family)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)

    def _update_preview(self):
        theme = self._selected_theme
        colors = PREVIEW_COLORS.get(theme, PREVIEW_COLORS["dark"])
        font = self.font_combo.currentData() or "Inter"

        self.preview_frame.setStyleSheet(f"""
            #previewFrame {{
                background-color: {colors['surface']};
                border: 1px solid #252a33;
                border-radius: 6px;
                padding: 12px;
            }}
            #previewTitle {{
                color: {colors['text']};
                font-family: "{font}";
                font-size: 16px;
                font-weight: 600;
            }}
            #previewBody {{
                color: {colors['text']};
                font-family: "{font}";
                font-size: 13px;
                opacity: 0.7;
            }}
            #previewMuted {{
                color: {colors['accent']};
                font-family: "{font}";
                font-size: 12px;
                font-weight: 500;
            }}
        """)

    def _save_config(self):
        self.config.panel_position = self.position_combo.currentData()
        self.config.theme = self.theme_combo.currentData()
        self.config.font_family = self.font_combo.currentData()
        self.config.save()
        self.accept()
