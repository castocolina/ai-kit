# Eval 03 — generic / unknown framework routes to direct-edit fixer

## Scenario

User invokes `review-spec` on a doc that doesn't match any seeded framework profile.

## Prompt

```
/review-spec docs/rfcs/0042-rate-limiting.md
```

## Expected behavior

1. Orchestrator confirms file exists on disk (Step 0).
2. Resolves codebase root (Step 0.1).
3. Detects framework: no matching seed profile; FRAMEWORK_PROFILE_PATH = `none`. ARCHETYPE inferred from content shape or defaults to `design`.
4. Runs Step 0.7 — resolves `TOOLS_PY`/`CHECKLIST_SKILL_MD`, `RUN_TMP_DIR`, and `REVIEWER_LIST` (1 entry unless `review-spec.toml` configures cross-AI `double` mode; in this eval's default no-config state, `REVIEWER_LIST` is the single-entry `NO_CONFIG_FALLBACK`).
5. Dispatcher reviewer subagent. Reviewer uses generic archetype checklists (no profile); report written to `$RUN_TMP_DIR/iter<N>-<key>.md`, read as `EFFECTIVE_REPORT_PATH` by Step 2 (Step 1.5 runs every iteration to bind that name; its merge call itself is skipped here since `REVIEWER_LIST` has only 1 entry).
6. If reviewer returns `Issues Found`: no `revise_protocol` → uses generic fixer (`review-spec-fixer`, Step 3a). Dispatches fresh fixer subagent.
7. Fixer edits the file in place and returns `Edits Applied`.
8. Re-reviews. If approved, surfaces approval message.

## Pass criteria

- Framework detection falls back gracefully — no crash, no hang
- FRAMEWORK_PROFILE_PATH = `none` passed to both reviewer and fixer
- Fix routed to `review-spec-fixer` (Step 3a)
- Fixer edits the document directly (no hand-off command surfaced)
- Surface message on approval is concise and includes the file path
