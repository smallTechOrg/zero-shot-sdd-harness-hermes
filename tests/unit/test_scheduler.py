"""Unit tests for the spaced-repetition scheduler (pure, no I/O, no LLM)."""

from src import scheduler as S


def test_default_state_is_due_immediately():
    st = S.default_state("item-x", now=1000.0)
    assert st["box"] == 0
    assert st["due_at"] == 1000.0
    assert S.is_due(st, 1000.0) is True


def test_correct_review_promotes_box_and_spaces_out():
    st = S.default_state("a", now=0.0)
    st = S.review(st, True, now=0.0)
    assert st["box"] == 1
    assert st["streak"] == 1
    # due_at moved forward by the box-1 interval (60s)
    assert st["due_at"] == 60.0
    assert S.is_due(st, 59.0) is False
    assert S.is_due(st, 60.0) is True


def test_wrong_review_resets_to_box_zero():
    st = S.default_state("a", now=0.0)
    st = S.review(st, True, now=0.0)   # -> box 1
    st = S.review(st, True, now=60.0)  # -> box 2
    st = S.review(st, False, now=120.0)  # miss -> box 0, lapses +1
    assert st["box"] == 0
    assert st["streak"] == 0
    assert st["lapses"] == 1
    assert st["last_correct"] is False
    assert S.is_due(st, 120.0) is True  # box 0 is due immediately


def test_box_is_capped_at_max():
    st = S.default_state("a", now=0.0)
    for _ in range(20):
        st = S.review(st, True, now=st["due_at"] + 1)
    assert st["box"] <= S.MAX_BOX


def test_sm2_lite_graduates_long_streaks_faster():
    st = S.default_state("a", now=0.0)
    # build to box 3 with a 3-long streak (still below the cap)
    for _ in range(3):
        st = S.review(st, True, now=st["due_at"] + 1)
    assert st["box"] == 3
    assert st["streak"] == 3
    prev_box = st["box"]
    st = S.review(st, True, now=st["due_at"] + 1)
    # from box>=3 with streak>=3 it promotes by 2 (SM-2-lite early graduation)
    assert st["box"] - prev_box == 2


def test_select_due_prefers_weakest_due_item():
    # two items: one due at t=100 (box 2), one due at t=100 (box 0)
    recs = [
        {"item_id": "strong", "box": 4, "streak": 4, "lapses": 0,
         "due_at": 100.0, "last_seen": 50.0, "last_correct": True},
        {"item_id": "weak", "box": 0, "streak": 0, "lapses": 2,
         "due_at": 100.0, "last_seen": 50.0, "last_correct": False},
    ]
    chosen = S.select_due(recs, now=200.0, seed=1.0)
    assert chosen == "weak"  # lowest box wins among due items


def test_select_due_falls_back_to_lowest_box_when_none_due():
    recs = [
        {"item_id": "a", "box": 0, "streak": 0, "lapses": 0,
         "due_at": 9999.0, "last_seen": 50.0, "last_correct": True},
        {"item_id": "b", "box": 3, "streak": 3, "lapses": 0,
         "due_at": 9999.0, "last_seen": 50.0, "last_correct": True},
    ]
    chosen = S.select_due(recs, now=100.0, seed=1.0)
    assert chosen == "a"  # weakest known item kept in rotation


def test_select_due_round_robins_fresh_items():
    recs = [
        {"item_id": "x", "box": 0, "streak": 0, "lapses": 0,
         "due_at": 0.0, "last_seen": 0.0, "last_correct": False},
        {"item_id": "y", "box": 0, "streak": 0, "lapses": 0,
         "due_at": 0.0, "last_seen": 0.0, "last_correct": False},
        {"item_id": "z", "box": 0, "streak": 0, "lapses": 0,
         "due_at": 0.0, "last_seen": 0.0, "last_correct": False},
    ]
    # deterministic coverage: calling with different seeds yields variety
    seen = {S.select_due(recs, now=0.0, seed=s) for s in range(3, 9)}
    assert len(seen) >= 2  # not always the same first pick


def test_select_due_introduces_fresh_before_repeating_seen():
    # One seen item + several never-seen: scheduler must keep introducing fresh
    # items instead of looping the already-seen one (regression for the "stuck
    # on the same rhythm note" bug).
    recs = [
        {"item_id": "seen", "box": 0, "streak": 0, "lapses": 0,
         "due_at": 0.0, "last_seen": 50.0, "last_correct": False},
        {"item_id": "freshA", "box": 0, "streak": 0, "lapses": 0,
         "due_at": 0.0, "last_seen": 0.0, "last_correct": False},
        {"item_id": "freshB", "box": 0, "streak": 0, "lapses": 0,
         "due_at": 0.0, "last_seen": 0.0, "last_correct": False},
    ]
    chosen = S.select_due(recs, now=100.0, seed=1.0)
    assert chosen != "seen"
    assert chosen in {"freshA", "freshB"}


def test_select_due_empty_returns_none():
    assert S.select_due([], now=0.0) is None


def test_build_records_seeds_box_from_weight():
    items = ["treble:G4", "treble:C5"]
    states = S.build_records(
        items,
        get_state=lambda i: None,
        weight_for=lambda i: 1.0 if i == "treble:G4" else 0.05,
        now=1000.0,
    )
    by_id = {s["item_id"]: s for s in states}
    # high weight -> high box, low weight -> low box
    assert by_id["treble:G4"]["box"] > by_id["treble:C5"]["box"]
    # seeded items are immediately due
    assert S.is_due(by_id["treble:G4"], 1000.0)
