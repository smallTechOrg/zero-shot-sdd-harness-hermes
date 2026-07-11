# Capability: Deterministic Note Naming

## What It Does
Renders a single note on a staff and verifies the student's spoken/clicked name against the **computed** pitch name (MIDI → name), independent of any LLM.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| exercise_id | str | backend-generated | yes |
| student_answer | str (note name, e.g. "G4") | UI click/input | yes |

## Outputs
| Output | Type | Destination |
| correct | bool | UI |
| computed_name | str | UI (revealed on miss) |
| hint | str | UI + spoken |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| none | — | — |

## Business Rules
- The correct name is **always** derived from the rendered MIDI pitch via `music.theory` — never from the LLM.
- Answer comparison is case-insensitive and ignores whitespace; octave is required.
- A miss returns a computed hint (nearest staff-line/space counting from the clef) and allows exactly one retry before revealing.

## Success Criteria
- [ ] A test proves an exercise's `correct_name` equals `midi_to_name(rendered_midi)` and is **independent** of any LLM output.
- [ ] Wrong answer → `correct=false` + non-empty `hint`; correct answer → `correct=true`.
