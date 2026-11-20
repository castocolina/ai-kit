---
id: opencode
display_name: OpenCode CLI
status: confirmed
read_only: unconfirmed
detect: "which opencode"
last_verified: 2026-11-20
source: recorded help of opencode 2.3.2 (tests/fixtures/cli_help/opencode/, refreshed by tools/record_cli_help.py)
---

# opencode — reviewer profile

**Multi-provider by design** — `opencode models` lists every model it routes to as `provider/model` (for example `fake/placeholder-model-1`; model-example: invented id). Store `runtime = "opencode"` and the listed id as `model`.

The runner formulas (opencode 2.3.2 `run --help`, recorded) are:

```text
opencode run --model <model> --auto --format json --standalone            # exec
opencode run --model <model> --agent plan --format json --standalone   # review
```

ai-kit stores the pair, not this argv. A `#variant` suffix (`provider/model#variant`) selects an effort level. `opencode models` prints ids without variants; the model API (`GET /api/model`, `variants[].id`) lists them, and ai-kit stores them as listed (seen 2026-11-19: none, minimal, low, medium, high, xhigh, max, thinking). `opencode models` accepts the global `--standalone` and `--server` flags; the runner's listing does not pass them, so it reads the shared service, read-only. The prompt arrives on stdin; a table-runtime entry has no `{prompt}` placeholder.

Read-only is unconfirmed. Review passes `--agent plan`; that is the runner's
review shape, not a confirmed guarantee that the CLI cannot write. The runner
also sets `OPENCODE_DISABLE_AUTOUPDATE=1` and
`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`. It still loads `~/.agents/skills` and
`~/.config/opencode/skills` (a partial bare profile, per opencode's docs).

`opencode stats` shows token usage and cost. Its parseable shape is
unconfirmed; availability is classified from the runner's status line.
