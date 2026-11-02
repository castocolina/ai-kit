---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 13
subsystem: ui
tags: [cursor, status-line, quota, config-isolation]

requires:
  - phase: 23-07
    provides: Shared renderer, neutral context and gauge functions
  - phase: 23-12
    provides: Cursor quota cache and state probe
provides:
  - Cursor payload adapter, HOST, entry point and configuration sample
  - Four inferred quota/reset segments using the shared gauge
  - Cursor config/provider namespace isolation tests
affects: [status-line, cursor, phase-23-14, phase-23-15]

actuals:
  tokens: 1660
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns: [Host-specific ConfigSpec and provider namespace, cache-only quota read in render]

key-files:
  created:
    - tools/cursor_payload.py
    - tools/cursor_segments.py
    - tools/cursor_host.py
    - tools/cursor-status-line.py
    - tools/cursor-statusline.toml.sample
  modified:
    - tests/test_cursor_status_line.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "Cursor quota visibility is labeled inferred and stale cache data receives a distinct marker."
  - "API usage remains disabled by default and is independently toggleable."

patterns-established:
  - "Cursor quota coloring imports the shared gap/color/sign helpers by identity."
  - "Cursor config, provider env and provider cache use host-specific namespaces."

requirements-completed: [STL-02, STL-03]
coverage:
  - id: D1
    description: Cursor status-line entry adapts real-shaped payloads through the shared renderer.
    requirement: STL-02
    verification:
      - kind: unit
        ref: tests/test_cursor_status_line.py#test_entry_renders_path_model_and_nullable_context
        status: pass
    human_judgment: false
  - id: D2
    description: Four quota/reset segments use shared gauge behavior, inferred markers and local reset time.
    requirement: STL-02
    verification:
      - kind: unit
        ref: tests/test_cursor_status_line.py#test_shared_gauge_identity_and_included_variants
        status: pass
      - kind: unit
        ref: tests/test_cursor_status_line.py#test_api_default_toggle_and_all_extra_kinds
        status: pass
      - kind: unit
        ref: tests/test_cursor_status_line.py#test_reset_is_local_time_and_weekly_window
        status: pass
    human_judgment: false
  - id: D3
    description: Cursor configuration, providers, and cache remain isolated from Claude namespaces.
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_cursor_status_line.py#test_config_namespace_provider_namespace_and_no_network_render
        status: pass
      - kind: unit
        ref: tests/test_cursor_status_line.py#test_claude_config_does_not_scan_cursor_provider_directory
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-13: 3/3 passed (orchestrator re-run; step 2 expected util_gap_color/util_gap_sign in common_fmt, they live in common_types since 23-04: identity holds there; cache-base defect fixed in 29ae44e, no stray files, no leaked refreshers)"
---

# Phase 23 Plan 13 Summary

**Cursor status line now renders payload context and cache-derived quota segments through the shared renderer.**

## Performance

- **Duration:** 65 min
- **Started:** 2026-10-24T00:21:00-03:00
- **Completed:** 2026-10-24T01:26:00-03:00
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Added Cursor host, payload adapter, thin entry point, and configuration sample.
- Added included, API, extra-usage, and billing-cycle reset segments, with inferred/stale markers and shared gauge behavior.
- Added coverage for host-specific configuration, external provider environment/cache namespace, and Claude provider discovery isolation.

## Task Commits

1. **Task 1: Cursor host, payload adapter and entry** - `0c635f8` (feat)
2. **Task 2: Cursor quota segments on the shared gauge** - `94f5806` (feat)
3. **Task 3: Cursor config env and provider namespace isolation** - `309d750` (test)

## Files Created/Modified
- `tools/cursor_payload.py` - Cursor stdin payload adapter and context builder.
- `tools/cursor_host.py` - Cursor defaults, configuration spec, and host assembly.
- `tools/cursor-status-line.py` - Thin status-line entry point.
- `tools/cursor_segments.py` - Four quota/reset segments using shared gauge helpers.
- `tools/cursor-statusline.toml.sample` - Cursor configuration example.
- `tests/test_cursor_status_line.py` - Payload, quota rendering, and isolation regression tests.
- `Makefile`, `.pre-commit-config.yaml` - Generated test group listings.

## Decisions Made
- Followed the design's inferred classification for quota data from the undocumented Dashboard API; no live owner-only verification was attempted.
- Kept the API usage segment disabled by default.

## Deviations from Plan

- Task 3 exercised Cursor provider env delivery and cache placement and asserted Claude config discovery excludes the Cursor provider directory. Real Claude provider execution and strict capture were not modified; those remain covered by existing Claude oracle tests.
- Added segment-toggle gating to quota builders so direct segment invocation respects per-segment configuration, matching shared-renderer behavior.

**Total deviations:** 1 scoped verification adjustment and 1 correctness adjustment.
**Impact on plan:** All requested behaviors remain within scope; no shared common modules were changed.

## Issues Encountered
- Render-width tests found the context geometry is available directly on `Context.cols`; changed the assertion to validate that contract.
- Provider tests initially configured an incomplete replacement layout; configured the provider in its own row and used the supplied working directory so the subprocess could execute.
- A temporary `cursor/` cache directory created by an early default-environment test was removed after each test run.

## Deleted tests

None.

## Pre-existing failures

None observed in targeted plan tests.

## Verification

- `uv run ruff check tools/cursor_segments.py tests/test_cursor_status_line.py` — passed.
- `uv run pylint tools/cursor_segments.py` — passed.
- `uv run python tools/run_unittest_parallel.py tests.test_cursor_status_line` — passed (11 tests).
- Spawned child cleanup: no provider child remained after synchronous subprocess completion; ephemeral scratch/cache artifacts removed.
- `make test` and `make validate` are serialized orchestrator wave-barrier gates and were not run here.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Cursor render-side artifacts and isolation tests are ready for the setup, doctor, and wizard integration plans. The owner-only live Cursor spike remains unrun as required.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
