---
name: ai-kit-spec-config
description: "Cross-AI lane setup: detects installed CLIs and models, proposes a review set and an execute set from the model catalog for the owner to pick, asks each role's priority order, effort and opt-in flags, then writes the [lanes] table of ai-kit's config.toml. Writes the per-project ./.aikit/config.toml by default (always announces the exact path), asks before replacing an existing [lanes] table (local or global), and migrates an old review-spec.toml on first use. Use when the user requests cross-AI review or execute setup, or when ai-kit-spec-review or ai-kit-spec-execute-superpowers offers it because no lanes exist. Supports --check-only (report availability, no writes), --local (force local write without asking), and --global (force the user ${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml directly)."
---

## Your task

Set up (or refresh) `ai-kit-spec-review`'s cross-AI reviewer configuration.

**Read [`references/config-file.md`](references/config-file.md) when** the user asks where the config lives, about another table in the file, the migration of an old `review-spec.toml`, or trust.

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
- **Never save a CLI reviewer entry without testing it via `check-reviewer` first** — catch auth/model/entitlement problems before persisting. The one exception: the user declined the test at Step 2.5's write-risk ask; that entry is saved untested and named so at Step 4.
- **Never silently pre-filter model families based on your own judgment** — always let the user decide, informed by your research (user agency over paternalism).
- **Never paste a multi-provider CLI's raw model list** — show the sorted, labeled `catalog-report` rows and the `propose-lanes` shortlist instead (raw lists can be hundreds of ids; the report keeps them readable).
- **Never write the global config without an explicit `--global` or a Step 2.1 "replace" answer, and never treat `--global` or `--local` as consent to replace an existing roster** (global changes affect all projects; default is local).
- **Never skip asking about session-default entries** — the only zero-external-dependency option, worth having as a fallback in a role's order even when the user mainly wants external CLI lanes.
- **Never omit or soften `(running under: unknown)`** — when `detect-current-runtime` returns
  `"unknown"`, render that annotation literally in Step 2.7's session-default ask. An
  `unknown` host gets a session-default entry (no `runtime`, `model = ""`), never a guessed
  runtime. Dropping the annotation or rewording it to "not detected" is the same silent-omit
  as leaving `purpose` unset on a brand-new entry.
- **Never skip announcing the target path before asking reviewer questions** — user must know where config is headed from the start.
- **Never re-derive the write target at Step 3** — use what Step 2 already resolved and announced (consistency guarantee).
- **Never translate literal identifiers** — `purpose` values (REVIEW/EXECUTE), model ids, catalog keys, CLI/runtime names, and field labels stay in their literal, invariant form regardless of what language the rest of this conversation is in. Narrate and explain in the user's own language, but never garble an identifier a user or this skill needs to match against config values by translating it.
- **Never run `trust-local` (the trusting form) without the user's explicit yes** — not even for the `./.aikit/config.toml` this wizard just wrote. Show `trust-local --cwd <project root> --show` first so the user consents after seeing each reviewer's argv; until then a file with a command-bearing entry (defined at Step 4) has its whole `[lanes]` table inactive.
- **Never let the proposal's order stand as the owner's pick** — jev or the scorer only orders the shortlist; no lane configuration is written before the owner confirms the review set and the execute set.
- **Never ask a wizard question in a herdr pane or of another agent** — every question goes to the owner in the owner's own session.
- **Never write a lane whose data-use confirmation was declined or skipped**, and never default an unknown data-use note to a safe value.
- **Never set `usage_limited`, `escalate_runtime` or `escalate_model` without the owner's explicit yes** — no price, name, ranking or default turns one on.
- **Never read or print opencode's `auth.json` or any `apiKey`** — the stale-provider report
  reads provider names only, and a key value never belongs in a reply.

### Step 1 — Detect

```bash
python3 "$TOOLS_PY" detect-runtimes
python3 "$TOOLS_PY" detect-tools
```

Parse the printed JSON: for each CLI marked `"installed": true`, note its
path, plus its `models` list when present (pi, opencode, cursor, codex and claude carry
one, grok never does; a CLI whose enumeration failed degrades to no list).

