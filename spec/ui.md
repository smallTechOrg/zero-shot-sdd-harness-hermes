# UI — CCTNS Analyst

> Web dashboard. Single page served at `/app/` by FastAPI.

## Frames

### Primary page — `frontend/src/app/page.tsx`

A single screen with three regions:

| Region           | Contents                                                        |
|------------------|-----------------------------------------------------------------|
| **Header**       | Brand mark · "CCTNS Analyst" · mirror-mode badge (`mock`/`live`)|
| **Composer**     | Question `<textarea>` + **Ask** button + (stub) “Follow-up” input panel with `Phase 3` placeholder label |
| **Results**      | Loading skeleton · prose **answer** headline · latency badge · results table (`≤ 100` rows shown) · **Show SQL** toggle reveals the SQL |
| **Sidebar (stub)**| "Conversation history — **Coming in Phase 2**"                       |
| **Switch panel (stub)** | "Switch to live CCTNS — **Coming in Phase 3**"               |
| **Role panel (stub)**   | "Multi-user / role filter — **Coming in Phase 2**"            |

### Error template — `frontend/src/app/error.tsx`

A readable error page that does **not** show a stack trace; says what failed,
why (in plain English) and offers a link back to `/app/`.

## States (per `harness/patterns/ui-ux.md`)

| State      | What renders                                                |
|------------|-------------------------------------------------------------|
| Empty      | Guidance copy: “Ask a question about CCTNS data.”            |
| Loading    | Skeleton with step-counter badge (“Step 2 of 4 …”).         |
| Error      | `error.tsx` template with a one-line reason + Retry button. |
| Ideal      | Answer headline + table + SQL toggle + latency badge.       |

## Stubs (NEVER mistaken for bugs)

Each stub is a **clearly-labelled** static element:

- *"Follow-up input — coming in Phase 3"* (greyed-out textarea)
- *"Conversation history — coming in Phase 2"* (sidebar heading only)
- *"Switch to live CCTNS — coming in Phase 3"* (toggle labelled disabled)
- *"Multi-user / role filter — coming in Phase 2"* (selector labelled disabled)

In every stub: `aria-disabled="true"` and a `data-stub="phase-N"` attribute so
qa-auditor can detect an unlabelled-or-broken-looking stub.

## Tech specifics (per `harness/patterns/tech-stack.md`)

- Next.js 15 + React 19 + Tailwind v4 static export (`output: 'export'`,
  `basePath: '/app'`).
- `postcss.config.mjs` uses `@tailwindcss/postcss` plugin (NON-OPTIONAL).
- `globals.css` first two lines: `@source "../";` then `@import "tailwindcss";`
  (NON-OPTIONAL).
- All `dev` / `build` / `start` scripts carry
  `NODE_OPTIONS=--no-experimental-webstorage` (Node-25 SSR safety).

## Code font — markdown rendering

LLM text outputs are rendered through `react-markdown` + `remark-gfm`. Raw
strings in the answer would render `**bold**` / bullet syntax literally — a
broken-looking UI. The system prompt requests formatted output (newlines,
indentation) for any returned code blocks.
