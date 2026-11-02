---
phase: 20-live-validation-on-codex-opencode
plan: 03
subsystem: testing
tags: [codex, opencode, gsd-core, smoke, snapshot, artifacts]

# Dependency graph
requires:
  - phase: 20-live-validation-on-codex-opencode
    provides: "20-02 comparison and resolve-model harness"
provides:
  - "Host-local Codex and opencode scratch-project smoke installation and validation"
  - "Semantic Codex/opencode protected-set snapshot guard"
  - "Labelled smoke artifacts and evidence reporting"
affects: [20-04, 20-05, 20-07]

# Actuals (#2632)
actuals:
  tokens: 13111
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns: ["Scratch-local installer with isolated HOME and XDG directories", "Explicit scratch-root trust-table snapshot exemption"]

key-files:
  created: [.planning/phases/20-live-validation-on-codex-opencode/20-03-SUMMARY.md]
  modified: [tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py]

key-decisions:
  - "Use only an already cached installer whose package version matches the checkout pin; never fetch during a smoke."
  - "Keep agent and command snapshot hashes content-sensitive, while skills and plugins are guarded by names."
  - "Limit Codex trust-table exemptions to explicitly provided scratch roots."

patterns-established:
  - "Run local installs with HOME and all XDG paths under the smoke's temporary work directory."
  - "Export scratch artifacts only after replacing machine paths with stable labels."

requirements-completed: [EVAL-04, EVAL-05]
coverage:
  - id: D1
    description: "Hermetic smoke tests cover the isolated install seam, pinned version, exact local root, failure ordering, cached installer selection, and baked-model comparisons."
    verification:
      - kind: unit
        ref: "tests.test_gsd_curated_eval.TestSmoke"
        status: pass
    human_judgment: false
  - id: D2
    description: "Semantic snapshot tests cover the scratch-root exemption and Codex/opencode allowlist boundaries."
    verification:
      - kind: unit
        ref: "tests.test_gsd_curated_eval.TestSnapshot"
        status: pass
    human_judgment: false
  - id: D3
    description: "Codex and opencode live scratch smokes completed with local pinned installs, all baked models equal, repeat installs stable, and protected host state unchanged."
    verification:
      - kind: e2e
        ref: "tmp/p20/local-codex.md and tmp/p20/local-opencode.md"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-10-18
status: complete
orchestrator_verify: "VERIFY 20-03: 3/3 passed"
---

# Phase 20: Live Validation on Codex and opencode Summary

**Codex and opencode smoke validation now exercises pinned scratch-local installs, baked model parity, and a scoped semantic host-config guard.**

## Performance

- **Duration:** About 25 minutes for this resumed segment; the initial execution dispatch stopped at its 1770-second deadline.
- **Started:** 2026-10-18T08:25:00Z (resume; approximate)
- **Completed:** 2026-10-18T08:50:45Z
- **Tasks:** 3
- **Files modified:** 3 (including this summary)

## Accomplishments
- Added local gsd-core installation for Codex and opencode scratch projects, isolated under throwaway HOME and XDG directories, with exact inventory-root/version checks and planned-versus-baked validation.
- Extended the strict snapshot to Codex and opencode configuration, agent, command, skill, plugin and hook allowlist entries; TOML trust entries are exempted only for explicitly named scratch roots.
- Added generated-path and labelled artifact reporting, `--keep-scratch`, opencode model frontmatter handling, and hermetic tests for the critical smoke and snapshot seams.
- Codex and opencode evidence both report all smoke steps passing, 35 agents matching, idempotent re-install, and an unchanged protected set.

## Task Commits

1. **Task 1: Scratch-local pinned installer and Codex smoke** - `6bd9175` (`feat(20-03): install pinned local gsd-core in host smoke`)
2. **Task 2: Codex/opencode snapshot allowlist coverage** - `4ff3832` (`test(20-03): guard codex and opencode config allowlist`)
3. **Task 3 and follow-up harness fix: opencode artifacts and valid JSON output** - `81bef8e` (`fix(20-03): write valid JSON artifacts`)
4. **Hermetic smoke and snapshot regression cases** - `e640460` (`test(20-03): hermetic smoke and snapshot cases`)

**Plan metadata:** This summary is committed separately as `docs(20-03): plan summary`.

## Files Created/Modified
- `tests/gsd_curated_eval.py` - Host-local installs, scoped snapshots, baked-model checks, artifact export, and evidence reporting.
- `tests/test_gsd_curated_eval.py` - Hermetic smoke and snapshot regression tests.
- `.planning/phases/20-live-validation-on-codex-opencode/20-03-SUMMARY.md` - Execution summary and verification record.

## Decisions Made
- Kept installer discovery strictly cache-only and required package version equality with the repository pin.
- The `resolve-model.json` artifact fix in `81bef8e` writes a real JSON newline rather than a literal backslash-n, ensuring exported JSON parses.
- Did not alter planning state, roadmap, or requirements files.

## Deviations from Plan

### Auto-fixed Issues

**1. Harness artifact JSON had an invalid literal newline escape**
- **Found during:** Task 3 live artifact verification.
- **Issue:** The resolve-model and baked JSON exports ended in the two characters `\\n`, making the JSON unreadable by strict parsers.
- **Fix:** Changed the artifact payload suffix to a real newline and added artifact-shape verification.
- **Files modified:** `tests/gsd_curated_eval.py`
- **Verification:** Parsed the exported opencode `resolve-model.json` and confirmed 35 records with model and tier fields.
- **Committed in:** `81bef8e`.

**Total deviations:** 1 harness correction.
**Impact on plan:** Correctness fix only; no scope change.

## Issues Encountered
- The initial execution dispatch ended at its 1770-second deadline before the required hermetic regression tests and summary were committed. This resumed segment completed those tests and documentation.
- The parallel unit group failed in two SIGINT tests of `tests.test_ai_kit_spec_runner_dispatch` when launched from the executor's shell. Orchestrator root cause: a background launcher starts Python with SIGINT ignored, and the tests assumed the default handler (reproduced with `trap '' INT`). Fixed in c538f93 (setUp installs `default_int_handler`); module passes with SIGINT ignored and default.
- No product defect found; no D-04 routing required.
- No smokes were rerun in this resumed segment. Existing evidence files are `tmp/p20/local-codex.md` and `tmp/p20/local-opencode.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for the subsequent phase work to consume the labelled Codex/opencode artifacts and the printed scratch-work path for snapshot checks.
- Unit group 42/42 after the SIGINT test fix (c538f93).

---
*Phase: 20-live-validation-on-codex-opencode*
*Completed: 2026-10-18*
