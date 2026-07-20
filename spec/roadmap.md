# Roadmap

## What This Agent Does
The UP Police Data Analyst agent enables authorized officers to query FIR/CCTNS, HR/personnel, and logistics/property data in a read-only Microsoft SQL Server database using natural language. It returns answers with the executed SQL, timing, and optional visualizations (charts/tables), while ensuring raw data never leaves the DB and all interactions are audited per PVP/IT Act requirements.

## Who Uses It
Primary users are IPS officers (senior leadership), SHOs (station house officers), and beat constables who need ad-hoc insights during shifts or for reports. The analytics team uses it for scheduled queries and dashboard building.

## Core Problem Being Solved
Manual SQL querying is slow, error-prone, and limited to technical users. Officers currently rely on the analytics team for data requests, causing delays. This agent puts safe, governed data access directly in officers' hands via a chat interface.

## Success Criteria
- [ ] Officers can ask natural-language questions about crime, personnel, or logistics data and receive accurate answers with SQL and timing within 15 seconds p50.
- [ ] Raw database rows are never included in LLM prompts; only schema and aggregates are used unless explicitly opted-in for disambiguation.
- [ ] Every query is logged immutably (user ID, question, SQL, row count, latency, result hash) for audit and compliance.
- [ ] The agent handles ambiguous queries by requesting clarification or showing a refined question before execution.
- [ ] Saved/pinned reports persist across sessions and can be shared within teams.

## What This Agent Does NOT Do (Out of Scope)
- Write or modify data in the database (strictly read-only).
- Provide real-time alerting or predictive analytics (Phase 2+).
- Integrate with external systems like crime mapping or facial recognition (future phases).
- Replace the need for approved analytics team reports; it supplements ad-hoc inquiry.

## Key Constraints
- Latency: p50 ≤ 15 seconds end-to-end (user question to answer display).
- DB load: Minimize via schema-only LLM context by default, mandatory LIMIT/TOP clauses, and connection pooling (max 5).
- Privacy: Sensitive PII (victims, addresses, chargesheets) never leaves the SQL Server; audit logs are tamper-evident.
- Access: Role-based row-level filtering (district/unit) enforced at the DB layer via service policies; officer identity via header.
- Compliance: Full audit trail meets PVP Act and IT Act requirements for data access logging.

## Phases of Development

### Phase 1 — Core Inquiry & Pinning
- **Goal:** Enable a single natural-language question → SQL → executed → answered flow with collapsible SQL/chart/table panels and a sidebar of recent/pinned reports.
- **Independent slices (parallel build units):**
  - `slice-schema` (backend) — introspect MSSQL schema and cache it for LLM context; deps: none
  - `slice-agent-loop` (backend) — implement the planner→sql_writer→validator→executor→answer_writer graph; deps: slice-schema
  - `slice-audit` (backend) — add immutable audit table and logging middleware; deps: none
  - `slice-frontend` (frontend) — chat input, collapsible answer panels (SQL/chart/table), sidebar with recent queries and pinned reports; deps: none
- **Key surfaces / files:**
  - Backend: `src/db/mssql/` (schema introspection, connection), `src/graph/` (agent nodes/edges), `src/prompts/data_analyst.md`, `src/api/analyst.py` (endpoint), `src/db/models.py` (audit table), `alembic/` (migration for audit table)
  - Frontend: `frontend/public/` (index.html, styles.css, app.js for chat UI)
- **Gate command:** `uv run alembic upgrade head && uv run pytest tests/phase1 -v`
- **How the user tests it (handoff seed):**
  1. Start the server: `.venv/bin/python -m src` (or `uv run python -m src`) from repo root.
  2. Open `http://localhost:8001/app/` in a browser.
  3. Type a natural-language question like "Show total FIRs registered last week in Lucknow district".
  4. Verify the agent returns an answer with:
     - The executed SQL (collapsible panel) with a `LIMIT` or `TOP` clause.
     - Row count and timing.
     - Optional chart/table if the result is suitable.
     - The question and answer appear in the sidebar under "Recent".
  5. Click the pin icon to save the query; verify it appears under "Pinned" and persists after a page refresh.
  6. Confirm no raw data appears in the agent's thinking (visible via observability logs) — only schema or aggregates.

### Phase 2 — Sharing & Visualization
- **Goal:** Wire the pinned reports into real functionality: export, scheduled queries, and richer visualizations (time-series, heatmaps).
- **Independent slices (parallel build units):**
  - `slice-export` (backend) — add CSV/XLSX export for pinned reports; deps: slice-agent-loop
  - `slice-scheduler` (backend) — add cron-like scheduling for pinned reports; deps: slice-agent-loop
  - `slice-viz` (backend) — add chart-type selection (bar, line, pie, heatmap) and rendering; deps: slice-agent-loop
  - `slice-frontend-viz` (frontend) — enhance answer panels with chart controls and export buttons; deps: slice-frontend
- **Key surfaces / files:**
  - Backend: new API endpoints for export/scheduling, chart generation logic.
  - Frontend: updated collapsible panels with chart type dropdown and export.
- **Gate command:** `uv run pytest tests/phase2 -v`
- **How the user tests it (handoff seed):**
  1. After Phase 1 is working, create a pinned report.
  2. Click "Export" to download CSV/XLSX; verify file contains expected data.
  3. Set a schedule (e.g., daily at 9 AM) and verify the system records it.
  4. Change chart type in the panel and verify the visualization updates accordingly.
  5. Confirm audit logs still capture all interactions.

### Phase 3 — Role-Based Access & Advanced Audit
- **Goal:** Implement district/unit row-level security, JWT-based officer authentication, and real-time alerting on anomalous patterns (e.g., sudden spike in complaints).
- **Independent slices (parallel build units):**
  - `slice-auth` (backend) — validate JWT tokens and map to officer ID/unit; deps: slice-agent-loop
  - `slice-rls` (backend) — add row-level security via MSSQL session context or views; deps: slice-auth
  - `slice-alert` (backend) — add anomaly detection rules and notification hooks; deps: slice-agent-loop
  - `slice-frontend-auth` (frontend) — login page and unit/district selector; deps: slice-frontend
- **Key surfaces / files:**
  - Backend: auth middleware, RLS implementation, alert rule engine.
  - Frontend: login UI and context-aware query routing.
- **Gate command:** `uv run pytest tests/phase3 -v`
- **How the user tests it (handoff seed):**
  1. Log in as an officer from a specific district.
  2. Ask a question that should return only data from that district (e.g., "Show pending cases").
  3. Verify results are filtered to the officer's unit.
  4. Attempt a cross-district query and confirm it returns only permitted data or an error.
  5. Trigger an anomaly (e.g., upload a test CSV with a spike) and verify an alert is generated.
  6. Confirm audit logs record the officer ID for every query.