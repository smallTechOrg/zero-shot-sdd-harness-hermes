"""Deterministic spaced-repetition scheduler (pure, no I/O, no LLM).

Implements a Leitner-box scheduler with due-time spacing and SM-2-lite
promotion. The module is PURE: it takes scheduling state in and returns
scheduling state out, with no DB or time side effects. Callers inject
`now` so everything here is unit-testable and deterministic.

State per scheduling item (a row keyed by ``item_id``):
    box        int   — Leitner box (0..max_box); higher = known better
    streak      int   — consecutive correct answers
    lapses      int   — total times dropped (after a miss from a high box)
    due_at      float — epoch seconds when the item is next due
    last_seen   float — epoch seconds of last review
    last_correct bool  — whether the last review was correct

Leitner intervals (in seconds) per box. Lower boxes are reviewed sooner.
A miss never promotes: it drops the item to box 0 and resets the streak.
A correct answer promotes one box (capped), unless the item is already
past-due AND has a long streak — then it graduates faster (SM-2-lite).
"""

from __future__ import annotations

# Leitner box intervals in seconds. Box 0 is reviewed almost immediately
# (next time it is selected); higher boxes space further apart.
_LEITNER_INTERVALS_S = [
    0,        # box 0: due now (immediate re-review)
    60,       # box 1: ~1 min
    600,      # box 2: ~10 min
    3600,     # box 3: ~1 hour
    86400,    # box 4: ~1 day
    604800,   # box 5: ~1 week
]

MAX_BOX = len(_LEITNER_INTERVALS_S) - 1


def default_state(item_id: str, now: float) -> dict:
    """A fresh scheduling record for a never-seen item (boxed at 0, due now)."""
    return {
        "item_id": item_id,
        "box": 0,
        "streak": 0,
        "lapses": 0,
        "due_at": now,
        "last_seen": 0.0,
        "last_correct": False,
    }


def _interval_for(box: int) -> float:
    return _LEITNER_INTERVALS_S[min(max(box, 0), MAX_BOX)]


def _box_for_weight(weight: float) -> int:
    """Map a Phase-1 Leitner-style mastery weight (0.05..1.0) onto a box.

    Lets us seed the pure scheduler from the existing mastery weights so the
    two systems stay consistent during migration.
    """
    w = max(0.0, min(1.0, weight))
    return int(round(w * MAX_BOX))


def _seed_state(item_id: str, weight: float, now: float) -> dict:
    box = _box_for_weight(weight)
    return {
        "item_id": item_id,
        "box": box,
        "streak": 0 if box == 0 else box,  # assume known streak ~ box when seeded
        "lapses": 0,
        "due_at": now - _interval_for(box),  # seeded items are immediately due
        "last_seen": 0.0,
        "last_correct": box > 0,
    }


def review(item: dict, correct: bool, now: float) -> dict:
    """Apply a review outcome and return the NEXT scheduling state.

    Pure: returns a new dict; does not mutate ``item``.
    """
    item = dict(item)
    item["last_seen"] = now
    item["last_correct"] = correct

    if correct:
        # SM-2-lite: if the item is already well-known (high box) and has a
        # decent streak, graduate it one extra box to space it out faster.
        promote = 1
        if item["box"] >= 3 and item["streak"] >= 3:
            promote = 2
        item["box"] = min(MAX_BOX, item["box"] + promote)
        item["streak"] += 1
    else:
        item["box"] = 0
        item["streak"] = 0
        item["lapses"] += 1

    interval = _interval_for(item["box"])
    item["due_at"] = now + interval
    return item


def is_due(item: dict, now: float) -> bool:
    return item["due_at"] <= now


def select_due(records: list[dict], now: float, seed: float = 0.0) -> str | None:
    """Pick the next item to review from scheduling records.

    Order of precedence (pure, deterministic given ``seed``):
      1. Never-seen items (last_seen == 0) get full first-pass coverage before
         any re-review — they are rotated evenly so the tutor introduces every
         item. This is what prevents "stuck on the same note".
      2. Items due now, prioritised by lowest box (weakest first), earliest
         due_at, then a deterministic rotate so the same weak item isn't
         repeated forever.
      3. Nothing due: rotate over the whole set by lowest box, then rotate.

    ``seed`` is a caller-supplied float (e.g. a monotonic counter / time) used
    to rotate coverage — NOT for correctness. Callers should pass a value that
    advances each call (a counter, not a wall-clock that can repeat).
    """
    if not records:
        return None

    def _rotate(cands: list[dict]) -> dict:
        # Even rotation: index derived from seed, modulo the candidate count,
        # so successive calls walk the set instead of re-picking the same item.
        idx = int(round(seed)) % max(1, len(cands))
        return sorted(cands, key=lambda r: r["item_id"])[idx]

    fresh = [r for r in records if r.get("last_seen", 0.0) <= 0.0]
    if fresh:
        return _rotate(fresh)["item_id"]

    due = [r for r in records if is_due(r, now)]
    pool = due if due else records
    chosen = sorted(
        pool,
        key=lambda r: (r["box"], r["due_at"], r["item_id"]),
    )
    # rotate within the weakest box bucket so we don't loop one item
    weakest_box = chosen[0]["box"]
    bucket = [r for r in chosen if r["box"] == weakest_box]
    return _rotate(bucket)["item_id"]


def build_records(
    items: list[str], get_state, weight_for, now: float, default_weight: float = 0.3
) -> list[dict]:
    """Build scheduler records for a set of item ids.

    ``get_state(item_id)`` returns a persisted scheduling row (or None);
    ``weight_for(item_id)`` returns the Phase-1 mastery weight (or default).
    This bridges persisted scheduling state with the legacy weight column so
    the scheduler uses the strongest available signal.
    """
    records = []
    for item_id in items:
        persisted = get_state(item_id)
        if persisted:
            records.append(persisted)
        else:
            weight = weight_for(item_id) if weight_for else default_weight
            records.append(_seed_state(item_id, weight, now))
    return records
