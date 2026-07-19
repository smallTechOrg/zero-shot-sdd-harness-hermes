# Roadmap

> Spec-driven source of truth. When code and spec disagree, the spec wins.

---

## What This Agent Does

A read-only, natural-language data analyst over a **live Microsoft SQL Server** database. The user types a plain-English question into a browser UI; the agent translates it into a single, safe `SELECT` and runs it against MSSQL — returning a small result table, the SQL it ran, and a per-question token/cost indicator. Every question is logged locally for audit.

## Who Uses It

A single Windows developer / analyst on a local machine with a working `master` MSSQL instance reachable via Windows Integrated Auth (Trusted_Connection). Single-user; no multi-tenancy in scope.

## Core Problem Being Solved

A large MSSQL database is expensive to query naively (`SELECT *` on wide tables, unconstrained joins). The operator wants to ask questions in plain English, see the SQL the system generated for verification, and never pay for runaway queries — without skill-up on T-SQL or instrumenting queries by hand.

## Success Criteria

- [ ] A user can type *"how many tables are in the database?"* and get back a real row count from `INFORMATION_SCHEMA.TABLES` in under 15s.
- [ ] Every `/api/ask` request writes one row to the local audit log (`data/agent.db`).
- [ ] The generated SQL is **always**: (a) a single SELECT, (b) bounded by `TOP N` or LIMIT when applicable, (c) free of `INSERT/UPDATE/DELETE/DDL` keywords and `;`-stacked statements.
- [ ] The MSSQL server is touched **exactly once per request** (no schema re-introspection per request — schema cached in-process on startup).
- [ ] The `/health` endpoint returns ok on boot.
- [ ] The UI loads at `http://localhost:8001/app/`, accepts input, shows the result table.

## What This Agent Does NOT Do (Out of Scope)

- Writes/DDL: never. The validator blocks.
- Multi-DB, multi-DB-connection, multi-server.
- Multi-turn session memory within a UI session.
- Authentication, multi-tenancy, role-based access control.
- Charts/exports (Phase 2).
- Conversation history sidebar (Phase 2).
- Caching: every Ask hits the live MSSQL. Optimisation is via *smart query generation* only.
- Production hardening: load balancing, retries beyond one, observability dashboards.

## Key Constraints

- **Latency:** ≤15s per question, configurable via `AGENT_MSSQL_QUERY_TIMEOUT_SEC`.
- **DB load:** one query per request; bounded; trust-bounded by prompt to push filters down.
- **Read-only:** enforced in two layers (system prompt + regex validator).
- **Real-key testing:** Gemini API key from `.env` is required for the Phase 1 gate.
- **No fake data:** the user's "test path" must hit the actual MSSQL on local `master`.

## Phases of Development

> Phase 1 is the smallest user-testable win. It is real on the tested path; everything else is clearly-labelled stubs. Audit + read-only + token-loud are wired from day one.

### Phase 1 — First Win (read-only NL analyst over live MSSQL)

- **Goal:** the user can ask plain-English questions about their local `master` MSSQL in a browser and get a real result table back, see the SQL that ran, and see growing token usage — *all against their real database, never a mock, never a fixture*.
- **Independent slices (parallel build units):**
  - `slice-spec` (design) — all of `spec/` filled in (this canvas)
  - `slice-scaffold` (build) — `src/mssql_analyst/`, `frontend/`, `pyproject.toml`, `alembic.ini`, `alembic/`, `.env.example`, first commit + push + PR
  - `slice-tooling` (backend) — `pyodbc` MSSQL connector + safety validator + `last_50` audit DB schema + alembic migration
  - `slice-graph` (backend) — `graph/nodes.py`, `graph/runner.py`, `graph/edges.py`, `graph/agent.py` for NL→SQL→execute→return (one Gemini call), `LLMClient`/`GeminiProvider`, system prompts
  - `slice-api` (backend) — `/health`, `/v1/answer` (renamed to `/api/ask` in this project), `/api/usage`, `/` root banner, `/app/` mount
  - `slice-frontend` (frontend) — Next.js static export: question form, result table, collapsible SQL, "tokens used so far" badge, last-50 sidebar placeholder
  - `slice-tests` (tests) — unit SQL validator + integration `/v1/answer` + `/api/usage` real-MSSQL + Playwright smoke
