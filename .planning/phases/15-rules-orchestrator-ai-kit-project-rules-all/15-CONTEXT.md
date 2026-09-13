# Phase 15: Rules Orchestrator (ai-kit-project-rules-all) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning — BLOCKED on Phases 9-14 landing first (see Phase Boundary)

<domain>
## Phase Boundary

New orchestrator skill `ai-kit-project-rules-all` runs all 6 checkers'
`check`/`remediate` against one target repo and aggregates their findings
into one criticality-ordered report. Preserves the existing
`/agent-md-refactor` hand-off for AGENTS.md-domain findings only; every
other domain's findings are inline, report-only, no auto-apply. Cross-
skill merging of findings across domains exists only inside this
orchestrator, never inside any individual checker's own `remediation.py`.

This is the LAST phase in the v1.2 family's strict dependency chain — it
needs all 5 new domain checkers (makefile, precommit, arch, docker, cicd)
plus the Phase 9-pruned agents checker to exist before it has anything to
invoke.

**Hard prerequisite — this phase cannot be planned or executed before
Phases 9-14 actually land.** `.planning/ROADMAP.md`'s "Depends on" line
for Phase 15 names Phase 14 directly, with the explicit rationale that all
6 checkers must exist first. As of this discussion, NONE of Phases 9-14
have a plan or execution yet (each has only a CONTEXT.md) — this is the
deepest context-ahead-of-execution gap in the family so far.

</domain>

<decisions>
## Implementation Decisions

### Invocation model
- **D-01:** The orchestrator invokes each of the 6 checkers via subprocess
  dispatch, parsing each one's stdout JSON — NOT via direct Python import
  across skill packages. Confirmed via the current codebase: every
  checker already exposes a standalone CLI entry script (e.g.
  `skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-
  checker.py`) whose `check` subcommand does `print(json.dumps(check(
  repo_root), indent=2))` — this is the existing, working contract every
  checker already honors. Subprocess dispatch is also the only invocation
  model consistent with the "no skill imports another skill's package
  directly" convention (`.planning/intel/constraints.md` §"Shared package
  import convention") — a direct Python import would make the
  orchestrator the one skill in the family that violates its own family's
  independently-copyable design rationale.
  — **Reversibility:** costly — switching to direct imports later means
  restructuring every checker's packaging/import surface, not a local
  tweak.

### Partial-failure handling
- **D-02:** If one checker's subprocess invocation fails (non-zero exit,
  crash, malformed JSON on stdout), the orchestrator reports that failure
  inline as a labeled entry in the aggregated report and continues
  aggregating the other 5 checkers' real findings — it does NOT abort the
  whole run. Rationale: ROADMAP Success Criterion 1's "none silently
  dropped" would itself be violated by a crashed checker's domain
  vanishing from the report with no explanation; this also follows
  `PROJECT.md`'s confidence-labeling Core Value — "couldn't check this
  domain" must be visibly distinct from "checked, no findings," never
  conflated.
  — **Reversibility:** reversible — switching to abort-on-any-failure
  later is a small control-flow change, not a migration.

### Everything else — already locked by ROADMAP + design spec
- **D-03:** The criticality-ordered aggregation (Success Criterion 2), the
  AGENTS.md-only `/agent-md-refactor` hand-off preservation (Success
  Criterion 3), the stubbed-integration-test shape (Success Criterion 4),
  and the cross-skill-merging-only-in-the-orchestrator boundary (Success
  Criterion 5) are accepted as written — no scope changes surfaced.

### Claude's Discretion
- Exact subprocess-invocation mechanics (parallel vs. sequential dispatch
  of the 6 checkers; timeout handling) — D-01/D-02 lock the model and the
  failure-reporting behavior, not the exact orchestration code shape.
- Exact schema for a D-02 failure entry in the aggregated report (e.g.
  `{"domain": "docker", "error": "...", "status": "failed"}` vs. some
  other shape) — left to the planner, as long as it's visibly distinct
  from a normal empty-findings entry.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec and roadmap
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"`ai-kit-project-rules-all` (new)" — the authoritative aggregation/
  hand-off-preservation description this phase implements
- `.planning/ROADMAP.md` §"Phase 15: Rules Orchestrator
  (ai-kit-project-rules-all)" — goal, the Phase-14 dependency note (all 6
  checkers must exist), and the 5 fixture-provable success criteria
- `.planning/REQUIREMENTS.md` — `REQ-rules-all` (Traceability table, v1.2
  section)
- `.planning/intel/constraints.md` §"Shared package import convention" and
  §"Cross-skill remediation merging ownership" — the two constraints
  directly motivating D-01 and Success Criterion 5 respectively
- `.planning/PROJECT.md` §"Constraints" — "Confidence labeling" Core Value
  motivating D-02

### Every prior phase's CONTEXT.md (this phase depends on all of them existing)
- `.planning/phases/09-.../09-CONTEXT.md` through
  `.planning/phases/14-.../14-CONTEXT.md` — each names the exact CLI
  contract / `check` output shape the orchestrator must invoke and parse;
  in particular Phase 10/11/14's retrofitted `skills/_shared/` convergence
  decisions (Makefile-parsing, precommit-parsing, per-language tool
  catalog) describe infrastructure the orchestrator itself does NOT need
  to touch directly (it only calls each checker's CLI, never imports
  `skills/_shared/` itself) — but the researcher/planner should still read
  them to understand what each checker's `check` output actually contains

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-
  checker.py` / `cli.py:187-213` — confirmed CLI contract (`main(argv)`
  dispatch, `check`/`remediate`/`cache-update` subcommands, JSON-on-stdout
  for `check`) this phase's subprocess-dispatch logic targets; every other
  checker in the family (9-14) will expose the same shape by the time this
  phase is planned

### Established Patterns
- Standalone entry-script-per-skill pattern (`<skill-dir>/<skill-name>.py`
  wrapping `cli.main`) — already established, this phase's subprocess
  dispatch calls these scripts by path, not by package import

### Integration Points
- This is the only skill in the family that deliberately invokes the
  other 5 (plus the pruned agents checker) as external processes rather
  than importing shared code from `skills/_shared/` — its own dependency
  surface is just "can find and exec 6 other skills' entry scripts,"
  nothing from `skills/_shared/ai_kit_rules_common/` directly

</code_context>

<specifics>
## Specific Ideas

None beyond the invocation-model and partial-failure decisions above —
the design spec and ROADMAP already fully specify this phase's
aggregation/ordering/hand-off behavior.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 15's scope.

### Reviewed Todos (not folded)
None — `cross_reference_todos` found the same 3 historical todos
(`resolves_phase: 6/7/8`) already confirmed not live candidates during
Phases 9-14's discussions.

</deferred>

---

*Phase: 15-Rules Orchestrator (ai-kit-project-rules-all)*
*Context gathered: 2026-09-13*
