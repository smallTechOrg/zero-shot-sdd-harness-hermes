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
from .music import phrase as P
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
from .synth import DEFAULT_BPM

DRILL_TYPES = ("note", "rhythm", "phrase", "melody", "rhythm-dictation")

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
    if drill_type == "phrase":
        return _make_phrase_exercise(clefs, now)
    if drill_type == "melody":
        return _make_melody_exercise(clefs, now)
    if drill_type == "rhythm-dictation":
        return _make_rhythmdict_exercise(clefs, now)
    return _make_note_exercise(student_id, clefs, now)


# --------------------------------------------------------------------------- #
# Phrase (sight-reading / transcription) exercises — Phase 3
# --------------------------------------------------------------------------- #
def make_phrase(clef: str = "treble", rng: random.Random | None = None) -> dict:
    """Build a phrase dict: {clef, steps, correct}. Correctness is COMPUTED."""
    phrase = P.generate_phrase(clef=clef, rng=rng)
    phrase["correct"] = P.correct_transcription(phrase)
    return phrase


def _make_phrase_exercise(clefs: list[str], now: float) -> dict:
    """Sight-reading / transcription exercise (Phase 3).

    Returns the rendered phrase SVG + the COMPUTED correct sequence. The answer
    is included here so the transcription UI can reveal it — correctness is still
    computed, never LLM.
    """
    _ = now
    clef = (clefs or ["treble"])[0]
    phrase = make_phrase(clef=clef)
    steps = phrase["steps"]
    return {
        "id": f"phrase_{uuid.uuid4().hex[:12]}",
        "drill_id": None,
        "type": "phrase",
        "clef": clef,
        "midi": None,
        "correct_name": "phrase",
        "phrase": steps,
        "correct": phrase["correct"],  # computed [name, dur] sequence
        "staff_svg": P.render_phrase_svg(phrase),
        "options": [],
        "steps": len(steps),
    }


# --------------------------------------------------------------------------- #
# Phase 4 — Writing notation (dictation): melody + rhythm
# --------------------------------------------------------------------------- #
def make_melody(clef: str = "treble", rng: random.Random | None = None) -> dict:
    """Build a melody-dictation exercise: a PLAYED melodic line (pitch +
    duration per step) the student must reproduce on the staff.

    The correct sequence is COMPUTED from the generated melody via
    ``P.correct_transcription`` — never the LLM. The answer is NOT returned
    in the exercise; only the audio + per-step placement metadata.
    """
    melody = P.generate_melody(clef=clef, rng=rng)
    melody["correct"] = P.correct_transcription(melody)
    return melody


def make_rhythm_pattern(rng: random.Random | None = None) -> dict:
    """Build a rhythm-dictation exercise: a PLAYED duration pattern (no pitch)
    the student must reproduce on a step grid.

    Correctness is COMPUTED per step via ``R.check_duration`` (duration label
    match) — never the LLM. Only the audio + per-step metadata is returned.
    """
    pattern = P.generate_rhythm_pattern(rng=rng)
    # the computed correct duration sequence (rest-aware, but the *name* is the
    # duration label for both notes and rests).
    correct = [R.name_for(s["duration_label"], s["is_rest"]) for s in pattern["steps"]]
    pattern["correct"] = correct
    return pattern


def _make_melody_exercise(clefs: list[str], now: float) -> dict:
    _ = now
    clef = (clefs or ["treble"])[0]
    melody = make_melody(clef=clef)
    # Per-step placement metadata for the UI: a clickable staff + duration picker.
    # NO answer in the payload — the student must derive it by ear.
    steps_meta = [
        {"duration_label": s["duration_label"], "is_rest": False}
        for s in melody["steps"]
    ]
    return {
        "id": f"melody_{uuid.uuid4().hex[:12]}",
        "drill_id": None,
        "type": "melody",
        "clef": clef,
        "mode": "melody",
        "midi": None,
        "correct_name": "",
        "phrase": melody["steps"],       # pitched steps -> the UI renders a staff
        "steps_meta": steps_meta,
        "steps": len(melody["steps"]),
        "bpm": DEFAULT_BPM,
        "staff_svg": P.render_phrase_svg(melody),  # shown AFTER submission (reveal)
        "options": [],                    # placement UI supplies its own controls
        "correct": None,                # never sent to the client
    }


