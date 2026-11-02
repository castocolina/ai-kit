---
phase: 18-cross-ai-skills-apply-pipeline
plan: 12
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-02]
duration_s: 541
orchestrator_verify: "VERIFY 18-12: 2/2 passed"
---

# Plan 18-12 — Cross-AI review contract, deadline, and knobs

Implemented XAI-02 in `cross-ai.mjs`: review-mode git contract, claude review-only, workstream-aware deadlines, and per-candidate knobs; self-test and e2e verification passed.

## Accomplishments

- Review mode treats a clean tree as success and any write as `contract_violation` (no fallback); null before/after snapshots yield `unverified`; pre-retry tree checks block review retries after a write.
- Added `retryArgv` (review re-runs fresh review argv; exec keeps resume), `--print-argv` retry stderr lines, claude review-only block with fake `claude`, and Task 1 self-test cases.
- Replaced `outerTimeoutS` with `liveOuterTimeoutS` (honors `GSD_WORKSTREAM`), fixed `innerTimeoutS` with a 1s margin floor, deadline stderr line, knob flags (`--codex-effort`, `--codex-service-tier`, `--cursor-mode`), `extraArgs` wiring, and `outer-race` elapsed-time case.
- Verified: `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test`, `make e2e-test`, `tests.test_cross_ai_runner_e2e`, and `TestCrossAiTemplateText`; supervisor script unchanged.

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs`

## Commits

- `d6ae25b` — feat(18-12): review contract and claude review-only block
- `856f0a9` — feat(18-12): live workstream-aware deadline and per-candidate knobs
