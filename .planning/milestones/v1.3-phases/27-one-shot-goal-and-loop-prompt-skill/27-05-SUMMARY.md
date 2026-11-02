---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 05
subsystem: tooling
tags: [goal-prompt, strategy-matrix, survival-rank, property-tests, stdlib, tdd]
requires:
  - phase: 27-01
    provides: "skill directory, gp_common helpers, fixture builders, pyright path, test-group listings"
  - phase: 27-02
    provides: "scope kinds (opengsd, gsd-unproven, superpowers, none) that the matrix reads"
  - phase: 27-03
    provides: "primitive rows with kind, rank, availability (gp_host.build_primitives output)"
  - phase: 27-04
    provides: "e2e detection that feeds the derived provable flag"
provides:
  - "gp_matrix.RULES: the strategy matrix as a tuple of row dicts, rows M01 to M11l"
  - "gp_matrix.select(MatrixInputs) -> {strategies, dropped}: one to three ranked strategies, exactly one recommended"
  - "gp_matrix.wake_primitive(primitives): the loop-capable row with the highest survival rank, labelled unverified when not available"
  - "gp_matrix.derive(count, unattended, e2e_none, mockups): must_outlive and provable, never asked (D-11)"
affects: [27-09 detect CLI, 27-10 SKILL.md and prompt rendering]

# Actuals (#2632): chars/4 over the git diff of the four files this plan changed (41571 bytes)
actuals:
  tokens: 10392
  tasks: 2
  commits: 2
  plan_head_before: 5f2e5c8125b56d462a8d3c243e4c55f1da690ffd
  plan_head_after: c4f685df05aca5d4d5b08a4d31f8947774f5286f

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Strategy matrix as data: row dicts with plain-value predicates, a pure selector, one test per row id"
    - "Dedupe by strategy id (lower rank wins), then sort by (rank, matrix order), keep at most three"

key-files:
  created:
    - skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py
    - tests/test_ai_kit_spec_goal_prompt_matrix.py
  modified:
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "A user-requested goal or loop whose primitive is missing is never emitted; it is reported in `dropped` with a reason."
  - "The loop and goal strategies take the highest-rank non-absent primitive of their kind (ties: first in list); a loop on rank 0 says it dies with the session."
  - "M09 (plain) is a fallback that fires only when no other row fired; its primitive is the OS-timer row when the table has one."
  - "must_outlive and provable are derived: outlive for more than one phase or plan or unattended work; provable when e2e exists and no mockup is involved."

patterns-established:
  - "Property sweep over scope x request x host table x derived flags, with one invariant per test."
  - "Non-vacuity check: broken copies of the module in a git-ignored scratch directory, each caught by at least one test."

requirements-completed: []  # GPS-01 selector logic is delivered; the detect CLI that calls it lands in 27-09 (same precedent as 27-01 to 27-04).

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 05: Strategy matrix as data, with one test per row and property tests Summary

**A pure strategy selector: a tuple of rule rows (M01 to M11l) returns one to three ranked strategies with exactly one recommended, names the loop primitive by survival rank, and derives must-outlive and provable from the work**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 2 of 2 completed
- **Files created:** 2; **files modified:** 2 (test-group listings only)

## Accomplishments
- `RULES` holds the matrix as data: scope kinds, the user request, the needed primitive kind, must-outlive, provable, and a fallback flag. Row ids are the test names.
- `select` fires every matching row, dedupes by strategy id (lower rank wins), sorts by (rank, matrix order), keeps at most three and marks the first `recommended`. A requested goal or loop with no primitive appears in `dropped`.
- `OpenGSD` always yields `autonomous`; `/goal` is never produced without a non-absent goal primitive.
- `wake_primitive` picks the highest-rank loop-capable row (`loop`, `schedule`, `wake`, `os-timer`) and labels it `unverified` unless that row is `available`.
- `derive` computes `must_outlive` (count above one, or unattended) and `provable` (e2e present and no mockup) without asking.
- 31 tests: `TestRows` (13, one per row id), `TestWake` (3), `TestDerive` (6), `TestProperties` (9).

## Task Commits

1. **Task 1: RULES, select and derive with one test per row** - `0f5d377` (feat)
2. **Task 2: property tests over the whole input space** - `c4f685d` (test)

**Plan metadata:** recorded in the docs commit that adds this file (see the completion report).

## Files Created/Modified
- `skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py` - `MatrixInputs`, `RULES`, `select`, `wake_primitive`, `derive` (stdlib only; no I/O)
- `tests/test_ai_kit_spec_goal_prompt_matrix.py` - 31 tests: row, wake, derive and property classes; hand-built primitive tables; no real host binary
- `Makefile`, `.pre-commit-config.yaml` - test-group listings regenerated with `tools/gen_test_groups.py` (the new module added to the unit group)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint] Ruff and pylint findings in the Task 1 files, fixed before the commit**
- **Found during:** Task 1, before its commit
- **Issue:** a nested `if` (SIM102), two over-long lines in the test module (E501), and pylint E1136 "unsubscriptable" on a `None`-able best primitive, which pylint could not narrow through `or`.
- **Fix:** a single `if`; shorter lines; `_best` now uses `max(..., default=None)`, which keeps the first primitive on a rank tie.
- **Commit:** `0f5d377`

