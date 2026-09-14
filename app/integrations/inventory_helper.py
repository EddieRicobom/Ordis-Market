"""
integrations.inventory_helper
==============================

Launches an external, Operator-provided inventory-export helper (such as
Sainan's warframe-api-helper: https://github.com/Sainan/warframe-api-helper)
as its own separate process -- exactly like double-clicking it in Explorer.

Ordis: "I did not build this tool, I do not run inside it, and I do not
        watch what it does once it starts. I simply open the door and let
        it walk through on its own."

IMPORTANT: this module performs NO process interaction with Warframe and
NO memory reading, here or anywhere else in Ordis Market. It starts a
separate executable the Operator explicitly selects -- the same thing a
shortcut or a file manager would do. Whatever that external program does
after it starts (including how it obtains Warframe's session credentials)
is entirely its own affair, run at the Operator's own discretion and risk,
not Ordis Market's.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

_CONFIG_FILENAME = "inventory_helper_path.txt"


class InventoryHelperLaunchError(Exception):
    """Raised when the external helper executable could not be started."""


def launch_inventory_helper(executable_path: str | Path) -> subprocess.Popen:
    """Starts the given executable as an independent process and returns
    immediately. Does not wait for it to finish, and never inspects,
    reads from, or otherwise interacts with it afterward.
    """
    path = Path(executable_path)
    if not path.exists():
        raise InventoryHelperLaunchError(f"'{path}' does not exist.")
    if not path.is_file():
        raise InventoryHelperLaunchError(f"'{path}' is not a file.")

    try:
        # cwd is set to the executable's own folder so it behaves exactly
        # as it would if the Operator double-clicked it there themselves
        # (e.g. so it writes inventory.json next to itself, as designed).
        return subprocess.Popen([str(path)], cwd=str(path.parent))
    except OSError as exc:
        raise InventoryHelperLaunchError(f"Could not start '{path.name}': {exc}") from exc


def _config_path(data_dir: Optional[Path] = None) -> Path:
    if data_dir is None:
        from app.config.settings import DATA_DIR as _DATA_DIR

        data_dir = _DATA_DIR
    return Path(data_dir) / _CONFIG_FILENAME


def load_saved_helper_path(data_dir: Optional[Path] = None) -> Optional[Path]:
    """Returns the last-remembered helper executable path, if any, so the
    Operator only has to locate it once."""
    config_path = _config_path(data_dir)
    if not config_path.exists():
        return None
    text = config_path.read_text(encoding="utf-8").strip()
    return Path(text) if text else None


def save_helper_path(executable_path: str | Path, data_dir: Optional[Path] = None) -> None:
    config_path = _config_path(data_dir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(str(executable_path), encoding="utf-8")
