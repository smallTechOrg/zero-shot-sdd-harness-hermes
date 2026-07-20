# Architecture

## System Overview

A single FastAPI process serves both the API and the zero-build static frontend. The process owns one SQLite database for session state, CSV metadata, and the append-only `query_log`. The actual data analysis happens in-process against DuckDB — a local, zero-infra analytical engine — so the live production database is never queried by the analyst-facing path in Phase 1+. In Phase 2, a background cache layer populates DuckDB from the live MsSQL via materialized refresh silos.

```
Browser (internal network)
  └─ http://localhost:8001/app/ (zero-build static UI, single-origin)
       ├─ POST /api/v1/sessions        — create a new conversation session
       ├─ POST /api/v1/sessions/{id}/csv   — upload one or more CSVs
       ├─ POST /api/v1/sessions/{id}/runs  — submit a natural-language question
       └─ GET  /api/v1/sessions/{id}/runs/{run_id} — fetch a prior run

FastAPI process (port 8001, pinned interpreter: .venv/bin/python -m src)
  ├─ session manager (in-memory + SQLite for metadata)
  ├─ CSV ingestion → DuckDB (in-process, local filesystem)
  ├─ graph nodes: plan → query → execute → explain (LangGraph)
  ├─ LLM provider: OpenRouter (Anthropic/Gemini/OpenRouter adapters already in src/llm/)
  ├─ query_log (SQLite, append-only)
  └─ Phase 2+: background cache-refresh worker for live MsSQL
```

## Components

### 1. Session Manager

Tracks active sessions, their loaded files, schema cache, and conversation history. Ephemeral: restart clears in-memory state; persisted metadata + full `query_log` survive restarts.

### 2. CSV Ingestion Service

Exposes a `/csv` upload endpoint (multipart/form-data, multiple files). Produces a DuckDB in-memory database for the session, executing CREATE TABLE AS for each CSV, and a lightweight per-table schema summary (column names, types, NULL counts, row count, min/max for numeric, top-5 distinct for low-cardinality strings). The schema summary is cached (TTL infinity for the life of a session) and injected into every plan node context.

### 3. Plan → Query → Cache → Explain (Agent Graph)

LangGraph state machine, 4 nodes:

| Node | Purpose | Output |
|------|---------|--------|
| `plan` | Inspect session schema cache + conversation history, write a structured plan (which tables/columns, what aggregation, what filter). Emit a natural-language plan string. | plan_text |
| `query` | Given the plan, generate one executable SQL target (DuckDB dialect) or Python+pandas fallback if DuckDB SQL is insufficient (e.g. custom string functions from the protocol). Emit **exactly one** query per run. | generated_code, code_language |
| `execute` | Execute against the session's DuckDB db (or MsSQL cache for Phase 2). Enforce SET TRANSACTION READ ONLY if on live DB. Capture row_count and latency_ms. | rows (JSON), row_count, latency_ms, cache_hit |
| `explain` | Summarize the rows + generate chart spec (chart_type, x, y, title, color_by) + 3–6 dashboard KPIs. Also emit: result_hash (SHA-256 of row payload), row_count, latency_ms. | nl_answer, chart_spec, kpis, result_hash, audit_block |

Edges: `plan → query → execute → explain` on success; any failure routes to `handle_error`, which returns `error`, `error_message`, `generated_code` (partial if available), and routes the run to the audit log with `status=failed`. Retries use `clarify`-style single-question feedback to the LLM via `handle_clarify` — a short prompt explaining the failure type ("DB error: column not found — pick from: …"; "Ambiguous column — did you mean col_a or col_b?") and one retry maximum per step.

### 4. Query Execution Service

- **DuckDB (default / CSV)**: in-process, per-session DB file. No config needed.
- **MsSQL via pyodbc**: 
  - A read-only DB user (SELECT + SET TRANSACTION READ ONLY enforced at connection level) is required.
  - A background refresh runs schema introspection once per session (or on demand), producing a DuckDB mirror cache.
  - Query request is first attempted against the DuckDB cache. A cache miss (feature flag / first-time question) hits the live DB. Result rows are stored in the cache for future reuse. Cache freshness is bounded by a TTL (default: until session ends; configurable via env var).
  - Cache staleness is surfaced in the answer panel ("Data is 14 minutes stale as of HH:MM").
- **Both backends**: `query_exec.py` abstracts to `execute_on_duckdb()` / `execute_on_mssql()` with the same return shape.

