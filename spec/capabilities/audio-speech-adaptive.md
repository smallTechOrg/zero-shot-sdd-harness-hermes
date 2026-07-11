# Capability: Local Audio Demo

## What It Does
Synthesises the played note as a WAV using an in-process oscillator (no external service), so the student hears the exact pitch that is rendered.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| midi | int | computed exercise pitch | yes |

## Outputs
| Output | Type | Destination |
| audio/wav | binary | UI `<audio>` element |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| none | — | — |

## Business Rules
- Frequency = 440 * 2**((midi-69)/12). A short attack/decay envelope, ~0.8s, 16-bit PCM, 22050 Hz.
- No network, no API key, no ffmpeg dependency.

## Success Criteria
- [ ] `/api/notes/{id}/audio` returns a valid WAV whose decoded fundamental frequency matches the note within 1%.

# Capability: Spoken Answer & Hint (edge-tts)

## What It Does
Speaks the teaching text / hint using free `edge-tts`.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| text | str | backend (Gemini or computed) | yes |

## Outputs
| Output | Type | Destination |
| audio/mpeg | binary | UI `<audio>` |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| edge-tts | synthesize | 503 → UI shows text |

## Business Rules
- Only teaching text is spoken, never the "correct" answer unless the student asked to reveal.
- Offline → endpoint 503, UI renders the text.

## Success Criteria
- [ ] `/api/notes/{id}/speak` returns audio/mpeg for valid text; 503 when edge-tts unreachable.

# Capability: Adaptive Drill Selection

## What It Does
Picks the next note/exercise using the student's per-topic mastery (private SQLite) — drilling weak spots more often.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| student_id | str | UI | yes |
| clefs | list[str] | UI | yes |

## Outputs
| Output | Type | Destination |
| exercise | object | UI |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | read/write mastery | fatal if DB missing |

## Business Rules
- Lower-mastery topics are sampled with higher probability (weighted).
- Mistakes reduce a topic's mastery; correct answers increase it (simple Leitner-style weight).

## Success Criteria
- [ ] After a wrong answer on note X, the next selection is more likely to be in X's topic than before (statistically, over a run).
- [ ] Mastery persists across requests for the same `student_id`.
