# Architecture — AI Music Tutor

## System Overview

A single-page web app (Next.js, statically exported and served by the FastAPI backend) drives one exercise at a time. The backend owns all correctness-critical logic: it **computes** the note name from the rendered pitch (deterministic music theory), synthesises the note's audio locally, and checks the student's answer against the computed name. Gemini is called **once per drill set** to produce teaching text (hints, tips, the reasoning behind the drill) — never the note name. `edge-tts` speaks that text. A private SQLite DB stores only per-student notation-mastery state.

## Component Map

```
[Browser: Next.js UI]
   │  REST + SSE
   ▼
[FastAPI backend  :8001]
   ├── /app  → serves built Next.js static export
   ├── /api/exercises/start  → starts a drill set (ONE Gemini call)
   ├── /api/notes/next       → next computed exercise (streamed)
   ├── /api/notes/{id}/check → checks answer vs COMPUTED name
   ├── /api/notes/{id}/audio → local-synth WAV
   ├── /api/notes/{id}/speak → edge-tts MP3 of teaching text
   └── /api/mastery          → per-student mastery state
        │
        ├── music/      deterministic theory (MIDI↔name, staff placement, clefs)
        ├── synth.py    numpy→WAV local audio (no deps)
        ├── llm.py      Gemini client (one call per set)  ← REAL key from .env
        ├── speech.py   edge-tts (free)
        └── db.py       SQLite per-student mastery
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| UI (Next.js) | Render staff, capture click-answer, play audio, show reasoning+tokens, SSE stream |
| API (FastAPI) | Route handlers, schema validation, serving static UI, SSE |
| Domain (music/) | Deterministic note-name computation, staff coordinates, clef logic |
| Service | Drill selection (adaptive), Gemini teaching-text generation, audio synth, TTS, mastery store |
| Storage | SQLite — per-student mastery only |

## Data Flow

1. Tutor clicks **Start drill** → UI `POST /api/exercises/start` with `student_id` + `clefs`.
2. Backend calls Gemini **once** → teaching text + a suggested topic set; stores `drill_id`, returns the first exercise.
3. Backend computes the note (pitch, name, staff placement) deterministically; the note is rendered as SVG; `GET /audio` returns the local-synth WAV.
4. Student clicks a note name → `POST /api/notes/{id}/check` → backend compares to the **computed** name → correct/incorrect + computed hint.
5. On incorrect → UI speaks a hint (edge-tts) and lets the student retry; mastery for that topic is down-weighted.
6. On correct → mastery up-weighted; next note is selected (adaptive) and **streamed** via SSE.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gemini (`AGENT_GEMINI_API_KEY`) | Teaching text, hints, tips — ONE call per drill set | If key missing: backend returns a deterministic fallback teaching text and logs a warning; exercises still generate and check (correctness is never LLM-dependent). |
| edge-tts | Free speech for hints/answers | If offline: speech endpoint returns 503; UI shows the text instead of audio. |
| ffmpeg (optional) | Not required — audio is synthesised in-process as WAV. | N/A |

## Stack

> **Note:** the harness skeleton defaults (LangGraph/Anthropic/PostgreSQL) are **overridden** by the explicit brief. This project is a deterministic single-LLM-call service, so no agent framework is used.

- **Language:** Python 3.11
- **Agent framework:** none (single deterministic service + one Gemini call per drill set)
- **LLM provider + model:** Google Gemini — `gemini-2.5-flash` (fast/cheap; configurable via `AGENT_LLM_MODEL`). Key: `AGENT_GEMINI_API_KEY` from `.env`.
- **Backend:** FastAPI (serves API + the static-exported Next.js UI on `:8001/app/`)
- **Database + ORM:** SQLite (per-student mastery only) + `sqlite3` stdlib. Chosen as the **production** store per the brief ("per-student profile, private"); not a PostgreSQL substitute.
- **Frontend:** Next.js 15 + React 19 + Tailwind v4 (static export, `basePath: '/app'`, mounted by FastAPI)
- **Dependency management:** pip (`.venv`) for Python / npm for frontend
- **Audio synthesis:** in-process numpy → 16-bit PCM WAV (zero external deps, free)
- **Speech:** `edge-tts` (free)

| Key library | Version | Purpose |
|-------------|---------|---------|
| fastapi | ^0.115 | HTTP API + static UI serving + SSE |
| uvicorn | ^0.34 | ASGI server |
| google-genai | ^1.0 | Gemini client (one call per drill set) |
| edge-tts | ^1.2 | Free speech synthesis |
| numpy | ^2.0 | Audio WAV synthesis |
| pytest | ^8.3 | Tests |
| next / react / react-dom | 15 / 19 | Frontend |
| tailwindcss v4 | ^4.0 | Styling |

**Avoid:** any package that trusts an LLM for the *correct* note name; any paid audio/TTS API; per-student data beyond notation mastery.

## Deployment Model

Local-first: `python -m src` starts uvicorn on `:8001`, serving the API and the pre-built UI from `frontend/out` at `http://localhost:8001/app/`. The UI must be built once (`cd frontend && npm run build`) before the server is launched. Suitable for a teacher's laptop; no cloud required.
