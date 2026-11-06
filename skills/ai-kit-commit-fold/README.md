# ai-kit-commit-fold

Folds a finished GSD or superpowers plan's commits into one commit per logical feature. The skill
text is `SKILL.md`; the one policy every fold follows is `references/folding-policy.md`.

## Unit flow

On top of the fold, the skill runs the unit flow: `fold.py start` creates a unit's branch on the stack
top, `fold.py checkpoint` folds and pushes it (the first push opens a draft PR), and `fold.py ready`
marks the PR ready after verification. Restack, hotfix, merge-chain, settings and push consent are
the same `fold.py` CLI. Pushes need push consent, granted once per repository. The contract any
planning system can plug into is `references/unit-contract.md`; the GSD and superpowers adapters are
in `references/adapter-guide.md`.

## Files

- `SKILL.md`: how to run the fold, the unit flow, push consent, cascade conflicts and the GSD hooks.
- `fold.py boundary` (`--point start|plan|wave`): one unit boundary run (index refresh and the unit brief); `fold.py index` refreshes the codegraph index and the graphify graph.
- GSD hook points: `discuss:pre` step `ai-kit-fold start`, `plan:pre` planner contribution (`ai-kit-fold boundary-plan`), `execute:wave:pre` step `ai-kit-fold boundary-wave`, `execute:wave:post` step `ai-kit-fold checkpoint`, `ship:pre` gate `ai-kit-fold ship`.
- `references/unit-contract.md`, `references/adapter-guide.md`: the neutral unit contract and the adapters.
- `scripts/`: the engine (`fold.py` entry point, `fold_engine.py`, `fold_adapters.py`, `fold_group.py`).
- `references/folding-policy.md`: the policy text; each rule is pinned by a doc-contract check in `tests/test_arch.py`.
- `gsd/ai-kit-commit-fold/`: the GSD capability bundle (`capability.json`, `ai-kit-fold.cjs`).

## Tests

`tests/test_ai_kit_commit_fold*.py`. `tests/test_ai_kit_commit_fold_e2e.py` runs the capability
through the checkout's project-local gsd-core in a temp fixture project.

## Status

A temporary home: the engine is planned to move into `ai-kit-project-rules`.
