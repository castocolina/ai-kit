---
phase: 21-cursor-live-validation
plan: 03
subsystem: testing
tags: [cursor, gsd-core, curated-config, resolve-model, smoke]
requires:
  - phase: 21-01
    provides: Cursor runtime identification and model handling
provides:
  - Cursor project-local gsd-core root resolution
  - Cursor host matrix and hermetic local smoke evidence
  - Cursor baked-chain, generated-path, and protected-set harness coverage
affects: [21-04, 21-05, 21-06]
actuals:
  tokens: 2800
  tasks: 2
  commits: 4
tech-stack:
  added: []
  patterns: [host-specific gsd-core resolution, protected Cursor path snapshotting, resolve-model-only bake verification]
key-files:
  created: [.planning/phases/21-cursor-live-validation/21-03-SUMMARY.md]
  modified:
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - tests/gsd_curated_eval.py
    - tests/test_ai_kit_gsd_curated_config_matrix.py
    - tests/test_curated_config_apply.py
    - tests/test_curated_config_inventory.py
    - tests/test_gsd_curated_eval.py
key-decisions:
  - "Keep GSD_RUNTIME=cursor set for project-local resolve-model; unlike the other hosts, this runtime's resolver needs the explicit host signal."
  - "Treat baked Cursor files as model-free and independently compare planned models against resolve-model."
requirements-completed: [EVAL-07]
coverage:
  - id: D1
    description: Cursor project-local .cursor/gsd-core takes precedence and is documented.
    requirement: EVAL-07
    verification:
      - kind: unit
        ref: tests/test_curated_config_inventory.py#test_cursor_host_prefers_cursor_root_over_claude_root
        status: pass
    human_judgment: false
  - id: D2
    description: Cursor host matrix passes its 420 checks through CLI and its fourth e2e test class.
    requirement: EVAL-07
    verification:
      - kind: e2e
        ref: tests/test_ai_kit_gsd_curated_config_matrix.py#TestResolveModelMatrixCursor
        status: pass
      - kind: other
        ref: python3 tests/gsd_curated_eval.py matrix --host cursor
        status: pass
    human_judgment: false
  - id: D3
    description: Hermetic cursor local smoke completes all ten steps and emitted artifacts prove no models were baked or selected from fast ids.
    requirement: EVAL-07
    verification:
      - kind: e2e
        ref: tmp/p21/local-cursor.md and tmp/p21/local-cursor-artifacts/
        status: pass
      - kind: other
        ref: python3 tests/gsd_curated_eval.py snapshot --check tmp/p21/plan03.task2.before.json --scratch-root <scratch>
        status: pass
    human_judgment: false
  - id: D4
    description: Snapshot strictly protects Cursor hooks.json and tracks agents/skills directory names.
    verification:
      - kind: unit
        ref: tests/test_gsd_curated_eval.py#TestSnapshot.test_cursor_agents_skills_hooks_are_protected
        status: pass
    human_judgment: false
duration: 90min
completed: 2026-10-18
status: complete
orchestrator_verify: "VERIFY 21-03: 1/2 passed"
---

# Phase 21 Plan 03: Cursor Harness Support Summary

**Cursor project-local gsd-core resolution and a 420-check host matrix, backed by a hermetic ten-step smoke with model-free installer verification.**

## Performance

- **Duration:** approximately 90 min
- **Started:** 2026-10-18
- **Completed:** 2026-10-18
- **Tasks:** 2
- **Files modified:** 7 (plus this summary)

## Accomplishments

- Added `.cursor/gsd-core` as the cursor-first project root, regression-tested host preference and documented the resolution order.
- Added the Cursor matrix host class and CLI option; cursor and Claude matrices each passed 420 checks, and the four matrix classes collect 36 tests total.
- Updated smoke verification for Cursor's model-free baked files, generated paths and protected-home entries. The local cursor smoke passed all 10 steps and produced artifacts showing 35 resolved models, all baked entries null, three active Cursor tier slots, and three active specialist overrides, with no `-fast` models.
- Added snapshot coverage for `<home>/.cursor/hooks.json` and the names of `<home>/.cursor/agents` and `<home>/.cursor/skills`; these name listings do not detect edits to existing files.

## Task Commits

1. **Task 1: cursor project-local gsd-core root; matrix --host cursor and its e2e class** — `9129390`
2. **Task 2: resolve-model-only cursor chain correction** — `2405963`

