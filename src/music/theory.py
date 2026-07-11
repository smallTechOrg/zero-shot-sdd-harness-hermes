"""Deterministic music-theory core.

This module is the source of truth for note names and staff placement.
It is PURE and has NO dependency on any LLM. The LLM is never allowed to
name a note — every "correct" answer in the app is derived here from the
rendered MIDI pitch via :func:`midi_to_name`.

Correctness contract (tested in tests/test_theory.py):
  * midi_to_name(m) == scientific pitch name (C4, A4=440, ...)
  * name_to_midi(midi_to_name(m)) == m
  * staff step of a note is the diatonic distance from the clef's
    bottom-line reference note, ignoring accidentals.
"""

from __future__ import annotations

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Letter index 0..6 for diatonic distance math (C=0, D=1, ..., B=6)
_LETTER_INDEX = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}

# MIDI numbers for each clef's bottom LINE note (the reference, step 0).
CLEF_BOTTOM_LINE_MIDI = {
    "treble": 64,  # E4
    "bass": 43,    # G2
}

# Natural-only exercise ranges (inclusive MIDI) per clef for Phase 1.
CLEF_RANGE = {
    "treble": (60, 79),  # C4 .. G5 (ledger lines below & above)
    "bass": (43, 65),    # G2 .. F4
}


def midi_to_name(midi: int) -> str:
    """Convert a MIDI note number to scientific pitch notation (e.g. 'A4')."""
    if not isinstance(midi, int):
        midi = int(round(midi))
    octave = midi // 12 - 1
    name = NOTE_NAMES[midi % 12]
    return f"{name}{octave}"


def name_to_midi(name: str) -> int:
    """Parse a scientific pitch name ('G4', 'C#5') to a MIDI number."""
    name = name.strip()
    letter = name[0].upper()
    i = 1
    acc = 0
    while i < len(name) and name[i] in "#b":
        acc += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    semitone = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter]
    return (octave + 1) * 12 + semitone + acc


def _diatonic_abs_index(midi: int) -> int:
    """Absolute diatonic (letter-only) position, ignoring accidentals."""
    octave = midi // 12 - 1
    letter_idx = _LETTER_INDEX[midi % 12]
    return octave * 7 + letter_idx


def diatonic_distance(midi: int, ref_midi: int) -> int:
    """Signed count of diatonic letter steps from ref to midi (no accidentals)."""
    return _diatonic_abs_index(midi) - _diatonic_abs_index(ref_midi)


def staff_step(midi: int, clef: str) -> int:
    """Diatonic step of a note relative to the clef's bottom line (step 0)."""
    return diatonic_distance(midi, CLEF_BOTTOM_LINE_MIDI[clef])


def is_natural(midi: int) -> bool:
    return midi % 12 in _LETTER_INDEX


def natural_names_in_clef(clef: str) -> list[str]:
    """All natural note names within the clef's Phase-1 range."""
    lo, hi = CLEF_RANGE[clef]
    return [midi_to_name(m) for m in range(lo, hi + 1) if is_natural(m)]


def pitch_frequency(midi: int) -> float:
    """Equal-tempered frequency in Hz (A4 = 440)."""
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))
