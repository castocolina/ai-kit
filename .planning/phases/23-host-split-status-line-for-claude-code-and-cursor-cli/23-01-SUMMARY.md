---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 01
subsystem: testing
tags: [status-line, golden-tests, subprocess, provider]
requires: []
provides:
  - Raw-ANSI all-segments render golden for six Claude payload cases
  - Entry subprocess output and strict-provider input/environment/cache oracles
affects: [phase-23-status-line-split]
actuals:
  tokens: 1800
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [byte-for-byte golden oracle, scratch-rooted subprocess environment]
key-files:
  created:
    - tests/fixtures/golden/inputs_full.json
    - tests/fixtures/golden/expected_full_ansi.txt
    - tests/fixtures/golden/entry_payload.json
    - tests/fixtures/golden/entry_render.txt
    - tests/fixtures/golden/strict_provider_capture.json
  modified:
    - tests/test_status_line.py
    - tests/test_system_memory_e2e.py
key-decisions:
  - "Fixed the in-process oracle cwd under the plan scratch directory so cwd-derived path output is stable."
  - "Constructed fixture child environments with every host/config root isolated beneath the synthetic HOME."
requirements-completed: [STL-01, STL-02]
coverage:
  - id: D1
    description: Six-case raw-ANSI rendering golden pins all segments except render_time and slowest.
    requirement: STL-01
    verification:
      - kind: unit
        ref: tests.test_status_line#TestFullGoldenAnsi
        status: pass
    human_judgment: false
  - id: D2
    description: Entry subprocess output and strict provider capture are byte-pinned before the split.
    requirement: STL-01
    verification:
      - kind: unit
        ref: tests.test_status_line#TestEntryRender
        status: pass
      - kind: unit
        ref: tests.test_status_line#TestStrictProviderCapture
        status: pass
    human_judgment: false
  - id: D3
    description: System-memory E2E installation and render cannot inherit host config roots.
    verification:
      - kind: e2e
        ref: tests.test_system_memory_e2e
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-23
status: complete
orchestrator_verify: "VERIFY 23-01: 2/2 passed"
---

# Phase 23 Plan 01: D-05 Oracle Summary

**Raw-ANSI rendering, entry stdout, and strict-provider inputs are pinned before the host split.**

## Performance

- **Tasks:** 2/2
- **Files modified:** 7
- **Production base:** `e440c9af0ed316e12473c4f0b416b9bcffc720f8`
- **Oracle commit:** `4c4bcec461df3cf4e4d58e19472429b8a7b29357`

## Accomplishments

- Added six full-render payload cases and a deterministic raw-ANSI golden with every segment enabled except `render_time` and `slowest`.
- Pinned the entry subprocess's exact output and strict external provider's stdin, environment keys, workspace cwd, and cache result.
- Isolated the system-memory fixture's child environment and asserted inherited host roots cannot cause sentinel writes.

## Task Commits

1. **Raw-ANSI all-segments golden oracle** — `a0888e219a5d7ea9fe929594146ff614c905c873`
2. **Entry render and strict-provider oracle** — `4c4bcec461df3cf4e4d58e19472429b8a7b29357`

## Files Created/Modified

- `tests/test_status_line.py` — deterministic in-process and subprocess oracle tests.
- `tests/test_system_memory_e2e.py` — scratch-only host roots and sentinel regression.
- `tests/fixtures/golden/inputs_full.json` — six render cases.
- `tests/fixtures/golden/expected_full_ansi.txt` — byte-exact ANSI render oracle.
- `tests/fixtures/golden/entry_payload.json` and `entry_render.txt` — entry input/output oracle.
- `tests/fixtures/golden/strict_provider_capture.json` — provider input/environment/cache oracle.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## Deleted tests

None.

## Verification

- `python3 -m unittest tests.test_status_line.TestFullGoldenAnsi` — passed.
- `python3 -m unittest tests.test_status_line` — passed (307 tests).
- `python3 -m unittest tests.test_system_memory_e2e` — passed.
- `make test-unit` — passed (51/51 system-python modules and 1/1 uv module).
- Fixture checks confirmed six ANSI blocks and required glyphs; provider capture required keys and normalized paths.
- Confirmed no production files changed from `production_base` and `TestGoldenOutput` remained unchanged.

## Next Phase Readiness

The pre-split Claude behavior is pinned for subsequent Part A moves. Downstream preservation checks should compare oracle fixture blobs to the `oracle_commit` above.
