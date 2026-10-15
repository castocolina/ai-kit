---
phase: 18-cross-ai-skills-apply-pipeline
plan: 09
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-02]
duration_s: 296
orchestrator_verify: "VERIFY 18-09: 3/3 passed"
---

# Plan 18-09 — Cross-AI runner template v2

Shipped a versioned `cross-ai.mjs` template with a single `AIKIT-XAI` status line on every exit, hermetic black-box `--self-test`, and contract tests for the renderer.

## Accomplishments

- Added `skills/ai-kit-spec-review/references/cross-ai.mjs` (template=2, UNSTAMPED): default CONFIG, `finish()` status mapping, pi/cursor/opencode/codex runtimes (no grok target), hermetic self-test with fake CLIs and argv/parser coverage.
- Added `resolve_cross_ai_template_path()` in `tooling_guidance.py`.
- Added E2E module `tests/test_cross_ai_runner_e2e.py` (`runner_env`, `TestRunnerTemplate.test_self_test`) and registered it in `E2E_MODULES` (Makefile / `.pre-commit-config.yaml` regenerated).
- Added `TestCrossAiTemplateText` in `tests/test_ai_kit_spec.py` for header, CONFIG, scrub drift, and retired-CLI region checks.
- Verified: `node --check`, `node … --self-test`, unit/E2E gates, prototype `.planning/scripts/cross-ai.mjs` unchanged.

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` (new)
- `tests/test_cross_ai_runner_e2e.py` (new)
- `skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py`
- `tests/test_ai_kit_spec.py`
- `tools/run_unittest_parallel.py`
- `Makefile`
- `.pre-commit-config.yaml`

## Commit hashes

- `c75f1b8` — feat(18-09): cross-AI runner template with status line and hermetic self-test
- `15135f1` — feat(18-09): runner runtime blocks and template path resolver
- `c68e3f4` — test(18-09): runner template header, CONFIG and scrub-list contract
