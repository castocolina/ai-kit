---
name: ai-kit-spec-config
description: Sets up cross-AI reviewer config by detecting installed CLIs/models, asking which to use as reviewers and priority order, then writing review-spec.toml. Writes per-project ./.aikit/review-spec.toml by default (always announces the exact path), asks before updating an existing global config. Use when the user requests cross-AI review setup or when ai-kit-spec-review warns no config exists. Supports --check-only (report availability, no writes), --local (force local write without asking), and --global (force ~/.config/ai-kit/review-spec.toml directly).
---

## Your task

Set up (or refresh) `ai-kit-spec-review`'s cross-AI reviewer configuration.

### Step 0 — Locate `ai-kit-spec.py` and the CLI profiles

`ai-kit-spec.py` and its `references/cli-profiles/` live inside the
**`ai-kit-spec-review`** skill's own directory (a sibling of this skill, not
this skill's own directory, and not a top-level `tools/`/`references/` —
see `ai-kit-spec-review/SKILL.md`'s Step 0.7 point 0 for why).
Resolve them the identical way `ai-kit-spec-review/SKILL.md` itself resolves
these same two paths (its own Step 0.7 point 0) — same three candidates,
self-contained, no shared variable between the two skills — so both
agree on one procedure:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review" \
         "$(dirname "<absolute path to THIS SKILL.md>")/../ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
done
TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/ai-kit-spec.py"
CLI_PROFILES_DIR="$REVIEW_SPEC_SKILL_DIR/references/cli-profiles"
if [ -f "$TOOLS_PY" ]; then
  RUNTIMES_JSON="$(python3 "$TOOLS_PY" cache-path --kind runtimes)"
