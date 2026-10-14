"""
ui.theme
========

A Warframe-inspired dark theme for the Ordis Market dashboard: near-black
Orbiter-style panels, a Tenno-cyan accent for interactive elements, and a
muted Orokin-gold accent for headers and emphasis.

Ordis: "I have redecorated. Please admire the color scheme before you
        start selling things."

This is plain Qt Style Sheet (QSS) text -- a CSS-like subset, not full
CSS3 (no box-shadow/transition/transform support), applied once at the
QApplication level so it covers the main window plus any dialogs
(QFileDialog, QMessageBox) consistently. Kept in its own module so the
color palette can be tuned without touching widget/layout code.

Widgets opt into a look through their object name (QLabel#SummaryLabel) or a
"role" property (QPushButton[role="primary"] for the main actions,
[role="ghost"] for the quiet ones).
"""

from __future__ import annotations

# -- Palette -----------------------------------------------------------
# Named here once so the values below stay consistent and easy to retune.
BG_BASE = "#0b0f14"          # near-black Orbiter panel background
BG_PANEL = "#121821"         # slightly raised panel/card background
BG_PANEL_ALT = "#171f2b"     # alternating table row / hover background
BORDER = "#26313f"           # subtle structural border
ACCENT_CYAN = "#4fd6c9"      # Tenno energy cyan -- primary interactive accent
ACCENT_CYAN_DIM = "#2f8f86"  # pressed/dimmer cyan
ACCENT_GOLD = "#c9a961"      # Orokin gold -- headers, emphasis, selection
TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED = "#8a97a8"
DANGER = "#e0654f"


STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}}

QLabel#AppTitle {{
    color: {ACCENT_GOLD};
    font-size: 16pt;
    font-weight: 700;
    letter-spacing: 1px;
}}

QLabel#AppSubtitle {{
    color: {TEXT_MUTED};
    font-style: italic;
}}

QLabel#SummaryLabel {{
    color: {TEXT_PRIMARY};
    padding: 2px 10px;
    border-left: 2px solid {ACCENT_CYAN_DIM};
}}

QLabel#LoadingLabel {{
    color: {ACCENT_CYAN};
    font-style: italic;
}}

QPushButton {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 6px 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

QPushButton:hover {{
    border: 1px solid {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}

QPushButton:pressed {{
    background-color: {ACCENT_CYAN_DIM};
    color: {BG_BASE};
    border: 1px solid {ACCENT_CYAN_DIM};
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    background-color: {BG_BASE};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_BASE};
}}

QTabBar::tab {{
    background-color: {BG_PANEL};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    padding: 6px 18px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    color: {ACCENT_GOLD};
    border-bottom: 2px solid {ACCENT_GOLD};
}}

QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}

QTextEdit {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 6px;
}}

QLineEdit, QComboBox, QSpinBox {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 5px 8px;
    selection-background-color: {ACCENT_CYAN_DIM};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border: 1px solid {ACCENT_CYAN};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT_CYAN_DIM};
    selection-background-color: {ACCENT_CYAN_DIM};
    outline: none;
}}

QTableWidget {{
    background-color: {BG_PANEL};
    alternate-background-color: {BG_PANEL_ALT};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_GOLD};
    selection-color: {BG_BASE};
}}

QTableWidget::item {{
    padding: 4px 6px;
}}

QHeaderView::section {{
    background-color: {BG_BASE};
    color: {ACCENT_GOLD};
    padding: 6px 8px;
    border: none;
    border-bottom: 2px solid {ACCENT_CYAN_DIM};
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QTableWidget QTableCornerButton::section {{
    background-color: {BG_BASE};
    border: none;
}}

QProgressBar {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 3px;
    text-align: center;
    color: {TEXT_PRIMARY};
    font-weight: 600;
    height: 18px;
}}

QProgressBar::chunk {{
    /* the dimmer cyan keeps the white percentage readable where it crosses the bar */
    background-color: {ACCENT_CYAN_DIM};
    border-radius: 2px;
}}

QStatusBar {{
    background-color: {BG_BASE};
    color: {ACCENT_CYAN};
    border-top: 1px solid {BORDER};
}}

QMessageBox {{
    background-color: {BG_PANEL};
    color: {TEXT_PRIMARY};
}}

QMessageBox QPushButton {{
    min-width: 70px;
}}

QScrollBar:vertical {{
    background: {BG_BASE};
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT_CYAN_DIM};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QToolTip {{
    background-color: {BG_PANEL};
    color: {ACCENT_CYAN};
    border: 1px solid {ACCENT_CYAN_DIM};
    padding: 4px 6px;
}}

QPushButton:focus {{
    border: 1px solid {ACCENT_CYAN_DIM};
}}

QPushButton[role="primary"] {{
    background-color: rgba(79, 214, 201, 0.12);
    border: 1px solid {ACCENT_CYAN_DIM};
    color: {ACCENT_CYAN};
}}

QPushButton[role="primary"]:hover {{
    background-color: rgba(79, 214, 201, 0.22);
    border: 1px solid {ACCENT_CYAN};
}}

QPushButton[role="primary"]:pressed {{
    background-color: {ACCENT_CYAN_DIM};
    color: {BG_BASE};
}}

QPushButton[role="primary"]:disabled {{
    background-color: {BG_BASE};
    border: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}

QPushButton[role="ghost"] {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {TEXT_MUTED};
}}

QPushButton[role="ghost"]:hover {{
    border: 1px solid {BORDER};
    color: {ACCENT_CYAN};
}}

QFrame#StatStrip {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
}}

