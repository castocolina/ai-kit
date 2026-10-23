---
phase: 19-evaluation-on-claude
plan: 01
subsystem: testing
tags: [curated-config, resolve-model, oracle, snapshot, digest, e2e]

requires:
  - phase: 18.1-one-runtime-model
    provides: DIGEST_CMD formula for skill digests
provides:
  - dev-only eval helper with snapshot, digest and resolve-model matrix subcommands
  - plan-derived resolve-model oracle over live gsd-core tables
  - real-node matrix e2e module registered in E2E_MODULES
affects: [19-02, 19-03, 19-04, 19-05, 19-10]

actuals:
  tokens: n/a
  tasks: 2
  commits: 1

key-files:
  created:
    - tests/gsd_curated_eval.py
    - tests/test_gsd_curated_eval.py
    - tests/test_ai_kit_gsd_curated_config_matrix.py
  modified:
    - tests/test_curated_config_apply_e2e.py
    - tools/run_unittest_parallel.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "gsd-core guard widened to 1.16. and 1.17. (GSD_CORE_PREFIXES, shared by the helper and the apply e2e tier), per the orchestrator's instruction for this checkout"
  - "Oracle branch order mirrors the resolver: model_overrides.<agent>, then models.<phase type>, then MODEL_PROFILES[agent][profile]"
  - "Empty resolved model fails unless inheritance is promised; nothing in this phase promises it"
  - "matrix refuses non-Claude hosts with exit 2 until Phase 20 extends the oracle"
  - "Hard stops raise a SystemExit subclass carrying exit_code and reason, so tests assert both"

patterns-established:
  - "Every matrix bundle lives under mkdtemp() and is removed in a finally block, including when its builder raises"
  - "Output carries only <worktree>, <home> and <scratch> labels, never machine paths or file values"

requirements-completed: [APP-05, EVAL-02, EVAL-03]

duration: n/a
completed: 2026-10-17
status: complete
orchestrator_verify: "VERIFY 19-01: 2/2 passed"
---

# Phase 19-01: Curated-config eval helper with resolve-model matrix oracle

**Dev-only eval helper with protected-set snapshot, SKILL.md digest and a real-node resolve-model matrix (5 combinations x 2 start paths x 35 agents, 420 checks) graded against an oracle built from live gsd-core tables.**

## Performance

- **Tasks:** 2
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments
- `snapshot --out` / `--check` hashes the strict and host-managed protected sets, with `<home>/.cursor/cli-config.json` in the strict set. On this machine `snapshot ok` and the JSON contains no absolute path.
- `digest` prints `551234cc5f4f55cc`, identical to the 18.1-21 DIGEST_CMD one-liner for `ai-kit-gsd-curated-config`. `--check` rejects zero-digest rows and superseded/context rows are skipped.
- `matrix` ran against the checkout-local gsd-core (1.17.0): all 10 rows (5 combinations x P1/P2) match the oracle across 35 agents, Control 1 fails 33 of 35 unoverridden agents (the other two carry overrides), Control 2 passes, and the informational runtime row reads `gpt-5.6-sol` / tier `opus` with `informational: true`.
- `matrix --host codex` exits 2 with `matrix oracle supports claude only ...`.
- `test_curated_config_apply_e2e` guard widened to `GSD_CORE_PREFIXES` (`1.16.`, `1.17.`) in both the `_gsd16_or_skip` and the class-level twin, and in the module docstring. Its 7 real-node tests now run instead of skipping.
- Unit tier: 56 hermetic tests in `tests/test_gsd_curated_eval.py` (oracle, snapshot, digest, matrix env, matrix shape, labels, version guard, CLI). Real-node matrix e2e: 9 tests in `tests/test_ai_kit_gsd_curated_config_matrix.py`, registered in `E2E_MODULES`; `Makefile` and `.pre-commit-config.yaml` regenerated with `tools/gen_test_groups.py`.

## Task Commits

Single commit for the plan (per Run rule 10): `test(19-01): curated-config eval helper: snapshot, digest, resolve-model matrix with oracle`.