fi
printf '%s\n' "$TOOLS_PY" "$CLI_PROFILES_DIR" "$RUNTIMES_JSON"
```

(The third candidate is `ai-kit-spec-config`'s own sibling — matching
`SEEDS_DIR`'s own third candidate — since this skill's directory and
`ai-kit-spec-review`'s are installed alongside each other in every shape:
plugin, `~/.claude/skills`, or a direct dev checkout. `cache-path`
resolves the `${XDG_CACHE_HOME:-$HOME/.cache}`-aware path through
`ai-kit-spec.py`'s own `cache_runtimes_path` — the same call
`ai-kit-spec-review/SKILL.md` itself uses
— so both skills always agree on where this file lives.)

**Resolve this whole block once, in one `Bash` call, and record
`TOOLS_PY`/`CLI_PROFILES_DIR`/`RUNTIMES_JSON` from its `printf` output as
literal absolute paths — not shell environment variables.** Every `Bash`
tool call in this harness starts a fresh shell, so a variable assigned in
one call is gone by the next; every `$TOOLS_PY`/`$CLI_PROFILES_DIR`/
`$RUNTIMES_JSON` reference in Steps 1–3 below means "the literal path
captured here", substituted directly, exactly the way `ai-kit-spec-review/SKILL.md`'s
own `TOOLS_PY`/`RUN_TMP_DIR` work (its own Step 0.7 points 0/1) — this
skill has its own separate `AskUserQuestion` interaction (Step 2) between
this resolution and Step 3's write, guaranteeing at least one call
boundary in between. If `TOOLS_PY` does not exist at the resolved path,
stop and report: "ai-kit-spec-review's own `ai-kit-spec.py` module is missing —
this skill configures cross-AI review for `ai-kit-spec-review`, which must
already be installed."

## NEVER

- **Never infer a model's vendor from its name** — always call `infer-vendor` (training knowledge is stale, consistency matters).
- **Never hand-write a `command` template for a CLI the factory knows** — prefer `build-command` / `build-model-id` for known CLIs (the factory encodes verified quoting; hand-written is error-prone). Only hand-write for CLIs outside the registry when `build-command` reports "no command builder registered."
- **Never save a CLI reviewer entry without testing it via `check-reviewer` first** — catch auth/model/entitlement problems before persisting.
- **Never silently pre-filter model families based on your own judgment** — always let the user decide, informed by your research (user agency over paternalism).
- **Never paste a multi-provider CLI's raw model list ungrouped** — always run `group-models` first (raw lists can be hundreds of ids; grouping makes them readable).
- **Never write to the global config without asking** — unless `--global` or `--local` was explicitly passed (global changes affect all projects; default is local).
- **Never skip asking about native reviewer entries** — the only zero-external-dependency reviewer option, worth having available as a fallback (placed last in `policy.ladder`) even when the user primarily wants external CLI reviewers.
- **Never skip announcing the target path before asking reviewer questions** — user must know where config is headed from the start.
- **Never re-derive the write target at Step 3** — use what Step 2 already resolved and announced (consistency guarantee).

### Step 1 — Detect

```bash
python3 "$TOOLS_PY" detect-runtimes
python3 "$TOOLS_PY" detect-tools
```

Parse the printed JSON: for each CLI marked `"installed": true`, note its
path; for `opencode`, note its `models` list.

`detect-tools` prints `{"rg": bool, "sd": bool, "bat": bool, "eza": bool, "fd": bool,
"codegraph": bool}` — informational only, this step does not add new wizard questions.
When asking the user optional per-reviewer/per-executor questions later in the wizard,
mention which of these are present on this machine — this is the data
`ai-kit-spec-execute` (Plan 2/3) will need later; this step only surfaces it.

**If `--check-only` was passed**, report which CLIs are installed. Then
read the target config file (`~/.config/ai-kit/review-spec.toml` if
`--global` was passed, else `./.aikit/review-spec.toml` by default) and
note each `[[reviewers]]` entry's `key`/`cli` if it exists. (This is a
raw on-disk read only, not `cfg_resolve`'s merged view.) If any entries exist, probe their **quota availability** — the core
purpose of `--check-only` — using a throwaway path:
```bash
python3 "$TOOLS_PY" probe-quota --cwd "$(pwd)" --quota-path "$(mktemp)"
```
`probe-quota` has no `--local`/`--global` flag — it always runs the full
`cfg_resolve` merge, so output may include keys from both local and
global configs. Report each `key`'s `available` boolean only for keys
that also appeared in the raw-read listing above — drop any extra the
merge surfaced — so both parts describe the same set of reviewers.

Two edge cases: (1) if `--global` was passed but a local config with
`strategy = "local-only"` exists, the merge returns only local entries,
shadowing the global keys the raw read listed; (2) `probe-quota` only
probes keys reachable from `policy.ladder`. For any raw-read key with no
match in probe output, report `available: unknown (not probed — either
absent from policy.ladder or shadowed by local-only strategy)` rather
than silently dropping it or guessing.

This makes live probe calls to each configured CLI (same mechanism as
dispatch time), but "no writes" means nothing is persisted to real
`quota.json`/`review-spec.toml` locations — the throwaway path is
discarded. Then stop; do not save the runtimes snapshot, matching this
skill's `--check-only` contract.

**Otherwise**, persist the snapshot before continuing to Step 2:
```bash
python3 "$TOOLS_PY" detect-runtimes --save "$RUNTIMES_JSON"
```
(re-running detection here is cheap and keeps this step's logic linear —
`--save` persists via `cache_write_json`, so `ai-kit-spec-review` doesn't
have to re-detect next session.)

### Step 2 — Ask

This step gathers reviewer configuration through a series of prompts: starting with the write target (local vs. global), then asking which CLIs and models to register, resolving vendor details, building commands, testing them, and finally setting policy priorities and strategy options.

| I want to... | Go to |
|---|---|
| Decide where the config gets written | Step 2.1 |
| Pick which CLIs/models to register | Step 2.2 |
| Figure out a model's vendor | Step 2.3 |
| Build the actual command/model-id | Step 2.4 |
| Verify a candidate actually works | Step 2.5 |
| Tag a reviewer as UI/coding/planning-oriented | Step 2.6 |
| Register a native (no-CLI) reviewer | Step 2.7 |
| Set the priority/fallback order | Step 2.8 |

#### Step 2.1 — Resolve the write target

**Resolve the write target first, before asking anything else about reviewers.** Default is **local** (`./.aikit/review-spec.toml`) — a per-project config is the safer default since it can't silently affect other projects. `--global` forces `~/.config/ai-kit/review-spec.toml` directly, skipping the ask below. `--local` also forces local directly, skipping the ask (both flags are an explicit choice, so neither needs confirming). With **neither flag passed** (the common case): `Read` `~/.config/ai-kit/review-spec.toml` to check whether a global config already exists.
- If it does **not** exist, proceed with the local default silently — nothing would be overwritten either way, so asking would just be friction.
- If it **does** exist, use `AskUserQuestion` to ask explicitly before writing anywhere: "A global review-spec.toml already exists at `~/.config/ai-kit/review-spec.toml`. Write a new per-project config at `./.aikit/review-spec.toml` instead (recommended — doesn't touch the existing global config), or update the existing global config?" — with the local option first/default. Only proceed to overwrite the global file if the user explicitly picks that option here.

**Once the target is resolved, announce it immediately** — print "Writing to: `<resolved absolute path>`" before asking any of the reviewer questions below, so the user knows where this run's answers are headed from the start (not just in Step 4's closing report, which restates the same path after the write actually happens).

#### Step 2.2 — Pick which CLIs and models to register

For each installed CLI (beyond the current session's own runtime), use `AskUserQuestion` to ask whether the user wants it available as a cross-AI reviewer. For a multi-provider CLI (`opencode`, `cursor-agent`, or any future CLI `build_runtimes_snapshot` lists a `models` array for — this applies uniformly, not just to the two known today), additionally ask which of its listed models to register as reviewer entries.

**A multi-provider CLI's raw model list can be very long** (confirmed live: cursor-agent's catalog is ~200 ids — a handful of base model families each multiplied out by effort/thinking/fast-tier variants, e.g. `claude-opus-5-thinking-high-fast`). Never paste the raw list at the user as-is. Group it first:
```bash
python3 "$TOOLS_PY" group-models --runtimes-json "$RUNTIMES_JSON" --cli <id>
```
This prints `{"<family>": ["<variant-id>", ...], ...}` — one entry per base model family, each holding its own tier/effort/fast variants (the grouping is a plain suffix-stripping heuristic, not a quality judgment; an id it can't confidently collapse just becomes its own single-member family, which is fine). Present the **families**, not the raw ids, as the first choice — then let the user drill into a chosen family's variant list only if they want a specific tier rather than the default.

**This rule applies to single-provider CLIs too, not just a multi-provider CLI's grouped catalog above** — e.g. codex/grok have no `models` list to group at all, so an unfamiliar model id for them (its exact string shape, whether effort/tier belongs in the id or a separate flag) must still be researched the same way before it's proposed to the user; confirmed live 2026-08-28 that guessing here (`gpt-5.6-sol-high` instead of the real `gpt-5.6-sol`) produces a candidate that fails outright at Step 2.5's live test. **For any family/model name you don't confidently recognize, research it before asking the user to choose — do not guess or rely solely on training knowledge, which is very likely stale for this.** Frontier models and CLI catalogs change faster than any model's training cutoff; this instruction applies whenever this skill actually runs, for whichever CLIs and catalogs exist at that time — never assume a name from today's session (or from this doc's own examples) is still current. Use `WebSearch` to find out, for an unfamiliar family: how recent it is relative to the vendor's other offerings (so the user can tell a superseded generation from the current one), and — where discoverable — whether it's positioned as a reasoning/planning-oriented model (better suited for analyzing or authoring specs/plans) or an instruction-following/tool-use-oriented model (better suited for well-scoped execution work with clear direction) — this maps to the `strength` question below, so raise it there informed by what you found rather than guessing blind. Summarize what you found for the user in a line or two per unfamiliar family before they choose — do not silently pre-filter families out on your own judgment; the user makes the final call on what's current/worth keeping, informed by your research.

**Before finalizing a CLI outside codegraph support (today: `grok`), check for a
codegraph-capable alternative.** For each model being registered on such a CLI, run:
```bash
python3 "$TOOLS_PY" check-codegraph-alternative --cli <id> --model <model-id> \
  --runtimes-json "$RUNTIMES_JSON"
