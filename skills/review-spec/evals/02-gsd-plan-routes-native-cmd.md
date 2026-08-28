# Eval 02 — GSD plan routes to native slash command

## Scenario

User invokes `review-spec` on a GSD plan document that has issues.

## Prompt

```
/review-spec .planning/phases/02-auth/PLAN.md
```

## Expected behavior

1. Orchestrator confirms file exists on disk (Step 0).
2. Resolves codebase root via `git -C <doc-dir> rev-parse --show-toplevel` (Step 0.1).
3. Detects framework as `gsd` from `.planning/` path prefix and project markers.
4. Resolves GSD profile from SEEDS_DIR (absolute). ARCHETYPE = `plan`.
5. Runs Step 0.7 — resolves `TOOLS_PY`/`CHECKLIST_SKILL_MD`, `RUN_TMP_DIR`, and `REVIEWER_LIST` (1 entry unless `review-spec.toml` configures cross-AI `double` mode; in this eval's default no-config state, `REVIEWER_LIST` is the single-entry `NO_CONFIG_FALLBACK`).
6. Dispatches reviewer subagent; reviewer returns `Issues Found`; report written to `$RUN_TMP_DIR/iter<N>-<key>.md`, read as `EFFECTIVE_REPORT_PATH` by Step 2 (Step 1.5 runs every iteration to bind that name; its merge call itself is skipped here since `REVIEWER_LIST` has only 1 entry).
7. Orchestrator checks GSD profile's `revise_protocol.routes` for archetype `plan` → finds `slash_command` → attempts to invoke `/gsd-plan-phase {phase_id} --reviews` with findings.
8. If slash-command tool unavailable: surfaces pre-filled command + report path to user (Step 3b surface fallback). Does NOT edit files directly.
9. If command succeeds: dispatches `gsd-plan-checker` as validate step (3c), then re-reviews.

## Pass criteria

- Fix NOT routed to `review-spec-fixer` (generic fixer)
- Orchestrator does NOT edit `.planning/phases/02-auth/PLAN.md` itself
- On slash-command unavailability: surface message contains the exact command and report temp path
- ARCHETYPE = `plan`, framework = `gsd`
- Reviewer prompt contains only the file path, not document content
