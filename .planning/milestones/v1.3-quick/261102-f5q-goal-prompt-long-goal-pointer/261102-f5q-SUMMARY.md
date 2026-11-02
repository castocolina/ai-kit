---
phase: quick-261102-f5q
plan: 01
subsystem: goal-prompt
tags: [goal-prompt, pointer-form, skill-judge, evidence]
status: complete
requirements: [GPS-02]
commits: 6
plan_head_before: 23ba001
---

# Quick 261102-f5q: long /goal condition behind a pointer

A `/goal` condition over 1,000 characters no longer sits on the `/goal` line. The first block line is a short pointer to the file's own `## Full goal` section.

## Commits
- 7dfad91: `gp_render.py` (threshold, `goal_style`, pointer line, `## Full goal` section, `goal_form`, `full_chars`, unverified warning) with its render, CLI and golden tests and the pointer golden.
- 5c8d4fb: eval `precise-long-goal-pointer` and a test that reproduces its assertions on the real CLI.
- ce8ad9f: SKILL.md, README, references (new `references/evidence.md` holds the sources of the closed checks), drift tests, the Phase 27 capture follow-up.
- bfe6ec7: generated test listings (`tools/gen_test_groups.py`) register the new test module.
- 1bbcc7d: the skill-judge checker takes round 6 and a referee-one report. Later: 7b61f3c (Full objective section), bb364f7 (eval), 3577128 (docs), the round 7 checker and report commits.
- The round 6 reports and the verdict update are in the last docs commit.

## Decisions
- Threshold `GOAL_POINTER_THRESHOLD` = 1,000 characters: below the 1,800 budget, above the fixed text (about 300) plus the scope clause cut at 600.
- `goal_style` is `auto` (default), `inline` or `pointer`; an unknown value is refused (exit 2). Only the `goal` block changes; the default golden is untouched.
- Rule lines keep the 200-character cap; the `## Full goal` body wraps at 100 columns with no cap and is checked as one line by the text guards.

## Verification
- `python3 tools/run_unittest_parallel.py --group unit --group arch`: 76/76 modules. `make validate`: ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest (core) and unittest (wizard) passed.
- The host following `/goal read document ... at section ...` stays unverified; render warns each time.

## Follow-up (owner decision)
- A shortened objective now ends with `(full text: <path> section Full objective)` and the file keeps the whole text in `## Full objective` (before `## Full goal`); the false re-render sentence and the `tmp/` statements in SKILL.md are corrected and tied to the code by drift tests.

## Known open
- Skill-judge round 7: referee-one 94.4%, referee-three 87.2%, verdict UNRESOLVED (87.2 is below the 90.4 base); `--gate` is pending until an owner decision. Medium and low findings are listed in `27-SKILL-JUDGE.md`.
