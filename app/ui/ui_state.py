"""
ui.ui_state
===========

Remembers how the Operator left the window -- size and position, the Market
filters and the table sort -- in data/ui_state.json, next to the other
persisted files. Never fatal: a missing, unreadable or odd file just means
"start with the defaults".
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.common.files import atomic_write_text

logger = logging.getLogger("ordis_market.ui")


class UiStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, state: dict[str, Any]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self._path, json.dumps(state, indent=2))
        except OSError as exc:  # a read-only folder must not stop the app closing
            logger.warning("Could not save the window state: %s", exc)
