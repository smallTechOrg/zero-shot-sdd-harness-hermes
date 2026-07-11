"""Deterministic staff notation SVG renderer.

Produces a self-contained SVG string for a single note on a given clef.
Position is computed from :func:`src.music.theory.staff_step` — no LLM
involvement. Usable in the browser UI directly (returns an <svg> string).
"""

from __future__ import annotations

from .rhythm import DURATIONS
from .theory import (
    CLEF_BOTTOM_LINE_MIDI,
    staff_step,
    midi_to_name,
)

# Geometry
WIDTH = 460
LINE_SPACING = 12.0          # px between staff lines
HALF_STEP = LINE_SPACING / 2.0
BOTTOM_LINE_Y = 110.0        # y of the clef's bottom line (step 0)
TOP_MARGIN = 60.0
LEFT = 40.0
NOTE_X = 250.0
STAFF_WIDTH = 380.0

CLEF_GLYPH = {
    "treble": "\U0001D11E",  # 𝄞
    "bass": "\U0001D122",    # 𝄢
}
CLEF_FONT_SIZE = {"treble": 74, "bass": 56}
CLEF_Y = {"treble": 132, "bass": 120}


def _line_ys() -> list[float]:
    """y for each of the 5 staff lines (step 0..8)."""
    return [BOTTOM_LINE_Y - i * LINE_SPACING for i in range(5)]


def _ledger_lines(midi: int, clef: str) -> list[str]:
    step = staff_step(midi, clef)
    out: list[str] = []
    if step > 8:  # above the top line
        s = 10
        while s <= step:
            y = BOTTOM_LINE_Y - s * HALF_STEP
            out.append(_hline(y))
            s += 2
    elif step < 0:  # below the bottom line
        s = -2
        while s >= step:
            y = BOTTOM_LINE_Y - s * HALF_STEP
            out.append(_hline(y))
            s -= 2
    return out


def _hline(y: float) -> str:
    x1 = NOTE_X - 18
    x2 = NOTE_X + 18
    return (
        f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" '
        f'stroke="#1f2937" stroke-width="1.6"/>'
    )


