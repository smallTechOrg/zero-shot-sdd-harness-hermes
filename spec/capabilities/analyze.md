# Capability: Analyze Multi-CSV Data

## What It Does
Given 1–many CSV files and a natural-language question, returns a narrative insight grounded in the combined data plus a structured chart spec describing the best visualization for the main findings, in one LLM call.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `files[]` | `multipart/form-data` | Frontend file upload | yes |
| `instruction` | string | Frontend form | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `output_text` | string | `RunRow.output_text`, frontend Result block |
| `provider` | string | `RunRow.provider` |
| `model` | string | `RunRow.model` |

## External Calls

| System | Operation | On Failure |
|--------|-----------|-----------|
| LLM provider | `complete()` once | Terminate run as failed with actionable message |

## Business Rules
- Exactly one provider key from `.env`; missing or invalid key fails the run with a clear message.
- Phase 1 input gate: reject more than 10 files or total serialized footprint over ~5MB; surface `400 validation_error`.
- Phase 1 stores structural schema summaries plus representative rows; raw file bytes are not persisted.
- When multiple CSVs share column names, the node infers join keys and reports the assumption explicitly; if no join is feasible, it answers per-file separately.

## Success Criteria
- [ ] Success path completes in < 20s p95 for datasets up to 500k rows combined on default OpenRouter model.
- [ ] Output includes concrete values from the data (totals, counts, time ranges) and at least one chart spec.
- [ ] Failed runs surface `status=failed` with the error message visible in-run.

## Extension — Phase 2 MsSQL Federation

> Assumed: federation uses normalized question text + deterministic parameters as the query fingerprint; cache entries are SQLite-backed aggregates; TTL is configurable; live SQL access is read-only.

- Known query patterns with cache present return prior aggregates with `cache_hit=true`.
- Unknown patterns execute against MsSQL and store the result for future repeats.
- Cache latency is targeted under 1s; live query latency under 5s.
