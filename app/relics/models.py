"""
relics.models
=============

Plain data for the Relics tab: which relics exist, what they drop, and which
Prime parts make up each Prime set. No I/O and no Qt in here.

Ordis: "Relics, Operator. Small glowing boxes of regret and occasional
        Forma."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

REFINEMENTS = ("Intact", "Exceptional", "Flawless", "Radiant")
ERAS = ("Lith", "Meso", "Neo", "Axi")


def norm(text: str) -> str:
    """Lower-cases and drops everything but letters/digits, so that an
    inventory id ('gyre_prime_chassis_blueprint'), an internal path segment
    ('GyrePrimeChassisBlueprint') and a display name ('Gyre Prime Chassis
    Blueprint') all reduce to the same token."""
    return _NON_ALNUM.sub("", text.lower())


@dataclass(frozen=True)
class RelicReward:
    part_key: str  # norm()-ed internal key of the part, e.g. 'gyreprimechassisblueprint'
    rarity: str  # 'Common' | 'Uncommon' | 'Rare'
    chance: float  # percent, for THIS relic's refinement


@dataclass(frozen=True)
class Relic:
    key: str  # norm()-ed internal key, e.g. 't1voidprojectiongyreprimedbronze'
    name: str  # in-game name, e.g. 'Lith G14 Intact'
    era: str  # 'Lith' | 'Meso' | 'Neo' | 'Axi'
    code: str  # 'G14'
    refinement: str  # one of REFINEMENTS
    vaulted: bool
    rewards: tuple[RelicReward, ...]

    @property
    def short_name(self) -> str:
        return f"{self.era} {self.code}"


@dataclass(frozen=True)
class PrimePart:
    key: str  # norm()-ed internal key of the part as relics drop it
    name: str  # display name, e.g. 'Gyre Prime Chassis Blueprint'
    need: int = 1  # how many the set's recipe consumes
    alt_keys: tuple[str, ...] = ()  # other keys that count as owning it (the built Component)


@dataclass(frozen=True)
class PrimeSet:
    name: str  # e.g. 'Gyre Prime'
    parts: tuple[PrimePart, ...]


@dataclass(frozen=True)
class RelicData:
    relics: tuple[Relic, ...] = ()
    sets: tuple[PrimeSet, ...] = ()
    fetched_at: float = 0.0
    _by_key: dict = field(default_factory=dict, repr=False, compare=False)
    _by_name: dict = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_key", {r.key: r for r in self.relics})
        object.__setattr__(self, "_by_name", {norm(r.name): r for r in self.relics})

    def find_relic(self, inventory_id: str) -> Optional[Relic]:
        """Matches an inventory id by internal key or by in-game name."""
        token = norm(inventory_id)
        return self._by_key.get(token) or self._by_name.get(token)

    def __bool__(self) -> bool:
        return bool(self.relics and self.sets)
