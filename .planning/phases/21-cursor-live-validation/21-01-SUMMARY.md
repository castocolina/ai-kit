---
phase: 21-cursor-live-validation
plan: 01
subsystem: ai_kit_spec
tags: [cursor, PATH, detection, model-parser, runtimes-cache]
requires: []
provides:
  - Guarded cursor binary resolution scans PATH entries and records real_path in built and refreshed runtime rows.
  - Public parse_cursor_models parses captured Cursor output and rejects non-ASCII model id tokens.
affects: [21-02, 21-07, cursor-runtime-detection]
actuals:
  tokens: 2600
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [Guarded PATH scan with an injected which seam, pure token-based CLI listing parser]
key-files:
  created:
    - tests/fixtures/cursor_models.txt
    - tests/fixtures/cursor_models_empty.txt
    - tests/fixtures/cursor_models_auth_failed.txt
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - skills/ai-kit-spec-review/ai_kit_spec/routing.py
    - tests/test_ai_kit_spec_runtimes_table.py
    - tests/test_ai_kit_spec_routing.py
    - tests/test_ai_kit_spec.py
key-decisions:
  - "No runtimes schema bump: real_path is informational and no consumer relies on it."
  - "D-09 seam adaptation: functools.partial(shutil.which, path=first_path) supplies the initial PATH hit; path_env controls the scan of every entry, with empty entries mapped to os.curdir. Callable seams without a path keyword are kept compatible and do not receive scan calls."
  - "R8 treats detection.py and routing.py together as one ai_kit_spec runtime-package change for SPEC-06."
requirements-completed: [SPEC-06]
coverage:
  - id: D1
    description: Guarded cursor agent resolution, no-shell invocation, build/refresh real_path recording, and session-default-only selection.
    requirement: SPEC-06
    verification:
      - kind: unit
        ref: tests/test_ai_kit_spec_runtimes_table.py#TestGuardedAgentBinary
        status: pass
      - kind: unit
        ref: tests/test_ai_kit_spec_routing.py#TestTargetedRefresh.test_refresh_records_real_path_of_the_re_resolved_binary
        status: pass
    human_judgment: false
  - id: D2
    description: Public token-based cursor models parser validated against captured and synthetic fixtures.
    requirement: SPEC-06
    verification:
      - kind: unit
        ref: tests/test_ai_kit_spec.py#TestParseCursorModels
        status: pass
      - kind: other
        ref: python3 tests/gsd_curated_eval.py snapshot --check tmp/p21/plan01.before.json
        status: pass
    human_judgment: false
duration: 0min
completed: 2026-10-18
status: complete
---

# Phase 21 Plan 01: Cursor Detection and Models Parser Summary

**Cursor detection now scans guarded PATH entries, records resolved binary paths, and parses the captured model listing as validated ASCII id tokens.**

## Performance

- **Duration:** Single execution session
- **Started:** 2026-10-18
- **Completed:** 2026-10-18
- **Tasks:** 2
- **Files modified/created:** 8

## Accomplishments

- Added scan-all guarded `agent` lookup, mapping empty PATH segments to the current directory; recorded `real_path` on runtime snapshot build and refresh without a schema bump.
- Kept cursor invocation shell-free and pinned its session-default-only selector behavior.
- Added public `parse_cursor_models` with ANSI cleanup, nameless entries, empty-account handling, and strict ASCII id tokens; checked the byte-identical 269-line capture (265 ids, 79 `-fast`) plus synthetic empty and auth-failure fixtures.

## Task Commits

1. **Task 1: Scan guarded PATH entries and record real paths** — `8bbbdca`
2. **Task 2: Add the public parser and captured fixtures** — `5e3d349`

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` — guarded PATH scan, real-path snapshot field, and public cursor listing parser.
- `skills/ai-kit-spec-review/ai_kit_spec/routing.py` — refreshes real_path on re-resolved rows.
- `tests/test_ai_kit_spec_runtimes_table.py` — PATH, shell-free listing and session-default-only coverage.
- `tests/test_ai_kit_spec_routing.py` — stale real_path refresh regression and path-aware test seams.
- `tests/test_ai_kit_spec.py` — snapshot equality pins and parser coverage.
- `tests/fixtures/cursor_models.txt` — captured Cursor listing.
- `tests/fixtures/cursor_models_empty.txt` and `tests/fixtures/cursor_models_auth_failed.txt` — synthetic formatter/stderr fixtures.

## Decisions Made

- Kept `RUNTIMES_SCHEMA_VERSION` at 5 because the new real_path field is informational and not relied on by consumers.
- Applied the D-09 test seam adaptation: the partial resolver supplies the first hit, while `path_env` enumerates scan directories. Updated the `_which_in` helper and routing test seams that needed to accept `path=`; signature inspection preserves one-argument fake resolvers that cannot be scanned.
- Applied the R8 package reading: detection and routing changes together constitute one SPEC-06 runtime-package change.

## Deviations from Plan

**1. [Rule 1 - Bug] Preserved narrow injected `which_fn` seams**
- **Found during:** Task 1
- **Issue:** Existing one-argument fake resolvers raised `TypeError` when the guarded PATH scan passed `path=`.
- **Fix:** Scan calls are made only when the injected callable supports a `path` keyword or `**kwargs`; updated relevant tests to use path-aware seams where scan behavior is under test.
- **Files modified:** `skills/ai-kit-spec-review/ai_kit_spec/detection.py`, `tests/test_ai_kit_spec_runtimes_table.py`, `tests/test_ai_kit_spec_routing.py`.
- **Verification:** Focused runtime/routing tests and all 42 unit modules passed.
- **Committed in:** `8bbbdca`

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** Maintains existing injection compatibility while enabling deterministic multi-entry scans.

## Issues Encountered

None.

## Next Phase Readiness

Ready for Phase 21-02 and 21-07 consumers of the captured fixture and resolver behavior.

---
*Phase: 21-cursor-live-validation*
*Completed: 2026-10-18*
