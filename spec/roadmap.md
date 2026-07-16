# Roadmap — CCTNS Analyst Agent

> A natural-language → read-only-SQL → short-answer analyst over the **CCTNS mirror**,
> tuned for low latency and low load on the source database. Built for UP Police
> analysts.

---

## What This Agent Does

The CCTNS analyst turns a free-form analyst question (e.g. *"How many FIRs in
Lucknow in the last 30 days?"*) into a single read-only SQL query against the
**CCTNS mirror** (a denormalized, bounded copy of the source CCTNS MsSQL
database, living under the `cctns_mirror` schema), executes it within strict
bounds, and returns a short prose answer with the SQL it ran and a small table
of rows. It never returns raw rows to the LLM — only schema + aggregates — to
keep regulated CCTNS data within the production trust boundary.

## Who Uses It

UP Police analysts and investigating officers who need quick, ad-hoc numbers
from CCTNS without paying the cost of a SQL query against the live operational
database.

## Core Problem Being Solved

Live CCTNS is read-sensitive and load-sensitive: ad-hoc analyst queries cost
DBAs' time and can spike load on the operational system. A separate mirrored
read-replica, queried through a bounded agent, keeps analyst productivity high
without taxing the operational DB.

## Success Criteria

- [ ] P50 end-to-end latency from POST to prose answer ≤ 6 s against the mock
      mirror; ≤ 10 s against the live mirror.
- [ ] 100 % of LLM payloads contain schema, aggregates, or ≤ N sample rows
      only — **no** raw row bodies (data-locality test asserts this verbatim).
- [ ] Every executed SQL is bounded: row_cap ≤ 1000, statement_timeout ≤ 10 s.
- [ ] The mock mirror holds ≥ 500 synthetic FIRs across ≥ 5 tables; the
      gate test asserts a value only computable from the **full** dataset.
- [ ] The analyst can ask, see a short answer, expand "Show SQL", and see a
      latency badge — end-to-end — against the real Gemini key, no console
      errors.

## What This Agent Does NOT Do (Out of Scope)

- **Writes** — never mutates CCTNS, the mirror, or our own DB.
- **Cross-database joins** beyond the mirror's denormalized shape.
- **Any** tool other than SQL on the mirror.
- Real-time push to Slack / dashboards (declared in Phase 2/3).
- Multi-user / RBAC (Phase 2).
- Live CCTNS production connector (Phase 3).

## Key Constraints

- **Latency:** p50 ≤ 6 s on mock, ≤ 10 s on live. One LLM call per request on
  the primary path (no streaming re-prompts); a one-time self-correction retry
  if the SQL validator rejects the first pass.
- **Privacy:** raw rows MUST NOT enter any LLM payload; data-locality is a
  BLOCK-level check enforced by a prompt-spy test.
- **DB load:** row_cap=1000, statement_timeout=10 s; one statement per request;
  no concurrent RUN batch on the same connection.
- **Compliance:** every read against the live mirror is audit-logged with
  user, question, and sql_template (Phase 3).
- **Stack:** Python 3.11 + FastAPI + LangGraph + SQLAlchemy 2.0 with raw-SQL
  escape hatch; Gemini `gemini-2.5-flash` (configurable via `APP_LLM_MODEL`);
  Next.js 15 + React 19 + Tailwind v4 static export at `/app/`.

---

## Phases of Development

### Phase 1 — Single-shot NL → SQL → Answer (smallest user-testable win)

- **Goal:** A UP Police analyst can paste a natural-language question into the
  web UI, get back a short prose answer + the SQL the system ran + a small
  results table, with a latency badge.
- **Independent slices (parallel build units):**
  - `slice-a` (backend — graph+LLM) — `src/cctns_analyst/graph/*`,
    `src/cctns_analyst/llm/*`, `src/cctns_analyst/prompts/*.md`. deps: none.
  - `slice-b` (backend — DB+mock-mirror) — `src/cctns_analyst/db/*`,
    `src/cctns_analyst/tools/{cctns_mirror,mock_mirror}.py`, seed script.
    deps: none (the prompt's schema lookup is at runtime; slice-b publishes
    `list_tables()` and `columns_for()` regardless of slice-a being there).
  - `slice-c` (backend — API+config+observability) —
    `src/cctns_analyst/api/*`, `src/cctns_analyst/domain/*`,
    `src/cctns_analyst/config/*`, `src/cctns_analyst/observability/*`,
    `src/cctns_analyst/{__init__,__main__}.py`. deps: declared on
    `slice-a` (graph compose) and `slice-b` (mirror references in
    `answer.py`); therefore slice-c **must** ship after `slice-a`+`slice-b`
    land.
  - `slice-d` (frontend) — `frontend/*`, `tests/e2e/smoke.spec.ts`. deps:
    declared on `slice-c` (the UI calls `/v1/answer`); therefore slice-d
    ships after `slice-c`.
- **Key surfaces / files:**
  - slice-a: `src/cctns_analyst/graph/{state,nodes,edges,agent,runner}.py`,
    `src/cctns_analyst/llm/{client,providers/{base,factory,gemini}}.py`,
    `src/cctns_analyst/prompts/{nl_to_sql,summarize}.md`.
  - slice-b: `src/cctns_analyst/db/{__init__,models,session}.py`,
    `src/cctns_analyst/tools/{cctns_mirror,mock_mirror}.py`,
    `scripts/seed_mock_mirror.py`.
  - slice-c: `src/cctns_analyst/api/{__init__,_common,health,answer}.py`,
    `src/cctns_analyst/domain/{question,answer_run}.py`,
    `src/cctns_analyst/config/settings.py`,
    `src/cctns_analyst/observability/events.py`,
    `src/cctns_analyst/{__init__,__main__}.py`.
  - slice-d: `frontend/{package.json,next.config.mjs,postcss.config.mjs,src/app/{globals.css,layout.tsx,page.tsx,error.tsx}}`,
    `tests/e2e/smoke.spec.ts`.
- **Gate command (run from project root `E:\smalltech\hermes\zero-shot-hermes-harness`):**
  ```bash
  uv sync
  uv run alembic upgrade head && uv run alembic current
  uv run pytest -q
  cd frontend && npm install --silent && npm run build && cd ..
  ! grep -r '@tailwind' frontend/out
  grep -rE '\.(flex|grid|bg-|rounded-|text-)' frontend/out/_next/static/css/*.css | head
  npx playwright install --with-deps chromium && npx playwright test tests/e2e/ --reporter=line
  uv run python -m src &   # boot smoke on :8001, then kill
  ```
- **How the user tests it (handoff seed):**
  - The root session launches the server.
  - User opens `http://localhost:8001/app/`.
  - User types a question (e.g. *"How many FIRs in Lucknow in the last 30 days?"*),
    clicks **Ask**.
  - User observes: short prose answer, a results table (≤ ~100 rows shown),
    "Show SQL" toggle revealing the SQL, latency badge; **Loading** state while
    in flight; **Error** template on a deliberately broken question (e.g.
    `"?"`).
  - Clearly-labelled **stubs** for: follow-up input (Phase 3),
    conversation history sidebar (Phase 2), switch-to-live-CCTNS panel
    (Phase 3), multi-user / role-filter panel (Phase 2). Each stub says
    "Coming in Phase 2/3" — never "broken" or "error".

### Phase 2 — Multi-turn + history + role-based filtering

- **Goal:** Conversation memory, per-role row-level filter policy, and a
  history sidebar in the UI.
- **Independent slices (parallel build units):**
  - `slice-p2a` (backend — conversation memory) —
    `src/cctns_analyst/db/models.py` adds `Session`, `Turn`; new
    `src/cctns_analyst/graph/memory.py`. deps: none.
  - `slice-p2b` (backend — role-based row filtering) — new
    `src/cctns_analyst/tools/row_filter.py`, prompt augmentation in
    `prompts/nl_to_sql.md`. deps: none.
  - `slice-p2c` (frontend — history sidebar) — `frontend/src/app/page.tsx`
    history panel, new `frontend/src/components/HistorySidebar.tsx`.
    deps: declared on slice-p2a.
- **Key surfaces / files:** as above.
- **Gate command:**
  ```bash
  uv run pytest -q
  cd frontend && npm run build && cd ..
  npx playwright test tests/e2e/ --reporter=line
  ```
- **How the user tests it:** asks a follow-up referencing earlier turns;
  toggles a role selector (e.g. *Investigating Officer*) and re-asks;
  sees prior turns in the sidebar that survive a page reload.

### Phase 3 — Real CCTNS connector + production hardening

- **Goal:** Live (read-only) connector to the production mirror, token-bucket
  rate limit, audit log every read against production.
- **Independent slices (parallel build units):**
  - `slice-p3a` (backend — live connector) —
    `src/cctns_analyst/tools/cctns_mirror.py` adds `MssqlMirror`
    (pyodbc) keyed off `CCTNS_MIRROR_URL`. deps: none.
  - `slice-p3b` (backend — rate limit + audit log) —
    `src/cctns_analyst/observability/audit.py`,
    `src/cctns_analyst/tools/limiter.py`. deps: none.
  - `slice-p3c` (frontend — switch-to-live panel) —
    `frontend/src/app/page.tsx` panel wired to a `POST /v1/mirror-mode`.
    deps: declared on slice-p3a.
- **Key surfaces / files:** as above.
- **Gate command:** production-DB connection from `.env`; full E2E live.
  ```bash
  uv run pytest -q -m live
  cd frontend && npm run build && cd ..
  npx playwright test tests/e2e/ --reporter=line
  ```
- **How the user tests it:** flips a switch in the UI; asks a question; the
  audit-log endpoint returns the read; latency stays within the p50 bar.
