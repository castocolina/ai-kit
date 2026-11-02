---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 06
subsystem: tooling
tags: [goal-prompt, template, strict-engine, guards, opengsd, stdlib, tdd]
requires:
  - phase: 27-01
    provides: "skill directory, gp_common helpers, test-group listings"
  - phase: 27-04
    provides: "e2e detection result shape (commands, gates, none) read by the DONE WHEN lines"
  - phase: 27-05
    provides: "strategy selector; the OpenGSD autonomous row (M01) that this render implements"
provides:
  - "assets/prompt-template.md: FILE and BLOCK_INLINE sections split by === NAME ==="
  - "gp_render.PromptTemplate (delimiter §§, strict substitute), load_template, fill"
  - "gp_render.check_condition (4,000 code-point cap), check_fields (path fields), check_text (forbidden kinds, 60 rule lines, 200 characters, 7,000 block, 1,800 /goal budget, wrapper rules)"
  - "gp_render.choose_path (goals dirs, git-ignored tmp/, -2/-3 suffixes), write_atomic (temp file plus os.replace, never overwrites)"
  - "gp_render.render(detect, answers, ctx): the OpenGSD phases case to one committed file, returning the contract stdout"
  - "gp_sections: fixed rule lines for the eleven labeled sections, assemble_rails, rail_sections, done_lines (detected e2e commands)"
affects:
  - "27-07: other strategies (render raises NotImplementedError for non-OpenGSD scopes)"
  - "27-08: e2e-none and mockup done lines (done_lines raises NotImplementedError)"
  - "27-09: detect CLI, R18/R19 parity through check_rules, golden file"
  - "27-10: SKILL.md and the render CLI"

# Actuals (#2632): chars/4 over the git diff of the six files this plan changed (74001 bytes)
actuals:
  tokens: 18500
  tasks: 3
  commits: 3
  plan_head_before: 2d22f720ff27f3d9872a9dc964d1fddcbff11d02
  plan_head_after: 518697ed0569b1adbaba0bbacc15120e38d7c4d7

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Template as an asset: named sections, one strict substitution per section, no delimiter left in output"
    - "Guards as data-free checks that return problem kinds; messages never echo the matched value"
    - "Placement by unique_path plus write_atomic; the render writes nothing when a guard fails"

key-files:
  created:
    - skills/ai-kit-spec-goal-prompt/assets/prompt-template.md
    - skills/ai-kit-spec-goal-prompt/scripts/gp_render.py
    - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
    - tests/test_ai_kit_spec_goal_prompt_render.py
  modified:
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "Fixed rule text longer than 200 characters is split across rule lines (readiness step, QUOTA directives A and B); the wording is otherwise verbatim."
  - "D-28 supersedes D-25's 1,500-character figure for the OpenGSD block. The block holds the rails: the phases 16, 16.1, 17 fixture renders 4,532 characters and 52 rule lines. The 7,000-character ceiling is the derived bound. The 1,500 figure survives only as the 1,800-character /goal condition budget."
  - "The /goal condition cap (4,000 code points) is enforced by check_condition; the 1,800 budget is a generation failure in check_text, as Task 2 specifies."
  - "Readiness problems are render warnings in stdout and never written into the file, so plan_rule_lines takes no readiness flag."
  - "write_atomic refuses an existing target as a second guard behind choose_path."
  - "Turn cap in STOP IF is 200 (a Claude's-discretion default; the SPEC names no number)."

patterns-established:
  - "Guard tests pair one clean document (no problems) with one inserted violation per forbidden kind"
  - "Boundary tests at 4,000 and 4,001 code points, and the 3,000 two-byte case that proves code points, not bytes"

requirements-completed: []  # GPS-02..04 are listed in the plan, but the renderer alone does not complete them: the render CLI and SKILL.md land in 27-09/27-10, and the R18/R19 parity test in 27-09. Same precedent as 27-05.

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 06: Prompt template, guards and the OpenGSD render Summary

**The OpenGSD goal prompt renders end to end: a strict `§§` template, fixed rail sections within the 200-character and 60-line budgets, guards that refuse a forbidden text, and one dated, atomically written file in `.planning/goals/`**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 3 of 3 completed, one commit each
- **Files created:** 4; **files modified:** 2 (test-group listings only)

