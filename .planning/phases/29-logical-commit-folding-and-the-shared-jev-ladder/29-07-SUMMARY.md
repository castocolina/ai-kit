---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 07
subsystem: goal-prompt
tags: [jev, goal-prompt, installed-skill-lookup, black-box, goldens, stdlib]

# Dependency graph
requires:
  - phase: 29-03
    provides: jev_review.py detect entry point and the SKILLS_ROOTS lookup order in jev-fast-decision
provides:
  - goal-prompt reaches jev only through jev-fast-decision's own detect entry point, found by its installed-skill lookup
  - generated prompt text and SKILL.md treat jev as a black box: ask the skill, follow its SKILL.md
affects: [29-11 (goal-prompt no longer calls decide.py; spec-discuss is the last caller), 29-15 (goal-prompt on the cross-skill allowlist), 29-16 (judges the SKILL.md change against the 29-05 baseline)]

# Actuals (#2632): chars/4 over the realized diff (7147059..f3cc63e, 29968 chars)
actuals:
  tokens: 7492
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "lookup copy with an AST parity check: gp_host.SKILLS_ROOTS equals jev_ladder.py's SKILLS_ROOTS"
    - "jev_status returns a fixed reason per failure; exit 2 from detect means an old client"

key-files:
  modified:
    - skills/ai-kit-spec-goal-prompt/scripts/gp_host.py
    - skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py
    - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
    - skills/ai-kit-spec-goal-prompt/SKILL.md
    - tests/test_ai_kit_spec_goal_prompt_host.py
    - tests/test_ai_kit_spec_goal_prompt_cli.py
    - tests/test_ai_kit_spec_goal_prompt_pointer.py
    - tests/test_ai_kit_spec_goal_prompt_objective.py
    - tests/test_ai_kit_spec_goal_prompt_golden.py
    - tests/test_ai_kit_spec_goal_prompt_render.py
    - tests/test_ai_kit_spec_goal_prompt_variants.py
    - tests/fixtures/goal_prompt/golden/opengsd-goal-pointer.md
    - tests/fixtures/goal_prompt/golden/opengsd-recommended.md

key-decisions:
  - "find_jev uses the --jev-client override only when it names a file; otherwise the installed-skill lookup runs (plan wording)."
  - "Exit 2 from detect maps to 'jev-fast-decision too old: re-run the ai-kit installer'; any other non-zero exit is 'detect failed'."
  - "The gray-area line names the jev-fast-decision skill. The two jev-absence guards exempt only that line; every other non-report line must still not mention jev."

patterns-established:
  - "Host tests run jev_status with a scratch HOME and an empty own root; the real-seam case uses a synthetic argparse client that lacks detect."

requirements-completed: [JEV-06]

plan_head_before: 7147059b7f9d1aef57a1244e310de6eca80090c2
plan_head_after: f3cc63ef4a52303f9a144ddea98d797c9dd6b8c3
commits: 2

# Metrics
duration: "about 8 min (start snapshot file mtime 22:16:47Z to this write at 22:24:49Z)"
completed: 2026-11-04
status: complete
---

# Phase 29 Plan 07: goal-prompt reaches jev as a black box Summary

**goal-prompt finds jev-fast-decision through its installed-skill lookup and runs only `detect`; the generated text and SKILL.md say only "ask the jev-fast-decision skill and follow its SKILL.md"**

## Performance

- **Duration:** about 8 min (start snapshot file mtime to this write; not separately timed)
- **Tasks:** 2 of 2
- **Files modified:** 13

## Accomplishments

- `gp_host.py`: `DECIDE_CLI` removed. `JEV_ENTRY_REL`, a `SKILLS_ROOTS` copy of jev_ladder.py's table, `skills_roots`, `find_jev`, and `jev_status(seams, jev_client, env, own_root)` added. `jev_status` runs `[sys.executable, <jev_review.py>, "detect"]` and nothing else.
- Named reasons: `jev-fast-decision not installed` (no run), `jev-fast-decision too old: re-run the ai-kit installer` (exit 2), `detect failed`, `detect output not json`, `no usable backend`; success reasons unchanged.
- `goal_prompt.py detect`: `--jev-client PATH` replaces `--decide-cli`, and the lookup searches the same skills dir as the other sibling CLIs.
- `gp_sections.py`: the gray-area line and the advisory report line (split into two fixed lines, 189, 162 and 105 characters) ask the jev-fast-decision skill and follow its SKILL.md. Each stays under the 198-character cap.
- `SKILL.md`: the "When something is missing" jev row names the installed skill and both absence reasons. The jev NEVER line points at the skill's SKILL.md.
- Goldens regenerated (`UPDATE_GOLDEN=1`). The only golden changes are the three gray-area lines. `tmp/p29/07/golden_diff.sh` printed `golden diff: jev lines only`, and the diff was read by hand.

