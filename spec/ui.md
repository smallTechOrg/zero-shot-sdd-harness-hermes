# UI

## Design Principles

- Zero-build, single-origin — no npm, no bundler. Served by the backend at `/app` on **port 8001**.
- Enterprise-grade visual polish by default — clear typography, consistent spacing, no hackathon framing. Clean table layouts, well-labelled stubs for future surfaces.
- Progressive rendering: the answer panel fills in as the agent progresses (plan block → generated code block → KPIs → table → chart).

---

## Screens

### Upload / Home (`/app/`)
- Header: "UP Police Data Analyst" with the UPP logo area (text badge in a bounded colour block).
- Two-column layout:
  - **Left sidebar**: session picker (new / open / close), loaded files list with row counts, cache status badge, clear all.
  - **Main panel**: drag-and-drop upload zone (dashed border, accepts `.csv`; max size warning).
- Stubs:
  - "Connect to Live Database" button → opens a labelled stub: "MsSQL tab — coming in Phase 2".
  - "Account" / "Login" tab → labelled stub: "Auth — coming in Phase 3".
- Backdrop: clean off-white + UPP-inspired navy accent; no gradients.

### Ask Question (`/app/` — same page)
- Question textarea (placeholder: "Ask a question about your data — e.g. top 10 PS by total FIRs last month").
- Submit button; disabled if no session is active.
- Streaming lifecycle indicator: text-only three-state label ("Planning…", "Running query…", "Explaining result…") replacing a spinner.

### Answer Panel (slots, rendered in order)

| Slot | Content | Notes |
|------|---------|-------|
| **Dashboard KPIs** | 3–6 counters (total rows, date range, distinct X, trend ↑/↓) | Flat row of glass-morphism cards |
| **Plan block** | Collapsible. Heading: "Plan". Body: plan_text | Collapsed by default; expand button |
| **Generated code block** | Collapsible. `generated_code` with language label + copy button + source badge (`DuckDB` / `MsSQL` / `MsSQL Cache`) | Collapsed by default |
| **Data table** | Sortable, paginated (50 rows/page), char-truncated cells with hover tooltip showing full value | Debounced column sorting |
| **Chart area** | Auto-suggested single chart (bar / line / pie) with title + legend | Responsive; no Plotly; SVG rendered client-side or from server-provided spec |
| **Audit chain footer** | `row_count`, `latency_ms`, `result_hash` (shortened), `created_at` | Sans-serif, small; matte |

### Session History (sidebar)
- List of prior questions in this session; clicking loads the prior answer (from the `runs` table).
- Disabled / labelled stub in Phase 1: "Persistent history — coming in Phase 3".

### Error State
- If the run fails or clarifies: prominent red-bordered card with the `error_message` (and `clarify_prompt` when applicable). Retry button re-issues the same question. Generated code (partial or full) is preserved in the code block so the user can debug.

---

## Interactions

- Keyboard shortcut: `Cmd/Ctrl + Enter` in the question textarea submits.
- After each completed run, the question textarea keeps the last question pre-filled (one backspace to edit).
- CSV drop highlights the sidebar's "loaded files" list; progress shown during upload (single-file numerator; aggregation shown once) because DuckDB writes are fast.

---

## Responsive

- Below 768 px: sidebar collapses into a top slide-out drawer.
- Table stacks to a card list on mobile; chart area goes full-width.
- The app is internal-network-only; no mobile optimisation beyond the reflow above unless requested.

---

## What is Stubbed in Phase 1

Each stub carries the label **"Coming in Phase N"** — never "Coming soon" or "TBD". Stubs at `/app/`:

- **"Connect to Live Database" tab** → Phase 2. Creates a disabled form with the label "MsSQL connection — Phase 2".
- **"Account / Settings" tab** → Phase 3. Login button, disabled, labelled "Auth — Phase 3".
- **"Download CSV / Excel" button** → Phase 2+ (or beyond). Disabled, greyed out, labelled "Export — coming soon".

A stub must never look like a bug.
