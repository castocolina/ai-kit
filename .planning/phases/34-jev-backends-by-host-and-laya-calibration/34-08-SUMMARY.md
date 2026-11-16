---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 08
subsystem: skills
tags: [jev, guard, zen, opencode, delegation, config-record, requirements, roadmap]

# Dependency graph
requires:
  - phase: 34-06
    provides: probe learning, the Laya and TypeSafe record files, --check-updates and the config set keys
  - phase: 34-07
    provides: the finished jev-fast-decision text (the guard scans it and may reword it)
provides:
  - tests/test_jev_fast_decision_guard.py, the no-Zen, no-opencode-backend and no-delegation guard over the skill tree
  - the [jev] keys, session overrides and jev records in docs/config/design.md, README.md, tools/hooks/README.md and curated-config's session-gate sentence
  - D-15 amendments of JEV-01, JEV-03, JEV-07, JEV-10 and Phase 34 success criteria 1, 4 and 6
affects: [34-09 live Laya calibration (updates the limit sentence), 34-10 judge loop (re-judges jev-fast-decision and the curated-config sentence)]

# Actuals (#2632)
actuals:
  tokens: 16802    # chars/4 over the base..HEAD diff of the three commits (67208 chars)
  tasks: 3
  commits: 3       # MEASURED: git rev-list --count 65d6927..HEAD (plan ledger)
plan_head_before: 65d6927371e2ecb9f4e71d8a65c05ca891fe3428
plan_head_after: 4a825ff1d0b2052531deed702b42dda2f6179d38

# Tech tracking
tech-stack:
  added: []
  patterns: [sentence-level guard: prose is joined across wrapped lines and split into sentences, a negation exempts only the verb it directly precedes, every rule has a violating fixture]

key-files:
  created:
    - tests/test_jev_fast_decision_guard.py
  modified:
    - Makefile
    - .pre-commit-config.yaml
    - docs/config/design.md
    - README.md
    - tools/hooks/README.md
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "The guard passed the skill tree as Plan 07 left it on the first run, so no skill sentence was reworded and no pattern was narrowed."
  - "The guard's allow-list is by phrase and line-level: a line that holds an allowed phrase passes even if it also used opencode as a backend. This is the stated limit of the rule, not a gap found in the tree."
  - "Every jev script cite in docs/config/design.md now names a line that holds a name the same design line writes in backticks (27 cites, checked by a scratch script)."
  - "curated-config's session-gate sentence and _JEV_SESSION_NOTE keep the substrings GSD_PATH_JEV=1 and GSD_PATH_JEV_TIMEOUT_SECONDS, which two tests pin."

patterns-established:
  - "The delegation rule reads sentences: a verb-bound negation (`never installs`) clears only its own verb, and `not only` / `not just` are not negations."

requirements-completed: [JEV-13, JEV-01, JEV-07]

# Metrics
duration: not recorded (start time was not captured in this run)
completed: 2026-11-15
status: complete
---

# Phase 34 Plan 08: jev guard, config record and D-15 amendments

**A guard test keeps Zen, an opencode backend and install delegation out of jev-fast-decision (it passes the real tree and each rule has a violating fixture), and the config record, READMEs and REQUIREMENTS/ROADMAP now match the code**

## Performance

- **Duration:** not recorded
- **Tasks:** 3 of 3
- **Files changed:** 9 modified, 1 created

## Accomplishments

- `tests/test_jev_fast_decision_guard.py`: six tests. The real skill tree passes; the backend table names exactly `laya` and `typesafe`; each rule (Zen, opencode outside a host-folder line, tools-installer, sentence-level delegation, package-manager or container code strings, table names) fails on a violating fixture; the delegation rule catches a wrapped instruction, a named repository without llm-env, an unrelated negation, a delegate phrasing, a `not only` hand-off and a docstring; allowed lines pass; an empty tree passes.
- Regenerated test-group listings (`Makefile`, `.pre-commit-config.yaml`) so the new module runs in the unit tier; `tests.test_gate_scope` passes.
- `docs/config/design.md`: the `[jev]` table bullet, the Inventory writer and reader cells for the project and user `config.toml` rows, the consent and secrets cites, the environment-only overrides (`KNOB_ENV`, `URL_ENV`, the timeouts), and the jev learning records under the state folder. Every cite was refreshed to its current line.
- `README.md` and `tools/hooks/README.md`: the `[jev]` keys and the hooks' knob (`[jev] enabled`, `GSD_PATH_JEV=0`, no user-layer read).
- curated-config: one sentence in `SKILL.md` and `_JEV_SESSION_NOTE` now say jev runs unless `[jev] enabled` is false, with `GSD_PATH_JEV=1` or `0` overriding it for one session (fact correction only).
- D-15 amendments appended in the existing `*(amended ...)*` style: JEV-01, JEV-03, JEV-07, JEV-10 and Phase 34 criteria 1, 4 and 6. No progress table, checkbox or `**Plans**:` line changed.

## Task Commits

1. **Task 1: the guard test and the regenerated test-group listings** - `8d8bba5` (test)
2. **Task 2: design record, READMEs and curated-config's one sentence** - `1fc6aa3` (docs)
3. **Task 3: REQUIREMENTS and ROADMAP amendments** - `4a825ff` (docs)

The phase-wide gates (ruff, pyright, pylint, vulture, test-unit) were run after Task 3 and were not separate commits.

## Files Created/Modified

