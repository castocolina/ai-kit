---
phase: 18-cross-ai-skills-apply-pipeline
plan: 11
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-02]
duration_s: 557
orchestrator_verify: "VERIFY 18-11: 2/2 passed"
---

# Plan 18-11: Model preflight and transient retry capacity

Cross-AI runner now preflights models against each CLI’s listing, skips preflight when listings fail, and maps exhausted transient retries to retry-later capacity.

## Accomplishments

- Added `listModels()` (bounded via `runChild`, `min(15s, deadline)`) with parsers aligned to `detection.py` for pi RPC, opencode, cursor-agent, and codex.
- Preflight runs once per candidate before first spawn (skipped under `--print-argv`); absent models → `bad_model` (69) without spawning; unusable listings log a note and run proceeds.
- Updated self-test fakes for listing subcommands and `FAKE_PI_LIST=hang`; added preflight, retry, and capacity self-test cases.
- Transient retries that exhaust `CONFIG.retries` now finish as `capacity` (75, retry-later); fake `flaky` / `overloaded` modes with counter in scratch `$HOME`.

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` — `listModels`, preflight, fake listings, retry-to-capacity, self-test cases
- `tmp/patch_18_11.py` — one-shot patch helper (scratch, gitignored)

## Commits

- `678432c` — feat(18-11): runner preflights the model against each CLI's own list
- `1a0d597` — feat(18-11): transient retries end in retry-later capacity
