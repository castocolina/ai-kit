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

**Multi-provider by design** — `opencode models` lists every model it
routes to, under its own provider namespaces. Confirmed live output
includes third-party models with no separate CLI needed:
`opencode-go/kimi-k3`, `opencode-go/qwen3.8-max`, `opencode-go/grok-4.6`,
`opencode-go/gpt-5.6-luna`, plus `ollama-cloud/*` and local-model entries.
This is how Kimi/Qwen reviewers are reachable in this design without a
dedicated Kimi/Qwen CLI profile — set `cli = "opencode"` and
`model = "opencode-go/kimi-k3"` (or whichever listed id), with `vendor`
set explicitly to the model's real maker (`moonshot`, `alibaba`, etc.), not
`"opencode"` itself.

Non-interactive: `opencode run [message..]`. Model: `-m/--model
<provider/model>`.

**No `{prompt}` in this template — prompt delivery is stdin-only,
confirmed live**: `opencode run -m {model}` with no positional `message`
argument reads the prompt from stdin. `review-spec/SKILL.md`'s Step 1
external dispatch and `probe_reviewer_quota` both redirect the
already-on-disk prompt file as this process's stdin unconditionally, so
this needs no special-casing at the dispatch step.

```bash
opencode run -m {model}
```

(`{model}` here is the full `<provider/model>` id, e.g.
`opencode-go/kimi-k3` or a local provider's `local-llm-env/my-plan-review`
— it is a bare config `command` template placeholder, unquoted.
`render_reviewer_command` still accepts a `{prompt}` placeholder too,
`shlex.quote`d, for a hand-written open-hatch template that prefers to
inline it — this profile's own template simply doesn't use it.)

`opencode stats` shows token usage/cost statistics — likely the quota
introspection source; exact parseable shape unconfirmed, research during
implementation.
