"""
home.targets
============

Where a click on the Home can take the Operator. Plain strings so the Home
(presentation) never has to know how MainWindow implements each screen.
"""

from __future__ import annotations

from enum import Enum


class Target(str, Enum):
    MARKET = "market"  # the Market tab, filters reset
    MARKET_TRADABLE = "market_tradable"  # Market, "Tradable Only"
    MARKET_PRIME_SETS = "market_prime_sets"  # Market, searching "prime set"
    MARKET_BY_SCORE = "market_by_score"  # Market, best sell score first
    MARKET_BY_QTY = "market_by_qty"  # Market, biggest stacks first
    MARKET_BY_DUCATS = "market_by_ducats"  # Market, best Ducat deals first
    RELICS = "relics"  # the Relics tab
    RELICS_READY = "relics_ready"  # Relics, "Already complete"
    RELICS_ONE_AWAY = "relics_one_away"  # Relics, "Every set I hold a part of"
    RELICS_COMPLETABLE = "relics_completable"  # Relics, "Can be completed with my relics"
