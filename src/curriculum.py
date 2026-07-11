"""Curriculum definition — the set of topics the tutor can drill (Phase 2).

This module is the single source of truth for *what* can be drilled and how
each topic is addressed (its id, type, and the candidate items the spaced-
repetition scheduler picks from). Keep it pure (no DB, no LLM) so the
dashboard, the suggestion engine, and the drill selector all agree.
"""

from __future__ import annotations

from .music.rhythm import DURATIONS
from .music.theory import natural_names_in_clef


def topic_blocks(clefs: list[str] | None = None) -> dict[str, dict]:
    """Return the curriculum keyed by topic id.

    Each value describes a drillable topic:
        id, label, type ("note" | "rhythm"), clefs, items (candidate item
        ids the scheduler draws from), goal (human description).
    """
    clefs = clefs or ["treble", "bass"]
    blocks: dict[str, dict] = {}

    for clef in clefs:
        if clef not in ("treble", "bass"):
            continue
        items = [f"{clef}:{n}" for n in natural_names_in_clef(clef)]
        blocks[f"note-{clef}"] = {
            "id": f"note-{clef}",
            "label": f"Note naming — {clef} clef",
            "type": "note",
            "clefs": [clef],
            "items": items,
            "goal": f"Name every natural note on the {clef} staff from sight.",
        }

    rhythm_items = [f"rhythm:{label}" for label in DURATIONS]
    blocks["rhythm"] = {
        "id": "rhythm",
        "label": "Rhythm / duration naming",
        "type": "rhythm",
        "clefs": clefs,
        "items": rhythm_items,
        "goal": "Name note & rest durations (whole → sixteenth).",
    }

    # Phase 3: sight-reading / transcription — one scheduling item for the
    # whole-phrase skill (per-step correctness is internal to src.music.phrase).
    blocks["phrase"] = {
        "id": "phrase",
        "label": "Sight-reading & transcription",
        "type": "phrase",
        "clefs": clefs,
        "items": ["phrase"],
        "goal": ("Transcribe a short notated phrase — note name + duration per "
                 "step, in order."),
    }
    # Phase 4: writing notation (dictation) — melody + rhythm each one item.
    blocks["melody"] = {
        "id": "melody",
        "label": "Melody dictation (write the notes)",
        "type": "melody",
        "clefs": clefs,
        "items": ["melody"],
        "goal": ("Listen to a short melodic line with a metronome pulse, then "
                 "place each note's pitch + duration on the staff."),
    }
    blocks["rhythm-dictation"] = {
        "id": "rhythm-dictation",
        "label": "Rhythm dictation (write the durations)",
        "type": "rhythm-dictation",
        "clefs": clefs,
        "items": ["rhythm-dictation"],
        "goal": ("Listen to a rhythm pattern with a metronome pulse, then "
                 "place each duration (and rest) on the step grid."),
    }
    return blocks


def topic_order() -> list[str]:
    """A sensible learning order across the curriculum (used by /suggest)."""
    return ["note-treble", "note-bass", "rhythm", "phrase", "melody", "rhythm-dictation"]


def item_topic(item_id: str) -> str | None:
    """Map an item id back to the topic block id it belongs to."""
    for tid, blk in topic_blocks().items():
        if item_id in blk["items"]:
            return tid
    return None
