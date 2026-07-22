# Agent

## Agent Architecture Pattern

**Chosen:** Graph (LangGraph) with tool-use loop plus a planner node and a finalizer. Rationale: the task is multi-step but branches on which data source is active (CSV vs live DB), needs structured tool orchestration for schema inspection / SQL execution / caching, and produces a rich structured output rather than a single text blob.

## LLM Provider & Model

| Agent / Node | Provider | Model ID | Rationale |
|--------------|----------|----------|-----------|
| Default planner / answerer | OpenRouter | `tencent/hy3` | Cheap baseline ($0.14/M input); overridable via env |
| SQL generation node | OpenRouter | `AGENT_LLM_MODEL` env default | Same provider, stronger structured-output rules for SQL |
| Optional fallback | Anthropic / Gemini | from `.env` | provider layer abstracts routing |

**Fallback behaviour:** retry with backoff on 429; on 404 verify model slug in env; on provider outage persist failure state and surface actionable error instead of crashing.

**Prompt strategy:** system/user split per node; structured output enforced where applicable (JSON schema or constrained generation); minimal batch calls — one LLM call per high-level artifact, never per token/row.

## Tools & Tool Calling

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| `plan_query` | Produce an execution plan (data source, safety caps, output shape) | question text, source selector, schema summary | structured plan | none |
| `inspect_csv` | Return CSV metadata after ingestion (columns, types, row count, head) | file IDs | metadata dict | reads local artifact store |
| `analyze_pandas` | Run filtered/aggregated Pandas analysis and return DataFrame summary | plan, dataset IDs, filters | answer text + table payload | reads in-memory frame, no writes |
| `inspect_mssql_schema` | Reflect live DB schema objects relevant to the question | connection label, question keywords | table/column metadata | read-only DB call |
| `execute_mssql_query` | Execute validated read-only SQL against MsSQL within row/time budgets | SQL string, row cap, timeout | rows + row count + latency | read-only DB call; caches by fingerprint |
| `write_report` | Persist a named report or scheduled task | name, payload, schedule? | report/schedule ID | writes app DB |
| `render_chart` | Build chart payload from result data | result table + chart spec | chart spec JSON | none |

**Tool selection strategy:** the planner emits an explicit tool-call sequence; the graph executes tools in order with observation between calls.

**Tool failure handling:** tool-level exceptions become state-level `error`; the graph routes to `handle_error`; partial tools fail closed with a clear message and preserve any safe-to-surface artifacts.

## Agent State

```python
class AgentState(TypedDict, total=False):
    run_id: str
    question: str
    analyst_id: str
    source: str | None
    plan: dict | None
    csv_file_ids: list[str] | None
    mssql_connection_label: str | None
    schema_metadata: dict | None
    sql: str | None
    sql_error: str | None
    query_fingerprint: str | None
    cache_hit: bool | None
    rows: list[dict] | None
    row_count: int | None
    row_budget_exceeded: bool | None
    answer_text: str | None
    table_payload: dict | None
    chart_payload: dict | None
    follow_ups: list[str] | None
    anomalies: list[str] | None
    report_id: str | None
    schedule_id: str | None
    output_files: list[str] | None
    latency_ms: int | None
    provider: str | None
    model: str | None
    status: str | None
    error: str | None
    log: list[str] | None
```

## Nodes / Steps

### `intake`

**Reads from state:** `question`, `csv_file_ids`, `mssql_connection_label`

**Writes to state:** `source`, `plan`, `log`

**LLM call:** no — rule-based source routing plus planner LLM call

**External calls:** local artifact metadata lookup; optional schema preview

**Behaviour:** Determine whether the question targets uploaded CSVs, the live MsSQL connection, or both. Produce a compact execution plan: tool sequence, row budget, output shape, and safety checks. If inputs are insufficient, surface a clarification step.

### `plan_query` (LLM-assisted when needed)

**Reads from state:** question, source, schema metadata

**Writes to state:** `plan`, `log`

**LLM call:** yes — planner prompt over question + schema/head summary

**External calls:** schema reflection / CSV head

**Behaviour:** Choose tool sequence and constraints (timeout, row cap, cache eligibility). Emit a serialisable plan object. If the question appears unsafe or ambiguous, flag it for analyst confirmation before execution.

### `tool_use`

**Reads from state:** `plan`

**Writes to state:** `schema_metadata`, `sql`, `rows`, `query_fingerprint`, `cache_hit`, `sql_error`, `row_budget_exceeded`, `latency_ms`, `log`

**LLM call:** conditional — for SQL generation when source is live DB

**External calls:** `inspect_csv`, `inspect_mssql_schema`, `execute_mssql_query`, `analyze_pandas`

