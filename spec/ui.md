# UI

> Single-page Next.js static export served by FastAPI at `/app/`. Phase 1 = the primary journey is real; everything else is a clearly-labelled stub.

## The page (`/`)

Everything lives on one route, served at `http://localhost:8001/app/`.

### Layout (top → bottom)

1. **Header**
   - Title: "MSSQL Analyst" (top left)
   - Right-side chip: "tokens used so far: NN" (live from `/api/usage`), and "source: live MSSQL" written next to it.

2. **Question form**
   - Label: "Question"
   - Textarea (≥2 rows) bound to a `useState`. Preefilled with a starter prompt like *"How many tables are in master?"*.
   - **Ask** button (submit); disabled while busy.

3. **Loading state** (when busy)
   - Banner: "running against live MSSQL…".

4. **Error state** (when API returned non-null `error`)
   - Banner with the `code: message` and a one-line hint.

5. **Result section** (when happy path)
   - Latency / row-count chip ("1234 ms · 1 row")
   - Markdown-rendered **answer** (Phase 1 uses the raw row; the answer text is the user's question + a deterministic header: e.g. *"Found 74 tables in master."*)
   - **Result table** (rendered from `columns` + `rows`, paginated at 100 if larger)
   - **Show SQL** toggle reveals the generated `SELECT` in a `<pre>` block.

6. **Sidebar (right side, desktop ≥ 1024px / bottom on mobile)**
   - Heading: "Last 50"
   - Phase 1: placeholder text *"available in Phase 2"*.
   - Phase 2: real list pulled from `/api/usage.last_questions`.

7. **Disability / non-functional stubs** (clearly labelled, never mistaken for bugs)
   - "Multi-DB / switch DB — coming in Phase 3" (disabled button)
   - "Charts — coming in Phase 2" (disabled button)
   - "Export CSV — coming in Phase 2" (disabled button)
   - "Follow-up input — coming in Phase 3" (disabled textarea)

## States per surface

| Surface | States |
|---------|--------|
| Ask button | idle / busy |
| Form textarea | empty / non-empty; never disabled |
| Result section | hidden (idle) / loading / error / success |
| Result table | empty (no rows) / 1–N rows / >100 (paginated) |
| Show SQL toggle | collapsed / expanded |
| Tokens badge | (`0…∞`) updated after every successful ask |

## Empty / loading / error / ideal

- **Empty:** on first load, no result section. Form is empty (or pre-filled).
- **Loading:** "running against live MSSQL…" banner only.
- **Error:** red banner with the API `code: message` and a human hint.
- **Ideal:** green chip with latency, answer card, real result table, collapsible SQL.

## Accessibility

- Form has `<label htmlFor="q">`.
- All buttons have visible focus rings (Tailwind defaults).
- Colour contrast meets WCAG AA (Tailwind default palette).
- Result table is wrapped in `<div class="overflow-x-auto">` for narrow viewports.

## Accessibility / a11y — Phase 2 should also cover

- Tab order: header → textarea → Ask → SQL toggle → sidebar (when populated).
- Live region for errors (`role="alert"`).

## What Phase 1 explicitly does NOT do in the UI

- No charts, no sparkline, no follow-up chat.
- No history (just a placeholder).
- No multi-tab layout, no settings, no themes (it respects prefers-color-scheme).
- No login screen.

## Styling

- Next.js 15 + React 19 + Tailwind v4.
- `globals.css` first two lines are `@source "../";` then `@import "tailwindcss";` (per `harness/patterns/tech-stack.md` — non-negotiable).
- Static export served by FastAPI at `/app/`.
- All scripts run with `NODE_OPTIONS=--no-experimental-webstorage` (Node ≥ 25 SSR safety).
