# Roadmap

## What This Agent Does

A local, on-prem data analyst agent for the UP Police. Analysts upload one or more CSV exports, ask natural-language questions, and receive answers backed by generated SQL, result tables, charts, downloadable reports, anomaly flags, and suggested follow-ups. Behind the same interface the agent connects to a live **MsSQL** database for ad-hoc queries over production police data. A scheduling layer lets analysts register recurring questions or reports that run on a timetable and store named reports.

## Who Uses It

- **Primary:** Police data analysts and investigation officers at a station or crime-branch level.
- **Secondary:** Admin / senior officers who consume recurring scheduled reports or named dashboards.

## Core Problem Being Solved

- Analysts currently switch between CSV exports, hand-rolled Excel filters, and SSMS queries to answer operational questions.
- Direct DB queries from analysts are costly, inconsistent, and risky.
- Recuring reporting is manual, slow, and delivered as one-off attachments.

## Success Criteria

- A new analyst can upload 2+ CSVs and get a SQL-backed, chart-plus-table answer in under 2 minutes with no SQL knowledge.
- A live-connection query against a million-row MsSQL table returns a verified result without manual query authoring.
- Scheduled reports run unattended and persist named results analysts can replay.
- Queries show full reasoning trail: planner steps, generated SQL, row counts, and latency.
- Zero data leaves the on-prem machine by default unless explicitly exported.

## What This Agent Does NOT Do (Out of Scope)

- Writes, updates, or deletes data in the live MsSQL database (read-only by default).
- Acts as a replacement for verified forensic data extraction or mandatory statutory reports.
- Stores or transmits analyst data outside the controlled local deploy unless the analyst explicitly exports it.
- Authenticates individual users beyond simple identity labels (v1 user model is analyst-level only, no role matrix).

## Key Constraints

- **On-prem only:** data must not leave the machine by default.
- **DB load budget:** max ~5 DB-active seconds per analyst question; default to cached/read-replica or local aggregates for repeated asks.
- **Latency bar:** millions-of-row tables accept a few seconds but must not hammer the DB.
- **LLM cost:** use OpenRouter default model `tencent/hy3` (cheap), configurable via env.
- **Compliance context:** outputs may be audit-visible; preserve query text, inputs, timestamps, and analyst identity.

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** It must work perfectly the first time the user tests it.

### Phase 1 — CSV-backed Q&A with verified reasoning surface

- **Goal:** The analyst can upload multiple CSV files, ask a question in natural language, and receive a complete answer package: natural-language answer, result table, follow-up suggestions, and a downloadable CSV — with the full chain visible in the UI.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — ingestion + QA pipeline for multiple CSV uploads with validation, alongside a Pandas-backed analytical runner that produces DataFrames. deps: none
  - `slice-b` (frontend) — multi-file upload UI, chat input, streaming reasoning log, answer/table/chart/report output pane, download actions, scheduled-report registration stub, and DB connection stub. deps: none
- **Key surfaces / files:** `src/api/uploads.py`, `src/api/reports.py`, `src/domain/csv.py`, `src/domain/report.py`, `src/graph/nodes.py`, `src/graph/state.py`, `src/graph/agent.py`, `src/prompts/analyst.md`, `frontend/public/index.html`, `frontend/public/styles.css`, `frontend/public/app.js`, `tests/unit/test_csv_analyst.py`, `tests/integration/test_csv_pipeline.py`, `spec/capabilities/csv-upload-and-qa.md`, `spec/capabilities/named-reports-and-schedules.md`, `spec/data.md`, `spec/api.md`, `spec/ui.md`, `spec/agent.md`
- **Gate command:** `uv run pytest tests/unit -q && uv run pytest tests/integration -q`
- **How the user tests it (handoff seed):** Run `uv run python -m src`; open `http://localhost:8001/app/`; upload 2 CSV files; ask an analytical question; verify answer text, table, follow-ups, and CSV download work. Named reports and schedules surfaces should be clearly labelled stubs in this phase.

### Phase 2 — Live MsSQL connection with low-load query execution

- **Goal:** Add a live MsSQL connection path with secure on-prem connection, schema-aware prompting, generated SQL execution, caching, row budgets, and latency observability — all surfaced in the existing UI by wiring previously stubbed surfaces.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — pyodbc connection manager, schema reflection, SQL generation + validation, safe execution with row caps, simple result cache keyed on query fingerprint, observability spans, and MsSQL-specific retry/backoff. deps: none
  - `slice-b` (frontend + integration) — connection form, schema browser, query-fingerprint details view, cache-hit indicators, latency + DB-load indicators, deployment guide, and `.env` hygiene updates. deps: none
- **Key surfaces / files:** `src/config/settings.py`, `src/db/session.py`, `src/db/models.py`, `src/llm/providers/factory.py`, `src/llm/providers/openrouter.py`, `src/graph/nodes.py`, `src/graph/state.py`, `src/prompts/analyst.md`, `src/api/health.py`, `src/api/runs.py`, `src/api/uploads.py`, `src/api/schedules.py`, `frontend/public/*`, `tests/unit/test_mssql_*.py`, `tests/integration/test_mssql_pipeline.py`, `spec/capabilities/live-mssql-query.md`, `spec/architecture.md`, `spec/data.md`, `spec/api.md`, `spec/ui.md`, `spec/agent.md`, `.env.example`, `README.md`
- **Gate command:** `uv run pytest tests/unit -q && uv run pytest tests/integration -q`
- **How the user tests it (handoff seed):** Run `uv run python -m src`; open `http://localhost:8001/app/`; connect to MsSQL via the UI; inspect schema; ask a question that produces SQL; execute against a large table; verify cache reuse on repeat; observe latency/load indicators; confirm no data leaves the machine.

### Phase 3 — Named reports, rerun, dashboard tiles, real schedules

- **Goal:** Wire the Phase 1 UI stubs for named reports, rerun, schedules, and dashboard tiles into fully functional features with persisted history, scheduler execution, rerun lineage, and dashboard summaries.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — report model + CRUD, schedule model + runner, rerun lineage, dashboard tile aggregation queries, schedule history. deps: none
  - `slice-b` (frontend) — saved reports list, report detail + rerun button, schedule creation/editor, dashboard tile grid, history/audit view. deps: none
- **Key surfaces / files:** `src/db/models.py`, `src/api/reports.py`, `src/api/schedules.py`, `src/api/dashboard.py`, `src/graph/nodes.py`, `src/graph/state.py`, `src/prompts/report.md`, `frontend/public/*`, `tests/unit/test_reports.py`, `tests/unit/test_schedules.py`, `tests/integration/test_reports_pipeline.py`, `spec/capabilities/named-reports-and-schedules.md`, `spec/api.md`, `spec/ui.md`, `spec/data.md`, `spec/agent.md`, `README.md`
- **Gate command:** `uv run pytest tests/unit -q && uv run pytest tests/integration -q`
- **How the user tests it (handoff seed):** Run `uv run python -m src`; open `http://localhost:8001/app/`; create and save a named report; rerun it; create a schedule; observe history in the dashboard; verify outputs are backed by persisted results, not transient memory.
