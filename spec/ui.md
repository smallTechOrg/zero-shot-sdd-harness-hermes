# UI

## UI Type
Web app (Next.js 15 static export, served by the backend at `/app/`). Single screen for tutor + student.

## Views / Screens

### Screen: Drill (primary, REAL in Phase 1)

**Purpose:** Run a note-naming drill, one note at a time, with sound, feedback, and reasoning.

**Key elements:**
- **Staff panel** — interactive SVG staff (treble, and bass toggle). The current note is drawn; clicking the staff is not required (answer buttons are the input), but the note is highlighted on play.
- **Play button** — fetches `/audio` and plays the note.
- **Answer buttons** — the note-name options (e.g. E4 F4 G4 A4 B4). Clicking submits the answer.
- **Feedback banner** — green "Correct!" / amber "Not quite — hint: …" with a Retry button on a miss.
- **Reasoning & tokens panel** — Gemini's teaching text + token counts (prompt/completion/total) + model. Collapsible.
- **Next button / auto-advance** — after a correct answer (or a revealed answer), the next note streams in.
- **Progress / mastery chips** — small per-topic mastery indicators (real, read from `/mastery`).

**Actions available:**
- Start drill (clef selector: treble / bass)
- Play note audio
- Submit answer (click name)
- Retry after a miss
- Reveal answer (after a miss, shows computed name + speaks it)
- Hear spoken hint/answer (edge-tts)
- Jump to next note

## Error States
- **Loading** — spinner / disabled buttons while an exercise generates.
- **Audio unavailable** — if `/audio` or `/speak` fails, show a text fallback (the note name / hint text) instead of a broken player.
- **LLM unavailable** — if Gemini key is missing, the reasoning panel shows "Teaching text unavailable (offline)" and exercises still work (deterministic fallback).
- **Empty** — before a drill starts, a friendly "Start a drill" empty state.

## Labelled Stubs (Phase 1 — clearly non-functional)
These appear as disabled cards / "Phase 2 — coming soon" so they are never mistaken for bugs:
- **Chords** drill
- **Rhythm tapping** drill
- **Progressions / sight-reading**
- **Multi-student studio**
- **PDF / image export**
- **Animated full-piece playback**

## Tech Stack
Next.js 15 + React 19 + Tailwind CSS v4 (static export, `basePath: '/app'`, served at `http://localhost:8001/app/`).
