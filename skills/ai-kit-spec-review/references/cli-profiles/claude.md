---
id: claude
display_name: Claude Code CLI
status: confirmed
read_only: unconfirmed
detect: "which claude"
last_verified: 2026-08-28
source: live smoke test against a real installed claude CLI, piping a
  prompt via stdin with no positional prompt argument
---

# claude — reviewer profile

The runner has a review formula and an execute formula for `claude`. The execute formula runs with full permissions, like every other execute runtime, and is labelled unverified until a live probe is recorded; the runner then prints a note on every execute call. ai-kit's routing still skips an exec-mode `claude` candidate with route `no_formula` until it reads the runner's own `--describe` fact: a fact about what ai-kit has recorded, not a table flag. Advice (seed row, unverified): `claude` is usually the main agent on this host, so it is more often a review target than an executor.

The runner's review formula (review mode) is:

```text
claude -p --model <model> --output-format json --permission-mode plan
```

The execute formula (execute role) is:

```text
claude -p --model <model> --output-format json --permission-mode bypassPermissions
```

A resume adds `--resume <id>` with an id the runner printed in `session=`.

ai-kit does not store that argv. A review entry stores the pair
`runtime = "claude"` and `model`, and dispatch runs it through the supervised
runner. `<model>` is the entry's model: one of the four aliases (`sonnet`,
`opus`, `haiku`, `fable`) when this host is Claude Code and selects per call,
or a full id the runner passes to `--model`.

Read-only enforcement is not live-verified. The formula passes
`--permission-mode plan`; that is the runner's review shape, not a confirmed
guarantee that the CLI cannot write.

Prompt delivery is stdin. The runner pipes the prompt; there is no `{prompt}`
placeholder because a table-runtime entry stores no `command`.

On a Claude Code host the same pair can run natively instead: the host's own
subagent takes the alias, and no subprocess starts. That per-call alias
selection is Claude Code only.

Quota and context-window introspection: unconfirmed syntax. No dedicated usage
subcommand is confirmed here; availability is classified from the runner's
status line (`AIKIT-XAI status=...`), the same way every other runner runtime
is classified.
