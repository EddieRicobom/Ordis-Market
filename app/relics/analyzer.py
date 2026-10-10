"""
relics.analyzer
===============

Cross-references what the Operator owns (Prime parts and relics, from the
imported inventory) with the relic drop tables, and reports for every Prime
set which parts are still missing and which of the Operator's own relics
could drop them.

Pure calculation: no I/O, no Qt.

Ordis: "You have three of the four parts, Operator, and a relic that might
        give you the fourth. I would call that hope. Statistically it is
        about one in four."
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from app.inventory.models import InventoryItem
from app.relics.models import REFINEMENTS, PrimePart, PrimeSet, Relic, RelicData, norm


class SetState(str, Enum):
    COMPLETE = "Complete"  # every part is already owned
    COMPLETABLE = "Completable"  # every missing part drops from a relic you own
    PARTIAL = "Partial"  # some missing parts drop from your relics, some don't
    NONE = "Nothing"  # no owned part and no owned relic helps


@dataclass(frozen=True)
class Dropper:
    """One of the Operator's relics (best owned refinement of an era+code)
    that can drop a given part."""

    relic: Relic
    quantity: int  # how many of this era+code relic are owned, all refinements
    rarity: str
    chance: float  # percent per opening, at the best owned refinement
    all_chance: float  # percent to get the part if EVERY owned copy (each at its own refinement) is opened


@dataclass(frozen=True)
class PartStatus:
    part: PrimePart
    owned: int
    droppers: tuple[Dropper, ...]  # best chance first; empty if no owned relic drops it

    @property
    def missing(self) -> int:
        return max(self.part.need - self.owned, 0)


@dataclass(frozen=True)
class OpenSuggestion:
    """Open this relic: it covers these still-missing parts."""

    relic: Relic
    quantity: int
    covers: tuple[PrimePart, ...]


@dataclass(frozen=True)
class SetStatus:
    prime_set: PrimeSet
    parts: tuple[PartStatus, ...]
    state: SetState
    suggestions: tuple[OpenSuggestion, ...]

    @property
    def need_units(self) -> int:
        return sum(p.part.need for p in self.parts)

    @property
    def owned_units(self) -> int:
        return sum(min(p.owned, p.part.need) for p in self.parts)

    @property
    def missing_parts(self) -> tuple[PartStatus, ...]:
        return tuple(p for p in self.parts if p.missing > 0)


@dataclass(frozen=True)
class RelicsReport:
    sets: tuple[SetStatus, ...]
    owned_relic_kinds: int  # distinct relics (era + code), any refinement
    owned_relic_total: int  # total relics counting quantities
    unmatched_relic_ids: tuple[str, ...]  # relic-looking ids we have no drop data for


def _owned_tokens(items: Iterable[InventoryItem]) -> dict[str, int]:
    owned: dict[str, int] = defaultdict(int)
    for item in items:
        owned[norm(item.item_id)] += item.quantity
    return owned


def _owned_part_count(part: PrimePart, owned: dict[str, int]) -> int:
    keys = {part.key, norm(part.name), *part.alt_keys}  # internal path form or display-name form
    return sum(owned.get(k, 0) for k in keys)


def _owned_relics(items: Iterable[InventoryItem], data: RelicData) -> tuple[dict[str, tuple[Relic, int]], list[str]]:
    owned: dict[str, tuple[Relic, int]] = {}
    unmatched: list[str] = []
    for item in items:
        token = norm(item.item_id)
        if "voidprojection" not in token and not _looks_like_relic_name(item.item_id):
            continue
        relic = data.find_relic(item.item_id)
        if relic is None:
            if not token.startswith("t5voidprojection"):  # Requiem relics never drop Prime parts
                unmatched.append(item.item_id)
            continue
        previous = owned.get(relic.key)
        owned[relic.key] = (relic, (previous[1] if previous else 0) + item.quantity)
    return owned, unmatched


def _looks_like_relic_name(item_id: str) -> bool:
    token = norm(item_id)
    return any(token.startswith(era.lower()) and token.endswith(ref.lower()) for era in ("lith", "meso", "neo", "axi") for ref in REFINEMENTS)


def _droppers_by_part(owned_relics: dict[str, tuple[Relic, int]]) -> dict[str, list[Dropper]]:
    """part key -> the owned relics that drop it, one entry per era+code
    (the best owned refinement), best chance first."""
    best: dict[tuple[str, str, str], Dropper] = {}  # (era, code, part key) -> dropper
    miss_all: dict[tuple[str, str, str], float] = defaultdict(lambda: 1.0)  # P(no drop in any opening)
    quantity_by_relic: dict[tuple[str, str], int] = defaultdict(int)
    for relic, qty in owned_relics.values():
        quantity_by_relic[(relic.era, relic.code)] += qty
    for relic, qty in owned_relics.values():
        for reward in relic.rewards:
            slot = (relic.era, relic.code, reward.part_key)
            miss_all[slot] *= (1.0 - reward.chance / 100.0) ** qty
            current = best.get(slot)
            if current is None or reward.chance > current.chance:
                best[slot] = Dropper(
                    relic=relic,
                    quantity=quantity_by_relic[(relic.era, relic.code)],
                    rarity=reward.rarity,
                    chance=reward.chance,
                    all_chance=0.0,
                )
    for slot, dropper in list(best.items()):
        best[slot] = Dropper(
            relic=dropper.relic,
            quantity=dropper.quantity,
            rarity=dropper.rarity,
            chance=dropper.chance,
            all_chance=round((1.0 - miss_all[slot]) * 100.0, 2),
        )
    by_part: dict[str, list[Dropper]] = defaultdict(list)
    for (_era, _code, part_key), dropper in best.items():
        by_part[part_key].append(dropper)
    for droppers in by_part.values():
        droppers.sort(key=lambda d: (-d.chance, d.relic.vaulted, d.relic.short_name))
    return by_part


def _suggest(missing: list[PartStatus]) -> tuple[OpenSuggestion, ...]:
    """Greedy cover: repeatedly pick the owned relic that covers the most
    still-uncovered missing parts (ties: higher combined drop chance)."""
    uncovered = {p.part.key: p for p in missing if p.droppers}
    relic_covers: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    relic_ref: dict[tuple[str, str], Dropper] = {}
    for status in uncovered.values():
        for dropper in status.droppers:
            slot = (dropper.relic.era, dropper.relic.code)
            relic_covers[slot][status.part.key] = dropper.chance
            relic_ref.setdefault(slot, dropper)

    suggestions: list[OpenSuggestion] = []
    while uncovered:
        scored = [
            (len(set(covers) & set(uncovered)), sum(c for k, c in covers.items() if k in uncovered), slot)
            for slot, covers in relic_covers.items()
        ]
        scored = [s for s in scored if s[0] > 0]
        if not scored:
            break
        _count, _chance, slot = max(scored, key=lambda s: (s[0], s[1]))
        covered_now = [uncovered[k].part for k in relic_covers[slot] if k in uncovered]
        ref = relic_ref[slot]
        suggestions.append(OpenSuggestion(relic=ref.relic, quantity=ref.quantity, covers=tuple(covered_now)))
        for part in covered_now:
            uncovered.pop(part.key, None)
    return tuple(suggestions)


def analyze_relics(items: Iterable[InventoryItem], data: RelicData) -> RelicsReport:
    items = list(items)
    owned_parts = _owned_tokens(items)
    owned_relics, unmatched = _owned_relics(items, data)
    droppers = _droppers_by_part(owned_relics)

    statuses: list[SetStatus] = []
    for prime_set in data.sets:
        parts = tuple(
            PartStatus(
                part=part,
                owned=_owned_part_count(part, owned_parts),
                droppers=tuple(droppers.get(part.key, ())),
            )
            for part in prime_set.parts
        )
        missing = [p for p in parts if p.missing > 0]
        if not missing:
            state = SetState.COMPLETE
        elif all(p.droppers for p in missing):
            state = SetState.COMPLETABLE
        elif any(p.droppers for p in missing) or any(p.owned for p in parts):
            state = SetState.PARTIAL
        else:
            state = SetState.NONE
        statuses.append(
            SetStatus(
                prime_set=prime_set,
                parts=parts,
                state=state,
                suggestions=_suggest(missing) if missing else (),
            )
        )

    kinds = {(r.era, r.code) for r, _q in owned_relics.values()}
    return RelicsReport(
        sets=tuple(statuses),
        owned_relic_kinds=len(kinds),
        owned_relic_total=sum(q for _r, q in owned_relics.values()),
        unmatched_relic_ids=tuple(sorted(set(unmatched))),
    )
