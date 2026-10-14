import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HAVE_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAVE_QT, "PySide6 not installed")
class TestTableRefresh(unittest.TestCase):
    """Regression: with the window visible, refilling an already-populated
    table used to take ~17 s for 200 rows (ResizeToContents columns being
    re-measured on every setItem), freezing the app after UPDATE MARKET."""

    def test_second_refresh_of_a_visible_table_is_fast(self):
        from PySide6.QtWidgets import QApplication, QHeaderView

        from app.analysis.portfolio import ItemAnalysis, PortfolioAnalyzer, PortfolioReport
        from app.config.settings import AppSettings, PricingStrategy
        from app.inventory.parser import InventoryParser
        from app.inventory.repository import InventoryRepository
        from app.market.liquidity import LiquidityLevel, LiquidityReport
        from app.market.pricing import PriceQuote
        from app.market.sell_score import Recommendation, SellScoreResult
        from app.ui.main_window import MainWindow

        app = QApplication.instance() or QApplication(sys.argv)
        tmp = Path(tempfile.mkdtemp())
        win = MainWindow(
            InventoryParser(), InventoryRepository(tmp / "s.json"),
            PortfolioAnalyzer(MagicMock(), MagicMock(), AppSettings()),
        )
        n = 300
        analyses = tuple(
            ItemAnalysis(
                item_id=f"i{i}", slug=f"i{i}", display_name=f"Item number {i} Prime Blueprint",
                quantity=i % 7 + 1, tradable=True, category="x", is_prime=True,
                price=PriceQuote(1, 1, 1, float(i % 90 + 1), 3, PricingStrategy.LOWEST),
                liquidity=LiquidityReport(LiquidityLevel.HIGH, 3, 3, 1.0),
                sell_score=SellScoreResult(i % 100, Recommendation.SELL, ("a",)),
            )
            for i in range(n)
        )
        win._report = PortfolioReport(analyses, n, n, 1000.0, 0, n)
        win.resize(1200, 800)
        win.show()
        app.processEvents()
        try:
            win._refresh_table()
            app.processEvents()
            started = time.time()
            win._refresh_table()  # what _on_analysis_done does after UPDATE MARKET
            app.processEvents()
            elapsed = time.time() - started
            self.assertEqual(win.table.rowCount(), n)
            self.assertLess(elapsed, 3.0, f"refresh took {elapsed:.1f}s")
            # the columns are back to auto-sizing after the refill
            header = win.table.horizontalHeader()
            self.assertEqual(header.sectionResizeMode(1), QHeaderView.ResizeToContents)
            self.assertGreaterEqual(header.sectionSize(0), win._ITEM_COLUMN_MIN)  # the Item column absorbs the free width
            self.assertTrue(win.table.isSortingEnabled())
            self.assertTrue(win.table.updatesEnabled())
        finally:
            win.close()


if __name__ == "__main__":
    unittest.main()
