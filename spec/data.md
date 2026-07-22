# Data

## Data Domains

This agent is local-first and does not own canonical police-domain schemas; its app-level domain models are execution and audit records. The live DB may contain any schema the deployment allowslist exposes.

### App Metadata (SQLite app DB)

| Entity | Key Fields | Lifecycle |
|--------|------------|-----------|
| `Run` | `run_id`, `analyst_id`, `source_type`, `question`, `status`, `provider`, `model`, `latency_ms`, `output_text`, `error_message`, `created_at`, `updated_at` | Created at question execution; read for history/dashboard; never deleted automatically |
| `NamedReport` | `report_id`, `analyst_id`, `name`, `question`, `source_config`, `created_at`, `updated_at` | Created on save; updated on edit; rerun creates linked `Run` records |
| `Schedule` | `schedule_id`, `analyst_id`, `report_id`, `cron`, `enabled`, `last_run_at`, `next_run_at`, `created_at`, `updated_at` | Created from saved report or standalone schedule; disabled rather than deleted |
| `CsvArtifact` | `artifact_id`, `analyst_id`, `filename`, `stored_path`, `sha256`, `column_summary`, `row_count`, `created_at` | Created on upload; retained for session and for named-report source binding |

### Live DB (MsSQL, read-only)

| Entity | Key Fields | Lifecycle |
|--------|------------|-----------|
| Allowlisted tables | table/column metadata from `inspect_mssql_schema` | Read-only reflection; no writes |
| Query cache | fingerprint → result rows + metadata | In-memory or local-disk cache keyed on SQL fingerprint and row cap |

### Input Artifacts (CSV uploads)

- Stored under a session-scoped local directory.
- Validated at upload: row count, column headers, type coercion summary, encoding detection.
- Retained for the duration of the session and bound to named reports if saved.

## Relationships

```
Analyst 1 ──► * Run
Analyst 1 ──► * NamedReport
NamedReport 1 ──► * Run (reruns)
NamedReport 1 ──► 1 Schedule (optional)
Schedule 1 ──► * Run (executed runs)
Analyst 1 ──► * CsvArtifact
Run ──► ? CsvArtifact (when source is CSV)
Run ──► ? Schema objects (when source is live DB)
```
