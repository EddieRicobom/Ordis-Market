"""
ui.sound_manager
================

Plays Ordis' short UI sounds (activate / complete / error / click /
notification).

Design notes -- why it is built this way (an earlier SoundManager built a new
QMediaPlayer per play() and kept only the latest one):

* One QSoundEffect per sound, created once and kept alive. QSoundEffect is
  Qt's API for short, low-latency effects. Creating a player per play() call
  would destroy earlier players while they are still playing.
* QtMultimedia is imported lazily, on the first sound, never at module import.
  A machine whose audio stack is missing or broken can then only ever lose
  the sounds, not the whole application at start-up.
* Everything is best-effort: no method here raises. A sound problem is logged
  and the app carries on silently.
* The sound files are located relative to the app (bundled by PyInstaller, next
  to the .exe, or in the source tree), never relative to whatever the current
  working directory happens to be.
* Headless Qt platforms (offscreen / minimal -- tests, CI) are silent, and
  ORDIS_NO_SOUND=1 mutes the app on purpose.

Ordis: "I have prepared a small fanfare. It is mostly beeps. I am told this is
        acceptable."
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

SOUND_NAMES = ("activate", "complete", "error", "click", "notification")
DEFAULT_VOLUME = 0.6
_SILENT_PLATFORMS = frozenset({"offscreen", "minimal"})

EffectFactory = Callable[[Path, float], Any]


def _has_all_sounds(directory: Path) -> bool:
    return all((directory / f"ordis_{name}.wav").is_file() for name in SOUND_NAMES)


def candidate_sound_dirs() -> list[Path]:
    """Folders that may hold the .wav files, best first."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", None)  # PyInstaller --add-data
        if bundle_dir:
            candidates.append(Path(bundle_dir) / "sounds")
        candidates.append(Path(sys.executable).resolve().parent / "sounds")
    candidates.append(Path(__file__).resolve().parents[2] / "sounds")  # source tree
    return candidates


def find_sounds_dir() -> Optional[Path]:
    """The first candidate folder with all the sounds, regenerating them into
    the app's data folder if none of the shipped ones is usable."""
    for candidate in candidate_sound_dirs():
        if _has_all_sounds(candidate):
            return candidate

    try:
        from app.config.settings import DATA_DIR
        from app.ui.sound_generator import SoundGenerator

        generated = Path(DATA_DIR) / "sounds"
        if not _has_all_sounds(generated):
            SoundGenerator(str(generated)).generate_all()
        if _has_all_sounds(generated):
            return generated
    except Exception:  # noqa: BLE001 - sound is optional
        logger.warning("Could not generate the sound effects.", exc_info=True)
    return None


def _qt_effect_factory(path: Path, volume: float) -> Any:
    from PySide6.QtCore import QUrl
    from PySide6.QtMultimedia import QSoundEffect

    effect = QSoundEffect()
    effect.setSource(QUrl.fromLocalFile(str(path)))
    effect.setVolume(volume)
    return effect


class SoundManager:
    """Best-effort player for Ordis' sound effects. Create and use it from
    the UI thread only (QSoundEffect objects belong to the thread that made
    them)."""

    def __init__(
        self,
        sounds_dir: Optional[Path] = None,
        effect_factory: Optional[EffectFactory] = None,
        enabled: Optional[bool] = None,
        volume: float = DEFAULT_VOLUME,
    ) -> None:
        self._sounds_dir = Path(sounds_dir) if sounds_dir is not None else None
        self._effect_factory = effect_factory
        self._enabled = enabled  # None = decide automatically on first use
        self._volume = volume
        self._effects: Dict[str, Any] = {}
        self._loaded = False

    # -- public API ---------------------------------------------------------

    def preload(self) -> None:
        """Loads the effects now (call once the window is up) so the first
        sound doesn't pay the start-up cost."""
        self._ensure_loaded()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def play(self, name: str) -> None:
        try:
            if not self._ensure_loaded():
                return
            effect = self._effects.get(name)
            if effect is not None:
                effect.play()
        except Exception:  # noqa: BLE001 - a sound must never break the app
            logger.debug("Could not play sound %r", name, exc_info=True)

    def play_start(self) -> None:
        self.play("activate")

    def play_complete(self) -> None:
        self.play("complete")

    def play_error(self) -> None:
        self.play("error")

    def play_click(self) -> None:
        self.play("click")

    def play_notification(self) -> None:
        self.play("notification")

    # -- internals ----------------------------------------------------------

    def _is_enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        if os.environ.get("ORDIS_NO_SOUND"):
            return False
        try:
            from PySide6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            return app is not None and app.platformName() not in _SILENT_PLATFORMS
        except Exception:  # noqa: BLE001
            return False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return bool(self._effects)
        self._loaded = True
        try:
            if not self._is_enabled():
                return False
            directory = self._sounds_dir or find_sounds_dir()
            if directory is None:
                logger.warning("Sound effects not found; running without sound.")
                return False
            factory = self._effect_factory or _qt_effect_factory
            self._effects = {
                name: factory(directory / f"ordis_{name}.wav", self._volume)
                for name in SOUND_NAMES
            }
        except Exception:  # noqa: BLE001 - e.g. no audio stack on this machine
            logger.warning("Sound is unavailable; running without it.", exc_info=True)
            self._effects = {}
        return bool(self._effects)


_instance: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """The app-wide SoundManager (created on first use)."""
    global _instance
    if _instance is None:
        _instance = SoundManager()
    return _instance
