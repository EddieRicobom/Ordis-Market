import importlib.util
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

HAVE_QT = importlib.util.find_spec("PySide6") is not None
ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

_SETUP = textwrap.dedent(
    """
    import sys, tempfile, time
    from pathlib import Path
    from unittest.mock import MagicMock
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from app.analysis.portfolio import PortfolioAnalyzer
    from app.config.settings import AppSettings
    from app.inventory.parser import InventoryParser
    from app.inventory.repository import InventoryRepository
    from app.relics.store import RelicDataStore
    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    tmp = Path(tempfile.mkdtemp())
    def make(store):
        return MainWindow(InventoryParser(), InventoryRepository(tmp / "saved.json"),
                          PortfolioAnalyzer(MagicMock(), MagicMock(), AppSettings()), relic_store=store)
    """
)

_TABS = _SETUP + textwrap.dedent(
    """
    plain = make(None)
    assert plain.relics_tab is None
    win = make(RelicDataStore(tmp / "relic_data.json"))
    assert win.tabs.count() == 2 and win.tabs.tabText(1) == "RELICS"
    print("OK")
    """
)

# The relic download is a blocking network call; closing the window mid-download
# must not abort the process ("QThread: Destroyed while thread is still running").
_SHUTDOWN = _SETUP + textwrap.dedent(
    """
    class Slow(RelicDataStore):
        def load(self):
            return None
        def refresh(self, fetcher=None):
            time.sleep(1.0)
            raise RuntimeError("cancelled by test")

    win = make(Slow(tmp / "relic_data.json"))
    win.show()
    win.tabs.setCurrentIndex(1)  # first visit starts the auto-download
    def close_mid_download():
        assert win.relics_tab._worker.isRunning(), "download finished too early for this test"
        win.close()
        app.quit()
    QTimer.singleShot(200, close_mid_download)
    app.exec()
    assert not win.relics_tab._worker.isRunning()
    print("OK")
    """
)


def _run(script):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH=str(ROOT))
    return subprocess.run([PYTHON, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class TestMainWindowRelics(unittest.TestCase):
    def test_tabs_only_exist_with_a_relic_store(self):
        proc = _run(_TABS)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertIn("OK", proc.stdout)

    def test_closing_during_relic_download_does_not_abort(self):
        proc = _run(_SHUTDOWN)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
