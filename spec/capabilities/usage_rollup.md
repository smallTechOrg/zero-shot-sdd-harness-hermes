# Capability: Daily Token Rollup (Phase 2)

Per-UTC-day aggregate of `tokens_used` across `answer_runs`. Drives the "tokens-per-day sparkline" at the top of the sidebar.

## What It Does

Reads the precomputed `day` column on `answer_runs` and groups tokens by day. Returns descending-sorted buckets for the last N days.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `days` | int (1–90, default 14) | `?days=` query parameter | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `data.days[]` | list[UsageDayBucket] | UI sparkline |

`UsageDayBucket` shape: `{day: "YYYY-MM-DD", tokens: int, questions: int}`.

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite via SQLAlchemy 2.0 | `SELECT day, tokens_used FROM answer_runs` then group in Python | 500 |

## Business Rules

- `day` is the UTC day the row was created (computed and written at insert time — see `ask.py`).
- "1970-01-01" rows (default column value, never inserted into in practice but possible on hard reset) are excluded from the response.
- Sort: descending by day (newest first).
- Limit: take only the first N (= `days` value) distinct days after sort.
- Tokens are summed across all rows for each day, regardless of `status` (a successful + a failed ask on the same day both contribute tokens).

## Success Criteria

- [ ] After seeding N `answer_runs` rows across 3 distinct days, `GET /api/usage/by-day?days=14` returns descending-sorted buckets matching the seeded data.
- [ ] `?days=7` returns at most 7 buckets.
- [ ] Out-of-range `?days=0` (or negative) is clamped to 1; `?days=999` is clamped to 90.
