# Capability: Audit-Write Each Question

Every `/api/ask` request writes exactly one `answer_runs` row to the SQLite audit log (`data/agent.db`). The row is updated from `pending` to its final status after the graph completes.

## What It Does

A pure SQLAlchemy persistence step. The API inserts a `pending` row at the start of the request, then updates it with the final state after the graph returns. The status field encodes the outcome.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `request_id` | UUID string | per-request | yes |
| `question` | string | `req.question` | yes |
| `sql_template` | string | graph final `sql` (may be empty) | no (filled on completion) |
| `sql_attempts` | int | graph final | no |
| `row_count` | int | graph final | no |
| `latency_ms` | int | wall-clock of the whole API call | no |
| `tokens_used` | int | Gemini usage_metadata total (0 if unavailable) | no |
| `status` | `pending`/`completed`/`failed` | lifecycle | yes |
| `error_message` | string \| null | graph final | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| (row persisted in `data/agent.db`) | ORM `answer_runs` row | audit log |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite via SQLAlchemy 2.0 | `INSERT` then `UPDATE` | API still returns the request outcome; audit failure is logged to stdout but is not blocking in Phase 1 |

## Business Rules

- One row per request, no exceptions.
- `created_at`/`updated_at` are UTC.
- The `id` is a UUID generated in Python (not the DB) for testability.
- Phase 2: prune-on-insert so older than 50 rows are deleted.

## Success Criteria

- [ ] `GET /api/usage` returns a `total_questions` count strictly greater than the count before any `/api/ask` call was made.
- [ ] The `last_questions` array contains the just-completed request as the newest entry.
- [ ] On a `failed` request, `status = "failed"` and `error_message` is non-null.
- [ ] On a `completed` request, `sql_template` is non-empty and starts with `SELECT` (or `WITH`).
