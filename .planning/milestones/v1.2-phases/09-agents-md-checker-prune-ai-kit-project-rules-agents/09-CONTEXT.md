# Phase 9: AGENTS.md Checker Prune (ai-kit-project-rules-agents) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Prune `ai-kit-agents-md-rules-checker` down to AGENTS.md/CLAUDE.md-prose
scope only, renaming it to `ai-kit-project-rules-agents`. All Makefile/
`.pre-commit-config.yaml`-specific logic (the `makefile_checker.py` module,
the Makefile-tooling `stack_cache.py`/`stack_detect.py`, the `cache-path`/
`cache-update` subcommands, and the Makefile-`ALL_TOOLING_KEYS`-specific
`_validate_tooling_payload`) is removed from this skill's source tree so
Phase 10 (`ai-kit-project-rules-makefile`) has exactly one, unambiguous
owner for those checks. The existing `/agent-md-refactor` hand-off for
AGENTS.md content is unchanged. No new checks are added in this phase —
it is a subtraction/rename, not new capability.

</domain>

<decisions>
## Implementation Decisions

### Rename scope
- **D-01:** The rename is a FULL rename, not directory-only: the skill
  directory (`skills/ai-kit-agents-md-rules-checker/` →
  `skills/ai-kit-project-rules-agents/`), the inner Python package
  (`ai_kit_agents_md_rules_checker/` → `ai_kit_project_rules_agents/`),
  and the test file (`tests/test_ai_kit_agents_md_rules_checker.py` →
  `tests/test_ai_kit_project_rules_agents.py`) all move together in the
  same commit. Chosen to avoid a skill named `ai-kit-project-rules-agents`
  internally importing a package still called
  `ai_kit_agents_md_rules_checker`, which would be inconsistent with every
  other skill in this milestone's `ai-kit-project-rules-*` family.
  — **Reversibility:** reversible — a further rename later is a normal
  `git mv` + import-path edit, not a migration.
