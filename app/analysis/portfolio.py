"""
analysis.portfolio
===================

PortfolioAnalyzer ties inventory + catalog + market repository +
pricing/liquidity/sell-score/ducats together into one row-per-item
analysis the UI can display, filter, and export.

Ordis: "This is where I combine everything I know into one enormous
        table. Try not to stare directly at the total value column."
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Optional

from app.catalog.catalog import CatalogEntry, ItemCatalog
from app.catalog.name_index import NameIndex
from app.catalog.wiki_index import WikiIndex
from app.config.settings import AppSettings
from app.inventory.models import InventoryItem, InventorySnapshot
from app.market.ducats import DucatAnalyzer, DucatComparison
from app.market.liquidity import LiquidityAnalyzer, LiquidityLevel, LiquidityReport
from app.market.pricing import PriceAnalyzer, PriceQuote
from app.market.repository import MarketRepository, OrdersResult
from app.market.sell_score import Recommendation, SellScoreAnalyzer, SellScoreResult


@dataclass
class ItemAnalysis:
    item_id: str
    slug: Optional[str]
    display_name: str
    quantity: int
    tradable: bool
    category: str
    is_prime: bool

    base_name: Optional[str] = None
    """The clean item name with no rank suffix (e.g. 'Serration', not
    'Serration (Rank 10)'). Use this, not display_name, for anything that
    needs to match against a name-keyed external source (the Wiki index,
    the DE name index) -- display_name is for showing to a human, this is
    for matching. Kept separate deliberately after a real bug where the
    Wiki lookup used display_name and could never match a ranked mod's
    already-cached link because the rank suffix made every rank look like
    a different item name."""

    price: Optional[PriceQuote] = None
    liquidity: Optional[LiquidityReport] = None
    sell_score: Optional[SellScoreResult] = None
    ducats: Optional[DucatComparison] = None
    wiki_url: Optional[str] = None
    """Link to the item's official Warframe Wiki page, if known. Populated
    from a passive, already-cached WikiIndex lookup only -- PortfolioAnalyzer
    never makes a live Wiki request itself (see catalog/wiki_index_builder.py
    for the separate, Operator-triggered process that populates this)."""

    data_available: bool = True
    error: Optional[str] = None

    @property
    def unit_price(self) -> Optional[float]:
        return self.price.recommended_price if self.price else None

    @property
    def total_value(self) -> Optional[float]:
        if self.unit_price is None:
            return None
        return round(self.unit_price * self.quantity, 2)

    @property
    def liquidity_level(self) -> LiquidityLevel:
        return self.liquidity.level if self.liquidity else LiquidityLevel.UNKNOWN

    @property
    def recommendation(self) -> Recommendation:
        return self.sell_score.recommendation if self.sell_score else Recommendation.UNKNOWN

    @property
    def score(self) -> int:
        return self.sell_score.score if self.sell_score else 0


@dataclass
class PortfolioReport:
    analyses: tuple[ItemAnalysis, ...]
    total_inventory_items: int
    total_tradable_items: int
    estimated_total_value: float
    unresolved_count: int
    catalog_matched_count: int = 0
    """How many parsed inventory items were successfully matched against
    the item catalog (i.e. found and recognized as a real item, tradable
    or not). Distinct from total_tradable_items, which only counts the
    subset that's actually sellable. A low ratio of this vs
    total_inventory_items usually means the catalog is stale/empty
    (click UPDATE ITEMS) rather than that the items are unrecognized."""

    stale_price_slug_count: int = 0
    """How many distinct market slugs fell back to stale cached data
    during this analysis (market was reachable before, but not this
    time). Report-level rather than per-item since it's about overall
    market reachability, not any single item."""

    market_error_slug_count: int = 0
    """How many distinct market slugs had no usable data at all --
    neither live nor a stale cache -- during this analysis."""


class PortfolioAnalyzer:
    """Runs the full per-item analysis pipeline across an inventory
    snapshot. Network calls are funneled through MarketRepository, which
    handles caching/offline behavior -- this class only orchestrates.
    """

    def __init__(
        self,
        catalog: ItemCatalog,
        market_repository: MarketRepository,
        settings: AppSettings,
        price_analyzer: Optional[PriceAnalyzer] = None,
        liquidity_analyzer: Optional[LiquidityAnalyzer] = None,
        sell_score_analyzer: Optional[SellScoreAnalyzer] = None,
        ducat_analyzer: Optional[DucatAnalyzer] = None,
        name_index: Optional[NameIndex] = None,
        wiki_index: Optional[WikiIndex] = None,
        max_workers: int = 4,
    ) -> None:
        self._catalog = catalog
        self._repo = market_repository
        self._wiki_index = wiki_index
        self._settings = settings
        self._price_analyzer = price_analyzer or PriceAnalyzer()
        self._liquidity_analyzer = liquidity_analyzer or LiquidityAnalyzer()
        self._sell_score_analyzer = sell_score_analyzer or SellScoreAnalyzer()
        self._ducat_analyzer = ducat_analyzer or DucatAnalyzer()
        self._name_index = name_index
        self._max_workers = max(1, max_workers)
        """Bounded worker count for concurrently fetching distinct market
        slugs. warframe.market's own published rate limit (3 req/sec,
        enforced by the thread-safe RateLimiter inside WarframeMarketClient
        regardless of caller count) is the true throughput ceiling here --
        concurrency doesn't bypass it, it only overlaps request latency
        with that limit's idle time. Worst case, if latency is already
        below the rate-limit floor, this simply provides no speedup; it
        never makes things slower or violates the limit."""

    def analyze(
        self,
        snapshot: InventorySnapshot,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        force_refresh: bool = False,
    ) -> PortfolioReport:
        total = len(snapshot.items)
        completed = 0

        def _tick(count: int = 1) -> None:
            nonlocal completed
            completed += count
            if progress_callback:
                progress_callback(min(completed, total), total)

        # Phase 1 (sequential, no network): resolve each inventory item to
        # its catalog entry, if any. Items that are unresolved or
        # not-tradable are finished immediately here -- identical logic/
        # error text to the old single-pass implementation, just split out
        # so it can run before any network I/O happens.
        finished: dict[int, ItemAnalysis] = {}
        pending: list[tuple[int, InventoryItem, CatalogEntry]] = []

        for index, inv_item in enumerate(snapshot.items):
            entry = self._resolve_entry(inv_item)
            early = self._early_exit_analysis(inv_item, entry)
            if early is not None:
                finished[index] = early
                _tick()
            else:
                pending.append((index, inv_item, entry))

        # Phase 2 (network, bounded concurrency, deduplicated by slug):
        # multiple inventory items can resolve to the same market slug --
        # most commonly the same mod owned at several fusion ranks -- so
        # fetch each DISTINCT slug's order book only once per analyze()
        # call, not once per inventory item. This is the single biggest
        # avoidable source of redundant API requests in this pipeline.
        items_per_slug: dict[str, int] = {}
        for _, _, entry in pending:
            items_per_slug[entry.slug] = items_per_slug.get(entry.slug, 0) + 1

        orders_by_slug: dict[str, OrdersResult] = {}
        liquidity_by_slug: dict[str, LiquidityReport] = {}

        def _fetch(slug: str) -> tuple[str, OrdersResult]:
            try:
                return slug, self._repo.get_orders(slug, force_refresh=force_refresh)
            except Exception as exc:  # noqa: BLE001 - one bad slug must not sink the batch
                return slug, OrdersResult(item_orders=None, from_cache=False, stale=False, error=str(exc))

        unique_slugs = list(items_per_slug.keys())
        if unique_slugs:
            worker_count = min(self._max_workers, len(unique_slugs))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = [executor.submit(_fetch, slug) for slug in unique_slugs]
                for future in as_completed(futures):
                    slug, result = future.result()
                    orders_by_slug[slug] = result
                    if result.item_orders is not None:
                        liquidity_by_slug[slug] = self._liquidity_analyzer.analyze(result.item_orders)
                    _tick(items_per_slug[slug])

        # Phase 3 (sequential, CPU-only, uses the already-fetched/deduped
        # slug data): assemble the final per-item result. Price still has
        # to be computed per inventory item, not per slug, since mod rank
        # filtering makes it legitimately different even for the same slug.
        for index, inv_item, entry in pending:
            result = orders_by_slug[entry.slug]
            finished[index] = self._finish_analysis(
                inv_item, entry, result, liquidity_by_slug.get(entry.slug)
            )

        analyses = [finished[i] for i in range(len(snapshot.items))]

        total_value = 0.0
        tradable_count = 0
        matched_count = 0
        for analysis in analyses:
            if analysis.slug is not None:
                matched_count += 1
            if analysis.tradable:
                tradable_count += 1
            if analysis.total_value:
                total_value += analysis.total_value

        stale_slugs = sum(1 for r in orders_by_slug.values() if r.stale)
        error_slugs = sum(1 for r in orders_by_slug.values() if r.item_orders is None)

        return PortfolioReport(
            analyses=tuple(analyses),
            total_inventory_items=snapshot.total_items,
            total_tradable_items=tradable_count,
            estimated_total_value=round(total_value, 2),
            unresolved_count=snapshot.unresolved_count,
            catalog_matched_count=matched_count,
            stale_price_slug_count=stale_slugs,
            market_error_slug_count=error_slugs,
        )

    # -- internal ------------------------------------------------------

    def _wiki_url_for(self, entry: Optional[CatalogEntry]) -> Optional[str]:
        """Passive, network-free lookup only -- see module docstring and
        catalog/wiki_index_builder.py for why this never makes a live
        request itself."""
        if self._wiki_index is None or entry is None:
            return None
        return self._wiki_index.get(entry.name)

    def _resolve_entry(self, inv_item: InventoryItem) -> Optional[CatalogEntry]:
        return (
            (self._catalog.find_by_game_ref(inv_item.game_ref) if inv_item.game_ref else None)
            or self._catalog.get(inv_item.item_id)
            or self._catalog.find_by_name(inv_item.raw_name)
            or self._match_via_name_index(inv_item)
        )

    def _early_exit_analysis(
        self, inv_item: InventoryItem, entry: Optional[CatalogEntry]
    ) -> Optional["ItemAnalysis"]:
        """Returns a finished ItemAnalysis for the two cases that never
        need a market fetch (unresolved / not tradable), or None if this
        item needs to proceed to the network phase."""
        if entry is None:
            return ItemAnalysis(
                item_id=inv_item.item_id,
                slug=None,
                display_name=self._display_name(inv_item.raw_name, inv_item.mod_rank),
                base_name=inv_item.raw_name,
                quantity=inv_item.quantity,
                tradable=False,
                category="unknown",
                is_prime=False,
                data_available=False,
                error="Not found in the item catalog.",
            )

        if not entry.tradable:
            return ItemAnalysis(
                item_id=inv_item.item_id,
                slug=entry.slug,
                display_name=self._display_name(entry.name, inv_item.mod_rank),
                base_name=entry.name,
                quantity=inv_item.quantity,
                tradable=False,
                category=entry.category,
                is_prime=entry.is_prime,
                wiki_url=self._wiki_url_for(entry),
                data_available=False,
                error="Item is not tradable on warframe.market.",
            )

        return None

    def _finish_analysis(
        self,
        inv_item: InventoryItem,
        entry: CatalogEntry,
        result: OrdersResult,
        liquidity: Optional[LiquidityReport],
    ) -> ItemAnalysis:
        if result.item_orders is None:
            return ItemAnalysis(
                item_id=inv_item.item_id,
                slug=entry.slug,
                display_name=self._display_name(entry.name, inv_item.mod_rank),
                base_name=entry.name,
                quantity=inv_item.quantity,
                tradable=True,
                category=entry.category,
                is_prime=entry.is_prime,
                wiki_url=self._wiki_url_for(entry),
                data_available=False,
                error=result.error or "No market data available.",
            )

        price = self._price_analyzer.analyze(
            result.item_orders, strategy=self._settings.pricing_strategy, mod_rank=inv_item.mod_rank
        )
        # Liquidity is identical for every item sharing this slug (it
        # doesn't depend on mod rank), so it's computed once per slug in
        # Phase 2 and simply reused here rather than recomputed per item.
        if liquidity is None:
            liquidity = self._liquidity_analyzer.analyze(result.item_orders)
        sell_score = self._sell_score_analyzer.score(price, liquidity, inv_item.quantity)
        ducats = self._ducat_analyzer.compare(
            price.recommended_price, entry.ducats, self._settings.ducat_reference_value
        )

        return ItemAnalysis(
            item_id=inv_item.item_id,
            slug=entry.slug,
            display_name=self._display_name(entry.name, inv_item.mod_rank),
            base_name=entry.name,
            quantity=inv_item.quantity,
            tradable=True,
            category=entry.category,
            is_prime=entry.is_prime,
            price=price,
            liquidity=liquidity,
            sell_score=sell_score,
            ducats=ducats,
            wiki_url=self._wiki_url_for(entry),
            data_available=True,
        )

    @staticmethod
    def _display_name(base_name: str, mod_rank: Optional[int]) -> str:
        """Appends a rank suffix so two rows of the same mod at different
        ranks are visually distinguishable in the table/export, e.g.
        'Serration (Rank 10)' vs 'Serration (Rank 0)'."""
        if mod_rank is None:
            return base_name
        return f"{base_name} (Rank {mod_rank})"

    def _match_via_name_index(self, inv_item: InventoryItem) -> Optional[CatalogEntry]:
        """Last-resort match: translate the raw internal ItemType path into
        its official Digital Extremes display name (via NameIndex, sourced
        from DE's own Public Export data), then look that name up in the
        warframe.market catalog by name. This is what resolves items like
        Prime part blueprints, whose internal path bears no resemblance to
        either their warframe.market slug or a gameRef match.
        """
        if self._name_index is None or not inv_item.game_ref:
            return None
        display_name = self._name_index.get(inv_item.game_ref)
        if not display_name:
            return None
        return self._catalog.find_by_name(display_name)
