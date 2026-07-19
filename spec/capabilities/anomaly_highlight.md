# Capability: Anomaly Highlighting (Phase 2)

Flag rows in a past query whose values across **any** numeric column deviate from the column mean by ≥ `threshold` standard deviations. Drives the red border / "anomaly" badge in the result table.

## What It Does

Pure function — `anomaly_zscore(columns, rows, *, threshold, min_samples)` — called by the `/api/ask/{run_id}/anomalies` endpoint with the persisted rows from `result_rows_json`. Returns the zero-based row indices that are flagged.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `run_id` | UUID string | path parameter | yes |
| `threshold` | float (> 0, default 2.0) | `?threshold=` query parameter | no |
| `columns` | list[str] | loaded from `result_columns_json` | yes |
| `rows` | list[list[Any]] | loaded from `result_rows_json` | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `data.run_id` | string | response envelope |
| `data.threshold` | float | response envelope |
| `data.flagged_rows` | list[int] | UI (per-row red border) |
| `data.flagged_count` | int | UI (count chip) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite | `SELECT ... FROM answer_runs WHERE id = ?` | 404 |

No SQL Server connection — this endpoint reads cached data only.

## Business Rules

- A row is flagged iff **at least one** of its numeric-column values satisfies `|z| ≥ threshold`.
- A column with fewer than `min_samples=4` valid numeric values is not scored.
- A column with `std-dev == 0` (constant) is not scored.
- Non-numeric columns are ignored; their cells do not raise.
- `inf`/`NaN` are filtered out before computing mean/std (a column of infs falls back to "not enough finite samples").
- Sort the flagged indices ascending for a stable UI mapping.
- Phase-3 will replace z-score with median + MAD for outlier-robust scoring; not Phase 2.

## Success Criteria

- [ ] For rows `[[1], [2], [3], [4], [100]]` with threshold=2.0, `flagged_rows == [4]` (only the 100).
- [ ] For a constant column (`[[5], [5], [5], [5], [5]]`), `flagged_rows == []` (no flags).
- [ ] For rows containing non-numeric cells like `[["a"], ["b"], [1], [2], [3], [4]]`, the function does not raise and computes on the 4 numerics.
- [ ] For `threshold=3.0` on a tighter cluster, fewer rows are flagged than `threshold=2.0`.
