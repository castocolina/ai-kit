---
phase: 32-re-judge-baseline
plan: 01
subsystem: testing
tags: [skill-judge, judge-prompt, verdict-records, stdlib, pyright, ruff]

requires: []
provides:
  - "tools/judge_loop.py: prompt (judge prompt, manifest and probe), ingest (lane verdict records), check (one lane end to end)"
  - "Judge prompt that embeds the installed skill-judge byte for byte, with one test-module reading for every skill"
  - "Record and manifest layout: one record per (loop, skill, round, judge), attempts kept, verdicts never overwritten"
  - "validate_verdict with the rubric pin, arithmetic, grade bands, finding shape and below-max coverage"
  - "Native judge agent at effort xhigh in its frontmatter; README row says so"
affects: [32-04 pool/count, 32-07 report/full check, 32-08 baseline judge run, 32-09 publish records]

actuals:
  tokens: 21992
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Manifest pins (rubric_version, spec_sha, skill digest) recorded at prompt time; ingest refuses a verdict under another pin"
    - "Probe prompt with one 8-hex code after each embedded file; the expected answer is one word"
    - "Lane outcome recorded as attempts; a failed lane writes no verdict and never a round"

key-files:
  created:
    - tools/judge_loop.py
    - tests/test_judge_loop.py
  modified:
    - tests/test_arch.py
    - Makefile
    - .pre-commit-config.yaml
    - agents/ai-kit-judge.md
    - README.md

key-decisions:
  - "Judge prompt rules 1 to 7 are fixed text; the module list comes from staged_mapper.covering_modules, or the line 'no script test found'"
  - "A skill ships runnable code when a tracked .py/.mjs/.cjs/.js/.sh file is at its root or under scripts/, or a top-level folder holds __init__.py; .txt templates and references/ never count"
  - "ingest refuses (exit 1, nothing written) a verdict whose judge, skill or pin differs from the lane's manifest, and a record that already holds a verdict or belongs to another judge"
  - "ingest records a non-usable lane as an attempt with its error and no verdict (exit 0); a native lane is usable with its lane.out and a note, no status line"
  - "check uses exact string compare for --judges; a record with a null verdict is skipped for validation and for the summary line; a round with no verdict is 'not judged'"
  - "Usage rules through argparse exit 2: --probe takes no --skill/--loop/--round; --replaces and --reason go together"
  - "The probe answer is AIKIT-SENTINEL plus one code per embedded file, joined with hyphens (one word, and a lane that drops part of the package cannot answer it)"

patterns-established:
  - "Tool functions take root explicitly; find_root never derives it from the module's path"
  - "Skill names must match SAFE_SKILL before any git pathspec or record path is built"

requirements-completed: [JDG-01, JDG-02]

duration: not recorded (no start timestamp captured for this plan)
completed: 2026-11-07
status: complete
commits: 4
plan_head_before: d2d6dd6fdd1a84bc5d163f68811a575fa2c2d087
plan_head_after: aed3b70bc2ddf3fb33c13c757606b08386c389cc

coverage:
  - id: D1
    description: "Judge prompt: embeds skill-judge SKILL.md, rubric, cited spec files and schema byte for byte, with the fixed rules and the module list; manifest records digests and pins"
    requirement: "JDG-01"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestPrompt"
        status: pass
    human_judgment: false
  - id: D2
    description: "Probe prompt: one code per embedded file after its END marker; expected answer is one word"
    requirement: "JDG-02"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestPrompt::test_probe_answer_carries_one_code_per_embedded_file"
        status: pass
    human_judgment: false
  - id: D3
    description: "Ingest: records a lane's verdict with its manifest and status; refusals (judge, skill, pin, overwrite, slug) and attempts for failed lanes"
    requirement: "JDG-02"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestIngest"
        status: pass
    human_judgment: false
  - id: D4
    description: "Check: one lane end to end prints the skill line, reports a stale digest after an edit, and refuses a judge outside the list"
    requirement: "JDG-02"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestTracer"
        status: pass
    human_judgment: false
  - id: D5
    description: "Verdict validator: exact keys, arithmetic, grade bands at 80.0 and 79.9, findings, below-max coverage, duplicate ids and the pin"
    requirement: "JDG-02"
    verification:
      - kind: unit
        ref: "tests/test_judge_loop.py#TestVerdictValidation"
        status: pass
    human_judgment: false
  - id: D6
    description: "Native judge agent requests xhigh effort through its frontmatter"
    requirement: "JDG-01"
    verification:
      - kind: other
        ref: "grep -c '^effort: xhigh$' agents/ai-kit-judge.md (prints 1); tests.test_setup ok"
        status: pass
    human_judgment: true
    rationale: "Whether Claude Code honours effort: in a user-level agent file is unobserved (research open item 1, D-10); the report must label it unverified until a run shows it"
---

# Phase 32 Plan 01: Judge loop prompt, ingest and check Summary

