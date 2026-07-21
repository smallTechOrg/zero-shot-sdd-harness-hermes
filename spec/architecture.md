# Architecture

> **Assumed:** No existing UP Police stack was specified at intake; all technology choices below are binding intake answers + documented Assumed flags.

---

## System Overview

The UP Police Data Analyst Agent is a single-server, on-prem FastAPI application. A user uploads CSVs (or connects to MsSQL) and asks questions in natural language. A LangGraph agent pipeline generates SQL/Python, executes it safely, and returns a code-transparent answer with tables, charts, and downloads — all within the same browser session. An audit log persists every query with query text, generated SQL, row count, latency, and user identity.

## Component Map

```
[Browser UI] ──────► [FastAPI app]
                            │
                     ┌──────┴──────┐
                     │  LangGraph  │  ← LLM (on-prem / air-gapped endpoint)
                     │  agent run  │
                     └──────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        [SQLite /       [MsSQL        [Assets]
         CSV cache]      pyodbc]       (charts PDF)
                            ▲
                     [Query Cache] (dedup + TTL)
                            ▲
                     [Audit Log] (SQLite / structured file)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API (FastAPI) | Serves UI, accepts uploads, runs queries, returns JSON |
| Agent loop (LangGraph) | Plans, generates SQL/Python, evaluates, retries, finalizes |
| Tools | SQL executor (SQLite + MsSQL), chart renderer, report generator |
| Session / Cache | Dataset metadata + query cache + artifact store |
| Observability | Structured audit trail + request logging |

## Data Flow

1. **Trigger:** User uploads CSVs via POST `/upload` or connects MsSQL via POST `/datasource/connect`.
2. **Ingest:** CSVs are parsed with pandas, schema inferred (column names, types, sample rows, row counts) → metadata saved to SQLite. MsSQL introspects live schema via `INFORMATION_SCHEMA`.
3. **Ask:** User submits a natural-language question via POST `/query`. LangGraph pipeline runs:
   - plan → generate SQL/Python → execute → evaluate → (iterate if confidence < threshold) → finalize
4. **Render:** API returns: NL answer, generated code block, tabular results (JSON), optional chart data/URLs, artifact download links.
5. **Audit:** Every query is logged with user, question, SQL, row count, latency, cache hit/miss, success.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| On-prem LLM endpoint | SQL generation + NL answer | Agent surfaces a clear error; queue retry with backoff |
| MsSQL (Phase 2) | Live production data | Read-only fallback to last cached snapshot if unreachable |
| SQLite (Phase 1) | CSV-backed query runtime | DB file missing → 500; re-ingestion required |
| pyodbc | MsSQL connectivity | Connection refused → surface error; MsSQL tab hidden |

## Stack

- **Language:** Python 3.11+
- **Agent framework:** LangGraph (single-agent loop with one tool-call node; conditional retry edge for iterate-until-right)
- **LLM provider + model:** On-prem / air-gapped LLM endpoint; configurable via `AGENT_LLM_PROVIDER` + `AGENT_LLM_MODEL` in `.env`. Baseline provider layer already supports Anthropic, Gemini, OpenRouter (extend with custom endpoint).
- **Backend:** FastAPI
- **Database + ORM:** SQLite (dev, via SQLAlchemy 2.0); pyodbc (MsSQL Phase 2)
- **Frontend:** Zero-build static HTML/JS/CSS served at `/app`
- **Dependency management:** uv + pyproject.toml

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | latest | HTTP API |
| sqlalchemy | 2.0+ | ORM / DB session |
| pyodbc | latest | MsSQL connectivity |
| pandas | latest | CSV parsing + DataFrame ops |
| langgraph | latest | Agent graph |
| langchain-core | latest | Prompt + LLM I/O |
| matplotlib | latest | Chart generation |
| reportlab / openpyxl | latest | PDF / Excel reports |
| structlog | latest | Structured logging |
| python-dotenv | latest | Env loading |

**Avoid:** Any cloud inference in production; direct pandas read of >10 lakh rows without chunking; bare `python` outside the pinned `.venv/bin/python`.

## Deployment Model

Long-running FastAPI service (production) or `.venv/bin/python -m src` (dev). MsSQL access via read-only account. LLM endpoint reachable only on internal network. No external egress required or configured.
