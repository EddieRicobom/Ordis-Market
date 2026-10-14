"""
tools/make_icon.py
==================

Exports the program icon (drawn in app/ui/app_icon.py) as:

  assets/ordis_market.ico   multi-size Windows icon, used by build.bat / PyInstaller
  assets/ordis_market.png   512 px picture, used by the README

Run from the project folder after changing the artwork:

    python tools/make_icon.py

The .ico is written by hand (PNG-compressed entries, supported since Windows
Vista), so no imaging library is needed beyond PySide6 itself.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QBuffer, QIODevice  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from app.ui.app_icon import ICON_SIZES, render_icon  # noqa: E402


def png_bytes(size: int) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    render_icon(size).save(buffer, "PNG")
    return bytes(buffer.data())


def build_ico(sizes=ICON_SIZES) -> bytes:
    """An .ico container holding one PNG per size."""
    images = [(size, png_bytes(size)) for size in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))  # reserved, type=icon, count
    offset = len(header) + 16 * len(images)
    directory = b""
    payload = b""
    for size, data in images:
        dimension = 0 if size >= 256 else size  # 0 means 256 in the directory
        directory += struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)
    return header + directory + payload


_APP = None  # keeps the Qt application alive for the whole run


def main() -> int:
    global _APP
    _APP = QGuiApplication.instance() or QGuiApplication(sys.argv[:1] + ["-platform", "offscreen"])
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    (assets / "ordis_market.ico").write_bytes(build_ico())
    (assets / "ordis_market.png").write_bytes(png_bytes(512))
    print(f"Wrote {assets / 'ordis_market.ico'} and {assets / 'ordis_market.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
