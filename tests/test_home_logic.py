import unittest
from datetime import date, datetime, timedelta, timezone

from app.analysis.portfolio import ItemAnalysis, PortfolioReport
from app.home import headline as hl
from app.home.schedule import (
    BARO_ANCHOR,
    RESURGENCE_ANCHOR,
    BaroPhase,
    EventKind,
    baro_status,
    build_timeline,
    format_countdown,
    next_weekly_reset,
    resurgence_status,
)
from app.home.summary import (
    AttentionItem,
    InventorySummary,
    Level,
    SetsSummary,
    attention_items,
    summarize_inventory,
    summarize_sets,
)
from app.home.targets import Target
from app.market.ducats import DucatComparison, DucatVerdict
from app.market.sell_score import Recommendation, SellScoreResult
from app.relics.analyzer import analyze_relics
from tests.relics_fixture import inv, real_data

UTC = timezone.utc


def utc(*args):
    return datetime(*args, tzinfo=UTC)


class TestBaro(unittest.TestCase):
    def test_known_real_visits(self):
        # Dates published for real visits across 2023-2026 must all be arrivals.
        for day in [(2023, 7, 14), (2024, 11, 1), (2026, 4, 3), (2026, 5, 15), (2026, 9, 18), (2026, 10, 2)]:
            arrival = utc(*day, 13)
            status = baro_status(arrival)
            self.assertIs(status.phase, BaroPhase.PRESENT, day)
            self.assertEqual(status.arrival, arrival, day)
            self.assertEqual(arrival.weekday(), 4)  # Friday

    def test_phases_around_a_visit(self):
        arrival = utc(2026, 10, 16, 13)
        before = baro_status(arrival - timedelta(seconds=1))
        self.assertIs(before.phase, BaroPhase.UPCOMING)
        self.assertEqual(before.arrival, arrival)
        self.assertEqual(before.last_departure, utc(2026, 10, 4, 13))
        during = baro_status(arrival + timedelta(hours=47, minutes=59))
        self.assertIs(during.phase, BaroPhase.PRESENT)
        self.assertEqual(during.departure, utc(2026, 10, 18, 13))
        self.assertEqual(during.target(), during.departure)
        after = baro_status(arrival + timedelta(hours=48))
        self.assertIs(after.phase, BaroPhase.UPCOMING)
        self.assertEqual(after.arrival, utc(2026, 10, 30, 13))
        self.assertEqual(after.target(), after.arrival)

    def test_works_before_the_anchor_and_with_naive_input(self):
        self.assertIs(baro_status(BARO_ANCHOR - timedelta(days=30)).phase, BaroPhase.UPCOMING)
        naive = datetime(2026, 10, 10, 12)  # treated as UTC
        self.assertEqual(baro_status(naive).arrival, utc(2026, 10, 16, 13))

    def test_local_timezone_does_not_change_the_instant(self):
        sao_paulo = timezone(timedelta(hours=-3))
        a = baro_status(datetime(2026, 10, 10, 9, tzinfo=sao_paulo))
        b = baro_status(utc(2026, 10, 10, 12))
        self.assertEqual(a, b)


class TestResurgence(unittest.TestCase):
    def test_known_rotations(self):
        for day in [(2026, 2, 19), (2026, 3, 19), (2026, 6, 11), (2026, 8, 6), (2026, 9, 3), (2026, 10, 1)]:
            start = utc(*day, 18)
            status = resurgence_status(start)
            self.assertEqual(status.rotation_start, start, day)
            self.assertEqual(status.day_number, 1)
            self.assertEqual(start.weekday(), 3)  # Thursday

    def test_current_rotation(self):
        status = resurgence_status(utc(2026, 10, 10, 12))
        self.assertEqual(status.rotation_start, utc(2026, 10, 1, 18))
        self.assertEqual(status.next_reset, utc(2026, 10, 29, 18))
        self.assertEqual(status.following_reset, utc(2026, 11, 26, 18))
        self.assertEqual((status.day_number, status.total_days), (9, 28))

    def test_last_day_and_rollover(self):
        last = resurgence_status(utc(2026, 10, 29, 17, 59))
        self.assertEqual(last.day_number, 28)
        rolled = resurgence_status(utc(2026, 10, 29, 18))
        self.assertEqual(rolled.rotation_start, utc(2026, 10, 29, 18))
        self.assertEqual(rolled.day_number, 1)
        self.assertEqual(RESURGENCE_ANCHOR.weekday(), 3)


