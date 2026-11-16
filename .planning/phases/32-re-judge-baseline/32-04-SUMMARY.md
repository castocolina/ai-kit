---
phase: 32-re-judge-baseline
plan: 04
subsystem: testing
tags: [skill-judge, judge-pool, judge-count, jev, probe, stdlib]

requires:
  - phase: 32-re-judge-baseline
    provides: "tools/judge_loop.py prompt, ingest, check and the probe prompt (plan 32-01)"
provides:
  - "tools/judge_loop.py pool: probe results decide the judge pool; substitutes recorded with reasons"
  - "tools/judge_loop.py count: deterministic judge count per skill, plus an advisory jev score item built from fixed words"
  - "Loop record <records>/loops/<loop>.json with the pool and counts keys"
affects: [32-08 baseline judge run, 32-07 report and full check]

actuals:
  tokens: 26042
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Probe usable only on a clean exit whose stdout equals the expected one-word answer"
    - "Judge count: deterministic triggers first; jev asked only when they give one; jev never lowers two to one"
    - "The jev item carries fixed instructions, fixed levels and word bands computed from numbers"

key-files:
  created: []
  modified:
    - tools/judge_loop.py
    - tests/test_judge_loop.py

key-decisions:
  - "A substitute is a native fill-in only; configured judges that fail their probe are recorded under probes with their reason, not as substitutes"
  - "numstat rejects a base that is not 7 to 40 hex digits before any git call, and a skill name that fails SAFE_SKILL"
  - "change_words classifies references first, then evals, then scripts (code suffix, not in references or evals)"
  - "count re-counts only the chosen skills and merges them into the existing counts dict; pool and other keys are kept"
  - "A missing jev client is recorded as jev unavailable: no jev client found, via the same ask path as a jev error"

patterns-established:
  - "Judge pool and count records keep the inputs they were computed from (probe status lines, last_v4) for later audit"

requirements-completed: [JDG-06, JDG-01]

duration: not recorded (no start timestamp captured for this plan)
completed: 2026-11-07
status: complete
commits: 3
plan_head_before: 767a07748aecb1f73a4d4aacb2dddf5e4ef2f27d
plan_head_after: f979405

coverage:
  - id: D1
    description: "Pool: probe results in configured order; first two usable judges form the pool; one usable judge plus native; native alone when none usable or the list is empty; every substitute with a reason"
    requirement: "JDG-01"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestPool"
        status: pass
    human_judgment: false
  - id: D2
    description: "Probe usability: exact one-word answer, status=ok, exit=0, tree=clean; each unusable reason named"
    requirement: "JDG-01"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestPool::test_unusable_probe_reasons"
        status: pass
    human_judgment: false
  - id: D3
    description: "Count: deterministic triggers (no verdict, critical or high finding, last percent within 7.0 of 80) and the 72.9/73.0/87.0/87.1 boundaries"
    requirement: "JDG-06"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestCount"
        status: pass
    human_judgment: false
  - id: D4
    description: "jev score item: pinned exact text, fixed words only, no path or skill name; level 2 or more raises one to two; own reasoning, unavailable jev and an unresolvable base keep one with the reason"
    requirement: "JDG-06"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestCount::test_jev_item_is_pinned_to_fixed_words"
        status: pass
      - kind: unit
        ref: "tests/test_judge_loop.py#TestCountGit"
        status: pass
    human_judgment: false
  - id: D5
    description: "Count record: jev asked/item/level/note, and final_count reproduces the recorded count and reasons"
    requirement: "JDG-06"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestCountGit::test_jev_level_two_raises_one_to_two_and_round_trips"
        status: pass
    human_judgment: false
  - id: D6
    description: "CLI pool and count write the loop record, keep the other keys, refuse a skill in both maps and an unknown --skill"
    requirement: "JDG-01"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestPool::test_cli_pool_writes_the_loop_record_and_keeps_other_keys"
        status: pass
      - kind: unit
        ref: "tests/test_judge_loop.py#TestCountGit::test_cli_count_refuses_a_skill_in_both_maps_and_an_unknown_skill"
        status: pass
    human_judgment: false
---

# Phase 32 Plan 04: Judge pool and judge count Summary

**Judge pool from probe results with recorded substitutes, and a per-skill judge count (one or two) from deterministic triggers plus a jev score item built only from fixed words**

