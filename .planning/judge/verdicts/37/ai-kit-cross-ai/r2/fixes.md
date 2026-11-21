# Loop 37 round 2 fixes: ai-kit-cross-ai

Round 2 left 4 high findings (referee-one), so the skill goes to round 3, the last (decide.py row `next-round`); the orchestrator fixes them in the skill's own files before that round.

- D6-1 (referee-one, high): the argv-file section says supervision is not containment: the tree check detects a change after the fact, prevents no write and cannot run outside a git work tree; a review-role argv-file lane is launched only with an owner-approved read-only command inside a git work tree. File: `skills/ai-kit-cross-ai/SKILL.md` (section 2).
- D8-1 (referee-one, high): section 2 resolves one `$RUNNER` path first (the project copy, otherwise the sibling `ai-kit-spec-review` template; stop when neither exists) and uses it for the header check and every launch; the launch examples use `node "$RUNNER"`. Files: `skills/ai-kit-cross-ai/SKILL.md`, `skills/ai-kit-cross-ai/references/launch-and-wait.md`.
- D8-2 (referee-one, high): setting lines describe the resolved invocation and print before the model preflight, so they never prove the model ran; the outcome is the exit code and the last `AIKIT-XAI` line. File: `skills/ai-kit-cross-ai/SKILL.md` (Settings report).
- D8-3 (referee-one, high): "a bare id is refused before spawn" is replaced by the three checks the template makes: the syntax floor (exit 2, `usage`), the advisory seed-shape note (the call runs), and the live preflight (`bad_model`, exit 69). File: `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md`.
