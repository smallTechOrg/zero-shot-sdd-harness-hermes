# Agent

> The agent graph contract and runtime behavior. Required because this project uses LangGraph.

## Pattern

- **Type:** Single-step planner + executor.
- **Source:** `harness/patterns/agentic-ai.md` — one LLM call per run with structured JSON output; no internal loops; errors do not raise into the API.
- **Why:** Deterministic latency and cost for Phase 1. Federation/cache routing is added in Phase 2.

## State

`AgentState` flows through the graph.

```python
class AgentState(TypedDict, total=False):
    run_id: str
    input_text: str
    instruction: str
    output_text: str
    provider: str
    model: str
    status: str
    error: str | None
```

- `input_text` may hold serialized schema summaries for multiple uploaded files.
- `output_text` holds the final insight text summarizing combined-file findings.
- Phase 1 does not change state shape from the baseline.

## Nodes

| Node | File:function | Responsibility |
|------|--------------|---------------|
| `analyze_data` | `src/graph/nodes.py::analyze_data` | Parse uploaded CSV inputs to schema+summary, build LLM prompt, call LLM once, return `output_text`, `provider`, `model`. Captures failures in `error`. |
| `handle_error` | `src/graph/nodes.py::handle_error` | Marks run `status=failed`. |
| `finalize` | `src/graph/nodes.py::finalize` | Marks run `status=completed`. |

## Edges

| From | Condition | To |
|------|-----------|----|
| `analyze_data` | `error` is truthy | `handle_error` |
| `analyze_data` | otherwise | `finalize` |
| `finalize` | — | `END` |
| `handle_error` | — | `END` |

## Error Handler

- Node catches `LLMError` and any parsing exception and returns `{"error": str(exc)}`.
- The graph never raises; errors become failed runs in `RunRow.error_message`.

## Concurrency

- Graph compiled once at import; each run is synchronous within the FastAPI request.
- No fan-out or parallel tool use in Phase 1.

## Assembly

```python
def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("analyze_data", analyze_data)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)
    g.set_entry_point("analyze_data")
    g.add_conditional_edges(
        "analyze_data",
        after_transform,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()
```

## Federation Layer — Phase 2

> **Assumed:** query fingerprinting uses normalized question + selected parameters as the cache key; cache entries expire based on a configurable TTL; MsSQL access is read-only with no mutations.

- Cache is a SQLite-backed aggregate store keyed by `query_hash`.
- Misses execute read-only SQL through a dedicated `mssql_federation` node.
- Each node call emits `cache_hit`, `query_hash`, and latency in run metadata.

## Observability

- Each run emits `input_chars`, `file_count`, row/share summaries when feasible, and `output_chars`.
- The span is tagged with `provider`, `model`, `run_id`, and final `status`.