```
When `alternative_cli` is non-null, tell the user in one line before they confirm: `"<model> is
also reachable via <alternative_cli>, which supports codegraph_explore (grok CLI does not) —
consider registering it through <alternative_cli> instead for grounding-heavy review/execute
work."` This is informational only (best-effort substring match, per
`find_codegraph_alternative`'s own docstring) — the user still makes the final call; never
silently substitute the CLI or drop the original option.


#### Step 2.3 — Resolve vendor attribution

**Vendor attribution is deterministic — never infer it from the model name yourself.** For every model id (whether picked from a multi-provider CLI's list or typed by the user for a single-provider CLI), resolve `vendor` by calling:
```bash
python3 "$TOOLS_PY" infer-vendor --model <model-id>
```
When this prints `{"vendor": null}` (no known prefix — e.g. an `ollama-cloud/*` id, or a genuinely new model this table hasn't seen yet), ask the user directly for the real vendor rather than guessing — this is the one case a human still has to supply the answer, and it should be rare (the table in `ai-kit-spec.py`'s `_MODEL_VENDOR_PREFIXES` already covers every model family confirmed live in the CLI profiles).

#### Step 2.4 — Build the command and model id

For each CLI the user wants, read its profile under `$CLI_PROFILES_DIR/<id>.md` for anything CLI-specific this step doesn't already cover (prerequisites, known quirks, plan/entitlement gating — `cursor-agent.md` documents several). **Prefer the factory subcommands below over hand-writing a `command` template or a bracket-parameter model string** — for the CLIs `build_reviewer_command`/`build_reviewer_model_id` already know (`ai-kit-spec.py`'s `_COMMAND_BUILDERS` registry — currently codex, claude, grok, opencode, cursor-agent), the factory encodes verified quoting a hand-written template is easy to get wrong:
```bash
python3 "$TOOLS_PY" build-command --cli <id> \
  [--effort <e>] [--service-tier <t>] [--mode plan|ask]
```
**codex's `model` field must be the BARE model id — never suffix an effort/tier tag onto it.** Confirmed live 2026-08-29: `codex exec -m gpt-5.6-sol-high` is REJECTED outright ("The 'gpt-5.6-sol-high' model is not supported..."); the correct pair is `model = "gpt-5.6-sol"` with `effort = "high"` passed separately to `build-command` above (codex's own `-c model_reasoning_effort` flag carries it, not the model string). This is the opposite convention from cursor-agent below, where effort/fast/context ARE baked into the model-id string — do not carry that pattern over to codex. codex also has no `models`/`list-models` subcommand to cross-check an id against (confirmed via `codex --help`), so there is no live catalog check possible here; if the exact current model id isn't already confirmed from this session's own detection/research, treat it as unfamiliar and research it per Step 2.2's rule before proposing it to the user, rather than typing a remembered id from training knowledge.