- `tests/test_jev_fast_decision_guard.py` - the guard: `skill_files`, `prose_units`, `delegation_problem`, `text_problems`, `code_problems`, `table_problems`, `tree_problems` and `TestJevGuard`
- `Makefile`, `.pre-commit-config.yaml` - regenerated by `tools/gen_test_groups.py`
- `docs/config/design.md` - `[jev]` table, Inventory writer/reader cells, environment-only overrides, state and records
- `README.md`, `tools/hooks/README.md` - `[jev]` settings and the hooks' knob
- `skills/ai-kit-gsd-curated-config/SKILL.md`, `.../recommend.py` - one sentence and `_JEV_SESSION_NOTE`
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` - D-15 amendments

## Opencode lines in the skill tree (how the guard treats each)

The skill tree had five `opencode` lines before the guard. All five are host-folder lines and pass the allow-list; none is a backend name.

- `reference.md:196` "Claude Code and opencode read `~/.claude/skills`": passes on the phrase "Claude Code and opencode".
- `reference.md:198` "...which opencode, pi and Cursor also read...": passes on "opencode, pi and Cursor".
- `reference.md:208` the lookup row `${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills`: passes on "opencode/skills".
- `scripts/jev_ladder.py:40` the lookup root `"opencode/skills"`: passes on "opencode/skills".
- `evals/trigger-queries.json:15` the near-miss query "...codex and opencode both review every plan...": passes on "codex and opencode both review".

The guard was not reworded for any of them. A test fixture confirms that `opencode` as a backend name (`Use the opencode backend for long items.`) fails.

## Decisions Made

- No sentence of the skill tree needed rewording: the first run of the guard over Plan 07's text reported nothing, so the Task 1 step 2 contingency did not apply.
- The design record's cites are checked by `tmp/p34/08/cites_check.py` (scratch, not committed): each cite must share its design line with a backticked name that appears on the cited lines. Result: `cites: 27 checked`, exit 0.
- The REQUIREMENTS and ROADMAP amendments are text-only; `tmp/p34/08/amend_check.py` (scratch) confirms each amended block and the three Phase 34 criteria. Result: `amend: ok`.

## Deviations from Plan

**1. [Rule 3 - Blocking] Line-length lint on the new test module**
- **Found during:** Task 1 commit (first attempt)
- **Issue:** ruff E501 on five lines of `tests/test_jev_fast_decision_guard.py`; the hook blocked the commit, so nothing was committed on that attempt.
- **Fix:** wrapped the five lines; the commit then passed every hook.
- **Files modified:** `tests/test_jev_fast_decision_guard.py`
- **Verification:** ruff passed on the commit's hook run; `make ruff` exits 0.
- **Committed in:** `8d8bba5`

**2. [Environment, not fixed] check-dogfood cannot pass in this worktree**
- **Found during:** Task 3 gate run (`make check-dogfood`, exit 2)
- **Issue:** the worktree has no project-local `.claude/gsd-core` (git-ignored, not in the worktree checkout), so the no-write guard reports the two real-GSD integration tests as skipped, and the live project as unguarded. The judge notes below do not fail the gate.
- **What I tried:** copied the main checkout's project-local `.claude/gsd-core` into this worktree's ignored `.claude/`. Its `bin/gsd-tools.cjs` then crashed on every invocation: `bin/lib/command-roster.cjs` line 36 requires `../../../scripts/fix-slash-commands.cjs`, a file that exists in neither checkout (a read-only grep confirms the main checkout's install has the same line). With the copy, the no-write guard ran and three real-GSD e2e tests failed on that crash.
- **Action:** moved the copy out of the worktree's `.claude/` to `tmp/p34/08/gsd-core-copy` (no delete). The worktree is back to its delivered state, and check-dogfood exits 2 with the two "unguarded" problems.
- **Status:** not caused by this plan's changes; it is a defect of the installed GSD copy that the repo does not fix. It needs an owner decision (the install's dev-only require, or a repo-side `scripts/fix-slash-commands.cjs`). Until then `make check-dogfood` cannot print `check-dogfood: ok` in any worktree, and the main checkout's copy would hit the same crash.

## Issues Encountered

- **Judge notes, not run (plan 34-10 owns the judge loop).** check-dogfood prints notes for stale digests (ai-kit-usage-metrics, jev-fast-decision, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-cross-ai, ai-kit-session-wake, ai-kit-spec-execute-superpowers, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss) and facts drift for jev-fast-decision, ai-kit-spec-review and ai-kit-spec-goal-prompt. This plan adds two changes the re-judge must see: the curated-config sentence (fact-only, per the plan) and the new guard module, which the commit mapper counts as a covering module of jev-fast-decision. I did not verify which of the other stale digests predate this plan; 34-10 should re-judge with both changes in view.
- **Gates run:** `make ruff`, `make pyright`, `make pylint`, `make vulture` and `make test-unit` each exit 0. The unit group runs 126/126 modules and the arch group 1/1 module (`tools/run_unittest_parallel.py --group unit` and `--group arch`, both with the rails).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 34-09 (live Laya calibration) updates the limit sentence in `SKILL.md` and `backends/laya.md`; the design record and REQUIREMENTS/ROADMAP amendments already say the sentence cites the latest calibration.
- 34-10 (judge loop) owns the judge records; `check-dogfood` will stay red until the records are refreshed and the GSD install defect above is resolved.

## Self-Check: PASSED

- The three task commits (`8d8bba5`, `1fc6aa3`, `4a825ff`) are ancestors of HEAD.
- `tests/test_jev_fast_decision_guard.py` is tracked.
- Count lines: `=== tests.test_jev_fast_decision_guard: ok in 0.2s Ran 6 tests`; `=== tests.test_gate_scope: ok ... Ran 62 tests`; `4/4 modules passed` for the four Task 2 modules; `amend: ok`; `cites: 27 checked`; unit `126/126 modules passed`; arch `1/1 modules passed`.

---
*Phase: 34-jev-backends-by-host-and-laya-calibration*
*Completed: 2026-11-15*
