# Architecture

---

## System Overview

A single FastAPI service running on a Windows machine, exposed at `http://localhost:8001/`. It accepts natural-language questions from a browser UI, translates them to SQL via Gemini, executes the SQL against the local MSSQL instance (Windows Integrated Auth), and returns a small result table. Every step is audited in a local SQLite log. No caching layer; the MSSQL server is touched once per request with the smallest possible query footprint.

```
[Browser]  ──HTTP/JSON──▶  [FastAPI :8001]
                                 │
                                 ├──▶ [LangGraph Agent] ──▶ [Gemini API] (NL→SQL)
                                 │              │
                                 │              ▼
                                 │        [SQL Safety Validator] (system prompt + regex)
                                 │              │
                                 │              ▼
                                 │        [MSSQL Mirror via pyodbc]  ─▶  [SQL Server master]
                                 │              │
                                 ▼
                          [SQLite Audit Log]      [Response: SQL + rows + columns + tokens]
```

## Component Map

- **FastAPI app** (`src/mssql_analyst/api/`) — exposes `/health`, `/api/ask`, `/api/usage`. Mounts the Next.js static export at `/app/`.
- **LangGraph agent** (`src/mssql_analyst/graph/`) — minimal ReAct loop: `nl_to_sql → execute_sql → handle_error/finalize`. Single-shot for Phase 1.
- **LLM client** (`src/mssql_analyst/llm/`) — thin wrapper; only place that imports `google-genai`.
- **MSSQL mirror** (`src/mssql_analyst/tools/mssql.py`) — `pyodbc` connection with Windows Integrated Auth. Caches `INFORMATION_SCHEMA.TABLES/COLUMNS` once at startup; never re-queries schema per request.
- **Safety validator** (`src/mssql_analyst/tools/validator.py`) — regex check: must start with `SELECT`/`WITH`; refuse `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/GRANT/REVOKE`; refuse `;`-stacked statements.
- **Audit log** (`src/mssql_analyst/db/`) — SQLite; one `answer_runs` row per ask.

## Layers

| Layer | Responsibility |
|-------|----------------|
| **Web UI** (`frontend/`) | Question input, Ask button, result table, collapsible SQL, "tokens used" badge, last-50 sidebar (Phase 2). |
| **API** (`src/mssql_analyst/api/`) | Request validation, graph invocation, audit write, response envelope. |
| **Agent graph** (`src/mssql_analyst/graph/`) | Orchestration of NL→SQL→execute→finalize via LangGraph. |
| **Tools** (`src/mssql_analyst/tools/`) | MSSQL connector + SQL safety validator. |
| **LLM providers** (`src/mssql_analyst/llm/providers/`) | `GeminiProvider` (factory + boundary). |
| **Persistence** (`src/mssql_analyst/db/`) | Audit-DB SQLAlchemy models, session, migration. |

## Data Flow

1. Trigger: user types in the web UI (single-page Next.js) and clicks Ask.
2. Frontend POSTs `{question}` to `/api/ask`.
3. FastAPI binds request_id, persists a pending `AnswerRun` row, invokes the LangGraph graph.
4. `nl_to_sql` node: calls Gemini with a system prompt that includes the cached schema + the question. Expects JSON `{"sql": "..."}` back; runs the safety validator on the SQL. If unsafe, sets `error: "unsafe_sql"` and routes to `handle_error`.
5. `execute_sql` node: opens a `pyodbc` connection (15s timeout), executes the SQL, returns `(columns, rows, raw_count)`. Always enforces the row-cap server-side (`TOP N`).
6. `finalize`: marks `status: completed` (or `failed` if earlier).
7. FastAPI persists the final `AnswerRun` row (status, sql, row_count, error_message, latency_ms, tokens_used).
8. Response: `{answer: {sql, columns, rows, row_count, latency_ms, tokens_used}}`.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| **Microsoft SQL Server** (local `master`, Windows Integrated Auth) | Source of data; runs the bounded SELECT. | Connection refused / timeout → returned as `{"error": "mssql_unavailable"}`. |
| **`google-genai` (Gemini API)** | NL → SQL translation. | Network error / 429 / 5xx → returned as `{"error": "llm_unavailable"}`. |

## Stack

> Concrete technology choices. Generic rules are in `harness/patterns/tech-stack.md`.

- **Language:** Python 3.11 (Windows venv, MSYS/bash shell).
- **Agent framework:** LangGraph ≥ 0.2 (minimal ReAct loop in Phase 1; no multi-agent).
- **LLM provider + model:** Google Gemini (`gemini-3.1-pro` default, override via `AGENT_LLM_MODEL`).
- **Backend:** FastAPI ≥ 0.115 + Uvicorn ≥ 0.32.
- **Database (source):** Microsoft SQL Server via `pyodbc ≥ 5.2` (production DB driver; declared in main `[project.dependencies]`).
- **Database (audit):** SQLite at `data/agent.db`, via SQLAlchemy 2.0.
- **ORM:** SQLAlchemy 2.0 (audit DB only — NOT used as a substitute for MSSQL).
- **Frontend:** Next.js 15 + React 19 + Tailwind v4 (static export, `basePath: /app`, mounted by FastAPI at `/app/`).
- **Dependency management:** `uv` + `pyproject.toml`.
- **Test:** `pytest`, `httpx`, Playwright (chromium).

| Key library | Version | Purpose |
|-------------|---------|---------|
| `fastapi` | ≥ 0.115 | HTTP API |
| `uvicorn[standard]` | ≥ 0.32 | ASGI server |
| `pydantic` / `pydantic-settings` | ≥ 2.8 / ≥ 2.5 | Request validation, settings |
| `sqlalchemy` | ≥ 2.0 | Audit DB ORM (NOT a substitute for MSSQL) |
| `alembic` | ≥ 1.13 | Migrations (audit DB) |
| `google-genai` | ≥ 1.0 | Gemini SDK |
| `langgraph` | ≥ 0.2 | Agent graph runtime |
| `langchain-core` | ≥ 0.3 | Typed-dict state (used by LangGraph) |
| `pyodbc` | ≥ 5.2 | **Production DB driver** (MSSQL) |
| `httpx` | ≥ 0.27 | Misc HTTP |
| `structlog` | ≥ 24.1 | Structured JSON logging to stdout |

**Avoid:**
- SQLAlchemy for MSSQL queries — use `pyodbc` directly (small integration surface; the agent exec is one SELECT at a time).
- A mock/in-memory mirror as a default — Phase 1 is live-only by spec.
- A two-server dev flow (`npm dev :3000`); single-origin `npm run build` → `:8001/app/`.
- Eager `app = create_app()` at module import time in `api/__init__.py` (causes SDK cold-import hang on TestClient; use `__getattr__` lazy proxies).

## Deployment Model

Local development process on the user's Windows machine, run via `.venv/bin/python -m src` from the repo root. The frontend is built once (`npm run build` → `frontend/out`) and served by FastAPI under `/app/`. Alembic creates the audit DB only; the MSSQL data source is the user's existing instance (no migrations against MSSQL).