Ask the user for `effort`/`service_tier` (codex) or `mode` (cursor-agent, default `plan`) only when that CLI's profile documents the knob — most CLIs take neither, and `build-command` silently ignores params a given CLI's builder doesn't use. For `cursor-agent` specifically, effort/fast/context are encoded in the model id itself, not the command — ask the user for any of those they want, then:
```bash
python3 "$TOOLS_PY" build-model-id --cli cursor-agent --base-model <id> \
  [--effort <e>] [--fast true|false] [--context <c>]
```
and use the printed id as this entry's `model` field (unchanged from the plain id when no overrides were given).

**The factory is a convenience for known CLIs, not the only way to register a reviewer.** `build-command` fails with "no command builder registered" for any CLI outside that registry — a CLI this catalog of profiles hasn't caught up with yet, a brand-new provider, or a fully custom local script the user wants to wire in. `review-spec.toml`'s `command` field has always accepted a plain hand-written template with just `{model}`/`{prompt}` as placeholders (`render_reviewer_command` fills both at dispatch time, exactly the same way regardless of whether the template came from a builder or was typed by hand) — when `build-command` doesn't recognize a CLI, fall back to asking the user for that raw template directly instead of blocking. This is the intended open escape hatch: any CLI/script that can be invoked non-interactively with a model and a prompt can become a reviewer entry, whether or not this design has a named builder for it yet.

