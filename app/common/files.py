"""
common.files
============

Small file helpers shared by the stores that persist JSON next to the app.
"""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, text: str) -> None:
    """Writes `text` to `path` so that a crash, a kill or a thread terminated
    mid-write can never leave a half-written file behind: the new content goes
    to a sibling temp file first and then replaces the target in one step."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
