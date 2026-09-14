import unittest

from app.ui.filters import LIQUIDITY_SORT_RANK, RECOMMENDATION_SORT_RANK, is_prime_set_name


class TestIsPrimeSetName(unittest.TestCase):
    def test_matches_simple_prime_set(self):
        self.assertTrue(is_prime_set_name("Mesa Prime Set"))
        self.assertTrue(is_prime_set_name("Ash Prime Set"))

    def test_case_insensitive(self):
        self.assertTrue(is_prime_set_name("mesa prime set"))
        self.assertTrue(is_prime_set_name("MESA PRIME SET"))

    def test_tolerates_trailing_whitespace(self):
        self.assertTrue(is_prime_set_name("Mesa Prime Set   "))
        self.assertTrue(is_prime_set_name("  Mesa Prime Set"))

    def test_does_not_match_individual_parts(self):
        self.assertFalse(is_prime_set_name("Mesa Prime Neuroptics Blueprint"))
        self.assertFalse(is_prime_set_name("Mesa Prime Systems"))
        self.assertFalse(is_prime_set_name("Braton Prime Barrel"))

    def test_does_not_match_mid_string_occurrence(self):
        # "Prime Set" must be at the end, not just present somewhere.
        self.assertFalse(is_prime_set_name("Prime Set Bonus Item Thing"))

    def test_does_not_match_non_prime_items(self):
        self.assertFalse(is_prime_set_name("Braton"))
        self.assertFalse(is_prime_set_name("Serration"))

    def test_rank_suffix_from_mod_display_names_still_no_match(self):
        # Sanity check against the "(Rank N)" suffix used elsewhere for mods
        # -- should never accidentally be treated as a prime set.
        self.assertFalse(is_prime_set_name("Serration (Rank 10)"))

    def test_empty_string(self):
        self.assertFalse(is_prime_set_name(""))


class TestSortRankTables(unittest.TestCase):
    def test_liquidity_ranks_are_strictly_ordered(self):
        ordered = ["N/A", "VERY LOW", "LOW", "MEDIUM", "HIGH", "VERY HIGH"]
        ranks = [LIQUIDITY_SORT_RANK[label] for label in ordered]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(ranks))  # all distinct

    def test_recommendation_ranks_are_strictly_ordered(self):
        ordered = ["UNKNOWN", "KEEP", "CONSIDER", "SELL"]
        ranks = [RECOMMENDATION_SORT_RANK[label] for label in ordered]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(ranks))


if __name__ == "__main__":
    unittest.main()
