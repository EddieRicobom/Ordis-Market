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

    def test_cache_keeps_the_mod_rank_of_each_order(self):
        # Regression: mod_rank was dropped on save, so a cached ranked mod had
        # no listings "at its rank" and was priced as N/A.
        ranked = ItemOrders(
            slug="serration",
            sell_orders=(
                MarketOrder(OrderType.SELL, 5.0, 1, True, "ingame", mod_rank=0),
                MarketOrder(OrderType.SELL, 40.0, 1, True, "ingame", mod_rank=10),
            ),
            buy_orders=(MarketOrder(OrderType.BUY, 3.0, 1, True, "ingame", mod_rank=10),),
            fetched_at=time.time(),
        )
        client = MagicMock()
        client.get_orders_for_item.return_value = ranked
        repo = MarketRepository(client, self.cache)
        repo.get_orders("serration")

        cached = repo.get_orders("serration")
        self.assertTrue(cached.from_cache)
        self.assertEqual([o.mod_rank for o in cached.item_orders.sell_orders], [0, 10])
        self.assertEqual([o.mod_rank for o in cached.item_orders.buy_orders], [10])
        client.get_orders_for_item.assert_called_once()

    def test_legacy_cache_without_mod_rank_is_refetched_but_still_a_stale_fallback(self):
        legacy = {
            "slug": "serration",
            "sell_orders": [
                {"order_type": "sell", "platinum": 40.0, "quantity": 1, "user_online": True, "user_status": "ingame"}
            ],
            "buy_orders": [],
            "fetched_at": time.time(),
        }
        self.cache.set("orders_serration", legacy)
        client = MagicMock()
        client.get_orders_for_item.return_value = sample_orders("serration")
        repo = MarketRepository(client, self.cache)

        result = repo.get_orders("serration")  # fresh by TTL, but v1 -> must hit the network
        self.assertFalse(result.from_cache)
        client.get_orders_for_item.assert_called_once()

        # A v1 file is still better than nothing when the network is down.
        self.cache.set("orders_other", {**legacy, "slug": "other"})
        client.get_orders_for_item.side_effect = MarketUnavailableError("down")
        fallback = repo.get_orders("other")
        self.assertTrue(fallback.from_cache)
        self.assertTrue(fallback.stale)
        self.assertIsNone(fallback.item_orders.sell_orders[0].mod_rank)

    def test_network_failure_without_cache_returns_error(self):
        client = MagicMock()
        client.get_orders_for_item.side_effect = MarketUnavailableError("down")
        repo = MarketRepository(client, self.cache)
        result = repo.get_orders("brand_new_item")
        self.assertIsNone(result.item_orders)
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
