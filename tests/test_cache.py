import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.cache.cache_store import PriceCache


class TestPriceCache(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.cache = PriceCache(Path(self.tmp_dir.name), ttl_seconds=1)

    def test_set_and_get(self):
        self.cache.set("mesa_prime_systems", {"price": 30})
        value = self.cache.get("mesa_prime_systems")
        self.assertEqual(value, {"price": 30})

    def test_missing_key_returns_none(self):
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_expired_entry_returns_none(self):
        self.cache.set("mesa_prime_systems", {"price": 30})
        # Force an immediate expiry by using a cache with 0 ttl.
        expiring_cache = PriceCache(Path(self.tmp_dir.name), ttl_seconds=0)
        import time

        time.sleep(0.01)
        self.assertIsNone(expiring_cache.get("mesa_prime_systems"))

    def test_stale_get_ignores_ttl(self):
        self.cache.set("mesa_prime_systems", {"price": 30})
        expiring_cache = PriceCache(Path(self.tmp_dir.name), ttl_seconds=0)
        import time

        time.sleep(0.01)
        self.assertEqual(expiring_cache.get_stale("mesa_prime_systems"), {"price": 30})


if __name__ == "__main__":
    unittest.main()
