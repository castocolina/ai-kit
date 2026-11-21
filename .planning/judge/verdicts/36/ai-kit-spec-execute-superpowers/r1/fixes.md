# Loop 36 round 1 fixes for ai-kit-spec-execute-superpowers

Bar met (worst 87.2 B, no critical finding, lowest percent 87.2 against the loop 32 base 86.4); three high findings (two from referee-one, one from referee-two) fixed in place under the 3-or-fewer rule. No further round runs for this skill and its digest is stale by design until its next loop.

- referee-one D8-1 (high): the plan's scalar file outlives a run, so a later run of the same plan could fold from an earlier run's `FOLD_BASE` or skip the ready step through a stale `UNIT_FLOW=0`; Step 5 now clears both once the last report's outcome is `done` or `nothing to do` (any other outcome keeps them for the re-run), and Step 1 says so where it records them. File: `skills/ai-kit-spec-execute-superpowers/SKILL.md`.
- referee-one D8-2 (high): the codex confinement claim is qualified: writes stay in the target dir, `/tmp`, `$TMPDIR` and any writable root the owner's codex configuration adds, so it is not an unconditional boundary. Files: `skills/ai-kit-spec-execute-superpowers/SKILL.md`, `skills/ai-kit-spec-execute-superpowers/references/design-notes.md`.
- referee-two D8-1 (high): the fix-round increment block now carries the condition in the prose before it and in a comment on its line: run only at a new round; a resume restores `$FIX_ROUND`, never runs the block, and goes straight to `references/escalation.md`'s resolve block. File: `skills/ai-kit-spec-execute-superpowers/SKILL.md`.

Not fixed (below the fix rule's severity): the medium and low findings of both judges stay in the verdict records.
