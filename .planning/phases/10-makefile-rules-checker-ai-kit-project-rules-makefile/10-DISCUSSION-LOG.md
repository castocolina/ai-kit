# Phase 10: Makefile Rules Checker (ai-kit-project-rules-makefile) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-13
**Phase:** 10-Makefile Rules Checker (ai-kit-project-rules-makefile)
**Areas discussed:** Precommit-parsing helper ownership, stack-detection helper ownership

---

## Precommit helpers

| Option | Description | Selected |
|--------|-------------|----------|
| Move to skills/_shared/ now | `parse_precommit_hooks`, `_iter_precommit_hook_blocks`, `check_precommit_prepush_split` relocate to `skills/_shared/ai_kit_rules_common/` as part of this phase's own commit. | ✓ |
| Land in Phase 10 only; Phase 11 figures it out later | Keep them skill-local to `ai-kit-project-rules-makefile`; defer ownership to Phase 11. | |

**User's choice:** Move to skills/_shared/ now
**Notes:** These functions are load-bearing for Phase 10's own `check_makefile_shape` (unions `REQUIRED_STATIC_TARGETS` with pre-commit hook ids) AND explicitly named as Phase 11's inherited functions for the Makefile↔pre-commit parity check — leaving them skill-local would force either a forbidden cross-skill import or near-duplicate reimplementation later.

---

## Stack detection

| Option | Description | Selected |
|--------|-------------|----------|
| Move detect_stacks to skills/_shared/ now | `stack_detect.py`'s `detect_stacks()` relocates alongside the already-shared `stack_cache.py`. | ✓ |
| Keep detect_stacks in ai-kit-project-rules-makefile only | Leave it skill-local; revisit later if another phase needs it. | |

**User's choice:** Move detect_stacks to skills/_shared/ now
**Notes:** Stack-aware tooling recommendations recur in Phase 11 (tooling taxonomy) and Phase 13 (docker) — keeping stack detection paired with the stack-tooling cache in one shared location avoids a second split-ownership gap identical to the precommit-helpers one.

---

## Claude's Discretion

- Exact "`docker-up`-shaped target" detection heuristic (regex vs. fixed name list).
- Whether the shellcheck-threshold check's CI-config cross-check is stubbed now or left fully to Phase 15's orchestrator — the design spec already scopes this ("standalone... can only confirm the Makefile+pre-commit halves"), so this is an implementation note, not an open decision.
- Whether to migrate the current skill's Makefile-checker test fixtures verbatim or write fresh ones.

## Deferred Ideas

None. A flag was raised (not a deferred idea, a blocking prerequisite): Phase 10 cannot actually be planned/executed until Phase 9 lands — see CONTEXT.md's `<domain>` section. `cross_reference_todos` was re-run for this phase and found the same 3 historical todos (resolves_phase: 6/7/8) already confirmed not live candidates during Phase 9's discussion.
