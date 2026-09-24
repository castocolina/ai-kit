# Phase 10: Makefile Rules Checker (ai-kit-project-rules-makefile) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning — BLOCKED on Phase 9 landing first (see Phase Boundary)

<domain>
## Phase Boundary

New skill `ai-kit-project-rules-makefile` owns every Makefile-specific
check dropped by Phase 9's prune (`REQUIRED_STATIC_TARGETS` shape,
`validate` chain-incomplete, `test`/`test-unit` pairing, the stack-aware
tooling-recommendation research-dispatch), plus 5 new checks the design
spec adds: `validate-<category>` alias family, help/fail reachability,
recipe-line-length cap (3 lines), Docker build-before-up, and a shellcheck-
threshold + advisory ordering heuristic.

**Hard prerequisite — this phase cannot be planned or executed before
Phase 9 actually lands.** `.planning/ROADMAP.md`'s own "Depends on" line
for Phase 10 states this explicitly, and `.planning/STATE.md`'s
Accumulated Context repeats it: "Phase 10 cannot safely claim the dropped
`makefile_checker.py` logic until Phase 9 has actually landed (otherwise
neither skill owns those checks, or both do)." As of this discussion,
Phase 9 has only a CONTEXT.md — no plan has been written or executed yet.
This CONTEXT.md captures vision-level decisions now (so they aren't lost),
but the researcher/planner for Phase 10 MUST verify Phase 9 is actually
merged (the old skill directory renamed/pruned, `makefile_checker.py`
physically absent from `ai-kit-project-rules-agents`) before grounding any
plan against "what currently exists" — the codebase snapshot used during
THIS discussion (2026-09-13) still shows the pre-Phase-9 state
(`skills/ai-kit-agents-md-rules-checker/`, not yet renamed or pruned).

</domain>

<decisions>
## Implementation Decisions

### Shared-package extraction (new, beyond Phase 9's scope)
- **D-01:** `parse_precommit_hooks`, `_iter_precommit_hook_blocks`, and
  `check_precommit_prepush_split` — currently defined inside
  `makefile_checker.py` and load-bearing for today's `check_makefile_shape`
  (it unions `REQUIRED_STATIC_TARGETS` with `hooks.keys()`) — move to
  `skills/_shared/ai_kit_rules_common/` as part of THIS phase's work, not
  left in `ai-kit-project-rules-makefile`'s own tree. Rationale: the design
  spec explicitly names these same functions as Phase 11
  (`ai-kit-project-rules-precommit`)'s inherited functions too (for the
  Makefile↔pre-commit parity check); since "no skill imports another
  skill's package directly" is a hard convention
  (`.planning/intel/constraints.md` §"Shared package import convention"),
  leaving them Phase-10-local would force either a forbidden cross-skill
  import or a near-duplicate reimplementation when Phase 11 is planned.
  — **Reversibility:** costly — undoing this after Phase 11 is built means
  re-plumbing two skills' imports, not a local tweak.
- **D-02:** `stack_detect.py`'s `detect_stacks()` (generic repo-stack
  detection: Python/Node/Go/etc., currently Makefile-checker-local, no
  Makefile-specific logic inside it) ALSO moves to
  `skills/_shared/ai_kit_rules_common/` as part of this phase, alongside
  the already-shared `stack_cache.py` it's paired with. Rationale: stack-
  aware tooling recommendations recur in Phase 11's tooling-taxonomy
  research and Phase 13's (`ai-kit-project-rules-docker`) checks — keeping
  stack detection and the stack-tooling cache together in one shared
  location avoids a second split-ownership gap identical to D-01's.
  — **Reversibility:** reversible — `detect_stacks` has no external
  callers outside this skill family yet, so moving it again later costs
  nothing beyond an import-path edit.
