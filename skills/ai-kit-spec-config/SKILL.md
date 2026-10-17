---
name: ai-kit-spec-config
description: Cross-AI reviewer config setup — detects installed CLIs/models, asks which to use as reviewers and in what priority order, then writes review-spec.toml. Writes per-project ./.aikit/review-spec.toml by default (always announces the exact path), asks before updating an existing global config. Use when the user requests cross-AI review setup or when ai-kit-spec-review warns no config exists. Supports --check-only (report availability, no writes), --local (force local write without asking), and --global (force ~/.config/ai-kit/review-spec.toml directly).
---

## Your task

Set up (or refresh) `ai-kit-spec-review`'s cross-AI reviewer configuration.

This skill is a **Process** (a fixed Step 0→4 sequence: locate, detect,
ask, write, report) executed with **Tool-level rigor** at each step — every
CLI call, model id, and TOML field goes through the `ai-kit-spec.py`
factory subcommands rather than being hand-typed, because a wrong quote or
guessed model id fails silently or errors out at dispatch time far from
where the mistake was made.

**Host tools.** `Bash` below means the host's shell tool; `AskUserQuestion` (with
`multiSelect`) means its structured-question tool; `Read` means its file reader. On a host
without a structured-question tool, ask in plain conversation instead: number the options,
accept several numbers where a step says `multiSelect: true`, and wait for the answer before
the next step. Never answer a question on the user's behalf because no tool exists for it.

### Step 0 — Locate `ai-kit-spec.py` and the CLI profiles

`ai-kit-spec.py` and its `references/cli-profiles/` live inside the sibling
**`ai-kit-spec-review`** skill's directory (see its Step 0.7 point 0 for why). Resolve them
with the same candidate order that skill uses, self-contained:

```bash
for d in "$(dirname "<absolute path to THIS SKILL.md>")/../ai-kit-spec-review" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
done
TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/ai-kit-spec.py"
CLI_PROFILES_DIR="$REVIEW_SPEC_SKILL_DIR/references/cli-profiles"
if [ -f "$TOOLS_PY" ]; then
  RUNTIMES_JSON="$(python3 "$TOOLS_PY" cache-path --kind runtimes)"
  SCRATCH="$(mktemp -d -t ai-kit-spec-config-XXXXXX)"
fi
printf '%s\n' "$TOOLS_PY" "$CLI_PROFILES_DIR" "$RUNTIMES_JSON" "$SCRATCH"
```

The sibling is tried first so the module that runs is the one installed beside the
`SKILL.md` you are following, not an older copy elsewhere. `SCRATCH` is this run's private
scratch directory (mode 0700, unique per run): every temporary file below goes inside it,
never at a fixed `/tmp/<name>` path another run could share or pre-plant, and Step 4 (or the
`--check-only` stop) removes it. `cache-path` resolves the `${XDG_CACHE_HOME:-$HOME/.cache}`-aware
runtimes path through `ai-kit-spec.py` itself, so both skills agree on where it lives.

**Resolve this whole block once, in one `Bash` call, and record its four printed lines as
literal absolute paths — not shell environment variables.** Every `Bash` call starts a fresh
shell, so every `$TOOLS_PY`/`$CLI_PROFILES_DIR`/`$RUNTIMES_JSON`/`$SCRATCH` below means "the
literal path captured here", substituted directly. If `TOOLS_PY` does not exist at the
resolved path, stop and report: "ai-kit-spec-review's own `ai-kit-spec.py` module is missing —
this skill configures cross-AI review for `ai-kit-spec-review`, which must already be
installed."

## NEVER

- **Never infer a model's vendor from its name** — always call `infer-vendor` (training knowledge is stale, consistency matters).
- **Never hand-write a `command` for a runtime the runner knows** — a table runtime stores `runtime` and `model` (plus its knobs); the runner builds the argv. Only a CLI outside the runner table gets a custom `command`.
- **Never save a CLI reviewer entry without testing it via `check-reviewer` first** — catch auth/model/entitlement problems before persisting.
- **Never silently pre-filter model families based on your own judgment** — always let the user decide, informed by your research (user agency over paternalism).
- **Never paste a multi-provider CLI's raw model list ungrouped** — always run `group-models` first (raw lists can be hundreds of ids; grouping makes them readable).
- **Never write to the global config without asking** — unless `--global` or `--local` was explicitly passed (global changes affect all projects; default is local).
- **Never skip asking about session-default reviewer entries** — the only
  zero-external-dependency reviewer option, worth having available as a fallback (placed last
  in `policy.ladder`) even when the user primarily wants external CLI reviewers.
