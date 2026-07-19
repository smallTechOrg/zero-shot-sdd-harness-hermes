# Capability: History List (Phase 2)

Read-only list of past questions and answers, newest first. Drives the production "sidebar" surface on the UI; replaces the Phase-1 placeholder.

## What It Does

Loads `answer_runs` rows in newest-first order with offset paging. Returns both the page and a total count so the UI can render "X of Y".

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `limit` | int (1–200, default 50) | `?limit=` query parameter | no |
| `offset` | int (≥ 0, default 0) | `?offset=` query parameter | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `data.limit` | int | response envelope |
| `data.offset` | int | response envelope |
| `data.total` | int | response envelope |
| `data.rows[]` | list[HistoryRow] | UI sidebar |

`HistoryRow` shape: `{id, question, sql, status, row_count, tokens_used, latency_ms, created_at}`.

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite via SQLAlchemy 2.0 | `SELECT ... FROM answer_runs ORDER BY created_at DESC LIMIT ? OFFSET ?` | the endpoint returns 500 + log; sidebar shows empty-state |

## Business Rules

- Reads only `status='completed'` + `'failed'` rows (no `'pending'` — pending is a millisecond window).
- No filters on `status` by default. (Could be added later.)
- Phase-3 will add date-range filters; not Phase 2.

## Success Criteria

- [ ] After 1 `/api/ask` returns 200 (or 502 with a recorded failed row), `GET /api/history?limit=50` returns `total≥1` and includes that row in `rows`.
- [ ] `GET /api/history?limit=5&offset=5` returns `rows=[]` after the first page when there are only N < 5 rows past page 1.
- [ ] Response shape matches `HistoryResponse` exactly (limit/offset/total/rows keys present).
