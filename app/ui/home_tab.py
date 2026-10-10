"""
ui.home_tab
===========

The Home: a presentation layer over what Ordis Market already knows. It
computes nothing new itself; numbers come from the last analysis report and
the Relics analysis (see app.home.summary), the Baro / Prime Resurgence times
from the fixed cycles in app.home.schedule.

Clicking a card or an attention row emits `navigate(Target)`; MainWindow
decides how to show the matching existing screen.

Ordis: "Welcome to the bridge, Operator. Everything important is on this
        page. The rest is in tabs. I am not sure why."
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Iterable, Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from app.analysis.portfolio import PortfolioReport
from app.home.headline import HeadlineContext, pick_headline
from app.home.schedule import (
    SOON,
    BaroPhase,
    baro_status,
    build_timeline,
    format_countdown,
    resurgence_status,
)
from app.home.summary import (
    InventorySummary,
    SetsSummary,
    attention_items,
    summarize_inventory,
    summarize_sets,
)
from app.home.targets import Target
from app.inventory.models import InventoryItem
from app.relics.analyzer import analyze_relics
from app.relics.models import RelicData
from app.relics.store import RelicDataStore
from app.ui.home_widgets import (
    AttentionRow,
    HologramCore,
    HudCard,
    MiniBar,
    StatCard,
    TimelineStrip,
    styled_label,
)
from app.ui.theme import ACCENT_CYAN, ACCENT_GOLD, TEXT_MUTED, TEXT_PRIMARY

logger = logging.getLogger(__name__)

_LOCAL_FMT = "%a %d %b, %H:%M"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: float) -> str:
    return f"{value:,.0f}p"


def _local(moment: datetime) -> str:
    return moment.astimezone().strftime(_LOCAL_FMT)


def _ago(delta_seconds: float) -> str:
    days = int(delta_seconds // 86400)
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''} ago"
    return f"{int(delta_seconds // 3600)} h ago"


class HomeTab(QWidget):
    navigate = Signal(object)  # a Target

    def __init__(
        self,
        store: Optional[RelicDataStore],
        get_report: Callable[[], Optional[PortfolioReport]],
        get_items: Callable[[], Iterable[InventoryItem]],
        get_analyzed_text: Callable[[], str],
        now_provider: Callable[[], datetime] = _utc_now,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._get_report = get_report
        self._get_items = get_items
        self._get_analyzed_text = get_analyzed_text
        self._now = now_provider
        self._relic_data: Optional[RelicData] = None
        self._relic_data_loaded = False
        self._summary: Optional[InventorySummary] = None
        self._sets: Optional[SetsSummary] = None
        self._has_inventory = False
        self._busy = False
        self._attention_signature: object = None

        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self.tick)

        self._build_ui()
        self.refresh()

    # -- construction ---------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        root.addWidget(self._build_header())
        root.addLayout(self._build_stats())
        root.addLayout(self._build_middle())
        root.addWidget(self._build_timeline())
        root.addStretch(1)

    def _build_header(self) -> QWidget:
        card = HudCard(accent=ACCENT_GOLD)
        card.setToolTip("Ordis, summing up what he knows right now.")
        row = QHBoxLayout()
        row.setSpacing(18)
        self.core = HologramCore(132)
        self.core.setToolTip("Ordis is watching.")
        row.addWidget(self.core)
        column = QVBoxLayout()
        column.setSpacing(6)
        column.addStretch(1)
        column.addWidget(styled_label("ORDIS", 9, ACCENT_GOLD, 700, 3))
        self.lbl_headline = styled_label("", 16, TEXT_PRIMARY, 500, italic=True, wrap=True)
        self.lbl_headline.setToolTip("A line chosen from a fixed set according to your situation (no AI involved).")
        column.addWidget(self.lbl_headline)
        self.lbl_meta = styled_label("", 9, TEXT_MUTED, wrap=True)
        self.lbl_meta.setToolTip("What this page is built from.")
        column.addWidget(self.lbl_meta)
        column.addStretch(1)
        row.addLayout(column, stretch=1)
        card.body.addLayout(row)
        return card

    def _build_stats(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self.card_value = StatCard("Estimated value", ACCENT_GOLD, Target.MARKET)
        self.card_items = StatCard("Inventory", ACCENT_CYAN, Target.MARKET)
        self.card_tradable = StatCard("Tradable", ACCENT_CYAN, Target.MARKET_TRADABLE)
        self.card_ready = StatCard("Prime sets ready", ACCENT_GOLD, Target.RELICS_READY)
        self.card_close = StatCard("One part away", ACCENT_GOLD, Target.RELICS_ONE_AWAY)
        self.card_ducats = StatCard("Ducats", ACCENT_CYAN, Target.MARKET_BY_DUCATS)
        tips = {
            self.card_value: "What your analyzed inventory would sell for at current lowest prices. Click to open the Market tab.",
            self.card_items: "Different items and total units in your imported inventory. Click to open the Market tab.",
            self.card_tradable: "Items that can actually be sold on warframe.market. Click to list them.",
            self.card_ready: "Prime sets for which you already hold every part. Click to open them on the Relics tab.",
            self.card_close: "Prime sets missing exactly one part. Click to see them on the Relics tab.",
            self.card_ducats: "Ducats your Prime parts would fetch from Baro Ki'Teer. Click to sort the Market by the best Ducat deals.",
        }
        for card, tip in tips.items():
            card.setToolTip(tip)
            card.clicked.connect(self.navigate)
            row.addWidget(card, stretch=1)
        return row

    def _build_middle(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self.card_attention = HudCard("What needs attention", ACCENT_GOLD)
        self.card_attention.setToolTip("Situations found in your inventory. Click one to open the matching screen.")
        self._attention_box = QVBoxLayout()
        self._attention_box.setSpacing(2)
        self.card_attention.body.addLayout(self._attention_box)
        self.card_attention.body.addStretch(1)
        row.addWidget(self.card_attention, stretch=5)

        self.card_baro = HudCard("Baro Ki'Teer", ACCENT_GOLD)
        self.card_baro.setToolTip(
            "Calculated from his fixed schedule: every 14 days, Friday 13:00 UTC, for 48 hours. "
            "A special event could shift it."
        )
        self.baro_pill = styled_label("", 8, ACCENT_GOLD, 700, 1.5)
        self.baro_countdown = styled_label("", 24, ACCENT_GOLD, 700)
        self.baro_when = styled_label("", 9, TEXT_PRIMARY)
        self.baro_bar = MiniBar(ACCENT_GOLD)
        self.baro_extra = styled_label("", 8, TEXT_MUTED, wrap=True)
        for w in (self.baro_pill, self.baro_countdown, self.baro_when, self.baro_bar, self.baro_extra):
            self.card_baro.body.addWidget(w)
        self.card_baro.body.addStretch(1)
        row.addWidget(self.card_baro, stretch=4)

        self.card_resurgence = HudCard("Prime Resurgence", ACCENT_CYAN)
        self.card_resurgence.setToolTip(
            "Calculated from the 28-day rotation (Thursday 18:00 UTC). Which Primes are in the "
            "vault is not known offline. A Resurgence event could shift the date."
        )
        self.res_pill = styled_label("", 8, ACCENT_CYAN, 700, 1.5)
        self.res_countdown = styled_label("", 24, ACCENT_CYAN, 700)
        self.res_when = styled_label("", 9, TEXT_PRIMARY)
        self.res_bar = MiniBar(ACCENT_CYAN)
        self.res_extra = styled_label("", 8, TEXT_MUTED, wrap=True)
        for w in (self.res_pill, self.res_countdown, self.res_when, self.res_bar, self.res_extra):
            self.card_resurgence.body.addWidget(w)
        self.card_resurgence.body.addStretch(1)
        row.addWidget(self.card_resurgence, stretch=4)
        return row

    def _build_timeline(self) -> QWidget:
        card = HudCard("Coming up", ACCENT_CYAN)
        card.setToolTip("The next events Ordis knows about, in order (not to scale). Times are in your local time zone.")
        self.timeline = TimelineStrip()
        card.body.addWidget(self.timeline)
        return card

    # -- data -----------------------------------------------------------------

    def invalidate_relic_data(self) -> None:
        """Drop the cached relic tables (call after they were re-downloaded)."""
        self._relic_data_loaded = False

    def _relic_tables(self) -> Optional[RelicData]:
        if not self._relic_data_loaded:
            self._relic_data_loaded = True
            self._relic_data = self._store.load() if self._store is not None else None
        return self._relic_data

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._render_header(self._now())

    def refresh(self) -> None:
        """Recompute everything from the app's current state."""
        report = self._get_report()
        items = list(self._get_items())
        self._has_inventory = bool(items) or report is not None
        self._summary = summarize_inventory(report) if report is not None else None
        self._sets = None
        data = self._relic_tables()
        if data is not None and items:
            try:
                self._sets = summarize_sets(analyze_relics(items, data))
            except Exception:  # noqa: BLE001 - the Home must never take the app down
                logger.exception("Could not summarise Prime sets for the Home")
        self._render_stats()
        self._render_attention()
        self.tick()

    def tick(self) -> None:
        """Once per second while visible: countdowns, timeline, headline."""
        now = self._now()
        self._render_header(now)
        self._render_baro(now)
        self._render_resurgence(now)
        self.timeline.set_events(now, build_timeline(now))

    def showEvent(self, event) -> None:  # noqa: N802
        self.refresh()
        self._clock.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:  # noqa: N802
        self._clock.stop()
        super().hideEvent(event)

    # -- rendering ------------------------------------------------------------

    def _render_header(self, now: datetime) -> None:
        ctx = HeadlineContext(
            now_local_date=now.astimezone().date(),
            now_utc=now,
            baro=baro_status(now),
            resurgence=resurgence_status(now),
            has_inventory=self._has_inventory,
            summary=self._summary,
            sets=self._sets,
        )
        self.lbl_headline.setText(f"“{pick_headline(ctx)}”")
        if self._busy:
            meta = "Analysis in progress..."
        elif self._summary is not None:
            meta = self._get_analyzed_text()
        elif self._has_inventory:
            meta = "Inventory imported, not analyzed yet."
        else:
            meta = "No inventory imported yet."
        self.lbl_meta.setText(meta)

    def _render_stats(self) -> None:
        s = self._summary
        if s is None:
            hint = "Import an inventory" if not self._has_inventory else "Run ANALYZE INVENTORY"
            for card, title in (
                (self.card_value, "no analysis yet"),
                (self.card_items, "nothing imported" if not self._has_inventory else "not analyzed"),
                (self.card_tradable, "no analysis yet"),
                (self.card_ducats, "no analysis yet"),
            ):
                card.set_content("-", title, hint, muted=True)
        else:
            self.card_value.set_content(_money(s.estimated_value), "estimated value", "from your last analysis")
            self.card_items.set_content(f"{s.distinct_items:,}", "different items", f"{s.total_units:,} units in total")
            self.card_tradable.set_content(f"{s.tradable_items:,}", "items to sell", "sellable on warframe.market")
            if s.ducat_items:
                hint = (
                    f"{s.ducat_deals} item{'s' if s.ducat_deals != 1 else ''} better kept for Ducats"
                    if s.ducat_deals
                    else "no item beats its plat price"
                )
                self.card_ducats.set_content(f"{s.ducats_total:,}", "Ducats in Prime parts", hint)
            else:
                self.card_ducats.set_content("0", "no Ducat items found", "", muted=True)

        if self._sets is not None:
            n = self._sets
            self.card_ready.set_content(str(n.ready), "ready to build", "you hold every part" if n.ready else "none yet", muted=not n.ready)
            self.card_close.set_content(
                str(n.one_away), "sets", f"{n.completable} finishable with your relics", muted=not n.one_away
            )
        else:
            hint = "Import an inventory" if not self._has_inventory else "Open RELICS to download the drop tables"
            self.card_ready.set_content("-", "needs relic data", hint, muted=True)
            self.card_close.set_content("-", "needs relic data", hint, muted=True)
            self.card_ready.set_target(Target.RELICS if self._has_inventory else Target.MARKET)
            self.card_close.set_target(Target.RELICS if self._has_inventory else Target.MARKET)
            return
        self.card_ready.set_target(Target.RELICS_READY)
        self.card_close.set_target(Target.RELICS_ONE_AWAY)

    def _render_attention(self) -> None:
        items = attention_items(self._summary, self._sets, self._has_inventory, self._relic_data is not None)
        signature = [(i.level, i.text, i.detail, i.target) for i in items]
        if signature == self._attention_signature:
            return
        self._attention_signature = signature
        while self._attention_box.count():
            child = self._attention_box.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        if not items:
            self._attention_box.addWidget(styled_label("Nothing needs your attention right now.", 10, TEXT_MUTED, italic=True))
            return
        for item in items:
            row = AttentionRow(item.level.value, item.text, item.detail, item.target)
            row.clicked.connect(self.navigate)
            self._attention_box.addWidget(row)

    def _render_baro(self, now: datetime) -> None:
        status = baro_status(now)
        target = status.target()
        self.baro_countdown.setText(format_countdown(target - now))
        if status.phase is BaroPhase.PRESENT:
            self.baro_pill.setText("PRESENT NOW  ·  LEAVES IN")
            self.baro_when.setText(f"Leaves {_local(status.departure)}")
            self.baro_bar.set_fraction(1 - (status.departure - now) / (status.departure - status.arrival))
            extra = f"Arrived {_local(status.arrival)}."
            if self._summary is not None and self._summary.ducat_deals:
                extra += f" {self._summary.ducat_deals_total:,} Ducats of yours are worth more kept for him."
            self.baro_extra.setText(extra)
        else:
            soon = status.arrival - now <= SOON
            self.baro_pill.setText("ARRIVING SOON  ·  IN" if soon else "NEXT VISIT  ·  ARRIVES IN")
            self.baro_when.setText(f"Arrives {_local(status.arrival)}")
            self.baro_bar.set_fraction(1 - (status.arrival - now) / (status.next_after - status.arrival))
            extra = f"Stays 48 h, until {_local(status.departure)}."
            if status.last_departure is not None:
                extra += f" Last visit ended {_ago((now - status.last_departure).total_seconds())}."
            if self._summary is not None and self._summary.ducat_deals:
                extra += f" {self._summary.ducat_deals_total:,} Ducats of yours are worth more kept for him."
            self.baro_extra.setText(extra)

    def _render_resurgence(self, now: datetime) -> None:
        status = resurgence_status(now)
        soon = status.next_reset - now <= SOON
        self.res_pill.setText("ROTATING SOON  ·  IN" if soon else "NEXT ROTATION  ·  ROTATES IN")
        self.res_countdown.setText(format_countdown(status.next_reset - now))
        self.res_when.setText(f"Rotates {_local(status.next_reset)}")
        elapsed = (now - status.rotation_start).total_seconds()
        self.res_bar.set_fraction(elapsed / (status.next_reset - status.rotation_start).total_seconds())
        self.res_extra.setText(
            f"Rotation day {status.day_number} of {status.total_days}, since {_local(status.rotation_start)}. "
            f"The one after rotates {_local(status.following_reset)}. Estimated from the 28-day cycle."
        )
