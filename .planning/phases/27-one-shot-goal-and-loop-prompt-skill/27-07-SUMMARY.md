---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 07
subsystem: tooling
tags: [goal-prompt, strategies, goal, loop, plain, superpowers, shared-rails, stdlib, tdd]
requires:
  - phase: 27-06
    provides: "PromptTemplate, guards, fixed section builders and the OpenGSD autonomous render"
  - phase: 27-02
    provides: "gp_scope Plan, load_plans, execution_order and dependents"
  - phase: 27-05
    provides: "strategy entries (id, rank, recommended, primitive, label) from gp_matrix"
provides:
  - "gp_sections: goal_block, loop_block, plain_block, strategy_heading, superpowers_rule_lines, superpowers_order_lines, generic_rule_lines, Work"
  - "gp_render: BlockView, Block, build_blocks; one file with a block per ranked strategy and one shared ## Rails section"
  - "render for opengsd, gsd-unproven, superpowers and free-text (none) work sets; the NotImplementedError stub is gone"
  - "assets/prompt-template.md: BLOCK_PLAIN section for the fenced paragraph and /goal or /loop blocks"
affects:
  - "27-08: done_lines still raises NotImplementedError for an e2e none result and for mockups (WINDOWS #5)"
  - "27-09: the render CLI must send work_set {kind: free, text} and {kind: plans, files}; the R18/R19 parity test (WINDOWS #6)"
  - "27-10: SKILL.md documents the block shapes and the unverified labels"

# Actuals (#2632): chars/4 over the git diff of the seven files this plan changed (70295 bytes)
actuals:
  tokens: 17574
  tasks: 2
  commits: 2
  plan_head_before: 0b4de64945eeda3d26aeb4e344413b25476685bc
  plan_head_after: 902a6b4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One file, one block per strategy: the recommended first, each block under a numbered heading"
    - "Inline rails only inside an autonomous block; every other block names the shared Rails section by its repo-relative path"
    - "Work family resolved once (opengsd | gsd-unproven | superpowers | none); rails and ORDER are chosen by family"
    - "Unverified primitives are labelled in the heading, and in the paste text for goal, loop and plain blocks"

key-files:
  created:
    - tests/test_ai_kit_spec_goal_prompt_strategies.py
  modified:
    - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
    - skills/ai-kit-spec-goal-prompt/scripts/gp_render.py
    - skills/ai-kit-spec-goal-prompt/assets/prompt-template.md
    - tests/test_ai_kit_spec_goal_prompt_render.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "The paste text of a goal, loop or plain block names the unverified primitive; the autonomous block's first line stays flags-only (D-12), so its label lives in the heading alone."
  - "check_text keeps its opengsd_block keyword with a narrower meaning: when True, each inline autonomous block must carry all eleven sections. The inline caps and flags rules apply to every /gsd-autonomous block whatever the keyword says; shared rails get the rule caps and the DONE WHEN and jev checks."
  - "The work family is resolved from work_set.kind and the detected identity: phases give opengsd or gsd-unproven, plans give superpowers, free text gives none. A plans work set is restricted to the named files inside render; detect_scope itself is unchanged (WINDOWS #2 stays open)."
  - "rail_sections takes a Work NamedTuple (family, scope text, phases, plans). Its old four-argument form is gone; the 27-06 test helper was updated to match."
  - "ORDER is emitted only when it has lines: a single plan with no free text and the free-text (none) family have no ORDER section."
  - "The free-text answer is {kind: free, text}. This shape is my choice; 27-09 must emit it."

requirements-completed: []  # GPS-01 and GPS-02 are covered by the renderer, but the render CLI and the R18/R19 parity test land in 27-09. Same precedent as 27-05 and 27-06.

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 07: Goal, loop, plain and superpowers rails Summary

**One goal file now holds a paste block per ranked strategy: an inline autonomous block for OpenGSD, `/goal` and `/loop` blocks plus a plain paragraph sharing one Rails section, and superpowers rails with dependency order and stop scope**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 2 of 2 completed, one commit each
- **Files created:** 1; **files modified:** 6 (`gp_sections.py`, `gp_render.py`, the template, the 27-06 render test module, and the two generated listings)

