## Review: plan-bad.md

### Document Type
plan

### Files Read (fresh from disk)
- plan-bad.md (51 lines)

### HIGH

- **Task 1 names no file** — Location: Task 1, Files block (the line `- Modify: TBD`). Required: replace `Modify: TBD` with `Modify: skills/commit-message/SKILL.md`, the file the argument parser belongs to. Why: an executor cannot start Task 1 without a named file to change.

### MEDIUM

- **Goal is a fragment, not a sentence** — Location: the Goal line (`**Goal:** Add \`--draft\` flag.`). Required: state the goal in one sentence that names what a user gets with `--draft`. Why: a fragment gives the executor no clear test for done.

### Status: Issues Found — fix and re-invoke
