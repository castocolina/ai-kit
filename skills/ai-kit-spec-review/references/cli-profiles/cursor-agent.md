---
id: cursor-agent
display_name: Cursor Agent CLI
status: confirmed
read_only: "confirmed (--mode plan or --mode ask — both explicitly read-only per --help; --sandbox enabled is a secondary, redundant guard)"
detect: "which cursor-agent"
last_verified: 2026-08-28
source: cursor-agent --help, live against a real authenticated install (2026.08.25-3e8eec8)
---

# cursor-agent — reviewer profile

**Binary name hazard — always use `cursor-agent`, never `agent`.**
Cursor's own installer symlinks `~/.local/bin/agent` → the real
`cursor-agent` binary, but on a machine that also has the Grok CLI
installed (`~/.grok/bin/agent`), `PATH` order decides which `agent`
resolves — confirmed live: `~/.grok/bin/agent` won on this machine even
though cursor's `agent` symlink existed too, because `~/.grok/bin`
appeared earlier in `PATH`. `detect_installed_clis`/`KNOWN_CLIS` already
only ever probes `cursor-agent` (never the ambiguous bare `agent`) — do
not "helpfully" add `agent` as an alias anywhere in this design.

**Read-only dispatch — use `--mode plan` (not just `--sandbox`).**
`cursor-agent --help` documents `--mode plan` as "read-only/planning
(analyze, propose plans, no edits)" and `--mode ask` as "Q&A style ...
(read-only)" — this is the real, confirmed read-only guarantee, stronger
than the generic `--sandbox <enabled|disabled>` flag (which only
"explicitly enable or disable sandbox mode (overrides config)" — no
read-only guarantee documented on its own). Use `--mode plan` for review
dispatch; `review-spec.py`'s `build_reviewer_command("cursor-agent",
mode=...)` builder refuses any other mode with a `ValueError` rather
than building a write-capable command.

**Prerequisite — `~/.cursor/` must be writable by the invoking user,
independent of the target repo's own read-only posture.** Confirmed
live: `--mode plan` still needs to write its own sandbox policy file
under `~/.cursor/sandbox-policies/` and a per-project state directory
under `~/.cursor/projects/<slug>/` — neither is optional bookkeeping
cursor-agent can skip. A restricted execution environment that denies
writes to `$HOME` (this design's own dev sandbox did, until bypassed)
makes cursor-agent fail with an unrelated-looking `ENOENT`/`EROFS` error
on that internal write, **not** a message about the actual review. If a
dispatch fails with an error mentioning `~/.cursor/`, this is the cause
— it is not a signal about model/quota availability and should not be
treated as one.

**Free-plan model gating — confirmed live, and it looks like a bug if
you don't know about it.** On a Cursor Free plan, only `--model auto`
works; any named model (`glm-5.2-high`, `kimi-k3-high`, `claude-...`,
even that model wrapped in a bracket-parameter override) fails with
`ActionRequiredError: Named models unavailable Free plans can only use
Auto. Switch to Auto or upgrade plans to continue.` (exit code 1). A
bracket-parameter override on a model this plan can't use at all fails
with a *different* message instead (`Cannot use this model: <id>.
Available models: auto, ...`) — both are real, both are correctly
classified `available: False` by `probe_reviewer_quota` (nonzero exit
code alone is sufficient; the extra `_UNAVAILABLE_SIGNALS` entries for
`actionrequirederror` are belt-and-suspenders). `cursor-agent models`
lists every model the *account* can see, not what the *plan* can
actually use — do not treat that list as availability; always run
`check-reviewer` (or let `probe-quota` do it) against a candidate before
trusting it works.

**Config is global-only and gets overwritten per run — do not rely on a
per-repo cursor config file.** Unlike `review-spec.toml`'s own local/
global split, cursor-agent's own settings live in a single global
location (`~/.cursor/cli-config.json`) that each invocation can rewrite;
there is no per-project cursor config this design should read or write.
Every per-call setting this design needs (model, effort/fast/context,
mode) must be passed as CLI arguments (`--model`, `--mode`) — never rely
on cursor's own persisted config state to carry a setting between calls,
since a different concurrent invocation (or the user's own interactive
use of `cursor-agent`) can change it first.

**Model catalog — confirmed live** (`cursor-agent models`, ~90+ ids):
multiple `gpt-5.x-codex-*`/`gpt-5.6-*` tiers (OpenAI), `claude-opus-5-*`/
`claude-sonnet-5-*`/`claude-fable-5-*` (Anthropic, several effort tiers
each, `-fast` variants, some with `1M`/thinking context variants),
`cursor-grok-4.5/4.6-*` (xAI, Cursor's own routing prefix — not the
standalone `grok` CLI), `composer-2.5*` (Cursor's own model),
`gemini-3.7-flash-high` (Google), `glm-5.2-high`/`glm-5.2-max` (Zhipu),
`kimi-k3-low`/`-high`/`-max`, `kimi-k2.7-code` (Moonshot). Vendor
attribution for all of these is in `review-spec.py`'s
`_MODEL_VENDOR_PREFIXES` table (`infer-vendor` CLI subcommand) — do not
re-infer it by reading model names.

**Effort/fast/context tuning is encoded in the `--model` argument
itself, not a separate flag** — confirmed live (`--help`): "Parameterized
models accept quoted bracket overrides, e.g.
`claude-opus-4-8[context=1m,effort=high,fast=false]`". `review-spec.py`'s
`build_reviewer_model_id("cursor-agent", base_model, effort=...,
fast=..., context=...)` builds this string for the reviewer entry's own
`model` field — never hand-write the bracket syntax in
`review-spec.toml` directly.

Non-interactive: `-p`/`--print`. **Use `--output-format text` (or omit
the flag — `text` is the default), never `json`**: `review-spec.py`'s
report parsing expects the reviewer output template's raw markdown on
stdout, not a JSON wrapper. `status`/`whoami` reports auth status
(confirmed live: `✓ Logged in as <email>`).

**No `{prompt}` in this template — prompt delivery is stdin-only,
confirmed live**: `--print`/`-p` is a boolean flag (`--help`: "Print
responses to console ... (default: false)"), not a value-taking one — set
alone, with no positional prompt argument, cursor-agent reads the prompt
from stdin instead. `review-spec/SKILL.md`'s Step 1 external dispatch and
`probe_reviewer_quota` both redirect the already-on-disk prompt file as
this process's stdin unconditionally, so this needs no special-casing at
the dispatch step.

```bash
cursor-agent -p --output-format text --mode plan --model {model}
```

(`review-spec.py`'s `build_reviewer_command("cursor-agent", mode="plan")`
returns exactly this template — do not hand-write it; `{model}` is a bare
config `command` template placeholder, unquoted. `render_reviewer_command`
still accepts a `{prompt}` placeholder too, `shlex.quote`d, for a
hand-written open-hatch template that prefers to inline it — this
profile's own template simply doesn't use it.)

**Quota/plan-gating probe — confirmed live**: a trivial call against a
named model on a Free-plan account returns the `ActionRequiredError`
above with exit code 1; the same call with `--model auto` succeeds with
exit code 0 and clean plain-text output. This is the reference
implementation for testing this profile's `probe_reviewer_quota`
classification end to end — it needs no CLI-specific parser, the same
generic "nonzero exit or unavailable-signal text" rule every other
profile uses already covers it.
