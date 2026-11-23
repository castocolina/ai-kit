# Loop 36 round 1 fixes for ai-kit-spec-config

Bar met (worst 88.8 B, no critical finding, lowest percent 88.8 against the loop 35 base 88.0); three high findings (two from referee-one, one from referee-two) fixed in place under the 3-or-fewer rule. No further round runs for this skill and its digest is stale by design until its next loop.

- referee-one D8-1 (high): the write-risk warning and question of Step 2.5 now say the test call starts in a private temporary directory (as `quota.py` `_run_probe` does) but runs with the CLI's normal write permissions, which nothing confines to that directory, and that later runs use them against the working tree; the same correction in the quota-probe question. Files: `skills/ai-kit-spec-config/SKILL.md`, `skills/ai-kit-spec-config/references/check-only.md`.
- referee-one D8-2 (high): the load condition for `references/cli-model-selection.md` now names both callers: step 2 of the wizard flow for its items 1 to 4, and step 6 for item 6, the code-index alternative check that runs for every kept lane. File: `skills/ai-kit-spec-config/SKILL.md`.
- referee-two D8-1 (high): step 5 of the wizard flow now says the usability record comes from step 6's own call with `--catalog-path` and no `--effort`, so a lane whose effort is tested takes two separate calls (the CLI refuses both flags together). File: `skills/ai-kit-spec-config/references/wizard-flow.md`.

Not fixed (below the fix rule's severity): the medium and low findings of both judges stay in the verdict records.
