---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 07
subsystem: status-line
tags: [python, host-split, renderer, git-timeouts]
requires:
  - phase: 23-06
    provides: Host-parameterized common renderer and Claude HOST definition
provides:
  - Host-neutral Context with typed ClaudeData on ctx.host
  - Nullable shared context segment and window-based quota gauge
  - Bounded git probes with timeout coverage
affects: [23-13, status-line]
actuals:
  tokens: 620
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [host-specific payload typed on neutral Context, gauge over explicit time windows]
key-files:
  created: []
  modified:
    - tools/common_render.py
    - tools/common_types.py
    - tools/common_fmt.py
    - tools/common_probe.py
    - tools/common_segments.py
    - tools/claude_payload.py
    - tools/claude_probes.py
    - tools/claude_segments.py
    - tests/test_status_line.py
    - tests/fixtures/statusline_split/audit.md
key-decisions:
  - "Claude payload fields are accessed only through core_claude_data(ctx); generic modules do not inspect ctx.host."
patterns-established:
  - "A host's data may be stored as a typed host payload while shared Context contains only neutral fields."
  - "util_window_gap computes elapsed-window gap; host-specific window interpretation remains in an adapter."
requirements-completed: [STL-01, STL-02, STL-03]
coverage:
  - id: D1
    description: "Neutral Context carries ClaudeData through ctx.host while Claude probes and segments preserve the oracle render."
    requirement: STL-01
    verification:
      - kind: unit
        ref: tests.test_status_line#TestFullGoldenAnsi,TestEntryRender,TestStrictProviderCapture
        status: pass
      - kind: other
        ref: "uv run pyright; Context attribute inspection; common-module ctx.host grep"
        status: pass
    human_judgment: false
  - id: D2
    description: "Shared nullable context segment and explicit-window gap function support generalized host windows."
    requirement: STL-02
    verification:
      - kind: unit
        ref: tests.test_status_line#TestWindowGap,TestRateGap,TestCooperativeBuilders
        status: pass
    human_judgment: false
  - id: D3
    description: "Both git subprocess probes are bounded and slow-git behavior is covered directly and through the entry."
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests.test_status_line#TestProcAndGit.test_slow_git_times_out_to_empty_snapshot,test_entry_render_survives_slow_git
        status: pass
      - kind: other
        ref: "AST scan for git subprocess.run calls without timeout"
        status: pass
    human_judgment: false
duration: 17min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-07: 3/3 passed"
---

# Phase 23 Plan 07: Neutral Context, Gauge, and Git Timeouts Summary

**Claude-specific payload data now lives in typed ClaudeData, the shared gauge accepts explicit windows, and git probes have hard timeouts.**

## Performance

- **Duration:** approximately 17 min
- **Started:** 2026-10-24
- **Completed:** 2026-10-24
- **Tasks:** 3/3
- **Files modified:** 10

## Accomplishments

- Moved ten Claude-only fields out of `Context` into `ClaudeData`, accessed by Claude modules through `core_claude_data(ctx)`; shared context fields allow `None`.
- Made the common context segment hide for a missing percentage and omit its maximum variant when the maximum is absent.
- Added `util_window_gap` and delegated Claude's rate-gap arithmetic to it without changing the color/sign helpers.
- Added two-second timeouts to both git subprocess probes and tested timeout handling with a synthetic slow executable and the real entry path.
- Kept the D-05 golden fixtures unchanged; their diff from oracle commit `4c4bcec461df3cf4e4d58e19472429b8a7b29357` is empty.

## Task Commits

1. **Neutral Context and ClaudeData** — `0ae0f54`.
2. **Window gauge and nullable shared context** — `f1fbd27`.
3. **Bound git calls with timeouts** — `46f4145` (includes this summary).

## Files Created/Modified

- `tools/common_render.py`, `tools/common_segments.py` — neutral context shape and nullable context segment.
- `tools/claude_payload.py`, `tools/claude_probes.py`, `tools/claude_segments.py` — typed Claude data and host-specific readers.
- `tools/common_fmt.py` — explicit-window gap function.
- `tools/common_types.py`, `tools/common_probe.py` — git timeout constant and timeout handling.
- `tests/test_status_line.py` — host payload helper updates and behavior tests.
- `tests/fixtures/statusline_split/audit.md` — Context classification updated to generalized.

## Decisions Made

- `Context.host` is `object`; Claude-specific narrowing is localized to `core_claude_data` in `claude_payload`.
- The audit row for Context changed from `split` to `generalized` to describe its neutral-field contract.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first fake-git probe test isolated PATH too narrowly and could not locate the system `sleep`; fixed the fixture PATH to include `os.defpath`. Both the direct probe and entry tests then passed.
- A compound verification assertion initially expected `OK` in the runner's aggregate output; the runner reports module summaries instead. The complete output was checked and all requested modules passed.

## Deleted tests

- No tests deleted.

## Verification

- Task 1 touched suites: 3/3 modules passed (384 tests); ruff passed; pyright passed; Context inspection passed; common-module host-field check passed.
- Task 2 status-line suite: 1/1 module passed (316 tests); gauge spot checks passed; ruff and pyright passed.
- Task 3 status-line suite: 1/1 module passed (318 tests); direct slow git returned within the patched deadline; entry returned within six seconds; AST timeout scan passed; ruff and pyright passed.
- D-05 oracle fixture diff from `4c4bcec461df3cf4e4d58e19472429b8a7b29357` — empty.
- `make test` and `make validate` — not run by this plan; serialized wave barrier is owned by the orchestrator.

## Next Phase Readiness

- Shared status-line core is ready for Cursor's nullable context and explicit quota-window use.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
