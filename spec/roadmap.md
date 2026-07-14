# Roadmap — Data Analyst Agent

## What This Agent Does

A single-user data-analyst agent that turns a plain-English question about a
reporting data warehouse into read-only SQL, executes it against Microsoft SQL
Server (Azure SQL Edge in Phase 1, an 8 TB warehouse in production), and renders
the result as a Chart.js chart (bar/line/pie). The agent PLANS the analysis and
picks a chart type before writing SQL, streams its reasoning to the UI, and
NEVER sends raw data rows to the LLM — only the warehouse schema and aggregate
profile metadata.

## Who Uses It

A single analyst running a few ad-hoc queries per day, refining questions in a
session.

## Core Problem Being Solved

Replaces the manual write-SQL-then-build-a-chart loop against a huge warehouse
with a conversational plan → SQL → chart pipeline that is read-only-safe and
privacy-preserving (no raw rows to the LLM).

## Success Criteria

- [ ] Plain-English question → correct Chart.js chart on the core path.
- [ ] Generated SQL is rejected if it contains any mutating token.
- [ ] Raw rows are never included in any LLM request payload.
- [ ] Every run is audited to SQLite (question, plan, sql, chart, rows, tokens).
- [ ] Reasoning streams to the UI (SSE) with a running daily token total.

## What This Agent Does NOT Do (Out of Scope for Phase 1)

- No tables, CSV export, or saved query history (later phases).
- No multi-user auth. No write operations of any kind.
- No dashboard composition / multiple charts per question.

## Key Constraints

- Read-only NON-NEGOTIABLE: deny-list INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/
  GRANT/EXEC/MERGE (case-insensitive) + enforced TOP row limit, never SELECT *.
- Privacy: only schema + aggregate profile stats to the LLM; never raw rows.
- Scale: every query capped with TOP; warehouse is 8 TB in production.

## Phases of Development

### Phase 1 — Ask → Plan → SQL → Chart (core path)

- **Goal:** Type a plain-English question, agent plans + generates read-only SQL,
  runs it, streams reasoning, and renders the correct Chart.js chart.
- **Independent slices:**
  - `backend` — ASP.NET Core 8 Web API + SchemaService, SqlGenerationService
    (OpenRouter), SqlExecutionService (deny-list + TOP), ChartService,
    AuditService (SQLite). deps: none
  - `seed` — .NET console that creates WarehouseDemo star schema + ~100k rows.
    deps: none
  - `frontend` — React + Vite + Chart.js SPA (question box, reasoning panel,
    chart, step counter, daily token total, clarification). deps: backend API shape
- **Key surfaces:** `data-analyst/backend/`, `data-analyst/seed/`,
  `data-analyst/frontend/`, `data-analyst/tests/`.
- **Gate command:** `cd data-analyst/tests && dotnet test` (offline, no secrets)
  plus live core path: start backend + frontend, ask "Show me monthly sales
  amount by channel as a line chart".
- **How the user tests it:** see `PHASE1_HANDOFF.md`.

### Phase 2 — History & saved queries (future)

- Persist and browse past runs; re-run saved questions.

### Phase 3 — Tables + CSV export, multi-chart dashboards (future)

### Phase 4 — Production warehouse cutover + query cost governance (future)