- **D-02:** Every repo-tree reference to the old name found by scouting
  (`Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, `README.md`,
  plus the skill's own internal files) must be updated in the same commit
  as the rename — not left as a follow-up. See Code Context below for the
  full list found.

### Stale-bytecode cleanup (explicit plan step)
- **D-03:** The plan must include an explicit task step that deletes any
  `__pycache__`/`.pyc` left behind at the OLD skill path
  (`skills/ai-kit-agents-md-rules-checker/`) after the `git mv`-based
  rename — not left implicit. This exact gap (a rename commit leaving
  orphaned bytecode-cache directories at the old, now-untracked path) was
  found and manually cleaned up THREE separate times earlier this session
  (`ai-kit-gsd-config`, the pre-rename `ai-kit-agents-md-checker` dir, and
  the `review-spec` family) — writing the cleanup into the plan itself as
  a real step prevents a fourth recurrence, rather than relying on
  `.gitignore` alone (which hides the clutter from `git status` but does
  not remove it from disk).

### Makefile-tooling validator ownership
- **D-04:** `_validate_tooling_payload` (the `ALL_TOOLING_KEYS`-membership/
  non-empty-string/`(source: ...)`-provenance validator, deliberately left
  in this skill's own `cli.py` per the shared-package plan's Deviation #1
  rather than moved to `skills/_shared/`) moves to
  `ai-kit-project-rules-makefile`'s new source tree AS PART OF Phase 9's
  own prune commit — it is not left behind for Phase 10 to recreate from
  scratch. Rationale: it is Makefile-tooling-specific code in the same
  category as `makefile_checker.py`/`stack_cache.py`, which Phase 9 is
  already dropping; moving it now keeps the prune atomic (no dead
  validator left in the pruned skill once `check` no longer returns a
  `"makefile"` key) and satisfies ROADMAP Success Criterion 2's "removed
  from the skill's source tree" literally. Phase 10's own plan picks up
  this already-moved file rather than re-deriving the validator against
  the design spec's cache-payload contract from nothing.
  — **Reversibility:** reversible — the moved file is plain code sitting
  in a not-yet-wired skill directory until Phase 10 wires it up; moving it
  again costs nothing structural.

### Claude's Discretion
- Exact destination path/filename for the moved `_validate_tooling_payload`
  inside the not-yet-created `ai-kit-project-rules-makefile` tree (D-04) is
  left to the Phase 9 planner/implementer — Phase 10's own planning pass
  will wire it into that skill's `cli.py` when that skill is built; Phase 9
  only needs to land the file somewhere sane under that future skill's
  directory (create the directory if needed) without wiring it into a
  `SKILL.md` or `cli.py` that doesn't exist yet.
- Exact shape of the bytecode-cleanup step (D-03) — a plan `Step` with a
  plain `rm -rf` of the old path's `__pycache__`, run immediately after the
  `git mv` step — is left to the planner; no specific script or tooling is
  mandated.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec and roadmap
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"`ai-kit-project-rules-agents` (pruned)" — the authoritative Keeps/Drops
  list, `check` output shape (`{"workflow": [...]}` only), and `SKILL.md`
  scope-line requirement this phase implements
- `.planning/ROADMAP.md` §"Phase 9: AGENTS.md Checker Prune
  (ai-kit-project-rules-agents)" — goal, dependency note (must complete
  before Phase 10 is planned), and the 5 success criteria, including the
  skill-judge regression-baseline criterion
- `.planning/REQUIREMENTS.md` — `REQ-rules-agents-prune` (Traceability
  table, v1.2 section)
- `docs/superpowers/plans/2026-09-12-ai-kit-rules-shared-package.md` §"Self
  Review Notes" Deviation #1 — the exact prior reasoning for why
  `_validate_tooling_payload` was left in this skill's `cli.py` instead of
  moving to `skills/_shared/`; Phase 9's D-04 supersedes the "deferred to a
  named follow-up plan" part of that deviation by naming Phase 9 itself as
  that follow-up's first half (the move), with Phase 10 doing the second
  half (the wiring)

### skill-judge regression baseline — correction
- `.planning/phases/06-agents-md-rules-checker-skill/06-03-SUMMARY.md` /
  `.planning/STATE.md` Accumulated Context, Phase 6 entry — records the
  ACTUAL last-known skill-judge score as **104/120**, zero Critical Issues,
  after Phase 6 Plan 03's fix round. ROADMAP.md Phase 9 Success Criterion 5
  states the pre-prune baseline as "98/120" — that is the SPEC's own cited
  pre-fix score (see the design spec's "Context and motivation" section,
  which separately cites an estimated ~109/120 post-fix figure). Treat
  **104/120 as the real, verified pre-prune baseline** for the "no
  regression" check — the researcher/planner should re-run `/skill-judge`
  fresh against the current (pre-prune) `SKILL.md` to confirm this number
  rather than trusting either cited figure blindly, per the project's own
  stale-knowledge-verification rule.

### Skills this phase's rename/prune must keep working
- `~/.claude/skills/agent-md-refactor/SKILL.md` — the unchanged hand-off
  target; Step A/B/C of this skill's wrap mechanism must still invoke it
  exactly as today after the rename
- `~/.claude/skills/skill-judge/` — the review gate this phase's pruned
  `SKILL.md` must pass (Success Criterion 5)
- `skills/_shared/ai_kit_rules_common/` (already merged via the shared-
  package plan above) — `rule_checker.py` must import the shared
  classification engine from here rather than a local copy (ROADMAP
  Success Criterion 2)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skills/_shared/ai_kit_rules_common/classification.py` — the shared
  classification engine (`evaluate_condition`, `_classify_flat`,
  `_classify_plain_groups`, `_classify_tool_scoped_groups`) this skill's
  `rule_checker.py` must switch to importing, already extracted and
  working (Phase: prior `ai-kit-rules-shared-package` plan, merged to
  `main`)

### Established Patterns
- Current skill source tree (`skills/ai-kit-agents-md-rules-checker/
  ai_kit_agents_md_rules_checker/`): `cli.py`, `__init__.py`,
  `makefile_checker.py` (drop), `remediation.py` (keep — but now generic
  per-skill via `skills/_shared/`'s version; confirm which one this skill
  should import post-prune), `rule_checker.py` (keep, re-wire import),
  `rules.py` (keep, all 17 rules), `stack_cache.py`/`stack_detect.py`
  (drop — Makefile-tooling-specific versions; the shared, generic version
  already lives at `skills/_shared/ai_kit_rules_common/stack_cache.py`),
  `tool_presence.py` (keep or switch to the shared version — confirm
  during planning which copy is the Makefile-specific one vs. reusable)
- Full grep of every repo-tree file still referencing the old name
  (`ai-kit-agents-md-rules-checker` / `ai_kit_agents_md_rules_checker`),
  for the rename commit's scope (D-02): `Makefile`, `pyproject.toml`,
  `.pre-commit-config.yaml`, `README.md` (skill registration table row),
  `tmp/agents-md-rules-research-python.json` (scratch — confirm still
  needed before touching), `skills/_shared/ai_kit_rules_common/
  classification.py` (a reference/docstring, not an import — confirm),
  and all files under the skill's own directory plus its test file.
  Planning-artifact files under `.planning/phases/06-*/` and
  `.planning/intel/` are historical record — do NOT rename/edit those.
- README.md's current row (line 39) reads: `Checks an AGENTS.md/CLAUDE.md
  file and its Makefile/.pre-commit-config.yaml target shape against
  ai-kit's own 17-rule house ruleset...` — this description itself must
  be rewritten to drop the Makefile/pre-commit clause once the skill no
  longer checks those.

### Integration Points
- This skill's own `check` CLI command currently returns a dict keyed by
  at least `"workflow"` and `"makefile"`; after this phase it must return
  `{"workflow": [...]}` only (ROADMAP Success Criterion 1) — any caller
  (orchestrator-to-be in Phase 15, or ad hoc invocations) that currently
  reads a `"makefile"` key from this skill's output will need to stop
  doing so, though no such caller exists yet in this milestone.

</code_context>

<specifics>
## Specific Ideas

- The user's concern driving D-03 (explicit bytecode-cleanup step) came
  directly from this session's own experience: three separate pre-rename
  leftover directories (`ai-kit-gsd-config`, the old
  `ai-kit-agents-md-checker`, and the `review-spec` family) were found and
  manually `rm -rf`'d earlier today, all caused by the same root pattern —
  a `git mv` rename not clearing bytecode cache at the old path. The user
  wants this written into the plan itself this time, not caught after the
  fact again.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 9's prune/rename scope. The 3
pending todos that keyword-matched this phase during `cross_reference_todos`
(`2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md`,
the curated-gsd-config todo, and the status-line-quota todo) are not new
matches — all three already carry `resolves_phase: 6/7/8` respectively from
the prior v1.1 milestone, and Phases 6-8 are already complete. None were
folded; none need re-review.

### Reviewed Todos (not folded)
None — see above; the 3 keyword matches are already-resolved historical
todos from a different milestone, not live candidates for this phase.

</deferred>

---

*Phase: 9-AGENTS.md Checker Prune (ai-kit-project-rules-agents)*
*Context gathered: 2026-09-13*
