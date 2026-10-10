"""
home.schedule
=============

Baro Ki'Teer and Prime Resurgence timing, computed locally from their fixed
cycles. No network, no API: just a known anchor date plus the cycle length.

* Baro Ki'Teer: every 14 days, arrives Friday 13:00 UTC, stays 48 hours
  (anchor: Friday 2024-11-01 13:00 UTC).
* Prime Resurgence (Varzia): the vault rotates every 28 days, Thursday
  18:00 UTC (anchor: Thursday 2026-06-11 18:00 UTC).
* Weekly reset: Monday 00:00 UTC.

Both cycles were checked against dates published for 2023-2026. They are
*calculated*, not read from the game: a special event can shift one, so the
UI labels them as estimated.

Everything takes `now` as an argument so it can be tested with fixed times.

Ordis: "I do not look out of the window, Operator. I count. It is more
        reliable. Mostly."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

UTC = timezone.utc

BARO_ANCHOR = datetime(2024, 11, 1, 13, 0, tzinfo=UTC)
BARO_PERIOD = timedelta(days=14)
BARO_STAY = timedelta(hours=48)

RESURGENCE_ANCHOR = datetime(2026, 6, 11, 18, 0, tzinfo=UTC)
RESURGENCE_PERIOD = timedelta(days=28)

SOON = timedelta(days=3)  # "approaching" threshold used for headlines and highlights


class BaroPhase(str, Enum):
    PRESENT = "Present"
    UPCOMING = "Upcoming"


@dataclass(frozen=True)
class BaroStatus:
    phase: BaroPhase
    arrival: datetime  # this visit's arrival if PRESENT, otherwise the next arrival
    departure: datetime  # when that visit ends
    last_departure: Optional[datetime]  # end of the most recent finished visit (None while PRESENT)
    next_after: datetime  # the arrival after `arrival`

    def target(self) -> datetime:
        """The moment the countdown runs to."""
        return self.departure if self.phase is BaroPhase.PRESENT else self.arrival


@dataclass(frozen=True)
class ResurgenceStatus:
    rotation_start: datetime  # when the current rotation began
    next_reset: datetime  # when it rotates (current rotation ends)
    following_reset: datetime  # the rotation after that
    day_number: int  # 1-based day inside the current 28-day rotation
    total_days: int


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def _cycle_start(anchor: datetime, period: timedelta, now: datetime) -> datetime:
    """Latest cycle start at or before `now` (works for dates before the anchor too)."""
    return anchor + ((now - anchor) // period) * period


def baro_status(now: datetime) -> BaroStatus:
    now = _aware(now)
    arrival = _cycle_start(BARO_ANCHOR, BARO_PERIOD, now)
    if now < arrival + BARO_STAY:
        return BaroStatus(
            phase=BaroPhase.PRESENT,
            arrival=arrival,
            departure=arrival + BARO_STAY,
            last_departure=None,
            next_after=arrival + BARO_PERIOD,
        )
    next_arrival = arrival + BARO_PERIOD
    return BaroStatus(
        phase=BaroPhase.UPCOMING,
        arrival=next_arrival,
        departure=next_arrival + BARO_STAY,
        last_departure=arrival + BARO_STAY,
        next_after=next_arrival + BARO_PERIOD,
    )


def resurgence_status(now: datetime) -> ResurgenceStatus:
    now = _aware(now)
    start = _cycle_start(RESURGENCE_ANCHOR, RESURGENCE_PERIOD, now)
    return ResurgenceStatus(
        rotation_start=start,
        next_reset=start + RESURGENCE_PERIOD,
        following_reset=start + 2 * RESURGENCE_PERIOD,
        day_number=(now - start).days + 1,
        total_days=RESURGENCE_PERIOD.days,
    )


def next_weekly_reset(now: datetime) -> datetime:
    """Next Monday 00:00 UTC (strictly after `now`)."""
    now = _aware(now).astimezone(UTC)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days_ahead = (7 - midnight.weekday()) % 7  # Monday == 0
    candidate = midnight + timedelta(days=days_ahead)
    return candidate if candidate > now else candidate + timedelta(days=7)


def format_countdown(delta: timedelta) -> str:
    """'3d 04h 12m' while it is days away, '4h 12m 09s' inside the last day."""
    total = int(delta.total_seconds())
    if total <= 0:
        return "now"
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"
    return f"{minutes}m {seconds:02d}s"


# -- timeline --------------------------------------------------------------


class EventKind(str, Enum):
    BARO = "baro"
    RESURGENCE = "resurgence"
    RESET = "reset"


@dataclass(frozen=True)
class TimelineEvent:
    kind: EventKind
    label: str
    when: datetime


def build_timeline(now: datetime, limit: int = 5) -> list[TimelineEvent]:
    """The next few events the app knows about, soonest first."""
    now = _aware(now)
    baro = baro_status(now)
    resurgence = resurgence_status(now)

    events: list[TimelineEvent] = []
    if baro.phase is BaroPhase.PRESENT:
        events.append(TimelineEvent(EventKind.BARO, "Baro leaves", baro.departure))
    else:
        events.append(TimelineEvent(EventKind.BARO, "Baro arrives", baro.arrival))
    events.append(TimelineEvent(EventKind.BARO, "Baro arrives", baro.next_after))
    events.append(TimelineEvent(EventKind.RESURGENCE, "Resurgence rotates", resurgence.next_reset))
    events.append(TimelineEvent(EventKind.RESET, "Weekly reset", next_weekly_reset(now)))
    events.append(TimelineEvent(EventKind.RESURGENCE, "Resurgence rotates", resurgence.following_reset))
    events.sort(key=lambda event: event.when)
    return events[:limit]
