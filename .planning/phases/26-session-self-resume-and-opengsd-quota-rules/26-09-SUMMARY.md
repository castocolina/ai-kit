---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 09
subsystem: testing
tags: [rules-checker, agents-md, parallel-tests, cpu-share, gradle, maven, pytest-xdist]

# Dependency graph
requires:
  - phase: 26-08
    provides: "OpenGSD-only R18/R19, verbatim remediation entries, notices, presence-filtered CLI (include_present)"
provides:
  - "R20: parallel unit tests capped at floor(40% of the available CPUs), composed per detected stack"
  - "tool_catalog.PARALLEL_TEST_FORMS: one data table of per-stack forms (go, python, node, maven, gradle, gradle-kts, rust)"
  - "stack_detect.STACK_ORDER and detect_markers"
  - "classification: stack-detected condition, stack-form classification, hardcoded_worker_counts"
affects: [26-10, 26-12, rules-checker family, ai-kit-project-rules-all]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: "not measured (chars/4 over the realized diff was not computed)"
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-stack rows are data: the engine matches runner phrases, count flags, signals and marker files, with no per-language branch"
    - "Stack forms round-trip: the composed text, written back to AGENTS.md, classifies as present"

key-files:
  created: []
  modified:
    - skills/_shared/ai_kit_rules_common/tool_catalog.py
    - skills/_shared/ai_kit_rules_common/stack_detect.py
    - skills/_shared/ai_kit_rules_common/classification.py
    - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py
    - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rule_checker.py
    - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py
    - skills/ai-kit-project-rules-agents/SKILL.md
    - skills/ai-kit-project-rules-all/SKILL.md
    - skills/ai-kit-project-rules-makefile/SKILL.md
    - README.md
    - tests/test_ai_kit_project_rules_agents.py
    - tests/test_ai_kit_rules_common.py

key-decisions:
  - "R20 is gated on `stack-detected`, not on `opengsd`, and is `verbatim: true` so Step C inserts it unchanged"
  - "Gradle rows select by marker file (build.gradle, build.gradle.kts), not by the test-runner group, which names no Gradle command; the shared catalog stays unchanged because cicd and precommit read it"
  - "A stack with no table row gets a clause that says no verified form exists, and is listed in unverified_stacks; it does not lower the status"
  - "Round-trip present detection keys on the R20 signal groups, so an unverified stack never blocks a clean remediation"

patterns-established:
  - "Pattern 1: a new stack's form is one row in PARALLEL_TEST_FORMS with a dated source, never an engine branch"
  - "Pattern 2: line-scoped literal-count detection: a runner phrase or the generic test word scopes each flag, and a flag counts only at a token start"

requirements-completed: [QTA-06]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "R20 is missing for a python repo; the remediation entry is verbatim and writes back as present"
    requirement: QTA-06
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestParallelTestRule.test_remediation_text_written_back_is_present_and_filtered_by_cli"
        status: pass
  - id: D2
    description: "Each detected stack gets its own clause; Gradle Groovy and Kotlin each get their own syntax; three java markers order Maven, Groovy, Kotlin"
    requirement: QTA-06
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestParallelTestRule.test_each_stack_gets_its_own_clause_and_round_trips_present"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestParallelTestRule.test_three_java_markers_give_maven_groovy_kotlin_in_that_order"
        status: pass
  - id: D3
    description: "40% boundary: exactly 40% passes; 41% (percent, 0.41C, prose) and literal counts are flagged as near_miss"
    requirement: QTA-06
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestParallelTestRule.test_share_above_forty_percent_is_flagged_in_each_form"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestParallelTestRule.test_literal_counts_next_to_a_test_command_are_flagged"
        status: pass
  - id: D4
    description: "Table guard: runners sit in the shared test-runner group, each marker belongs to one row, rows follow STACK_ORDER, every row has a dated source"
    requirement: QTA-06
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_rules_common.py#TestParallelTestTable"
        status: pass
  - id: D5
    description: "The eight rule-count strings all read 20, tied to len(RULES)"
    requirement: QTA-06
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_agents.py#TestRuleCountStrings"
        status: pass

# Deviations
deviations:
  - "Pinned test-only: test_r18_and_r19_follow_r17_in_catalog_order renamed to test_r18_r19_r20_follow_r17_in_catalog_order and extended to the new tail (R20 is appended after R19)"

# Verification status — honest scope
unverified-live:
  - "pytest-xdist, jest/vitest, cargo and the Gradle property were cited from docs, not run; only go (go1.27.1) and maven (3.9.16) flags were run locally"
orchestrator_verify: "VERIFY 26-09: 2/2 passed"
---

# Phase 26 Plan 09: R20 parallel-test CPU share

**R20 caps parallel unit tests at floor(40% of the available CPUs) per detected stack, with a literal count or a share above 40% flagged as near_miss; the house ruleset is now 20 rules.**

## Performance

- **Tasks:** 2 (tracer, then pins)
- **Commits:** 3 (one feature, one test, plus this summary)

## Accomplishments

