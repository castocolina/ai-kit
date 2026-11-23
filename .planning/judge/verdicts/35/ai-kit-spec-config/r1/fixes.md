# Loop 35 round 1 fixes for ai-kit-spec-config

Bar met (worst 88.0 B, no critical finding); three high findings, all from referee-one, fixed in place under the 3-or-fewer rule. No further round runs and the skill's digest is stale by design until its next loop.

- D8-1 (high): the ranking snippet now narrows `discovered` to the runtimes the user kept at Step 2.2 before building pairs and ranking, with a matching sentence; new eval `edge-declined-runtime-never-presented`. Files: `skills/ai-kit-spec-config/references/cli-model-selection.md`, `skills/ai-kit-spec-config/evals/evals.json`, `tests/test_ai_kit_spec_check_providers.py` (pinned eval id list, test renamed `test_skill_evals_have_the_twelve_cases`).
- D8-2 (high): the migrate-only gate moved from Step 2.1 to Step 1, before the snapshot is saved and before Step 1.5; it now says to stop with no `detect-runtimes --save`, no catalog step and no write; new eval `edge-migrate-only-runs-no-setup`. Files: `skills/ai-kit-spec-config/SKILL.md`, `skills/ai-kit-spec-config/evals/evals.json`.
- D8-3 (high): `references/catalog.md` gets a `## Catalog path` section with `cache-path --kind catalog` before the Discover commands, and item 1 of `cli-model-selection.md` says Step 1.5 printed the same path and carries it forward. Files: `skills/ai-kit-spec-config/references/catalog.md`, `skills/ai-kit-spec-config/references/cli-model-selection.md`, `tests/test_spec_config_catalog_text.py` (allowed command list and named commands gain `cache-path`).

Not fixed (below the fix rule's severity): the medium and low findings of both judges stay in the verdict records.
