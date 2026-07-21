# UI

---

## UI Type

Zero-build static web app (HTML + JS + CSS) served at `/app`. No framework build step; single-page layout with server-side rendering of responses.

## Views / Screens

### Screen: Chat + Upload

**Purpose:** Primary user workspace — upload CSVs, connect MsSQL, ask questions, view answers.

**Key elements:**
- Sidebar: session history, linked datasets, datasource selector
- Main area: chat history (user question + NL answer + code block + result table)
- Top bar: upload button (drag-drop), MsSQL connect button, user/role badge
- Stub badges (Phase 1): Charts, Reports tabs — greyed out with "Coming in Phase 2"

**Actions available:**
- Drag/drop or click to upload CSV
- Type NL question and submit
- View and copy generated SQL/Python code
- Download results as CSV (real in Phase 1; PDF/Excel in Phase 2)
- Clear / start new session

### Screen: Dashboard *(Phase 2 stub + real)*

**Purpose:** Saved queries, historical trends, quick-access charts.

**Key elements (Phase 1 stub, Phase 2 real):**
- Saved query tiles (grey "Coming soon" in Phase 1)
- District heatmap placeholder
- Report library skeleton

---

## Error States

- **No datasets loaded:** Datasource selector shows "Upload a CSV or connect MsSQL to start" — inline, not an error page.
- **LLM endpoint down:** Banner at top: "Answer service temporarily unavailable. Please retry in a moment." — chat still loads; last cached answer shown if available.
- **Query timeout (> 30s):** Spinner stops, message shown with generated SQL + "Query timed out. Try simplifying." — partial result preserved.
- **Upload failure:** Inline toast under the upload area with filename, error reason, and retry button.

## Tech Stack

Zero-build static: vanilla HTML5 + vanilla JS + CSS (no framework build step). Server-rendered partials for chat turns. Chart rendering: matplotlib PNG returned by API, displayed as `<img>`. No client-side data processing (server does all pandas/SQL work).
