import re
import unittest
from unittest.mock import MagicMock

from app.ui.theme import STYLESHEET, apply_theme

# Qt Style Sheets support a CSS2.1-like subset -- these commonly-used CSS3
# properties are NOT supported and Qt will silently ignore (or warn about)
# them if present, so a regression here would be a real, easy-to-miss bug.
_UNSUPPORTED_CSS3_PROPERTIES = (
    "box-shadow",
    "transition",
    "transform",
    "animation",
    "flex",
    "grid-template",
    "text-shadow",
)

_EXPECTED_SELECTORS = (
    "QMainWindow",
    "QPushButton",
    "QLineEdit",
    "QTableWidget",
    "QHeaderView::section",
    "QProgressBar",
    "QProgressBar::chunk",
    "QStatusBar",
    "QToolTip",
)


class TestStylesheetStructure(unittest.TestCase):
    def test_stylesheet_is_nonempty_string(self):
        self.assertIsInstance(STYLESHEET, str)
        self.assertGreater(len(STYLESHEET.strip()), 100)

    def test_braces_are_balanced(self):
        self.assertEqual(STYLESHEET.count("{"), STYLESHEET.count("}"))

    def test_no_unsupported_css3_properties(self):
        lowered = STYLESHEET.lower()
        for prop in _UNSUPPORTED_CSS3_PROPERTIES:
            self.assertNotIn(
                prop, lowered, f"Qt QSS does not support '{prop}' -- remove or it will be a no-op."
            )

    def test_expected_selectors_present(self):
        for selector in _EXPECTED_SELECTORS:
            self.assertIn(selector, STYLESHEET)

    def test_no_double_curly_braces_left_from_fstring_escaping(self):
        # A common bug when hand-writing an f-string-based QSS block:
        # forgetting to collapse {{ }} escapes, leaving literal double
        # braces in the final string Qt receives.
        self.assertNotIn("{{", STYLESHEET)
        self.assertNotIn("}}", STYLESHEET)

    def test_every_selector_block_has_at_least_one_declaration(self):
        # Catches accidentally-empty rule blocks left over from edits.
        blocks = re.findall(r"\{([^{}]*)\}", STYLESHEET)
        for block in blocks:
            self.assertTrue(block.strip(), "Found an empty QSS rule block.")

    def test_hex_colors_are_well_formed(self):
        # Only check colors used as CSS property *values* (after a colon),
        # not Qt's '#ObjectName' selector syntax (e.g. 'QLabel#AppTitle'),
        # which also starts with '#' but isn't a color at all.
        for match in re.findall(r":\s*(#[0-9a-fA-F]+)\s*;", STYLESHEET):
            self.assertIn(len(match), (4, 7), f"Malformed hex color: {match}")


class TestApplyTheme(unittest.TestCase):
    def test_apply_theme_sets_stylesheet_on_target(self):
        fake_app = MagicMock()
        apply_theme(fake_app)
        fake_app.setStyleSheet.assert_called_once_with(STYLESHEET)


if __name__ == "__main__":
    unittest.main()
