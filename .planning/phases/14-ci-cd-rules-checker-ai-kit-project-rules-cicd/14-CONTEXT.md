# Phase 14: CI/CD Rules Checker (ai-kit-project-rules-cicd) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning — BLOCKED on Phases 9-13 landing first (see Phase Boundary)

<domain>
## Phase Boundary

New skill `ai-kit-project-rules-cicd` checks that a target repo's CI config
(`.github/workflows/*.yml`, `.gitlab-ci.yml`, or equivalent) reuses commands
already defined in Makefile targets, pre-commit hooks, `package.json`
scripts, or Gradle tasks, rather than duplicating tool invocations inline
in CI YAML. A CI step running `ruff check .` directly when `make ruff`
already does the same thing is a finding naming both the duplicate and the
target it should call instead.

ai-kit's own `.gitlab-ci.yml` was scouted: it only includes GitLab's
Security/Secret-Detection template and declares a `test` stage with no
job under it — it contains zero direct tool invocations, so it is neither
a flag-worthy violation nor a fully-compliant positive example for this
skill's checks. Unlike Phase 12's `arch-test` self-example, this skill's
behavior is proven entirely by synthetic fixtures (already the ROADMAP's
own framing for all 4 success criteria).

**Hard prerequisite — this phase cannot be planned or executed before
Phases 9-13 actually land.** `.planning/ROADMAP.md`'s "Depends on" line
for Phase 14 names Phase 13 directly; the full chain back to Phase 9 is
unbroken. As of this discussion, NONE of Phases 9-13 have a plan or
execution yet (each has only a CONTEXT.md).

</domain>

<decisions>
## Implementation Decisions

### Makefile-parsing convergence (the one real gray area this phase surfaced — retroactively corrects Phases 10 and 11 too)
- **D-01:** `parse_makefile_targets`/`parse_makefile_recipe`/
  `parse_makefile_prerequisites` move to `skills/_shared/
  ai_kit_rules_common/` — NOT left in `ai-kit-project-rules-makefile`'s
  own tree as Phase 10's original CONTEXT assumed. Discovered while
  discussing this phase: Success Criterion 4 requires this skill to
  "reuse the shared classification/cache package rather than
  re-implementing its own parsing primitives," but Makefile-target
  parsing wasn't actually in `skills/_shared/` yet — only the precommit-
  parsing helpers and `detect_stacks()` were (Phase 10's D-01/D-02).
  Tracing further, Phase 11's own parity check independently needs
  Makefile-target parsing too (to match targets against pre-commit hook
  ids). That makes 3 skills (10, 11, 14) needing the same primitives —
  the exact split-ownership pattern already caught and fixed twice this
  session. **This decision has been retrofitted into Phase 10 CONTEXT.md
  (new D-05) and Phase 11 CONTEXT.md (new D-05)** — both were amended and
  committed (`568b4ce`) alongside this phase's own discussion, since the
  correction changes what those two already-discussed phases must
  actually build, not just this one.
  — **Reversibility:** costly — same reasoning as the prior convergence
  decisions (Phase 10 D-01, Phase 11 D-01): undoing this after Phase 11
  is built means re-plumbing multiple skills' imports.

### Everything else — already locked by ROADMAP + design spec
- **D-02:** The 4-surface reuse check (Makefile targets, pre-commit hooks,
  `package.json` scripts, Gradle tasks) and the exact fixture-provable
  behavior in ROADMAP Success Criteria 1-3 are accepted as written. CI
  platform parsing (GitHub Actions `jobs→steps→run:` shape vs. GitLab CI
  `jobs→script:` shape) follows the same stdlib-only regex/indentation-
  aware parsing approach Phase 13's D-01 already established for this
  skill family — not re-litigated here, just inherited.
- **D-03:** Command-equivalence matching (deciding that a CI `run:` line
  "duplicates" a given Makefile target/hook/script/task) follows the same
  exact-vs-fuzzy-matching discretion precedent already set in Phase 11's
  CONTEXT (bidirectional parity-check matching) — left to the planner, not
  a new vision-level decision.

### Claude's Discretion
- Exact matching strictness for D-03 (exact recipe-body string match vs.
  tool-name-only fuzzy match ignoring flags).
- Whether `package.json`-script parsing and Gradle-task parsing reuse a
  shared generic "reuse-source" abstraction in `skills/_shared/` or stay
  Phase-14-local data structures — no other skill in this family needs
  `package.json`/Gradle parsing, so unlike D-01 there's no cross-skill
  convergence pressure; left to the planner's judgment on code cleanliness
  alone.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec and roadmap
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"`ai-kit-project-rules-cicd` (new)" — the authoritative reuse-check
  description this phase implements
- `.planning/ROADMAP.md` §"Phase 14: CI/CD Rules Checker
  (ai-kit-project-rules-cicd)" — goal, the Phase-13 dependency note, and
  the 4 fixture-provable success criteria
- `.planning/REQUIREMENTS.md` — `REQ-rules-cicd` (Traceability table,
  v1.2 section)
- `.planning/phases/10-makefile-rules-checker-ai-kit-project-rules-
  makefile/10-CONTEXT.md` §D-05 (retrofit) and `.planning/phases/
  11-pre-commit-rules-checker-ai-kit-project-rules-precommit/
  11-CONTEXT.md` §D-05 (retrofit) — the two amended decisions this
  phase's D-01 depends on; read these BEFORE assuming Phase 10's original
  (pre-retrofit) scope

### Existing parsing precedent
- `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
  makefile_checker.py` — `parse_makefile_targets`/`parse_makefile_recipe`/
  `parse_makefile_prerequisites`, the functions D-01 relocates
- `.gitlab-ci.yml` (ai-kit's own, repo root) — scouted; confirmed to
  contain zero direct tool invocations (just an included security-scan
  template and an empty `test` stage), so it is not usable as either a
  triggering or non-triggering fixture for this skill's own checks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None directly in ai-kit's own CI config (see domain note above) —
  every fixture for this phase is synthetic
- `skills/_shared/ai_kit_rules_common/`, once D-01's Makefile-parsing
  primitives land there (as part of Phase 10's own retrofitted work) —
  this phase imports directly, never re-implements

### Established Patterns
- Phase 13's D-01 (stdlib-only, indentation-aware regex/text YAML
  parsing, no library dependency) is the precedent this phase follows for
  parsing both GitHub Actions and GitLab CI YAML — not re-decided here
- Phase 11's exact-vs-fuzzy-matching discretion precedent (bidirectional
  parity check) — reused for D-03's command-equivalence matching

### Integration Points
- This phase is the first to need Makefile-parsing primitives from
  `skills/_shared/` that weren't already confirmed-shared before this
  discussion — D-01's retrofit closes that gap for Phase 10/11 as well as
  this phase

</code_context>

<specifics>
## Specific Ideas

None beyond the Makefile-parsing-convergence discovery above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 14's scope (D-01 is a retrofit
correction to already-discussed phases, not new scope for THIS phase
beyond what the design spec already describes).

### Reviewed Todos (not folded)
None — `cross_reference_todos` found the same 3 historical todos
(`resolves_phase: 6/7/8`) already confirmed not live candidates during
Phases 9-13's discussions.

</deferred>

---

*Phase: 14-CI/CD Rules Checker (ai-kit-project-rules-cicd)*
*Context gathered: 2026-09-13*
