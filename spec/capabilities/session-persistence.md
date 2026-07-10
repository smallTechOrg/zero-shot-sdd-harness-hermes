# Capability: Session Persistence & Download

## What It Does

Persists each generation as a SQLite session row (topic, hosts, status, audio path) and serves the
finished episode as a downloadable mp3.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| session_id | string | generate response | yes |
| audio bytes | bytes | TTS node | yes (on done) |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| session row | SQLite | `data/podcasts.db` |
| mp3 file | file | `data/<session_id>.mp3` |
| download response | HTTP | browser |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | insert/update session | logged; if DB unwritable, app fails to start |

## Business Rules

- A session row is created on generate (status `generating`).
- On completion, status → `done` and `audio_path` is set; the browser gets a `done` SSE event with
  the download URL.
- Download returns 404 until status is `done`.

## Success Criteria

- [ ] A generate call creates a session row; a completed run flips to `done` with a real file path.
- [ ] The saved file is a valid, non-empty mp3 (asserted by tests reading the bytes).
- [ ] `GET /api/podcast/download/{id}` returns the file only when `done`.
