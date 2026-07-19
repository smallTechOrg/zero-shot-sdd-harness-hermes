# Capability Index

Phase 1 capabilities:

1. **Translate NL Question → SQL** — see `nl_to_sql.md`.
2. **Execute bounded SELECT on MSSQL** — see `execute_bounded_query.md`.
3. **Audit-Write Each Question** — see `audit_write.md`.

Phase 2 capabilities (replacing the Phase-1 stubs):

4. **History List** — see `history_list.md` (sidebar list, newest-first + paging).
5. **Daily Token Rollup** — see `usage_rollup.md` (sparkline + per-day buckets).
6. **CSV Export** — see `csv_export.md` (download a result table as `.csv`).
7. **Anomaly Highlighting** — see `anomaly_highlight.md` (z-score flags rows on the result table).

Phase 3/4 capabilities (stubs in Phase 2):

- **Multi-DB switcher** — stays a Phase-3 stub (UI button visible but disabled).
- **Follow-up chat** — stays a Phase-3 stub.
- **NL→SQL retry on validator rejection** — Phase 3.
- **Multi-turn session memory** — Phase 3.
- **Outlier-robust scoring (median + MAD)** — Phase 3 replacement for z-score.
- **Bulk export of matching questions** — Phase 4.
