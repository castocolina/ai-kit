---
phase: 07-curated-gsd-config-skill
plan: 03
subsystem: config
tags: [python, cli, gsd-config, detection, regex]

# Dependency graph
requires:
  - phase: 07-curated-gsd-config-skill (Plan 01/02)
    provides: gsd_catalog.py/gsd_write.py write path (config_set/config_get), critical_agents.py, cross_ai_build.py, model_detect.py, preference_match.py, cli.py's DI convention (which_fn/run_fn/env_fn)
provides:
  - claude_md_detect.detect_claude_md_path (D-06 priority-ordered instruction-file resolution)
  - frontend_detect.detect_frontend_present (D-08 bounded package.json/README frontend-stack heuristic)
  - workflow_defaults.WORKFLOW_DEFAULTS (D-07's fixed 27-key workflow-flag bundle)
  - cli.py subcommands: detect-claude-md-path, detect-frontend, apply-claude-md-path, apply-workflow-defaults
  - D-09 merge-mode end-to-end integration test (TestMergeModeEndToEnd)
affects: [07-04 (skill registration/close-out), any future plan writing workflow.* or claude_md_path keys]

# Actuals (#2632)
actuals:
  tokens: 6032
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dependency-injected isfile_fn/read_fn detection helpers (mirrors gsd_catalog.py's isfile_fn=os.path.isfile convention) for zero-real-I/O unit testing"
    - "Bounded, re.escape()'d word-boundary regex matching for free-text signal scanning (README/doc text), distinct from exact-key-membership matching for structured manifest data (package.json dependency keys)"

key-files:
  created:
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/claude_md_detect.py
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/frontend_detect.py
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/workflow_defaults.py
  modified:
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/cli.py
    - tests/test_ai_kit_gsd_config.py

key-decisions:
  - "D-06: claude_md_path resolution checks AGENTS.md, CLAUDE.local.md, AGENTS.local.md, CLAUDE.md in that exact priority order, returning None (never a fabricated default) when none exist."
  - "D-08: frontend detection is a package.json dependency-manifest scan (exact key membership, not regex) OR a bounded README.md word-boundary text scan -- either signal alone is sufficient, a malformed package.json never short-circuits the independent README check."
  - "D-07: the workflow-defaults bundle is a fixed, planning-time-sourced 27-key literal dict, excluding the six keys owned elsewhere in this phase (ui_phase, ui_review, cross_ai_execution, cross_ai_command, cross_ai_timeout, plan_review_convergence) so no key is ever double-written across plans."
  - "Rule 1 auto-fix: gsd_write.config_set's shared _coerce_value has no Python-None handling (falls through to the literal string \"None\"), so the bundle's two None-valued entries are substituted to the string \"null\" locally inside cli.py's apply-workflow-defaults -- gsd-tools' own config-set recognizes \"null\" as its unset/clear sentinel. Kept scoped to this plan's own file rather than widening gsd_write.py's shared helper (outside this plan's declared files_modified)."

patterns-established:
  - "Detection modules (claude_md_detect.py, frontend_detect.py) are pure, dependency-injected functions with zero production I/O side effects beyond the injected fn parameters -- fully testable against fake filesystems/readers."
  - "cli.py subcommand pairs keep detection and application strictly separate (detect-frontend never calls apply-workflow-defaults itself) -- the caller/orchestrator wires the detected boolean into the apply flags, matching every other detect/apply pair in this skill."

requirements-completed: [REQ-cfg-curated-questions, REQ-cfg-writes-config]

coverage:
  - id: D1
    description: "claude_md_detect.detect_claude_md_path resolves AGENTS.md/CLAUDE.local.md/AGENTS.local.md/CLAUDE.md in priority order, or None when none exist"
    requirement: "REQ-cfg-writes-config"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestDetectClaudeMdPath"
        status: pass
    human_judgment: false
  - id: D2
    description: "frontend_detect.detect_frontend_present returns a bounded, non-raising boolean signal from package.json/README.md, with re.escape()'d word-boundary matching (fixes the next.js-as-wildcard Cycle 2 LOW finding)"
    requirement: "REQ-cfg-writes-config"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestDetectFrontendPresent"
        status: pass
    human_judgment: false
  - id: D3
    description: "workflow_defaults.WORKFLOW_DEFAULTS is exactly 27 keys with zero overlap against the five/six keys owned elsewhere in this phase"
    requirement: "REQ-cfg-curated-questions"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestWorkflowDefaults"
        status: pass
    human_judgment: false
  - id: D4
    description: "cli.py apply-workflow-defaults writes the bundle plus ui_phase/ui_review from caller-supplied flags (never hardcoded); apply-claude-md-path writes only on a non-empty path"
    requirement: "REQ-cfg-writes-config"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestApplyWorkflowDefaultsCli"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestApplyClaudeMdPathCli"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-09 merge-mode contract: a fresh project falls through Plan 01's ensure-project first, and an existing config with unrelated keys is left byte-identical after this plan's writes run"
    requirement: "REQ-cfg-writes-config"
    verification:
      - kind: integration
        ref: "tests/test_ai_kit_gsd_config.py#TestMergeModeEndToEnd::test_merge_mode_end_to_end"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-11
status: complete
---

# Phase 07 Plan 03: claude_md_path/frontend detection, D-07 defaults bundle, D-09 merge-mode proof Summary

**Priority-ordered instruction-file detection, a bounded re.escape()'d package.json/README frontend-stack heuristic, a fixed 27-key workflow-defaults bundle, and a real-subprocess D-09 merge-mode integration test -- all wired into four new `cli.py` subcommands.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-11 (this session)
- **Completed:** 2026-09-11
- **Tasks:** 2/2 completed
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments
- `claude_md_detect.detect_claude_md_path` (D-06) -- checks `AGENTS.md`, `CLAUDE.local.md`, `AGENTS.local.md`, `CLAUDE.md` in that exact priority order, returning `None` (never a fabricated default) when none exist.
- `frontend_detect.detect_frontend_present` (D-08) -- `package.json` dependency scan OR bounded, `re.escape()`'d, word-boundary README.md text scan; never raises on missing/malformed input. Added `test_next_js_dot_is_literal_not_a_wildcard` closing the cross-AI review Cycle 2 LOW finding.
- `workflow_defaults.WORKFLOW_DEFAULTS` (D-07) -- fixed, literal 27-key bundle sourced from this repo's own `.planning/config.json`, with an explicit `EXCLUDED_KEYS` frozenset documenting the six keys owned elsewhere in this phase.
- Four new `cli.py` subcommands: `detect-claude-md-path`, `detect-frontend`, `apply-claude-md-path`, `apply-workflow-defaults`.
- `TestMergeModeEndToEnd` (D-09) -- real-subprocess integration test proving both the fresh-project-falls-through-`ensure-project` path and the existing-file unrelated-keys-untouched path.

## Task Commits

Each task was committed atomically:

1. **Task 1: claude_md_path and frontend-presence detection** - `8168b54` (feat)
2. **Task 2: D-07 workflow-defaults bundle, wiring, and the merge-mode end-to-end integration test** - `90233cd` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/claude_md_detect.py` - D-06 priority-ordered instruction-file path resolution
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/frontend_detect.py` - D-08 bounded frontend-presence heuristic
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/workflow_defaults.py` - D-07 fixed 27-key workflow-defaults bundle
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/cli.py` - four new subcommands (detect-claude-md-path, detect-frontend, apply-claude-md-path, apply-workflow-defaults)
- `tests/test_ai_kit_gsd_config.py` - 16 new tests across 6 new test classes (`TestDetectClaudeMdPath`, `TestDetectFrontendPresent`, `TestWorkflowDefaults`, `TestApplyWorkflowDefaultsCli`, `TestApplyClaudeMdPathCli`, `TestMergeModeEndToEnd`)

## Decisions Made
- Kept the `None` → `"null"` coercion fix local to `cli.py`'s `apply-workflow-defaults` rather than widening `gsd_write.py`'s shared `_coerce_value` helper, since `gsd_write.py` is outside this plan's declared `files_modified` and the fix only needs to apply at this one call site (see Deviations below).
- Used exact dependency-key membership (not regex) for the `package.json` signal, and bounded `re.escape()`'d word-boundary regex only for the free-text README signal -- the two data shapes (structured manifest keys vs. prose text) warrant different match strategies, and the exact-membership approach for `package.json` is inherently immune to the "reactive"-contains-"react" substring trap without needing its own regex.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `gsd_write.config_set`'s value coercion mishandled Python `None`**
- **Found during:** Task 2 (D-09 integration test, running against the real installed gsd-core)
- **Issue:** `workflow_defaults.WORKFLOW_DEFAULTS` includes two `None`-valued entries (`code_review_command`, `plan_bounce_script`), matching this repo's own reference `.planning/config.json`. `gsd_write.config_set`'s `_coerce_value` (from Plan 01) has no special case for `None` -- it falls through to `str(None)` == `"None"`, which gsd-tools' `config-set` persists verbatim as the literal string `"None"` rather than recognizing it as the `"null"` unset/clear sentinel its own parser defines (`config.cjs` line 714). The real-subprocess `TestMergeModeEndToEnd` test caught this immediately (`AssertionError: 'None' != None`); it would have silently written a wrong string value in production.
- **Fix:** In `cli.py`'s `apply-workflow-defaults`, substitute the literal string `"null"` for any `WORKFLOW_DEFAULTS` value that is `None` before calling `config_set` -- `gsd-tools` then correctly clears/unsets that key rather than storing a bogus string.
- **Files modified:** `skills/ai-kit-gsd-config/ai_kit_gsd_config/cli.py`
- **Verification:** `TestMergeModeEndToEnd::test_merge_mode_end_to_end` passes against the real installed gsd-core; full `tests.test_ai_kit_gsd_config` suite (87 tests) passes.
- **Committed in:** `90233cd` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** Necessary for the D-09 integration test to pass against real gsd-tools; no scope creep -- fix stayed within this plan's own `cli.py`, not the shared `gsd_write.py` module outside `files_modified`.

## Issues Encountered
- This worktree's branch was created before Plans 07-01/07-02 were merged to `main`, so `.planning/phases/07-curated-gsd-config-skill/` and `skills/ai-kit-gsd-config/` did not initially exist on disk in this worktree. Fast-forwarded the worktree branch to `main` (`git merge --ff-only main`) before starting -- a clean fast-forward, no conflicts, no divergent commits lost.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 07-04 (skill registration/close-out: `SKILL.md`, `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml`) can proceed -- confirmed by reading 07-01-SUMMARY.md/07-02-SUMMARY.md's precedent that `make test`/`make lint`/`pyproject.toml` registration is intentionally deferred to 07-04, not a gap in this plan. `python3 -m unittest tests.test_ai_kit_gsd_config -v` (87 tests, OK) was run directly per this plan's own `<verify>` blocks; the full `make test` (1595 tests + 16 install tests) and `make lint` were also run standalone to confirm zero regressions to the existing baseline.
- No blockers.

---
*Phase: 07-curated-gsd-config-skill*
*Completed: 2026-09-11*

## Self-Check: PASSED

- FOUND: `skills/ai-kit-gsd-config/ai_kit_gsd_config/claude_md_detect.py`
- FOUND: `skills/ai-kit-gsd-config/ai_kit_gsd_config/frontend_detect.py`
- FOUND: `skills/ai-kit-gsd-config/ai_kit_gsd_config/workflow_defaults.py`
- FOUND: commit `8168b54`
- FOUND: commit `90233cd`
