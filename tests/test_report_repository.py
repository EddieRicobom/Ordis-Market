import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.analysis.portfolio import ItemAnalysis, PortfolioReport
from app.analysis.report_repository import ReportRepository
from app.config.settings import PricingStrategy
from app.market.ducats import DucatComparison, DucatVerdict
from app.market.liquidity import LiquidityLevel, LiquidityReport
from app.market.pricing import PriceQuote
from app.market.sell_score import Recommendation, SellScoreResult


def make_full_report() -> PortfolioReport:
    rich_analysis = ItemAnalysis(
        item_id="mesa_prime_systems",
        slug="mesa_prime_systems",
        display_name="Mesa Prime Systems",
        base_name="Mesa Prime Systems",
        quantity=3,
        tradable=True,
        category="warframe_part",
        is_prime=True,
        price=PriceQuote(30, 31, 30.5, 30, 5, PricingStrategy.LOWEST),
        liquidity=LiquidityReport(LiquidityLevel.HIGH, 10, 5, 3.0),
        sell_score=SellScoreResult(80, Recommendation.SELL, ("High liquidity", "Good price")),
        ducats=DucatComparison(30, 45, 0.6667, 8.0, DucatVerdict.KEEP_FOR_DUCATS),
        wiki_url="https://wiki.warframe.com/w/Mesa_Prime",
        data_available=True,
    )
    sparse_analysis = ItemAnalysis(
        item_id="unknown_thing",
        slug=None,
        display_name="Unknown Thing",
        base_name="Unknown Thing",
        quantity=1,
        tradable=False,
        category="unknown",
        is_prime=False,
        data_available=False,
        error="Not found in the item catalog.",
    )
    return PortfolioReport(
        analyses=(rich_analysis, sparse_analysis),
        total_inventory_items=2,
        total_tradable_items=1,
        estimated_total_value=90.0,
        unresolved_count=0,
        catalog_matched_count=1,
        stale_price_slug_count=1,
        market_error_slug_count=0,
    )


class TestReportRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.repo = ReportRepository(Path(self.tmp_dir.name) / "last_analysis.json")

    def test_no_saved_report_returns_none(self):
        self.assertIsNone(self.repo.load())

    def test_full_round_trip_preserves_all_fields(self):
        original = make_full_report()
        self.repo.save(original, "2026-09-05T10:00:00+00:00")

        loaded = self.repo.load()
        self.assertIsNotNone(loaded)
        report, analyzed_at = loaded
        self.assertEqual(analyzed_at, "2026-09-05T10:00:00+00:00")

        self.assertEqual(report.total_inventory_items, 2)
        self.assertEqual(report.total_tradable_items, 1)
        self.assertEqual(report.estimated_total_value, 90.0)
        self.assertEqual(report.catalog_matched_count, 1)
        self.assertEqual(report.stale_price_slug_count, 1)
        self.assertEqual(len(report.analyses), 2)

        rich = report.analyses[0]
        self.assertEqual(rich.display_name, "Mesa Prime Systems")
        self.assertEqual(rich.price.recommended_price, 30)
        self.assertEqual(rich.price.strategy_used, PricingStrategy.LOWEST)
        self.assertEqual(rich.liquidity.level, LiquidityLevel.HIGH)
        self.assertEqual(rich.sell_score.recommendation, Recommendation.SELL)
        self.assertEqual(rich.sell_score.reasons, ("High liquidity", "Good price"))
        self.assertEqual(rich.ducats.verdict, DucatVerdict.KEEP_FOR_DUCATS)
        self.assertEqual(rich.wiki_url, "https://wiki.warframe.com/w/Mesa_Prime")

        sparse = report.analyses[1]
        self.assertIsNone(sparse.slug)
        self.assertIsNone(sparse.price)
        self.assertIsNone(sparse.liquidity)
        self.assertFalse(sparse.data_available)
        self.assertEqual(sparse.error, "Not found in the item catalog.")

    def test_corrupt_file_returns_none_not_crash(self):
        self.repo._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.repo._storage_path.write_text("not json{{{", encoding="utf-8")
        self.assertIsNone(self.repo.load())

    def test_missing_required_key_returns_none_not_crash(self):
        import json

        self.repo._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.repo._storage_path.write_text(json.dumps({"analyses": []}), encoding="utf-8")
        self.assertIsNone(self.repo.load())

    def test_clear_removes_the_file(self):
        self.repo.save(make_full_report(), "2026-09-05T10:00:00+00:00")
        self.assertTrue(self.repo._storage_path.exists())
        self.repo.clear()
        self.assertFalse(self.repo._storage_path.exists())
        self.assertIsNone(self.repo.load())

    def test_clear_on_nonexistent_file_does_not_raise(self):
        self.repo.clear()  # must not raise

    def test_overwrite_replaces_previous_save(self):
        self.repo.save(make_full_report(), "2026-09-05T10:00:00+00:00")
        smaller = PortfolioReport(
            analyses=(),
            total_inventory_items=0,
            total_tradable_items=0,
            estimated_total_value=0.0,
            unresolved_count=0,
        )
        self.repo.save(smaller, "2026-09-05T11:00:00+00:00")

        loaded_report, analyzed_at = self.repo.load()
        self.assertEqual(analyzed_at, "2026-09-05T11:00:00+00:00")
        self.assertEqual(len(loaded_report.analyses), 0)


if __name__ == "__main__":
    unittest.main()
