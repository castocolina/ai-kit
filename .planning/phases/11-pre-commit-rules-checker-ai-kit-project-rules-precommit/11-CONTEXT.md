# Phase 11: Pre-commit Rules Checker (ai-kit-project-rules-precommit) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning — BLOCKED on Phases 9 and 10 landing first (see Phase Boundary)

<domain>
## Phase Boundary

New skill `ai-kit-project-rules-precommit` owns the bidirectional Makefile↔
pre-commit **parity** check (every hook id ↔ a matching single-tool
Makefile target, both directions) and classifies every detected tool in a
target repo's `.pre-commit-config.yaml` into the design spec's 6-category
cross-language taxonomy (Formatting, Type-checking, Linting/code-quality,
Security (SAST), Duplicate-code, Dead-code), flagging "enable-everything"
configs, absent Duplicate-code/Dead-code tooling, and the ruff/golangci-
lint-specific anti-patterns the spec names explicitly.

**Hard prerequisite — this phase cannot be planned or executed before
Phases 9 AND 10 actually land.** `.planning/ROADMAP.md`'s "Depends on"
line for Phase 11 names Phase 10 directly ("the parity check needs the
Makefile-target-parsing conventions `ai-kit-project-rules-makefile`
established"), and Phase 10 itself depends on Phase 9. As of this
discussion, NEITHER Phase 9 nor Phase 10 has a plan or execution yet
(each has only a CONTEXT.md). This CONTEXT.md captures vision-level
decisions now so they aren't lost, but the researcher/planner for Phase 11
MUST verify both prior phases are actually merged — in particular that
`skills/_shared/ai_kit_rules_common/` already contains
`parse_precommit_hooks`/`check_precommit_prepush_split`/`detect_stacks`
(Phase 10's D-01/D-02) — before grounding any plan against "what currently
exists." The codebase snapshot used during this discussion (2026-09-13)
still shows the pre-Phase-9 state.

</domain>

<decisions>
## Implementation Decisions

### Shared per-language tool-knowledge convergence (new, beyond Phase 10's scope)
- **D-01:** The "which tool covers which category, per language" knowledge
  — Phase 10's stack-tooling research-dispatch cache (5 Makefile-target
  categories: `formatter`, `security-scanner`, `code-smell-detector`,
  `duplicate-code-detector`, `dead-code-detector`) and Phase 11's own
  6-category taxonomy (Formatting, Type-checking, Linting/code-quality,
  Security, Duplicate-code, Dead-code — design spec's "Baseline stacks by
  language" table) — converges into ONE shared per-language tool catalog
  in `skills/_shared/ai_kit_rules_common/`, rather than staying two
  independently-hardcoded datasets. Rationale: both skills answer
  overlapping questions about the same concrete tools (ruff, mypy, bandit,
  vulture, eslint, etc.); leaving them separate recreates the exact
  split-ownership drift risk already caught and fixed twice in Phase 10's
  own discussion (D-01/D-02 there). A correction or a newly-researched
  stack should benefit both skills at once.
  — **Reversibility:** costly — once Phase 10 is built against its own
  5-category cache and Phase 11 against a converged catalog, un-merging
  them later means re-deriving which facts either skill actually needs.
- **D-02:** The reconciliation needed for D-01 (Phase 10's 5 Makefile-
  target category names vs. Phase 11's 6 taxonomy category names — Type-
  checking has no Makefile-target equivalent today, since there's no
  `REQUIRED_STATIC_TARGETS` entry for it) is this phase's own job to work
  out during planning/implementation — NOT a reason to abandon D-01's
  convergence. The exact mapping (e.g. a category-name alias table, or a
  superset schema Phase 10's cache simply doesn't populate the
  Type-checking slot for) is left to the planner.
- **D-03:** The already-spec'd, already-researched "Confirmed redundant-
  vs-complementary pairs" table and "Fast-vs-slow ordering guidance" are
  NOT re-researched or re-litigated — they are locked, verified-by-prior-
  research content from the design spec, hardcoded verbatim (reusing D-01's
  shared catalog structure where the two overlap, e.g. the baseline-
  stacks-by-language table feeding both the pairs-table lookups and the
  Makefile checker's tooling recommendations).

### Unknown tool-pair default policy (inherited from PROJECT.md Core Value — not re-discussed)
- **D-04:** A tool pair covering the same category that is NOT in the
  design spec's "Confirmed redundant-vs-complementary pairs" table is
  treated as presumed-complementary (not flagged) rather than presumed-
  redundant. This follows directly from `PROJECT.md`'s Core Value
  ("no diagnostic is presented with more certainty than its actual
  sourcing") — flagging an unresearched pair as redundant would claim
  confidence the skill doesn't have. This is not a new decision so much as
  a restated inherited constraint; no alternative was seriously considered.

### Claude's Discretion
- Exact matching algorithm for the bidirectional parity check (ROADMAP
  Success Criterion 1 only specifies the two discriminating fixture
  outcomes — a hook with no matching target, and a target with no matching
  hook — not whether matching is exact-string or normalized/fuzzy).
- Exact shape of the converged per-language tool catalog from D-01 (schema,
  file location within `skills/_shared/ai_kit_rules_common/`, whether it's
  one file or split by concern) — left to the Phase 11 planner/implementer,
  in coordination with whatever shape Phase 10 already committed to its
  own stack-tooling cache.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec and roadmap
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"`ai-kit-project-rules-precommit` (new)" — the authoritative Inherits/
  Ruleset section (enable-everything flag, Duplicate/Dead-code absence
  flags, ruff-specific checks, golangci-lint-specific check)
- Same spec §"Tooling taxonomy (cross-language, generalized)" — the
  6-category table, "Baseline stacks by language" table, "Confirmed
  redundant-vs-complementary pairs" table, and "Fast-vs-slow ordering
  guidance" section — ALL of this content is locked, already-researched
  knowledge this phase hardcodes (per D-01's converged-catalog decision),
  not re-derives
- `.planning/ROADMAP.md` §"Phase 11: Pre-commit Rules Checker
  (ai-kit-project-rules-precommit)" — goal, the Phase-10 dependency note,
  and the 5 fixture-provable success criteria
- `.planning/REQUIREMENTS.md` — `REQ-rules-precommit` (Traceability table,
  v1.2 section)
- `.planning/PROJECT.md` §"Constraints" — "Confidence labeling" Core Value
  line motivating D-04
- `.planning/phases/10-makefile-rules-checker-ai-kit-project-rules-
  makefile/10-CONTEXT.md` — Phase 10's D-01/D-02 (the precedent D-01 here
  follows) and its own blocking-prerequisite note re: Phase 9

### Skills this phase's taxonomy/parity checks must compose with
- `~/.claude/skills/skill-judge/` — the review gate this phase's new
  `SKILL.md` must pass
- `~/.claude/skills/naming-analyzer/` — confirms the `ai-kit-project-rules-
  precommit` name per this milestone's already-decided naming scheme

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (as of 2026-09-13, pre-Phase-9/10 snapshot)
- `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
  makefile_checker.py` — `parse_precommit_hooks`/`_iter_precommit_hook_
  blocks`/`check_precommit_prepush_split` are the functions Phase 10's D-01
  relocates to `skills/_shared/ai_kit_rules_common/`; Phase 11 imports them
  from there once Phase 10 lands, never re-implements them
- `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
  stack_cache.py` (skill-local, Makefile-tooling-specific) — its own
  docstring already states the intended destination is the future
  Makefile-checker skill (Phase 10); its `RESEARCH_CATEGORIES` constant
  (`formatter`, `security-scanner`, `code-smell-detector`,
  `duplicate-code-detector`, `dead-code-detector`) is the concrete 5-
  category schema D-01/D-02's reconciliation must map against the design
  spec's 6-category taxonomy

### Established Patterns
- Phase 6 CONTEXT D-04's cache-with-staleness-check research-dispatch
  model (established for Makefile tooling, carries forward here): for any
  language outside the design spec's 5 already-researched baseline stacks
  (Python/Node-TS/Java/Rust/Go), Phase 11 follows the same
  "check cache → dispatch research if missing/stale → cache the result"
  pattern rather than guessing from training data, consistent with the
  project's stale-knowledge-verification rule

### Integration Points
- `.pre-commit-config.yaml` parsing (`parse_precommit_hooks`) is the same
  parser both this skill AND Phase 10 use — D-01 converges the tool-
  knowledge layer; the parser itself already converges via Phase 10's D-01
  (shared package), so Phase 11 has no separate pre-commit-file-parsing
  work to do, only the parity-comparison and taxonomy-classification logic
  on top of the already-shared parse output

</code_context>

<specifics>
## Specific Ideas

None beyond the tool-knowledge-convergence decision above — the design
spec already specifies this phase's checks in full fixture-provable
detail (enable-everything configs, category-absence flags, the exact
ruff/golangci-lint anti-patterns), leaving little open for vision-level
discussion.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 11's scope.

### Reviewed Todos (not folded)
None — `cross_reference_todos` found the same 3 historical todos
(`resolves_phase: 6/7/8`) already confirmed not live candidates during
Phase 9's and Phase 10's discussions.

</deferred>

---

*Phase: 11-Pre-commit Rules Checker (ai-kit-project-rules-precommit)*
*Context gathered: 2026-09-13*