def _make_rhythmdict_exercise(clefs: list[str], now: float) -> dict:
    _ = (now, clefs)
    pattern = make_rhythm_pattern()
    steps_meta = [
        {"duration_label": s["duration_label"], "is_rest": s["is_rest"]}
        for s in pattern["steps"]
    ]
    return {
        "id": f"rhythm_{uuid.uuid4().hex[:12]}",
        "drill_id": None,
        "type": "rhythm-dictation",
        "clef": "treble",
        "mode": "rhythm",
        "midi": None,
        "correct_name": "",
        "phrase": None,                 # no pitch -> step grid, not a staff
        "steps_meta": steps_meta,
        "steps": len(pattern["steps"]),
        "bpm": DEFAULT_BPM,
        "staff_svg": "",
        "options": [],
        "correct": None,                # never sent to the client
    }


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
    if exercise.get("type") == "phrase":
        return "phrase"  # whole phrase is one scheduling item
    if exercise.get("type") == "melody":
        return "melody"  # whole melody dictation is one scheduling item
    if exercise.get("type") == "rhythm-dictation":
        return "rhythm-dictation"  # whole rhythm dictation is one item
    return f"{exercise['clef']}:{exercise['correct_name']}"


def item_id_for(exercise: dict) -> str:
    return topic_for(exercise)


def _persist_review(student_id: str, exercise: dict, correct: bool) -> str:
    topic = topic_for(exercise)
    record_result(student_id, topic, correct)
    iid = item_id_for(exercise)
    prev = get_sched(student_id, iid)
    state = prev if prev else default_state(iid, time.time())
    state = review(state, correct, time.time())
    save_sched(student_id, state)
    return topic


def check_melody(exercise: dict, submitted: list[dict], student_id: str) -> dict:
    """Verify a melody dictation submission (name + duration per step).

    The verdict is COMPUTED by ``src.music.phrase.check_transcription``
    against the generated melody — never the LLM. Mastery/scheduling for
    the whole melody skill is persisted under the ``melody`` topic.
    """
    melody = {"clef": exercise["clef"], "steps": exercise["phrase"]}
    result = P.check_transcription(melody, submitted)
    topic = _persist_review(student_id, exercise, result["correct"])
    result["topic"] = topic
    return result


def check_rhythm_dictation(
    exercise: dict, submitted: list[dict], student_id: str
) -> dict:
    """Verify a rhythm-dictation submission (duration per step, no pitch).

    Each submitted step is ``{"duration": str}``; correctness is COMPUTED
    per step via ``src.music.rhythm.check_duration`` on the generated
    pattern's duration label. Never the LLM.
    """
    pattern_steps = [
        {"duration_label": s["duration_label"], "is_rest": s.get("is_rest", False)}
        for s in (exercise.get("steps_meta") or [])
    ]
    total = len(pattern_steps)
    details: list[dict] = []
    first_wrong: int | None = None
    for i in range(total):
        exp_label = pattern_steps[i]["duration_label"]
        exp_is_rest = pattern_steps[i].get("is_rest", False)
        sub = submitted[i] if i < len(submitted) else {}
        got = (sub.get("duration") or "").strip().lower()
        verdict = R.check_duration(exp_label, got, exp_is_rest)
        dur_ok = verdict["correct"]
        details.append(
            {
                "duration_ok": dur_ok,
                "expected": exp_label,
            }
        )
        if first_wrong is None and not dur_ok:
            first_wrong = i
    if len(submitted) != total:
        first_wrong = first_wrong if first_wrong is not None else (
            len(submitted) if len(submitted) < total else 0
        )
    result = {
        "correct": first_wrong is None and len(submitted) == total,
        "total_steps": total,
        "first_wrong_step": first_wrong,
        "details": details,
    }
    topic = _persist_review(student_id, exercise, result["correct"])
    result["topic"] = topic
    return result


def check_phrase(exercise: dict, submitted: list[dict], student_id: str) -> dict:
    """Verify a transcribed phrase sequence, update mastery/scheduling.

    ``submitted`` is a list of {"name", "duration"} per step. The verdict is
    COMPUTED by src.music.phrase against the generated phrase — never the LLM.
    """
    result = P.check_transcription({"clef": exercise["clef"], "steps": exercise["phrase"]}, submitted)
    # Reuse computed correct sequence for the hint.
    topic = topic_for(exercise)
    record_result(student_id, topic, result["correct"])
    iid = item_id_for(exercise)
    prev = get_sched(student_id, iid)
    state = prev if prev else default_state(iid, time.time())
    state = review(state, result["correct"], time.time())
    save_sched(student_id, state)
    result["topic"] = topic
    return result


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