## Performance

- **Duration:** not recorded (no start timestamp captured for this plan)
- **Started:** not recorded
- **Completed:** 2026-11-07
- **Tasks:** 2 planned (3 commits: 2 feature commits and one pyright fix)
- **Files modified:** 2 (`tools/judge_loop.py`, `tests/test_judge_loop.py`)

## Accomplishments

- `pool` subcommand: each judge's probe lane is usable only on `status=ok`, `exit=0`, `tree=clean` and an exact echo of the expected answer; the first two usable judges form the pool, else one usable judge plus the native id, else the native id alone; the result is written under `pool` in `<records>/loops/<loop>.json`
- `count` subcommand: the deterministic count runs first; jev is asked only when it gives one judge; the jev item holds fixed instructions, fixed level texts and word bands from the percent distance and the change size, never a path or skill name; a level of 2 or more raises one to two, and nothing lowers two to one
- Every jev outcome is recorded: the item, whether it was asked, the level, and the note; `final_count` reproduces the recorded count and reasons from them
- `TestPool` (13 tests) and `TestCount` / `TestCountGit` (37 tests) cover every behavior line of the plan, using fixture judge ids and fake jev clients only

## Task Commits

1. **Task 1: judge pool end to end** - `b3fe65f` (feat)
2. **Task 2: judge count, deterministic triggers and the jev score item** - `ba56d54` (feat; TDD, see deviations)
3. **Fix: pyright error found by the plan's `make pyright`** - `f979405` (fix; a separate logical change)

## Files Created/Modified

- `tools/judge_loop.py` - `probe_result`, `choose_pool`, `read_loop_file`, `update_loop_file`; `deterministic_count`, `percent_words`, `change_words`, `jev_item`, `jev_level`, `final_count`, `ask_jev`, `find_jev_client`, `numstat`, `count_skill`, `load_inputs`; CLI `pool` and `count`; constants `JEV_INSTRUCTIONS`, `JEV_LEVELS`, `BAR_TENTHS`, `BAND_TENTHS`; exception `JevUnavailable`
- `tests/test_judge_loop.py` - `write_probe`, `ANSWER`, `NATIVE`, `_last`, `ladder_answer`, `FakeAsk`; classes `TestPool`, `TestCount`, `TestCountGit`

## Decisions Made

- A substitute is the native id only. Configured judges that fail their probe are recorded under `probes` with their reason; they are not listed as substitutes.
- `numstat` refuses a base that is not 7 to 40 lowercase hex digits before any git call, and a skill name that fails `SAFE_SKILL`; git is called with argv lists and `--` before the pathspec.
- `change_words` puts a file under `references/` first, then under `evals/`; `scripts` counts code-suffix files outside both.
- `count` re-counts only the chosen skills and merges them into the existing `counts` dict, so a batch run keeps the other skills and the `pool` key.
- No jev call was made while executing. The choices that came up (substitute semantics, file classification, merge scope) are settled by the plan's behavior examples, so no jev choice was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-commit ruff and pylint blocked the first commit attempts (E501)**
- **Found during:** Task 1 and Task 2 commits
- **Issue:** one docstring in each task exceeded 100 columns (`probe_result`, `jev_level`, `final_count`) and one test call was too long
- **Fix:** shortened the docstrings and split the call; re-staged and committed the same logical change
- **Commit:** `b3fe65f`, `ba56d54` (the landed commits contain the fix)

**2. [Rule 1 - Bug] `make pyright` reported one error after `make test`**
- **Found during:** the plan's last step (`make pyright`, exit 2)
- **Issue:** the `_last` test helper inferred `judged_at` as `str`, but the count tests pass `None`
- **Fix:** annotated the parameter `str | None`
- **Commit:** `f979405` (its own logical change)
- **Verification:** `make pyright` exit 0 (`Passed`); the commit hook re-ran `tests.test_judge_loop` (74 ok)

**Total deviations:** 2 auto-fixed (1 blocking lint, 1 pyright type annotation).

### Process Deviations

