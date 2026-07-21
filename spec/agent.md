# Agent

---

## Agent Architecture Pattern

**Chosen:** Single-agent loop (plan → generate SQL/Python → execute → evaluate → finalize) with a single conditional retry edge (iterate-until-right). Rationale: the task is one deterministic tool-call loop against a data store — no branches, no handoffs, no multi-agent coordination needed. LangGraph gives us checkpointing and retry edges without the overhead of a multi-node graph.

## LLM Provider & Model

| Node | Provider | Model ID | Rationale |
|------|----------|----------|-----------|
| main (plan + generate + evaluate) | On-prem / air-gapped endpoint | Configurable via `AGENT_LLM_MODEL` | Single model drives the entire loop; cheaper than multi-model routing for this task |

**Fallback behaviour:** Retry with exponential backoff on transient API errors (429, 5xx). After 3 retries, surface a clear error to the user and surface the last generated SQL for manual inspection. Degraded mode: cache hit returns previous answer without LLM.

**Prompt strategy:** System prompt in `src/prompts/csv-query.md` (split: system context + tool instructions + few-shot examples). Structured JSON output for SQL/Python generation; final answer is free text.

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `sql_execute` | Execute read-only SQL against active datasource (SQLite or MsSQL) | `sql: str, params: dict` | `{columns, rows, row_count, latency_ms}` | None (read-only) |
| `chart_generate` | Render a matplotlib chart and return base64 PNG | `data: list, chart_type: str, title: str` | `{base64_png, width, height}` | Writes to `./assets/` |
| `report_generate` | Produce PDF or Excel report from result set | `rows, columns, format: "pdf" \| "xlsx"` | `{file_url, file_size}` | Writes to `./assets/` |
| `datasource_info` | Return active datasource schema (tables/columns) | none | `{datasource, tables: [...]}` | None |

**Tool selection strategy:** The main agent decides which tool to call based on its current reasoning step. SQL execution is the default; chart/report tools are invoked only when the user asks for visuals or downloads.

**Tool failure handling:** Each tool catches its own exceptions; fatal errors set `state["error"]` and route to `handle_error` node. Retry logic inside tool wrappers for transient DB errors; no retry on schema/syntax errors.

## Agent State

```python
class AgentState(TypedDict):
    # Identity
    run_id: int
    user_id: str

    # Input
    question: str
    datasource_id: str | None
    uploaded_files: list[str] | None  # Phase 1

    # Pipeline data (populated progressively by nodes)
    plan: list[str] | None
    sql: str | None
    sql_result: dict | None       # columns, rows, row_count
    evaluate_score: float | None
    iteration: int
    max_iterations: int

    # Output
    answer: str | None
    code_display: str | None     # the SQL/Python shown to user
    chart_urls: list[str] | None
    download_urls: list[str] | None

    # Control
    error: str | None
    checkpoint: str | None       # last completed node name
```

## Nodes / Steps

### `node_plan`

**Reads from state:** `question`, `datasource_id`, `uploaded_files`, `user_id`  
**Writes to state:** `plan`  
**LLM call:** Yes — generates a 1–3 step execution plan from the question  
**External calls:** `datasource_info` (to know which tables are available)  
**Behaviour:** Breaks the user's question into a plan: which tables to query, which filters, whether a chart or report is implicitly requested.

### `node_generate_sql`

**Reads from state:** `question`, `plan`, `datasource_id`, `iteration`  
**Writes to state:** `sql`, `code_display`  
**LLM call:** Yes — generates a read-only SQL query (or Python against pandas DataFrames for CSV mode)  
**External calls:** `datasource_info`  
**Behaviour:** Produces an executable read-only query. On MsSQL paths, enforces `WITH (NOLOCK)` hint and avoids DDL/DML.

### `node_execute`

**Reads from state:** `sql`, `datasource_id`  
**Writes to state:** `sql_result`  
**LLM call:** No  
**External calls:** `sql_execute` (SQLite or pyodbc MsSQL)  
**On Failure:** Fatal SQL error → `error`, else log + continue (e.g., empty result is valid)

**Behaviour:** Runs the query. Measures latency. Returns columns, rows, row_count.

### `node_evaluate`

**Reads from state:** `question`, `sql_result`, `answer` (if regenerating)  
**Writes to state:** `evaluate_score`, `checkpoint`  
**LLM call:** Yes — evaluates whether the result answers the question (score 0–1)  
**External calls:** None  

**Behaviour:** If `evaluate_score < 0.8` AND `iteration < max_iterations` → route back to `node_generate_sql`. Else → `node_finalize`.

### `node_chart` *(Phase 2)*

**Reads from state:** `sql_result`, `question`  
**Writes to state:** `chart_urls`  
**LLM call:** Yes — decides chart type and data mapping  
**External calls:** `chart_generate`  

### `node_report` *(Phase 2)*

**Reads from state:** `sql_result`, `question`  
**Writes to state:** `download_urls`  
**LLM call:** Yes — structures the report layout  
**External calls:** `report_generate`  

### `node_finalize`

