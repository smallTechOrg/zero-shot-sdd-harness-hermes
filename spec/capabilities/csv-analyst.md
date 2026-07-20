# Capability: CSV Analyst

## What It Does

Accepts multiple CSV file uploads into a single session, builds a per-session DuckDB analytical database backed by the uploaded files, and answers natural-language questions over the combined dataset with a multi-step plan→query→execute→explain graph.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `input_text` | str | User query via API/UI | ✓ |
| `csv_files` | multipart/form-data (list[UploadFile]) | POST /api/v1/sessions/{id}/csv | ✓ |
| `session_id` | UUID | Client-supplied or server-assigned | ✓ |
| `conversation_history` | list[{role,content}] | Session state (in-memory + persisted via API for reload) | — |

## Outputs

| Output | Type | Destination |
|--------|------|------------|
| `run_id` | UUID | API response |
| `status` | enum(pending, running, completed, failed, clarifying) | DB row |
| `output_text` | JSON blob: `{nl_answer, chart_spec, kpis, audit_block}` | DB row + API response |
| `plan_text` | str | API response (inner field of output_text) |
| `generated_code` | str | API response (inner field of output_text) |
| `rows` | list[dict] (truncated to MAX_ROWS_IN_RESPONSE) | API response (inner field) |
| `row_count` | int | API response (inner field) |
| `latency_ms` | float | API response (inner field) |
| `result_hash` | str (sha256) | query_log row + API response |
| `clarify_prompt` | str \| None | API response (when status=clarifying) |
| `error_message` | str \| None | DB row + API response (when failed) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| OpenRouter API | `POST /chat/completions` (one call per node: plan, query, explain) | Retry once with exponential backoff (configured in `src/llm/client.py`); surface as `clarify_prompt` if ambiguous, fall back to `error_message` |
| DuckDB (local) | `.execute()` for schema inspection + target query | Log + fail run; surface failed SQL to user |
| Filesystem (local) | Write session db file (`.duckdb_session_{session_id}`) | Fail session creation with 500 |

## Business Rules

- A session **must** have at least one CSV uploaded before a run is accepted — API returns 422 with a helpful message otherwise.
- A single run uses **exactly one** generated query (see `src/prompts/query.md` for the single-target rule). Multi-step "drill-down" is achieved by re-prompting with follow-up natural-language questions, not by an implicit multi-query chain in one run.
- Maximum uploaded CSV size: `MAX_CSV_BYTES` env var (default 100 MB). Maximum concurrent open sessions: `MAX_SESSIONS` env var (default 50); older idle sessions are evicted LRU.
- The conversation history is capped: last `MAX_HISTORY_TURNS` (default 20 turns = 40 messages) are sent to the LLM; older turns are summarised into a `prior_summary` field from the same context. Truncation is silent (no user-visible warning; raises only if the LLM call fails on over-length).
- `result_hash` is computed over the JSON-serialized result rows with sorted keys and deterministic null formatting; repeated runs on the same cached query for the same question produce the same `result_hash` (idempotency signal).
- Rate limiting per API key / session per `RATE_LIMIT_RUNS_PER_MINUTE` env var (default 20 runs/min/session).

## Success Criteria

- [ ] Upload 3+ CSV files and receive a coherent joint schema summary in under 5 seconds.
- [ ] Ask a question; receive plan, single generated query, row count, latency, a ranked sortable table, and an auto-suggested bar/line/pie chart all within 10 seconds on local data.
- [ ] Follow-up question context-aware within session; stale-session refresh path works (session re-loaded from disk continues history).
- [ ] DB/schema ambiguity surfaces a `clarify_prompt` rather than a silent failure.
- [ ] `query_log` row is present for every run; `generated_code`, `row_count`, `latency_ms`, `result_hash` are all populated on success.
- [ ] Integration tests pass with a real LLM key and a real pg/duckdb fixture; pytest gate asserts response content not merely status code.
