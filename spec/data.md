# Data

This section describes the data the agent works with, the local cache it maintains, and the audit trail it writes. The live production MsSQL schema is outside this repository; this agent is read-only against it.

## Entities

| Entity | Storage | Phase | Notes |
|--------|---------|-------|-------|
| `run` | SQLite (dev) / PostgreSQL (prod) | 1 | One row per user question. Tracks status + provider + model + timing. |
| `run_output` | SQLite / PostgreSQL | 1 | Final answer text, result table JSON, generated SQL. |
| `audit` | PostgreSQL | 1 | Immutable query audit: user, question, sql, tables_touched, row_count, latency_ms, token_usage. |
| `csv_upload` | SQLite (workspace) / PostgreSQL (prod) | 1 | File ref, schema fingerprint, ingest path. |
| `workspace` | PostgreSQL | 2 | Named saved datasets, scratchpads, and saved SQL the user can re-attach. |
| `cache_aggregate` | PostgreSQL | 2 | Materialised aggregates keyed by question + source fingerprint for cache-first fallback. |
| `role` / `user` | PostgreSQL | 3 | Role-based access control: investigator, analyst, supervisor. |

## CSV Workspace

- CSVs are parsed into pandas DataFrames and registered as tables in a working SQLite database for the duration of the session / run.
- Column names are normalised to lower_snake_case; type inference is best-effort.
- Row counts, column types, and a schema fingerprint are stored for duplicate-detection and cache keys.

## Live MsSQL (read-only)

- Accessed via SQLAlchemy + pyodbc or asyncodbc using a connection string from `.env`.
- All queries are scoped to read-only transactions; the agent cannot emit DML/DDL.
- Schema is introspected on first connect and cached locally to minimise live round-trips.

## PostgreSQL Audit + Cache

- Audit table is append-only; rows are never mutated after insert.
- Cache aggregates are refreshed on a defined schedule (default: nightly) or on-demand when a user requests a fresh answer.

## Row Limits & Guards

- Default hard row limit for ad-hoc queries: 100,000 rows.
- Cache fallback is triggered when the live DB query exceeds 30 s or returns a connectivity error.
- Sensitive-category columns (juveniles, women, victim identifiers) are flagged at schema-ingest time and trigger a user confirmation gate before execution.
