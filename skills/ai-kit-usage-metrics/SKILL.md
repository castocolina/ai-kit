---
name: ai-kit-usage-metrics
description: Build a local usage-metrics dashboard from AI CLI session logs. Use when the user asks about "usage metrics", "usage dashboard", "how do I use my AI CLIs", command history across Claude Code / opencode / rtk, or wants a static HTML view of captured shell commands. Wave 2 captures Claude Code, opencode, and rtk raw sources; refinement still covers Claude Code simple Bash only.
---

# ai-kit-usage-metrics

Thin wrapper around `ai-kit-usage-metrics.py`. Invoke the CLI; do not
re-implement capture, refine, or dashboard generation in prose.

## Scope

Wave 2 of the usage-metrics pipeline. Honest coverage:

- **Raw capture runtimes (3):** Claude Code session JSONL under
  `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/*/*.jsonl`; opencode's
  `${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db` (session /
  message / part) plus `storage/**/*.json`; rtk's
  `${XDG_DATA_HOME:-$HOME/.local/share}/rtk/history.db` (commands +
  parse_failures) and `rtk/tee/*.log`.
- **Refined commands:** still Claude Code simple (non-compound) Bash
  `tool_use` entries only — a command whose text contains `&`, `;`, or `|`
  is captured losslessly in raw storage but is not refined this wave.
  opencode / rtk envelopes are captured, not yet refined.
- **Outputs:** `${XDG_DATA_HOME:-$HOME/.local/share}/ai-kit/usage-metrics/`
  holding `raw/{claude,opencode,rtk}.jsonl`, `refined/refined.db`, and
  `dashboard.html`.

Codex, Cursor, compound-command decomposition, and the full 5-axis
dashboard UI are later waves (05-03+). Do not claim they work yet.

Never read or write the operator's real config to "just see real data"
during development; tests and verification use scratch `XDG_DATA_HOME` /
`CLAUDE_CONFIG_DIR` trees.

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
