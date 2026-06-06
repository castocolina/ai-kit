---
name: commit-message
description: Use when generating a git commit message for staged changes, all working changes, an amend to the last commit, or a specific commit hash. Triggered by: "commit message", "write a commit", "generate commit", "amend message", or passing staged/working/amend/<hash> as args.
---

# Commit Message Generator

Analyze git changes and produce Conventional Commits messages in up to three levels of detail.

## When to Use

- User asks for a commit message (with or without arguments)
- Skill invoked with args: `staged`, `working`, `amend`, or a commit hash

## Mode Selection

Interpret the argument passed via the Skill tool `args` field:

| Argument | Mode |
|---|---|
| *(none)* or `staged` | Analyze staged changes only |
| `working` or `all` | Analyze all changes (staged + unstaged) |
| `amend` | Analyze the last commit; show current message and suggest improvement |
| A commit hash (e.g. `abc1234`) | Analyze that specific commit |

## Gather Context First

Before generating the message, use git tools (mcp__git or Bash) to collect:

1. **Worktree root** — `git rev-parse --show-toplevel`
2. **Status** — `git status --short`
3. **Staged diff stat** — `git diff --cached --stat`
4. **Unstaged diff stat** — `git diff --stat` *(for `working`/`all` mode)*
5. **Last commit** — `git log -1 --format="%H %s"` *(for `amend` or hash mode)*
6. **Task ID** — scan `docs/tasks/` filenames for the active task number

## Format

```
type: [task-id] brief description   ← max 50 chars
<blank line>
- Bullet points summarizing changes
<blank line>
BREAKING CHANGE: ...   ← footer, only if needed
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `chore`, `test`, `style`

**Task ID:** Extract the task number from `docs/tasks/` and place it as `[203]` at the START of the description. Omit if no active task file exists.

## Output

Three detail levels exist:

1. **Concise** — max 3 lines, no body
2. **Medium** — max 10 lines, brief bullet body
3. **Detailed** — 10+ lines for complex, multi-scope changes

**If the user explicitly requests a specific level** (e.g. "just the medium", "concise only", "give me the detailed one"), output ONLY that level — nothing else.

**Otherwise**, always produce Concise. Only add Medium if the change spans multiple concerns worth summarizing. Only add Detailed if the change is multi-scope or includes breaking changes. Label each version so the user can choose.

## CRITICAL

Do NOT create any git commit. Output the message(s) only and WAIT for explicit user authorization before running `git commit`.
