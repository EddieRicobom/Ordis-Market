"""
ui.app_icon
===========

The Ordis Market program icon, drawn in code so it is always available (window
title bar, taskbar, dialogs) without shipping or locating an image file, and
so tools/make_icon.py can export the very same artwork as assets/*.ico / *.png
for the Windows executable.

An original emblem, not a depiction of any character: a broken Tenno-cyan ring
(the orbit of the trade) around a faceted Orokin-gold gem (the currency), on a
dark Orbiter panel. The same colours as the theme, so the icon and the UI read
as one thing.

Ordis: "I have drawn myself. Or something that vaguely resembles my mood."
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)

# Same values as app/ui/theme.py (kept literal here so this module has no
# dependency on the stylesheet).
_BG_TOP = QColor("#142030")
_BG_BOTTOM = QColor("#070a0f")
_BORDER = QColor("#26313f")
_CYAN = QColor("#4fd6c9")
_CYAN_DIM = QColor("#2f8f86")
_GOLD_LIGHT = QColor("#f0d88e")
_GOLD = QColor("#c9a961")
_GOLD_DARK = QColor("#8f7132")

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
"""Sizes bundled in the .ico and added to the window's QIcon."""


def render_icon(size: int) -> QImage:
    """The icon as a transparent-cornered ARGB image of `size` x `size` px.
    Small sizes get a bolder ring and a bigger gem so they stay readable."""
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    p.scale(size, size)  # draw in unit coordinates from here on
    small = size <= 32
    tiny = size <= 20

    # Plate: rounded square with a faint top-lit gradient.
    plate = QRectF(0.02, 0.02, 0.96, 0.96)
    gradient = QLinearGradient(0, 0, 0, 1)
    gradient.setColorAt(0.0, _BG_TOP)
    gradient.setColorAt(1.0, _BG_BOTTOM)
    p.setBrush(QBrush(gradient))
    p.setPen(Qt.NoPen if small else QPen(_BORDER, 0.012))
    radius = 0.20
    p.drawRoundedRect(plate, radius, radius)

    centre = QPointF(0.5, 0.5)

    # Soft cyan glow behind the ring.
    if not tiny:
        glow = QRadialGradient(centre, 0.46)
        glow_colour = QColor(_CYAN)
        glow_colour.setAlpha(70)
        glow.setColorAt(0.0, glow_colour)
        glow_colour.setAlpha(0)
        glow.setColorAt(1.0, glow_colour)
        p.setBrush(QBrush(glow))
        p.setPen(Qt.NoPen)
        p.drawEllipse(centre, 0.46, 0.46)

    # Hairline outer ring (only where there are enough pixels to show it).
    if size >= 48:
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(_CYAN_DIM, 0.008))
        p.drawEllipse(centre, 0.385, 0.385)

    # Main ring: three arcs with gaps, like an open orbit.
    ring_radius = 0.30 if not small else 0.31
    ring_width = 0.062 if not small else (0.095 if not tiny else 0.12)
    pen = QPen(_CYAN, ring_width)
    pen.setCapStyle(Qt.RoundCap if not tiny else Qt.FlatCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    ring_rect = QRectF(
        centre.x() - ring_radius, centre.y() - ring_radius, ring_radius * 2, ring_radius * 2
    )
    sweep = 92  # degrees drawn per arc (the gaps take the other 28)
    for k in range(3):
        start = 90 + 120 * k + 10  # first arc starts just left of the top
        p.drawArc(ring_rect, int(start * 16), int(sweep * 16))

    # The gem: a faceted rhombus in Orokin gold.
    half_w = 0.170 if not small else 0.190
    half_h = 0.230 if not small else 0.255
    top = QPointF(0.5, 0.5 - half_h)
    right = QPointF(0.5 + half_w, 0.5)
    bottom = QPointF(0.5, 0.5 + half_h)
    left = QPointF(0.5 - half_w, 0.5)
    gem = QPolygonF([top, right, bottom, left])
    body = QLinearGradient(left, right)
    body.setColorAt(0.0, _GOLD_LIGHT)
    body.setColorAt(0.55, _GOLD)
    body.setColorAt(1.0, _GOLD_DARK)
    p.setBrush(QBrush(body))
    p.setPen(Qt.NoPen)
    p.drawPolygon(gem)

    if not tiny:
        # Upper-left facet, lighter; lower-right facet, darker.
        facet_light = QColor(255, 255, 255, 95)
        p.setBrush(facet_light)
        p.drawPolygon(QPolygonF([top, centre, left]))
        facet_dark = QColor(0, 0, 0, 70)
        p.setBrush(facet_dark)
        p.drawPolygon(QPolygonF([bottom, centre, right]))
        if not small:
            # Crisp edge lines between the facets.
            p.setPen(QPen(QColor(255, 244, 205, 150), 0.006))
            p.drawLine(top, centre)
            p.drawLine(left, centre)
            p.drawLine(right, centre)
            p.drawLine(bottom, centre)
            # A small specular spark on the top-left facet.
            spark = QPainterPath()
            spark.addEllipse(QPointF(0.452, 0.385), 0.017, 0.017)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 230))
            p.drawPath(spark)

    p.end()
    return img


def build_app_icon() -> QIcon:
    """A QIcon with every size in ICON_SIZES, so Qt/Windows pick a crisp one."""
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(render_icon(size)))
    return icon