#### Step 2.5 — Test the candidate before saving

**Before finalizing any CLI entry, actually test it — don't just trust that the model id and command work.** Run:
```bash
python3 "$TOOLS_PY" check-reviewer --key <candidate-key> --model <model-id> \
  --vendor <vendor> --cli <id> --command "<built command>" \
  [--extra-json '<json>']
```
This makes one real call through the CLI (the same mechanism `probe-quota` uses later) and prints `{"available": bool, "detail": "..."}`. If `available` is `false`, show the user the `detail` message verbatim (it is the CLI's own real error text — e.g. a bad model id, an auth problem, or a plan/entitlement gate like `cursor-agent`'s Free-plan restriction) and ask whether to save the entry anyway (it may just be a temporary quota exhaustion, worth keeping for later) or drop it.

**If the profile's `read_only:` field says `unconfirmed`**, print one line before writing that entry: "Note: `<id>` has no confirmed read-only invocation — this reviewer runs with the CLI's normal write permissions against your working tree." — inform, don't block; the user is choosing to accept that CLI's default risk.

#### Step 2.6 — Ask about the optional strength attribute

**Also ask, for every entry (CLI or native), an optional `strength`**: `"ui"`, `"coding"`, `"planning"`, or left unset — free text otherwise, not validated. This is informational only — captured in `review-spec.toml` for a human (or a future version of this design) to read, but **not yet consumed by any resolution logic today** (`resolve_reviewers`/`resolve_ladder_pick` ignore it completely). Tell the user this plainly if they ask what it does: it doesn't change dispatch behavior yet, it just gets saved.

#### Step 2.7 — Ask about native reviewer entries

**Also ask, explicitly — do not skip this**: whether to register one or more **native** (`cli`-omitted) reviewer entries — dispatched via whatever runtime is hosting *this* session, not any one specific model or vendor. Today that host is Claude Code, whose own dispatch mechanism is the `Agent` tool's four tier aliases (`sonnet`/`opus`/`haiku`/`fable`) — but "native" itself is a runtime-agnostic concept: the same config shape (`cli` omitted) is what a future opencode-hosted or Antigravity-hosted run of this same skill would use for *its* own current-session model, whatever that host's own alias/selection mechanism turns out to be. Don't imply in prose or example keys that native means "Claude" or "opus" specifically — call it the current-runtime/native entry, and let its `key` describe the tier (e.g. `native-primary`, `native-fallback`), not the vendor.

Worth asking regardless of `policy.mode`, since it's the only zero-external-dependency reviewer option available (never rate-limited/API-gated the way an external CLI can be) — useful as either a primary pick or a pure fallback, depending on where the user places it in `policy.ladder` at Step 2.8. **A native entry is never automatically prioritized over external ones** — `resolve_reviewers` (`ai-kit-spec.py`) treats every ladder entry identically regardless of native/external; only its position in `policy.ladder` decides priority, and quota/availability failures (never native-vs-external status) decide fallback (changed 2026-08-29 — an earlier design gave native entries an automatic guaranteed-baseline slot in `double` mode regardless of ladder position; a real config hit this and got a silently reordered ladder, so it was removed). If the user wants a native entry as pure fallback, place it LAST in the ladder order at Step 2.8. For each native entry the user wants **on this Claude-Code-hosted run**, `model` must be one of the four `Agent`-tool aliases (`sonnet`/`opus`/`haiku`/`fable`), never a full model id like `"opus-5"`; ask the user to pick one of those four rather than typing a version string. (A different host runtime would substitute its own alias set here — this constraint is Claude Code's dispatch mechanism, not a property of "native" itself.)

