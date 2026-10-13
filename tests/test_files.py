import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.common.files import atomic_write_text


class TestAtomicWrite(unittest.TestCase):
    def test_writes_and_replaces_without_leaving_a_temp_file(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "data.json"
        atomic_write_text(target, json.dumps({"a": 1}))
        atomic_write_text(target, json.dumps({"a": 2}))
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 2})
        self.assertEqual([p.name for p in tmp.iterdir()], ["data.json"])

    def test_a_failure_mid_write_keeps_the_old_file(self):
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "data.json"
        atomic_write_text(target, "old")
        with mock.patch("app.common.files.os.replace", side_effect=OSError("killed")):
            with self.assertRaises(OSError):
                atomic_write_text(target, "new")
        self.assertEqual(target.read_text(encoding="utf-8"), "old")


if __name__ == "__main__":
    unittest.main()
