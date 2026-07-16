# Architecture — CCTNS Analyst Agent

---

## System Overview

The CCTNS analyst is a single-user, browser-driven natural-language → SQL →
short-answer tool. The user types a question into a Next.js UI mounted at
`/app/`, served by a FastAPI backend on `:8001`. The backend runs a LangGraph
state machine: an LLM stage drafts a bounded SELECT against the CCTNS mirror;
a SQL executor runs it under strict caps (row_cap, statement_timeout); a
validator step allows one self-correction retry if the SQL is malformed; a
summarizer turns the (≤ row_cap) rows into a short prose answer; a finalize
node records the run. Raw CCTNS row bodies never enter the LLM payload —
only schema, aggregates, or short samples are sent.

Two data-source modes: **mock** (in-process, seeded with ≥ 500 synthetic FIR
rows across 5 tables — `fir`, `accused`, `victim`, `officer`, `district`) when
`CCTNS_MIRROR_URL` is unset; **live** (real `cctns_mirror` schema on a pyodbc
SQL Server connection) when `CCTNS_MIRROR_URL` is set. The mode is exposed via
`GET /health` and is the single flip a deployment makes.

Observability: structured JSON logs via structlog on every request — fields
`timestamp, level, request_id, run_id, question, sql_template, latency_ms,
row_count, token_count, error`.

## Component Map

```
[Browser]
    ↓  POST /v1/answer   {question}
[FastAPI :8001]
    ↓
[LangGraph  ──►  NL→SQL node  ──►  ExecuteSQL node  ──►  Validate node (1 retry) ──►  Summarize node  ──►  Finalize]
    ↓                                                                          ↑
[LLMClient (Gemini flash)]                                                [LLMClient (Gemini flash)]
    ↓                                                                          ↑
[Mirror: mock when CCTNS_MIRROR_URL=='  else MssqlMirror via pyodbc] ────────┘
    ↓
[AnswerRun row written to SQLite via SQLAlchemy 2.0]
```

## Layers

| Layer              | Responsibility                                                  |
|--------------------|-----------------------------------------------------------------|
| API (FastAPI)      | HTTP boundary; validation; single-origin static mount of `/app` |
| Graph (LangGraph)  | NL→SQL→executor→validate→summarize→finalize; one retry on fail  |
| LLM (Gemini)       | `LLMClient` wrapper; one call per node; `SecretStr` keys only    |
| Tools              | `cctns_mirror` (live) and `mock_mirror` (dev); SQL executor     |
| DB (SQLAlchemy)    | `AnswerRun`, `CctnsTable` (mirror-schema metadata)              |
| Frontend (Next.js) | Single page `/app/`; results table; Show-SQL toggle; stubs      |

## Data Flow

1. **Trigger:** `POST /v1/answer` from the browser.
2. **Validate:** FastAPI body schema (`{question: str, length ≤ 2000}`).
3. **Graph:** LangGraph invokes `nl_to_sql` → LLM produces a `SELECT` against
   `cctns_mirror.*` from a system prompt containing only **schema** + the question.
4. **Execute:** `execute_sql` runs the SQL via `CctnsMirror` (mock or live) with
   `row_cap` and `statement_timeout`. Result is ≤ 1000 rows; only schema + the
   bounded result (or aggregations thereof) feed the **next** LLM step.
5. **Validate:** `validate_result` checks for empty result / shape errors;
   on failure, one retry of `nl_to_sql` with the validation error in the
   prompt.
6. **Summarize:** `summarize_answer` LLM call returns a short prose summary.
7. **Finalize:** write `AnswerRun` (status, latency_ms, row_count, sql_template);
   emit the structured JSON log.
8. **Output:** JSON body `{answer, sql, columns, rows, latency_ms, row_count,
   sql_attempts}`; the browser renders answer + table + Show-SQL toggle.

## External Dependencies

| Dependency         | Purpose                                          | Failure mode                                |
|--------------------|--------------------------------------------------|---------------------------------------------|
| Gemini API         | NL→SQL + summarize (real provider, `.env` key)   | 5xx → pipeline error → error template        |
| CCTNS mirror (live)| `cctns_mirror` schema, SQL Server via pyodbc     | down → 503 from executor → error template    |
| Mock mirror (dev)  | in-process synthetic data; ≥ 500 rows            | n/a (deterministic; seeded once on startup) |
| SQLite (local)     | `AnswerRun` audit trail                          | disk full → log error; UI degrades but runs  |

## Stack

- **Language:** Python 3.11
- **Agent framework:** LangGraph (state machines with conditional retry)
- **LLM provider + model:** Gemini (`gemini-2.5-flash`, configurable via
  `APP_LLM_MODEL`)
- **Backend:** FastAPI (uvicorn)
- **Database + ORM:** SQLAlchemy 2.0 with `text()` escape hatch; SQLite for
  our own state; SQLAlchemy-2.0 mapped types only
- **Mirror:** SQLAlchemy + `pyodbc` SQL Server reachable from `CCTNS_MIRROR_URL`
  (prod); in-process `MockMirror` (dev)
- **Frontend:** Next.js 15 + React 19 + Tailwind v4 (`output:'export'`,
  `basePath:'/app'`, served by FastAPI at `/app/`)
- **Dependency management:** uv + `pyproject.toml`
- **Observability:** structlog (JSON to stdout)

| Key library                        | Version  | Purpose                       |
|------------------------------------|----------|-------------------------------|
| fastapi                            | ^0.115   | HTTP                          |
| uvicorn[standard]                  | ^0.32    | ASGI                          |
| langgraph                          | ^0.2     | State machine                 |
| langchain-core                     | ^0.3     | LLM plumbing                  |
| google-genai                       | ≥ 1.0    | Gemini provider               |
| pyodbc                             | ^5.2     | SQL Server mirror driver      |
| sqlalchemy                         | ≥ 2.0    | ORM + raw SQL                 |
| pydantic + pydantic-settings       | ≥ 2.8    | Settings + body validation    |
| structlog                          | ≥ 24.1   | Structured logs               |
| pytest + httpx + testclient         | latest   | Test suite                    |
| playwright + @playwright/test      | latest   | E2E (chromium)                |

**Avoid:**
- A hardcoded op-list mapping questions to canned queries (the agentic-ai pattern
  catalogue explicitly forbids this — pattern #22).
- SQLite-as-substitute-for-MSSQL tests where the gate claims production fidelity
  — the mock mirror IS the dev/prod default and is documented as such.
- LangSmith / OpenTelemetry in Phase 1.

## Deployment Model

Long-running local service. Single binary: `uv run python -m src` exposes
FastAPI on `0.0.0.0:8001`, mounts the Next.js static export from
`frontend/out` at `/app/`, exposes JSON APIs under `/v1/*`. Default port is
8001 per `tech-stack.md`; overridable via the `PORT` env var.