- **TDD RED was not committed as its own `test(32-04)` commit.** The pre-commit `staged-tests` and ruff hooks would reject a commit of failing tests, and `--no-verify` is forbidden. Instead, RED was captured by running the Task 2 tests against placeholder stubs (functions that returned `None`, with the constants and `JevUnavailable` real): `tests.test_judge_loop` exited 1 with 74 tests run, and the target `TestCount.test_no_verdict_gives_two` failed on its own assertion (`AssertionError: None != (2, ['no rubric-v4 verdict'])`). Other RED failures were `TypeError` from the stubs and the CLI tests exiting 2 with `invalid choice: 'count'`. GREEN followed by implementing the functions; the stubs were then replaced.
- **The `gsd_run check tdd-red-evidence` classifier was not run.** The full raw RED report was not captured intact, so no record could be built from it. The RED evidence above is the semantic record only.
- **The commit ledger (protocol 0c) was not written.** The Write tool refused the shared `.git/worktrees/...` path. Commits are measured from `tmp/p32/04/base_sha` (`767a077`), as in 32-01: `git rev-list --count 767a077..HEAD` = 3.

## Verification Results

| Command | Exit | Result |
|---|---|---|
| `scope.py start` | 0 | `start 5dcfc5f0 /tmp/ai-kit-p32-run-04-5dcfc5f0` |
| `scope.py selftest` | 0 | `selftest ok` |
| `run_unittest_parallel.py tests.test_judge_loop` (after Task 1) | 0 | ok, 47 tests |
| `run_unittest_parallel.py tests.test_judge_loop tests.test_arch` (after Task 1) | 0 | 2/2 modules ok (47, 103 tests) |
| `run_unittest_parallel.py tests.test_judge_loop` (Task 2 RED, stubs) | 1 | 74 tests ran; target assertion failure as recorded above |
| `run_unittest_parallel.py tests.test_judge_loop tests.test_arch` (Task 2 GREEN) | 0 | 2/2 modules ok (74, 103 tests) |
| `scope.py test` (`make test`) | 0 | unit 101/101 modules; unit-uv 1/1; integration 8/8; e2e 25/25; `tests/test_install.sh` 48 passed, 0 failed; arch 1/1 (103 tests) |
| `make pyright` (first run) | 2 | 1 error at `tests/test_judge_loop.py:939` (`judged_at` None), fixed in `f979405` |
| `make pyright` (after fix) | 0 | `Passed` |
| `run_unittest_parallel.py tests.test_judge_loop tests.test_arch` (after `f979405`) | 0 | 2/2 modules ok (74, 103 tests) |
| `grep -c "def choose_pool" tools/judge_loop.py` | 0 | 1 |
| `grep -c "def deterministic_count" tools/judge_loop.py` | 0 | 1 |
| `grep -c -i referee tools/judge_loop.py` | 1 | 0 |
| `scope.py close` | 0 | `leftover (this run):` empty; reported items belong to other sessions (the 32-03 executor's `nap.sh`, its `/tmp/ai-kit-p32-run-03-*` scratch, and the orchestrator); last line `clean` |

`make test` ran at `ba56d54`, before the pyright annotation fix. The fix changes only a type annotation, and the module tests were re-run after it (74 ok, 103 ok).

## Issues Encountered

- A `.venv` appeared in the worktree when the uv-based ruff hook first ran. It is gitignored, and the close check does not count it.
- The `scope.py close` step removes its own empty per-run temp directory and zero-byte `uv-*.lock` files under the system temp dir (`/tmp`). The owner's local rule says "never delete outside `tmp/`". I followed the phase rails, which specify this cleanup, and flag the conflict for the owner's decision.

## Known Stubs

None. The RED-step placeholders were replaced in the GREEN implementation before the first commit that contains them.

## Threat Flags

None beyond the plan's threat model. The jev item holds fixed text and word bands only; `numstat` gates its base and skill inputs before any git call; `ask_jev` runs the client with an argv list and a fixed environment.

## Self-Check

- `tools/judge_loop.py` and `tests/test_judge_loop.py` are tracked at HEAD.
- Commits `b3fe65f`, `ba56d54` and `f979405` are ancestors of HEAD.

## Next Phase Readiness

- Plan 32-08 can call `pool` for the probes and `count` for the inputs in `<records>/inputs.json`; the loop record keys are `pool` and `counts`.
- Plan 32-07's `report` and full `check` read the `counts` entries (`count`, `reasons`, `last_v4`, `jev`).

---
*Phase: 32-re-judge-baseline*
*Completed: 2026-11-07*