- R20 is a `workflow` rule, `stack-detected`, `verbatim: true`, appended after R19.
- Per-stack forms come from one table (`tool_catalog.PARALLEL_TEST_FORMS`) with no per-language branch in the engine.
- A python repo without the rule gets R20 `missing`; its verbatim remediation, written back, classifies `present` and is filtered from the default `check` output (visible with `include_present`).
- Go, node, maven, gradle (Groovy), gradle-kts (Kotlin), rust and python each get their own clause; multi-stack clauses follow `STACK_ORDER` and identical clauses are written once.
- The 40% boundary: `0.4C` and `40%` pass; `0.41C`, `41%` (percent or prose) and literal counts (`pytest -n 12`, `make -j 8 test`, `--maxWorkers=4`, `maxParallelForks = 8`) are flagged; `tail -n 50 build.log` and `make -j 8 build` are not.
- Docs: all eight rule-count strings read 20, pinned to `len(RULES)` by `TestRuleCountStrings`. Agents SKILL.md Step C inserts `verbatim` entries unchanged, its `remediate` description names `notices`, and it has a `runtime-identity` trust note. The rules-all SKILL.md says four keys and the `notices` order.

## Files Created/Modified

- `skills/_shared/ai_kit_rules_common/tool_catalog.py` - `PARALLEL_TEST_FORMS` (7 rows), `PARALLEL_TEST_GENERIC`, signal groups, count flags
- `skills/_shared/ai_kit_rules_common/stack_detect.py` - `STACK_ORDER`, `detect_markers`
- `skills/_shared/ai_kit_rules_common/classification.py` - `stack-detected` condition, stack-form classification, `hardcoded_worker_counts`
- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` - R20
- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rule_checker.py` - docstring count
- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py` - `stacks` and `stack_markers` presence
- `skills/ai-kit-project-rules-agents/SKILL.md`, `skills/ai-kit-project-rules-all/SKILL.md`, `skills/ai-kit-project-rules-makefile/SKILL.md`, `README.md` - counts and docs
- `tests/test_ai_kit_project_rules_agents.py` - `TestParallelTestRule`, `TestRuleCountStrings`, tail-order pin
- `tests/test_ai_kit_rules_common.py` - `TestParallelTestTable`

## Commits

- `b26674d` feat(26-09): R20 parallel tests capped at 40% of the CPUs, per detected stack
- `a32487a` test(26-09): pin R20 per stack, the 40% boundary and literal counts

## Decisions Made

- The Gradle rows select by marker file, not the test-runner group, as D-27's 2026-10-28 amendment says.
- An unverified stack gets a clause that says so, and does not lower the status (so the round trip stays clean).
- The count-string test ties every match to `len(RULES)` and fails below 8 matches, so a silently dropped file cannot pass.

## Deviations from Plan

**1. [Rule 1 - Bug] Pyright error in the table guard**
- **Found during:** Task 2 verification (pyright at HEAD)
- **Issue:** `set(...)` over `OUT_OF_TAXONOMY_GROUPS["test-runner"]["markers"]` typed `object`, a `reportArgumentType` error.
- **Fix:** Narrowed in the test with `assertIsInstance` and an explicit `set[object]`. The shared catalog type is unchanged.
- **Committed in:** `a32487a` (amended into the test commit)

**2. [Rule 1 - Bug] Vacuous dedupe test**
- **Found during:** Task 2 self-review
- **Issue:** `test_identical_clause_text_is_written_once` could never fail, because no real repo produces a duplicate clause.
- **Fix:** Replaced with a synthetic two-row test; a mutation check (removing the dedupe) makes it fail.
- **Committed in:** `a32487a`

**3. [Rule 1 - Bug] Test expectations corrected**
- Two of my own test fixtures were wrong: a case-sensitive expectation for `hardcoded_counts` (which keeps the original text by design) and a 40% fixture missing the generic sentence. Fixed the expectations, not the engine.

**4. [Rule 3 - Blocking] Existing test pinned the old tail**
- `test_r18_and_r19_follow_r17_in_catalog_order` expected R19 as the last rule. Extended to R20 (see `deviations` in the frontmatter). The pin was updated, not loosened.

**5. Gate gap: pyright was not run before the first commit**
- Commit `b26674d` (Task 1) was verified with pyright clean, but the Task 2 commit `5ad8079` was made while pyright failed. Pyright runs at `pre-push` in this repo, not at commit, so the commit hook missed it. Fixed by amending the local, unpushed commit to `8b666c1`, then `a32487a`.

## Issues Encountered

- **Pre-existing formatting:** `skills/ai-kit-project-rules-agents/.../cli.py`, `tests/test_ai_kit_project_rules_agents.py` and three other shared files were already unformatted at HEAD. Not reformatted, to keep the diff scoped; `ruff check` (the gate) is clean.
- **Not verified live:** pytest-xdist, jest/vitest `--maxWorkers`, cargo `--test-threads`, and the Gradle `maxParallelForks` property were taken from their cited docs. No network access here, so they were not run. Only `go help build` (go1.27.1) and `mvn -h` (3.9.16) were run locally. Each row's `source` says which.
- **Shared checkout:** commit `fef6397` (a backlog docs commit not made by this executor) landed between Task 1 and Task 2 in this shared checkout. Left as is.
- **skill-judge:** not run. It applies only to plans 18.1-21 and 18.1-22.

## Next Phase Readiness

- R20 is in place and the count is 20; 26-10 and 26-12 can build on the `verbatim`/`notices` contract.
- The Gradle, pytest-xdist and jest clauses should be re-verified against live docs when next touched.

---
*Phase: 26-session-self-resume-and-opengsd-quota-rules*
*Completed: 2026-10-30*
