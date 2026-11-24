# Phase 44: curated-config writes the agreed settings - Context

**Gathered:** 2026-11-23 (interactive, after 44-SPEC.md)
**Status:** Ready for planning (requirement 7 needs the researcher first)

<domain>
## Phase Boundary

On a fixture project, curated-config writes the agreed profile, routing, models, effort, workflow defaults, skill assignments,
graphify flags and lens wiring through the project's `gsd-tools`, removes nothing it did not plan, offers the effort sync for the
checkout and a worktree session's launch directory as one approval-gated follow-up with a stale-agent report, and sets (or
records that GSD already has) the keys that make the plan checker read an amended plan again.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked** (requirement 7 flagged: its meaning waits for the researcher). See `44-SPEC.md` for full
requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `44-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** the writes of the agreed settings, the two-directory effort sync follow-up, the plan-checker keys or
their citation, docs, evals and the judge loop.
**Out of scope (from SPEC.md):** the cascade, the tagged-docs reader and the v1 records (Phase 43); installing or updating GSD,
`gsd update` or user-level writes; changing a custom branch template or turning worktrees off without the owner; the shared jev
client and the runner and lane code.

</spec_lock>

<decisions>
## Implementation Decisions

### Write path and defaults
- **D-01: Every write goes through the project's `gsd-tools config-set` via the existing `GsdTools` wrapper
  (`ai_kit_spec/gsd_tools.py`), with validation first.** Effort and model values are checked against the host's allowed set
  before any call; a rejected value writes nothing for it and names its key. Whether any path writes the file directly today is
  the researcher's open question 2; a direct path found there is converted in the first slice. **Own reasoning** (jev not
  asked): the owner's rule and the SPEC's first prohibition. Ledger.
- **D-02: The defaults are plan entries with a reason and a source label,** produced by one function beside
  `workflow_defaults.py`: the two UI flags (existing `frontend_detect`), `response_language`, `claude_md_path` (existing detector,
  refused when the file is missing), `git.branching_strategy = "phase"` with the template left at GSD's default (a differing custom
  template is reported, never rewritten), and `intel`. **Own reasoning.** Ledger.
- **D-03: `workflow.use_worktrees` gets no write at all** (GSD's default is `true`); its plan entry is a note quoting the two cases
  where GSD itself turns it off, taken from the installed docs (a branch ahead of `origin/HEAD` degrades to sequential, restored by
  `worktree.baseRef:"head"`; a runtime with `dispatch.isolation: none` and an explicit `true` fails closed, warning `W025`). An
  owner-set `false` is kept. **Own reasoning.** Ledger.

### Skills, graphify and lenses
- **D-04: Skill assignment reads the role-keyed table** (`skill-roles.json`) and the host's skills from the inventory, and maps a
  role to a GSD agent through the existing `roles.py`; an unsorted skill goes to the classify offer. **Own reasoning.** Ledger.
- **D-05: The graphify keys use `plan-set` entries written in order (`graphify.enabled`, then `graphify.auto_update`),** only when
  the `graphify` binary is installed (detection reuses the repository's existing tool detection, fixed at plan time); the effect
  text comes from the installed `workflows/settings.md` and `references/planner-graphify-auto-update.md` with their label; an
  owner-set `false` is kept and shown as an owner choice. **Own reasoning.** Ledger.
- **D-06: The lens proposal is one function** over the table's `review_lens` and `ui_lens` roles, the host's skills, the runtime's
  loading ability and `frontend_detect`; it returns the difference to the project's current wiring; on ai-kit itself the
  difference is empty (the fixture is a copy of ai-kit's own wiring). **Own reasoning.** Ledger.

### Effort sync and the plan checker
- **D-07: The effort sync stays an approval-gated follow-up** (owner decision 2026-11-23): `followups.effort_sync_argv` emits one
  entry per directory (the checkout and the worktree launch directory, found by the researcher's open question 3; one entry when
  they are the same), one approval covers the block, and after the sync every agent file's `effort:` frontmatter is re-read and
  compared with the config so a stale file is reported with its path. *(owner decision; the report shape is own reasoning)*
  Ledger.
- **D-08: Requirement 7 waits for research.** The plan's first task records the researcher's answer (does gsd-core 1.22.0 re-run
  the plan checker after `--reviews` amends a plan, and which key controls it) with a file-and-line citation as a dated amendment
  of `44-SPEC.md`; the fixture config then shows keys set, or unchanged with the citation recorded. Never answered by invented
  text.

### Order
- **D-09: Build order is a vertical slice.** (1) the write-path audit and validation; (2) the defaults entries; (3) graphify;
  (4) skills and lenses; (5) the two-directory effort sync and the stale report; (6) the plan-checker keys (after research);
  (7) evals, docs and the skill-judge loop of `ai-kit-gsd-curated-config`.

### Claude's Discretion
Function and module names, the allowed-effort source, the `response_language` literal (from the installed docs), the graphify
detection helper and the report wording.

### Folded Todos
None folded.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/44-curated-config-writes-the-agreed-settings/44-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/ROADMAP.md` §Phase 44 and `.planning/REQUIREMENTS.md` CUR-03, CUR-04, CUR-05, CUR-07, CUR-08, CUR-09, LENS-03

