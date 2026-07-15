# Full Stack Analytics Agent (Phase 1)

> **All commands run from the repo root.**

A spec-driven analytics agent for the **#local** entity (website + mobile app). It aggregates
six source families — Google Analytics 4, the business DB, Google Play, Apple App Store, and
Instagram / LinkedIn / Facebook — into one **acquisition + retention funnel**
(Visit/Install → Signup → Activated → Retained → Revenue) and renders it on a live web dashboard.

**Phase 1 status:** the *full architecture* is wired (connectors interface, aggregation, funnel,
LangGraph pipeline, dashboard). With **no credentials**, the dashboard runs entirely on a
**sample adapter** and shows a guided setup flow for each source. Real connectors light up in
Phase 2 the moment you add a key to `.env`.

---

## Quick start (no keys needed)

```bash
# 1. Create your .env from the template (nothing required to fill in for Phase 1)
cp .env.example .env

# 2. Install Python deps + create the DB tables
uv sync
uv run alembic upgrade head

# 3. Build the frontend (Next.js static export)
cd frontend && npm install && npm run build && cd ..

# 4. Run the server (serves API + dashboard)
uv run python -m src
```

Open **http://localhost:8001/app/** — you'll see the funnel, KPI tiles, a trend sparkline, and
seven connector cards (all "NOT CONFIGURED" with a "Set up" button), driven by sample data.

> **Optional LLM:** set `AGENT_OPENROUTER_API_KEY` in `.env` for a live insight narration.
> Without it, the insight panel shows a clearly-labelled sample summary.

---

## What you get in Phase 1

| Surface | Status |
|---------|--------|
| Unified 5-stage funnel (blended web+app) | ✅ real (sample data) |
| KPI tiles: signups / activated / retention % / revenue | ✅ real (sample data) |
| Time-series trend sparkline | ✅ real |
| Connector status + guided setup panel (7 sources) | ✅ real UI, keys wired for Phase 2 |
| On-demand Refresh (re-pull + re-aggregate) | ✅ real |
| OpenRouter insight narration | ✅ optional (sample fallback) |
| Real external API calls (GA4, stores, social) | ⏳ Phase 2 (flagged, behind env keys) |
| Notifications / scheduled refresh | ⏳ Phase 2 (labelled stubs) |

The funnel is computed from a single `ConnectorHub` interface. `SampleConnector` provides a full
realistic funnel with zero credentials; the six real connectors (`GA4Connector`, `BusinessDbConnector`,
`PlayStoreConnector`, `AppStoreConnector`, `InstagramConnector`, `LinkedInConnector`, `FacebookConnector`)
exist but return "not configured" until their env key is set.

---

## API (served at `http://localhost:8001`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | liveness |
| GET | `/api/funnel` | latest 5-stage funnel + sample flag |
| GET | `/api/kpis` | KPI tiles |
| GET | `/api/snapshots` | time-series points |
| GET | `/api/connectors` | per-source configured state |
| GET | `/api/setup_guide?source=<id>` | ordered setup steps for a source |
| POST | `/api/refresh` | run the pipeline, return new funnel |

---

## Tests

```bash
# Python (unit + integration) — no key needed in Phase 1
uv run pytest tests/ -q

# Frontend E2E (Playwright) — requires a running server on :8001
cd frontend && npx playwright install chromium
npx playwright test tests/e2e/ --reporter=line
```

The Phase 1 E2E boots the app, asserts the funnel + KPIs render styled with **0 console errors**,
and clicks Refresh.

---

## Project layout

```
src/analytics_agent/   FastAPI app, LangGraph pipeline, connectors, DB, LLM client
frontend/              Next.js 15 static export (basePath: /app)
tests/                 pytest (unit + integration) + Playwright e2e
spec/                  product + architecture + agent + phased plan
harness/               engineering rules / patterns / skills (the SDD harness)
alembic/               migrations
```

## Next phase

Phase 2 wires the six real source connectors behind their env keys, powers the insight panel with
the live OpenRouter LLM, and adds scheduled refresh + notification hooks.
