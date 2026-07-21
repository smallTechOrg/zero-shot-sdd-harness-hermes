# Data Model

---

## Storage Technology

- **Phase 1:** SQLite via SQLAlchemy 2.0 (local dev DB + dataset metadata + audit log)
- **Phase 2:** pyodbc (MsSQL read-only) + SQLite for persistent cache + audit log
- **Artifacts:** local filesystem under `./assets/` (charts, reports) with cleanup TTL

## Entities

### Entity: Dataset

Represents one uploaded CSV or MsSQL datasource connection.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | yes | Primary key |
| user_id | str | yes | Uploading / connecting user |
| name | str | yes | Display name |
| source_type | enum: `csv` / `mssql` | yes | Origin |
| schema | JSON | yes | Inferred schema: columns, types, sample rows, row_count |
| file_path | str | no | CSV storage path (Phase 1) |
| mssql_connection | JSON | no | Encrypted connection string (Phase 2) |
| created_at | datetime | yes | Upload timestamp |
| last_queried_at | datetime | no | For cache staleness |

### Entity: Session

A conversation session associated with one or more datasets.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | yes | Primary key |
| user_id | str | yes | Owner |
| dataset_ids | JSON | yes | List of linked dataset IDs |
| created_at | datetime | yes |
| last_active_at | datetime | yes |
| context_summary | str | no | Compressed conversation context for multi-turn |

### Entity: QueryRun

One agent run answering a single question.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | yes | Primary key |
| session_id | UUID | yes | FK to session |
| user_id | str | yes | Who asked |
| question | str | yes | Raw NL question |
| datasource_id | UUID | yes | Active datasource at query time |
| plan | JSON | no | Agent plan |
| generated_sql | str | no | SQL / Python executed |
| result_columns | JSON | no | Column names + types |
| result_row_count | int | no | Row count returned |
| result_preview | JSON | no | First 100 rows (for audit, not full result) |
| evaluate_score | float | no | Confidence score |
| iteration_count | int | no | How many retry loops |
| latency_ms | int | no | Total run time |
| cache_hit | bool | no | Whether answer came from cache |
| status | enum: `success` / `failed` / `partial` | yes |
| error_message | str | no | If failed |
| chart_urls | JSON | no | Phase 2 |
| download_urls | JSON | no | Phase 2 |
| started_at | datetime | yes |
| completed_at | datetime | yes |

### Entity: QueryCache

Deduplicated query result for fast repeats.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | yes | Primary key |
| cache_key | str | yes | Hash of datasource_id + normalized SQL |
| generated_sql | str | yes |
| result_columns | JSON | yes |
| result_rows | JSON | yes | Full result cached |
| result_row_count | int | yes |
| created_at | datetime | yes |
| expires_at | datetime | yes | TTL-based eviction |

### Entity: AuditLog

Structured append-only log for compliance.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | yes | Primary key |
| run_id | UUID | yes | FK to QueryRun |
| user_id | str | yes |
| event_type | str | yes | e.g., `query_start`, `sql_generated`, `sql_executed`, `chart_rendered` |
| event_data | JSON | yes | Timestamped payload |
| created_at | datetime | yes |

## Relationships

- `Session` 1 ──── N `QueryRun` (a session has many query runs)
- `QueryRun` 1 ──── 1 `QueryCache` (cache miss creates cache; hit reuses)
- `QueryRun` 1 ──── N `AuditLog` (each step logged)
- `Session` N ──── N `Dataset` (a session links to 1+ datasets via `Session.dataset_ids` JSON)

## Data Lifecycle

- Datasets are created on CSV upload or MsSQL connect. CSV files are stored in `./data/uploads/` for the session lifetime.
- QueryRuns are immutable once completed (audit compliance).
- QueryCache entries expire after `CACHE_TTL` (configurable, default 1 hour). Cache invalidation on new dataset upload or explicit TTL expiry.
- AuditLog entries are append-only; retention policy: 180 days, then archive (configurable via `RETENTION_DAYS`).

## Sensitive Data

- **PII fields in raw CSV:** Not stored in preview beyond `result_preview` (top 100 rows, dev-only). Production should avoid persisting raw PHI.
- **MsSQL connection strings:** Stored encrypted at rest (`cryptography.fernet` key in `.env`).
- **Audit log:** Contains query text and schema metadata — treated as sensitive; access-controlled by role.
- **No row leaves the server:** All LLM inference is on-prem; API responses contain only results + metadata.
