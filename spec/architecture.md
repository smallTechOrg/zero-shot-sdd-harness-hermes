# Architecture

> The source of truth for how the system is structured, how data moves, and what each component owns.

## System Overview

```
Browser (static /app)
     │
     ▼
FastAPI app (src/api)
  - POST /runs accepts multipart CSV files + instruction
  - GET /runs/{run_id} retrieves history
     │
     ▼
LangGraph agent (src/graph)
  ├─ analyze_data (Phase 1)
  └─ mssql_federation (Phase 2)
     │
     ▼
LLM provider layer (src/llm)
  ├─ Anthropic | Gemini | OpenRouter-compatible
     │
     ▼
Persistent store (src/db)
  ├─ SQLite for run history + cache metadata (Phase 1–2)
  └─ Read-only MsSQL connector for live production queries (Phase 2)
```

The FastAPI app serves the UI and the `/runs` + `/health` endpoints. Each run creates a `RunRow`, builds an `AgentState`, and compiles it through a LangGraph `StateGraph[AgentState]`. Errors are captured in state and persisted as `status=failed`; the graph never raises into the API layer.

## Components

| Component | Path | Responsibility |
|-----------|------|---------------|
| Server / routes | `src/api/` | HTTP envelope, JSON responses, frontend mount at `/app` |
| Graph | `src/graph/` | LangGraph assembly, state typing, nodes, edges |
| Capability nodes | `src/graph/nodes.py` | `analyze_data` in Phase 1; `mssql_federation` in Phase 2 |
| Prompts | `src/prompts/` | System prompt templates loaded by nodes |
| LLM layer | `src/llm/` | Provider factory, adapters, retry |
| Persistence | `src/db/` | SQLAlchemy SQLite for history; optional MsSQL engine/cache |
| Frontend | `frontend/public/` | Static HTML/CSS/JS served at `/app` |
| Observability | `src/observability/` | structlog, spans |

## Data Flow

1. Analyst selects 1–many CSV file inputs and types a natural-language question in the `/app` UI.
2. Frontend issues `multipart/form-data POST /runs` with `instruction` plus `files[]`.
3. API validates input size/file types and writes `RunRow(status=running)` with `instruction` and representative `input_text`.
4. LangGraph builds `AgentState` and invokes the Phase-1 `analyze_data` node:
   - parses each CSV into schema + head/tail snippets,
   - joins on common or explicitly named key columns,
   - calls the LLM once for structured JSON output containing `insight`, `table_summary`, and `chart_spec`.
5. API updates `RunRow` from final state and returns it.
6. Phase 2 routes known question patterns through the MsSQL federation layer first; on cache miss it executes a read-only query, stores the aggregate, and returns the result.

## Data Entities

- `RunRow`: one row per agent execution with fields: `run_id`, `status`, `input_text`, `instruction`, `output_text`, `provider`, `model`, `error_message`, `created_at`, `updated_at`.
- Phase 2 may extend run metadata with cache-specific fields (`cache_hit`, `cache_key`, `mssql_latency_ms`, `query_hash`).

## Error Paths

- CSV parse or schema inference fails → captured in `state["error"]`, routed to `handle_error`, surfaced as `status=failed`.
- LLM call fails → same failed-run path.
- Input exceeds size gate → API returns `400` with a clear validation error before graph execution.
- Phase 2: cache unavailable or MsSQL unreachable → falls back to live query if allowed, otherwise fails the run explicitly.

## Config / Env

- `.env` is the only manual setup step; exactly one provider key required.
- `PORT`, `AGENT_LOG_LEVEL`, `AGENT_DATABASE_URL` stay baseline.
- `AGENT_DATABASE_URL_MSSQL` and cache tuning land in Phase 2.

## Stack

| Concern | Choice | Notes |
|---------|--------|-------|
| Language | Python 3.11+ | Baseline |
| Runtime | FastAPI + Uvicorn | Baseline |
| Agent framework | LangGraph ≥0.2.28 | Baseline |
| DB driver / ORM | SQLAlchemy 2.0 + SQLite | Baseline/Metadata store |
| MsSQL driver | `pymssql` or `pyodbc` | Phase 2 only |
| Migrations | Alembic | Baseline support |
| Frontend | Static HTML/CSS/JS at `frontend/public/` | Baseline; no npm/bundler |
| LLM access | httpx, provider layer | Anthropic/Gemini/OpenRouter-compatible |
| Observability | structlog | Baseline |
| Tests | pytest + TestClient | Phase 1 integration smoke |

> **Assumed:** Phase 1 adds no mandatory new env vars beyond existing baseline. Phase 2 adds one optional connection string.
