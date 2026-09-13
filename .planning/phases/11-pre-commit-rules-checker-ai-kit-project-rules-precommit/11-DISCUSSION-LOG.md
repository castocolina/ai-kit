# Phase 11: Pre-commit Rules Checker (ai-kit-project-rules-precommit) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-13
**Phase:** 11-Pre-commit Rules Checker (ai-kit-project-rules-precommit)
**Areas discussed:** Tool-knowledge convergence (Phase 10 cache vs. Phase 11 taxonomy)

---

## Tool knowledge

| Option | Description | Selected |
|--------|-------------|----------|
| Converge into skills/_shared/ now | Phase 10's Makefile-tooling cache and Phase 11's 6-category taxonomy share one per-language tool catalog in `skills/_shared/ai_kit_rules_common/`. | ✓ |
| Keep Phase 11's taxonomy skill-local | Phase 11 hardcodes the design spec's tables directly; Phase 10 keeps its own separate catalog. | |

**User's choice:** Converge into skills/_shared/ now
**Notes:** Both skills answer overlapping "which tool covers which category, per language" questions about the same concrete tools. Leaving them separate recreates the exact split-ownership drift risk already caught and fixed twice in Phase 10's own discussion.

---

## Claude's Discretion

- Exact bidirectional parity-matching algorithm (exact-string vs. normalized/fuzzy hook-id↔target-name matching).
- Exact shape/location of the converged per-language tool catalog within `skills/_shared/ai_kit_rules_common/`.

## Deferred Ideas

None. A blocking-prerequisite note was recorded (not a deferred idea): Phase 11 depends on both Phase 9 and Phase 10 landing first — see CONTEXT.md's `<domain>` section. The unknown-tool-pair default policy (D-04: presumed-complementary, not presumed-redundant) was stated as an inherited constraint from PROJECT.md's Core Value rather than put to a question, since no real alternative was on the table. `cross_reference_todos` re-confirmed the same 3 historical todos (resolves_phase: 6/7/8) are not live candidates.