- **Never omit or soften `(running under: unknown)`** — when `detect-current-runtime` returns
  `"unknown"`, render that annotation literally in Step 2.7's session-default ask. An
  `unknown` host gets a session-default entry (no `runtime`, `model = ""`), never a guessed
  runtime. Dropping the annotation or rewording it to "not detected" is the same silent-omit
  as leaving `purpose` unset on a brand-new entry.
- **Never skip announcing the target path before asking reviewer questions** — user must know where config is headed from the start.
- **Never re-derive the write target at Step 3** — use what Step 2 already resolved and announced (consistency guarantee).
- **Never translate literal identifiers** — `purpose` values (REVIEW/EXECUTE), model ids, catalog keys, CLI/runtime names, and field labels stay in their literal, invariant form regardless of what language the rest of this conversation is in. Narrate and explain in the user's own language, but never garble an identifier a user or this skill needs to match against config values by translating it.
- **Never run `trust-local` (the trusting form) without the user's explicit yes** — not even for the `./.aikit/review-spec.toml` this wizard just wrote. Show `trust-local --cwd <project root> --show` first so the user consents after seeing each reviewer's argv; until then the file stays inactive.

### Step 1 — Detect

```bash
python3 "$TOOLS_PY" detect-runtimes
python3 "$TOOLS_PY" detect-tools
```

Parse the printed JSON: for each CLI marked `"installed": true`, note its
path, plus its `models` list when present (pi, opencode, cursor, codex and claude carry
one, grok never does; a CLI whose enumeration failed degrades to no list).

`detect-tools` prints `{"rg": bool, "sd": bool, "bat": bool, "eza": bool, "fd": bool,
"codegraph": bool}` — informational only, this step does not add new wizard questions.
When asking the user optional per-reviewer/per-executor questions later in the wizard,
mention which of these are present on this machine — this is the data
`ai-kit-spec-execute` (Plan 2/3) will need later; this step only surfaces it.

**If `--check-only` was passed**, report which CLIs are installed. Then
read the target config file (`~/.config/ai-kit/review-spec.toml` if
`--global` was passed, else `./.aikit/review-spec.toml` by default) and
note each `[[reviewers]]` entry's `key`/`runtime` (or legacy `cli`) if it exists. (This is a
raw on-disk read only, not `cfg_resolve`'s merged view.) If any entries exist, probe their **quota availability** — the core
purpose of `--check-only` — using a throwaway path:
```bash
python3 "$TOOLS_PY" probe-quota --cwd "$(pwd)" --no-save-runtimes --quota-path "$SCRATCH/quota.json"
```
`probe-quota` has no `--local`/`--global` flag — it always runs the full
`cfg_resolve` merge, so output may include keys from both local and
global configs. Report each `key`'s `available` boolean only for keys
that also appeared in the raw-read listing above — drop any extra the
merge surfaced — so both parts describe the same set of reviewers.

Three edge cases: (1) if `--global` was passed but a local config with
`strategy = "local-only"` exists, the merge returns only local entries,
shadowing the global keys the raw read listed; (2) `probe-quota` only
probes keys reachable from `policy.ladder`; (3) an untrusted local file is
ignored entirely (stderr prints `ignoring untrusted project-local config`),
so none of its keys are probed. For any raw-read key with no match in probe
output, report `available: unknown (not probed — absent from policy.ladder,
shadowed by local-only strategy, or the local config is untrusted)` rather
than silently dropping it or guessing. When the untrusted line appears, relay
it and print the `trust-local --cwd <project root> --show` command for the
user to run later — `--check-only` never runs the trusting `trust-local`
form, because that writes a trust record.

