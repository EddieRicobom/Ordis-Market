import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.analysis.portfolio import ItemAnalysis, PortfolioReport
from app.export import exporter
from app.market.liquidity import LiquidityLevel
from app.market.sell_score import Recommendation


def make_report() -> PortfolioReport:
    analysis = ItemAnalysis(
        item_id="mesa_prime_systems",
        slug="mesa_prime_systems",
        display_name="Mesa Prime Systems",
        quantity=2,
        tradable=True,
        category="warframe_part",
        is_prime=True,
    )
    # Manually set post-init-only-like fields via price/liquidity/sell_score
    from app.market.pricing import PriceQuote
    from app.market.liquidity import LiquidityReport
    from app.market.sell_score import SellScoreResult
    from app.market.ducats import DucatComparison, DucatVerdict
    from app.config.settings import PricingStrategy

    analysis.price = PriceQuote(30, 31, 30.5, 30, 5, PricingStrategy.RECOMMENDED)
    analysis.liquidity = LiquidityReport(LiquidityLevel.HIGH, 10, 5, 3.0)
    analysis.sell_score = SellScoreResult(80, Recommendation.SELL, ("High liquidity",))
    analysis.wiki_url = "https://wiki.warframe.com/w/Mesa_Prime"
    analysis.ducats = DucatComparison(
        platinum_price=30, ducats=45, plat_per_ducat=0.6667, reference_plat_per_ducat=8.0,
        verdict=DucatVerdict.KEEP_FOR_DUCATS,
    )

    return PortfolioReport(
        analyses=(analysis,),
        total_inventory_items=1,
        total_tradable_items=1,
        estimated_total_value=60.0,
        unresolved_count=0,
    )


class TestExporter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.report = make_report()

    def test_export_csv(self):
        path = Path(self.tmp_dir.name) / "out.csv"
        exporter.export_csv(self.report, path)
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0], exporter._HEADERS)
        self.assertEqual(rows[1][0], "Mesa Prime Systems")
        self.assertEqual(rows[1][exporter._HEADERS.index("Recommendation")], "SELL")
        self.assertEqual(
            rows[1][exporter._HEADERS.index("WikiURL")], "https://wiki.warframe.com/w/Mesa_Prime"
        )
        self.assertEqual(rows[1][exporter._HEADERS.index("Ducats")], "45")
        self.assertEqual(rows[1][exporter._HEADERS.index("DucatVerdict")], "KEEP FOR DUCATS")

    def test_export_csv_omits_ducats_when_insufficient_data(self):
        from app.market.ducats import DucatComparison, DucatVerdict

        self.report.analyses[0].ducats = DucatComparison(
            platinum_price=None, ducats=None, plat_per_ducat=None,
            reference_plat_per_ducat=8.0, verdict=DucatVerdict.INSUFFICIENT_DATA,
        )
        path = Path(self.tmp_dir.name) / "out.csv"
        exporter.export_csv(self.report, path)
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[1][exporter._HEADERS.index("Ducats")], "")

    def test_export_json(self):
        path = Path(self.tmp_dir.name) / "out.json"
        exporter.export_json(self.report, path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["estimated_total_value"], 60.0)
        self.assertEqual(payload["items"][0]["item"], "Mesa Prime Systems")

    def test_export_xlsx_without_openpyxl_raises_export_error(self):
        try:
            import openpyxl  # noqa: F401

            self.skipTest("openpyxl is installed in this environment")
        except ImportError:
            pass
        path = Path(self.tmp_dir.name) / "out.xlsx"
        with self.assertRaises(exporter.ExportError):
            exporter.export_xlsx(self.report, path)


if __name__ == "__main__":
    unittest.main()
