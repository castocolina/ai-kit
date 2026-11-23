# Loop 38.1 round 3 fixes: ai-kit-cross-ai

Two high findings (referee-one; referee-two had none), three or fewer, so `decide.py met 2 3` gave
`fix`: they are fixed here under the no-rejudge rule and the skill gets no further round (its digest
is stale by design until its next loop). Each was checked against the runner template
`skills/ai-kit-spec-review/references/cross-ai.mjs` first.

- referee-one D8-1 (SKILL.md:109): confirmed (the tree snapshot runs `git add -A` into a temporary index and `git write-tree`, cross-ai.mjs:5295-5308, which writes git objects; real runs sweep and keep state under the state home). Section 2 now says a review call writes git objects and its own state even without a legacy retry source, and that a review which may write nothing at all needs an owner-approved isolated checkout and state directory, or stops. File: skills/ai-kit-cross-ai/SKILL.md.
- referee-one D8-2 (SKILL.md:289): confirmed (`taskDigest` keys the baseline on the `<objective>` text, else on the prompt body, cross-ai.mjs:3936-3944; the `session` line of a real call prints only after the call started). The partial fix round now adds its paragraph outside the `<objective>` block, previews the call with `--print-argv` and requires `session` `applied`, and treats a prompt without an `<objective>` block as an owner stop. File: skills/ai-kit-cross-ai/SKILL.md.

## Phase 38.1 code review (after round 3; no judge round, recorded in 38.1-REVIEW.md)

- The class table's `auth` row now says that on a confirmed router lane an auth row marked for the router reads as `quota` (the catalogue's two auth rows carry `routerClass: quota`; `--describe` prints `auth.router_quota: true`).
- Section 6 gains the `[runner.retry]` key table (one row per key with its default and bounds, `hard_every_s` included; SPEC R10's one-row-per-new-key edge), pinned against the template CONFIG `retry` by `PolicyText.test_section_6_has_one_row_per_retry_key_with_its_default`, and a conditional sentence: a copy whose CONFIG `retry` predates `hard_every_s` keeps its own list and takes 600 s from the defaults.
- The blocked-until section now says a row pool's provider is the model id's part before `/` (an id without one needs `--pool`) and that the record follows the attempt, not the run's status (runner fix in the same review: one call site before the review-dirty and git-failure returns).
- references/subprocess-quota-policy.md: an in-call hard wait's re-attempt belongs to the next check (`cycle` + 1) and is not a soft retry.
