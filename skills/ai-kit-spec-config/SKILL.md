---
name: ai-kit-spec-config
description: "Cross-AI lane setup: detects installed CLIs and models, proposes a review set and an execute set from the model catalog for the owner to pick, asks each role's priority order, effort and opt-in flags, then writes the [lanes] table of ai-kit's config.toml. Writes the per-project ./.aikit/config.toml by default, names the target first, and asks before replacing any existing [lanes] table. Use when the user wants to set up, refresh or check cross-AI review or execute lanes (which models review, which implement, in what fallback order), even without the word lanes; when ai-kit-spec-review or ai-kit-spec-execute-superpowers offers it because no lanes exist; to find lane providers opencode no longer lists; or to ask about migrating an old review-spec.toml. Supports --check-only (report availability, no config writes), --local and --global (pick the target, never consent to replace it). Not for running a review or execute with configured lanes, hand-editing one lane value, or editing [runner] or opencode.jsonc."
---

## Your task

Set up (or refresh) ai-kit's cross-AI lanes: the review and execute lanes and each role's order, written to the `[lanes]` table of `config.toml`.

**Read [`references/config-file.md`](references/config-file.md) when** the user asks where the config lives, about another table in the file, the migration of an old `review-spec.toml`, or trust.

Run Steps 0 to 4 in order (locate, detect, ask, write, report). Every CLI call, model id and TOML
field goes through the `ai-kit-spec.py` factory subcommands, never hand-typed: a wrong quote or a
guessed model id fails silently, or errors at dispatch far from where the mistake was made.

**Host tools.** `Bash`, `AskUserQuestion` (with `multiSelect`) and `Read` name the host's shell,
structured-question and file-reading tools. Without a structured-question tool, ask in plain
conversation: number the options, accept several numbers where a step says `multiSelect: true`,
and wait for the answer. Never answer a question on the user's behalf because no tool exists for it.

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
- **Never write a skill role the owner did not confirm** — `classify-skills` only proposes, and its jev answer is advisory; `confirm-skill-role` runs once per role the owner confirmed.
- **Never ask a wizard question in a herdr pane or of another agent** — every question goes to the owner in the owner's own session.
- **Never write a lane whose data-use confirmation was declined or skipped**, and never default an unknown data-use note to a safe value.
- **Never set `usage_limited`, `escalate_runtime` or `escalate_model` without the owner's explicit yes** — no price, name, ranking or default turns one on.
- **Never read or print opencode's `auth.json` or any `apiKey`** — the stale-provider report
  reads provider names only, and a key value never belongs in a reply.

## Gotchas

- Reads migrate: a catalog fetch and `trust-local --show` both migrate a pending old `review-spec.toml` they read, so running them can move a roster the owner wanted left alone (Step 1.5, `references/trust-flow.md`); the read-only checks (`--check-only`, `check-providers`, `probe-quota --no-migrate`) report `migration pending` and write nothing.
- `detect-current-runtime` returns the first host marker in a fixed precedence, not the immediate parent CLI, so a nested session can report the wrong host (Step 2.7).
- codex takes the bare model id: an effort suffix on it is rejected at dispatch. cursor carries fast and context inside the id (Step 2.4).
- `timeout_tiers` are cumulative attempts, so the default can run 60 minutes, not 30; a per-lane override is a flat key, and a nested one is rejected by the writer (Step 2.8).
- A test call's private temporary directory does not confine the CLI's write permissions, so the call can still write your files (Step 2.5).

