"""Local audio synthesis — no external service, no ffmpeg.

Renders a single note as a 16-bit PCM WAV in memory using numpy.
The pitch is taken from the COMPUTED midi (never the LLM).
"""

from __future__ import annotations

import io
import struct
import wave

import numpy as np

from .music.theory import pitch_frequency


def _note_samples(midi: int, duration: float = 0.8, sr: int = 22050) -> np.ndarray:
    """Synthesize a note with a soft attack/decay envelope (mono float -1..1)."""
    freq = pitch_frequency(midi)
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    # Slight vibrato + a 2nd harmonic for a warmer, more "instrument-like" tone.
    vibrato = 1.0 + 0.003 * np.sin(2 * np.pi * 5.0 * t)
    tone = np.sin(2 * np.pi * freq * vibrato * t)
    tone = tone + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
    # Envelope: quick attack, exponential decay.
    env = np.ones_like(t)
    attack = int(0.01 * sr)
    env[:attack] = np.linspace(0.0, 1.0, attack)
    decay = np.exp(-3.0 * t)
    env = env * decay
    return (0.35 * tone * env).astype(np.float32)


def synth_wav_bytes(midi: int, duration: float = 0.8, sr: int = 22050) -> bytes:
    """Return a WAV file (bytes) for the given MIDI note."""
    samples = _note_samples(midi, duration, sr)
    pcm = (samples * 32767.0).clip(-32768, 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()
