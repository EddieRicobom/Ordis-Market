import unittest

from app.market.sets import SetAnalyzer


class TestSetAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = SetAnalyzer()

    def test_missing_data_returns_none_comparison(self):
        result = self.analyzer.compare("mesa_prime_set", None, {})
        self.assertIsNone(result.better_as_set)

    def test_set_more_profitable(self):
        result = self.analyzer.compare(
            "mesa_prime_set",
            set_value=120,
            component_prices={"neuroptics": 30, "chassis": 25, "systems": 32},
        )
        self.assertEqual(result.component_value_total, 87)
        self.assertEqual(result.difference, 33)
        self.assertTrue(result.better_as_set)

    def test_components_more_profitable(self):
        result = self.analyzer.compare(
            "cheap_prime_set",
            set_value=40,
            component_prices={"a": 20, "b": 20, "c": 15},
        )
        self.assertFalse(result.better_as_set)


if __name__ == "__main__":
    unittest.main()
