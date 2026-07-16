# Agent — CCTNS Analyst (LangGraph)

> Required because LangGraph is in use. An incomplete graph is a CRITICAL
> BLOCKER.

## Pattern

State machine (linear with one self-correction retry on SQL validation
failure). Concatenation of pattern #22 (LLM-Generated Code Execution) and the
default ReAct loop (catalogued at `harness/patterns/agentic-ai.md`).

## LLM per node

| Node            | Provider | Model              | Why                                  |
|-----------------|----------|--------------------|--------------------------------------|
| `nl_to_sql`     | Gemini   | `gemini-2.5-flash` | low-latency SQL drafting             |
| `summarize_answer` | Gemini | `gemini-2.5-flash` | short prose over an aggregate result |

All env-configurable via `APP_LLM_MODEL`. Secrets read by presence only via
`Settings.gemini_api_key: SecretStr`.

## State

```python
class AgentState(TypedDict, total=False):
    request_id: str       # uuid; threaded into logs
    question: str         # raw user question (length ≤ 2000)
    sql: str | None       # drafted SELECT (mirrors cctns_mirror.* only)
    sql_attempts: int     # incremented on retry; capped at 2
    columns: list[str]    # column names returned by executor
    rows: list[tuple]     # bounded result ≤ row_cap
    row_count: int        # len(rows) after cap trim
    error: str | None     # populated on pipeline failure
    latency_ms: int       # wall time from request to finalise
    answer: str | None    # short prose summary (final deliverable)
```

## Nodes

| Node              | Purpose                                                                              |
|-------------------|--------------------------------------------------------------------------------------|
| `nl_to_sql`       | LLM drafts a `SELECT` against `cctns_mirror` schema only (system prompt = schema).   |
| `execute_sql`     | Run via `CctnsMirror` with `row_cap=1000` and `statement_timeout=10 s`.               |
| `validate_result` | Detect empty result / schema mismatch / disallowed statements; on fail, bump attempts.|
| `summarize_answer`| LLM turns the (≤1000) rows + question into ≤ 6-sentence prose; numeric where useful.  |
| `finalize`        | Persist `AnswerRun` to SQLite; emit JSON log; mark complete.                         |
| `handle_error`    | Stuck-terminal node that records the error and emits the error JSON.                 |

## Edges

```
                     Q
                     ▼
                nl_to_sql  ─────────────────────►  handle_error (on LLM/protocol error)
                     │                                          │
                     ▼                                          ▼
                execute_sql  ──► validate_result ──► summarize_answer ──► finalize (END)
                     │              │   retry-once       │
                     ▼              ▼                   ▼
                execute_sql  ◄─── if attempts<2
                     │
                     ▼ (still failing)
                 handle_error ──► (END)
```

Conditions are in `src/cctns_analyst/graph/edges.py`:
- `after_nl_to_sql`: empty `sql` ⇒ `handle_error`, else `execute_sql`.
- `after_execute_sql`: SQLAlchemy / pyodbc error ⇒ `handle_error`, else
  `validate_result`.
- `after_validate`: invalid *and* `sql_attempts < 2` ⇒ bump attempts, return to
  `nl_to_sql`. Valid ⇒ `summarize_answer`. Empty result + attempts ≥ 2 ⇒
  `summarize_answer` (the answer should say "no rows match").
- `after_summarize`: `summarize_answer` failed ⇒ `handle_error`, else
  `finalize`.

## Memory

Stateless across requests in Phase 1. Phase 2 introduces conversation memory:
sessions and turns stored in SQLite (`Session`, `Turn` tables); graph state
hydrated from prior turns on each request. Not implemented here.

## Human-in-the-loop

None in Phase 1. Phase 3 may add a low-confidence review gate for write-style
queries — not in scope for this build.

## Error handling

| Level | Behaviour                                                       |
|-------|------------------------------------------------------------------|
| LLM   | provider 4xx/5xx ⇒ graph captures in `state["error"]` ⇒ finalize records `status=failed` |
| Tool  | pyodbc transient / row-cap exceeded ⇒ graph captures same ⇒ error template (no HTTPException for UI) |
| DB    | SQLite write failure ⇒ log ERROR; UI continues with degraded UX |

## Concurrency

- One LLM call at a time per request (sequential node execution).
- Multiple concurrent user requests run independently, each in its own session.
- The mirror's executor creates a fresh SQLAlchemy `Connection` per request
  and closes it deterministically in a `try/finally` so a long-running
  statement cannot block another.

## Graph assembly (pseudocode, ≤ 60 lines)

```python
# src/cctns_analyst/graph/agent.py
from langgraph.graph import StateGraph, END
from cctns_analyst.graph.state import AgentState
from cctns_analyst.graph.nodes import (
    nl_to_sql, execute_sql, validate_result,
    summarize_answer, finalize, handle_error,
)
from cctns_analyst.graph.edges import (
    after_nl_to_sql, after_execute_sql, after_validate, after_summarize,
)

def build() -> Any:
    g = StateGraph(AgentState)
    g.add_node("nl_to_sql",         nl_to_sql)
    g.add_node("execute_sql",       execute_sql)
    g.add_node("validate_result",   validate_result)
    g.add_node("summarize_answer",  summarize_answer)
    g.add_node("finalize",          finalize)
    g.add_node("handle_error",      handle_error)
    g.set_entry_point("nl_to_sql")
    g.add_conditional_edges(
        "nl_to_sql", after_nl_to_sql,
        {"execute_sql": "execute_sql", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "execute_sql", after_execute_sql,
        {"validate_result": "validate_result", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "validate_result", after_validate,
        {"nl_to_sql": "nl_to_sql", "summarize_answer": "summarize_answer"},
    )
    g.add_conditional_edges(
        "summarize_answer", after_summarize,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()
```

Single compiled instance is built once per process in `runner.py`.