## Accomplishments

- `goal_block` builds one `/goal` line that names the rails file and section, DONE WHEN, the exit code and count line, the unit-test sentence and a turn cap. The 5,000-character objective case fails generation with the code-point count in the message.
- `loop_block` uses `/loop <interval> ...` for `/loop`, `CronCreate one-shot`, `CronCreate recurring` and `ScheduleWakeup`. For an OS timer or no primitive it returns a plain paragraph that relies on the QUOTA A wake. Neither form contains `--`.
- `plain_block` and `strategy_heading` give the plain strategy its flagged heading. An unverified strategy gets ` [unverified: <primitive>]` in its heading and an "unverified on this host" sentence in its paste text.
- `build_blocks` orders the blocks with the recommended one first, whatever the input order. `render` writes one file: every block under a numbered heading, and one `## Rails` section after the COPY TO HERE marker whenever a non-autonomous block exists. An autonomous block keeps its rails inline, so an `[autonomous, goal]` file holds the rails twice.
- `superpowers_rule_lines` gives the six fixed superpowers rules. `superpowers_order_lines` gives `Plans in order: ...`, one stop-scope line per plan that has dependents, and one line per free-text dependency. A single plan with no free text has no ORDER section.
- `render` now handles every matrix row: `autonomous` for OpenGSD and gsd-unproven, `goal`, `loop` and `plain` for superpowers and free text, and free text with the generic rules and no ORDER section. The NotImplementedError stub is gone, which closes WINDOWS #4.
- `check_text` also checks the shared Rails section (60 rule lines, 200 characters each, DONE WHEN with the unit-test sentence, jev only with advisory) and refuses a copy marker that appears other than once.

## Task Commits

1. **Task 1: goal, loop and plain blocks with the shared-rails file shape** - `ac11ff5` (feat)
2. **Task 2: superpowers orchestration rails with dependency order and stop scope** - `902a6b4` (feat). The commit also carries the unverified-primitive sentence in the paste text, which was a Task 1 must-have.

**Plan metadata:** recorded in the docs commit that adds this file and the state updates (see the completion report).

## Files Created/Modified

- `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py` - the block builders, the superpowers and generic rule lines, the superpowers order lines, `Work`, and the family switch in `rail_sections` (stdlib only; imports `gp_scope`, `gp_e2e` and `gp_common`)
- `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py` - `BlockView`, `Block`, `build_blocks`, the work-set resolution (`_phase_work`, `_plan_work`, `_free_work`), the shared-rails checks, and the multi-block `render`
- `skills/ai-kit-spec-goal-prompt/assets/prompt-template.md` - the `BLOCK_PLAIN` section
- `tests/test_ai_kit_spec_goal_prompt_strategies.py` - new: `TestBlocks` (22 tests) and `TestSuperpowers` (13 tests); 35 in total
- `tests/test_ai_kit_spec_goal_prompt_render.py` - the 27-06 helper now passes a `Work`; the superseded NotImplementedError test is replaced by a test that a plans work set needs a superpowers scope
- `Makefile`, `.pre-commit-config.yaml` - test-group listings regenerated with `tools/gen_test_groups.py`

## Deviations from Plan

### Plan-shape and spec changes

**1. [Signature] `rail_sections(detect, answers, work)`.** The plan kept the 27-06 form `(detect, answers, scope_desc, phases)`. Superpowers needs the plans and the family, so the four arguments became one `Work` NamedTuple.

**2. [Signature] `check_text` keeps `opengsd_block` with a narrower meaning.** The plan's tests call `check_text(..., opengsd_block=False)`, so the keyword stays. Its meaning is now "require all eleven sections in each inline autonomous block". The flags, size and rule caps for a `/gsd-autonomous` block apply whatever the keyword says, because the block's first line decides them.

**3. [Label] Unverified labels reach the paste text for goal, loop and plain blocks.** The plan's must-have says heading and block. The autonomous block is the exception: its first line must stay flags-only (D-12), so its label is in the heading only. This is recorded in `.planning/WINDOWS.md`.

**4. [Test layout] `TestSuperpowers` landed in the second commit.** The module had to stay green at the first commit, and the superpowers render needs Task 2's ORDER. The class was held back in a scratch copy and restored for Task 2. The tests were run red before the implementation.