**Behaviour:** Execute plan tools in order. Cache read-only SQL results by fingerprint for repeated asks. Enforce row/time budgets. On failure, populate `sql_error` and stop tool execution.

### `synthesize_answer`

**Reads from state:** `question`, `plan`, `rows`, `sql_error`, `row_budget_exceeded`, `source`

**Writes to state:** `answer_text`, `table_payload`, `chart_payload`, `follow_ups`, `anomalies`, `output_files`, `log`

**LLM call:** yes — structured answer prompt with optional chart spec generation

**External calls:** file writer for downloadable output

**Behaviour:** Convert tool outputs into a coherent answer, table, chart spec, follow-ups, and anomalies. If a budget was exceeded, note it. If input was cached, note it in the trace.

### `finalize`

**Reads from state:** everything

**Writes to state:** `status`, `provider`, `model`, `log`

**External calls:** app DB persistence for run/report/schedule outcome

**Behaviour:** Persist outcome metadata, emit final status, and prepare the response envelope.

### `handle_error`

**Reads from state:** `error`, `run_id`

**Writes to state:** `status`, `log`

**External calls:** run status update in app DB

**Behaviour:** Mark run failed, record error_message, and terminate.

## Graph / Flow Topology

```
START
  │
  ▼
intake
  │
  ▼
plan_query
  │
  ▼
tool_use ──(sql_error / budget exceeded)──► handle_error ──► END
  │
  ▼
synthesize_answer
  │
  ▼
finalize ──► END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| `tool_use` | `sql_error` is not None or `row_budget_exceeded` is True | `handle_error` |
| `tool_use` | otherwise | `synthesize_answer` |

## Memory & Context

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph state | Plan → tool outputs → synthesized answer |
| **Across runs** | SQLite app DB (runs/reports/schedules tables) | Past answers, report metadata, schedule definitions, analyst identity |
| **Conversation** | within-session server-side store keyed by analyst/session | prior questions and answers for follow-up context |

**Context window management:** tool outputs are reduced to summaries or row budgets before being injected into synthesis; long result sets are chunked or aggregated rather than inlined raw.

## Human-in-the-Loop Checkpoints

| Checkpoint | What is shown to the user | Expected user action | Timeout / default |
|------------|---------------------------|----------------------|-------------------|
| Plan confirmation | planner steps, tool sequence, row/time budget | Approve / Edit / Abort | 60s default to approve if safe |
| Safety/exemption review | generated SQL preview for live DB | Approve / Cancel | 30s, cancel on expiry |

## Error Handling & Recovery

**Node-level:** Each node catches exceptions and routes them into `state["error"]` rather than raising through the graph.

**Graph-level (`handle_error` node):**
- Reads: `state.error`, `state.run_id`
- Updates DB: run status → `failed`, `error_message`, `completed_at`
- Logs with `run_id` context and provider/model metadata
- Terminates graph

**Resume / retry strategy:** Cache-backed SQL results allow immediate rerun without DB re-query; non-cacheable runs retry with backoff and a clear error surface.

**Partial failure:** Non-critical follow-up generation failing does not block the core answer; the UI surfaces which pieces were produced and which failed.

## Observability

| Signal | What | Where |
|--------|------|-------|
| Trace | One trace per run, one span per node | structured log + optional OpenTelemetry |
| LLM calls | Provider, model, prompt token summary, completion token summary, latency | structured log |
| Tool calls | Tool name, inputs hash, success/error, latency, row count | structured log |
| Run outcome | Status, total duration, error if any, source used | DB + structured log |

## Concurrency Model

- **Run isolation:** API-level serial execution per `run_id`; concurrent analyst runs are allowed with scoped artifacts/cache keys.
- **Parallel nodes within a run:** leaf tool inspections that do not mutate state may be fan-out candidates; baseline keeps them sequential for determinism.
- **Checkpointing:** baseline uses LangGraph memory for within-run state; no persistent checkpoint saver unless scheduled/job-runner persistence requires it.

## Graph Assembly (`src/graph/agent.py`)

```python
graph = StateGraph(AgentState)
graph.add_node("intake", intake)
graph.add_node("plan_query", plan_query)
graph.add_node("tool_use", tool_use)
graph.add_node("synthesize_answer", synthesize_answer)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)

graph.set_entry_point("intake")
graph.add_edge("intake", "plan_query")
graph.add_edge("plan_query", "tool_use")

graph.add_conditional_edges(
    "tool_use",
    after_tool_use,
    {"synthesize_answer": "synthesize_answer", "handle_error": "handle_error"},
)

graph.add_edge("synthesize_answer", "finalize")
graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)
```
