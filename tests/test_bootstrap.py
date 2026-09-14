import importlib
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from app.bootstrap import ensure_dependencies

# NOTE: app.bootstrap.importlib IS the real `importlib` module object (not a
# copy), so patching its `import_module` attribute affects the whole
# process for the duration of the patch -- including unittest/mock's own
# internal name resolution. Every fake import function below must therefore
# be *name-aware* and delegate anything that isn't our fake target module
# back to the ORIGINAL import_module captured below (captured once, up
# front, before any patching happens -- NOT via `importlib.import_module`
# at call time, since by then that attribute IS the mock).
_REAL_IMPORT_MODULE = importlib.import_module


class TestBootstrap(unittest.TestCase):
    def test_all_satisfied_installs_nothing(self):
        def fake_import(name):
            if name == "fakepkg":
                return MagicMock()
            return _REAL_IMPORT_MODULE(name)

        with patch("app.bootstrap.importlib.import_module", side_effect=fake_import):
            with patch("app.bootstrap.subprocess.run") as mock_run:
                result = ensure_dependencies({"fakepkg": "fakepkg>=1.0"}, quiet=True)

        self.assertEqual(result.already_satisfied, ("fakepkg",))
        self.assertEqual(result.installed, ())
        self.assertTrue(result.ok)
        mock_run.assert_not_called()

    def test_missing_dependency_gets_installed(self):
        state = {"installed": False}

        def fake_import(name):
            if name == "fakepkg":
                if state["installed"]:
                    return MagicMock()
                raise ImportError(name)
            return _REAL_IMPORT_MODULE(name)

        def fake_run(*args, **kwargs):
            state["installed"] = True
            return MagicMock(returncode=0)

        with patch("app.bootstrap.importlib.import_module", side_effect=fake_import):
            with patch("app.bootstrap.subprocess.run", side_effect=fake_run) as mock_run:
                result = ensure_dependencies({"fakepkg": "fakepkg>=1.0"}, quiet=True)

        mock_run.assert_called_once()
        self.assertIn("fakepkg", result.installed)
        self.assertTrue(result.ok)

    def test_install_failure_is_reported_not_raised(self):
        def fake_import(name):
            if name == "fakepkg":
                raise ImportError(name)
            return _REAL_IMPORT_MODULE(name)

        with patch("app.bootstrap.importlib.import_module", side_effect=fake_import):
            with patch(
                "app.bootstrap.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "pip"),
            ):
                result = ensure_dependencies({"fakepkg": "fakepkg>=1.0"}, quiet=True)

        self.assertFalse(result.ok)
        self.assertIn("fakepkg", result.failed)

    def test_auto_install_disabled_just_reports_missing(self):
        def fake_import(name):
            if name == "fakepkg":
                raise ImportError(name)
            return _REAL_IMPORT_MODULE(name)

        with patch("app.bootstrap.importlib.import_module", side_effect=fake_import):
            with patch("app.bootstrap.subprocess.run") as mock_run:
                result = ensure_dependencies(
                    {"fakepkg": "fakepkg>=1.0"}, auto_install=False, quiet=True
                )

        mock_run.assert_not_called()
        self.assertFalse(result.ok)
        self.assertEqual(result.failed, ("fakepkg",))

    def test_install_reports_success_but_still_unimportable(self):
        # pip claims success but the module still can't be imported --
        # bootstrap should not lie about that.
        def fake_import(name):
            if name == "fakepkg":
                raise ImportError(name)
            return _REAL_IMPORT_MODULE(name)

        with patch("app.bootstrap.importlib.import_module", side_effect=fake_import):
            with patch("app.bootstrap.subprocess.run", return_value=MagicMock(returncode=0)):
                result = ensure_dependencies({"fakepkg": "fakepkg>=1.0"}, quiet=True)

        self.assertFalse(result.ok)
        self.assertIn("fakepkg", result.failed)


if __name__ == "__main__":
    unittest.main()
