"""
market.sell_score
==================

SellScoreAnalyzer combines price + liquidity + quantity owned into a
single 0-100 score and a plain recommendation.

Ordis: "I have distilled your entire financial situation into one number.
        I hope that is not too much power for a single Cephalon."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.market.liquidity import LiquidityLevel, LiquidityReport
from app.market.pricing import PriceQuote


class Recommendation(str, Enum):
    SELL = "SELL"
    CONSIDER = "CONSIDER"
    KEEP = "KEEP"
    UNKNOWN = "UNKNOWN"


_LIQUIDITY_POINTS = {
    LiquidityLevel.VERY_HIGH: 30,
    LiquidityLevel.HIGH: 24,
    LiquidityLevel.MEDIUM: 15,
    LiquidityLevel.LOW: 7,
    LiquidityLevel.VERY_LOW: 2,
    LiquidityLevel.UNKNOWN: 0,
}


@dataclass(frozen=True)
class SellScoreResult:
    score: int  # 0-100
    recommendation: Recommendation
    reasons: tuple[str, ...] = field(default_factory=tuple)


class SellScoreAnalyzer:
    """Scores a single owned item stack (price quote x liquidity x
    quantity) on a 0-100 scale.

    Weighting (out of 100):
      * up to 30 points -- liquidity
      * up to 30 points -- total stack value (quantity x recommended price)
      * up to 25 points -- price quality (recommended vs. lowest available,
        rewarding items that aren't in a race-to-the-bottom)
      * up to 15 points -- quantity owned beyond a single "keep one" copy
        (extra copies of anything are natural sell candidates)
    """

    def __init__(
        self,
        high_value_plat_threshold: float = 150.0,
        sell_threshold: int = 65,
        consider_threshold: int = 35,
    ) -> None:
        # Guarded against zero/negative so a misconfigured threshold can
        # never cause a ZeroDivisionError in score() below -- clamped once
        # here rather than checked on every score() call.
        self._high_value_threshold = max(high_value_plat_threshold, 0.01)
        self._sell_threshold = sell_threshold
        self._consider_threshold = consider_threshold

    def score(
        self,
        price: PriceQuote,
        liquidity: LiquidityReport,
        quantity_owned: int,
    ) -> SellScoreResult:
        if price.recommended_price is None or liquidity.level == LiquidityLevel.UNKNOWN:
            return SellScoreResult(
                score=0,
                recommendation=Recommendation.UNKNOWN,
                reasons=("No usable market data was found for this item.",),
            )

        reasons: list[str] = []
        total_value = price.recommended_price * quantity_owned

        liquidity_points = _LIQUIDITY_POINTS[liquidity.level]
        if liquidity_points >= 24:
            reasons.append("High liquidity")
        elif liquidity_points <= 7:
            reasons.append("Low liquidity")

        value_points = min(30, round((total_value / self._high_value_threshold) * 30))
        if total_value >= self._high_value_threshold:
            reasons.append("High total value")

        price_quality_points = 25
        if price.lowest_sell and price.recommended_price:
            gap_ratio = (price.recommended_price - price.lowest_sell) / max(price.lowest_sell, 1)
            if gap_ratio < -0.5:
                # Recommended price sits far below lowest-listed -- unusual,
                # treat cautiously.
                price_quality_points = 10
            elif price.sample_size <= 1:
                price_quality_points = 12
                reasons.append("Only one visible listing (price may be unreliable)")
        else:
            price_quality_points = 5

        if price_quality_points >= 20:
            reasons.append("Good price")

        quantity_points = min(15, max(0, quantity_owned - 1) * 5)
        if quantity_owned > 1:
            reasons.append(f"You own {quantity_owned} (extra copies beyond one)")

        total_score = min(
            100, liquidity_points + value_points + price_quality_points + quantity_points
        )

        if total_score >= self._sell_threshold:
            recommendation = Recommendation.SELL
            reasons.insert(0, "Strong demand" if liquidity_points >= 24 else "Decent opportunity")
        elif total_score >= self._consider_threshold:
            recommendation = Recommendation.CONSIDER
        else:
            recommendation = Recommendation.KEEP

        return SellScoreResult(
            score=total_score, recommendation=recommendation, reasons=tuple(reasons)
        )