This makes live probe calls to each configured CLI (same mechanism as
dispatch time), but "no writes" means nothing is persisted to ai-kit's
caches or config: the throwaway `--quota-path` keeps quota rows out of the
real `quota.json`, and `--no-save-runtimes` keeps `probe-quota`'s routing
step from writing the runtimes cache (a cold or stale cache is rebuilt in
memory only, and a targeted refresh is never written back). Then
`rm -rf "$SCRATCH"` and stop; do not save the runtimes snapshot, matching this
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

Before registering any candidate, weigh it against two judgment calls, not
just the mechanics below: **is this CLI's quota reliable enough to be a
primary pick, or only worth keeping as a fallback?** (a CLI with a tight
free-tier limit belongs low in the ladder, not first) — and **does this
model's strength (planning vs. execution-oriented, per Step 2.2's
purpose-weighted ranking) actually match what the user reviews most?** Registering every
available CLI/model indiscriminately produces a bloated, hard-to-reason-about
ladder; the goal is a config the user can predict the fallback behavior of
at a glance.

| I want to... | Go to |
|---|---|
| Decide where the config gets written | Step 2.1 |
| Pick which CLIs/models to register | Step 2.2 |
| Figure out a model's vendor | Step 2.3 |
| Build the actual command/model-id | Step 2.4 |
| Verify a candidate actually works | Step 2.5 |
| Tag a reviewer as UI/coding/planning-oriented | Step 2.6 |
| Register a session-default (no-runtime) reviewer | Step 2.7 |
| Set the priority/fallback order | Step 2.8 |

#### Step 2.1 — Resolve the write target

**Resolve the write target first, before asking anything else about reviewers.** Default is **local** (`./.aikit/review-spec.toml`) — a per-project config is the safer default since it can't silently affect other projects. `--global` forces `~/.config/ai-kit/review-spec.toml` directly, skipping the ask below. `--local` also forces local directly, skipping the ask (both flags are an explicit choice, so neither needs confirming). With **neither flag passed** (the common case): `Read` `~/.config/ai-kit/review-spec.toml` to check whether a global config already exists.
- If it does **not** exist, proceed with the local default silently — nothing would be overwritten either way, so asking would just be friction.
- If it **does** exist, use `AskUserQuestion` to ask explicitly before writing anywhere: "A global review-spec.toml already exists at `~/.config/ai-kit/review-spec.toml`. Write a new per-project config at `./.aikit/review-spec.toml` instead (recommended — doesn't touch the existing global config), or update the existing global config?" — with the local option first/default. Only proceed to overwrite the global file if the user explicitly picks that option here.

**Once the target is resolved, announce it immediately** — print "Writing to: `<resolved absolute path>`" before asking any of the reviewer questions below, so the user knows where this run's answers are headed from the start (not just in Step 4's closing report, which restates the same path after the write actually happens).

#### Step 2.2 — Pick which CLIs and models to register

