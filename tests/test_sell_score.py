import unittest

from app.market.liquidity import LiquidityLevel, LiquidityReport
from app.market.pricing import PriceQuote
from app.market.sell_score import Recommendation, SellScoreAnalyzer
from app.config.settings import PricingStrategy


class TestSellScoreAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = SellScoreAnalyzer()

    def test_unknown_when_no_price(self):
        price = PriceQuote(None, None, None, None, 0, PricingStrategy.RECOMMENDED)
        liquidity = LiquidityReport(LiquidityLevel.UNKNOWN, 0, 0, None)
        result = self.analyzer.score(price, liquidity, quantity_owned=1)
        self.assertEqual(result.recommendation, Recommendation.UNKNOWN)
        self.assertEqual(result.score, 0)

    def test_high_value_high_liquidity_sells(self):
        price = PriceQuote(190, 195, 192, 190, 20, PricingStrategy.RECOMMENDED)
        liquidity = LiquidityReport(LiquidityLevel.VERY_HIGH, 20, 10, 2.0)
        result = self.analyzer.score(price, liquidity, quantity_owned=3)
        self.assertEqual(result.recommendation, Recommendation.SELL)
        self.assertGreaterEqual(result.score, 65)

    def test_low_value_low_liquidity_keeps(self):
        price = PriceQuote(2, 2, 2, 2, 1, PricingStrategy.RECOMMENDED)
        liquidity = LiquidityReport(LiquidityLevel.VERY_LOW, 1, 0, None)
        result = self.analyzer.score(price, liquidity, quantity_owned=1)
        self.assertEqual(result.recommendation, Recommendation.KEEP)

    def test_extra_copies_increase_score(self):
        price = PriceQuote(50, 52, 51, 50, 5, PricingStrategy.RECOMMENDED)
        liquidity = LiquidityReport(LiquidityLevel.MEDIUM, 4, 2, 1.0)
        result_one = self.analyzer.score(price, liquidity, quantity_owned=1)
        result_many = self.analyzer.score(price, liquidity, quantity_owned=5)
        self.assertGreater(result_many.score, result_one.score)

    def test_zero_threshold_does_not_raise_zero_division_error(self):
        # Regression test: a misconfigured (or maliciously/accidentally
        # zero) threshold must not crash scoring.
        analyzer = SellScoreAnalyzer(high_value_plat_threshold=0)
        price = PriceQuote(50, 52, 51, 50, 5, PricingStrategy.RECOMMENDED)
        liquidity = LiquidityReport(LiquidityLevel.MEDIUM, 4, 2, 1.0)
        result = analyzer.score(price, liquidity, quantity_owned=1)  # must not raise
        self.assertIsInstance(result.score, int)

    def test_negative_threshold_does_not_raise_zero_division_error(self):
        analyzer = SellScoreAnalyzer(high_value_plat_threshold=-10)
        price = PriceQuote(50, 52, 51, 50, 5, PricingStrategy.RECOMMENDED)
        liquidity = LiquidityReport(LiquidityLevel.MEDIUM, 4, 2, 1.0)
        result = analyzer.score(price, liquidity, quantity_owned=1)  # must not raise
        self.assertIsInstance(result.score, int)


if __name__ == "__main__":
    unittest.main()
