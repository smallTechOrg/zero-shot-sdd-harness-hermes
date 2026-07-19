# MSSQL Analyst

A read-only, natural-language data analyst over a live Microsoft SQL Server database. Type a plain-English question; the agent translates it to a single bounded `SELECT`, runs it on your local MSSQL (Windows Integrated Auth), and returns a small result table — alongside the SQL it generated and a running token counter.

Single-user, local. Built spec-first from `spec/`. Phase 1 done; Phase 2/3 gated behind stubs in the UI.

> **All commands run from the repo root.** The repo root IS the agent project — there is no subdirectory to `cd` into.

---

## Quick start (Phase 1)

### 1. Configure `.env`

`.env` already exists. Edit it so the MSSQL block looks like (truth to your local setup):

```ini
# Gemini (already populated in your environment)
AGENT_GEMINI_API_KEY=...

# Phase 1 — live MSSQL via Windows Integrated Auth
AGENT_MSSQL_HOST=localhost
AGENT_MSSQL_DB=master
AGENT_MSSQL_DRIVER=ODBC Driver 17 for SQL Server   # Use 17 or 18 if installed
AGENT_MSSQL_INTEGRATED_AUTH=true
AGENT_MSSQL_USER=
AGENT_MSSQL_PASSWORD=
AGENT_MSSQL_QUERY_TIMEOUT_SEC=15
AGENT_MSSQL_ROW_CAP=1000

PORT=8001
```

### 2. Sync deps + create the audit-log DB

```bash
uv sync
uv run alembic upgrade head
uv run alembic current              # must show a revision, not blank
```

### 3. Build the frontend (one-time, then re-build only when `frontend/` changes)

```bash
cd frontend && npm install && npm run build && cd ..
```

The npm scripts are intentionally **bare** (`next build`, no inline `NODE_OPTIONS=`) because Windows `cmd` won't parse inline env-var prefixes; Node ≥25 SSR safety is handled by the runtime pinning the dependency matrix enforces (Next 15.5.4 is built on Node 22/24). If you must use Node ≥25, run with `NODE_OPTIONS=--no-experimental-webstorage npx next build` instead.

### 4. Run the server

```bash
uv run python -m src
```

- Open **http://localhost:8001/app/** for the UI.
- Open **http://localhost:8001/health** for liveness + mode.
- Open **http://localhost:8001/docs** for OpenAPI / Swagger.

### 5. Try it

Type: *"how many tables are in master?"* and click **Ask**.

You should see:
- A result table (≥ 1 row).
- The `SELECT` it ran (via the **Show SQL** toggle).
- The "tokens used" badge in the header increasing.

Each question writes one row to `data/agent.db` (see `GET /api/usage`).

---

## Endpoints

| Method | Path           | Purpose                                              |
|--------|----------------|------------------------------------------------------|
| GET    | `/`            | Banner with service + UI + API URLs                  |
| GET    | `/health`      | Liveness + `mssql_mode` (live / unconfigured) + model |
| POST   | `/api/ask`     | One question → `{sql, columns, rows, row_count, latency_ms, tokens_used, status, sql_attempts}` |
| GET    | `/api/usage`   | Running totals + last-5 questions from the audit log |
| GET    | `/app/...`     | Static UI (Next.js export)                            |
| GET    | `/docs`        | Swagger UI                                           |

See **`spec/api.md`** for the full contract + error envelope.

---

## Tests

```bash
uv run pytest tests/unit/ -v          # no env needed — pure unit
uv run pytest tests/integration/ -v   # uses stub LLM + stub connector (no live deps)
uv run pytest tests/ -v               # full suite
```

The integration tests are wired to a stubbed LLM provider and a stubbed MSSQL connector so they run on any machine without a live MSSQL.

Playwright E2E (planned for the Stage 3 human gate):

```bash
cd tests/e2e && npm ci && npx playwright install --with-deps chromium && npx playwright test tests/e2e/ --reporter=line
```

---

## Architecture (Phase 1)

- **`src/mssql_analyst/`** — the Python package.
  - `api/` — FastAPI routers (`/health`, `/api/ask`, `/api/usage`, root banner).
  - `graph/` — LangGraph state machine: `nl_to_sql → execute_sql → finalize | handle_error`.
  - `llm/` — single-boundary LLM client + Gemini provider.
  - `tools/` — the MSSQL connector (`pyodbc`, Windows Integrated Auth, cached schema) and the SQL safety validator.
  - `db/` — SQLite audit log models + session.
  - `observability/` — structured JSON logging via structlog.
- **`frontend/`** — Next.js 15 + Tailwind v4 static export, mounted at `/app/`.
- **`spec/`** — the product spec (single source of truth).
- **`tests/`** — unit + integration. E2E (Playwright) wired for the gate.

Read **`spec/architecture.md`** for the data flow + layer map.

---

## What's real in Phase 1

- Real Gemini (auto-detected).
- Real MSSQL (Windows Integrated Auth against your `master`) on **every** question.
- Real audit-log write to `data/agent.db`.
- Token counter and "Show SQL" toggle on the UI.
- Two-layer read-only enforcement (system prompt + regex validator).

## What's a clearly-labelled stub (and why)

- **Last-50 sidebar** — placeholder, "History (last 50) — coming in Phase 2".
- **Charts / CSV export** — disabled and labelled.
- **Multi-DB switcher / follow-up chat** — disabled and labelled "Phase 3".

Details in **`spec/roadmap.md`** → "Phase 1 — what is REAL on the tested path" and what is a stub.

---

## Out of scope for Phase 1

Writes, DDL, multi-DB, multi-turn session memory, charts, exports, authentication, multi-tenancy, retry-on-validator (Phase 3), multi-user rate limiting.

---

## Status

Phase 1 ready. See `spec/roadmap.md` for phases 2/3/4 plans.
