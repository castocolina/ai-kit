---
id: cursor
display_name: Cursor Agent CLI
status: confirmed
read_only: "confirmed (--mode plan or --mode ask — both explicitly read-only per --help; --sandbox enabled is a secondary, redundant guard)"
detect: "which cursor-agent"
last_verified: 2026-08-28
source: cursor-agent --help, live against a real authenticated install (2026.08.25-3e8eec8)
---

# cursor — reviewer profile

A cursor reviewer stores the pair `runtime = "cursor"` and `model`. Dispatch
runs it through the supervised runner, which builds the argv; the entry stores
no `command`. Bracket model ids (`base[effort=high,fast=false,context=1m]`) are
accepted: the runner strips the `\[[^\]]*\]$` suffix and checks the bare id
against `cursor-agent models`, and the suffix itself is not validated.

**Binary name hazard — `agent` counts only when its realpath ends in `cursor-agent`.**
Cursor and Grok both ship an `agent` binary, so PATH order is ambiguous. The
runner accepts `cursor-agent` first, and falls back to bare `agent` only when
`realpath` of that binary ends in `cursor-agent`. An unguarded `agent` is not a
cursor binary.

**Review now defaults to `--mode ask`.** Both `--mode plan` ("read-only/planning
(analyze, propose plans, no edits)") and `--mode ask` ("Q&A style ... (read-only)")
are documented read-only in `cursor-agent --help`, and both are stronger than
`--sandbox`, which only toggles sandbox mode and documents no read-only guarantee.
The runner's review formula passes `--mode ask` unless the entry sets
`cursor_mode = "plan"`, which keeps the old plan behavior. A migrated entry whose
stored command used `--mode plan` keeps `cursor_mode = "plan"` automatically.
Exec is a different formula (`--force --sandbox disabled`), not a review mode.

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
treated as one. The same writes happen under `--mode ask`.

**Fresh/unseen directories require `--trust` — confirmed live 2026-08-31.**
A `target_dir`/workspace cursor-agent has never run against before (e.g. a
freshly created worktree) fails with `Workspace Trust Required` before
`--mode`'s own read-only guarantee or `--force` even come into play —
this makes `probe-quota`/`check-reviewer` falsely report the candidate
unavailable on a brand-new project. `--help`: "Trust the current
workspace without prompting" — it only skips that interactive
confirmation, it grants no additional write capability beyond what
`--mode`/`--force` already control, so the runner's review and exec
formulas both pass `--trust`.

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
status and stderr — exit code alone is sufficient for these messages).
`cursor-agent models`
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
attribution for all of these is in `ai_kit_spec/vendor.py`'s
`_MODEL_VENDOR_PREFIXES` table (`infer-vendor` CLI subcommand) — do not
re-infer it by reading model names.

**Effort/fast/context tuning is encoded in the `--model` argument
itself, not a separate flag** — confirmed live (`--help`): "Parameterized
models accept quoted bracket overrides, e.g.
`claude-opus-4-8[context=1m,effort=high,fast=false]`".
`build-model-id --runtime cursor` builds this string for the entry's `model`
field — never hand-write the bracket syntax in `review-spec.toml` directly.

The runner's review formula (ask is the default; `cursor_mode = "plan"`
swaps the mode) is:

```text
cursor-agent -p --output-format json --model <model> --mode ask \
  --trust --workspace <cwd>
```

It parses the last JSON `result` event, so this profile uses `json` rather
than `text`. The prompt arrives on stdin (`-p` is a boolean flag), and a
table-runtime entry stores no `{prompt}` placeholder. `status`/`whoami`
reports auth (`✓ Logged in as <email>`, confirmed live).

**Quota/plan-gating probe — confirmed live**: a trivial call against a
named model on a Free-plan account returns the `ActionRequiredError`
above with exit code 1; the same call with `--model auto` succeeds with
exit code 0. Availability is classified from the runner's status line.
