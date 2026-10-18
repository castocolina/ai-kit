---
phase: 20-live-validation-on-codex-opencode
plan: 07
subsystem: testing
tags: [codex, opencode, interactive-validation, gates]
requires:
  - phase: 20-06
    provides: Host-aware product labels and headless smoke evidence
provides:
  - Interactive Codex and Opencode EVAL-04/EVAL-05 procedures with retained smoke artifacts
  - Dated D-07 loader-observation and SPEC R5/ROADMAP SC3 amendments
  - Full phase gates and recorded test counts
 affects: [phase-20-verification, curated-config]
actuals:
  tokens: 12000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns: [Human verification remains nonblocking and distinct from headless evidence]
key-files:
  created:
    - .planning/phases/20-live-validation-on-codex-opencode/20-INTERACTIVE-CODEX.md
    - .planning/phases/20-live-validation-on-codex-opencode/20-INTERACTIVE-OPENCODE.md
  modified:
    - .planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-CODEX.md
    - .planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-OPENCODE.md
    - .planning/phases/20-live-validation-on-codex-opencode/20-CONTEXT.md
    - .planning/phases/20-live-validation-on-codex-opencode/20-SPEC.md
    - .planning/ROADMAP.md
    - tests/test_ai_kit_gsd_curated_config_matrix.py
    - tests/test_gsd_curated_eval.py
key-decisions:
  - "Codex and Opencode TUI runs remain human_verification items; headless results do not close EVAL-04/EVAL-05."
  - "The Opencode loader proof is explicitly pending unless standalone run events identify exactly the single baked model."
  - "Fix the pyright failure in the matrix test mixin and nullable assertion within the one-module D-04 threshold."
requirements-completed: [EVAL-04, EVAL-05]
coverage:
  - id: D1
    description: Interactive-run scripts document host-specific evidence collection, protected smoke operation, and retained artifacts.
    requirement: EVAL-04
    verification:
      - kind: manual_procedural
        ref: "20-INTERACTIVE-CODEX.md and 20-INTERACTIVE-OPENCODE.md; dry-run command syntax checks"
        status: pass
    human_judgment: true
    rationale: The actual TUI runs must be performed and returned by the user; scripts are procedures, not live evidence.
  - id: D2
    description: D-07, SPEC R5 adjacency, and ROADMAP SC3 accurately state loader scope and optional probe status.
    verification:
      - kind: other
        ref: "Task 1 automated verify and amendment checks"
        status: pass
    human_judgment: false
  - id: D3
    description: Repository gates and container gate pass with recorded nonzero test counts.
    verification:
      - kind: integration
        ref: "tmp/p20/gates/test.txt; tmp/p20/gates/validate.txt; tmp/p20/gates/validate-unittest.txt; tmp/p20/gates/docker.txt"
        status: pass
    human_judgment: false
  - id: D4
    description: Pyright failures discovered by make validate are fixed and verified.
    verification:
      - kind: unit
        ref: "uv run pyright tests/test_ai_kit_gsd_curated_config_matrix.py tests/test_gsd_curated_eval.py"
        status: pass
    human_judgment: false

# Metrics
duration: 28 min
completed: 2026-10-18
status: complete
orchestrator_verify: "VERIFY 20-07: 2/2 passed"
---

# Phase 20 Plan 07 Summary

**Interactive host evidence scripts and phase-gate records now preserve the Codex/Opencode verification boundary, including required Opencode lane and loader checks.**

## Performance

- **Duration:** 28 min (within the dispatched run; dates are system UTC date)
- **Started:** 2026-10-18
- **Completed:** 2026-10-18
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added per-host interactive procedures with names-only environment capture, fresh snapshot baselines, smoke artifacts, and post-smoke checks. Opencode steps 6 and 7 are required and specify four lane trials plus evidence-based loader precedence outcomes.
- Amended D-07 with the `debug agents` limitation and per-agent scope, updated the R5 adjacency row, clarified ROADMAP SC3, and replaced both smoke placeholders with the pending interactive evidence requirements.
- `make test`, `make validate`, verbose pre-push unittest, and `make e2e-docker` passed. Initial validation discovered a pyright defect; fixed in a same-plan test-only commit and reran gates successfully.

## Task Commits

