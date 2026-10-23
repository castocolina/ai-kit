---
phase: 18-cross-ai-skills-apply-pipeline
plan: 10
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-02]
duration_s: 775
orchestrator_verify: "VERIFY 18-10: 2/2 passed"
---

# Plan 18-10 Complete

Implemented the XAI-02 failure contract in the cross-ai template: stderr-only classification, temp-index tree state, process-group lifecycle, and black-box self-test coverage.

## Accomplishments

- Added the `// <patterns>` block and `classify(stderr, structuredError)`; mapped outcomes to closed exit classes with route-aware billing and `unverified` for unknown git state.
- Added Task 1 self-test cases (quote, billing, auth, perm, quota, crash, nochange, empty, cursor-error) and `TestCrossAiTemplateText.test_patterns_block`.
- Implemented `runChild`/`finalize`, `deadline`/`finalizeBy`/`budgetMs`, async `treeState`, git wrapper, output discipline (`log`/`finished`/`exitFlushed`), and Task 2 self-test cases (dirtycrash, fallback, reedit, hang, not_installed, SIGTERM, gcescape, gcpipe, gcterm, git-before/after/hang).
- Verified: `node --self-test`, `tests.test_cross_ai_runner_e2e`, `TestCrossAiTemplateText`, and `make e2e-test` all pass; `.planning/scripts/cross-ai.mjs` untouched.

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs`
- `tests/test_ai_kit_spec.py`

## Commits

- `6734da9` — feat(18-10): stderr-only classification and the closed exit classes
- `15b43e5` — feat(18-10): temp-index tree id, fallback rules and group kill
