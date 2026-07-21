# Capability: Audit Log

## What It Does
Record a structured, immutable audit trail for every query and significant action, capturing who asked what, when, how long it took, what SQL ran, and whether it succeeded — supporting compliance and post-incident review.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| event_type | str | Pipeline (query_start, sql_generated, sql_executed, chart_rendered, etc.) | yes |
| event_data | JSON | Pipeline payload | yes |
| user_id | str | Session / API auth | yes |
| run_id | UUID | QueryRun | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| audit_log_id | UUID | DB row |
| created_at | datetime | DB row |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite (audit DB) | INSERT | Non-fatal; log warning to stderr, continue — no user-facing error |

## Business Rules

- Audit log is append-only; no UPDATE or DELETE permitted.
- Retention: 180 days (configurable). Automatic archive after 30 days.
- Access to audit log restricted to `admin` and `auditor` roles (Phase 2).
- Each audit entry includes: timestamp (UTC), user_id, session_id, run_id, event_type, event_data, datasource_id.

## Success Criteria

- [ ] Every query produces ≥ 4 audit entries (start, sql_generated, sql_executed, finalize)
- [ ] Audit entries immutable via API — `DELETE /audit/<id>` returns 405
- [ ] `GET /audit/runs?user=<id>` returns paginated history scoped to user
