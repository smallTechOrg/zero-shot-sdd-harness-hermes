# Roadmap

A natural-language data analyst for the UP Police. Analysts upload CSV files and ask questions in plain English; the agent inspects schemas, generates safe queries, executes them, and returns a natural-language answer plus a table, bar/line/pie charts, and dashboard KPIs. In Phase 2+ it extends to a large MsSQL database with low-latency, low-load access via a local DuckDB cache and materialized views.

---

## What This Agent Does

Lets analysts and senior officers inside the UP Police ask natural-language questions over police operational data — initially uploaded as CSV files, later sourced directly from a large MsSQL database (CCTNS-style). The agent converts questions into executable queries (SQL or Python+pandas), runs them, and presents the answer as a short natural-language explanation, a data table, auto-suggested bar/line/pie charts, and dashboard-style aggregate counters (KPIs) at the top of the page. All data processing is local; the live production database is never queried more than necessary thanks to a DuckDB cache layer and session-scoped materialized views. Full execution transparency is surfaced: the inspected schema, the generated query, row counts, latency, and a result hash are shown in the answer panel and logged to the query_log table.

## Who Uses It

- **Analysts/officers** — ad-hoc exploration, 10–50 queries/day, uploading fresh CSVs or re-querying the live DB.
- **Senior officers** — on-demand summaries and dashboard views without running SQL.

## Core Problem Being Solved

Police analysts currently export data to CSV, open it in spreadsheet tools, and manually build pivot tables or write ad-hoc SQL themselves. This is slow, error-prone, and scales poorly with large datasets (millions of rows). A single wrong join or filter can silently produce wrong numbers with no audit trail. This agent removes that friction — and adds the missing governance: every generated query is inspectable, auditable, and low-impact on production systems.

## Success Criteria

- [ ] Upload 3+ CSV files simultaneously and get correct schema detection and a coherent joint schema in under 5 seconds.
- [ ] Ask "show me top-10 police stations by pendency" and receive a ranked list with a bar chart in under 10 seconds on a local CSV session.
- [ ] Restart the server; prior session data is not required to be preserved (ephemeral sessions — logged to query_log for audit).
- [ ] Connect to a MsSQL database with read-only credentials; run a multi-table aggregate in under 3 seconds with zero live-DB load on subsequent ask.
- [ ] The generated query is visible alongside the answer, and the query_log row contains the full generated code + result hash.
- [ ] CSRF/XSS/SQL-injection surface is audited in the produced code and explicitly covered in the test gate (no blind trust).

## What This Agent Does NOT Do (Out of Scope)

- Writes/updates/deletes data in the production database (read-only agent — defer write scope to a future capability).
- Multi-turn conversational memory across server restarts (Phase 1 sessions are scoped to a single running instance; history does not persist across restarts until optional Redis/cookie store is added in a later phase).
- User authentication, role-based access control, or SSO (defer to a later Phase 4+; Phase 1 runs auth-unlocked on the internal network).
- Real-time streaming of streaming result rows (progressive page updates simulate streaming; true SSE is deferred).
- Direct export to Excel (no download button in Phase 1 — defer to Phase 2+).
- Natural-language interaction over unstructured/non-tabular data.

## Key Constraints

- **On-premises data**: The production database must never leave the police network. Only the LLM API call traverses the public internet (OpenRouter); all data stays local.
- **Minimal live-DB load**: Queries to the live MsSQL database are executed at most once per distinct question across the lifetime of a session; subsequent asks are served from DuckDB cache. The agent issues SET TRANSACTION READ ONLY; the DB user has no DML privileges.
- **Low latency**: Target < 3 seconds for an end-to-end answer on a cached multi-table query; < 10 seconds on a cold MsSQL query.
- **Cost**: Prefer cheaper OpenRouter models for routine queries; allow per-session override via env vars. Token usage is surfaced as a running total in the dashboard.
- **Audit trail**: Every question -> generated code -> execution -> result must be append-only logged to `query_log`. The log must include the full generated code, row count, latency_ms, and a hash of the result payload.
- **Python**: 3.11+. SQLAlchemy 2.x dialect for MsSQL is `mssql+pyodbc://`. Test driver rules: if production is MsSQL via pyodbc, integration tests must use the same driver (not SQLite).

## Phases of Development

> Phase 1 is the smallest user-testable quick win. The full primary journey must work end-to-end and be real on the tested path. The UI is visually complete: the working path is live, and every future surface is a clearly-labelled NON-FUNCTIONAL stub.

