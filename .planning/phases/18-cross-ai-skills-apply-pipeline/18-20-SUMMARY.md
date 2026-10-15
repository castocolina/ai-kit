---
phase: 18-cross-ai-skills-apply-pipeline
plan: 20
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [APP-04]
duration_s: 315
orchestrator_verify: "VERIFY 18-20: 3/3 passed"
---

# Plan 18-20: Post-apply follow-ups with grouped approval

Closed the apply loop with a follow-ups block (pinned local gsd-core installer, effort sync when needed, map-codebase recommendation) and a `followups --approve` gate.

## Accomplishments

- Added `followups.py` with `build_followups` / `run_followups`, plan-time and apply-written key union via `--require`, workstream skips for claude/opencode effort sync, disclosures, and `host.resolve_gsd_core` for local gsd-tools.
- Wired apply success reports to include a non-executing `followups` block and a new CLI `followups` subcommand with destination binding via `apply.resolve_target`.
- Added `tests/test_curated_config_followups.py` covering tracer, effort sync, ordering, disclosures, approval gate, drift, idempotency, and destination binding; regenerated Makefile / `.pre-commit-config.yaml` test groups.
- Verified `python3 -m unittest tests.test_curated_config_followups tests.test_curated_config_apply tests.test_gate_scope` and `make test-unit`.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py`
- `tests/test_curated_config_followups.py` (new)
- `Makefile`, `.pre-commit-config.yaml`

## Commits

- `b5bef71` — feat(18-20): grouped follow-ups with the pinned local installer
- `0176185` — feat(18-20): effort sync follow-up, workstream skip, ordering, disclosures
- `6aefb0d` — feat(18-20): follow-ups for apply-written keys, approval gate, re-run reporting
