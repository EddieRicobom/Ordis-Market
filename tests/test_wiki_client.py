import unittest
from unittest.mock import MagicMock, patch

from app.integrations.wiki_client import WikiClient


def make_response(json_data):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = json_data
    return response


class TestWikiClient(unittest.TestCase):
    def setUp(self) -> None:
        self.client = WikiClient(requests_per_second=1000)

    def test_exact_match_resolves_with_redirect_handling(self):
        payload = {
            "query": {
                "pages": {
                    "123": {
                        "title": "Mesa Prime",
                        "fullurl": "https://wiki.warframe.com/w/Mesa_Prime",
                    }
                }
            }
        }
        with patch.object(self.client._session, "get", return_value=make_response(payload)):
            result = self.client.resolve("Mesa Prime")
        self.assertEqual(result.url, "https://wiki.warframe.com/w/Mesa_Prime")
        self.assertTrue(result.exact_match)
        self.assertEqual(result.resolved_title, "Mesa Prime")

    def test_missing_page_falls_back_to_fuzzy_search(self):
        exact_payload = {"query": {"pages": {"-1": {"missing": True}}}}
        fuzzy_payload = [
            "Mesa Primee",
            ["Mesa Prime"],
            [""],
            ["https://wiki.warframe.com/w/Mesa_Prime"],
        ]
        responses = [make_response(exact_payload), make_response(fuzzy_payload)]
        with patch.object(self.client._session, "get", side_effect=responses):
            result = self.client.resolve("Mesa Primee")
        self.assertEqual(result.url, "https://wiki.warframe.com/w/Mesa_Prime")
        self.assertFalse(result.exact_match)
        self.assertEqual(result.resolved_title, "Mesa Prime")

    def test_completely_unknown_item_returns_none_gracefully(self):
        exact_payload = {"query": {"pages": {"-1": {"missing": True}}}}
        fuzzy_payload = ["Nonexistent Thing", [], [], []]
        responses = [make_response(exact_payload), make_response(fuzzy_payload)]
        with patch.object(self.client._session, "get", side_effect=responses):
            result = self.client.resolve("Nonexistent Thing")
        self.assertIsNone(result.url)
        self.assertFalse(result.exact_match)

    def test_network_failure_does_not_raise_treated_as_not_found(self):
        import requests

        with patch.object(
            self.client._session, "get", side_effect=requests.ConnectionError("down")
        ):
            result = self.client.resolve("Anything")
        self.assertIsNone(result.url)

    def test_malformed_opensearch_response_handled_gracefully(self):
        exact_payload = {"query": {"pages": {"-1": {"missing": True}}}}
        responses = [make_response(exact_payload), make_response({"not": "a list"})]
        with patch.object(self.client._session, "get", side_effect=responses):
            result = self.client.resolve("Weird Item")
        self.assertIsNone(result.url)


if __name__ == "__main__":
    unittest.main()
