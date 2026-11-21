---
phase: 36-spec-config-as-the-hub
plan: 28
subsystem: docs
tags: [readme, design-record, agents-md, seed-flag-markdown-scan, doc-pins]

requires: [36-10, 36-14, 36-16, 36-19, 36-25]
provides:
  - "README.md: rewritten rows for ai-kit-spec-review, ai-kit-spec-config and ai-kit-spec-execute-superpowers; the configuration section names the role tables, `config-status`, the delete-after-check migration default and the `.retiring` recovery; the `[models]` line says it is read and written now"
  - "docs/config/design.md: Tables bullets for `[lanes.policy.review]` and `[lanes.policy.execute]` and the new lane keys; the two review-spec rows of Assignments and of Inventory; a new `AI_KIT_KEEP_MIGRATION_BACKUP` bullet under Environment-only settings (`config_migrate.py:61`)"
  - "AGENTS.md: the RUNTIMES bullet names the exec-formula mirror and the seed advice text instead of the review-only flag"
  - "tests/test_no_seed_refusal.py: `seed_flag_markdown_hits` and `TestNoSeedFlagInMarkdown` (2 tests, one non-vacuity case); tests/test_spec_config_flow_text.py: `TestConfigDocsText` (5 tests; module now 40 tests)"

key-files:
  modified:
    - README.md
    - docs/config/design.md
    - AGENTS.md
    - tests/test_no_seed_refusal.py
    - tests/test_spec_config_flow_text.py

requirements-completed: [HUB-01, HUB-05, HUB-07, HUB-10]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=384s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 28: README, design record and AGENTS.md for the hub

One commit (pre-fold): `fc0ba6a docs(36-28): README, design record and AGENTS.md for the hub, seed-flag markdown scan` (5 files, +113 -16, commit hook passed).

## Accomplishments

- A reader of the README, the design record or AGENTS.md sees the hub, the per-role orders and the migration default as shipped.
- No Markdown under `skills/` (outside evals' data), nor AGENTS.md, README.md or docs/config/design.md, names the token `review_only` (`test_no_markdown_names_the_seed_flag` passes with an empty hit list).

## Deviations and notes

- One wording change against plan block G2: the lane wrote "a failed final migration removal" where the plan says "a failed final removal". Same meaning; the pins (`deleted after the value check` twice in Assignments and Inventory, `.retiring`, `keep_backup_from_env`) pass.
- Tests inline the plan's `ADAPTER_ROW` as a wrapped string literal (same value); no behaviour change.
- The baseline entry for `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (`cleaned_by` "36" in `tests/fixtures/no_hardcoded_models_baseline.json`) is NOT touched by this plan; no plan of this wave owns it. It stays for the orchestrator.
- Residual texts that still name a removed or renamed key (none is a `review_only` token): `skills/ai-kit-spec-execute-superpowers/references/escalation.md` lines 26, 106 and 132 still say `policy.ladder` (no plan of this chunk owns that file), and `skills/ai-kit-spec-config/SKILL.md:301` says `That review-only default exists for legacy entries` (it describes the `purpose` default of a pre-migration entry).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_spec_config_flow_text tests.test_no_seed_refusal tests.test_config_design_record tests.test_config_callers tests.test_quota_policy_text tests.test_cross_ai_skill_text tests.test_ai_kit_spec_runtimes_table tests.test_agents_md_links tests.test_arch_hardcoded_models`: exit 0, 9/9 modules (40, 8, 11, 10, 19, 30, 62, 5 and 23 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: rc 0. `rg -c "Phase 36" docs/config/design.md`: no match.

## Self-Check: PASSED
