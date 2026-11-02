---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 09
subsystem: infra
tags: [cross-ai, quota, execute-skills, policy-reference, one-shot-wake]

requires:
  - phase: 25-06
    provides: the runner ladder the skills now describe (rungs, router cycles, exit 75 and 69)
  - phase: 25-07
    provides: the dogfood runner on template 7, which this plan does not edit
provides:
  - the canonical subprocess-quota-policy reference with its 4-line instruction-file pointer
  - the GSD and superpowers execute skills following the runner's ladder
  - a text test pinning the stop sentence, the link and the one-shot-only re-invoke
affects: [25-10, 25-11, 26]

actuals:
  tokens: 14500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A skill describes the runner's ladder and links the canonical reference; it never restates it"
    - "Only a confirmed-router exit 75 gets one one-shot same-lane re-invoke; every other stop waits for the owner"

key-files:
  created:
    - skills/ai-kit-spec-review/references/subprocess-quota-policy.md
    - tests/test_quota_policy_text.py
  modified:
    - skills/ai-kit-spec-execute-gsd/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/state-management.md
    - skills/ai-kit-spec-execute-superpowers/references/escalation.md
    - skills/ai-kit-spec-execute-superpowers/references/design-notes.md
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py
    - tests/test_ai_kit_spec_superpowers.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "Assumption A1 stays pending owner confirmation through C7 in 25-OWNER-CAPTURES.md: pre-dispatch candidate choice and rounds 4-5 escalation are existing behavior, not settled policy"
  - "Other hosts have no CronCreate, so they print retry_after_s, the state path and the re-invoke command; that row is unverified (D-16)"
  - "Whether a one-shot wake fires while GSD's retry/skip/abort prompt is pending is unverified"

patterns-established:
  - "CronCreate survives only on a line that also carries one-shot and retry_after_s, and only in the two execute SKILL.md files"
  - "The quota budget is keyed by lane and model; the resumed session id is stored per task key"

requirements-completed: [QTA-03]

coverage:
  - id: D1
    description: "One canonical policy reference describes the runner's ladder and ends with a 3-4 line pointer naming .planning/scripts/cross-ai.mjs"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_quota_policy_text.py#PolicyReference"
        status: pass
    human_judgment: false
  - id: D2
    description: "The GSD execute skill links the reference, schedules nothing on a probe-time stop, and keeps exactly one one-shot same-lane re-invoke for a confirmed-router exit 75"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_quota_policy_text.py#GsdExecuteSkill"
        status: pass
    human_judgment: false
  - id: D3
    description: "The superpowers execute skill stops on a failed dispatch, never re-resolves to another candidate, and its references no longer schedule a repeated wake"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_quota_policy_text.py#SuperpowersExecuteSkill"
        status: pass
    human_judgment: false
  - id: D4
    description: "dispatch_injection.py and error_classifier.py messages and comments say stop and report, with no wake wording"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_quota_policy_text.py#PythonMessages"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-09: 3/3 passed"
---

# Phase 25 Plan 09: Execute Skills Follow the Runner Ladder Summary

**The execute skills stop and report on a subprocess failure, with one canonical ladder reference and exactly one one-shot same-lane re-invoke for a confirmed-router exit 75.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-10-24T20:30:00Z
- **Completed:** 2026-10-24T21:15:00Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments

- One reference, `subprocess-quota-policy.md`, describes the runner's ladder (one CLI per call, the classes, both rungs, the dirty-tree rule, router cycles with the lane-and-model state key, the stops, the evidence lines, the CONFIG clamps) and ends with the 4-line instruction-file pointer.
- `ai-kit-spec-execute-gsd` writes resumable state and stops on a probe-time `quota_exhausted`; on a GSD cross-AI failure it relays the runner's evidence, never answers `skip` or `retry` for an auth, billing or bad-model stop, and schedules exactly one one-shot same-lane re-invoke for a confirmed-router exit 75.
- `ai-kit-spec-execute-superpowers` stops the wave on a failed dispatch in both the `"quota"` and `"real_error"` branches, never re-resolves to another candidate, and keeps rounds 4-5 escalation and the pre-dispatch choice as existing behavior pending owner confirmation.
- The Python messages match: `QuotaExhaustedError` says the caller persists state and stops, and `"quota"` from `classify_dispatch_failure` means stop and report.

## Task Commits

Each task was committed atomically:

1. **Task 1: Policy reference, the GSD execute skill pointing at it, and the text test** - `d2d0400` (docs)
2. **Task 2: The superpowers execute skill stops and reports, never re-dispatches** - `ec7c3b0` (docs)
3. **Task 3: Python messages and comments match, text test covers them** - (this commit) (test)

## Files Created/Modified

- `skills/ai-kit-spec-review/references/subprocess-quota-policy.md` - the canonical ladder reference and the instruction-file pointer
- `tests/test_quota_policy_text.py` - text pins with non-vacuity for both execute skills and the Python modules
- `skills/ai-kit-spec-execute-gsd/SKILL.md` - stop and report, plus the one-shot caller contract
- `skills/ai-kit-spec-execute-superpowers/SKILL.md` - no post-failure re-dispatch; the same caller contract
- `skills/ai-kit-spec-execute-superpowers/references/state-management.md` - "Resumable state: writing it"
- `skills/ai-kit-spec-execute-superpowers/references/escalation.md` - a later re-run by the owner
- `skills/ai-kit-spec-execute-superpowers/references/design-notes.md` - the same rewording
- `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` - stop-and-report messages and docstrings
- `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py` - the `quota` reason comment
- `tests/test_ai_kit_spec_superpowers.py` - comments reworded to a later re-run
- `Makefile`, `.pre-commit-config.yaml` - generated test-group listings

## Decisions Made

- A1 is recorded as pending, not settled: the pre-dispatch quota probe and rounds 4-5 capability escalation stay as existing behavior until the owner confirms them through C7.
- The other-hosts row and firing during a pending GSD prompt are both marked unverified in the reference, matching D-16.

## Deviations from Plan

None - plan executed exactly as written.

## Deleted tests

None.

## Remaining wake-word lines in tests/test_ai_kit_spec_superpowers.py

None. Task 3 reworded every comment and the one test name that named the wake, so the scan for `hourly`, `every hour`, `recurring`, `CronCreate` and `wake` prints nothing.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 25-10 documents the same ladder in the review skill, curated-config and the README, and owns C7.
- 25-11 judges both execute SKILL.md files, which this plan changed.
- The orchestrator runs the project-wide `make test` and `make validate` barrier.

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-24*