## Accomplishments
- The template asset holds the FILE and BLOCK_INLINE sections. `PromptTemplate` uses the `§§` delimiter, and `$?`, `${PIPESTATUS[0]}` and JSON braces stay literal. `fill` is strict: a missing key raises `GuardError`.
- `gp_sections` builds the eleven labeled sections (OBJECTIVE to REPORT). `cross_ai: true` is the first rule of RULES FOR EVERY PLAN, unless native execution was chosen. Both QUOTA directives (A: this session's wake, B: the cross-AI children) sit under separate bullets, with the R18 and R19 literals present.
- `check_text` refuses: `--no-verify`, a skipped test tier, a jev mention without "advisory", jev inside DONE WHEN or STOP IF, the home path, a configured secret, `sk-`/`ghp_` shapes, the delimiter, a flag token after line 1 of the block, more than 60 rule lines, a rule line over 200 characters, a block over 7,000 characters, a `/goal` condition over 1,800 characters, a four-backtick token outside a fence, a wrapper over three sentences or 15 percent of the file, and a DONE WHEN without "Unit tests alone never count as done."
- `check_condition` enforces the 4,000 code-point cap (4,000 passes, 4,001 fails). `check_fields` refuses a machine path in `output_dir` or `work_set.files`, and names the field, never the value.
- `choose_path` places OpenGSD and GSD goals in `.planning/goals/`, superpowers goals in `docs/superpowers/goals/`, and kind `none` in a git-ignored `tmp/`. A name collision gets `-2`, then `-3`.
- `render(detect, answers, ctx)` writes the phases 16, 16.1, 17 fixture to `.planning/goals/2026-10-31-phases-16-16-1-17.md`. Its first line is `/gsd-autonomous --from 16 --to 17 --converge`, and it returns the contract stdout dict. Readiness problems come back as `warnings`, never in the file.
- 69 tests in `tests/test_ai_kit_spec_goal_prompt_render.py`: `TestTemplateAndSections` (18), `TestGuards` (28), `TestDoneLines` (4), `TestPlacement` (8), `TestRenderOpenGsd` (11).

## Task Commits

1. **Task 1: template asset, strict engine and the fixed OpenGSD sections** - `efea775` (feat)
2. **Task 2: guards and budgets that fail generation** - `c3c0c3c` (feat)
3. **Task 3: done-when lines, file placement and the OpenGSD render** - `518697e` (feat)

**Plan metadata:** recorded in the docs commit that adds this file (see the completion report).

## Files Created/Modified
- `skills/ai-kit-spec-goal-prompt/assets/prompt-template.md` - FILE and BLOCK_INLINE sections; the block uses a four-backtick fence
- `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py` - `PromptTemplate`, `load_template`, `fill`, the guards, `RenderContext`, `choose_path`, `write_atomic`, `render` (stdlib only)
- `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py` - section builders, `assemble_rails`, `rail_sections`, `done_lines` (stdlib only)
- `tests/test_ai_kit_spec_goal_prompt_render.py` - 69 tests; the render writes only into a `TemporaryDirectory` git repository
- `Makefile`, `.pre-commit-config.yaml` - test-group listings regenerated with `tools/gen_test_groups.py`

## Deviations from Plan

### Plan-shape and spec-conflict changes

**1. [Spec conflict] Fixed text longer than 200 characters was split.** The plan says every fixed line is at most 200 characters, but three verbatim lines exceed it: the readiness step (272 characters), QUOTA directive A (250) and directive B (224). The readiness step became three rule lines. Directive A and B each kept their bullet, with the overflow in three-space sub-lines. Wording is otherwise verbatim.

**2. [Signature] `plan_rule_lines(candidate_skills, native)`.** The plan's `readiness_ok` argument was dropped, because the text does not change with readiness. Generation-time readiness problems become `render` warnings instead.

**3. [Signature] `objective_lines(answers, scope_desc)`** takes the scope description string, not a scope dict. The plan's `phases` and `plans` forms are both string forms.

**4. [Signature] `check_text(text, *, opengsd_block, home="", secrets=())`.** The contract listed only `opengsd_block`. `home` and `secrets` were added so the whole-text scan and the secret scan run inside `check_text`, as Task 2 requires.

**5. [Placement] `HEADINGS` lives in `gp_render.py`.** It started in `gp_sections.py`, but Task 2's file list does not include that module, so it was moved back before the commit.

**6. [Order] `done_lines` was implemented in Task 1**, as the plan's Task 1 instruction says. Its exact-line tests (`TestDoneLines`) landed in Task 3, so they passed on arrival. They compare the full list of lines, so they still pin the wording.

**7. [Engine] `PromptTemplate.flags = re.NOFLAG`, not `0`.** Pyright in basic mode rejects `Literal[0]` for the `RegexFlag` declaration. The `§§` delimiter works with `string.Template` on Python 3.14, so the single-`§` fallback was not needed.

**8. [Additive guard] `write_atomic` refuses an existing target.** The plan relies on `choose_path` alone. The refusal is a second guard and changes no tested behavior.

**9. [Ledger] The plan-commit ledger was written late.** Protocol 0c says to write it before the first task commit. I wrote it after the three commits, from the parent of the first (`efea775^`, which is `2d22f72`). The measured count is the same as the protocol would give.

### Plan verify command defect

**10. [Plan defect] `uv run pyright ... | tail -n 3 | grep -q '0 errors'` returns 1.** Pyright prints a version-update banner after its summary line, so `tail -n 3` never shows the `0 errors` line. The real output reads `0 errors, 0 warnings, 0 informations`. The same defect appeared in 27-04 and 27-05.

### Auto-fixed during execution
- Ruff E501 and SIM102 findings, a pylint line-too-long, and a pyright `Literal[0]` finding were fixed before each commit. No commit used `--no-verify`.
- A docstring that described the native readiness behavior was corrected during Task 1.

## Known Stubs

These are deliberate, documented gaps, not placeholder data. Each raises `NotImplementedError` instead of emitting a wrong prompt.

| File | Behavior | Resolved by |
|------|----------|-------------|
| `skills/ai-kit-spec-goal-prompt/scripts/gp_render.py` (`render`) | Scopes other than `opengsd`, and plans work sets, raise `NotImplementedError` ("plan 27-07 adds more") | 27-07 |
| `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py` (`done_lines`) | An e2e result with `none: true`, or any mockups, raises `NotImplementedError` ("plan 27-08") | 27-08 |

These two gaps are recorded in `.planning/WINDOWS.md` (see Open Gaps).

## Threat Flags

None. The one new subprocess is a fixed-argument `git check-ignore -q tmp/x` in `_ignored`, read-only and inside the plan's register. The render writes exactly one new file in the chosen directory.

## Open Gaps (recorded in `.planning/WINDOWS.md`)

- **Non-OpenGSD and e2e-none rendering.** Covered by the Known Stubs above.
- **R18/R19 parity through `check_rules` is not in this plan.** D-22 requires it; the plan that owns it is 27-09 (Task 2). The QUOTA text was written to carry the literals, and `TestTemplateAndSections` checks them directly, but the parity test against `check_rules` has not run.
- **Golden file for the OpenGSD case** is not created here. It belongs to 27-09.

## Unverified Items

- **No agent has run the rendered block.** The `/gsd-autonomous` flags-only first line is pinned by a test, but not checked against the workflow's real argument parser in `autonomous.md`.
- **`§§` with `string.Template` is verified on Python 3.14 only.** The repo's ruff target is py312; the behavior on 3.12 is unverified.
- **`git check-ignore` is verified with a `tmp/` pattern only.** Other ignore forms are unverified.
- **Fixture host and repo values are hand-built.** The wake primitive (`CronCreate recurring`), the reviewers and the e2e commands are fixtures. No real host table or real repository was read.
- **The 1,800-character `/goal` budget** is enforced as a generation failure. No OpenGSD render emits a `/goal` block, so that path has only unit tests.
- **The DONE WHEN wording is unverified against a real e2e run.** The lines are generic and were checked only as text.

## Self-Check

- Created files exist: `assets/prompt-template.md`, `scripts/gp_render.py`, `scripts/gp_sections.py` (checked by `git ls-files` path test; `tests/test_ai_kit_spec_goal_prompt_render.py` is in the same commits).
- Commits `efea775`, `c3c0c3c` and `518697e` are ancestors of HEAD and carry `feat(27-06):` subjects.
- `commits: 3` was measured as `git rev-list --count 2d22f72...HEAD` before this docs commit.
- `python3 tools/run_unittest_parallel.py --group unit --group arch`: 69 of 69 modules passed, including `tests.test_ai_kit_spec_goal_prompt_render` (69 tests) and `tests.test_arch`.
- `ruff check`, `pylint` (10.00 on `skills/ai-kit-spec-goal-prompt/scripts`), `pyright` (`0 errors, 0 warnings, 0 informations`) and `vulture` are clean on the new files. `tests.test_gate_scope` passes.
