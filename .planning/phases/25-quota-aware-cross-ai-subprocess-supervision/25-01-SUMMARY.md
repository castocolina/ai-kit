---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 01
subsystem: infra
tags: [cross-ai, runner, subprocess, self-test]

requires:
  - phase: 18.1-curated-config-v2
    provides: the template-6 cross-ai runner and its black-box self-test harness
provides:
  - a runner call that spawns exactly one CLI, the first of --prefer or CONFIG.prefer
  - every status line ending action=stop, with the status table holding exit codes only
  - a self-test matrix proving no second CLI runs after any first-CLI outcome
affects: [25-02, 25-03, 25-04, 25-05, 25-06, 25-07]

actuals:
  tokens: 1664
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "The prefer order is a menu: only its first entry is ever evaluated or spawned"
    - "finish ignores any action override and always prints action=stop"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs

key-decisions:
  - "Owner decision 2026-10-24: no automatic fallback; the first prefer entry is the only CLI that runs"
  - "The exec-mode review-only refusal evaluates only the first entry, never the whole menu"

patterns-established:
  - "A missing or model-less first choice is reported (not_installed exit 127, no_model exit 2), never replaced"

requirements-completed: [QTA-03]

coverage:
  - id: D1
    description: "A runner call spawns only the first CLI of --prefer or CONFIG.prefer and reports that CLI's own outcome"
    requirement: QTA-03
    verification:
      - kind: e2e
        ref: "node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test (no-second-cli-*, config-prefer-first-only, not-installed-first, no-model-first)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every status line ends action=stop and the status table rows carry only exit codes"
    requirement: QTA-03
    verification:
      - kind: other
        ref: "grep -cE \"action: '(stop|fallback|retry-later)'\" skills/ai-kit-spec-review/references/cross-ai.mjs prints 0; full --self-test prints self-test ok"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-01: 2/2 passed"
---

# Phase 25 Plan 01: One CLI per call Summary

**The runner spawns exactly one CLI per call, the first of `--prefer` or `CONFIG.prefer`, and every status line ends `action=stop`.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-10-24T20:29:00Z
- **Completed:** 2026-10-24T20:46:18Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- `main` runs only `cands[0]`; a missing binary ends `status=not_installed` exit 127 and a missing model ends `status=no_model` exit 2, each naming that CLI, with no other CLI spawned.
- `STATUS_TABLE` rows keep only `exit`; `finish` ignores any `fields.action` override and always prints `action=stop`. The router billing rule keeps only its exit-75 half. `tryNextCli` and the dirty-tree demotion are gone.
- The exec-mode review-only refusal evaluates only the first entry, so a later review-only entry never rejects an exec run whose first choice has an exec formula.
- A generated self-test matrix pins every first-CLI outcome (crash, quota, billing, auth, permission_blocked, empty_answer, no_change, timeout, bad_model, contract_violation) plus `CONFIG.prefer` to spawn no second CLI.

## Task Commits

Each task was committed atomically:

1. **Task 1: One CLI per call, end to end** - `a063759` (feat)
2. **Task 2: The no-second-CLI matrix** - `c974820` (test)

**Plan metadata:** committed with Task 2 (docs: complete 25-01 plan)

## Files Created/Modified
- `skills/ai-kit-spec-review/references/cross-ai.mjs` - single-CLI `main`, `action=stop` status lines, the no-second-CLI self-test matrix

## Decisions Made
None - followed the plan and the owner's 2026-10-24 decision as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Deleted tests

None

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for 25-02 (the pattern table and `classifyStop` land on this single-CLI loop).
- `--self-test` prints `self-test ok` and stays well under the 120 s budget.
- The removed literals (`tryNextCli`, `trying the next CLI`, `retry-later`, `action=fallback`) are absent from the template, comments and case names included.

## Self-Check: PASSED

- `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` prints `self-test ok` (full run, plus the fourteen named Task 2 cases).
- `grep -cE "action: '(stop|fallback|retry-later)'"` prints 0.
- `grep -c "name: 'no-second-cli-"` prints 1 (one generator, not ten copies).

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-24*
