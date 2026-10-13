import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HAVE_QT = importlib.util.find_spec("PySide6") is not None

if HAVE_QT:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from app.analysis.portfolio import PortfolioAnalyzer
    from app.config.settings import AppSettings
    from app.home.targets import Target
    from app.inventory.parser import InventoryParser
    from app.inventory.repository import InventoryRepository
    from app.market.sell_score import Recommendation
    from app.relics.store import RelicDataStore
    from app.relics.view import FilterMode
    from app.ui.home_tab import HomeTab
    from app.ui.main_window import MainWindow
    from tests.relics_fixture import inv, real_data
    from tests.test_home_logic import _analysis, _report

UTC = timezone.utc
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class _QtCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)


class TestHomeTab(_QtCase):
    def make(self, report=None, items=(), store=None, now=NOW):
        self.report, self.items = report, list(items)
        self.clock = [now]
        return HomeTab(
            store, lambda: self.report, lambda: self.items, lambda: "Last Analysis: test", lambda: self.clock[0]
        )

    def test_empty_state_guides_the_operator(self):
        tab = self.make()
        self.assertEqual(tab.card_value.value_label.text(), "-")
        self.assertIn("Import an inventory", tab.card_value.hint_label.text())
        self.assertIn("No inventory", tab.lbl_meta.text())
        self.assertEqual(tab._attention_box.count(), 1)
        row = tab._attention_box.itemAt(0).widget()
        self.assertIn("No inventory", row.findChildren(type(tab.lbl_meta))[0].text())

    def test_numbers_come_from_the_report(self):
        report = _report([_analysis("Gyre Prime Set", 2, price=50.0), _analysis("Ash Prime Systems", 3)], value=555.0)
        tab = self.make(report, [inv("gyre_prime_set")])
        self.assertEqual(tab.card_value.value_label.text(), "555p")
        self.assertEqual(tab.card_items.value_label.text(), "2")
        self.assertEqual(tab.card_tradable.value_label.text(), "2")
        self.assertIn("Last Analysis", tab.lbl_meta.text())

    def test_countdowns_use_the_clock_and_tick_forward(self):
        tab = self.make()
        self.assertEqual(tab.baro_countdown.text(), "6d 01h 00m")  # to Fri 16 Oct 13:00 UTC
        self.assertEqual(tab.res_countdown.text(), "19d 06h 00m")  # to Thu 29 Oct 18:00 UTC
        self.assertIn("ARRIVES IN", tab.baro_pill.text())
        self.clock[0] = NOW + timedelta(days=6, hours=2)  # Baro is on the relay
        tab.tick()
        self.assertIn("PRESENT", tab.baro_pill.text())
        self.assertEqual(tab.baro_countdown.text(), "1d 23h 00m")  # until he leaves, Sun 13:00 UTC
        self.assertIn("Baro", tab.lbl_headline.text())

    def test_relic_cards_need_the_tables_then_use_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RelicDataStore(Path(tmp) / "relic_data.json")
            report = _report([_analysis("Forma Blueprint", 1)])
            tab = self.make(report, [inv("cedoprimebarrel")], store)
            self.assertEqual(tab.card_ready.value_label.text(), "-")
            self.assertEqual(tab.card_ready._target, Target.RELICS)
            store.save(real_data())
            tab.invalidate_relic_data()
            tab.items = self.items = [inv(k) for k in ("cedoprimebarrel", "cedoprimereceiver", "cedoprimestock", "cedoprimeblueprint")]
            tab.refresh()
            self.assertEqual(tab.card_ready.value_label.text(), "1")
            self.assertEqual(tab.card_ready._target, Target.RELICS_READY)

    def test_clicking_a_card_and_an_attention_row_emits_the_target(self):
        report = _report([_analysis("Ash Prime Systems", 3, rec=Recommendation.SELL)])
        tab = self.make(report, [inv("ash_prime_systems")])
        tab.resize(1100, 700)
        tab.show()
        received = []
        tab.navigate.connect(received.append)
        QTest.mouseClick(tab.card_tradable, Qt.LeftButton)
        row = tab._attention_box.itemAt(0).widget()
        QTest.mouseClick(row, Qt.LeftButton)
        self.assertEqual(received, [Target.MARKET_TRADABLE, Target.MARKET_BY_SCORE])
        tab.hide()

    def test_every_widget_has_a_tooltip(self):
        tab = self.make()
        for card in (tab.card_value, tab.card_items, tab.card_tradable, tab.card_ready, tab.card_close,
                     tab.card_ducats, tab.card_attention, tab.card_baro, tab.card_resurgence, tab.core):
            self.assertTrue(card.toolTip())

    def test_timer_only_runs_while_visible(self):
        tab = self.make()
        self.assertFalse(tab._clock.isActive())
        tab.show()
        self.assertTrue(tab._clock.isActive())
        self.assertTrue(tab.core._timer.isActive())
        tab.hide()
        self.assertFalse(tab._clock.isActive())
        self.assertFalse(tab.core._timer.isActive())

    def test_a_broken_relic_analysis_does_not_take_the_page_down(self):
        store = MagicMock()
        store.load.return_value = real_data()
        tab = self.make(_report([_analysis("X Prime Set", 1)]), [inv("x")], store)
        with mock.patch("app.ui.home_tab.analyze_relics", side_effect=RuntimeError("boom")):
            with self.assertLogs("app.ui.home_tab", level="ERROR"):
                tab.refresh()
        self.assertEqual(tab.card_ready.value_label.text(), "-")


