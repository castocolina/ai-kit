---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 01
subsystem: infra
tags: [cross-ai, runner, env-marker, self-test, dogfood]

requires: []
provides:
  - Runner marker AI_KIT_CROSS_AI_CHILD=1 on every child env built by childEnv (read by 26-04's arm refusal)
affects: [26-04]

actuals:
  tasks: 2
  commits: 2

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - tests/cursor_fakes.py

key-decisions:
  - "The marker is set last in childEnv, after both scrub loops, so neither a caller's extra nor an inherited value changes it"

requirements-completed: [QTA-04]
---

# Phase 26 Plan 01: Runner child marker Summary

Every cross-AI runner child now sees `AI_KIT_CROSS_AI_CHILD=1`, and the dogfood runner carries it.

## Commits

- `49b9120` feat(26-01): mark every cross-AI runner child with AI_KIT_CROSS_AI_CHILD=1
  (template `childEnv` + fake pi mode `envmarker` + self-test case `child-marker-env`, and the
  dogfood copy re-rendered through `ensure-runner`; exactly those two files)
- `ab5ec47` fix(tests): stop the Cursor fake dashboard's handler threads with the server (deviation, below)

## Verify evidence

- Guard: `CLAUDECODE=1`; no cross-AI run in flight (`pgrep` empty) before both tasks.
- `selftest_s_baseline=168` (template, HEAD `66baac3`).
- Task 1: `child-marker-env` alone -> `self-test ok`; full template self-test -> `self-test ok`,
  `selftest_s=167`; marker named 4 times in the template; `CONFIG.scrubEnv` does not list it; the
  template names neither the session-wake directory nor its package (0 hits).
- Non-vacuity: the same case on a scratch copy with the marker line removed ->
  `self-test FAIL child-marker-env: marker.seen="0"`.
- Task 2: committed copy and working copy `pristine` before the render; `ensure-runner --cwd .` ->
  `{"ready": true, "runner": "change", ...}`; no `.new`; dogfood self-test `self-test ok`,
  `selftest_s=167`; parsed CONFIG equals the committed one (runtime `pi`, models, routerBacked
  kept); `dogfood ok`; `tests.test_curated_config_script` 1/1 (TestDogfoodCopy OK);
  `make test-unit` 57/57 + 1/1; commit check on `49b9120` passes (verify exit 0).
- Pre-commit hooks passed on both commits (no `--no-verify`).

## Deviations

- **[Rule 13, pre-existing flake fixed at its root] `tests.test_cursor_quota` aborted at
  interpreter shutdown** (rc -6, `_enter_buffered_busy ... daemon threads`) in the first
  `make test-unit`, after all 37 tests passed. Not caused by this plan (its commit touches only
  `.mjs` files); reproduced on parent `66baac3` in a temp worktree (1/6 runs aborted, worktree
  removed) and in this tree (3/6). Cause: `tests/cursor_fakes.py` trickle handlers looped
  forever on daemon threads and logged BrokenPipe tracebacks after the client gave up. Fix: a
  stop event ends every delay and trickle loop, handler threads are non-daemon and joined by
  `server_close()`, and a client `ConnectionError` is not logged. After it: 10/10 clean runs of
  `test_cursor_quota` + `test_cursor_fakes`, `make test-unit` green, pyright and vulture clean.
  Committed separately (one logical change), outside `files_modified`.

## Scratch

`tmp/p26/01/` (before.json, logs, check.py) is deleted after this SUMMARY.
