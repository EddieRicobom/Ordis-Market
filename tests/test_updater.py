import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from app.catalog.catalog import ItemCatalog
from app.catalog.name_index import NameIndex
from app.catalog.updater import ItemCatalogUpdater, NameIndexUpdater
from app.catalog.warframe_export import WarframeExportError
from app.market.client import MarketClientError


class TestItemCatalogUpdater(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.catalog = ItemCatalog(Path(self.tmp_dir.name) / "catalog.json")
        self.client = MagicMock()
        self.updater = ItemCatalogUpdater(
            self.catalog, self.client, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600
        )

    def test_first_run_fetches_from_network(self):
        self.client.get_items.return_value = [
            {"id": "1", "slug": "argon_crystal", "i18n": {"en": {"name": "Argon Crystal"}}}
        ]
        result = self.updater.ensure_fresh()
        self.assertTrue(result.updated)
        self.assertEqual(result.entry_count, 1)
        self.client.get_items.assert_called_once()

    def test_second_run_uses_cache_without_refetching(self):
        self.client.get_items.return_value = [
            {"id": "1", "slug": "argon_crystal", "i18n": {"en": {"name": "Argon Crystal"}}}
        ]
        self.updater.ensure_fresh()

        fresh_catalog = ItemCatalog(Path(self.tmp_dir.name) / "catalog.json")
        fresh_updater = ItemCatalogUpdater(
            fresh_catalog, self.client, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600
        )
        result = fresh_updater.ensure_fresh()
        self.assertFalse(result.updated)
        self.assertTrue(result.used_cache)
        self.client.get_items.assert_called_once()  # not called again

    def test_network_failure_falls_back_to_disk_cache(self):
        self.client.get_items.return_value = [
            {"id": "1", "slug": "argon_crystal", "i18n": {"en": {"name": "Argon Crystal"}}}
        ]
        self.updater.ensure_fresh()

        self.client.get_items.side_effect = MarketClientError("down")
        result = self.updater.ensure_fresh(force=True)
        self.assertTrue(result.used_cache)
        self.assertIsNotNone(result.error)

    def test_network_failure_with_no_cache_reports_error(self):
        self.client.get_items.side_effect = MarketClientError("down")
        result = self.updater.ensure_fresh()
        self.assertFalse(result.used_cache)
        self.assertEqual(result.entry_count, 0)
        self.assertIsNotNone(result.error)


class TestNameIndexUpdater(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.name_index = NameIndex(Path(self.tmp_dir.name) / "name_index.json")

    def test_first_run_fetches_via_fetch_fn(self):
        fetch_fn = MagicMock(return_value={"/Lotus/Foo/Bar": "Foo Bar"})
        updater = NameIndexUpdater(
            self.name_index, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600, fetch_fn=fetch_fn
        )
        result = updater.ensure_fresh()
        self.assertTrue(result.updated)
        self.assertEqual(result.entry_count, 1)
        fetch_fn.assert_called_once()

    def test_second_run_uses_cache(self):
        fetch_fn = MagicMock(return_value={"/Lotus/Foo/Bar": "Foo Bar"})
        updater = NameIndexUpdater(
            self.name_index, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600, fetch_fn=fetch_fn
        )
        updater.ensure_fresh()

        fresh_index = NameIndex(Path(self.tmp_dir.name) / "name_index.json")
        fresh_updater = NameIndexUpdater(
            fresh_index, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600, fetch_fn=fetch_fn
        )
        result = fresh_updater.ensure_fresh()
        self.assertTrue(result.used_cache)
        fetch_fn.assert_called_once()  # still only called once total

    def test_fetch_failure_falls_back_to_cache(self):
        fetch_fn = MagicMock(return_value={"/Lotus/Foo/Bar": "Foo Bar"})
        updater = NameIndexUpdater(
            self.name_index, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600, fetch_fn=fetch_fn
        )
        updater.ensure_fresh()

        fetch_fn.side_effect = WarframeExportError("DE's servers are down")
        result = updater.ensure_fresh(force=True)
        self.assertTrue(result.used_cache)
        self.assertIsNotNone(result.error)

    def test_fetch_failure_with_no_cache_reports_error(self):
        fetch_fn = MagicMock(side_effect=WarframeExportError("down"))
        updater = NameIndexUpdater(
            self.name_index, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600, fetch_fn=fetch_fn
        )
        result = updater.ensure_fresh()
        self.assertFalse(result.used_cache)
        self.assertEqual(result.entry_count, 0)
        self.assertIsNotNone(result.error)

    def test_force_bypasses_fresh_cache(self):
        fetch_fn = MagicMock(return_value={"/Lotus/Foo/Bar": "Foo Bar"})
        updater = NameIndexUpdater(
            self.name_index, Path(self.tmp_dir.name) / "meta.txt", ttl_seconds=3600, fetch_fn=fetch_fn
        )
        updater.ensure_fresh()
        updater.ensure_fresh(force=True)
        self.assertEqual(fetch_fn.call_count, 2)


if __name__ == "__main__":
    unittest.main()
