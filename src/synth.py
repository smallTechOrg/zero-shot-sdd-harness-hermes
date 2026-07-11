"""Local audio synthesis — no external service, no ffmpeg.

Renders a single note as a 16-bit PCM WAV in memory using numpy.
The pitch is taken from the COMPUTED midi (never the LLM).
"""

from __future__ import annotations

import io
import wave

import numpy as np

from .music.rhythm import beats
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


def synth_phrase_wav_bytes(
    phrase: dict,
    seconds_per_beat: float = 0.6,
    sr: int = 22050,
) -> bytes:
    """Concatenate a phrase's steps into one WAV.

    Pitched steps play their note for their duration's worth of beats; rests
    become matching stretches of silence. The whole phrase is one seamless
    stream so the student can hear the transcribed sequence. Computed from the
    phrase's MIDI + duration labels — never the LLM.
    """
    chunks: list[np.ndarray] = []
    for step in phrase["steps"]:
        dur_sec = max(0.15, beats(step["duration_label"]) * seconds_per_beat)
        if step.get("is_rest") or step.get("midi") is None:
            chunks.append(np.zeros(int(sr * dur_sec), dtype=np.float32))
        else:
            chunks.append(_note_samples(step["midi"], dur_sec, sr))
    if not chunks:
        chunks.append(np.zeros(int(sr * 0.3), dtype=np.float32))
    samples = np.concatenate(chunks)
    pcm = (samples * 32767.0).clip(-32768, 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()
