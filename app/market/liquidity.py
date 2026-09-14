"""
market.liquidity
=================

LiquidityAnalyzer estimates how easily an item could actually be sold,
based only on data we truly have (visible order counts / online sellers).

Ordis: "Liquidity is not a feeling, Operator. It is a count of how many
        people currently want your junk. I do not fabricate this number."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.market.models import ItemOrders, OrderType


class LiquidityLevel(str, Enum):
    VERY_HIGH = "VERY HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY LOW"
    UNKNOWN = "N/A"


@dataclass(frozen=True)
class LiquidityReport:
    level: LiquidityLevel
    online_sell_count: int
    online_buy_count: int
    spread: float | None  # cheapest sell - highest buy, if both exist


class LiquidityAnalyzer:
    """Classifies liquidity from visible order counts.

    We never invent volume/trend data we do not have. If the market
    response gives us nothing usable, the verdict is UNKNOWN -- not a
    guess dressed up as a number.
    """

    # Thresholds are on "distinct online sell listings", the most honest
    # proxy we have for "could I actually sell this soon".
    _THRESHOLDS = (
        (15, LiquidityLevel.VERY_HIGH),
        (8, LiquidityLevel.HIGH),
        (3, LiquidityLevel.MEDIUM),
        (1, LiquidityLevel.LOW),
    )

    def analyze(self, item_orders: ItemOrders) -> LiquidityReport:
        online_sells = [
            o for o in item_orders.sell_orders if o.order_type == OrderType.SELL and o.user_online
        ]
        online_buys = [
            o for o in item_orders.buy_orders if o.order_type == OrderType.BUY and o.user_online
        ]

        if not item_orders.sell_orders and not item_orders.buy_orders:
            return LiquidityReport(
                level=LiquidityLevel.UNKNOWN,
                online_sell_count=0,
                online_buy_count=0,
                spread=None,
            )

        level = LiquidityLevel.VERY_LOW
        for threshold, candidate_level in self._THRESHOLDS:
            if len(online_sells) >= threshold:
                level = candidate_level
                break

        spread = None
        if online_sells and online_buys:
            cheapest_sell = min(o.platinum for o in online_sells)
            highest_buy = max(o.platinum for o in online_buys)
            spread = round(cheapest_sell - highest_buy, 2)

        return LiquidityReport(
            level=level,
            online_sell_count=len(online_sells),
            online_buy_count=len(online_buys),
            spread=spread,
        )
