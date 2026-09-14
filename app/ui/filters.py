"""
ui.filters
==========

Pure-Python filter/sort helper logic used by the dashboard table.

Kept deliberately free of any PySide6 import so it can be unit-tested on
its own, without a Qt runtime available -- main_window.py imports these
rather than redefining them inline.
"""

from __future__ import annotations

import re

# Matches a display name ending in "... Prime Set" (case-insensitive,
# tolerant of trailing whitespace) -- used by the "Hide Prime Sets"
# filter, since a full assembled set's price is often not what someone
# comparing individual component prices wants to see.
_PRIME_SET_PATTERN = re.compile(r"\bprime set\b\s*$", re.IGNORECASE)

# Ordinal rank so text columns with a natural order (not just
# alphabetical) sort sensibly when the table's click-to-sort is used.
LIQUIDITY_SORT_RANK = {
    "VERY HIGH": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "VERY LOW": 1,
    "N/A": 0,
}
RECOMMENDATION_SORT_RANK = {"SELL": 3, "CONSIDER": 2, "KEEP": 1, "UNKNOWN": 0}


def is_prime_set_name(display_name: str) -> bool:
    return bool(_PRIME_SET_PATTERN.search(display_name.strip()))
