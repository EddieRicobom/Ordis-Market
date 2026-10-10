"""Shared helpers for the relics tests."""

import json
from pathlib import Path

from app.inventory.models import InventoryItem
from app.relics.wfcd_source import build_relic_data

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "wfcd_relics_sample.json"


def raw_fixture() -> dict:
    """A small slice of the real WFCD dataset: every relic (Intact + Radiant)
    that drops a part of Gyre / Akbolto / Cedo Prime, one Requiem relic, and
    the official recipes of those three Prime items."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def real_data():
    raw = raw_fixture()
    return build_relic_data(raw["relics"], raw["items"].values(), fetched_at=1_700_000_000.0)


def inv(item_id: str, quantity: int = 1) -> InventoryItem:
    return InventoryItem(item_id=item_id, quantity=quantity, raw_name=item_id)


def status_for(report, set_name: str):
    return next(s for s in report.sets if s.prime_set.name == set_name)
