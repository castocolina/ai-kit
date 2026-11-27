---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 07
subsystem: runner template (real-home guard for exec lanes inside an ai-kit checkout)
tags: [cross-ai, runner, real-home-guard, self-test]
requires: [41-06]
provides:
  - "cross-ai.mjs: `AI_KIT_MARKERS` (detection.py and tools/setup.py) and `aiKitCheckout(dir)`, a filesystem-only walk that stops at the first folder holding a `.git` entry (folder or linked-worktree file) and needs both markers there; no environment variable, no subprocess"
  - "cross-ai.mjs runCli: `if (mode === 'exec' && aiKitCheckout(ctx.cwd)) env.AI_KIT_REFUSE_REAL_HOME = '1';` right after the lane env is built (an inherited other value is replaced; review mode and model listing unchanged)"
  - "cross-ai-selftest.mjs: fakes `realhome` and `review-realhome`, helper `writeRealhomeMarkers(repo)`, six `realhome-*` logic cases (checkout root, subdirectory under a ceiling at the checkout root, inherited 0, linked worktree, nested plain repo, review mode)"
affects: [41-08, 41-14]
key-files:
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - skills/ai-kit-spec-review/references/cross-ai-selftest.mjs
decisions:
  - "Window rule: `make check-dogfood` is red by design until 41-08 re-renders the live copy; no checkpoint, fold or push between 41-07 and 41-08."
metrics:
  tasks: 2
  commits: 2
---

# Phase 41 Plan 07: real-home guard for exec lanes inside an ai-kit checkout Summary

The runner template now sets `AI_KIT_REFUSE_REAL_HOME=1` in the environment of every exec lane whose working directory is
inside an ai-kit checkout: walking up from the lane's directory, the first folder holding a `.git` entry decides, and it counts
only when it also holds `skills/ai-kit-spec-review/ai_kit_spec/detection.py` and `tools/setup.py`. Review lanes, model listing and
directories outside a checkout are unchanged. Six hermetic self-test cases pin it.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 21588ee | feat(41-07): set the real-home guard for exec lanes inside an ai-kit checkout |
| 2 | c173b67 | test(41-07): pin the real-home guard in a subdirectory, an inherited value, a linked worktree, a nested plain repo and review mode |

Cross-AI lanes (pi, router-env/my-coding), one per task, each AIKIT-XAI `status=ok attempts=1`: Task 1 377 s (lane hook
158/158 + uv 21/21), Task 2 196 s (lane hook 158/158 + uv 21/21, all self-test shards included). The hook deferred
`tests.test_ai_kit_gsd_curated_config_matrix` to push both times. Task tip recorded in `tmp/run-2026-11-23/p41-07/task-tip.sha`.

## Verification (chunk executor, own runs)

- Acceptance Task 1: `function aiKitCheckout(dir) {` 1, the `AI_KIT_MARKERS` line 1, the exec env line 1,
  `realhome-exec-checkout-root` 1, `AI_KIT_REFUSE_REAL_HOME` in the template 1, the `.git` walk line 1; `GIT_CEILING_DIRECTORIES`
  still 2 parses, `EXEC_PREAMBLE` still 3 hits (unchanged). The diff equals the plan text; no new line carries an id.
- Acceptance Task 2: `name: 'realhome-` 6; both subjects as planned; scope from 100f59c: exactly the two `files_modified` paths.
- `run_cases.py` with the six realhome cases plus `child-marker-env`: `self-test ok`, rc 0.
- `tests.test_cross_ai_runner_e2e` (28) and `tests.test_runner_describe` (20): `2/2 modules passed`.
- `--print-argv` (pi, router-env/my-coding) of the template in exec and review mode and of the live copy in exec mode: identical
  before and after once the per-run session uuid is normalized (the env line does not reach argv).
- Gates after the plan: unit + arch groups under the watchdog `204/204 modules passed` (peak 7, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make pylint` exit 0 each. `make check-dogfood` exits non-zero with exactly the one expected
  problem line `check-dogfood: .planning/scripts/cross-ai.mjs differs from the template outside the config block` (the rest are
  judge stale-digest and facts-drift notes and `no-write guard: 3 attempted, 3 executed, 0 skipped`).

## Deviations

- Task 2 `realhome-exec-linked-worktree`: the plan's check reads `path.join(wt, '.git')`, but `wt` is local to `setup`; the lane
  rebuilt the same path from the literal in `check`, so `rg -c -F "'wt-realhome-exec-linked-worktree'"` prints 2 instead of the
  planned 1. Same path, same assertion (the `.git` must be a file); open for code review.

## Open items

- `make check-dogfood` stays red until plan 41-08 bumps the template to 14 and re-renders the live copy.
- The deferred `tests.test_ai_kit_gsd_curated_config_matrix` is run after 41-08 (the window's end).