- **Key surfaces/files:**
  - `spec/*` — spec-writer fills all files
  - `src/mssql_analyst/{config,db,domain,graph,llm,tools,api,observability,prompts}/`
  - `frontend/src/app/{page.tsx,layout.tsx,globals.css}` and `frontend/{next.config.js,postcss.config.js,package.json,tsconfig.json}`
  - `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/0001_initial.py`
  - `tests/unit/`, `tests/integration/`, `tests/e2e/`
  - `pyproject.toml`, `alembic.ini`, `.env.example`, `README.md`
- **Gate command:** the EXACT sequence that proves Phase 1 works against real MSSQL + real Gemini:
  ```bash
  # from repo root, in order:
  .venv/bin/python -m uv pip install -e ".[dev]"   # sync deps (idempotent)
  .venv/bin/python -m alembic upgrade head         # create audit DB tables
  cd frontend && NODE_OPTIONS=--no-experimental-webstorage npm ci && NODE_OPTIONS=--no-experimental-webstorage npm run build && cd ..
  cd tests/e2e && npm ci && npx playwright install --with-deps chromium && cd ../..
  .venv/bin/python -m pytest tests/ -v -m 'not live_marker'  # + live tests if GEMINI_API_KEY set
  ( .venv/bin/python -m src & sleep 3 && \
      curl -sf http://localhost:8001/health && \
      curl -sf http://localhost:8001/app/ | head -20 && \
      curl -sf -X POST http://localhost:8001/api/ask \
        -H 'Content-Type: application/json' \
        -d '{"question":"how many tables are in master?"}' )
  ```
  The user will **not** run any of this — the root session does, then presents ONE URL.
- **How the user tests it (handoff seed):**
  - Open **`http://localhost:8001/app/`**
  - Type: *"how many tables are in master?"*
  - Click **Ask**
  - **Expected:** a result table appears (≥1 row, column `table_count` with a real number), latency chip shows ms and rows, "tokens used so far: N" badge increases from the prior value.
  - **Click "Show SQL"** → see the generated `SELECT` it ran.
  - **Stubs (do not mistake for bugs):** the right sidebar reads *"History (last 50) — coming in Phase 2"*. Multi-DB toggles, charts, exports, and follow-up chat are all disabled/greyed-out and labelled "coming in Phase 2/3".

### Phase 2 — Stack completion (real features behind the stubs)

- **Goal:** turn every Phase-1 stub into a real, working capability.
- **Independent slices:** last-50 sidebar with pagination, token/cost charts (tokens-per-day sparkline), CSV export of result tables, anomaly highlighting (rows whose value deviates from median).
- **Gate command:** `uv run pytest tests/ -v` + Playwright `npx playwright test tests/e2e/`.
- **How the user tests it:** return to `http://localhost:8001/app/`, refresh, see a populated history sidebar; export a result table; hover a row to flag an anomaly.

### Phase 3 — Agentic upgrade (smart query generation, resilience)

- **Goal:** when the natural-language question is ambiguous or schema spans many tables, the agent plans and self-corrects (one retry with validator feedback) instead of returning a single-shot result.
- **Independent slices:** NL→SQL self-retry on validator rejection, token-aware row-cap adjustment, structured observability surface (per-run timings to stdout JSON).
- **Gate command:** `uv run pytest tests/ -v` against a deliberately-hard question (e.g. *"count firs grouped by district"*) that requires the retry path.
- **How the user tests it:** type a question requiring a join; observe attempt-only-once if first guess is right; see latency stay under 15s.

### Phase 4 — Polish & ship

- **Final drift audit, README verification, PR finalisation.**

### Architectural notes (from `spec/architecture.md`)

- Stack: Python 3.11+, FastAPI, LangGraph, pyodbc, SQLAlchemy (audit DB only), google-genai (Gemini), Next.js 15 + Tailwind v4 (static export), SQLite for audit log.
- Reuses the proven cctns_analyst scaffold layout under the `mssql_analyst` package name. **Mock mirror is excluded from Phase 1** — the live MSSQL is the only data source from day one.
