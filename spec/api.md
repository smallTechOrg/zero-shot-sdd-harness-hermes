# API

---

## API Style

REST (JSON). Served from the FastAPI backend. Static frontend is at `/app` (zero-build HTML/JS).

## Endpoints / Commands

### `POST /upload`

**Purpose:** Upload one or more CSVs for a new or existing session.

**Request (multipart/form-data):**
```json
{
  "session_id": "UUID | omit to create new",
  "files": [
    {
      "filename": "fir_2024.csv",
      "content_type": "text/csv"
    }
  ]
}
```

**Response (201):**
```json
{
  "session_id": "UUID",
  "datasets": [
    {
      "id": "UUID",
      "name": "fir_2024.csv",
      "source_type": "csv",
      "schema": { "columns": [...], "row_count": 50000, "sample_rows": [...] },
      "created_at": "..."
    }
  ]
}
```

**Error cases:**

| Status | Condition |
|--------|-----------|
| 413 | File too large (> 200 MB) |
| 422 | Unparseable CSV (encoding, empty) |

---

### `POST /datasource/connect`

**Purpose:** Connect to a MsSQL datasource *(Phase 2)*.

**Request:**
```json
{
  "session_id": "UUID",
  "name": "UP Police Crime DB",
  "host": "mssql.internal",
  "database": "CrimeDB",
  "username": "analyst_ro",
  "password": "REDACTED",
  "port": 1433
}
```

**Response (200):**
```json
{
  "datasource_id": "UUID",
  "name": "UP Police Crime DB",
  "schema": { "tables": [{"name": "FIR", "columns": [...]}, ...] }
}
```

**Error cases:**

| Status | Condition |
|--------|-----------|
| 401 | Auth failed (wrong credentials) |
| 503 | MsSQL unreachable |

---

### `POST /query`

**Purpose:** Ask a natural-language question against the active datasource(s).

**Request:**
```json
{
  "session_id": "UUID",
  "question": "Top 5 districts by total FIR count in 2024",
  "datasource_id": "UUID | omit for auto-detect"
}
```

**Response (200):**
```json
{
  "run_id": "UUID",
  "answer": "In 2024, district X recorded the highest FIR count...",
  "code_display": "SELECT ... FROM ... WHERE ...",
  "sql_result": {
    "columns": ["district", "fir_count"],
    "rows": [["Aligarh", 3421], ...],
    "row_count": 5
  },
  "evaluate_score": 0.95,
  "iteration_count": 1,
  "latency_ms": 3200,
  "cache_hit": false,
  "chart_urls": ["/assets/chart_abc.png"],
  "download_urls": [{"format": "pdf", "url": "/assets/report_xyz.pdf"}],
  "status": "success"
}
```

**Error cases:**

| Status | Condition |
|--------|-----------|
| 400 | Empty question or invalid session ID |
| 422 | No datasource available for this session |
| 500 | Agent pipeline failed (retried 3×); `error_message` in body |
| 503 | LLM endpoint unreachable |

---

### `GET /datasets`

**Purpose:** List datasets linked to a session.

**Params:** `session_id: UUID`

**Response (200):**
```json
{ "datasets": [ { "id": "...", "name": "...", "source_type": "csv" | "mssql", ... } ] }
```

---

### `GET /runs`

**Purpose:** List query runs for a session (audit / history).

**Params:** `session_id: UUID`, `limit: int = 20, offset: int = 0`

**Response (200):**
```json
{
  "runs": [
    {
      "run_id": "...",
      "question": "...",
      "status": "success",
      "latency_ms": 3200,
      "cache_hit": false,
      "completed_at": "..."
    }
  ]
}
```

---

### `GET /health`

**Purpose:** Liveness + readiness check.

**Response (200):**
```json
{ "status": "ok", "llm_endpoint": "connected", "db": "ok" }
```

---

## Authentication

**Phase 1:** IP allowlist or shared internal auth token (configurable via `API_TOKEN` in `.env`).  
**Phase 2:** Role-based login. Roles: `analyst` (full access), `viewer` (read-only, no execute), `admin` (all + user management). Token via `Authorization: Bearer <token>` header.
