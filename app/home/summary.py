"""
home.summary
============

Turns what the app already knows (the last PortfolioReport and, when the relic
tables are downloaded, the Relics analysis) into the numbers and "needs
attention" items shown on the Home.

Nothing here computes a price, a score or a set state itself: it only counts
and sums results the existing analyzers produced. Pure Python, no Qt.

Ordis: "I did not calculate anything new. I merely gathered it where you
        could see it. I am told this is called 'management'."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.analysis.portfolio import PortfolioReport
from app.home.targets import Target
from app.market.ducats import DucatVerdict
from app.market.sell_score import Recommendation
from app.relics.analyzer import RelicsReport, SetState
from app.relics.view import FilterMode, filter_statuses
from app.ui.filters import is_prime_set_name

MANY_TRADABLE = 100  # "a worrying amount of tradable items"
MANY_DUPLICATES = 10  # distinct items held in more than one copy


@dataclass(frozen=True)
class SetsSummary:
    ready: int  # every part owned: ready to build/trade
    one_away: int  # exactly one part short (and at least one owned)
    completable: int  # every missing part drops from a relic you own


@dataclass(frozen=True)
class InventorySummary:
    estimated_value: float
    distinct_items: int
    total_units: int
    tradable_items: int
    assembled_sets: int  # units of "X Prime Set" already assembled
    ducat_items: int  # items that have a Ducat value
    ducats_total: int  # Ducats if every such unit were turned in
    ducat_deals: int  # items the Ducat analysis says are worth more as Ducats
    ducat_deals_total: int  # Ducats in those items
    duplicate_items: int
    duplicate_units: int  # copies beyond the first
    sell_candidates: int
    stale_prices: int
    missing_prices: int


class Level(str, Enum):
    GOOD = "good"  # something to act on (gold)
    INFO = "info"  # worth knowing (cyan)
    WARN = "warn"  # something is missing or off (red)


@dataclass(frozen=True)
class AttentionItem:
    level: Level
    text: str
    detail: str
    target: Optional[Target] = None


def summarize_inventory(report: PortfolioReport) -> InventorySummary:
    ducat_items = ducats_total = deals = deals_total = 0
    duplicate_items = duplicate_units = sell = assembled = 0
    units = 0
    for a in report.analyses:
        units += a.quantity
        if a.tradable and a.quantity > 1:  # resources like Credits or Endo are not "duplicates"
            duplicate_items += 1
            duplicate_units += a.quantity - 1
        if is_prime_set_name(a.display_name):
            assembled += a.quantity
        if a.recommendation is Recommendation.SELL:
            sell += 1
        if a.ducats is not None and a.ducats.ducats:
            ducat_items += 1
            ducats_total += a.ducats.ducats * a.quantity
            if a.ducats.verdict is DucatVerdict.KEEP_FOR_DUCATS:
                deals += 1
                deals_total += a.ducats.ducats * a.quantity
    return InventorySummary(
        estimated_value=report.estimated_total_value,
        distinct_items=report.total_inventory_items,
        total_units=units,
        tradable_items=report.total_tradable_items,
        assembled_sets=assembled,
        ducat_items=ducat_items,
        ducats_total=ducats_total,
        ducat_deals=deals,
        ducat_deals_total=deals_total,
        duplicate_items=duplicate_items,
        duplicate_units=duplicate_units,
        sell_candidates=sell,
        stale_prices=report.stale_price_slug_count,
        missing_prices=report.market_error_slug_count,
    )


def summarize_sets(relics: RelicsReport) -> SetsSummary:
    # The first and last counts use the same filters as the Relics tab, so the
    # Home and the tab can never disagree.
    ready = len(filter_statuses(relics.sets, FilterMode.COMPLETE))
    completable = len(filter_statuses(relics.sets, FilterMode.COMPLETABLE))
    one_away = sum(
        1
        for s in relics.sets
        if s.state is not SetState.COMPLETE and s.owned_units > 0 and s.need_units - s.owned_units == 1
    )
    return SetsSummary(ready=ready, one_away=one_away, completable=completable)


def _plural(count: int, singular: str, plural: Optional[str] = None) -> str:
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"


def attention_items(
    summary: Optional[InventorySummary],
    sets: Optional[SetsSummary],
    has_inventory: bool,
    has_relic_data: bool,
) -> list[AttentionItem]:
    """Situations worth a look, most actionable first. Each carries where a
    click should go."""
    items: list[AttentionItem] = []

    if summary is None:
        if not has_inventory:
            items.append(AttentionItem(
                Level.WARN, "No inventory imported yet",
                "Import or grab your inventory on the Market tab to fill this page.", Target.MARKET))
        else:
            items.append(AttentionItem(
                Level.WARN, "Inventory not analyzed yet",
                "Run ANALYZE INVENTORY on the Market tab.", Target.MARKET))
    else:
        if summary.sell_candidates:
            items.append(AttentionItem(
                Level.GOOD, f"{_plural(summary.sell_candidates, 'item')} rated SELL",
                "Best sell scores first.", Target.MARKET_BY_SCORE))
        if summary.ducat_deals:
            items.append(AttentionItem(
                Level.GOOD,
                f"{_plural(summary.ducat_deals, 'item')} worth more as Ducats",
                f"{summary.ducat_deals_total} Ducats in total, for Baro Ki'Teer.", Target.MARKET_BY_DUCATS))
        if summary.assembled_sets:
            items.append(AttentionItem(
                Level.INFO, f"{_plural(summary.assembled_sets, 'assembled Prime Set')} on hand",
                "Compare their price with the parts' price.", Target.MARKET_PRIME_SETS))
        if summary.duplicate_items >= MANY_DUPLICATES:
            items.append(AttentionItem(
                Level.INFO, f"{summary.duplicate_items} items held in several copies",
                f"{summary.duplicate_units} spare copies. Biggest stacks first.", Target.MARKET_BY_QTY))
        if summary.missing_prices:
            items.append(AttentionItem(
                Level.WARN, f"{_plural(summary.missing_prices, 'item')} without market data",
                "UPDATE MARKET on the Market tab to try again.", Target.MARKET))
        elif summary.stale_prices:
            items.append(AttentionItem(
                Level.WARN, f"{_plural(summary.stale_prices, 'item')} priced from an old cache",
                "UPDATE MARKET for fresh prices.", Target.MARKET))

    if sets is not None:
        if sets.ready:
            items.insert(0, AttentionItem(
                Level.GOOD, f"{_plural(sets.ready, 'Prime set')} ready to build",
                "You already hold every part.", Target.RELICS_READY))
        if sets.one_away:
            items.append(AttentionItem(
                Level.GOOD, f"{_plural(sets.one_away, 'Prime set')} one part away",
                "Closest sets first.", Target.RELICS_ONE_AWAY))
        if sets.completable:
            items.append(AttentionItem(
                Level.GOOD, f"{_plural(sets.completable, 'Prime set')} finishable with your relics",
                "Every missing part drops from a relic you own.", Target.RELICS_COMPLETABLE))
    elif has_inventory and not has_relic_data:
        items.append(AttentionItem(
            Level.INFO, "Relic drop tables not downloaded",
            "Open the Relics tab once to see Prime set progress here.", Target.RELICS))

    return items
