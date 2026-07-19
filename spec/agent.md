# Agent Graph

> Single base ReAct loop. Phase 1 = one shot per question; no retry, no reflection (still real ReAct because the LLM produces the tool call rather than a fixed pipeline).

## Pattern

- **Tool Use (#5)** + **Reasoning (#17)**. One LLM call generates one SQL; the system validates and executes it; the structured result is returned alongside the SQL.
- **Guardrails (#18)** — system prompt forbids DDL/DML; regex validator blocks anything else.
- **Resource-Aware Optimisation (#16)** — `TOP N` push-down; row cap enforced server-side.

The graph is wired in Phase 1 even though most "smart" behaviours are deferred; this is so that Phase 2/3 can extend it (retry, reflection) without reshaping it.

## State

```python
class AgentState(TypedDict, total=False):
    # inputs
    request_id: str
    question: str
    # nl_to_sql outputs
    sql: str | None
    validation_error: str | None
    # execute_sql outputs
    columns: list[str]
    rows: list[tuple]
    row_count: int
    tokens_used: int
    # terminal
    status: str            # "completed" | "failed"
    error: str | None
    latency_ms: int
```

Every field is optional — only nodes that set a key contribute to it.

## Nodes

| Node | Inputs | Outputs | Notes |
|------|--------|---------|-------|
| `nl_to_sql` | `question`, `schema (cached)` | `sql` or `error` | Calls `LLMClient.complete_json`. Validates with `assert_select_only` (regex). |
| `execute_sql` | `sql`, `row_cap`, `timeout` | `columns`, `rows`, `row_count`, `tokens_used` (sets 0 for Phase 1 — Gemini token count is optional) | Runs in pyodbc context manager. |
| `handle_error` | `state.error` | `{status: "failed"}` | Terminal. Surfaces `error` to API. |
| `finalize` | `state.status` | `{status: "completed" if no error else "failed"}` | Terminal. |

## Edges

- `nl_to_sql` → if `sql` empty OR `error` set → `handle_error`; else `execute_sql`.
- `execute_sql` → if `error` set → `handle_error`; else `finalize`.
- `handle_error`/`finalize` → `END`.

```
[nl_to_sql] ──(no sql / error)──▶ [handle_error] ─▶ END
       │
       └──(sql ok)──▶ [execute_sql] ──▶ [finalize] ─▶ END
                │
                └──(error)──▶ [handle_error] ─▶ END
```

## Error handling

- Every node catches `Exception` and returns `{"error": <public message>, "status": "failed"}` instead of raising into the graph. The graph only routes on `error` keys.
- Executor wraps `pyodbc.OperationalError` / `pyodbc.ProgrammingError` and returns them as `error` keys, never raises.

## Concurrency

Single request per graph invocation. No fan-out, no background tasks in Phase 1. Concurrent users would require a process model upgrade (Phase 3+).

## Graph assembly (pseudocode)

```python
g = StateGraph(AgentState)
g.add_node("nl_to_sql", partial(nl_to_sql, llm=llm, schema_provider=mssql_schema))
g.add_node("execute_sql", partial(execute_sql, executor=mssql_executor, row_cap=1000, timeout=15))
g.add_node("handle_error", lambda s: {"status": "failed", "error": s.get("error")})
g.add_node("finalize",    lambda s: {"status": s.get("status") or "completed"})
g.set_entry_point("nl_to_sql")
g.add_conditional_edges("nl_to_sql", after_nl_to_sql, {"execute_sql": "execute_sql", "handle_error": "handle_error"})
g.add_edge("execute_sql", "finalize")
g.add_edge("handle_error", END)
g.add_edge("finalize", END)
return g.compile()
```

## Dependencies (bound at request time)

- `llm` — `LLMClient` wrapping `GeminiProvider`.
- `mssql_schema` — `Callable[[], dict[table, list[col]]]` returned from `mssql.connector.MssqlConnector.describe_schema()`; **cached at startup, NOT per-request**.
- `mssql_executor` — `Callable[[str], tuple[cols, rows, count]]` returned from `mssql.connector.MssqlConnector.execute(sql)`.

## Phase 2/3 hooks

- Retry on validator rejection → add `validate_sql` node + a cycle edge `validate_sql → nl_to_sql (with attempts cap)` — wired in Phase 3.
- Token-aware row cap → `execute_sql` reads `tokens_used` to adjust — wired in Phase 4.
- Multi-turn memory → new `recall_history` node reads from `answer_runs` — wired in Phase 2.