class TestResetsAndFormatting(unittest.TestCase):
    def test_weekly_reset_is_next_monday_midnight_utc(self):
        self.assertEqual(next_weekly_reset(utc(2026, 10, 10, 12)), utc(2026, 10, 12))
        self.assertEqual(next_weekly_reset(utc(2026, 10, 12, 0, 0, 1)), utc(2026, 10, 19))
        self.assertEqual(next_weekly_reset(utc(2026, 10, 12)), utc(2026, 10, 19))  # strictly after

    def test_countdown_text(self):
        self.assertEqual(format_countdown(timedelta(days=3, hours=4, minutes=12, seconds=9)), "3d 04h 12m")
        self.assertEqual(format_countdown(timedelta(hours=4, minutes=12, seconds=9)), "4h 12m 09s")
        self.assertEqual(format_countdown(timedelta(minutes=5, seconds=3)), "5m 03s")
        self.assertEqual(format_countdown(timedelta(seconds=-1)), "now")

    def test_timeline_is_sorted_and_limited(self):
        events = build_timeline(utc(2026, 10, 10, 12), limit=4)
        self.assertEqual(len(events), 4)
        self.assertEqual([e.when for e in events], sorted(e.when for e in events))
        self.assertEqual(events[0].kind, EventKind.RESET)
        self.assertEqual(events[1].label, "Baro arrives")

    def test_timeline_shows_departure_while_baro_is_here(self):
        events = build_timeline(utc(2026, 10, 16, 20))
        self.assertTrue(any(e.label == "Baro leaves" and e.when == utc(2026, 10, 18, 13) for e in events))


def _analysis(name, qty, price=10.0, rec=Recommendation.CONSIDER, ducats=None, verdict=DucatVerdict.SELL_FOR_PLAT, **kw):
    from app.analysis.portfolio import PriceQuote
    from app.config.settings import PricingStrategy

    return ItemAnalysis(
        item_id=name.lower().replace(" ", "_"), slug=name.lower().replace(" ", "_"), display_name=name,
        quantity=qty, tradable=True, category="x", is_prime=True,
        price=PriceQuote(price, price, price, price, 3, PricingStrategy.LOWEST),
        sell_score=SellScoreResult(50, rec, ()),
        ducats=DucatComparison(price, ducats, 1.0, 8.0, verdict) if ducats is not None else None,
        **kw,
    )


def _report(analyses, **kw):
    return PortfolioReport(tuple(analyses), len(analyses), len(analyses), kw.pop("value", 123.0), 0, len(analyses), **kw)


class TestSummary(unittest.TestCase):
    def test_counts(self):
        report = _report(
            [
                _analysis("Gyre Prime Set", 2),
                _analysis("Ash Prime Systems", 3, rec=Recommendation.SELL, ducats=45, verdict=DucatVerdict.KEEP_FOR_DUCATS),
                _analysis("Ash Prime Chassis", 1, ducats=15),
                _analysis("Forma Blueprint", 1),
            ],
            stale_price_slug_count=2,
            market_error_slug_count=1,
        )
        s = summarize_inventory(report)
        self.assertEqual(s.estimated_value, 123.0)
        self.assertEqual((s.distinct_items, s.total_units), (4, 7))
        self.assertEqual(s.assembled_sets, 2)
        self.assertEqual((s.duplicate_items, s.duplicate_units), (2, 3))  # 2x set (1 spare) + 3x systems (2 spare)
        self.assertEqual(s.sell_candidates, 1)
        self.assertEqual((s.ducat_items, s.ducats_total), (2, 45 * 3 + 15))
        self.assertEqual((s.ducat_deals, s.ducat_deals_total), (1, 135))
        self.assertEqual((s.stale_prices, s.missing_prices), (2, 1))

    def test_empty_report(self):
        s = summarize_inventory(_report([], value=0.0))
        self.assertEqual((s.total_units, s.assembled_sets, s.ducats_total), (0, 0, 0))

    def test_sets_match_the_relics_tab_filters(self):
        data = real_data()
        report = analyze_relics(
            [inv(k) for k in ("cedoprimebarrel", "cedoprimereceiver", "cedoprimestock", "cedoprimeblueprint")]
            + [inv("gyreprimeblueprint"), inv("gyreprimechassiscomponent"), inv("gyreprimehelmetblueprint")],
            data,
        )
        sets = summarize_sets(report)
        self.assertEqual(sets.ready, 1)  # Cedo Prime
        self.assertEqual(sets.one_away, 1)  # Gyre Prime misses only its systems part


def _summary(**kw):
    base = dict(
        estimated_value=0.0, distinct_items=0, total_units=0, tradable_items=0, assembled_sets=0,
        ducat_items=0, ducats_total=0, ducat_deals=0, ducat_deals_total=0, duplicate_items=0,
        duplicate_units=0, sell_candidates=0, stale_prices=0, missing_prices=0,
    )
    base.update(kw)
    return InventorySummary(**base)


