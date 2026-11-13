# commit-message

This is the text of the existing `commit-message` skill that the designs in this folder refer to.

## What it does

1. Reads the staged diff with `git diff --staged`. With nothing staged it stops with "nothing to commit".
2. Writes one Conventional Commits message: a type, an optional scope, a subject of 72 characters or fewer, and a body when the change needs one.
3. Prints the message.

## Rules

- Do NOT create any git commit. Output the message(s) only and WAIT for explicit user authorization before running `git commit`.
- Never stage files; staging is the user's step.
