"""Integration tests — live Gemini call + real exercise generation + check.

Runs against the REAL Gemini key in .env (presence-only check; skip if absent).
Also covers the deterministic check path (correct/incorrect) which does NOT
depend on the LLM.
"""

import os
import sys
import time

import pytest

# Make `src` importable when run via `python -m pytest` from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import (
    ensure_student,
    get_all_sched,
    get_mastery,
    get_sched,
    init_db,
    record_result,
    save_sched,
)  # noqa: E402
from src.drill import (  # noqa: E402
    check_answer,
    make_exercise,
    suggest_next_topic,
    topic_for,
)
from src.llm import generate_teaching  # noqa: E402
from src.music.theory import midi_to_name  # noqa: E402
from src import scheduler as SCHED  # noqa: E402


def _key_present() -> bool:
    if os.environ.get("AGENT_GEMINI_API_KEY"):
        return True
    try:
        with open(".env") as f:
            for line in f:
                if line.strip().startswith("AGENT_GEMINI_API_KEY="):
                    return bool(line.strip().split("=", 1)[1].strip())
    except FileNotFoundError:
        return False
    return False


@pytest.fixture(autouse=True)
def _db():
    init_db()
    yield


def test_drill_generates_and_checks_correctly_no_llm_needed():
    """The core correctness path works WITHOUT any LLM — name is computed."""
    ensure_student("it-student")
    ex = make_exercise("it-student", ["treble"])
    # computed name matches its own midi
    assert ex["correct_name"] == midi_to_name(ex["midi"])
    # correct answer is accepted
    r = check_answer(ex, ex["correct_name"], "it-student")
    assert r["correct"] is True
    assert r["computed_name"] == ex["correct_name"]
    assert r["hint"] is None
    # wrong answer is rejected with a computed hint
    wrong = "C9" if ex["correct_name"] != "C9" else "D9"
    r2 = check_answer(ex, wrong, "it-student")
    assert r2["correct"] is False
    assert r2["hint"] and ex["correct_name"] in r2["hint"]


def test_mastery_persists_and_updates():
    ensure_student("m-student")
    ex = make_exercise("m-student", ["treble"])
    topic = topic_for(ex)
    before = {m["topic"]: m for m in get_mastery("m-student")}
    record_result("m-student", topic, True)
    after = {m["topic"]: m for m in get_mastery("m-student")}
    if topic in before:
        assert after[topic]["attempts"] == before[topic]["attempts"] + 1
        assert after[topic]["correct"] == before[topic]["correct"] + 1
    else:
        assert after[topic]["attempts"] == 1


@pytest.mark.skipif(not _key_present(), reason="AGENT_GEMINI_API_KEY not set in .env")
def test_start_makes_one_real_gemini_call_and_returns_teaching():
    """Live smoke: a real Gemini call returns teaching text + tokens."""
    teaching = generate_teaching("reading notes on the staff", "treble")
    assert teaching["used_fallback"] is False
    assert teaching["text"].strip()
    assert teaching["tokens"]["total"] > 0
    assert teaching["model"]


def test_rhythm_drill_computed_correctness_and_persists_sched():
    """Phase 2: rhythm exercises compute the name + persist scheduling state."""
    ensure_student("r-student")
    ex = make_exercise("r-student", ["treble"], drill_type="rhythm")
    assert ex["type"] == "rhythm"
    # computed name equals the rendered label, never guessed
    assert ex["correct_name"] == ex["label"]
    assert ex["staff_svg"].startswith("<svg")
    # a wrong answer is rejected with a computed hint
    wrong = "whole" if ex["label"] != "whole" else "half"
    r = check_answer(ex, wrong, "r-student")
    assert r["correct"] is False
    assert r["hint"] and ex["label"] in r["hint"]
    # scheduling state was persisted for the rhythm item
    iid = f"rhythm:{ex['label']}"
    st = get_sched("r-student", iid)
    assert st is not None
    assert st["last_seen"] > 0


def test_scheduler_persists_box_and_spaces_review():
    """Phase 2: a correct review promotes the box; a miss resets it (DB)."""
    ensure_student("s-student")
    iid = "treble:C5"
    st = SCHED.default_state(iid, time.time())
    st = SCHED.review(st, True, time.time())
    save_sched("s-student", st)
    persisted = get_sched("s-student", iid)
    assert persisted["box"] == st["box"] == 1
    # now a miss resets it
    st2 = SCHED.review(persisted, False, time.time())
    save_sched("s-student", st2)
    assert get_sched("s-student", iid)["box"] == 0


def test_suggest_next_topic_returns_curriculum_block():
    """Phase 2: the suggestion engine returns a drillable topic block."""
    ensure_student("sg-student")
    suggestion = suggest_next_topic("sg-student", ["treble", "bass"])
    assert suggestion["topic_id"] in ("note-treble", "note-bass", "rhythm")
    assert suggestion["label"]
    assert suggestion["drill_type"] in ("note", "rhythm")
    assert suggestion["weak_item"]


def test_dashboard_data_shape():
    """Phase 2: the dashboard aggregates mastery + sched + suggestion."""
    ensure_student("d-student")
    from src.drill import make_exercise, check_answer

    ex = make_exercise("d-student", ["treble"], drill_type="note")
    check_answer(ex, ex["correct_name"], "d-student")
    topics = get_all_sched("d-student")
    # at least the reviewed item has scheduling state
    assert any(s["item_id"] == topic_for(ex) for s in topics)

