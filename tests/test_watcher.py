import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.inventory.watcher import InventoryFileWatcher


class TestInventoryFileWatcher(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.watcher = InventoryFileWatcher(filename="inventory.json")

    def test_inactive_without_watch_dir(self):
        self.assertFalse(self.watcher.is_active)
        self.assertIsNone(self.watcher.poll())

    def test_no_file_yet_returns_none(self):
        self.watcher.set_watch_dir(self.tmp_dir.name)
        self.assertIsNone(self.watcher.poll())

    def test_existing_file_detected_on_first_poll(self):
        target = Path(self.tmp_dir.name) / "inventory.json"
        target.write_text("{}", encoding="utf-8")

        self.watcher.set_watch_dir(self.tmp_dir.name)
        result = self.watcher.poll()
        self.assertEqual(result, target)

    def test_unchanged_file_not_reported_twice(self):
        target = Path(self.tmp_dir.name) / "inventory.json"
        target.write_text("{}", encoding="utf-8")

        self.watcher.set_watch_dir(self.tmp_dir.name)
        first = self.watcher.poll()
        second = self.watcher.poll()
        self.assertEqual(first, target)
        self.assertIsNone(second)

    def test_updated_file_reported_again(self):
        target = Path(self.tmp_dir.name) / "inventory.json"
        target.write_text("{}", encoding="utf-8")

        self.watcher.set_watch_dir(self.tmp_dir.name)
        self.watcher.poll()  # consume the initial detection

        time.sleep(0.01)
        target.write_text('{"items": []}', encoding="utf-8")
        # Force a distinguishable mtime on filesystems with coarse resolution.
        new_time = time.time() + 1
        import os

        os.utime(target, (new_time, new_time))

        result = self.watcher.poll()
        self.assertEqual(result, target)

    def test_clear_deactivates_watcher(self):
        self.watcher.set_watch_dir(self.tmp_dir.name)
        self.watcher.clear()
        self.assertFalse(self.watcher.is_active)
        self.assertIsNone(self.watcher.target_path)

    def test_switching_watch_dir_resets_state(self):
        target = Path(self.tmp_dir.name) / "inventory.json"
        target.write_text("{}", encoding="utf-8")
        self.watcher.set_watch_dir(self.tmp_dir.name)
        self.watcher.poll()  # consume

        with TemporaryDirectory() as other_dir:
            other_target = Path(other_dir) / "inventory.json"
            other_target.write_text("{}", encoding="utf-8")
            self.watcher.set_watch_dir(other_dir)
            result = self.watcher.poll()
            self.assertEqual(result, other_target)


if __name__ == "__main__":
    unittest.main()
