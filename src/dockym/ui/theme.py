"""Dockym Design System — Modern UI Theme (2025-2026)

Inspired by VS Code, Linear, Docker Desktop, and OrbStack.
Key principles:
- 8px grid system for consistent spacing
- 6px border-radius for all interactive elements
- Subtle hover states (visible but not jarring)
- Accessible focus rings
- Reduced visual noise
- Clear visual hierarchy
"""

DOCKYM_QSS = """
/* === DOCKYM DESIGN SYSTEM — GitHub Dark + Carbon Inspired (2025-2026) === */

/* === ROOT PALETTE === */
* {
    color: #8b949e;
    font-family: "Inter", "Cantarell", "Noto Sans", "DejaVu Sans", "Segoe UI", "SF Pro", "Roboto", sans-serif;
    font-size: 13px;
    outline: none;
}

QMainWindow, QDialog, QWidget#centralWidget, QWidget#contentArea {
    background-color: #0d1117;
}

QWidget {
    background-color: transparent;
}

/* === TITLE BAR / HEADER (Compact 40px) === */
#headerBar {
    background-color: #010409;
    border-bottom: 1px solid #21262d;
    min-height: 40px;
    max-height: 40px;
}

#headerTitle {
    color: #e6edf3;
    font-size: 14px;
    font-weight: 600;
}

#headerSubtitle {
    color: #484f58;
    font-size: 12px;
    font-weight: 400;
}

#headerSep {
    color: #484f58;
    font-size: 14px;
    padding: 0 2px;
}

#countLabel {
    color: #8b949e;
    font-size: 11px;
    font-weight: 500;
    padding: 3px 8px;
    background-color: #21262d;
    border-radius: 10px;
}

#eventsIndicator {
    color: #58a6ff;
    font-size: 12px;
    font-weight: 600;
    padding: 0 6px;
}

#eventsIndicator[connected="true"] { color: #3fb950; }
#eventsIndicator[connected="false"] { color: #f85149; }

/* === SIDEBAR === */
#sidebar {
    background-color: #010409;
    border-right: 1px solid #21262d;
}

#logoContainer {
    background-color: #010409;
    border-bottom: 1px solid #21262d;
    min-height: 48px;
    max-height: 48px;
}

#logoLabel {
    color: #e6edf3;
    font-size: 16px;
    font-weight: 700;
    padding: 0 16px;
}

#logoBrand {
    color: #58a6ff;
    font-weight: 700;
}

#navList {
    background-color: transparent;
    border: none;
    padding: 8px 0;
}

#navList::item {
    color: #8b949e;
    padding: 10px 16px;
    border-left: 2px solid transparent;
    border-radius: 0;
    margin: 2px 0;
    font-size: 13px;
    font-weight: 500;
}

#navList::item:hover {
    background-color: #161b22;
    color: #c9d1d9;
}

#navList::item:selected {
    background-color: #161b22;
    color: #e6edf3;
    border-left: 2px solid #58a6ff;
}

#versionLabel {
    color: #484f58;
    font-size: 10px;
    padding: 12px 16px;
}

/* === CARDS / PANELS === */
QFrame#projectCard, QFrame#serviceCard {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
}

/* === TREE (Continuous-row hover/selection) === */
QTreeWidget {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    selection-background-color: #1f6feb22;
    selection-color: #e6edf3;
    outline: none;
    padding: 0;
    font-size: 13px;
}

QTreeWidget::item {
    padding: 6px 8px;
    border: none;
    color: #8b949e;
    min-height: 32px;
    /* No margin/border-radius here: the row-level highlight is painted
       by _ServiceRowDelegate so the entire row is one continuous rect. */
}

/* No per-cell hover/selected backgrounds — the delegate handles it for
   a uniform, row-spanning highlight. */

/* Per-row action button (play / stop) */
QToolButton[class="rowAction"] {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px;
    margin: 0;
}
QToolButton[class="rowAction"]:hover {
    background-color: #21262d;
    border: 1px solid #30363d;
}
QToolButton[class="rowAction"]:pressed {
    background-color: #161b22;
}
QToolButton[class="rowAction"]:disabled {
    opacity: 0.5;
}

QTreeWidget::branch {
    background-color: transparent;
}

QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children {
    image: none;
}

QTreeWidget::branch:open:has-children {
    image: none;
}

QHeaderView::section {
    background-color: #010409;
    color: #484f58;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #21262d;
    font-weight: 600;
    font-size: 11px;
    outline: none;
}

/* === TABLE === */
QTableView {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    selection-background-color: #1f6feb22;
    selection-color: #e6edf3;
    gridline-color: #21262d;
    outline: none;
}

QTableView::item {
    padding: 8px 12px;
    border: none;
    color: #8b949e;
}

QTableView::item:hover {
    background-color: #1c2128;
    color: #c9d1d9;
}

QTableView::item:selected {
    background-color: #1f6feb22;
    color: #e6edf3;
}

/* === BUTTONS (Consistent 6px radius) === */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #30363d;
    border: 1px solid #3d444d;
    color: #e6edf3;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border: 1px solid #21262d;
}

QPushButton#btn-primary {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #238636;
    font-weight: 600;
}

QPushButton#btn-primary:hover {
    background-color: #2ea043;
    border: 1px solid #2ea043;
}

QPushButton#btn-primary:pressed {
    background-color: #1a7f37;
    border: 1px solid #1a7f37;
}

QPushButton#btn-primary:disabled {
    background-color: #1a4d2e;
    color: #3fb95066;
    border: 1px solid #1a4d2e;
}

QPushButton#btn-danger {
    background-color: #21262d;
    color: #f85149;
    border: 1px solid #f8514933;
}

QPushButton#btn-danger:hover {
    background-color: #f8514918;
    border: 1px solid #f8514966;
    color: #ff7b72;
}

QPushButton#btn-danger:disabled {
    background-color: #161b22;
    color: #f8514944;
    border: 1px solid #21262d;
}

/* === INPUTS === */
QLineEdit {
    background-color: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border: 1px solid #58a6ff;
    background-color: #0d1117;
}

QLineEdit::placeholder {
    color: #484f58;
}

QComboBox {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 7px 12px;
    min-height: 18px;
}

QComboBox:hover {
    border: 1px solid #3d444d;
}

QComboBox:focus {
    border: 1px solid #58a6ff;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #8b949e;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb22;
    selection-color: #e6edf3;
    outline: none;
    padding: 4px;
    border-radius: 6px;
}

/* === LABELS === */
QLabel {
    color: #8b949e;
    background-color: transparent;
}

QLabel#accent {
    color: #58a6ff;
    font-weight: 600;
}

QLabel#muted {
    color: #484f58;
    font-size: 11px;
    font-weight: 500;
}

QLabel#title {
    color: #e6edf3;
    font-size: 14px;
    font-weight: 600;
}

QLabel#infoCard, QFrame#infoCard {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 12px 16px;
    color: #8b949e;
}

/* === INFO CARD LABELS === */
QLabel#svcName {
    color: #e6edf3;
    font-size: 15px;
    font-weight: 600;
}

QLabel#svcDetail {
    color: #8b949e;
    font-size: 12px;
    font-weight: 500;
}

QLabel#svcStatus {
    color: #c9d1d9;
    font-size: 13px;
    font-weight: 500;
    padding: 4px 0;
}

/* === SECTION LABELS === */
QLabel#sectionLabel {
    color: #484f58;
    font-size: 11px;
    font-weight: 600;
    padding: 0 4px;
}

/* === SECTION DIVIDER === */
QFrame#sectionDivider {
    background-color: #21262d;
    border: none;
    max-height: 1px;
    min-height: 1px;
}

/* === ACTION CARDS === */
QFrame#actionCard {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
}

QFrame#actionCard QPushButton {
    padding: 9px 12px;
    font-size: 12px;
    min-height: 18px;
}

QFrame#actionCard QPushButton#btn-primary {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #238636;
    font-weight: 600;
}

QFrame#actionCard QPushButton#btn-primary:hover {
    background-color: #2ea043;
    border: 1px solid #2ea043;
}

QFrame#actionCard QPushButton#btn-danger {
    color: #f85149;
    border: 1px solid #f8514933;
    background-color: #21262d;
}

QFrame#actionCard QPushButton#btn-danger:hover {
    background-color: #f8514918;
    border: 1px solid #f8514966;
    color: #ff7b72;
}

/* === SPLITTER (Subtle 1px handle) === */
QSplitter::handle {
    background-color: transparent;
}

QSplitter::handle:horizontal {
    width: 1px;
    background-color: #21262d;
}

QSplitter::handle:vertical {
    height: 1px;
    background-color: #21262d;
}

QSplitter::handle:hover {
    background-color: #58a6ff;
}

/* === STATUS BAR (Compact) === */
QStatusBar {
    background-color: #010409;
    color: #484f58;
    border-top: 1px solid #21262d;
    font-size: 11px;
    font-weight: 500;
    padding: 0 8px;
    min-height: 22px;
}

QStatusBar::item {
    border: none;
}

/* === GROUP BOX === */
QGroupBox {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    margin-top: 14px;
    padding: 16px;
    font-weight: 600;
    color: #c9d1d9;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #484f58;
    font-size: 11px;
    font-weight: 600;
}

/* === LIST WIDGET === */
QListWidget {
    background-color: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    selection-background-color: #1f6feb22;
    selection-color: #e6edf3;
}

QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
    color: #8b949e;
    margin: 1px 4px;
}

QListWidget::item:hover {
    background-color: #1c2128;
    color: #c9d1d9;
}

QListWidget::item:selected {
    background-color: #1f6feb22;
    color: #e6edf3;
}

/* === SCROLL BAR (Refined) === */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border: none;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 4px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    border: none;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #30363d;
    border-radius: 4px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #484f58;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* === TOOLTIPS === */
QToolTip {
    background-color: #1c2128;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* === MENUS === */
QMenu {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px 6px 16px;
    border-radius: 4px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background-color: #1f6feb22;
    color: #e6edf3;
}

QMenu::separator {
    height: 1px;
    background-color: #21262d;
    margin: 4px 12px;
}

QMenu::item:disabled {
    color: #484f58;
}

/* === CHECKBOX === */
QCheckBox {
    color: #8b949e;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #30363d;
    border-radius: 4px;
    background-color: #21262d;
}

QCheckBox::indicator:hover {
    border: 1px solid #58a6ff;
}

QCheckBox::indicator:checked {
    background-color: #238636;
    border: 1px solid #238636;
}

/* === SPIN BOX === */
QSpinBox {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 18px;
}

QSpinBox:focus {
    border: 1px solid #58a6ff;
}

QSpinBox::up-button, QSpinBox::down-button {
    border: none;
    width: 20px;
}

QSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #8b949e;
}

QSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #8b949e;
}

/* === TEXT EDIT (logs, code) === */
QTextEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

/* === FOCUS STATES (Subtle but visible) === */
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #58a6ff;
}

QTreeWidget:focus {
    border: 1px solid #58a6ff;
}

QTextEdit:focus {
    border: 1px solid #58a6ff;
}

/* === DIALOG BUTTON BOX === */
QDialogButtonBox QPushButton {
    min-width: 80px;
}

/* === SCROLL AREA === */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* === FRAMELESS TITLE BAR === */
#titleBar {
    background-color: #010409;
    border-bottom: 1px solid #21262d;
    min-height: 40px;
    max-height: 40px;
}

#titleBarIcon {
    padding: 0;
}

#titleBarTitle {
    color: #e6edf3;
    font-size: 13px;
    font-weight: 600;
    padding: 0 4px;
}

#titleBarTray {
    background-color: transparent;
    color: #8b949e;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 400;
}

#titleBarTray:hover {
    background-color: #1c2128;
    color: #e6edf3;
}

#titleBarEvents {
    color: #58a6ff;
    font-size: 12px;
    font-weight: 600;
    padding: 0 4px;
}

#titleBarCount {
    color: #8b949e;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    background-color: #21262d;
    border-radius: 10px;
}

#titleBarMin, #titleBarMax, #titleBarClose {
    background-color: transparent;
    color: #8b949e;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 400;
}

#titleBarMin:hover, #titleBarMax:hover {
    background-color: #1c2128;
    color: #e6edf3;
}

#titleBarClose:hover {
    background-color: #f85149;
    color: #ffffff;
}
"""


