# Harness Feedback Log (live, from real `/zero-shot-build` runs)

This file tracks **meta-harness feedback** given by the user while running the harness — kept on its
own branch/PR (`harness/meta-feedback-live`) so it never mixes with app-build PRs
(e.g. `feature/music-tutor-v0.1`).

## Rules now enforced in the harness (from this feedback)

1. **Intake + testing gate must use `clarify` as MULTI-SELECT, never single-choice.**
   The user said: *"u should ask multi choice questions not single choice choice"*. Applied: every
   product/technical round is multi-select; the Stage 3 gate is a multi-select checklist
   (tick all that apply: staff renders / audio plays / checking correct / hints work / streaming works /
   reasoning shown), NOT a single verdict. (2026-07-11)

2. **Don't make the user read a wall of text — ask clean questions.**
   The user said: *"you're making me read a lot, you should be asking questions"*. The skill's Stage 3
   already mandates the gate be a `clarify` call, not a prose wall; reaffirmed and kept.

3. **Fidelity rule — emulate the original verbatim.**
   The user said: *"scrap PR #4, re-port the original verbatim, as close to that harness as possible"*
   and *"it should be as close to that harness as possible"* / *"hope that makes it hermes native"*.
   Merged as PR #5 (1:1 re-port; only Hermes tool mapping). No process deviations from the original.

## Open / in-flight feedback (not yet folded into a doc)

- **Confirmed: background `delegate_task` returns at ~95% (iteration cap), skipping the git hard-gate.**
  During the live music-tutor build, agent-builder hit its iteration cap after the code was complete
  and verified (pytest 10 passed, server boots, UI builds) but BEFORE committing/pushing/opening the PR.
  The parent (root session) had to finish the hard gate itself: stash app work off the feedback branch,
  create `feature/music-tutor-v0.1` from `main`, commit, push, open PR #7. This is exactly the
  `sub-agent-early-return` failure mode already documented in `references/hermes-pitfalls.md`. It is now
  CONFIRMED on a real run, not just theoretical. Action: the skill's Stage 2/4 hard-gate wording already
  covers it ("if a background delegation returns early... the parent finishes those steps"); keep it, and
  consider lowering the delegation iteration cap risk by giving agent-builder explicit git/gh steps early.
  (2026-07-11)

## How to extend this file

Append under the right section as feedback arrives. Each item: quote the user's words, the date, and
what changed (or will change) in the harness because of it. Keep app-build discussion OUT of this file.
