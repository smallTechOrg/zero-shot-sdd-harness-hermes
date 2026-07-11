# zero-shot-build — Hermes runtime pitfalls (condensed)

Condensed from real `/zero-shot-build` runs (auto-podcaster agent). Durable lessons only — not the app changelog. Mirror of the "Hermes runtime notes" section in SKILL.md, with the fix recipes.

## Pitfalls → fixes

### 1. Background delegation returns before finishing
- **Symptom:** a `delegate_task` sub-agent hits a fixable bug and ends its turn at ~95% — no commit, no push, no PR.
- **Fix:** the parent finishes. Read the *actual* files (don't trust the summary), fix the bug, run the REAL test suite (live keys), then commit/push/PR. Make "commit + push + open PR" a hard gate in the agent-builder role, not an optional last step.

### 2. `max_spawn_depth=1` blocks nested fan-out
- **Symptom:** the orchestrator can't spawn code-generator / qa-auditor children, so the build never proceeds.
- **Fix:** run inline. agent-builder reads `harness/agents/*.md` as procedure references and does the work itself. Don't wait for workers that will never spawn.

### 3. `clarify` empty answer
- **Symptom:** the user submits the prompt with no selection.
- **Fix:** treat as "you decide" → pick the lowest-risk default, label it `Assumed:` in the brief. Don't re-ask or block.

### 4. Handoff run-steps don't match the scaffold
- **Symptom:** Stage 3 says `uv run python -m src` / `uv run alembic`, but the scaffold uses a venv + a different entrypoint; `python -m src` with an empty `src/__init__.py` starts *nothing*.
- **Fix:** before writing the handoff, actually boot the server and hit `/health`. Add `src/__main__.py` so `python -m src` works:
  ```python
  import argparse, os, uvicorn
  if __name__ == "__main__":
      p = argparse.ArgumentParser()
      p.add_argument("--host", default=os.environ.get("AUTO_PODCASTER_HOST", "0.0.0.0"))
      p.add_argument("--port", type=int, default=int(os.environ.get("AUTO_PODCASTER_PORT", "8001")))
      a = p.parse_args()
      uvicorn.run("src.main:app", host=a.host, port=a.port)
  ```
  Then write the *verified* commands into the handoff.

### 5. Cheap re-verify (don't re-burn the live API on every commit)
  ```bash
  .venv/bin/python -m py_compile src/graph/dialogue.py src/graph/tts.py tests/test_generate.py
  .venv/bin/python -m pytest tests/ --collect-only -q   # proves imports resolve, no ModuleNotFoundError
  ```
  Reserve the full live-API run for the first green and after logic changes.

## Reusable fix patterns (Python / FastAPI)

- **Package import rule:** a module *inside* a subpackage (e.g. `src/graph/dialogue.py`) must import a sibling of the package (`src/config`, `src/prompts`) via `..config` / `..prompts`, **not** `.config`. A file wrongly named `__init__.py` becomes the package root and breaks relative imports — rename it to a real module name (`dialogue.py`).
- **starlette `TestClient` streaming:** use `with client.stream("GET", url) as s:` then `s.iter_raw()`; `client.get(url, stream=True)` is wrong (raises `TypeError`).
- **Name→id mapping:** when parsing LLM output of the form `Name: text`, map the spoken name back to the *entity id* (not the display name) before any lookup, or you get `KeyError` on the id lookup.
- **Deprecated SDKs:** `google.generativeai` is deprecated (warns, still works). Migrate to `google.genai` as tech-debt cleanup in a later phase — not a Phase-1 blocker.
- **Venv hygiene:** when a background terminal launches a server, pin the interpreter explicitly (`.venv/bin/python -m uvicorn ...`). A shared agent venv may have a broken/incomplete package set and silently shadow `.venv`, causing `ModuleNotFoundError` red herrings.

## User-flow corrections (HIGH VALUE — from the user directly)

### 6. SHIP-FIRST PREFERENCE WAS REVERSED — do NOT encode it
- **What happened:** during one run the agent (mis)read an early user remark ("the Claude Code
  harness used to ask too many questions") as a durable preference and rewrote the harness to cap
  intake at 1–2 rounds + "ship-first, ask-after." At session end the user **explicitly reversed** it:
  *"Scrap PR #4 entirely and re-port the original harness files verbatim (true 1:1 emulation), adding
  ONLY the Hermes tool mapping"* and *"it should be as close to that harness as possible."*
- **Correction (bake this in so it doesn't recur):** this Hermes port's job is to **mirror the original
  `zero-shot-sdd-harness` as closely as possible**. Apply ONLY the mechanical tool mapping
  (AskUserQuestion→`clarify`, Agent→`delegate_task`, pnpm→npm, uv run→`.venv/bin/python`,
  `.claude/`→`harness/`). Do NOT invent process preferences or slash the original's behavior (e.g. the
  original's `minimum 5` product intake rounds stay `minimum 5`). A single off-hand comment is NOT a
  durable preference — confirm before rewriting the harness's core process. When in doubt, match the
  original file in `harness/` exactly.
- **What stays valid (not reversed):** the *gate/reporting* style correction — at the human testing
  gate, ASK via one `clarify` question, don't dump a prose wall (see §12). That is a separate,
  still-active preference about communication, not about intake depth.

### 7. Frontend tooling mismatch (run-steps)
- **Symptom:** Stage 3 handoff said `pnpm build` / `pnpm dev`, but the user's machine had **npm, not
  pnpm** → frontend wouldn't start.
- **Fix:** when the scaffold uses Next.js, prefer `npm install` + `npm run dev` unless the project
  explicitly pins pnpm (check `package-lock.json` vs `pnpm-lock.yaml` presence, or just use `npm`).
  Verify the dev server actually serves (curl `:3000` → 200) before writing the URL into the handoff.

### 8. Streaming audio freezes after the FIRST chunk (SSE → `<audio>`)
- **Symptom:** backend streams a full, correct podcast (hundreds of `event: audio` chunks, real mp3),
  but the browser only plays ~3 seconds then stops. Root cause: the `<audio>.src` was set **once**
  from a blob built from only the first chunk; later chunks never update it.
- **Fix (React/Next pattern):** keep an array of `Uint8Array` chunks in a ref; on each SSE `audio`
  event, push the chunk and bump a `chunkCount` state. A `useEffect([chunkCount])` rebuilds the blob
  from ALL chunks, sets `audioRef.current.src = URL.createObjectURL(blob)`, and calls `.play()`.
  Revoke the old object URL in the effect cleanup. Do NOT build the blob once and stop.
  ```tsx
  const [chunkCount, setChunkCount] = useState(0);
  // in SSE loop, on "audio": chunksRef.current.push(base64ToBytes(data)); setChunkCount(c => c+1);
  useEffect(() => {
    if (!chunksRef.current.length || !audioRef.current) return;
    const url = URL.createObjectURL(new Blob(chunksRef.current, { type: "audio/mpeg" }));
    audioRef.current.src = url;
    audioRef.current.play().catch(() => {});
    return () => URL.revokeObjectURL(url);
  }, [chunkCount]);
  ```
- **Why it matters:** this is a generic pitfall for ANY app that streams audio over SSE/WebSocket to
  a browser `<audio>` element. The data path can be 100% correct server-side and still look "broken"
  to the user. Always verify the *played duration*, not just that bytes were delivered.

### 9. Dual-venv red herring (pin the interpreter in background terminals)
- **Symptom:** `uvicorn` launched via a background terminal failed with `ModuleNotFoundError:
  No module named 'pydantic_core._pydantic_core'` / `google.generativeai`, even though `pytest` had
  just passed. Cause: the shared **Hermes agent venv** (`~/.hermes/hermes-agent/venv`) is on `PATH`
  in that shell and has a broken/incomplete package set; it shadowed the project's `.venv`. `pytest`
  had silently used `.venv`; the background server did not.
- **Fix:** always invoke servers with the explicit project interpreter — `cd repo && .venv/bin/python
  -m uvicorn src.main:app ...` (or `.venv/bin/python -m src`). Never rely on a bare `uvicorn` /
  `python` resolving to the right env in a background terminal. After starting, confirm with a real
  `curl /health` — a port may be bound by a *different* venv's process from an earlier launch, so a
  stale "startup complete" log line is NOT proof the server you intended is the one listening.
- **Cheap stream probe:** `references/verify_stream_probe.sh` drives generate→stream→download and
  asserts event count + mp3 size. Use it (not just `/health`) to confirm the pipeline is whole.

### 10. Player RESETS on every chunk (the regression after §8)
- **Symptom:** after the §8 fix (rebuild blob per `chunkCount`), audio plays but *restarts from the
  beginning on every chunk* — sounds like it keeps "resetting". Root cause: the effect called
  `.play()` on every chunk, and rebuilding `src` from scratch reseeks to 0 each time. A plain blob
  can't append to a playing element.
- **Fix (true progressive playback):** use **MediaSource Extensions**. Chrome MSE does NOT support
  `audio/mpeg` (raw mp3) — it supports `audio/webm;codecs=opus`. Transcode each utterance server-side
  (ffmpeg `mp3 -> webm/opus`, one standalone WebM segment per turn) and append via a `SourceBuffer`
  in `sequence` mode. The browser then plays seamlessly as buffers arrive. Fallback when MSE is
  unavailable: build the whole blob once at `done` and play it (smooth, but not live).
  ```ts
  const ms = new MediaSource();
  audio.src = URL.createObjectURL(ms);
  ms.addEventListener("sourceopen", () => {
    const sb = ms.addSourceBuffer("audio/webm;codecs=opus");
    sb.mode = "sequence";
    flush();                       // append pending webm segments
    sb.addEventListener("updateend", flush);
  });
  ```
- **Why it matters:** the per-chunk `play()` anti-pattern is easy to reintroduce. Build the live path
  on MSE from the start; never `play()` inside a per-chunk loop.

### 11. BATCH the LLM call — never loop per output token/line
- **Symptom:** a streaming build that calls the LLM **once per generated line** (e.g. one Gemini call
  per podcast turn) silently burns the user's **monthly spend cap** — ~12–24 calls per episode. The
  user hit `ResourceExhausted` repeatedly; the cap was the *monthly dollar ceiling*, which backoff
  (rate-limit handling) does NOT fix.
- **Fix:** **generate the whole artifact in ONE LLM call**, then parse and stream the pieces. For a
  podcast: one Gemini call returns the full script; the server parses lines and yields them one at a
  time so TTS + live playback still happen line-by-line. Cost drops from ~12–24 calls/episode to 1.
- **Why it matters:** a durable pattern for ANY streaming/agentic build. Looping an LLM call per
  token/line/sentence is the #1 silent cost blowup. Batch generation; stream only the *output*.
- **Quota-aware verification:** never re-run the live LLM/API just to satisfy a verification gate when
  the user is near a cap. Use cheap static checks (compile + import + `--collect-only`) and rely on a
  PRIOR live run for behavioral proof. If you must re-verify behavior, wait for the cap to reset or
  ask the user first.

### 12. At the human gate, ASK with a MULTI-SELECT checklist — don't dump a wall of prose
- **Symptom:** the gate either pastes long status paragraphs, or asks one single-choice "works / broken?" verdict. Prose makes the user read; a single verdict collapses a multi-feature phase into one bit and loses *which* parts passed and *which* failed.
- **Fix:** the human testing gate is ONE `clarify` call, **always MULTI-SELECT, never single-choice** — one option per testable feature the phase shipped (derived from that phase's success criteria), plus a load-state question and a "Nothing worked" escape. Tick-all-that-apply pinpoints failures in a single answer. State only what the user must act on (the URL, one-line status) then ask. Put findings in notes (a skill reference), not the chat wall.
- **Why it matters:** stated preference. Bias every gate and post-fix turn toward one multi-select `clarify`. Long explanations belong in artifacts, not the conversation.