def get_theme_colors(theme: str = "dark") -> dict:
    """Return the colour-token dict for the given theme name.

    Kept separate from get_theme_qss so non-QSS consumers (e.g. the row
    delegate) can read the same tokens without rendering a stylesheet.
    """
    if theme == "light":
        return {
            "bg": "#ffffff",
            "bg_header": "#f6f8fa",
            "bg_surface": "#f6f8fa",
            "bg_elevated": "#ffffff",
            "bg_hover": "#eaeef2",
            "bg_selected": "#ddf4ff",
            "text_primary": "#1f2328",
            "text_secondary": "#656d76",
            "text_muted": "#8c959f",
            "text_disabled": "#afb8c1",
            "border": "#d0d7de",
            "border_hover": "#afb8c1",
            "accent": "#0969da",
            "accent_hover": "#218bff",
            "success": "#1a7f37",
            "success_hover": "#2da44e",
            "danger": "#cf222e",
            "danger_hover": "#a40e26",
        }
    if theme == "dark_vscode":
        return {
            "bg": "#1e1e1e",
            "bg_header": "#252526",
            "bg_surface": "#252526",
            "bg_elevated": "#2d2d2d",
            "bg_hover": "#2a2d2e",
            "bg_selected": "#264f78",
            "text_primary": "#d4d4d4",
            "text_secondary": "#969696",
            "text_muted": "#6a6a6a",
            "text_disabled": "#5a5a5a",
            "border": "#3c3c3c",
            "border_hover": "#4a4a4a",
            "accent": "#007acc",
            "accent_hover": "#1c97ea",
            "success": "#4ec9b0",
            "success_hover": "#6fcfbd",
            "danger": "#f14c4c",
            "danger_hover": "#e06c75",
        }
    if theme == "dark_claude":
        return {
            "bg": "#141413",
            "bg_header": "#1A1917",
            "bg_surface": "#1A1917",
            "bg_elevated": "#2B2A27",
            "bg_hover": "#2B2A27",
            "bg_selected": "#3B3A37",
            "text_primary": "#EAE7DF",
            "text_secondary": "#A9A39A",
            "text_muted": "#6B665F",
            "text_disabled": "#4A4945",
            "border": "#2B2A27",
            "border_hover": "#3B3A37",
            "accent": "#D4967E",
            "accent_hover": "#E0AB96",
            "success": "#9ACA86",
            "success_hover": "#A8D696",
            "danger": "#D47563",
            "danger_hover": "#E08573",
        }
    # dark (default)
    return {
        "bg": "#0d1117",
        "bg_header": "#010409",
        "bg_surface": "#161b22",
        "bg_elevated": "#1c2128",
        "bg_hover": "#1c2128",
        "bg_selected": "#1f6feb22",
        "text_primary": "#e6edf3",
        "text_secondary": "#8b949e",
        "text_muted": "#484f58",
        "text_disabled": "#484f58",
        "border": "#21262d",
        "border_hover": "#30363d",
        "accent": "#58a6ff",
        "accent_hover": "#79c0ff",
        "success": "#3fb950",
        "success_hover": "#56d364",
        "danger": "#f85149",
        "danger_hover": "#ff7b72",
    }


