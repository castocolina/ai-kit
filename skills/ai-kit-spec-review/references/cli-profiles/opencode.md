---
id: opencode
display_name: OpenCode CLI
status: confirmed
read_only: unconfirmed
detect: "which opencode"
last_verified: 2026-08-28
source: live smoke test against a real installed opencode CLI + a real
  local-provider model (local-llm-env/my-plan-review), piping a prompt
  via stdin with no positional message argument
---

# opencode — reviewer profile

**Multi-provider by design** — `opencode models` lists every model it routes
to, under its own provider namespaces. Confirmed live output includes
third-party models with no separate CLI needed: `opencode-go/kimi-k3`,
`opencode-go/qwen3.8-max`, `opencode-go/grok-4.6`, `opencode-go/gpt-5.6-luna`,
plus `ollama-cloud/*` and local-model entries. This is how Kimi/Qwen reviewers
are reachable without a dedicated profile: store `runtime = "opencode"` and
`model = "opencode-go/kimi-k3"` (or whichever listed id), with `vendor` set to
the model's real maker (`moonshot`, `alibaba`, ...), not `"opencode"`.

The runner formula (opencode 2.0.29 `run --help`) is:

```text
opencode run --model <model> --format json            # exec: adds --auto
opencode run --model <model> --agent plan --format json   # review
```

ai-kit stores the pair, not this argv. A `#variant` suffix
(`provider/model#variant`) is a model-id suffix the runner strips before the
listing check: the listing has no variants, and the suffix itself is not
validated. The prompt arrives on stdin; a table-runtime entry has no
`{prompt}` placeholder.

Read-only is unconfirmed. Review passes `--agent plan`; that is the runner's
review shape, not a confirmed guarantee that the CLI cannot write. The runner
also sets `OPENCODE_DISABLE_AUTOUPDATE=1` and
`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`. It still loads `~/.agents/skills` and
`~/.config/opencode/skills` (a partial bare profile, per opencode's docs).

`opencode stats` shows token usage and cost. Its parseable shape is
unconfirmed; availability is classified from the runner's status line.
