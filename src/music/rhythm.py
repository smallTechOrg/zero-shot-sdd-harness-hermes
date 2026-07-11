"""Deterministic rhythm / duration naming core.

This module is the source of truth for *what a rhythm symbol is called*.
It is PURE and has NO dependency on any LLM. The LLM is never allowed to
name a duration — every "correct" answer in the rhythm drill is derived
here from the rendered symbol via :func:`name_for`.

Correctness contract (tested in tests/test_rhythm.py):
  * The set of valid duration labels is fixed and known.
  * :func:`name_for` returns the canonical label for a (label, is_rest) pair.
  * :func:`check_duration` compares the student's answer to the computed
    name case-insensitively and ignores surrounding whitespace.
"""

from __future__ import annotations

# Canonical duration labels, ordered short -> long, with their musical facts.
# ``beats`` is the duration in quarter-note beats. ``flags`` is the number of
# flags on the note stem (0 for whole/half/quarter). ``filled`` controls the
# note-head fill. Rests reuse the same labels but draw a rest glyph.
DURATIONS: dict[str, dict] = {
    "whole":     {"beats": 4.0,  "flags": 0, "filled": False, "is_note": True},
    "half":      {"beats": 2.0,  "flags": 0, "filled": False, "is_note": True},
    "quarter":   {"beats": 1.0,  "flags": 0, "filled": True,  "is_note": True},
    "eighth":    {"beats": 0.5,  "flags": 1, "filled": True,  "is_note": True},
    "sixteenth": {"beats": 0.25, "flags": 2, "filled": True,  "is_note": True},
}

# Rest labels mirror the notes; rendered as rest glyphs (still named the same).
REST_LABELS = ["whole", "half", "quarter", "eighth", "sixteenth"]


def duration_labels() -> list[str]:
    """All valid rhythm labels (notes and rests share the vocabulary)."""
    return list(DURATIONS.keys())


def is_valid_label(label: str) -> bool:
    return label in DURATIONS


def beats(label: str) -> float:
    return DURATIONS[label]["beats"]


def name_for(label: str, is_rest: bool = False) -> str:
    """Canonical name for a rendered rhythm symbol.

    The correct answer is simply the duration label — never guessed by the
    LLM. ``is_rest`` is recorded so the drill can ask "name this rest", but
    the *name* is the same duration label (e.g. 'quarter').
    """
    label = label.strip().lower()
    if label not in DURATIONS:
        raise ValueError(f"unknown duration label: {label!r}")
    return label


def check_duration(label: str, student_answer: str, is_rest: bool = False) -> dict:
    """Verify a rhythm answer against the COMPUTED name.

    Returns {correct, computed_name, hint, revealed}. The hint is computed
    (counts beats) — never LLM-generated.
    """
    computed = name_for(label, is_rest)
    correct = student_answer.strip().lower() == computed
    hint = None
    if not correct:
        b = beats(computed)
        kind = "rest" if is_rest else "note"
        hint = (
            f"That {kind} lasts {b:g} beat{'s' if b != 1 else ''} — "
            f"it is a {computed}."
        )
    return {
        "correct": correct,
        "computed_name": computed,
        "hint": hint,
        "revealed": False,
    }
