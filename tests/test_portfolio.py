import time
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.analysis.portfolio import PortfolioAnalyzer
from app.catalog.catalog import CatalogEntry, ItemCatalog
from app.config.settings import AppSettings, PricingStrategy
from app.inventory.models import InventoryItem, InventorySnapshot
from app.market.models import ItemOrders, MarketOrder, OrderType
from app.market.repository import OrdersResult


class TestPortfolioAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = ItemCatalog.__new__(ItemCatalog)  # bypass disk path requirement
        self.catalog._entries = {
            "mesa_prime_systems": CatalogEntry(
                slug="mesa_prime_systems",
                item_id="1",
                name="Mesa Prime Systems",
                category="warframe_part",
                tradable=True,
                is_prime=True,
                ducats=45,
            ),
            "untradable_thing": CatalogEntry(
                slug="untradable_thing",
                item_id="2",
                name="Untradable Thing",
                tradable=False,
            ),
        }
        self.catalog._name_index = {
            "mesa prime systems": "mesa_prime_systems",
            "untradable thing": "untradable_thing",
        }
        self.catalog._game_ref_index = {}

        self.repo = MagicMock()
        self.settings = AppSettings(pricing_strategy=PricingStrategy.RECOMMENDED)
        self.analyzer = PortfolioAnalyzer(self.catalog, self.repo, self.settings)

    def test_full_pipeline_for_known_tradable_item(self):
        orders = ItemOrders(
            slug="mesa_prime_systems",
            sell_orders=tuple(
                MarketOrder(OrderType.SELL, p, 1, True, "ingame") for p in (30, 32, 35)
            ),
            buy_orders=(MarketOrder(OrderType.BUY, 20, 1, True, "ingame"),),
            fetched_at=time.time(),
        )
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=orders, from_cache=False, stale=False
        )

        snapshot = InventorySnapshot(
            items=(InventoryItem("mesa_prime_systems", 2, "Mesa Prime Systems"),),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)

        self.assertEqual(len(report.analyses), 1)
        analysis = report.analyses[0]
        self.assertTrue(analysis.data_available)
        self.assertIsNotNone(analysis.unit_price)
        self.assertEqual(analysis.total_value, analysis.unit_price * 2)
        self.assertEqual(report.total_tradable_items, 1)

    def test_untradable_item_skips_market_lookup(self):
        snapshot = InventorySnapshot(
            items=(InventoryItem("untradable_thing", 1, "Untradable Thing"),),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        analysis = report.analyses[0]
        self.assertFalse(analysis.tradable)
        self.repo.get_orders.assert_not_called()

    def test_unknown_item_not_in_catalog(self):
        snapshot = InventorySnapshot(
            items=(InventoryItem("mystery_item_xyz", 1, "Mystery Item XYZ"),),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        analysis = report.analyses[0]
        self.assertFalse(analysis.data_available)
        self.assertIn("catalog", analysis.error.lower())

    def test_market_error_surfaces_without_crashing(self):
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=None, from_cache=False, stale=False, error="down"
        )
        snapshot = InventorySnapshot(
            items=(InventoryItem("mesa_prime_systems", 1, "Mesa Prime Systems"),),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        analysis = report.analyses[0]
        self.assertFalse(analysis.data_available)
        self.assertEqual(analysis.error, "down")

    def test_game_ref_match_resolves_items_name_matching_would_miss(self):
        # Simulates a real inventory export: item_id/raw_name are mangled
        # ("mesaprimeneuroptics" / the raw internal path), but the exact
        # original ItemType path (game_ref) matches the catalog entry's
        # own gameRef -- this is the fix for real-world imports where the
        # in-game internal path bears no resemblance to warframe.market's
        # slug or display name.
        self.catalog._entries["mesa_prime_neuroptics_blueprint"] = CatalogEntry(
            slug="mesa_prime_neuroptics_blueprint",
            item_id="99",
            name="Mesa Prime Neuroptics Blueprint",
            category="warframe_part",
            tradable=True,
            is_prime=True,
            ducats=45,
            game_ref="/Lotus/Powersuits/Mesa/MesaPrimeNeuroptics",
        )
        self.catalog._game_ref_index["/Lotus/Powersuits/Mesa/MesaPrimeNeuroptics"] = (
            "mesa_prime_neuroptics_blueprint"
        )

        orders = ItemOrders(
            slug="mesa_prime_neuroptics_blueprint",
            sell_orders=(MarketOrder(OrderType.SELL, 20, 1, True, "ingame"),),
            buy_orders=(),
            fetched_at=time.time(),
        )
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=orders, from_cache=False, stale=False
        )

        snapshot = InventorySnapshot(
            items=(
                InventoryItem(
                    item_id="mesaprimeneuroptics",  # mangled, won't match slug or name
                    quantity=1,
                    raw_name="/Lotus/Powersuits/Mesa/MesaPrimeNeuroptics",
                    source_field="ItemType",
                    game_ref="/Lotus/Powersuits/Mesa/MesaPrimeNeuroptics",
                ),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)

        analysis = report.analyses[0]
        self.assertTrue(analysis.data_available)
        self.assertEqual(analysis.slug, "mesa_prime_neuroptics_blueprint")
        self.assertEqual(report.catalog_matched_count, 1)

    def test_catalog_matched_count_tracks_matches_not_just_tradable(self):
        # An untradable-but-recognized item should still count as "matched"
        # even though it's not tradable -- these are different signals.
        snapshot = InventorySnapshot(
            items=(
                InventoryItem("untradable_thing", 1, "Untradable Thing"),
                InventoryItem("mystery_item_xyz", 1, "Mystery Item XYZ"),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        self.assertEqual(report.catalog_matched_count, 1)  # only the known-but-untradable one
        self.assertEqual(report.total_tradable_items, 0)

    def test_name_index_fallback_resolves_blueprint_when_all_else_fails(self):
        # This is the real-world scenario reported: a Prime part blueprint
        # (e.g. 'Nidus Systems Blueprint') whose internal ItemType path
        # matches neither a slug, a raw name, nor (in this test) a gameRef
        # entry -- only the DE Public Export name-translation resolves it.
        from app.catalog.name_index import NameIndex

        name_index = NameIndex.__new__(NameIndex)
        name_index._entries = {
            "/Lotus/Types/Recipes/WarframeRecipes/NidusSystemsBlueprint": "Nidus Systems Blueprint"
        }
        self.analyzer._name_index = name_index

        self.catalog._entries["nidus_systems_blueprint"] = CatalogEntry(
            slug="nidus_systems_blueprint",
            item_id="42",
            name="Nidus Systems Blueprint",
            category="warframe_part",
            tradable=True,
            is_prime=False,
        )
        self.catalog._name_index["nidus systems blueprint"] = "nidus_systems_blueprint"

        orders = ItemOrders(
            slug="nidus_systems_blueprint",
            sell_orders=(MarketOrder(OrderType.SELL, 15, 1, True, "ingame"),),
            buy_orders=(),
            fetched_at=time.time(),
        )
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=orders, from_cache=False, stale=False
        )

        snapshot = InventorySnapshot(
            items=(
                InventoryItem(
                    item_id="nidussystemsblueprint",  # mangled, no direct match
                    quantity=1,
                    raw_name="/Lotus/Types/Recipes/WarframeRecipes/NidusSystemsBlueprint",
                    source_field="ItemType",
                    game_ref="/Lotus/Types/Recipes/WarframeRecipes/NidusSystemsBlueprint",
                ),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)

        analysis = report.analyses[0]
        self.assertTrue(analysis.data_available)
        self.assertEqual(analysis.slug, "nidus_systems_blueprint")
        self.assertEqual(analysis.display_name, "Nidus Systems Blueprint")

    def test_no_name_index_configured_skips_fallback_gracefully(self):
        # analyzer in setUp has no name_index wired -- must not crash.
        snapshot = InventorySnapshot(
            items=(
                InventoryItem(
                    item_id="unresolvable",
                    quantity=1,
                    raw_name="/Lotus/Some/Unknown/Path",
                    source_field="ItemType",
                    game_ref="/Lotus/Some/Unknown/Path",
                ),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        self.assertFalse(report.analyses[0].data_available)

    def test_ranked_mod_gets_rank_specific_price_and_display_name(self):
        self.catalog._entries["serration"] = CatalogEntry(
            slug="serration", item_id="1", name="Serration", category="mod", tradable=True
        )
        self.catalog._name_index["serration"] = "serration"

        # Mixed-rank order book: a naive unranked lookup would blend these.
        orders = ItemOrders(
            slug="serration",
            sell_orders=(
                MarketOrder(OrderType.SELL, 5, 1, True, "ingame", mod_rank=0),
                MarketOrder(OrderType.SELL, 90, 1, True, "ingame", mod_rank=10),
            ),
            buy_orders=(),
            fetched_at=time.time(),
        )
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=orders, from_cache=False, stale=False
        )

        snapshot = InventorySnapshot(
            items=(
                InventoryItem("serration@rank10", 1, "Serration", mod_rank=10),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        analysis = report.analyses[0]

        self.assertTrue(analysis.data_available)
        self.assertEqual(analysis.display_name, "Serration (Rank 10)")
        # Must reflect the rank-10 price (90), not the blended/rank-0 price (5).
        self.assertEqual(analysis.unit_price, 90)

    def test_wiki_url_is_passive_lookup_only_no_network(self):
        from app.catalog.wiki_index import WikiIndex

        self.catalog._entries["mesa_prime_systems"] = CatalogEntry(
            slug="mesa_prime_systems", item_id="1", name="Mesa Prime Systems", tradable=True
        )
        self.catalog._name_index["mesa prime systems"] = "mesa_prime_systems"

        wiki_index = WikiIndex.__new__(WikiIndex)
        wiki_index._entries = {"Mesa Prime Systems": "https://wiki.warframe.com/w/Mesa_Prime"}
        wiki_index._unresolved = set()
        self.analyzer._wiki_index = wiki_index

        self.repo.get_orders.return_value = OrdersResult(
            item_orders=ItemOrders(slug="mesa_prime_systems", sell_orders=(), buy_orders=(), fetched_at=time.time()),
            from_cache=False,
            stale=False,
        )

        snapshot = InventorySnapshot(
            items=(InventoryItem("mesa_prime_systems", 1, "Mesa Prime Systems"),),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        self.assertEqual(report.analyses[0].wiki_url, "https://wiki.warframe.com/w/Mesa_Prime")
        # Confirm no network-capable object was touched for the wiki lookup:
        # wiki_index here is a plain dict-backed stub with no client at all.

    def test_wiki_url_none_when_no_index_configured(self):
        # analyzer in setUp has no wiki_index wired -- must not crash.
        self.catalog._entries["untradable_thing"] = CatalogEntry(
            slug="untradable_thing", item_id="2", name="Untradable Thing", tradable=False
        )
        snapshot = InventorySnapshot(
            items=(InventoryItem("untradable_thing", 1, "Untradable Thing"),),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        self.assertIsNone(report.analyses[0].wiki_url)

    def test_duplicate_slug_fetched_only_once(self):
        # The real-world case: the same mod owned at several ranks all
        # resolve to the same warframe.market slug. Orders/liquidity for
        # that slug must be fetched/computed once per analyze() call, not
        # once per InventoryItem.
        self.catalog._entries["serration"] = CatalogEntry(
            slug="serration", item_id="1", name="Serration", category="mod", tradable=True
        )
        self.catalog._name_index["serration"] = "serration"

        orders = ItemOrders(
            slug="serration",
            sell_orders=(
                MarketOrder(OrderType.SELL, 5, 1, True, "ingame", mod_rank=0),
                MarketOrder(OrderType.SELL, 90, 1, True, "ingame", mod_rank=10),
            ),
            buy_orders=(),
            fetched_at=time.time(),
        )
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=orders, from_cache=False, stale=False
        )

        snapshot = InventorySnapshot(
            items=(
                InventoryItem("serration@rank0", 1, "Serration", mod_rank=0),
                InventoryItem("serration@rank10", 1, "Serration", mod_rank=10),
                InventoryItem("serration@rank10b", 1, "Serration", mod_rank=10),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)

        # Only one network/cache call for the shared slug, regardless of
        # how many InventoryItems reference it.
        self.repo.get_orders.assert_called_once_with("serration", force_refresh=False)
        # But each item still gets its own rank-correct price.
        prices = {a.item_id: a.unit_price for a in report.analyses}
        self.assertEqual(prices["serration@rank0"], 5)
        self.assertEqual(prices["serration@rank10"], 90)
        self.assertEqual(prices["serration@rank10b"], 90)

    def test_results_preserve_original_item_order_despite_concurrency(self):
        # Concurrent slug fetches complete in nondeterministic order; the
        # final report must still list analyses in the original snapshot
        # order, not fetch-completion order.
        for i in range(20):
            slug = f"item_{i}"
            self.catalog._entries[slug] = CatalogEntry(
                slug=slug, item_id=str(i), name=f"Item {i}", tradable=True
            )
            self.catalog._name_index[f"item {i}"] = slug

        def fake_get_orders(slug, force_refresh=False):
            # Simulate varied completion timing across threads.
            n = int(slug.split("_")[1])
            time.sleep(0.001 * (20 - n))
            return OrdersResult(
                item_orders=ItemOrders(
                    slug=slug,
                    sell_orders=(MarketOrder(OrderType.SELL, float(n + 1), 1, True, "ingame"),),
                    buy_orders=(),
                    fetched_at=time.time(),
                ),
                from_cache=False,
                stale=False,
            )

        self.repo.get_orders.side_effect = fake_get_orders

        snapshot = InventorySnapshot(
            items=tuple(InventoryItem(f"item_{i}", 1, f"Item {i}") for i in range(20)),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)

        self.assertEqual([a.item_id for a in report.analyses], [f"item_{i}" for i in range(20)])
        # Prices should match each item's own slug, not a shuffled one.
        for i, analysis in enumerate(report.analyses):
            self.assertEqual(analysis.unit_price, float(i + 1))

    def test_one_failing_slug_does_not_affect_others(self):
        self.catalog._entries["good_item"] = CatalogEntry(
            slug="good_item", item_id="1", name="Good Item", tradable=True
        )
        self.catalog._entries["bad_item"] = CatalogEntry(
            slug="bad_item", item_id="2", name="Bad Item", tradable=True
        )
        self.catalog._name_index["good item"] = "good_item"
        self.catalog._name_index["bad item"] = "bad_item"

        def fake_get_orders(slug, force_refresh=False):
            if slug == "bad_item":
                raise RuntimeError("simulated network failure")
            return OrdersResult(
                item_orders=ItemOrders(
                    slug=slug,
                    sell_orders=(MarketOrder(OrderType.SELL, 10, 1, True, "ingame"),),
                    buy_orders=(),
                    fetched_at=time.time(),
                ),
                from_cache=False,
                stale=False,
            )

        self.repo.get_orders.side_effect = fake_get_orders

        snapshot = InventorySnapshot(
            items=(
                InventoryItem("good_item", 1, "Good Item"),
                InventoryItem("bad_item", 1, "Bad Item"),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)

        by_id = {a.item_id: a for a in report.analyses}
        self.assertTrue(by_id["good_item"].data_available)
        self.assertEqual(by_id["good_item"].unit_price, 10)
        self.assertFalse(by_id["bad_item"].data_available)
        self.assertIn("simulated network failure", by_id["bad_item"].error)

    def test_progress_callback_reaches_total_exactly_once_each_item(self):
        self.catalog._entries["mesa_prime_systems"] = CatalogEntry(
            slug="mesa_prime_systems", item_id="1", name="Mesa Prime Systems", tradable=True
        )
        self.catalog._name_index["mesa prime systems"] = "mesa_prime_systems"
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=ItemOrders(slug="mesa_prime_systems", sell_orders=(), buy_orders=(), fetched_at=time.time()),
            from_cache=False,
            stale=False,
        )
        snapshot = InventorySnapshot(
            items=(
                InventoryItem("mesa_prime_systems", 1, "Mesa Prime Systems"),
                InventoryItem("untracked_item", 1, "Untracked Item"),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        progress_calls = []
        self.analyzer.analyze(snapshot, progress_callback=lambda i, n: progress_calls.append((i, n)))

        self.assertTrue(progress_calls)
        # Monotonically non-decreasing, and finishes exactly at the total.
        counts = [c for c, _ in progress_calls]
        self.assertEqual(counts, sorted(counts))
        self.assertEqual(progress_calls[-1], (2, 2))

    def test_custom_max_workers_respected(self):
        analyzer = PortfolioAnalyzer(self.catalog, self.repo, self.settings, max_workers=1)
        self.assertEqual(analyzer._max_workers, 1)

    def test_max_workers_floor_is_one(self):
        analyzer = PortfolioAnalyzer(self.catalog, self.repo, self.settings, max_workers=0)
        self.assertEqual(analyzer._max_workers, 1)


    def test_ranked_mod_base_name_has_no_rank_suffix(self):
        # Regression test for a real bug: display_name carries a rank
        # suffix ('Serration (Rank 10)'), but base_name must stay clean
        # so it can be shared across ranks for Wiki/name-index lookups --
        # using display_name there meant every rank looked like a
        # different item and could never match an already-cached link.
        self.catalog._entries["serration"] = CatalogEntry(
            slug="serration", item_id="1", name="Serration", category="mod", tradable=True
        )
        self.catalog._name_index["serration"] = "serration"
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=ItemOrders(
                slug="serration",
                sell_orders=(MarketOrder(OrderType.SELL, 90, 1, True, "ingame", mod_rank=10),),
                buy_orders=(),
                fetched_at=time.time(),
            ),
            from_cache=False,
            stale=False,
        )
        snapshot = InventorySnapshot(
            items=(InventoryItem("serration@rank10", 1, "Serration", mod_rank=10),),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        analysis = report.analyses[0]
        self.assertEqual(analysis.display_name, "Serration (Rank 10)")
        self.assertEqual(analysis.base_name, "Serration")

    def test_two_ranks_of_same_mod_share_one_base_name(self):
        self.catalog._entries["serration"] = CatalogEntry(
            slug="serration", item_id="1", name="Serration", category="mod", tradable=True
        )
        self.catalog._name_index["serration"] = "serration"
        self.repo.get_orders.return_value = OrdersResult(
            item_orders=ItemOrders(slug="serration", sell_orders=(), buy_orders=(), fetched_at=time.time()),
            from_cache=False,
            stale=False,
        )
        snapshot = InventorySnapshot(
            items=(
                InventoryItem("serration@rank0", 1, "Serration", mod_rank=0),
                InventoryItem("serration@rank10", 1, "Serration", mod_rank=10),
            ),
            imported_at=datetime.now(timezone.utc),
            source_path="test",
        )
        report = self.analyzer.analyze(snapshot)
        base_names = {a.base_name for a in report.analyses}
        self.assertEqual(base_names, {"Serration"})  # one shared name, not two different ones


if __name__ == "__main__":
    unittest.main()
