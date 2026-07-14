# UI — Data Analyst Agent

Single page (React + Vite).

## Layout
- **Header:** title + running daily token total (polls `/api/audit?date=today`).
- **Question box:** text input + "Ask" button. One question at a time (disabled
  while streaming).
- **Reasoning panel (collapsible):** shows the full reasoning chain as it streams
  via SSE, with a "Step N of M" counter. Collapsed by default after completion.
- **Plan + SQL:** the plan text and generated SQL shown (SQL read-only, mono).
- **Clarification prompt:** if the API returns a clarification, render it as a
  prompt asking the user to refine; no chart is drawn.
- **Chart canvas:** Chart.js (react-chartjs-2) renders bar/line/pie per
  `chartType`.

## Behaviour
- On Ask → open SSE to `/api/query/stream`, append steps live, then draw chart.
- Errors (deny-list / LLM not configured) render inline, non-fatal.

## Stubs (labelled NON-FUNCTIONAL for later phases)
- "History" tab — disabled, tooltip "Coming in Phase 2".
- "Export CSV" button — disabled, tooltip "Coming in Phase 3".