## Task Commits

1. **Task 1: goal_prompt detect reports jev through the installed entry point, or a named reason** - `35d77d0` (feat)
2. **Task 2: black-box jev text in the generated prompt and SKILL.md; goldens regenerated** - `f3cc63e` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pylint too-many-returns on `jev_status`**
- **Found during:** Task 1 commit (pylint hook, R0911, 7/6 returns). The commit was refused; nothing was committed.
- **Fix:** Moved the detect-JSON reading into `_jev_reading`. `jev_status` keeps four returns and pylint is 10.00/10 on gp_host.py and goal_prompt.py. The fixed commit is `35d77d0`.

### Test expectation adjusted to the plan's own text

**2. [Plan-text consequence] The two jev-absence guards in `test_ai_kit_spec_goal_prompt_variants.py` exempt the gray-area line**
- **Found during:** Task 2 test run. Both guards assert that jev is named only in the REPORT section, and they failed on the new gray-area line, which names the skill by design (plan step "ask the jev-fast-decision skill").
- **Fix:** Exempted only lines starting with `- Gray areas:`. Every other non-report line is still checked. The advisory-line test and the cap test pass.

### Process notes

**3. Commit ledger written after the last task commit.** The plan's protocol 0c asks for the ledger before the first commit. It was written at close from the start base `7147059`, which the worktree assertion had already verified as HEAD at start. `commits: 2` is measured from that ledger.

**4. jev client path.** The brief's `$HOME/.claude/skills/jev-fast-decision/scripts/jev_review.py` form was refused by the worktree shell guard (runtime-expanded program path). The call used the in-repo copy `skills/jev-fast-decision/scripts/jev_review.py` with the same flags.

**5. Negative test contains the old flag name.** `test_detect_takes_jev_client_and_rejects_the_old_flag` asserts that `--decide-cli` is rejected. The plan's `rg` acceptance line therefore returns that one line (cli test line 330). It is intentional. The rest of the decide-CLI names are gone from the goal-prompt skill, its fixtures and its tests.

**6. Acceptance `rg -c "follow its SKILL.md" gp_sections.py` prints 1, not 2.** The report line splits the phrase across two string literals (`"... (follow its "` and `"SKILL.md), ..."`), so a line-based count sees it once. The rendered text has it twice: the 189-character gray-area line and the 162-character advisory line.

### Not done in this plan

- **skill-judge not run.** SKILL.md has a material change. AGENTS.md requires the skill-judge loop before a skill is marked complete. The plan defers this to plan 29-16, which judges the change against the 29-05 baseline. This SKILL.md is not yet judged.

## Self-Check

**Verified:**
- Modified files all exist and are committed (`git status --short` clean after the task commits).
- `35d77d0` and `f3cc63e` are ancestors of HEAD.
- `SKILLS_ROOTS` parity with `skills/jev-fast-decision/scripts/jev_ladder.py` (AST literal comparison): exit 0.
- `python3 tmp/p29/07/scope.py test` (one `make test`, per-run TMPDIR): exit 0, 1m12s, zero `failed:` lines. Every tier reported all modules passed.
- The four goal-prompt modules changed in Task 2 pass; the five Task 1 modules passed at `35d77d0`.
- `golden_diff.sh`: `golden diff: jev lines only`.
- `scope.py close`: `clean`.

## Self-Check: PASSED

## jev Call Log

Client: in-repo `skills/jev-fast-decision/scripts/jev_review.py`, env `GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20`, one batch of two items at reviewed_head `f3cc63e`.

- **c1** (choice: which way to keep the jev guard meaningful): answer `a` (exempt only the gray-area line), confidence 0.83, backend typesafe (consent on file), needs_fallback false. **Did:** implemented option a.
- **f1** (criterion: exempting only the gray-area line still fails the build when another section names jev): answer `supported`, confidence 0.31, needs_fallback true on both laya and typesafe. **Did:** verified by reading the guard code and by the passing variants module; the answer was not used as a gate.

## Known Stubs

None.

## Threat Flags

None. `detect` output is still reduced to booleans and fixed reason strings, as the plan's threat model requires.

## Worktree Notes

- `.venv` (gitignored) created by `uv run` in the worktree.
- `.claude/gsd-core` and `.claude/scripts` copied from the main checkout (gitignored, never committed).
- `scope.py close` reported only other sessions' processes and temp dirs (`reported (not this run)`); nothing from this run was left.
