---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 08
subsystem: tooling
tags: [goal-prompt, create-first, mockup, jev, cross-ai, turn-cap, stdlib, tdd]
requires:
  - phase: 27-07
    provides: "goal, loop, plain and superpowers blocks, the shared Rails section and the Work family"
provides:
  - "gp_sections.done_lines: create-first task when no e2e suite exists, mockup human-review line; the NotImplementedError placeholder is gone (WINDOWS #5)"
  - "gp_sections.report_lines: one advisory jev line naming the decide.py ladder, REPORT only, only when detect.jev.usable"
  - "gp_sections.order_lines: cross_ai gap line for phases whose existing plans lack the declaration (never for native execution)"
  - "gp_sections.turn_cap and work_items: max(60, 40 * items), printed in STOP IF and in the /goal condition"
  - "gp_render: readiness problems as stdout-only warnings; machine-path mockup guard; non-numeric phase number guard"
affects:
  - "27-09: render CLI, R18/R19 parity test (WINDOWS #6); BlockView.turn_cap defaults to the floor when a caller does not pass one"

# Actuals (#2632): chars/4 over the git diff of the goal-prompt skill, its tests and the two listings (51303 bytes)
actuals:
  tokens: 12825
  tasks: 2
  commits: 2
  plan_head_before: f843bbb0b97e29b00091e4aac3abc2ffcf96ce6d
  plan_head_after: c2c7fb10b24666967c1ef99bf2aa67e265b05b4f

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Content variants are pure section builders; the renderer decides which variant a file gets"
    - "Readiness problems leave the file: they are stdout warnings for the generator only"

key-files:
  created:
    - tests/test_ai_kit_spec_goal_prompt_variants.py
  modified:
    - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
    - skills/ai-kit-spec-goal-prompt/scripts/gp_render.py
    - tests/test_ai_kit_spec_goal_prompt_render.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "The jev usable line now says 'through the decide.py ladder' (the SPEC names the ladder; the 27-06 wording did not)."
  - "Native execution never gets the cross_ai gap line: its plans omit cross_ai: true by design, so listing them would contradict the native rule."
  - "The turn cap counts phases for a phases work set, plans for a plans work set, and one task for free text."
  - "The mockup machine-path guard and the non-numeric phase guard live in gp_render (check_fields, _phase_work), because gp_render is where the work set and answers are validated."
  - "The readiness warnings are built from detect.readiness.problems only (fixed reasons from gp_host), and only for a GSD family that is not native."

requirements-completed: [GPS-03, GPS-04]  # GPS-02: the file-level cross_ai declaration and gap line are done; the render CLI and the R18/R19 parity land in 27-09

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 08: Create-first, mockup review, advisory jev, cross_ai gap and derived turn cap Summary

**The DONE WHEN section now opens with a create-first task when no e2e suite exists, mockups route to human review, the advisory jev line appears only in REPORT, phases whose plans lack cross_ai get a gap line, and the turn cap is derived from the item count**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 2 of 2 completed, one commit each
- **Commits:** `3bb4bc0` (Task 1), `c2c7fb1` (Task 2)

## Accomplishments

- `done_lines` no longer raises. With `none: true` the first DONE WHEN line is the create-first task, followed by the evidence, gates, process-group and unit-test lines, and no `E2E:` line. With detected commands the output is byte-identical to 27-06 (the existing exact-text test still passes).
- A mockup adds one line: capture e2e screenshots or TUI snapshots, print their paths, list them for human review, and "No automated judge decides it." Mockup descriptions collapse to one line.
- The jev usable line is the only jev line in a file, sits in REPORT, and passes `check_text` only because it carries the word advisory. The unusable case states the omission and its reason. A sweep test renders a usable jev with a mockup and asserts no line mixes jev with mockup, screenshot or UI.
- `order_lines` adds `Existing plans missing cross_ai: true (add it, then execute): <phases>.` for phases with `0 < plan_count` and `cross_ai_plans < plan_count`. It is absent for native execution.
- `turn_cap(items) = max(60, 40 * items)`; the number appears in STOP IF and in the `/goal` condition.
- `render` warnings are `cross-AI readiness failed: <problem>` from `readiness.problems`, never written into the file. A ready readiness, or native execution, gives an empty list.
- A machine-path mockup is refused by field name; a non-numeric phase number raises `GuardError` (it used to raise `ValueError`).

## Task Commits

1. **Task 1: create-first, mockup human review and the advisory jev step** - `3bb4bc0` (feat). Adds `TestDoneVariants` (9 tests) and `TestJevVariants` (6 tests); replaces the 27-06 placeholder test; regenerates the two listings.
2. **Task 2: existing cross_ai gap line, derived turn cap and readiness warnings** - `c2c7fb1` (feat). Adds `TestCrossAiVariants` (11 tests) and `TestRenderGuards` (2 tests).

## Files Created/Modified

