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
4. Dispatcher reviewer subagent. Reviewer uses generic archetype checklists (no profile).
5. If reviewer returns `Issues Found`: no `revise_protocol` → uses generic fixer (`applying-review-feedback`, Step 3a). Dispatches fresh fixer subagent.
6. Fixer edits the file in place and returns `Edits Applied`.
7. Re-reviews. If approved, surfaces approval message.

## Pass criteria

- Framework detection falls back gracefully — no crash, no hang
- FRAMEWORK_PROFILE_PATH = `none` passed to both reviewer and fixer
- Fix routed to `applying-review-feedback` (Step 3a)
- Fixer edits the document directly (no hand-off command surfaced)
- Surface message on approval is concise and includes the file path
