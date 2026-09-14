import unittest
from unittest.mock import patch

from app.integrations.launcher import (
    WARFRAME_STEAM_APP_ID,
    build_steam_launch_uri,
    launch_warframe_via_steam,
)


class TestSteamLauncher(unittest.TestCase):
    def test_build_uri_default_app_id(self):
        uri = build_steam_launch_uri()
        self.assertEqual(uri, f"steam://run/{WARFRAME_STEAM_APP_ID}")

    def test_build_uri_custom_app_id(self):
        uri = build_steam_launch_uri("12345")
        self.assertEqual(uri, "steam://run/12345")

    def test_launch_success(self):
        with patch("app.integrations.launcher.webbrowser.open", return_value=True) as mock_open:
            result = launch_warframe_via_steam()
        self.assertTrue(result)
        mock_open.assert_called_once_with(f"steam://run/{WARFRAME_STEAM_APP_ID}")

    def test_launch_reports_false_on_failure(self):
        with patch("app.integrations.launcher.webbrowser.open", return_value=False):
            result = launch_warframe_via_steam()
        self.assertFalse(result)

    def test_launch_never_raises(self):
        with patch(
            "app.integrations.launcher.webbrowser.open", side_effect=RuntimeError("no browser")
        ):
            result = launch_warframe_via_steam()
        self.assertFalse(result)

    def test_no_process_or_memory_apis_used(self):
        # Guard against regression: this module must stay limited to
        # opening a URI, never touching the game process directly.
        import app.integrations.launcher as launcher_module
        import inspect

        source = inspect.getsource(launcher_module)
        for forbidden in ("ReadProcessMemory", "ctypes", "psutil", "subprocess"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
