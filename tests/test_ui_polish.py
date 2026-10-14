"""Tests for the interface polish: program icon, theme glyphs, empty states,
table cues, keyboard shortcuts, remembered window state, wrapping toolbar."""

import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests.test_home_tab import HAVE_QT, _QtCase

ROOT = Path(__file__).resolve().parent.parent

if HAVE_QT:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QPushButton, QWidget

    from app.analysis.portfolio import ItemAnalysis, PortfolioAnalyzer, PortfolioReport
    from app.config.settings import AppSettings, PricingStrategy
    from app.inventory.parser import InventoryParser
    from app.inventory.repository import InventoryRepository
    from app.market.liquidity import LiquidityLevel, LiquidityReport
    from app.market.pricing import PriceQuote
    from app.market.sell_score import Recommendation, SellScoreResult
    from app.relics.store import RelicDataStore
    from app.relics.view import FilterMode
    from app.ui.app_icon import ICON_SIZES, build_app_icon, render_icon
    from app.ui.flow_layout import FlowLayout
    from app.ui.main_window import MainWindow
    from app.ui.theme import ACCENT_CYAN
    from app.ui.theme_assets import ensure_ui_icons
    from app.ui.ui_state import UiStateStore
    from tests.relics_fixture import inv, real_data
    from tools.make_icon import build_ico


def analysis(i, quantity=1, price=10.0, recommendation=Recommendation.SELL):
    return ItemAnalysis(
        item_id=f"i{i}", slug=f"i{i}", display_name=f"Item {i}", quantity=quantity,
        tradable=True, category="x", is_prime=False,
        price=PriceQuote(1, 1, 1, price, 3, PricingStrategy.LOWEST),
        liquidity=LiquidityReport(LiquidityLevel.HIGH, 3, 3, 1.0),
        sell_score=SellScoreResult(50, recommendation, ("a",)),
    )


def report_of(*analyses):
    n = len(analyses)
    return PortfolioReport(tuple(analyses), n, n, 100.0, 0, n)


class TestProgramIcon(_QtCase):
    def test_every_size_renders_a_rounded_plate_with_artwork(self):
        for size in ICON_SIZES:
            img = render_icon(size)
            self.assertEqual((img.width(), img.height()), (size, size))
            self.assertEqual(img.pixelColor(0, 0).alpha(), 0, f"{size}px: corner should be transparent")
            centre = img.pixelColor(size // 2, size // 2)
            self.assertGreater(centre.alpha(), 200, f"{size}px: the gem should be opaque")
            self.assertGreater(centre.red(), centre.blue(), f"{size}px: the gem is gold, not blue")

    def test_qicon_has_all_sizes(self):
        sizes = {s.width() for s in build_app_icon().availableSizes()}
        self.assertEqual(sizes, set(ICON_SIZES))

    def test_ico_container_is_well_formed(self):
        data = build_ico()
        reserved, kind, count = struct.unpack_from("<HHH", data, 0)
        self.assertEqual((reserved, kind, count), (0, 1, len(ICON_SIZES)))
        for k in range(count):
            width, height, _c, _r, _planes, bits, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + 16 * k)
            self.assertEqual(width, height)
            self.assertEqual(bits, 32)
            self.assertEqual(data[offset:offset + 8], b"\x89PNG\r\n\x1a\n")
            self.assertLessEqual(offset + length, len(data))

    def test_shipped_icon_files_exist_and_are_valid(self):
        ico = (ROOT / "assets" / "ordis_market.ico").read_bytes()
        self.assertEqual(ico[:4], b"\x00\x00\x01\x00")
        png = QImage(str(ROOT / "assets" / "ordis_market.png"))
        self.assertFalse(png.isNull())
        self.assertEqual(png.width(), 512)

    def test_build_script_uses_the_icon(self):
        build = (ROOT / "build.bat").read_text(encoding="utf-8")
        self.assertIn("--icon", build)
        self.assertIn("ordis_market.ico", build)


