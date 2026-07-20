# Agent Graph

Pattern: **Plan → Query → Execute → Explain** with retry-on-error and a single clarifying-round sub-loop.

Source: `harness/patterns/agentic-ai.md` — the Plan–Execute–Check pattern, extended with an explicit Clarify step to keep the human in the loop on DB ambiguities without stalling the pipeline.

---

## Graph Pattern

```
          ┌─────────────┐
  start ──│    plan     │─── plan_text
          └──────┬──────┘
                 │
          ┌──────▼──────┐
          │   query     │─── generated_code, code_language
          └──────┬──────┘
                 │
          ┌──────▼─────────┐
          │  execute       │─── rows, row_count, latency_ms
          └──────┬─────────┘
                 │
          ┌──────▼──────┐
          │   explain   │─── nl_answer, chart_spec, kpis, result_hash
          └──────┬──────┘
                 │
               finalize
              (status=completed)

Any node → on error → handle_error (status=failed) OR handle_clarify (one clarifying prompt, retry once)
```

---

## State

Type: dict keyed by strings (LangGraph `StateGraph` with `add` reducer on list-typed values).

| Key | Type | Description |
|-----|------|-------------|
| `run_id` | str | The run row primary key (set once at graph entry) |
| `session_id` | str | Session ID for CSV metadata + conversation history caching |
| `input_text` | str | The user's latest question |
| `conversation_history` | list[{role: user\|assistant, content: str}] | Prior Q&A in this session; fed to every node as additional context |
| `instruction` | str | Alias for input_text in the current run |
| `plan_text` | str \| None | Structured plan from the plan node |
| `generated_code` | str \| None | SQL or Python from the query node |
| `code_language` | str \| None | `"sql"` or `"python"` |
| `rows` | list[dict] \| None | Result rows from the execute node |
| `row_count` | int \| None | Filled by execute node |
| `latency_ms` | float \| None | Filled by execute node |
| `nl_answer` | str \| None | Final natural-language explanation |
| `chart_spec` | dict \| None | `{type, x, y, title, color_by?}` |
| `kpis` | list[dict] \| None | `[{label, value, unit?}, ...]` |
| `result_hash` | str \| None | SHA-256 of row payload bytes |
| `source` | str \| None | `duckdb` \| `mssql` \| `mssql-cache` |
| `error` | str \| None | Error message on failure; cleared on retry |
| `status` | str | `pending` → `running` → `completed` \| `failed` \| `clarifying` |
| `clarify_prompt` | str \| None | A clarifying question for the user, set by `handle_clarify` |
| `cache_hit` | bool \| None | True when served from msql-cache |

---

## Nodes

### `plan(state) -> partial_state`

Input: `input_text` + `conversation_history` + schema summary for the current session.

Behaviour:
- Calls LLM with a structured plan prompt (see `src/prompts/plan.md`) that logs all tables, columns, and types known for this session.
- Outputs a plan_text JSON string listing: tables, columns, filters, aggregations, joins, sort, limit.
- Never executes any query.

Failure modes → `handle_error` with `error_message` set.

Output: `{plan_text, error, status}`.

---

### `query(state) -> partial_state`

Input: `plan_text` + `conversation_history` + `plan_text`.

Behaviour:
- Calls LLM with a plan-to-code prompt (see `src/prompts/query.md`).
- Generates **exactly one** executable target — DuckDB SQL (preferred) or Python+pandas (allowed for non-standard string ops or date functions not supported by DuckDB; the node must explicitly flag `code_language=python` and the execution node must use the runner service's Python runner).
- Validates the generated SQL syntactically in-process via DuckDB's `.execute()` before returning; on syntax error, retries once with the error appended to the prompt.

Output: `{generated_code, code_language, error, status}`.

---

### `execute(state) -> partial_state`

Input: `generated_code` + `code_language` + `session_id` + `source` flag.

Behaviour:
- Phase 1: executes on the session's DuckDB via `src/services/query_exec.py` (`execute_on_duckdb`).
- Phase 2: `execute_on_mssql` first checks DuckDB cache (materialized view per table-set); on hit, returns cache rows with `cache_hit=True`; on miss, opens a `SET TRANSACTION READ ONLY` pyodbc connection, runs the query, writes the result set to the cache file, returns rows with `cache_hit=False`.
- Captures `row_count`, `latency_ms` (wall-clock per query).
- Result is JSON-serialized deterministically (sorted keys, null-safe); `result_hash` = `sha256` of the UTF-8 bytes.

Output: `{rows, row_count, latency_ms, result_hash, source, cache_hit, error, status}`.

---

### `explain(state) -> partial_state`

Input: `rows`, `row_count`, `input_text`, `conversation_history`, `plan_text`.

Behaviour:
- Calls LLM with `src/prompts/explain.md`: summarise rows, select chart spec (bar / line / pie — pick only one unless rows unambiguously support a stacked/grouped structure, in which case a grouped bar is acceptable), compute 3–6 dashboard KPIs from the rows (count, sum, average, date range, distinct values, time-trend direction), and emit a result_hash echo.
- Always include the raw row_count and latency_ms verbatim in the answer block for audit.

Output: `{nl_answer, chart_spec, kpis, error, status}`.

---

### `finalize(state) -> partial_state`

Merges executor output into RunRow: status=completed, output_text (json blob with nl_answer, chart_spec, kpis, audit_block), provider, model. Zero logic — just a terminal state merge.

Output: `{status: "completed"}`.

---

### `handle_error(state) -> partial_state`

Routes to `status="failed"`. Preserves `error`, `error_message`, `generated_code` (partial if available from the failing node), `plan_text` (if present), and `latency_ms` if execute started. Marks the run failed in DB via `update_run(run_id, status="failed", error_message=...)`.

Output: `{status: "failed"}`.

---

### `handle_clarify(state) -> partial_state`

One-shot sub-loop: emits a user-facing clarifying question (e.g. "Column `PS` not found — did you mean `ps_name` or `police_station`?") and routes the run back to the user without failing. The frontend re-submits the original question prepended with the user's reply; the graph re-enters at `plan` with the full context. Maximum one clarification round per step; beyond that the run fails gracefully.

Output: `{status: "clarifying", clarify_prompt, error: None}`.

---

## Concurrency

Each run is a single in-process LangGraph `invoke`. No parallel execution within a single run. Multiple concurrent runs share the same session's DuckDB but do not share a transaction — DuckDB handles MVCC internally.

---

## Assembly (runner.py pseudocode)

```python
from langgraph.graph import StateGraph, END
from src.graph.nodes import plan, query, execute, explain, finalize, handle_error, handle_clarify

graph = StateGraph(AgentState)
graph.add_node("plan", plan)
graph.add_node("query", query)
graph.add_node("execute", execute)
graph.add_node("explain", explain)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)
graph.add_node("handle_clarify", handle_clarify)

graph.add_edge("plan", "query")
graph.add_edge("query", "execute")
graph.add_edge("execute", "explain")
graph.add_edge("explain", "finalize")
graph.add_edge("finalize", END)

def route_after(state):
    if state.get("status") == "clarifying":
        return "handle_clarify"
    if state.get("error"):
        return "handle_error"
    # else continue flow
    return ...

graph.add_conditional_edges("plan", route_after, {"handle_clarify": "handle_clarify", "handle_error": "handle_error", "query": "query"})
# same pattern for query and execute

agentic_ai = graph.compile()
```

The existing `src/graph/agent.py` and `src/graph/edges.py` are updated in place to implement this assembly.