#### Step 2.8 — Set policy.mode, policy.ladder order, and strategy

Then ask: `policy.mode` (`single` or `double`) and the `policy.ladder` order — this is the **priority fallback list**: the order reviewers are tried in, first available wins the primary slot (`double` mode also seats an independent secondary). Default the order to the order the user answered the per-CLI and native-entry questions in, combined, but let them reorder; once confirmed, echo it back as a numbered list so the user sees the exact fallback order before it's written (`cfg_render_toml` also writes this same list as a `#`-comment above `[policy]` in the file itself, so it stays readable to anyone opening `review-spec.toml` directly later, not just at setup time). If the resolved write target (above) is **local**, also ask whether this local config should be `local-only` or the default `global-merge` — set the JSON config's top-level `strategy` key to `"local-only"` if so (`cfg_render_toml` renders it as a bare `strategy = "..."` line at the top of the file); omit the key entirely for the default (global-merge applies, no line needed).

The `strategy` question does not apply when the resolved target is global — `strategy` only ever describes how a *local* config relates to the global one.

**When at least one external-CLI reviewer is being registered** (native-only configs have no
subprocess to time out), also ask whether to customize `policy.timeout_tiers` from its default
`[600, 1200, 1800]` — 10, then 20, then 30 minutes, each tier a fresh attempt after the previous
one is killed, so the tiers are **cumulative**: the worst case is their sum (60 minutes), not a
30-minute ceiling. Most users should keep the default; only ask this as an offer, don't require
an answer. If the user wants a specific reviewer entry to use different tiers (e.g. a known-slow
`effort=high` combination), that goes in a flat `timeout_tiers = [900, 1800]` key directly on
that `[[reviewers]]` entry, instead of the policy-wide default. It must be a **flat** key on the
entry — this config format has no nested-object support (`extra` is derived at read time from
every `[[reviewers]]` key the schema doesn't recognize, and the TOML writer has no dict branch),
so a nested `extra = { timeout_tiers = [...] }` would be written out as a string and silently
fall back to the policy default.

### Step 3 — Write

Build the JSON shape `skills/ai-kit-spec-review/ai-kit-spec.py`'s `render-toml` subcommand
expects (`{"strategy": "...", "policy": {...}, "reviewers": [...]}` — the
`strategy` key only when Step 2 asked for `local-only`), write it to a
temp JSON file, then let `--out` do the write directly (via
`cfg_write_toml`, creating parent dirs as needed) rather than piping
stdout through a second write yourself:

```bash
python3 "$TOOLS_PY" render-toml --json-config <temp.json> --out <target path>
```

`<target path>` is the write target Step 2 resolved and already
announced — `./.aikit/review-spec.toml` by default (or explicitly via
`--local`), `~/.config/ai-kit/review-spec.toml` only via `--global` or
because the user picked "update the existing global config" at Step 2's
ask. Never re-derive the target here independently of what Step 2
already resolved and told the user. (The runtimes snapshot was already
persisted in Step 1 via `--save` — no separate write needed here.)

### Step 4 — Report

Print a summary confirming the write, always including the exact
absolute path (repeat it even though Step 2 already announced it — this
is the confirmation that the write actually happened, not just the plan
to do it): "Config written to: `<target path>`." Then the resolved
`policy.mode`, and the **priority fallback order** as its own explicit
numbered list (the same list already echoed back during Step 2, now
confirmed as written) — e.g.:
```
Priority fallback order:
  1. codex-gpt
  2. sonnet-native
  3. grok-flagship
```
not folded into a single vague sentence about "reviewers configured in
some order" — the point of this report is that the user can see the
exact fallback sequence without having to open the file.