class TestThemeGlyphs(_QtCase):
    def test_glyph_images_are_written(self):
        glyphs = ensure_ui_icons()
        self.assertEqual(set(glyphs), {"check", "arrow_down", "arrow_up", "arrow_down_hover", "arrow_up_hover"})
        for path in glyphs.values():
            self.assertTrue(Path(path).is_file())
            self.assertNotIn("\\", path)  # forward slashes: safe inside url("...") on Windows


class TestUiStateStore(unittest.TestCase):
    def test_round_trip_and_bad_files(self):
        tmp = Path(tempfile.mkdtemp())
        store = UiStateStore(tmp / "ui_state.json")
        self.assertEqual(store.load(), {})  # no file yet
        store.save({"a": 1})
        self.assertEqual(store.load(), {"a": 1})
        (tmp / "ui_state.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(store.load(), {})
        (tmp / "ui_state.json").write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(store.load(), {})  # valid JSON, wrong shape

    def test_unwritable_location_is_not_fatal(self):
        tmp = Path(tempfile.mkdtemp())
        blocker = tmp / "file"
        blocker.write_text("x")
        UiStateStore(blocker / "sub" / "ui_state.json").save({"a": 1})  # parent is a file: must not raise


class _WindowCase(_QtCase):
    def make_window(self, **kwargs):
        tmp = Path(tempfile.mkdtemp())
        self.tmp = tmp
        store = RelicDataStore(tmp / "relic_data.json")
        store.save(real_data())
        win = MainWindow(
            InventoryParser(), InventoryRepository(tmp / "saved.json"),
            PortfolioAnalyzer(MagicMock(), MagicMock(), AppSettings()),
            relic_store=store, **kwargs,
        )
        self.addCleanup(win.close)
        return win

    def import_inventory(self, win, count=3):
        path = self.tmp / "inv.json"
        path.write_text(json.dumps({"items": [{"item_id": f"x{i}", "quantity": 1} for i in range(count)]}))
        win._import_from_path(str(path), auto=False)


class TestEmptyStates(_WindowCase):
    def test_market_explains_what_to_do_at_each_stage(self):
        win = self.make_window()
        self.assertIs(win.table_stack.currentWidget(), win.table_stack.widget(1))
        self.assertIn("No inventory yet", win.lbl_empty_title.text())
        self.assertTrue(win.btn_clear_filters.isHidden())
        self.assertEqual(win.lbl_row_count.text(), "")

        self.import_inventory(win, 3)
        self.assertEqual(win.lbl_empty_title.text(), "Ready to price your inventory")
        self.assertIn("3 items", win.lbl_empty_hint.text())

        win._report = report_of(analysis(1), analysis(2))
        win._refresh_table()
        self.assertIs(win.table_stack.currentWidget(), win.table)
        self.assertEqual(win.lbl_row_count.text(), "2 of 2 items")

    def test_filters_that_hide_everything_offer_a_way_back(self):
        win = self.make_window()
        win._report = report_of(analysis(1), analysis(2))
        win.txt_search.setText("zzz-no-such-item")
        win._refresh_table()
        self.assertEqual(win.lbl_empty_title.text(), "Nothing matches these filters")
        self.assertFalse(win.btn_clear_filters.isHidden())
        self.assertEqual(win.lbl_row_count.text(), "0 of 2 items")
        win.btn_clear_filters.click()
        self.assertEqual(win.txt_search.text(), "")
        self.assertIs(win.table_stack.currentWidget(), win.table)
        self.assertEqual(win.table.rowCount(), 2)


class TestTableCues(_WindowCase):
    def test_numbers_align_right_with_separators_and_recommendations_are_coloured(self):
        win = self.make_window()
        win._report = report_of(
            analysis(1, quantity=1500, price=12.0, recommendation=Recommendation.SELL),
            analysis(2, quantity=1, price=3.0, recommendation=Recommendation.KEEP),
        )
        win._refresh_table()
        rows = {win.table.item(r, win._COL_ITEM).text(): r for r in range(win.table.rowCount())}
        big = rows["Item 1"]
        self.assertEqual(win.table.item(big, win._COL_QTY).text(), "1,500")
        self.assertEqual(win.table.item(big, win._COL_TOTAL).text(), "18,000p")
        self.assertTrue(win.table.item(big, win._COL_QTY).textAlignment() & Qt.AlignRight)
        self.assertEqual(win.table.item(big, win._COL_RECOMMENDATION).foreground().color().name(), ACCENT_CYAN)
        small = rows["Item 2"]
        self.assertNotEqual(win.table.item(small, win._COL_RECOMMENDATION).foreground().color().name(), ACCENT_CYAN)

    def test_numeric_columns_still_sort_by_value(self):
        win = self.make_window()
        win._report = report_of(analysis(1, price=9.0), analysis(2, price=84.0), analysis(3, price=100.0))
        win._refresh_table()
        win.table.sortItems(win._COL_PRICE, Qt.AscendingOrder)
        self.assertEqual(
            [win.table.item(r, win._COL_PRICE).text() for r in range(3)], ["9p", "84p", "100p"]
        )


class TestShortcutsAndDebounce(_WindowCase):
    def test_shortcuts_exist_and_buttons_advertise_them(self):
        win = self.make_window()
        keys = {s.key().toString() for s in win._shortcuts}
        self.assertTrue({"Ctrl+O", "Ctrl+R", "F5", "Ctrl+E", "Ctrl+F", "Ctrl+1", "Ctrl+2", "Ctrl+3"} <= keys)
        for button, key in ((win.btn_import, "Ctrl+O"), (win.btn_analyze, "Ctrl+R"), (win.btn_update_market, "F5"), (win.btn_export, "Ctrl+E")):
            self.assertIn(f"Shortcut: {key}", button.toolTip())
        win._update_button_states()  # re-run: the hint must not pile up
        self.assertEqual(win.btn_update_market.toolTip().count("Shortcut: F5"), 1)

    def test_search_shortcut_opens_the_market_tab(self):
        win = self.make_window()
        self.assertIs(win.tabs.currentWidget(), win.home_tab)
        win._focus_search()
        self.assertIs(win.tabs.currentWidget(), win._market_page)

    def test_min_score_changes_are_debounced(self):
        win = self.make_window()
        refreshes = []
        win._refresh_table = lambda: refreshes.append(1)
        win._search_debounce_timer.timeout.disconnect()
        win._search_debounce_timer.timeout.connect(win._refresh_table)
        for value in (10, 20, 30, 40):
            win.spin_min_score.setValue(value)
        self.assertEqual(refreshes, [])  # nothing yet: still waiting for the last step
        self.assertTrue(win._search_debounce_timer.isActive())
        win._search_debounce_timer.timeout.emit()
        self.assertEqual(refreshes, [1])

    def test_primary_actions_are_marked(self):
        win = self.make_window()
        self.assertEqual(win.btn_analyze.property("role"), "primary")
        self.assertEqual(win.btn_update_market.property("role"), "primary")
        self.assertEqual(win.btn_launch_warframe.property("role"), "ghost")


class TestRememberedWindowState(_WindowCase):
    def test_filters_sort_and_geometry_come_back(self):
        state_path = Path(tempfile.mkdtemp()) / "ui_state.json"
        win = self.make_window(ui_state_path=state_path)
        win.resize(1111, 666)
        win.txt_search.setText("serration")
        win.chk_tradable_only.setCurrentIndex(2)
        win.spin_min_score.setValue(35)
        win.chk_hide_prime_sets.setChecked(True)
        win.table.horizontalHeader().setSortIndicator(win._COL_TOTAL, Qt.DescendingOrder)
        win.close()
        saved = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["filters"], {"search": "serration", "type": 2, "min_score": 35, "hide_prime_sets": True})

        restored = []
        original = MainWindow.restoreGeometry
        MainWindow.restoreGeometry = lambda self, data: restored.append(bytes(data.toBase64()).decode("ascii")) or original(self, data)
        self.addCleanup(setattr, MainWindow, "restoreGeometry", original)
        again = self.make_window(ui_state_path=state_path)
        self.assertEqual(restored, [saved["geometry"]])  # the saved geometry is what gets restored
        self.assertEqual(again.txt_search.text(), "serration")
        self.assertEqual(again.chk_tradable_only.currentIndex(), 2)
        self.assertEqual(again.spin_min_score.value(), 35)
        self.assertTrue(again.chk_hide_prime_sets.isChecked())
        header = again.table.horizontalHeader()
        self.assertEqual((header.sortIndicatorSection(), header.sortIndicatorOrder()), (again._COL_TOTAL, Qt.DescendingOrder))
        self.assertTrue(saved["geometry"])
        self.assertIs(again.tabs.currentWidget(), again.home_tab)  # always opens on HOME

    def test_nonsense_state_is_ignored(self):
        state_path = Path(tempfile.mkdtemp()) / "ui_state.json"
        state_path.write_text(json.dumps({"geometry": 5, "filters": {"min_score": "many", "type": 99}, "sort": ["x"]}))
        win = self.make_window(ui_state_path=state_path)
        self.assertEqual(win.spin_min_score.value(), 0)

    def test_no_state_path_means_nothing_is_written(self):
        win = self.make_window()
        win.close()  # must simply work


