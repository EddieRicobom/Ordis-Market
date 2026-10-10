import unittest

from app.relics.analyzer import SetState, analyze_relics
from app.relics.models import PrimePart, PrimeSet, Relic, RelicData, RelicReward
from tests.relics_fixture import inv, real_data, status_for

CEDO_ALL = ("cedoprimebarrel", "cedoprimeblueprint", "cedoprimereceiver", "cedoprimestock")
# Real relic keys from the fixture:
LITH_C14_INTACT = "t1voidprojectionvorunaprimeabronze"  # drops Cedo Prime Blueprint (Rare 2%), vaulted
LITH_C14_RADIANT = "t1voidprojectionvorunaprimeaplatinum"  # same, 10%
AXI_T13_INTACT = "t4voidprojectiongyreprimebbronze"  # drops Gyre Prime Chassis Blueprint (Uncommon 11%)


class TestOwnership(unittest.TestCase):
    def setUp(self):
        self.data = real_data()

    def analyze(self, *items):
        return analyze_relics(items, self.data)

    def test_empty_inventory_means_nothing_everywhere(self):
        report = self.analyze()
        self.assertTrue(all(s.state is SetState.NONE for s in report.sets))
        self.assertEqual(report.owned_relic_total, 0)

    def test_set_is_complete_when_every_part_is_owned(self):
        status = status_for(self.analyze(*(inv(k) for k in CEDO_ALL)), "Cedo Prime")
        self.assertIs(status.state, SetState.COMPLETE)
        self.assertEqual((status.owned_units, status.need_units), (4, 4))
        self.assertEqual(status.suggestions, ())

    def test_parts_are_matched_by_display_name_style_ids_too(self):
        items = [inv(k) for k in ("cedo_prime_barrel", "cedo_prime_blueprint", "cedo_prime_receiver", "cedo_prime_stock")]
        self.assertIs(status_for(self.analyze(*items), "Cedo Prime").state, SetState.COMPLETE)

    def test_a_built_warframe_component_counts_as_the_blueprint(self):
        items = [inv("gyreprimeblueprint"), inv("gyreprimechassiscomponent"), inv("gyreprimehelmetblueprint"), inv("gyreprimesystemscomponent")]
        status = status_for(self.analyze(*items), "Gyre Prime")
        self.assertIs(status.state, SetState.COMPLETE)

    def test_parts_needing_two_copies(self):
        base = [inv("akboltoprimeblueprint"), inv("akboltoprimelink"), inv("akboltoprimereceiver", 2)]
        one_barrel = status_for(self.analyze(*base, inv("akboltoprimebarrel", 1)), "Akbolto Prime")
        self.assertIs(one_barrel.state, SetState.PARTIAL if not one_barrel.missing_parts[0].droppers else SetState.COMPLETABLE)
        self.assertEqual([(p.part.key, p.missing) for p in one_barrel.missing_parts], [("akboltoprimebarrel", 1)])
        self.assertEqual((one_barrel.owned_units, one_barrel.need_units), (5, 6))
        two_barrels = status_for(self.analyze(*base, inv("akboltoprimebarrel", 2)), "Akbolto Prime")
        self.assertIs(two_barrels.state, SetState.COMPLETE)

    def test_extra_copies_do_not_inflate_progress(self):
        status = status_for(self.analyze(inv("cedoprimebarrel", 5)), "Cedo Prime")
        self.assertEqual(status.owned_units, 1)


