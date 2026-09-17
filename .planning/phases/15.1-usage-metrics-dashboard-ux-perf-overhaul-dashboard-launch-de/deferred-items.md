# Deferred Items — Phase 15.1

Items discovered during execution that are out of this phase's declared file
scope (`skills/ai-kit-usage-metrics/ai_kit_usage_metrics/{refiner,dashboard,cli}.py`,
`tests/test_ai_kit_usage_metrics.py`) and were therefore NOT fixed, per the
executor's Scope Boundary rule.

## Plan 01

- **`tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image`
  fails on this machine** — `mermaid-cli`'s pnpm-global install is missing
  `node_modules/@mermaid-js/mermaid-cli/src/cli.js`
  (`MODULE_NOT_FOUND` at `/home/bazzite/.local/share/pnpm/global/v11/...`).
  Confirmed pre-existing and unrelated to this plan: the failing file
  (`skills/markdown-to-pdf/scripts/render_mermaid.py`) is not in Plan 01's
  `files_modified`, and `make test-unit` reproduces the identical single
  error both before and after this plan's changes. Environment issue on
  this machine (stale/incomplete `mmdc` global install), not a code defect.
- **`uv run pre-commit run pyright --hook-stage pre-push`** reports one
  pre-existing error in
  `skills/ai-kit-project-rules-precommit/ai_kit_project_rules_precommit/pair_checks.py:178`
  (`"object" is not iterable`). None of this plan's 4 touched files
  (`refiner.py`, `dashboard.py`, `cli.py`, `tests/test_ai_kit_usage_metrics.py`)
  are implicated — pyright type-checks the whole project, and this finding
  is entirely outside Plan 01's scope.

## Plan 03

- **`ruff check tests/test_ai_kit_usage_metrics.py`** reports one
  pre-existing `E501` (line too long) at `tests/test_ai_kit_usage_metrics.py:1242`,
  in `_codex_custom_tool_call_line`'s signature — introduced by Plan 02's
  commit `5825442a` (2026-09-16), not touched by this plan. Confirmed via
  `git blame`; none of Plan 03's own additions to this file are involved.
- `tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image`
  still fails on this machine for the same pre-existing `mmdc` reason logged
  under Plan 01 above — reconfirmed via `make test-unit`, still the only
  error in the full 2510-test run.

## Plan 04

- `tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image`
  still fails on this machine for the same pre-existing `mmdc` reason logged
  under Plan 01 above — reconfirmed via `make test-unit` (2518 tests, 1
  error, 20 skipped — the identical single error). None of this plan's 3
  touched files (`dashboard.py`, `refined_store.py`,
  `tests/test_ai_kit_usage_metrics.py`) are implicated.

## Plan 05

- `tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image`
  still fails on this machine for the same pre-existing `mmdc` reason logged
  under Plan 01 above — reconfirmed via `make test-unit` (2525 tests, 1
  error, 20 skipped — the identical single error, same `MODULE_NOT_FOUND`
  at the same pnpm-global path). `git log -- tests/test_markdown_to_pdf.py
  skills/markdown-to-pdf/scripts/render_mermaid.py` shows no commit from
  this phase (15.1) touches either file — confirmed pre-existing and
  outside this plan's scope, not fixed here.
- `tests.test_ai_kit_usage_metrics.py:1242` `ruff` `E501` — same
  pre-existing finding logged under Plan 03, still present, still
  untouched by this plan's own additions to the file.
