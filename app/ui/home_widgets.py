"""
ui.home_widgets
===============

Custom-painted building blocks for the Home tab: an animated holographic
emblem, HUD-style cards with corner brackets, and the timeline strip.
Everything is drawn with QPainter (no image assets).

The emblem is an original abstract design (rings, ticks and a watching
aperture), not a depiction of any character.

Ordis: "I have been given a face made of light and arithmetic. I find it
        flattering. Possibly too flattering."
"""

from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from app.home.schedule import EventKind, TimelineEvent, format_countdown
from app.ui.theme import (
    ACCENT_CYAN,
    ACCENT_CYAN_DIM,
    ACCENT_GOLD,
    BG_BASE,
    BG_PANEL,
    BG_PANEL_ALT,
    BORDER,
    DANGER,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

LEVEL_COLORS = {"good": ACCENT_GOLD, "info": ACCENT_CYAN, "warn": DANGER}
KIND_COLORS = {EventKind.BARO: ACCENT_GOLD, EventKind.RESURGENCE: ACCENT_CYAN, EventKind.RESET: TEXT_MUTED}


def styled_label(
    text: str = "",
    size_pt: float = 10,
    color: str = TEXT_PRIMARY,
    weight: int = 400,
    spacing: float = 0,
    italic: bool = False,
    wrap: bool = False,
) -> QLabel:
    """A label with a transparent background (so it sits on a card, not on the
    page colour the global stylesheet gives every QWidget)."""
    label = QLabel(text)
    label.setWordWrap(wrap)
    label.setStyleSheet(
        f"background: transparent; color: {color}; font-size: {size_pt}pt; font-weight: {weight};"
        f"letter-spacing: {spacing}px; font-style: {'italic' if italic else 'normal'};"
    )
    return label


def _color(hex_code: str, alpha: int = 255) -> QColor:
    colour = QColor(hex_code)
    colour.setAlpha(alpha)
    return colour


def add_glow(widget: QWidget, hex_code: str, radius: int = 18, alpha: int = 150) -> None:
    """Soft bloom around a label, like light bleeding off a projection."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(radius)
    effect.setOffset(0, 0)
    effect.setColor(_color(hex_code, alpha))
    widget.setGraphicsEffect(effect)


class HologramCore(QWidget):
    """Holographic emblem: a projection base with a light beam, rotating arcs, a
    tick ring, a breathing core and a drifting aperture. Now and then it
    flickers and splits into red/cyan fringes for a split second, like an
    unstable projection. Animates only while visible, and not at all when
    animations are off."""

    FRAME_MS = 33
    BASE_H = 16  # room under the emblem for the projector

    def __init__(self, size: int = 138, animated: bool = True, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._t = 0.0
        self._animated = animated
        self._rng = random.Random(7)
        self._next_glitch = 3.0
        self._glitch_until = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._advance)

    def set_animated(self, animated: bool) -> None:
        self._animated = animated
        if animated and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()
            self._glitch_until = 0.0
        self.update()

    def _advance(self) -> None:
        self._t += self.FRAME_MS / 1000.0
        if self._t >= self._next_glitch:
            self._glitch_until = self._t + 0.16
            self._next_glitch = self._t + self._rng.uniform(4.0, 9.0)
        self.update()

    def glitching(self) -> bool:
        return self._animated and self._t < self._glitch_until

    def showEvent(self, event) -> None:  # noqa: N802
        if self._animated:
            self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def _geometry(self) -> tuple[QPointF, float]:
        area_h = self.height() - self.BASE_H
        return QPointF(self.width() / 2, area_h / 2 + 2), min(self.width(), area_h) / 2 - 4

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        c, radius = self._geometry()
        self._paint_projector(painter, c, radius)
        if not self.glitching():
            self._paint_emblem(painter, c, radius)
            return

        # Unstable frame: draw the emblem to an image, then composite it with
        # red / cyan fringes and a few sliced, shifted strips.
        image = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        inner = QPainter(image)
        inner.setRenderHint(QPainter.Antialiasing, True)
        self._paint_emblem(inner, c, radius)
        inner.end()

        def tinted(colour: QColor) -> QImage:
            copy = QImage(image)
            tint = QPainter(copy)
            tint.setCompositionMode(QPainter.CompositionMode_SourceIn)
            tint.fillRect(copy.rect(), colour)
            tint.end()
            return copy

        painter.setOpacity(0.55)
        painter.drawImage(QPointF(-2.5, 0), tinted(QColor(255, 70, 110)))
        painter.drawImage(QPointF(2.5, 0), tinted(QColor(60, 230, 255)))
        painter.setOpacity(0.85)
        strip = self._rng.randint(8, 18)
        y = 0
        while y < image.height():
            shift = self._rng.choice((-3, 0, 0, 3)) if self._rng.random() < 0.35 else 0
            painter.drawImage(QPointF(shift, y), image, QRectF(0, y, image.width(), strip))
            y += strip

    def _paint_projector(self, painter: QPainter, c: QPointF, radius: float) -> None:
        """Emitter disc under the emblem and the faint cone of light above it."""
        base_y = self.height() - self.BASE_H / 2 - 1
        base_w = radius * 1.35
        beam = QLinearGradient(0, base_y, 0, c.y())
        beam.setColorAt(0.0, _color(ACCENT_CYAN, 70))
        beam.setColorAt(1.0, _color(ACCENT_CYAN, 0))
        cone = QPolygonF([
            QPointF(c.x() - base_w * 0.5, base_y),
            QPointF(c.x() + base_w * 0.5, base_y),
            QPointF(c.x() + radius * 0.62, c.y()),
            QPointF(c.x() - radius * 0.62, c.y()),
        ])
        painter.setPen(Qt.NoPen)
        painter.setBrush(beam)
        painter.drawPolygon(cone)
        for scale, alpha in ((1.0, 200), (0.66, 120), (0.33, 90)):
            painter.setPen(QPen(_color(ACCENT_CYAN, alpha), 1.2))
            painter.setBrush(_color(ACCENT_CYAN, 28 if scale == 1.0 else 0))
            painter.drawEllipse(QPointF(c.x(), base_y), base_w * scale / 2, 4.5 * scale)

    def _paint_emblem(self, painter: QPainter, c: QPointF, radius: float) -> None:
        t = self._t
        painter.setOpacity(1.0)

        # tick ring
        for i in range(60):
            major = i % 5 == 0
            angle = math.radians(i * 6)
            outer, inner = radius, radius - (8 if major else 4)
            painter.setPen(QPen(_color(ACCENT_GOLD if major else ACCENT_CYAN_DIM, 230 if major else 140), 1.4 if major else 1))
            painter.drawLine(
                QPointF(c.x() + outer * math.cos(angle), c.y() + outer * math.sin(angle)),
                QPointF(c.x() + inner * math.cos(angle), c.y() + inner * math.sin(angle)),
            )

        # rotating arcs
        arc_rect = QRectF(c.x() - (radius - 13), c.y() - (radius - 13), 2 * (radius - 13), 2 * (radius - 13))
        painter.setPen(QPen(_color(ACCENT_CYAN, 220), 2.2, Qt.SolidLine, Qt.RoundCap))
        for k in range(3):
            start = (t * 38 + k * 120) % 360
            painter.drawArc(arc_rect, int(-start * 16), int(-62 * 16))

        # counter-rotating dashed ring
        dashed = QPen(_color(ACCENT_CYAN_DIM, 200), 1.2, Qt.CustomDashLine)
        dashed.setDashPattern([2.0, 4.0])
        dashed.setDashOffset(-t * 6)
        painter.setPen(dashed)
        ring = radius * 0.7
        painter.drawEllipse(c, ring, ring)

        # core glow
        core = radius * 0.44 * (1 + 0.035 * math.sin(t * 2.1))
        glow = QRadialGradient(c, core * 1.6)
        glow.setColorAt(0.0, _color("#e9fffc", 235))
        glow.setColorAt(0.35, _color(ACCENT_CYAN, 190))
        glow.setColorAt(0.7, _color(ACCENT_CYAN, 50))
        glow.setColorAt(1.0, _color(ACCENT_CYAN, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(c, core * 1.6, core * 1.6)

        # aperture + pupil + scanline, clipped to the core disc
        disc = QPainterPath()
        disc.addEllipse(c, core, core)
        painter.save()
        painter.setClipPath(disc)
        painter.setBrush(_color(BG_BASE, 215))
        painter.drawEllipse(c, core * 1.15, core * 0.34)
        pupil_x = math.sin(t * 0.7) * core * 0.3
        painter.setBrush(_color("#e9fffc", 255))
        painter.drawEllipse(QPointF(c.x() + pupil_x, c.y()), core * 0.17, core * 0.17)
        scan_y = c.y() - core + ((t * 0.55) % 1.0) * 2 * core
        painter.setPen(QPen(_color("#ffffff", 70), 1))
        painter.drawLine(QPointF(c.x() - core, scan_y), QPointF(c.x() + core, scan_y))
        painter.restore()

        # orbiting markers
        painter.setPen(Qt.NoPen)
        painter.setBrush(_color(ACCENT_GOLD, 240))
        for k in range(3):
            angle = t * 0.85 + k * 2 * math.pi / 3
            painter.drawEllipse(
                QPointF(c.x() + radius * 0.56 * math.cos(angle), c.y() + radius * 0.56 * math.sin(angle)), 2.6, 2.6
            )


class HoloOverlay(QWidget):
    """Transparent layer on top of a card: static scanlines, plus a soft band of
    light that sweeps across now and then. Never takes mouse input."""

    SWEEP_MS = 1100
    FRAME_MS = 40
    _tile: Optional[QPixmap] = None

    def __init__(self, card: QWidget, accent: str, animated: bool = True) -> None:
        super().__init__(card)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._accent = accent
        self._animated = animated
        self._progress: Optional[float] = None
        self._rng = random.Random()
        self._idle = QTimer(self)
        self._idle.setSingleShot(True)
        self._idle.timeout.connect(self._start_sweep)
        self._frames = QTimer(self)
        self._frames.setInterval(self.FRAME_MS)
        self._frames.timeout.connect(self._step)

    @classmethod
    def _scanlines(cls) -> QPixmap:
        if cls._tile is None:
            tile = QPixmap(1, 3)
            tile.fill(Qt.transparent)
            painter = QPainter(tile)
            painter.fillRect(0, 0, 1, 1, QColor(0, 0, 0, 38))
            painter.end()
            cls._tile = tile
        return cls._tile

    def set_animated(self, animated: bool) -> None:
        self._animated = animated
        self._idle.stop()
        self._frames.stop()
        self._progress = None
        if animated and self.isVisible():
            self._schedule()
        self.update()

    def _schedule(self) -> None:
        self._idle.start(self._rng.randint(3500, 9000))

    def _start_sweep(self) -> None:
        self._progress = 0.0
        self._frames.start()

    def _step(self) -> None:
        assert self._progress is not None
        self._progress += self.FRAME_MS / self.SWEEP_MS
        if self._progress >= 1.0:
            self._progress = None
            self._frames.stop()
            self._schedule()
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        if self._animated and not self._idle.isActive() and not self._frames.isActive():
            self._schedule()
        super().showEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._idle.stop()
        self._frames.stop()
        self._progress = None
        super().hideEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QBrush(self._scanlines()))
        if self._progress is None:
            return
        w, h = self.width(), self.height()
        x = -0.25 * w + self._progress * 1.5 * w
        band = QLinearGradient(x - 70, 0, x + 70, 0)
        band.setColorAt(0.0, _color(self._accent, 0))
        band.setColorAt(0.5, _color(self._accent, 46))
        band.setColorAt(1.0, _color(self._accent, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(band)
        painter.drawPolygon(QPolygonF([QPointF(x - 70 + 24, 0), QPointF(x + 70 + 24, 0), QPointF(x + 70 - 24, h), QPointF(x - 70 - 24, h)]))


class HudCard(QFrame):
    """Dark panel with HUD corner brackets and an optional small-caps title.
    Subclass or add widgets through `body`."""

    clicked = Signal(object)

    def __init__(
        self,
        title: str = "",
        accent: str = ACCENT_CYAN,
        target=None,
        parent: Optional[QWidget] = None,
        animated: bool = True,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self._target = target
        self._hover = False
        self.holo = HoloOverlay(self, accent, animated)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 12, 16, 12)
        self.body.setSpacing(4)
        self.title_label: Optional[QLabel] = None
        if title:
            self.title_label = styled_label(title.upper(), 8, TEXT_MUTED, 600, 1.6)
            self.body.addWidget(self.title_label)
        if target is not None:
            self.setCursor(QCursor(Qt.PointingHandCursor))

    def set_animated(self, animated: bool) -> None:
        self.holo.set_animated(animated)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self.holo.setGeometry(self.rect())
        self.holo.raise_()  # keep the overlay above the labels added after it
        super().resizeEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        self.holo.setGeometry(self.rect())
        self.holo.raise_()
        super().showEvent(event)

    def set_target(self, target) -> None:
        self._target = target
        self.setCursor(QCursor(Qt.PointingHandCursor) if target is not None else QCursor(Qt.ArrowCursor))
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = self._target is not None
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._target is not None and event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self._target)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.fillRect(rect, _color(BG_PANEL_ALT if self._hover else BG_PANEL))
        painter.setPen(QPen(_color(BORDER), 1))
        painter.drawRect(rect)
        bracket = 10
        painter.setPen(QPen(_color(self._accent, 255 if self._hover else 190), 2))
        left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
        for x, y, dx, dy in ((left, top, 1, 1), (right, top, -1, 1), (left, bottom, 1, -1), (right, bottom, -1, -1)):
            painter.drawLine(x, y, x + dx * bracket, y)
            painter.drawLine(x, y, x, y + dy * bracket)


class MiniBar(QWidget):
    """Thin progress bar (0..1) used for the Baro stay and the Resurgence cycle."""

    def __init__(self, color: str = ACCENT_CYAN, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._color = color
        self._fraction = 0.0
        self.setFixedHeight(6)

    def set_fraction(self, fraction: float) -> None:
        self._fraction = max(0.0, min(1.0, fraction))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), _color(BORDER))
        width = int(self.width() * self._fraction)
        painter.fillRect(0, 0, width, self.height(), _color(self._color))


class StatCard(HudCard):
    """Big number + caption. Clickable when it has a target."""

    def __init__(self, title: str, accent: str = ACCENT_CYAN, target=None, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, accent, target, parent)
        self.setMinimumWidth(150)
        self.value_label = styled_label("-", 22, accent, 700)
        add_glow(self.value_label, accent)
        self.caption_label = styled_label("", 9, TEXT_PRIMARY)
        self.hint_label = styled_label("", 8, TEXT_MUTED, wrap=True)
        self.body.addWidget(self.value_label)
        self.body.addWidget(self.caption_label)
        self.body.addWidget(self.hint_label)
        self.body.addStretch(1)

    def set_content(self, value: str, caption: str = "", hint: str = "", muted: bool = False) -> None:
        colour = TEXT_MUTED if muted else self._accent
        self.value_label.setStyleSheet(
            f"background: transparent; color: {colour}; font-size: 22pt; font-weight: 700;"
        )
        self.value_label.setText(value)
        self.caption_label.setText(caption)
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))


class AttentionRow(QFrame):
    """One line in "What needs attention": a coloured marker, text, detail."""

    clicked = Signal(object)

    def __init__(self, level: str, text: str, detail: str, target, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._level = level
        self._target = target
        self._hover = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 5, 10, 5)
        layout.setSpacing(0)
        layout.addWidget(styled_label(text, 10, TEXT_PRIMARY, 600))
        layout.addWidget(styled_label(detail, 8, TEXT_MUTED))
        if target is not None:
            self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip(detail + ("  (click to open)" if target is not None else ""))

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = self._target is not None
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._target is not None and event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self._target)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if self._hover:
            painter.fillRect(self.rect(), _color(BG_BASE))
        colour = _color(LEVEL_COLORS.get(self._level, ACCENT_CYAN))
        painter.setPen(Qt.NoPen)
        painter.setBrush(colour)
        cy = self.height() / 2
        diamond = QPainterPath()
        diamond.moveTo(11, cy - 5)
        diamond.lineTo(16, cy)
        diamond.lineTo(11, cy + 5)
        diamond.lineTo(6, cy)
        diamond.closeSubpath()
        painter.drawPath(diamond)
        if self._target is not None:
            painter.setPen(QPen(_color(TEXT_MUTED), 1.6))
            x = self.width() - 14
            painter.drawLine(QPointF(x, cy - 4), QPointF(x + 4, cy))
            painter.drawLine(QPointF(x + 4, cy), QPointF(x, cy + 4))


class TimelineStrip(QWidget):
    """"Today -> next events" drawn as nodes on a line, evenly spaced (it is a
    sequence, not a to-scale calendar)."""

    FRAME_MS = 50

    def __init__(self, parent: Optional[QWidget] = None, animated: bool = True) -> None:
        super().__init__(parent)
        self._now: Optional[datetime] = None
        self._events: list[TimelineEvent] = []
        self._animated = animated
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._advance)
        self.setMinimumHeight(92)

    def set_animated(self, animated: bool) -> None:
        self._animated = animated
        if animated and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _advance(self) -> None:
        self._phase += self.FRAME_MS / 1000.0
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802
        if self._animated:
            self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def set_events(self, now: datetime, events: list[TimelineEvent]) -> None:
        self._now = now
        self._events = events
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._now is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        nodes = [("TODAY", self._now, ACCENT_CYAN)] + [(e.label, e.when, KIND_COLORS[e.kind]) for e in self._events]
        count = len(nodes)
        margin = 100
        line_y = 30
        usable = max(self.width() - 2 * margin, 1)
        xs = [margin + usable * i / max(count - 1, 1) for i in range(count)]

        painter.setPen(QPen(_color(BORDER), 2))
        painter.drawLine(QPointF(xs[0], line_y), QPointF(xs[-1], line_y))
        painter.setPen(QPen(_color(ACCENT_CYAN_DIM), 2))
        if count > 1:
            painter.drawLine(QPointF(xs[0], line_y), QPointF(xs[1], line_y))
            if self._animated:  # a light travelling from today toward the next event
                travel = (self._phase % 3.0) / 3.0
                head = xs[0] + (xs[1] - xs[0]) * travel
                glow = QRadialGradient(QPointF(head, line_y), 9)
                glow.setColorAt(0.0, _color("#e9fffc", 230))
                glow.setColorAt(1.0, _color(ACCENT_CYAN, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(QPointF(head, line_y), 9, 9)
        if self._animated:  # pulse ring around "today"
            pulse = (self._phase % 1.8) / 1.8
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(_color(ACCENT_CYAN, int(190 * (1 - pulse))), 1.4))
            painter.drawEllipse(QPointF(xs[0], line_y), 6 + 12 * pulse, 6 + 12 * pulse)

        name_font = QFont(self.font())
        name_font.setPointSizeF(8)
        name_font.setBold(True)
        name_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
        small_font = QFont(self.font())
        small_font.setPointSizeF(8)
        for index, (label, when, hex_code) in enumerate(nodes):
            x = xs[index]
            painter.setPen(QPen(_color(hex_code), 2))
            painter.setBrush(_color(BG_BASE if index else hex_code))
            painter.drawEllipse(QPointF(x, line_y), 6, 6)
            half = min(usable / max(count - 1, 1), 200) / 2
            box = QRectF(x - half, line_y + 12, 2 * half, 16)
            painter.setFont(name_font)
            painter.setPen(_color(hex_code if index else TEXT_PRIMARY))
            painter.drawText(box, Qt.AlignHCenter | Qt.AlignVCenter, label.upper())
            painter.setFont(small_font)
            painter.setPen(_color(TEXT_MUTED))
            if index == 0:
                lines = [when.astimezone().strftime("%a %d %b, %H:%M")]
            else:
                lines = [when.astimezone().strftime("%a %d %b, %H:%M"), "in " + format_countdown(when - self._now)]
            for n, text in enumerate(lines):
                painter.drawText(QRectF(x - half, line_y + 28 + n * 15, 2 * half, 15), Qt.AlignHCenter | Qt.AlignVCenter, text)


Clock = Callable[[], datetime]