class TestRelics(unittest.TestCase):
    def setUp(self):
        self.data = real_data()

    def analyze(self, *items):
        return analyze_relics(items, self.data)

    def cedo_with(self, *relics):
        return self.analyze(inv("cedoprimebarrel"), inv("cedoprimereceiver"), inv("cedoprimestock"), *relics)

    def test_completable_when_an_owned_relic_drops_the_only_missing_part(self):
        status = status_for(self.cedo_with(inv(LITH_C14_INTACT, 5)), "Cedo Prime")
        self.assertIs(status.state, SetState.COMPLETABLE)
        dropper = status.missing_parts[0].droppers[0]
        self.assertEqual((dropper.relic.short_name, dropper.rarity, dropper.chance, dropper.quantity), ("Lith C14", "Rare", 2.0, 5))
        self.assertAlmostEqual(dropper.all_chance, round((1 - 0.98**5) * 100, 2))

    def test_best_owned_refinement_is_used_and_odds_combine_all_copies(self):
        status = status_for(self.cedo_with(inv(LITH_C14_INTACT, 1), inv(LITH_C14_RADIANT, 1)), "Cedo Prime")
        dropper = status.missing_parts[0].droppers[0]
        self.assertEqual((dropper.relic.refinement, dropper.chance, dropper.quantity), ("Radiant", 10.0, 2))
        self.assertAlmostEqual(dropper.all_chance, round((1 - 0.98 * 0.90) * 100, 2))

    def test_relic_ids_in_game_name_form_are_recognised(self):
        status = status_for(self.cedo_with(inv("lith_c14_intact", 2)), "Cedo Prime")
        self.assertIs(status.state, SetState.COMPLETABLE)

    def test_partial_when_only_some_missing_parts_have_a_relic(self):
        status = status_for(self.analyze(inv("gyreprimeblueprint"), inv(AXI_T13_INTACT, 3)), "Gyre Prime")
        self.assertIs(status.state, SetState.PARTIAL)
        covered = {p.part.key for p in status.missing_parts if p.droppers}
        self.assertEqual(covered, {"gyreprimechassisblueprint"})

    def test_missing_part_without_any_relic_blocks_completable(self):
        status = status_for(self.analyze(*(inv(k) for k in CEDO_ALL[:2])), "Cedo Prime")
        self.assertIsNot(status.state, SetState.COMPLETABLE)

    def test_requiem_relics_are_ignored_but_unknown_prime_relics_are_reported(self):
        report = self.analyze(inv("t5voidprojectionimmortalabronze", 2), inv("t1voidprojectionbrandnewprimeabronze", 1))
        self.assertEqual(report.unmatched_relic_ids, ("t1voidprojectionbrandnewprimeabronze",))
        self.assertEqual(report.owned_relic_total, 0)

    def test_owned_relic_counts(self):
        report = self.analyze(inv(LITH_C14_INTACT, 4), inv(LITH_C14_RADIANT, 1), inv(AXI_T13_INTACT, 2))
        self.assertEqual(report.owned_relic_total, 7)
        self.assertEqual(report.owned_relic_kinds, 2)  # Lith C14 (two refinements) + Axi T13


def _relic(key, name, *drops):
    era, code, refinement = name.split()
    return Relic(key, name, era, code, refinement, False, tuple(RelicReward(part, "Common", chance) for part, chance in drops))


class TestSuggestions(unittest.TestCase):
    def setUp(self):
        parts = tuple(PrimePart(k, k.upper()) for k in ("a", "b", "c", "d"))
        self.data = RelicData(
            relics=(
                _relic("r1", "Lith A1 Intact", ("a", 10.0), ("b", 10.0)),  # covers two parts
                _relic("r2", "Lith A2 Intact", ("b", 25.0)),  # better odds for b, but covers less
                _relic("r3", "Meso B1 Intact", ("c", 5.0)),
            ),
            sets=(PrimeSet("Test Prime", parts),),
        )

    def test_greedy_cover_prefers_the_relic_covering_most_missing_parts(self):
        report = analyze_relics([inv("lith_a1_intact"), inv("lith_a2_intact"), inv("meso_b1_intact", 3)], self.data)
        status = report.sets[0]
        self.assertIs(status.state, SetState.PARTIAL)  # nothing owned drops 'd'
        picks = [(s.relic.short_name, tuple(p.key for p in s.covers)) for s in status.suggestions]
        self.assertEqual(picks, [("Lith A1", ("a", "b")), ("Meso B1", ("c",))])  # r2 is redundant
        self.assertEqual(status.suggestions[1].quantity, 3)

    def test_droppers_are_sorted_by_chance(self):
        status = analyze_relics([inv("lith_a1_intact"), inv("lith_a2_intact")], self.data).sets[0]
        part_b = next(p for p in status.parts if p.part.key == "b")
        self.assertEqual([d.relic.short_name for d in part_b.droppers], ["Lith A2", "Lith A1"])


if __name__ == "__main__":
    unittest.main()
