import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.inventory.parser import (
    InvalidInventoryFileError,
    InventoryFileNotFoundError,
    InventoryParser,
)


class TestInventoryParser(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = InventoryParser()
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def _write(self, name: str, content) -> Path:
        path = Path(self.tmp_dir.name) / name
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    def test_file_not_found_raises(self):
        with self.assertRaises(InventoryFileNotFoundError):
            self.parser.parse_file(Path(self.tmp_dir.name) / "nope.json")

    def test_invalid_json_raises(self):
        path = Path(self.tmp_dir.name) / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        with self.assertRaises(InvalidInventoryFileError):
            self.parser.parse_file(path)

    def test_empty_list_raises(self):
        path = self._write("empty.json", [])
        with self.assertRaises(InvalidInventoryFileError):
            self.parser.parse_file(path)

    def test_normalized_format(self):
        path = self._write(
            "normalized.json",
            {"items": [{"item_id": "mesa_prime_systems", "quantity": 2}]},
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 1)
        self.assertEqual(snapshot.items[0].item_id, "mesa_prime_systems")
        self.assertEqual(snapshot.items[0].quantity, 2)

    def test_generic_name_quantity_list(self):
        path = self._write(
            "generic.json",
            [
                {"name": "Mesa Prime Neuroptics", "quantity": 3},
                {"name": "Braton Prime Barrel", "count": 5},
            ],
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 2)
        ids = {i.item_id for i in snapshot.items}
        self.assertIn("mesa_prime_neuroptics", ids)
        self.assertIn("braton_prime_barrel", ids)

    def test_nested_category_format(self):
        path = self._write(
            "nested.json",
            {
                "MiscItems": [
                    {"ItemType": "/Lotus/Types/Items/MiscItems/OrokinCell", "ItemCount": 40}
                ],
                "Suits": [
                    {"ItemType": "/Lotus/Powersuits/Mesa/MesaPrime", "ItemCount": 1}
                ],
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 2)
        ids = {i.item_id: i.quantity for i in snapshot.items}
        self.assertEqual(ids["orokincell"], 40)
        self.assertEqual(ids["mesaprime"], 1)

    def test_duplicate_ids_are_merged(self):
        path = self._write(
            "dupes.json",
            {
                "items": [
                    {"item_id": "argon_crystal", "quantity": 5},
                    {"item_id": "argon_crystal", "quantity": 7},
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 1)
        self.assertEqual(snapshot.items[0].quantity, 12)

    def test_zero_or_negative_quantity_dropped(self):
        path = self._write(
            "zeros.json",
            {
                "items": [
                    {"item_id": "argon_crystal", "quantity": 0},
                    {"item_id": "orokin_cell", "quantity": -3},
                    {"item_id": "mesa_prime_systems", "quantity": 1},
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 1)
        self.assertEqual(snapshot.items[0].item_id, "mesa_prime_systems")

    def test_unresolvable_records_are_counted_not_fatal(self):
        path = self._write(
            "partial.json",
            {
                "items": [
                    {"quantity": 5},  # no name-ish field at all
                    {"item_id": "mesa_prime_systems", "quantity": 1},
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 1)
        self.assertEqual(snapshot.unresolved_count, 1)

    def test_unrecognized_shape_raises(self):
        path = self._write("weird.json", {"foo": "bar"})
        with self.assertRaises(InvalidInventoryFileError):
            self.parser.parse_file(path)


    def test_item_type_records_preserve_full_game_ref(self):
        path = self._write(
            "gameref.json",
            {
                "Suits": [
                    {
                        "ItemType": "/Lotus/Powersuits/Mesa/MesaPrime",
                        "ItemId": {"$oid": "abc"},
                    }
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 1)
        item = snapshot.items[0]
        # item_id stays the lossy short form (for display/debugging)...
        self.assertEqual(item.item_id, "mesaprime")
        # ...but game_ref preserves the full, untouched original path, which
        # is what actually gets matched against warframe.market's catalog.
        self.assertEqual(item.game_ref, "/Lotus/Powersuits/Mesa/MesaPrime")

    def test_non_item_type_records_have_no_game_ref(self):
        path = self._write(
            "noref.json",
            {"items": [{"name": "Mesa Prime Neuroptics", "quantity": 1}]},
        )
        snapshot = self.parser.parse_file(path)
        self.assertIsNone(snapshot.items[0].game_ref)

    def test_same_mod_different_ranks_kept_as_separate_entries(self):
        # This is the real-world case reported: the same mod owned at two
        # different fusion ranks must NOT be merged into one stack.
        path = self._write(
            "ranked_mods.json",
            {
                "Upgrades": [
                    {
                        "ItemType": "/Lotus/Upgrades/Mods/Warframe/AvatarShieldMaxMod",
                        "UpgradeFingerprint": '{"lvl":7}',
                        "ItemId": {"$oid": "a"},
                    },
                    {
                        "ItemType": "/Lotus/Upgrades/Mods/Warframe/AvatarShieldMaxMod",
                        "UpgradeFingerprint": '{"lvl":10}',
                        "ItemId": {"$oid": "b"},
                    },
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 2)
        ranks = sorted(i.mod_rank for i in snapshot.items)
        self.assertEqual(ranks, [7, 10])
        # Different item_id strings so they never accidentally re-merge.
        ids = {i.item_id for i in snapshot.items}
        self.assertEqual(len(ids), 2)

    def test_same_mod_same_rank_still_merges_and_counts_copies(self):
        path = self._write(
            "same_rank.json",
            {
                "Upgrades": [
                    {
                        "ItemType": "/Lotus/Upgrades/Mods/Rifle/WeaponDamageAmountMod",
                        "UpgradeFingerprint": '{"lvl":10}',
                        "ItemId": {"$oid": "a"},
                    },
                    {
                        "ItemType": "/Lotus/Upgrades/Mods/Rifle/WeaponDamageAmountMod",
                        "UpgradeFingerprint": '{"lvl":10}',
                        "ItemId": {"$oid": "b"},
                    },
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 1)
        self.assertEqual(snapshot.items[0].quantity, 2)
        self.assertEqual(snapshot.items[0].mod_rank, 10)

    def test_unranked_stack_has_no_mod_rank(self):
        path = self._write(
            "unranked.json",
            {
                "RawUpgrades": [
                    {
                        "ItemType": "/Lotus/Types/Sentinels/SentinelPrecepts/Revenge",
                        "ItemCount": 172,
                    }
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertIsNone(snapshot.items[0].mod_rank)
        self.assertEqual(snapshot.items[0].quantity, 172)

    def test_malformed_upgrade_fingerprint_does_not_crash(self):
        path = self._write(
            "bad_fingerprint.json",
            {
                "Upgrades": [
                    {
                        "ItemType": "/Lotus/Upgrades/Mods/Warframe/SomeMod",
                        "UpgradeFingerprint": "not valid json",
                        "ItemId": {"$oid": "a"},
                    }
                ]
            },
        )
        snapshot = self.parser.parse_file(path)
        self.assertEqual(snapshot.total_items, 1)
        self.assertIsNone(snapshot.items[0].mod_rank)


if __name__ == "__main__":
    unittest.main()
