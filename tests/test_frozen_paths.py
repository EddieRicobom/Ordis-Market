import importlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestFrozenPathResolution(unittest.TestCase):
    """Regression test: a PyInstaller --onefile build must anchor its
    persistent data next to the real .exe, not inside the temporary
    extraction folder __file__ would otherwise point to (which
    PyInstaller deletes on exit, silently wiping everything every run).
    """

    def tearDown(self) -> None:
        # Always restore normal (non-frozen) state and reload the module
        # back to its real behavior, so later tests aren't affected by
        # this test's simulated frozen environment.
        if hasattr(sys, "frozen"):
            del sys.frozen
        if hasattr(sys, "_MEIPASS"):
            del sys._MEIPASS
        import app.config.settings as settings

        importlib.reload(settings)

    def test_frozen_mode_anchors_next_to_executable(self):
        with TemporaryDirectory() as tmp_dir:
            fake_exe = Path(tmp_dir) / "OrdisMarket.exe"
            fake_exe.touch()

            sys.frozen = True
            sys.executable = str(fake_exe)

            import app.config.settings as settings

            importlib.reload(settings)

            self.assertEqual(settings.ROOT_DIR, Path(tmp_dir).resolve())
            self.assertTrue(settings.DATA_DIR.exists())
            self.assertTrue(settings.DATA_DIR.is_relative_to(Path(tmp_dir).resolve()))
            self.assertTrue(settings.LOG_DIR.is_relative_to(Path(tmp_dir).resolve()))

    def test_non_frozen_mode_uses_file_based_path_unchanged(self):
        # Sanity check that normal (non-frozen) behavior is untouched --
        # this is the path every other test in this project relies on.
        import app.config.settings as settings

        importlib.reload(settings)
        self.assertFalse(getattr(sys, "frozen", False))
        # Should resolve to the real project root, not some arbitrary path.
        self.assertTrue((settings.ROOT_DIR / "app").exists())


if __name__ == "__main__":
    unittest.main()