### Earlier decisions
- `.planning/phases/43-curated-config-reads-docs-at-the-installed-tag/43-CONTEXT.md` (cascade, tagged docs, v1 records)
- `.planning/phases/39-lane-capability-blocks-and-lens-skills/39-CONTEXT.md` (the role-keyed table)
- `.planning/phases/39.2-spec-discuss-branch-strategy-for-stacked-units/39.2-SPEC.md` R5 (the branch-name check that the "branch per
  phase" default must keep satisfying)

### Code and docs the phase touches
- `skills/ai-kit-gsd-curated-config/SKILL.md`, `ai_kit_gsd_curated_config/{presets,recommend,roles,critical_agents,
  workflow_defaults,plan_edit,apply,skills,followups,frontend_detect,claude_md_detect}.py`
- `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py` (`GsdTools`), `references/skill-roles.json`
- Installed docs (read only): `.claude/gsd-core/references/planning-config.md`, `model-profiles.md`,
  `planner-graphify-auto-update.md`, `workflows/settings.md`, `workflows/plan-phase.md`

### Tests that pin or must keep passing
- `tests/test_curated_config_*.py`, `tests/test_gsd_curated_eval.py`, `tests/test_ai_kit_gsd_curated_config.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `presets.py` (`dynamic_routing.*`), `recommend.py` (`model_profile_overrides.<host>.<tier>`, jev use), `workflow_defaults.py`,
  `frontend_detect.py`, `claude_md_detect.py`, `followups.effort_sync_argv`, `plan_edit.py` (`plan-set`, `plan-unset`).

### Established Patterns
- Every write is a reviewed plan entry with an effect label and a source label; an unverified effect is flagged.
- A follow-up that changes a checkout is listed and approval-gated; the `--no-focus`, scratch-HOME and no-user-level-write rules.

### Integration Points
- SKILL.md Step 3 (plan review), the follow-up approval step, `apply`, the inventory's `skill_roles`.

</code_context>

<specifics>
## Specific Ideas

The default `git.phase_branch_template` renders the fold flow's unit branch names, which is why "branch per phase" writes only the
strategy and why a custom template is reported, not rewritten (it would trip Phase 39.2's name check).

</specifics>

<deferred>
## Deferred Ideas

- An automatic effort sync under a standing approval (the owner chose approval-gated for now).
- Turning `workflow.use_worktrees` off for a project that always diverges from `origin/HEAD` (an owner choice per project).

### Reviewed Todos (not folded)
- 26 other todos matched by keyword only; none concerns these writes.

</deferred>

---

*Phase: 44-curated-config writes the agreed settings*
*Context gathered: 2026-11-23*
