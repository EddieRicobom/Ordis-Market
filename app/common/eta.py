"""
common.eta
==========

Time-remaining estimate for long jobs (the market refresh runs for minutes at
warframe.market's 3 requests/second). No Qt in here.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable, Optional

MIN_SPAN_SECONDS = 3.0
"""Progress has to have been observed for at least this long before a rate is
trusted; a single burst of cache hits would otherwise promise a finish in
seconds."""

MIN_REMAINING_SECONDS = 5.0
"""Below this the estimate is not worth showing."""


class EtaEstimator:
    """Estimates the seconds left from the progress made in a sliding window of
    recent time. Looking only at the recent past (instead of the whole run)
    keeps the early instant steps -- items that need no network call, cache
    hits -- from making the rest of the run look faster than it is."""

    def __init__(self, window_seconds: float = 20.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._window = window_seconds
        self._clock = clock
        self._samples: deque[tuple[float, int]] = deque()

    def reset(self) -> None:
        self._samples.clear()

    def update(self, done: int, total: int) -> Optional[float]:
        """Records progress and returns the estimated seconds remaining, or
        None while there is not enough to go on (or nothing worth showing)."""
        now = self._clock()
        self._samples.append((now, done))
        # Keep one sample older than the window so the window is always fully spanned.
        while len(self._samples) > 2 and self._samples[1][0] <= now - self._window:
            self._samples.popleft()

        oldest_time, oldest_done = self._samples[0]
        span = now - oldest_time
        gained = done - oldest_done
        remaining_items = total - done
        if remaining_items <= 0 or span < MIN_SPAN_SECONDS or gained <= 0:
            return None
        remaining = remaining_items / (gained / span)
        return remaining if remaining >= MIN_REMAINING_SECONDS else None


def format_eta(seconds: Optional[float]) -> str:
    """'~45 s', '~3 min', '~1 h 05 min'; '' when there is no estimate."""
    if seconds is None:
        return ""
    if seconds < 60:
        return f"~{max(5, int(round(seconds / 5.0)) * 5)} s"
    minutes = int(-(-seconds // 60))  # ceil: better to under-promise
    if minutes < 60:
        return f"~{minutes} min"
    hours, minutes = divmod(minutes, 60)
    return f"~{hours} h {minutes:02d} min"
