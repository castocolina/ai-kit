---
name: ai-kit-usage-metrics
description: Build a local usage-metrics dashboard from AI CLI session logs. Use when the user asks about "usage metrics", "usage dashboard", "how do I use my AI CLIs", command history across Claude Code, or wants a static HTML view of captured shell commands. Wave 1 covers Claude Code simple (non-compound) Bash commands only.
---

# ai-kit-usage-metrics

Thin wrapper around `ai-kit-usage-metrics.py`. Invoke the CLI; do not
re-implement capture, refine, or dashboard generation in prose.

## Scope

Wave 1 of the usage-metrics pipeline. Honest coverage:

- **Runtime:** Claude Code session JSONL under
  `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/*/*.jsonl` only.
- **Commands:** simple (non-compound) Bash `tool_use` entries — a command
  whose text contains `&`, `;`, or `|` is captured losslessly in raw storage
  but is not refined this wave.
- **Outputs:** `${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit/usage-metrics/`
  holding `raw/claude.jsonl`, `refined/refined.db`, and `dashboard.html`.

opencode, rtk, Codex, Cursor, compound-command decomposition, and the full
5-axis dashboard UI are later waves. Do not claim they work yet.

Never read or write the operator's real config to "just see real data"
during development; tests and verification use a scratch `CLAUDE_CONFIG_DIR`.

## Resolve the entrypoint

Resolve once per invocation, in one Bash call, and record the printed path as
a **literal absolute path**.

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-usage-metrics}" \
         "$HOME/.claude/skills/ai-kit-usage-metrics" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-usage-metrics" \
         "$HOME/.agents/skills/ai-kit-usage-metrics" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-usage-metrics.py" ] && { printf '%s\n' "$d/ai-kit-usage-metrics.py"; break; }
done
```

## Subcommands

- `capture` — lossless raw JSONL ingest for each registered source
- `refine` — simple-command rows into `refined.db`
- `dashboard` — regenerate static `dashboard.html` from the refined DB
- `run` — `capture` then `refine` then `dashboard`

```bash
python3 "$TOOLS_PY" run
```

`$TOOLS_PY` is the literal absolute path recorded from the resolution block.
The pipeline never sends data off-machine.
