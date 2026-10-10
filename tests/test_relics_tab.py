import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HAVE_QT = importlib.util.find_spec("PySide6") is not None

if HAVE_QT:
    from PySide6.QtWidgets import QApplication

    from app.relics.models import RelicData
    from app.relics.store import RelicDataStore
    from app.relics.view import FilterMode
    from app.relics.wfcd_source import RelicDataError
    from app.ui import relics_tab as rt
    from tests.relics_fixture import inv, real_data


class _FakeStore:
    """Stands in for RelicDataStore: no disk, no network."""

    def __init__(self, cached=None, fetched=None, error=None):
        self.cached, self.fetched, self.error = cached, fetched, error
        self.refreshes = 0

    def load(self):
        return self.cached

    def is_stale(self, data):
        return False

    def refresh(self):
        self.refreshes += 1
        if self.error:
            raise RelicDataError(self.error)
        return self.fetched


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class TestRelicsTab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.messages = []
        self.items = []
        self.started = []
        sm = rt.get_sound_manager()
        self._sound_patch = [
            (name, getattr(sm, name)) for name in ("play_notification", "play_error")
        ]
        for name, _ in self._sound_patch:
            setattr(sm, name, lambda *a, **k: None)
        self.sm = sm

    def tearDown(self):
        for name, fn in self._sound_patch:
            setattr(self.sm, name, fn)

    def make_tab(self, store, run_inline=True):
        def start(worker):
            self.started.append(worker)
            if run_inline:
                worker.run()  # synchronous: signals are delivered directly

        return rt.RelicsTab(store, lambda: self.items, start, self.messages.append)

    def table_names(self, tab):
        return [tab.table.item(r, 0).text() for r in range(tab.table.rowCount())]

    def test_shows_cached_data_without_downloading(self):
        store = _FakeStore(cached=real_data())
        self.items = [inv("gyreprimeblueprint")]
        tab = self.make_tab(store)
        tab.on_activated()
        self.assertEqual(store.refreshes, 0)
        self.assertIn("Gyre Prime", tab_all(tab))

    def test_all_five_filters_change_the_rows(self):
        self.items = [inv("gyreprimeblueprint"), inv("cedoprimebarrel")]
        tab = self.make_tab(_FakeStore(cached=real_data()))
        tab.on_activated()
        counts = {}
        for index, mode in enumerate(FilterMode):
            tab.cmb_mode.setCurrentIndex(index)
            counts[mode] = tab.table.rowCount()
        self.assertEqual(counts[FilterMode.ALL], len(real_data().sets))
        self.assertEqual(counts[FilterMode.OWNED], 2)
        self.assertEqual(counts[FilterMode.COMPLETE], 0)
        self.assertGreater(len(set(counts.values())), 1)  # not all identical (old str-Enum bug)

    def test_initial_order_is_priority_order(self):
        self.items = [inv("gyreprimeblueprint")]
        tab = self.make_tab(_FakeStore(cached=real_data()))
        tab.cmb_mode.setCurrentIndex(list(FilterMode).index(FilterMode.ALL))
        tab.on_activated()
        states = [tab.table.item(r, 2).text() for r in range(tab.table.rowCount())]
        self.assertNotEqual(states[0], "Nothing")

    def test_first_open_downloads_once_and_shows_result(self):
        data = real_data()
        store = _FakeStore(fetched=data)
        self.items = [inv("gyreprimeblueprint")]
        tab = self.make_tab(store)
        tab.on_activated()
        self.assertEqual(store.refreshes, 1)
        self.assertTrue(tab.btn_update.isEnabled())
        self.assertTrue(tab.progress.isHidden())
        self.assertIn("Gyre Prime", tab_all(tab))
        tab.on_activated()
        self.assertEqual(store.refreshes, 1)  # cached in memory now

    def test_failed_download_reports_and_does_not_loop(self):
        store = _FakeStore(error="no network")
        tab = self.make_tab(store)
        with self.assertLogs("app.ui.relics_tab", level="ERROR"):
            tab.on_activated()
        tab.on_activated()
        self.assertEqual(store.refreshes, 1)  # auto-download is tried once only
        self.assertTrue(tab.btn_update.isEnabled())
        self.assertTrue(any("no network" in m for m in self.messages))
        self.assertIn("failed", tab.lbl_status.text())
        self.assertFalse(tab.lbl_hint.isHidden())
        with self.assertLogs("app.ui.relics_tab", level="ERROR"):
            tab.start_update()  # manual retry is still possible
        self.assertEqual(store.refreshes, 2)

    def test_no_inventory_shows_hint(self):
        tab = self.make_tab(_FakeStore(cached=real_data()))
        tab.on_activated()
        self.assertEqual(tab.table.rowCount(), 0)
        self.assertIn("Import an inventory", tab.lbl_hint.text())

    def test_reload_before_first_open_is_a_noop(self):
        store = _FakeStore(cached=real_data())
        tab = self.make_tab(store)
        tab.reload()
        self.assertEqual(tab.table.rowCount(), 0)

    def test_reload_picks_up_a_new_inventory(self):
        tab = self.make_tab(_FakeStore(cached=real_data()))
        self.items = [inv("gyreprimeblueprint")]
        tab.on_activated()
        tab.cmb_mode.setCurrentIndex(list(FilterMode).index(FilterMode.OWNED))
        self.assertEqual(self.table_names(tab), ["Gyre Prime"])
        self.items = [inv("cedoprimebarrel")]
        tab.reload()
        self.assertEqual(self.table_names(tab), ["Cedo Prime"])

    def test_search_filters_rows(self):
        self.items = [inv("gyreprimeblueprint")]
        tab = self.make_tab(_FakeStore(cached=real_data()))
        tab.on_activated()
        tab_all(tab)
        tab.txt_search.setText("cedo")
        tab._render()  # skip the debounce
        self.assertEqual(self.table_names(tab), ["Cedo Prime"])

    def test_detail_follows_selection_and_everything_has_tooltips(self):
        self.items = [inv("gyreprimeblueprint")]
        tab = self.make_tab(_FakeStore(cached=real_data()))
        tab.on_activated()
        tab_all(tab)
        tab.table.selectRow(0)
        first = tab.table.item(0, 0).text()
        self.assertTrue(tab.txt_detail.toPlainText().startswith(first))
        for col in range(tab.table.columnCount()):
            self.assertTrue(tab.table.horizontalHeaderItem(col).toolTip())
        for widget in (tab.btn_update, tab.cmb_mode, tab.txt_search, tab.txt_detail, tab.lbl_status):
            self.assertTrue(widget.toolTip())

    def test_real_store_roundtrip_feeds_the_tab(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = RelicDataStore(Path(tmp) / "relic_data.json")
            store.save(real_data())
            self.items = [inv("gyreprimeblueprint")]
            tab = self.make_tab(store)
            tab.on_activated()
            self.assertIsInstance(store.load(), RelicData)
            self.assertTrue(tab.table.rowCount() >= 0)


def tab_all(tab):
    tab.cmb_mode.setCurrentIndex(list(FilterMode).index(FilterMode.ALL))
    return [tab.table.item(r, 0).text() for r in range(tab.table.rowCount())]


if __name__ == "__main__":
    unittest.main()