1. **Task 1: Interactive host scripts and source amendments** — `223f32b` (`docs(20-07): add interactive host evidence scripts`)
2. **D-04 gate fix: test type annotations** — `2619290` (`fix(20-07): make matrix test mixin type-checkable`)
3. **Task 2: Gate evidence, smoke closures, and summary** — this commit

## Files Created/Modified

- `.planning/phases/20-live-validation-on-codex-opencode/20-INTERACTIVE-CODEX.md` — Codex interactive evidence procedure.
- `.planning/phases/20-live-validation-on-codex-opencode/20-INTERACTIVE-OPENCODE.md` — required lane and loader steps, optional SC3 probe.
- `.planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-CODEX.md`, `20-SMOKE-OPENCODE.md` — interactive pointers and gate results.
- `.planning/phases/20-live-validation-on-codex-opencode/20-CONTEXT.md`, `20-SPEC.md`, `.planning/ROADMAP.md` — dated amendments.
- `tests/test_ai_kit_gsd_curated_config_matrix.py`, `tests/test_gsd_curated_eval.py` — pyright correction with verification.

## Fixes

The initial `make validate` found 23 pyright errors: the shared matrix mixin did not inherit `unittest.TestCase`, and a test passed a nullable mismatch string to `assertIn`. Commit `2619290` fixes both; targeted pyright reports zero errors. Subsequent `make validate` and full `make test` passed. No product bug fix or decimal phase was needed.

## Human verification

- Codex interactive run: pending; follow `20-INTERACTIVE-CODEX.md`. The TUI names-only list determines whether `CODEX_THREAD_ID` and `CODEX_VERSION` labels can move from pending to the confirmed outcome. Any signal table change and `tests/test_ai_kit_spec_runtimes_table.py` update belong together under D-04.
- Opencode interactive run: pending; follow `20-INTERACTIVE-OPENCODE.md`. Required Step 6 performs two trials each for `/gsd-review --phase 20 --opencode` and `review.default_reviewers=["opencode"]`; LLM-judged behavior requires actual user-session model calls. Required Step 7 uses loader output to prove or leave R5 pending; `debug agents` shared-service output is supporting evidence only. The dated D-07 and R5 amendments document this boundary.
- Native per-call probe is optional: ROADMAP SC3 is an OR and the `native_selectors == ()` session-default branch is already pinned; live probing can only upgrade a label later.

## Environment findings

- Initial validate failed only on the test typing defects fixed in `2619290`; final run passed.
- Docker E2E passed (`exit=0`). No container-engine absence or interactive host environment findings.
- The older plan04 baseline also reported `snapshot ok`; it is informational, while the plan07 baseline is the gate.

## Process proof

- No `gc-late` or `node -e while` descendants were listed after self-test/gate work.
- Compared process list against `tmp/p20/headless/ps-before.txt`: existing Codex daemon and managed Opencode service remained; the three cross-AI processes (PIDs 322315, 322317, 322325) were already present in the 20-04 baseline (PIDs 88564, 88566, 88573) and belong to the other active execution, not this plan. They were left untouched. No process started by this plan remains.

## Gate counts

- `make test`: `exit=0`; 56 module result lines, 4,343 tests total. Matrix module ran 36; loader found 9 tests in each of the three host classes, total 36. The matrix and e2e tier ran only once as part of `make test`.
- `make validate`: `exit=0`; all hooks passed.
- Verbose pre-push unittest: `exit=0`; 43 modules, 4,125 tests total.
- `make e2e-docker`: `exit=0`.
- Snapshot: plan07 `snapshot ok`; plan04 `snapshot ok` (information).
- Secret scan clean; phase `$HOME` literal scan clean.

## Deviations from Plan

A make-validate failure prompted an in-scope D-04 type fix to one Python test module; the regression verification is included in the same commit. Otherwise, the planned work was followed. Human host procedures remain pending by design and are not blocking checkpoints.

## Issues Encountered

None unresolved. The initial pyright failure was fixed and all required gates were rerun successfully.

## Next Phase Readiness

The interactive procedures are ready for user execution. EVAL-04/EVAL-05 must remain pending until their respective TUI evidence is returned and analyzed.

---
*Phase: 20-live-validation-on-codex-opencode*
*Completed: 2026-10-18*
