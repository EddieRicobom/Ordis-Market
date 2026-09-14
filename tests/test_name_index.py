import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.catalog.name_index import NameIndex


class TestNameIndex(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.index = NameIndex(Path(self.tmp_dir.name) / "name_index.json")

    def test_empty_index_returns_none(self):
        self.assertIsNone(self.index.get("/Lotus/Foo/Bar"))
        self.assertEqual(len(self.index), 0)

    def test_load_from_pairs(self):
        count = self.index.load_from_pairs({"/Lotus/Foo/Bar": "Foo Bar"})
        self.assertEqual(count, 1)
        self.assertEqual(self.index.get("/Lotus/Foo/Bar"), "Foo Bar")

    def test_save_and_reload_round_trip(self):
        self.index.load_from_pairs({"/Lotus/Foo/Bar": "Foo Bar"})
        self.index.save()

        reloaded = NameIndex(Path(self.tmp_dir.name) / "name_index.json")
        loaded = reloaded.load_from_disk()
        self.assertTrue(loaded)
        self.assertEqual(reloaded.get("/Lotus/Foo/Bar"), "Foo Bar")

    def test_load_from_disk_missing_file_returns_false(self):
        self.assertFalse(self.index.load_from_disk())

    def test_load_from_disk_corrupt_file_returns_false(self):
        path = Path(self.tmp_dir.name) / "name_index.json"
        path.write_text("not json{{{", encoding="utf-8")
        self.assertFalse(self.index.load_from_disk())

    def test_load_from_disk_non_dict_json_returns_false(self):
        path = Path(self.tmp_dir.name) / "name_index.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        self.assertFalse(self.index.load_from_disk())


if __name__ == "__main__":
    unittest.main()
