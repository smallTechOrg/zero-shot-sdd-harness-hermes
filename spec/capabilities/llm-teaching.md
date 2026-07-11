# Capability: LLM Teaching Text (one call per set)

## What It Does
Calls Gemini **once per drill set** to produce teaching text: a short explanation of the current topic, a hint template, and a tip — surfaced in the UI with full reasoning + token usage. The LLM **never** decides the correct note name.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| topic | str | backend (computed) | yes |
| clef | str | UI | yes |

## Outputs
| Output | Type | Destination |
| teaching_text | str | UI reasoning panel |
| tokens | {prompt, completion, total} | UI reasoning panel |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | generateContent | key missing → deterministic fallback text; log warning |

## Business Rules
- Exactly **one** Gemini call per `start` (drill set), not per note.
- The model may *propose* a note, but the backend **ignores** it and computes its own.
- Token usage is captured and returned.

## Success Criteria
- [ ] `POST /api/exercises/start` makes ≤1 Gemini call and returns `teaching_text` + `tokens`.
- [ ] A live smoke test confirms a real Gemini call returns non-empty teaching text and token counts (key present in `.env`).
