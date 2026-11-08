---
phase: 32-re-judge-baseline
plan: 06
subsystem: testing
tags: [frontmatter, yaml, skills, installer, pyyaml, npm-yaml, unit-tests]

requires:
  - phase: 32-re-judge-baseline
    provides: plan 32-03 (the judge pool and judge count) completed before this wave
provides:
  - Strict frontmatter gate for every SKILL.md and the judge agent the installer lists
  - PyYAML cross-check of the same fixtures and tree (unit-uv group)
  - One-time comparison of the gate against the npm yaml package recorded below (SPEC R8)
affects: [32-VERIFICATION, skill discovery on hosts]

actuals:
  tokens: 11581   # chars/4 over the realized diff (git diff base..HEAD, 46326 chars)
  tasks: 2
  commits: 3      # MEASURED: git rev-list --count c2faec5..HEAD
plan_head_before: c2faec548a3bad0053b2d0c3f96d40e7d878cd56
plan_head_after: f5d7b4b0e6cb85085c91265bbbc9468a1d76ce29

tech-stack:
  added: []
  patterns:
    - "Strict YAML subset parser in a unit test, cross-checked by PyYAML (uv) and the npm yaml package (one-time)"

key-files:
  created:
    - tests/test_skill_frontmatter.py
    - tests/test_skill_frontmatter_pyyaml.py
  modified:
    - tests/test_setup.py
    - tools/run_unittest_parallel.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "The gate is a unit test that reuses tools/setup.py enumerate_entries, so it covers exactly the entries the installer ships"
  - "Two designed-stricter shapes are rejected on purpose: a plain continuation line without a colon and an inline ' #' comment (valid YAML, but the gate refuses them)"
  - "The two narrower guards in tests/test_setup.py were removed, not kept beside the gate"

patterns-established:
  - "Fixture corpus with a per-label subTest and a DESIGNED_STRICTER set that names every intentional gap to PyYAML"

requirements-completed: [JDG-07]

duration: not measured
completed: 2026-11-07
status: complete
---

# Phase 32 Plan 06: Strict frontmatter gate for every installable entry Summary

**Strict frontmatter gate over all 24 skills and the judge agent, cross-checked by PyYAML and the npm yaml package on 27 fixtures with no unexplained disagreement**

## Performance

