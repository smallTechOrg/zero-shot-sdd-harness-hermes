# Capability: CSV Export (Phase 2)

Stream the result of a past question as `text/csv`. The data is sourced from the `answer_runs.result_columns_json` + `answer_runs.result_rows_json` columns populated at `/api/ask` time, so the export works even with the database disconnected (no fresh MSSQL round-trip).

## What It Does

Reads `result_columns_json` and `result_rows_json`, calls the pure `to_csv` helper, returns the bytes with `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="mssql-<run_id>.csv"`.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `run_id` | UUID string | path parameter | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| CSV body | text/csv | browser download |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite via SQLAlchemy 2.0 | `SELECT result_columns_json, result_rows_json, status FROM answer_runs WHERE id = ?` | 404 if no run; 404 if run.status != "completed" |

## Business Rules

- Only `status='completed'` runs are exportable. `pending`/`failed` runs return 404 with code `ask_not_completed`.
- The CSV uses CRLF line terminators and RFC 4180 quoting (commas, quotes, CR, LF inside a cell trigger double-quote wrapping).
- Numbers are emitted as their natural repr; `None` is emitted as an empty cell; bool is `true`/`false`.
- Phase-3 will add a search-by-question-glob endpoint to bulk-export; not Phase 2.

## Success Criteria

- [ ] After a successful `/api/ask`, `GET /api/ask/{run_id}/csv` returns 200 with `Content-Type: text/csv` and a body that starts with the column header row.
- [ ] A comma inside a value triggers the value to be wrapped in double quotes; an embedded `";` is escaped to `""`.
- [ ] `GET /api/ask/00000000-0000-0000-0000-000000000000/csv` returns 404 with `code: ask_not_found`.
- [ ] `GET /api/ask/{run_id}/csv` on a `failed` row returns 404 with `code: ask_not_completed`.
