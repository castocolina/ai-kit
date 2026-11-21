---
phase: 36-spec-config-as-the-hub
plan: 22
subsystem: spec-config
tags: [probe-quota, role-flag, check-only, consent-list]

requires: [36-04, 36-10, 36-21]
provides:
  - "cli.py: probe-quota --role review|execute|both (default review); _role_lanes, _probe_role_keys, _probe_lanes build the probed lanes from the role lists, never the key-merged flat view; _route_reviewers takes an optional lanes argument; under --role both a key that names different lanes in the two roles is probed as its review lane with one stderr line"
  - "check-only.md: the write-risk snippet and the probe command use _probe_lanes(config, 'both') and --role both; the consent list names each entry's model and command; one paragraph on shared keys, usage-limited lanes and the per-run probe spend; edge-case wording names the role orders"
  - "tests/test_role_orders.py: PROBE_ROSTER and TestProbeQuotaRole (6 tests; the module holds 23)"

key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-config/references/check-only.md
    - tests/test_role_orders.py

requirements-completed: [HUB-05]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=787s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 22: probe-quota by role

One commit (pre-fold): `36f60f3 feat(36-22): probe quota by role` (3 files, +208 -17, commit hook passed).

## Accomplishments

- `probe-quota` probes the lane of the requested role: review lanes by default, execute lanes with `--role execute`, both once per key with `--role both`; a usage-limited lane is probed like any other. Tests check the argv each probe ran.
- `--check-only` lists exactly the lanes the probe runs, with model and command; a test executes the reference's snippet.

## Deviations and notes

- Docstrings of the new cli helpers are one line (the plan gave longer ones); one blank line instead of two sits before `_role_lanes` (ruff passes). No file outside the plan's three paths changed. Shipped text edited: `skills/ai-kit-spec-config/references/check-only.md` (a reference, not a SKILL.md).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_role_orders tests.test_ai_kit_spec_check_providers tests.test_config_layers tests.test_ai_kit_spec_routing tests.test_config_callers tests.test_ai_kit_spec tests.test_arch_hardcoded_models tests.test_skill_text_history`: exit 0, 8/8 modules (23, 29, 54, 31, 10, 694, 23 and 45 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole source, reference and test diff against the plan.

## Self-Check: PASSED