- **Duration:** not measured
- **Tasks:** 2 planned (plus one pyright fix commit)
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- `tests/test_skill_frontmatter.py` parses every SKILL.md and `agents/ai-kit-judge.md` with a strict YAML subset and checks name and description (1,024-character cap, name = folder, 1-64 lowercase characters). The tree passes with zero problems.
- `tests/test_skill_frontmatter_pyyaml.py` (unit-uv) parses the same fixtures and the tree with PyYAML `safe_load` extended to reject duplicate keys. Its results equal the gate's on every fixture except the two designed-stricter cases.
- The one-time comparison with the npm `yaml` package (2.9.0, from the skills CLI's npx cache) agrees with the gate on 25 of 27 fixtures; the other two are the labelled designed-stricter cases. Zero DIFFERENT.
- The two narrower guards in `tests/test_setup.py` are removed; the other `TestReadFrontmatter` tests stay.

## Task Commits

1. **Task 1: strict frontmatter gate end to end** - `1ca4d44` (test)
2. **Task 2: fixture corpus, PyYAML cross-check, npm comparison** - `8b2511c` (test)
3. **Pyright fix found by the final gate** - `f5d7b4b` (fix)

## TDD evidence (RED before GREEN)

- Task 1 RED: `tests/test_skill_frontmatter.py` written before any parser code. Run before the fix: `=== tests.test_skill_frontmatter: FAILED ... Ran 5 tests ... FAILED (errors=5)`, every error `NameError: name 'parse_strict' is not defined` / `entry_problems` / `entry_files`. GREEN after the parser: `tests.test_skill_frontmatter: ok ... Ran 5 tests`.
- Task 2 RED: the PyYAML module written before its helpers: `ImportError: cannot import name 'DESIGNED_STRICTER' from 'tests.test_skill_frontmatter'`. The gate module before the fixtures: `FAILED (errors=2)`, `NameError: name 'FIXTURES' is not defined` and `name 'DESIGNED_STRICTER' is not defined`. GREEN after the fixture corpus: 7 tests ok; PyYAML module: 3 tests ok under uv.

## R8 comparison with the npm yaml package

Command (run once, not committed): `python3 tmp/p32/06/dump_fixtures.py` then `node tmp/p32/06/yaml_compare.mjs` (exit 0). The script reads the npx cache folder `~/.npm/_npx/ac0ed6aa23b37c1e` (it holds `node_modules/yaml` and `node_modules/skills`), installs nothing and writes nothing outside `tmp/`. `gate` is the Python gate's live verdict; `yaml` is `YAML.parse` with the default duplicate-key check and the same field rules.

```
yaml 2.9.0 (npm, from the npx cache)
skills 1.5.20 (npm, from the npx cache)
valid plain	gate=accept	yaml=accept	same
colon on first line	gate=reject	yaml=reject	same
colon on continuation line	gate=reject	yaml=reject	same
tab-indented line	gate=reject	yaml=reject	same
unterminated quote	gate=reject	yaml=reject	same
duplicate key	gate=reject	yaml=reject	same
non-string name	gate=reject	yaml=reject	same
1025-character description	gate=reject	yaml=reject	same
uppercase name	gate=reject	yaml=reject	same
name differs from folder	gate=reject	yaml=reject	same
65-character name	gate=reject	yaml=reject	same
double hyphen	gate=reject	yaml=reject	same
leading hyphen	gate=reject	yaml=reject	same
trailing hyphen	gate=reject	yaml=reject	same
empty description	gate=reject	yaml=reject	same
empty frontmatter	gate=reject	yaml=reject	same
no frontmatter	gate=reject	yaml=reject	same
plain continuation without colon	gate=reject	yaml=accept	designed-stricter
inline comment	gate=reject	yaml=accept	designed-stricter
1024-character description	gate=accept	yaml=accept	same
64-character name	gate=accept	yaml=accept	same
folded description	gate=accept	yaml=accept	same
literal description	gate=accept	yaml=accept	same
double-quoted description	gate=accept	yaml=accept	same
single-quoted description with a doubled quote	gate=accept	yaml=accept	same
non-ASCII description of 1024 characters	gate=accept	yaml=accept	same
description before name	gate=accept	yaml=accept	same
fixtures 27: same 25, designed-stricter 2, DIFFERENT 0
```

## Verification results

| Command | Exit | Result |
|---|---|---|
| `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_skill_frontmatter tests.test_setup tests.test_gate_scope` | 0 | 3/3 modules; test_skill_frontmatter 7 tests, test_setup 479, test_gate_scope 60 |
| `AI_KIT_REFUSE_REAL_HOME=1 uv run python tools/run_unittest_parallel.py tests.test_skill_frontmatter_pyyaml tests.test_framework_profiles` | 0 | 2/2 modules; pyyaml 3 tests, framework_profiles 6 |
| `node tmp/p32/06/yaml_compare.mjs` | 0 | 27 fixtures, DIFFERENT 0 (above) |
| `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p32/06/scope.py test` (`make test`) | 0 | unit 103/103, unit-uv 2/2, integration 8/8, e2e 25/25 (plus `tests/test_install.sh`: 48 passed, 0 failed), arch 1/1; no `failed:` line |
| `AI_KIT_REFUSE_REAL_HOME=1 make pyright` (after fix commit) | 0 | pyright Passed |
| `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/p32/06/scope.py close` | 0 | `leftover (this run):` empty; last line `clean` |
| `grep -c "def test_real_inline_descriptions_are_strict_yaml\|def test_real_entries_have_a_name_and_a_description" tests/test_setup.py` | - | 0 (baseline 2) |
| `grep -c "tests.test_skill_frontmatter" Makefile` | - | 1 (baseline 0) |
| `grep -c "tests.test_skill_frontmatter_pyyaml" tools/run_unittest_parallel.py` | - | 1 (baseline 0) |
| `grep -c "unit-uv: tests.test_framework_profiles tests.test_skill_frontmatter_pyyaml" Makefile` | - | 1 |

Each task commit also ran the commit-stage hooks: `1ca4d44` ran 109/109 unit and arch modules (full run, shared test machinery), `8b2511c` ran 118/118 modules including the uv module, `f5d7b4b` ran its three covering modules.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pyright errors in the PyYAML cross-check**
- **Found during:** Task 2 step 7 (the plan's final `make pyright`)
- **Issue:** `frontmatter_body` returns `None` without a frontmatter block; three `yaml.load` calls in the cross-check tests received the `Optional[str]` directly (`reportArgumentType`).
- **Fix:** Added `_must_body(text)`, which asserts a body exists before loading, and used it in the three call sites.
- **Files modified:** `tests/test_skill_frontmatter_pyyaml.py`
- **Verification:** `make pyright` exits 0; the uv module still reports 3 tests ok.
- **Committed in:** `f5d7b4b` (own fix commit, as the plan requires)

### Plan-directed change to the scope script

- `tmp/p32/06/scope.py` places the per-run temp dir R at `<worktree root>/tmp/p32/06/run-<run_id>` instead of the system temp dir, per the temp-files rule of this plan. Everything else in the 29-01 spec is as written. Run ids: `223ca8e7`.

**Total deviations:** 1 auto-fixed (Rule 1), plus the one directed scope-script change above.
**Impact on plan:** None on the gate's behavior; the fix only narrows types in test code.

## Issues Encountered

- The close check reports processes of other sessions and of the orchestrator's session wake (`nap.sh 170 worktree-agent-a8783801189d1d8a1:32-06`, `pid 2830842`) under `reported (not this run)`. They are not from this run and were left alone.
- The `actuals.tokens` figure is the realized diff measure (11581). The changed-file measure is 115202, dominated by the whole of `tests/test_setup.py`, which this plan edited by removing 31 lines. The diff figure is the one the summary contract names.

## Next Phase Readiness

- Every installable entry parses strictly today, so the gate passes on the current tree with no SKILL.md edits. Plan 32-05 owns the SKILL.md files and changes no frontmatter, so this plan did not touch them.
- The orchestrator copies the "R8 comparison with the npm yaml package" block above into `32-VERIFICATION.md`.

## Self-Check: PASSED

- Created files exist: `tests/test_skill_frontmatter.py`, `tests/test_skill_frontmatter_pyyaml.py`.
- Commits exist: `1ca4d44`, `8b2511c`, `f5d7b4b` on `worktree-agent-a8783801189d1d8a1`.

---
*Phase: 32-re-judge-baseline*
*Completed: 2026-11-07*
