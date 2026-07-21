# API

> REST contract for the agent runtime. Baseline endpoints are preserved; the request body for `POST /runs` becomes the dataset+question carrier in Phase 1.

## API Style

REST + JSON. FastAPI auto-generates OpenAPI docs at `/docs`.

## Endpoints / Commands

### `GET /health`

**Purpose:** Verify server and LLM configuration. Never shows secrets.

**Request:** none

**Response:**
```json
{
  "status": "ok",
  "provider": "openrouter",
  "model": "tencent/hy3",
  "key_configured": true
}
```

### `POST /runs`

**Purpose:** Execute one agent run. Past datastructures become the `input_text`; user question becomes `instruction`.

**Request:**
```json
{
  "text": "month,revenue,cost\nJan,120,80\nFeb,150,90\nMar,170,95",
  "instruction": "What's the profit trend and what chart shows it best?"
}
```

**Validation (Phase 1):**
- `text` is non-empty.
- `instruction` is non-empty.
- Serialized payload does not exceed the input size gate (Phase 1).

**Response (200, success):**
```json
{
  "data": {
    "run_id": "...",
    "status": "completed",
    "output_text": "Profit increased from 40 in Jan to 75 in Mar... Best chart: line chart with month on x and profit on y.",
    "provider": "openrouter",
    "model": "tencent/hy3"
  },
  "error": null
}
```

**Response (200, failure run):**
```json
{
  "data": {
    "run_id": "...",
    "status": "failed",
    "output_text": null,
    "provider": null,
    "model": null,
    "error_message": "No LLM API key configured..."
  },
  "error": null
}
```

### `GET /runs/{run_id}`

**Purpose:** Retrieve a completed or failed run by its id.

**Response (200):**
```json
{
  "data": {
    "run_id": "...",
    "status": "completed",
    "output_text": "...",
    "provider": "openrouter",
    "model": "tencent/hy3"
  },
  "error": null
}
```

**Error cases:**

| Status | Condition |
|--------|-----------|
| `400` | Missing or invalid request body on `POST /runs`. |
| `404` | `run_id` not found on `GET /runs/{run_id}`. |
| `500` | Invariant: run row missing after creation. |

## Authentication

None in Phase 1. In later phases, if multi-user access is needed, API key or OAuth should be added and surfaced through configuration.
