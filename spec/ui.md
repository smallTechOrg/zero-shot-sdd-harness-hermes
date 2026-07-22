# UI

> Single-origin web UI at `/app`. No framework; served as static files by FastAPI.

## Screens

### 1. Home / Workspace

- Analyst identity label in header.
- Top actions: new question, connect to MsSQL (stubbed in Phase 1).
- Main panel: chat thread of question → reasoning log → answer package.
- Right panel: dataset list / connection status.

### 2. Upload & Datasets

- Multi-file upload dropzone for CSVs with validation feedback: row count, columns, encoding, parse errors.
- Dataset cards show name, size, row count, and last-refreshed time.
- Remove dataset action with confirmation.

### 3. Ask a Question

- Natural-language input with optional assistant trigger `/` for suggestions.
- Past questions dropdown for quick rerun or refine.
- Render reasoning log as a collapsible streaming timeline:

```
intake → plan → tool use → synthesis → finalize
```

### 4. Answer Package

- Final answer text block.
- Table with sortable columns and copy-to-clipboard.
- Chart placeholder; renders chart when payload is present.
- Follow-up chips: click to rerun question with follow-up appended.
- Anomaly chips: click to open filtered follow-up.
- Download actions: CSV, PDF report stub (PDF deferred to Phase 2+).

### 5. Named Reports

- Saved reports list with name, last-run status, last-run timestamp.
- Report detail view: question, source summary, history/runs list, rerun button.
- Create/edit named report modal.

### 6. Schedules

- Schedule list with cron, enabled state, next-run timestamp.
- Create/edit schedule modal tied to a saved report.
- History of scheduled executions with success/failure indicators.
- **Phase 1:** clearly-labelled NON-FUNCTIONAL stub surfaces for schedule creation and history, with a note that scheduling becomes real in Phase 3.

### 7. Dashboard

- Tile grid summarizing: total runs today, active schedules, latest named report status, DB connection health when connected.
- **Phase 1:** static non-functional tiles labelled “coming soon” where data is not yet wired.
- **Phase 3:** fully functional tiles backed by app DB aggregates.

## Interaction Notes

- Streaming updates are represented as appended log entries; true websocket streaming is deferred to Phase 2 if needed.
- Auth is out of scope for Phase 1; analyst identity is a simple text label stored with each run.
