"""Integration tests — live Gemini call + real exercise generation + check.

Runs against the REAL Gemini key in .env (presence-only check; skip if absent).
Also covers the deterministic check path (correct/incorrect) which does NOT
depend on the LLM.
"""

import os
import sys

import pytest

# Make `src` importable when run via `python -m pytest` from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import ensure_student, get_mastery, init_db, record_result  # noqa: E402
from src.drill import check_answer, make_exercise, topic_for  # noqa: E402
from src.llm import generate_teaching  # noqa: E402
from src.music.theory import midi_to_name  # noqa: E402


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
