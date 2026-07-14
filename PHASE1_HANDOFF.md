# Phase 1 — Test Handoff

## Project root
`/Users/sai/Workspace/Code/zero-shot-sdd-harness-hermes` (branch
`feature/data-analyst-v0.1`). App code under `data-analyst/`.

## Run commands
```bash
export PATH="$HOME/.dotnet:$PATH"
# Seed (already run once; idempotent — safe to re-run):
cd data-analyst && dotnet run --project seed
# Backend (parent owns this lifecycle — DO NOT auto-start in CI):
cd data-analyst/backend && dotnet run          # http://localhost:8001
# Frontend:
cd data-analyst/frontend && npm install && npm run dev   # http://localhost:5173
```

## Exact core path to test (the gate)
1. Ensure repo-root `.env` has a real `AGENT_OPENROUTER_API_KEY`.
2. Start backend, then frontend.
3. Open http://localhost:5173.
4. Type: **"Show me monthly sales amount by channel as a line chart"** → Ask.
5. Expected: reasoning streams in (plan → SQL → Step N of M), then a **line
   chart** renders with one series per channel across months. Daily token total
   updates in the header. SQL shown is a read-only `SELECT TOP …` (no SELECT *).

## Offline gate (no secrets)
```bash
cd data-analyst/tests && dotnet test    # 22 tests pass
```

## What is REAL vs STUBBED
- REAL: seed (100k rows in live Azure SQL Edge), schema introspection +
  aggregate profiling, SQL deny-list + TOP enforcement, read-only execution,
  chart shaping, SQLite audit, SSE streaming, OpenRouter SQL generation.
- STUBBED (labelled in UI, non-functional): "History" (Phase 2), "Export CSV"
  (Phase 3).

## DB seed confirmation
`DimDate=730, DimStore=20, DimProduct=200, DimChannel=4, FactSales=100000`.

## Blocker / pending
- LIVE LLM gate is pending the parent adding `AGENT_OPENROUTER_API_KEY` to
  `.env`. With it empty, `/api/query*` return 503 "LLM not configured"; build +
  tests + seed are unaffected.
- OpenRouter is called with the standard `/api/v1/chat/completions` + JSON
  `response_format`; if the chosen model ignores `response_format`, the parser
  also strips markdown fences as a fallback. If the model still returns
  non-JSON, that surfaces as a 400/stream error (flag for parent).

## Gate command the parent will run
Live: start backend + frontend, run the core path above.
Offline proof: `cd data-analyst/tests && dotnet test`.
