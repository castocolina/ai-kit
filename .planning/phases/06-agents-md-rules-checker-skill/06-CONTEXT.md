# Phase 6: AGENTS.md Rules Checker Skill - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A new skill that wraps `/agent-md-refactor`: it checks any AGENTS.md/CLAUDE.md-style
agent-instruction file against ai-kit's accumulated 17-rule house ruleset (Makefile
target shape + workflow rules), flags individual gaps, and drives remediation by
feeding missing/near-miss rules into `/agent-md-refactor` so that skill does the
actual placement. Scaffolded via `/superpowers:writing-skills`, reviewed via
`/skill-judge`, named via `/naming-analyzer`.

</domain>

<decisions>
## Implementation Decisions

### Wrap mechanism
- **D-01:** The checker does not run as a separate "report gaps" pass alongside
  `/agent-md-refactor`. It maintains the house ruleset and, for each missing rule,
  feeds it as input to `/agent-md-refactor` (programmatic invoke, not just
  documentation of a two-step workflow), which performs the actual insertion —
  respecting its own progressive-disclosure file structure/format, paraphrasing
  each rule concisely rather than pasting verbatim, as long as the rule's intent
  survives. — **Reversibility:** costly — changing this later means re-plumbing
  how the checker and agent-md-refactor hand off to each other, not a local tweak.
- **D-02:** Rules are inserted most-critical-first, using the criticality tiers
  from D-06 (Ruleset scope) to order insertion.
- **D-03:** When a rule is already present but phrased differently from ai-kit's
  canonical wording, the checker does NOT force a rewrite to canonical phrasing.
  It recommends/warns when the existing prose isn't close enough to the rule's
  intent, and otherwise treats it as satisfied. Start lenient, iterate the
  closeness heuristic later ("we can experiment with any first approach and
  improve later").
- **D-04:** Stack-specific tooling recommendations (formatting, security-leak
  detection, code-smell/duplicate/dead-code, full test pyramid, cheapest/
  fail-fastest ordering for `validate`, pre-commit vs. pre-push split) are NOT
  hardcoded to the todo's example languages (go/python/node/java) alone. Before
  recommending tooling for a detected stack, the skill checks a cached
  per-stack research reference; if missing or stale, it dispatches a research
  subagent first (per rule 14/15's verify-before-trusting-memory, spike-before-plan
  spirit) and caches the findings (e.g. under a stack-refs reference file) for
  reuse on future invocations against that stack. — **Reversibility:** costly —
  switching away from the cache-with-staleness-check model later means
  redesigning how/when research is triggered and how cache freshness is judged.

### Report format
- **D-05:** Findings are presented inline in the conversation only — never
  written to a persisted report file in the target repo. Git is already the
  history of AGENTS.md edits; a separate report file documenting "why this file
  was edited" is exactly the kind of file the user does not want. (Extends/
  clarifies rule 10: ephemeral documentation, if any throwaway doc is ever
  needed during this work, explicitly belongs under `./tmp/docs`, not scattered
  elsewhere or treated as a project artifact.)

### Ruleset scope
- **D-06:** The 17-rule house ruleset is hardcoded into the skill (it is
  explicitly ai-kit's own accumulated ruleset, not a general rules-engine for
  other projects), but organized as structured data (id, text, criticality
  tier, applicability condition) rather than freeform prose, so it stays
  programmatically inspectable without being a reusable external product.
- **D-07:** Each rule entry carries an explicit applicability `condition`
  field — `always` for universal rules (e.g. English-only, commit hygiene,
  no-absolute-paths) vs. `tool-presence: <tool>` for rules already scoped to
  optional tooling (rtk, modern CLI tools, CodeGraph, graphify). The checker
  skips or reframes a rule whose condition isn't met for the target
  project/environment rather than flagging it as a generic gap. This mirrors
  Phase 3's Tool-Substitution Awareness Hook pattern (live tool-presence
  verification), which the checker should reuse rather than reinvent.

### Enforcement mode
- **D-08:** The checker auto-applies clearly-missing rules (feeds them to
  `/agent-md-refactor` for insertion without a confirmation gate). It only
  stops to confirm with the user on near-miss/ambiguous wording cases (D-03).
  This is a deliberate departure from PROJECT.md's "every config write is
  atomic and explicitly confirmed" Core Value line — that line is scoped to
  runtime CLI config files (opencode.jsonc, Codex TOML, Claude JSON), a
  different artifact class from an agent-instruction doc like AGENTS.md.
  — **Reversibility:** reversible — AGENTS.md edits are plain git-tracked file
  changes; switching to always-confirm later is a small flow change, not a
  migration.

