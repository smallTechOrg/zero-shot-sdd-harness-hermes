# Data Model — Auto-Podcaster

## Storage Technology

SQLite (local, single-user). One table is sufficient for Phase 1. File at
`<project-root>/data/podcasts.db` (gitignored). Chosen because the app is explicitly local/single-user
(see `harness/patterns/tech-stack.md` — SQLite only for explicitly local/single-user).

## Entities

### Entity: session

One podcast generation run.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT (UUID) | yes | Primary key. |
| topic | TEXT | yes | The one-line topic the user entered. |
| hosts | TEXT (JSON) | yes | JSON array of selected host ids (2–3). |
| status | TEXT | yes | `generating` \| `done` \| `failed`. |
| audio_path | TEXT | no | Absolute path to the finished mp3 (set when `done`). |
| error | TEXT | no | Error message if `failed`. |
| created_at | TEXT (ISO8601) | yes | Generation start time. |
| updated_at | TEXT (ISO8601) | yes | Last status change. |

### Relationships

None (single table in Phase 1).

## Data Lifecycle

- Created on `POST /api/podcast/generate` with status `generating`.
- Updated to `done` (with `audio_path`) or `failed` (with `error`) as the pipeline finishes.
- Audio file written to `data/` as chunks arrive; finalized on `done`.
- No deletion in v1 (Phase 5 may add retention/cleanup).

## Sensitive Data

- `AGENT_GEMINI_API_KEY` is **never** stored in SQLite or anywhere in the app DB. It lives only in
  repo-root `.env`, loaded at startup. No PII is collected (single-user, local).
