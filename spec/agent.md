# Agent

> Required when the project uses an agent framework. Delete this file if your project has no agent framework.
---
## Agent Architecture Pattern

<!-- FILL IN: Which pattern does this agent follow? Choose one and describe why. -->

| Pattern | Use when |
|---------|----------|
| **Single-agent loop** | One LLM drives a deterministic tool-call loop. No branches, no handoffs. |
| **Graph (LangGraph)** | Multi-step pipeline with conditional edges, checkpointing, or parallel nodes. |
| **Multi-agent** | Specialised sub-agents with distinct roles; orchestrator routes between them. |
| **Supervisor** | One supervisor LLM dispatches to worker agents based on task type. |
| **Human-in-the-loop** | Execution pauses at defined checkpoints for user review or approval. |

**Chosen:** Graph (LangGraph) — multi-step pipeline over CSV cache and live MsSQL, with safe SQL execution, chart-aware synthesis, and explicit error routing.

---
## LLM Provider & Model

<!-- FILL IN: Which model drives each agent/node? State provider, model ID, and why. -->

| Agent / Node | Provider | Model ID | Rationale |
|-------------|----------|----------|-----------|
| plan_query | OpenRouter (default; configurable via .env) | AGENT_LLM_MODEL, else provider default | Structured SQL planning from schema context at lowest default cost. |
| finalize | OpenRouter (same) | same as plan_query | One synthesis call: answer + chart spec + suggestions. |

**Fallback behaviour:** If the LLM API is unreachable, rate-limited, or returns a server error, the run fails gracefully with a surfaced error envelope (HTTP 200 + status=failed) plus an actionable `error_message`. No silent fallback to a stub. MsSQL connectivity failures degrade to cache-only and the UI shows the degraded mode.

**Prompt strategy:** System/user split, schema injected as markdown context, result shape constrained by JSON mode / structured instruction. Max two LLM calls per run: plan → execute (tool) → finalize.

---
## Tools & Tool Calling

<!-- FILL IN: Every tool the agent can call. -->

| Tool name | Description | Inputs | Output | Side-effects |
|-----------|-------------|--------|--------|--------------|
| schema_tool | Introspect cache or live DB tables + columns | session_id, data_source | markdown schema + table list | read-only |
| execute_sql_safe | Run read-only SQL against cache or live DB | session_id, sql, data_source, max_rows | columns/rows/latency | read-only |
| db_health | Check live MsSQL connectivity | — | connection info | network call |

**Tool selection strategy:** LLM chooses `schema_tool` for schema context, `execute_sql_safe` for answer generation, `db_health` for connectivity checks. Invalid SQL is rejected before execution (DML keywords blocked).

**Tool failure handling:** SQL validation failure returns an error; connectivity failure returns cache-only result with a degraded-mode flag.

---
## Agent State

<!-- FILL IN: The full state type. Every field must be named, typed, and annotated with what populates it. -->

```python
class AgentState(TypedDict):
  # Identity
  run_id: int
  session_id: str | None

  # Input
  question: str
  data_source: str  # "cache" or "live"

  # Schema + plan
  schema_markdown: str | None
  sql: str | None
  chart_spec: dict | None
  suggestions: list[str] | None

  # Tool output
  query_result: dict | None
  tool_error: str | None

  # Final
  output_text: str | None

  # Meta
  provider: str | None
  model: str | None
  latency_ms: int | None
  status: str | None
  error: str | None
```

---
## Nodes / Steps

<!-- FILL IN: One section per node. For single-agent loops, describe each "step" or "tool call phase". -->

### `plan_query`

**Reads from state:** `session_id`, `question`, `data_source`

**Writes to state:** `schema_markdown`, `sql`, `chart_spec`, `suggestions`, `provider`, `model`

**LLM call:** One call using the SQL-generation system prompt + schema context + user question. Outputs SQL (or pandas plan fallback), chart type, and next-question suggestions.

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB / MsSQL | schema_tool to fetch table list | set state error and route to handle_error |

**Behaviour:** Plans the analytical query from the available schema and user question; emits executable SQL (read-only), a chart spec when the result will be numeric, and suggested follow-up questions.

---

### `execute_tool`

**Reads from state:** `session_id`, `sql`, `data_source`

**Writes to state:** `query_result`, `tool_error`

**LLM call:** None.

