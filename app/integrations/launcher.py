"""
integrations.launcher
======================

Launches Warframe through Steam's own `steam://run/<appid>` URI handler --
the same mechanism a desktop shortcut or the Steam library's "Play" button
uses.

Ordis: "I will start the engine, Operator. I will not, however, ride along
        and read your mail while you drive. Steam handles the rest; I am
        merely opening a door."

This module does exactly one thing: ask the operating system to open a
`steam://` URI. It never touches Warframe's process once it starts, never
reads memory, and has no way to know or control whether the game actually
launched successfully -- that visibility belongs to Steam, not us.
"""

from __future__ import annotations

import webbrowser

# Warframe's Steam application ID.
WARFRAME_STEAM_APP_ID = "230410"


def build_steam_launch_uri(app_id: str = WARFRAME_STEAM_APP_ID) -> str:
    return f"steam://run/{app_id}"


def launch_warframe_via_steam(app_id: str = WARFRAME_STEAM_APP_ID) -> bool:
    """Asks the OS to open Steam's launch URI for Warframe.

    Returns True if the URI handler was invoked without raising an
    exception -- this does NOT confirm Warframe actually started, only
    that we successfully handed the request off to the OS/Steam, exactly
    as if the Operator had clicked a desktop shortcut.
    """
    uri = build_steam_launch_uri(app_id)
    try:
        return bool(webbrowser.open(uri))
    except Exception:  # noqa: BLE001 - never let a launch attempt crash the app
        return False
