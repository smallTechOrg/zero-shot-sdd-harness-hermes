# Capability: MsSQL Connect

## What It Does
Allow the user to connect the agent session to a live MsSQL database (read-only) via ODBC, introspect the schema, and use it as the active datasource for NL queries — replacing or augmenting the uploaded CSV datasets.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| MsSQL connection config | JSON (host, db, user, password, port) | User via `/datasource/connect` | yes |
| session_id | UUID | Client | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| datasource_id | UUID | API JSON |
| schema | JSON (tables, columns, types) | API JSON — shown in sidebar |
| connect status | str | API JSON |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| MsSQL via pyodbc | `SELECT` from `INFORMATION_SCHEMA` | 503 to user; MsSQL tab disabled |
| Audit log | Record connection attempt | Non-fatal |

## Business Rules

- Connection uses a read-only DB account; write operations are blocked at the DB level.
- Connection string stored encrypted at rest ( Fernet key from `.env`).
- Datasource can be set as active per session; only one active at a time.
- On MsSQL, all agent-generated queries include `WITH (NOLOCK)` hint.
- If MsSQL is unreachable, the session falls back to any previously linked CSV datasets with a warning banner.

## Success Criteria

- [ ] Connect to a test MsSQL instance → schema appears in sidebar without page reload
- [ ] Query against MsSQL ("Top 5 districts") → correct result returned in ≤ 5 s (p95)
- [ ] Query cache hit on repeated identical question → latency < 1 s
- [ ] Second attempt after temporary MsSQL outage → clear error shown, session continues with CSV fallback
