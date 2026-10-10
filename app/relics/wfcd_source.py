"""
relics.wfcd_source
==================

Builds RelicData from the community-maintained WFCD "warframe-items" dataset
(https://github.com/WFCD/warframe-items), which is derived from Digital
Extremes' own exports.

Two inputs:

* Relics.json -- every relic (all four refinements) with its six rewards and
  per-refinement drop chances. This alone tells us which Prime sets exist
  and which parts they consist of (checked against the official recipes:
  162 of 164 Prime items match exactly; the other two -- Sagek and Galariak
  Prime -- simply don't drop from any relic).
* Warframes / Primary / Secondary / ... .json -- each Prime item's official
  recipe components, used only for two things relics can't tell us: how many
  of a part the recipe consumes (Akbolto Prime needs 2 barrels, 2 receivers)
  and that a Warframe part's built "Component" counts as owning the
  "Blueprint" that relics drop.

`build_relic_data` is pure (no I/O) so it can be tested with small fixtures.

Ordis: "I did not write these tables, Operator. I merely read them aloud with
        great feeling."
"""

from __future__ import annotations

import logging
import re
import time
from typing import Iterable, Optional

from app.common.http import make_session
from app.relics.models import (
    ERAS,
    REFINEMENTS,
    PrimePart,
    PrimeSet,
    Relic,
    RelicData,
    RelicReward,
    norm,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://raw.githubusercontent.com/WFCD/warframe-items/master/data/json/"
RELICS_FILE = "Relics.json"
REQUIRED_ITEM_FILES = ("Warframes.json", "Primary.json", "Secondary.json", "Melee.json")
OPTIONAL_ITEM_FILES = (
    "Archwing.json",
    "Arch-Gun.json",
    "Arch-Melee.json",
    "Sentinels.json",
    "Pets.json",
)

_RELIC_NAME = re.compile(
    r"^(?P<era>" + "|".join(ERAS) + r") (?P<code>\S+) (?P<refinement>" + "|".join(REFINEMENTS) + r")$"
)
_SET_PREFIX = re.compile(r"^(?P<set>.*? Prime)\b")
_PRIME_WORD = re.compile(r"\bPrime\b")


class RelicDataError(Exception):
    """The relic dataset could not be downloaded or understood."""


def parse_relic_name(name: str) -> Optional[tuple[str, str, str]]:
    """'Lith G14 Intact' -> ('Lith', 'G14', 'Intact'); None for anything else
    (e.g. Requiem relics, which don't drop Prime parts)."""
    match = _RELIC_NAME.match(name.strip())
    if not match:
        return None
    return match["era"], match["code"], match["refinement"]


def part_key(unique_name: str) -> str:
    """'/Lotus/Types/Recipes/Weapons/WeaponParts/AkboltoPrimeBarrel' ->
    'akboltoprimebarrel' (the same token an inventory id reduces to)."""
    return norm(unique_name.rstrip("/").rsplit("/", 1)[-1])


def _blueprint_alias(key: str) -> str:
    # A Warframe's built part ('...chassiscomponent') is what the recipe
    # consumes; relics drop its blueprint ('...chassisblueprint').
    return key[: -len("component")] + "blueprint" if key.endswith("component") else key


def _parse_relics(relics_json: Iterable[dict]) -> tuple[list[Relic], dict[str, str]]:
    relics: list[Relic] = []
    part_names: dict[str, str] = {}
    for raw in relics_json:
        parsed = parse_relic_name(str(raw.get("name", "")))
        if parsed is None:
            continue
        era, code, refinement = parsed
        rewards: list[RelicReward] = []
        for reward in raw.get("rewards") or []:
            item = reward.get("item") or {}
            name = str(item.get("name", ""))
            unique = str(item.get("uniqueName", ""))
            if not unique or not _PRIME_WORD.search(name):
                continue  # Forma and other non-Prime rewards don't matter here
            key = part_key(unique)
            part_names[key] = name
            rewards.append(
                RelicReward(
                    part_key=key,
                    rarity=str(reward.get("rarity", "")),
                    chance=float(reward.get("chance") or 0.0),
                )
            )
        if not rewards:
            continue
        relics.append(
            Relic(
                key=part_key(str(raw.get("uniqueName", ""))),
                name=f"{era} {code} {refinement}",
                era=era,
                code=code,
                refinement=refinement,
                vaulted=bool(raw.get("vaulted", False)),
                rewards=tuple(rewards),
            )
        )
    return relics, part_names


def _official_recipes(item_files: Iterable[Iterable[dict]]) -> dict[str, dict[str, tuple[int, str]]]:
    """set name -> {part key (blueprint-aliased): (count needed, original key)}."""
    official: dict[str, dict[str, tuple[int, str]]] = {}
    for items in item_files:
        for item in items:
            name = str(item.get("name", ""))
            if not name.endswith(" Prime"):
                continue
            parts: dict[str, tuple[int, str]] = {}
            for component in item.get("components") or []:
                unique = str(component.get("uniqueName", ""))
                if "/Recipes/" not in unique:
                    continue  # resources (Orokin Cells, Plastids...) aren't relic parts
                original = part_key(unique)
                parts[_blueprint_alias(original)] = (int(component.get("itemCount") or 1), original)
            if parts:
                official[name] = parts
    return official


def build_relic_data(
    relics_json: Iterable[dict],
    item_files: Iterable[Iterable[dict]] = (),
    fetched_at: Optional[float] = None,
) -> RelicData:
    relics, part_names = _parse_relics(relics_json)
    official = _official_recipes(item_files)

    keys_by_set: dict[str, list[str]] = {}
    for key, name in part_names.items():
        match = _SET_PREFIX.match(name)
        if match:
            keys_by_set.setdefault(match["set"], []).append(key)

    sets: list[PrimeSet] = []
    for set_name in sorted(keys_by_set):
        recipe = official.get(set_name, {})
        parts = []
        for key in sorted(keys_by_set[set_name], key=lambda k: part_names[k]):
            need, original = recipe.get(key, (1, key))
            parts.append(
                PrimePart(
                    key=key,
                    name=part_names[key],
                    need=max(need, 1),
                    alt_keys=(original,) if original != key else (),
                )
            )
        sets.append(PrimeSet(name=set_name, parts=tuple(parts)))

    era_order = {era: i for i, era in enumerate(ERAS)}
    relics.sort(key=lambda r: (era_order.get(r.era, 99), r.code.rjust(4), REFINEMENTS.index(r.refinement)))
    return RelicData(
        relics=tuple(relics),
        sets=tuple(sets),
        fetched_at=time.time() if fetched_at is None else fetched_at,
    )


def _get_json(session, filename: str, timeout: int):
    try:
        response = session.get(BASE_URL + filename, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001 - network, HTTP and JSON errors alike
        raise RelicDataError(f"Could not download {filename}: {exc}") from exc


def fetch_relic_data(session=None, timeout: int = 90) -> RelicData:
    """Downloads the dataset and builds RelicData. Raises RelicDataError if
    the relics (or a recipe file needed for correct part counts) cannot be
    fetched -- better to keep the previous cache than to store wrong data."""
    session = session or make_session()
    relics_json = _get_json(session, RELICS_FILE, timeout)
    if not isinstance(relics_json, list):
        raise RelicDataError("Relics.json did not contain a list of relics.")

    item_files = [_get_json(session, name, timeout) for name in REQUIRED_ITEM_FILES]
    for name in OPTIONAL_ITEM_FILES:
        try:
            item_files.append(_get_json(session, name, timeout))
        except RelicDataError:
            logger.warning("Optional relic data file %s unavailable; continuing.", name)

    data = build_relic_data(relics_json, item_files)
    if not data:
        raise RelicDataError("The downloaded data contained no usable relics or Prime sets.")
    return data
