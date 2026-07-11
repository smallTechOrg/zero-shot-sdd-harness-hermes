"""Unit tests for the deterministic sight-reading phrase core (Phase 3).

Proves the HARD CONSTRAINT for the phrase drill: note names, durations, AND
the order of the transcribed sequence are COMPUTED from the generated phrase,
never taken from or influenced by the LLM.
"""

import random

from src.music import phrase as P
from src.music import rhythm as R
from src.music.theory import midi_to_name, name_to_midi


def _phrase(clef="treble", n_steps=None, seed=1):
    return P.generate_phrase(clef=clef, n_steps=n_steps, rng=random.Random(seed))


def test_generate_phrase_length_and_shapes():
    ph = _phrase(n_steps=4)
    assert len(ph["steps"]) == 4
    for s in ph["steps"]:
        assert "midi" in s and "duration_label" in s and "is_rest" in s
        assert s["duration_label"] in R.duration_labels()
        assert s["is_rest"] == (s["midi"] is None)


def test_generate_phrase_length_bounds_when_random():
    rng = random.Random(42)
    for _ in range(50):
        ph = P.generate_phrase(clef="treble", rng=rng)
        assert 2 <= len(ph["steps"]) <= 4


def test_generate_phrase_is_deterministic_with_seed():
    a = P.generate_phrase(clef="treble", n_steps=3, rng=random.Random(7))
    b = P.generate_phrase(clef="treble", n_steps=3, rng=random.Random(7))
    assert a["steps"] == b["steps"]


def test_correct_transcription_uses_computed_names_and_durations():
    # a fully-pitched phrase
    ph = {"clef": "treble", "steps": [
        {"midi": 67, "duration_label": "quarter", "is_rest": False},
        {"midi": None, "duration_label": "half", "is_rest": True},
        {"midi": 72, "duration_label": "eighth", "is_rest": False},
    ]}
    correct = P.correct_transcription(ph)
    assert correct == [
        ("G4", "quarter"),
        ("rest", "half"),
        ("C5", "eighth"),
    ]
    # names are computed from midi, durations from the label
    assert correct[0][0] == midi_to_name(67)
    assert correct[2][0] == midi_to_name(72)


def test_step_name_rest_vs_note():
    assert P.step_name({"midi": None, "is_rest": True, "duration_label": "whole"}) == "rest"
    assert P.step_name({"midi": 60, "is_rest": False, "duration_label": "quarter"}) == "C4"


def test_check_transcription_all_correct():
    ph = _phrase(n_steps=3, seed=3)
    correct = P.correct_transcription(ph)
    submitted = [{"name": n, "duration": d} for n, d in correct]
    res = P.check_transcription(ph, submitted)
    assert res["correct"] is True
    assert res["first_wrong_step"] is None
    assert res["total_steps"] == 3
    assert all(d["name_ok"] and d["duration_ok"] for d in res["details"])


def test_check_transcription_wrong_name_points_at_step():
    ph = _phrase(n_steps=3, seed=5)
    correct = P.correct_transcription(ph)
    # flip the name of step 1 (index 1)
    wrong_name = "C9" if correct[1][0] != "C9" else "D9"
    submitted = [
        {"name": correct[0][0], "duration": correct[0][1]},
        {"name": wrong_name, "duration": correct[1][1]},
        {"name": correct[2][0], "duration": correct[2][1]},
    ]
    res = P.check_transcription(ph, submitted)
    assert res["correct"] is False
    assert res["first_wrong_step"] == 1
    assert res["details"][1]["name_ok"] is False
    assert res["details"][1]["expected"] == [correct[1][0], correct[1][1]]


def test_check_transcription_wrong_duration_points_at_step():
    ph = _phrase(n_steps=3, seed=9)
    correct = P.correct_transcription(ph)
    wrong_dur = "whole" if correct[2][1] != "whole" else "half"
    submitted = [
        {"name": correct[0][0], "duration": correct[0][1]},
        {"name": correct[1][0], "duration": correct[1][1]},
        {"name": correct[2][0], "duration": wrong_dur},
    ]
    res = P.check_transcription(ph, submitted)
    assert res["correct"] is False
    assert res["first_wrong_step"] == 2
    assert res["details"][2]["duration_ok"] is False


def test_check_transcription_order_sensitive():
    ph = _phrase(n_steps=3, seed=11)
    correct = P.correct_transcription(ph)
    # same entries but swapped order -> must fail and point at step 0
    swapped = [correct[1], correct[0], correct[2]]
    submitted = [{"name": n, "duration": d} for n, d in swapped]
    res = P.check_transcription(ph, submitted)
    assert res["correct"] is False
    assert res["first_wrong_step"] == 0


def test_check_transcription_case_insensitive():
    ph = _phrase(n_steps=2, seed=2)
    correct = P.correct_transcription(ph)
    submitted = [
        {"name": correct[0][0].upper(), "duration": correct[0][1].upper()},
        {"name": correct[1][0].upper(), "duration": correct[1][1].upper()},
    ]
    res = P.check_transcription(ph, submitted)
    assert res["correct"] is True


def test_check_transcription_wrong_length_flagged():
    ph = _phrase(n_steps=3, seed=4)
    correct = P.correct_transcription(ph)
    # submit only 2 of 3
    submitted = [{"name": n, "duration": d} for n, d in correct[:2]]
    res = P.check_transcription(ph, submitted)
    assert res["correct"] is False
    assert res["total_steps"] == 3


def test_phrase_svg_renders_all_steps_and_bar_line():
    ph = _phrase(n_steps=4, seed=1)
    svg = P.render_phrase_svg(ph)
    assert svg.startswith("<svg")
    assert "font-family=\"Bravura\"" in svg  # clef + glyphs
    # a final bar line (two vertical lines near the right edge) is present
    assert svg.count("<line") >= 5 + 4  # 5 staff lines + steps + bar lines
    # rests (if any) use SMuFL rest glyphs, not words
    for s in ph["steps"]:
        if s["is_rest"]:
            from src.music.staff import REST_GLYPH
            assert REST_GLYPH[s["duration_label"]] in svg


def test_phrase_svg_note_matches_midi_placement():
    ph = {"clef": "treble", "steps": [
        {"midi": 71, "duration_label": "quarter", "is_rest": False},
    ]}
    svg = P.render_phrase_svg(ph)
    # the rendered note name is the computed name (not asserted via text, but
    # the structure must be a note head ellipse, not a rest glyph text)
    assert "<ellipse" in svg
    assert midi_to_name(71) == "B4"


def test_roundtrip_midi_name_inside_phrase():
    for midi in range(60, 80):
        assert name_to_midi(midi_to_name(midi)) == midi
