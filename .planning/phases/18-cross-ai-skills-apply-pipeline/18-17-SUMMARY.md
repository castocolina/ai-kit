---
phase: 18-cross-ai-skills-apply-pipeline
plan: 17
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [APP-02]
duration_s: 417
orchestrator_verify: "VERIFY 18-17: 3/3 passed"
---

# 18-17: apply --dry-run pre-flight

Shipped read-only `apply --dry-run`: plan/inventory validation, destination binding, gsd-core key pre-flight, diff report, and script preview — no config writes.

## Accomplishments

- Added `apply.py` with `ApplyDeps`, `load_inputs`, `needs_choice_keys`, `resolve_target`, `preflight`, `diff_entries`, `script_preview`, and `dry_run_report`.
- Wired v2 `apply` in `cli.py` (`_cmd_apply`); non-`--dry-run` exits 2 until 18-18.
- `TestDryRunTracer` covers end-to-end dry-run (config-path + tables node calls, no `config-set`).
- `TestApplyRefusals` covers needs_choice, digest mismatch, binding, node/encoder failures, and load-time plan validation.
- `TestDiffKinds`, `TestDryRunDeterminism`, and `TestApplyDispatch` pin SPEC R12 edges and exact-name handler dispatch.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py`
- `tests/test_curated_config_apply.py`

## Commits

- `3ab07a5` — feat(18-17): apply --dry-run with gsd-core key pre-flight
- `ddead2d` — test(18-17): apply pre-flight refusals
- `c65a0cc` — test(18-17): dry-run diff kinds, ordering and dispatch

## Issues Encountered

- `make pyright` (whole-repo Makefile target) still reports errors outside this plan’s files; `skills/ai-kit-gsd-curated-config/` and `tests/test_curated_config_apply.py` pass pyright when checked directly.
