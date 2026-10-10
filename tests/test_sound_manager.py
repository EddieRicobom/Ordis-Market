import contextlib
import io
import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from app.ui import sound_manager as sm
from app.ui.sound_generator import SoundGenerator
from app.ui.sound_manager import SOUND_NAMES, SoundManager, find_sounds_dir

REPO_SOUNDS = Path(sm.__file__).resolve().parents[2] / "sounds"


class FakeEffect:
    def __init__(self, path, volume):
        self.path, self.volume, self.plays = path, volume, 0

    def play(self):
        self.plays += 1


class TestSoundManager(unittest.TestCase):
    def make(self, **kwargs):
        created = {}

        def factory(path, volume):
            effect = FakeEffect(path, volume)
            created[path.name] = effect
            return effect

        manager = SoundManager(sounds_dir=REPO_SOUNDS, effect_factory=factory, enabled=True, **kwargs)
        return manager, created

    def test_effects_are_created_once_and_reused(self):
        manager, created = self.make()
        manager.play_start()
        manager.play_start()
        manager.play_complete()
        self.assertEqual(set(created), {f"ordis_{n}.wav" for n in SOUND_NAMES})
        self.assertEqual(created["ordis_activate.wav"].plays, 2)
        self.assertEqual(created["ordis_complete.wav"].plays, 1)

    def test_each_helper_plays_its_own_sound(self):
        manager, created = self.make()
        manager.play_error()
        manager.play_click()
        manager.play_notification()
        for name, plays in (("error", 1), ("click", 1), ("notification", 1), ("activate", 0)):
            self.assertEqual(created[f"ordis_{name}.wav"].plays, plays, name)

    def test_unknown_sound_is_ignored(self):
        manager, _ = self.make()
        manager.play("does_not_exist")  # must not raise

    def test_disabled_manager_never_touches_the_audio_stack(self):
        def boom(path, volume):
            raise AssertionError("factory must not be called while muted")

        manager = SoundManager(sounds_dir=REPO_SOUNDS, effect_factory=boom, enabled=False)
        manager.play_start()
        manager.set_enabled(False)
        manager.play_complete()

    def test_env_var_mutes_the_app(self):
        def boom(path, volume):
            raise AssertionError("factory must not be called while muted")

        with patch.dict(os.environ, {"ORDIS_NO_SOUND": "1"}):
            manager = SoundManager(sounds_dir=REPO_SOUNDS, effect_factory=boom)
            manager.play_start()

    def test_headless_without_a_qt_app_is_silent(self):
        def boom(path, volume):
            raise AssertionError("factory must not be called without a GUI app")

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ORDIS_NO_SOUND", None)
            with patch("PySide6.QtGui.QGuiApplication.instance", return_value=None):
                SoundManager(sounds_dir=REPO_SOUNDS, effect_factory=boom).play_start()

    def test_a_failing_audio_backend_never_raises(self):
        def broken(path, volume):
            raise RuntimeError("no audio device")

        manager = SoundManager(sounds_dir=REPO_SOUNDS, effect_factory=broken, enabled=True)
        with self.assertLogs(sm.logger, level="WARNING"):
            manager.play_start()
        manager.play_complete()  # second call must not retry or raise

    def test_a_failing_effect_play_never_raises(self):
        class Exploding(FakeEffect):
            def play(self):
                raise RuntimeError("device vanished")

        manager = SoundManager(
            sounds_dir=REPO_SOUNDS, effect_factory=lambda p, v: Exploding(p, v), enabled=True
        )
        manager.play_error()

    def test_missing_sounds_dir_never_raises(self):
        with patch.object(sm, "find_sounds_dir", return_value=None), self.assertLogs(sm.logger, level="WARNING"):
            manager = SoundManager(effect_factory=lambda p, v: FakeEffect(p, v), enabled=True)
            manager.play_start()

    def test_volume_is_passed_to_the_effect(self):
        manager, created = self.make(volume=0.25)
        manager.play_click()
        self.assertEqual(created["ordis_click.wav"].volume, 0.25)

    def test_finds_the_shipped_sounds_regardless_of_cwd(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                self.assertEqual(find_sounds_dir(), REPO_SOUNDS)
            finally:
                os.chdir(old)


class TestSoundFiles(unittest.TestCase):
    """The shipped .wav files must be real, clean tones (they were once
    written with scrambled byte order, which plays as loud noise)."""

    @staticmethod
    def _samples(path):
        with wave.open(str(path)) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 44100)
            raw = w.readframes(w.getnframes())
        return struct.unpack("<%dh" % (len(raw) // 2), raw)

    @staticmethod
    def _roughness(samples):
        delta = sum(abs(samples[i + 1] - samples[i]) for i in range(len(samples) - 1)) / (len(samples) - 1)
        level = sum(abs(x) for x in samples) / len(samples)
        return delta / max(level, 1)

    def test_shipped_sounds_are_smooth_tones_not_noise(self):
        for name in SOUND_NAMES:
            samples = self._samples(REPO_SOUNDS / f"ordis_{name}.wav")
            self.assertGreater(len(samples), 1000, name)
            self.assertLess(self._roughness(samples), 0.3, f"{name} sounds like noise")

    def test_generator_writes_interleaved_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator = SoundGenerator(tmp)
            generator.write_wav([1, -2, 300, -32768, 32767], "t.wav")
            self.assertEqual(self._samples(Path(tmp) / "t.wav"), (1, -2, 300, -32768, 32767))

    def test_generator_regenerates_every_sound(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                paths = SoundGenerator(tmp).generate_all()
            self.assertEqual(set(paths), set(SOUND_NAMES))
            for path in paths.values():
                self.assertLess(self._roughness(self._samples(path)), 0.3)

    def test_chirp_actually_sweeps_between_its_end_frequencies(self):
        samples = SoundGenerator(tempfile.mkdtemp()).generate_frequency_sweep(400, 1200, 0.5, 0.3)

        def pitch(segment):
            crossings = sum(1 for i in range(len(segment) - 1) if (segment[i] < 0) != (segment[i + 1] < 0))
            return crossings / 2 / (len(segment) / 44100)

        n = len(samples)
        start, end = pitch(samples[: n // 10]), pitch(samples[-n // 10 :])
        self.assertLess(abs(start - 440), 60)   # ~ f0 + a little way into the sweep
        self.assertLess(abs(end - 1160), 60)    # ~ f1 minus a little


if __name__ == "__main__":
    unittest.main()
