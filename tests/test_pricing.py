import time
import unittest

from app.config.settings import PricingStrategy
from app.market.models import ItemOrders, MarketOrder, OrderType
from app.market.pricing import PriceAnalyzer


def make_order(order_type: OrderType, platinum: float, online: bool = True) -> MarketOrder:
    return MarketOrder(order_type=order_type, platinum=platinum, quantity=1, user_online=online)


class TestPriceAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = PriceAnalyzer()

    def test_no_orders_returns_none_quote(self):
        item_orders = ItemOrders(slug="x", sell_orders=(), buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders)
        self.assertIsNone(quote.recommended_price)
        self.assertEqual(quote.sample_size, 0)

    def test_lowest_strategy(self):
        sells = (
            make_order(OrderType.SELL, 20),
            make_order(OrderType.SELL, 15),
            make_order(OrderType.SELL, 18),
        )
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.LOWEST)
        self.assertEqual(quote.recommended_price, 15)
        self.assertEqual(quote.lowest_sell, 15)

    def test_average_and_median(self):
        sells = tuple(make_order(OrderType.SELL, p) for p in (10, 20, 30, 40))
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.AVERAGE)
        self.assertAlmostEqual(quote.average_sell, 25.0)
        self.assertAlmostEqual(quote.median_sell, 25.0)

    def test_offline_orders_excluded_by_default(self):
        sells = (
            make_order(OrderType.SELL, 5, online=False),
            make_order(OrderType.SELL, 25, online=True),
        )
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.LOWEST)
        # The suspiciously cheap offline listing should not win.
        self.assertEqual(quote.lowest_sell, 25)

    def test_recommended_trims_outliers_with_enough_samples(self):
        # One absurd outlier plus a cluster of "real" prices.
        prices = [1, 40, 41, 42, 43, 44, 45]
        sells = tuple(make_order(OrderType.SELL, p) for p in prices)
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.RECOMMENDED)
        # Recommended should sit near the real cluster, not chase the '1'.
        self.assertGreater(quote.recommended_price, 10)

    def test_recommended_with_few_samples_uses_lowest(self):
        sells = tuple(make_order(OrderType.SELL, p) for p in (10, 12))
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.RECOMMENDED)
        self.assertEqual(quote.recommended_price, 10)

    def test_mod_rank_filters_to_exact_rank_only(self):
        sells = (
            MarketOrder(OrderType.SELL, 5, 1, True, "ingame", mod_rank=0),
            MarketOrder(OrderType.SELL, 8, 1, True, "ingame", mod_rank=5),
            MarketOrder(OrderType.SELL, 40, 1, True, "ingame", mod_rank=10),
        )
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())

        quote_rank10 = self.analyzer.analyze(item_orders, strategy=PricingStrategy.LOWEST, mod_rank=10)
        self.assertEqual(quote_rank10.lowest_sell, 40)
        self.assertEqual(quote_rank10.sample_size, 1)

        quote_rank0 = self.analyzer.analyze(item_orders, strategy=PricingStrategy.LOWEST, mod_rank=0)
        self.assertEqual(quote_rank0.lowest_sell, 5)

    def test_mod_rank_zero_matches_unspecified_rank_orders(self):
        # Orders that don't specify a rank at all are treated as
        # equivalent to rank 0, matching how most non-explicit listings work.
        sells = (MarketOrder(OrderType.SELL, 5, 1, True, "ingame", mod_rank=None),)
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.LOWEST, mod_rank=0)
        self.assertEqual(quote.lowest_sell, 5)

    def test_mod_rank_with_no_matching_orders_returns_empty_quote(self):
        sells = (MarketOrder(OrderType.SELL, 5, 1, True, "ingame", mod_rank=3),)
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.LOWEST, mod_rank=10)
        self.assertIsNone(quote.recommended_price)
        self.assertEqual(quote.sample_size, 0)

    def test_no_mod_rank_specified_includes_all_orders_regardless_of_rank(self):
        sells = (
            MarketOrder(OrderType.SELL, 5, 1, True, "ingame", mod_rank=0),
            MarketOrder(OrderType.SELL, 40, 1, True, "ingame", mod_rank=10),
        )
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        quote = self.analyzer.analyze(item_orders, strategy=PricingStrategy.LOWEST)  # no mod_rank
        self.assertEqual(quote.sample_size, 2)


if __name__ == "__main__":
    unittest.main()
