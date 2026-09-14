import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.config.settings import _fallback_root_dir, _prepare_data_dirs


class TestPrepareDataDirs(unittest.TestCase):
    def test_writable_primary_location_is_used_directly(self):
        with TemporaryDirectory() as tmp_dir:
            primary = Path(tmp_dir) / "app_folder"
            primary.mkdir()

            root, data, cache, log, used_fallback = _prepare_data_dirs(primary_root=primary)

            self.assertEqual(root, primary)
            self.assertFalse(used_fallback)
            self.assertTrue(data.exists())
            self.assertTrue(cache.exists())
            self.assertTrue(log.exists())
            self.assertTrue(data.is_relative_to(primary))

    def test_falls_back_when_primary_cannot_be_written(self):
        with TemporaryDirectory() as tmp_dir, TemporaryDirectory() as fallback_dir:
            primary = Path(tmp_dir) / "locked_folder"
            primary.mkdir()
            # Force a genuine, portable OSError regardless of whether these
            # tests run as root (which would otherwise bypass a real
            # permission-bit-based test): put a plain FILE where the code
            # needs to create a "data" directory, so mkdir() fails with a
            # real FileExistsError -- exercising the exact except OSError
            # branch a permission failure would also hit in production.
            (primary / "data").write_text("not a directory", encoding="utf-8")

            with patch(
                "app.config.settings._fallback_root_dir", return_value=Path(fallback_dir)
            ):
                root, data, cache, log, used_fallback = _prepare_data_dirs(primary_root=primary)

            self.assertTrue(used_fallback)
            self.assertEqual(root, Path(fallback_dir))
            self.assertTrue(data.is_relative_to(Path(fallback_dir)))
            self.assertTrue(data.exists())
            self.assertTrue(cache.exists())
            self.assertTrue(log.exists())

    def test_original_unwritable_location_is_left_alone(self):
        # The fallback must not try to "fix" or write into the original
        # broken location at all once it's given up on it.
        with TemporaryDirectory() as tmp_dir, TemporaryDirectory() as fallback_dir:
            primary = Path(tmp_dir) / "locked_folder"
            primary.mkdir()
            (primary / "data").write_text("not a directory", encoding="utf-8")

            with patch(
                "app.config.settings._fallback_root_dir", return_value=Path(fallback_dir)
            ):
                _prepare_data_dirs(primary_root=primary)

            self.assertFalse((primary / "logs").exists())


class TestFallbackRootDir(unittest.TestCase):
    def test_uses_localappdata_when_set(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": "/fake/localappdata"}):
            result = _fallback_root_dir()
        self.assertEqual(result, Path("/fake/localappdata") / "OrdisMarket")

    def test_uses_home_dotfolder_when_localappdata_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "LOCALAPPDATA"}
        with patch.dict(os.environ, env, clear=True):
            result = _fallback_root_dir()
        self.assertEqual(result, Path.home() / ".ordis-market")


if __name__ == "__main__":
    unittest.main()
