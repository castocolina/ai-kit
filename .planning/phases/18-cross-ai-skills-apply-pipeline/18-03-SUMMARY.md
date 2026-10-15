---
phase: 18-cross-ai-skills-apply-pipeline
plan: 03
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [SKL-01, SKL-03, SKL-04]
duration_s: 354
orchestrator_verify: "VERIFY 18-03: 3/3 passed"
---

# 18-03 — Skill inventory and System One backend signal

Inventory now reports loadable skills (real paths, root escape, Claude plugins), per-host ponytail visibility, and System One backend reachability/key presence without exposing secrets.

## Accomplishments

- Added `skill_scan.py` with `scan_skills`, `plugin_skills`, `ponytail_visibility`, and `system_one_backend` (bounded TCP connect, presence-only key check).
- Wired inventory fields `skills`, `ponytail_visibility`, and `system_one_backend`; removed legacy `project_facts.list_skills`; extended schema-2 validation and test fixtures.
- Added `tests/test_curated_config_skills.py` covering end-to-end inventory, R7/plugin edge cases, ponytail per-host visibility, and backend/sentinel tests.
- Extended `InventoryDeps.connect_fn` and optional `connect_fn` on inventory CLI for injectable connects in tests.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skill_scan.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/project_facts.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py`
- `tests/test_curated_config_skills.py` (new)
- `tests/test_curated_config_inventory.py`
- `tests/test_curated_config_recommend.py`
- `Makefile`, `.pre-commit-config.yaml`

## Commits

- `bdd8600` — feat(18-03): inventory skills with real paths, root escape and plugins
- `cfd4dee` — test(18-03): skill scan, plugin visibility and ponytail per-host cases
- `656b30d` — feat(18-03): System One backend reachability and key presence
