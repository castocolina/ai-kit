# Phase 15: Rules Orchestrator (ai-kit-project-rules-all) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-13
**Phase:** 15-Rules Orchestrator (ai-kit-project-rules-all)
**Areas discussed:** Invocation model, partial-failure handling

---

## Invocation model

| Option | Description | Selected |
|--------|-------------|----------|
| Subprocess dispatch, parse stdout JSON | Call each checker's standalone CLI entry script, parse its JSON output. | ✓ |
| Direct Python import across skill packages | Import each checker's cli module directly. | |

**User's choice:** Subprocess dispatch
**Notes:** Matches the existing, working CLI contract every checker already exposes; keeps every checker independently copyable, consistent with the family's own "no skill imports another skill's package directly" convention.

---

## Partial failure

| Option | Description | Selected |
|--------|-------------|----------|
| Report the failure inline, continue aggregating the other 5 | A failed checker produces a labeled error entry; the rest of the report proceeds normally. | ✓ |
| Abort the whole aggregation if any checker fails | A single checker failure produces no report at all. | |

**User's choice:** Report inline, continue
**Notes:** Matches Success Criterion 1's "none silently dropped" and PROJECT.md's confidence-labeling Core Value — "couldn't check" must be visibly distinct from "checked, no findings."

---

## Claude's Discretion

- Parallel vs. sequential subprocess dispatch; timeout handling.
- Exact schema for a failure entry in the aggregated report.

## Deferred Ideas

None. `cross_reference_todos` re-confirmed the same 3 historical todos are not live candidates. The blocking-prerequisite note (Phases 9-14 must land first) was recorded in CONTEXT.md's `<domain>` section — this is the deepest context-ahead-of-execution gap in the family (all 6 prior phases still unplanned).