**judge_loop.py builds per-judge prompts that embed the installed skill-judge byte for byte, records each lane's outcome against its manifest pins, and checks the records end to end**

## Performance

- **Duration:** not recorded (no start timestamp captured for this plan)
- **Started:** not recorded
- **Completed:** 2026-11-07
- **Tasks:** 3 planned (4 commits: 3 feature commits and one typing fix)
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- `tools/judge_loop.py` (stdlib only) with `prompt`, `ingest` and `check`; `prompt --probe` writes the probe prompt and its one-word expected answer
- A judge prompt embeds SKILL.md, the rubric, every spec file the rubric's source column cites (anchors stripped, first-appearance order) and the verdict schema, then rules 1 to 7; two skills' prompts differ only in the name and the module line
- Each prompt writes `manifest.json` with the skill digest, the rubric pin, each embedded file's sha256, the module list, `ships_code` and the prompt sha256
- `ingest` joins the manifest, the lane's last `AIKIT-XAI ` line and the verdict line into one record at `verdicts/<loop>/<skill>/r<N>/<judge slug>.json`; refusals, attempts and null-verdict records as the plan states
- `check` prints the skill line (`loop`, `round`, `rounds`, `judges`, `worst`, `critical`, `high`, `digest current|stale`) and the judge-list and stale-digest problems
- `validate_verdict` checks keys, arithmetic, grade bands (80.0 is B, 79.9 is C), finding shape, unique finding ids and a finding for every below-max dimension
- `agents/ai-kit-judge.md` carries `effort: xhigh`; the README row says so

## Task Commits

1. **Task 1: One skill, one judge, end to end** - `9e16bce` (feat)
2. **Task 2: Prompt contents, probe prompt, ingest rules and validator edges** - `b7b2596` (feat)
3. **Task 3: Native judge lane at xhigh effort and README row** - `9fedb83` (feat)
4. **Fix: pyright errors found by the plan's `make pyright`** - `aed3b70` (fix; a separate logical change)

**Plan metadata:** this SUMMARY commit (docs; follows the four commits above)

## Files Created/Modified

- `tools/judge_loop.py` - the tool: root resolver, skills roots and judge lookup, skill files and digest, pin reader, embedded files, module list, prompt and probe builders, manifest writer, status and verdict parsers, validator, finding path check, ingest, check, CLI
- `tests/test_judge_loop.py` - `TestTracer`, `TestPrompt`, `TestIngest`, `TestVerdictValidation`, `TestUsage` (34 tests; fixture skill-judge package and temp git repositories, no host CLI, no `.planning/`)
- `tests/test_arch.py` - `"tools/judge_loop.py"` added to `LOOKUP_COPIES` so its `SKILLS_ROOTS` literal is drift-checked against jev's reference
- `Makefile`, `.pre-commit-config.yaml` - regenerated listings from `tools/gen_test_groups.py` (the new module in the unit group; the generator also added `tests.test_arch` to the `unittest (core)` entry, which the committed listing lacked)
- `agents/ai-kit-judge.md` - frontmatter `effort: xhigh`
- `README.md` - the `ai-kit-judge` row names Opus at xhigh effort set in its frontmatter

## Decisions Made

- The module list is `staged_mapper.covering_modules(build_index(root), "skills/<name>/SKILL.md")`, sorted; no skill gets an empty list silently
- `check` compares `--judges` as exact strings; a record whose judge is not listed is a problem, not a warning
- A round with records but no verdict prints no summary line and the problem `<skill>: not judged (no verdict in loop <L> round <N>)`
- `--round`/`--loop`/`--skill` checks run through argparse, so a usage error exits 2 as the plan requires
- No 2-4 option choice arose that the plan did not already decide, so no jev call was made in this plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] First commit attempt blocked by ruff and pylint**
- **Found during:** Task 1 commit
- **Issue:** E501 in two lines, UP031 (`%` formatting) in four places, `type(x) is int` checks flagged as unidiomatic, and `_summary` and `_check_skill` over the argument and local limits
- **Fix:** f-strings, `_is_int` helper, `_summary` and `_check_skill` split into helpers; re-staged and committed as the same logical change
- **Files modified:** `tools/judge_loop.py`, `tests/test_judge_loop.py`
- **Verification:** ruff and pylint hooks passed; `tests.test_judge_loop` ok
- **Committed in:** `9e16bce`

**2. [Rule 1 - Bug] `make pyright` reported 15 errors after Task 3**
- **Found during:** the plan's last step (`make pyright`, exit 2)
- **Issue:** Optional narrowing in the test helpers (`ModuleSpec | None`, `_record()` returning `None`), an inferred dict type in `_load_record` (`attempts` as `None | list`) and a possibly-`None` `loop` in `_check_skill`
- **Fix:** `assert` on the module spec; `_record_path` plus assertions on existence; `_new_record` with a `dict[str, Any]` annotation; the `loop is None` check moved ahead of the round lookup
- **Files modified:** `tools/judge_loop.py`, `tests/test_judge_loop.py`
- **Verification:** `make pyright` exit 0 (`Passed`); `tests.test_judge_loop` 34 ok; `tests.test_arch` 103 ok
- **Committed in:** `aed3b70`

