# Capability: `answer_question`

## What It Does
Owns the primary user journey end-to-end: a single natural-language question
in, JSON answer out.

## Inputs

| Input      | Type   | Source                  | Required |
|------------|--------|-------------------------|----------|
| `question` | `str`  | `POST /v1/answer` body  | yes      |

## Outputs

| Output          | Type   | Destination       |
|-----------------|--------|-------------------|
| `answer`        | `str`  | JSON response     |
| `sql`           | `str`  | JSON response     |
| `columns`       | `list[str]` | JSON response |
| `rows`          | `list[tuple]` (`≤ ~100` rendered; the bounded full set in payload) | JSON response |
| `latency_ms`    | `int`  | JSON response              |
| `row_count`     | `int`  | JSON response              |
| `sql_attempts`  | `int`  | JSON response              |

## External Calls

Composes `nl_to_sql`, `execute_bounded_query`, and `summarize_results` via
LangGraph (see `spec/agent.md`).

## Business Rules

- One question maps to one bounded run; status is recorded in `AnswerRun`.
- Errors surface as `{error: {code, message}}` envelope with a 4xx (validation)
  or 5xx (infra) status — never a raw stack trace; the UI renders an error
  template, never an `HTTPException` JSON body.

## Success Criteria

- [ ] `POST /v1/answer` returns 200 with a valid JSON body when given a
      well-formed question that matches some row in the mirror.
- [ ] `GET /health` returns `{status:"ok", mirror_mode:"mock"|"live"}`.
- [ ] On query failure (timeout / SQL error), the response is the error
      envelope, status 5xx; the persisted `AnswerRun.status = "failed"`.
- [ ] End-to-end latency p50 ≤ 6 s against the mock mirror (real Gemini key).
