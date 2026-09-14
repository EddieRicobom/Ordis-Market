"""
common.rate_limiter
====================

A simple token-bucket limiter enforcing N requests/second, shared by any
HTTP client in this project that needs to be polite to a third-party
service (warframe.market, the Warframe Wiki's MediaWiki API, ...).

Ordis: "Think of it as me counting to myself before I speak again."
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / max(requests_per_second, 0.001)
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            remaining = self._min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_call = time.monotonic()
