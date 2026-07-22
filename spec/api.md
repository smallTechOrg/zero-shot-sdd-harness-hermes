# API

> **Assumed:** FastAPI HTTP surface; uploads as `multipart/form-data`; JSON responses with standard `run_id` and `status` fields.
> **Assumed:** Phase 1 endpoints only; Phase 2/3 endpoints are stubbed in the UI but return 501 until implemented.

## Base

`/api/v1`

## Endpoints

| Method | Path | Purpose | Auth | Phase |
|--------|------|---------|------|-------|
| `POST` | `/api/v1/upload` | Upload one or more CSV files | Bearer token | 1 |
| `POST` | `/api/v1/query` | Ask a natural-language question over uploaded data or live DB | Bearer token | 1 |
| `GET` | `/api/v1/runs/{run_id}` | Fetch a completed run: answer, table, generated SQL, audit ref | Bearer token | 1 |
| `GET` | `/api/v1/runs/{run_id}/download` | Download the result set as CSV | Bearer token | 1 |
| `GET` | `/api/v1/health` | Provider + DB + cache status | None | 1 |
| `POST` | `/api/v1/auth/token` | Issue JWT for RBAC users | Form login | 3 |
| `POST` | `/api/v1/live-db/test` | Test connectivity to MsSQL / show cache status | Bearer token | 2 |
| `GET` | `/api/v1/workspaces` | List saved workspaces for current user | Bearer token | 3 |
| `POST` | `/api/v1/workspaces` | Create / update a named workspace | Bearer token | 3 |
| `GET` | `/api/v1/audit/export` | Export audit rows as CSV / JSON | Supervisor only | 3 |

## Request/Response Shapes

### `POST /api/v1/query`

**Request body**

```json
{
  "question": "How many thefts by district last month?",
  "data_source": "csv",
  "csv_file_ids": [12, 15],
  "workspace_id": null,
  "row_limit": 10000
}
```

**Response body**

```json
{
  "run_id": 101,
  "status": "completed",
  "answer_text": "There were 342 thefts across 12 districts...",
  "result_table": {
    "columns": ["district", "count"],
    "rows": [{"district": "Lucknow", "count": 78}]
  },
  "generated_sql": "SELECT district, COUNT(*) AS count FROM fir WHERE ...",
  "tables_touched": ["fir"],
  "executed_row_count": 78,
  "latency_ms": 1240,
  "provider": "nim",
  "model": "meta/llama-3-8b-instruct",
  "csv_download_url": "/api/v1/runs/101/download",
  "followups": ["Which month had the highest spike?", "Show station-wise breakdown"],
  "anomaly_flags": [],
  "sensitive_warning": null,
  "served_from_cache": false,
  "error": null
}
```

## Error Responses

| HTTP | Body shape | Meaning |
|------|-----------|---------|
| 400 | `{"detail": "...", "field": "..."}` | Invalid request, bad schema/column, missing parameter |
| 401 | `{"detail": "Not authenticated"}` | Missing/invalid bearer token |
| 403 | `{"detail": "Forbidden"}` | RBAC rejection |
| 422 | `{"detail": "..."}` | Validation failure |
| 429 | `{"detail": "Rate limited"}` | LLM rate-limit or DB connection-limit |
| 500 | `{"detail": "...", "run_id": 101}` | Agent / graph failure; use `run_id` to retrieve partial state |
