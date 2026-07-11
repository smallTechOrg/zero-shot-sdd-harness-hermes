# Roadmap — AI Music Tutor (Staff Notation Reading)

## What This Agent Does

An AI music tutor that teaches **staff notation reading** (clefs, note names, pitch, rhythm) to self-taught instrumentalists who never learned to read music. A tutor/teacher and student use it together on **one browser screen**. The app drills notation topics one exercise at a time, renders an interactive staff, plays the note's sound via **local synthesis**, speaks explanations via free TTS, and tracks which notation topics the student has mastered in a **private per-student SQLite profile**. Spaced-repetition adapts to the student's weak spots.

## Who Uses It

- **Tutor / teacher** (the operator): starts a drill, hears the spoken answer, sees the LLM's reasoning + token usage, and reviews the student's mastery gaps.
- **Student** (the learner): sees the rendered staff, hears the note, names the note by clicking, gets a hint on a miss, retries, and advances.

Both look at the **same screen** — there is no separate student login in Phase 1. One student profile is active per session.

## Core Problem Being Solved

Self-taught players can perform but cannot read notation. Existing apps quiz with multiple-choice or pre-recorded audio and **trust the model for the "correct" answer** — a wrong note name from an LLM would actively mis-teach. This tutor makes note-name correctness **deterministic** (computed from the rendered pitch), uses the LLM *only* for human explanations/hints/adaptive pacing, and gives immediate **correct sound + spoken feedback** so the learner builds the ear-to-symbol link.

## Success Criteria

- [ ] An exercise's "correct note name" is **computed from the rendered pitch** (MIDI → name), never taken from the LLM. A unit test proves the LLM's guessed name is ignored.
- [ ] A generated exercise renders a real, readable staff (treble, and bass when in scope) with the correct note placement, and the played audio pitch matches the rendered note.
- [ ] A wrong answer returns a computed-correct hint (and a retry path); a correct answer advances with adaptive spacing.
- [ ] The Gemini key is used to generate a **whole drill set's worth of teaching text in ONE call** (no per-note LLM calls), and its reasoning + token usage are surfaced in the UI.
- [ ] The student's per-topic mastery persists in a private SQLite DB and drives the next-topic suggestion.

## What This Agent Does NOT Do (Out of Scope — Phase 1)

- Chords / harmony drills (labelled stub)
- Rhythm tapping / duration drills (labelled stub)
- Chord-progression / sight-reading full pieces (labelled stub)
- Multi-student studio / class management (labelled stub)
- PDF / image export of exercises (labelled stub)
- Animated full-piece playback (labelled stub; the note plays, but not a draw-on animation)

## Key Constraints

- **Correctness is non-negotiable.** Note names are computed, never LLM-guessed.
- **Local synthesis only** for musical audio (free, no API). Speech uses `edge-tts` (free).
- **One LLM call per drill set**, not per note — the user has a monthly spend cap.
- **Privacy:** only per-student notation-mastery state is persisted; nothing else.
- Runs on **one screen**; tutor + student together.

## Phases of Development

### Phase 1 — Note-Naming Drill (first win)

- **Goal:** A tutor starts a "note naming" drill → the app renders a note on a treble (and, when selected, bass) staff, plays its sound, the student names/clicks it → the app **computes** correctness, gives a hint + retry on a miss, advances with adaptive spacing → the next note streams in. Full LLM reasoning + tokens shown.
- **Independent slices (parallel build units):**
  - `slice-backend` (backend `src/`) — FastAPI app, music-theory engine, drill/exercise generation, local audio synth, Gemini hint/explanation client (one call per set), SQLite mastery store. Owns `src/`. Deps: none.
  - `slice-frontend` (frontend `frontend/`) — Next.js static-export UI: interactive staff SVG, click-to-answer, audio playback, SSE stream of upcoming notes, reasoning + token panel, clearly-labelled stubs for later phases. Owns `frontend/`. Deps: none (contract via `spec/api.md`).
- **Key surfaces / files:**
  - backend: `src/main.py`, `src/music/`, `src/drill.py`, `src/synth.py`, `src/llm.py`, `src/speech.py`, `src/db.py`, `src/schemas.py`, `pyproject.toml`, `requirements.txt`
  - frontend: `frontend/app/page.tsx`, `frontend/app/staff.tsx`, `frontend/app/globals.css`, `frontend/next.config.mjs`, `frontend/postcss.config.mjs`, `frontend/package.json`, `frontend/tests/e2e/smoke.spec.ts`
- **Gate command:**
  ```
  .venv/bin/python -m pytest tests/ -q
  ```
  (runs the computed-correctness unit tests + the live Gemini drill-and-check smoke against the real key in `.env`). Frontend gate: `cd frontend && npm run build` (styled CSS) + `npx playwright test tests/e2e/` against the live server.
- **How the user tests it (handoff seed):**
  1. Start backend + frontend (run command in README): `uv run python -m src` serves the built UI at `http://localhost:8001/app/`.
  2. Click **Start drill** → a note appears on the treble staff, its sound plays, and the note-name buttons are shown.
  3. Click the correct note name → green "Correct!" + spoken praise; the next note streams in automatically.
  4. Click a wrong name → a computed-correct hint ("Count up from E — this is G") + a retry; the answer is accepted on the second try.
  5. Open the **Reasoning & tokens** panel → see Gemini's one-call teaching text + token counts.
  6. **Stubs (clearly labelled, non-functional):** Chords, Rhythm tapping, Progressions, Multi-student, PDF export, Animated piece — all show "Phase 2 — coming soon".

### Phase 2 — Adaptive Spacing, Rhythm & Topics (planned)

> Delivers ≥3 capabilities: (1) true spaced-repetition scheduling from mastery state, (2) rhythm/duration naming drill, (3) proactive next-topic suggestion UI + per-topic progress dashboard. Wires the labelled stubs above into real features. *Not built in this handoff.*
