# Roadmap

## What This Agent Does

A data analyst agent for the Uttar Pradesh Police that lets analysts upload multiple CSV files and ask natural-language questions about the data. In Phase 2 it connects directly to a large Microsoft SQL Server database, routing analytical queries through a DuckDB cache layer to keep DB load low and latency under ~2 seconds for aggregated queries. The agent reasons over schema, generates safe SQL (or uses pandas), executes, and returns a plain-English answer with optional charts — no SQL knowledge required from the analyst.

## Who Uses It

- **Primary user:** Data analysts, crime researchers, and policy officers in the UP Police data unit.
- **Goal:** Self-serve crime, FIR, and operational data exploration without waiting for a DBA to write and run queries. Upload a monthly CSV dump, ask "show me district-wise theft trend last quarter" — get an answer and a chart.

## Core Problem Being Solved

Currently, analysts request reports from a central database team, leading to 24–72 hour turnaround times. CSVs arrive by email, stored in shared drives with no searchable index. There is no safe way for analysts to run ad-hoc SQL against the live MsSQL production database without risking locking or full-table scans. This agent eliminates the bottleneck: it ingests CSVs to a local DuckDB cache, understands schema on its own, and builds optimized queries against either the cache or the live MsSQL backend.

## Success Criteria

- [ ] An analyst uploads 3 CSVs (≤ 50 MB each) and gets a schema summary in under 5 seconds.
- [ ] Asking "how many FIRs registered in Lucknow in 2024?" returns a correct count from uploaded CSVs without any code.
- [ ] MsSQL read-replica connection is configured; the same question routed to live DB returns in < 2 s p95.
- [ ] DuckDB cache automatically refreshes on upload, keeping DB read-load to zero for exploratory queries.
- [ ] Queries that return numeric results display as a chart without extra steps.

## What This Agent Does NOT Do (Out of Scope)

- Write or modify data in the MsSQL production database (read-only).
- Store or process classified/national-security data beyond what analysts already have access to; it does not add a new authorization layer.
- Run ETL pipelines or scheduled data loads (those remain with the data engineering team).
- Approve, escalate, or act on findings — it is an analysis tool, not a decision-maker.

## Key Constraints

- **Latency:** p95 < 2 s for aggregated queries on DB; < 5 s for CSV queries on 50 MB files.
- **DB load:** All exploratory analytical queries must hit DuckDB cache, not MsSQL, unless explicitly routed live.
- **Data residency:** UP Police data stays on-prem or in approved government cloud; no third-party data leaves the boundary.
- **Provider:** LLM must run via a single configured key (Anthropic, Gemini, or OpenRouter — default OpenRouter for cost at scale).
- **Concurrency:** Support 5 simultaneous analyst sessions without DB overload.

## Phases of Development

### Phase 1 — CSV Analyst (core capability, read-only, zero DB dependency)

- **Goal:** Analysts upload multiple CSVs, get schema auto-detected, and ask natural-language questions answered from uploaded data — fully functional, tested, no live DB required.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — CSV ingestion + DuckDB cache, plus the LangGraph node that routes questions through the LLM to generate SQL/pandas answers; deps: none
  - `slice-b` (frontend) — Upload zone, schema browser, chat interface, result/card layout; deps: none (calls same API as slice-a)
  - `slice-c` (prompts + tests) — LLM prompt for SQL generation, unit tests for the ingestion and tool layer; deps: none
- **Key surfaces / files:**
  - Backend writes: `src/db/csv_store.py`, `src/llm/prompts/query.md`, `src/graph/nodes.py`, `src/api/routes_ingest.py`, `src/api/routes_query.py`, `src/graph/state.py`, `src/domain/query.py`
  - Frontend writes: `frontend/public/index.html`, `frontend/public/app.js`, `frontend/public/styles.css`
  - Shared API + DB session + settings unchanged
- **Gate command:** `uv run pytest tests/unit -q && uv run pytest tests/integration -q`
- **How the user tests it (handoff seed):**
  1. Run: `uv run python agent.py --run` → opens at `http://localhost:8001/app/`
  2. Upload two small CSVs (e.g. `fir_2024.csv`, `district_lookup.csv`)
  3. Schema panel shows detected columns + types
  4. Type "How many FIRs in Lucknow?" → see count + a simple bar chart of top-5 districts
  5. "Stub" items NOT yet wired: MsSQL live-query button, refresh-from-DB button — these appear greyed out with label "Coming in Phase 2"

### Phase 2 — Live MsSQL Connection (with DuckDB cache)

- **Goal:** Connect to MsSQL read replica; route queries through DuckDB cache for sub-2-second analytical response; cache auto-refreshes on analyst request.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — MsSQL connector (pyodbc), DuckDB ↔ MsSQL sync, live-query routing logic; deps: Phase 1 complete
  - `slice-b` (frontend) — DB connection panel, source toggle (CSV cache / live DB / both), refresh button; deps: none on frontend wiring, calls same API
- **Key surfaces / files:**
  - Backend writes: `src/db/mssql_connector.py`, `src/db/cache_sync.py`, `src/api/routes_db.py`, `src/graph/nodes.py`
  - Frontend writes: `frontend/public/index.html`, `frontend/public/app.js`
- **Gate command:** `uv run pytest tests/integration -q`
- **How the user tests it (handoff seed):**
  1. Open the app, enter MsSQL connection string in Settings panel
  2. Click "Connect" → status badge turns green with schema count
  3. Click "Refresh Cache" → DuckDB mirrors live schema
  4. Ask a live-DB question (toggle source to "Live") → answer returns with `source: mssql` and a ~1.5 s response time shown

### Phase 3 — Production Hardening (auth, observability, SLO)

- **Goal:** RBAC (analyst vs admin), query audit log, rate limiting, SLO monitoring dashboard, and a production Docker image.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — auth middleware, query audit log table, rate limiter
  - `slice-b` (frontend) — login screen, admin dashboard, SLO widget
- **Gate command:** `uv run pytest tests/ -q`
- **How the user tests it (handoff seed):** full deployment to staging, login as analyst, run a query, check audit log row, check SLO met.