class TestAttention(unittest.TestCase):
    def test_onboarding(self):
        no_inv = attention_items(None, None, has_inventory=False, has_relic_data=False)
        self.assertEqual(len(no_inv), 1)
        self.assertIn("No inventory", no_inv[0].text)
        not_analyzed = attention_items(None, None, has_inventory=True, has_relic_data=True)
        self.assertIn("not analyzed", not_analyzed[0].text)
        self.assertEqual(not_analyzed[0].target, Target.MARKET)

    def test_quiet_inventory_has_nothing_to_flag(self):
        self.assertEqual(attention_items(_summary(total_units=5), SetsSummary(0, 0, 0), True, True), [])

    def test_items_carry_targets_and_ready_sets_come_first(self):
        items = attention_items(
            _summary(sell_candidates=3, ducat_deals=2, ducat_deals_total=90, assembled_sets=1, duplicate_items=12, duplicate_units=30),
            SetsSummary(ready=2, one_away=4, completable=5),
            True, True,
        )
        self.assertEqual(items[0].target, Target.RELICS_READY)
        targets = {i.target for i in items}
        self.assertEqual(
            targets,
            {Target.RELICS_READY, Target.MARKET_BY_SCORE, Target.MARKET_BY_DUCATS, Target.MARKET_PRIME_SETS,
             Target.MARKET_BY_QTY, Target.RELICS_ONE_AWAY, Target.RELICS_COMPLETABLE},
        )
        self.assertIn("1 item rated SELL", attention_items(_summary(sell_candidates=1), None, True, True)[0].text)

    def test_duplicates_below_threshold_are_not_flagged(self):
        self.assertEqual(attention_items(_summary(duplicate_items=9), None, True, True), [])

    def test_market_problems_and_missing_relic_data(self):
        items = attention_items(_summary(missing_prices=2, stale_prices=3), None, True, False)
        texts = [i.text for i in items]
        self.assertIn("2 items without market data", texts)
        self.assertFalse(any("old cache" in t for t in texts))  # the worse problem wins
        self.assertTrue(any(i.target is Target.RELICS for i in items))
        self.assertTrue(all(isinstance(i, AttentionItem) and isinstance(i.level, Level) for i in items))


def _ctx(now, summary=None, sets=None, has_inventory=True):
    return hl.HeadlineContext(
        now_local_date=date(2026, 10, 10), now_utc=now, baro=baro_status(now), resurgence=resurgence_status(now),
        has_inventory=has_inventory, summary=summary, sets=sets,
    )


class TestHeadline(unittest.TestCase):
    far = utc(2026, 10, 10, 12)  # Baro 6 days out, Resurgence 19 days out

    def key(self, ctx):
        return hl.headline_key(ctx)

    def test_priority_order(self):
        self.assertEqual(self.key(_ctx(utc(2026, 10, 16, 14), _summary())), "baro_here")
        self.assertEqual(self.key(_ctx(utc(2026, 10, 14, 14), _summary())), "baro_soon")
        self.assertEqual(self.key(_ctx(utc(2026, 10, 27, 12), _summary())), "resurgence_soon")
        self.assertEqual(self.key(_ctx(self.far, has_inventory=False)), "no_inventory")
        self.assertEqual(self.key(_ctx(self.far)), "not_analyzed")
        self.assertEqual(self.key(_ctx(self.far, _summary(tradable_items=500), SetsSummary(1, 0, 0))), "sets_ready")
        self.assertEqual(self.key(_ctx(self.far, _summary(tradable_items=500), SetsSummary(0, 3, 0))), "many_tradable")
        self.assertEqual(self.key(_ctx(self.far, _summary(tradable_items=5), SetsSummary(0, 3, 0))), "sets_close")
        self.assertEqual(self.key(_ctx(self.far, _summary(tradable_items=5), SetsSummary(0, 0, 0))), "calm")

    def test_baro_beats_everything(self):
        ctx = _ctx(utc(2026, 10, 16, 14), _summary(tradable_items=500), SetsSummary(5, 5, 5))
        self.assertEqual(self.key(ctx), "baro_here")

    def test_line_is_stable_for_a_day_and_comes_from_the_pool(self):
        ctx = _ctx(self.far, _summary(), SetsSummary(0, 0, 0))
        self.assertEqual(hl.pick_headline(ctx), hl.pick_headline(ctx))
        self.assertIn(hl.pick_headline(ctx), hl.LINES["calm"])
        self.assertTrue(all(hl.LINES[k] for k in hl.LINES))


if __name__ == "__main__":
    unittest.main()
