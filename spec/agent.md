# Agent — Auto-Podcaster

> This project uses **no agent framework**. The "agent" is a deterministic, linear three-node
> pipeline orchestrated by the FastAPI API layer. `spec/agent.md` is filled for completeness of the
> spec discipline (the documented agent graph), but the implementation is a plain Python pipeline,
> not a LangGraph/Supervisor graph.

## Agent Architecture Pattern

**Chosen:** Linear pipeline (Single-agent loop equivalent, no branching). Rationale: the
conversation is generated strictly turn-by-turn in speaker order; there are no conditional edges,
checkpoints, or parallel sub-agents. A graph framework would be gold-plating.

| Pattern | Use when |
|---------|----------|
| **Single-agent loop** | One LLM drives a deterministic tool-call loop. No branches, no handoffs. ✅ chosen |
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |
| **Multi-agent** | Specialised sub-agents with distinct roles; orchestrator routes between them. |
| **Supervisor** | One supervisor LLM dispatches to worker agents based on task type. |

---

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| `dialogue-generator` | Google Gemini | `models/gemini-2.5-flash` | Fast, cheap, available for the repo key; good conversational naturalness. |

**Fallback behaviour:** None on the tested path. If Gemini returns an error (auth, rate limit,
network), the SSE stream emits an `error` event and the session is marked `failed`. We surface the
real failure — no offline stub.

**Prompt strategy:** System prompt sets the cast (names + personas) and the topic + turn order; the
user turn requests **one** next speaker line at a time (low `max_output_tokens`), so we can stream
each line to TTS as soon as it arrives. Structured output: plain text per turn (one line per
response), parsed by a small delimiter contract (see `spec/api.md` dialogue format).

---

## Tools & Tool Calling

No tool calling. The only external operations are the Gemini generate call and the edge-tts
`Communicate.stream()` call.

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| (none) | The pipeline calls Gemini + edge-tts directly; no LLM tool use. | | | |

---

## Agent State

```python
class PodcastRun:
    session_id: str          # UUID, set at generate time
    topic: str               # from request
    hosts: list[Host]        # selected personas (name, voice, persona)
    turns: list[Turn]        # accumulated (speaker, text) as produced
    audio_path: str | None   # final mp3 path, set on completion
    status: str              # generating | done | failed
```

---

## Nodes / Steps

### `dialogue-generator`

**Reads:** `topic`, `hosts`, conversation-so-far (`turns`).
**Writes:** one `Turn` (speaker + text) per call.
**LLM call:** yes — Gemini, one next line per request, `max_output_tokens` small (~220).
**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | `generate_content` | fatal → SSE `error` event, session `failed` |

**Behaviour:** Maintains a running transcript. Each call asks Gemini for the next speaker + line,
alternating hosts, keeping the conversation coherent and on-topic. Stops after a configured number
of turns (`MAX_TURNS`, default 12) or when Gemini emits an explicit `[END]` marker.

### `tts`

**Reads:** a `Turn` (speaker + text).
**Writes:** raw audio bytes (mp3 container via edge-tts's native mp3 stream).
**LLM call:** no.
**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| edge-tts | `Communicate(text, voice).stream()` | fatal → SSE `error` event, session `failed` |

**Behaviour:** Maps the speaker to their assigned edge-tts voice, streams audio bytes. Distinct
voice per host.

### `streamer`

**Reads:** audio bytes from `tts`.
**Writes:** SSE `audio` event per chunk; appends bytes to the session's output file.
**LLM call:** no.
**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | update session status / path | logged; session `failed` |

**Behaviour:** Emits `data: {json audio chunk ref}` over SSE; on stream end emits a `done` event
with the download URL and flips session status to `done`.

---

## Graph / Flow Topology

```text
START (generate request)
  │
  ▼
dialogue-generator ──► tts ──► streamer ──(loop until MAX_TURNS or [END])
                                      │
                                      ▼
                                   done (mp3 saved, session=done)
```

**Conditional edges:** none (linear). Loop termination = `MAX_TURNS` reached OR Gemini returns
`[END]`.

---

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| Within a run | in-process `PodcastRun` object | transcript-so-far, audio buffer |
| Across runs | SQLite | finished sessions + audio paths (no cross-run learning) |
| Conversation | the running `turns` list | current episode script |

**Context window management:** Only the recent transcript is sent back to Gemini each turn
(sliding window capped at `MAX_TURNS`), keeping the prompt bounded.

---

## Human-in-the-Loop Checkpoints

None in v1 (one-shot generate).

---

## Error Handling & Recovery

**Node-level:** each node catches its own exceptions; fatal errors emit an SSE `error` event and set
session status `failed`. No silent degradation on the tested path.

**Resume / retry strategy:** none in v1 — a failed run is restarted by the user.

**Partial failure:** if TTS fails mid-episode, the partial audio file is kept and the session is
marked `failed` with an error message surfaced to the UI.

---

## Observability

| Signal | What | Where |
|--------|------|-------|
| Run outcome | status, turns, audio bytes, error | SQLite + stdout structured log |
| LLM calls | model, prompt tokens, latency | structured log (presence only; no key) |
| TTS calls | voice, bytes | structured log |

---

## Concurrency Model

- **Run isolation:** single user, one active generation at a time is expected; the API does not
  enforce a queue but concurrent runs each get their own `session_id` + file.
- **Parallel nodes within a run:** none — strictly sequential (dialogue → tts → stream) so audio
  order matches the conversation.
- **Checkpointing:** none (SQLite row per session is the only durable state).

---

## Pipeline Assembly (`src/graph/stream.py`)

```python
async def run_pipeline(session, topic, hosts):
    async for turn in dialogue.stream_turns(topic, hosts):
        session.turns.append(turn)
        async for chunk in tts.synthesize(turn):
            yield sse_audio(chunk)
            write_to_file(session.audio_path, chunk)
    finalize(session)  # status=done, emit done event
```
