"""
relics.store
============

Disk cache for RelicData (data/relic_data.json), so the Relics tab opens
instantly and works offline after the first download.

Only the *derived* data is stored (a few hundred KB), not the ~10 MB of raw
dataset it is built from.

Ordis: "Remembered. Filed. Judged. In that order."
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Callable, Optional

from app.relics.models import PrimePart, PrimeSet, Relic, RelicData, RelicReward
from app.relics.wfcd_source import fetch_relic_data, parse_relic_name

logger = logging.getLogger(__name__)

FORMAT_VERSION = 1
DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # new Primes ship every few months; weekly is plenty


def _to_payload(data: RelicData) -> dict:
    return {
        "version": FORMAT_VERSION,
        "fetched_at": data.fetched_at,
        "relics": [
            {
                "k": r.key,
                "n": r.name,
                "v": r.vaulted,
                "r": [[w.part_key, w.rarity, w.chance] for w in r.rewards],
            }
            for r in data.relics
        ],
        "sets": [
            {"n": s.name, "p": [[p.key, p.name, p.need, list(p.alt_keys)] for p in s.parts]}
            for s in data.sets
        ],
    }


def _from_payload(payload: dict) -> RelicData:
    relics = []
    for raw in payload["relics"]:
        era, code, refinement = parse_relic_name(raw["n"])  # raises TypeError if malformed
        relics.append(
            Relic(
                key=raw["k"],
                name=raw["n"],
                era=era,
                code=code,
                refinement=refinement,
                vaulted=bool(raw["v"]),
                rewards=tuple(RelicReward(k, rarity, float(chance)) for k, rarity, chance in raw["r"]),
            )
        )
    sets = [
        PrimeSet(
            name=raw["n"],
            parts=tuple(PrimePart(k, name, int(need), tuple(alts)) for k, name, need, alts in raw["p"]),
        )
        for raw in payload["sets"]
    ]
    return RelicData(relics=tuple(relics), sets=tuple(sets), fetched_at=float(payload["fetched_at"]))


class RelicDataStore:
    def __init__(self, path: Path, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._path = Path(path)
        self._ttl_seconds = ttl_seconds

    def load(self) -> Optional[RelicData]:
        """The cached data, or None if there is none or it can't be read.
        Never raises: a corrupt cache just means "download it again"."""
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if payload.get("version") != FORMAT_VERSION:
                return None
            data = _from_payload(payload)
        except (OSError, ValueError, KeyError, TypeError):
            return None
        return data or None

    def save(self, data: RelicData) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(_to_payload(data)), encoding="utf-8")
        os.replace(tmp, self._path)  # a crash mid-write can't leave a half-written cache

    def is_stale(self, data: Optional[RelicData]) -> bool:
        return data is None or (time.time() - data.fetched_at) > self._ttl_seconds

    def refresh(self, fetcher: Callable[[], RelicData] = fetch_relic_data) -> RelicData:
        """Downloads fresh data and caches it. Raises RelicDataError on
        failure, leaving any previous cache untouched."""
        data = fetcher()
        try:
            self.save(data)
        except OSError:
            logger.warning("Could not write the relic data cache.", exc_info=True)
        return data
