import unittest

from app.ord_isms import messages as ordis


class TestMessagePoolsAreSubstantial(unittest.TestCase):
    """Guards against the pools silently shrinking back down over time."""

    def test_major_pools_have_multiple_entries(self):
        pools_needing_variety = [
            ordis.STARTUP,
            ordis.IMPORT_START,
            ordis.IMPORT_SUCCESS,
            ordis.MARKET_QUERY,
            ordis.MARKET_RATE_LIMITED,
            ordis.ANALYSIS_START,
            ordis.ANALYSIS_DONE,
            ordis.SELL_SCORE_GOOD,
            ordis.SELL_SCORE_KEEP,
            ordis.EXPORT_DONE,
            ordis.CATALOG_UPDATE_DONE,
        ]
        for pool in pools_needing_variety:
            self.assertGreaterEqual(len(pool), 3, f"Pool too small: {pool}")

    def test_no_empty_or_duplicate_strings_within_a_pool(self):
        all_pools = [
            v
            for name, v in vars(ordis).items()
            if name.isupper() and isinstance(v, list)
        ]
        for pool in all_pools:
            self.assertTrue(all(isinstance(s, str) and s.strip() for s in pool))
            self.assertEqual(len(pool), len(set(pool)), f"Duplicate entry in {pool}")


class TestSayHelpers(unittest.TestCase):
    def test_say_returns_item_from_pool(self):
        pool = ordis.STARTUP
        for _ in range(20):
            self.assertIn(ordis.say(pool), pool)

    def test_market_is_being_difficult_returns_string(self):
        self.assertIsInstance(ordis.market_is_being_difficult(), str)

    def test_ask_the_market_nicely_uses_market_query_pool(self):
        for _ in range(20):
            self.assertIn(ordis.ask_the_market_nicely(), ordis.MARKET_QUERY)

    def test_calm_the_market_frenzy_uses_rate_limited_pool(self):
        for _ in range(20):
            self.assertIn(ordis.calm_the_market_frenzy(), ordis.MARKET_RATE_LIMITED)


class TestSayAnalysisSummary(unittest.TestCase):
    def test_high_value_uses_high_value_pool(self):
        result = ordis.say_analysis_summary(
            estimated_total_value=1000, catalog_matched_count=900, total_items=1000
        )
        self.assertIn(result, ordis.ANALYSIS_DONE_HIGH_VALUE)

    def test_low_value_uses_low_value_pool(self):
        result = ordis.say_analysis_summary(
            estimated_total_value=10, catalog_matched_count=900, total_items=1000
        )
        self.assertIn(result, ordis.ANALYSIS_DONE_LOW_VALUE)

    def test_low_match_ratio_takes_priority_over_value(self):
        # Even a huge total value shouldn't hide a bad match ratio --
        # the Operator needs to know UPDATE ITEMS might help.
        result = ordis.say_analysis_summary(
            estimated_total_value=5000, catalog_matched_count=10, total_items=1000
        )
        self.assertIn(result, ordis.ANALYSIS_LOW_MATCH_RATIO)

    def test_mid_range_uses_default_pool(self):
        result = ordis.say_analysis_summary(
            estimated_total_value=200, catalog_matched_count=900, total_items=1000
        )
        self.assertIn(result, ordis.ANALYSIS_DONE)

    def test_zero_items_does_not_crash(self):
        result = ordis.say_analysis_summary(
            estimated_total_value=0, catalog_matched_count=0, total_items=0
        )
        self.assertIsInstance(result, str)


class TestSayLiquidity(unittest.TestCase):
    def test_high_liquidity_string_value(self):
        self.assertIn(ordis.say_liquidity("HIGH"), ordis.LIQUIDITY_HIGH)

    def test_very_high_maps_to_high_pool(self):
        self.assertIn(ordis.say_liquidity("VERY HIGH"), ordis.LIQUIDITY_HIGH)

    def test_medium(self):
        self.assertIn(ordis.say_liquidity("MEDIUM"), ordis.LIQUIDITY_MEDIUM)

    def test_low_and_very_low_map_to_low_pool(self):
        self.assertIn(ordis.say_liquidity("LOW"), ordis.LIQUIDITY_LOW)
        self.assertIn(ordis.say_liquidity("VERY LOW"), ordis.LIQUIDITY_LOW)

    def test_unknown_or_unmapped_falls_back(self):
        self.assertIn(ordis.say_liquidity("N/A"), ordis.LIQUIDITY_UNKNOWN)
        self.assertIn(ordis.say_liquidity("something_weird"), ordis.LIQUIDITY_UNKNOWN)

    def test_accepts_enum_like_object_with_value_attr(self):
        class FakeLevel:
            value = "HIGH"

        self.assertIn(ordis.say_liquidity(FakeLevel()), ordis.LIQUIDITY_HIGH)


class TestSayRecommendation(unittest.TestCase):
    def test_sell(self):
        self.assertIn(ordis.say_recommendation("SELL"), ordis.SELL_SCORE_GOOD)

    def test_consider(self):
        self.assertIn(ordis.say_recommendation("CONSIDER"), ordis.SELL_SCORE_CONSIDER)

    def test_keep(self):
        self.assertIn(ordis.say_recommendation("KEEP"), ordis.SELL_SCORE_KEEP)

    def test_unknown_falls_back_to_keep_pool(self):
        self.assertIn(ordis.say_recommendation("UNKNOWN"), ordis.SELL_SCORE_KEEP)


if __name__ == "__main__":
    unittest.main()
