"""
market.sets
===========

SetAnalyzer compares "sell components separately" vs. "sell (or value)
the assembled set" for Prime items composed of multiple parts.

Ordis: "Some things are worth more together. Like us, Operator. Mostly
        the items, though. I am statistically less liquid."
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class SetComparison:
    set_slug: str
    component_value_total: float
    set_value: Optional[float]
    difference: Optional[float]  # set_value - component_value_total
    better_as_set: Optional[bool]


class SetAnalyzer:
    """Pure calculation: given a set's own market price and the summed
    price of its components, report which is more profitable.

    This performs no market I/O itself -- callers supply prices already
    resolved via PriceAnalyzer for the set slug and each component slug.
    """

    def compare(
        self,
        set_slug: str,
        set_value: Optional[float],
        component_prices: Mapping[str, float],
    ) -> SetComparison:
        component_total = round(sum(component_prices.values()), 2) if component_prices else 0.0

        if set_value is None or not component_prices:
            return SetComparison(
                set_slug=set_slug,
                component_value_total=component_total,
                set_value=set_value,
                difference=None,
                better_as_set=None,
            )

        difference = round(set_value - component_total, 2)
        return SetComparison(
            set_slug=set_slug,
            component_value_total=component_total,
            set_value=set_value,
            difference=difference,
            better_as_set=difference > 0,
        )
