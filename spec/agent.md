# Agent — `scaffold-agent`

> Phase 1 keeps the agent surface intentionally tiny. Phase 2 replaces the inner node with a real LangGraph graph.

---

## Agent Architecture Pattern

**Chosen:** Single-agent loop (Phase 1) → Graph (Phase 2).

Rationale: Phase 1 must ship a working scaffold kit fast; a single deterministic agent node keeps dependencies small.
Phase 2 can introduce LangGraph without changing the API contract.

## LLM Provider & Model

| Node | Provider | Model ID | Rationale |
|-------|----------|----------|-----------|
| agent_node | Optional | gpt-4o-mini or claude-haiku-3-5-20240307 | Live responses when `LLM_API_KEY` is set; otherwise degraded to stub path. |

**Fallback behaviour:**
- Missing/invalid key → stub path. No retries, no delays.
- Network failure → 500 with message "LLM call failed"; logged with traceback.

**Prompt strategy:**
- Phase 1: static prompt template `You are a helpful assistant.` with user message appended.
- Phase 2: replace with system prompt from `prompts/transform.md` placeholder.

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| echo | Returns stub reply echoing user input. | messages | string | None |
| llm_call | Calls configured OpenAI-compatible endpoint. | messages, model | string | Network call |

**Tool selection strategy:**
- Phase 1: if `LLM_API_KEY` is set, always use `llm_call`.

**Tool failure handling:**
- On failure: raise 500 with "LLM call failed".

## Agent State

```python
class AgentState(TypedDict):
    run_id: int                # set at entry
    messages: list             # full conversation so far
    reply: str | None          # final assistant message
    error: str | None          # fatal error, if any
```

## Nodes / Steps

### `agent_node`

**Reads from state:** `messages`
**Writes to state:** `reply`, `error`
**LLM call:** yes, if configured; uses a small static prompt.
**External calls:** OpenAI-compatible or Anthropic-compatible client.

**Behaviour:**
- Build prompt from the last user message.
- If a live provider is configured, return the model output.
- Otherwise return a string prefixed with `[stub]` plus the user message.

### `handle_error`

**Reads from state:** `error`
**Writes to state:** sets `reply` to an error string.
**Behaviour:** terminate graph with "Something went wrong."

## Graph / Flow Topology

```
START → agent_node → END
  │
  └─(error)→ handle_error → END
```

Phase 2 introduces LangGraph with this ASCII skeleton ready to wire into the backend.

## Memory & Context

- Within a run: full messages list in memory.
- Across runs: none in Phase 1 (database receipt is optional).

## Error Handling & Recovery

- Node-level: try/except around LLM call; sets `error`.
- Graph-level: `handle_error` node sets assistant-facing message and returns.

## Observability

- Structured log on every `/api/chat` request: `run_id`, `status`, `latency_ms`.
- Errors logged with full traceback.

## Concurrency Model

- One FastAPI worker per process; SQLite allows one writer at a time, which is sufficient for local dev.
- Threaded `ProcessPoolExecutor` may be used for blocking LLM calls in production.