`detect-tools` prints `{"rg": bool, "sd": bool, "bat": bool, "eza": bool, "fd": bool,
"codebase-memory-mcp": bool}` — informational only, this step does not add new wizard questions.
When asking the user optional per-reviewer/per-executor questions later in the wizard,
mention which of these are present on this machine — this is the data
`ai-kit-spec-execute` will need later; this step only surfaces it.

**No way to ask: stop here.** If the host has no structured-question tool and no plain conversation with the user (a subagent, a print-mode or other headless run), stop after the two detection commands above: read [`references/headless.md`](references/headless.md), print its block, write no config, cache or trust record (no runtimes snapshot, no catalog), remove `$SCRATCH`, and say that a person must run ai-kit-spec-config. This check comes before every branch below, `--check-only` included.

**If `--check-only` was passed**, read [references/check-only.md](references/check-only.md)
and follow it: it asks Step 2.5's write-risk question before any live probe, reports availability
and stale providers, then stops with no writes.

**A migrate-only request is not this wizard's write.** When the user only asks to migrate an old `review-spec.toml`, report `migration pending`, say that the next command that reads the roster (`probe-quota`, `resolve-reviewers` or a review run) migrates it, and stop: run no `detect-runtimes --save`, no catalog step and no write. Run the full setup only if the user also wants the lanes replaced.

**Otherwise**, persist the snapshot before continuing to Step 2:
```bash
python3 "$TOOLS_PY" detect-runtimes --save "$RUNTIMES_JSON"
```
(re-running detection here is cheap and keeps this step's logic linear —
`--save` persists via `cache_write_json`, so `ai-kit-spec-review` doesn't
have to re-detect next session.)

Then run the stale-provider report (read-only; exits 0 whatever it finds, so it never stops setup):
```bash
python3 "$TOOLS_PY" check-providers --cwd "$(pwd)"
```
Show its lines to the user as they are. A `warning:` line is a finding to relay, not an error,
and an `(unconfirmed: ...)`, `config file only` or `not checked` line is never upgraded to
"verified" or called "stale".

### Step 1.5 — Catalog

Run the catalog flow and **MANDATORY read** [`references/catalog.md`](references/catalog.md).
Show the `catalog-report` output and its attribution lines verbatim, then continue to Step 2.
The review and execute proposal is Step 2.2's `propose-lanes` run over this catalog.

### Step 2 — Ask

Before registering any lane, weigh two judgment calls, not just the mechanics below: **is this lane's quota reliable enough to be a primary pick, or only worth keeping as a fallback?** (a lane with a tight free-tier limit belongs low in its role's order, not first) — and **does the model's strength match the purpose it is chosen for?** (the proposal ranks per purpose). Registering every available model indiscriminately produces orders nobody can predict; the goal is a config whose fallback behavior the user sees at a glance.

| I want to... | Go to |
|---|---|
| Decide where the config gets written | Step 2.1 |
| Ask the questions in order: runtimes per purpose, proposal, free lanes, effort, orders, escalation | Step 2.2 |
| Figure out a model's vendor | Step 2.3 |
| Store the pair and its runner knobs | Step 2.4 |
| Verify a candidate actually works | Step 2.5 |
| Tag a lane as UI/coding/planning-oriented | Step 2.6 |
| Register a session-default (no-runtime) lane | Step 2.7 |
| Set the mode, the strategy and the timeouts | Step 2.8 |

#### Step 2.1 — Resolve the write target

