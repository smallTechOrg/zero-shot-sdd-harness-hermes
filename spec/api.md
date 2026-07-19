# API

> Single FastAPI service at `http://localhost:8001/`. All endpoints return `{"data": ..., "error": null}` or `{"data": null, "error": {"code": "...", "message": "..."}}`. Errors use HTTP status codes that match `code`.

---

## `GET /health`
Liveness probe.
- **Request:** none.
- **Response 200:**
  ```json
  {"data": {"status": "ok", "mssql_mode": "live", "version": "0.1.0"}, "error": null}
  ```

## `POST /api/ask`
Primary endpoint. Run one question through the graph and return the result.
- **Request body:**
  ```json
  { "question": "how many tables are in master?" }
  ```
  Constraints: `question: string, 1 ≤ len ≤ 2000`.
- **Response 200:**
  ```json
  {
    "data": {
      "sql": "SELECT COUNT(*) AS table_count FROM INFORMATION_SCHEMA.TABLES",
      "columns": ["table_count"],
      "rows": [[74]],
      "row_count": 1,
      "sql_attempts": 1,
      "latency_ms": 1234,
      "tokens_used": 578,
      "status": "completed"
    },
    "error": null
  }
  ```
- **Response — error envelope (HTTP 4xx/5xx):**
  ```json
  {"data": null, "error": {"code": "unsafe_sql", "message": "DDL/DML keywords are forbidden in mirror queries"}}
  ```
  Codes used in Phase 1:
  - `400 empty_question` (question was empty/whitespace-only post-strip)
  - `400 unsafe_sql` (validator rejected the SQL the LLM produced)
  - `422 validation_error` (FastAPI body validation, e.g. `question` missing)
  - `500 pipeline_error` (graph raised an exception that was not captured)
  - `502 llm_unavailable` (Gemini errored; raw message bubbles up)
  - `502 mssql_unavailable` (pyodbc OperationalError / ProgrammingError)
  - `503 no_db_configured` (the agent ran but no MSSQL connection params are present in `.env`)

## `GET /api/usage`
Returns the running per-totals from the audit log.
- **Request:** none.
- **Response 200:**
  ```json
  {
    "data": {
      "total_questions": 4,
      "total_tokens": 1842,
      "total_rows_returned": 18,
      "last_questions": [
        {
          "id": "…uuid…",
          "question": "how many tables are in master?",
          "sql": "SELECT COUNT(*) AS table_count FROM INFORMATION_SCHEMA.TABLES",
          "status": "completed",
          "row_count": 1,
          "tokens_used": 578,
          "latency_ms": 1234,
          "created_at": "2026-07-17T15:33:11Z"
        }
        /* up to 5 most-recent, newest first */
      ]
    },
    "error": null
  }
  ```
- In Phase 1 the *sidebar* uses this; Phase 2 adds full pagination.

## `GET /`
Root banner; for smoke and human discovery.
- **Response 200:**
  ```json
  {
    "service": "mssql_analyst",
    "version": "0.1.0",
    "ui": "/app/",
    "api": "/api/ask",
    "health": "/health"
  }
  ```

## `GET /app/<static>` *(handled by FastAPI's StaticFiles mount)*
- Serves `frontend/out/` (the Next.js static-export build) at the single-origin path `http://localhost:8001/app/`. The frontend uses `basePath: "/app"` and `output: "export"`. The router serves `index.html` for SPA routes.

## Error model summary

| HTTP status | code                    | when |
|-------------|-------------------------|------|
| 200         | (none)                  | happy path |
| 400         | `empty_question`        | `question` is whitespace only after stripping |
| 400         | `unsafe_sql`            | validator rejected the SQL |
| 422         | `validation_error`      | Pydantic body validation (FastAPI default) |
| 500         | `pipeline_error`        | graph raised unhandled |
| 502         | `llm_unavailable`       | Gemini errored |
| 502         | `mssql_unavailable`     | pyodbc OperationalError/ProgrammingError |
| 503         | `no_db_configured`      | MSSQL_* env vars missing |
