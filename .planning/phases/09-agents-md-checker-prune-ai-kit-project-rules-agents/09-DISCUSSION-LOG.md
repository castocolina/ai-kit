# Phase 9: AGENTS.md Checker Prune (ai-kit-project-rules-agents) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-13
**Phase:** 9-AGENTS.md Checker Prune (ai-kit-project-rules-agents)
**Areas discussed:** Rename scope, Stale bytecode cleanup, _validate_tooling_payload ownership

---

## Rename scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full rename (dir + package + test file) | skills/ai-kit-agents-md-rules-checker/ → skills/ai-kit-project-rules-agents/, inner package ai_kit_agents_md_rules_checker/ → ai_kit_project_rules_agents/, and tests/test_ai_kit_agents_md_rules_checker.py → tests/test_ai_kit_project_rules_agents.py, all in one commit. | ✓ |
| Directory-only rename | Only the skill directory changes; inner package and test file keep their current names. | |

**User's choice:** Full rename (dir + package + test file)
**Notes:** Matches the pattern used for the prior `ai-kit-gsd-curated-config` rename; avoids a renamed skill internally importing a package still named after the old skill.

---

## Stale bytecode cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit cleanup step in the plan | A written task step deletes `__pycache__`/`.pyc` at the old path after the `git mv` rename. | ✓ |
| Leave implicit, rely on gitignore | No dedicated step; assume existing .pyc/.gitignore handling is sufficient. | |

**User's choice:** Explicit cleanup step in the plan
**Notes:** Same root-cause pattern (git mv leaves orphaned bytecode cache at the old, now-untracked path) was found and manually fixed three separate times earlier this session (`ai-kit-gsd-config`, the pre-rename `ai-kit-agents-md-checker` dir, `review-spec`). The user wants it caught by the plan itself this time.

---

## _validate_tooling_payload ownership

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 9 moves it now | The Makefile-`ALL_TOOLING_KEYS`-specific validator moves to the (not-yet-built) `ai-kit-project-rules-makefile` tree as part of Phase 9's own prune commit. | ✓ |
| Leave for Phase 10 to recreate | Phase 9 deletes it outright; Phase 10 re-derives it from the SPEC's cache-payload contract when planned. | |

**User's choice:** Phase 9 moves it now
**Notes:** Keeps the prune atomic — no dead validator left behind, satisfies ROADMAP Success Criterion 2's "removed from the skill's source tree" literally. Phase 10 wires the already-moved file in rather than rewriting it from scratch.

---

## Claude's Discretion

- Exact destination path/filename for the moved `_validate_tooling_payload` inside the not-yet-created `ai-kit-project-rules-makefile` tree.
- Exact shape of the bytecode-cleanup plan step (a plain `rm -rf` after the `git mv` step is the expected shape, but left to the planner).

## Deferred Ideas

None. The 3 pending todos that keyword-matched Phase 9 during cross-reference (`todo.match-phase`) were reviewed and not folded — all three already carry `resolves_phase: 6/7/8` from the completed v1.1 milestone and are not live candidates for this phase.