- **D-05 (retrofit, added during Phase 14's discussion, 2026-09-13):**
  `parse_makefile_targets`, `parse_makefile_recipe`, and
  `parse_makefile_prerequisites` ALSO move to
  `skills/_shared/ai_kit_rules_common/` as part of this phase's own work,
  for the same reason as D-01/D-02. Discovered while discussing Phase 14
  (`ai-kit-project-rules-cicd`): that skill needs to parse Makefile targets
  to know what `make <target>` commands already exist (to flag CI steps
  duplicating them), and Phase 11's parity check independently needs the
  same parsing to match Makefile targets against pre-commit hook ids —
  this is now a 3-skill convergence (10, 11, 14), not just the 2-skill
  case D-01/D-02 already covered. Leaving these functions Phase-10-local
  would force Phase 11 and Phase 14 into the same forbidden-cross-skill-
  import-or-reimplement dilemma D-01/D-02 already exist to prevent, and
  directly conflicts with Phase 14's own Success Criterion 4 ("reuses the
  shared classification/cache package rather than re-implementing its own
  parsing primitives").
  — **Reversibility:** costly — same reasoning as D-01.

### Inherited scope (from the design spec, locked — not re-discussed)
- **D-03:** Every check named in the design spec's `ai-kit-project-rules-
  makefile` component section is in scope: `parse_makefile_targets`/
  `parse_makefile_recipe`/`parse_makefile_prerequisites`,
  `REQUIRED_STATIC_TARGETS` shape check, `chain_incomplete` on `validate`,
  `test`/`test-unit` pairing, the tooling-recommendation research-dispatch
  (Step D), and the 5 new checks (`validate-<category>` family, help/fail
  reachability, recipe-line-length cap, Docker build-before-up, shellcheck
  threshold + advisory ordering heuristic) — see ROADMAP Success Criteria
  1-5 for the exact fixture-provable behavior each must satisfy. No scope
  changes surfaced during this discussion.

### Claude's Discretion
- Exact detection heuristic for a "`docker-up`-shaped target" (regex on
  target name vs. a fixed name list) — ROADMAP Success Criterion 5 only
  specifies the observable behavior (flagged when no `docker-build`-shaped
  prerequisite exists), not the matching mechanism.
- Whether the shellcheck-threshold check's CI-config cross-check (full
  confirmation requires `ai-kit-project-rules-cicd`'s output, per the
  design spec) is stubbed/deferred now or left entirely to Phase 15's
  orchestrator to wire — the design spec already states this skill
  "standalone... can only confirm the Makefile+pre-commit halves," so no
  new decision is needed here, just an implementation note.
- Whether to reuse/migrate the current skill's Makefile-checker test
  fixtures (`tests/test_ai_kit_agents_md_rules_checker.py`'s Makefile-
  related test cases) verbatim into the new skill's test file, vs. writing
  fresh fixtures — left to the planner; either satisfies ROADMAP Success
  Criterion 1's "reproduces every check... with the same finding shape."

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec and roadmap
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"`ai-kit-project-rules-makefile` (new)" — the authoritative Inherits/New
  Checks list this phase implements, including the exact category names
  (`security-scanner`, `duplicate-code-detector`, `dead-code-detector`,
  `formatter`, `code-smell-detector`) for the `validate-<category>` family
- `.planning/ROADMAP.md` §"Phase 10: Makefile Rules Checker
  (ai-kit-project-rules-makefile)" — goal, the Phase-9 dependency note, and
  the 5 fixture-provable success criteria
- `.planning/REQUIREMENTS.md` — `REQ-rules-makefile` (Traceability table,
  v1.2 section)
- `.planning/intel/constraints.md` §"Shared package import convention" —
  the "no skill imports another skill's package directly" rule motivating
  D-01/D-02
- `.planning/phases/09-agents-md-checker-prune-ai-kit-project-rules-agents/
  09-CONTEXT.md` — Phase 9's own decisions, in particular D-04
  (`_validate_tooling_payload` moves to this skill's tree as part of
  Phase 9's own commit) and D-03 (explicit stale-`__pycache__` cleanup
  step) — both set precedent this phase's D-01/D-02 follow

### Skills this phase's new checks must compose with
- `~/.claude/skills/skill-judge/` — the review gate this phase's new
  `SKILL.md` must pass (no remaining Critical/Important finding)
- `~/.claude/skills/naming-analyzer/` — confirms (or finalizes) the
  `ai-kit-project-rules-makefile` name — this milestone's names are already
  user-decided (`ai-kit-project-rules-<domain>` scheme), but the pipeline
  step still runs per the project's established skill-authoring convention

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (as of 2026-09-13, pre-Phase-9 snapshot)
- `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
  makefile_checker.py` (418 lines) — `check_makefile_shape` is the
  top-level entry point; confirmed it calls `parse_precommit_hooks` (to
  union `REQUIRED_STATIC_TARGETS | hooks.keys()`) and
  `check_precommit_prepush_split` directly — these are load-bearing for
  Makefile checks today, not incidental, which is why D-01 matters (a
  naive "drop everything precommit-flavored" read of the design spec would
  break Phase 10's own `check_makefile_shape` logic)
- `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
  stack_detect.py` — `detect_stacks()`, imported by `makefile_checker.py`
  alongside the Makefile-tooling-specific `stack_cache.py` (the version
  being dropped, per Phase 9 CONTEXT — not to be confused with the already-
  shared, generic `skills/_shared/ai_kit_rules_common/stack_cache.py`)
- `skills/_shared/ai_kit_rules_common/` (already merged, prior
  `ai-kit-rules-shared-package` plan) — `classification.py`,
  `remediation.py`, `stack_cache.py` (generic), `tool_presence.py` already
  live here; D-01/D-02 extend this same directory with 2 more modules

### Established Patterns
- `tests/test_ai_kit_agents_md_rules_checker.py:152` —
  `test_parse_precommit_hooks_handles_quoted_ids` is the existing test
  coverage for the function D-01 moves; confirms it already has dedicated
  test coverage to carry forward (migrate, not just port the production
  code) when it relocates to `skills/_shared/`
- Research-dispatch / stack-tooling cache pattern (`_resolve_across_stacks`,
  `get_stack_tooling`) in `check_makefile_shape` — already wired to the
  shared `stack_cache.py`'s `get_stack_tooling`; Phase 10 continues calling
  this exact pattern, just from its own skill's `cli.py`

### Integration Points
- Phase 10's `check` command becomes the sole owner of a `"makefile"`-keyed
  finding list — the exact key Phase 9 drops from its own `check` output
  (ROADMAP Phase 9 Success Criterion 1 / Phase 10 Success Criterion 1)
- `skills/_shared/ai_kit_rules_common/` grows to include precommit-parsing
  and stack-detection helpers (D-01/D-02) that Phase 11 will import from,
  not re-derive

</code_context>

<specifics>
## Specific Ideas

None beyond the two shared-package-extraction decisions above — this
discussion stayed focused on cross-phase ownership boundaries rather than
new vision-level behavior, since the design spec already specifies the
new checks' exact fixture-provable behavior in detail.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 10's scope.

### Reviewed Todos (not folded)
None — `cross_reference_todos` was not re-run for this phase; Phase 9's
discussion already confirmed the 3 pending todos (resolves_phase: 6/7/8)
are historical and not live candidates for any Phase 9-15 work.

</deferred>

---

*Phase: 10-Makefile Rules Checker (ai-kit-project-rules-makefile)*
*Context gathered: 2026-09-13*