**Reads from state:** `question`, `sql_result`, `answer`, `chart_urls`, `download_urls`  
**Writes to state:** `checkpoint` = "finalized"  
**LLM call:** Yes — synthesizes NL answer from code + result  
**External calls:** None  

**Behaviour:** Composes the final user-facing answer in clean text with the generated SQL shown below. Appends chart/report links when present. Sets `checkpoint` and completes the run.

### `node_handle_error`

**Reads from state:** `run_id`, `error`  
**Writes to state:** none (terminal node)  
**External calls:** DB update (run status → failed, error_message, completed_at)  
**Behaviour:** Logs the error with full context. Terminates graph.

## Graph / Flow Topology

```
                       ┌─────────────────────┐
                       │        START         │
                       └──────────┬──────────┘
                                  ▼
                           node_plan
                                  │
                                  ▼
                         node_generate_sql
                                  │
                                  ▼
                           node_execute
                                  │
                                  ▼
                           node_evaluate
                            │            │
                   score < 0.8          score >= 0.8
                   and retries           or timeout
                      left?                │
                    ┌─────┘                 ▼
                    │              node_finalize
                    ▼                    │
           (back to generate)             ▼
                                   handle_error (on fatal error)
                                             │
                                             ▼
                                            END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `node_plan` | error set during planning | `handle_error` |
| `node_generate_sql` | error after max retries | `handle_error` |
| `node_execute` | fatal SQL error | `handle_error` |
| `node_evaluate` | score >= 0.8 OR iteration >= max_iterations | `node_finalize` |
| `node_evaluate` | score < 0.8 AND iteration < max_iterations | `node_generate_sql` |
| `node_finalize` | error set during synthesis | `handle_error` |

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| Within a run | LangGraph state | All in-progress data (plan, SQL, results, iteration count) |
| Across runs | SQLite (session + dataset tables) | Session history, dataset metadata, query audit trail |
| Conversation | Session history table (last N turns) | Prior questions + answers for multi-turn context |

**Context window management:** Dataset metadata (schema + row counts + sample) is pre-computed and injected; full CSV content is never inlined. MsSQL queries are pushed to the DB — only compact result sets flow back.

## Human-in-the-Loop Checkpoints

**Assumed:** None for Phase 1. Phase 2 may add optional HITL for MsSQL write-sensitive validation if needed by UP Police policy.

## Error Handling & Recovery

**Node-level:** Each node catches its own exceptions; fatal errors set `state["error"]`. `node_evaluate` and `node_execute` treat non-fatal errors (empty results, evaluate below threshold) as control-flow signals, not exceptions.

**Graph-level (`handle_error` node):**
- Reads: `state.error`, `state.run_id`
- Updates DB: run status → "failed", `error_message`, `completed_at`
- Logs error with `run_id` context
- Terminates graph

**Resume / retry strategy:** LangGraph checkpointing (SqliteSaver) records every completed node. A failed run can be resumed manually via the root session; API endpoint exposed in Phase 2 for authenticated retry.

**Partial failure:** Non-critical tool failures (e.g., chart generation fails) degrade gracefully: the NL answer + SQL are returned, chart section is omitted, and the audit log records the partial outcome.

## Observability

| Signal | What | Where |
|--------|------|-------|
| Trace | One trace per run, one span per node | Structured log (JSON) via structlog |
| LLM calls | Prompt tokens, completion tokens, latency, model | Structured log per call |
| Tool calls | Tool name, inputs, success/error, latency | Structured log |
| Run outcome | Status, total duration, error if any, row_count | DB (runs table) + structured log |

## Concurrency Model

- **Run isolation:** One run per session ID (serial). API returns 409 if session is busy.
- **Parallel nodes within a run:** Phase 1 is sequential (plan → generate → execute → evaluate). Phase 2 adds optional parallel chart+report generation after `node_finalize` if both are requested.
- **Checkpointing:** SqliteSaver — required for iterate-until-right and for HITL-ready resume.

## Graph Assembly (`src/graph/runner.py`)

```python
from langgraph.graph import StateGraph, END
from src.graph.nodes import (
    node_plan,
    node_generate_sql,
    node_execute,
    node_evaluate,
    node_finalize,
    node_handle_error,
)

graph = StateGraph(AgentState)

graph.add_node("plan", node_plan)
graph.add_node("generate_sql", node_generate_sql)
graph.add_node("execute", node_execute)
graph.add_node("evaluate", node_evaluate)
graph.add_node("finalize", node_finalize)
graph.add_node("handle_error", node_handle_error)

graph.set_entry_point("plan")
graph.add_edge("plan", "generate_sql")
graph.add_edge("generate_sql", "execute")
graph.add_edge("execute", "evaluate")

graph.add_conditional_edges(
    "evaluate",
    lambda s: (
        "handle_error"
        if s.get("error")
        else (
            "finalize"
            if s.get("evaluate_score", 0) >= 0.8
            or s.get("iteration", 0) >= s.get("max_iterations", 3)
            else "generate_sql"
        )
    ),
)

graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

compiled_graph = graph.compile(checkpointer=SqliteSaver.from_conn_string(DB_URL))
```
