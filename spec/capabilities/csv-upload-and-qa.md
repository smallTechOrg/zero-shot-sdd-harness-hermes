# Capability: CSV Upload and Q&A

## What It Does

Ingest one or more analyst-supplied CSV exports, validate them, shape them into queryable datasets, and answer natural-language analytical questions against the combined data using Pandas-backed execution.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| CSV files | multipart upload | analyst UI or API | yes, at least one |
| Analyst question | text | analyst UI | yes |
| Analyst identity | text | UI session label | yes |
| Filters / date range | JSON / text | analyst UI | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| Natural-language answer | text | API + UI |
| Result table payload | JSON | API + UI |
| Downloadable CSV | file | UI download action |
| Follow-up suggestions | list of text | API + UI |
| Anomaly flags | list of text | API + UI |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Local filesystem | Store uploaded CSVs in a session-scoped artifact folder | Surface upload error and abort |
| Pandas | Read CSVs, validate schema/head, execute filtered/aggregated analysis | Surface data-shape error; never crash |
| LLM | Interprets question into analysis plan and final text answer | Retry with backoff; surface actionable provider error |
| SQLite app DB | Persist run state and metadata | Log error and continue without persistence if non-critical |

## Business Rules

- Files are stored locally; nothing is sent outbound unless the analyst explicitly exports/downloads.
- A run may reference multiple CSV datasets joined or compared as named sources.
- Row counts, columns, and head previews are validated at intake and surfaced in the UI if malformed.
- Each question is logged with analyst identity, timestamp, provider/model, latency, and any SQL used.
- Cache is optional for Pandas-backed analysis; the default path is direct execution against in-memory frames.

## Success Criteria

- [ ] Two CSVs upload successfully and appear in a session dataset list.
- [ ] A natural-language question produces an answer with at least one clearly referenced dataset and one result table.
- [ ] A downloadable CSV export matches the surfaced result table.
- [ ] Follow-up suggestions and at least one anomaly flag appear when underlying data supports it.
- [ ] The reasoning log shows intake → plan → tool use → answer steps.
