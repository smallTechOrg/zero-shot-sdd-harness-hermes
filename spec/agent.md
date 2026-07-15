# Agent Graph

Pattern: **linear pipeline with optional LLM node** (LangGraph `StateGraph`). The pipeline is the analytics refresh; it is deterministic except for the optional narration node.

## State

```python
class PipelineState(TypedDict, total=False):
    entity: str                 # "#local"
    run_id: str
    error: str | None
    records: list[SourceRecord] # produced by fetch_sources
    snapshot: Snapshot | None   # produced by compute_funnel
    insight: str | None         # produced by narrate (None if no LLM key)
    status: str                 # "completed" | "failed"
```

## Nodes

| Node | Input | Does | Output |
|------|-------|------|--------|
| `fetch_sources` | `entity` | `ConnectorHub.pull_all(entity)` → `SourceRecord`s | `records` |
| `aggregate` | `records` | normalize + write `SourceRecord` audit rows | (side-effect) |
| `compute_funnel` | `records` | build `Snapshot` (funnel + KPIs) + `FunnelPoint` | `snapshot` |
| `narrate` | `snapshot` | optional LLM summary (skipped if no key) | `insight` |
| `handle_error` | `error` | log + set `status="failed"` | — |
| `finalize` | all | commit `Snapshot`/`FunnelPoint`, set `status="completed"` | — |

## Edges

```
entry → fetch_sources
fetch_sources →(error?)-> handle_error : aggregate
aggregate → compute_funnel
compute_funnel →(error?)-> handle_error : narrate
narrate → finalize
handle_error → END
finalize → END
```

## Error handler

Any node sets `state["error"]`; routing sends to `handle_error`, which records the failure and ends. The API returns the last good snapshot + an error flag rather than crashing.

## Finalize

Writes `Snapshot` and `FunnelPoint` rows via `create_db_session()`, returns `status`.

## Concurrency

Single linear chain — no parallelism needed. `fetch_sources` pulls connectors sequentially (each is independent but cheap in sample mode; real connectors will be parallelized in Phase 2).

## Assembly

`graph/agent.py` builds and compiles the graph once at import (`_build_graph().compile()`); `graph/runner.py:run_pipeline(entity)` invokes it and returns the `Snapshot`.
