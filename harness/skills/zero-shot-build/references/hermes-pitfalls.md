# zero-shot-build — Hermes runtime pitfalls

Durable, generic lessons from real `/zero-shot-build` runs on Hermes. Only things that
change what you do on the *next* build. The architecture in SKILL.md already encodes the
big ones (root-session orchestration, inline fallback, gate-owns-the-run); this file keeps
the sharp edges.

**How lessons get here:** each build keeps a live `NOTES.md` journal on its feature branch
(see SKILL.md → "The build journal"). After the run, the durable generic lesson is
distilled into this file via a separate harness PR; the run-specific war stories stay on
the build branch.

### 1. A delegated worker can return before finishing
- **Symptom:** a `delegate_task` child ends its turn with code written but the last 5%
  (a rename, a failing import, git) skipped — its summary still reads "done".
- **Fix:** the root verifies every handback — files exist, gate re-run cheaply — and
  finishes the remainder inline. Never re-delegate the missing 5%.

### 2. `max_spawn_depth=1` — workers cannot spawn workers
- **Fix:** the ROOT session is the orchestrator (this is the architecture, not a
  workaround). Delegation is for leaf work only; when it's unavailable at all, run the role
  file inline as a checklist. Never wait for a child that cannot spawn.

### 3. `clarify` can fail to load; answers can come back empty
- **Fix:** no load → ask in plain text, one question at a time (never a wall of questions).
  Empty answer → treat as "you decide": lowest-risk default, recorded as `Assumed:`.

### 4. Sub-agent background processes die on return
- **Fix:** only the root session launches servers the user (or the smoke) will touch. A
  worker booting a server "for the handoff" hands the user a dead port.

### 5. Pin the interpreter; boot before you hand off
- **Fix:** launch with `.venv/bin/python -m src` — bare `python`/`uvicorn` can resolve to a
  shared agent venv (silent `ModuleNotFoundError`). Before writing any handoff, actually
  boot the server and hit `/health` — write only verified run commands and URLs.

### 6. A stale dev DB turns a green suite into a live 500
- **Symptom:** tests pass (fresh tmp DB per test) but the live server 500s —
  `table runs has no column named …`. `create_all` never ALTERs an existing table.
- **Fix:** schema changed ⇒ ship the alembic migration in the same slice and apply it (or
  recreate the dev DB) before the boot gate. The boot gate must exercise the same DB the
  user will hit.

### 7. Batch the LLM call — never loop per output line/token
- **Symptom:** one call per generated line silently burned a real monthly spend cap
  (backoff can't fix a cap).
- **Fix:** generate the whole artifact in ONE call; parse and stream the pieces downstream.

### 8. A present key can still be dead
- **Symptom:** `.env` has the key, presence check passes, every real-call gate then fails
  401 ("User not found" — revoked/deleted account).
- **Fix:** at intake, validate the chosen provider's key with one minimal real call before
  building. On 401 mid-build: BLOCKED naming the env var — it's a user step, not a bug.

### 9. Re-verify cheaply — don't re-burn the live API
- **Fix:** after mechanical edits, `py_compile` + `pytest --collect-only` proves imports
  resolve. Reserve full real-key runs for first-green, logic changes, and pre-handoff.
  Free-tier quotas (429) trip fast during builds — retry/backoff belongs in the generated
  code, and cap your own test generations.

### 10. At the human gate, the ROOT owns the run — multi-select, always
- **Fix:** launch (pinned interpreter, free port, retry if busy) → live smoke (health + new
  endpoints + the served UI) → hand the user ONE verified URL + "what to click" → only then
  the multi-select `clarify` checklist (one option per shipped feature + a "nothing worked"
  escape). If it won't boot, that's a BLOCKER to fix, not a question to ask.

---

## From mining the prior runs' Hermes logs (auto-podcaster / music-tutor / data-analyst)

Evidence counts are from `~/.hermes/logs/agent.log*` across Jul 10–20 builds.

### 11. Rate-limit storms dwarf the retry budget — prefer sequential over fan-out on one key
- **Symptom:** 500+ `429`/`RateLimitError` lines; ~3,300 "credential pool: no available
  entries" polls ≈ **~14h cumulative blocked**. Parallel fan-out and background sessions all
  hammer ONE shared key/pool; a 3× / 2–6 s backoff is orders of magnitude too small.
- **Fix:** on a shared/free key, run slices **sequentially inline** — parallel delegation
  multiplies 429s, it doesn't speed the build up. Cap your own test generations. Tell the
  user up front that a small paid balance removes the single biggest source of stalls.

### 12. A delegated worker can report ✓ completed with a 429 error as its whole body
- **Symptom:** ~29% of delegations delivered a batch marked `status=completed` whose body
  was only "API call failed after 3 retries". "Completed" ≠ "succeeded".
- **Fix:** trust-but-verify includes the handback CONTENT — if a worker's return is an
  error/empty/a rate-limit body, treat the slice as NOT done and finish it inline. Never
  read the status field alone.

### 13. `clarify` times out at ~300 s and returns an empty answer indistinguishable from a skip
- **Symptom:** long waits ending in `"user_response": ""`; some sessions burned 80+ min in
  clarify alone.
- **Fix:** an empty answer — whether a real skip OR a 5-min timeout — is always "you decide":
  lowest-risk default, recorded `Assumed:`. Never re-ask the same question; keep questions
  few and batched so a timeout costs one default, not a lost round.

### 14. Validate the model slug + params, not just the key, on the first real call
- **Symptom:** first-call-of-session failures — `model_not_found`/`does not exist` (7),
  `Encrypted content is not supported` (6), unrecognized `reasoning_effort` (3). Free model
  slugs churn (a pinned `:free` model can vanish or go paid-only overnight).
- **Fix:** the intake real-call check (pitfall §8) asserts the **model** answers too, not
  just that the key authenticates. On `model_not_found`, list the provider's current models
  and pick an available one before building — don't start a phase on a dead slug.

### 15. Long context gets compressed mid-build — keep durable state on disk, not in the chat
- **Symptom:** frequent context-compression events with message-alternation repairs; state
  that lived only in the conversation was lost or garbled across a compaction.
- **Fix:** the spec, the roadmap, `NOTES.md`, and committed code are the durable memory —
  re-read `spec/roadmap.md` and `git log` at the start of each phase rather than trusting
  recall. Never hold a decision only in conversational context across a long phase.

### 16. `.env` is unreadable by design on Hermes — never punt the check back to the user
- **Symptom:** live run — at the technical round the agent said "I can't read `.env` for
  security reasons, please open it and confirm you set the key," 10 minutes into the
  session. Confirmed in `~/.hermes/logs/agent.log`: `read_file` on any `.env`/`.env.*` path
  is hard-blocked platform-side ("Access denied: ... secret-bearing environment file").
  That block is correct — the bug is stopping there instead of working around it.
- **Fix:** never call `read_file` on `.env`. Run it through `terminal`/`execute_code`
  instead — a short script that loads `.env` itself (`python-dotenv`, or `source .env` in
  bash) and prints ONLY a pass/fail signal: presence as a boolean, then the result of one
  real test call (`OK`/`401`/`429`/`model_not_found`) — never the key value or a raw
  exception that might echo it. Only escalate to the user if presence is false or the test
  call fails, and say exactly why — never "go check the file yourself and report back."
