# Roadmap

The **Full Stack Analytics Agent** aggregates every signal for the `#local` entity (website + mobile app) — Google Analytics 4, the business DB, Google Play, Apple App Store, and Instagram / LinkedIn / Facebook — into one acquisition + retention funnel and a live dashboard, with on-demand refresh and a guided connector-setup flow for sources you haven't wired up yet.

---

## What This Agent Does

A single analytics surface for `#local`. It pulls from six source families, normalizes them into a unified event/funnel model, computes the core **Visit/Install → Signup → Activated → Retained → Revenue** funnel (blended web + app), and renders KPI tiles, the funnel chart, and a plain-language insight panel on a web dashboard. Aggregated results are cached and stored as time-series history; a raw-pull audit trail records every source fetch.

## Who Uses It

The `#local` owner/operator (a single, non-technical-leaning operator). They open a browser dashboard to see how acquisition and retention are trending, and they get guided help connecting each data source the first time.

## Core Problem Being Solved

Today the signals live in six disconnected consoles (GA4, Play/App Store consoles, Meta Business Suite, the app DB). There is no single funnel, no blended acquisition+retention view, and no starting point for setting the connectors up. This agent consolidates the view and removes the "where do I even put the key" friction.

## Success Criteria

- [ ] Opening the dashboard shows the 5-stage funnel for `#local` with real shape (not a spinner) on first load
- [ ] Each of the 6 connectors shows a clear CONNECTED / NOT CONFIGURED state
- [ ] Clicking a NOT CONFIGURED connector opens a step-by-step setup guide naming the exact env var + where to get it
- [ ] Refreshing re-pulls (or re-samples) every source and updates the funnel + KPIs + a new time-series point
- [ ] With no API keys set, the dashboard still renders fully from the sample adapter and labels sample data as sample

## What This Agent Does NOT Do (Out of Scope for v0.1)

- No real external API calls yet — real connectors are behind a feature flag and light up when keys are added (Phase 2+)
- No Slack/email/push notifications (deferred to a later phase)
- No scheduled/cron refresh in Phase 1 (on-demand only; scheduler is a later phase)
- No multi-entity / multi-tenant support (single `#local` entity)
- No anomaly detection beyond a simple delta vs previous snapshot

---

## Phases of Development

### Phase 1 — Unified funnel + dashboard (smallest first-time-right win)

**Goal.** Open a browser dashboard for `#local` and see the blended acquisition+retention funnel, KPI tiles, and a time-series sparkline, computed from a unified aggregation layer that already supports all six source families behind one interface. Real connectors exist but are flagged off; a sample adapter renders the full UI with no credentials. A guided setup panel tells you exactly how to connect each source.

**Independent slices** (default independent; built concurrently, disjoint paths):

1. **`scaffold`** — `pyproject.toml`, `alembic.ini`, `alembic/` (env.py, script.py.mako, versions/0001_initial.py), `.env.example`, `src/analytics_agent/__init__.py`. Owns: project config + migration → DB tables. *No dependency.*
2. **`backend-core`** — `src/analytics_agent/config/settings.py`, `db/`, `domain/`, `llm/`, `observability/`, `tools/`, `graph/`, `api/`. Owns: settings, SQLAlchemy models, domain models, LLM client (OpenRouter), connectors interface + sample adapter + 6 flagged real adapters, aggregation + funnel tool, LangGraph pipeline, FastAPI app + `/health` + `/api/*` routers. *Depends on `scaffold` (models + tables).*
3. **`frontend`** — `frontend/` (Next.js 15 static export, `basePath: '/app'`, Tailwind v4), `src/app/page.tsx` dashboard, connector setup panel, `tests/e2e/smoke.spec.ts`. Owns: the UI surface only (never touches `src/`). *Depends on `backend-core` (the `/api/*` contract in `spec/api.md`).*
4. **`tests`** — `tests/` (unit + integration + e2e wiring). Owns: `conftest.py`, unit tests (settings, models, graph-compiles), integration test (pipeline end-to-end against real code, sample mode, asserts funnel values + DB rows). *Depends on `backend-core`.*

**Key surfaces/files.** See `spec/architecture.md` (`## Stack`) and `spec/api.md`.

**Gate (exact command, runs from repo root).** All must pass:

```
uv run alembic upgrade head
uv run pytest tests/ -q
uv run python -m src --selftest
cd frontend && npm run build
npx playwright test tests/e2e/ --reporter=line
```

> Phase 1 gate runs against the **production DB driver (SQLite)** with the sample adapter as the default data source — no external API keys required. The OpenRouter key is optional in Phase 1 (insights panel renders a clearly-labelled sample summary when the key is absent). Phase 2+ is the real-key gate.

**How the user tests it.** After the gate, the root session launches the server and hands the user ONE live URL (`http://localhost:8001/app/`). The user opens it and should see: (1) the funnel with 5 stages and counts, (2) KPI tiles (signups, activated, retention %, revenue), (3) a sparkline of the last several snapshots, (4) six connector cards — all `NOT CONFIGURED` with a "Set up" button opening a guide, (5) a "Refresh" button that re-samples and updates everything. Stubs that are clearly labelled: the real external connectors, the notifications bell, the scheduled-refresh toggle.

### Phase 2 — Real connectors + live insights + scheduler (requirements phase)

**Goal.** Wire the six real source connectors (GA4, business DB, Play, App Store, Instagram, LinkedIn, Facebook) behind the existing interface, flip them on via env flags as keys are added, power the insight panel with the real OpenRouter LLM, and add a scheduled refresh.

**Capability floor: ≥3 capabilities** — (1) real source connectors, (2) live LLM insight narration, (3) scheduled refresh + (deferred) notification hooks. *This phase is not built in this run; it is the next invocation of `/zero-shot-build`.*
