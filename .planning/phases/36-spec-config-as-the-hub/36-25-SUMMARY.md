---
phase: 36-spec-config-as-the-hub
plan: 25
subsystem: spec-config
tags: [skill-skeleton, headless-stop, config-file, doc-contract-tests]

requires: [36-23, 36-24]
provides:
  - "skills/ai-kit-spec-config/SKILL.md rewritten as the step skeleton (484 to 423 lines): new description naming both callers, four new NEVER items, the no-way-to-ask stop right after Step 1's detection commands, Step 2.2 pointing at wizard-flow.md and free-lanes.md, per-role orders in Step 3 and Step 4, the keep-backup answer on both replacement routes, placeholders only in Step 2.7"
  - "references/headless.md (new, 21 lines): the no-way-to-ask block"
  - "references/config-file.md: role tables, `## Lane settings` (every MODEL_BOUND key), migration default, `## Read-only commands`"
  - "tests/test_spec_config_flow_text.py: TestSkillSkeleton (13 tests) and TestConfigFileText (2 tests); the module now holds 35 tests"

key-files:
  created:
    - skills/ai-kit-spec-config/references/headless.md
  modified:
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/config-file.md
    - tests/test_spec_config_flow_text.py

requirements-completed: [HUB-01, HUB-05, HUB-07, HUB-10]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=199s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 25: spec-config skeleton, headless stop and config-file lane settings

One commit (pre-fold): `5552477 docs(36-25): spec-config skeleton, headless stop and config-file lane settings` (4 files, +213 -119, commit hook passed). SKILL.md after the edit: `skills/ai-kit-spec-config/SKILL.md`, 423 lines (cap 500).

## Accomplishments

- A run with no way to ask stops after the two detection commands, prints the block of `references/headless.md` and writes no config, cache or trust record.
- SKILL.md is a skeleton over the question flow; the owner-pick, herdr, data-use and flag rules are NEVER items.
- config-file.md names both role tables, every model-bound lane key, the delete-after-check migration default (`AI_KIT_KEEP_MIGRATION_BACKUP=1`, `render-toml --keep-backup`) and the read-only commands.

## Spec statements without a plan task (SPEC R13, D-23)

- Per-model page rule: `skills/ai-kit-spec-config/SKILL.md:164` (Step 2.2) says the data-use note is read once per chosen model from that model's own vendor page, a page read for another model is never its source, and a model the provider page does not name gets `unknown` with source `none`.
- Doc-contract pin: `tests/test_spec_config_flow_text.py:279` (phrase `once per chosen model`, inside `test_step_2_2_points_to_the_flow`).

## R13 concurrency

The wizard composes the data-use note and the confirmation in memory and writes them through the same atomic splicing writer (`render-toml`), so the last writer wins and nothing else is shared. No code needed.

## Deviations and notes

- The tests are lighter in form than the plan text: the named module constants `HEADLESS_SENTENCE`, `HEADLESS_LINES`, `DETECT_TOOLS_CMD`, `CHECK_ONLY_BRANCH`, `SAVE_CMD`, `NEVER_ADDITIONS`, `REPLACEMENT_GATE`, `GLOBAL_ASK` are inlined as literals in the tests (only `SKILL`, `HEADLESS`, `CONFIG_FILE`, `KEEP_ENV`, `KEEP_ANSWER` are module constants). The test bodies check the same phrases and orders; `test_headless_stop_comes_right_after_detection` pins the shorter marker `If the host has no structured-question tool` instead of the full sentence. No behaviour is lost; flagged for code review.
- Every other text block of the plan (S1 to S5, T1 to T19, C1 to C5, headless.md) is present verbatim in the files and every OLD block is gone (checked by `tmp/run-2026-11-19/blk_check.py`).
- `skills/ai-kit-spec-config/SKILL.md:301` still says `That review-only default exists for legacy entries`: it describes the `purpose` default of a pre-migration entry, not the removed `review_only` key (no `review_only` token is left in the skill folder).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py` over tests.test_spec_config_flow_text (35), test_spec_config_lane_json (6), test_config_callers (10), test_skill_text_history (45), test_arch_hardcoded_models (23), test_ai_kit_spec_check_providers (29), test_spec_config_catalog_text (6), test_cross_ai_skill_text (30), test_ai_kit_spec_runtimes_table (62), test_skill_frontmatter (7): exit 0, 10/10 modules.
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: rc 0.

## Self-Check: PASSED
