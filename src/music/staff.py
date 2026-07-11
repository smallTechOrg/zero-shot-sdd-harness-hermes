"""Deterministic staff notation SVG renderer.

Produces a self-contained SVG string for a single note / rhythm symbol. Position
is computed from :func:`src.music.theory.staff_step` — no LLM involvement.

Glyphs (clefs, rests, flags) use the **Bravura SMuFL font** (OFL-licensed, vendored
at frontend/public/fonts/Bravura.woff and loaded in globals.css via @font-face) so
they render as *correct* notation in any browser. Noteheads and stems are drawn as
SVG primitives (their shapes are simple and exact). The LLM is never involved.
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

# Unicode musical symbols for clefs (standard Unicode, drawn by Bravura).
CLEF_GLYPH = {
    "treble": "\U0001D11E",  # 𝄞
    "bass": "\U0001D122",    # 𝄢
}
CLEF_FONT_SIZE = {"treble": 78, "bass": 58}
CLEF_Y = {"treble": 138, "bass": 122}

# SMuFL Private-Use-Area codepoints for rests + flags (rendered by Bravura).
# NOTE: these are in the U+E4xx / U+E2xx PUA, NOT the U+1D4xx math plane.
REST_GLYPH = {
    "whole": "\uE4E3",     # restWhole
    "half": "\uE4E4",      # restHalf
    "quarter": "\uE4E5",   # restQuarter
    "eighth": "\uE4E6",    # restEighth
    "sixteenth": "\uE4E7", # restSixteenth
}
FLAG_GLYPH = {
    "eighth": "\uE240",    # flag8thUp
    "sixteenth": "\uE241", # flag16thUp
}

# Font size (px) to draw a rest glyph so it reads at staff scale.
REST_FONT_SIZE = {"whole": 30, "half": 30, "quarter": 42, "eighth": 42, "sixteenth": 42}
# Vertical placement of the rest glyph's baseline so it sits correctly on the line.
REST_Y = {"whole": 122, "half": 103, "quarter": 116, "eighth": 116, "sixteenth": 116}


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

    # clef glyph (Bravura)
    parts.append(
        f'<text x="{LEFT - 6:.1f}" y="{CLEF_Y[clef]:.1f}" '
        f'font-family="Bravura" font-size="{CLEF_FONT_SIZE[clef]}" '
        f'fill="#1f2937">{CLEF_GLYPH[clef]}</text>'
    )

    # ledger lines for this note (behind the note head)
    parts.extend(_ledger_lines(midi, clef))

    # stem (up below middle line step 4, down above)
    stem_up = step < 4
    sx = NOTE_X + 9 if stem_up else NOTE_X - 9
    sy_top = y - 34 if stem_up else y + 34
    parts.append(
        f'<line x1="{sx:.1f}" y1="{y:.1f}" x2="{sx:.1f}" y2="{sy_top:.1f}" '
        f'stroke="#1f2937" stroke-width="1.6"/>'
    )

    # note head (slightly tilted filled ellipse — exact shape)
    parts.append(
        f'<g transform="rotate(-18 {NOTE_X:.1f} {y:.1f})">'
        f'<ellipse cx="{NOTE_X:.1f}" cy="{y:.1f}" rx="9" ry="6.6" '
        f'fill="#111827"/></g>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


# ---- Rhythm / duration rendering -------------------------------------------------
# A rhythm symbol (note or rest) is drawn on a single staff line centred on the
# staff so the student focuses on the *shape* (open vs filled head, flags, rest
# glyph), not the pitch. Duration correctness is computed in src.music.rhythm.

RHYTHM_LINE_Y = (BOTTOM_LINE_Y + TOP_MARGIN) / 2.0 + 10.0


def render_rhythm(label: str, is_rest: bool = False) -> str:
    """Return an SVG string rendering a rhythm symbol (note or rest) for the
    given duration label. Computed, never LLM. Real SMuFL glyphs for rests/flags."""
    if label not in DURATIONS:
        raise ValueError(f"unknown duration label: {label}")
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
            f'<text x="{NOTE_X:.1f}" y="{REST_Y[label]:.1f}" '
            f'text-anchor="middle" font-family="Bravura" '
            f'font-size="{REST_FONT_SIZE[label]}" fill="#111827">'
            f'{REST_GLYPH[label]}</text>'
        )
    else:
        # filled vs open note head (open = whole/half)
        fill = "#111827" if info["filled"] else "none"
        parts.append(
            f'<g transform="rotate(-18 {NOTE_X:.1f} {y:.1f})">'
            f'<ellipse cx="{NOTE_X:.1f}" cy="{y:.1f}" rx="9" ry="6.6" '
            f'fill="{fill}" stroke="#111827" stroke-width="1.6"/></g>'
        )
        # stem (whole notes have none)
        if label != "whole":
            stem_up = True
            sy_top = y - 34 if stem_up else y + 34
            sx = NOTE_X + 9 if stem_up else NOTE_X - 9
            parts.append(
                f'<line x1="{sx:.1f}" y1="{y:.1f}" x2="{sx:.1f}" y2="{sy_top:.1f}" '
                f'stroke="#111827" stroke-width="1.6"/>'
            )
            # flag(s) via real Bravura glyph at the stem top
            if info["flags"] >= 1:
                parts.append(
                    f'<text x="{sx:.1f}" y="{(sy_top + 4):.1f}" '
                    f'font-family="Bravura" font-size="30" fill="#111827">'
                    f'{FLAG_GLYPH["eighth"]}</text>'
                )
            if info["flags"] >= 2:
                parts.append(
                    f'<text x="{sx:.1f}" y="{(sy_top + 20):.1f}" '
                    f'font-family="Bravura" font-size="30" fill="#111827">'
                    f'{FLAG_GLYPH["sixteenth"]}</text>'
                )

    parts.append("</svg>")
    return "\n".join(parts)
