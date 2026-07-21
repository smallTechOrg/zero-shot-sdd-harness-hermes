# UI

> Static server-rendered UI mounted at `/app` in Phase 1. No SPA framework.

## UI Type

Static web dashboard (zero-build HTML/CSS/JS from `frontend/public/`).

## Views / Screens

### Screen: Analysis Form

**Purpose:** Primary user journey. User enters or pastes CSV/JSON and a question; the agent returns insight + chart spec.

**Key elements:**
- Dataset textarea (`#text`)
- Instruction input (`#instruction`)
- Run button (`#run-btn`)
- Status indicator
- Error panel
- Result panel with insight text and chart metadata

**Actions available:**
- Submit run against the active LLM or see explicit failure when no key is configured

### Screen: Run History

**Purpose:** Show prior runs with run id, provider, model, and status.

**Key elements:**
- History list pulled from `/runs` semantic surface implemented in Phase 2; in Phase 1 this may be a non-functional labelled stub.

## Error States

- No API key: badge shows `no API key — set one in .env`; button remains enabled but run surfaces provider error in the error panel.
- Run failed: status + `error_message` shown under Error; Result remains hidden.
- Network/server error: catch block shows backend failure.

## Tech Stack

Plain HTML + CSS + JS from `frontend/public/`, served by FastAPI at `/app`. No npm/bundler in Phase 1. Phase 2 may add Chart.js CDN for chart rendering.
