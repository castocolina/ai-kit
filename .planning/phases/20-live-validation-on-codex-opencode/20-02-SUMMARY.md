---
phase: 20-live-validation-on-codex-opencode
plan: 02
subsystem: testing
tags: [eval-harness, resolve-model, matrix, codex, opencode]
requires: ["20-01"]
provides:
  - "host-aware resolve-model oracle (codex, opencode, claude) with the four tier cases"
  - "matrix --host codex|opencode on real node, discriminating Control 1 per host"
affects: ["20-03", "20-04", "20-05", "20-07"]
key-files:
  modified:
    - tests/gsd_curated_eval.py
    - tests/test_gsd_curated_eval.py
    - tests/test_ai_kit_gsd_curated_config_matrix.py
executor: cross-ai (pi router-env/my-coding); SUMMARY written by the orchestrator
requirements-completed: [EVAL-04, EVAL-05]
duration_s: 1770
orchestrator_verify: "VERIFY 20-02: 2/2 passed"
---

# Phase 20 Plan 02: Host-aware resolve-model oracle summary

**The resolve-model oracle and matrix now grade codex and opencode on real node; all three hosts print `matrix ok (420 checks)` and the non-claude refusal is gone.**

## Accomplishments

- Task 1 (ca68924): `promised`/`compare`/`_mismatches` take the host; `live_tables` loads `bin/lib/model-catalog.cjs` and returns `RUNTIME_PROFILE_MAP` as `runtime_profiles`; a non-zero resolve-model exit never supplies passing evidence; `matrix --host codex|opencode`.
- Task 2 (09e61cb): the informational runtime row is claude-only (`informational: null` elsewhere); one mixin builds `TestResolveModelMatrix{,Codex,Opencode}`; refusal tests replaced by per-host oracle and control tests.

## Verification (orchestrator, after the executor's timeout)

- Plan verify 2/2 passed (`tmp/p20/matrix-codex.txt`, `matrix-claude.txt`, `matrix-opencode.txt` all `matrix ok (420 checks)`; unit group 42/42 after e40ced6).
- Acceptance: opencode `controls ok` (Control 1 expected 6 = observed 6, Control 2 ok); codex `codex controls ok` (expected 2); `MESSAGE_NON_CLAUDE` absent; 3 `TestResolveModelMatrix` classes.
- Loader test count for `tests.test_ai_kit_gsd_curated_config_matrix`: **27** (e2e run: `Ran 27 tests`, `OK`).

## Deviations from Plan

- The executor hit the runner's 1770 s deadline (exit 124) after both task commits, before writing this SUMMARY; the orchestrator re-ran every verify and acceptance command and wrote it.
- The unit-group verify exposed a 20-01 miss: `tests/test_ai_kit_spec.py` still pinned template 3 in `test_header_and_config_contract`. Fixed by the orchestrator in e40ced6 (pin moved to 4), not part of this plan's files.

## Product defects

No product defect.

## Issues Encountered

None.
