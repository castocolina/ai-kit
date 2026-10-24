---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 02
subsystem: infra
tags: [cross-ai, runner, classifier, pattern-table, redaction]

requires:
  - phase: 25-quota-aware-cross-ai-subprocess-supervision
    provides: the single-CLI runner loop from plan 25-01
provides:
  - one labelled JSON pattern table between the runner's // <patterns> markers
  - classifyStop, a pure matcher over stderr and structured error events
  - a status line that names the matched row (route, rule, pattern)
affects: [25-03, 25-04, 25-05, 25-06]

actuals:
  tokens: 4718
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Rows are tried in pinned table order; the router lane is resolved before any row"
    - "Child stderr is relayed through one bounded line splitter and a secret redactor"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - tests/test_ai_kit_spec.py

key-decisions:
  - "Owner ladder A11: rate-limit wording and a bare 429 are quota-class, no longer transient"
  - "On a router lane a row with routerClass quota reports status=quota exit 75; entry-point auth stays auth exit 69"

patterns-established:
  - "classifyStop is a pure function of (table, inputs, router lane) and returns status, rule and label"
  - "Answer text never reaches the matcher: pi stdout, opencode text events and codex items are skipped"

requirements-completed: [QTA-01]

coverage:
  - id: D1
    description: "One labelled per-CLI JSON table classifies every failed attempt from stderr and structured error events, and the status line names the matched row and its label"
    requirement: QTA-01
    verification:
      - kind: e2e
        ref: "node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test (quota tail, billing-router, sentinel-failed-line, sentinelsplit, sentinel-overlong, 53 pure-classify fixtures, pure-classify-order-mutation, pure-classify-idempotent)"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_spec.TestCrossAiTemplate.test_patterns_block"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-02: 2/2 passed"
---

# Phase 25 Plan 02: Pattern table and classifier Summary

**One labelled JSON pattern table classifies every failed attempt from stderr and structured error events, and the status line names the matched row.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-10-24T20:48:00Z
- **Completed:** 2026-10-24T21:43:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced the two-regex `PATTERNS` object with a 65-row JSON array (id, cli, input, match, class, optional routerClass, terminal, label, evidence) tried in the pinned D-03 order.
- Added the pure `classifyStop` and `extractEvents`: opencode `type:error` in both shapes, codex `error` and `turn.failed`, cursor and claude final result only when `is_error`; pi contributes nothing. The old `classify` function and the router billing rule in `finish` are gone.
- On a router lane every row whose `routerClass` is `quota` reports `status=quota` exit 75 under its own row id; entry-point auth stays `auth` exit 69. The status line appends `route= rule= pattern=` after `action=stop`.
- Child stderr is relayed through one bounded (64 KiB) line splitter and a secret redactor, so a key split across chunks or carried on an overlong line never reaches the log.
- Pinned 53 observed-message fixtures as in-process `pure-classify-*` cases, plus an order-mutation case and an idempotency case.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pattern table, pure matcher and structured events wired into every failed attempt** - `f9fb3a6` (feat)
2. **Task 2: Observed-message fixtures as pure self-test cases, order pinned with a mutation check** - (this commit, test)

**Plan metadata:** committed with Task 2 (docs: complete 25-02 plan)

## Files Created/Modified
- `skills/ai-kit-spec-review/references/cross-ai.mjs` - the JSON pattern table, `classifyStop`, `extractEvents`, the redacting line relay, the status-line evidence tail and the pure fixture cases
- `tests/test_ai_kit_spec.py` - `test_patterns_block` rewritten for the row schema
- `.planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-02-SUMMARY.md` - this summary

## Decisions Made
None - followed the plan and the owner's 2026-10-24 ladder as specified. No open question needed the jev ladder.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The delayed split-token fake exited before it wrote**
- **Found during:** Task 1 (pattern table and classifier)
- **Issue:** `sentinelsplit` schedules its second stderr chunk after 50 ms, but the fake harness exits the process as soon as the mode function returns, so the delayed write never happened and the case saw an empty answer.
- **Fix:** Added `sentinelsplit` to the sticky-fake set so the process stays alive until its own `process.exit`.
- **Files modified:** skills/ai-kit-spec-review/references/cross-ai.mjs
- **Verification:** `AIKIT_XAI_SELFTEST_CASES=sentinelsplit` passes and the whole log contains neither sentinel.
- **Committed in:** `f9fb3a6` (Task 1 commit)

**2. [Rule 1 - Bug] A retried transient left its row on the later success line**
- **Found during:** Task 1 (pattern table and classifier)
- **Issue:** The first attempt's classification was written into `liveFields`, so the `flaky` case's successful retry reported that row instead of the defaults.
- **Fix:** The evidence travels only on the failure result object; `liveFields` keeps the defaults, and a later success prints `rule=- pattern=none`.
- **Files modified:** skills/ai-kit-spec-review/references/cross-ai.mjs
- **Verification:** the full `--self-test` prints `self-test ok`, including `flaky`.
- **Committed in:** `f9fb3a6` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes make the specified checks true. No scope change.

## Deleted tests

None

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for 25-03 (`--classify-only`, `--route-<cli>`, `ROUTER_HINTS`). `classifyStop` already takes an explicit table and a router-lane flag.
- The `// <patterns>` block parses as a 65-row JSON array; `test_patterns_block` passes (708 tests, `1/1 modules passed`).
- `--self-test` prints `self-test ok` for the full run and for the named Task 2 subset. 53 `pure-classify-<name>` fixtures plus `pure-classify-order-mutation` and `pure-classify-idempotent`.
- Bare status-code rows and the `rate.?limit` / `too many requests` rows ship `terminal: false` for 25-04.

## Self-Check: PASSED

- `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` prints `self-test ok`.
- The patterns block parses as JSON; `function classify(` is absent; `routerBacked[fields.cli]` occurs 0 times.

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-24*
