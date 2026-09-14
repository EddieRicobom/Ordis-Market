"""
cache.cache_store
==================

PriceCache: a small TTL-based JSON disk cache for market order data, so
Ordis Market can run in offline mode using the last known prices.

Ordis: "I forget nothing. I am, medically speaking, incapable of it."
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional


class PriceCache:
    def __init__(self, storage_dir: Path, ttl_seconds: int) -> None:
        self._storage_dir = storage_dir
        self._ttl_seconds = ttl_seconds
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return self._storage_dir / f"{safe_key}.json"

    def get(self, key: str, ignore_ttl: bool = False) -> Optional[Any]:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        stored_at = payload.get("stored_at", 0)
        if not ignore_ttl and (time.time() - stored_at) > self._ttl_seconds:
            return None
        return payload.get("value")

    def get_stale(self, key: str) -> Optional[Any]:
        """Return the cached value even if expired -- used for offline mode."""
        return self.get(key, ignore_ttl=True)

    def set(self, key: str, value: Any) -> None:
        path = self._path_for(key)
        payload = {"stored_at": time.time(), "value": value}
        path.write_text(json.dumps(payload), encoding="utf-8")

    def age_seconds(self, key: str) -> Optional[float]:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return time.time() - payload.get("stored_at", 0)
