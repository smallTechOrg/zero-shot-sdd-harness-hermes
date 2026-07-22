# Roadmap

---

## What This Agent Does

The Crime Statistics Analysis Agent allows detectives and crime analysts to upload multiple CSV datasets, which are automatically merged and schema-mapped. Users can query the agent in natural language to uncover trends, anomalies, and resource allocation recommendations. The agent acts as an AI data analyst, returning a structured dashboard with executive summaries, key findings, and time-series charts.

## Who Uses It

- **Detectives & Crime Analysts:** Investigating long-term trends across districts, correlating different crime types, and planning resource allocation. They need fast, reliable answers backed by data and visual charts without writing SQL or Python code themselves.

## Core Problem Being Solved

Detectives often have disparate CSV reports with differing schemas. Merging these files and writing scripts/SQL to analyze them takes hours or days. This agent replaces the manual data wrangling and charting process, enabling instant natural language exploration of the data.

## Success Criteria

- [ ] Users can upload multiple CSV files (up to 100MB total) and the agent successfully merges them in memory.
- [ ] Users can ask "Compare crime trends year-wise" and receive a structured dashboard with a time-series chart.
- [ ] The system accurately identifies missing dates/columns and either infers them or gracefully fails.
- [ ] The agent remembers conversation history within a session for follow-up questions.

## What This Agent Does NOT Do (Out of Scope)

- The agent does not save CSV data permanently (data is session-bound).
- The agent does not train new ML models (it relies on zero-shot LLM reasoning and Pandas for deterministic calculations).
- The agent does not connect to live police dispatch databases (batch CSV uploads only).

## Key Constraints

- **Scale:** Supports files up to ~100MB (~100,000 rows), processed in-memory using Pandas.
- **Privacy:** Data is strictly session-bound and wiped when the session expires or the UI is closed.
- **Provider:** Must use the Gemini API (via `AGENT_GEMINI_API_KEY`).

## Phases of Development

### Phase 1 — End-to-End Single Query on Merged CSVs

- **Goal:** Allow the user to upload multiple CSVs (up to 100MB total), which are automatically merged and mapped. The user can ask a single question, and the agent returns a structured dashboard response with summary and time-series line charts.
- **Independent slices (parallel build units):**
  - `slice-backend-core` (backend) — API endpoints (`/upload`, `/analyze`, `/health`), CSV merging/mapping logic via pandas, and LangGraph agent setup. deps: none
  - `slice-frontend-core` (frontend) — React dashboard skeleton (Vite), drag & drop upload component, loading animation, and structured result view. deps: none
- **Key surfaces / files:**
  - `slice-backend-core`: `src/api/routes.py`, `src/services/csv_service.py`, `src/graph/nodes.py`, `src/graph/state.py`
  - `slice-frontend-core`: `frontend/src/App.tsx`, `frontend/src/components/Upload.tsx`, `frontend/src/components/Dashboard.tsx`, `frontend/src/index.css`
- **Gate command:** `uv run pytest tests/test_phase1.py`
- **How the user tests it (handoff seed):** Run the backend (`uv run python -m src`) and frontend dev server (`cd frontend && npm run dev`). Open the UI, drag two sample CSVs, and ask "Which district has the most crime?". Expect a dashboard with a summary and a bar chart.

### Phase 2 — Multi-Turn Conversational Memory & Advanced Capabilities

- **Goal:** Introduce session memory so detectives can ask follow-up questions about the data, and add anomaly/hotspot detection capabilities.
- **Independent slices (parallel build units):**
  - `slice-backend-memory` (backend) — SQLite integration for conversational state and session storage. deps: slice-backend-core
  - `slice-frontend-chat` (frontend) — Interactive chat UI updates to support history and follow-up prompts. deps: slice-frontend-core
- **Key surfaces / files:**
  - `slice-backend-memory`: `src/db/database.py`, `src/db/models.py`, `src/graph/memory.py`
  - `slice-frontend-chat`: `frontend/src/components/Chat.tsx`, `frontend/src/App.tsx`
- **Gate command:** `uv run pytest tests/test_phase2.py`
- **How the user tests it (handoff seed):** Ask a follow-up question in the UI: "Drill down into District A". Expect the agent to remember the context of the first query and return specific data for District A.

### Phase 3 — Production Readiness & Polish

- **Goal:** Dockerization, robust error handling for edge-case files, full test coverage, logging enhancements, and final UI polish (dark/light mode).
- **Independent slices (parallel build units):**
  - `slice-ops` (backend) — `Dockerfile`, `docker-compose.yml`, README updates. deps: none
  - `slice-testing-ui` (frontend) — UI theme toggle, error boundary components. deps: slice-frontend-chat
- **Key surfaces / files:**
  - `slice-ops`: `Dockerfile`, `docker-compose.yml`, `README.md`
  - `slice-testing-ui`: `frontend/src/components/ThemeToggle.tsx`, `frontend/src/index.css`
- **Gate command:** `uv run pytest tests/test_phase3.py`
- **How the user tests it (handoff seed):** Toggle dark/light mode. Upload a malformed CSV and verify the error is displayed cleanly.
