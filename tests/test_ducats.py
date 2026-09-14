import unittest

from app.market.ducats import DucatAnalyzer, DucatVerdict


class TestDucatAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = DucatAnalyzer()

    def test_insufficient_data_without_price(self):
        result = self.analyzer.compare(None, 45, reference_plat_per_ducat=8.0)
        self.assertEqual(result.verdict, DucatVerdict.INSUFFICIENT_DATA)

    def test_insufficient_data_without_ducats(self):
        result = self.analyzer.compare(20.0, None, reference_plat_per_ducat=8.0)
        self.assertEqual(result.verdict, DucatVerdict.INSUFFICIENT_DATA)

    def test_sell_for_plat_when_ratio_high(self):
        # 20 plat / 45 ducats ~ 0.44 plat/ducat -> way below reference, expect KEEP
        result = self.analyzer.compare(20.0, 45, reference_plat_per_ducat=0.1)
        self.assertEqual(result.verdict, DucatVerdict.SELL_FOR_PLAT)

    def test_keep_for_ducats_when_ratio_low(self):
        result = self.analyzer.compare(5.0, 45, reference_plat_per_ducat=1.0)
        self.assertEqual(result.verdict, DucatVerdict.KEEP_FOR_DUCATS)


if __name__ == "__main__":
    unittest.main()