The tracer commit also contains the harness/test additions listed in its task file set. The additional fix commit corrects a host-signal issue exposed by the smoke.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py` — Cursor-first local gsd-core root.
- `skills/ai-kit-gsd-curated-config/SKILL.md` — Resolution order documents Cursor.
- `tests/test_curated_config_apply.py` — Pins the `.cursor/gsd-core` documentation statement.
- `tests/test_curated_config_inventory.py` — Cursor root resolution and host-scoped precedence regressions.
- `tests/gsd_curated_eval.py` — Cursor matrix, model-free baked-chain guard, generated paths and protected snapshot entries.
- `tests/test_ai_kit_gsd_curated_config_matrix.py` — Fourth host class.
- `tests/test_gsd_curated_eval.py` — Matrix collection, baked-chain, generated-path and snapshot tests.
- `.planning/phases/21-cursor-live-validation/21-03-SUMMARY.md` — Plan outcome and verification record.

## Decisions Made

- Cursor installer output is treated as `resolve-model only`: the full baked map, including compact files, must contain no model field, while plan-to-resolve-model comparisons remain active.
- Project-local resolve-model probes retain `GSD_RUNTIME=cursor`; the first smoke showed the host's managed runtime configuration alone did not select its per-tier model overrides.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Retain the Cursor runtime signal for the post-install resolve-model check**
- **Found during:** Task 2 local smoke attempt 1.
- **Issue:** The common smoke chain removed `GSD_RUNTIME` for all non-Claude hosts. Cursor resolve-model then used tier aliases rather than the planned Cursor runtime model ids.
- **Fix:** Preserve `GSD_RUNTIME` for cursor only; continue removing it for existing non-Claude paths.
- **Files modified:** `tests/gsd_curated_eval.py`.
- **Verification:** Cursor smoke attempt 2 passed all ten steps and artifact assertions; unit and e2e groups passed.
- **Committed in:** `2405963`.

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** Necessary harness correction discovered by the rehearsal; no second product-module change.

## Issues Encountered

- The initial `make`-style unit group run exposed regressions in the newly added snapshot and generated-path tests, plus a mismatch in the cursor resolve-model fixture. These were corrected and the complete unit suite passed on rerun.
- Cursor smoke attempt 1 failed at the post-apply resolve-model step because `GSD_RUNTIME` was removed; its evidence was archived as `tmp/p21/local-cursor.attempt1.md` and its log as `tmp/p21/local-cursor.attempt1.log`. The follow-up attempt passed. Harness fixes: retain the cursor runtime signal; no other harness fix was needed.
- The rehearsal artifact check excludes plan entries with `op: unset` when checking planned specialist models, since these entries intentionally have null values. The successful artifact check found 3 active cursor slots and 3 active specialist overrides.
- The existing plan03 baseline correctly reported Cursor snapshot labels added by G6 after its pre-G6 capture. It was checked before that harness change; the rehearsal used the post-G6 `plan03.task2.before.json` baseline and finished with `snapshot ok`.

## Verification

- Cursor inventory tests, required-statements pin, oracle/environment/collection tests: passed.
- `matrix --host cursor` and `matrix --host claude`: `matrix ok (420 checks)` each.
- Cursor e2e class: 9 tests passed; complete matrix e2e module: 36 tests passed.
- `tests.test_gsd_curated_eval`: 297 tests passed.
- `python3 tools/run_unittest_parallel.py --group unit`: 43/43 modules passed.
- `python3 tools/run_unittest_parallel.py --group e2e`: 8/8 modules passed.
- The Cursor matrix e2e class passed 9 tests; its complete matrix module passed 36 tests.
- Local Cursor smoke: 10/10 steps passed; artifacts had 35 model resolutions, all baked values null, no fast model in active planned slots/overrides or resolved output; secret scan and real-home path scan clean; protected snapshot unchanged.
- Invalid matrix host exits 2 and lists all four accepted hosts.
- No AI CLI was invoked. No fake grandchild processes remained after verification.

## Next Phase Readiness

Ready for 21-04's headless Cursor dispatch rehearsal. Local evidence is in `tmp/p21/local-cursor.md` with its artifacts under `tmp/p21/local-cursor-artifacts/`.

---
*Phase: 21-cursor-live-validation*
*Completed: 2026-10-18*
