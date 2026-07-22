# API

> Single-origin backend serving both the API and the frontend at `/app`. Default dev port: `8001`.

## Endpoints

### `POST /api/upload_csv`

Upload one or more CSV files for analyst session use.

- **Request:** `multipart/form-data` with `files[]` and optional `analyst_id`
- **Response:** `{ "artifact_ids": [...], "dataset_summaries": [...] }`
- **Errors:** 400 on empty upload, 413 on excessive payload, 500 on storage failure

### `POST /api/runs`

Execute a question against uploaded CSV datasets.

- **Request body:** `{ "question": string, "csv_artifact_ids": string[], "filters"?: object, "analyst_id"?: string }`
- **Response:** `ok({ run_id, status, answer_text, table_payload, chart_payload, follow_ups, anomalies, output_files, provider, model, latency_ms, log })`
- **Errors:** 400 on missing question, 404 on missing artifact, 500 on execution failure

### `POST /api/mssql/query`

Execute a natural-language question against the live MsSQL connection.

- **Request body:** `{ "question": string, "mssql_connection_label"?: string, "analyst_id"?: string }`
- **Response:** `ok({ run_id, status, answer_text, table_payload, sql, query_fingerprint, cache_hit, row_count, latency_ms, provider, model })`
- **Errors:** 400 on missing question or connection, 500 on schema/SQL/execution failure

### `GET /api/mssql/schema`

Reflect schema objects relevant to the connection/context.

- **Query params:** `connection_label?`, `search?`
- **Response:** `ok({ tables: [...], columns: [...] })`
- **Errors:** 500 on reflection failure

### `POST /api/reports`

Save a named report from a run or free-text question.

- **Request body:** `{ "name": string, "question": string, "source_type": "csv" | "mssql", "source_config": object, "analyst_id"?: string }`
- **Response:** `ok({ report_id, name, created_at })`
- **Errors:** 400 on missing name/question, 409 on duplicate name for same analyst

### `POST /api/reports/{report_id}/rerun`

Re-execute a saved report and create a new run record.

- **Response:** `ok({ run_id, status, answer_text, table_payload, ... })`
- **Errors:** 404 on missing report, 410 if underlying dataset/connection is unavailable

### `POST /api/schedules`

Create or update a scheduled report.

- **Request body:** `{ "report_id": string, "cron": string, "enabled"?: boolean, "analyst_id"?: string }`
- **Response:** `ok({ schedule_id, report_id, cron, enabled, next_run_at })`
- **Errors:** 400 on invalid cron, 404 on missing report

### `GET /api/dashboard/tiles`

Return dashboard summary tiles.

- **Response:** `ok({ tiles: [...] })`
- **Errors:** 200 empty tiles if no history yet

### `GET /api/health`

Health + active provider/model metadata.

- **Response:** `ok({ status, provider, model, db: "ok" | "error" })`

## Envelope

Every successful response follows the `ok()` envelope; failures use structured API errors with code/message/status.
