import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.catalog.wiki_index import WikiIndex


class TestWikiIndex(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.index = WikiIndex(Path(self.tmp_dir.name) / "wiki_index.json")

    def test_empty_index(self):
        self.assertIsNone(self.index.get("Mesa Prime"))
        self.assertFalse(self.index.has_been_attempted("Mesa Prime"))

    def test_set_resolved(self):
        self.index.set_resolved("Mesa Prime", "https://wiki.warframe.com/w/Mesa_Prime")
        self.assertEqual(self.index.get("Mesa Prime"), "https://wiki.warframe.com/w/Mesa_Prime")
        self.assertTrue(self.index.has_been_attempted("Mesa Prime"))

    def test_set_unresolved_marks_attempted_without_a_url(self):
        self.index.set_unresolved("Nonexistent Thing")
        self.assertIsNone(self.index.get("Nonexistent Thing"))
        self.assertTrue(self.index.has_been_attempted("Nonexistent Thing"))

    def test_resolving_after_unresolved_clears_unresolved_state(self):
        self.index.set_unresolved("Mesa Prime")
        self.index.set_resolved("Mesa Prime", "https://wiki.warframe.com/w/Mesa_Prime")
        self.assertEqual(self.index.get("Mesa Prime"), "https://wiki.warframe.com/w/Mesa_Prime")

    def test_save_and_reload_round_trip(self):
        self.index.set_resolved("Mesa Prime", "https://wiki.warframe.com/w/Mesa_Prime")
        self.index.set_unresolved("Nonexistent Thing")
        self.index.save()

        reloaded = WikiIndex(Path(self.tmp_dir.name) / "wiki_index.json")
        loaded = reloaded.load_from_disk()
        self.assertTrue(loaded)
        self.assertEqual(reloaded.get("Mesa Prime"), "https://wiki.warframe.com/w/Mesa_Prime")
        self.assertTrue(reloaded.has_been_attempted("Nonexistent Thing"))

    def test_load_from_disk_missing_file_returns_false(self):
        self.assertFalse(self.index.load_from_disk())

    def test_load_from_disk_corrupt_file_returns_false(self):
        path = Path(self.tmp_dir.name) / "wiki_index.json"
        path.write_text("not json{{", encoding="utf-8")
        self.assertFalse(self.index.load_from_disk())


if __name__ == "__main__":
    unittest.main()
