"""
ui.theme_assets
===============

Qt style sheets can colour a checkbox or a spin box, but the little glyphs
inside them (check mark, arrows) have to be images. Rather than ship image
files (and find them again from a frozen .exe), the few glyphs the theme
needs are drawn here with QPainter and written once to a per-user temp folder
the style sheet can point at.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF

_ICON_PX = 32  # drawn large, shown small: stays crisp on high-DPI screens


def _canvas() -> tuple[QImage, QPainter]:
    img = QImage(_ICON_PX, _ICON_PX, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    return img, p


def _check_mark(colour: QColor) -> QImage:
    img, p = _canvas()
    pen = QPen(colour, 4.2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline(QPolygonF([QPointF(8, 17), QPointF(14, 23), QPointF(24.5, 9.5)]))
    p.end()
    return img


def _arrow(colour: QColor, up: bool) -> QImage:
    img, p = _canvas()
    p.setPen(Qt.NoPen)
    p.setBrush(colour)
    if up:
        points = [QPointF(8, 20), QPointF(24, 20), QPointF(16, 10)]
    else:
        points = [QPointF(8, 12), QPointF(24, 12), QPointF(16, 22)]
    p.drawPolygon(QPolygonF(points))
    p.end()
    return img


def ensure_ui_icons(
    dark: str = "#0b0f14", light: str = "#8a97a8", accent: str = "#4fd6c9"
) -> dict[str, str]:
    """Writes the glyphs (if they are not there yet) and returns
    {name: forward-slash path}, ready for `url(...)` in a style sheet. Falls
    back to an empty dict when the folder cannot be written, in which case the
    theme simply keeps Qt's default glyphs."""
    folder = Path(tempfile.gettempdir()) / "ordis_market_ui" / "glyphs-1"
    drawings: dict[str, Callable[[], QImage]] = {
        "check": lambda: _check_mark(QColor(dark)),
        "arrow_down": lambda: _arrow(QColor(light), up=False),
        "arrow_up": lambda: _arrow(QColor(light), up=True),
        "arrow_down_hover": lambda: _arrow(QColor(accent), up=False),
        "arrow_up_hover": lambda: _arrow(QColor(accent), up=True),
    }
    paths: dict[str, str] = {}
    try:
        folder.mkdir(parents=True, exist_ok=True)
        for name, draw in drawings.items():
            path = folder / f"{name}.png"
            if not path.exists() and not draw().save(str(path), "PNG"):
                return {}
            paths[name] = path.as_posix()
    except OSError:
        return {}
    return paths
