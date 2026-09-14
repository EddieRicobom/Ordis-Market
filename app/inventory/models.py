"""
inventory.models
=================

Normalized, source-agnostic inventory data structures.

These models are intentionally decoupled from whatever file format the
Operator imports (a hand-written JSON list, a warframe-api-helper export,
a browse.wf export, etc.). Whatever comes in, it becomes an InventoryItem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class InventoryItem:
    """A single owned stack of an item.

    item_id:
        Best-effort stable identifier for the item as found in the import
        file (could be a Warframe internal unique name, a warframe.market
        slug, or a display name if nothing better is available -- see
        InventoryParser for the resolution order).
    quantity:
        How many the Operator owns.
    raw_name:
        The original name/label found in the source file, kept for display
        and for later catalog matching even if item_id resolution fails.
    source_field:
        Which field of the source record we used to derive item_id, for
        debugging traceability ("unique_name", "url_name", "name", ...).
    game_ref:
        The untouched, original Warframe internal path (e.g.
        '/Lotus/Weapons/Tenno/LongGuns/TnWispRifle/TnWispRifle') when the
        source record was keyed by 'ItemType' -- unlike item_id, this is
        NOT lowercased or trimmed to a single path segment, since matching
        it against warframe.market's own 'gameRef' field requires the
        exact original string. None for records that didn't come from an
        ItemType-style field.
    mod_rank:
        The mod's fusion rank (0 = unranked/unfused), when this item is a
        mod. None for non-mod items. Two copies of the *same* mod at
        *different* ranks are deliberately different InventoryItem
        entries (different item_id, different mod_rank) rather than being
        merged into one stack -- their market value differs enormously by
        rank, so collapsing them together would silently average away
        real information. Same-mod-same-rank copies still merge normally.
    """

    item_id: str
    quantity: int
    raw_name: str
    source_field: str = "name"
    game_ref: Optional[str] = None
    mod_rank: Optional[int] = None


@dataclass(frozen=True)
class InventorySnapshot:
    """The result of a single import operation."""

    items: tuple[InventoryItem, ...]
    imported_at: datetime
    source_path: str
    unresolved_count: int = 0

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def total_quantity(self) -> int:
        return sum(i.quantity for i in self.items)
