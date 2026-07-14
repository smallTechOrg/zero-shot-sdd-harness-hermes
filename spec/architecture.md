# Architecture — Data Analyst Agent

## Stack

- **Backend:** ASP.NET Core 8 Web API (Minimal API), C# / .NET 8 SDK.
- **DB driver:** Microsoft.Data.SqlClient 5.2.2 (native arm64 macOS verified).
- **Warehouse:** Microsoft SQL Server — Azure SQL Edge in Docker (Phase 1).
- **Audit store:** SQLite via Microsoft.Data.Sqlite.
- **LLM:** OpenRouter chat completions (`AGENT_LLM_MODEL`, default
  google/gemini-flash-1.5). Streaming SSE.
- **Env loading:** DotNetEnv reads repo-root `.env` at app startup.
- **Frontend:** React 18 + Vite + Chart.js via react-chartjs-2.
- **Tests:** xUnit.

## Component Layout

```
data-analyst/
  backend/    ASP.NET Core 8 Minimal API + Services
  seed/       .NET console warehouse seeder
  frontend/   React + Vite + Chart.js SPA
  tests/      xUnit unit tests
```

## Data Flow (core path)

1. UI POSTs `{question}` to `/api/query`.
2. SchemaService returns cached warehouse schema + aggregate profiles.
3. SqlGenerationService builds a system prompt (schema + profiles ONLY, no rows)
   and calls OpenRouter, receiving strict JSON `{plan, chartType, sql, reasoning,
   clarification}`.
4. If `clarification` present → return it; UI asks the user. No SQL runs.
5. SqlExecutionService validates SQL (deny-list + enforced TOP, no SELECT *),
   executes read-only, returns rows to ChartService only (never the LLM).
6. ChartService shapes rows into Chart.js `{labels, datasets}`.
7. AuditService records the run to SQLite.
8. `/api/query/stream` (SSE) streams plan → sql → reasoning steps.

## Privacy & Safety Boundaries

- LLM payload = schema + profile stats. Enforced by construction: query results
  are never passed to any LLM call.
- Deny-list + TOP enforcement run server-side before execution.
