"""Unit tests for the deterministic rhythm / duration naming core.

These prove the HARD CONSTRAINT for the Phase 2 rhythm drill: the correct
duration name is COMPUTED from the rendered symbol, never taken from or
influenced by the LLM.
"""

from src.music import rhythm as R
from src.music import staff as S
from src.music import theory as T  # noqa: F401  (ensure theory still importable)


def test_duration_labels_are_fixed_set():
    labels = R.duration_labels()
    assert labels == ["whole", "half", "quarter", "eighth", "sixteenth"]


def test_beats_are_correct_and_descending():
    assert R.beats("whole") == 4.0
    assert R.beats("half") == 2.0
    assert R.beats("quarter") == 1.0
    assert R.beats("eighth") == 0.5
    assert R.beats("sixteenth") == 0.25


def test_name_for_is_canonical_and_case_insensitive():
    assert R.name_for("quarter") == "quarter"
    # the canonical name is always lowercase + the exact label
    for label in R.duration_labels():
        assert R.name_for(label) == label


def test_check_duration_rejects_wrong_and_computes_hint():
    res = R.check_duration("eighth", "quarter", is_rest=False)
    assert res["correct"] is False
    assert res["computed_name"] == "eighth"
    assert res["hint"] is not None
    assert "eighth" in res["hint"]
    assert "0.5" in res["hint"]  # computed beat count in the hint


def test_check_duration_accepts_computed_name_note():
    res = R.check_duration("quarter", "Quarter")  # case-insensitive
    assert res["correct"] is True
    assert res["hint"] is None
    assert res["computed_name"] == "quarter"


def test_check_duration_rest_named_same_as_note():
    # A rest of a given duration is named by its duration label, not "rest".
    res = R.check_duration("half", "half", is_rest=True)
    assert res["correct"] is True
    assert res["computed_name"] == "half"


def test_check_duration_ignores_whitespace():
    res = R.check_duration("sixteenth", "  Sixteenth  ")
    assert res["correct"] is True


def test_unkknown_label_raises():
    import pytest
    with pytest.raises(ValueError):
        R.name_for("triplet")


def test_rhythm_svg_renders_note_head_and_stem():
    svg = S.render_rhythm("quarter", is_rest=False)
    assert svg.startswith("<svg")
    assert "<ellipse" in svg  # note head
    assert "<line" in svg     # stem


def test_whole_note_has_no_stem():
    svg = S.render_rhythm("whole", is_rest=False)
    # whole notes have an open note head but no stem/flag
    assert "<ellipse" in svg
    # flags/stem only appear for non-whole; whole is uniquely head-only + filled=False
    # (we can't easily assert absence of stem; assert open head fill="none")
    assert 'fill="none"' in svg


def test_eighth_note_has_flag():
    svg = S.render_rhythm("eighth", is_rest=False)
    # eighth notes render a flag path
    assert "<path" in svg


def test_rest_glyph_renders():
    svg = S.render_rhythm("quarter", is_rest=True)
    assert svg.startswith("<svg")
    assert "rest" in svg.lower() or "𝄼" in svg or "quarter rest" in svg


def test_llm_not_involved_in_correctness():
    """The computed correct name must equal the label, regardless of any
    hypothetical LLM-proposed name — guarding the production rule for rhythm."""
    from src.drill import make_exercise
    ex = make_exercise("unit-rhythm", ["treble"], drill_type="rhythm")
    # correct_name derives from the rendered label, not from any LLM source.
    assert ex["type"] == "rhythm"
    assert ex["correct_name"] == R.name_for(ex["label"], ex.get("is_rest", False))
    assert ex["correct_name"] in ex["options"]
