import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from app.cache.cache_store import PriceCache
from app.market.client import MarketUnavailableError
from app.market.models import ItemOrders, MarketOrder, OrderType
from app.market.repository import MarketRepository


def sample_orders(slug="mesa_prime_systems"):
    return ItemOrders(
        slug=slug,
        sell_orders=(MarketOrder(OrderType.SELL, 30.0, 1, True, "ingame"),),
        buy_orders=(),
        fetched_at=time.time(),
    )


class TestMarketRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.cache = PriceCache(Path(self.tmp_dir.name), ttl_seconds=300)

    def test_live_fetch_populates_cache(self):
        client = MagicMock()
        client.get_orders_for_item.return_value = sample_orders()
        repo = MarketRepository(client, self.cache)

        result = repo.get_orders("mesa_prime_systems")

        self.assertFalse(result.from_cache)
        self.assertEqual(result.item_orders.sell_orders[0].platinum, 30.0)
        client.get_orders_for_item.assert_called_once()

        # Second call should be served from cache, no second network call.
        result2 = repo.get_orders("mesa_prime_systems")
        self.assertTrue(result2.from_cache)
        client.get_orders_for_item.assert_called_once()

    def test_offline_mode_uses_stale_cache(self):
        client = MagicMock()
        client.get_orders_for_item.return_value = sample_orders()
        repo = MarketRepository(client, self.cache)
        repo.get_orders("mesa_prime_systems")  # populate cache

        repo.offline_mode = True
        result = repo.get_orders("mesa_prime_systems")
        self.assertTrue(result.from_cache)
        self.assertTrue(result.stale)

    def test_offline_mode_without_cache_returns_error(self):
        client = MagicMock()
        repo = MarketRepository(client, self.cache, offline_mode=True)
        result = repo.get_orders("never_cached_item")
        self.assertIsNone(result.item_orders)
        self.assertIsNotNone(result.error)

    def test_network_failure_falls_back_to_stale_cache(self):
        client = MagicMock()
        client.get_orders_for_item.return_value = sample_orders()
        repo = MarketRepository(client, self.cache)
        repo.get_orders("mesa_prime_systems")  # populate

        client.get_orders_for_item.side_effect = MarketUnavailableError("down")
        result = repo.get_orders("mesa_prime_systems", force_refresh=True)
        self.assertTrue(result.from_cache)
        self.assertTrue(result.stale)
        self.assertIsNotNone(result.error)

    def test_network_failure_without_cache_returns_error(self):
        client = MagicMock()
        client.get_orders_for_item.side_effect = MarketUnavailableError("down")
        repo = MarketRepository(client, self.cache)
        result = repo.get_orders("brand_new_item")
        self.assertIsNone(result.item_orders)
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
