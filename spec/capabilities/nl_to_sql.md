# Capability: Translate NL Question → SQL

Transforms a natural-language question into a single bounded `SELECT` against the local MSSQL `master` database.

## What It Does

Calls the configured Gemini model once with the cached MSSQL schema and the user's question. The model is asked to return `{"sql": "..."}`. The safety validator runs immediately; if the SQL is rejected, the request errors out with `unsafe_sql`. The whole flow is one round-trip in Phase 1.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `question` | string | HTTP body of `/api/ask` | yes |
| `schema` | `dict[table, list[{name, type}]]` | `MssqlConnector.describe_schema()` cached at startup | yes (cached) |
| `request_id` | string | per-request middleware | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `sql` | string | agent state → executor / API response |
| `error` | string \| null | agent state when validator rejected |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| `google-genai` `GeminiProvider.complete_json` | generate `{"sql": "..."}` | `{"error": "llm_unavailable: <class>", "status": "failed"}` (graph does not raise) |
| `assert_select_only(sql)` | regex scan | `{"error": "unsafe_sql: …", "status": "failed"}` |

## Business Rules

- Output MUST be a single statement. Multiple statements separated by `;` are rejected.
- Output MUST NOT contain `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, `REVOKE` (case-insensitive).
- Output MUST begin with `SELECT` or `WITH` (whitespace tolerated).
- The LLM is told to prefer `TOP N` (or `SET ROWCOUNT`) to bound result size when the question implies "show me …".
- The LLM is told that only the cached schema's tables are queryable.
- The LLM is told to prefer `INFORMATION_SCHEMA.TABLES` / `INFORMATION_SCHEMA.COLUMNS` for "what tables exist?" questions.

## Success Criteria

- [ ] Given `{"question": "How many tables are in master?"}`, the LLM call returns a parseable `{"sql": "..."}` shape **at least 9/10 times** on identical input (vs. stochastic failure modes).
- [ ] The returned SQL passes `assert_select_only` (no DDL/DML).
- [ ] `tokens_used` is non-zero when the Gemini response exposes usage_metadata; zero (not crash) when it does not.
- [ ] When the LLM tries to emit a `DELETE`, the error returned to the API is `unsafe_sql`, not a 500.