**External calls:**

| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB or MsSQL | execute_sql_safe | capture error into tool_error and continue |

**Behaviour:** Executes the planned SQL against the chosen store, enforcing max_rows and read-only constraints. Captures results or error for the finalize node.

---

### `finalize`

**Reads from state:** `question`, `sql`, `query_result`, `tool_error`, `chart_spec`, `suggestions`

**Writes to state:** `output_text`, `status`, `latency_ms`, `error`

**LLM call:** One synthesis call producing a plain-English answer, formatted table excerpt, chart JSON, and suggestions.

**External calls:** None.

**Behaviour:** Turns structured results into a human-readable answer; degrades gracefully when the tool errored.

---
## Graph / Flow Topology

<!-- FILL IN: ASCII diagram of node flow. Show ALL conditional edges explicitly. -->

```
START
 │
 ▼
plan_query ──(llm/tool error)──► handle_error ──► END
 │
 ▼
execute_tool ──(tool ok)──► finalize ──► END
 │                │
 │                └──(tool error)──► finalize ──► END
 ▼
END
```

**Conditional edges:**

| Source node | Condition | Target |
|-------------|-----------|--------|
| plan_query | error present | handle_error |
| execute_tool | tool_error present | finalize (degraded) |

---
## Memory & Context

<!-- FILL IN: How does the agent remember things across turns, steps, or runs? -->

| Scope | Mechanism | What is stored |
|-------|-----------|----------------|
| **Within a run** | LangGraph state | schema, SQL, result, answer, chart |
| **Across runs** | SQLite RunRow | question, answer JSON, provider, model, latency, error |
| **Conversation** | Not enabled in Phase 1 | follow-up context deferred |

**Context window management:** Only schema markdown + question are sent to the LLM. Row data is never injected into prompts.

---
## Human-in-the-Loop Checkpoints

<!-- FILL IN: Where does execution pause for human input? Delete section if not applicable. -->

| Checkpoint | What is shown to the user | Expected user action | Timeout / default |
|------------|--------------------------|----------------------|-------------------|
| (none in Phase 1) | | | |

---
## Error Handling & Recovery

<!-- FILL IN: How the agent handles failures at each level. -->

**Node-level:** Each node catches exceptions and writes to state; never raises through the graph. `execute_tool` returns SQL errors in `tool_error` without crashing.

**Graph-level (handle_error node):**
- Reads: `error`, `run_id`
- Persists status=failed and `error_message`
- Logs with `run_id` context via structlog

**Resume / retry strategy:** Failed runs are idempotent; analyst resubmits the same question.

**Partial failure:** Tool layer returns cache results while marking live-DB as degraded when MsSQL is unreachable.

---
## Observability

<!-- FILL IN: What is logged, traced, and measured? -->

| Signal | What | Where |
|--------|------|-------|
| **Trace** | One span per node | structlog |
| **LLM calls** | provider/model/input_chars/output_chars | structlog |
| **Tool calls** | tool name, lateny_ms, row_count | structured log |
| **Run outcome** | status, latency_ms, provider, model, error_message | POST/RunRow + response |

---
## Concurrency Model

<!-- FILL IN: How concurrent agent runs are handled. -->

- **Run isolation:** parallel run support via shared run_id and stateless queries; duckdb file is session-scoped.
- **Parallel nodes within a run:** none in Phase 1; nodes are sequential.
- **Checkpointing:** none required in Phase 1 (queries are short).

---
## Graph Assembly (`src/graph/agent.py`)

<!-- FILL IN: Pseudocode showing how nodes and edges are wired. Must be ≤ 60 lines in the real file. -->

```python
graph = StateGraph(AgentState)

graph.add_node("plan_query", plan_query)
graph.add_node("execute_tool", execute_tool)
graph.add_node("finalize", finalize)
graph.add_node("handle_error", handle_error)

graph.set_entry_point("plan_query")

# Error edge from plan_query
graph.add_conditional_edges(
  "plan_query",
  lambda s: "handle_error" if s.get("error") else "execute_tool",
  {
    "execute_tool": "execute_tool",
    "handle_error": "handle_error",
  },
)

graph.add_edge("execute_tool", "finalize")
graph.add_edge("finalize", END)
graph.add_edge("handle_error", END)

compiled_graph = graph.compile()
```
