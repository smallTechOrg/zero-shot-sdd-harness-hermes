# API — Auto-Podcaster

## API Style

REST + Server-Sent Events (SSE). CORS enabled for the local frontend origin.

## Endpoints / Commands

### `GET /health`

**Purpose:** Liveness/readiness probe. Returns service status; never calls external APIs.

**Response:**
```json
{ "status": "ok" }
```

**Error cases:** none (always 200 if the process is up).

---

### `POST /api/podcast/generate`

**Purpose:** Start a podcast generation for a topic + selected hosts. Creates a session row and
returns its `session_id`. The audio is then consumed from the SSE stream (see below).

**Request:**
```json
{
  "topic": "future of remote work",
  "hosts": ["maya", "leo"]
}
```
- `topic` (string, required): one-line topic. Max 200 chars.
- `hosts` (array of string, required): 2–3 host persona ids from the fixed cast (see
  `spec/ui.md` / `src/prompts.py`).

**Response `200`:**
```json
{ "session_id": "8f3c...", "status": "generating" }
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | missing/invalid `topic` or `hosts` (wrong count, unknown host id) |
| 500 | Gemini key missing/invalid (surfaced; points at `.env`) |

---

### `GET /api/podcast/stream/{session_id}`

**Purpose:** Stream the generated audio as Server-Sent Events. Content-Type `text/event-stream`.
The client reads events and plays audio chunks live.

**SSE event types:**
- `event: audio` → `data: <base64-or-binary mp3 chunk>` — one per TTS chunk.
  - Phase 1 uses newline-delimited binary: each `data:` line carries a base64 mp3 chunk for easy
    `<audio>` playback via a MediaSource/concatenation in the browser.
- `event: done` → `data: {"status":"done","download_url":"/api/podcast/download/{session_id}"}`
- `event: error` → `data: {"status":"failed","message":"..."}`

**Error cases:**
| Status | Condition |
|--------|-----------|
| 404 | unknown `session_id` |
| 500 | stream interrupted by upstream failure (also emits `error` event) |

---

### `GET /api/podcast/download/{session_id}`

**Purpose:** Download the finished episode as an mp3 file.

**Response:** `200`, `Content-Type: audio/mpeg`, `Content-Disposition: attachment`.

**Error cases:**
| Status | Condition |
|--------|-----------|
| 404 | unknown session or audio not ready (status != `done`) |

---

## Dialogue Turn Format (internal contract)

Each Gemini turn returns a single line in the form:

```text
SPEAKER: <one line of dialogue>
```

The dialogue node parses `SPEAKER` to the matching host and accumulates `Turn(speaker, text)`.
An episode ends when Gemini returns `[END]` or `MAX_TURNS` is reached.

## Authentication

None. Single-user local app. The only secret is `AGENT_GEMINI_API_KEY`, read from repo-root `.env`
at startup — never exposed via any endpoint, log, or response.