class TestHolographicEffects(_QtCase):
    def make(self, animations):
        self.report, self.items = None, []
        return HomeTab(None, lambda: self.report, lambda: self.items, lambda: "x", lambda: NOW, animations=animations)

    def test_effects_run_only_while_visible_and_when_enabled(self):
        from app.ui.home_widgets import HoloOverlay

        tab = self.make(True)
        overlays = tab.findChildren(HoloOverlay)
        self.assertGreaterEqual(len(overlays), 9)  # one per card
        self.assertFalse(tab.core._timer.isActive())
        tab.show()
        self.assertTrue(tab.core._timer.isActive())
        self.assertTrue(tab.timeline._timer.isActive())
        self.assertTrue(all(o._idle.isActive() for o in overlays))  # a light sweep is scheduled
        tab.set_animations(False)  # reduce motion
        self.assertFalse(tab.core._timer.isActive())
        self.assertFalse(tab.timeline._timer.isActive())
        self.assertFalse(any(o._idle.isActive() or o._frames.isActive() for o in overlays))
        tab.hide()

    def test_animations_off_means_nothing_moves_from_the_start(self):
        tab = self.make(False)
        tab.show()
        self.assertFalse(tab.core._timer.isActive())
        self.assertFalse(tab._typer.isActive())
        self.assertEqual(tab.lbl_headline.text(), "\u201c" + tab._headline_full.strip("\u201c\u201d") + "\u201d")
        tab.hide()

    def test_headline_types_itself_out_when_it_changes(self):
        tab = self.make(True)
        tab.show()
        tab._set_headline("\u201cHello there, Operator.\u201d")  # a new line while visible
        self.assertTrue(tab._typer.isActive())
        tab._type_next()
        self.assertTrue(tab.lbl_headline.text().endswith("\u258c"))
        self.assertLess(len(tab.lbl_headline.text()), len("\u201cHello there, Operator.\u201d"))
        for _ in range(40):
            tab._type_next()
        self.assertFalse(tab._typer.isActive())
        self.assertEqual(tab.lbl_headline.text(), "\u201cHello there, Operator.\u201d")
        tab._set_headline("\u201cHello there, Operator.\u201d")  # same line: no retype
        self.assertFalse(tab._typer.isActive())
        tab.hide()

    def test_the_once_a_second_tick_does_not_restart_the_typing(self):
        tab = self.make(True)
        tab.show()
        tab.tick()
        line = tab._headline_full
        for _ in range(60):
            tab._type_next()
        tab.tick()
        tab.tick()
        self.assertFalse(tab._typer.isActive())
        self.assertEqual(tab._headline_full, line)
        tab.hide()

    def test_overlays_never_block_clicks(self):
        from app.ui.home_widgets import HoloOverlay

        tab = self.make(True)
        for overlay in tab.findChildren(HoloOverlay):
            self.assertTrue(overlay.testAttribute(Qt.WA_TransparentForMouseEvents))

    def test_glitch_and_sweep_frames_paint_without_error(self):
        from app.ui.home_widgets import HoloOverlay

        tab = self.make(True)
        tab.resize(1100, 700)
        tab.show()
        tab.core._glitch_until = tab.core._t + 10
        self.assertTrue(tab.core.glitching())
        for overlay in tab.findChildren(HoloOverlay):
            overlay._progress = 0.5
        tab.timeline._phase = 1.0
        pixmap = tab.grab()  # renders every widget, including the glitch composite
        self.assertFalse(pixmap.isNull())
        tab.hide()

    def test_glitches_happen_now_and_then(self):
        tab = self.make(True)
        tab.core._animated = True
        seen = 0
        for _ in range(600):  # ~20 s of frames
            tab.core._advance()
            seen += tab.core.glitching()
        self.assertGreater(seen, 0)
        self.assertLess(seen, 120)  # brief, not constant


