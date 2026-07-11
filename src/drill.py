"""Drill logic — adaptive note/rhythm selection + exercise assembly.

All note names and rhythm durations are COMPUTED here from the rendered
symbol via src.music.theory / src.music.rhythm. The LLM is never asked to
name a note or a duration.

Phase 2: note-topic selection uses a real spaced-repetition scheduler
(src.scheduler) backed by persisted scheduling state (src.db sched table).
The drill type is selectable ("note" | "rhythm").
"""

from __future__ import annotations

import random
import time
import uuid

from .curriculum import topic_blocks, topic_order
from .db import (
    get_all_sched,
    get_mastery,
    get_sched,
    record_result,
    save_sched,
    weight_for,
)
from .music import rhythm as R
from .music.staff import render_rhythm, render_staff
from .music.theory import (
    CLEF_BOTTOM_LINE_MIDI,
    CLEF_RANGE,
    is_natural,
    midi_to_name,
    name_to_midi,
    natural_names_in_clef,
)
from .scheduler import build_records, default_state, review, select_due

DRILL_TYPES = ("note", "rhythm")

# Monotonic counter so the scheduler rotates coverage across items instead of
# re-picking the same one (seed must advance per call, not be wall-clock).
_SELECT_SEQ = 0


def _next_select_seq() -> int:
    global _SELECT_SEQ
    _SELECT_SEQ += 1
    return _SELECT_SEQ


def _clef_candidates(clef: str) -> list[int]:
    lo, hi = CLEF_RANGE[clef]
    return [m for m in range(lo, hi + 1) if is_natural(m)]


def _options(correct_midi: int, clef: str, n: int = 4) -> list[str]:
    """Correct name + distractors drawn from the same clef's naturals."""
    correct = midi_to_name(correct_midi)
    pool = [nm for nm in natural_names_in_clef(clef) if nm != correct]
    distract = random.sample(pool, min(n - 1, len(pool)))
    opts = [correct] + distract
    random.shuffle(opts)
    return opts


# --------------------------------------------------------------------------- #
# Spaced-repetition note selection
# --------------------------------------------------------------------------- #

def _note_item_ids(student_id: str, clefs: list[str]) -> list[str]:
    blocks = topic_blocks(clefs)
    ids: list[str] = []
    for tid, blk in blocks.items():
        if blk["type"] == "note":
            ids.extend(blk["items"])
    return ids


def _scheduler_records(student_id: str, item_ids: list[str], now: float) -> list[dict]:
    return build_records(
        item_ids,
        get_state=lambda iid: get_sched(student_id, iid),
        weight_for=lambda iid: weight_for(student_id, iid),
        now=now,
    )


def _weighted_pick(student_id: str, clef: str) -> int:
    """Pick a natural MIDI note in the clef, weighting weak topics higher."""
    cands = _clef_candidates(clef)
    weights = []
    for m in cands:
        topic = f"{clef}:{midi_to_name(m)}"
        w = weight_for(student_id, topic)
        weights.append(1.0 / max(w, 0.05))
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0.0
    for m, wgt in zip(cands, weights):
        upto += wgt
        if r <= upto:
            return m
    return cands[-1]


def _scheduled_note_midi(student_id: str, clefs: list[str], now: float) -> tuple[str, int]:
    item_ids = _note_item_ids(student_id, clefs)
    records = _scheduler_records(student_id, item_ids, now)
    chosen = select_due(records, now, seed=_next_select_seq())
    if not chosen:
        clef = random.choice(clefs)
        return clef, _weighted_pick(student_id, clef)
    # chosen is like "treble:G4"; map to a MIDI in the chosen clef's range.
    clef, name = chosen.split(":", 1)
    midi = name_to_midi(name)
    lo, hi = CLEF_RANGE[clef]
    if lo <= midi <= hi and is_natural(midi):
        return clef, midi
    # Fallback: weighted pick if scheduler returned an odd/unknown id.
    return clef, _weighted_pick(student_id, clef)


# --------------------------------------------------------------------------- #
# Exercise assembly
# --------------------------------------------------------------------------- #

def make_exercise(
    student_id: str,
    clefs: list[str],
    drill_type: str = "note",
    now: float | None = None,
) -> dict:
    """Create one exercise with a COMPUTED correct answer + rendered SVG."""
    now = now if now is not None else time.time()
    if drill_type == "rhythm":
        return _make_rhythm_exercise(student_id, now)
    return _make_note_exercise(student_id, clefs, now)


def _make_note_exercise(student_id: str, clefs: list[str], now: float) -> dict:
    clef, midi = _scheduled_note_midi(student_id, clefs, now)
    correct = midi_to_name(midi)
    return {
        "id": f"note_{uuid.uuid4().hex[:12]}",
        "drill_id": None,
        "type": "note",
        "midi": midi,
        "correct_name": correct,          # COMPUTED, not from LLM
        "clef": clef,
        "staff_svg": render_staff(midi, clef),
        "options": _options(midi, clef),
    }


