"""
relics.view
===========

Presentation logic for the Relics tab, kept free of Qt so it can be tested:
which sets to show for a filter, in what order, and the text for each cell.

Ordis: "I have sorted them by how close you are to being finished. It is
        motivating. Or humiliating. Depends on the row."
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from app.relics.analyzer import Dropper, SetState, SetStatus
from app.relics.models import PrimePart


class FilterMode(str, Enum):
    COMPLETABLE = "Can be completed with my relics"
    CLOSEST = "Partly covered by my relics"
    COMPLETE = "Already complete"
    OWNED = "Every set I hold a part of"
    ALL = "All Prime sets"


_STATE_RANK = {
    SetState.COMPLETABLE: 0,
    SetState.PARTIAL: 1,
    SetState.COMPLETE: 2,
    SetState.NONE: 3,
}


def state_rank(state: SetState) -> int:
    return _STATE_RANK[state]


def filter_statuses(statuses: Iterable[SetStatus], mode: FilterMode, query: str = "") -> list[SetStatus]:
    needle = query.strip().lower()

    def wanted(status: SetStatus) -> bool:
        if needle and needle not in status.prime_set.name.lower():
            return False
        if mode is FilterMode.COMPLETABLE:
            return status.state is SetState.COMPLETABLE and status.owned_units > 0
        if mode is FilterMode.CLOSEST:
            return status.state is SetState.PARTIAL and status.owned_units > 0
        if mode is FilterMode.COMPLETE:
            return status.state is SetState.COMPLETE
        if mode is FilterMode.OWNED:
            return status.owned_units > 0
        return True

    return sort_statuses(s for s in statuses if wanted(s))


def sort_statuses(statuses: Iterable[SetStatus]) -> list[SetStatus]:
    """Most actionable first: completable before partial, then the set you are
    furthest along with, then the one needing the fewest relic openings."""

    def key(status: SetStatus):
        progress = status.owned_units / status.need_units if status.need_units else 0.0
        return (state_rank(status.state), -progress, len(status.suggestions), status.prime_set.name)

    return sorted(statuses, key=key)


def short_part_name(part: PrimePart, set_name: str) -> str:
    """'Gyre Prime Chassis Blueprint' -> 'Chassis Blueprint' (inside a row that
    already names the set)."""
    prefix = set_name + " "
    return part.name[len(prefix):] if part.name.startswith(prefix) else part.name


def parts_text(status: SetStatus) -> str:
    return f"{status.owned_units}/{status.need_units}"


def missing_text(status: SetStatus) -> str:
    if status.state is SetState.COMPLETE:
        return "-"
    labels = []
    for part_status in status.missing_parts:
        label = short_part_name(part_status.part, status.prime_set.name)
        if part_status.missing > 1:
            label += f" ×{part_status.missing}"
        labels.append(label)
    return ", ".join(labels)


def open_text(status: SetStatus) -> str:
    """'Neo C9 ×11 → Blueprint; Lith S18 ×4 → String'"""
    if status.state is SetState.COMPLETE:
        return "Nothing to open -- ready to build"
    chunks = []
    for suggestion in status.suggestions:
        covers = ", ".join(short_part_name(p, status.prime_set.name) for p in suggestion.covers)
        chunks.append(f"{suggestion.relic.short_name} ×{suggestion.quantity} → {covers}")
    uncovered = [
        short_part_name(p.part, status.prime_set.name) for p in status.missing_parts if not p.droppers
    ]
    if uncovered:
        chunks.append("no relic of yours drops: " + ", ".join(uncovered))
    return "; ".join(chunks) if chunks else "-"


def _dropper_line(dropper: Dropper) -> str:
    relic = dropper.relic
    vaulted = ", vaulted" if relic.vaulted else ""
    return (
        f"{relic.short_name} ({relic.refinement}{vaulted}) ×{dropper.quantity}: "
        f"{dropper.chance:g}% per opening ({dropper.rarity}), "
        f"{dropper.all_chance:g}% if you open all of yours"
    )


def detail_text(status: SetStatus) -> str:
    """Multi-line breakdown shown under the table for the selected set."""
    lines = [f"{status.prime_set.name} -- {status.state.value}, {parts_text(status)} parts"]
    for part_status in status.parts:
        part = part_status.part
        label = short_part_name(part, status.prime_set.name)
        have = f"{min(part_status.owned, part.need)}/{part.need}"
        if part_status.missing == 0:
            lines.append(f"  [x] {label}  ({have})")
            continue
        lines.append(f"  [ ] {label}  ({have})")
        if not part_status.droppers:
            lines.append("        none of your relics drop this")
        for dropper in part_status.droppers[:4]:
            lines.append("        " + _dropper_line(dropper))
        if len(part_status.droppers) > 4:
            lines.append(f"        ... and {len(part_status.droppers) - 4} more of your relics")
    return "\n".join(lines)
