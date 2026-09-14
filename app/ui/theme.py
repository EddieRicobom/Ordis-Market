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
    padding: 7px 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
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
    height: 16px;
}}

QProgressBar::chunk {{
    background-color: {ACCENT_CYAN};
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
"""


def apply_theme(app) -> None:
    """Applies the Warframe-inspired stylesheet to a QApplication (or any
    QWidget) instance. Safe to call once at startup."""
    app.setStyleSheet(STYLESHEET)
