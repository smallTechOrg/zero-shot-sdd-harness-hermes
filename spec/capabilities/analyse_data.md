# Capability: Analyse Structured Police Data

## What It Does

Answers a single natural-language question over structured police data — either from uploaded CSV exports or the live read-only MsSQL source — and returns an auditable result set with the generated SQL, row counts, and a CSV download. It is the Phase 1 core loop for the UP Police Data Analyst agent.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `question` | string | User | yes |
| `data_source` | enum: `csv` \| `live_db` \| `cache` | User | yes |
| `csv_file_ids` | list[int] | Upload store | when `data_source == csv` |
| `workspace_id` | int \| null | Saved workspace | no |
| `row_limit` | int | User / policy | no |
| `schema_summary` | string | Auto-generated | no (ingested if missing) |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| Answer text | string | API response + UI |
| Result table | `{columns: list[str], rows: list[dict]}` | API response + UI |
| Generated SQL | string | API response + UI audit view |
| CSV download | binary | `/api/v1/runs/{run_id}/download` |
| Audit row | row | PostgreSQL audit table |
| Follow-ups / anomaly flags / sensitive warning | objects | API response + UI |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| NVIDIA NIM | One LLM call for plan / SQL / answer synthesis | Surface structured error; offer cache/offline fallback if applicable |
| SQLite workspace | Read-only query over ingested CSV tables | Endpoint returns 400 with missing-schema message |
| MsSQL | Read-only live query | Route to cache fallback when unavailable; show "served from cache" indicator |
| PostgreSQL cache | Precomputed aggregate lookup | Continue to live or admit answer unavailability with retry guidance |

## Business Rules

- All executed SQL must be read-only; DDL/DML is rejected before execution.
- A missing or ambiguous column is surfaced to the user; the agent never guesses silently.
- Sensitive case categories (juveniles, women, victim identifiers) trigger a confirmation gate before execution.
- Row-limit policy is enforced at execution, not just in generated code.
- Audit rows are written before the response is returned, never in a background fire-and-forget path.

## Success Criteria

- [ ] API smoke uploads a CSV and returns a question answer in under 2 s for a 5 000-row table.
- [ ] Generated SQL is present in the response and matches the returned row count.
- [ ] CSV download contains the exact rows shown in the result table.
- [ ] When MsSQL is disconnected, the same question on cached data returns within 3 s with `served_from_cache: true`.
- [ ] A malformed question (missing table/column) returns a 400-style structured error, not a 500.
