# Roadmap

> The source of truth for what this agent is, who it's for, and how we build it phase by phase.

## What This Agent Does

A **data analyst agent** built for the UP Police that lets analysts upload multiple CSV datasets in one request, ask natural-language questions over the combined data, and receive concise insight summaries plus automatically generated visualization specs. Phase 2 adds a **MsSQL federation layer** that caches repeated query aggregates outside the production database, reducing live-DB load and improving latency for recurring investigations.

## Who Uses It

- **Primary:** UP Police data analysts and investigation officers who work with multiple flat-file extracts (FIR, vehicle, officer, crime-type, station datasets) and need cross-dataset answers without waiting for a DBA.
- **Secondary:** Administrators monitoring query volume and cache hit rate across stations.

## Core Problem Being Solved

Police data analysis today typically requires:
1. Opening multiple CSV extracts in different sheets or tools.
2. Writing joins/queries by hand.
3. Re-running similar queries against the live MsSQL instance, increasing load during peak periods.

This agent replaces that workflow with one request: upload CSVs, ask in plain language, get an insight + visualization spec. Phase 2 shifts repeating question patterns to a cached federation layer so the production DB sees fewer identical scans.

## Success Criteria

- [ ] Analyst can upload 2–6 CSV files in one form and receive one coherent cross-dataset insight in under ~20s for files up to 50MB total/500k rows.
- [ ] The returned answer is grounded in the uploaded data: it names actual columns, rows, and totals explicitly.
- [ ] All runs are persisted by `run_id` and retrievable with status, provider, and timing metadata.
- [ ] `/app` UI clearly shows the working path; future surfaces are labelled stubs.
- [ ] Phase 2 gate validates that repeated identical questions hit the federation cache, not the live DB, with measured cache-hit telemetry.

## What This Agent Does NOT Do (Out of Scope)

- Writing back to or modifying source CSV/MsSQL data; read-only analysis only.
- Identity lookup or authentication against police directories.
- Long-running ETL pipelines, streaming ingestion, or scheduled extracts.
- Full BI dashboarding; this is an analyst Q&A surface, not a superset of Power BI/Tableau.

## Key Constraints

> **Assumed:**
> - Phase 1 keeps the baseline FastAPI + LangGraph + SQLAlchemy + SQLite stack; no new runtime deps beyond what's already in `src/` for the baseline path.
> - Phase 1 keeps all data in-process for the request; datasets are small enough for prompt-context serialization (≤ ~5MB total after encoding or ~50k tokens). Larger inputs return a clear API error.
> - Phase 2 introduces MsSQL read-only connectivity plus a local cache store; baseline already supports `AGENT_DATABASE_URL=sqlite:///...` so we add a second engine without breaking Phase 1.
> - Exactly one provider key is required, drawn from `.env` as in the baseline.

- Latency target: < 20s p95 for 50k-row combined profile on default OpenRouter cheap model.
- Cost target: one LLM call per run; no LLM call per output token.
- DB load target in Phase 2: identical questions answered from cache; cache-hit ratio reported in run metadata.
- Privacy: raw CSV text is passed in the prompt body only for the duration of the run; raw file bytes are not persisted in Phase 1.

## Phases of Development

> **Phase 1 is the smallest first-time-right user-testable win.** It must work perfectly the first time the user tests it — zero rough edges on the tested path. Its backend is minimal but REAL on the one core path. Its frontend is visually complete: real UI for the one working path PLUS clearly-labelled NON-FUNCTIONAL stubs for everything coming later, so the user sees the vision.

### Phase 1 — Multi-CSV Insight

- **Goal:** Upload multiple CSV files, ask a natural-language question, receive one insight grounded in the combined data with a chart spec.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — add multipart upload parsing to `POST /runs`, infer schemas per file, combine CSVs into one read-only in-memory summary, build the LLM prompt from it, persist results. deps: none.
  - `slice-b` (frontend) — redesign `frontend/public/` for multi-file upload, dataset summary panel, question input, run history, and a result card showing insight text + chart metadata. deps: none.
- **Key surfaces / files:**
  - `slice-a`: `src/api/runs.py`, `src/api/_common.py`, `src/graph/nodes.py`, `src/graph/state.py`, `src/graph/agent.py`, `src/graph/edges.py`, `src/prompts/analyze.md`, `src/db/models.py`, `src/summarizer.py`.
  - `slice-b`: `frontend/public/index.html`, `frontend/public/app.js`, `frontend/public/styles.css`.
- **Gate command:** `uv run pytest tests/integration/test_phase1_e2e.py -q` against the real LLM/API via `.env`; fails if no key or provider unavailable.

### Phase 2 — MsSQL Federation + Cache

- **Goal:** Add a read-only MsSQL federation layer that answers pre-registered query patterns with cached aggregates and falls back to live SQL only on cache miss.
- **Independent slices (parallel build units):**
  - `slice-a` (backend) — add `AGENT_DATABASE_URL_MSSQL` connector with query fingerprinting, local aggregate cache, and `cache_hit`/`query_hash` telemetry in run output. deps: none.
  - `slice-b` (frontend) — add cache telemetry panel, DB state selector, and chart rendering via CDN. deps: none.
- **Key surfaces / files:** `src/db/mssql.py`, `src/graph/nodes.py`, `src/graph/state.py`, `src/graph/runner.py`, `src/api/runs.py`, `src/domain/run.py`, `src/config/settings.py`, `frontend/public/*`.
- **Gate command:** `uv run pytest tests/integration/test_phase2_e2e.py -q`; asserts cache-hit behavior and stable latency under repeated identical questions.
- **How the user tests it:** Configure `AGENT_DATABASE_URL_MSSQL` in `.env`, run the same question twice, verify second run hits cache and returns `cache_hit=true`.
