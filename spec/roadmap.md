# Roadmap

## What This Agent Does

A data analyst agent for the Uttar Pradesh Police that answers natural-language questions over police data — starting from uploaded CSV exports (FIRs, daily diaries, incident logs, offence registers) and later extending to direct read-only queries against a large centralised MsSQL database. It generates auditable answers plus downloadable result sets, charts, and the raw SQL or pandas code behind the answer. It is built for investigators, analysts, and command leadership who cannot write SQL but need trustworthy, traceable numbers from police data.

## Who Uses It

- Investigating officers at a district — ad-hoc queries during case work.
- Dedicated data analysts / research cells — heavy repeated usage.
- Command-level leadership (SSP / DIG) — occasional strategic queries.
- Occasional users across a wide range of ranks and SQL literacy.

## Core Problem Being Solved

Today the same questions — "how many vehicle thefts in Lucknow last month?", "which police stations show the highest violent-crime trend this quarter?" — require either knowing SQL, waiting for a data analyst, or exporting CSVs into Excel and manually pivoting. The agent removes that friction, keeps answers auditable, and reduces ad-hoc load on the live database via caching and offline (CSV) mode.

## Success Criteria

- [ ] A user can upload one or more CSVs, ask a natural-language question, and get a table-backed answer plus CSV download.
- [ ] The answer includes the generated SQL / pandas code, row count, tables touched, and latency.
- [ ] When the live MsSQL DB is unreachable, the agent pivots transparently to the locally cached snapshot without an error.
- [ ] For a core analytical question on 10M-row live tables, a cached or indexed answer returns in under 3 seconds end-to-end.
- [ ] Every query is auditable: timestamp, user, question, data sources, SQL/code, row count, latency, token spend.
- [ ] The Phase 1 live-server smoke against the real LLM key passes and the human test gate approves CSVs + Q&A.

## Key Assumptions (from intake, cannot ask user)

> **Assumed:** "All of the above" for all session models, memory, error handling, output forms, proactive hints, scale, privacy, reliability, transparency, cost signals, progress signals, and audit — i.e. the agent must support every option in each dimension where the user selected all.
> **Assumed:** "All of the above" for stack: baseline Python + FastAPI + SQLite for CSV mode (dev); PostgreSQL for query state / metadata / sessions / audit trail; MsSQL via pyodbc for live production queries.
> **Assumed:** LLM provider is **NVIDIA NIM** using its OpenAI-compatible endpoint.
> **Assumed:** NIM base URL, model slug, and API key will be supplied by the user in `.env` via standard `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` style variables added by the build.
> **Assumed:** Phase 1 delivers the smallest end-to-end win: single CSV upload + one Q&A turn with table + CSV export + generated SQL + audit log. No live MsSQL in Phase 1.
> **Assumed:** Phase 2 adds live MsSQL read-only access with cache-first fallback.
> **Assumed:** Role-based access control, junior-sensitive warnings, and exportable audit reports are included from Phase 1 (cannot be deferred — user selected all).

## What This Agent Does NOT Do (Out of Scope)

- Write to the MsSQL database. All live queries are read-only.
- Handle non-tabular unstructured data without a parser step outside Phase 1 scope.
- Replace RMS / core police systems — it is an analyst layer on top of exports / read replicas.
- Real-time alerting / streaming ingestion (explicitly excluded for now).

## Key Constraints

- **Privacy & residency:** rows must never leave the police network or approved boundary.
- **Cost:** prefer OSS and caching; minimise LLM token spend.
- **Latency:** cached / small-CSV answers must feel near-instant; large live queries tolerate a few seconds.
- **Reliability:** when the live DB is slow / under maintenance, the agent must stay usable via offline (CSV) or cached snapshot mode.
- **Production bar:** audited, error-resilient, role-aware, with a full audit trail.

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** The tested path is CSV upload + one natural-language question → answer with table + CSV download + generated SQL + audit log entry. All other surfaces are clearly-labelled non-functional stubs.

### Phase 1 — CSV Analyst (offline-first core loop)

- **Goal:** One working end-to-end analyst loop over uploaded CSVs, with a real LLM call and an audit log.
- **Independent slices:**
  - `slice-a` (backend) — CSV ingestion, schema inference, pandas-backed SQL runner, answer assembly, audit logging.
  - `slice-b` (frontend) — upload form, Q&A panel, results table, CSV download, stubs for MsSQL + charts + saved workspaces.
- **Key surfaces / files:**
  - Backend: new capability module under `src/graph/nodes.py` (CSV path), `src/prompts/csv_analyst.md`, new API routes in `src/api/runs.py` or a new `src/api/csv.py`, DB models in `src/db/models.py`, migrations in `alembic/`, tests in `tests/unit` and `tests/integration`.
  - Frontend: `frontend/public/index.html`, `frontend/public/styles.css`, `frontend/public/app.js`.
- **Gate command (real LLM + real SQLite/pandas flow):** `uv run pytest tests/integration/test_csv_analyst.py -q`
- **How the user tests it (handoff seed):**
  - Run `.venv/bin/python -m src` and open `/app`.
  - Upload a small CSV with 2 000–5 000 rows of dummy crime data.
  - Ask "How many rows in this file?" and "Which district has the highest count by offence?"
  - Expected: table answer, CSV download button works, an audit row is created, "Live DB" tab shows a stub badge.

### Phase 2 — Live MsSQL + Cache Fallback

- **Goal:** Add read-only live MsSQL access with a local cache so the agent answers quickly even when the production DB is busy or unreachable.
- **Independent slices:**
  - `slice-a` (backend) — MsSQL read-only adapter via pyodbc / asyncodbc / SQLAlchemy+MSSQL, schema introspection, cache materialisation, cache invalidation policy.
  - `slice-b` (frontend) — data-source selector (CSV vs Live DB), cache-status indicator, connection-test output.
- **Key surfaces / files:**
  - Backend: new DB module `src/db/mssql.py`, cache tables, new nodes/edges in `src/graph/nodes.py` for live-vs-cache routing.
  - Frontend: new controls in `frontend/public/app.js` and markup.
- **Gate command:** `uv run pytest tests/integration/test_mssql_cache.py -q`
- **How the user tests it (handoff seed):**
  - With MsSQL connection configured in `.env`, ask a known count-level question.
  - Disconnect the MsSQL endpoint; confirm the same question still returns from the local cache with a "served from cache" indicator.
  - Reconnect; confirm new queries hit the live DB and refresh the cache.

### Phase 3 — Polish, Roles, and Production Hardening

- **Goal:** Role enforcement, charting/export richness, saved workspaces, supervisor audit export, and production resilience.
- **Independent slices:**
  - `slice-a` (backend) — RBAC middleware, per-query audit export endpoint, chart data API, saved-query / workspace tables.
  - `slice-b` (frontend) — login-role-aware UI, chart renderer, supervisor audit export panel, saved-workspace manager.
- **Key surfaces / files:**
  - Backend: auth guards, PDF/CSV export, additional tests plus load / failure-mode tests.
  - Frontend: charts, export buttons, saved workspace list.
- **Gate command:** `uv run pytest tests -q`
- **How the user tests it (handoff seed):**
  - Log in as supervisor; export full audit CSV.
  - Log in as investigator; confirm junior-sensitive warning is shown on flagged queries.
  - Verify charts render for a time-series question.
