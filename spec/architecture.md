# Architecture

## System Overview
The UP Police Data Analyst agent is a read-only interface over a Microsoft SQL Server database containing FIR/CCTNS, HR/personnel, and logistics/property data. Authorized officers interact via a chat-based web UI to ask natural-language questions about crime, personnel, or logistics data. The agent translates questions into safe SQL queries, executes them against the database, and returns answers with the executed SQL, timing, and optional visualizations. All interactions are logged immutably for audit and compliance.

## Component Map
```mermaid
graph TD
    A[Officer's Browser] -->|HTTPS/WSS| B(FastAPI Backend)
    B -->|SQLAlchemy + pyodbc| C[Microsoft SQL Server]
    B -->|HTTP (JSON)| D[OpenRouter LLM API]
    B -->|Append-only| E[Audit Table (SQL Server)]
    B -->|Serve at /app| F[Static Frontend (HTML/JS)]
```

## Layers
| Layer | Responsibility |
|-------|----------------|
| Presentation | Static HTML/JS frontend served at `/app`; handles user input, displays answers with collapsible SQL/chart/table panels, and shows recent/pinned reports sidebar. |
| API | FastAPI endpoints (`/api/ask`, `/api/pin`, `/api/recent`) that validate input, invoke the agent loop, and return structured responses. |
| Agent Loop | LangGraph-based reasoning loop: Planner → SQL Writer → Validator → Executor → Answer Writer. Each step is a node with conditional edges for error handling and retries. |
| Tools & Storage | SQLAlchemy ORM with MSSQL driver (`pyodbc`/`aioodbc`) for schema introspection and query execution; audit table for immutable logging. |
| External | OpenRouter LLM API (primary: Anthropic Claude Sonnet 3.5, fallback: Claude Haiku) for reasoning and SQL generation. |

## Data Flow
1. Trigger: Officer types a question in the chat input and presses Enter.
2. Frontend sends POST `/api/ask` with `{ question, officer_id }` (officer_id from headers or login context).
3. API validates input, creates an agent run record, and invokes the LangGraph agent loop.
4. Planner node refines the question (if ambiguous) and outputs a refined question or clarification request.
5. SQL Writer node generates a parameterized SQL query using the cached schema (tables/columns only, no row data).
6. Validator node checks the SQL for safety: ensures read-only, mandates `LIMIT/TOP`, blocks `SELECT *`, and validates against a read-only DB user policy.
7. Executor node runs the SQL against the MSSQL database via SQLAlchemy, capturing row count and latency.
8. Answer Writer node formats the result into a natural-language answer, optionally generating a chart/table if the data is suitable.
9. The run record is updated with the answer, SQL, timing, and an immutable audit log entry is written.
10. API returns the answer, SQL, timing, and optional chart spec to the frontend.
11. Frontend displays the answer with collapsible panels for SQL and chart/table, and updates the recent/pinned sidebar.

## External Dependencies
| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Microsoft SQL Server | Stores FIR/CCTNS, HR/personnel, and logistics/property data; source of truth for all queries. | Database downtime causes 503 errors; agent returns "Database unavailable" error. |
| OpenRouter LLM API | Provides reasoning and SQL generation via Anthropic Claude models. | API downtime or rate limiting causes fallback to cheaper model or explicit error; agent may ask user to rephrase or try later. |
| Officer Auth System (future) | Provides JWT tokens for officer identification (Phase 3). | Missing/invalid token results in 401 error; Phase 1 uses stubbed officer_id from header. |

## Stack
- **Language:** Python 3.11
- **Agent framework:** LangGraph
- **LLM provider + model:** OpenRouter (Anthropic Claude Sonnet 3.5 for planning, Claude Haiku for cheap fallback)
- **Backend:** FastAPI
- **Database + ORM:** Microsoft SQL Server + SQLAlchemy 2.0 (with `pyodbc`/`aioodbc` driver)
- **Frontend:** Zero-build static HTML/CSS/JS (served at `/app`)
- **Dependency management:** uv + pyproject.toml

| Key library | Version | Purpose |
|-------------|---------|---------|
| langgraph | 0.1.x | Agent reasoning loop |
| fastapi | 0.109.x | Web API and server |
| sqlalchemy | 2.0.x | ORM and DB abstraction |
| pyodbc | 5.x | MSSQL driver (sync) |
| aioodbc | 1.x | Async MSSQL driver (if needed) |
| pydantic | 2.x | Data validation and settings |
| python-dotenv | 1.x | Load environment variables from `.env` |
| structlog | 23.x | Structured logging |
| alembic | 1.13.x | Database migrations |

**Avoid:** 
- Raw SQL string concatenation (use ORM or parameterized queries only).
- Storing secrets in code or logs (use `.env` and secret hygiene rules).
- Using SQLite as a substitute for production PostgreSQL/MSSQL in tests (tests must use the real driver).
- Hardcoding model names or DB connection strings (load from config/env).

## Deployment Model
The agent runs as a long-running service via `uv run python -m src` (which starts Uvicorn on port 8001). It is designed for deployment behind a reverse proxy (NGINX/Apache) with TLS termination in production. In development, it runs locally on `http://localhost:8001`.