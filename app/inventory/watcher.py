"""
inventory.watcher
==================

InventoryFileWatcher polls a folder the Operator points us to (e.g. wherever
`warframe-api-helper` saves `inventory.json`) and reports when that file is
new or has changed, so Ordis Market can auto-import it without the Operator
clicking "Import" every time.

Ordis: "I am not reading anything I should not. I am simply... watching a
        folder. Like a very patient, very bored Cephalon."

This performs ONLY local filesystem polling of a folder the Operator
explicitly selects. It never touches the Warframe process, never scans
memory, and never launches or automates any other tool -- it just notices
when a file the Operator told us about has changed, the same way any file
sync utility would.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class InventoryFileWatcher:
    def __init__(self, filename: str = "inventory.json") -> None:
        self._filename = filename
        self._watch_dir: Optional[Path] = None
        self._last_mtime: Optional[float] = None

    def set_watch_dir(self, directory: str | Path) -> None:
        self._watch_dir = Path(directory)
        self._last_mtime = None  # reset so the first poll after switching
        # folders will report the existing file, not silently skip it.

    def clear(self) -> None:
        self._watch_dir = None
        self._last_mtime = None

    @property
    def watch_dir(self) -> Optional[Path]:
        return self._watch_dir

    @property
    def is_active(self) -> bool:
        return self._watch_dir is not None

    @property
    def target_path(self) -> Optional[Path]:
        if self._watch_dir is None:
            return None
        return self._watch_dir / self._filename

    def poll(self) -> Optional[Path]:
        """Checks whether the target file exists and is new/changed since
        the last poll. Returns its path if there's something to import,
        otherwise None. Safe to call repeatedly (e.g. from a UI timer).
        """
        path = self.target_path
        if path is None or not path.exists():
            return None

        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None

        if self._last_mtime is None or mtime > self._last_mtime:
            self._last_mtime = mtime
            return path
        return None