### Plan-shape changes (documented, not treated as bugs)

**2. Tie-order test uses a synthetic RULES tuple.** The plan asked for two primitive tables that produce equal ranks. Ranks come from the rows, not from the primitives, and no two live rows can fire together with equal rank for one input. `test_ties_keep_matrix_order` patches `gp_matrix.RULES` with three equal-rank rows and checks both orders.

**3. The M09 reason wording.** The plan says "no goal, loop or schedule primitive". An OS timer counts as loop-capable here, and M09 can fire with an OS timer present when the work does not need to outlive one session. The reason therefore reads "no strategy fits this host and work; the plain prompt relies on the OS-timer wake (flagged, unverified)", and it names "no OS-timer row on this host" when the table has none.

**4. Property tests were written after the selector.** Task 2 had no red phase, because the selector already existed when its tests were added. Non-vacuity was checked instead: broken copies of the module were run against the tests in a git-ignored scratch directory (`tmp/p27/`, removed afterwards). Six mutants were each caught by at least one test: a dedupe that keeps the worst rank, a reversed tie order, a goal row with no goal requirement, the OpenGSD autonomous request removed, the dropped list removed, and no recommendation marked. One mutant survived: a dedupe that keeps the later row on an equal rank. No input of the shipped matrix has an equal-rank duplicate, so that mutant is equivalent for this matrix and no test should pin it.

**5. Verify command for pyright.** The plan's `uv run pyright ... | tail -n 3 | grep -q '0 errors'` exits 1 as written, because pyright prints a version-update banner after its summary line. Run without the `tail`, pyright reports `0 errors, 0 warnings, 0 informations`. The code is clean; the command is not. The same issue was noted in 27-04.

### Process notes

**6. Branch and commit namespace.** The commits are on `gsd/v1.3-curated-config-v2`, the phase branch this worktree was assigned to. The protected-branch check passed (`false`). The agent-branch allow-list in the commit protocol was not applied, because this prompt has no `<sequential_execution>` block. The same choice was made for 27-02 to 27-04 under orchestrator instruction.

**7. Pre-commit hooks.** Each commit ran ruff, pylint, py-compile and the stash-and-restore wrapper. All passed; no `--no-verify`.

**8. Requirements.** GPS-01 is in the frontmatter. The selector logic is delivered here, but the detect CLI that reads the matrix does not exist yet, so `requirements-completed` is empty (same precedent as 27-01 to 27-04).

## Known Stubs

None. `gp_matrix.py` has no placeholder values and no unwired data source.

## Threat Flags

None. The module is pure: no subprocess, file, network or auth code. Its only inputs are the primitive dicts passed in.

## Open Gaps (recorded in `.planning/WINDOWS.md`)

- **A user request for `autonomous` on a non-OpenGSD scope has no row.** `superpowers`, `none` and `gsd-unproven` have no autonomous row except M08 (which fires for `gsd-unproven`). A request for `autonomous` on `superpowers` or `none` is silently ignored, not listed in `dropped`. The SPEC strategy list does not cover it. The planner or user should decide whether it is a strategy or a dropped request.

## Unverified Items

- **Contract check with the real host table builder, rows absent.** `gp_host.build_primitives(None, ...)` with fake `Seen` values, fed into `select` for claude, codex, opencode and cursor, gave the expected shapes: codex's unverified `/goal` is labelled `unverified` (M05 or M11g), a host with no goal gets `dropped: goal`, and `wake_primitive` gives `None` for codex. The matrix rows from `ai-kit-session-wake matrix --json` were not supplied, so the claude loop rows were not exercised with real data. This check ran in a scratch shell and is not committed.
- **No CLI yet.** `detect` and `render` do not call the selector; the wiring lands in 27-09 and 27-10.
- **Test runs.** `tools/run_unittest_parallel.py --group unit --group arch` passed 68/68 modules in 37 seconds, including `tests.test_arch` (66 tests) and `tests.test_gate_scope`. `tests.test_ai_kit_spec_goal_prompt_matrix` passed 31/31. ruff check and format, pylint (10.00 on `skills/ai-kit-spec-goal-prompt/scripts`), pyright (0 errors) and vulture at 80% confidence are clean on the new files. `make validate`, `make test` and `make e2e-test` were not run as whole targets; the pre-commit hooks ran on each commit.

## Self-Check

- Created files exist: `skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py`, `tests/test_ai_kit_spec_goal_prompt_matrix.py`.
- Commits `0f5d377` and `c4f685d` are on the branch with `feat(27-05):` and `test(27-05):` subjects.
- `commits: 2` was measured as `git rev-list --count 5f2e5c8...HEAD` (ledger base) before this docs commit.
