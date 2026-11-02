---
phase: quick-261024-ryk
plan: 01
subsystem: curated-config, spec-discuss
tags: [agent-skills, trusted-global-roots, gsd-core]
status: complete
requirements: [SKL-03, SKL-04]
commits: 3
plan_head_before: 5b4ec21
plan_head_after: ce6984e7c4c95df4507b10b434a0ef2031dc8232
actuals:
  tasks: 3
  commits: 3
---

# Quick 261024-ryk: agent skills only through references gsd-core resolves

Agents no longer run silently without their skills: this repo loads jev by project path, curated-config wires only references gsd-core resolves, and spec-discuss reports skipped entries at setup.

## Commits
- d587b1f: `.planning/config.json` now lists `skills/jev-fast-decision` for both agents (gsd-tools `config-set`, diff `2 2`). `query agent-skills` prints no WARNING for either agent.
- 23441b1: curated-config feature (scan, skills, plan_io, plan_edit, apply, golden, tests, SKILL.md, SKL-03 and D-34 amendments).
- ce6984e: spec-discuss setup check, analyzer rule, doc-pin tests.

## What changed
- `skill_scan`: escaping global rows carry `ai_kit_skills_dir` (two marker skills in the parent dir).
- `skills`: `skip_reason`, `needed_root`, `global_ref_skip_reason`; `unwired_reason` and `trusted_roots` only consider resolvable references. One machine-specific `needs_choice` root per ai-kit install; other escaping skills get a cause-and-fix `skill_unwired` note.
- `plan_io.skipped_skill_problem` is called by `plan-set`/`plan-unset` (post-edit) and `apply.prepare`; force-immune. Declining the root is refused while agents hold dependent skills, and the refusal prints runnable `plan-set` commands.

## Decisions
- The ai-kit install root stays a `needs_choice` approval unless a configured root already covers it.
- "Not installed" names are left to apply's existing refusal, not the new check.

## Deviations from Plan
- [Rule 3 - Blocking] `tests/test_curated_config_apply_e2e.py` (not in the plan's file list) seeds a home whose claude link now must point into an ai-kit tree, otherwise the real gsd-core golden apply no longer wires react-dev. Updated `_seed_home`; the real-node e2e passes.
- [Rule 3] SKILL.md avoids the phrase "on this machine" (pinned by `test_no_machine_specific_claims`) and keeps the word "declined" (pinned by `test_required_statements`).
- Golden drift was limited to the three `claude-*-adaptive` trusted-roots entries; no `inventory_digest` change.

## Skill docs for the orchestrator's skill-judge loop
- `skills/ai-kit-gsd-curated-config/SKILL.md`
- `skills/ai-kit-gsd-spec-discuss/SKILL.md`
- `skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md`

## Verification
Targeted modules (skills, plan_edit, golden, recommend, apply, inventory, followups, eval, e2e, apply_e2e, curated_config, spec_discuss), `ruff`, `pyright` and `pylint` pass. `make validate` and `make test` were not run (orchestrator).

## Known Stubs
None.

## Self-Check: PASSED
Commits d587b1f, 23441b1, ce6984e exist on the branch; the working tree has only the untracked `.planning/quick/` directory.