### Claude's Discretion
- Exact schema/shape of the per-rule data structure (D-06) and the stack-refs
  cache file format/location (D-04) are left to the planner/implementer, as
  long as they satisfy the conditions above (structured, not prose; cached
  with staleness re-check).
- Exact closeness heuristic for D-03's "not close enough" warning is
  explicitly meant to be a first-pass approximation, improved iteratively —
  not something to over-engineer in the first plan.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source todo and requirements
- `.planning/todos/pending/2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md` — full 17-rule house ruleset text this phase must enforce (note: rule 2's cited reference path `../gitig/.pre-commit-config.yaml` does not resolve from this repo root — treat it as stale/from a different machine, not a real path to follow; use this repo's own `Makefile`/`.pre-commit-config.yaml` as the live reference pattern instead, see Code Context below)
- `.planning/REQUIREMENTS.md` §"v1.1 Requirements" — REQ-agtmd-wrapper, REQ-agtmd-makefile-rules, REQ-agtmd-workflow-rules, REQ-agtmd-skill-pipeline
- `.planning/ROADMAP.md` §"Phase 6: AGENTS.md Rules Checker Skill" — goal and 4 success criteria

### Skills this phase wraps/uses
- `~/.claude/skills/agent-md-refactor/SKILL.md` — the existing progressive-disclosure refactor skill this new skill wraps; confirmed it has no rule-checking logic of its own today (Phase 1: contradiction-finder, Phase 2-5: extract/categorize/structure/prune) — purely structural, no house-rule awareness
- `~/.claude/skills/skill-judge/` — review gate this phase's new skill must pass
- `~/.claude/skills/naming-analyzer/` — picks the final skill name (do not assume a name upfront)
- Pipeline entry point: `/superpowers:writing-skills` (superpowers plugin) — scaffolds the new skill

### Related prior-phase mechanism (pattern to reuse, not re-invoke)
- Phase 3 (Tool-Substitution Awareness Hook, completed 2026-09-09/10) — live
  tool-presence verification pattern for `rtk`; D-07's `tool-presence` condition
  should follow the same verify-live-don't-assume approach rather than a new
  detection mechanism.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `~/.claude/skills/agent-md-refactor/SKILL.md` — the 5-phase refactor process
  (Find Contradictions → Identify Essentials → Categorize → Structure → Prune)
  this new skill calls into for actual file edits.

### Established Patterns
- This repo's own `Makefile` (targets: `install`, `dev`, `reconfigure`,
  `uninstall`, `doctor`, `check`, `test`, `lint`, `validate`) and
  `.pre-commit-config.yaml` (hooks: `ruff`, `pylint`, `pyright`, `vulture`,
  `shellcheck`, `py-compile`, `unittest`, `unittest-wizard`) do NOT themselves
  follow the target shape rule 2 mandates (no `setup-env`, no 1:1 per-hook
  targets, no `test-unit`/`test-integration`/`e2e-test`/`arch-test` split).
  This is explicitly out of scope for this phase (making ai-kit's own Makefile
  compliant is not a Phase 6 deliverable) but it IS a useful concrete example
  of "a real Makefile the checker would currently flag" for test fixtures.
- Phase 3's Tool-Substitution Awareness Hook (SessionStart hook, live rtk
  verification) is the established pattern for D-07's tool-presence condition
  checks.

### Integration Points
- New skill invokes `/agent-md-refactor` programmatically (D-01) rather than
  just documenting it as a prerequisite step.

</code_context>

<specifics>
## Specific Ideas

- The stack-aware tooling research (D-04) was explicitly inspired by the
  project's own theory→hypothesis→spike methodology (rule 15) and stale-
  knowledge-verification rule (rule 14) — the user drew the parallel
  themselves: recommending tooling for an unresearched stack from training
  data alone repeats the same mistake those rules exist to prevent.
- User's own example of the kind of per-stack research needed: for a given
  stack (e.g. Rust), determine formatting tool, security-leak scanner,
  code-smell detector, the full rule set + verifying tool for each, unit/e2e/
  integration/arch test tooling, duplicate/dead-code detection, which checks
  are most important and fail fastest, and the pre-commit vs. pre-push split.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 6 scope. (Phase 7 and Phase 8 already
exist as separate roadmap phases for the other two pending todos; no new
scope surfaced during this discussion that isn't already covered by Phase 6's
success criteria.)

</deferred>

---

*Phase: 6-AGENTS.md Rules Checker Skill*
*Context gathered: 2026-09-10*
