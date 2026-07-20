# API

Base path: `/api/v1`. All responses JSON; errors use `{"detail": "..."}` or the baseline's `api_error` envelope.

## Authentication

Phase 1: open (no auth). Phase 3: JWT via `Authorization: Bearer <token>`; base implementation `src/api/auth.py`.

---

## Endpoints

### POST /api/v1/sessions

Create a new conversation session.

Request: `{}`

Response `201`:
```json
{
  "id": "uuid",
  "status": "active",
  "created_at": "ISO-8601",
  "schema_summary": null
}
```

---

### GET /api/v1/sessions/{session_id}

Fetch session metadata.

Response `200`:
```json
{
  "id": "uuid",
  "status": "active",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "schema_summary": { "tables": [...], "row_counts": {...} },
  "turn_count": 3
}
```

---

### POST /api/v1/sessions/{session_id}/csv

Upload one or more CSV files into the session's DuckDB.

Request: `multipart/form-data`; field name `files` (multiple).

Response `200`:
```json
{
  "session_id": "uuid",
  "uploaded": ["fir_2024.csv", "chargesheet_2024.csv"],
  "schema_summary": { "tables": [...], "row_counts": {...} },
  "errors": []
}
```

Errors: `422` if no files, `413` if any file exceeds `MAX_CSV_BYTES`, `500` on DuckDB write failure.

---

### POST /api/v1/sessions/{session_id}/runs

Submit a natural-language question.

Request:
```json
{ "input_text": "top 10 police stations by total FIRs" }
```

Response `200` (Phase 1 — synchronous, real-key path):
```json
{
  "run_id": "uuid",
  "status": "completed" | "failed" | "clarifying",
  "output_text": "{\"nl_answer\": \"...\", \"chart_spec\": {...}, \"kpis\": [...], \"audit_block\": {...}, \"plan_text\": \"...\", \"generated_code\": \"SELECT ...\", \"rows\": [...], \"row_count\": 10, \"latency_ms\": 1.24, \"result_hash\": \"sha256hex\", \"source\": \"duckdb\"}",
  "provider": "openrouter",
  "model": "anthropic/claude-sonnet-4-6",
  "plan_text": "SELECT ps_name, COUNT(*) ...",
  "generated_code": "SELECT ps_name, COUNT(*) ...",
  "rows": [...],
  "row_count": 10,
  "latency_ms": 1.24,
  "result_hash": "sha256hex",
  "source": "duckdb",
  "clarify_prompt": null
}
```

When `status=clarifying`, `clarify_prompt` contains a user-facing string the UI shows; `output_text` is still present (may contain partial plan_text).

When `status=failed`, `error_message` is populated instead of `output_text`.

---

### GET /api/v1/sessions/{session_id}/runs/{run_id}

Fetch a prior run by id. Same response shape as POST.

---

### POST /api/v1/db/connect  (Phase 2)

Submit MsSQL connection details. Server validates with `SET TRANSACTION READ ONLY` before accepting.

Request:
```json
{ "connection_string": "mssql+pyodbc://...", "connection_label": "CCTNS-Prod" }
```

Response `200`:
```json
{ "session_id": "uuid", "schema_summary": { "tables": [...] }, "cache_status": "ready" }
```

---

### GET /api/v1/db/cache/status  (Phase 2)

Return cache hydration state for the current session.

Response `200`:
```json
{ "session_id": "uuid", "tables": [{"name": "firs", "state": "cached", "last_refreshed_at": "..."}] }
```

---

## Rate-limiting

Per-session window: `RATE_LIMIT_RUNS_PER_MINUTE` (default 20). Burst-bucket: equal to the per-minute limit. Limit applies to POST /runs only. Return `429 Retry-After` when exceeded.

## Versioning

Single-version API in Phase 1. Phase 3+ adds `Accept: application/vnd.updatanalyst.v2+json` negotiation. Path prefix `/v1` to be added later without breaking embedding.
