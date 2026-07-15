# API

All routes return the envelope `{ "data": <payload>, "error": null }` or raise `api_error(code, message, status)`. Base path `/api`. Served by FastAPI at `http://localhost:8001`.

| Method | Path | Purpose | Success |
|--------|------|---------|---------|
| GET | `/health` | liveness | `{ "status": "ok" }` |
| GET | `/api/funnel` | latest 5-stage funnel + sample flag | funnel object |
| GET | `/api/kpis` | KPI tiles (signups, activated, retention_pct, revenue) | kpi object |
| GET | `/api/snapshots` | time-series `FunnelPoint`s (newest last) | list |
| GET | `/api/connectors` | per-source `{ id, name, configured, env_var }` | list |
| GET | `/api/setup_guide?source=<id>` | ordered setup steps for a source | steps list |
| POST | `/api/refresh` | run pipeline, return new funnel | funnel object |

## Funnel response shape

```json
{
  "entity": "#local",
  "sample": true,
  "stages": [
    { "stage": "visit_or_install", "count": 12000 },
    { "stage": "signup", "count": 1800 },
    { "stage": "activated", "count": 940 },
    { "stage": "retained", "count": 610 },
    { "stage": "revenue", "count": 230 }
  ],
  "insight": "Sample insight — set AGENT_OPENROUTER_API_KEY for live narration."
}
```

## Connectors response shape

```json
[
  { "id": "ga4", "name": "Google Analytics 4", "configured": false, "env_var": "GA4_PROPERTY_ID + GA4_CREDENTIALS_JSON" },
  { "id": "business_db", "name": "Business DB", "configured": false, "env_var": "BUSINESS_DB_URL" },
  { "id": "play_store", "name": "Google Play", "configured": false, "env_var": "PLAY_STORE_CREDENTIALS_JSON" },
  { "id": "app_store", "name": "Apple App Store", "configured": false, "env_var": "APPSTORE_CONNECT_KEY_ID" },
  { "id": "instagram", "name": "Instagram", "configured": false, "env_var": "INSTAGRAM_ACCESS_TOKEN" },
  { "id": "linkedin", "name": "LinkedIn", "configured": false, "env_var": "LINKEDIN_ACCESS_TOKEN" },
  { "id": "facebook", "name": "Facebook", "configured": false, "env_var": "FACEBOOK_ACCESS_TOKEN" }
]
```

## Error cases

- `POST /api/refresh` during a real-connector failure → returns last good funnel + `error` describing the failed source (pipeline degrades, never 500s on a single source).
- Unknown `source` in setup_guide → `api_error("unknown_source", ..., 404)`.