## Files Created/Modified
- `tests/gsd_curated_eval.py` - dev-only helper: `snapshot`, `digest`, `matrix` subcommands and the oracle
- `tests/test_gsd_curated_eval.py` - hermetic unit tests of the oracle, snapshot, digest and matrix env
- `tests/test_ai_kit_gsd_curated_config_matrix.py` - real-node matrix e2e module
- `tests/test_curated_config_apply_e2e.py` - `_golden_bundle` gains `profile=`, `rigor=`, `defaults=`, `pre_inventory=`; gsd-core guard widened to `GSD_CORE_PREFIXES`
- `tools/run_unittest_parallel.py` - `E2E_MODULES` entry for the matrix module
- `Makefile`, `.pre-commit-config.yaml` - regenerated test group listings
- `.planning/phases/19-evaluation-on-claude/19-01-SUMMARY.md` - this file

## Decisions Made
- The plan pinned gsd-core 1.16.x; this checkout runs 1.17.0. Following the orchestrator's instruction, the guard accepts both lines. `MODEL_PROFILES` and `AGENT_TO_PHASE_TYPE` were verified equal on this machine (35 keys each, empty symmetric difference), and the matrix re-checks key parity every run.
- Matrix failures are `_refusal` exceptions (a `SystemExit` subclass with `exit_code` and `reason`), because plain `SystemExit(code, msg)` stores a tuple in `.code`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scratch bundle directories leaked when a builder raised**
- **Found during:** Task 2 verification (10 empty `/tmp/xai-matrix-*` directories after the unit run)
- **Issue:** `_bundle_for` created a `mkdtemp()` directory and did not remove it if `bundle_fn` raised.
- **Fix:** Remove the scratch directory on failure and add `test_bundle_for_removes_scratch_when_the_builder_fails`.
- **Files modified:** `tests/gsd_curated_eval.py`, `tests/test_gsd_curated_eval.py`
- **Verification:** `/tmp/xai-matrix-*` count is 0 after the unit run and after the real-node matrix.
- **Committed in:** the plan commit

**2. [Rule 3 - Blocking] gsd-core 1.16.x guard**
- **Found during:** Task 1
- **Issue:** the checkout-local gsd-core is 1.17.0, so the existing guard skipped every real-node test.
- **Fix:** Widened the guard to `GSD_CORE_PREFIXES` as the orchestrator instructed.
- **Verification:** `python3 -m unittest tests.test_curated_config_apply_e2e` runs 7 tests and passes.
- **Committed in:** the plan commit

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking). Impact: no scope creep.

## Issues Encountered
- The plan's leak-check pattern also matches the text of the shell command that runs it. The real-process check (`pgrep -af "gsd_curated_eval.py|gsd-tools.cjs"`) lists only two `gsd-tools.cjs` processes (PIDs 395619, 395621). Both appear in `tmp/pids-19-01.before`, so this plan did not start them and they are left alone.
- Per-plan gsd-core version: `1.17.0`, not the `1.16.x` the plan assumed. Recorded above.

## Verification
- `python3 -m unittest tests.test_gsd_curated_eval tests.test_curated_config_apply_e2e` passes (63 tests).
- `python3 tools/run_unittest_parallel.py --group unit`: 42/42 modules passed.
- `python3 tools/run_unittest_parallel.py --group e2e`: 8/8 modules passed, including `tests.test_ai_kit_gsd_curated_config_matrix` (9 tests, 75 s).
- `ruff check`, `pyright` (0 errors) and `vulture` pass on the plan's Python files. No line exceeds 100 characters.
- Matrix: `python3 tests/gsd_curated_eval.py matrix --json` exits 0 with the assertion from the plan's acceptance criteria printing `ok`. Output contains no `$HOME`, `$PWD` or `$TMPDIR` string.
- Snapshot: `snapshot --out tmp/snap.json` then `snapshot --check tmp/snap.json` prints `snapshot ok`.
- Digest: `551234cc5f4f55cc`.
- Leak check: `ps -eo pid=,args= | awk 'NR==FNR{b[$1];next} !($1 in b) && /gsd-tools[.]cjs|[g]sd_curated_eval/' tmp/pids-19-01.before -` prints nothing (the `pgrep` finding above is the same two pre-existing processes).

## Pre-existing failures
None.

## Deleted tests
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 19-02 can use `_golden_bundle(profile=, rigor=, defaults=, pre_inventory=)` and `matrix_env`.
- 19-03 and 19-04 extend `check_digests` and add `grade`, `secret-scan` and `smoke` to the same helper.

---
*Phase: 19-evaluation-on-claude*
*Completed: 2026-10-17*
