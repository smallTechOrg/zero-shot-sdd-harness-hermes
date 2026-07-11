# Data Model — `scaffold-agent`

---

## Storage Technology

SQLite (dev) via SQLAlchemy 2.0 core + Alembic. Production swaps to Postgres by changing `DATABASE_URL` — migrations are identical.

## Entities

### Entity: `Run`

Represents a single agent invocation. Used for observability in dev.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | yes | Primary key |
| created_at | DateTime | yes | Run start time |
| status | String(32) | yes | queued / running / succeeded / failed |
| user_message | Text | yes | Last user message (Phase 1 stores the request body). |
| assistant_message | Text | no | Generated reply, if any. |
| error_message | Text | no | Reason for failure, if any. |

### Entity: `Message` (optional Phase 1)

Persisted chat history.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | yes | Primary key |
| run_id | Integer | yes | Foreign key to `Run`. |
| role | String(16) | yes | `user` or `assistant`. |
| content | Text | yes | Message body. |
| created_at | DateTime | yes | Message time. |

## Relationships

- Run 1..n Message.

## Data Lifecycle

- Created on `POST /api/chat`.
- Updated when the agent writes its reply.
- No deletion strategy in Phase 1; runs table grows unbounded; user can delete `data/app.db`.

## Sensitive Data

- `.env` is ignored by git. No PII. The chat history is ephemeral and local.
