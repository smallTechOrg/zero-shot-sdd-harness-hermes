# Data

## Entities

### session

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID (PK) | Server-generated |
| `created_at` | datetime (UTC) | |
| `updated_at` | datetime (UTC) | |
| `status` | enum(active, archived, evicted) | evicted = LRU'd when over MAX_SESSIONS |
| `schema_summary` | JSON | DuckDB schema snapshot cached at upload time — tables, columns, types, row counts |
| `prior_summary` | str \| None | Summary of now-truncated conversation history for context continuity |
| `turn_count` | int | Incremented on each run completion |

Relationships: 1 session → N runs, 1 session → N uploaded CSVs (tracked only in DuckDB file; not separately persisted).

### run

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID (PK) | |
| `session_id` | UUID (FK → session.id) | |
| `status` | enum(pending, running, completed, failed, clarifying) | |
| `input_text` | text (NOT NULL) | Copy of the user's question at submission time |
| `instruction` | text (NOT NULL) | Alias for input_text for compatibility with baseline schema |
| `output_text` | JSON \| None | Full `{nl_answer, chart_spec, kpis, audit_block, plan_text, generated_code, rows, row_count, latency_ms, result_hash, source}` |
| `provider` | str \| None | LLM provider slug |
| `model` | str \| None | LLM model name |
| `error_message` | str \| None | Populated on failure |
| `created_at` | datetime (UTC) | |
| `updated_at` | datetime (UTC) | |

Relationships: N runs → 1 session.

### query_log

Phase 1 write-log; append-only — never updated or deleted by application code.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID (PK) | |
| `session_id` | UUID | Best-effort; may be null on hard errors |
| `user_id` | str \| None | Phase 3+; null until auth |
| `question` | text | Exact user question |
| `generated_code` | text \| None | Full SQL or Python |
| `code_language` | enum(sql, python) \| None | |
| `source` | enum(duckdb, mssql, mssql-cache) \| None | |
| `row_count` | int \| None | |
| `latency_ms` | float \| None | |
| `result_hash` | str \| None | SHA-256 of deterministic row payload |
| `status` | enum(success, failed, clarified_error) | |
| `error_message` | str \| None | |
| `created_at` | datetime (UTC) | |

Phase 2 adds:

### db_connection

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID (PK) | |
| `session_id` | UUID | |
| `connection_label` | str | Human-readable name for the connection |
| `connection_string` | text (encrypted at rest) | Phase 3: encrypted before write |
| `schema_version_hash` | str \| None | SHA-256 of last introspected schema; triggers re-fresh |
| `last_refreshed_at` | datetime (UTC) \| None | |
| `created_at` | datetime (UTC) | |
| `updated_at` | datetime (UTC) | |

Phase 2 adds:

### cache_snapshot

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID (PK) | |
| `session_id` | UUID | |
| `source_table` | str | MsSQL table reflected into DuckDB |
| `duckdb_file` | str | Path of the materialized DuckDB file |
| `row_count` | int | |
| `refresh_strategy` | enum(manual, scheduled, on_first_miss) | |
| `last_refreshed_at` | datetime (UTC) | |
| `expires_at` | datetime (UTC) \| None | TTL from env var; null = live |

Relationships: 1 session → N cache_snapshots, each pointed at one MsSQL source table.

## Lifecycle

```
Upload CSV:
  POST /csv → create_session (or add to existing)
  → ingest CSV into DuckDB session file
  → cache schema_summary (in-memory + stored in session)
  → session.status = active

Ask question:
  POST /runs
  → state: pending → running
  → plan → query → execute → explain
  → state: completed (or failed / clarifying)

Clarify round:
  state: clarifying
  ← user reply re-submitted with original question prepended
  → re-enter plan node with full context
  → (no new run_id — same run, same run_id)

DB connection (Phase 2):
  POST /db/connect
  → validate connection (SET TRANSACTION READ ONLY)
  → introspect live MsSQL schema
  → write schema_summary + db_connection row
  → flag session as `has_live_db = True`

Cache refresh (Phase 2):
  cache miss on mssql table:
  → READ ONLY query on live DB
  → write result set to DuckDB cache file
  → update cache_snapshot row (last_refreshed_at, row_count)
  → return rows

Session eviction (LRU):
  touch_count evicted on over MAX_SESSIONS
  → qa-auditor: older sessions may have pending jobs; cancel before evict
```

## Security & Privacy Notes

- No data leaves the on-prem network except the LLM API call to OpenRouter (text-only; no file/DB data sent to the LLM — only the schema summary and the generated SQL).
- Row contents stay entirely in DuckDB memory.
- The `query_log` table is append-only — no UPDATE/DELETE paths exist in the application.
- `db_connection.connection_string` is unencrypted in Phase 1 Phase 2 adds encryption-at-rest for this column.
