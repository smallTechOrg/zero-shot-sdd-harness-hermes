# zero-shot-build — Hermes runtime pitfalls

Durable, generic lessons from real `/zero-shot-build` runs. Only things that change what you do on the
*next* build — not an app changelog. Keep this lean.

### 1. A delegated build can return before finishing
- **Symptom:** a `delegate_task` sub-agent ends its turn with code written and verified but git skipped — no commit, no push, no PR.
- **Fix:** the parent finishes. Read the *actual* files (don't trust the summary), run the real gate, then commit/push/PR. "Commit + push + open PR" is a hard gate in the agent-builder role, not an optional epilogue.

### 2. `max_spawn_depth=1` blocks nested fan-out
- **Symptom:** the orchestrator can't spawn code-generator / qa-auditor children, so the build stalls.
- **Fix:** run inline. agent-builder reads `harness/agents/*.md` as procedure and does the work itself. Don't wait for workers that will never spawn.

### 3. Empty or "you decide" answer at intake
- **Symptom:** the user replies to an intake question with nothing useful ("whatever", "you decide", blank).
- **Fix:** treat as "you decide" → pick the lowest-risk default, label it `Assumed:` in the brief. Don't block; a single gentle follow-up is fine, endless re-asking is not.

### 4. Boot before you hand off; pin the interpreter
- **Fix:** before writing the Stage 3 handoff, actually boot the server and hit `/health` — write only *verified* run commands. Launch servers with the explicit project interpreter (`.venv/bin/python -m ...`), never a bare `python`/`uvicorn` that a shared agent venv can shadow (silent `ModuleNotFoundError`).

### 5. Re-verify cheaply — don't re-burn the live API
- **Fix:** after a commit, prove no regression with `py_compile` + `pytest --collect-only` (imports resolve). Reserve the full live-API run for the first green and after logic changes.

### 6. Batch the LLM call — never loop per output token/line
- **Symptom:** calling the LLM once per generated line/token silently burns the user's monthly spend cap (which backoff can't fix).
- **Fix:** generate the whole artifact in ONE call, then parse and stream the pieces downstream. Applies to any streaming/agentic build.

### 7. At the human gate, the ROOT SESSION owns the run — ASK with a per-feature checklist question
- **Symptom:** the gate asked "does it work?" but never launched the server or gave a URL, so the user ended up starting/killing processes and hunting ports. The run was bounced back to the user.
- **Fix:** before the checklist, the root session MUST launch the server (explicit interpreter, **free port**, retry if busy), smoke-test live (health + new endpoints + a real in-browser render with **0 console errors** — the root session can use its own browser), then hand **ONE live URL** + one-line status. Only THEN ask the checklist as a plain-text question (Hermes has no multiple-choice) — list one numbered line per feature shipped and ask the user to reply works/broken per line, never a bare yes/no. If it won't boot, that's a BLOCKER, not a question. The user must never run a terminal command to test. (From PR #8.)