def _make_rhythm_exercise(student_id: str, now: float) -> dict:
    item_ids = [f"rhythm:{label}" for label in R.DURATIONS]
    records = _scheduler_records(student_id, item_ids, now)
    chosen = select_due(records, now, seed=_next_select_seq()) or "rhythm:quarter"
    _, label = chosen.split(":", 1)
    is_rest = random.random() < 0.5
    return {
        "id": f"rhythm_{uuid.uuid4().hex[:12]}",
        "drill_id": None,
        "type": "rhythm",
        "label": label,
        "is_rest": is_rest,
        "correct_name": R.name_for(label, is_rest),   # COMPUTED
        "staff_svg": render_rhythm(label, is_rest),
        "options": R.duration_labels(),
    }


def topic_for(exercise: dict) -> str:
    if exercise.get("type") == "rhythm":
        return f"rhythm:{exercise['label']}"
    return f"{exercise['clef']}:{exercise['correct_name']}"


def item_id_for(exercise: dict) -> str:
    return topic_for(exercise)


def check_answer(exercise: dict, student_answer: str, student_id: str) -> dict:
    """Verify the answer against the COMPUTED name, update mastery + scheduling."""
    if exercise.get("type") == "rhythm":
        result = R.check_duration(
            exercise["label"], student_answer, exercise.get("is_rest", False)
        )
    else:
        computed = exercise["correct_name"]
        correct = student_answer.strip().lower() == computed.strip().lower()
        result = {
            "correct": correct,
            "computed_name": computed,
            "hint": None,
            "revealed": False,
        }
        if not correct:
            ref = CLEF_BOTTOM_LINE_MIDI[exercise["clef"]]
            ref_name = midi_to_name(ref)
            step = abs(name_to_midi(computed) - ref)
            direction = "up" if name_to_midi(computed) >= ref else "down"
            result["hint"] = (
                f"From the {exercise['clef']} clef's bottom line note {ref_name}, "
                f"count {direction}: this is {computed}."
            )

    # update mastery (legacy weight) and scheduling state (spaced repetition)
    topic = topic_for(exercise)
    record_result(student_id, topic, result["correct"])
    iid = item_id_for(exercise)
    prev = get_sched(student_id, iid)
    state = prev if prev else default_state(iid, time.time())
    state = review(state, result["correct"], time.time())
    save_sched(student_id, state)
    return result


# --------------------------------------------------------------------------- #
# Proactive next-topic suggestion (powered by the dashboard + scheduler)
# --------------------------------------------------------------------------- #

def suggest_next_topic(
    student_id: str, clefs: list[str], now: float | None = None
) -> dict:
    """Proactively suggest the weakest topic to drill next (for the UI).

    Returns a dict with topic_id/label/type/drill_type/reason/weak_item and a
    mastery summary. Combines curriculum order with measured mastery (weight)
    and scheduler box across all candidate items.
    """
    now = now if now is not None else time.time()
    blocks = topic_blocks(clefs)
    mastery = {m["topic"]: m for m in get_mastery(student_id)}
    sched = {s["item_id"]: s for s in get_all_sched(student_id)}

    best = None  # (priority, order_idx, tid, weak_item, avg_box, avg_w)
    for order_idx, tid in enumerate(topic_order()):
        blk = blocks.get(tid)
        if not blk:
            continue
        weights = []
        boxes = []
        for iid in blk["items"]:
            weights.append(mastery.get(iid, {}).get("weight", 0.3))
            boxes.append(sched.get(iid, {}).get("box", 0))
        avg_w = sum(weights) / len(weights) if weights else 0.3
        avg_box = sum(boxes) / len(boxes) if boxes else 0
        weak = min(
            blk["items"],
            key=lambda iid: (sched.get(iid, {}).get("box", 0),
                             mastery.get(iid, {}).get("weight", 0.3)),
        )
        priority = avg_w  # smaller = weaker = higher priority
        candidate = (priority, order_idx, tid, weak, avg_box, avg_w)
        if best is None or priority < best[0]:
            best = candidate

    if not best:
        return {"topic_id": None, "label": None, "reason": "no curriculum",
                "weak_item": None, "mastery_summary": {}}

    _, order_idx, tid, weak, avg_box, avg_w = best
    blk = blocks[tid]
    reason = (
        f"Lowest mastery in your curriculum "
        f"(avg {avg_w:.0%} across {len(blk['items'])} items; "
        f"weakest: {weak})."
    )
    return {
        "topic_id": tid,
        "label": blk["label"],
        "type": blk["type"],
        "drill_type": blk["type"],
        "reason": reason,
        "weak_item": weak,
        "avg_box": avg_box,
        "avg_weight": avg_w,
    }
