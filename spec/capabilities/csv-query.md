# Capability: CSV Query (upload + NL question + answer)

## What It Does
Accept one or more CSV files via upload, infer their schemas, store them in a local SQLite-backed session, let the user ask natural-language questions, and return a code-transparent NL answer plus result tables — all in one round-trip.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| CSV files | multipart/form-data | User upload via `/upload` | yes (at least one) |
| NL question | str | User input via `/query` | yes |
| session_id | UUID | Client-provided or auto-created | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| NL answer | str | API JSON `answer` field |
| Generated SQL/Python | str | API JSON `code_display` field (shown as code block) |
| Result table | JSON (columns + rows) | API JSON `sql_result` field |
| Run metadata | JSON | API JSON (run_id, latency_ms, evaluate_score, iteration_count, cache_hit) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| On-prem LLM | Generate SQL / Python from question + schema | Retry 3× with backoff; on final failure return 500 with clear error |
| SQLite (pandas/sqlalchemy) | Execute generated SQL or run pandas query | Fatal SQL error → set `error`, route to `handle_error` |
| Audit log DB | Append structured event | Non-fatal (best-effort) |

## Business Rules

- All queries are read-only (SELECT, no DDL/DML).
- If CSV size exceeds 200 MB → return 413 and surface error to user.
- If schema inference fails (e.g., all-null columns) → warn user, propose a manual column-type hint.
- Iterate-until-right: max 3 generate → execute → evaluate loops per query.
- Final answer includes generated SQL/Python above the NL answer for transparency.
- Empty or ambiguous question → clarify shown to user, no silent fallback.

## Success Criteria

- [ ] Upload 3 CSVs (50k rows each) → ask "district-wise total FIR count 2024" → NL answer + SQL + table returned in < 15 s
- [ ] Generated SQL matches the result table when manually executed in the same session
- [ ] Second identical query returns same result with `cache_hit: true` and reduced latency
- [ ] Audit log entry exists for each query with user_id, question, SQL, row_count, latency_ms, status