**5. [Scope] A plans work set is restricted inside `render`.** The restriction matches the answer's files to the detected plans by basename. `detect_scope` itself still lists every plan, so WINDOWS #2 stays open.

**6. [Interface] The free-text answer shape is `{kind: "free", text: ...}`.** The plan names no key for it. 27-09 must send this shape.

### Plan verify command defect

**7. [Plan defect] The Task 2 pyright verify line fails although pyright reports 0 errors.** The command is `uv run pyright ... | tail -n 3 | grep -q '0 errors'`. Pyright's output ends with the version banner and then a blank line, so `tail -n 3` never shows the `0 errors` line. The real result is `0 errors, 0 warnings, 0 informations`. This is the same defect 27-06 recorded as item 10.

### Auto-fixed during execution

- Ruff E501 (two docstrings) and RUF005 (a list concatenation) were fixed before the Task 1 commit. Pylint and vulture are clean.
- An unused `execution_order` import was removed from `gp_sections.py` during Task 1 and restored in Task 2, where it is used.

## Known Stubs

| File | Behavior | Resolved by |
|------|----------|-------------|
| `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py` (`done_lines`) | An e2e result with `none: true`, or any mockup, still raises `NotImplementedError` ("plan 27-08"). A superpowers or free-text render with no detected e2e command therefore fails until 27-08. | 27-08 (WINDOWS #5) |

## Threat Flags

None. The render writes one new file through `write_atomic`; the only subprocess is the existing read-only `git check-ignore`. Plan titles and free text are collapsed to one line, and `check_text` refuses a leaked home path, a secret, `--no-verify` and a duplicate copy marker.

## Broken-windows ledger

- Closed: WINDOWS #4 (the render stub), via `gsd-tools windows fixed 4`.
- Still open for other plans: #5 (27-08), #6 (27-09), #2 (detect-level plan restriction, 27-09 wiring), #3 (an autonomous request on a superpowers scope, unassigned).
- Added in this plan: a deviation for the autonomous heading-only label, and a deviation for a rule line over 200 characters (a long plan title or objective refuses generation instead of wrapping).

## Unverified Items

- **No host has run any rendered block.** The `/goal` and `/loop` forms, and the claim that `CronCreate` and `ScheduleWakeup` are loop primitives, come from the matrix fixtures. They are not checked against a live host.
- **The `/gsd-autonomous` flags line is pinned by a test, not by the workflow's argument parser.** This carries over from 27-06.
- **Superpowers rails assume the orchestrator can dispatch one subagent per plan.** D-09 was refined on 2026-10-14; nothing here checks that a host supports it.
- **A plan title or objective over about 200 characters refuses generation.** No test covers a wrapped title, and the case is recorded in the ledger.
- **The `none` family's generic rules have only unit-level coverage.** No real free-text run has been rendered.
- **The `/goal` condition budget is measured with `len`.** That counts code points, as the SPEC requires, but it is not checked against a real host.

## Self-Check

- Created file exists: `tests/test_ai_kit_spec_goal_prompt_strategies.py` (in both commits).
- Commits `ac11ff5` and `902a6b4` are ancestors of HEAD and carry `feat(27-07):` subjects.
- `commits: 2` was measured as `git rev-list --count 0b4de64...HEAD` (the ledger file `gsd-plan-head-before-27-07` was written after the first commit, from its parent, as 27-06 did).
- Test runs: `tests.test_ai_kit_spec_goal_prompt_strategies` 35 of 35 (TestBlocks 22, TestSuperpowers 13); `tests.test_ai_kit_spec_goal_prompt_render` all passing; `tests.test_gate_scope` OK.
- `python3 tools/run_unittest_parallel.py --group unit --group arch`: 70 of 70 modules passed, exit 0.
- `ruff check` on the goal-prompt scripts and both test modules: all checks passed. `pylint` on `skills/ai-kit-spec-goal-prompt/scripts`: 10.00/10. `pyright` on the skill and the strategies test: 0 errors, 0 warnings. `vulture --min-confidence 80`: no findings.
- `.planning/config.json` was never staged.
