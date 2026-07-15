# Architecture

## Overview

A single FastAPI service (`src/analytics_agent`) owns the data layer, the aggregation pipeline (a small LangGraph), and the HTTP API. A Next.js 15 static export is served by FastAPI at `/app/`. The browser talks only to the backend's `/api/*` JSON endpoints.

The data flow for one refresh:

```
dashboard "Refresh" ──► POST /api/refresh ──► run_pipeline()
        │                                            │
        │                                   fetch_sources (graph node)
        │                                      └─ ConnectorHub.pull_all()
        │                                           ├─ sample adapter (default)
        │                                           └─ real adapters (flagged, if key set)
        │                                   aggregate (graph node)
        │                                      └─ normalize → SourceRecord rows
        │                                   compute_funnel (graph node)
        │                                      └─ 5-stage funnel + KPIs
        │                                   narrate (graph node, optional LLM)
        │                                   finalize → write Snapshot + FunnelPoint rows
        ▼
   GET /api/funnel, /api/kpis, /api/snapshots, /api/connectors
        ▼
   Next.js dashboard renders funnel, KPI tiles, sparkline, connector panel
```

## Components

- **`ConnectorHub`** (`tools/connectors/`) — one interface (`BaseConnector.pull() -> list[SourceRecord]`). A `SampleConnector` returns realistic synthetic data so the whole UI works with zero credentials. Six real connectors (`GA4Connector`, `BusinessDbConnector`, `PlayStoreConnector`, `AppStoreConnector`, `InstagramConnector`, `LinkedInConnector`, `FacebookConnector`) exist but each returns "not configured" unless its env key is present. Selected by `provider=auto` resolution (real when key set, else sample).
- **Aggregation tool** (`tools/aggregate.py`) — normalizes `SourceRecord`s into the funnel stages and KPI set; stores `SourceRecord` (raw audit), `Snapshot` (cached aggregate), `FunnelPoint` (time-series).
- **Pipeline** (`graph/`) — LangGraph: `fetch_sources → aggregate → compute_funnel → narrate → finalize`.
- **API** (`api/`) — `health`, `funnel`, `kpis`, `snapshots`, `connectors`, `refresh`, `setup_guide`.
- **Frontend** (`frontend/`) — `page.tsx` dashboard + `ConnectorSetupPanel` + `RefreshButton`.

## Data Flow

On-demand: a dashboard load issues `GET /api/funnel` (+ kpis, snapshots, connectors). If no fresh snapshot exists (or `Refresh` is pressed), the backend runs `run_pipeline()` which pulls, aggregates, and writes a new `Snapshot` + `FunnelPoint`. Results are cached in SQLite and served until the next refresh.

## Stack

> **Assumed:** Python 3.11 (host has 3.11.15; harness prefers 3.12+ but 3.11 is fully supported by FastAPI/SQLAlchemy/LangGraph). Pinned in `pyproject.toml` as `requires-python = ">=3.11"`.

- **Language:** Python 3.11
- **Backend:** FastAPI 0.115+, Uvicorn
- **Agent framework:** LangGraph (`langgraph`) — pipeline is a 5-node `StateGraph`, compiled once at import
- **LLM provider:** OpenRouter (`AGENT_OPENROUTER_API_KEY`), model `anthropic/claude-sonnet-4-6` default, configurable via `ANALYTICS_LLM_MODEL`. Insight narration is optional; sample summary shown when key absent.
- **Database:** SQLite (single-tenant, local — per harness default for local/single-user tools). Driver `sqlite` (stdlib) — declared in `[project.dependencies]`, not dev-only.
- **ORM:** SQLAlchemy 2.0 (declarative `Mapped` types)
- **Migrations:** Alembic
- **Frontend:** Next.js 15 + React 19, static export (`output: 'export'`, `basePath: '/app'`), Tailwind CSS v4 (`@tailwindcss/postcss` + `@source`), served by FastAPI
- **Dependency management:** uv (Python) / npm (TypeScript)
- **Observability:** structured stdout logging via `structlog` for every pipeline run (timestamp, stages, latency_ms, error); OpenRouter call logged (presence-only). Never deferred.
- **Dev port:** 8001 (hard-coded in `__main__.py`, overridable via `PORT`)