**Resolve the write target first, before asking anything else about reviewers.** Default is **local** (`./.aikit/config.toml`) — a per-project config is the safer default since it can't silently affect other projects. The global file is the user layer, `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` (the same rule the config reader uses; a relative or blank `XDG_CONFIG_HOME` counts as unset); resolve it once to an absolute path, called `<user config>` below. `--global` forces `<user config>` directly, skipping the ask below. `--local` also forces local directly, skipping the ask (both flags are an explicit choice, so neither needs confirming). With **neither flag passed** (the common case): `Read` `<user config>` and check whether a global roster exists. A global roster exists when that file has a `[lanes]` table, or when an old `review-spec.toml` sits beside it in the same folder (that old roster migrates into the config.toml on the write). A config.toml with neither counts as no roster.
- If it does **not** exist, proceed with the local default silently.
- If it **does** exist, use `AskUserQuestion` to ask explicitly before writing anywhere: "A global roster already exists at `<user config>` (or as an old `review-spec.toml` there that migrates into it). Write a per-project roster at `./.aikit/config.toml` instead (recommended — doesn't touch the global roster), or replace the global roster?" — with the local option first/default. When that global roster is an old `review-spec.toml`, offer replace in two forms: "replace" (the old file migrates first and is deleted once the migration's value check passes) and "replace, and keep the old roster as `review-spec.toml.migrated`". Picking either form here is the replacement consent below for the global file, and the keep form is also its keep answer.

**Replacement gate (every flag combination).** `Read` the resolved target itself. If it already holds a roster (a `[lanes]` table, or an old `review-spec.toml` beside it, which migrates into the target on the write) and the user has not already approved replacing that exact file above, use `AskUserQuestion`: "`<resolved absolute path>` already holds a roster. Replace it with the roster built in this run (its current lanes and policy are lost unless you re-enter them; other tables and comments in the file are kept; an old `review-spec.toml` migrates first and is deleted once the migration's value check passes), or stop and keep it?" — with "stop" first/default. When an old `review-spec.toml` sits beside the target, add a third answer, "replace, and keep the old roster as `review-spec.toml.migrated`", which also migrates first. `--local`/`--global` choose the target, never consent to replace it. On "stop", end the run without writing. Only an explicit "replace" (either form) lets Step 3 pass `--replace`, and only the keep form adds `--keep-backup`; without `--replace`, `render-toml --out` refuses an existing roster and writes nothing.

**Once the target is resolved, announce it immediately** — print "Writing to: `<resolved absolute path>`" before asking any of the reviewer questions below, so the user knows where this run's answers are headed from the start (not just in Step 4's closing report, which restates the same path after the write actually happens).

#### Step 2.2 — Ask the questions in order

**MANDATORY — READ ENTIRE FILE:** before asking any lane question, read [`references/wizard-flow.md`](references/wizard-flow.md) completely; **NEVER set any range limits when reading it.** It is the one place the question order lives: preferred runtimes per purpose, the catalog inputs, the `propose-lanes` shortlist per purpose, the free-lane questions of [`references/free-lanes.md`](references/free-lanes.md) (read it when a chosen model has a zero price), each chosen lane's pair and effort, the test call, the session default, the alternative lane, each role's order and the escalation flags. Review and execute stay separate in every question; no lane configuration is written before both sets are confirmed, and Step 3 writes only the lanes chosen there (the catalog step and the test calls still record catalog and usability data).

**Do NOT load** `references/cli-model-selection.md` unless `wizard-flow.md` sends you there: step 2 (a preferred runtime with no `models` list, or unmatched candidates) for its items 1 to 4, and step 6 for its item 6, the code-index alternative check that runs for every kept lane. Skipping the flow reproduces landmines this wizard already hit: guessing a codex id (`placeholder-model-1-high` instead of `placeholder-model-1`), dumping a ~200-id cursor list raw instead of the catalog report, proposing before unmatched confirmation, and writing every catalog candidate instead of the chosen lanes.

