import importlib as real_importlib
import unittest
from unittest.mock import patch

from app.bootstrap import _installed_version, _is_unsatisfied, _parse_min_version

# NOTE: same gotcha documented in test_bootstrap.py -- app.bootstrap.importlib
# IS the real importlib module object, so patching its import_module
# attribute affects the whole process, including patch()'s own internal
# name resolution. Every fake import function below is name-aware and
# delegates anything that isn't the target fake module back to the real
# import_module, captured once up front before any patching happens.
_REAL_IMPORT_MODULE = real_importlib.import_module


def _fake_import_returning_none_for(target_name: str):
    def _fake(name):
        if name == target_name:
            return None
        return _REAL_IMPORT_MODULE(name)

    return _fake


class TestParseMinVersion(unittest.TestCase):
    def test_simple_spec(self):
        self.assertEqual(_parse_min_version("PySide6>=6.7,<7.0"), (6, 7))

    def test_spec_with_patch_version(self):
        self.assertEqual(_parse_min_version("requests>=2.31.0,<3.0"), (2, 31, 0))

    def test_no_lower_bound_returns_none(self):
        self.assertIsNone(_parse_min_version("somepkg<3.0"))

    def test_no_bounds_at_all_returns_none(self):
        self.assertIsNone(_parse_min_version("somepkg"))

    def test_spaces_around_operator_tolerated(self):
        self.assertEqual(_parse_min_version("pkg >= 1.2"), (1, 2))


class TestInstalledVersion(unittest.TestCase):
    def test_unknown_package_returns_none(self):
        self.assertIsNone(_installed_version("this_package_definitely_does_not_exist_12345"))

    def test_parses_real_installed_package_version(self):
        # requests is a real dependency of this project and should be
        # installed in any environment these tests run in.
        version = _installed_version("requests")
        self.assertIsNotNone(version)
        self.assertIsInstance(version, tuple)
        self.assertTrue(all(isinstance(part, int) for part in version))

    def test_unparseable_version_string_returns_none(self):
        with patch("app.bootstrap.metadata.version", return_value="not-a-version-at-all"):
            self.assertIsNone(_installed_version("whatever"))


class TestIsUnsatisfied(unittest.TestCase):
    def test_import_failure_is_unsatisfied(self):
        with patch("app.bootstrap.importlib.import_module", side_effect=ImportError):
            self.assertTrue(_is_unsatisfied("fakepkg", "fakepkg>=1.0"))

    def test_importable_with_no_version_bound_is_satisfied(self):
        with patch("app.bootstrap.importlib.import_module", side_effect=_fake_import_returning_none_for("fakepkg")):
            self.assertFalse(_is_unsatisfied("fakepkg", "fakepkg"))

    def test_importable_but_below_minimum_version_is_unsatisfied(self):
        with patch("app.bootstrap.importlib.import_module", side_effect=_fake_import_returning_none_for("fakepkg")):
            with patch("app.bootstrap._installed_version", return_value=(1, 0)):
                self.assertTrue(_is_unsatisfied("fakepkg", "fakepkg>=2.0"))

    def test_importable_and_at_or_above_minimum_is_satisfied(self):
        with patch("app.bootstrap.importlib.import_module", side_effect=_fake_import_returning_none_for("fakepkg")):
            with patch("app.bootstrap._installed_version", return_value=(2, 5)):
                self.assertFalse(_is_unsatisfied("fakepkg", "fakepkg>=2.0"))

    def test_unknown_installed_version_is_treated_as_satisfied_not_forced(self):
        # Can't verify -- shouldn't force an unnecessary reinstall on a guess.
        with patch("app.bootstrap.importlib.import_module", side_effect=_fake_import_returning_none_for("fakepkg")):
            with patch("app.bootstrap._installed_version", return_value=None):
                self.assertFalse(_is_unsatisfied("fakepkg", "fakepkg>=2.0"))

    def test_exact_minimum_version_is_satisfied(self):
        with patch("app.bootstrap.importlib.import_module", side_effect=_fake_import_returning_none_for("fakepkg")):
            with patch("app.bootstrap._installed_version", return_value=(2, 0)):
                self.assertFalse(_is_unsatisfied("fakepkg", "fakepkg>=2.0"))


if __name__ == "__main__":
    unittest.main()
