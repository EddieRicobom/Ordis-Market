"""
analysis.report_repository
============================

Persists the last completed PortfolioReport to disk, so the dashboard can
show your last analysis results immediately on startup instead of an
empty table until you click ANALYZE INVENTORY again.

Ordis: "I keep a copy of my last report, Operator, in case you close me
        by accident. I am nothing if not prepared."

This is separate from InventoryRepository (which persists the raw
imported inventory) and from the various TTL caches (catalog, name
index, wiki index, price cache) -- those all cache *inputs*; this caches
the *computed output* of a full analysis run, so reopening the app
doesn't require redoing the work at all, not just avoiding re-fetching
data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.analysis.portfolio import ItemAnalysis, PortfolioReport
from app.config.settings import PricingStrategy
from app.market.ducats import DucatComparison, DucatVerdict
from app.market.liquidity import LiquidityLevel, LiquidityReport
from app.market.pricing import PriceQuote
from app.market.sell_score import Recommendation, SellScoreResult


def _price_to_dict(p: Optional[PriceQuote]) -> Optional[dict]:
    if p is None:
        return None
    return {
        "lowest_sell": p.lowest_sell,
        "average_sell": p.average_sell,
        "median_sell": p.median_sell,
        "recommended_price": p.recommended_price,
        "sample_size": p.sample_size,
        "strategy_used": p.strategy_used.value,
    }


def _price_from_dict(d: Optional[dict]) -> Optional[PriceQuote]:
    if d is None:
        return None
    return PriceQuote(
        lowest_sell=d.get("lowest_sell"),
        average_sell=d.get("average_sell"),
        median_sell=d.get("median_sell"),
        recommended_price=d.get("recommended_price"),
        sample_size=d.get("sample_size", 0),
        strategy_used=PricingStrategy(d.get("strategy_used", PricingStrategy.LOWEST.value)),
    )


def _liquidity_to_dict(l: Optional[LiquidityReport]) -> Optional[dict]:
    if l is None:
        return None
    return {
        "level": l.level.value,
        "online_sell_count": l.online_sell_count,
        "online_buy_count": l.online_buy_count,
        "spread": l.spread,
    }


def _liquidity_from_dict(d: Optional[dict]) -> Optional[LiquidityReport]:
    if d is None:
        return None
    return LiquidityReport(
        level=LiquidityLevel(d.get("level", LiquidityLevel.UNKNOWN.value)),
        online_sell_count=d.get("online_sell_count", 0),
        online_buy_count=d.get("online_buy_count", 0),
        spread=d.get("spread"),
    )


def _sell_score_to_dict(s: Optional[SellScoreResult]) -> Optional[dict]:
    if s is None:
        return None
    return {"score": s.score, "recommendation": s.recommendation.value, "reasons": list(s.reasons)}


def _sell_score_from_dict(d: Optional[dict]) -> Optional[SellScoreResult]:
    if d is None:
        return None
    return SellScoreResult(
        score=d.get("score", 0),
        recommendation=Recommendation(d.get("recommendation", Recommendation.UNKNOWN.value)),
        reasons=tuple(d.get("reasons", [])),
    )


def _ducats_to_dict(c: Optional[DucatComparison]) -> Optional[dict]:
    if c is None:
        return None
    return {
        "platinum_price": c.platinum_price,
        "ducats": c.ducats,
        "plat_per_ducat": c.plat_per_ducat,
        "reference_plat_per_ducat": c.reference_plat_per_ducat,
        "verdict": c.verdict.value,
    }


def _ducats_from_dict(d: Optional[dict]) -> Optional[DucatComparison]:
    if d is None:
        return None
    return DucatComparison(
        platinum_price=d.get("platinum_price"),
        ducats=d.get("ducats"),
        plat_per_ducat=d.get("plat_per_ducat"),
        reference_plat_per_ducat=d.get("reference_plat_per_ducat", 0.0),
        verdict=DucatVerdict(d.get("verdict", DucatVerdict.INSUFFICIENT_DATA.value)),
    )


def _analysis_to_dict(a: ItemAnalysis) -> dict:
    return {
        "item_id": a.item_id,
        "slug": a.slug,
        "display_name": a.display_name,
        "base_name": a.base_name,
        "quantity": a.quantity,
        "tradable": a.tradable,
        "category": a.category,
        "is_prime": a.is_prime,
        "price": _price_to_dict(a.price),
        "liquidity": _liquidity_to_dict(a.liquidity),
        "sell_score": _sell_score_to_dict(a.sell_score),
        "ducats": _ducats_to_dict(a.ducats),
        "wiki_url": a.wiki_url,
        "data_available": a.data_available,
        "error": a.error,
    }


def _analysis_from_dict(d: dict) -> ItemAnalysis:
    return ItemAnalysis(
        item_id=d["item_id"],
        slug=d.get("slug"),
        display_name=d["display_name"],
        base_name=d.get("base_name"),
        quantity=d.get("quantity", 0),
        tradable=d.get("tradable", False),
        category=d.get("category", "unknown"),
        is_prime=d.get("is_prime", False),
        price=_price_from_dict(d.get("price")),
        liquidity=_liquidity_from_dict(d.get("liquidity")),
        sell_score=_sell_score_from_dict(d.get("sell_score")),
        ducats=_ducats_from_dict(d.get("ducats")),
        wiki_url=d.get("wiki_url"),
        data_available=d.get("data_available", True),
        error=d.get("error"),
    )


class ReportRepository:
    """Disk-backed storage for the last completed PortfolioReport, keyed
    with a timestamp so the UI can show the Operator exactly how stale
    what they're looking at is."""

    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path

    def save(self, report: PortfolioReport, analyzed_at_iso: str) -> None:
        payload = {
            "analyzed_at": analyzed_at_iso,
            "total_inventory_items": report.total_inventory_items,
            "total_tradable_items": report.total_tradable_items,
            "estimated_total_value": report.estimated_total_value,
            "unresolved_count": report.unresolved_count,
            "catalog_matched_count": report.catalog_matched_count,
            "stale_price_slug_count": report.stale_price_slug_count,
            "market_error_slug_count": report.market_error_slug_count,
            "analyses": [_analysis_to_dict(a) for a in report.analyses],
        }
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self) -> Optional[tuple[PortfolioReport, str]]:
        """Returns (report, analyzed_at_iso) if a previous analysis is on
        disk and parses cleanly, otherwise None. Never raises -- a
        corrupt or missing cache just means "nothing to restore", not a
        crash."""
        if not self._storage_path.exists():
            return None
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        try:
            report = PortfolioReport(
                analyses=tuple(_analysis_from_dict(d) for d in payload["analyses"]),
                total_inventory_items=payload["total_inventory_items"],
                total_tradable_items=payload["total_tradable_items"],
                estimated_total_value=payload["estimated_total_value"],
                unresolved_count=payload["unresolved_count"],
                catalog_matched_count=payload.get("catalog_matched_count", 0),
                stale_price_slug_count=payload.get("stale_price_slug_count", 0),
                market_error_slug_count=payload.get("market_error_slug_count", 0),
            )
        except (KeyError, TypeError, ValueError):
            return None

        return report, payload.get("analyzed_at", "")

    def clear(self) -> None:
        """Removes the persisted report, if any -- used when the
        Operator re-imports a different inventory, since an old
        analysis for a different snapshot would otherwise be misleading."""
        if self._storage_path.exists():
            self._storage_path.unlink()
