# Loop 36 round 2 fixes: ai-kit-spec-review

Round 2 left 3 high findings (all from referee-one; referee-two none), bar met: the fix row, no further round.

- D8-1 (high): Step 0.1 point 1 resolves the toplevel of every document, not only the first; agreeing toplevels give the root, differing ones fall to point 2's different-worktrees rule, which now names the declared cross-repo labeled set as the exception. File: `skills/ai-kit-spec-review/SKILL.md`.
- D8-2 (high): the pending-lane resume file records `revisions_authorized`, and the re-invoke restores it; when it is absent or `no`, Step 3 surfaces the findings and asks before any fixer or framework rewrite. File: `skills/ai-kit-spec-review/references/cross-ai-dispatch.md`.
- D8-3 (high): Step 0.7 point 0 runs `detect-tools` only when `TOOLS_PY` exists and sets `TOOL_AVAILABILITY_JSON` to `{}` otherwise, matching the missing-helper fallback. File: `skills/ai-kit-spec-review/references/cross-ai-dispatch.md`.

Medium and low findings were not counted by the rule and were not changed. The skill's digest is stale by design until its next loop.
