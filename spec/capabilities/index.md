# Capabilities — CCTNS Analyst

A capability is one cohesive unit of behaviour. Each `spec/capabilities/*.md`
file describes one capability using the standard template. The list below is
the canonical index — keep it current.

## Capability index

- [Natural language → SQL](./nl_to_sql.md) — LLM drafts a bounded SELECT.
- [Execute bounded query](./execute_bounded_query.md) — Row-cap + timeout.
- [Summarize results](./summarize_results.md) — Prose summary from rows.
- [Answer question](./answer_question.md) — Orchestrator; owns the primary
  user journey end-to-end.

Phase 2 (planned, defined in `spec/roadmap.md`):
- Conversation memory (session-scoped turns).
- Role-based row-level filter.
- History sidebar.

Phase 3 (planned):
- Live CCTNS connector (`MssqlMirror` via pyodbc).
- Token-bucket rate limit.
- Audit log every read.
- Switch-to-live panel wiring.