Read the data-use note once per chosen model from that model's own vendor page; never reuse a page read for another model as its source, and if a provider page does not name it, use `unknown` with source `none`.

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
plus the knobs that runtime takes as entry fields (`effort`, asked at `references/wizard-flow.md` step 5; `service_tier` for codex;
`cursor_mode` for cursor, default `ask`). The runner builds the argv from those fields at
dispatch. `build-command --runtime <id>` is an optional preview of that argv — it prints the
argv and says that a config.toml lane stores `runtime` and `model`; do not store its output as a
`command`. How a stored pair is run, waited for and retried is in
[`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md) for runtime/model dispatch; this skill
only stores the pair, and the runner refuses a model id its runtime's grammar disallows.
```bash
python3 "$TOOLS_PY" build-command --runtime <id> \
  [--effort <e>] [--service-tier <t>] [--mode plan|ask]
```
**codex's `model` field must be the BARE model id — never suffix an effort/tier tag onto it.**
A live check confirmed that codex rejects an effort suffix on the model id; shown here with invented placeholders: `codex exec -m placeholder-model-1-high` is rejected, and the correct pair is `model = "placeholder-model-1"`
with `effort = "high"` stored on the entry (the runner passes it as `--codex-effort`, not in
the model string). For cursor below, fast and context sit in the model-id string and the runner composes
the lane's effort into it at dispatch — never carry that pattern over to codex. codex has no
`models`/`list-models` subcommand (confirmed via `codex --help`), but `detect-runtimes`
enumerates its user-selectable models from the real binary's `codex debug models` output
(entries with `visibility: "list"` only) into `clis.codex.models` — when `$RUNTIMES_JSON`
carries that list, pick the model id from it. When it does not (an older codex without
`debug models`, or an enumeration that failed and degraded to no list), treat the exact current
model id as unfamiliar and research it per Step 2.2's rule before proposing it to the user,
rather than typing a remembered id from training knowledge.

For `cursor` specifically, fast and context are encoded in the model id itself, not a runner
flag — ask the user for either, then:
```bash
python3 "$TOOLS_PY" build-model-id --runtime cursor --base-model <id> \
  [--fast true|false] [--context <c>]
```
and use the printed id as this entry's `model` field (unchanged from the plain id when no
overrides were given). `build-model-id` stays for these cursor bracket ids. Leave `--effort` out: the lane's `effort` key is merged into the id's bracket at dispatch, and an id that already carries an effort keeps it and prints an `ignored:` line for a different lane effort.

**Grok has no runner formula.** `build-command --runtime grok` prints the command to store on a
custom entry with no `runtime`, trust-gated like any custom command. Any other CLI outside the
runner table — a CLI this catalog of profiles hasn't caught up with yet, a brand-new provider,
or a fully custom local script — is that same escape hatch: a custom entry with a hand-written
`command` and no `runtime`. A lane entry's `command` field accepts a plain template with
just `{model}`/`{prompt}` as placeholders. Hand-written templates are split into argv the way a
shell splits words; `{model}`, `{prompt}`, and any `extra` fields each fill a whole argument
(`{prompt}` needs no quoting). Shell operators (`;`, `|`, `&&`, `>`), `$` expansions, and
backticks are rejected with an error naming the reviewer — wrap a pipeline in a script and
register the script. This is the intended open escape hatch: any CLI/script that can be invoked
non-interactively with a model and a prompt can become a reviewer entry.

#### Step 2.5 — Test the pair before saving

**Check write risk first, before any live call.** When the runtime's profile (read at Step 2.4)
has `read_only: unconfirmed`, the test below runs that CLI from a private temporary directory, not
from the working tree, but with its normal write permissions, so nothing stops it from writing to
other paths you can write, your files included. Before running it, use `AskUserQuestion`: "Note: `<id>` has
no confirmed read-only invocation — its test call starts in a private temporary directory but runs
with the CLI's normal write permissions, and every later run uses them against your working tree.
Run the one test call now, or skip the test?" — with "skip
the test" first/default. On skip, run no call, keep the entry and report it as untested at Step 4;
on yes, continue below. A runtime with no profile (pi today) is treated the same way, because
nothing confirms a read-only invocation for it.

**Then, before finalizing any table-runtime entry, actually test the pair — don't just trust that
the model id works.** Run:
```bash
python3 "$TOOLS_PY" check-reviewer --key <candidate-key> --model <model-id> \
  --vendor <vendor> --runtime <id> --catalog-path <catalog> \
  [--extra-json '<json>']
```
Pass `--catalog-path <catalog>` to `check-reviewer` so the result is recorded as the pair's usability.
A custom entry (no `runtime`) is tested the same way with `--command '<template>'` instead of
`--runtime`. This makes one real call through the runner or the custom launcher (the same
mechanism `probe-quota` uses later) and prints `{"available": bool, "detail": "..."}`. If
`available` is `false`, show the user the `detail` message verbatim (it is the CLI's own real
error text — e.g. a bad model id, an auth problem, or a plan/entitlement gate like `cursor`'s
Free-plan restriction) and ask whether to save the entry anyway (it may just be a temporary
quota exhaustion, worth keeping for later) or drop it.

For a lane whose proposal row shows a zero price, say in one line before the call: "This test call spends part of the lane's allowance."

The write-risk answer is about the test call only: saving the entry stays the user's choice, because every later dispatch accepts that CLI's default risk the same way.

#### Step 2.6 — Ask about the optional strength attribute; `purpose` comes from Step 2.2

**Also ask, for every entry (a pair or the session default), an optional `strength`**: `"ui"`,
`"coding"`, `"planning"`, or left unset — free text otherwise, not validated. This is
informational only — captured in the lane entry for a human (or a future version of this
design) to read, but **not yet consumed by any resolution logic today**
(`resolve_reviewers`/`resolve_ladder_pick` ignore it completely). Tell the user this plainly if
they ask what it does: it doesn't change dispatch behavior yet, it just gets saved.

**`purpose` is NOT asked here** — the set the lane was confirmed in at Step 2.2 gives it: `review`, `execute`, or `both` for a pair kept in both sets. Carry it forward unchanged; do not re-ask, and do not silently drop it.

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

Worth asking regardless of `policy.mode`, since it is the only zero-external-dependency option (it needs no extra CLI and no external quota probe; the session's own quota still applies and is not observable here): useful as a primary pick or a pure fallback, depending on where the user places it in its role's order (`references/wizard-flow.md` step 9). **A host-run entry is never automatically prioritized over a subprocess one** — only its position in its role's order decides priority, and quota or availability failures decide fallback; for a pure fallback, place it last in that order. **When the captured `host` is `"claude"`**, the entry is the pair `runtime = "claude"` plus one of the short aliases that host defines (shown here as `placeholder-alias-1`), never a full model id such as `placeholder-model-1`; ask the user to pick one of those aliases rather than typing a version string. On any other host, or `unknown`, the entry is the session default (no `runtime`, `model = ""`), because only Claude Code's aliases are verified per-call selectable.

**Also ask, for each such entry, the same `purpose` question Step 2.2 answers for ranked
candidates**: review, execute, or both? (`"review"` | `"execute"` | `"both"`.) A
session-default entry never goes through Step 2.2's catalog/ranking flow — there is no model id
to look up — so without this question it would get no `purpose` at all, and the writer files an
entry with no `purpose` under `[[lanes.review]]` only (`split_by_purpose`), silently dropping an
execute or both answer. That review-only default exists for legacy entries, never for a
brand-new one. Carry the answer into this entry's `purpose` field at Step 3's write,
exactly like a Step 2.2-sourced entry — never leave it unset for a newly-registered one. Carry
the captured host into the entry as described above — never silently omitted.

#### Step 2.8 — Set `policy.mode`, strategy and timeouts

Then ask `policy.mode` (`single` or `double`): `single` seats the first available lane of the review order; `double` also seats an independent secondary. Each role's order was already asked at `references/wizard-flow.md` step 9; `render-toml` keeps a generated `#` comment with each order above its `[lanes.policy.review]` or `[lanes.policy.execute]` table, so it stays readable to anyone opening `config.toml` later. If the resolved write target (above) is **local**,
also ask whether this local config should be `local-only` or the default `global-merge` — set
the JSON config's top-level `strategy` key to `"local-only"` if so (`render-toml` writes it as `strategy = "..."` under `[lanes]`); omit the key entirely for the
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
that lane entry, instead of the policy-wide default. It must be a **flat** key on the
entry — this config format has no nested-object support (the writer rejects a nested value),
so a nested `extra = { timeout_tiers = [...] }` is not a way to set it.

### Step 3 — Write

Build the JSON shape `skills/ai-kit-spec-review/ai-kit-spec.py`'s `render-toml` subcommand expects: `{"strategy": "local-only", "policy": {"mode": "single", "timeout_tiers": [600, 1200, 1800], "review": {"ladder": ["<key>"]}, "execute": {"ladder": ["<key>"]}}, "lanes": [...]}` — `strategy` only when Step 2.8 asked for `local-only`, `timeout_tiers` only when changed, a role's `review` or `execute` table only when that role has a lane, and never a flat `ladder`. Each object in `lanes` carries: `key`; `runtime` and `model` (or neither, for the session default; `command` only on a custom entry for a CLI outside the table); `purpose` (`review`, `execute` or `both`, from Step 2.2 or Step 2.7 — every newly registered entry gets an explicit `purpose`; an absent `purpose` is reserved for a pre-migration entry carried forward unchanged); its knobs and `strength`; `is_router` or `fallback_quota` only when confirmed `true`; `effort` when chosen, plus `effort_source` only after a test call accepted it; `escalate_runtime` or `escalate_model` only when `true`; `usage_limited` (and `usage_limit_note`) only on the owner's yes; `pool` on every zero-price lane; and the data-use keys on every zero-price lane the owner confirmed (`references/free-lanes.md`). Never write a `false` flag. [`references/config-file.md`](references/config-file.md) shows an example. `render-toml` rejects anything else and prints why. Pass `--catalog-path <catalog>` (the path Step 1.5 printed) and `--runtimes-json "$RUNTIMES_JSON"` (the snapshot Step 1 saved), so the write checks each effort against the evidence the proposal used.

Write it to `$SCRATCH/config.json`, then let `--out` do the write directly (atomic, creating parent dirs as needed) rather than piping stdout through a second write yourself:

```bash
python3 "$TOOLS_PY" render-toml --json-config "$SCRATCH/config.json" --out <target path> \
  [--replace] [--keep-backup] --catalog-path <catalog> --runtimes-json "$RUNTIMES_JSON" > "$SCRATCH/rendered.toml" 2> "$SCRATCH/render-toml-stderr.txt"
echo "render-toml exit $?"
```

`<target path>` is the write target Step 2 resolved and already
announced — `./.aikit/config.toml` by default (or explicitly via
`--local`), `<user config>` only via `--global` or
because the user picked "replace the global roster" at Step 2.1's
ask. Never re-derive the target here independently of what Step 2
already resolved and told the user. Add `--replace` only when the target holds a roster (a `[lanes]` table, or an old `review-spec.toml` beside it, which migrates) and Step 2.1's replacement gate got an explicit "replace"; with `--replace`, render-toml first migrates that old roster and prints one line. Add `--keep-backup` only for Step 2.1's keep answer: the migrated old roster then stays as `review-spec.toml.migrated`; without it the old file is deleted once the migration's value check passes. (The runtimes snapshot was already
persisted in Step 1 via `--save` — no separate write needed here.)
**Capture stderr to `$SCRATCH/render-toml-stderr.txt`** — `render-toml`
prints a `WARNING:` line there for every lane entry it
rejected-and-dropped instead of writing (e.g. a malformed entry), and
this is the ONLY place that warning is ever emitted — Step 4 below reads
this file to decide whether to surface it. `$SCRATCH/rendered.toml` holds
the whole written file (stdout adds one trailing newline, so compare with `diff`, not
`cmp`).

