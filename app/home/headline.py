"""
home.headline
=============

The one line Ordis says at the top of the Home. A fixed set of lines picked by
simple conditions, in priority order. No generation, no randomness that
changes while you look: the pick is stable for a given situation and day.

Ordis: "I have a line for every occasion. Several, in fact. I rotate them
        daily so you do not notice."
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.home.schedule import SOON, BaroPhase, BaroStatus, ResurgenceStatus
from app.home.summary import MANY_TRADABLE, InventorySummary, SetsSummary


@dataclass(frozen=True)
class HeadlineContext:
    now_local_date: date
    now_utc: datetime
    baro: BaroStatus
    resurgence: ResurgenceStatus
    has_inventory: bool
    summary: Optional[InventorySummary]
    sets: Optional[SetsSummary]


LINES = {
    "baro_here": [
        "The Void Trader is aboard the relay, Operator. Check your Ducats before he leaves.",
        "Baro Ki'Teer has arrived. Your spare Prime parts may have found a purpose.",
    ],
    "baro_soon": [
        "The merchant is approaching. I recommend checking your Ducats.",
        "Baro Ki'Teer will be here soon. Spare Prime parts do not trade themselves.",
    ],
    "resurgence_soon": [
        "A new Prime rotation approaches, Operator.",
        "The Prime Resurgence is about to change. Varzia will not wait for us.",
    ],
    "sets_ready": [
        "Operator, I found Prime sets ready for trade.",
        "You are holding complete Prime sets. I would call that a good day.",
    ],
    "many_tradable": [
        "Operator, I have detected a worrying amount of tradable items.",
        "So many tradable items. I have started to feel responsible.",
    ],
    "sets_close": [
        "Some Prime sets are one part away from completion. How tantalising.",
        "A single part separates you from a finished set, Operator. Perhaps two. I rounded.",
    ],
    "no_inventory": [
        "I have no inventory to judge yet, Operator. Show me what you are hoarding.",
        "Import your inventory and I will tell you what it is worth. Gently.",
    ],
    "not_analyzed": [
        "Your inventory is here, but unpriced. Shall we ask the market?",
    ],
    "calm": [
        "All quiet, Operator. The market is behaving. I am suspicious.",
        "Nothing urgent. I will keep watching anyway.",
        "Systems nominal. Your inventory remains, regrettably, yours to manage.",
    ],
}


def _pick(key: str, today: date) -> str:
    pool = LINES[key]
    return pool[zlib.crc32(f"{key}:{today.isoformat()}".encode()) % len(pool)]


def headline_key(ctx: HeadlineContext) -> str:
    if ctx.baro.phase is BaroPhase.PRESENT:
        return "baro_here"
    if ctx.baro.arrival - ctx.now_utc <= SOON:
        return "baro_soon"
    if ctx.resurgence.next_reset - ctx.now_utc <= SOON:
        return "resurgence_soon"
    if not ctx.has_inventory:
        return "no_inventory"
    if ctx.summary is None:
        return "not_analyzed"
    if ctx.sets is not None and ctx.sets.ready:
        return "sets_ready"
    if ctx.summary.tradable_items >= MANY_TRADABLE:
        return "many_tradable"
    if ctx.sets is not None and ctx.sets.one_away:
        return "sets_close"
    return "calm"


def pick_headline(ctx: HeadlineContext) -> str:
    return _pick(headline_key(ctx), ctx.now_local_date)
