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


def _num_previously_seen(records: list[dict]) -> int:
    return sum(1 for r in records if r.get("last_seen", 0.0) > 0.0)


def select_due(records: list[dict], now: float, seed: float = 0.0) -> str | None:
    """Pick the next item to review from scheduling records.

    Order of precedence (pure, deterministic given ``seed``):
      1. Items that are due now, prioritised by lowest box (weakest first),
         then by earliest due_at, with a tiny deterministic tie-break from
         ``seed`` so we don't always repeat the same item.
      2. If nothing is due but some items have been seen, pick the lowest box
         overall (so we always keep the weakest in rotation).
      3. Brand-new items never seen: round-robin by a deterministic hash of
         the item_id + seed, so first-pass coverage is even across the set.

    ``seed`` is a caller-supplied float (e.g. time or a counter) used only
    for tie-breaking, never for correctness.
    """
    if not records:
        return None

    seen = [r for r in records if r.get("last_seen", 0.0) > 0.0]
    fresh = [r for r in records if r.get("last_seen", 0.0) <= 0.0]

    due = [r for r in seen if is_due(r, now)]
    if due:
        due_sorted = sorted(
            due,
            key=lambda r: (r["box"], r["due_at"], _hash_tiebreak(r["item_id"], seed)),
        )
        return due_sorted[0]["item_id"]

    # Nothing due: keep the weakest known item in rotation.
    if seen:
        seen_sorted = sorted(
            seen,
            key=lambda r: (r["box"], r["due_at"], _hash_tiebreak(r["item_id"], seed)),
        )
        return seen_sorted[0]["item_id"]

    # All brand-new: deterministic round-robin so initial coverage is even.
    fresh_sorted = sorted(
        fresh, key=lambda r: (_hash_tiebreak(r["item_id"], seed), r["item_id"])
    )
    return fresh_sorted[0]["item_id"]


def _hash_tiebreak(s: str, seed: float) -> float:
    """Deterministic float in [0, 1) from a string + seed (no randomness)."""
    h = hash((s, round(seed * 1000))) & 0xFFFFFFFF
    return h / 0xFFFFFFFF


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
