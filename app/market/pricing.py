"""
market.pricing
==============

PriceAnalyzer turns raw sell orders into a defensible recommended price.

Ordis: "Calculating a reasonable selling price. Not the lowest, unless you
        insist. I have seen what 'lowest' does to an Operator's wallet."
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional, Sequence

from app.config.settings import PricingStrategy
from app.market.models import ItemOrders, MarketOrder, OrderType


@dataclass(frozen=True)
class PriceQuote:
    lowest_sell: Optional[float]
    average_sell: Optional[float]
    median_sell: Optional[float]
    recommended_price: Optional[float]
    sample_size: int
    strategy_used: PricingStrategy


class PriceAnalyzer:
    """Computes price quotes for an item from its currently visible orders.

    'RECOMMENDED' does not simply take the lowest listing: an anomalously
    cheap outlier (a typo, a rush-sale, a bait listing) can badly distort
    a naive minimum. Instead RECOMMENDED trims obvious low-end outliers
    before picking a competitive-but-sane price near the low end of what
    remains.
    """

    def __init__(self, outlier_trim_ratio: float = 0.15) -> None:
        # Fraction of the *cheapest* prices considered "possibly anomalous"
        # and excluded from RECOMMENDED when there is enough sample size
        # to safely do so.
        self._outlier_trim_ratio = outlier_trim_ratio

    def analyze(
        self,
        item_orders: ItemOrders,
        strategy: PricingStrategy = PricingStrategy.RECOMMENDED,
        online_only: bool = True,
        mod_rank: Optional[int] = None,
    ) -> PriceQuote:
        prices = self._eligible_sell_prices(item_orders.sell_orders, online_only, mod_rank)

        if not prices:
            return PriceQuote(
                lowest_sell=None,
                average_sell=None,
                median_sell=None,
                recommended_price=None,
                sample_size=0,
                strategy_used=strategy,
            )

        prices_sorted = sorted(prices)
        lowest = prices_sorted[0]
        average = round(statistics.fmean(prices_sorted), 2)
        median = round(statistics.median(prices_sorted), 2)
        recommended = self._recommended_price(prices_sorted)

        chosen = {
            PricingStrategy.LOWEST: lowest,
            PricingStrategy.AVERAGE: average,
            PricingStrategy.MEDIAN: median,
            PricingStrategy.RECOMMENDED: recommended,
        }[strategy]

        return PriceQuote(
            lowest_sell=lowest,
            average_sell=average,
            median_sell=median,
            recommended_price=chosen,
            sample_size=len(prices_sorted),
            strategy_used=strategy,
        )

    # -- internal ------------------------------------------------------

    @staticmethod
    def _eligible_sell_prices(
        orders: Sequence[MarketOrder], online_only: bool, mod_rank: Optional[int] = None
    ) -> list[float]:
        eligible = [
            o
            for o in orders
            if o.order_type == OrderType.SELL and (o.user_online or not online_only)
        ]
        if mod_rank is not None:
            # Rank-specific pricing: a rank-0 order (or one that simply
            # didn't specify a rank at all) is treated as equivalent to
            # 'unranked' -- everything else must match the exact rank
            # requested, since a rank-10 mod and a rank-0 mod are not the
            # same product even though they share a catalog entry.
            eligible = [
                o
                for o in eligible
                if o.mod_rank == mod_rank or (mod_rank == 0 and o.mod_rank is None)
            ]
        return [o.platinum for o in eligible]

    def _recommended_price(self, prices_sorted: list[float]) -> float:
        n = len(prices_sorted)
        if n < 4:
            # Too few data points to safely discard anything -- Ordis
            # is not that brave.
            return prices_sorted[0]

        trim_count = max(0, int(n * self._outlier_trim_ratio))
        trimmed = prices_sorted[trim_count:] if trim_count < n - 1 else prices_sorted

        if not trimmed:
            trimmed = prices_sorted

        # Recommend just under the cheapest *non-anomalous* listing so the
        # Operator stays competitive without racing an outlier to the
        # bottom.
        floor = trimmed[0]
        recommended = floor - 1 if floor > 1 else floor
        return round(max(recommended, 1), 2)
