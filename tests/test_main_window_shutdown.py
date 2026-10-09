import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

import importlib.util

HAVE_QT = importlib.util.find_spec("PySide6") is not None

ROOT = Path(__file__).resolve().parent.parent
# Captured at import time: other tests temporarily fake sys.executable (frozen-exe
# path tests), and a leaked fake value must not break launching the subprocess.
PYTHON = sys.executable

# Runs in a subprocess: the bug this guards against is a hard process abort
# ("QThread: Destroyed while thread is still running"), which would take the
# whole test runner down with it instead of failing one test.
_SCRIPT = textwrap.dedent(
    """
    import sys, tempfile, time
    from pathlib import Path
    from unittest.mock import MagicMock
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from app.analysis.portfolio import PortfolioAnalyzer
    from app.catalog.catalog import CatalogEntry, ItemCatalog
    from app.config.settings import AppSettings
    from app.inventory.parser import InventoryParser
    from app.inventory.repository import InventoryRepository
    from app.market.models import ItemOrders
    from app.market.repository import OrdersResult
    from app.ui.main_window import MainWindow

    slugs = [f"item_{i}" for i in range(12)]
    catalog = ItemCatalog.__new__(ItemCatalog)
    catalog._entries = {s: CatalogEntry(slug=s, item_id=s, name=s, category="misc", tradable=True) for s in slugs}
    catalog._name_index = {s: s for s in slugs}
    catalog._game_ref_index = {}

    repo = MagicMock()
    def slow(slug, force_refresh=False):
        time.sleep(0.5)
        return OrdersResult(item_orders=ItemOrders(slug=slug, sell_orders=(), buy_orders=(), fetched_at=time.time()),
                            from_cache=False, stale=False)
    repo.get_orders.side_effect = slow

    app = QApplication(sys.argv)
    tmp = Path(tempfile.mkdtemp())
    inv = tmp / "inv.json"
    inv.write_text('{"items": [' + ",".join('{"item_id": "%s", "quantity": 1}' % s for s in slugs) + ']}')
    win = MainWindow(InventoryParser(), InventoryRepository(tmp / "saved.json"),
                     PortfolioAnalyzer(catalog, repo, AppSettings()))
    win._import_from_path(str(inv), auto=False)
    win._on_analyze_clicked()

    def close_mid_run():
        assert win._worker.isRunning(), "analysis finished too early for this test"
        win.close()
        app.quit()

    QTimer.singleShot(200, close_mid_run)
    app.exec()
    assert not win._worker.isRunning()
    print("OK")
    """
)


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class TestMainWindowShutdown(unittest.TestCase):
    def test_closing_during_analysis_does_not_abort(self):
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(ROOT))
        proc = subprocess.run(
            [PYTHON, "-c", _SCRIPT],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
