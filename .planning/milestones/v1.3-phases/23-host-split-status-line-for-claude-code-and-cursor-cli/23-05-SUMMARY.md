---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 05
subsystem: testing
tags: [status-line, python, split-conformance]

requires:
  - phase: 23-04
    provides: split foundation, move audit and disposable test rewrite/check tools
provides:
  - Completed Stage 3 Claude status-line split with a thin entry point
  - Direct split-module imports in the status-line doctor
  - Split-module architecture checks and checkpoint purity validation
affects: [23-06, 23-07, 23-08, 23-09]

actuals:
  tokens: 1100
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns: ["Segment builder discovery across shared and Claude-specific modules"]

key-files:
  created: [tools/claude_host.py, tools/common_segments.py]
  modified: [tools/status-line.py, tools/statusline-doctor.py, tests/test_arch.py, tests/test_status_line.py]

key-decisions:
  - "The status-line entry delegates to claude_host.main without re-exporting implementation symbols."
  - "The doctor imports render, payload, config and probe modules directly rather than loading the entry by path."

patterns-established:
  - "Architecture and split-conformance rules inspect the split modules, not the thin entry."

requirements-completed: [STL-01]
coverage:
  - id: D1
    description: "Stage 3 moved into split modules while retaining the existing rendering suite and oracle behavior."
    requirement: STL-01
    verification:
      - kind: unit
        ref: "tests.test_status_line, tests.test_external_segments, tests.test_statusline_doctor, tests.test_claude_precompact, tests.test_arch, tests.test_setup"
        status: pass
      - kind: other
        ref: "python3 tmp/p23/04/split_check_tests.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Split location, thin-entry and AST conformance checks cover the finished split."
    requirement: STL-01
    verification:
      - kind: unit
        ref: "tests.test_arch"
        status: pass
      - kind: other
        ref: "python3 checkpoint purity check for split_hash_mismatches"
        status: pass
    human_judgment: false

duration: 42min
completed: 2026-10-23
status: complete
orchestrator_verify: "VERIFY 23-05: 2/2 passed (orchestrator re-run; split_hash_mismatches() returns strings, the verify read .name: the one generalized mismatch is core_discover_builders, non-generalized mismatches empty)"
---

# Phase 23 Plan 05 Summary

**Claude status-line render, segment and entry code now live in split modules, with the legacy entry reduced to delegation.**

## Performance

- **Duration:** 42 min
- **Started:** Recorded at task start in the ignored `tmp/p23/05/started` marker.
- **Completed:** 2026-10-23
- **Tasks:** 2
- **Files modified:** 12 tracked files across both task commits.

## Accomplishments
- Moved the remaining render and segment code to `common_render.py`, `common_segments.py`, `claude_segments.py` and `claude_host.py`; `tools/status-line.py` delegates to `claude_host.main()`.
- Retargeted status-line and external-segment tests, removed the doctor's monolith-loading shim, and routed transcript compaction parity to `claude_probes`.
- Added architecture checks for split modules and a thin entry; conformance confirms that only the explicitly generalized builder registry differs from its source AST at the Plan 05 checkpoint.

## Task Commits

1. **Task 1: Stage 3 split move and thin entry** - `4a5c6a3` (`refactor(23-05): stage 3 split move and thin entry`)
2. **Task 2: Split conformance without the monolith** - `78e31fa` (`test(23-05): split conformance without the monolith`)

## Files Created/Modified
- `tools/claude_host.py` - Claude render registry, packer and entrypoints.
- `tools/common_segments.py` - shared segment builders moved from the entry module.
- `tools/claude_segments.py`, `tools/common_render.py`, `tools/status-line.py` - Claude-specific builders, render core, and thin delegating entry.
- `tools/statusline-doctor.py` - direct imports from split modules.
- `tests/test_status_line.py`, `tests/test_external_segments.py`, `tests/test_statusline_doctor.py`, `tests/test_claude_precompact.py`, `tests/test_arch.py` - retargeted tests and split checks.

## Decisions Made
- Kept the builder registry as a one-time module-level snapshot, collecting `seg_*` definitions from both segment modules.
- Preserved assertion parity; the disposable checker reports three `assertions unchanged` results.

## Deviations from Plan

### Auto-fixed Issues

**1. Import and type-check corrections in moved modules and doctor**
- **Found during:** Task 1 verification.
- **Issue:** Moved code and the doctor depended on module-qualified probe/payload imports, and pyright identified two existing typing assumptions that no longer held after direct imports.
- **Fix:** Imported required modules directly, used the direct probe import, and removed the redundant cast while supplying the config binder's optional git value with an empty mapping fallback.
- **Files modified:** `tools/claude_host.py`, `tools/statusline-doctor.py`.
- **Verification:** Six-module test command passed; touched-module pyright passed.
- **Committed in:** `4a5c6a3` for split/import fixes; the final doctor typing cleanup remains to be committed with the summary.

**2. Checker normalization for retargeted stdlib aliases**
- **Found during:** Task 1 assertion-diff verification.
- **Issue:** The existing disposable assertion checker treated allowed retargets from `sl.time`/`sl.datetime` to stdlib modules as assertion changes.
- **Fix:** Extended its normalization and retarget allowlist, preserving comparisons of the assertion bodies.
- **Files modified:** `tmp/p23/04/split_check_tests.py` (ignored disposable verification tool).
- **Verification:** The checker printed three `assertions unchanged` lines.
- **Committed in:** Not tracked; scratch tool only.

---

**Total deviations:** 2 auto-fixed.
**Impact on plan:** Necessary import/type and checker updates; no runtime behavior was intentionally changed beyond the planned registry discovery.

## Issues Encountered
- The initial touched-module run exposed missing moved imports and stale test references; these were corrected and the full six-module task runner passed.
- `make test` and `make validate` were not run because the plan reserves them for the shared wave barrier.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Stage 3 is complete; follow-on host-neutralization and behavior work can build on `claude_host` and the split modules.
- The orchestrator should rerun the disposable assertion checker and remove plan scratch directories at the wave barrier.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-23*
