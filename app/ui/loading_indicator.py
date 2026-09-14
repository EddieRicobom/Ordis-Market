"""
ui.loading_indicator
=====================

A small, Warframe-flavored "still working" indicator: a rotating ring of
tick marks (evocative of the Orokin scanning/loading motifs seen
throughout Warframe's UI) drawn entirely with QPainter -- no image or GIF
assets involved -- paired with a status label that cycles through an
Ordis message pool periodically.

Ordis: "Behold, a spinning ring of light. It means I am working. Or that
        I am having a small crisis. The two look remarkably similar."

This is a supplement to, not a replacement for, the existing percentage
QProgressBar: long operations (analysis, catalog refresh) show both --
the progress bar for concrete numeric progress where available, and this
indicator so the screen still feels alive when progress isn't granular
(e.g. a single bulk catalog fetch with no per-item percentage).
"""

from __future__ import annotations

import math
import random
from typing import List, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui.theme import ACCENT_CYAN


class OrokinSpinner(QWidget):
    """A rotating ring of fading tick marks. Pure QPainter, no assets."""

    TICK_COUNT = 12
    ROTATION_STEP_DEGREES = 8
    FRAME_INTERVAL_MS = 45

    def __init__(self, parent: Optional[QWidget] = None, diameter: int = 20) -> None:
        super().__init__(parent)
        self._diameter = diameter
        self.setFixedSize(diameter, diameter)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_INTERVAL_MS)
        self._timer.timeout.connect(self._advance)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _advance(self) -> None:
        self._angle = (self._angle + self.ROTATION_STEP_DEGREES) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        center = self.rect().center()
        radius = (self._diameter / 2) - 3

        for i in range(self.TICK_COUNT):
            tick_angle = math.radians(self._angle + (360 / self.TICK_COUNT) * i)
            fade = i / self.TICK_COUNT
            color = QColor(ACCENT_CYAN)
            color.setAlphaF(0.15 + 0.85 * (1 - fade))
            pen = QPen(color)
            pen.setWidthF(2.0)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)

            x1 = center.x() + radius * 0.55 * math.cos(tick_angle)
            y1 = center.y() + radius * 0.55 * math.sin(tick_angle)
            x2 = center.x() + radius * math.cos(tick_angle)
            y2 = center.y() + radius * math.sin(tick_angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.end()


class LoadingIndicator(QWidget):
    """Spinner + a status label that cycles through a message pool.

    Usage::

        self.loading_indicator.start(ordis.ANALYSIS_START + ordis.PROCESSING_FLAVOR)
        ...
        self.loading_indicator.stop()
    """

    DEFAULT_INTERVAL_MS = 3200

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._spinner = OrokinSpinner(self)
        self._label = QLabel("")
        self._label.setObjectName("LoadingLabel")

        layout.addWidget(self._spinner)
        layout.addWidget(self._label, stretch=1)

        self._pool: List[str] = []
        self._message_timer = QTimer(self)
        self._message_timer.timeout.connect(self._cycle_message)

        self.hide()

    def start(self, message_pool: List[str], interval_ms: int = DEFAULT_INTERVAL_MS) -> None:
        self._pool = list(message_pool) if message_pool else ["Working..."]
        self._cycle_message()
        self._message_timer.start(interval_ms)
        self._spinner.start()
        self.show()

    def stop(self) -> None:
        self._message_timer.stop()
        self._spinner.stop()
        self.hide()

    def _cycle_message(self) -> None:
        if self._pool:
            self._label.setText(random.choice(self._pool))
