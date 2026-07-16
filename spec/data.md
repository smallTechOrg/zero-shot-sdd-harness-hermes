# Data Model — CCTNS Analyst

> We do **not** persist raw CCTNS rows. The mirror holds them. Our DB holds
> only audit/run metadata.

## Entities

### `AnswerRun`
One row per `POST /v1/answer` call.

| Field          | Type         | Notes                                             |
|----------------|--------------|---------------------------------------------------|
| `id`           | `str` (uuid) | primary key                                       |
| `request_id`   | `str` (uuid) | matches the in-process `state["request_id"]`      |
| `question`     | `str`        | length ≤ 2000                                     |
| `sql_template` | `str`        | the SELECT ran (empty if failed before execution) |
| `sql_attempts` | `int`        | 1 or 2                                            |
| `row_count`    | `int`        | 0 … row_cap                                       |
| `latency_ms`   | `int`        | ≤ statement_timeout + LLM time                   |
| `status`       | `enum`       | `pending` / `completed` / `failed`                |
| `error_message`| `str|None`   |                                                  |
| `created_at`   | `timestamp`  | UTC; default `now()`                              |
| `updated_at`   | `timestamp`  | UTC; `onupdate=now()`                             |

### `Question`
Intentionally **not** a separate table — questions are stored inline in
`AnswerRun`. (No PII separation needed in Phase 1; questions are operational
payloads, not user accounts.)

### `CctnsTable`
Mirror schema metadata, version-stamped. One row per logical table discovered
on the mirror. Holds column names + types only — never row data.

| Field         | Type         | Notes                                                |
|---------------|--------------|------------------------------------------------------|
| `name`        | `str`        | primary key (the logical table name)                 |
| `schema_name` | `str`        | e.g. `cctns_mirror`                                  |
| `columns_json`| `str`        | JSON list of `{name, type}`                          |
| `version`     | `str`        | bumped when mirror metadata changes; used for cache  |
| `captured_at` | `timestamp`  | UTC                                                  |

## Relationships

```
AnswerRun ──────(by request_id)─►──►── matching future runs (Phase 2)
```

(Phase 2 will add `Session` + `Turn` tables for conversation memory; not in
Phase 1.)

## Lifecycle

- `AnswerRun`: created at graph entry (`status=pending`), updated at finalize
  (`completed` or `failed`). Never mutated thereafter; audit-trail.
- `CctnsTable`: refreshed when the mirror's schema introspection reports a
  new version (Phase 3 connector).

## PII / Sensitivity

- Questions may contain case-identifying terms ("Lucknow district", "fir
  2024-0012") — treat as **sensitive**. We do not send the question text to
  any external telemetry, only to the LLM provider; logs include the
  question only on infra-level errors (Phase 3 audit log will gate this
  precisely).
- No row payloads ever persisted. Schema metadata only.

## Storage

- SQLite at `APP_DATABASE_URL=sqlite:///./data/agent.db` for `AnswerRun` and
  `CctnsTable`. Migrations via Alembic (`alembic upgrade head`).
