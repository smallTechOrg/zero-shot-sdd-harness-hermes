# Architecture — `scaffold-agent`

> Single source of truth for Phase 1. Template source lives in `templates/; `scripts/bootstrap.py` is the generator.

---

## System Overview

This repo is both a **generator source** and a **spec harness**.
`main` contains:
- the canonical spec in `spec/`,
- engineering rules in `harness/`,
- a project-generation CLI in `scripts/`,
- embedded project templates in `templates/`.

A user runs `scripts/bootstrap.py <name>` (or wraps it via `scripts/new_agent.sh`) and a complete project tree is written to a fresh directory outside this repo.
The generated project is a runnable FastAPI + React + SQLite service with an agent stub.

## Component Map

```
templates/agent-project/   ← embedded source templates
    │
    ▼
scripts/bootstrap.py       ← generator engine (read + substitute + write)
    │
    ▼
<user-cwd>/<project-name>/ ← generated project (not in main)
    ├── backend/
    │     ├── main.py       ← FastAPI app
    │     ├── db.py         ← SQLAlchemy engine/session
    │     ├── models.py     ← ORM models
    │     ├── alembic/      ← migrations
    │     └── ...
    ├── frontend/
    │     ├── src/          ← Vite + React + TS
    │     └── package.json
    ├── docker-compose.yml
    ├── Dockerfile.*
    └── README.md
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| Generator | `bootstrap.py` reads `templates/`, substitutes tags, writes to `PROJECT_ROOT`. |
| API | FastAPI routers expose `/health` and `/api/chat`; optional `/api/runs` for trace storage in dev. |
| Agent Stub | A single node that returns a canned reply or forwards to an LLM if a key is present. |
| Data | SQLAlchemy 2 core + Alembic. SQLite in dev; swap to Postgres via DATABASE_URL without code changes. |
| Frontend | Vite + React + TypeScript. Calls `/api/chat` with fetch. |
| Ops | Docker Compose binds backend `:8000` and frontend dev server `:5173`. |

## Data Flow

1. User POSTs `{messages:[...]}` to `/api/chat`.
2. FastAPI validates with Pydantic (optional; MVP passes through).
3. Agent stub builds a prompt, checks `LLM_API_KEY` in env.
   - Key present: calls OpenAI-compatible or Anthropic-compatible endpoint.
   - No key: returns stub response with the user message echoed back with a canned prefix.
4. Response is returned as `{"reply": "..."}`.
5. Frontend appends user bubble and assistant bubble.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| OpenAI/Anthropic API | Live agent responses (optional) | Stub path is used automatically; service remains up. |
| Docker | Local dev via Compose | User can run backend/frontend manually with `npm run dev` + `uvicorn`. |
| npm | Frontend build | Fails clearly with `npm install` error. |
| uv / pip | Python deps | Fails clearly at install step. |

## Stack

- **Agent framework:** LangGraph-compatible supervisor graph (minimal in Phase 1; extensible to multi-worker, planning, reflection)
- **LLM provider + model:** Anthropic / `claude-sonnet-4-6` default; Gemini / `gemini-3.1-pro` alternative; OpenRouter fallback
- **Backend:** FastAPI + Uvicorn
- **Database + ORM:** PostgreSQL + SQLAlchemy 2.0 / Alembic in prod; SQLite in dev via DATABASE_URL switch
- **Frontend:** React 18 + Vite 6 + TypeScript + Tailwind in `web/`; optional Expo app in `mobile/`
- **Packaging:** `pyproject.toml` + venv in backend; `package.json` in frontends
- **Agent harness:** each generated project includes `harness/skills/<slug>/SKILL.md` plus `harness/agents/*.md` stubs for orchestrator, worker, and qa patterns
- **Protocol surfaces:** MCP server stub and A2A message channel stubs in generated backend

| Key library | Version | Purpose |
|-------------|---------|---------|
| fastapi | latest | API |
| uvicorn[standard] | latest | ASGI server |
| sqlalchemy | 2.x | ORM |
| alembic | latest | Migrations |
| react | 18 | Frontend UI |
| vite | 6 | Frontend tooling |
| axios or fetch | — | HTTP from frontend |

**Avoid:**
- LangGraph / CrewAI / AutoGen in the base template (Phase 1 stub keeps dependency surface small).
- SQLAlchemy 1.x (ver 2 only).
- TypeScript generation beyond the template (no transpile-from-JS).

## Deployment Model

- **Local dev:** `docker compose up` binds `:8000` and `:5173`.
- **GCP VM:** deploy with two containers on Cloud Run or a single GCE VM running Docker + Compose.
- **Migration:** `alembic upgrade head` runs as an init container or pre-start command in the backend Dockerfile.
