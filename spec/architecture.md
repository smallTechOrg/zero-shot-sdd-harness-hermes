# Architecture

> **Assumed:** baseline Python + FastAPI + LangGraph; SQLite (dev) and a separate PostgreSQL database for sessions, workspaces, and audit; MsSQL accessed read-only via SQLAlchemy + pyodbc or asyncodbc; NVIDIA NIM as the LLM provider via its OpenAI-compatible HTTP endpoint.
> **Assumed:** all observability, E2E, and offline/cache fallback requirements apply.

## System Overview

The UP Police Data Analyst is a long-running FastAPI service. A user uploads CSVs, asks a natural-language question, and receives an auditable analytical answer backed by real data. In later phases the same loop can run over a live MsSQL read-only source instead of CSV, with a local cache that keeps answers fast and protects the production database from ad-hoc analytical load. The service is deployed on-premises on the police network; external egress is not required.

## Component Map

```
User (browser)
  │
  ▼
FastAPI Backend
  │
  ├─► CSV Ingestor —> parsed tables (pandas / SQLite / DuckDB if needed)
  ├─► MsSQL Adapter —> read-only live queries via SQLAlchemy + pyodbc / asyncodbc
  ├─► Cache Layer —> local PostgreSQL tables for precomputed aggregates + row-level cache
  ▼
LangGraph Agent
  │
  ├─► Planner node — turns the question into a query plan and data-source choice
  ├─► SQL/code generator — one tool call to the LLM; emits SQL or pandas
  ├─► Validator/runner — executes safely and enforces read-only / row limits
  ├─► Answer node — builds audited output, charts data, CSV blob
  ▼
Audit + Session tables (PostgreSQL)
  ▼
Frontend (static JS bundle served by FastAPI)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| HTTP / API | Request validation, auth, upload handling, response encoding |
| Graph | LangGraph state machine: plan → query → validate → answer |
| Data access | CSV ingestion, live MsSQL read-only adapter, cache reads/writes |
| Audit / sessions | Runs, queries, users, workspaces, exports (PostgreSQL) |
| LLM | One batched call per query; policy/guardrails via prompts |
| Frontend | Single-page static UI for upload, Q&A, charts, exports, workspace |

## Data Flow

1. Trigger: user uploads one or more CSVs, or chooses "Live DB" as the source.
2. Planner: the agent picks CSV vs live vs cache based on user selection and cache freshness policy.
3. Query generation: one LLM call emits SQL or pandas; CSV mode uses SQLite/SQLAlchemy against an ingested schema; live mode emits MsSQL-T-SQL dialect.
4. Validation: read-only check, row-limit enforcement, expected-column verification.
5. Execution: query runs; result set is materialised.
6. Answer assembly: natural-language answer, table, CSV download, generated code, audit row written.
7. Output: returned to the UI and saved to the run history.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| NVIDIA NIM (OpenAI-compatible endpoint) | Text-to-SQL, answer synthesis, follow-up suggestions | Degraded: agent surfaces error and offers best-guess cached answer or re-try guidance |
| MsSQL (read replica / production) | Live crime / case data | Offline mode: agent serves from local PostgreSQL cache with "served from cache" indicator |
| PostgreSQL (local) | Query cache, sessions, workspaces, audit log | Fatal for persistence features; CSV mode still works for uploads without PostgreSQL until the DB is restored |

## Stack

- **Language:** Python 3.11+
- **Agent framework:** LangGraph
- **LLM provider + model:** NVIDIA NIM — OpenAI-compatible HTTP; environment-configurable base URL, API key, model id.
- **Backend:** FastAPI + Uvicorn
- **Database + ORM:** SQLite (CSV ingest workspace) · PostgreSQL (sessions / workspaces / audit / materialised cache) · MsSQL via SQLAlchemy + pyodbc/asyncodbc (read-only)
- **Frontend:** Static HTML+CSS+JS in `frontend/public/`, served by FastAPI
- **Dependency management:** uv + pyproject.toml

| Key library | Version (target) | Purpose |
|-------------|------------------|---------|
| fastapi | >=0.115 | HTTP surface |
| uvicorn[standard] | >=0.30 | server |
| pydantic / pydantic-settings | >=2.7 / >=2.3 | validation and settings |
| sqlalchemy | >=2.0 | SQL generation + dialects |
| langgraph | >=0.2.28 | agent graph |
| httpx | >=0.27 | LLM HTTP calls |
| structlog | >=24.1 | structured audit logging |
| pyodbc / asyncodbc | latest stable | MsSQL driver connectivity |

**Avoid:** writing to the live production MsSQL database; client-side bundlers or build pipelines for the Phase 1 UI; per-line LLM loops in generated code.

## Deployment Model

- On-premises deployment as a single long-running service (`python -m src`) on the police network.
- `.env` for secrets; no external SaaS for persistence unless it is an approved government VPC service.
- Nightly or on-demand cache refresh for live DB materialisations.
