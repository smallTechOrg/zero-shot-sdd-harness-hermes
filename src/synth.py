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

# Default beats-per-minute for the metronome lead-in + steady playback.
# Surfaced (and adjustable) in the UI; the same BPM drives the metronome
# clicks and the phrase/rhythm playback so the student has a steady pulse.
DEFAULT_BPM = 80.0

# Short, bright metronome click: a fast-decaying high tone (a "tick").
# Two slightly different timbres give an accented downbeat (beat 1 of a bar)
# vs the unaccented beats, exactly like a real mechanical metronome.
_CLICK_DOWNBEAT_MIDI = 105.0  # A#7-ish, brighter
_CLICK_MIDI = 98.0            # G7-ish, normal tick


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


def _click_samples(midi: float, duration: float = 0.05, sr: int = 22050) -> np.ndarray:
    """A short, bright metronome tick (mono float -1..1)."""
    freq = pitch_frequency(int(round(midi)))
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    # Sine + a touch of 2nd harmonic, very fast decay so it reads as a tick.
    tone = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t)
    env = np.exp(-60.0 * t)
    return (0.5 * tone * env).astype(np.float32)


def metronome_clicks(
    n_clicks: int,
    bpm: float = DEFAULT_BPM,
    beats_per_bar: int = 4,
    sr: int = 22050,
) -> np.ndarray:
    """Return a WAV-samples array of ``n_clicks`` metronome ticks.

    The first tick of each bar is accented (downbeat), the rest are normal.
    Spacing between clicks is exactly one beat at ``bpm``. Computed, never
    LLM — pure timing/math.
    """
    if n_clicks <= 0:
        return np.zeros(0, dtype=np.float32)
    seconds_per_beat = 60.0 / max(1.0, bpm)
    chunks: list[np.ndarray] = []
    for i in range(n_clicks):
        is_downbeat = (i % beats_per_bar) == 0
        midi = _CLICK_DOWNBEAT_MIDI if is_downbeat else _CLICK_MIDI
        chunks.append(_click_samples(midi, sr=sr))
        # trailing silence to fill the rest of the beat
        pad = int(sr * (seconds_per_beat - 0.05))
        pad = max(pad, 1)
        chunks.append(np.zeros(pad, dtype=np.float32))
    return np.concatenate(chunks)


def _to_wav_bytes(samples: np.ndarray, sr: int = 22050) -> bytes:
    pcm = (samples * 32767.0).clip(-32768, 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _lead_in_clicks(bpm: float, lead_in: int, sr: int) -> np.ndarray:
    if lead_in and lead_in > 0:
        return metronome_clicks(lead_in, bpm=bpm, sr=sr)
    return np.zeros(0, dtype=np.float32)
def synth_wav_bytes(midi: int, duration: float = 0.8, sr: int = 22050) -> bytes:
    """Return a WAV file (bytes) for the given MIDI note."""
    samples = _note_samples(midi, duration, sr)
    return _to_wav_bytes(samples, sr)


def _phrase_samples(phrase: dict, seconds_per_beat: float, sr: int) -> np.ndarray:
    """Concatenate a phrase's steps into one seamless samples array."""
    chunks: list[np.ndarray] = []
    for step in phrase["steps"]:
        dur_sec = max(0.15, beats(step["duration_label"]) * seconds_per_beat)
        if step.get("is_rest") or step.get("midi") is None:
            chunks.append(np.zeros(int(sr * dur_sec), dtype=np.float32))
        else:
            chunks.append(_note_samples(step["midi"], dur_sec, sr))
    if not chunks:
        chunks.append(np.zeros(int(sr * 0.3), dtype=np.float32))
    return np.concatenate(chunks)


def synth_phrase_wav_bytes(
    phrase: dict,
    seconds_per_beat: float = 0.6,
    bpm: float | None = None,
    lead_in: int = 0,
    sr: int = 22050,
) -> bytes:
    """Concatenate a phrase's steps into one WAV, optionally with a metronome.

    If ``lead_in`` > 0, the metronome ticks ``lead_in`` times at ``bpm``
    (or DEFAULT_BPM) BEFORE the phrase starts, and keeps ticking under the
    phrase at the same tempo. This gives the student a steady pulse to judge
    durations by ear. The pitch/duration content is COMPUTED from
    ``phrase`` — never the LLM.

    This is used by Phase 3 (sight-reading playback) AND Phase 4 (melody
    dictation) so both share one metronome-backed playback path.
    """
    if bpm is None:
        bpm = DEFAULT_BPM
    seconds_per_beat = 60.0 / max(1.0, bpm)

    parts: list[np.ndarray] = [_lead_in_clicks(bpm, lead_in, sr)]
    # metronome clicks laid UNDER the phrase (one tick per beat, aligned)
    body = _phrase_samples(phrase, seconds_per_beat, sr)
    if lead_in and lead_in > 0:
        n_phrase_beats = max(1, int(round(len(body) / (sr * seconds_per_beat))))
        metro = metronome_clicks(n_phrase_beats, bpm=bpm, sr=sr)
        # pad the shorter of the two so they overlay channel-aligned
        n = max(len(body), len(metro))
        body_p = np.pad(body, (0, n - len(body)))
        metro_p = np.pad(metro, (0, n - len(metro)))
        parts.append(np.clip(body_p + metro_p, -1.0, 1.0))
    else:
        parts.append(body)
    samples = np.concatenate([p for p in parts if p.size])
    return _to_wav_bytes(samples, sr)


def synth_melody_wav_bytes(
    melody: dict,
    bpm: float | None = None,
    lead_in: int = 4,
    sr: int = 22050,
) -> bytes:
    """Play a *melody* (a dict with ``clef`` + ``steps`` of pitched notes)
    with a metronome lead-in and steady pulse — the Phase 4 melody-dictation
    playback. Exactly like :func:`synth_phrase_wav_bytes` but defaults to a
    racy lead-in and is the canonical melody path. Computed, never LLM.
    """
    if bpm is None:
        bpm = DEFAULT_BPM
    return synth_phrase_wav_bytes(
        {"clef": melody.get("clef", "treble"), "steps": melody["steps"]},
        bpm=bpm,
        lead_in=lead_in,
        sr=sr,
    )


def synth_rhythm_wav_bytes(
    pattern: dict,
    bpm: float | None = None,
    lead_in: int = 4,
    sr: int = 22050,
) -> bytes:
    """Play a *rhythm-only* pattern (durations, possibly with rests) with a
    metronome lead-in and steady pulse — the Phase 4 rhythm-dictation
    playback. The pattern is a dict with ``steps`` of
    ``{duration_label, is_rest}`` (no pitch). Computed, never LLM.
    """
    if bpm is None:
        bpm = DEFAULT_BPM
    # Reuse the phrase synth: rests carry no pitch; pitched steps are silent
    # (the rhythm exercises have no pitch — but to keep metronome-aligned
    # timing we render them as rests so only the click marks the beat).
    steps = [
        {"midi": None, "duration_label": s["duration_label"],
         "is_rest": True}
        for s in pattern["steps"]
    ]
    return synth_phrase_wav_bytes(
        {"clef": "treble", "steps": steps},
        bpm=bpm,
        lead_in=lead_in,
        sr=sr,
    )
