# Capability: Chart Generate

## What It Does
Render a matplotlib-based chart from query results and return it as a base64 PNG (and optionally SVG), surfaced as an inline image in the chat and available via a download URL.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| result columns + rows | JSON | Agent pipeline (`sql_result`) | yes |
| chart_type | str | LLM decides (bar, line, pie, heatmap) | no (defaults to bar) |
| title | str | LLM from question text | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| base64_png | str | Inline in chat response + `/assets/chart_<id>.png` |
| width, height | int | Inline display sizing |
| chart_url | str | Download link |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| matplotlib | Render PNG to `./assets/charts/` | Set `error`, omit chart from response; NL answer + SQL still delivered |

## Business Rules

- Matplotlib uses `Agg` backend only (no GUI).
- Chart size limited to 1200×800; larger datasets are aggregated (binned or top-N).
- Sensitive labels (PII) are anonymized (district codes only, no names) if configured.
- Chart files are garbage-collected after 7 days (configurable).

## Success Criteria

- [ ] Query "monthly trend of FIR 2024" → PNG chart returned alongside NL answer
- [ ] Chart renders correctly in-browser (no CORS error, size ≤ 1 MB)
- [ ] Matplotlib error (e.g., empty data) → agent falls back to text answer with warning, no 500
