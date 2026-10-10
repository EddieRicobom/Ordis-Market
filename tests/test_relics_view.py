import unittest

from app.relics.analyzer import SetState, analyze_relics
from app.relics.view import (
    FilterMode,
    detail_text,
    filter_statuses,
    missing_text,
    open_text,
    parts_text,
    short_part_name,
    sort_statuses,
)
from tests.relics_fixture import inv, real_data, status_for

CEDO_ALL = ("cedoprimebarrel", "cedoprimereceiver", "cedoprimestock")


def _report(*items):
    return analyze_relics(list(items), real_data())


class TestFilters(unittest.TestCase):
    def test_modes_select_the_right_states(self):
        data = real_data()
        relic = next(r for r in data.relics if r.era == "Lith" and any("cedoprime" in w.part_key for w in r.rewards))
        report = _report(inv("cedoprimebarrel"), inv(relic.name.replace(" ", "_").lower(), 2),
                         *(inv(k) for k in ("gyreprimeblueprint",)))
        completable = filter_statuses(report.sets, FilterMode.COMPLETABLE)
        self.assertTrue(all(s.state is SetState.COMPLETABLE for s in completable))
        owned = filter_statuses(report.sets, FilterMode.OWNED)
        self.assertTrue(all(s.owned_units > 0 for s in owned))
        self.assertEqual(len(filter_statuses(report.sets, FilterMode.ALL)), len(report.sets))

    def test_complete_filter_and_search(self):
        report = _report(*(inv(k) for k in ("cedoprimebarrel", "cedoprimereceiver", "cedoprimestock", "cedoprimeblueprint")))
        done = filter_statuses(report.sets, FilterMode.COMPLETE)
        self.assertEqual([s.prime_set.name for s in done], ["Cedo Prime"])
        self.assertEqual(filter_statuses(report.sets, FilterMode.ALL, " GYRE ")[0].prime_set.name, "Gyre Prime")
        self.assertEqual(filter_statuses(report.sets, FilterMode.ALL, "zzz"), [])

    def test_sets_with_nothing_owned_never_show_as_completable(self):
        report = _report()
        self.assertEqual(filter_statuses(report.sets, FilterMode.COMPLETABLE), [])


class TestSortAndText(unittest.TestCase):
    def test_sort_puts_actionable_sets_first(self):
        report = _report(inv("cedoprimebarrel"), inv("gyreprimeblueprint"))
        ordered = sort_statuses(report.sets)
        ranks = [s.state for s in ordered]
        order = [SetState.COMPLETABLE, SetState.PARTIAL, SetState.COMPLETE, SetState.NONE]
        self.assertEqual(ranks, sorted(ranks, key=order.index))

    def test_texts(self):
        status = status_for(_report(inv("cedoprimebarrel")), "Cedo Prime")
        self.assertEqual(parts_text(status), f"1/{status.need_units}")
        self.assertNotIn("Cedo Prime ", missing_text(status))
        self.assertIn("no relic of yours drops", open_text(status))  # no relics owned at all
        detail = detail_text(status)
        self.assertTrue(detail.startswith("Cedo Prime --"))
        self.assertIn("[x] Barrel", detail)
        self.assertIn("none of your relics drop this", detail)

    def test_complete_set_texts(self):
        status = status_for(_report(*(inv(k) for k in (*CEDO_ALL, "cedoprimeblueprint"))), "Cedo Prime")
        self.assertEqual(missing_text(status), "-")
        self.assertIn("ready to build", open_text(status))

    def test_short_part_name(self):
        part = status_for(_report(), "Cedo Prime").parts[0].part
        self.assertFalse(short_part_name(part, "Cedo Prime").startswith("Cedo"))


if __name__ == "__main__":
    unittest.main()
