import unittest
from unittest.mock import MagicMock, patch

from app.market.client import (
    ClientConfig,
    MarketNotFoundError,
    MarketRateLimitedError,
    MarketUnavailableError,
    WarframeMarketClient,
)


def make_response(status_code, json_data=None, headers=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = json_data or {}
    return response


class TestWarframeMarketClient(unittest.TestCase):
    def setUp(self) -> None:
        # No sleeping in tests -- rate limiter interval is effectively 0,
        # and we patch time.sleep for the backoff paths too.
        self.config = ClientConfig(requests_per_second=1000, max_retries=2, backoff_base_seconds=0.001)
        self.client = WarframeMarketClient(config=self.config)

    def test_get_orders_success(self):
        payload = {
            "data": [
                {"type": "sell", "platinum": 20, "quantity": 1, "user": {"status": "ingame"}},
                {"type": "buy", "platinum": 10, "quantity": 1, "user": {"status": "offline"}},
            ]
        }
        with patch.object(
            self.client._session, "request", return_value=make_response(200, payload)
        ):
            result = self.client.get_orders_for_item("mesa_prime_systems")
        self.assertEqual(len(result.sell_orders), 1)
        self.assertEqual(len(result.buy_orders), 1)
        self.assertEqual(result.sell_orders[0].platinum, 20)
        self.assertFalse(result.buy_orders[0].user_online)

    def test_404_raises_not_found(self):
        with patch.object(self.client._session, "request", return_value=make_response(404)):
            with self.assertRaises(MarketNotFoundError):
                self.client.get_orders_for_item("not_a_real_item")

    def test_429_retries_then_raises_after_budget(self):
        response = make_response(429, headers={"Retry-After": "0"})
        with patch.object(self.client._session, "request", return_value=response):
            with patch("time.sleep"):
                with self.assertRaises(MarketRateLimitedError):
                    self.client.get_orders_for_item("mesa_prime_systems")

    def test_429_then_success_recovers(self):
        responses = [
            make_response(429, headers={"Retry-After": "0"}),
            make_response(200, {"data": []}),
        ]
        with patch.object(self.client._session, "request", side_effect=responses):
            with patch("time.sleep"):
                result = self.client.get_orders_for_item("mesa_prime_systems")
        self.assertEqual(len(result.sell_orders), 0)

    def test_5xx_raises_unavailable_after_retries(self):
        with patch.object(self.client._session, "request", return_value=make_response(503)):
            with patch("time.sleep"):
                with self.assertRaises(MarketUnavailableError):
                    self.client.get_orders_for_item("mesa_prime_systems")

    def test_network_exception_raises_unavailable(self):
        import requests

        with patch.object(
            self.client._session, "request", side_effect=requests.ConnectionError("boom")
        ):
            with self.assertRaises(MarketUnavailableError):
                self.client.get_orders_for_item("mesa_prime_systems")

    def test_malformed_order_is_skipped_not_fatal(self):
        payload = {"data": [{"type": "sell"}, {"type": "sell", "platinum": 10, "quantity": 1}]}
        with patch.object(
            self.client._session, "request", return_value=make_response(200, payload)
        ):
            result = self.client.get_orders_for_item("mesa_prime_systems")
        self.assertEqual(len(result.sell_orders), 1)

    def test_mod_rank_extracted_from_order_payload(self):
        payload = {
            "data": [
                {"type": "sell", "platinum": 90, "quantity": 1, "mod_rank": 10, "user": {"status": "ingame"}},
                {"type": "sell", "platinum": 5, "quantity": 1, "rank": 0, "user": {"status": "ingame"}},
                {"type": "sell", "platinum": 3, "quantity": 1, "user": {"status": "ingame"}},
            ]
        }
        with patch.object(
            self.client._session, "request", return_value=make_response(200, payload)
        ):
            result = self.client.get_orders_for_item("serration")
        ranks = [o.mod_rank for o in result.sell_orders]
        self.assertEqual(ranks, [10, 0, None])


if __name__ == "__main__":
    unittest.main()
