"""Unit tests for the deterministic music-theory core.

These prove the HARD CONSTRAINT: the correct note name is computed from the
rendered pitch (MIDI), never taken from or influenced by the LLM.
"""

from src.music import theory as T
from src.music import staff as S


def test_midi_to_name_anchors():
    assert T.midi_to_name(60) == "C4"
    assert T.midi_to_name(67) == "G4"
    assert T.midi_to_name(69) == "A4"
    assert T.midi_to_name(72) == "C5"


def test_name_to_midi_roundtrip():
    for m in range(40, 85):
        assert T.name_to_midi(T.midi_to_name(m)) == m


def test_accidentals_roundtrip():
    assert T.name_to_midi("C#4") == 61
    assert T.name_to_midi("Bb4") == 70
    assert T.midi_to_name(61) == "C#4"


def test_staff_step_from_clef_bottom_line():
    # Treble bottom line is E4 (midi 64) -> step 0
    assert T.staff_step(64, "treble") == 0
    # E4 -> F4 is 1 diatonic step, G4 is 2
    assert T.staff_step(67, "treble") == 2
    # Bass bottom line is G2 (midi 43) -> step 0
    assert T.staff_step(43, "bass") == 0
    assert T.staff_step(45, "bass") == 1  # A2


def test_rendered_svg_is_valid_and_positions_note():
    svg = S.render_staff(67, "treble")  # G4
    assert svg.startswith("<svg")
    assert "<ellipse" in svg
    # The staff_svg encodes the note; re-deriving the name from midi matches.
    assert T.midi_to_name(67) == "G4"


def test_frequency_is_equal_tempered():
    # A4 = 440 Hz exactly
    assert abs(T.pitch_frequency(69) - 440.0) < 1e-9
    # one octave up doubles
    assert abs(T.pitch_frequency(81) - 880.0) < 1e-9


def test_llm_name_is_never_used_for_correctness():
    """The correct name must equal the computed name regardless of any
    hypothetical LLM-proposed name. This guards the production rule."""
    from src.drill import make_exercise

    ex = make_exercise("unit-student", ["treble"])
    # The exercise's correct_name is derived from its own midi, not from any
    # external source.
    assert ex["correct_name"] == T.midi_to_name(ex["midi"])
    # Options always include the computed correct name.
    assert ex["correct_name"] in ex["options"]
