# Capability: `execute_bounded_query`

## What It Does
Runs a single read-only `SELECT` on the mirror under strict caps.

## Inputs

| Input   | Type   | Source                | Required |
|---------|--------|-----------------------|----------|
| `sql`   | `str`  | `state["sql"]`        | yes      |

## Outputs

| Output      | Type             | Destination          |
|-------------|------------------|----------------------|
| `columns`   | `list[str]`      | `state["columns"]`   |
| `rows`      | `list[tuple]`    | `state["rows"]`      |
| `row_count` | `int`            | `state["row_count"]` |

## External Calls

| System               | Operation       | On Failure                                |
|----------------------|-----------------|-------------------------------------------|
| `CctnsMirror.execute(sql, row_cap, statement_timeout_ms)` | one SQL run | bubble up ⇒ `handle_error` |

## Business Rules

- `row_cap = 1000`, `statement_timeout = 10 s`, hard-coded defaults
  overridable via env (`APP_ROW_CAP`, `APP_STATEMENT_TIMEOUT_MS`).
- Result is **trimmed** to `row_cap` rows server-side; the LLM never sees
  more.
- One statement per request. Multiple statements forbidden.

## Success Criteria

- [ ] A query that returns 5,000 rows gets trimmed to 1,000.
- [ ] A query that exceeds the statement timeout raises ⇒ `state["error"]`
      set by the dispatcher; the graph does not crash.
- [ ] Resulting `columns` length matches the number of projected fields in
      `sql`.
