import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.catalog.catalog import ItemCatalog


class TestItemCatalog(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.catalog = ItemCatalog(Path(self.tmp_dir.name) / "catalog.json")

    def test_load_from_market_payload(self):
        raw = [
            {
                "id": "1",
                "slug": "mesa_prime_systems",
                "i18n": {"en": {"name": "Mesa Prime Systems"}},
                "tags": ["prime", "warframe_part"],
                "ducats": 45,
                "tradable": True,
            }
        ]
        count = self.catalog.load_from_market_payload(raw)
        self.assertEqual(count, 1)
        entry = self.catalog.get("mesa_prime_systems")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "Mesa Prime Systems")
        self.assertTrue(entry.is_prime)
        self.assertEqual(entry.ducats, 45)

    def test_find_by_name_case_insensitive(self):
        raw = [
            {
                "id": "1",
                "slug": "mesa_prime_systems",
                "i18n": {"en": {"name": "Mesa Prime Systems"}},
                "tags": ["prime"],
            }
        ]
        self.catalog.load_from_market_payload(raw)
        entry = self.catalog.find_by_name("mesa prime systems")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.slug, "mesa_prime_systems")

    def test_save_and_load_round_trip(self):
        raw = [
            {
                "id": "1",
                "slug": "argon_crystal",
                "i18n": {"en": {"name": "Argon Crystal"}},
                "tags": ["resource"],
                "tradable": False,
            }
        ]
        self.catalog.load_from_market_payload(raw)
        self.catalog.save()

        reloaded = ItemCatalog(Path(self.tmp_dir.name) / "catalog.json")
        loaded = reloaded.load_from_disk()
        self.assertTrue(loaded)
        entry = reloaded.get("argon_crystal")
        self.assertIsNotNone(entry)
        self.assertFalse(entry.tradable)

    def test_load_from_market_payload_extracts_game_ref(self):
        raw = [
            {
                "id": "1",
                "slug": "mesa_prime_neuroptics_blueprint",
                "i18n": {"en": {"name": "Mesa Prime Neuroptics Blueprint"}},
                "tags": ["prime"],
                "gameRef": "/Lotus/Powersuits/Mesa/MesaPrimeNeuroptics",
            }
        ]
        self.catalog.load_from_market_payload(raw)
        entry = self.catalog.find_by_game_ref("/Lotus/Powersuits/Mesa/MesaPrimeNeuroptics")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.slug, "mesa_prime_neuroptics_blueprint")

    def test_find_by_game_ref_missing_returns_none(self):
        self.assertIsNone(self.catalog.find_by_game_ref("/Lotus/Nonexistent/Path"))

    def test_game_ref_survives_save_and_reload(self):
        raw = [
            {
                "id": "1",
                "slug": "argon_crystal",
                "i18n": {"en": {"name": "Argon Crystal"}},
                "tags": ["resource"],
                "gameRef": "/Lotus/Types/Items/MiscItems/ArgonCrystal",
            }
        ]
        self.catalog.load_from_market_payload(raw)
        self.catalog.save()

        reloaded = ItemCatalog(Path(self.tmp_dir.name) / "catalog.json")
        reloaded.load_from_disk()
        entry = reloaded.find_by_game_ref("/Lotus/Types/Items/MiscItems/ArgonCrystal")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.slug, "argon_crystal")

    def test_skips_entries_without_slug(self):
        raw = [{"id": "1", "i18n": {"en": {"name": "No Slug Item"}}}]
        count = self.catalog.load_from_market_payload(raw)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
