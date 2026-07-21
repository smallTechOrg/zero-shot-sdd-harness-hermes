# Agent

> **Assumed:** LangGraph graph as defined below; NVIDIA NIM via OpenAI-compatible HTTP for all nodes that call the LLM.
> **Assumed:** one batched LLM call per query artifact; per-line LLM loops are forbidden.

## Agent Architecture Pattern

| Pattern | Use when |
|---------|----------|
| Single-agent loop | One LLM drives a deterministic tool-call loop. No branches, no handoffs. |
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |
| Multi-agent | Specialised sub-agents with distinct roles; orchestrator routes between them. |
| Supervisor | One supervisor LLM dispatches to worker agents based on task type. |
| Human-in-the-loop | Execution pauses at defined checkpoints for user review or approval. |

**Chosen:** **Graph (LangGraph)** — the analyst task is a multi-step pipeline with conditional data-source routing (CSV ingest vs live MsSQL vs cache) and audited state propagation across nodes.

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|--------------|----------|----------|-----------|
| `plan_query` | NVIDIA NIM (OpenAI-compatible) | Environment variable `OPENAI_MODEL`; default resolved by the provider factory. | Low-latency structured planning from the user's natural-language question. |
| `generate_code` | NVIDIA NIM (OpenAI-compatible) | Same as above. | Single batched call to produce SQL/pandas code. |
| `assemble_answer` | NVIDIA NIM (OpenAI-compatible) | Same as above. | Synthesis of results into a narrative answer + follow-ups. |

**Fallback behaviour:** If the NIM endpoint returns 401/429/model_not_found, the node sets `state.error` and the graph routes to `assemble_answer` with a surfaced error message and cached/offline guidance when available. Retry/backoff is handled in `src/llm/providers/base.py` via the existing retry policy.

**Prompt strategy:** Split system/user prompts; structured JSON-mode request when the node emits code; few-shot examples are loaded from `src/prompts/` per capability.

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `csv_ingestor` | Reads uploaded CSV files, infers schema, registers tables in the working SQLite store. | file_id, file_path | table_name, columns, row_count | Creates SQLite tables; writes ingest audit row. |
| `sql_runner` | Executes read-only SQL against the selected data source (SQLite for CSV, MsSQL for live, PostgreSQL for cache). | sql, data_source, row_limit | rows, columns, row_count, latency_ms | Read-only query execution. |
| `cache_reader` | Returns precomputed aggregates from the local cache when live DB is slow or unreachable. | question_hash, table_hint | rows, served_from_cache flag | None. |
| `audit_writer` | Persists a query audit row. | run_id, user_id, question, sql, tables_touched, row_count, latency_ms, token_usage | audit_id | Writes to PostgreSQL audit table. |
| `followup_generator` | Produces suggested follow-up questions and anomaly flags. | question, schema, result_summary | followups, anomaly_flags, sensitive_warning | None. |

**Tool selection strategy:** Each node corresponds to one tool call in the graph; the LLM decides parameters within that node. No free-form multi-tool call loop in Phase 1.

**Tool failure handling:** Node catches exceptions, writes `state.error`, and routes to `assemble_answer` so the user sees a best-guess message with the failed step. Fatal infra failures (DB unreachable) still return a degraded-mode answer with offline guidance.

## Agent State

```python
class AgentState(TypedDict, total=False):
    run_id: int
    user_id: int | None
    question: str
    instruction: str
    data_source: str | None  # "csv" | "live_db" | "cache"
    csv_file_ids: list[int] | None
    schema_summary: str | None
    query_plan: str | None
    generated_code: str | None
    executed_sql: str | None
    executed_rows: list[dict] | None
    executed_columns: list[str] | None
    executed_row_count: int | None
    latency_ms: int | None
    result_table: str | None
    answer_text: str | None
    csv_download_url: str | None
    followups: list[str] | None
    anomaly_flags: list[str] | None
    sensitive_warning: str | None
    tables_touched: list[str] | None
    provider: str | None
    model: str | None
    token_usage: dict | None
    memory_context: str | None
    saved_workspace_id: int | None
    status: str | None
    error: str | None
```

## Nodes / Steps

### `plan_query`

**Reads from state:** `question`, `data_source`, `csv_file_ids`, `schema_summary`

**Writes to state:** `query_plan`, `generated_code`, `executed_sql`, `data_source` (if not already set), `tables_touched`

**LLM call:** Yes — plans the query strategy, chooses data source, selects tables/columns.

**External calls:** `csv_ingestor` if schema is missing; `cache_reader` to check freshness when source is live DB.

**Behaviour:** Converts the natural-language question into a structured plan and, when needed, candidates CSV tables, live DB tables, or cached aggregates. It respects read-only constraints and row-limit policies before any execution.

### `generate_code`

**Reads from state:** `query_plan`, `schema_summary`, `data_source`

**Writes to state:** `generated_code`, `executed_sql`

**LLM call:** Yes — one batched call emits SQL (or pandas code for CSV mode) based on the plan and schema.

**External calls:** None.

**Behaviour:** Produces one artifact: a single SQL statement (or pandas pipeline) that answers the planned question. If the chosen data source is missing or the schema is insufficient, it returns a structured error message rather than guessing blindly.

### `execute_query`

**Reads from state:** `generated_code`, `data_source`, `csv_file_ids`

**Writes to state:** `executed_rows`, `executed_columns`, `executed_row_count`, `latency_ms`, `executed_sql`, `tables_touched`, `error`

**LLM call:** No.

**External calls:** `sql_runner` against SQLite / MsSQL / PostgreSQL cache; `cache_reader` fallback when live execution fails or is too slow.

