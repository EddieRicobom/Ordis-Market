import time
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.analysis.portfolio import (
    CHEAP_ITEM_MAX_AGE_SECONDS,
    PortfolioAnalyzer,
    plan_fetch_order,
    value_hints_from_report,
)
from app.catalog.catalog import CatalogEntry, ItemCatalog
from app.config.settings import AppSettings
from app.inventory.models import InventoryItem, InventorySnapshot
from app.market.models import ItemOrders, MarketOrder, OrderType
from app.market.repository import OrdersResult


class TestPlanFetchOrder(unittest.TestCase):
    def test_most_valuable_first_and_ties_keep_inventory_order(self):
        order, _ = plan_fetch_order(["a", "b", "c", "d"], {"a": 5, "b": 50, "c": 5, "d": 500})
        self.assertEqual(order, ["d", "b", "a", "c"])

    def test_unknown_slugs_rank_between_valuable_and_worthless(self):
        order, _ = plan_fetch_order(["cheap", "new", "big"], {"cheap": 1, "big": 900})
        self.assertEqual(order, ["big", "new", "cheap"])

    def test_cheap_tail_is_whatever_lies_beyond_the_first_95_percent_of_the_value(self):
        hints = {"big": 600, "mid": 350, "s1": 30, "s2": 20}  # total 1000
        _, cheap = plan_fetch_order(list(hints), hints, tail_share=0.05)
        self.assertEqual(cheap, {"s1", "s2"})  # big + mid already cover exactly 95%

    def test_one_dominant_item_makes_everything_else_cheap(self):
        hints = {"big": 960, "mid": 30, "s1": 10}
        _, cheap = plan_fetch_order(list(hints), hints, tail_share=0.05)
        self.assertEqual(cheap, {"mid", "s1"})

    def test_unknown_slugs_are_never_cheap(self):
        _, cheap = plan_fetch_order(["big", "new"], {"big": 100}, tail_share=0.5)
        self.assertNotIn("new", cheap)

    def test_no_tail_without_value_or_when_disabled(self):
        self.assertEqual(plan_fetch_order(["a", "b"], {"a": 0, "b": 0})[1], set())
        self.assertEqual(plan_fetch_order(["a", "b"], {"a": 10, "b": 1}, tail_share=0)[1], set())


def _orders(slug, price):
    return ItemOrders(
        slug=slug,
        sell_orders=(MarketOrder(OrderType.SELL, price, 1, True, "ingame"),),
        buy_orders=(),
        fetched_at=time.time(),
    )


class TestAnalyzerFetchPlan(unittest.TestCase):
    def setUp(self):
        slugs = ["big", "mid", "cheap1", "cheap2"]
        self.catalog = ItemCatalog.__new__(ItemCatalog)
        self.catalog._entries = {
            s: CatalogEntry(slug=s, item_id=s, name=s, category="misc", tradable=True) for s in slugs
        }
        self.catalog._name_index = {s: s for s in slugs}
        self.catalog._game_ref_index = {}
        self.snapshot = InventorySnapshot(
            items=tuple(InventoryItem(s, 1, s) for s in ["cheap1", "mid", "cheap2", "big"]),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        self.fetched = []
        self.repo = MagicMock()
        self.repo.get_orders.side_effect = self._get_orders
        # max_age_seconds is what only the cheap tail passes
        self.max_ages = {}

    def _get_orders(self, slug, force_refresh=False, max_age_seconds=None):
        self.fetched.append(slug)
        self.max_ages[slug] = max_age_seconds
        return OrdersResult(
            item_orders=_orders(slug, 10), from_cache=max_age_seconds is not None, stale=False
        )

    def analyzer(self):
        return PortfolioAnalyzer(self.catalog, self.repo, AppSettings(), max_workers=1)

    HINTS = {"big": 900.0, "mid": 90.0, "cheap1": 5.0, "cheap2": 5.0}

    def test_without_hints_nothing_changes(self):
        report = self.analyzer().analyze(self.snapshot, force_refresh=True)
        self.assertEqual(self.fetched, ["cheap1", "mid", "cheap2", "big"])  # inventory order
        self.assertTrue(all(v is None for v in self.max_ages.values()))
        self.assertEqual(report.cheap_reused_slug_count, 0)

    def test_hints_fetch_valuable_slugs_first(self):
        self.analyzer().analyze(self.snapshot, force_refresh=False, value_hints=self.HINTS)
        self.assertEqual(self.fetched, ["big", "mid", "cheap1", "cheap2"])
        self.assertTrue(all(v is None for v in self.max_ages.values()))  # no tail unless forced

    def test_forced_refresh_lets_the_cheap_tail_reuse_recent_prices(self):
        report = self.analyzer().analyze(self.snapshot, force_refresh=True, value_hints=self.HINTS)
        self.assertEqual(self.fetched, ["big", "mid", "cheap1", "cheap2"])
        self.assertIsNone(self.max_ages["big"])
        self.assertIsNone(self.max_ages["mid"])
        self.assertEqual(self.max_ages["cheap1"], CHEAP_ITEM_MAX_AGE_SECONDS)
        self.assertEqual(self.max_ages["cheap2"], CHEAP_ITEM_MAX_AGE_SECONDS)
        self.assertEqual(report.cheap_reused_slug_count, 2)
        self.assertEqual(report.market_error_slug_count, 0)

    def test_value_hints_from_a_previous_report(self):
        report = self.analyzer().analyze(self.snapshot)
        hints = value_hints_from_report(report)
        self.assertEqual(set(hints), {"big", "mid", "cheap1", "cheap2"})
        self.assertEqual(hints["big"], 10.0)
        self.assertEqual(value_hints_from_report(None), {})


if __name__ == "__main__":
    unittest.main()
