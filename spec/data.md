# Data Model

Entities (SQLAlchemy tables in `src/analytics_agent/db/models.py`):

## SourceRecord (raw pull audit trail)

| Field | Type | Notes |
|-------|------|-------|
| `id` | str (PK, uuid) | |
| `entity` | str | `#local` |
| `source` | str | `ga4`, `business_db`, `play_store`, `app_store`, `instagram`, `linkedin`, `facebook`, `sample` |
| `stage` | str | one of the 5 funnel stages |
| `count` | int | normalized count for that stage |
| `captured_at` | timestamp | when pulled |

## Snapshot (cached aggregate)

| Field | Type | Notes |
|-------|------|-------|
| `id` | str (PK, uuid) | |
| `entity` | str | |
| `sample` | bool | True when sample adapter produced it |
| `visit_or_install` | int | |
| `signup` | int | |
| `activated` | int | |
| `retained` | int | |
| `revenue` | float | |
| `insight` | str \| None | LLM or sample summary |
| `created_at` | timestamp | |

## FunnelPoint (time-series)

| Field | Type | Notes |
|-------|------|-------|
| `id` | str (PK, uuid) | |
| `entity` | str | |
| `sample` | bool | |
| `signup` | int | |
| `activated` | int | |
| `retained` | int | |
| `revenue` | float | |
| `created_at` | timestamp | |

## Relationships / lifecycle

- Every `run_pipeline()` writes N `SourceRecord`s (audit), one `Snapshot` (latest cache), one `FunnelPoint` (trend).
- `GET /api/funnel` returns the most recent `Snapshot`; `GET /api/snapshots` returns `FunnelPoint`s ordered by time.
- No deletes in Phase 1 (history is permanent; prune is a later concern).