**Behaviour:** Runs the query read-only with enforced row limits. On failure it attempts cache fallback when the source is live DB; otherwise it records the failure in `error` without raising. It always records the tables touched and row count for audit.

### `assemble_answer`

**Reads from state:** `executed_rows`, `executed_columns`, `question`, `executed_sql`, `error`, `followups`, `anomaly_flags`, `sensitive_warning`

**Writes to state:** `answer_text`, `result_table`, `csv_download_url`, `followups`, `anomaly_flags`, `sensitive_warning`, `status`

**LLM call:** One batched call to synthesise the answer, generate follow-up suggestions, flag anomalies, and emit junior-sensitive warnings when relevant.

**External calls:** `audit_writer` to persist the full audit row; `followup_generator` is the LLM call itself.

**Behaviour:** Builds the final user-facing answer. If `error` is set, it includes the failed step and a retry/offline guidance message. It never masks failures as successful answers.

### `finalize`

**Reads from state:** `status`

**Writes to state:** `status` (defaults to `"completed"`)

**LLM call:** No.

**External calls:** None.

**Behaviour:** Marks the run complete after the response has been returned and the audit row written.

### `handle_error`

**Reads from state:** `error`

**Writes to state:** `status` = `"failed"`, `error_message`

**LLM call:** No.

**External calls:** `audit_writer` to log the failure.

**Behaviour:** Terminal failure node. Used only when a prior node cannot continue at all.

## Graph / Flow Topology

```
START
  │
  ▼
plan_query ──(error)──► handle_error ──► END
  │
  ▼
generate_code ──(error)──► handle_error ──► END
  │
  ▼
execute_query ──(error)──► assemble_answer ──► finalize ──► END
  │                                    │
  │                                    ▼
  │                               finalize ──► END
  ▼
assemble_answer ──(error)──► handle_error ──► END
  │
  ▼
finalize ──► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `plan_query` | `state["error"]` is not `None` | `handle_error` |
| `plan_query` | otherwise | `generate_code` |
| `generate_code` | `state["error"]` is not `None` | `handle_error` |
| `generate_code` | otherwise | `execute_query` |
| `execute_query` | `state["error"]` is not `None` | `assemble_answer` |
| `execute_query` | otherwise | `assemble_answer` |
| `assemble_answer` | `state["error"]` is not `None` | `handle_error` |
| `assemble_answer` | otherwise | `finalize` |

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph state | All in-progress data, generated code, result set |
| **Across runs** | PostgreSQL + `saved_workspace_id` | Past CSV file refs, saved SQL, named scratchpads |
| **Conversation** | `memory_context` string + follow-up turn state | The previous question, answer summary, and suggested follow-ups for the next turn |
| **Cache** | PostgreSQL aggregate tables | Precomputed answers keyed by question + source fingerprint |

**Context window management:** The agent sends the schema summary and last turn summary, not full file contents, to the LLM. Large result sets are summarised before inclusion.

## Human-in-the-Loop Checkpoints

| Checkpoint | What is shown to the user | Expected user action | Timeout / default |
|------------|---------------------------|-----------------------|-------------------|
| Sensitive query warning | Modal / banner: "This query touches [category]. Confirm you are authorised to run it." | Approve / abort | Default abort on 30 s timeout |
| Live DB connection test | Connection status indicator + last-sync timestamp | Retry / switch to cache / switch to CSV | Default: stay on current source |

## Error Handling & Recovery

**Node-level:** Each node catches its own exceptions; non-fatal failures set `state.error` and continue to `assemble_answer` so the user sees a best-guess message. Fatal failures (LLM auth, total DB outage) route to `handle_error`.

**Graph-level (`handle_error` node):**
- Reads: `state.error`, `state.run_id`
- Updates DB: run status → `failed`, `error_message`, `completed_at`
- Logs error with `run_id` context
- Terminates graph

**Resume / retry strategy:** A failed run can be retried from `plan_query` with the same inputs; saved workspaces preserve the prior state for re-run on fresh data.

**Partial failure:** If `execute_query` fails but a cache hit exists, the agent degrades to cached results with a clearly visible "served from cache" indicator.

## Observability

| Signal | What | Where |
|--------|------|-------|
| Trace | One trace per run, one span per node | Structured log + DB audit row |
| LLM calls | Prompt tokens, completion tokens, latency, model, provider | Structured log + DB audit row |
| Tool calls | Tool name, inputs, success/error, latency | Structured log + DB audit row |
| Run outcome | Status, total duration, row count, error if any | DB + structured log |

## Concurrency Model

- **Run isolation:** Run IDs are scoped per user/session; simultaneous runs are independent.
- **Parallel nodes within a run:** `followup_generator` and `csv_ingestor` can run in parallel in later phases; Phase 1 runs sequentially.
- **Checkpointing:** LangGraph state is persisted per run via SQLite/PostgreSQL saver for long-running investigations.

## Graph Assembly (`src/graph/agent.py`)

```python
graph = StateGraph(AgentState)

graph.add_node("plan_query", plan_query)
graph.add_node("generate_code", generate_code)
graph.add_node("execute_query", execute_query)
graph.add_node("assemble_answer", assemble_answer)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)

graph.set_entry_point("plan_query")
graph.add_conditional_edges("plan_query", after_plan_query, {"generate_code": "generate_code", "handle_error": "handle_error"})
graph.add_conditional_edges("generate_code", after_generate_code, {"execute_query": "execute_query", "handle_error": "handle_error"})
graph.add_conditional_edges("execute_query", after_execute_query, {"assemble_answer": "assemble_answer", "handle_error": "handle_error"})
graph.add_conditional_edges("assemble_answer", after_assemble_answer, {"finalize": "finalize", "handle_error": "handle_error"})
graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

compiled_graph = graph.compile()
```
