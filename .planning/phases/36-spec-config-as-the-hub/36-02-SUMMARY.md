---
phase: 36-spec-config-as-the-hub
plan: 02
subsystem: planning
tags: [spec-amendment, r13, data-use, pools, judge-bar]

requires: []
provides:
  - "36-SPEC.md: R13 (free model data-use note and owner confirmation), R12 clause (g) (pool key and different-pool fallback), the grok directive, R7 acceptance with placeholder-cli-1, `13 locked`, six R13 edge rows and one R13 prohibition row (edge floor 52/52)"
  - "36-CONTEXT.md: D-20 to D-23, the plan-time decisions record pointer, D-03 and spec_lock refinements"
  - "ROADMAP.md: ai-kit-spec-review judged in loop 36 (Phase 36 criterion 7, Phase 39 criterion 5, Phase 40 criterion 5)"

key-files:
  modified:
    - .planning/phases/36-spec-config-as-the-hub/36-SPEC.md
    - .planning/phases/36-spec-config-as-the-hub/36-CONTEXT.md
    - .planning/ROADMAP.md

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding. Run 1 (lane-36-02, 43 s, AIKIT-XAI status=no_change exit=1 attempts=1 cycles=0): the model read the plan and stopped with an 'incomplete' text, no change. Run 2 (lane-36-02-r2, 227 s, status=ok exit=0 attempts=1 cycles=0, a do-not-stop-early paragraph added to the prompt) committed the SPEC and applied the CONTEXT and ROADMAP edits, then stopped on the dogfood check; the orchestrator committed the second commit."
---

# Phase 36 Plan 02: planning amendments

Two commits (pre-fold): `b85fd2d docs(36-02): amend the phase 36 spec with R13, R12 pools and the grok directive` (lane) and
`8eb8e78 docs(36-02): record D-20 to D-23 and judge ai-kit-spec-review in phase 36` (staged by the lane, committed by me).

## Accomplishments

- SPEC amended per texts T1 to T13 and T21 to T23; the edge-floor engine check prints `ok: true`, 52 floor rows, 52 table rows, nothing missing.
- CONTEXT holds D-20 to D-23, the decisions record bullet and the D-03 note; ROADMAP carries the three judge-bar amendments (3 lines changed).
- `tmp/p36/02/check_amend.py` prints `amend check: ok`.

## Deviations and notes

- The lane stopped before the second commit because its `check_dogfood.py --skip-no-write` run, done under a scratch HOME as the plan's shell rule says,
  failed with `capability ai-kit-commit-fold is inactive: ... no user consent record under GSD_HOME (default HOME)`. That is an artefact of the scratch
  HOME (the consent record lives in the real home), not a content defect. I ran the same check with the real HOME (read-only): exit 0,
  `check-dogfood: ok`, only the expected stale-digest and facts-drift notes (the loop 36 judge plan 36-29 refreshes them).
- Plan 36-01's scratch folder `tmp/p36/01` and this plan's `tmp/p36/02` stay under the ignored `tmp/`.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tmp/p36/02/check_amend.py`: `amend check: ok`; edge_floor check: ok, 52/52; `python3 tools/check_dogfood.py --skip-no-write`: exit 0.
- Read the ROADMAP diff (three single-line amendments, `(JDG-04)` still in Phase 36 criterion 7); commit hooks ran green (second commit: docs only, no modules).

## Self-Check: PASSED
