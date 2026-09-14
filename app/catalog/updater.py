"""
catalog.updater
================

ItemCatalogUpdater decides *when* to refresh the catalog from the network
and orchestrates the fetch, so ItemCatalog itself can stay a dumb store.
NameIndexUpdater does the same for the Digital Extremes name-mapping data
used to resolve raw inventory paths into human names (see
warframe_export.py) -- the two are refreshed independently since one is
warframe.market data and the other is Digital Extremes data, with
different failure modes.

Ordis: "I do not download the entire universe every time you sneeze,
        Operator. That would be excessive, even for me."
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.catalog.catalog import ItemCatalog
from app.catalog.name_index import NameIndex
from app.catalog.warframe_export import WarframeExportError, fetch_unique_name_index
from app.market.client import MarketClientError, WarframeMarketClient


class _TtlGate:
    """Shared 'is this cache stale yet' bookkeeping for the two updaters
    below -- both need the exact same disk-backed timestamp check, so it
    lives here once instead of twice.
    """

    def __init__(self, meta_path: Path, ttl_seconds: int) -> None:
        self._meta_path = meta_path
        self._ttl_seconds = ttl_seconds

    def is_stale(self) -> bool:
        if not self._meta_path.exists():
            return True
        try:
            last_updated = float(self._meta_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return True
        return (time.time() - last_updated) > self._ttl_seconds

    def mark_fresh(self) -> None:
        self._meta_path.parent.mkdir(parents=True, exist_ok=True)
        self._meta_path.write_text(str(time.time()), encoding="utf-8")


@dataclass
class CatalogUpdateResult:
    updated: bool
    entry_count: int
    used_cache: bool
    error: Optional[str] = None


class ItemCatalogUpdater:
    def __init__(
        self,
        catalog: ItemCatalog,
        client: WarframeMarketClient,
        meta_path: Path,
        ttl_seconds: int,
    ) -> None:
        self._catalog = catalog
        self._client = client
        self._gate = _TtlGate(meta_path, ttl_seconds)

    def ensure_fresh(self, force: bool = False) -> CatalogUpdateResult:
        loaded_from_disk = self._catalog.load_from_disk()

        if not force and loaded_from_disk and not self._gate.is_stale():
            return CatalogUpdateResult(
                updated=False, entry_count=len(self._catalog), used_cache=True
            )

        try:
            raw_items = self._client.get_items()
        except MarketClientError as exc:
            if loaded_from_disk:
                # Offline-friendly: keep using what we already have.
                return CatalogUpdateResult(
                    updated=False,
                    entry_count=len(self._catalog),
                    used_cache=True,
                    error=str(exc),
                )
            return CatalogUpdateResult(updated=False, entry_count=0, used_cache=False, error=str(exc))

        count = self._catalog.load_from_market_payload(raw_items)
        self._catalog.save()
        self._gate.mark_fresh()
        return CatalogUpdateResult(updated=True, entry_count=count, used_cache=False)


@dataclass
class NameIndexUpdateResult:
    updated: bool
    entry_count: int
    used_cache: bool
    error: Optional[str] = None


class NameIndexUpdater:
    """Refreshes the Digital Extremes uniqueName -> display name mapping
    used to resolve raw inventory ItemType paths (see warframe_export.py
    and PortfolioAnalyzer). Independent of ItemCatalogUpdater because it
    hits a completely different, unrelated data source (Digital Extremes'
    Public Export, not warframe.market) with its own availability and TTL.
    """

    def __init__(
        self,
        name_index: NameIndex,
        meta_path: Path,
        ttl_seconds: int,
        fetch_fn: Callable[[], dict[str, str]] = fetch_unique_name_index,
    ) -> None:
        self._name_index = name_index
        self._gate = _TtlGate(meta_path, ttl_seconds)
        self._fetch_fn = fetch_fn

    def ensure_fresh(self, force: bool = False) -> NameIndexUpdateResult:
        loaded_from_disk = self._name_index.load_from_disk()

        if not force and loaded_from_disk and not self._gate.is_stale():
            return NameIndexUpdateResult(
                updated=False, entry_count=len(self._name_index), used_cache=True
            )

        try:
            pairs = self._fetch_fn()
        except WarframeExportError as exc:
            if loaded_from_disk:
                return NameIndexUpdateResult(
                    updated=False,
                    entry_count=len(self._name_index),
                    used_cache=True,
                    error=str(exc),
                )
            return NameIndexUpdateResult(updated=False, entry_count=0, used_cache=False, error=str(exc))

        count = self._name_index.load_from_pairs(pairs)
        self._name_index.save()
        self._gate.mark_fresh()
        return NameIndexUpdateResult(updated=True, entry_count=count, used_cache=False)
