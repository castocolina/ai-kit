---
id: grok
display_name: Grok CLI (xAI)
status: confirmed
read_only: unconfirmed
detect: "which grok"
last_verified: 2026-08-28
source: grok --help + live smoke test against a real installed grok CLI —
  corrects two earlier unverified assumptions, that the bare positional
  prompt was headless-safe (it launches the TUI) and that
  `--output-format text` was a valid value (it is not); see below
---

# grok — reviewer profile

**Grok has no runner formula.** It is a custom entry: no `runtime`, a stored
`command`, trust-gated like any other custom command. `build-command --runtime grok`
prints the command to store:

```bash
grok -p {prompt} -m {model} --output-format plain
```

The launcher (the same supervision core as the runner, fixed argv, no shell)
runs that command. Because a custom entry has no runner status line, the
launcher classifies stderr itself (quota, auth, configuration, and the
remaining closed reasons).

**Headless mode requires `-p`/`--single <PROMPT>` — a bare positional
`grok <PROMPT>` launches the interactive TUI instead**, confirmed live: a
command missing `-p` fails with `Error: No such device or address (os
error 6)` when run without a tty (exactly the environment every subprocess
dispatch here runs in). That error says nothing about model or quota.
`-p`/`--single` is "Single-turn prompt. Prints the response to stdout and
exits".

Model: `-m/--model <MODEL>`. **`--output-format` accepts `plain`, `json`,
`streaming-json`, or `streaming-messages-json` only** — confirmed live via
`grok --help`. `text` is rejected (exit code 2). Never use `json`,
`streaming-json`, `streaming-messages-json` or `--json-schema` here either:
report parsing expects the reviewer's raw markdown on stdout, and a JSON
wrapper parses as zero findings. Always pass `--output-format plain`.

`{model}` and `{prompt}` are bare template placeholders. The launcher splits
the template the way a shell splits words and fills `{prompt}` as one whole
argument, so the template adds no extra quotes. Grok inlines the prompt, which
is why this template keeps `{prompt}` where the runner-backed profiles do not.

**Quota exhaustion — confirmed live**: an out-of-balance account returns
`Internal error: {"message": "API error (status 402 Payment Required): Grok
Build usage balance exhausted", "http_status": 402}` on stderr with a nonzero
exit. The launcher's stderr classification reads that as unavailable and
surfaces the message via `detail`.