class TestMainWindowHome(_QtCase):
    def make_window(self, auto=False, min_age=600):
        tmp = Path(tempfile.mkdtemp())
        store = RelicDataStore(tmp / "relic_data.json")
        store.save(real_data())
        win = MainWindow(
            InventoryParser(), InventoryRepository(tmp / "saved.json"),
            PortfolioAnalyzer(MagicMock(), MagicMock(), AppSettings()),
            relic_store=store, auto_update_market=auto, auto_update_min_age_seconds=min_age,
        )
        self.tmp = tmp
        return win

    def import_inventory(self, win):
        path = self.tmp / "inv.json"
        path.write_text(json.dumps({"items": [{"item_id": "cedoprimebarrel", "quantity": 1}]}))
        win._import_from_path(str(path), auto=False)

    def test_home_is_the_landing_tab(self):
        win = self.make_window()
        self.assertEqual(win.tabs.currentWidget(), win.home_tab)

    def test_market_shortcuts_set_filters_and_sorting(self):
        win = self.make_window()
        win.chk_hide_prime_sets.setChecked(True)
        win.spin_min_score.setValue(30)
        win._on_home_navigate(Target.MARKET_TRADABLE)
        self.assertEqual(win.tabs.currentWidget(), win._market_page)
        self.assertEqual(win.chk_tradable_only.currentText(), "Tradable Only")
        self.assertFalse(win.chk_hide_prime_sets.isChecked())  # filters were reset first
        self.assertEqual(win.spin_min_score.value(), 0)
        win._on_home_navigate(Target.MARKET_PRIME_SETS)
        self.assertEqual(win.txt_search.text(), "prime set")
        self.assertEqual(win.chk_tradable_only.currentIndex(), 0)
        win._on_home_navigate(Target.MARKET_BY_DUCATS)
        self.assertEqual(win.txt_search.text(), "")
        header = win.table.horizontalHeader()
        self.assertEqual((header.sortIndicatorSection(), header.sortIndicatorOrder()), (win._COL_DUCATS, Qt.DescendingOrder))
        win._on_home_navigate(Target.MARKET_BY_QTY)
        self.assertEqual(header.sortIndicatorSection(), win._COL_QTY)

    def test_relic_shortcuts_open_the_tab_in_the_right_mode(self):
        win = self.make_window()
        for target, mode in ((Target.RELICS_READY, FilterMode.COMPLETE), (Target.RELICS_ONE_AWAY, FilterMode.OWNED),
                             (Target.RELICS_COMPLETABLE, FilterMode.COMPLETABLE)):
            win.tabs.setCurrentWidget(win.home_tab)
            win._on_home_navigate(target)
            self.assertEqual(win.tabs.currentWidget(), win.relics_tab)
            self.assertEqual(win.relics_tab._current_mode(), mode)
        win.tabs.setCurrentWidget(win.home_tab)
        win._on_home_navigate(Target.RELICS)
        self.assertEqual(win.tabs.currentWidget(), win.relics_tab)

    def test_auto_update_runs_only_when_it_makes_sense(self):
        win = self.make_window(auto=True)
        calls = []
        win._on_analyze_clicked = lambda: calls.append(1)

        win._maybe_auto_update_market()
        self.assertEqual(calls, [])  # nothing imported: nothing to price

        self.import_inventory(win)
        win._maybe_auto_update_market()
        self.assertEqual(calls, [1])  # inventory but never analyzed
        self.assertTrue(win._analysis_is_auto)
        self.assertFalse(win._force_refresh_next_analysis)  # reuses prices that are still fresh

        win._analysis_is_auto = False
        win._analyzed_at = datetime.now(UTC) - timedelta(minutes=2)
        win._maybe_auto_update_market()
        self.assertEqual(calls, [1])  # analysed 2 minutes ago: fresh enough

        win._analyzed_at = datetime.now(UTC) - timedelta(hours=3)
        win._maybe_auto_update_market()
        self.assertEqual(calls, [1, 1])  # stale: refresh

    def test_auto_update_waits_for_the_startup_catalog_refresh(self):
        win = self.make_window(auto=True)
        self.import_inventory(win)
        calls = []
        win._on_analyze_clicked = lambda: calls.append(1)
        win._catalog_worker = MagicMock()
        win._catalog_worker.isRunning.return_value = True
        win._catalog_worker_is_startup = True
        win._maybe_auto_update_market()
        self.assertEqual(calls, [])  # the catalog is still being refreshed

        win._catalog_worker.isRunning.return_value = False
        win._maybe_auto_update_market()
        self.assertEqual(calls, [1])

    def test_auto_update_skips_while_an_analysis_is_running(self):
        win = self.make_window(auto=True)
        self.import_inventory(win)
        win._worker = MagicMock()
        win._worker.isRunning.return_value = True
        calls = []
        win._on_analyze_clicked = lambda: calls.append(1)
        win._maybe_auto_update_market()
        self.assertEqual(calls, [])

    def test_auto_update_failure_is_quiet(self):
        win = self.make_window(auto=True)
        win._analysis_is_auto = True
        win._show_error = MagicMock()
        win._on_analysis_failed("no network")
        win._show_error.assert_not_called()
        self.assertIn("no network", win.statusBar().currentMessage())
        win._on_analysis_failed("again")  # a manual run still gets the dialog
        win._show_error.assert_called_once()

    def test_reduce_motion_setting_reaches_the_home(self):
        tmp = Path(tempfile.mkdtemp())
        win = MainWindow(
            InventoryParser(), InventoryRepository(tmp / "saved.json"),
            PortfolioAnalyzer(MagicMock(), MagicMock(), AppSettings()),
            relic_store=RelicDataStore(tmp / "r.json"), home_animations=False,
        )
        win.show()
        self.assertFalse(win.home_tab.core._timer.isActive())
        win.close()

    def test_auto_update_is_scheduled_only_when_enabled(self):
        with mock.patch("app.ui.main_window.QTimer.singleShot") as single_shot:
            self.make_window(auto=False)
            targets = [c.args[1] for c in single_shot.call_args_list]
        self.assertFalse(any(getattr(t, "__name__", "") == "_maybe_auto_update_market" for t in targets))
        with mock.patch("app.ui.main_window.QTimer.singleShot") as single_shot:
            self.make_window(auto=True)
            targets = [c.args[1] for c in single_shot.call_args_list]
        self.assertTrue(any(getattr(t, "__name__", "") == "_maybe_auto_update_market" for t in targets))


class TestSettings(unittest.TestCase):
    def test_new_fields_roundtrip_and_default_on(self):
        s = AppSettings.from_dict({})
        self.assertTrue(s.auto_update_market_on_start)
        self.assertEqual(s.auto_update_min_age_seconds, 600)
        s2 = AppSettings.from_dict(AppSettings(auto_update_market_on_start=False, auto_update_min_age_seconds=60).to_dict())
        self.assertFalse(s2.auto_update_market_on_start)
        self.assertEqual(s2.auto_update_min_age_seconds, 60)
        self.assertTrue(AppSettings.from_dict({}).home_animations)
        self.assertFalse(AppSettings.from_dict(AppSettings(home_animations=False).to_dict()).home_animations)


if __name__ == "__main__":
    unittest.main()
