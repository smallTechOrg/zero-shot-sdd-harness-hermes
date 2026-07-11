# Agent

> This project has **no agent framework**. It is a deterministic FastAPI service that makes a **single Gemini call per drill set** for teaching text. The harness boilerplate's LangGraph skeleton is deliberately **not used** — the brief specifies a deterministic correctness core (computed note names) with the LLM confined to explanations/hints. An agent graph would add untested nondeterminism to the one thing that must be correct (the note name).

Per `harness/agents/spec-writer.md`, delete this file when no framework is used. The correctness-critical logic is a **pure deterministic function**, which is stronger than any graph for this use case.

---

## Why No Graph

| Concern | Graph approach | Chosen approach |
|---------|----------------|-----------------|
| Correct note name | LLM node could guess wrong | `midi_to_name()` pure function — 100% deterministic |
| Cost | risk of per-note calls | Exactly 1 Gemini call per `start` |
| Testability | mock the model | assert computed name == MIDI mapping, no model needed for correctness |

## LLM Integration (one call per set)

- **Call site:** `POST /api/exercises/start` → `llm.generate_teaching(topic, clef)`.
- **Model:** Gemini `gemini-2.5-flash` (configurable via `AGENT_LLM_MODEL`).
- **Input:** the *computed* topic (e.g. "treble clef, note G4") — the model explains, it does not name.
- **Output:** teaching text + token usage (`usage_metadata`).
- **Fallback:** if the key is absent/unreachable, return a deterministic static teaching string and `used_fallback=true`; exercises are unaffected.
- **Prompt strategy:** system prompt = "you are a patient music-theory tutor; explain the topic in ≤3 sentences; never state the answer as fact to be graded." Structured JSON output requested.

## Observability
- Structured stdout logging for each request (timestamp, path, latency ms, error if any).
- Gemini call logged with token counts and `used_fallback` flag.
- No LangSmith (no LangGraph). This satisfies the "structured request/response logging" observability requirement from day one.