For every CLI the user wants to consider (from Step 1's detection), build the ranked
candidate list via the model-discovery catalog rather than guessing or searching per model.
**Order matters here: unmatched candidates are researched and confirmed BEFORE anything is
ranked** — an unconfirmed guess must never appear in a ranked list the user is about to trust.

For each installed CLI from Step 1, the current session's own runtime included, use
`AskUserQuestion` to ask whether the user wants it available as a cross-AI reviewer at
all — registering every installed CLI indiscriminately is exactly what this step's own
opening framing at the top of Step 2 warns against. A pair on the host's own runtime is a
real option: routing runs it as a subprocess whenever the host cannot select that model per
call (a pi session can register another pi model this way). Only Claude Code's four aliases
on a Claude Code host run natively, and those are Step 2.7's session-default ask, not this
catalog flow.

**Do NOT load** `references/cli-model-selection.md` when Step 1 found no installed CLI,
or the user declined every installed CLI at the ask above. Session-default entries never go
through this catalog/ranking flow — continue at Step 2.3/2.7.

**MANDATORY — READ ENTIRE FILE:** when the user kept at least one CLI, before grouping
models, calling `fetch-model-catalog`, ranking, or presenting candidates, read
[`references/cli-model-selection.md`](references/cli-model-selection.md) completely
from start to finish. **NEVER set any range limits when reading this file.** It is the
8-item procedure (group → extra-candidate → fetch → unmatched-confirm → rank → present
→ codegraph-alternative → heuristic-confirm) plus the exact command templates. Skipping
it reproduces live landmines this wizard already hit: guessing a codex id
(`gpt-5.6-sol-high` instead of `gpt-5.6-sol`), dumping a ~200-id cursor list
ungrouped, ranking before unmatched confirmation, and silently dropping every
single-provider-CLI candidate by rebuilding `discovered` from `$RUNTIMES_JSON` alone.

#### Step 2.3 — Resolve vendor attribution

**Vendor attribution is deterministic — never infer it from the model name yourself.** For every model id (whether picked from a multi-provider CLI's list or typed by the user for a single-provider CLI), resolve `vendor` by calling:
```bash
python3 "$TOOLS_PY" infer-vendor --model <model-id>
```
When this prints `{"vendor": null}` (no known prefix — e.g. an `ollama-cloud/*` id, or a genuinely new model this table hasn't seen yet), ask the user directly for the real vendor rather than guessing — this is the one case a human still has to supply the answer, and it should be rare (the table in `ai-kit-spec.py`'s `_MODEL_VENDOR_PREFIXES` already covers every model family confirmed live in the CLI profiles).

#### Step 2.4 — Store the pair and its runner knobs

For each runtime the user wants, read its profile under `$CLI_PROFILES_DIR/<id>.md` for
anything runtime-specific this step doesn't already cover (prerequisites, known quirks,
plan/entitlement gating — `cursor.md` documents several). **Load only the profile(s) for
runtimes actually selected at Step 2.2 — do NOT read the whole `$CLI_PROFILES_DIR` directory
or preemptively load profiles for runtimes the user declined.** Each profile is a few KB of
quirks relevant to exactly one runtime; loading unselected ones adds noise without informing
any decision in this run. **When a selected runtime has no profile file** (pi has none
today), say so in one line and continue: the runner table, `build-command --runtime <id>`'s
preview and Step 2.5's live test are then the only sources — never invent quirks for it.

**A runtime the runner knows stores no `command`.** Store the pair: `runtime` and `model`,
plus the knobs that runtime takes as entry fields (`effort` and `service_tier` for codex,
`cursor_mode` for cursor, default `ask`). The runner builds the argv from those fields at
dispatch. `build-command --runtime <id>` is an optional preview of that argv — it prints the
argv and says that review-spec.toml stores `runtime` and `model`; do not store its output as a
`command`.
```bash
python3 "$TOOLS_PY" build-command --runtime <id> \
  [--effort <e>] [--service-tier <t>] [--mode plan|ask]
```
**codex's `model` field must be the BARE model id — never suffix an effort/tier tag onto it.**
Confirmed live 2026-08-29: `codex exec -m gpt-5.6-sol-high` is REJECTED outright ("The
'gpt-5.6-sol-high' model is not supported..."); the correct pair is `model = "gpt-5.6-sol"`
with `effort = "high"` stored on the entry (the runner passes it as `--codex-effort`, not in
the model string). This is the opposite convention from cursor below, where effort/fast/context
ARE baked into the model-id string — do not carry that pattern over to codex. codex has no
`models`/`list-models` subcommand (confirmed via `codex --help`), but `detect-runtimes`
enumerates its user-selectable models from the real binary's `codex debug models` output
(entries with `visibility: "list"` only) into `clis.codex.models` — when `$RUNTIMES_JSON`
carries that list, pick the model id from it. When it does not (an older codex without
`debug models`, or an enumeration that failed and degraded to no list), treat the exact current
model id as unfamiliar and research it per Step 2.2's rule before proposing it to the user,
rather than typing a remembered id from training knowledge.

For `cursor` specifically, effort/fast/context are encoded in the model id itself, not a runner
flag — ask the user for any of those they want, then:
```bash
python3 "$TOOLS_PY" build-model-id --runtime cursor --base-model <id> \
  [--effort <e>] [--fast true|false] [--context <c>]
```
and use the printed id as this entry's `model` field (unchanged from the plain id when no
overrides were given). `build-model-id` stays for these cursor bracket ids.

**Grok has no runner formula.** `build-command --runtime grok` prints the command to store on a
custom entry with no `runtime`, trust-gated like any custom command. Any other CLI outside the
runner table — a CLI this catalog of profiles hasn't caught up with yet, a brand-new provider,
or a fully custom local script — is that same escape hatch: a custom entry with a hand-written
`command` and no `runtime`. `review-spec.toml`'s `command` field accepts a plain template with
just `{model}`/`{prompt}` as placeholders. Hand-written templates are split into argv the way a
shell splits words; `{model}`, `{prompt}`, and any `extra` fields each fill a whole argument
(`{prompt}` needs no quoting). Shell operators (`;`, `|`, `&&`, `>`), `$` expansions, and
backticks are rejected with an error naming the reviewer — wrap a pipeline in a script and
register the script. This is the intended open escape hatch: any CLI/script that can be invoked
non-interactively with a model and a prompt can become a reviewer entry.

#### Step 2.5 — Test the pair before saving

**Before finalizing any table-runtime entry, actually test the pair — don't just trust that
the model id works.** Run:
```bash
python3 "$TOOLS_PY" check-reviewer --key <candidate-key> --model <model-id> \
  --vendor <vendor> --runtime <id> \
  [--extra-json '<json>']
```
A custom entry (no `runtime`) is tested the same way with `--command '<template>'` instead of
`--runtime`. This makes one real call through the runner or the custom launcher (the same
mechanism `probe-quota` uses later) and prints `{"available": bool, "detail": "..."}`. If
`available` is `false`, show the user the `detail` message verbatim (it is the CLI's own real
error text — e.g. a bad model id, an auth problem, or a plan/entitlement gate like `cursor`'s
Free-plan restriction) and ask whether to save the entry anyway (it may just be a temporary
quota exhaustion, worth keeping for later) or drop it.

**If the profile's `read_only:` field says `unconfirmed`**, print one line before writing that entry: "Note: `<id>` has no confirmed read-only invocation — this reviewer runs with the CLI's normal write permissions against your working tree." — inform, don't block; the user is choosing to accept that CLI's default risk.

#### Step 2.6 — Ask about the optional strength attribute; `purpose` comes from Step 2.2

**Also ask, for every entry (a pair or the session default), an optional `strength`**: `"ui"`,
`"coding"`, `"planning"`, or left unset — free text otherwise, not validated. This is
informational only — captured in `review-spec.toml` for a human (or a future version of this
design) to read, but **not yet consumed by any resolution logic today**
(`resolve_reviewers`/`resolve_ladder_pick` ignore it completely). Tell the user this plainly if
they ask what it does: it doesn't change dispatch behavior yet, it just gets saved.

**`purpose` is NOT asked here** — it was already captured at Step 2.2 (which ranked list(s),
REVIEW/EXECUTE/both, the user confirmed each candidate from). Carry that value forward unchanged
into this entry's fields; do not re-ask, and do not silently drop it.

#### Step 2.7 — Ask about the session default

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively.

Before asking, detect which runtime is hosting *this* session (never cached, always live):
```bash
python3 "$TOOLS_PY" detect-current-runtime
```
Capture the printed `host` (`pi` / `opencode` / `cursor` / `codex` / `claude` / `unknown`).
That value is shown in the prompt below and decides the entry's shape at Step 3. When several
CLIs are nested, the innermost one wins (pi > opencode > cursor > codex > claude), so a codex or
opencode session started from Claude Code records that CLI, not claude.

**Also ask, explicitly — do not skip this**: whether to register one or more entries that this
host runs itself (running under: <host>), not any one specific vendor. Substitute the captured
value into that annotation verbatim. When `detect-current-runtime` returns `"unknown"`, still
render `(running under: unknown)` literally — never omitted, never softened to "not detected"
or dropped from the prompt. Let the entry's `key` describe its place in the ladder (e.g.
`session-primary`, `session-fallback`), not a vendor.

