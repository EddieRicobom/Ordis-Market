"""
inventory.parser
=================

Parses a manually-provided inventory export into normalized
InventoryItem records.

Ordis: "I do not reach into the game's memory, Operator. That would be
        rude, unreliable, and almost certainly against someone's rules.
        I simply read the file you hand me. Like a civilized Cephalon."

SUPPORTED INPUT SHAPES
-----------------------
This parser accepts JSON files and tries several common shapes, because
"the current inventory export format" is a moving target across community
tools (see RESEARCH.md). It does NOT talk to the Warframe process, the
network, or any overlay tool -- it only reads bytes from disk.

1. Ordis Market's own normalized format::

    {"items": [{"item_id": "mesa_prime_neuroptics", "quantity": 3}, ...]}

2. A generic "name + quantity" export (many hand-rolled tools use this)::

    [{"name": "Mesa Prime Neuroptics", "quantity": 3}, ...]

3. warframe-api-helper / mobile-API-style inventory dumps, which nest
   typed arrays such as "Suits", "LongGuns", "Pistols", "Melee",
   "MiscItems", "Recipes", etc., each containing objects with an
   "ItemType" (internal unique name, e.g. "/Lotus/Powersuits/..."),
   plus an "ItemCount" or "ItemsSold"-style count field.

If a record cannot be resolved to *any* identifiable name/id and quantity
pair, it is skipped and counted in `unresolved_count` rather than crashing
the whole import -- Ordis would rather report a partial success than
refuse to help entirely.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from app.inventory.models import InventoryItem, InventorySnapshot


class InventoryFileNotFoundError(FileNotFoundError):
    """Raised when the given path does not exist."""


class InvalidInventoryFileError(ValueError):
    """Raised when the file exists but cannot be parsed as an inventory."""


# Keys we will try, in order, when looking for a "name-ish" field.
_NAME_KEYS = ("name", "item_name", "ItemType", "item_id", "url_name", "slug", "uniqueName")
# Keys we will try, in order, when looking for a "quantity-ish" field.
_QTY_KEYS = ("quantity", "count", "ItemCount", "qty", "amount")

# Nested arrays used by mobile-API-style / warframe-api-helper-style exports.
_KNOWN_NESTED_KEYS = (
    "Suits",
    "LongGuns",
    "Pistols",
    "Melee",
    "SpaceSuits",
    "SpaceGuns",
    "SpaceMelee",
    "MiscItems",
    "Recipes",
    "Mods",
    "RawUpgrades",
)


def _first_present(record: dict, keys: Iterable[str]) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def _clean_item_type(raw: str) -> str:
    """Turn a Warframe internal path like '/Lotus/Powersuits/Mesa/MesaPrime'
    into a shorter, still-stable slug-ish token for downstream catalog
    matching. We keep this deliberately simple; the ItemCatalog is
    responsible for the real fuzzy matching against a public item list.
    """
    token = raw.strip("/").split("/")[-1]
    return token or raw


def _extract_mod_rank(record: dict) -> Optional[int]:
    """Extracts a mod's fusion rank from its 'UpgradeFingerprint' field,
    e.g. '{"lvl":7}' -> 7. This field only appears on individually-owned
    mod copies (the 'Upgrades' bin in a mobile-API-style export); records
    without it return None (either not a mod, or an unranked bulk stack,
    which is handled correctly by simply not distinguishing a rank).
    """
    fingerprint_raw = record.get("UpgradeFingerprint")
    if not fingerprint_raw:
        return None
    try:
        parsed = json.loads(fingerprint_raw)
        rank = parsed.get("lvl") if isinstance(parsed, dict) else None
        return int(rank) if rank is not None else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


class InventoryParser:
    """Reads an inventory export file from disk and normalizes it.

    This class does exactly one thing: turn bytes on disk into
    InventoryItem records. It does not know about the market, the
    catalog, or the UI. Keep it that way.
    """

    def parse_file(self, path: str | Path) -> InventorySnapshot:
        file_path = Path(path)
        if not file_path.exists():
            raise InventoryFileNotFoundError(str(file_path))

        try:
            raw_text = file_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise InvalidInventoryFileError(
                f"'{file_path.name}' is not readable as UTF-8 text."
            ) from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise InvalidInventoryFileError(
                f"'{file_path.name}' is not valid JSON."
            ) from exc

        items, unresolved = self._normalize(data)

        return InventorySnapshot(
            items=tuple(items),
            imported_at=datetime.now(timezone.utc),
            source_path=str(file_path),
            unresolved_count=unresolved,
        )

    # -- internal ------------------------------------------------------

    def _normalize(self, data: Any) -> tuple[list[InventoryItem], int]:
        records: list[dict] = []

        if isinstance(data, list):
            records.extend(r for r in data if isinstance(r, dict))
        elif isinstance(data, dict):
            if "items" in data and isinstance(data["items"], list):
                # Ordis Market's own normalized format.
                records.extend(r for r in data["items"] if isinstance(r, dict))
            else:
                # Try mobile-API-style nested category arrays.
                found_nested = False
                for key in _KNOWN_NESTED_KEYS:
                    value = data.get(key)
                    if isinstance(value, list):
                        found_nested = True
                        records.extend(r for r in value if isinstance(r, dict))
                # Also scan any other top-level list-of-dicts we don't
                # explicitly know about, in case the export format has
                # shifted since RESEARCH.md was written.
                for key, value in data.items():
                    if key in _KNOWN_NESTED_KEYS:
                        continue
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        found_nested = True
                        records.extend(r for r in value if isinstance(r, dict))
                if not found_nested:
                    raise InvalidInventoryFileError(
                        "No recognizable item list was found in this file. "
                        "Ordis expected 'items', a list of records, or a "
                        "known nested category (Suits, MiscItems, ...)."
                    )
        else:
            raise InvalidInventoryFileError(
                "Top-level JSON must be a list or an object."
            )

        if not records:
            raise InvalidInventoryFileError("The inventory file contains no items.")

        merged: dict[str, InventoryItem] = {}
        unresolved = 0

        for record in records:
            name_raw = _first_present(record, _NAME_KEYS)
            qty_raw = _first_present(record, _QTY_KEYS)

            if name_raw is None:
                unresolved += 1
                continue

            try:
                quantity = int(qty_raw) if qty_raw is not None else 1
            except (TypeError, ValueError):
                quantity = 1

            if quantity <= 0:
                continue

            name_str = str(name_raw)
            source_field = next(
                (k for k in _NAME_KEYS if record.get(k) == name_raw), "name"
            )

            is_item_type_path = source_field == "ItemType" or name_str.startswith("/")
            game_ref = name_str if is_item_type_path else None

            if is_item_type_path:
                item_id = _clean_item_type(name_str).lower()
            else:
                item_id = name_str.strip().lower().replace(" ", "_")

            mod_rank = _extract_mod_rank(record)
            if mod_rank is not None:
                # Same mod, different rank == different market value.
                # Keep them as distinct entries rather than merging.
                item_id = f"{item_id}@rank{mod_rank}"

            if item_id in merged:
                existing = merged[item_id]
                merged[item_id] = InventoryItem(
                    item_id=item_id,
                    quantity=existing.quantity + quantity,
                    raw_name=existing.raw_name,
                    source_field=existing.source_field,
                    game_ref=existing.game_ref,
                    mod_rank=existing.mod_rank,
                )
            else:
                merged[item_id] = InventoryItem(
                    item_id=item_id,
                    quantity=quantity,
                    raw_name=name_str,
                    source_field=source_field,
                    game_ref=game_ref,
                    mod_rank=mod_rank,
                )

        return list(merged.values()), unresolved
