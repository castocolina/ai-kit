---
id: codex
display_name: OpenAI Codex CLI
status: confirmed
read_only: "confirmed (--sandbox read-only)"
detect: "which codex"
last_verified: 2026-08-28
source: codex --help + live smoke test against a real installed codex CLI
---

# codex — reviewer profile

Non-interactive: `codex exec`. Model: `-m <model>`. Reasoning effort and
service speed tier are SEPARATE knobs, each set via `-c key='"value"'`.

**No `{prompt}` in this template — prompt delivery is stdin-only,
confirmed live**: `codex --help` documents the positional `PROMPT` arg as
"If not provided as an argument (or if `-` is used), instructions are
read from stdin" — omitting it entirely (as this template does) reads the
whole prompt from stdin. `review-spec/SKILL.md`'s Step 1 external
dispatch and `probe_reviewer_quota` both redirect the already-on-disk
prompt file as this process's stdin unconditionally, so this needs no
special-casing at the dispatch step.

```bash
codex exec --sandbox read-only --skip-git-repo-check \
  -m {model} \
  -c model_reasoning_effort='"{effort}"' \
  -c service_tier='"{service_tier}"'
```

`{model}` above is the literal config `command` template placeholder —
bare, unquoted. `{effort}`/`{service_tier}` are also literal
`command`-template placeholders, but filled from the reviewer entry's own
`extra` table (e.g. `effort = "high"`, `service_tier = "fast"` in
`review-spec.toml`), not from `{model}` — `render_reviewer_command` fills
every placeholder the template references via
`resolved.command.format(model=..., prompt=..., **resolved.extra)`
(`{prompt}` is always accepted too, `shlex.quote`d, for a hand-written
open-hatch template that prefers to inline it instead — this profile's
own template simply doesn't reference it), so an entry that omits
`effort`/`service_tier` from its `extra` table and still references them
here fails to render (a config error, surfaced at dispatch — see
`review-spec/SKILL.md`'s reviewer dispatch step). **Do not append
`2>/dev/null`** — `probe_reviewer_quota` classifies availability from
`stdout + stderr` combined, so suppressing stderr hides the exact
usage-limit signal the probe below depends on.

**Quota probe — confirmed live**: a low-effort/fast-tier call against an
exhausted quota returns a usage-limit error. Example that produced exactly
that error during this design's research:

```bash
codex exec -m gpt-5.6-luna -c model_reasoning_effort='"low"' -c service_tier='"fast"' 'Only say: Hello world!'
```

This is the reference implementation for the "cheap probe, detect the
error" quota-check mechanism — parse the exit code / stderr for a
usage-limit signal rather than looking for a dedicated quota subcommand.
