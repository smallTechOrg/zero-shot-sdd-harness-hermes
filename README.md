# CCTNS Analyst

Natural-language → bounded SQL → short-answer analyst over the **CCTNS
mirror**, tuned for low latency and low load on the source database. Built
for UP Police analysts.

> **All commands below run from the project root** (`E:\smalltech\hermes\zero-shot-hermes-harness`).
> The package slug is `cctns_analyst` and lives at `src/cctns_analyst/`; the
> Next.js UI lives at `frontend/` and is mounted by FastAPI at `/app/`. The
> `harness/` directory is engineering rules for AI agents — leave it alone.

## What it does

1. The user types an analyst question into the UI.
2. The backend (FastAPI) routes through a **LangGraph** state machine:
   - `nl_to_sql` — LLM (Gemini `gemini-2.5-flash`) drafts a single SELECT
     against `cctns_mirror.*` (schema only; data-locality safe).
   - `execute_sql` — runs the SELECT on the configured mirror under strict
     bounds (row_cap=1000, statement_timeout=10s).
   - `validate_result` — one self-correction retry on validation failure.
   - `summarize_answer` — second LLM call turns the bounded result into a
     short prose summary.
   - `finalize` — persists an `AnswerRun` row.
3. The UI shows the prose answer, results table, the SQL, and a latency badge.

## Stack (binding)

- Python 3.11 + FastAPI + LangGraph + SQLAlchemy 2.0
- Gemini (`gemini-2.5-flash`) — provider key in `.env`
- ICC Mode: **mock** mirror (default in dev, in-process, ≥ 500 synthetic FIR rows)
  or **live** mirror via `CCTNS_MIRROR_URL` (Phase 3 connector)
- Next.js 15 + React 19 + Tailwind v4 static export at `/app/`
- SQLite for our own state (`AnswerRun`, `CctnsTable`)

## `.env`

```env
AGENT_DATABASE_URL=sqlite:///./data/agent.db
AGENT_GEMINI_API_KEY=<your-gemini-key>
AGENT_LLM_MODEL=gemini-2.5-flash
AGENT_LLM_PROVIDER=gemini
AGENT_ROW_CAP=1000
AGENT_STATEMENT_TIMEOUT_MS=10000
AGENT_LOG_LEVEL=INFO
AGENT_PORT=8001

# Flip to live mode:
# AGENT_CCTNS_MIRROR_URL=mssql+pyodbc://user:pass@host/cctns?driver=ODBC+Driver+18+for+SQL+Server
```

These are also documented in `.env.example`.

## Run

From the **repo root**:

```bash
# 1. install
uv sync --group dev

# 2. database
uv run alembic upgrade head
uv run alembic current  # verify the migration applied (not blank)

# 3. build the frontend (once; rerun after frontend changes)
cd frontend && npm install --silent && npm run build && cd ..

# 4. start the server (serves API + static UI on :8001)
uv run python -m src
```

Then open **http://localhost:8001/app/** in a browser.

## Test

```bash
uv run pytest -q                          # unit + integration
cd tests/e2e && npm install --silent && npx playwright install --with-deps chromium && cd ../..
npx playwright test tests/e2e/ --reporter=line
```

The integration suite uses a **recording stub LLM provider** so it runs
without burning a real Gemini call. Data-locality, bounded-query, and
full-data correctness gates are part of `uv run pytest -q`.

## Layout

```
src/cctns_analyst/
├── api/                  FastAPI routers, app factory
├── config/               Pydantic Settings (env_prefix=APP_)
├── db/                   SQLAlchemy 2.0 models + session
├── domain/               Pydantic body/response shapes
├── graph/                LangGraph state machine
├── llm/                  LLMClient + Gemini provider
├── observability/        structlog JSON
├── prompts/              .md templates
└── tools/                mock_mirror + cctns_mirror (live in Phase 3)
alembic/                  migrations
frontend/                 Next.js 15 + Tailwind v4 (static export)
tests/                    unit, integration, e2e/
spec/                     source of truth (this build's product spec)
```

## What's a stub

The UI panels for follow-up questions, conversation history, role-based
filtering, and switching to live CCTNS are **labelled stubs** saying
"Coming in Phase 2/3". They are deliberately not wired and never look
broken.