def render_staff(midi: int, clef: str) -> str:
    """Return an SVG string rendering a single note on the given clef."""
    if clef not in CLEF_BOTTOM_LINE_MIDI:
        raise ValueError(f"unknown clef: {clef}")
    step = staff_step(midi, clef)
    y = BOTTOM_LINE_Y - step * HALF_STEP
    lines_ys = _line_ys()

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} '
        f'{int(BOTTOM_LINE_Y + TOP_MARGIN):d}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="Note {midi_to_name(midi)} on {clef} clef">',
    ]

    # staff lines
    for ly in lines_ys:
        parts.append(
            f'<line x1="{LEFT:.1f}" y1="{ly:.1f}" x2="{LEFT + STAFF_WIDTH:.1f}" '
            f'y2="{ly:.1f}" stroke="#1f2937" stroke-width="1.4"/>'
        )

    # clef glyph
    parts.append(
        f'<text x="{LEFT - 6:.1f}" y="{CLEF_Y[clef]:.1f}" '
        f'font-family="serif" font-size="{CLEF_FONT_SIZE[clef]}" '
        f'fill="#1f2937">{CLEF_GLYPH[clef]}</text>'
    )

    # ledger lines for this note (behind the note head)
    parts.extend(_ledger_lines(midi, clef))

    # stem (up below middle line step 4, down above)
    stem_up = step < 4
    if stem_up:
        stem = (
            f'<line x1="{NOTE_X + 9:.1f}" y1="{y:.1f}" x2="{NOTE_X + 9:.1f}" '
            f'y2="{y - 34:.1f}" stroke="#1f2937" stroke-width="1.6"/>'
        )
    else:
        stem = (
            f'<line x1="{NOTE_X - 9:.1f}" y1="{y:.1f}" x2="{NOTE_X - 9:.1f}" '
            f'y2="{y + 34:.1f}" stroke="#1f2937" stroke-width="1.6"/>'
        )
    parts.append(stem)

    # note head (slightly tilted ellipse)
    parts.append(
        f'<g transform="rotate(-18 {NOTE_X:.1f} {y:.1f})">'
        f'<ellipse cx="{NOTE_X:.1f}" cy="{y:.1f}" rx="9" ry="6.6" '
        f'fill="#111827"/></g>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


# ---- Rhythm / duration rendering -------------------------------------------------
# A rhythm symbol (note or rest) is drawn on a single staff line centred on the
# staff so the student focuses on the *shape* (open vs filled head, flags), not
# the pitch. Duration correctness is computed in src.music.rhythm — never LLM.

RHYTHM_LINE_Y = (BOTTOM_LINE_Y + TOP_MARGIN) / 2.0 + 10.0


def _rest_glyph(label: str) -> str:
    """A simple, legible rest glyph (text) for the given duration label.

    Uses a label with a small shape cue rather than a true Bravura glyph so it
    renders in any font; the *name* is still computed in rhythm.py.
    """
    cue = {
        "whole": "▬ (whole rest)",
        "half": "𝄻 (half rest)",
        "quarter": "𝄼 (quarter rest)",
        "eighth": "𝄽 (eighth rest)",
        "sixteenth": "𝄾 (sixteenth rest)",
    }
    return cue.get(label, label)


def render_rhythm(label: str, is_rest: bool = False) -> str:
    """Return an SVG string rendering a rhythm symbol (note head + stem + flags
    or a rest glyph) for the given duration label. Computed, never LLM."""
    if label not in DURATIONS:
        raise ValueError(f"unknown duration label: {label!r}")
    info = DURATIONS[label]
    y = RHYTHM_LINE_Y

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} '
        f'{int(BOTTOM_LINE_Y + TOP_MARGIN):d}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="{"rest" if is_rest else "note"}: {label}">',
    ]

    # one reference staff line through the centre
    parts.append(
        f'<line x1="{LEFT:.1f}" y1="{y:.1f}" x2="{LEFT + STAFF_WIDTH:.1f}" '
        f'y2="{y:.1f}" stroke="#1f2937" stroke-width="1.4"/>'
    )

    if is_rest:
        parts.append(
            f'<text x="{NOTE_X - 30:.1f}" y="{y + 8:.1f}" '
            f'font-size="34" font-family="serif" fill="#111827">'
            f'{_rest_glyph(label)}</text>'
        )
    else:
        # filled vs open note head
        fill = "#111827" if info["filled"] else "none"
        stroke = "#111827"
        parts.append(
            f'<g transform="rotate(-18 {NOTE_X:.1f} {y:.1f})">'
            f'<ellipse cx="{NOTE_X:.1f}" cy="{y:.1f}" rx="9" ry="6.6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.6"/></g>'
        )
        # stem (whole notes have none; half/quarter/eighth/sixteenth do)
        if label != "whole":
            stem_up = True  # always up for clarity in the rhythm drill
            dirn = -1 if stem_up else 1
            parts.append(
                f'<line x1="{NOTE_X + 9:.1f}" y1="{y:.1f}" '
                f'x2="{NOTE_X + 9:.1f}" y2="{y + 34 * dirn:.1f}" '
                f'stroke="#111827" stroke-width="1.6"/>'
            )
            # flags for eighth / sixteenth
            if info["flags"] >= 1:
                fy = y + 34 * dirn
                parts.append(
                    f'<path d="M {NOTE_X + 9:.1f} {fy:.1f} '
                    f'q 14 6 10 22" fill="none" stroke="#111827" '
                    f'stroke-width="2.2"/>'
                )
            if info["flags"] >= 2:
                fy = y + 34 * dirn + 14
                parts.append(
                    f'<path d="M {NOTE_X + 9:.1f} {fy:.1f} '
                    f'q 14 6 10 22" fill="none" stroke="#111827" '
                    f'stroke-width="2.2"/>'
                )

    parts.append("</svg>")
    return "\n".join(parts)
