# Data Model

## Storage Technology

- **DuckDB** — embedded analytical database, one `.duckdb` file per dataset session.
  Chosen for: zero-config, SQL-compatible, fast aggregates on CSV-backed data, in-process with FastAPI.
- **MsSQL (via pyodbc)** — read-replica only, accessed through a connection pool.
  Used for authoritative real-time lookups when the analyst toggles source to "live".
- **SQLite (existing)** — run-logging via SQLAlchemy (unchanged from baseline).

## Entities

### RunRow (existing — shape extended)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT | yes | UUID primary key |
| status | TEXT | yes | pending / running / completed / failed |
| input_text | TEXT | yes | User question |
| instruction | TEXT | yes | Alias for input_text |
| output_text | TEXT | no | JSON `{answer, sql, chart, source, latency_ms}` |
| provider | TEXT | no | LLM provider used |
| model | TEXT | no | LLM model used |
| error_message | TEXT | no | Error detail if failed |
| created_at | TIMESTAMP | yes | Insertion time |
| updated_at | TIMESTAMP | yes | Last update |

### DatasetSession (new — optional in Phase 1 via add-on table)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT | yes | UUID primary key |
| name | TEXT | yes | Human label (e.g. "Q1 2025 FIR data") |
| tables | JSON/TEXT | yes | JSON list of `{name, row_count, columns}` |
| created_at | TIMESTAMP | yes | Ingestion time |
| updated_at | TIMESTAMP | yes | Last refresh |
| source | TEXT | yes | `upload` or `mssql` |
| duckdb_path | TEXT | yes | Path to the `.duckdb` file |

## Data Lifecycle

1. **Create:** CSVs uploaded via `POST /api/v1/ingest` → DuckDB file created + session row.
2. **Update:** Re-ingest with same session ID replaces/refreshes DuckDB tables.
3. **Refresh:** "Refresh from DB" → DuckDB mirrors live MsSQL schema + sample.
4. **Delete:** Session delete → DuckDB file removed + session row purged.
5. **Audit:** Every question appends a `RunRow` preserving `input_text` + `output_text` JSON.

## Sensitive Data

- Row data stays on-prem; LLM receives only column schema + question text, never row values.
- MsSQL password lives in `AGENT_MSSQL_CONNECTION_STRING` env var — never logged.
- Run log is local SQLite only; no external transit.
