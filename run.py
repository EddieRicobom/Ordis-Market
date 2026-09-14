#!/usr/bin/env python3
"""
run.py
======

Recommended way to launch Ordis Market from source.

Ordis: "Run this one, Operator. I promise to fetch my own parts before
        you have to ask twice."

Unlike `python -m app.main` (which assumes dependencies are already
installed and simply reports an error if they're not), this script checks
for PySide6 / requests / openpyxl first and installs anything missing via
pip automatically, then launches the dashboard.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make sure we're actually running from our own folder, no matter how this
# script was launched. Without this, a shortcut, "Run as administrator",
# or a scheduled task can leave the working directory pointed at something
# unrelated (commonly C:\Windows\System32 on Windows), which breaks every
# relative path this app or its bootstrap step relies on.
# Ordis: "I checked. We were not, in fact, supposed to be in System32."
_PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(_PROJECT_ROOT)
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.bootstrap import ensure_dependencies


def main() -> int:
    result = ensure_dependencies()

    if result.installed:
        print(f"[Ordis Market] Installed: {', '.join(result.installed)}")

    if not result.ok:
        print(
            "[Ordis Market] Ordis could not install everything automatically: "
            f"{', '.join(result.failed)}"
        )
        print(
            "Operator, please try manually: pip install -r requirements.txt"
        )
        return 1

    # Imported only now, after we're sure the packages exist.
    from app.main import main as app_main

    return app_main()


if __name__ == "__main__":
    sys.exit(main())
