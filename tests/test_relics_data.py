import tempfile
import unittest
from pathlib import Path

from app.relics.models import ERAS, norm
from app.relics.store import FORMAT_VERSION, RelicDataStore
from app.relics.wfcd_source import (
    RelicDataError,
    build_relic_data,
    fetch_relic_data,
    parse_relic_name,
    part_key,
)
from tests.relics_fixture import raw_fixture, real_data


class TestNaming(unittest.TestCase):
    def test_parse_relic_name(self):
        self.assertEqual(parse_relic_name("Lith G14 Intact"), ("Lith", "G14", "Intact"))
        self.assertEqual(parse_relic_name("Axi A1 Radiant"), ("Axi", "A1", "Radiant"))
        self.assertIsNone(parse_relic_name("Requiem I Intact"))
        self.assertIsNone(parse_relic_name("Lith G14"))

    def test_part_key_and_norm_agree_across_inventory_id_forms(self):
        self.assertEqual(part_key("/Lotus/Types/Recipes/Weapons/WeaponParts/AkboltoPrimeBarrel"), "akboltoprimebarrel")
        self.assertEqual(norm("akbolto_prime_barrel"), "akboltoprimebarrel")
        self.assertEqual(norm("Akbolto Prime Barrel"), "akboltoprimebarrel")


class TestBuilder(unittest.TestCase):
    def setUp(self):
        self.data = real_data()
        self.sets = {s.name: s for s in self.data.sets}

    def test_requiem_relics_are_ignored(self):
        self.assertFalse(any("Requiem" in r.name for r in self.data.relics))

    def test_forma_is_not_a_part(self):
        for prime_set in self.data.sets:
            for part in prime_set.parts:
                self.assertNotIn("forma", part.key)

    def test_relics_are_ordered_lith_first(self):
        eras = [r.era for r in self.data.relics]
        self.assertEqual(eras[0], ERAS[0])
        self.assertEqual(eras, sorted(eras, key=ERAS.index))

    def test_warframe_parts_accept_the_built_component(self):
        parts = {p.key: p for p in self.sets["Gyre Prime"].parts}
        self.assertEqual(parts["gyreprimechassisblueprint"].alt_keys, ("gyreprimechassiscomponent",))
        self.assertEqual(parts["gyreprimeblueprint"].alt_keys, ())  # the main blueprint has no built form

    def test_parts_needing_two_copies(self):
        parts = {p.key: p for p in self.sets["Akbolto Prime"].parts}
        self.assertEqual(parts["akboltoprimebarrel"].need, 2)
        self.assertEqual(parts["akboltoprimereceiver"].need, 2)
        self.assertEqual(parts["akboltoprimeblueprint"].need, 1)

    def test_a_set_without_recipe_data_defaults_to_one_of_each(self):
        self.assertTrue(all(p.need == 1 for p in self.sets["Mirage Prime"].parts))

    def test_vaulted_flag_and_rewards_are_kept(self):
        relic = self.data.find_relic("t1voidprojectioncitrineprimeabronze")
        self.assertEqual(relic.name, "Lith A13 Intact")
        self.assertTrue(relic.vaulted)
        chassis = next(r for r in relic.rewards if r.part_key == "gyreprimechassisblueprint")
        self.assertEqual((chassis.rarity, chassis.chance), ("Uncommon", 11.0))

    def test_find_relic_by_internal_key_or_game_name(self):
        by_key = self.data.find_relic("T4VoidProjectionGyrePrimeBBronze")
        by_name = self.data.find_relic("axi_t13_intact")
        self.assertIs(by_key, by_name)
        self.assertIsNone(self.data.find_relic("t5voidprojectionimmortalabronze"))

    def test_empty_input_gives_falsy_data(self):
        self.assertFalse(build_relic_data([], []))


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "relic_data.json"
        self.store = RelicDataStore(self.path)
        self.data = real_data()

    def test_round_trip_is_lossless(self):
        self.store.save(self.data)
        loaded = self.store.load()
        self.assertEqual(loaded.relics, self.data.relics)
        self.assertEqual(loaded.sets, self.data.sets)
        self.assertEqual(loaded.fetched_at, self.data.fetched_at)

    def test_missing_corrupt_or_old_format_means_no_cache_not_a_crash(self):
        self.assertIsNone(self.store.load())
        self.path.write_text("{not json", encoding="utf-8")
        self.assertIsNone(self.store.load())
        self.path.write_text('{"version": %d}' % (FORMAT_VERSION + 1), encoding="utf-8")
        self.assertIsNone(self.store.load())
        self.path.write_text('{"version": %d, "fetched_at": 1, "relics": [{"n": "oops"}], "sets": []}' % FORMAT_VERSION)
        self.assertIsNone(self.store.load())

    def test_staleness(self):
        self.assertTrue(self.store.is_stale(None))
        self.assertTrue(self.store.is_stale(self.data))  # fetched in 2023
        fresh = build_relic_data(raw_fixture()["relics"], [])
        self.assertFalse(self.store.is_stale(fresh))

    def test_refresh_saves_and_leaves_no_temp_file(self):
        result = self.store.refresh(fetcher=lambda: self.data)
        self.assertIs(result, self.data)
        self.assertTrue(self.path.exists())
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["relic_data.json"])

    def test_failed_refresh_keeps_the_previous_cache(self):
        self.store.save(self.data)

        def boom():
            raise RelicDataError("offline")

        with self.assertRaises(RelicDataError):
            self.store.refresh(fetcher=boom)
        self.assertEqual(self.store.load().sets, self.data.sets)


class _Response:
    def __init__(self, payload=None, error=None):
        self._payload, self._error = payload, error

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        return self._payload


class _Session:
    def __init__(self, files):
        self.files = files
        self.requested = []

    def get(self, url, timeout=None):
        name = url.rsplit("/", 1)[-1]
        self.requested.append(name)
        if name not in self.files:
            return _Response(error=RuntimeError("404"))
        return _Response(self.files[name])


class TestFetch(unittest.TestCase):
    def files(self):
        raw = raw_fixture()
        files = {"Relics.json": raw["relics"]}
        for name in ("Warframes", "Primary", "Secondary", "Melee"):
            files[name + ".json"] = raw["items"].get(name, [])
        return files

    def test_fetch_builds_data_from_all_files(self):
        session = _Session(self.files())
        with self.assertLogs("app.relics.wfcd_source", level="WARNING"):
            data = fetch_relic_data(session)
        self.assertTrue(data)
        self.assertIn("Relics.json", session.requested)
        self.assertEqual({p.key: p.need for p in next(s for s in data.sets if s.name == "Akbolto Prime").parts}["akboltoprimebarrel"], 2)

    def test_a_missing_optional_file_is_tolerated(self):
        session = _Session(self.files())  # Archwing/Arch-Gun/... are absent -> "404"
        with self.assertLogs("app.relics.wfcd_source", level="WARNING"):
            self.assertTrue(fetch_relic_data(session))

    def test_a_missing_required_file_fails_instead_of_caching_wrong_counts(self):
        files = self.files()
        del files["Secondary.json"]
        with self.assertRaises(RelicDataError):
            fetch_relic_data(_Session(files))

    def test_missing_relics_or_garbage_fails(self):
        files = self.files()
        del files["Relics.json"]
        with self.assertRaises(RelicDataError):
            fetch_relic_data(_Session(files))
        files = self.files()
        files["Relics.json"] = {"not": "a list"}
        with self.assertRaises(RelicDataError):
            fetch_relic_data(_Session(files))


if __name__ == "__main__":
    unittest.main()
