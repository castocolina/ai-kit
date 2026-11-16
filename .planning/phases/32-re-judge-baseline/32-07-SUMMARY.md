---
phase: 32-re-judge-baseline
plan: 07
subsystem: testing
tags: [skill-judge, judge-report, verdict-records, check-dogfood, stdlib]

requires:
  - phase: 32-re-judge-baseline
    provides: "tools/judge_loop.py prompt, ingest, check (32-01); pool and count (32-04); check_dogfood (32-02)"
provides:
  - "tools/judge_loop.py report: REJUDGE.md rendered from the records only (no git, no clock, no path)"
  - "Full check: every round validated, round cap, complete refutations only, worst judge decides the bar, judge counts recomputed, byte-compared report, --gate and --require-current"
  - "tools/check_dogfood.py check_judge_records: runs the checker on .planning/judge on every push"
affects: [32-08 baseline judge run, 32-09 publish records]

actuals:
  tokens: 16652
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Report is a pure function of the records; check compares a fresh render byte for byte"
    - "One judge order (judge_order) shared by the report rows and every worst_record call"
    - "Refutations count only when finding id, location, command and observed output are present and the id is a finding of that judge's verdict"

key-files:
  created: []
  modified:
    - tools/judge_loop.py
    - tests/test_judge_loop.py
    - tools/check_dogfood.py
    - tests/test_check_dogfood.py
    - AGENTS.md
    - README.md

key-decisions:
  - "check and render_report share one loader (load_round) that refuses a record missing any RECORD_KEYS key with a JudgeLoopError naming the file"
  - "The bar is decided by the worst judge: lowest bar rank, then lowest percent, then earliest in judge_order"
  - "Round cap: more than three rounds in one loop is a note, and a problem with --gate; the count is per skill per loop"
  - "A latest loop whose last round holds no verdict is the problem 'not judged' in every mode and gives no line"
  - "check-dogfood treats a missing .planning/judge as a note, never a problem"

patterns-established:
  - "Every check problem names the skill, round and judge; check-dogfood prefixes judge-record problems with 'judge records: '"

requirements-completed: [JDG-02, JDG-08, JDG-04, JDG-01]

duration: not recorded (no start timestamp captured for this plan)
completed: 2026-11-07
status: complete

commits: 3
plan_head_before: c2faec548a3bad0053b2d0c3f96d40e7d878cd56
plan_head_after: ae4fb61ed09779ae01a8b28a9fc9084109de2ff1
---

# Phase 32 Plan 07: Re-judge report and full records checker Summary

**REJUDGE.md is generated from the verdict records alone, and the checker re-validates every round, applies only complete refutations, lets the worst judge decide the bar, recomputes each judge count, and fails a push on any byte or number that differs**

## Performance

- **Duration:** not recorded (no start timestamp captured for this plan)
- **Tasks:** 3 planned, 3 commits (two feature commits, one fix commit)
- **Files modified:** 6

## Accomplishments

