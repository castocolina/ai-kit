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

**Headless mode requires `-p`/`--single <PROMPT>` — a bare positional
`grok <PROMPT>` launches the interactive TUI instead**, confirmed live: a
command missing `-p` fails with `Error: No such device or address (os
error 6)` when run without a tty (exactly the environment every subprocess
dispatch here runs in) — a misleading, unrelated-looking error that has
nothing to do with model/quota availability. `-p`/`--single` is documented
as "Single-turn prompt. Prints the response to stdout and exits" — this is
the real non-interactive entry point, not the bare positional argument
(which `--help` documents only as "Initial prompt for the interactive
session").

Model: `-m/--model <MODEL>`. Output shaping: `--output-format
<OUTPUT_FORMAT>`; `--json-schema <SCHEMA>` for structured output (implies
`--output-format json`). **`grok`'s `--output-format` only accepts `plain`,
`json`, `streaming-json`, or `streaming-messages-json` — confirmed live
via `grok --help`; unlike `claude`/`cursor-agent`, `text` is not a valid
value here and fails hard** (`error: invalid value 'text' for
'--output-format <OUTPUT_FORMAT>' ... [possible values: plain, json,
streaming-json, streaming-messages-json]`, exit code 2 — this is exactly
the kind of nonzero-exit failure `probe_reviewer_quota`'s generic
classification already catches, so a wrong value here silently reads as
"reviewer unavailable" rather than surfacing the real cause). **Never use
`--output-format json`/`streaming-json`/`streaming-messages-json` or
`--json-schema` here either** — `ai-kit-spec.py`'s report parsing
(`report_has_status`/`parse_findings`) expects the reviewer output
template's raw markdown (`### Status:`, `### <SEVERITY>` headings,
`- **title** — Location: ...` bullets) as plain text on stdout, not JSON;
a JSON-wrapped response parses as zero findings and can bury the
`### Status:` line inside an escaped string, silently degrading this
reviewer. Pass `--output-format plain` explicitly (this CLI's default
without the flag is its own interactive/other shape, not confirmed safe
to omit — always pass `plain` explicitly, unlike `claude`, where omitting
the flag is confirmed to default to `text`):

```bash
grok -p {prompt} -m {model} --output-format plain
```

(`{model}`/`{prompt}` are bare config `command` template placeholders,
unquoted; `{prompt}` is `shlex.quote`d by `render_reviewer_command`
before substitution, so never wrap it in your own quotes here.)

**Quota exhaustion — confirmed live**: a real out-of-balance account
returns `Internal error: {"message": "API error (status 402 Payment
Required): Grok Build usage balance exhausted", "http_status": 402}` on
stderr with a nonzero exit code — no CLI-specific parser needed, the same
generic "nonzero exit" rule every other profile uses already classifies
this `available: False` and surfaces the message verbatim via `detail`.
