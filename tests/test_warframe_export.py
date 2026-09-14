import lzma
import unittest
from unittest.mock import MagicMock

import requests

from app.catalog.warframe_export import (
    WarframeExportError,
    extract_name_pairs,
    fetch_unique_name_index,
    parse_index,
)


class TestParseIndex(unittest.TestCase):
    def test_parses_hashed_filenames(self):
        text = (
            "ExportWarframes_en.json!00_AbCdEf\n"
            "ExportWeapons_en.json!00_GhIjKl\n"
            "\n"
            "IgnoredLineWithoutBang\n"
        )
        result = parse_index(text)
        self.assertEqual(result["ExportWarframes_en.json"], "ExportWarframes_en.json!00_AbCdEf")
        self.assertEqual(result["ExportWeapons_en.json"], "ExportWeapons_en.json!00_GhIjKl")
        self.assertNotIn("IgnoredLineWithoutBang", result)

    def test_empty_text_returns_empty_dict(self):
        self.assertEqual(parse_index(""), {})


class TestExtractNamePairs(unittest.TestCase):
    def test_extracts_pairs_from_any_top_level_array(self):
        payload = {
            "ExportRecipes": [
                {
                    "uniqueName": "/Lotus/Types/Recipes/Weapons/BratonPrimeBlueprint",
                    "name": "Braton Prime Blueprint",
                },
                {"uniqueName": "no_name_field_here"},  # missing name -- skipped
            ],
            "SomeOtherCategory": [
                {"uniqueName": "/Lotus/Foo/Bar", "name": "Foo Bar"},
            ],
        }
        pairs = extract_name_pairs(payload)
        self.assertEqual(
            pairs["/Lotus/Types/Recipes/Weapons/BratonPrimeBlueprint"], "Braton Prime Blueprint"
        )
        self.assertEqual(pairs["/Lotus/Foo/Bar"], "Foo Bar")
        self.assertNotIn("no_name_field_here", pairs)

    def test_non_dict_payload_returns_empty(self):
        self.assertEqual(extract_name_pairs([]), {})

    def test_non_list_values_are_ignored(self):
        payload = {"SomeKey": "not a list", "OtherKey": 42}
        self.assertEqual(extract_name_pairs(payload), {})


def _lzma_compress(text: str) -> bytes:
    return lzma.compress(text.encode("utf-8"))


class TestDecompressIndex(unittest.TestCase):
    def test_standard_lzma_format(self):
        from app.catalog.warframe_export import _decompress_index

        text = "ExportWeapons_en.json!00_hash\n"
        compressed = lzma.compress(text.encode("utf-8"))
        self.assertEqual(_decompress_index(compressed), text)

    def test_legacy_format_alone_lzma(self):
        from app.catalog.warframe_export import _decompress_index

        text = "ExportWeapons_en.json!00_hash\n"
        compressed = lzma.compress(text.encode("utf-8"), format=lzma.FORMAT_ALONE)
        self.assertEqual(_decompress_index(compressed), text)

    def test_already_plain_text_index_is_accepted(self):
        from app.catalog.warframe_export import _decompress_index

        text = "ExportWeapons_en.json!00_hash\n"
        self.assertEqual(_decompress_index(text.encode("utf-8")), text)

    def test_genuinely_unrecognizable_data_raises_with_diagnostic_info(self):
        from app.catalog.warframe_export import _decompress_index

        with self.assertRaises(WarframeExportError) as ctx:
            _decompress_index(b"\x00\x01\x02\x03completely unrecognizable binary junk")
        self.assertIn("first bytes", str(ctx.exception))


class TestFetchUniqueNameIndex(unittest.TestCase):
    def test_successful_fetch_merges_all_manifests(self):
        index_text = (
            "ExportWarframes_en.json!00_hash1\n"
            "ExportWeapons_en.json!00_hash2\n"
        )
        index_response = MagicMock(content=_lzma_compress(index_text))
        index_response.raise_for_status.return_value = None

        warframes_response = MagicMock()
        warframes_response.raise_for_status.return_value = None
        warframes_response.json.return_value = {
            "ExportWarframes": [
                {"uniqueName": "/Lotus/Powersuits/Excalibur/Excalibur", "name": "Excalibur"}
            ]
        }

        weapons_response = MagicMock()
        weapons_response.raise_for_status.return_value = None
        weapons_response.json.return_value = {
            "ExportWeapons": [
                {"uniqueName": "/Lotus/Weapons/Tenno/Rifle/Braton", "name": "Braton"}
            ]
        }

        session = MagicMock()

        def fake_get(url, timeout):
            if "index_en" in url:
                return index_response
            if "hash1" in url:
                return warframes_response
            if "hash2" in url:
                return weapons_response
            raise AssertionError(f"Unexpected URL: {url}")

        session.get.side_effect = fake_get

        result = fetch_unique_name_index(session=session)
        self.assertEqual(result["/Lotus/Powersuits/Excalibur/Excalibur"], "Excalibur")
        self.assertEqual(result["/Lotus/Weapons/Tenno/Rifle/Braton"], "Braton")

    def test_index_fetch_failure_raises(self):
        session = MagicMock()
        session.get.side_effect = ConnectionError("no network")
        with self.assertRaises(WarframeExportError):
            fetch_unique_name_index(session=session)

    def test_bad_lzma_data_raises(self):
        response = MagicMock(content=b"not actually lzma data")
        response.raise_for_status.return_value = None
        session = MagicMock()
        session.get.return_value = response
        with self.assertRaises(WarframeExportError):
            fetch_unique_name_index(session=session)

    def test_one_bad_manifest_does_not_sink_the_others(self):
        index_text = (
            "ExportWarframes_en.json!00_hash1\n"
            "ExportWeapons_en.json!00_hash2\n"
        )
        index_response = MagicMock(content=_lzma_compress(index_text))
        index_response.raise_for_status.return_value = None

        good_response = MagicMock()
        good_response.raise_for_status.return_value = None
        good_response.json.return_value = {
            "ExportWeapons": [{"uniqueName": "/Lotus/Weapons/Tenno/Rifle/Braton", "name": "Braton"}]
        }

        session = MagicMock()

        def fake_get(url, timeout):
            if "index_en" in url:
                return index_response
            if "hash1" in url:
                raise requests.ConnectionError("this manifest is down")
            if "hash2" in url:
                return good_response
            raise AssertionError(f"Unexpected URL: {url}")

        session.get.side_effect = fake_get

        result = fetch_unique_name_index(session=session)
        self.assertEqual(result["/Lotus/Weapons/Tenno/Rifle/Braton"], "Braton")
        self.assertNotIn("/Lotus/Powersuits/Excalibur/Excalibur", result)

    def test_no_usable_data_raises(self):
        index_text = "ExportWarframes_en.json!00_hash1\n"
        index_response = MagicMock(content=_lzma_compress(index_text))
        index_response.raise_for_status.return_value = None

        session = MagicMock()
        session.get.side_effect = [index_response, requests.ConnectionError("down")]
        with self.assertRaises(WarframeExportError):
            fetch_unique_name_index(session=session)


if __name__ == "__main__":
    unittest.main()
