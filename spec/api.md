# API — CCTNS Analyst

> Either a REST surface (FastAPI) — single-port single-origin. The Next.js
> static export is served from `/app/` by the same FastAPI process on `:8001`.

## Surfaces

### `POST /v1/answer`
Single primary endpoint.

**Request body** (`application/json`):
```json
{ "question": "How many FIRs in Lucknow in the last 30 days?" }
```

| Field      | Type   | Required | Constraints                       |
|------------|--------|----------|-----------------------------------|
| `question` | `str`  | yes      | length 1..2000, trimmed of whitespace |

**200 response** (`application/json`):
```json
{
  "answer":        "There have been 17 FIRs registered in Lucknow district in the last 30 days.",
  "sql":           "SELECT COUNT(*) AS firs FROM cctns_mirror.fir WHERE district = 'Lucknow' AND …",
  "columns":       ["firs"],
  "rows":          [[17]],
  "latency_ms":    2410,
  "row_count":     1,
  "sql_attempts":  1
}
```

**Error envelope** (validation 4xx / infra 5xx):
```json
{ "error": { "code": "validation_error", "message": "question is required" } }
```

| Status | `code` (examples)              | When                                    |
|--------|--------------------------------|-----------------------------------------|
| 200    | —                              | success                                 |
| 400    | `validation_error`             | question missing / too long             |
| 422    | `empty_question`               | question is whitespace only             |
| 500    | `pipeline_error`               | graph reached `handle_error`            |
| 503    | `mirror_unavailable`           | executor connection failure             |

### `GET /health`
**200 response:**
```json
{ "status": "ok", "mirror_mode": "mock", "version": "0.1.0" }
```

`mirror_mode` is `"live"` when `CCTNS_MIRROR_URL` is set, else `"mock"`.
Always 200 unless the process is unable to import or initialise — in that
case the server simply doesn't bind.

### `GET /app/*`
The Next.js static export under `frontend/out` is mounted at `/app/`. The
single-origin rule from `harness/patterns/tech-stack.md` applies — the user
runs **one** server and opens **`http://localhost:8001/app/`** (with the
trailing slash).

## Authentication

None in Phase 1. Phase 2 introduces role-based row filtering; auth lands
there too (basic header token, then SSO).

## Errors

Errors are surfaced as the JSON envelope and **rendered as an error template
in the UI**, never thrown as a raw `HTTPException` JSON body to the SPA's
fetch layer (see `harness/patterns/code.md` "Pipeline Errors").
