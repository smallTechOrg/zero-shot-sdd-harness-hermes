# Capability: Named Reports and Schedules

## What It Does

Persist a named analytical report template or scheduled investigative query, keep its history, allow rerun on demand, and surface dashboard tiles summarizing scheduled and saved report state.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| Report name / label | text | analyst UI | yes |
| Question / prompt template | text | analyst UI | yes |
| Source config | CSV dataset IDs or MsSQL connection label | UI state | yes |
| Schedule cron / interval | text | UI scheduler form | no |
| Analyst identity | text | UI session | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| Named report ID | text | API + UI |
| Schedule ID / next-run timestamp | JSON | API + UI |
| Run history | list of run metadata | API + UI dashboard |
| Dashboard tile payload | JSON | UI dashboard grid |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLite app DB | Persist/report/update report and schedule records | Surface persistence error; do not lose analyst input |
| Agent runner | Re-execute saved questions against their source | Surface rerun error and preserve prior successful result |
| LLM | Regenerate answer when rerun is requested | Retry with backoff; fall back to prior cached answer if unchanged source |

## Business Rules

- A saved report may reference multiple CSV datasets or a live DB connection at save time; if datasets are removed later, reruns must fail with a clear missing-dataset error.
- Scheduled runs execute in-process against persisted schedule records; failed runs are retained in history with error metadata.
- Dashboard tiles reflect counts, last-run status, and last-run timestamp; no sensitive query text is embedded in tiles by default unless the UI explicitly opts in.
- Analyst identity is stored with every saved report, schedule, and rerun for audit transparency.

## Success Criteria

- [ ] An analyst can save a question as a named report and retrieve it by name from the reports list.
- [ ] Rerunning a saved report produces a new run record and preserves prior history.
- [ ] A schedule executes unattended and its result appears in history with timing metadata.
- [ ] Dashboard tiles show summary counts and last-run status for reports and schedules.
- [ ] Missing or removed datasets surface a clear actionable error on rerun.
