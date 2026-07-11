# Data Model

## Storage Technology
SQLite (file: `data/music_tutor.db`), storing **only** per-student notation-mastery state. This is the chosen production store per the brief (private, per-student, local). No other data is persisted.

## Entities

### Entity: Student
Represents one learner profile. Phase 1 uses a single implicit profile; the id is supplied by the UI.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | Student identifier (PK) |
| display_name | str | no | Optional label |
| created_at | datetime | yes | Profile creation time (UTC) |

### Entity: Mastery
One row per (student, topic). Tracks how well a notation topic is known.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | str | yes | PK (uuid) |
| student_id | str | yes | FK → Student.id |
| topic | str | yes | Notation topic key, e.g. `treble:C4` or `bass:G2` (note-name family / clef) |
| weight | float | yes | Leitner-style mastery weight (0.0–1.0+); higher = known |
| attempts | int | yes | Total attempts on this topic |
| correct | int | yes | Correct attempts |
| updated_at | datetime | yes | Last update (UTC) |

### Relationships
- Student 1 — * many Mastery (by `student_id`).

## Data Lifecycle
- A `Student` row is created lazily on first drill start for an unknown `student_id`.
- Each answer updates the matching `Mastery` (weight up on correct, down on miss; attempts/correct counters).
- Nothing is ever deleted in Phase 1; no PII beyond an optional display name.

## Sensitive Data
- Only notation-mastery is stored — no audio, no prompts, no conversations. The `display_name` is the only user-supplied free text and is local-only.
