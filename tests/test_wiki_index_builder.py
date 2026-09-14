import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from app.catalog.wiki_index import WikiIndex
from app.catalog.wiki_index_builder import WikiIndexBuilder
from app.integrations.wiki_client import WikiLookupResult


class TestWikiIndexBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.index = WikiIndex(Path(self.tmp_dir.name) / "wiki_index.json")
        self.client = MagicMock()
        self.builder = WikiIndexBuilder(self.index, self.client)

    def test_resolves_new_names(self):
        self.client.resolve.return_value = WikiLookupResult(
            url="https://wiki.warframe.com/w/Mesa_Prime", resolved_title="Mesa Prime", exact_match=True
        )
        result = self.builder.build_for_names(["Mesa Prime"])
        self.assertEqual(result.newly_resolved, 1)
        self.assertEqual(self.index.get("Mesa Prime"), "https://wiki.warframe.com/w/Mesa_Prime")

    def test_marks_unresolvable_names_without_crashing(self):
        self.client.resolve.return_value = WikiLookupResult(
            url=None, resolved_title=None, exact_match=False
        )
        result = self.builder.build_for_names(["Totally Made Up Item"])
        self.assertEqual(result.newly_unresolved, 1)
        self.assertTrue(self.index.has_been_attempted("Totally Made Up Item"))

    def test_already_known_names_are_skipped_without_a_network_call(self):
        self.index.set_resolved("Mesa Prime", "https://wiki.warframe.com/w/Mesa_Prime")
        result = self.builder.build_for_names(["Mesa Prime"])
        self.assertEqual(result.skipped_already_known, 1)
        self.client.resolve.assert_not_called()

    def test_force_rechecks_already_known_names(self):
        self.index.set_unresolved("Mesa Prime")
        self.client.resolve.return_value = WikiLookupResult(
            url="https://wiki.warframe.com/w/Mesa_Prime", resolved_title="Mesa Prime", exact_match=True
        )
        result = self.builder.build_for_names(["Mesa Prime"], force=True)
        self.assertEqual(result.newly_resolved, 1)
        self.client.resolve.assert_called_once()

    def test_deduplicates_names(self):
        self.client.resolve.return_value = WikiLookupResult(
            url="https://wiki.warframe.com/w/Mesa_Prime", resolved_title="Mesa Prime", exact_match=True
        )
        result = self.builder.build_for_names(["Mesa Prime", "Mesa Prime", "Mesa Prime"])
        self.assertEqual(self.client.resolve.call_count, 1)
        self.assertEqual(result.attempted, 1)

    def test_empty_and_none_names_are_ignored(self):
        result = self.builder.build_for_names(["", None, "  "])
        self.assertEqual(result.attempted, 0)
        self.client.resolve.assert_not_called()

    def test_progress_callback_invoked_per_name(self):
        self.client.resolve.return_value = WikiLookupResult(
            url="u", resolved_title="t", exact_match=True
        )
        calls = []
        self.builder.build_for_names(
            ["A", "B"], progress_callback=lambda i, n: calls.append((i, n))
        )
        self.assertEqual(calls, [(1, 2), (2, 2)])

    def test_saves_index_after_building(self):
        self.client.resolve.return_value = WikiLookupResult(
            url="https://wiki.warframe.com/w/Mesa_Prime", resolved_title="Mesa Prime", exact_match=True
        )
        self.builder.build_for_names(["Mesa Prime"])

        reloaded = WikiIndex(Path(self.tmp_dir.name) / "wiki_index.json")
        reloaded.load_from_disk()
        self.assertEqual(reloaded.get("Mesa Prime"), "https://wiki.warframe.com/w/Mesa_Prime")

    def test_results_correct_and_complete_under_concurrency(self):
        # Uses real ThreadPoolExecutor (not mocked out) to prove the
        # concurrent fetch phase produces correct, complete results for
        # every name, not just some of them.
        def fake_resolve(name):
            n = int(name.split("_")[1])
            time.sleep(0.001 * (10 - n))  # vary completion order across threads
            return WikiLookupResult(url=f"https://wiki.example/{name}", resolved_title=name, exact_match=True)

        self.client.resolve.side_effect = fake_resolve
        names = [f"item_{i}" for i in range(10)]

        result = self.builder.build_for_names(names)

        self.assertEqual(result.newly_resolved, 10)
        for name in names:
            self.assertEqual(self.index.get(name), f"https://wiki.example/{name}")

    def test_one_failing_name_does_not_affect_others(self):
        def fake_resolve(name):
            if name == "Bad Item":
                raise RuntimeError("simulated Wiki failure")
            return WikiLookupResult(url=f"https://wiki.example/{name}", resolved_title=name, exact_match=True)

        self.client.resolve.side_effect = fake_resolve

        result = self.builder.build_for_names(["Good Item", "Bad Item"])

        self.assertEqual(self.index.get("Good Item"), "https://wiki.example/Good Item")
        self.assertIsNone(self.index.get("Bad Item"))
        self.assertTrue(self.index.has_been_attempted("Bad Item"))
        self.assertEqual(result.newly_resolved, 1)
        self.assertEqual(result.newly_unresolved, 1)

    def test_custom_max_workers_respected(self):
        builder = WikiIndexBuilder(self.index, self.client, max_workers=1)
        self.assertEqual(builder._max_workers, 1)

    def test_max_workers_floor_is_one(self):
        builder = WikiIndexBuilder(self.index, self.client, max_workers=0)
        self.assertEqual(builder._max_workers, 1)

    def test_total_known_reflects_cumulative_resolved_count(self):
        self.index.set_resolved("Already Known", "https://wiki.example/Already_Known")
        self.client.resolve.return_value = WikiLookupResult(
            url="https://wiki.example/New_Item", resolved_title="New Item", exact_match=True
        )
        result = self.builder.build_for_names(["New Item"])
        self.assertEqual(result.total_known, 2)  # the pre-existing one plus the new one


if __name__ == "__main__":
    unittest.main()