class TestFlowLayout(_QtCase):
    def make(self, width):
        host = QWidget()
        layout = FlowLayout(host, h_spacing=10, v_spacing=5)
        for _ in range(4):
            button = QPushButton("x")
            button.setFixedSize(100, 30)
            layout.addWidget(button)
        host.resize(width, 200)
        return host, layout

    def test_wraps_when_narrow_and_stays_on_one_row_when_wide(self):
        _host, layout = self.make(1000)
        self.assertEqual(layout.heightForWidth(1000), 30)  # 4 x 100 + gaps fit
        self.assertEqual(layout.heightForWidth(250), 30 * 2 + 5)  # two per row
        self.assertEqual(layout.heightForWidth(100), 30 * 4 + 5 * 3)  # one per row

    def test_minimum_width_is_the_widest_item_not_the_sum(self):
        _host, layout = self.make(1000)
        self.assertEqual(layout.minimumSize().width(), 100)


class TestRelicsEmptyStates(_QtCase):
    def make_tab(self, items):
        from app.ui import relics_tab as rt

        class Store:
            def load(self):
                return real_data()

            def is_stale(self, data):
                return False

        self.items = items
        tab = rt.RelicsTab(Store(), lambda: self.items, lambda w: None, lambda m: None)
        tab.on_activated()
        return tab

    def test_empty_completable_list_explains_itself_and_can_widen(self):
        tab = self.make_tab([inv("gyreprimeblueprint")])
        self.assertEqual(tab.table.rowCount(), 0)
        self.assertEqual(tab.view_stack.currentIndex(), 1)
        self.assertIn("No set can be finished", tab.lbl_empty_title.text())
        self.assertFalse(tab.btn_widen.isHidden())
        tab.btn_widen.click()
        self.assertEqual(tab._current_mode(), FilterMode.OWNED)
        self.assertEqual(tab.view_stack.currentIndex(), 0)
        self.assertEqual(tab.lbl_count.text(), "1 set")  # singular

    def test_search_without_matches_has_its_own_message(self):
        tab = self.make_tab([inv("gyreprimeblueprint")])
        tab.show_mode(FilterMode.ALL)
        tab.txt_search.setText("zzzzz")
        tab._render()
        self.assertEqual(tab.lbl_empty_title.text(), "No set matches this search")
        self.assertTrue(tab.btn_widen.isHidden())

    def test_no_inventory_shows_a_neutral_message(self):
        tab = self.make_tab([])
        self.assertEqual(tab.lbl_empty_title.text(), "Nothing to list yet")


if __name__ == "__main__":
    unittest.main()
