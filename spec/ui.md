# UI — `scaffold-agent`

> Phase 1 is minimal but visually complete.

---

## UI Type

Web chat interface. Served as a Vite dev server in local dev; built assets served by FastAPI in production.

## Views / Screens

### Screen: Chat

**Purpose:** The user types a message and sees the agent reply.

**Key elements**
- Header with project title (placeholder literal "scaffold-agent chat" until capability slot is filled).
- Message area with user and assistant bubbles.
- Input row with Send button.

**Actions available**
- User inputs text and presses Enter or clicks Send.
- Server returns a reply.
- User sees assistant message appended immediately.

### Screen: Stubs (Phase 1)

**Purpose:** Show where future screens go.
**Key elements**
- Settings panel: labelled `TODO — LLM key, agent slot`
- History panel: labelled `TODO — run history`

**Actions available**
- None persistent; purely placeholder.

## Error States

- Loading: simple inline text "Thinking…" while awaiting `/api/chat`.
- Error: inline red banner under input when the request fails (500 / CORS / network).
- Empty input: input blur validation, inline hint.

## Tech Stack

- React 18 + TypeScript
- Vite 6
- Tailwind CSS 3 via CDN or PostCSS (prefer CDN in generated template for zero-config css).
- No shadcn/ui in Phase 1; keep dependencies minimal.
