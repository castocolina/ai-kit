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

Non-interactive: `-p`/`--print` (print response and exit). Model selection:
`--model <model>`. Output shaping: `--output-format <format>` (only works
with `--print`).

**No `{prompt}` in this template — prompt delivery is stdin-only,
confirmed live**: `claude -p` with no positional prompt argument reads
the prompt from stdin instead. `review-spec/SKILL.md`'s Step 1 external
dispatch and `probe_reviewer_quota` both redirect the already-on-disk
prompt file as this process's stdin unconditionally (not gated on
whether a given entry's `command` still has a literal `{prompt}`) — an
unread stdin pipe here is harmless, so this needs no special-casing.

```bash
claude -p --model {model} --output-format text
```

`{model}` above is the literal `command`-template placeholder every
reviewer entry's `command` field can reference — written bare, never
wrapped in extra quotes. `render_reviewer_command` (in `review-spec.py`)
still accepts a `{prompt}` placeholder too — `shlex.quote`d before
substitution — for a hand-written open-hatch `command` that prefers to
inline the prompt as a shell argument instead of relying on stdin; this
profile's own template simply doesn't use it. Copy this shape directly
into a `command` field.

Quota/context-window introspection: unconfirmed syntax — research
whether a dedicated Claude usage
subcommand exists; otherwise rely on the same "low-effort call, detect a
usage-limit error" mechanism confirmed for `codex` (`codex.md`, this same
`cli-profiles/` directory).