- `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py` - `done_lines` rewritten around `_e2e_lines`; `CREATE_FIRST`, `EVIDENCE`, `MOCKUP_REVIEW`; `turn_cap`, `work_items`; the cross_ai gap line; the jev wording. Stdlib only.
- `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py` - `BlockView.turn_cap`; readiness warnings from `problems`; the mockup guard in `check_fields`; the phase-number guard in `_phase_work`.
- `tests/test_ai_kit_spec_goal_prompt_variants.py` - new: 28 tests in four classes.
- `tests/test_ai_kit_spec_goal_prompt_render.py` - the 27-06 placeholder test is replaced; the jev wording pin is updated; the readiness-warning pin uses the new source.
- `Makefile`, `.pre-commit-config.yaml` - test-group listings regenerated with `tools/gen_test_groups.py` (the variants module added only).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Commit gate on the branch allow-list.** The pre-commit HEAD assertion refused commits on `gsd/v1.3-curated-config-v2` because the prompt carried no `<sequential_execution>` block. The coordinator then sent that block, and the commits were made on this branch under the sequential rule. No guard was bypassed.

**2. [Scope] Task 2 touched `tests/test_ai_kit_spec_goal_prompt_render.py`, which is not in the Task 2 file list.** The readiness-warning test pinned the old boolean-derived source, which the plan explicitly replaces. It was updated in `c2c7fb1` and recorded in that commit message.

**3. [Scope] The mockup and phase-number guards are in Task 2, not Task 1.** `gp_render.py` is listed only in Task 2. Their tests therefore sit in `TestRenderGuards`, committed with Task 2.

**4. [Interpretation] Native execution suppresses the cross_ai gap line.** The plan says ORDER lists the gap, but native plans omit `cross_ai: true` by design, so the line would contradict the native rule.

**5. [Interface] `BlockView.turn_cap` defaults to the floor (60).** The 27-07 strategy tests construct `BlockView` without a cap; the default keeps them unchanged.

### Plan verify command defects

**6. [Plan defect] The Task 2 pyright check fails although pyright reports 0 errors.** The command is `uv run pyright ... | tail -n 3 | grep -q '0 errors'`. Pyright's version banner occupies the last lines, so `tail` never shows the summary. The real result is `0 errors, 0 warnings, 0 informations`. This is the same defect recorded in 27-06 and 27-07.

**7. [Plan text] The create-first sentence is quoted verbatim from the plan, including the phrase "and make it pass", which is not grammatical.** I kept the quoted text so a grep against the plan still matches.

## Known Stubs

None. The `done_lines` placeholder is gone, and WINDOWS #5 is closed.

## Threat Flags

None. The new guard and the new text add no network, auth or file-access surface. Free text (mockups) is collapsed to one line and passes `check_text`.

## Broken-windows ledger

- Closed: WINDOWS #5 (`done_lines` placeholder), via `gsd-tools windows fixed 5`.
- Still open for other plans: #6 (R18/R19 parity, 27-09), #2 (the detect-level plans restriction, 27-09 wiring), #3 (an autonomous request on a superpowers or none scope), #7 (the autonomous block's unverified label, heading only), #8 (a rule line over 200 characters refuses generation), and #1 (the stub SKILL.md, 27-10).

## Unverified Items

- **Pre-commit hooks ran on each commit, but pyright and vulture were run by hand.** The pre-commit set that fired on the commits was ruff, pylint and py-compile; pyright (0 errors) and vulture (clean) were checked directly on the goal-prompt skill and the variants module.
- **No host has run a rendered block.** The `/goal` and loop claims, and the cross-AI gap rule, depend on the synthetic fixtures; they are not checked against a live host or a real GSD phase tree.
- **The cross_ai counter in `gp_scope` is trusted, not checked.** The gap line depends on `cross_ai_plans` counting the declarations in real PLAN.md files; the unit tests use hand-built counts.
- **Readiness warnings were checked with synthetic readiness dicts,** not with a real cross-ai runner probe.
- **A mockup or e2e line over 200 characters refuses generation** (WINDOWS #8). No test covers a wrapped line.
- **Formatting is not a gate.** `ruff format --check` would reformat five files, including code from earlier plans; `make format` is dev-only and was not applied, so the layout is unchanged.
- **The e2e detection fixtures are synthetic.** The Makefile, package-script, Playwright and empty-repo cases exercise `gp_e2e.detect_e2e` on temporary repositories, not on a real project.

## Self-Check

- Created file exists: `tests/test_ai_kit_spec_goal_prompt_variants.py` (committed in `3bb4bc0`).
- Commits `3bb4bc0` and `c2c7fb1` are ancestors of HEAD and carry `feat(27-08):` subjects.
- `commits: 2` was measured as `git rev-list --count f843bbb..HEAD`.
- Test runs: the eight goal-prompt modules pass 327 tests; `TestDoneVariants` 9 of 9; the variants module 28 of 28; `tests.test_gate_scope` OK.
- `python3 tools/run_unittest_parallel.py --group unit --group arch`: 71 of 71 modules passed, exit 0, before the bookkeeping commit.
- `ruff check` on the goal-prompt scripts and the new and changed test modules: all checks passed. `pylint` on `skills/ai-kit-spec-goal-prompt/scripts`: 10.00/10. `pyright`: 0 errors, 0 warnings. `vulture --min-confidence 80`: no findings.
- `.planning/config.json` was never staged.
