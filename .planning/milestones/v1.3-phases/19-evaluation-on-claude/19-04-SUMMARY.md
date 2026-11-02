---
phase: 19-evaluation-on-claude
plan: 04
subsystem: testing
tags: [curated-config, smoke, eval, repo-guard, fault-injection]

requires:
  - phase: 19-01
    provides: snapshot, digest, resolve-model matrix, real-node e2e tier
  - phase: 19-02
    provides: seeded scratch cache (`_seed_caches`, `assert_no_probe`)
provides:
  - "smoke subcommand: D-14 steps 1-7 as one host-agnostic procedure"
  - refuse_repo_apply guard on every real apply path
  - plan-copy fault injector with a recorded, undone prior write
  - byte-level validation after apply (skill references, backups, leftovers)
affects: [19-05, 19-10, phase-20]

key-files:
  modified:
    - tests/gsd_curated_eval.py
    - tests/test_gsd_curated_eval.py

key-decisions:
  - "refuse_repo_apply prints the reason and exits 2 (direct call and CLI agree)"
  - "smoke apply uses a keyword-tolerant which_fn: the product calls which_fn('gsd_run', path=...) when PATH is set"
  - "every step records its own failure, including non-SystemExit errors, so the snapshot always runs"

patterns-established:
  - "Steps return {name, ok, detail}; run_smoke continues to the strict snapshot diff"

requirements-completed: [EVAL-03, APP-05]

duration: n/a
completed: 2026-10-17
orchestrator_verify: "VERIFY 19-04: 2/2 passed"
---

# Phase 19-04: Scripted live smoke with repo-root refusal and fault injector

**`smoke` subcommand encodes the D-14 live procedure; project (a) runs end to end on real node and gsd-core 1.17.0; ai-kit is refused for any real apply.**

## Verification

- `python3 -m unittest tests.test_gsd_curated_eval -k TestSmoke`: 23 tests, OK (floor was 18).
- `python3 -m unittest tests.test_gsd_curated_eval`: 200 tests, OK (no regression in the 177 pre-existing).
- `refuse_repo_apply(REPO_ROOT)` exits 2 with `refusing a real apply on the repo root`; a scratch dir passes.
- Hand run of project (a) against real node, scratch `GSD_HOME`, seeded cache, all four steps PASS:
  - inventory, recommend, choices: no placeholder forced
  - dry run (tree hash unchanged), apply, validation: config reads back, backup equals pre-apply bytes, no marker
  - second apply: `writes 0`, bytes identical, backups +1
  - forced failure: `intel.enabled` written then undone, `failed_key` review.default_reviewers, exit 1, bytes restored, no marker
- `python3 tools/run_unittest_parallel.py --group unit`: 42/42. `--group e2e`: 8/8. `--group arch`: 1/1.
- `make lint`: passes. ruff check and format clean. pyright 0 errors. vulture clean.
- `python3 tests/gsd_curated_eval.py digest`: `551234cc5f4f55cc` (unchanged).

## Not verified here (explicit)

- The full `smoke` run was **not** executed (plan forbids it; 19-05 owns it). Steps 2 (ai-kit), 5 (project b) and 6 (matrix via `smoke`) are covered by unit tests with injected seams only, not live.
- Project (b) `validate_applied` was not run live.
- `make validate` and `make test` aggregates were not run by the executor; orchestrator gates per Run rule 7.

## Deviations from the plan's wording

- `_seed_caches` takes a `_Paths` layout, not `(work, repo_root)`; the smoke uses `_layout(work)`.
- `resolve_choices` closes artifact choices first, reloads, then model keys, as specified. A `plan-set` failure raises `SystemExit`, recorded as a step failure.
- `SmokeCtx.env` is the authority for `XDG_CACHE_HOME`; `_seed_for_smoke` refuses an env that points elsewhere.
- Lazy `cli` imports keep the file's existing `# pylint: disable=import-outside-toplevel` pattern (tests tier, not pylinted per AGENTS.md).

## Fixed during execution (this plan's own code)

- My first insert shadowed the grader's `_placeholders`; renamed to `_smoke_placeholders`. Three TestGrader errors went away.
- `refuse_repo_apply` raised `_refusal` which exited 1 on a direct call; now prints and `SystemExit(2)`.
- The smoke's `which_fn` was one-argument; the product passes `path=` when PATH is set. Fixed in the smoke's apply path only.
- Dry-run JSON leaked to stdout; captured.
- A non-`SystemExit` error in a step aborted the run; `_step` now records every failure.

## Pre-existing failures

- `vulture` `tests/test_gsd_curated_eval.py:799` unused `timeout` (100%): present at base `HEAD` (19-02, `7590acf`). Fixed here with a read of the argument in the fake's `wait`, since the caller passes `timeout=` by keyword.

## Deleted tests

None.

## Files Created/Modified

- `tests/gsd_curated_eval.py` - `smoke` subcommand, `refuse_repo_apply`, `tree_sha256`, `inject_fault`, `perturb_before_fault`, `resolve_choices`, `validate_applied`, step functions, `render_smoke_evidence`
- `tests/test_gsd_curated_eval.py` - `TestSmoke` (23 tests)
- `.planning/phases/19-evaluation-on-claude/19-04-SUMMARY.md` - this file