## Workflow

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
fi
printf '%s\n' "$TOOLS_PY" "$CLI_PROFILES_DIR" "$RUNTIMES_JSON"
```

The sibling is tried first so the module that runs is the one installed beside the
`SKILL.md` you are following, not an older copy elsewhere. `SCRATCH` is this run's private
scratch directory (mode 0700, unique per run), made on first need: the first `Bash` call that
writes a temporary file (the `--check-only` probe, the catalog fetch of
`references/cli-model-selection.md`, or Step 3) starts with
`SCRATCH="$(mktemp -d -t ai-kit-spec-config-XXXXXX)"; printf '%s\n' "$SCRATCH"`, and every later
call reuses that printed path. Every temporary file goes inside it, never at a fixed
`/tmp/<name>` path another run could share or pre-plant. A run that stops before that first need
leaves no scratch behind; once made, Step 4 (or the `--check-only` stop) removes it. `cache-path` resolves the `${XDG_CACHE_HOME:-$HOME/.cache}`-aware
runtimes path through `ai-kit-spec.py` itself, so both skills agree on where it lives.

**`<project root>`** is one absolute path, resolved here once: `git rev-parse --show-toplevel`
run from the current directory, or, outside Git, the directory the owner confirms. Every
`--cwd`, every raw read and the local target (`<project root>/.aikit/config.toml`, the file this
skill calls `./.aikit/config.toml`) use that same path, never the shell's `$(pwd)`.

**Resolve this whole block once, in one `Bash` call, and record its three printed lines as
literal absolute paths — not shell environment variables.** Every `Bash` call starts a fresh
shell, so every `$TOOLS_PY`/`$CLI_PROFILES_DIR`/`$RUNTIMES_JSON` below means "the literal path
captured here", and `$SCRATCH` the one printed at its first need, substituted directly. If `TOOLS_PY` does not exist at the
resolved path, stop and report: "ai-kit-spec-review's own `ai-kit-spec.py` module is missing —
this skill configures cross-AI review for `ai-kit-spec-review`, which must already be
installed."

### Step 1 — Detect

```bash
python3 "$TOOLS_PY" detect-runtimes
python3 "$TOOLS_PY" detect-tools
```

Parse the printed JSON: for each CLI marked `"installed": true`, note its
path, plus its `models` list when present (pi, opencode, cursor, codex and claude carry
one; a CLI without a listing command, or whose enumeration failed, has no list).

`detect-tools` prints `{"rg": bool, "sd": bool, "bat": bool, "eza": bool, "fd": bool,
"codebase-memory-mcp": bool}` — informational only, this step does not add new wizard questions.
When asking the user optional per-reviewer/per-executor questions later in the wizard,
mention which of these are present on this machine — this is the data
`ai-kit-spec-execute` will need later; this step only surfaces it.

**No way to ask: stop here.** If the host has no structured-question tool and no plain conversation with the user (a subagent, a print-mode or other headless run), stop after the two detection commands above: read [`references/headless.md`](references/headless.md), print its block, write no config, cache or trust record (no runtimes snapshot, no catalog, no scratch folder), and say that a person must run ai-kit-spec-config. This check comes before every branch below, `--check-only` included.

**If `--check-only` was passed** (a plain-words request only to check which lanes are available and change nothing, such as "just check my reviewers, change nothing", counts as the flag), read [references/check-only.md](references/check-only.md)
and follow it: it asks Step 2.5's write-risk question before any live probe, reports availability
and stale providers, then stops with no config, cache, snapshot or trust write. A live probe is
still a real run: the CLI's own side effects aside, the cross-AI runner keeps run state under
`${XDG_STATE_HOME:-~/.local/state}/ai-kit/` and may clear a dead run's leftovers there.

**A migrate-only request is not this wizard's write.** When the user only asks to migrate an old `review-spec.toml`, report `migration pending`, say that the next command that reads the roster (`probe-quota`, `resolve-reviewers` or a review run) migrates it, and stop: run no `detect-runtimes --save`, no catalog step and no write. Run the full setup only if the user also wants the lanes replaced. One exception: an old roster with a lane that names a removed runtime is never migrated by a read (each read uses the roster in memory and drops that lane with a removal note); say so instead of promising a migration, and offer the full setup to re-save those lanes.

**Otherwise**, persist the snapshot before continuing to Step 2:
```bash
python3 "$TOOLS_PY" detect-runtimes --save "$RUNTIMES_JSON"
```
(re-running detection here is cheap and keeps this step's logic linear —
`--save` persists via `cache_write_json`, so `ai-kit-spec-review` doesn't
have to re-detect next session.)

Then run the stale-provider report (read-only; exits 0 whatever it finds, so it never stops setup):
```bash
python3 "$TOOLS_PY" check-providers --cwd "<project root>"
```
Show its lines to the user as they are. A `warning:` line is a finding to relay, not an error,
and an `(unconfirmed: ...)`, `config file only` or `not checked` line is never upgraded to
"verified" or called "stale".

### Step 1.5 — Catalog

**A pending old roster comes first.** When an old `review-spec.toml` awaits migration in the
project's `.aikit/` or the user config folder and `$RUNTIMES_JSON` names an installed runtime
without a `models` list, the catalog fetch would migrate that roster: read the "Pending old
roster" section of [`references/catalog.md`](references/catalog.md) before anything else in
this step, and settle Step 2.1's write target and replacement gate first.

Run the catalog flow and **MANDATORY read** [`references/catalog.md`](references/catalog.md).
Show the `catalog-report` output and its attribution lines verbatim, then continue to Step 2.
The review and execute proposal is Step 2.2's `propose-lanes` run over this catalog.

### Step 1.6 — Sort unknown skills (optional)

First run the read-only listing, without asking (like the catalog step, it asks jev when jev is
present); this step never runs during a review or an execute run.

```bash
python3 "$TOOLS_PY" classify-skills --cwd <project root>
```

When it prints no `unsorted` line (only `no unsorted skills` or `not offered` lines), say so in one
line and go on to Step 2: there is nothing to offer. Otherwise offer the sort once, with the
`unsorted` names, and sort only after the owner agrees; skip it when the owner declines or no
question can be asked.

It prints one `unsorted <name> hosts=<hosts>` line per addressable
unsorted skill of the shared role table (a skill whose name the runner cannot address gets a `not offered <name> hosts=<hosts> reason=<reason>` line instead and no proposal) and, when jev is present, at most one `proposal <name> role=<role> confidence=<c> advisory`
line per skill (jev sees only the skill's name and the first 300 characters of its description).
With jev absent it prints `jev absent: nothing proposed`; after a low or missing answer the skill
has no proposal. Say so and offer the closed roles yourself. MCP servers are never sent to jev. A
proposal is advice: ask the owner about each skill and note each role the owner confirms. Write
nothing yet: once Step 2.1 has resolved and announced the write target, run for each confirmed
role

```bash
python3 "$TOOLS_PY" confirm-skill-role --name <skill> --role <role> --cwd <project root>
```

with `--global` in place of `--cwd <project root>` when the target is the user file. Each call
writes one `[skills.roles]` entry, labeled `user-stated`, which beats the seed row; a name the
command refuses stays unsorted. These writes come before the roster write and stand on their own:
a later roster failure does not undo them, so say so before the first call.

### Step 2 — Ask

`references/wizard-flow.md` sets the question order (Step 2.2); Steps 2.3 to 2.8 hold the per-topic rules it points to.

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

**Resolve the write target first, before asking anything else about reviewers.** The global file is the user layer, `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` (the same rule the config reader uses; a relative or blank `XDG_CONFIG_HOME` counts as unset); resolve it once to an absolute path, called `<user config>` below. Take the first case that applies:

1. Step 1.5's pending-old-roster case already resolved, gated and announced the target: reuse it and go on to Step 2.2.
2. Both `--local` and `--global`: they name no target; ask the owner which one is meant, then continue as case 3.
3. `--global` alone: `<user config>`; `--local` alone: `./.aikit/config.toml`. Either flag is an explicit choice, so skip the ask in case 4.
4. Neither flag (the common case): the default is **local** (`./.aikit/config.toml`), since a per-project config cannot silently affect other projects. `Read` `<user config>`: a global roster exists when that file has a `[lanes]` table, or when an old `review-spec.toml` sits beside it (it migrates into the config.toml on the write); a config.toml with neither counts as no roster. With no global roster, proceed with the local default silently. With one, use `AskUserQuestion` before writing anywhere: "A global roster already exists at `<user config>` (or as an old `review-spec.toml` there that migrates into it). Write a per-project roster at `./.aikit/config.toml` instead (recommended — doesn't touch the global roster), or replace the global roster?" — with the local option first/default. When that global roster is an old `review-spec.toml`, offer replace in two forms: "replace" (the old file migrates first and is deleted once the migration's value check passes) and "replace, and keep the old roster as `review-spec.toml.migrated`". Picking either form here is the replacement consent below for the global file, and the keep form is also its keep answer.

**Replacement gate (every flag combination).** `Read` the resolved target itself. If it already holds a roster (a `[lanes]` table, or an old `review-spec.toml` beside it, which migrates into the target on the write) and the user has not already approved replacing that exact file above, use `AskUserQuestion`: "`<resolved absolute path>` already holds a roster. Replace it with the roster built in this run (its current lanes and policy are lost unless you re-enter them, with the comments of any lane or policy table the new roster drops; other tables and their comments are kept; an old `review-spec.toml` migrates first and is deleted once the migration's value check passes), or stop and keep it?" — with "stop" first/default. When an old `review-spec.toml` sits beside the target, add a third answer, "replace, and keep the old roster as `review-spec.toml.migrated`", which also migrates first. `--local`/`--global` choose the target, never consent to replace it. On "stop", end the run without writing. Only an explicit "replace" (either form) lets Step 3 pass `--replace`, and only the keep form adds `--keep-backup`; without `--replace`, `render-toml --out` refuses an existing roster and writes nothing.

**Once the target is resolved, announce it immediately** — print "Writing to: `<resolved absolute path>`" before asking any of the reviewer questions below, so the user knows where this run's answers are headed from the start (not just in Step 4's closing report, which restates the same path after the write actually happens).

#### Step 2.2 — Ask the questions in order

**MANDATORY — READ ENTIRE FILE:** before asking any lane question, read [`references/wizard-flow.md`](references/wizard-flow.md) completely; **NEVER set any range limits when reading it.** It is the one place the question order lives: preferred runtimes per purpose, the catalog inputs, the `propose-lanes` shortlist per purpose, the free-lane questions of [`references/free-lanes.md`](references/free-lanes.md) (read it when a chosen model has a zero price), each chosen lane's pair and effort, the test call, the session default, the alternative lane, each role's order and the escalation flags. Review and execute stay separate in every question; no lane configuration is written before both sets are confirmed, and Step 3 writes only the lanes chosen there (the catalog step and the test calls still record catalog and usability data).

**Do NOT load** `references/cli-model-selection.md` unless `wizard-flow.md` sends you there: step 2 (a preferred runtime with no `models` list, or unmatched candidates) for its items 1 to 4, and step 6 for its item 6, the code-index alternative check that runs for every kept lane. Skipping the flow reproduces landmines this wizard already hit: guessing a codex id (`placeholder-model-1-high` instead of `placeholder-model-1`), dumping a ~200-id cursor list raw instead of the catalog report, proposing before unmatched confirmation, and writing every catalog candidate instead of the chosen lanes.

Read the data-use note once per chosen model that `free-lanes.md` asks about (a zero-price lane; no other lane gets the note), from that model's own vendor page; never reuse a page read for another model as its source, and if a provider page does not name it, use `unknown` with source `none`.

#### Step 2.3 — Resolve vendor attribution

**Vendor attribution is deterministic — never infer it from the model name yourself.** For every model id (whether picked from a multi-provider CLI's list or typed by the user for a single-provider CLI), resolve `vendor` by calling:
```bash
python3 "$TOOLS_PY" infer-vendor --model <model-id> --runtime <runtime-id>
```
Always pass the lane's runtime: a short alias of the claude runtime (Step 2.7's entry on a claude host) has no vendor prefix, and `--runtime claude` resolves it to `anthropic`.

When this prints `{"vendor": null}` (no known prefix — e.g. an `ollama-cloud/*` id, or a genuinely new model this table hasn't seen yet), ask the user directly for the real vendor rather than guessing — this is the one case a human still has to supply the answer, and it should be rare. Ask once for every such model of the run, with three options per model: type the vendor's name; "I don't know: save the lane without a vendor" (mark it recommended when the owner has no name to give); or drop the lane. A lane saved without a vendor gets no `vendor` key at all (never `unknown` or a guess; `render-toml` accepts it). The reviewer pick then treats its vendor as unknown: the cross-vendor filter never skips it, so in `single` mode it can be seated as the different-vendor reviewer even when its real vendor is the document author's, and when it is the `double` primary the secondary only has to differ from the author's vendor. Say that in one line when the owner picks it. The lookup is a best-effort prefix table (`_MODEL_VENDOR_PREFIXES` in the review skill's `ai_kit_spec/vendor.py`), not proof that every model family is covered.

#### Step 2.4 — Store the pair and its runner knobs

For each runtime the user wants, read its profile under `$CLI_PROFILES_DIR/<id>.md` for
anything runtime-specific this step doesn't already cover (prerequisites, known quirks,
plan/entitlement gating — `cursor.md` documents several). **Load only the profile(s) for
runtimes actually selected at Step 2.2 — do NOT read the whole `$CLI_PROFILES_DIR` directory
or preemptively load profiles for runtimes the user declined.** Each profile is a few KB of
quirks relevant to exactly one runtime; loading unselected ones adds noise without informing
any decision in this run. **When a selected runtime has no profile file** (no
`$CLI_PROFILES_DIR/<id>.md`), say so in one line and continue: the runner table, `build-command --runtime <id>`'s
preview and Step 2.5's live test are then the only sources — never invent quirks for it.

**A runtime the runner knows stores no `command`.** Store the pair: `runtime` and `model`,
plus the knobs that runtime takes as entry fields (`effort`, asked at `references/wizard-flow.md` step 5; `service_tier` for codex;
`cursor_mode` for cursor, default `ask`). The runner builds the argv from those fields at
dispatch. `build-command --runtime <id>` is an optional preview of that argv — it prints the
argv and says that a config.toml lane stores `runtime` and `model`; do not store its output as a
`command`. How a stored pair is run, waited for and retried is in
[`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md) for runtime/model dispatch; this skill
only stores the pair. The runner does not refuse an unusual id shape: it prints a shape note and
still runs it; it refuses an id only when the runtime's live model listing succeeds and lacks it
(`bad_model`), and the CLI itself may reject an id. Step 2.5's live test is the check that the
chosen id works.
```bash
python3 "$TOOLS_PY" build-command --runtime <id> \
  [--effort <e>] [--service-tier <t>] [--mode plan|ask]
```
**codex, cursor and custom entries:** read [`references/runtime-ids.md`](references/runtime-ids.md)
when a chosen lane is on codex or cursor, or is a custom entry for a CLI outside the runtime
table. In short: codex takes the bare model id, with `effort` on the entry (an effort suffix on
the id is rejected); cursor's fast and context go into the id through `build-model-id`; a custom
entry stores a trust-gated `command` template with `{model}`/`{prompt}` placeholders and no shell
operators.

#### Step 2.5 — Test the pair before saving

**Check write risk first, before any live call.** When the runtime's profile (read at Step 2.4)
has `read_only: unconfirmed`, the test below runs that CLI from a private temporary directory, not
from the working tree, but with its normal write permissions, so nothing stops it from writing to
other paths you can write, your files included. Before running it, use `AskUserQuestion`: "Note: `<id>` has
no confirmed read-only invocation — its test call starts in a private temporary directory but runs
with the CLI's normal write permissions, and every later run uses them against your working tree.
Run the one test call now, or skip the test?" — with "skip
the test" first/default. On skip, run no call, keep the entry and report it as untested at Step 4;
on yes, continue below. A runtime with no profile file is treated the same way, because
nothing confirms a read-only invocation for it.

**Then, before finalizing any table-runtime entry, actually test the pair — don't just trust that
the model id works.** Run:
```bash
python3 "$TOOLS_PY" check-reviewer --key <candidate-key> --model <model-id> \
  --vendor <vendor> --runtime <id> --catalog-path <catalog> \
  [--extra-json '<json>']
```
Leave `--vendor` out for a lane saved without a vendor. Pass `--catalog-path <catalog>` to `check-reviewer` so the result can be recorded as the pair's usability: the printed `usability` object says whether it was (`recorded`, with a `problem` when not, for example a pair the catalog does not list; no `usability` object means nothing was recorded), so report a catalog update only when `recorded` is true; a custom entry has no runtime, so its test records nothing. `--extra-json` carries the lane's other knobs (`service_tier`, `cursor_mode`, a custom entry's template fields), never `effort`: the command refuses an effort together with `--catalog-path`, so this call tests the pair without its chosen effort, and the effort level gets its own call (`references/wizard-flow.md` step 5). For a review lane, show its `capability` string beside the result: what that lane's final argv lets it do, from the review-role dry run, without starting the lane. For every saved lane, review and execute alike, Step 4 shows the `capability <runtime>/<model> <role>: <summary>` lines `config-status` prints (read-only, no probe needed).
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

**Offer an optional `strength` once for the run** (which entries, pairs or session default, to
tag, if any; the default is none): `"ui"`, `"coding"`, `"planning"`, or free text (not
validated). It is informational only: saved for a human to read, **not consumed by any
resolution logic** (`resolve_reviewers`/`resolve_ladder_pick` ignore it); say so in the offer.

**`purpose` is NOT asked here** — the set the lane was confirmed in at Step 2.2 gives it: `review`, `execute`, or `both` for a pair kept in both sets. Carry it forward unchanged; do not re-ask, and do not silently drop it.

#### Step 2.7 — Ask about the session default

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively. Those four are the `native_selectors` of the claude row of ai-kit's runtime table (`RUNTIMES` in the review skill's `ai_kit_spec/detection.py`), the only aliases routing runs natively, and not Claude Code's whole alias list; Step 1's `detect-runtimes` prints them as `aliases` for an installed claude.

Before asking, detect which runtime is hosting *this* session (never cached, always live):
```bash
python3 "$TOOLS_PY" detect-current-runtime
```
Capture the printed `host` (`pi` / `opencode` / `cursor` / `codex` / `claude` / `unknown`).
That value is shown in the prompt below and decides the entry's shape at Step 3. When several
CLIs are nested, their environment markers accumulate and the command returns the first marker in
a fixed precedence (pi > opencode > cursor > codex > claude); it does not verify which CLI is the
immediate parent. A codex or opencode session started from Claude Code records that CLI, not
claude, but a pi marker left in the environment wins even when another CLI started later. When
the owner says the printed host is not the active one, explain that precedence and offer a
session-default entry without a host-specific alias.

**Also ask, explicitly — do not skip this**: whether to register one or more entries that this
host runs itself (running under: <host>), not any one specific vendor. Substitute the captured
value into that annotation verbatim. When `detect-current-runtime` returns `"unknown"`, still
render `(running under: unknown)` literally — never omitted, never softened to "not detected"
or dropped from the prompt. Let the entry's `key` describe its place in the ladder (e.g.
`session-primary`, `session-fallback`), not a vendor.

Worth asking regardless of `policy.mode`, since it is the only zero-external-dependency option (it needs no extra CLI and no external quota probe; the session's own quota still applies and is not observable here): useful as a primary pick or a pure fallback, depending on where the user places it in its role's order (`references/wizard-flow.md` step 9). **A host-run entry is never automatically prioritized over a subprocess one** — only its position in its role's order decides priority, and quota or availability failures decide fallback; for a pure fallback, place it last in that order. **When the captured `host` is `"claude"`**, the entry is the pair `runtime = "claude"` plus one of the short aliases that host defines (shown here as `placeholder-alias-1`), never a full model id such as `placeholder-model-1`; ask the user to pick one of those aliases (the `aliases` list of Step 1's `detect-runtimes` output) rather than typing a version string. That pair has a `model`, so it carries a `vendor` like any other pair: Step 2.3 with `--runtime claude` prints `anthropic`. On any other host, or `unknown`, the entry is the session default (no `runtime`, `model = ""`), because only Claude Code's aliases are verified per-call selectable.

**Also ask, for each such entry, the same `purpose` question Step 2.2 answers for ranked
candidates**: review, execute, or both? (`"review"` | `"execute"` | `"both"`.) Such an entry
skips Step 2.2's catalog flow, and the writer files an entry with no `purpose`
under `[[lanes.review]]` only (`split_by_purpose`), a fallback kept for legacy entries, so an unasked purpose
silently drops an execute or both answer. Write the answer into its `purpose` at Step 3, with the
captured host's entry shape described above.

#### Step 2.8 — Set `policy.mode`, strategy and timeouts

Then ask `policy.mode` (`single` or `double`): `single` seats the first available lane of the review order whose vendor differs from the document author's, else the first available lane; `double` seats the first available lane and adds a secondary from another vendor only when one is available. Each role's order was already asked at `references/wizard-flow.md` step 9; `render-toml` keeps a generated `#` comment with each order above its `[lanes.policy.review]` or `[lanes.policy.execute]` table, so it stays readable to anyone opening `config.toml` later. If the resolved write target (above) is **local**,
also ask whether this local config should be `local-only` or the default `global-merge` — set
the JSON config's top-level `strategy` key to `"local-only"` if so (`render-toml` writes it as `strategy = "..."` under `[lanes]`); omit the key entirely for the
default (global-merge applies, no line needed).

The `strategy` question does not apply when the resolved target is global — `strategy` only
ever describes how a *local* config relates to the global one.

**When at least one subprocess reviewer is being registered** (a session-default-only config has no
subprocess to time out), offer, without requiring an answer, to change `policy.timeout_tiers` from
its default `[600, 1200, 1800]`. Each tier is a fresh attempt after the previous one is killed, so
the worst case is their **sum** (60 minutes), not a 30-minute ceiling; most users keep the default.
Different tiers for one lane (e.g. a known-slow `effort=high` pair) go in a **flat**
`timeout_tiers = [900, 1800]` key on that lane entry: the writer rejects a nested value, so a
nested `extra = { timeout_tiers = [...] }` is not a way to set it. Dispatch reads the flat key as
the lane's `extra.timeout_tiers` (every lane key outside `key`, `model`, `vendor`, `runtime` and
`command` lands there), so `resolve-timeout-tiers` returns it for that lane.

### Step 3 — Write

When both roles end with no lane (every candidate declined or dropped, and no session default), write nothing by default: say so and stop. Only on the owner's explicit request to clear the existing roster does an empty `lanes` list go to the writer, which then removes both role arrays.

Build the JSON shape `python3 "$TOOLS_PY" render-toml` expects: `{"strategy": "local-only", "policy": {"mode": "single", "timeout_tiers": [600, 1200, 1800], "review": {"ladder": ["<key>"]}, "execute": {"ladder": ["<key>"]}}, "lanes": [...]}` — `strategy` only when Step 2.8 asked for `local-only`, `timeout_tiers` only when changed, a role's `review` or `execute` table only when that role has a lane, and never a flat `ladder`. **Before building `lanes`, read the "Lane entry fields" section of [`references/config-file.md`](references/config-file.md)**: it says which key each entry carries and when (`vendor`, `purpose`, knobs, flags, `pool` and the data-use keys), beside an example. Every newly registered entry gets an explicit `purpose`, and a flag is written only as `true`, never `false`. `render-toml` rejects anything else and prints why. Pass `--catalog-path <catalog>` (the path Step 1.5 printed; left out only in `references/catalog.md`'s no-catalog session-default case) and `--runtimes-json "$RUNTIMES_JSON"` (the snapshot Step 1 saved), so the write checks each effort against the evidence the proposal used.

Write it to `$SCRATCH/config.json` (make `$SCRATCH` first, as Step 0 says, when no earlier step made it), then let `--out` do the write directly (atomic, creating parent dirs as needed) rather than piping stdout through a second write yourself:

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

**First, check the printed exit status**, before any other report line. Anything but
`render-toml exit 0` means the write is not confirmed, and a `WARNING:` line in
`$SCRATCH/render-toml-stderr.txt` on exit 0 means an item was left out of the file: in either
case **read [`references/write-failures.md`](references/write-failures.md)** and follow it (the
stop, the effort-refusal re-ask, the warning report). Never offer trust after a nonzero exit.

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
untested at Step 2.5 ("untested: `<key>` — its availability is unverified") and every entry saved without a vendor at Step 2.3 ("vendor unknown: `<key>` — the cross-vendor filter cannot exclude it").

Only after a confirmed write (exit 0, with or without `WARNING:` lines), run `python3 "$TOOLS_PY" config-status --cwd <project root>` (read-only, no probe) and show each `capability <runtime>/<model> <role>: <summary>` line it prints: one per lane of an `active` roster, review and execute lanes alike, in config order. The lines show that project's effective roster (project over user, per `strategy`), not only the file just written: label them so, and after a global write say when a `local-only` project file hides the saved lanes there. A `pending` or `none` roster prints no capability line: say that the capability view appears once the roster is active. On a non-zero exit, quote its stderr and say the capability view is unavailable. When the owner sorted skills at Step 1.6, also list each role it wrote (`confirmed <name> role=<role>`), each confirm that failed with its stderr (an earlier confirm stays written), and each skill left unsorted.

**When the write target was local** (`./.aikit/config.toml`), check whether it holds a
command-bearing entry. **Command-bearing** (the one definition, same as
[`references/config-file.md`](references/config-file.md) and `trust.command_lanes_bytes`): an
entry with a `command`, or an entry whose `key` equals the `key` of a `command` entry in this
file or in the user layer (only without `strategy = "local-only"`): the user `config.toml`'s
`[lanes]`, or, when it has none, an old `review-spec.toml` beside it pending migration, read in memory, in any
role (its fields fill that command's placeholders, so a
`runtime` entry that overrides a user command entry counts). A plain (runtime, model) pair with
its own key is not command-bearing. With none, the file needs no trust and is active at once.
When it holds at least one, tell the user the whole project `[lanes]` table stays inactive for
cross-AI review until trusted, then **MANDATORY read**
[`references/trust-flow.md`](references/trust-flow.md) and follow its steps in order: preview
with `trust-local --cwd <project root> --show`, show every command-bearing entry, and run the
trusting form only after an explicit yes. Outside `--check-only`, when `probe-quota` prints
`ignoring untrusted project-local config`, follow the same reference before treating its output
as authoritative for that project's local entries.

Finally, `rm -rf "$SCRATCH"` after a successful write. A failed write keeps it for inspection (above) and the report names its path; a run that ends any other way once `$SCRATCH` exists (the owner stops or cancels, an early stop) removes it before it ends.

## Evidence

- The bare-model rule for codex was confirmed live with a real model id, shown here with invented placeholders: codex rejects an effort suffix on the model id.
- Until 2026-08-29 an earlier design gave host-run entries an automatic guaranteed-baseline slot in `double` mode regardless of ladder position; a real config hit this and got a silently reordered ladder, so it was removed.