Worth asking regardless of `policy.mode`, since it's the only zero-external-dependency reviewer
option available (never rate-limited/API-gated the way an external CLI can be) — useful as
either a primary pick or a pure fallback, depending on where the user places it in
`policy.ladder` at Step 2.8. **A host-run entry is never automatically prioritized over a
subprocess one** — `resolve_reviewers` (`ai-kit-spec.py`) treats every ladder entry
identically; only its position in `policy.ladder` decides priority, and quota/availability
failures decide fallback (changed 2026-08-29 — an earlier design gave host-run entries an
automatic guaranteed-baseline slot in `double` mode regardless of ladder position; a real
config hit this and got a silently reordered ladder, so it was removed). If the user wants one
as pure fallback, place it LAST in the ladder order at Step 2.8. **When the captured `host` is
`"claude"`**, the entry is the pair `runtime = "claude"` plus one of the four aliases
(`sonnet`/`opus`/`haiku`/`fable`), never a full model id like `"opus-5"`; ask the user to pick
one of those four rather than typing a version string. On any other host, or `unknown`, the
entry is the session default (no `runtime`, `model = ""`), because only Claude Code's aliases
are verified per-call selectable today (Phases 20-22 extend this).

**Also ask, for each such entry, the same `purpose` question Step 2.2 answers for ranked
candidates**: review, execute, or both? (`"review"` | `"execute"` | `"both"`.) A
session-default entry never goes through Step 2.2's catalog/ranking flow — there is no model id
to look up — so without this question it would get no `purpose` at all, and the consumer side
reads an absent `purpose` as "matches both review and execute": an assumption that must be a
deliberate, documented legacy-compat default, never an accident of how a brand-new entry
happened to get written. Carry the answer into this entry's `purpose` field at Step 3's write,
exactly like a Step 2.2-sourced entry — never leave it unset for a newly-registered one. Carry
the captured host into the entry as described above — never silently omitted (D-04).

