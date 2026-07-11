# Harness feedback — human testing gate should own the run

Live-run lessons from building the AI Music Tutor (phases 1–2) that are NOT yet
folded into the harness procedures. Each is a candidate for a one-line rule in
`harness/agents/agent-builder.md` / `SKILL.md` (not a standalone doc long-term).

## Open items

### 1. The human gate must OWN launching the server — the user shouldn't manhandle the run
- **Symptom:** at the Phase-2 testing gate the agent left a `clarify` multi-select to the
  user but did NOT launch the server or give a live URL; the user ended up starting/killing
  processes and hunting for a free port themselves ("this one is busy", "only giving me whole
  notes"). The gate asked "did it work?" before the app was even running for them.
- **Rule to bake in:** the human testing gate is the agent's job to make *testable*, not the
  user's job to run. Before asking the multi-select checklist:
  1. boot the server (explicit project interpreter, pick a free port),
  2. smoke-test it live (health + the new endpoint(s) + a real in-browser render with 0 console
     errors — the agent can use its own browser),
  3. hand the user ONE live URL + a one-line "what to click",
  THEN ask the multi-select gate. If the server can't boot, that's a BLOCKER, not a question.
- **Why:** a gate that asks "does it work?" with no running app just bounces the work back to
  the user. The drill is only verifiable once it's actually live and the agent has proven it.

### 2. (reminder) agent-builder can return before git — already folded, keep enforcing
- The delegated build may end its turn with code+tests done but commit/push/PR skipped (seen
  twice). Parent finishes the hard gate. Covered in `agent-builder.md` + `hermes-pitfalls.md §1`.

### 3. (reminder) doc-accuracy: reference files must exist in the REPO skill
- `SKILL.md` referenced `references/hermes-pitfalls.md` before it existed in-repo (only in the
  installed copy). Fixed by adding it to the repo. Keep references resolvable from the repo.

## Not yet folded into the skill docs
Items 1–3 above are deliberately kept here until the next harness-hardening pass so they can be
condensed into generic one-liners in `agent-builder.md` / `SKILL.md` (mirroring the "effective and
lean" rule). Do NOT bloat the skill with prose — one line each when folded.