### Step 4 — Report

**First, check the printed exit status.** Anything but `render-toml exit 0` means the
write is not confirmed (a rejected config can end in a traceback, with no `WARNING:` line;
a `refusing to replace` line means nothing was written (render-toml checks the target before it migrates or writes anything); a `migrated ... to ...` line on stderr means the old roster moved into the target just before the write; a failure after the write,
such as printing stdout, can leave the target already replaced): show
`$SCRATCH/render-toml-stderr.txt` verbatim, `Read` the target and report "Config write NOT
confirmed" with what the target now holds, keep `$SCRATCH` for inspection and stop — never
offer trust after a nonzero exit.

One exception to that stop: when every stderr line is a `render-toml: <key>: effort ...` refusal (a level outside the model's list, or one the runner cannot pass), nothing was written; ask each named lane's effort again from the levels the line names, then re-run Step 3.

**On exit 0, check `$SCRATCH/render-toml-stderr.txt` for any `WARNING:`-prefixed
line.** If one or more are present, the write still succeeded but
`render-toml` silently dropped at least one lane entry —
never report a plain success in this case. Surface it clearly, e.g.:
```
Config written to: `<target path>` — but with warnings:
  WARNING: 1 issue(s) found and NOT written: <reviewer detail>
One or more lane entries were rejected and are NOT in the orders below. Review them and re-run if this wasn't intended.
```
Only when the captured file has no `WARNING:` lines, print a plain
summary confirming the write, always including the exact absolute path
(repeat it even though Step 2 already announced it — this is the
confirmation that the write actually happened, not just the plan to do
it): "Config written to: `<target path>`." Then, either way, the resolved `policy.mode` and **each role's priority order** as its own explicit numbered list, read from the `ladder` line of `[lanes.policy.review]` and of `[lanes.policy.execute]` in `$SCRATCH/rendered.toml` (what was actually written, which omits any rejected entry), never re-typed from Step 2's confirmed lists — e.g.:
```
Review order:
  1. review-primary
  2. session-fallback
Execute order:
  1. execute-primary
```
not folded into a single vague sentence about "reviewers configured in
some order" — the point of this report is that the user can see the
exact fallback sequence without having to open the file. If an order
differs from the one confirmed at Step 2.2, name the missing keys; a role with no lane has no order. Show every other stderr line (a migration line, a usage-limited role warning, a legacy-order note) as printed. Name every entry saved
untested at Step 2.5 ("untested: `<key>` — its availability is unverified").

**When the write target was local** (`./.aikit/config.toml`), check whether it holds a
command-bearing entry. **Command-bearing** (the one definition, same as
[`references/config-file.md`](references/config-file.md) and `trust.command_lanes_bytes`): an
entry with a `command`, or an entry whose `key` equals the `key` of a `command` entry in this
file or in the user config (the user config only without `strategy = "local-only"`), in any
role (its fields fill that command's placeholders, so a
`runtime` entry that overrides a user command entry counts). A plain (runtime, model) pair with
its own key is not command-bearing. When the file holds at least one, tell the user the whole
project `[lanes]` table stays inactive for cross-AI review until trusted; with none it needs no
trust and is active at once. Run
`python3 "$TOOLS_PY" trust-local --cwd <project root> --show`, where `<project root>` is the
parent of `.aikit/` — never `.aikit/` itself, which looks for `.aikit/.aikit/config.toml`
and exits 1. `--show` writes no trust record; it prints one JSON line per project entry that runs
as a subprocess (an entry with a `runtime` or a `command`, so more entries than the
command-bearing ones): `{"key", "argv", "trusted", "path"}`, where `argv` is the exact argument list
dispatch would run (already merged with the global config per `strategy`) with the prompt
shown as the literal `<prompt>` placeholder, or `{"key", "error"}` for an entry that would be
refused. Show those lines, ask whether to trust the file, and run
`python3 "$TOOLS_PY" trust-local --cwd <project root>` only after an explicit yes. Trust covers the file's command-bearing lane entries: editing another table, comments or spacing keeps it; changing a command-bearing entry needs a new trust; a file with no command-bearing entry needs none (`trust-local` prints `nothing to trust:`). `trust-local --cwd <project root>
--revoke` withdraws it, and still works after the file was deleted or moved.

Outside `--check-only`, when `probe-quota` prints `ignoring untrusted project-local config`,
apply the same `--show` / ask / trust sequence, then re-run `probe-quota` before treating its
output as authoritative for that project's local entries.

Finally, `rm -rf "$SCRATCH"` (only on a successful write; a failed one keeps it, above).

## Evidence

- The bare-model rule for codex was confirmed live with a real model id, shown here with invented placeholders: codex rejects an effort suffix on the model id.
- Until 2026-08-29 an earlier design gave host-run entries an automatic guaranteed-baseline slot in `double` mode regardless of ladder position; a real config hit this and got a silently reordered ladder, so it was removed.
