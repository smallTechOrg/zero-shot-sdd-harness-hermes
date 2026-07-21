# UI

> **Assumed:** `frontend/public/` static bundle served by FastAPI. Phase 1 is a single upload/Q&A screen with clearly-labelled non-functional stubs for MsSQL, saved workspaces, charts, and audit export.
> **Assumed:** no JS bundler or framework in Phase 1.

## Screens

### `#app` — Primary workspace

- **Upload pane:** drag-and-drop / file picker for one or more CSVs; shows file name, row count, and schema after ingest.
- **Source selector:** toggle between Uploaded CSV and Live DB. Live DB is a clearly-labelled **stub** in Phase 1 that returns a "coming in Phase 2" notice.
- **Ask bar:** text input + Ask button.
- **Progress signal:** step counter + timer during the query (planned → generated SQL → executed → assembling answer).
- **Answer panel:**
  - Narrative answer text.
  - Result table (sortable columns).
  - Metadata bar: tables touched, row count, latency, provider, model.
  - Generated SQL block with copy button.
  - Follow-up suggestions + anomaly flags + sensitive-category warning when applicable.
- **Action bar:**
  - Download CSV of the result set.
  - Save workspace (stub in Phase 1 — labelled "coming in Phase 2").

### Stubs in Phase 1 (clearly labelled, visually styled as disabled)

- **Charts panel:** shows "Charts – Phase 2" placeholder.
- **Saved workspaces list:** shows "Saved workspaces – Phase 2" placeholder.
- **Supervisor audit export:** shows "Supervisor export – Phase 3" placeholder.
- **Role switcher:** shows "Role-based access – Phase 3" placeholder.

## Frontend rules

- All text is plain English with police-domain examples preloaded as placeholder hints.
- Errors are shown inline, never as raw JSON or stack traces.
- The generated SQL block is aware that the user may need to audit or forward it; make it easy to copy.
