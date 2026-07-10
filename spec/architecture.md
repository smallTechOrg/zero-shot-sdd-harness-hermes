# Architecture — Auto-Podcaster

## System Overview

Auto-Podcaster is a single-user web app: the browser is the only client. A FastAPI backend owns the
whole generation pipeline (dialogue → TTS → streaming) and persistence; a Next.js frontend is a thin
client that posts a Generate request and plays the resulting SSE audio stream live, then offers a
download. There is no agent framework — the "agent" is a deterministic three-node pipeline
(dialogue-generator → TTS → streamer) orchestrated by the API layer.

## Component Map

```text
[Browser / Next.js]
    │  POST /api/podcast/generate {topic, hosts}
    │  GET  /api/podcast/stream/<id>  (text/event-stream)
    ▼
[FastAPI app]
    │
    ├─ dialogue-generator (Gemini) ──► turn list (speaker, text)
    ├─ TTS (edge-tts)            ──► per-line audio bytes
    ├─ streamer                  ──► SSE audio chunks + final mp3
    │
    └─ SQLite (session + file path)
```

## Layers

| Layer | Responsibility |
|-------|----------------|
| API | Accept generate requests, create session rows, expose SSE stream + health + download. |
| Dialogue | Call Gemini turn-by-turn to produce a coherent multi-host script. |
| TTS | Convert each script line to audio via edge-tts (distinct voice per host). |
| Stream | Emit audio chunks over SSE as synthesized; persist full audio to a file. |
| Storage | SQLite: sessions table (id, topic, hosts, status, audio_path, created_at). |

## Data Flow

1. Trigger: user submits topic + selected host personas from the frontend.
2. Backend creates a session row (status `generating`) and returns `session_id`.
3. Frontend opens the SSE stream for that `session_id`.
4. Dialogue-generator yields turns (speaker + line) one at a time from Gemini.
5. TTS node converts each line to audio bytes (host-specific voice) and the streamer emits an SSE
   `audio` event with the chunk.
6. Chunks are also appended to a file; on completion the file is finalized (mp3) and the session
   status flips to `done` with the `audio_path`.
7. Frontend plays chunks live; on the `done` event it reveals the download link.

## External Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| Gemini (Google Generative AI) | Dialogue generation per turn. | Surfaced as a 500 / SSE error event; session marked `failed`. No silent fallback. |
| edge-tts (Microsoft) | Text-to-speech per host. | Surfaced as SSE error event; session marked `failed`. |
| SQLite | Local session + file-path persistence. | App fails to start if DB file unwritable. |

## Stack

- **Language:** Python 3.11 (backend). TypeScript / React 19 (frontend).
- **Agent framework:** none — deterministic three-node pipeline orchestrated by the API layer.
- **LLM provider + model:** Google Gemini, `models/gemini-2.5-flash` (verified available + working with the repo key).
- **Backend:** FastAPI + Uvicorn, SSE via `StreamingResponse`.
- **Database + ORM:** SQLite (local/single-user), accessed via `sqlite3` stdlib wrapper (no ORM needed for one table).
- **Frontend:** Next.js (App Router) + React, vanilla fetch + `<audio>` for SSE.
- **Dependency management:** pip + `requirements.txt` for backend (venv). npm for frontend.

| Key library | Version | Purpose |
|-------------|---------|---------|
| `google-generativeai` | latest | Gemini dialogue generation |
| `edge-tts` | latest | Free per-host TTS (no API key) |
| `fastapi` / `uvicorn` | latest | HTTP + SSE server |
| `python-dotenv` | latest | Load repo-root `.env` |
| `pytest` | latest | Backend tests |

**Avoid:** paid TTS (ElevenLabs et al.) for v1; a heavy agent framework (LangGraph) — the pipeline is a simple linear flow; any ORM beyond what one table needs.

> **Assumed:** Frontend uses plain `fetch` + EventSource-free manual SSE parsing (EventSource only
> supports GET; we POST to generate then GET the stream by id). Next.js dev server on :3000, backend
> on :8001. These are documented in `spec/ui.md` / `spec/api.md`.

## Deployment Model

Local, single-user. Backend runs as a long-lived Uvicorn process; frontend as the Next.js dev server.
No container, no cloud, no auth. (Sharing in Phase 5 is a future, optional addition.)
