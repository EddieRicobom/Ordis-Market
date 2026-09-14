"""
inventory.repository
=====================

Keeps the currently-loaded inventory in memory and persists it to disk so
the Operator doesn't have to re-import every launch.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.inventory.models import InventoryItem, InventorySnapshot


class InventoryRepository:
    """Stores the last-imported inventory snapshot.

    Ordis: "I keep your inventory in a little box. A metaphorical box.
            Please do not ask where the box is."
    """

    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._snapshot: Optional[InventorySnapshot] = None

    @property
    def snapshot(self) -> Optional[InventorySnapshot]:
        return self._snapshot

    def save(self, snapshot: InventorySnapshot) -> None:
        self._snapshot = snapshot
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "imported_at": snapshot.imported_at.isoformat(),
            "source_path": snapshot.source_path,
            "unresolved_count": snapshot.unresolved_count,
            "items": [
                {
                    "item_id": item.item_id,
                    "quantity": item.quantity,
                    "raw_name": item.raw_name,
                    "source_field": item.source_field,
                    "game_ref": item.game_ref,
                    "mod_rank": item.mod_rank,
                }
                for item in snapshot.items
            ],
        }
        self._storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> Optional[InventorySnapshot]:
        if not self._storage_path.exists():
            return None
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        items = tuple(
            InventoryItem(
                item_id=i["item_id"],
                quantity=int(i["quantity"]),
                raw_name=i.get("raw_name", i["item_id"]),
                source_field=i.get("source_field", "name"),
                game_ref=i.get("game_ref"),
                mod_rank=i.get("mod_rank"),
            )
            for i in payload.get("items", [])
        )
        try:
            imported_at = datetime.fromisoformat(payload["imported_at"])
        except (KeyError, ValueError):
            imported_at = datetime.now(timezone.utc)

        snapshot = InventorySnapshot(
            items=items,
            imported_at=imported_at,
            source_path=payload.get("source_path", "unknown"),
            unresolved_count=int(payload.get("unresolved_count", 0)),
        )
        self._snapshot = snapshot
        return snapshot
