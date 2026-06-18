# Eval 04 — ambiguous framework detection uses low-confidence fallback

## Scenario

User invokes `review-spec` on a document whose framework can't be confidently determined, and the
user cannot or does not disambiguate.

## Prompt

```
/review-spec shared/architecture-decision.md
```

## Expected behavior

1. Orchestrator confirms file exists (Step 0).
2. Resolves codebase root (Step 0.1).
3. Framework detection is ambiguous: path matches no known seed's `detection_signals`; file contents don't clearly indicate a framework.
4. Orchestrator asks user once to disambiguate.
5. User responds "just use whatever" / does not specify.
6. Orchestrator sets FRAMEWORK_PROFILE_PATH = `none`, routes ALL archetypes through `applying-review-feedback` (Step 3a per low-confidence rule).
7. Reviewer dispatched with `FRAMEWORK_PROFILE_PATH = none`.
8. If issues found: fixer dispatched via Step 3a.
9. Surface message includes "Framework ambiguous — used the generic fixer." note.

## Pass criteria

- Orchestrator asks exactly once before falling back (not a blocking loop)
- FRAMEWORK_PROFILE_PATH set to `none` after fallback decision
- No native-skill or slash-command routing attempted
- Surface message explicitly notes framework ambiguity
- Review still completes (not aborted due to ambiguity)
