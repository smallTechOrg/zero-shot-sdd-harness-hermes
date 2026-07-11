"""Deterministic sight-reading phrase core.

A *phrase* is a short sequence (2-4 steps) of musical events, where each step
is either a pitched note (a MIDI number) or a rest, paired with a duration
label. The tutor renders the phrase on the staff and plays it; the student
*transcribes* it — reproducing the note name (or "rest") plus duration for
every step, in order.

Everything here is PURE and has NO dependency on any LLM:

* :func:`generate_phrase` builds a phrase deterministically (seeded RNG).
* :func:`render_phrase_svg` composes per-step staff/rhythm glyphs left-to-right
  with spacing + a final bar line (real SMuFL glyphs, reused from ``staff``).
* :func:`correct_transcription` returns the COMPUTED (name, duration) sequence.
* :func:`check_transcription` verifies a submitted sequence order-sensitively,
  pointing at exactly which step failed.

The LLM is never asked to name a note, a rest, or a duration.
"""

from __future__ import annotations

import random

from .rhythm import DURATIONS
from .staff import (
    BOTTOM_LINE_Y,
    CLEF_FONT_SIZE,
    CLEF_GLYPH,
    CLEF_Y,
    FLAG_GLYPH,
    HALF_STEP,
    LEFT,
    LINE_SPACING,
    REST_FONT_SIZE,
    REST_GLYPH,
    REST_Y,
    TOP_MARGIN,
)
from .theory import (
    CLEF_BOTTOM_LINE_MIDI,
    CLEF_RANGE,
    is_natural,
    midi_to_name,
    staff_step,
)

# Layout geometry for a multi-step phrase.
_STEP_GAP = 96.0          # horizontal distance between consecutive steps
_NOTE_START_X = LEFT + 70.0  # leave room for the clef on the left
_RIGHT_PAD = 56.0         # room for the final bar line
_STEM_LEN = 34.0
_HEAD_RX = 9.0
_HEAD_RY = 6.6

# Probability that a given step is a rest (kept low so phrases stay pitched).
_REST_PROB = 0.25

DURATION_LABELS = list(DURATIONS.keys())


# --------------------------------------------------------------------------- #
# Generation (deterministic, seeded)
# --------------------------------------------------------------------------- #
def generate_phrase(
    clef: str = "treble",
    n_steps: int | None = None,
    rng: random.Random | None = None,
) -> dict:
    """Build a phrase deterministically.

    ``rng`` is a seeded ``random.Random`` for reproducibility (tests). If
    ``n_steps`` is None a random length in [2, 4] is chosen. Each step is
    ``{"midi": int|None, "duration_label": str, "is_rest": bool}``.
    """
    if clef not in CLEF_RANGE:
        raise ValueError(f"unknown clef: {clef}")
    rng = rng or random.Random()
    if n_steps is None:
        n_steps = rng.randint(2, 4)
    n_steps = max(2, min(4, n_steps))

    lo, hi = CLEF_RANGE[clef]
    candidates = [m for m in range(lo, hi + 1) if is_natural(m)]

    steps: list[dict] = []
    for _ in range(n_steps):
        if rng.random() < _REST_PROB:
            midi = None
        else:
            midi = rng.choice(candidates)
        label = rng.choice(DURATION_LABELS)
        steps.append(
            {
                "midi": midi,
                "duration_label": label,
                "is_rest": midi is None,
            }
        )
    return {"clef": clef, "steps": steps}


# --------------------------------------------------------------------------- #
# Correct transcription (computed, never LLM)
# --------------------------------------------------------------------------- #
def step_name(step: dict) -> str:
    """The computed correct name for one step: note name or 'rest'."""
    if step.get("is_rest") or step.get("midi") is None:
        return "rest"
    return midi_to_name(step["midi"])


