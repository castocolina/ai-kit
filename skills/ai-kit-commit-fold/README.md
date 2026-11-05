# ai-kit-commit-fold

Folds a finished GSD or superpowers plan's commits into one commit per logical feature. The skill
text is `SKILL.md`; the one policy every fold follows is `references/folding-policy.md`.

## Files

- `SKILL.md`: how to run the fold, read its report and install the GSD capability.
- `scripts/`: the engine (`fold.py` entry point, `fold_engine.py`, `fold_adapters.py`, `fold_group.py`).
- `references/folding-policy.md`: the policy text; each rule is pinned by a doc-contract check in `tests/test_arch.py`.
- `gsd/ai-kit-commit-fold/`: the GSD capability bundle (`capability.json`, `ai-kit-fold.cjs`).

## Tests

`tests/test_ai_kit_commit_fold*.py`. `tests/test_ai_kit_commit_fold_e2e.py` runs the capability
through the checkout's project-local gsd-core in a temp fixture project.

## Status

A temporary home: the engine is planned to move into `ai-kit-project-rules`.
