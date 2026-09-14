import time
import unittest

from app.market.liquidity import LiquidityAnalyzer, LiquidityLevel
from app.market.models import ItemOrders, MarketOrder, OrderType


def sell(p, online=True):
    return MarketOrder(order_type=OrderType.SELL, platinum=p, quantity=1, user_online=online)


def buy(p, online=True):
    return MarketOrder(order_type=OrderType.BUY, platinum=p, quantity=1, user_online=online)


class TestLiquidityAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = LiquidityAnalyzer()

    def test_no_data_is_unknown(self):
        item_orders = ItemOrders(slug="x", sell_orders=(), buy_orders=(), fetched_at=time.time())
        report = self.analyzer.analyze(item_orders)
        self.assertEqual(report.level, LiquidityLevel.UNKNOWN)

    def test_very_high_liquidity(self):
        sells = tuple(sell(10 + i) for i in range(16))
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        report = self.analyzer.analyze(item_orders)
        self.assertEqual(report.level, LiquidityLevel.VERY_HIGH)

    def test_very_low_liquidity_with_some_data(self):
        sells = (sell(10, online=False),)  # exists but offline, doesn't count
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        report = self.analyzer.analyze(item_orders)
        self.assertEqual(report.level, LiquidityLevel.VERY_LOW)

    def test_spread_calculation(self):
        sells = (sell(20),)
        buys = (buy(15),)
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=buys, fetched_at=time.time())
        report = self.analyzer.analyze(item_orders)
        self.assertEqual(report.spread, 5)

    def test_medium_liquidity_threshold(self):
        sells = tuple(sell(10 + i) for i in range(3))
        item_orders = ItemOrders(slug="x", sell_orders=sells, buy_orders=(), fetched_at=time.time())
        report = self.analyzer.analyze(item_orders)
        self.assertEqual(report.level, LiquidityLevel.MEDIUM)


if __name__ == "__main__":
    unittest.main()