def correct_transcription(phrase: dict) -> list[tuple[str, str]]:
    """Return the COMPUTED (name, duration) sequence for the phrase.

    ``name`` is a note name (e.g. 'G4') or the literal 'rest'; ``duration`` is
    the duration label (e.g. 'quarter'). Always derived from the phrase data.
    """
    out: list[tuple[str, str]] = []
    for step in phrase["steps"]:
        out.append((step_name(step), step["duration_label"]))
    return out


def check_transcription(phrase: dict, submitted: list[dict]) -> dict:
    """Verify a transcribed sequence against the COMPUTED phrase.

    ``submitted`` is a list of ``{"name": str, "duration": str}`` for each step
    in order. Returns::

        {
          "correct": bool,
          "total_steps": int,
          "first_wrong_step": int | None,   # 0-based index, or None if all correct
          "details": [                       # per-step verdict
            {"name_ok": bool, "duration_ok": bool, "expected": [name, dur]},
            ...
          ],
        }

    Comparison is order-sensitive and case-insensitive; 'rest' is recognised as
    the rest name. Never consults the LLM.
    """
    expected = correct_transcription(phrase)
    total = len(expected)
    details: list[dict] = []
    first_wrong: int | None = None

    for i in range(total):
        exp_name, exp_dur = expected[i]
        sub = submitted[i] if i < len(submitted) else {}
        got_name = (sub.get("name") or "").strip().lower()
        got_dur = (sub.get("duration") or "").strip().lower()
        name_ok = got_name == exp_name.lower()
        # duration must be a valid label and match exactly
        dur_ok = got_dur == exp_dur.lower() and got_dur in DURATIONS
        details.append(
            {
                "name_ok": name_ok,
                "duration_ok": dur_ok,
                "expected": [exp_name, exp_dur],
            }
        )
        if first_wrong is None and not (name_ok and dur_ok):
            first_wrong = i

    # A different number of submitted steps is wrong even if prefix matches.
    if len(submitted) != total:
        first_wrong = first_wrong if first_wrong is not None else (
            len(submitted) if len(submitted) < total else 0
        )

    return {
        "correct": first_wrong is None and len(submitted) == total,
        "total_steps": total,
        "first_wrong_step": first_wrong,
        "details": details,
    }


# --------------------------------------------------------------------------- #
# SVG rendering (composes per-step glyphs left-to-right)
# --------------------------------------------------------------------------- #
def _line_ys() -> list[float]:
    return [BOTTOM_LINE_Y - i * LINE_SPACING for i in range(5)]


def _ledger_lines(midi: int, clef: str, x: float) -> list[str]:
    step = staff_step(midi, clef)
    out: list[str] = []
    if step > 8:
        s = 10
        while s <= step:
            y = BOTTOM_LINE_Y - s * HALF_STEP
            out.append(_hline(y, x))
            s += 2
    elif step < 0:
        s = -2
        while s >= step:
            y = BOTTOM_LINE_Y - s * HALF_STEP
            out.append(_hline(y, x))
            s -= 2
    return out


def _hline(y: float, x: float) -> str:
    x1 = x - 18
    x2 = x + 18
    return (
        f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" '
        f'stroke="#1f2937" stroke-width="1.6"/>'
    )


def _note_fragment(midi: int, clef: str, x: float) -> list[str]:
    step = staff_step(midi, clef)
    y = BOTTOM_LINE_Y - step * HALF_STEP
    parts: list[str] = []
    parts.extend(_ledger_lines(midi, clef, x))

    stem_up = step < 4
    sx = x + 9 if stem_up else x - 9
    sy_top = y - _STEM_LEN if stem_up else y + _STEM_LEN
    parts.append(
        f'<line x1="{sx:.1f}" y1="{y:.1f}" x2="{sx:.1f}" y2="{sy_top:.1f}" '
        f'stroke="#1f2937" stroke-width="1.6"/>'
    )
    # note head
    parts.append(
        f'<g transform="rotate(-18 {x:.1f} {y:.1f})">'
        f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{_HEAD_RX}" ry="{_HEAD_RY}" '
        f'fill="#111827"/></g>'
    )
    # duration flags via real Bravura glyphs (eighth = 1, sixteenth = 2)
    return parts