**Total deviations:** 2 auto-fixed (1 blocking lint, 1 pyright bug)
**Impact on plan:** Both fixes are behaviour-neutral; the one `make test` of this plan ran at `9fedb83`, before fix `aed3b70`, so the fix was verified by a targeted run (`tests.test_judge_loop`, `tests.test_arch`) and by the commit hooks. The plan's single `make test` was not repeated.

### Process deviation

- The commit-ledger protocol (0c, `gsd-plan-head-before-32-01`) was not written before the first task commit. `commits:` here is measured with `git rev-list --count d2d6dd6..HEAD` (base recorded in `tmp/p32/01/base_sha`), which gives 4.

## Verification Results

| Command | Exit | Result |
|---|---|---|
| `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p32/01/scope.py start` | 0 | `start f2934832 /tmp/ai-kit-p32-run-01-f2934832` |
| `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p32/01/scope.py selftest` | 0 | `selftest ok` |
| `tools/run_unittest_parallel.py tests.test_judge_loop tests.test_arch tests.test_gate_scope` (Task 1 verify) | 0 | 3/3 modules ok (6, 103, 57 tests) |
| `tools/run_unittest_parallel.py tests.test_judge_loop` (Task 2 verify, after its fixes) | 0 | ok, 34 tests |
| `tools/run_unittest_parallel.py tests.test_setup tests.test_judge_loop` (Task 3 verify) | 0 | 2/2 modules ok (481, 34 tests) |
| `tools/run_unittest_parallel.py tests.test_judge_loop tests.test_arch tests.test_gate_scope tests.test_setup` (final HEAD) | 0 | 4/4 modules ok (34, 103, 57, 481 tests) |
| `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p32/01/scope.py test` (`make test`) | 0 | unit 101/101 modules; unit-uv 1/1; integration 8/8; e2e 25/25; `tests/test_install.sh` 48 passed, 0 failed; arch 1/1 |
| `AI_KIT_REFUSE_REAL_HOME=1 make pyright` | 2 then 0 | first run 15 errors (fixed in `aed3b70`); final run `Passed` |
| ruff and pylint (pre-commit, on the commits) | 0 | Passed on `9e16bce`, `b7b2596`, `aed3b70` |
| `grep -c -i referee tools/judge_loop.py` | 0 | 0 |
| `grep -c "\.planning" tools/judge_loop.py` | 0 | 0 |
| `grep -c '"tools/judge_loop.py"' tests/test_arch.py` | 0 | 1 |
| `grep -c "tests.test_judge_loop" Makefile` | 0 | 1 |
| `grep -c "^effort: xhigh$" agents/ai-kit-judge.md` | 0 | 1 |
| `grep -c "AIKIT-SENTINEL-" tools/judge_loop.py` | 0 | 2 |
| `grep -c "PROBE PART" tools/judge_loop.py` | 0 | 3 |
| `grep -c "no script test found" tools/judge_loop.py` | 0 | 1 |

The final `scope.py close` (after this SUMMARY commit) is reported in the return message, not here.

## Issues Encountered

- The first commit attempt was blocked by lint (see deviation 1); fixed before the commit landed.
- `make pyright` failed after Task 3 (see deviation 2); fixed in a separate commit.
- The rubric-v4 interim `check` covers one loop and one round; `--gate`, `--require-current`, `pool`, `count`, `report` and the refutation records belong to plans 04 and 07, as the plan states.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. Lane output is parsed as data only (the verdict line is `json.loads`, never executed); finding paths are resolved and confined under the root; skill names are checked against `SAFE_SKILL` before any git pathspec; records are written atomically.

## Requirements Note

`requirements-completed` lists JDG-01 and JDG-02 as the plan declares them. Those requirements are only partly met by this plan (the report and the full checker come in plans 07 to 09), and later plans declare them too, so REQUIREMENTS.md was not marked complete here; the shared-ID gate leaves that to the orchestrator.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 32-04 (`pool`, `count`) and 32-07 (`report`, full `check`, refutation records) can build on `judge_loop.py` without changing its record layout.
- The probe prompt is ready for 32-04's `probe_result`, which compares the lane's stripped stdout with the `token` file.
- The native judge lane's effort is requested but not observed; the report must label it unverified until a run shows it.

## Self-Check: PASSED

- Files `tools/judge_loop.py` and `tests/test_judge_loop.py` are tracked at HEAD.
- Commits `9e16bce`, `b7b2596`, `9fedb83` and `aed3b70` are ancestors of HEAD.

---
*Phase: 32-re-judge-baseline*
*Completed: 2026-11-07*
