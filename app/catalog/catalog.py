"""
catalog.catalog
================

ItemCatalog holds the mapping from item_id/slug to display metadata
(name, category, ducats, tradable status, Prime/set relationships).

Ordis: "The catalog. My beautiful, ever-growing catalog. I have opinions
        about roughly forty percent of these items."
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class CatalogEntry:
    slug: str
    item_id: str
    name: str
    category: str = "unknown"
    tradable: bool = True
    is_prime: bool = False
    ducats: Optional[int] = None
    set_slug: Optional[str] = None
    is_set: bool = False
    component_slugs: tuple[str, ...] = ()
    icon: Optional[str] = None
    game_ref: Optional[str] = None
    """warframe.market's own reference to the item's internal Warframe path
    (e.g. '/Lotus/Powersuits/Mesa/MesaPrime'). When present, this is the
    most reliable way to match an inventory export's raw ItemType against
    the catalog -- far more reliable than name or slug heuristics, since
    it's the same identifier the game itself uses internally."""


class ItemCatalog:
    """In-memory + on-disk item catalog, keyed by slug.

    The catalog is populated from warframe.market's `/v2/items` index
    (see WarframeMarketClient.get_items) and cached to disk so we do not
    re-download it on every launch.
    """

    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._entries: dict[str, CatalogEntry] = {}
        self._name_index: dict[str, str] = {}  # lowercased name -> slug
        self._game_ref_index: dict[str, str] = {}  # game_ref path -> slug

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, slug: str) -> Optional[CatalogEntry]:
        return self._entries.get(slug)

    def find_by_name(self, name: str) -> Optional[CatalogEntry]:
        slug = self._name_index.get(name.strip().lower())
        return self._entries.get(slug) if slug else None

    def find_by_game_ref(self, game_ref: str) -> Optional[CatalogEntry]:
        """Looks up an entry by the internal Warframe ItemType path, e.g.
        '/Lotus/Weapons/Tenno/LongGuns/TnWispRifle/TnWispRifle'. This is
        the preferred lookup for items parsed from a real inventory
        export, since it doesn't depend on any name/slug normalization
        matching up between the game's internal naming and warframe.market's."""
        slug = self._game_ref_index.get(game_ref)
        return self._entries.get(slug) if slug else None

    def all_entries(self) -> Iterable[CatalogEntry]:
        return self._entries.values()

    def load_from_market_payload(self, raw_items: list[dict]) -> int:
        """Builds the catalog from warframe.market's item index payload.

        Each raw item is expected to look roughly like::

            {
              "id": "...", "slug": "mesa_prime_neuroptics",
              "i18n": {"en": {"name": "Mesa Prime Neuroptics"}},
              "tags": ["prime", "warframe_part"],
              "ducats": 65,
              "tradable": true,
              "set_root": false,
              "quantity_for_set": 1,
              "gameRef": "/Lotus/Powersuits/Mesa/MesaPrimeHelmet",
              ...
            }

        The exact v2 field names are still evolving (see RESEARCH.md);
        this loader is defensive and skips fields it cannot find rather
        than failing the whole catalog load. The 'gameRef' field name in
        particular has been observed under that casing in third-party
        tooling built against this API, but is checked under a couple of
        casing variants defensively since it isn't yet in first-party docs.
        """
        entries: dict[str, CatalogEntry] = {}
        name_index: dict[str, str] = {}
        game_ref_index: dict[str, str] = {}

        for raw in raw_items:
            slug = raw.get("slug")
            item_id = raw.get("id", slug)
            if not slug:
                continue

            i18n = raw.get("i18n", {})
            en = i18n.get("en", {}) if isinstance(i18n, dict) else {}
            name = en.get("name") or raw.get("item_name") or raw.get("name") or slug

            tags = raw.get("tags", []) if isinstance(raw.get("tags"), list) else []
            category = tags[0] if tags else "unknown"

            game_ref = (
                raw.get("gameRef")
                or raw.get("game_ref")
                or raw.get("gameref")
                or raw.get("uniqueName")
            )

            entry = CatalogEntry(
                slug=slug,
                item_id=str(item_id),
                name=name,
                category=category,
                tradable=bool(raw.get("tradable", True)),
                is_prime="prime" in [t.lower() for t in tags],
                ducats=raw.get("ducats"),
                set_slug=raw.get("set_root_slug") or raw.get("set_slug"),
                is_set=bool(raw.get("set_root", False)),
                component_slugs=tuple(raw.get("components_slugs", []) or ()),
                icon=en.get("icon") or raw.get("icon"),
                game_ref=game_ref,
            )
            entries[slug] = entry
            name_index[name.strip().lower()] = slug
            if game_ref:
                game_ref_index[game_ref] = slug

        self._entries = entries
        self._name_index = name_index
        self._game_ref_index = game_ref_index
        return len(entries)

    def save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "slug": e.slug,
                "item_id": e.item_id,
                "name": e.name,
                "category": e.category,
                "tradable": e.tradable,
                "is_prime": e.is_prime,
                "ducats": e.ducats,
                "set_slug": e.set_slug,
                "is_set": e.is_set,
                "component_slugs": list(e.component_slugs),
                "icon": e.icon,
                "game_ref": e.game_ref,
            }
            for e in self._entries.values()
        ]
        self._storage_path.write_text(json.dumps(payload), encoding="utf-8")

    def load_from_disk(self) -> bool:
        if not self._storage_path.exists():
            return False
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False

        entries: dict[str, CatalogEntry] = {}
        name_index: dict[str, str] = {}
        game_ref_index: dict[str, str] = {}
        for raw in payload:
            entry = CatalogEntry(
                slug=raw["slug"],
                item_id=raw["item_id"],
                name=raw["name"],
                category=raw.get("category", "unknown"),
                tradable=raw.get("tradable", True),
                is_prime=raw.get("is_prime", False),
                ducats=raw.get("ducats"),
                set_slug=raw.get("set_slug"),
                is_set=raw.get("is_set", False),
                component_slugs=tuple(raw.get("component_slugs", [])),
                icon=raw.get("icon"),
                game_ref=raw.get("game_ref"),
            )
            entries[entry.slug] = entry
            name_index[entry.name.strip().lower()] = entry.slug
            if entry.game_ref:
                game_ref_index[entry.game_ref] = entry.slug

        self._entries = entries
        self._name_index = name_index
        self._game_ref_index = game_ref_index
        return True
