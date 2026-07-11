"""Drill logic — adaptive note selection + exercise assembly.

All note names are COMPUTED here from the chosen MIDI pitch via
src.music.theory. The LLM is never asked to name a note.
"""

from __future__ import annotations

import random
import uuid

from .db import get_mastery, record_result, weight_for
from .music.staff import render_staff
from .music.theory import (
    CLEF_RANGE,
    is_natural,
    midi_to_name,
    name_to_midi,
    natural_names_in_clef,
)


def _clef_candidates(clef: str) -> list[int]:
    lo, hi = CLEF_RANGE[clef]
    return [m for m in range(lo, hi + 1) if is_natural(m)]


def _weighted_pick(student_id: str, clef: str) -> int:
    """Pick a natural MIDI note in the clef, weighting weak topics higher."""
    cands = _clef_candidates(clef)
    weights = []
    for m in cands:
        topic = f"{clef}:{midi_to_name(m)}"
        w = weight_for(student_id, topic)
        # higher selection probability when mastery is LOW
        weights.append(1.0 / max(w, 0.05))
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0.0
    for m, wgt in zip(cands, weights):
        upto += wgt
        if r <= upto:
            return m
    return cands[-1]


def _options(correct_midi: int, clef: str, n: int = 4) -> list[str]:
    """Correct name + distractors drawn from the same clef's naturals."""
    correct = midi_to_name(correct_midi)
    pool = [n for n in natural_names_in_clef(clef) if n != correct]
    distract = random.sample(pool, min(n - 1, len(pool)))
    opts = [correct] + distract
    random.shuffle(opts)
    return opts


def make_exercise(student_id: str, clefs: list[str]) -> dict:
    """Create one exercise with a COMPUTED correct name + rendered staff."""
    clef = random.choice(clefs)
    midi = _weighted_pick(student_id, clef)
    correct = midi_to_name(midi)
    return {
        "id": f"note_{uuid.uuid4().hex[:12]}",
        "drill_id": None,
        "midi": midi,
        "correct_name": correct,          # COMPUTED, not from LLM
        "clef": clef,
        "staff_svg": render_staff(midi, clef),
        "options": _options(midi, clef),
    }


def topic_for(exercise: dict) -> str:
    return f"{exercise['clef']}:{exercise['correct_name']}"


def check_answer(exercise: dict, student_answer: str, student_id: str) -> dict:
    """Verify the answer against the COMPUTED name and update mastery."""
    computed = exercise["correct_name"]
    correct = student_answer.strip().lower() == computed.strip().lower()
    record_result(student_id, topic_for(exercise), correct)
    hint = None
    if not correct:
        # Computed hint: count up from the clef's bottom line.
        from .music.theory import CLEF_BOTTOM_LINE_MIDI, midi_to_name

        ref = CLEF_BOTTOM_LINE_MIDI[exercise["clef"]]
        ref_name = midi_to_name(ref)
        step = abs(name_to_midi(computed) - ref)
        direction = "up" if name_to_midi(computed) >= ref else "down"
        hint = (
            f"From the {exercise['clef']} clef's bottom line note {ref_name}, "
            f"count {direction}: this is {computed}."
        )
    return {
        "correct": correct,
        "computed_name": computed,
        "hint": hint,
        "revealed": False,
    }


def suggest_next_topic(student_id: str, clefs: list[str]) -> str | None:
    """Proactively suggest the weakest topic to drill next (for the UI)."""
    mastery = get_mastery(student_id)
    by_topic = {m["topic"]: m for m in mastery}
    weakest = None
    weakest_w = 1.1
    for clef in clefs:
        for name in natural_names_in_clef(clef):
            topic = f"{clef}:{name}"
            w = by_topic.get(topic, {}).get("weight", 0.3)
            if w < weakest_w:
                weakest_w = w
                weakest = topic
    return weakest
