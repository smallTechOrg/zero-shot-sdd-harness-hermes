# Capability: `summarize_results`

## What It Does
Turns the bounded result rows + the original question into a short prose
answer (≤ 6 sentences).

## Inputs

| Input        | Type            | Source             | Required |
|--------------|-----------------|--------------------|----------|
| `question`   | `str`           | `state["question"]`| yes      |
| `columns`    | `list[str]`     | `state["columns"]` | yes      |
| `rows`       | `list[tuple]`   | `state["rows"]`    | yes      |
| `row_count`  | `int`           | `state["row_count"]` | yes    |

## Outputs

| Output    | Type   | Destination          |
|-----------|--------|----------------------|
| `answer`  | `str`  | `state["answer"]`    |

## External Calls

| System | Operation         | On Failure                       |
|--------|-------------------|----------------------------------|
| Gemini | one chat completion (`gemini-2.5-flash`) | bubble up ⇒ `handle_error` |

## Business Rules

- Answer is ≤ 6 sentences; one LLM call; no inner retries.
- The summary should mention the row count and a numeric head if the data
  is numeric.
- No raw row bodies enter the LLM payload — schema + ≤ 100 sample rows +
  aggregates only (data-locality block rule).

## Success Criteria

- [ ] Returns a non-empty string of ≤ ~ 600 chars for a small bounded
      result.
- [ ] The LLM payload contains no raw rows; only schema, sample (≤ 100),
      or aggregates.
- [ ] Empty result ⇒ the answer contains "no rows" or equivalent.
