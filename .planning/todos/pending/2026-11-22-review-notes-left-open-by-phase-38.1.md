---
created: 2026-11-22T00:00:00.000Z
title: Review notes left open by phase 38.1
area: tooling
severity: minor
files:
  - .planning/phases/38.1-runner-error-classification-and-retry-policy-inserted/38.1-REVIEW.md
  - .planning/phases/38.1-runner-error-classification-and-retry-policy-inserted/38.1-SPEC.md
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/references/cross-ai-errors.json
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py
  - tests/test_cross_ai_catalog.py
---

## Problem

The phase 38.1 code review left these items open. None loses data, prints a secret or leaves a process running; each
is a narrow window, a missing test for a branch that works today, a message that says too little, or a decision for
the owner.

## Goal

Close each item below when the named module is next changed, with a test for each behaviour change, and record the
owner's answer for the decision items before any code changes.

## Notes

- Decision (owner): `ensure-runner` keeps an upgraded copy's whole CONFIG `retry` object, so a copy rendered from
  template 10 (this project's live copy included) waits 600, 900, 1800 s and then every 600 s to the 4-hour cap, not
  the decided 60, 300, then 600 s. The plans recorded "no migration" as an orchestrator decision; the docs now say it and
  name the `[runner.retry]` override. Decide whether the upgrade replaces a kept `retry` equal to the old shipped
  default with the template's object.
- After an in-call hard wait the re-attempt can still open the one session reset: the hard tier starts when no session
  can be resumed, and when a later attempt makes the session resumable while `session_resets` is not spent,
  `ladderNext` returns `reset` and a soft series runs again in the call. Reachable only with a configured hard wait under
  60 s. Decide whether a call that entered the hard tier may still reset, and pin the answer with a case.
- An empty pool lock file blocks every later blocked-until write: `createLockFile` opens with `wx` and then writes, so a
  runner killed between the two leaves a file `readLockOnce` reads as `bad`, never cleared; each later write prints
  `cross-ai: blocked-until write skipped (pool lock busy)`. Treat a `bad` pool lock older than a short bound as stale,
  with a case that plants an empty lock.
- `blockedClear` (the `--blocked-clear` option and the ok-attempt clear) does not take the pool lock, so a writer that
  read the old record can write it back after a clear. Run the clear under `blockedWithLock`, failing open when busy.
- `--blocked-status` and `--blocked-clear` refuse only `--print-argv`, `--classify-only`, `--sweep`, `--describe` and
  `--self-test` beside them; lane flags (`--runtime`, `--model*`, `--prefer`, `--role`, `--pool`) are ignored and the
  call exits 0 without a launch. Refuse them as a usage error.
- `--classify-only` passes each entry's `stdout` to the stdout rows with no failure gate, while a live run reads stdout
  only for a failed attempt. Accept an optional `exit` per entry and gate on it, or document that every entry counts as
  a failed attempt.
- The stdout row `claude-hit-your-limit-stdout` matches `hit your (?:weekly )?limit`, but no case runs the weekly form
  through it and its evidence names the stderr case `evidence-claude-weekly`. Add a pure case and correct the evidence
  (catalogue JSON plus its template block through `ai_kit_spec.cross_ai_catalog`).
- `test_fixture_headers` (tests/test_cross_ai_catalog.py) checks paths, account and key shapes but not model names (R7):
  require model-like tokens to be `placeholder-model-<n>`, `router-env/<x>` or `fake` forms.
- SPEC R3 still lists "an empty answer" among the failed attempts whose stdout rows are read; plan 38.1-04 narrowed it
  (an exit-0 empty answer without a parse error stays `empty_answer`, case `stdout-claude-empty-gated`), and the SKILL and
  policy doc state the narrow rule. Add the dated amendment to R3 after the stacked units merge (unit 39 carries its own
  hunks of 38.1-SPEC.md, so an edit on unit 38.1 now would pause its restack).
- A host that prints the limit on stderr before its typed event is unverified (the live watcher keeps the first
  terminal string). Record the order from a real limit when one occurs (the opt-in capture hook idea of todo
  2026-11-02), then add a fixture.
- Product node spawns outside the runner's own callers were not opened by the review: `fold_adapters.py`,
  `gsd_tools.py`, `gsd_catalog.py`, `plan_io.py`, `followups.py`, `edge_floor.py` and `check_dogfood.py` run `node`
  through a plain `subprocess.run`, whose timeout kills only the first process. Check whether any can run under a HOME
  without the Volta toolchain (a test or a scratch-HOME helper) and, where it can, start it through `run_in_own_group`.
- R7's "with the commands used": the six bad-model fixtures record host, version and date but no capture command,
  because the SPEC's capture record never stored them; none was invented. Record the command with the next capture.
