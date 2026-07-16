# Capability: `nl_to_sql`

## What It Does
Turns a natural-language analyst question into a single read-only `SELECT`
against the `cctns_mirror` schema.

## Inputs

| Input      | Type   | Source                  | Required |
|------------|--------|-------------------------|----------|
| `question` | `str`  | caller (`POST /v1/answer`) | yes      |
| `schema`   | `dict` | runtime introspection of `CctnsMirror.list_tables()` | yes      |

## Outputs

| Output         | Type   | Destination                |
|----------------|--------|----------------------------|
| `sql`          | `str`  | `state["sql"]`             |
| `sql_attempts` | `int`  | `state["sql_attempts"]` (= 1 here) |

## External Calls

| System | Operation         | On Failure                       |
|--------|-------------------|----------------------------------|
| Gemini | one chat completion (`gemini-2.5-flash`) | bubble up ⇒ `handle_error` |

## Business Rules

- The output SQL must reference **only** the `cctns_mirror` schema (no joins,
  no CTEs, no DDL, no DML).
- Schema for the prompt comes from `CctnsMirror.list_tables()` — **never**
  includes row data (data-locality block rule).
- The prompt must use *one* LLM call per invocation; no inner retries here
  (the outer graph has the single retry-once).

## Success Criteria

- [ ] Given a valid question, returns a single `SELECT … FROM cctns_mirror.*`
      string.
- [ ] The LLM payload for the call contains **only schema**, not raw rows
      (prompt-spy test asserts this).
- [ ] Given a malformed protocol response, `state["error"]` is set; the
      node never raises into the graph loop.
