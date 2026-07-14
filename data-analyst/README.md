# Data Analyst Agent — v0.1 (Phase 1)

Plain-English question → read-only SQL → Chart.js chart, against Microsoft SQL
Server (Azure SQL Edge). Raw rows never reach the LLM — only schema + aggregate
profile stats. All app code lives under `data-analyst/`.

## Prerequisites

- .NET 8 SDK on PATH: `export PATH="$HOME/.dotnet:$PATH"`
- Docker (colima) with Azure SQL Edge at `localhost:1433` (sa / Str0ngP@ssw0rd!)
- Node 18+ / npm
- Repo-root `.env` (copy from `.env.example`). **Set `AGENT_OPENROUTER_API_KEY`**
  — the live query path needs it. Build, tests, and seed do NOT need it.

## Run

```bash
# 1. Seed the warehouse (creates WarehouseDemo + ~100k FactSales rows)
cd data-analyst && dotnet run --project seed

# 2. Backend API (port 8001)
cd data-analyst/backend && dotnet run

# 3. Frontend SPA (port 5173, proxies /api → 8001)
cd data-analyst/frontend && npm install && npm run dev
```

Open http://localhost:5173 and ask e.g.
*"Show me monthly sales amount by channel as a line chart"*.

## Test (no secrets needed)

```bash
cd data-analyst/tests && dotnet test
```

Covers: SQL deny-list enforcement, Chart.js shape transform, schema-profile
serializer. 22 tests.

## Endpoints

- `POST /api/query` — `{question}` → plan/chartType/sql/reasoning/data
- `POST /api/query/stream` — SSE stream of plan → sql → steps → data → done
- `GET /api/schema` — cached warehouse schema + aggregate profiles
- `GET /api/audit?date=YYYY-MM-DD` — runs + daily token total
- `GET /api/health` — `{status:"ok"}`

## Safety invariants

- Deny-list (INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/GRANT/EXEC/MERGE, CI) +
  enforced `TOP 1000` + no `SELECT *`, before any execution.
- LLM payload = schema + aggregate stats only; query results never sent to LLM.
- Every run audited to SQLite (`backend/bin/.../audit.db`).

## .env note

`AGENT_OPENROUTER_API_KEY` is required only for the live query path. If empty,
`/api/query*` return 503 "LLM not configured"; the app still builds, tests pass,
and seed runs.
