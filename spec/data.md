# Data Model

> Two storage backends:
> 1. **Microsoft SQL Server** — read-only source of data; we do NOT define its schema, we introspect at startup.
> 2. **SQLite audit log** — owned by this app; one table: `answer_runs`.

---

## MSSQL source (read-only)

We do NOT persist or migrate MSSQL. The agent reads `INFORMATION_SCHEMA.TABLES` and `INFORMATION_SCHEMA.COLUMNS` once at startup and caches the result for the lifetime of the process. The agent never queries raw rows through the LLM (only schema + counts/aggregates leave the box).

**Cached schema shape (Python):**
```python
dict[table_name, list[{"name": str, "type": str}]]
```

When the LLM needs to reference the schema, this dict is serialised into the prompt payload (NOT the row data).

## SQLite audit log

File path: `data/agent.db` (overridable via `AGENT_DATABASE_URL`). One table for Phase 1:

### `answer_runs`

| Column          | Type                | Notes |
|-----------------|---------------------|-------|
| `id`            | TEXT PRIMARY KEY    | UUID v4, default in Python. |
| `request_id`    | TEXT NOT NULL       | UUID of the HTTP request. |
| `question`      | TEXT NOT NULL       | The user's question. |
| `sql_template`  | TEXT NOT NULL       | The SQL the agent ran (empty if `status=failed` before SQL was generated). |
| `sql_attempts`  | INTEGER NOT NULL    | Number of nl_to_sql attempts (Phase 1 ≈ 1 unless bug). |
| `row_count`     | INTEGER NOT NULL    | Rows returned by MSSQL (0 if no SQL ran). |
| `latency_ms`    | INTEGER NOT NULL    | Total request wall-clock. |
| `tokens_used`   | INTEGER NOT NULL    | Sum of input+output tokens reported by Gemini (0 if unavailable). |
| `status`        | TEXT NOT NULL       | `pending` / `completed` / `failed`. |
| `error_message` | TEXT NULL           | Public error message on `failed`. |
| `created_at`    | TIMESTAMP NOT NULL  | UTC. |
| `updated_at`    | TIMESTAMP NOT NULL  | UTC. |
| `result_columns_json` | TEXT NOT NULL | Phase-2: JSON list of column names (e.g. `["n"]`). Defaults to `[]`. |
| `result_rows_json`    | TEXT NOT NULL | Phase-2: JSON list-of-lists of row values. Defaults to `[]`. |
| `day`                | TEXT NOT NULL | Phase-2: UTC day as ISO `yyyy-mm-dd`, populated at insert. Defaults to `1970-01-01`. |

### Indexes (Phase 1)
- Primary key only. Phase 2 adds `(created_at DESC)` for the "last 50 questions" sidebar.

## Lifecycle

- A row is inserted with `status=pending` at the start of every `/api/ask` call.
- It is updated to `status=completed` or `status=failed` after the graph finishes.
- No automatic deletion in Phase 1. Phase 2 introduces a "keep last N=50" prune-on-insert.

## Phase 2/3 entities (deferred)

- `conversations` — multi-turn session memory (Phase 2).
- `usage_daily` — daily token rollup (Phase 2).