def _note_with_flags(midi: int, clef: str, x: float, duration_label: str) -> list[str]:
    parts = _note_fragment(midi, clef, x)
    if duration_label in ("eighth", "sixteenth"):
        step = staff_step(midi, clef)
        y = BOTTOM_LINE_Y - step * HALF_STEP
        stem_up = step < 4
        sx = x + 9 if stem_up else x - 9
        sy_top = y - _STEM_LEN if stem_up else y + _STEM_LEN
        parts.append(
            f'<text x="{sx:.1f}" y="{(sy_top + 4):.1f}" '
            f'font-family="Bravura" font-size="30" fill="#111827">'
            f'{FLAG_GLYPH["eighth"]}</text>'
        )
        if duration_label == "sixteenth":
            parts.append(
                f'<text x="{sx:.1f}" y="{(sy_top + 20):.1f}" '
                f'font-family="Bravura" font-size="30" fill="#111827">'
                f'{FLAG_GLYPH["sixteenth"]}</text>'
            )
    return parts


def _rest_fragment(label: str, x: float) -> list[str]:
    return [
        f'<text x="{x:.1f}" y="{REST_Y[label]:.1f}" '
        f'text-anchor="middle" font-family="Bravura" '
        f'font-size="{REST_FONT_SIZE[label]}" fill="#111827">'
        f'{REST_GLYPH[label]}</text>'
    ]


def render_phrase_svg(phrase: dict) -> str:
    """Return an SVG string rendering the whole phrase on one staff.

    Notes/rests are placed left-to-right with spacing; a final bar line closes
    the phrase. Uses the same SMuFL glyphs and geometry as ``staff.render_staff``
    so it reads as correct notation. Computed, never LLM.
    """
    clef = phrase["clef"]
    if clef not in CLEF_BOTTOM_LINE_MIDI:
        raise ValueError(f"unknown clef: {clef}")
    steps = phrase["steps"]
    n = len(steps)

    # Width: start + n steps + trailing bar line.
    last_x = _NOTE_START_X + (n - 1) * _STEP_GAP
    width = int(last_x + _RIGHT_PAD)
    height = int(BOTTOM_LINE_Y + TOP_MARGIN)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Phrase: {n} steps on {clef} clef">',
    ]

    # staff lines across full width
    for ly in _line_ys():
        parts.append(
            f'<line x1="{LEFT:.1f}" y1="{ly:.1f}" x2="{width - 8:.1f}" '
            f'y2="{ly:.1f}" stroke="#1f2937" stroke-width="1.4"/>'
        )

    # clef glyph at the left
    parts.append(
        f'<text x="{LEFT - 6:.1f}" y="{CLEF_Y[clef]:.1f}" '
        f'font-family="Bravura" font-size="{CLEF_FONT_SIZE[clef]}" '
        f'fill="#1f2937">{CLEF_GLYPH[clef]}</text>'
    )

    # each step
    for i, step in enumerate(steps):
        x = _NOTE_START_X + i * _STEP_GAP
        if step.get("is_rest") or step.get("midi") is None:
            parts.extend(_rest_fragment(step["duration_label"], x))
        else:
            parts.extend(
                _note_with_flags(step["midi"], clef, x, step["duration_label"])
            )

    # final bar line (thin + thick) at the right edge
    bx = width - 22.0
    top = _line_ys()[-1]
    bottom = _line_ys()[0]
    parts.append(
        f'<line x1="{bx:.1f}" y1="{top:.1f}" x2="{bx:.1f}" y2="{bottom:.1f}" '
        f'stroke="#1f2937" stroke-width="2.2"/>'
    )
    parts.append(
        f'<line x1="{bx + 5:.1f}" y1="{top:.1f}" x2="{bx + 5:.1f}" '
        f'y2="{bottom:.1f}" stroke="#1f2937" stroke-width="5.0"/>'
    )

    parts.append("</svg>")
    return "\n".join(parts)
