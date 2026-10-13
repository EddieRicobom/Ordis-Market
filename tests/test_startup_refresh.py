import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from tests.test_home_tab import HAVE_QT, _QtCase

if HAVE_QT:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from app.analysis.portfolio import PortfolioAnalyzer
    from app.catalog.updater import CatalogUpdateResult, NameIndexUpdateResult
    from app.config.settings import AppSettings
    from app.inventory.parser import InventoryParser
    from app.inventory.repository import InventoryRepository
    from app.ui.main_window import MainWindow


def pump(predicate, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


class TestStartupRefresh(_QtCase):
    def make_window(self, initial_catalog=0, updater=None, auto=False):
        tmp = Path(tempfile.mkdtemp())
        self.tmp = tmp
        self.updater = updater or MagicMock()
        name_updater = MagicMock()
        name_updater.ensure_fresh.return_value = NameIndexUpdateResult(updated=False, entry_count=7, used_cache=True)
        win = MainWindow(
            InventoryParser(), InventoryRepository(tmp / "saved.json"),
            PortfolioAnalyzer(MagicMock(), MagicMock(), AppSettings()),
            self.updater, name_updater,
            initial_catalog_count=initial_catalog,
            refresh_catalog_on_start=True,
            auto_update_market=auto,
        )
        self.addCleanup(win.close)
        return win

    def test_window_is_built_without_touching_the_network(self):
        # Slow download: constructing the window must not wait for it.
        gate = threading.Event()
        updater = MagicMock()
        updater.ensure_fresh.side_effect = lambda force=False: (
            gate.wait(5) and CatalogUpdateResult(updated=True, entry_count=123, used_cache=False)
        )
        started = time.time()
        win = self.make_window(updater=updater)
        self.assertLess(time.time() - started, 1.0)
        self.assertTrue(pump(lambda: win._startup_refresh_running()))
        updater.ensure_fresh.assert_called_once_with(force=False)
        gate.set()
        self.assertTrue(pump(lambda: win.lbl_catalog_status.text() == "Catalog: 123 items known"))
        self.assertEqual(win.lbl_names_status.text(), "Item Names: 7 known")
        self.assertTrue(pump(lambda: not win._startup_refresh_running()))
        self.assertTrue(win._catalog_ready)

    def test_first_run_analyze_waits_for_the_first_download(self):
        gate = threading.Event()
        updater = MagicMock()
        updater.ensure_fresh.side_effect = lambda force=False: (
            gate.wait(5) and CatalogUpdateResult(updated=True, entry_count=10, used_cache=False)
        )
        win = self.make_window(initial_catalog=0, updater=updater)
        path = self.tmp / "inv.json"
        path.write_text(json.dumps({"items": [{"item_id": "x", "quantity": 1}]}))
        win._import_from_path(str(path), auto=False)
        self.assertTrue(pump(lambda: win._startup_refresh_running()))

        win._on_analyze_clicked()
        self.assertIsNone(win._worker)  # no analysis started on an empty catalog
        self.assertIn("catalog", win.statusBar().currentMessage().lower())
        gate.set()
        self.assertTrue(pump(lambda: win._catalog_ready))

    def test_with_a_catalog_on_disk_analyze_does_not_wait(self):
        gate = threading.Event()
        updater = MagicMock()
        updater.ensure_fresh.side_effect = lambda force=False: (
            gate.wait(5) and CatalogUpdateResult(updated=False, entry_count=10, used_cache=True)
        )
        win = self.make_window(initial_catalog=10, updater=updater)
        path = self.tmp / "inv.json"
        path.write_text(json.dumps({"items": [{"item_id": "x", "quantity": 1}]}))
        win._import_from_path(str(path), auto=False)
        self.assertTrue(pump(lambda: win._startup_refresh_running()))
        win._on_analyze_clicked()
        self.assertIsNotNone(win._worker)
        gate.set()
        pump(lambda: not win._worker.isRunning())

    def test_auto_market_update_starts_once_the_refresh_is_done(self):
        win = self.make_window(initial_catalog=10, auto=True)
        path = self.tmp / "inv.json"
        path.write_text(json.dumps({"items": [{"item_id": "x", "quantity": 1}]}))
        win._import_from_path(str(path), auto=False)
        calls = []
        win._on_analyze_clicked = lambda: calls.append(1)
        self.updater.ensure_fresh.return_value = CatalogUpdateResult(updated=False, entry_count=10, used_cache=True)
        # Let the startup worker finish, then run the follow-up the window schedules.
        self.assertTrue(pump(lambda: not win._catalog_worker_is_startup and win._catalog_worker is not None, 5))
        QTimer.singleShot(0, lambda: None)
        pump(lambda: bool(calls), 2)
        self.assertEqual(calls, [1])
        self.assertFalse(win._force_refresh_next_analysis)

    def test_failed_download_is_reported_quietly(self):
        updater = MagicMock()
        updater.ensure_fresh.return_value = CatalogUpdateResult(updated=False, entry_count=0, used_cache=False, error="no route")
        win = self.make_window(updater=updater)
        win._show_error = MagicMock()
        self.assertTrue(pump(lambda: "no route" in win.statusBar().currentMessage()))
        win._show_error.assert_not_called()
        self.assertFalse(win._catalog_ready)


class TestProgressEta(_QtCase):
    def make_window(self):
        tmp = Path(tempfile.mkdtemp())
        win = MainWindow(
            InventoryParser(), InventoryRepository(tmp / "saved.json"),
            PortfolioAnalyzer(MagicMock(), MagicMock(), AppSettings()),
        )
        self.addCleanup(win.close)
        return win

    def test_progress_bar_shows_the_time_left_when_it_is_known(self):
        win = self.make_window()
        win._eta = MagicMock()
        win._eta.update.return_value = 125.0
        win._on_progress(300, 852)
        self.assertEqual((win.progress_bar.value(), win.progress_bar.maximum()), (300, 852))
        self.assertEqual(win.progress_bar.format(), "%v / %m  -  ~3 min left")

        win._eta.update.return_value = None  # not enough data yet / nearly done
        win._on_progress(301, 852)
        self.assertEqual(win.progress_bar.format(), "%p%")

    def test_progress_bar_has_a_tooltip(self):
        self.assertIn("time left", self.make_window().progress_bar.toolTip())


if __name__ == "__main__":
    unittest.main()
