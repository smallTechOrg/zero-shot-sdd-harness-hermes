# Capability: ask_question
## What It Does
Converts a natural-language question about police data into a safe SQL query, executes it against the read-only MSSQL database, and returns an answer with the executed SQL, timing, and optional visualizations.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | string | user (chat input) | yes |
| officer_id | string | header or auth (Phase 3) | no (Phase 1: optional for audit) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| answer | string | agent message bubble |
| sql | string | collapsible "View SQL" panel |
| row_count | integer | part of answer text |
| latency_ms | integer | part of answer text |
| chart_spec | dict (optional) | collapsible "View Chart" panel |
| status | string ("success", "clarification_needed", "error") | determines message bubble type |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| MSSQL (read-only) | introspect_schema (tables/columns only) | set error, route to handle_error |
| MSSQL (read-only) | execute_sql (parameterized SELECT) | capture error, set state.error |
| OpenRouter LLM API | planner (question refinement) | retry 2x with backoff, then error |
| OpenRouter LLM API | sql_writer (SQL generation) | retry 2x with backoff, then error |
| OpenRouter LLM API | validator (SQL safety check) | retry 2x with backoff, then error |
| OpenRouter LLM API | answer_writer (natural-language summary) | retry 2x with backoff, then error |
| AuditLog table | insert immutable audit log | log error but do not fail run |

## Business Rules
- The agent must never include raw row data in any LLM prompt (schema-only by default).
- All SQL queries must be read-only (SELECT only) and include a LIMIT or TOP clause.
- The agent must use parameterized queries; never concatenate user input into SQL.
- If the planner determines the question is ambiguous, it must ask for clarification before proceeding.
- Every query must be logged immutably in the audit table for compliance.
- The officer_id (when available) must be included in the audit log for accountability.

## Success Criteria
- [ ] Given a clear natural-language question, the agent returns a correct answer with SQL and timing within 15 seconds p50.
- [ ] Given an ambiguous question, the agent asks for clarification instead of guessing.
- [ ] Given a potentially unsafe question (e.g., attempting INSERT), the agent rejects it with an error.
- [ ] The audit log contains an entry for every query with officer_id, question, SQL, row count, latency, and result hash.
- [ ] Raw data never appears in LLM prompts or logs (verified via observability).