def get_theme_qss(theme: str = "dark", font_family: str = "Inter") -> str:
    """Generate QSS with custom theme and font."""
    colors = get_theme_colors(theme)
    return f"""
/* === GENERATED THEME: {theme.upper()} (GitHub Dark Inspired) === */
* {{
    color: {colors['text_secondary']};
    font-family: "{font_family}", "Cantarell", "Noto Sans", "DejaVu Sans", "Segoe UI", "SF Pro", "Roboto", sans-serif;
    font-size: 13px;
    outline: none;
}}

QMainWindow, QDialog, QWidget#centralWidget, QWidget#contentArea {{
    background-color: {colors['bg']};
}}

QWidget {{
    background-color: transparent;
}}

/* === HEADER (Compact 40px) === */
#headerBar {{
    background-color: {colors['bg_header']};
    border-bottom: 1px solid {colors['border']};
    min-height: 40px;
    max-height: 40px;
}}

#headerTitle {{
    color: {colors['text_primary']};
    font-size: 14px;
    font-weight: 600;
}}

#headerSubtitle {{
    color: {colors['text_muted']};
    font-size: 12px;
    font-weight: 400;
}}

#headerSep {{ color: {colors['text_muted']}; font-size: 14px; padding: 0 2px; }}

#countLabel {{
    color: {colors['text_secondary']};
    font-size: 11px;
    padding: 3px 8px;
    background-color: {colors['border']};
    border-radius: 10px;
}}

#eventsIndicator {{
    color: {colors['accent']};
    font-size: 12px;
    font-weight: 600;
    padding: 0 6px;
}}

/* === BUTTONS (Consistent 6px radius) === */
QPushButton {{
    background-color: {colors['border']};
    color: {colors['text_secondary']};
    border: 1px solid {colors['border_hover']};
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 500;
    font-size: 13px;
    min-height: 18px;
}}

QPushButton:hover {{
    background-color: {colors['bg_hover']};
    color: {colors['text_primary']};
}}

QPushButton:pressed {{
    background-color: {colors['bg_surface']};
}}

QPushButton:disabled {{
    background-color: {colors['bg_surface']};
    color: {colors['text_disabled']};
    border: 1px solid {colors['border']};
}}

QPushButton#btn-primary {{
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #238636;
    font-weight: 600;
}}

QPushButton#btn-primary:hover {{
    background-color: #2ea043;
    border: 1px solid #2ea043;
}}

QPushButton#btn-danger {{
    color: {colors['danger']};
    border: 1px solid {colors['danger']}33;
}}

QPushButton#btn-danger:hover {{
    background-color: {colors['danger']}18;
    border: 1px solid {colors['danger']}66;
    color: {colors['danger_hover']};
}}

/* === INPUTS === */
QLineEdit {{
    background-color: {colors['bg']};
    color: {colors['text_primary']};
    border: 1px solid {colors['border_hover']};
    border-radius: 6px;
    padding: 8px 12px;
}}

QLineEdit:focus {{
    border: 1px solid {colors['accent']};
}}

QComboBox {{
    background-color: {colors['border']};
    color: {colors['text_secondary']};
    border: 1px solid {colors['border_hover']};
    border-radius: 6px;
    padding: 7px 12px;
}}

QComboBox:focus {{
    border: 1px solid {colors['accent']};
}}

QLabel {{
    color: {colors['text_secondary']};
    background-color: transparent;
}}

QLabel#muted {{
    color: {colors['text_muted']};
    font-size: 11px;
    font-weight: 500;
}}

QLabel#title {{
    color: {colors['text_primary']};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#sectionLabel {{
    color: {colors['text_muted']};
    font-size: 11px;
    font-weight: 600;
}}

QLabel#svcName {{
    color: {colors['text_primary']};
    font-size: 15px;
    font-weight: 600;
}}

QLabel#svcDetail {{
    color: {colors['text_secondary']};
    font-size: 12px;
}}

QLabel#svcStatus {{
    color: {colors['text_secondary']};
    font-size: 13px;
    padding: 4px 0;
}}

QFrame#infoCard, QFrame#actionCard {{
    background-color: {colors['bg_surface']};
    border: 1px solid {colors['border']};
    border-radius: 6px;
}}

/* === SECTION DIVIDER === */
QFrame#sectionDivider {{
    background-color: {colors['border']};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

/* === TREE (Improved) === */
QTreeWidget {{
    background-color: {colors['bg_surface']};
    alternate-background-color: {colors['bg_hover']};
    border: 1px solid {colors['border']};
    border-radius: 6px;
    selection-background-color: {colors['bg_selected']};
    selection-color: {colors['text_primary']};
    outline: none;
    padding: 0;
}}

QTreeWidget::item {{
    padding: 6px 8px;
    border: none;
    color: {colors['text_secondary']};
    min-height: 32px;
    /* Row-level hover/selection is painted by _ServiceRowDelegate so the
       whole row shares a single rounded rect — no per-cell styles here. */
}}

/* Per-row hover/selected is painted by _ServiceRowDelegate so the whole
   row shares a single continuous highlight. */

/* Per-row action button (play / stop) */
QToolButton[class="rowAction"] {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px;
    margin: 0;
}}
QToolButton[class="rowAction"]:hover {{
    background-color: {colors['bg_elevated']};
    border: 1px solid {colors['border_hover']};
}}
QToolButton[class="rowAction"]:pressed {{
    background-color: {colors['bg_surface']};
}}
QToolButton[class="rowAction"]:disabled {{
    opacity: 0.5;
}}

QHeaderView::section {{
    background-color: {colors['bg_header']};
    color: {colors['text_muted']};
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {colors['border']};
    font-weight: 600;
    font-size: 11px;
    outline: none;
}}

/* === SCROLL BAR === */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {colors['border_hover']};
    border-radius: 4px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors['text_muted']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QStatusBar {{
    background-color: {colors['bg_header']};
    color: {colors['text_muted']};
    border-top: 1px solid {colors['border']};
    font-size: 11px;
    min-height: 22px;
}}

QSplitter::handle:horizontal {{
    width: 1px;
    background-color: {colors['border']};
}}

QSplitter::handle:hover {{
    background-color: {colors['accent']};
}}

QGroupBox {{
    background-color: {colors['bg_surface']};
    border: 1px solid {colors['border']};
    border-radius: 6px;
    margin-top: 14px;
    padding: 16px;
    font-weight: 600;
    color: {colors['text_secondary']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {colors['text_muted']};
    font-size: 11px;
    font-weight: 600;
}}

QToolTip {{
    background-color: {colors['bg_elevated']};
    color: {colors['text_primary']};
    border: 1px solid {colors['border_hover']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

QMenu {{
    background-color: {colors['bg_surface']};
    color: {colors['text_secondary']};
    border: 1px solid {colors['border_hover']};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 16px;
    border-radius: 4px;
    margin: 2px 4px;
}}

QMenu::item:selected {{
    background-color: {colors['bg_selected']};
    color: {colors['text_primary']};
}}

QMenuBar {{
    background-color: {colors['bg_header']};
    color: {colors['text_secondary']};
    border-bottom: 1px solid {colors['border']};
    padding: 2px 0;
}}

QMenuBar::item {{
    background-color: transparent;
    color: {colors['text_secondary']};
    padding: 6px 12px;
    border-radius: 4px;
    margin: 2px 2px;
}}

QMenuBar::item:selected {{
    background-color: {colors['bg_hover']};
    color: {colors['text_primary']};
}}

QMenuBar::item:pressed {{
    background-color: {colors['bg_selected']};
    color: {colors['text_primary']};
}}

/* Custom menu bar (QPushButton-based) */
#menuBar {{
    background-color: {colors['bg_header']};
    border-bottom: 1px solid {colors['border']};
}}

QPushButton#menuBtn {{
    background-color: transparent;
    color: {colors['text_secondary']};
    border: none;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    border-radius: 4px;
}}

QPushButton#menuBtn:hover {{
    background-color: {colors['bg_hover']};
    color: {colors['text_primary']};
}}

QPushButton#menuBtn:pressed {{
    background-color: {colors['bg_selected']};
    color: {colors['text_primary']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {colors['border']};
    margin: 4px 12px;
}}

QCheckBox {{
    color: {colors['text_secondary']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {colors['border_hover']};
    border-radius: 4px;
    background-color: {colors['border']};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {colors['accent']};
}}

QCheckBox::indicator:checked {{
    background-color: #238636;
    border: 1px solid #238636;
}}

QPushButton:focus, QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {colors['accent']};
}}

QTreeWidget:focus {{
    border: 1px solid {colors['accent']};
}}
/* === FRAMELESS TITLE BAR === */
#titleBar {{
    background-color: {colors['bg_header']};
    border-bottom: 1px solid {colors['border']};
    min-height: 40px;
    max-height: 40px;
}}

#titleBarIcon {{
    padding: 0;
}}

#titleBarTitle {{
    color: {colors['text_primary']};
    font-size: 13px;
    font-weight: 600;
    padding: 0 4px;
}}

#titleBarBell {{
    background-color: transparent;
    color: {colors['text_secondary']};
    border: none;
    border-radius: 4px;
}}

#titleBarBell:hover {{
    background-color: {colors['bg_hover']};
    color: {colors['text_primary']};
}}

#titleBarEvents {{
    color: {colors['accent']};
    font-size: 12px;
    font-weight: 600;
    padding: 0 4px;
}}

#titleBarCount {{
    color: {colors['text_secondary']};
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    background-color: {colors['border']};
    border-radius: 10px;
}}

#titleBarMin, #titleBarMax, #titleBarClose {{
    background-color: transparent;
    color: {colors['text_secondary']};
    border: none;
    border-radius: 4px;
    font-size: 12px;
}}

#titleBarMin:hover, #titleBarMax:hover {{
    background-color: {colors['bg_hover']};
    color: {colors['text_primary']};
}}

#titleBarClose:hover {{
    background-color: {colors['danger']};
    color: #ffffff;
}}

/* === NOTIFICATION CENTER (bell popup) === */
#notifCenter {{
    background-color: {colors['bg_surface']};
    border: 1px solid {colors['border_hover']};
    border-radius: 8px;
}}

#notifCenterHeader {{
    background-color: {colors['bg_header']};
    border-bottom: 1px solid {colors['border']};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

#notifCenterTitle {{
    color: {colors['text_primary']};
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#notifCenterClear {{
    background-color: transparent;
    color: {colors['text_muted']};
    border: none;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
    border-radius: 4px;
    min-height: 14px;
}}

QPushButton#notifCenterClear:hover {{
    background-color: {colors['bg_hover']};
    color: {colors['text_primary']};
}}

QPushButton#notifCenterClear:disabled {{
    color: {colors['text_disabled']};
}}

#notifCenterScroll {{
    background-color: transparent;
    border: none;
}}

#notifCenterList {{
    background-color: transparent;
}}

#notifCenterEmpty {{
    color: {colors['text_muted']};
    font-size: 12px;
    padding: 24px;
}}

#notifItem {{
    background-color: transparent;
    border-bottom: 1px solid {colors['border']};
}}

#notifItem[unread="true"] {{
    background-color: {colors['bg_hover']};
}}

#notifItem:hover {{
    background-color: {colors['bg_elevated']};
}}

QLabel#notifItemMsg {{
    color: {colors['text_primary']};
    font-size: 12px;
    font-weight: 500;
    background-color: transparent;
}}

QLabel#notifItemTime {{
    color: {colors['text_muted']};
    font-size: 10px;
    font-weight: 400;
    background-color: transparent;
}}
"""
