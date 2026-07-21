# Data Model

> How data is stored and what it represents.

## Storage Technology

SQLite via SQLAlchemy 2.0 in Phase 1. Uses `alembic.ini` for schema evolution; baseline also supports `init_db()` auto-creation. PostgreSQL is the production target for any shared/multi-user deployment.

## Entities

### Entity: `RunRow` (`runs`)

One agent execution record with inputs, outputs, and execution metadata.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `TEXT` | yes | UUID primary key |
| `status` | `TEXT` | yes | `pending` / `running` / `completed` / `failed` |
| `input_text` | `TEXT` | yes | User's raw CSV/JSON or text payload |
| `instruction` | `TEXT` | yes | User's natural-language question |
| `output_text` | `TEXT` | no | LLM-generated insight summary |
| `provider` | `TEXT` | no | Active LLM provider |
| `model` | `TEXT` | no | Active LLM model |
| `error_message` | `TEXT` | no | Failure reason when `status=failed` |
| `created_at` | `TIMESTAMP` | yes | UTC creation time |
| `updated_at` | `TIMESTAMP` | yes | UTC last-updated time |

### Relationships

- `RunRow` is the only persisted entity in Phase 1.
- `RunRow.id` is referenced by the API endpoint `GET /runs/{run_id}`.
- Future phases may add a `RunArtifact` or `FileRecord` to hold uploaded files and derived chart metadata.

## Data Lifecycle

- **Create:** API `POST /runs` creates a `RunRow` with `status=running`.
- **Update:** `run_agent()` updates the row with final status/output/provider/model/error when the graph completes.
- **Read:** API `GET /runs/{run_id}` returns the latest state.
- **Delete:** Not exposed in Phase 1; expected in a later settings/admin surface.

## Sensitive Data

> **Assumed:** Phase 1 treats user-supplied input as transient; `input_text` is stored as text for debugging and history but is not encrypted at rest. No PII classification is applied in Phase 1. If user data is sensitive, they must use a self-hosted deployment with encrypted storage.
