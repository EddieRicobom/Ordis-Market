"""
Ordis Market - Sound Effect Generator
Version 2.0

Generates synthetic sound effects using Python's wave module.
Creates Ordis-themed notification sounds programmatically.
No external audio files required.
"""

import wave
import math
import os
from pathlib import Path


class SoundGenerator:
    """Generates synthetic sound effects for Ordis Market."""
    
    SAMPLE_RATE = 44100  # Standard CD quality
    
    def __init__(self, output_dir: str = "sounds"):
        """Initialize sound generator with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_sine_wave(self, frequency: float, duration: float, amplitude: float = 0.3) -> list:
        """
        Generate a sine wave.
        
        Args:
            frequency: Frequency in Hz
            duration: Duration in seconds
            amplitude: Volume (0.0-1.0)
        
        Returns:
            List of audio samples
        """
        num_samples = int(self.SAMPLE_RATE * duration)
        samples = []
        
        for i in range(num_samples):
            sample = amplitude * math.sin(2 * math.pi * frequency * i / self.SAMPLE_RATE)
            samples.append(int(sample * 32767))  # Convert to 16-bit
        
        return samples
    
    def generate_frequency_sweep(self, start_freq: float, end_freq: float, 
                                  duration: float, amplitude: float = 0.3) -> list:
        """
        Generate a frequency sweep (chirp).
        
        Args:
            start_freq: Starting frequency in Hz
            end_freq: Ending frequency in Hz
            duration: Duration in seconds
            amplitude: Volume (0.0-1.0)
        
        Returns:
            List of audio samples
        """
        num_samples = int(self.SAMPLE_RATE * duration)
        samples = []
        
        for i in range(num_samples):
            # Linear frequency interpolation
            t = i / self.SAMPLE_RATE
            current_freq = start_freq + (end_freq - start_freq) * (t / duration)
            sample = amplitude * math.sin(2 * math.pi * current_freq * t)
            samples.append(int(sample * 32767))  # Convert to 16-bit
        
        return samples
    
    def add_envelope(self, samples: list, attack: float = 0.05, 
                    decay: float = 0.1, sustain: float = 0.7, 
                    release: float = 0.2) -> list:
        """
        Apply ADSR envelope to samples.
        
        Args:
            samples: List of audio samples
            attack: Attack time in seconds
            decay: Decay time in seconds
            sustain: Sustain level (0.0-1.0)
            release: Release time in seconds
        
        Returns:
            Enveloped samples
        """
        total_duration = len(samples) / self.SAMPLE_RATE
        attack_samples = int(attack * self.SAMPLE_RATE)
        decay_samples = int(decay * self.SAMPLE_RATE)
        sustain_samples = int((total_duration - attack - decay - release) * self.SAMPLE_RATE)
        release_samples = int(release * self.SAMPLE_RATE)
        
        result = []
        
        # Attack phase (0 to 1)
        for i in range(attack_samples):
            envelope = i / max(attack_samples, 1)
            result.append(int(samples[i] * envelope))
        
        # Decay phase (1 to sustain)
        for i in range(decay_samples):
            envelope = 1.0 - (1.0 - sustain) * (i / max(decay_samples, 1))
            idx = attack_samples + i
            if idx < len(samples):
                result.append(int(samples[idx] * envelope))
        
        # Sustain phase
        for i in range(sustain_samples):
            idx = attack_samples + decay_samples + i
            if idx < len(samples):
                result.append(int(samples[idx] * sustain))
        
        # Release phase (sustain to 0)
        for i in range(release_samples):
            envelope = sustain * (1.0 - i / max(release_samples, 1))
            idx = attack_samples + decay_samples + sustain_samples + i
            if idx < len(samples):
                result.append(int(samples[idx] * envelope))
        
        return result[:len(samples)]
    
    def write_wav(self, samples: list, filename: str):
        """
        Write samples to WAV file.
        
        Args:
            samples: List of audio samples
            filename: Output filename
        """
        filepath = self.output_dir / filename
        
        with wave.open(str(filepath), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.SAMPLE_RATE)
            wav_file.writeframes(bytes([sample & 0xFF for sample in samples] + 
                                      [sample >> 8 & 0xFF for sample in samples]))
    
    def generate_ordis_activate(self):
        """
        Generate Ordis activation sound (ascending tones).
        Characteristic "Ordis powers up" effect.
        """
        # Three ascending tones with frequency sweep
        samples = []
        
        # Tone 1: 400 Hz
        samples.extend(self.generate_sine_wave(400, 0.15, 0.25))
        # Tone 2: 600 Hz
        samples.extend(self.generate_sine_wave(600, 0.15, 0.25))
        # Tone 3: 800 Hz with sweep up
        sweep = self.generate_frequency_sweep(800, 1000, 0.2, 0.3)
        samples.extend(sweep)
        
        # Apply envelope for smoothness
        samples = self.add_envelope(samples, attack=0.02, decay=0.05, sustain=0.8, release=0.1)
        
        self.write_wav(samples, "ordis_activate.wav")
        return str(self.output_dir / "ordis_activate.wav")
    
    def generate_ordis_complete(self):
        """
        Generate Ordis completion sound (satisfying double-note chime).
        Characteristic "task complete" effect.
        """
        samples = []
        
        # Low note: 523 Hz (C5) - 0.2s
        samples.extend(self.generate_sine_wave(523, 0.2, 0.3))
        # Slight pause
        samples.extend([0] * int(0.05 * self.SAMPLE_RATE))
        # High note: 784 Hz (G5) - 0.3s
        samples.extend(self.generate_sine_wave(784, 0.3, 0.35))
        
        # Apply envelope
        samples = self.add_envelope(samples, attack=0.01, decay=0.08, sustain=0.85, release=0.15)
        
        self.write_wav(samples, "ordis_complete.wav")
        return str(self.output_dir / "ordis_complete.wav")
    
    def generate_ordis_error(self):
        """
        Generate Ordis error sound (dissonant warning).
        Characteristic "something wrong" alert.
        """
        samples = []
        
        # Dissonant pair: 300 Hz and 400 Hz (minor second interval)
        for i in range(int(0.3 * self.SAMPLE_RATE)):
            t = i / self.SAMPLE_RATE
            sample = 0.2 * math.sin(2 * math.pi * 300 * t) + \
                    0.2 * math.sin(2 * math.pi * 400 * t)
            samples.append(int(sample * 32767))
        
        # Apply sharp envelope for alert effect
        samples = self.add_envelope(samples, attack=0.01, decay=0.05, sustain=0.6, release=0.1)
        
        self.write_wav(samples, "ordis_error.wav")
        return str(self.output_dir / "ordis_error.wav")
    
    def generate_ordis_click(self):
        """
        Generate subtle button click sound.
        Characteristic "interaction" effect.
        """
        # Short high-frequency burst (500 Hz)
        samples = self.generate_sine_wave(500, 0.08, 0.15)
        samples = self.add_envelope(samples, attack=0.005, decay=0.03, sustain=0.4, release=0.02)
        
        self.write_wav(samples, "ordis_click.wav")
        return str(self.output_dir / "ordis_click.wav")
    
    def generate_ordis_notification(self):
        """
        Generate notification sound (brief two-tone alert).
        Characteristic "update" effect.
        """
        samples = []
        
        # First note: 659 Hz (E5) - 0.1s
        samples.extend(self.generate_sine_wave(659, 0.1, 0.25))
        # Second note: 784 Hz (G5) - 0.15s
        samples.extend(self.generate_sine_wave(784, 0.15, 0.3))
        
        samples = self.add_envelope(samples, attack=0.01, decay=0.05, sustain=0.75, release=0.1)
        
        self.write_wav(samples, "ordis_notification.wav")
        return str(self.output_dir / "ordis_notification.wav")
    
    def generate_all(self):
        """Generate all Ordis sound effects."""
        print("Generating Ordis Sound Effects...")
        paths = {
            "activate": self.generate_ordis_activate(),
            "complete": self.generate_ordis_complete(),
            "error": self.generate_ordis_error(),
            "click": self.generate_ordis_click(),
            "notification": self.generate_ordis_notification(),
        }
        
        print(f"✓ Sounds generated in {self.output_dir}/")
        for name, path in paths.items():
            print(f"  ✓ {name}: {path}")
        
        return paths


if __name__ == "__main__":
    generator = SoundGenerator()
    generator.generate_all()
