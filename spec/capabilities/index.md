# Capability Index

Phase 1 capabilities:

1. **Translate NL Question → SQL** — see `nl_to_sql.md`.
2. **Execute bounded SELECT on MSSQL** — see `execute_bounded_query.md`.
3. **Audit-Write Each Question** — see `audit_write.md`.

Phase 2/3 capabilities (stubs in Phase 1):

- **Last-50 sidebar list** — wire `answer_runs` paging into the UI (Phase 2).
- **Token/cost charts** — render a daily rollup of tokens_used (Phase 2).
- **CSV export** — let the user download the result table of the most recent question (Phase 2).
- **Anomaly highlighting** — flag rows that deviate from the median by > 2 sigma (Phase 2).
- **NL→SQL retry on validator rejection** — one retry into `nl_to_sql` with the validator's complaint in the prompt context (Phase 3).
- **Multi-turn session memory** — previously-asked question/answer feed into the prompt (Phase 3).
- **Multi-DB connection picker** — switch between registered DBs at runtime (Phase 3).
