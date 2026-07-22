# Architecture

## System Overview

A local-first, on-prem data analyst agent for the UP Police. The agent ingests multiple CSV exports, executes natural-language analytical questions against either in-memory data or a live read-only MsSQL connection, and returns structured outputs: a natural-language answer, a result table, a chart, downloadable report files, follow-up suggestions, and anomaly flags. Scheduled reports and named reports with rerun/history are persistent first-class objects.

## Component Map

```
[Analyst Web UI]
    │
    ▼
[FastAPI Backend]
    │
    ├─ CSV Ingestion + Validation ──► Local artifact store
    │
    ├─ LLM Router/Planner ──► OpenRouter / Anthropic / Gemini
    │
    ├─ Analytical Runner
    │     ├─ Pandas path ──► uploaded CSV dataframes
    │     └─ MsSQL path ──► pyodbc / ODBC ↔ live DB
    │           ├─ Schema reflector
    │           ├─ SQL generator + validator
    │           └─ Result cache (fingerprint → rows + metadata)
    │
    ├─ Report/Schedule Store ──► SQLite app DB (SQLAlchemy)
    │
    └─ Observability ──► structured logs + trace spans
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API | HTTP endpoints for uploads, runs, reports, schedules, dashboard, health |
| Agent Loop | LangGraph state machine: intake → plan → tool use → observe → finalize |
| Tools | CSV validation/loader, Pandas analyzer, MsSQL schema+SQL tool, report/schedule persistence |
| Storage | SQLite app DB for reports/schedules/runs; local filesystem for uploaded CSVs; live MsSQL for production data queries |
| LLM | OpenRouter default (`tencent/hy3`), configurable; provider-agnostic httpx layer with retry/backoff |

## Data Flow

1. Trigger: analyst uploads CSV(s) or connects to live MsSQL and asks a question.
2. The agent builds a plan: which tool(s) to use, what schema/data to inspect, what reasoning trail to emit.
3. The analytical runner executes: Pandas for CSV data, read-only SQL via pyodbc for live DB with row caps, timeouts, and query fingerprint caching.
4. Output assembly: natural-language answer + result table + chart-ready payload + downloadable file + follow-ups/anomalies.
5. Persist: run, report, or schedule record is written to the SQLite app DB with timestamp, analyst identity, provider/model, latency, and error state.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| OpenRouter / LLM API | Answer synthesis, SQL drafting, planning, anomaly detection | Falls back to cached analysis when possible; surfaces clear error with retry guidance |
| pyodbc / ODBC Driver 18 for SQL Server | Live read-only queries against MsSQL | Times out, surfaces schema/connectivity error, never writes |
| SQLite (app DB) | Run/report/schedule persistence | Local file failure blocks new runs with explicit error; does not corrupt live DB |

## Stack

> **Basis:** Python 3.11 + FastAPI + LangGraph + SQLite via SQLAlchemy 2.0, extend in place with pyodbc + MsSQL. Frontend stays zero-build static served by the backend.

- **Language:** Python 3.11
- **Agent framework:** LangGraph
- **LLM provider + model:** OpenRouter, default `tencent/hy3`; env-overridable via `AGENT_LLM_MODEL`
- **Backend:** FastAPI + uvicorn
- **Database + ORM:** SQLite + SQLAlchemy 2.0 for app metadata; pyodbc + ODBC Driver 18 for live MsSQL read-only analytics
- **Frontend:** zero-build static (`frontend/public/`)
- **Dependency management:** uv + pyproject.toml
- **Runner:** LangGraph `StateGraph` with conditional edges into plan → tool use → observe → finalize

| Key library | Version | Purpose |
|-------------|---------|---------|
| fastapi | >=0.115 | API surface |
| uvicorn[standard] | >=0.30 | ASGI server |
| pydantic + pydantic-settings | >=2.7 / >=2.3 | Validation + config |
| sqlalchemy | >=2.0 | App DB ORM/migrations |
| alembic | >=1.13 | Schema migrations |
| langgraph | >=0.2.28 | Agent graph orchestration |
| httpx | >=0.27 | Provider-agnostic LLM HTTP |
| structlog | >=24.1 | Structured observability |
| pyodbc | latest | MsSQL read-only driver |

**Avoid:**
- Raw ad-hoc LLM calls outside the graph runner
- Writing through the live MsSQL connection from this agent
- Async DB drivers for this baseline; stick to sync SQLAlchemy + sync pyodbc for predictable Windows behavior
- Large npm/build toolchain for the frontend

## Deployment Model

Local-first long-running service on a police-premises machine. Single-origin web UI on port 8001. Optional scheduled background jobs via a lightweight runner against persisted schedule records. No outbound data path by default; explicit export actions are the only data movement boundary.
