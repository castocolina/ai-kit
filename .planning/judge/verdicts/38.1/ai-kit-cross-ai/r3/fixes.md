# Loop 38.1 round 3 fixes: ai-kit-cross-ai

Two high findings (referee-one; referee-two had none), three or fewer, so `decide.py met 2 3` gave
`fix`: they are fixed here under the no-rejudge rule and the skill gets no further round (its digest
is stale by design until its next loop). Each was checked against the runner template
`skills/ai-kit-spec-review/references/cross-ai.mjs` first.

- referee-one D8-1 (SKILL.md:109): confirmed (the tree snapshot runs `git add -A` into a temporary index and `git write-tree`, cross-ai.mjs:5295-5308, which writes git objects; real runs sweep and keep state under the state home). Section 2 now says a review call writes git objects and its own state even without a legacy retry source, and that a review which may write nothing at all needs an owner-approved isolated checkout and state directory, or stops. File: skills/ai-kit-cross-ai/SKILL.md.
- referee-one D8-2 (SKILL.md:289): confirmed (`taskDigest` keys the baseline on the `<objective>` text, else on the prompt body, cross-ai.mjs:3936-3944; the `session` line of a real call prints only after the call started). The partial fix round now adds its paragraph outside the `<objective>` block, previews the call with `--print-argv` and requires `session` `applied`, and treats a prompt without an `<objective>` block as an owner stop. File: skills/ai-kit-cross-ai/SKILL.md.
