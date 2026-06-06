# Add `--draft` flag to commit-message skill

## Context

Users want to preview the generated commit message before staging the commit, so they can edit it. The existing `commit-message` skill at `~/.claude/skills/commit-message/SKILL.md` always emits the final message and stages immediately. We add a `--draft` flag that prints the message to stdout without staging.

## Goal

A user running the skill with `--draft` gets the proposed message in their terminal, can edit it, and then runs the skill again without `--draft` to actually commit.

## Approach

Extend the existing skill rather than duplicate logic:

1. Reuse the diff-reading and message-generation paths already in `commit-message/SKILL.md`.
2. Add a single new branch: when `--draft` is present, print the generated message and exit before any `git add` / `git commit` step.
3. Stay aligned with the existing Conventional Commits formatting that `commit-message` already produces — no new format.

## Components

| Component | Responsibility |
|---|---|
| Argument parser | Detect `--draft` flag at skill entry |
| Generator (existing) | Unchanged — produces message |
| Output sink | If draft: stdout. If not: existing commit path. |

## Data flow

```
git staged diff → generator → message
                                 ├── --draft? → stdout, exit 0
                                 └── else      → existing commit path
```

## Error handling

- No staged changes → existing skill already errors with "nothing to commit"; reuse that path for `--draft` too.
- Generator failure → propagate the existing skill's error message; do not invent a new one.

## Testing

- Manual: stage a small change, run with `--draft`, confirm message printed and `git status` unchanged.
- Manual: run without `--draft` against the same staged change, confirm commit created.
- Regression: existing `commit-message` test paths must still pass.

## Out of scope

- Editing the message interactively (user uses their editor).
- Saving drafts to a file. If users want this, follow-up design.
