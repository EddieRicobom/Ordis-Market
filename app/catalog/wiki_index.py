"""
catalog.wiki_index
===================

Stores the item display name -> Warframe Wiki URL lookup, so the same
name is never looked up twice across sessions.

Ordis: "Once I know where something lives on the Wiki, I do not forget.
        Unlike some things, I choose to remember this."
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class WikiIndex:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._entries: dict[str, str] = {}  # name -> url
        self._unresolved: set[str] = set()  # names we already tried and found nothing for

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, name: str) -> Optional[str]:
        return self._entries.get(name)

    def has_been_attempted(self, name: str) -> bool:
        """True if we've already tried (successfully or not) to resolve
        this name, so the builder doesn't keep re-querying known misses
        on every refresh."""
        return name in self._entries or name in self._unresolved

    def set_resolved(self, name: str, url: str) -> None:
        self._entries[name] = url
        self._unresolved.discard(name)

    def set_unresolved(self, name: str) -> None:
        if name not in self._entries:
            self._unresolved.add(name)

    def save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"resolved": self._entries, "unresolved": sorted(self._unresolved)}
        self._storage_path.write_text(json.dumps(payload), encoding="utf-8")

    def load_from_disk(self) -> bool:
        if not self._storage_path.exists():
            return False
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        self._entries = dict(payload.get("resolved", {}))
        self._unresolved = set(payload.get("unresolved", []))
        return True
