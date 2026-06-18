# Eval 01 — superpowers plan routes to writing-plans skill

## Scenario

User invokes `review-spec` on a superpowers plan document.

## Prompt

```
/review-spec docs/superpowers/plans/2026-06-14-some-feature.md
```

## Expected behavior

1. Orchestrator confirms file exists on disk (Step 0).
2. Resolves codebase root from the plan file's directory using `git -C` (Step 0.1).
3. Detects framework as `superpowers` (conversation signal: file lives under `docs/superpowers/plans/`).
4. Resolves profile from SEEDS_DIR — absolute path. ARCHETYPE = `plan`.
5. Dispatches reviewer subagent (reviewing-specs skill) with the plan path, archetype, profile path, and codebase root. Prompt contains NO document content.
6. If reviewer returns `Issues Found`: checks profile's `revise_protocol.routes` for `plan` archetype → finds `skill:superpowers:writing-plans` → dispatches a fresh subagent invoking the `superpowers:writing-plans` skill with the report path + plan path.
7. Re-reviews after the skill-based fix. If approved, surfaces success message.

## Pass criteria

- Reviewer dispatched as a clean-context subagent (no document body in prompt)
- Archetype set to `plan`, framework to `superpowers`
- Fix routed to `writing-plans` skill (Step 3b-skill), NOT the generic `applying-review-feedback`
- SEEDS_DIR resolved as an absolute path (not a bare relative path)
- Surface message mentions approval and the file path