#### Step 2.8 — Set policy.mode, policy.ladder order, and strategy

Then ask: `policy.mode` (`single` or `double`) and the `policy.ladder` order — this is the
**priority fallback list**: the order reviewers are tried in, first available wins the primary
slot (`double` mode also seats an independent secondary). Default the order to the order the
user answered the per-runtime and session-default questions in, combined, but let them reorder;
once confirmed, echo it back as a numbered list so the user sees the exact fallback order
before it's written (`cfg_render_toml` also writes this same list as a `#`-comment above
`[policy]` in the file itself, so it stays readable to anyone opening `review-spec.toml`
directly later, not just at setup time). If the resolved write target (above) is **local**,
also ask whether this local config should be `local-only` or the default `global-merge` — set
the JSON config's top-level `strategy` key to `"local-only"` if so (`cfg_render_toml` renders
it as a bare `strategy = "..."` line at the top of the file); omit the key entirely for the
default (global-merge applies, no line needed).

The `strategy` question does not apply when the resolved target is global — `strategy` only
ever describes how a *local* config relates to the global one.

**When at least one subprocess reviewer is being registered** (a session-default-only config has no
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
`strategy` key only when Step 2 asked for `local-only`). **Each object in
`reviewers` now also carries `purpose` (`"review"`/`"execute"`/`"both"`, from
Step 2.2 for a ranked pair or Step 2.7 for a session-default one — every entry
this wizard newly registers gets an explicit `purpose`; absent `purpose` is
reserved for a pre-migration entry this run is merely carrying forward
unchanged, never for a brand-new one).
Every entry carries `runtime` and `model` (or neither, for the session default);
`command` appears only on a custom entry for a CLI outside the table or a
hand-tuned command; `render-toml` rejects anything else and prints why. Also
`is_router`/`fallback_quota` when Step 2.2/2.7 confirmed either as `true`**
(omit when `false`/unknown rather than writing a redundant `false` for every
entry — the consumer side already treats an absent field as "no preference,"
exactly like today's `task_affinity`; that fallback exists for legacy
compatibility, not as this wizard's normal path for a new entry). Write it to
`$SCRATCH/config.json`, then let `--out` do the write directly (atomic, creating
parent dirs as needed) rather than piping
stdout through a second write yourself:

```bash
python3 "$TOOLS_PY" render-toml --json-config "$SCRATCH/config.json" --out <target path> \
  > "$SCRATCH/rendered.toml" 2> "$SCRATCH/render-toml-stderr.txt"
echo "render-toml exit $?"
```

`<target path>` is the write target Step 2 resolved and already
announced — `./.aikit/review-spec.toml` by default (or explicitly via
`--local`), `~/.config/ai-kit/review-spec.toml` only via `--global` or
because the user picked "update the existing global config" at Step 2's
ask. Never re-derive the target here independently of what Step 2
already resolved and told the user. (The runtimes snapshot was already
persisted in Step 1 via `--save` — no separate write needed here.)
**Capture stderr to `$SCRATCH/render-toml-stderr.txt`** — `cfg_render_toml`
prints a `WARNING:` line there for every `[[reviewers]]` entry it
rejected-and-dropped instead of writing (e.g. a malformed entry), and
this is the ONLY place that warning is ever emitted — Step 4 below reads
this file to decide whether to surface it. `$SCRATCH/rendered.toml` holds
the exact bytes written.

### Step 4 — Report

**First, check the printed exit status.** Anything but `render-toml exit 0` means
nothing was written (a rejected config can end in a traceback, with no `WARNING:`
line at all): show `$SCRATCH/render-toml-stderr.txt` verbatim, report "Config NOT
written", keep `$SCRATCH` for inspection and stop — never offer trust for a file
this run did not write.

**On exit 0, check `$SCRATCH/render-toml-stderr.txt` for any `WARNING:`-prefixed
line.** If one or more are present, the write still succeeded but
`cfg_render_toml` silently dropped at least one `[[reviewers]]` entry —
never report a plain success in this case. Surface it clearly, e.g.:
```
Config written to: `<target path>` — but with warnings:
  WARNING: 1 issue(s) found and NOT written: <reviewer detail>
One or more reviewer entries were rejected and are NOT in the ladder above. Review them and re-run if this wasn't intended.
```
Only when the captured file has no `WARNING:` lines, print a plain
summary confirming the write, always including the exact absolute path
(repeat it even though Step 2 already announced it — this is the
confirmation that the write actually happened, not just the plan to do
it): "Config written to: `<target path>`." Then, either way, the
resolved `policy.mode`, and the **priority fallback order** as its own
explicit numbered list, read from the `policy.ladder` line of
`$SCRATCH/rendered.toml` (what was actually written, which omits any
rejected entry), never re-typed from Step 2's confirmed list — e.g.:
```
Priority fallback order:
  1. codex-gpt
  2. sonnet-native
  3. grok-flagship
```
not folded into a single vague sentence about "reviewers configured in
some order" — the point of this report is that the user can see the
exact fallback sequence without having to open the file. If that ladder
differs from the one confirmed in Step 2, name the missing keys.

**When the write target was local** (`./.aikit/review-spec.toml`), tell the user the file
stays inactive for cross-AI review until trusted. Run
`python3 "$TOOLS_PY" trust-local --cwd <project root> --show`, where `<project root>` is the
parent of `.aikit/` — never `.aikit/` itself, which looks for `.aikit/.aikit/review-spec.toml`
and exits 1. `--show` writes nothing; it prints one JSON line per local subprocess or custom
reviewer (an entry with a `runtime` or a `command`): `{"key", "argv", "trusted", "path"}`, where `argv` is the exact argument list
dispatch would run (already merged with the global config per `strategy`) with the prompt
shown as the literal `<prompt>` placeholder, or `{"key", "error"}` for an entry that would be
refused. Show those lines, ask whether to trust the file, and run
`python3 "$TOOLS_PY" trust-local --cwd <project root>` only after an explicit yes. Trust is tied
to the file's exact content: any edit needs a new trust. `trust-local --cwd <project root>
--revoke` withdraws it, and still works after the file was deleted or moved.

Outside `--check-only`, when `probe-quota` prints `ignoring untrusted project-local config`,
apply the same `--show` / ask / trust sequence, then re-run `probe-quota` before treating its
output as authoritative for that project's local entries.

Finally, `rm -rf "$SCRATCH"` (only on a successful write; a failed one keeps it, above).
