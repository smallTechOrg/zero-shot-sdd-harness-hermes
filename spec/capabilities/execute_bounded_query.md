# Capability: Execute bounded SELECT on MSSQL

Run a single, already-validated `SELECT` against MSSQL through `pyodbc`, return rows bounded to `row_cap`.

## What It Does

Opens (or reuses) a `pyodbc` connection to the configured MSSQL instance using Windows Integrated Auth (Trusted_Connection). Sets a query timeout. Executes the SQL. Caps the returned rows to `row_cap` server-side.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `sql` | string (single SELECT, validator-passed) | `nl_to_sql` node | yes |
| `row_cap` | int (default 1000; env `AGENT_MSSQL_ROW_CAP`) | settings | yes |
| `timeout_sec` | int (default 15; env `AGENT_MSSQL_QUERY_TIMEOUT_SEC`) | settings | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `columns` | list[str] | API response |
| `rows` | list[tuple] | API response |
| `row_count` | int (raw count, pre-cap) | API response + audit |
| `latency_ms` | int (exec-only, excludes LLM) | API response + audit |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| `pyodbc.connect(...)` | open MSSQL session with `Trusted_Connection=yes;` and `AGENT_MSSQL_DRIVER={...}` | `{"error": "mssql_unavailable: <class>", "status": "failed"}` |
| `cursor.execute(sql)` with `query_timeout` | run SELECT | `{"error": "mssql_unavailable: <class>", "status": "failed"}` |
| `cursor.fetchall()` | bounded read | `{"error": "mssql_unavailable: <class>", "status": "failed"}` |

## Business Rules

- Read-only: every connection has `autocommit=False` and is closed in a `with`; no `INSERT/UPDATE/DELETE/DDL` reach the cursor (validator gates upstream).
- Schema introspection (`INFORMATION_SCHEMA.TABLES/COLUMNS`) happens **once at startup**, then is cached as a Python dict. Per-request calls only ask Gemini, not the schema.
- `row_count` returned to the user is the count *before* server-side capping (so the caller knows truncation happened). The `rows` list itself is capped at `row_cap`.

## Success Criteria

- [ ] `SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES` against local `master` with Integrated Auth returns `(n,)` where n ≥ 1, in <5s.
- [ ] A `SELECT *` against an arbitrarily-populated table returns at most `row_cap=1000` rows even if the SQL did not contain `TOP`.
- [ ] A `pyodbc.OperationalError` (DB down) bubbles up as `mssql_unavailable`, not as a 500 with a stack trace.
- [ ] The schema cache is populated on first `/api/ask` and is exactly reused on subsequent calls (verified by an integration test that monkey-patches the schema introspection and asserts it is hit only once per process lifetime).
