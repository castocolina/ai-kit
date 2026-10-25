---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 10
subsystem: docs
tags: [failure-ladder, cross-ai, quota, owner-captures]

requires:
  - phase: 25-08
    provides: route resolution the docs describe
  - phase: 25-09
    provides: the subprocess quota policy reference and the one-shot caller contract
provides:
  - review skill and dispatch reference describing the runner failure ladder
  - curated-config skill, runner reference and README describing one CLI per call
  - owner capture kit with every result not run (owner)
affects: [25-11]

actuals:
  tokens: 3500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns: [docs link the policy reference instead of restating the ladder]

key-files:
  created:
    - .planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-OWNER-CAPTURES.md
  modified:
    - skills/ai-kit-spec-review/SKILL.md
    - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-gsd-curated-config/references/runner.md
    - README.md
    - tests/test_quota_policy_text.py

key-decisions:
  - "The review Failure relay is a sentence under the outcome table, because the table rows already exceed the line limit."

patterns-established:
  - "Skills describe the ladder by linking subprocess-quota-policy.md, never by copying it."

requirements-completed: [QTA-03, QTA-01]

coverage:
  - id: D1
    description: "The review skill links the policy, names the one-shot same-lane re-invoke, and the dispatch reference names transient."
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_quota_policy_text.py#ReviewSkill"
        status: pass
    human_judgment: false
  - id: D2
    description: "Curated-config docs and the README drop the prefer-order fallback and the template 6 wording and describe the one-CLI ladder."
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_quota_policy_text.py#CuratedConfigDocs"
        status: pass
    human_judgment: false
  - id: D3
    description: "The owner capture kit stages C1-C7 as not run (owner) with redaction and a classify-only check."
    requirement: QTA-01
    verification:
      - kind: other
        ref: "plan verify: 25-OWNER-CAPTURES.md kit check prints kit ok"
        status: pass
    human_judgment: true
    rationale: "The captures themselves are owner-only and must stay not run."

duration: 25min
completed: 2026-10-25
status: complete
orchestrator_verify: "VERIFY 25-10: 3/3 passed"
---

# Phase 25 Plan 10: Quota-Aware Docs and Owner Capture Kit Summary

**The review skill, the curated-config skill and the README now describe the one-CLI failure ladder at template 7, and the owner has a redacted capture kit whose seven results all read not run (owner).**

## Performance

- **Duration:** 25 min
- **Started:** 2026-10-25T01:25:00Z
- **Completed:** 2026-10-25T01:50:36Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- The review skill's subprocess branch links the policy reference, relays the runner's
  `cross-ai: report` and `AIKIT-XAI` lines, and states the bounded one-shot same-lane re-invoke
  for a confirmed-router exit 75.
- `cross-ai-dispatch.md` maps `transient` to `capacity` and names the evidence tokens and lines.
- The curated-config skill, its runner reference and the README drop the prefer-order fallback
  and the template 6 wording; `runner.md` gains the failure-ladder section and the verified
  upgrade behavior.
- `25-OWNER-CAPTURES.md` stages C1-C7 with capture steps, the `--classify-only` check, pass rules
  and `Result: not run (owner)`.

## Task Commits

1. **Task 1: review skill and dispatch reference** - `d1229d8` (docs)
2. **Task 2: curated-config text, runner reference and README** - `8f9de94` (docs)
3. **Task 3: owner capture kit and this summary** - see commit (docs)

## Files Created/Modified

- `skills/ai-kit-spec-review/SKILL.md` - ladder paragraph, caller contract, Step 5 relay
- `skills/ai-kit-spec-review/references/cross-ai-dispatch.md` - `transient` row and evidence tokens
- `skills/ai-kit-gsd-curated-config/SKILL.md` - first runner only, no second CLI, template 7
- `skills/ai-kit-gsd-curated-config/references/runner.md` - failure ladder and upgrade behavior
- `README.md` - template-7 runner, one CLI per call, no automatic fallback
- `tests/test_quota_policy_text.py` - pins for the review skill, curated docs and README
- `.planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-OWNER-CAPTURES.md` - kit

## Decisions Made

- The Step 5 relay sentence sits under the outcome table rather than inside the Failure row: the
  table's rows already exceed the 100-character line limit, and widening one would add to that.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 25-11 judges the two changed SKILL.md files.
- The owner kit is ready to fill; close-out points at `/gsd-plan-phase 25 --gaps`.

## Deleted tests

None

## Pre-existing failures

None

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-25*