QFrame#StatStrip QLabel#SummaryLabel {{
    background-color: transparent;
    padding: 6px 14px;
}}

QFrame#ToolbarSeparator {{
    background-color: {BORDER};
    min-width: 1px;
    max-width: 1px;
}}

QLabel#FooterLabel {{
    color: {TEXT_MUTED};
    font-size: 9pt;
    padding: 0 6px;
}}

QLabel#CountLabel {{
    color: {ACCENT_GOLD};
    font-weight: 600;
    padding: 0 6px;
}}

QLabel#EmptyTitle {{
    color: {TEXT_PRIMARY};
    font-size: 13pt;
    font-weight: 600;
}}

QLabel#EmptyHint {{
    color: {TEXT_MUTED};
    font-size: 10pt;
}}

QWidget#EmptyState {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
}}

QWidget#EmptyState QLabel {{
    background-color: transparent;
}}

QCheckBox {{
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {TEXT_MUTED};
    border-radius: 3px;
    background-color: {BG_PANEL};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {ACCENT_CYAN};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT_CYAN};
    border: 1px solid {ACCENT_CYAN};
}}

QSpinBox {{
    padding-right: 22px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    width: 20px;
    border-left: 1px solid {BORDER};
    background-color: {BG_PANEL_ALT};
}}

QSpinBox::up-button {{
    subcontrol-position: top right;
    border-top-right-radius: 3px;
}}

QSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: 3px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {BORDER};
}}

QScrollBar:horizontal {{
    background: {BG_BASE};
    height: 12px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {ACCENT_CYAN_DIM};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QTableWidget::item:hover {{
    background-color: {BG_PANEL_ALT};
}}

QTableWidget {{
    outline: none;
}}

QHeaderView::section:hover {{
    color: {ACCENT_CYAN};
}}

QTabBar::tab {{
    min-width: 70px;
}}

QSplitter::handle {{
    background-color: {BORDER};
}}

QSplitter::handle:vertical {{
    height: 3px;
}}

QSplitter::handle:hover {{
    background-color: {ACCENT_CYAN_DIM};
}}

QStatusBar QLabel {{
    color: {TEXT_MUTED};
    padding: 0 8px;
}}

QStatusBar QPushButton {{
    padding: 2px 10px;
    font-size: 8pt;
}}

QStatusBar::item {{
    border: none;
}}
"""


# Rules that need the glyph images from theme_assets (check mark, arrows).
# Kept apart from STYLESHEET so the base sheet stays pure text and the app
# still looks right, with Qt's own glyphs, if the images cannot be written.
GLYPH_STYLESHEET = """
QCheckBox::indicator:checked {{
    image: url("{check}");
}}

QComboBox::down-arrow {{
    image: url("{arrow_down}");
    width: 12px;
    height: 12px;
}}

QComboBox::down-arrow:on, QComboBox::down-arrow:hover {{
    image: url("{arrow_down_hover}");
}}

QSpinBox::up-arrow {{
    image: url("{arrow_up}");
    width: 10px;
    height: 10px;
}}

QSpinBox::down-arrow {{
    image: url("{arrow_down}");
    width: 10px;
    height: 10px;
}}

QSpinBox::up-arrow:hover {{
    image: url("{arrow_up_hover}");
}}

QSpinBox::down-arrow:hover {{
    image: url("{arrow_down_hover}");
}}
"""


def build_stylesheet(glyphs: dict[str, str] | None = None) -> str:
    """The base sheet, plus the glyph rules when the images are available."""
    if not glyphs or not all(key in glyphs for key in _GLYPH_KEYS):
        return STYLESHEET
    return STYLESHEET + GLYPH_STYLESHEET.format(**glyphs)


_GLYPH_KEYS = ("check", "arrow_down", "arrow_up", "arrow_down_hover", "arrow_up_hover")


def apply_theme(app) -> None:
    """Applies the Warframe-inspired stylesheet to a QApplication (or any
    QWidget) instance. Safe to call once at startup."""
    from app.ui.theme_assets import ensure_ui_icons

    app.setStyleSheet(build_stylesheet(ensure_ui_icons(
        dark=BG_BASE, light=TEXT_MUTED, accent=ACCENT_CYAN
    )))
