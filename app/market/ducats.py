"""
market.ducats
=============

DucatAnalyzer compares selling a Prime item for Platinum against keeping
it for Ducats (paid out only by trading it in to Baro Ki'Teer / relevant
in-game vendors for void traces, not by warframe.market).

Ordis: "Platinum spends anywhere. Ducats spend on Baro's shelf, four times
        a month, if he feels like showing up. Choose wisely, Operator."
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DucatVerdict(str, Enum):
    SELL_FOR_PLAT = "SELL FOR PLAT"
    KEEP_FOR_DUCATS = "KEEP FOR DUCATS"
    INSUFFICIENT_DATA = "INSUFFICIENT DATA"


@dataclass(frozen=True)
class DucatComparison:
    platinum_price: Optional[float]
    ducats: Optional[int]
    plat_per_ducat: Optional[float]
    reference_plat_per_ducat: float
    verdict: DucatVerdict


class DucatAnalyzer:
    """Compares plat/ducat ratio against a configurable reference value.

    The reference value represents "how much is one Ducat worth to you
    in Platinum terms" -- a personal threshold, since Ducats are spent on
    a fixed, curated Baro Ki'Teer rotation rather than a liquid market.
    """

    def compare(
        self,
        platinum_price: Optional[float],
        ducats: Optional[int],
        reference_plat_per_ducat: float,
    ) -> DucatComparison:
        if platinum_price is None or not ducats:
            return DucatComparison(
                platinum_price=platinum_price,
                ducats=ducats,
                plat_per_ducat=None,
                reference_plat_per_ducat=reference_plat_per_ducat,
                verdict=DucatVerdict.INSUFFICIENT_DATA,
            )

        ratio = round(platinum_price / ducats, 4)
        verdict = (
            DucatVerdict.SELL_FOR_PLAT
            if ratio >= reference_plat_per_ducat
            else DucatVerdict.KEEP_FOR_DUCATS
        )

        return DucatComparison(
            platinum_price=platinum_price,
            ducats=ducats,
            plat_per_ducat=ratio,
            reference_plat_per_ducat=reference_plat_per_ducat,
            verdict=verdict,
        )