### Phase 1 — Multi-CSV NL analyst with visible query chain

- **Goal:** Upload multiple CSV files, ask natural-language questions, get NL answer + table + charts + dashboard KPIs; see schema, generated code, row count, and latency in the answer panel. Session holds loaded data + full conversation history for follow-up questions.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — CSV ingestion + DuckDB cache schema + the `plan → query → cache → explain` agent graph + query_log persistence. Deps: none.
  - `slice-b` (backend) — REST API endpoints for session management (create/list/delete), CSV upload (multipart/form-data), and the run endpoint. Deps: slice-a.
  - `slice-c` (frontend) — Multi-file upload page + question form + answer panel (plan, code, table, charts, KPIs, chain). Deps: slice-b (contract only).
- **Key surfaces / files:**
  - Backend: `src/graph/nodes.py` (plan / query / explain / error-handler), `src/prompts/`, `src/api/sessions.py`, `src/api/runs.py`, `src/api/csv.py`, `src/db/models.py` (csv_upload, query_log), `src/services/csv_ingest.py`, `src/services/query_exec.py`, `src/observability/events.py`.
  - Frontend: `frontend/public/index.html`, `frontend/public/styles.css`, `frontend/public/app.js`.
- **Gate command:** `uv run pytest tests/integration -q` (real LLM key required; tests run against SQLite dev DB with a pipeline fixture that hits the real `/runs` and `/csv` endpoints).
- **How the user tests it (handoff seed):** `uv run python -m src`, open `http://localhost:8001/app/`. Upload 2–3 sample CSVs (FIRs + chargesheets). Ask "top 10 police stations by total FIRs". Expect: a ranked table + bar chart + dashboard KPIs (total FIRs, date range, distinct PS) + a visible "Generated SQL" section + row count + `X.XXs` latency. Ask a follow-up ("what about last month only?") — expect prior context understood. The MsSQL tab and the login tab should be clearly labelled stubs.

### Phase 2 — MsSQL live-database access with low-DB-load cache

- **Goal:** Connect to a live MsSQL database with read-only credentials; generate read-only queries against a materialized DuckDB cache so the live DB is hit at most once per new question type. Phase 1's multi-CSV path remains fully functional.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — MSSQL + DuckDB cache layer: schema introspection of the live DB, incremental cache-refresh, SET TRANSACTION READ ONLY enforcement, pyodbc dialect wiring. Deps: Phase 1 complete.
  - `slice-b` (backend) — Endpoint + graph extension: DB connection form, cache-commit trigger, graph extension for MsSQL plan node, result-hash + load-registered in query_log. Deps: slice-a.
  - `slice-c` (frontend) — MsSQL tab is wired to real: connection screen, cache status, schema browser, result panel as in Phase 1. Deps: slice-b (contract only).
- **Key surfaces / files:**
  - Backend: `src/db/models.py` (db_connection row, cache_snapshot), `src/services/mssql_cache.py`, `src/services/lockdown.py`, `src/graph/nodes.py` (db plan node), `src/api/db.py`.
  - Frontend: `frontend/public/app.js` (MsSQL tab), `frontend/public/index.html` (Db tab).
- **Gate command:** `uv run pytest tests/integration -q AND uv run python -m src --migrate` (pyodbc driver required; a Docker-based MSSQL test fixture or a local connection string). Integration tests assert READ ONLY enforcement and cache hit on a second identical query.
- **How the user tests it (handoff seed):** Supply MsSQL connection string in `MSSQL_CONNECTION_STRING`. Open `http://localhost:8001/app/`, switch to MsSQL tab, click "Connect". Ask a complex join query; verify cache status changes from "cold → warm" and the live DB touch count in query_log increments by exactly 1 on first ask and stays flat on the repeat.

### Phase 3 — Auth, audit, and resilience hardening

- **Goal:** JWT or API-key auth, rate-limiting, request-size limits (upload), and resilience (circuit-breaker on LLM, lazy DB reconnect, structured error responses).
- **Slices (serial):**
  - `slice-a` (backend) — auth dependency, JWT issuance, per-user query_log scoping, rate-limiter.
  - `slice-b` (frontend) — login screen, session token storage (httpOnly cookie), per-user history view.
- **Gate command:** `uv run pytest tests/ -q`
- **How the user tests it:** login required; unauth'd calls return 401; rate limiter triggers after threshold; all prior Phase 2 flows still pass.
