# UI — Auto-Podcaster

## UI Type

Web app (Next.js, App Router). Single page.

## Views / Screens

### Screen: Generate (home)

**Purpose:** The one working path. The user types a topic, picks 2–3 hosts, and generates a live
podcast.

**Key elements:**
- Topic text input (one line, placeholder "e.g. future of remote work").
- Cast picker: a list of 2–3 fixed host personas, each a selectable card showing name + voice +
  one-line persona. User selects 2 or 3. (Phase 1 supports 2 hosts as the primary path; 3 is
  accepted by the API but the picker highlights the 2-host default.)
- "Generate" button (disabled until a topic is entered and ≥2 hosts selected).
- Live `<audio>` player that plays the SSE audio stream as it arrives.
- Download link, revealed only when the `done` event arrives.
- Status text: idle / generating / done / error.

**Actions available:**
- Type topic.
- Toggle host cards (2–3).
- Click Generate → POST generate, then open SSE stream and feed the `<audio>` element.
- Click download when available.

> **Phase 1 stub (clearly labelled, non-functional):** a "Transcript" panel placeholder below the
> player reading *"Transcript — coming in Phase 2"*. It is explicitly a stub, never mistaken for a
> bug. Everything else on this screen is real.

## Error States

- Empty topic or <2 hosts selected → Generate button disabled (UI validation, no request sent).
- Generation error (SSE `error` event) → status shows the message, player stops.
- Backend down → Generate click surfaces a network error toast/message.

Every state has an explicit idle / loading(generating) / done / error representation.

## Tech Stack

Next.js 15 (App Router) + React 19 + TypeScript. No CSS framework required for Phase 1 (inline
styles / minimal CSS). SSE consumed via `fetch` + `ReadableStream` reader (EventSource only supports
GET; our generate is a POST, then we GET the stream by id). Audio played by appending received mp3
chunks to a `Blob` + `URL.createObjectURL` fed to `<audio>`.

> **Assumed:** frontend dev server on `http://localhost:3000`, backend on `http://localhost:8001`.
> CORS allows the frontend origin.
