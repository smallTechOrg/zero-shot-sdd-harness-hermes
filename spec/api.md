# API

## API Style
REST

## Endpoints / Commands
### `POST /api/ask`
**Purpose:** Accept a natural-language question from an officer, run it through the agent pipeline, and return the answer with optional SQL and chart.

**Request:**
```json
{
  "question": "string",
  "officer_id": "string (optional, from header in Phase 3)"
}
```

**Response:**
```json
{
  "answer": "string (natural-language response)",
  "sql": "string (the executed SQL, for transparency)",
  "execution_time_ms": "integer",
  "row_count": "integer",
  "chart_spec": "object (optional Vega-Lite specification)",
  "status": "string: "success" | "clarification_needed" | "error"
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | Missing or invalid `question` in request body. |
| 401 | Missing or invalid `officer_id` (when required by phase). |
| 429 | Agent rate-limited (upstream LLM or DB); retry after delay. |
| 500 | Internal agent error (see `answer` field for message). |
### `POST /api/pin`
**Purpose:** Save a question and its result as a pinned report for quick reuse.

**Request:**
```json
```json
{
  "question": "string",
  "officer_id": "string"
 1": "{
    "answer": "string": "integer",
    "string: "string thetime_ms":  integer",
  "row_count": "integer",
  "created_at": "ISO timestamp"
}'
  }
}
```

**Response:**
```json
{
  "id": "string (uuid)",
  "message": "Report pinned successfully"
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | Missing required fields. |
| 401 | Invalid or missing officer_id. |
| 500 | Database error while saving. |
### `GET /api/reports`
**Purpose:** List recent and pinned reports for an officer.

**Request:** None (officer_id from header or query)

**Response:**
```json
{
  "recent": [
    {
      "id": "string",
      "question": "string",
      "answer": "string",
      "created_at": "ISO timestamp"
    }
  ],
  "pinned": [
    {
      "id": "string",
      "question": "string",
      "answer": "string",
      "pinned_at": "ISO timestamp"
    }
  ]
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 401 | Invalid or missing officer_id. |
| 500 | Database error while fetching. |
### `GET /api/health`
**Purpose:** Simple health check; returns 200 if the service is up and can reach the DB and LLM API (without validating keys).

**Response:**
```json
{
  "status": "ok",
  "timestamp": "ISO timestamp",
  "services": {
    "database": "reachable" | "unreachable",
    "llm_api": "reachable" | "unreachable"
  }
}
```
## Authentication
In Phase 1, the officer_id is accepted as an optional header (`X-Officer-Id`) or query parameter for audit logging; no real authentication is performed. In Phase 3, this will be replaced with proper JWT validation against an identity provider.