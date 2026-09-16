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
