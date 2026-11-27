---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 07
subsystem: ai-kit-spec-review (lane_transport, lane_settings) and ai-kit-spec-config (references)
tags: [transport, resume, pane, lane-flag, spec-config]
requires: [42-06]
provides:
  - "lane_transport.py: TRANSPORTS, TRANSPORT_RENEW_ROUNDS = 3, RECORD_VERSION = 1, PANE_RENEWED, PANE_LABEL (unverified), TransportRequest (lane_id, runtime, interactive, verified, herdr_ok, model, mode), TransportChoice, verified_transports, choose_transport, record_round, read_record, write_record"
  - "tests/test_lane_transport.py fixture helpers describe_fact, runtimes_snapshot, request for later plans"
  - "lane_settings.py: interactive as the last LANE_FLAG_KEYS item (not model-bound), lane_interactive(entry)"
  - "spec-config wizard-flow.md section 10 asks once which lanes are interactive; config-file.md lists the key, its write rule and the example lane review-second with \"interactive\": true"
affects: [42-08, 42-09]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py
    - tests/test_lane_transport.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
    - tests/test_lane_settings.py
    - skills/ai-kit-spec-config/references/wizard-flow.md
    - skills/ai-kit-spec-config/references/config-file.md
    - tests/test_spec_config_flow_text.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "Anchor correction: detection.py has no detect_runtimes; the snapshot's listed_from field is set in build_runtimes_snapshot (read only, not edited)"
metrics:
  tasks: 2
  commits: 2
---

# Phase 42 Plan 07: lane transport chooser and the interactive lane flag Summary

Each lane round now has a transport choice: a fresh subprocess, a resumed session or a herdr pane. A resume is
offered only when the runner's session label reads `verified` for the installed host version (the snapshot's
`clis.<id>.listed_from.version`) and the call's mode is not in the runner's `noResume` list; a pane only for an
interactive lane with a verified pane label and herdr present. A session is reused for at most three rounds by the
same runtime, model and mode, then renewed; a per-plan record round-trips through the cache helpers. With today's
labels (every resume and the pane label unverified) every choice is a fresh subprocess. The owner's `interactive`
marker is a lane flag read only through `lane_interactive`, and spec-config writes it only as `true` for a lane the
owner names.

## Commits

- `81238cb` feat(42-07): lane transport chooser with verified labels, renewal and a per-plan record (Task 1)
- `c0e7765` feat(42-07): interactive lane flag written only when the owner names a lane (Task 2)

## Lane history

- Task 1: per-task fix-up lane `42-07-fix-a` (pi router-env/my-coding), status ok, 709 s, one commit; hook 232/232 +
  22/22 uv (full unit and arch: the listings were staged).
- Task 2: lane `42-07-fix-b`, status ok, 394 s, one commit; hook 164/164 + 21/21 uv.
- Both hooks deferred `tests.test_ai_kit_gsd_curated_config_matrix` to push (over the 60 s commit budget). I ran it
  under the guard at the clean plan HEAD `c0e7765`: 35 tests ok in 150.2 s, 1/1 modules passed (guard peak 0).
- The fix-up prompts were built before this chunk (from the plan text at `f53b133`) and carried the checked anchors.

## Checks (own runs)

- Acceptance greps of both tasks: every EXPECT value met (renew constant 1, five public defs 5, pane label literal 1,
  formula test 1, fixture helpers 3, listings name the module in Makefile 1 and .pre-commit-config.yaml 2; flag tuple
  1, `lane_interactive` def 1, READERS row 1, wizard line 1, example `"interactive": true` 1).
- Modules: `test_lane_transport` (20 tests), `test_lane_settings` (63), `test_spec_config_flow_text` (43),
  `test_spec_config_lane_json` (6), `test_adapter_escalation_flags` (32), `test_ai_kit_spec_superpowers` (208),
  `test_gate_scope` (62), `test_arch` (118), `test_arch_hardcoded_models` (23), `test_skill_text_history` (45): all ok.
- Gates: unit+arch `210/210 modules passed` (guard peak 7, no kill); `make test-integration` 9/9 modules passed;
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0.
- Diff review against the plan: a bool `rounds` is refused, None entry fields never count as bound, the pane branch
  comes before the resume check, `PANE_LABEL` reads unverified and is read at call time, `record_round` copies its
  input. The new config-file.md sentence that a pair change keeps `interactive` matches `MODEL_BOUND`, which does not
  name it while it names the escalation and usage-limit keys.
- Scope from the plan base `96024af`: exactly the nine `files_modified` paths. Added shipped lines carry no phase,
  decision or requirement id and no date; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.
- `skills/ai-kit-spec-config/SKILL.md` unchanged (256 lines before and after); no SKILL.md changed in this plan.

## Deviations

- Plan text versus code: the plan named `def detect_runtimes(` in detection.py; the snapshot field is set in
  `build_runtimes_snapshot` (read only, no edit needed).
- Task 1 test: the plan's loop spreading `request(verified, **pair)` failed pyright (str values could reach the bool
  parameters); the lane wrote the three cases as keyword calls (`model=`, `runtime=`, `mode=`) with the same
  assertions. The `request` helper keeps the plan's `**pair` signature.
- Task 2: the `lane_interactive` docstring wraps onto two lines for the 100-column bar (same wording).
