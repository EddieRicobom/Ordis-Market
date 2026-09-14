import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from app.integrations.inventory_helper import (
    InventoryHelperLaunchError,
    launch_inventory_helper,
    load_saved_helper_path,
    save_helper_path,
)


class TestLaunchInventoryHelper(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def _fake_exe(self, name: str = "warframe-api-helper.exe") -> Path:
        path = Path(self.tmp_dir.name) / name
        path.write_bytes(b"fake")
        return path

    def test_missing_file_raises(self):
        missing = Path(self.tmp_dir.name) / "nope.exe"
        with self.assertRaises(InventoryHelperLaunchError):
            launch_inventory_helper(missing)

    def test_directory_instead_of_file_raises(self):
        with self.assertRaises(InventoryHelperLaunchError):
            launch_inventory_helper(self.tmp_dir.name)

    def test_launches_with_cwd_set_to_parent(self):
        exe = self._fake_exe()
        with patch(
            "app.integrations.inventory_helper.subprocess.Popen", return_value=MagicMock()
        ) as mock_popen:
            launch_inventory_helper(exe)
        mock_popen.assert_called_once_with([str(exe)], cwd=str(exe.parent))

    def test_os_error_wrapped_as_launch_error(self):
        exe = self._fake_exe()
        with patch(
            "app.integrations.inventory_helper.subprocess.Popen",
            side_effect=OSError("permission denied"),
        ):
            with self.assertRaises(InventoryHelperLaunchError):
                launch_inventory_helper(exe)

    def test_no_memory_or_process_hooking_apis_used(self):
        import app.integrations.inventory_helper as helper_module
        import inspect

        source = inspect.getsource(helper_module)
        for forbidden in ("ReadProcessMemory", "ctypes", "psutil", "VirtualQueryEx"):
            self.assertNotIn(forbidden, source)


class TestHelperPathPersistence(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.data_dir = Path(self.tmp_dir.name)

    def test_no_saved_path_returns_none(self):
        self.assertIsNone(load_saved_helper_path(self.data_dir))

    def test_save_and_load_round_trip(self):
        exe_path = Path("C:/Tools/warframe-api-helper.exe")
        save_helper_path(exe_path, self.data_dir)
        loaded = load_saved_helper_path(self.data_dir)
        self.assertEqual(loaded, exe_path)

    def test_overwrites_previous_path(self):
        save_helper_path("C:/old/path.exe", self.data_dir)
        save_helper_path("D:/new/path.exe", self.data_dir)
        loaded = load_saved_helper_path(self.data_dir)
        self.assertEqual(loaded, Path("D:/new/path.exe"))


if __name__ == "__main__":
    unittest.main()
