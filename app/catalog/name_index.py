"""
catalog.name_index
===================

Stores the uniqueName -> display name lookup fetched from Digital
Extremes' Public Export (see warframe_export.py), with disk caching so it
isn't re-downloaded every launch.

Ordis: "A dictionary, Operator. Just a dictionary. I know, I was hoping
        for something more dramatic too."
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class NameIndex:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._entries: dict[str, str] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, unique_name: str) -> Optional[str]:
        return self._entries.get(unique_name)

    def load_from_pairs(self, pairs: dict[str, str]) -> int:
        self._entries = dict(pairs)
        return len(self._entries)

    def save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(json.dumps(self._entries), encoding="utf-8")

    def load_from_disk(self) -> bool:
        if not self._storage_path.exists():
            return False
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        self._entries = payload
        return True
