# Architecture

## System Overview

A FastAPI + LangGraph service that exposes a natural-language data-analysis interface over either uploaded CSV files (cached in DuckDB) or a live Microsoft SQL Server read replica. A single LLM call generates SQL or a pandas plan; a tool layer executes it safely; results flow back as text + optional Plotly chart JSON. Analysts interact through a zero-build static frontend at `/app`. The DuckDB cache absorbs all exploratory load, protecting the live MsSQL instance.

## Component Map

```
Frontend (static HTML/JS)
   │  POST /runs  POST /ingest  GET /schema  POST /db/connect  ...
   ▼
FastAPI app (src/api/)
   │  invokes
   ▼
LangGraph agent (src/graph/)
   │  calls tools
   ▼
Tool layer (src/graph/tools/)
   ├─ csv_ingest_tool   →  DuckDB cache  (local .duckdb files)
   ├─ schema_tool       →  DuckDB / MsSQL introspection
   ├─ query_cache_tool  →  DuckDB (fast, no DB load)
   └─ query_live_tool   →  MsSQL via pyodbc (read-replica only)
   ▼
Response → AgentState → RunRow → JSON API response
```

## Layers

| Layer | Responsibility | Files |
|-------|----------------|-------|
| Frontend | Upload CSVs, display schema, chat, render chart cards | `frontend/public/` |
| API | FastAPI routes; auth stub for Phase 3 | `src/api/routes_*.py`, `src/api/_common.py` |
| Graph | LangGraph state machine; 3 nodes (ingest → plan → query) | `src/graph/nodes.py`, `src/graph/runner.py` |
| Tools | CSV load, schema introspection, safe SQL execution (cache + live) | `src/graph/tools/*.py` |
| LLM prompts | SQL generation, answer synthesis, chart-plan generation | `src/llm/prompts/*.md` |
| Storage | DuckDB local cache (CSV), MsSQL (live); RunRow in SQLite | `src/db/` |
| Config | Pydantic Settings; env prefix `AGENT_` | `src/config/settings.py` |

## Data Flow

1. **Ingest trigger:** Analyst uploads one or more CSVs via `POST /api/v1/ingest`.
2. **CSV → DuckDB:** Each CSV is loaded as a DuckDB table; column types inferred; schema summary stored in `AgentState`.
3. **Question trigger:** Analyst types a question → `POST /api/v1/query` → `run_agent()`.
4. **Graph execution:**
   - `plan_query` node: uses `schema_tool` to read available tables/columns; calls LLM to produce a query plan (SQL string + chart spec).
   - `execute_cache` or `execute_live` tool: runs the SQL against DuckDB or MsSQL depending on routing.
   - `finalize` node: LLM synthesizes natural-language answer + chart data; writes to `output_text`.
5. **Response:** API returns `RunResult` with `output_text` (JSON containing `{answer, chart, sql, source})` plus metadata (`provider`, `model`, `latency_ms`).

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| LLM (Anthropic / Gemini / OpenRouter) | SQL generation + answer synthesis | Agent returns error envelope; retry with fallback provider if configured |
| DuckDB (local) | CSV cache, fast analytical queries | Local OPS — if DuckDB corrupted, re-ingest CSVs |
| MsSQL (read replica) | Authoritative current data | Agent falls back to DuckDB cache; UI shows "live DB unavailable — use cached data" |
| ODBC driver (msodbcsql) | MsSQL connectivity from Python | Cache-only mode activated; MsSQL features disabled gracefully |

## Stack

- **Language:** Python 3.11
- **Agent framework:** LangGraph 0.2.x
- **LLM provider + model:** OpenRouter (default `tencent/hy3`); Anthropic / Gemini configurable via `.env`
- **Backend:** FastAPI + Uvicorn
- **Database:** DuckDB (CSV cache), MsSQL via pyodbc (live read-replica), SQLite (run logging via SQLAlchemy)
- **Frontend:** Zero-build static HTML/CSS/JS, served at `/app`
- **Dependency management:** uv + pyproject.toml

| Key library | Version | Purpose |
|-------------|---------|---------|
| duckdb | latest | Local analytical cache from CSVs |
| pandas | 2.x | CSV type inference, result formatting |
| pyodbc | latest | MsSQL connectivity |
| plotly | latest | Chart spec generation (JSON) |
| openpyxl | latest | Optional .xlsx support (future) |

**Avoid:** Direct pandas df.plot (no GUI); full-table scans on MsSQL (always filter/aggregate before returning rows).

## Deployment Model

Long-running FastAPI service on a Windows Server VM inside the UP Police network (or via Docker). Analysts open a browser to `http://<host>:8001/app/`. No client-side install needed. For Phase 3: Gunicorn + Nginx reverse proxy, RBAC via API key or OAuth2 proxy.
