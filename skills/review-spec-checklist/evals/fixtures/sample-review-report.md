## Review: design-good.md

### Document Type
design

### Files Read (fresh from disk)
- design-good.md (50 lines)
- /home/user-zero/.claude/skills/commit-message/SKILL.md (66 lines)

### CRITICAL

- **Wrong factual claim about existing skill behavior** — Location: Context section, line 5 (the sentence beginning "The existing `commit-message` skill"). Required: Context section must accurately describe the current behavior of `commit-message/SKILL.md`. The actual SKILL.md (line 65) states: "Do NOT create any git commit. Output the message(s) only and WAIT for explicit user authorization before running `git commit`." The skill never stages or commits without authorization. Once the Context is corrected, re-evaluate whether `--draft` remains warranted given the existing wait-for-authorization behavior. Why: Two readers form different mental models of the codebase (one believes the skill auto-commits, one knows it does not). The design's stated motivation for `--draft` ("so they can edit it" before staging) may collapse once the premise is corrected, since the skill already withholds commit pending authorization.

### Status: Issues Found — fix and re-invoke