- `report RECORDS` writes `REJUDGE.md`: judged skills (batch, loop, rounds, judges, worst percent and grade, critical, high, refuted, bar, spread, digest), verdicts with lane status and substitute reasons, judge count inputs, the judge pool per loop, excluded skills, the 120-point history table, and refuted findings.
- `check` validates every record of every round (exact judge string, file name equals the judge slug, verdict pin and arithmetic, judge and skill equal the record's), counts rounds per skill per loop with the cap, applies refutations, recomputes each count through `final_count(deterministic_count(...))`, and compares `REJUDGE.md` byte for byte.
- `check --gate` fails an unmet bar or an over-cap loop; `--require-current` fails a stale digest.
- A record missing a key raises `JudgeLoopError` naming the file (`<path>: not a judge record (missing verdict)`), never a `KeyError` or traceback.
- `check_judge_records` in check-dogfood runs the checker on `.planning/judge`; a missing folder is a note.
- AGENTS.md and README describe the judge-records check and `tools/judge_loop.py`'s subcommands.

## Task Commits

1. **Tasks 1 and 2: report, full checker and their tests** - `2cf3014` (feat)
2. **Task 3: check-dogfood judge-records check, docs** - `853d7fe` (feat)
3. **Fix: narrow the pool type so `make pyright` passes** - `ae4fb61` (fix; its own logical change)

## Files Created/Modified

- `tools/judge_loop.py` - `ROUND_CAP`, `RECORD_KEYS`, `loop_key`, `latest_loop`, `round_numbers`, `load_round`, `load_refutations`, `refuted_ids`, `judge_bar`, `judge_order`, `worst_record`, `render_report`, the full `check` and its helpers; CLI `report`. The 32-01 interim `_loop_key` is now the public `loop_key`.
- `tests/test_judge_loop.py` - helpers `full_verdict`, `make_record`, `write_records`, `demo_inputs`, `demo_pool`; `ReportFixture`, `TestReport` (6 tests), `TestCheck` (15 tests); `TestTracer` fixture extended with `inputs.json` and `loops/32.json`, and a `report` run before each `check`.
- `tools/check_dogfood.py` - `JUDGE_LOOP_REL`, `_judge_loop` (loaded by path, registered in `sys.modules`), `check_judge_records`, composed in `main()` after the JDG-04 check.
- `tests/test_check_dogfood.py` - `TestJudgeRecords` (3 tests with a fake checker).
- `AGENTS.md`, `README.md` - the Testing bullet, the Commands line, the Development comment and the skill-judging paragraph.

## Decisions Made

- The three tracer/report/check cases in the plan are covered as written; the 80.0 / 79.9 bar boundary, the native substitute tie to the configured judge, and the `not judged` exit 1 are each tested.
- Task 1 and Task 2 share `tools/judge_loop.py` and `tests/test_judge_loop.py`. The staged-tests hook runs the whole module, so a Task-1-only commit would fail on the Task-2 tests. They land as one commit (`2cf3014`).
- `scope.py` puts its per-run temp dir at `<worktree>/tmp/p32/07/run-<run_id>` instead of the system temp dir, as the plan's temp-files rule allows. Everything else in the 29-01 spec is as written.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Long lines blocked the module's lint**
- **Found during:** the pylint and ruff runs before the commit
- **Issue:** one docstring in `tools/judge_loop.py` and two assertion strings in `tests/test_judge_loop.py` exceeded 100 columns
- **Fix:** wrapped and shortened them; committed in `2cf3014`

**2. [Rule 1 - Bug] `make pyright` reported 4 errors**
- **Found during:** the plan's `make pyright`
- **Issue:** `_default_judges` read `pool.get` through a conditional expression whose type pyright could not narrow
- **Fix:** an early `isinstance` check, the same pattern `_pool_lines` uses; committed as `ae4fb61`
- **Verification:** `make pyright` passed; `tests.test_judge_loop` and `tests.test_check_dogfood` ok

**3. [Rule 2 - Missing] A test was missing its `report` call**
- **Found during:** the first run of `tests.test_judge_loop`
- **Issue:** the native substitute test ran `check` before `report`, so `REJUDGE.md` was not found
- **Fix:** added the `report` call in the test; the module then passed (95 tests)

### Process Deviations

- **TDD RED was not captured.** The plan asks for RED evidence before the fix. I wrote the tests and the implementation before running the new tests, so no run was recorded against the pre-change tool. The only failure recorded during the work was the missing `report` call in item 3 above, which was a test bug, not a RED result.
- **Task 1 and Task 2 are one commit** (see Decisions Made).
- **The commit ledger (protocol 0c) was not written before the first commit.** `commits:` is measured with `git rev-list --count c2faec5..HEAD` (base in `tmp/p32/07/base_sha`), which gives 3 for the code commits.

## Verification Results

| Command | Exit | Result |
|---|---|---|
| `scope.py start` | 0 | `start 3469d2b6 <worktree>/tmp/p32/07/run-3469d2b6` |
| `scope.py selftest` | 0 | `selftest ok` |
| `run_unittest_parallel.py tests.test_judge_loop` (after Tasks 1-2) | 0 | ok, 95 tests |
| `run_unittest_parallel.py tests.test_judge_loop tests.test_arch` | 0 | 2/2 modules ok (95, 103 tests) |
| `run_unittest_parallel.py tests.test_check_dogfood tests.test_judge_loop tests.test_rules_docs tests.test_agents_md_links tests.test_arch` (after Task 3) | 0 | 5/5 modules ok (42, 95, 19, 5, 103 tests) |
| `uv run pylint tools/judge_loop.py` | 0 | 10.00/10 |
| `uv run ruff check` on `tools/judge_loop.py` and `tests/test_judge_loop.py` | 0 | All checks passed |
| `make pyright` (first run) | 2 | 4 errors in `tools/judge_loop.py` (fixed in `ae4fb61`) |
| `make pyright` (after fix) | 0 | Passed |
| `scope.py test` (`make test`, TMPDIR inside the worktree) | 0 | unit 102/102 modules; unit-uv 1/1; integration 8/8; e2e 25/25; `tests/test_install.sh` 48 passed, 0 failed; arch 1/1 (103 tests) |
| `make check-dogfood` in the worktree | 1 | Expected in a worktree: no checkout-local gsd-core, so the flow, lens and edge checks are "not checked" notes and the no-write guard skips its three tests. No `judge records:` line appeared; the judge-records check printed its note `judge records not checked: no .planning/judge`. The orchestrator runs the full gate in the main checkout. |

The commit-stage hooks ran on each commit: ruff, pylint, py-compile and the staged tests passed (2 modules, then 42 modules, then 3 modules).

## Issues Encountered

- The no-write guard of check-dogfood skips in a worktree (see the table). This is expected for this plan's checkout, not a failure of the judge-records check.
- The `actuals.tokens` figure is chars/4 over the realized diff (base to HEAD), on the same scale as the plan's estimate. It excludes the reading done before writing.

## Coverage Not Tested

- A refutation that names another judge's finding id (the plan's `F3` case): the code path is the same as the one tested (`refuted_ids` only counts ids of the judge's own verdict), but no test pins that exact case.
- A non-object JSON record (for example a bare list in a round folder) reaches `_load_record_file`'s non-dict branch but no test pins it.
- The `pool`-less loop file path in `judge_order` (a missing `pool` key counts as empty) is exercised only indirectly.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. The report and check read only the records folder and the tracked skill files; no git, clock or absolute path enters `REJUDGE.md`.

## Self-Check

- `tools/judge_loop.py`, `tests/test_judge_loop.py`, `tools/check_dogfood.py`, `tests/test_check_dogfood.py`, `AGENTS.md`, `README.md` are modified and committed.
- Commits `2cf3014`, `853d7fe`, `ae4fb61` are ancestors of HEAD.

---
*Phase: 32-re-judge-baseline*
*Completed: 2026-11-07*