### 5. Frontend (zero-build static, single-origin)

Served at `/app/` by the backend. No build step.

- Upload zone: multiple file picker + drag/drop.
- Session bar: shows loaded files + row counts + cache status.
- Question form: textarea + submit.
- Answer panel (progressive rendering):
  - **Plan block** (collapsed by default): `plan_text` from the plan node.
  - **Generated code block** (collapsible): `generated_code` with copy button; language label; source badge (`duckdb` | `mssql` | `mssql-cache`).
  - **Dashboard KPIs**: 3–6 counters from `explain`.
  - **Data table**: sortable, paginated; char limit per cell; "copy CSV" per-cell.
  - **Chart area**: auto-suggested single chart (bar / line / pie) based on `chart_spec`; resize-aware; legend toggle.
  - **Audit chain**: row_count, latency_ms, result_hash, timestamp.
- **Phase 2+ stubs** (clearly labelled in Phase 1):
  - "MsSQL connection" tab (unlocked, shows "Coming up").
  - "Login" tab (unlocked, shows "Coming up").
  - "Download CSV" button (disabled, labelled stub).

### 6. Observability & Audit

Structured structured logging (structlog) on every node entry/exit, LLM call, DB call, and error. Append-only `query_log` records:

- `id`, `session_id`, `user_id` (Phase 3+), `question`
- `generated_code`, `code_language`, `source` (duckdb | mssql | mssql-cache)
- `row_count`, `latency_ms`, `result_hash`, `status` (success | failed | clarified_error)
- `error_message` (partial if failed mid-step)
- `created_at`, `updated_at`

## Data Flow

```
User: "top 10 PS by total FIRs in last month"
  → upload CSV(s) into DuckDB
  → session created, schema summary cached

User: "top 10 PS by total FIRs in last month"
  → plan node: tables=["firs"], columns=["ps_name","fir_date"], agg=COUNT, filter=date_range
  → query node: SELECT ps_name, COUNT(*) AS total_firs FROM firs WHERE fir_date >= '2024-01-01' GROUP BY ps_name ORDER BY total_firs DESC LIMIT 10
  → execute node: DuckDB query → 10 rows, 0.02s
  → explain node: "10 stations returned, highest is X with Y FIRs"
    KPIs: total_firs=Y, date_range=2024-01-01 to …, ps_count=10, …
    chart_spec: {type: bar, x: ps_name, y: total_firs, title: "Top 10 PS by FIRs"}
  → answer rendered
```

For MsSQL in Phase 2, `execute` first checks the DuckDB cache; on miss, runs `SET TRANSACTION READ ONLY` then the same query against pyodbc → materialize to DuckDB → return rows as before.

## Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Runtime | Python 3.11+ | Team standard; FastAPI + LangGraph |
| API framework | FastAPI + uvicorn | Baseline; already wired |
| Agent framework | LangGraph ≥ 0.2.28 | Plan → Query → Execute → Explain pattern |
| ORM / DB | SQLAlchemy 2.x + Alembic migrations | Baseline; MsSQL via `mssql+pyodbc://` |
| Analytical engine | DuckDB (via `duckdb` PyPI) | Local, zero-infra, fast on millions of rows, works as both in-memory cache and MsSQL mirror |
| Live DB driver | pyodbc + ODBC 18 driver | MsSQL production driver; must stay in `[project.dependencies]` per rules |
| LLM provider | OpenRouter (`https://openrouter.ai/api/v1`) | User preference; model env-configurable |
| Default LLM model | Env-overridable; baseline: user's OpenRouter choice | Rule: never hardcode without verification |
| Frontend | Zero-build static HTML/CSS/JS at `frontend/public/`, single-origin | Baseline; no Node required |
| Auth (Phase 3+) | JWT + httpOnly cookie | Standard internal-tool pattern |
| Process manager | `uvicorn` via FastAPI lifespan | Single-process, single-port (8001) |
| Migrations | Alembic | Already wired in repo |
| Observability | structlog + append-only `query_log` table | Baseline + query audit |

> **Assumed:** pyodbc + MS ODBC 18 driver is installable on the target Linux server (confirmed by user as on-prem). If the internal network blocks outbound OpenRouter calls, a local LLM proxy (v1/openai-compatible) on the same network is an acceptable substitute; the provider adapter supports custom base URLs.
