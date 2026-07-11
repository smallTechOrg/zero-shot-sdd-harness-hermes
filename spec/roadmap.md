# Roadmap — `scaffold-agent`

> Filled by the spec-writer sub-agent. Every field is now authoritative for Phase 1.
> Tests run against real behavior on the tested path; generated outputs never enter `main`.

---

## What This Repo Does

This repo is the **scaffold product**: a self-contained hackathon starter-kit generator.
A user clones this repo and runs `scripts/bootstrap.py <project-name>` (or `npm`/`zero-shot-build` wrapper) to emit a complete, runnable project — FastAPI backend, React frontend, SQLite dev DB, Alembic migrations, Docker Compose, and a working agent stub — in a fresh directory.
The repo itself remains the template source on `main`; generated files never touch `main`.

## Who Uses It

Engineers in a hackathon or greenfield sprint who want a runnable FastAPI + React + SQLite skeleton immediately, without wiring ports, sessions, or migrations by hand.

## Core Problem Being Solved

Most scaffold repos are either empty boilerplate or opinioned generators that lock you into a framework.
This repo gives you a **single command scaffold** that drops a runnable agent scaffold into a sibling directory you can immediately open in Claude Code, Docker, or deploy to a GCP VM.

## Success Criteria

- `scripts/bootstrap.py my-project` creates a runnable project in a fresh directory in <60s.
- `cd my-project && docker compose up` serves both frontend and backend.
- `GET /health` returns 200.
- React loads and calls backend successfully.
- A real LLM key optionally enables live agent responses; without it, the stub behaves predictably.
- `npm run build` succeeds for the generated frontend.

## What This Repo Does NOT Do

- It does not implement user-facing application logic beyond the minimal agent stub.
- It does not manage generated projects in `main`.
- It does not include LangGraph, CrewAI, or AutoGen runtime in the base template (agent slot is a stub until Phase 2).
- It does not auto-deploy; deployment instructions are provided for GCP VM.

## Key Constraints

- `main` is spec + generator-only; generated project trees never land on `main`.
- Python setup uses `venv`, not system Python.
- npm is used for the generated frontend (no pnpm).
- The generated backend defaults to SQLite in dev, PostgreSQL-ready in prod.
- LLM keys are provided via `.env`; no secrets are committed.

## Phases of Development

> Each phase is one human-testable increment, behind a testing gate. Commands are exact.

### Phase 1 — Scaffold Kit (this handoff)

- **Goal:** Deliver a runnable scaffold kit where a single command creates a working FastAPI + React + SQLite project.
- **Independent slices:**
  - `slice-generator` (backend) — `scripts/bootstrap.py` + embedded templates, output materialisation, substitution engine.
  - `slice-backend-template` (backend) — FastAPI project manifest: `main.py`, `db.py`, `models.py`, `/health`, `/api/chat`, Alembic config.
  - `slice-frontend-template` (frontend) — Vite + React + TS chat UI, Tailwind, fetch wiring.
  - `slice-ops` (ops) — `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `.env.example`, README.
- **Gate command:** `uv run pytest tests/unit/ -v` (unit tests against `/health` using TestClient), plus `npm run build` inside the generated `frontend/`.
- **How the user tests it (handoff seed):**
  1. From repo root: `python3 scripts/bootstrap.py my-project`
  2. `cd my-project` (output is sibling to repo, never inside main).
  3. `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
  4. `docker compose up --build`
  5. Confirm `curl http://localhost:8000/health` -> 200.
  6. Confirm React loads at `http://localhost:5173` and the chat input calls `/api/chat`.
  7. `docker compose down`
  8. `cd frontend && npm install && npm run build` must pass.

### Phase 2 — Agent Slot (future)

- **Goal:** Wire the Phase-1 agent stub into a real LangGraph graph using pytest against a real API key.
- **Dependencies:** Phase 1 complete.
- **Gate command:** `uv run pytest tests/integration/ -v` with `ANTHROPIC_API_KEY` in `.env`.

### Phase 3 — Deploy Template (future)

- **Goal:** Add a `terraform/` or deployment manifest for a single GCP VM + Cloud SQL.
- **Dependencies:** Phase 2.
- **Gate command:** `cd deploy && terraform plan` (or documented equivalent).

### Phase 4 — Capability Plugin (future)

- **Goal:** Allow `--slot transform_text` or other capability names to swap the stub graph node and prompt template.
- **Dependencies:** Phase 2.
- **Gate command:** `python scripts/bootstrap.py my-agent --slot transform_text` produces a different graph node.
