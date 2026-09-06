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
- **Never translate literal identifiers** — `purpose` values (REVIEW/EXECUTE), model ids, catalog keys, CLI/runtime names, and field labels stay in their literal, invariant form regardless of what language the rest of this conversation is in. Narrate and explain in the user's own language, but never garble an identifier a user or this skill needs to match against config values by translating it.

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
| Register a native (no-CLI) reviewer | Step 2.7 |
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

1. Ensure a runtimes snapshot exists (Step 1 already produces one via `detect-runtimes
   --save`) — reuse `$RUNTIMES_JSON` from Step 0. Resolve the catalog cache path (no manual
   path-string surgery — a dedicated `--kind` exists precisely so this skill never has to
   derive one cache filename from another):
   ```bash
   CATALOG_JSON="$(python3 "$TOOLS_PY" cache-path --kind catalog)"
   ```
   **Ask which CLIs to consider, and group each multi-provider CLI's raw model list, BEFORE
   any of it is discovered/matched/ranked.** For each installed CLI (beyond the current
   session's own runtime), use `AskUserQuestion` to ask whether the user wants it available as
   a cross-AI reviewer at all — registering every installed CLI indiscriminately is exactly
   what this step's own opening framing at the top of Step 2 warns against. For each CLI the
   user keeps, if it's multi-provider (`models` array present — e.g. `opencode`,
   `cursor-agent`), **never hand its raw model list to `fetch-model-catalog` as-is** — a
   multi-provider CLI's raw list can be very long (confirmed live: cursor-agent's catalog is
   ~200 ids, a handful of base model families each multiplied out by effort/thinking/fast-tier
   variants, e.g. `claude-opus-5-thinking-high-fast`), and most of those tier variants will not
   exact-match models.dev/Artificial Analysis, which would otherwise turn item 4 below into
   hundreds of individual unmatched searches and confirmation prompts for what is really only a
   handful of base families. Group it first:
   ```bash
   python3 "$TOOLS_PY" group-models --runtimes-json "$RUNTIMES_JSON" --cli <id>
   ```
   This prints `{"<family>": ["<variant-id>", ...], ...}` — one entry per base model family,
   each holding its own tier/effort/fast variants (the grouping is a plain suffix-stripping
   heuristic, not a quality judgment; an id it can't confidently collapse just becomes its own
   single-member family, which is fine). Present the **families**, not the raw ids, and let the
   user pick a family (defaulting to its base id) or drill into a specific tier/effort variant
   only if they want one. **Always ask this via `AskUserQuestion` with `multiSelect: true`,
   consistently across every multi-provider CLI (opencode, cursor-agent, claude, or any other) —
   never single-select here, and never decide select-mode per CLI on your own judgment.** A user
   may legitimately want more than one family registered from the same CLI (e.g. both a flagship
   and a fast tier); deciding single- vs multi-select per CLI case-by-case has been observed in
   practice to produce inconsistent behavior across CLIs in the same run (confirmed live: one run
   presented opencode as multi-select and claude as single-select with no principled reason for
   the difference). Collect the chosen model id(s) per CLI, then write a FILTERED runtimes
   snapshot — a copy of `$RUNTIMES_JSON` whose `clis.<cli>.models` arrays are narrowed to only
   the CLIs kept and models chosen above (single-provider CLIs, which have no `models` array to
   narrow, pass through unchanged) — and use that filtered file, not the raw `$RUNTIMES_JSON`,
   as `--runtimes-json` in item 3's `fetch-model-catalog` call below:
   ```bash
   FILTERED_RUNTIMES_JSON="/tmp/filtered-runtimes.json"
   python3 -c "
import json
snap = json.load(open('$RUNTIMES_JSON'))
kept_clis = {<CLI names the user kept>}
chosen = {<cli>: [<chosen model id(s)>], ...}  # only for multi-provider CLIs
snap['clis'] = {name: ({**data, 'models': chosen[name]} if name in chosen else data)
                for name, data in snap.get('clis', {}).items() if name in kept_clis}
json.dump(snap, open('$FILTERED_RUNTIMES_JSON', 'w'))
"
   ```
   This is deliberate: `fetch-model-catalog` has no per-CLI/model selection flag of its own, and
   doesn't need one — its contract (discover everything a runtimes snapshot lists) is unchanged;
   this step scopes discovery upstream, at the input snapshot, before the subcommand ever runs,
   rather than duplicating the family-grouping judgment call this step already makes with the
   user.
2. **For any single-provider CLI (no `models` array — e.g. codex, grok) the user wants to
   consider that has NO existing `review-spec.toml` entry yet** (first-time setup): ask the user
   for a candidate model id now (never guess or trust training knowledge — WebSearch it for
   recency first, per this skill's `NEVER` list; confirmed live 2026-08-28 that guessing here,
   `gpt-5.6-sol-high` instead of the real `gpt-5.6-sol`, produces a candidate that fails
   outright at Step 2.5's live test). Collect these as `--extra-candidate <cli>:<model-id>`
   flags (repeatable) for the next command — this is what lets a brand-new
   single-provider-CLI candidate flow through the SAME matching/enrichment/ranking path as
   everything else, instead of being registered blind.
3. Refresh the catalog (this also picks up anything already in `review-spec.toml` for an
   already-configured single-provider CLI automatically). **Capture its printed JSON to a
   file** — `fetch-model-catalog` prints the FULL reconciled `discovered` candidate list
   (runtimes snapshot + registered single-provider-CLI models + `--extra-candidate`, exactly
   what the subcommand itself used) alongside `unmatched`/`rejections`, so this step never has
   to recompute a partial version of that list later (rebuilding `discovered` from
   `$RUNTIMES_JSON`'s own `models` arrays alone would silently exclude codex/grok/every
   single-provider-CLI candidate from ranking):
   ```bash
   python3 "$TOOLS_PY" fetch-model-catalog --runtimes-json "$FILTERED_RUNTIMES_JSON" \
     --catalog-path "$CATALOG_JSON" --cwd "$(pwd)" --if-stale \
     [--extra-candidate <cli>:<model-id> ...] > /tmp/fetch-model-catalog-result.json
   ```
   `--if-stale` here gates the models.dev/Artificial Analysis NETWORK calls only — candidate
   discovery/reconciliation always runs, so a brand-new model is reflected in this run's
   `unmatched`/`discovered` output even when the catalog itself is still fresh and nothing was
   re-fetched (see the flag's own help text).
   If this is the very first run (no catalog existed at `cache-path --kind catalog` before this
   command ran) and the printed JSON's `artificial_analysis_ok` is `false` with
   `rejections`/`unmatched` non-trivial, or the user asks about richer scores, mention:
   "Artificial Analysis (artificialanalysis.ai) adds intelligence/coding/agentic index scores
   and speed data to model ranking — optional, models.dev alone still gives context window,
   pricing, and tool-calling data. If you have a key, add
   `ARTIFICIAL_ANALYSIS_API_KEY=<key>` to `~/.config/ai-kit/secrets.env` yourself (this skill
   never writes that file), then re-run the command above without `--if-stale` so the fresh key
   gets used." **Never write, create, or edit `secrets.env` from this skill** — reading it is
   `local_secrets.load_secret`'s job; writing it is out of scope everywhere in this design.
   The printed JSON's `unmatched` list drives the next item (item 4 below). `rejections` is not
   currently consumed anywhere in this wizard flow — it's diagnostic output from
   `fetch-model-catalog` only; there is no step today that reads or acts on it.
4. **Unmatched-candidate research and confirmation — BEFORE ranking, never after.** For every
   entry in the captured JSON's `unmatched` list (a candidate that matched neither models.dev
   nor Artificial Analysis and has no prior catalog entry — each entry already carries its own
   locally-inferred `is_router`/`batch_mode`/`fallback_quota`, computed by `fetch-model-catalog`
   itself even though the candidate isn't in the catalog yet): do ONE targeted WebSearch for
   that specific model id + vendor name, summarize what you find in one line, and use
   `AskUserQuestion` to have the user confirm or correct the provider AND the three heuristic
   fields before any of it is ever persisted — this is the only per-model search this step ever
   does now, reserved for genuinely new/unrecognized models (e.g. one released after
   models.dev/Artificial Analysis last indexed it). Never auto-persist an unmatched candidate.

   **The catalog key MUST be re-derived from whatever provider the user actually confirms,
   never reused from `unmatched.key`** (which was computed from the PRE-confirmation provider
   GUESS). If the user corrects the provider, `unmatched.key` and the confirmed `provider`
   would otherwise disagree — violating the catalog's own `vendor/model` key invariant.
   Recompute the key the same way `fetch-model-catalog` itself would, via
   `canonical_key(confirmed_provider, bare_model_id)` — `bare_model_id` is `unmatched.model_id`
   with any `"<cli-provider-label>/"` prefix stripped (the same split `bare_model_part` uses:
   everything after the first `/`, or the whole string if there's no `/`). Do this with the same
   inline `python3 -c` `sys.path.insert` convention item 5 below uses (no separate CLI
   subcommand needed for a pure string computation):
   ```bash
   CONFIRMED_KEY="$(python3 -c "
import sys
sys.path.insert(0, '$(dirname "$TOOLS_PY")')
from ai_kit_spec.model_catalog import canonical_key
bare = '<unmatched.model_id>'.split('/', 1)[-1]
print(canonical_key('<confirmed provider>', bare))
")"
   ```
   Once confirmed, persist it under `$CONFIRMED_KEY` — never under the stale `unmatched.key`.
   This is the ONLY path that ever writes an unmatched candidate to the catalog
   (`fetch-model-catalog` itself deliberately never does):
   ```bash
   cat > /tmp/confirm-entry.json <<'JSON'
{"model_id": "<value of $CONFIRMED_KEY>",
 "entry": {"provider": "<confirmed provider>",
           "runtimes": {"<cli>": {"model_id": "<unmatched.model_id>"}},
           "source": {"models_dev": false, "artificial_analysis": false, "manual": true},
           "confidence": "low", "last_verified": "<today, YYYY-MM-DD>",
           "is_router": <confirmed is_router>, "batch_mode": <confirmed batch_mode>,
           "fallback_quota": <confirmed fallback_quota>,
           "heuristic_confirmed": ["is_router", "batch_mode", "fallback_quota"]}}
JSON
   python3 "$TOOLS_PY" confirm-catalog-entry --catalog-path "$CATALOG_JSON" \
     --entry-json /tmp/confirm-entry.json
   ```
   `heuristic_confirmed` records that the user was JUST asked to confirm all three fields
   above, in this same step — without it, Step 8 later in this same wizard run would re-ask
   `is_router`/`batch_mode`/`fallback_quota` for this same candidate, since it has no other way
   to know those three fields were already confirmed here.
   (When the user does NOT correct the provider — the common case — `$CONFIRMED_KEY` always
   equals `unmatched.key` exactly, since both are `canonical_key` applied to the same provider
   and bare model id; nothing changes for that path.)
5. **Rank only what's actually installed right now** — load the catalog, filter to
   `current_candidate_keys` using the SAME `discovered` list item 3's captured JSON already has
   (never recomputed from `$RUNTIMES_JSON` alone — that would silently drop every
   single-provider-CLI candidate), THEN rank per purpose. A catalog entry for a CLI/model no
   longer present in the current snapshot is excluded from ranking and from anything shown to
   the user, without being deleted from the cache. This is a Python call, not a subcommand; run
   it inline via `python3 -c` — note the explicit `sys.path.insert`, required because this runs
   from an arbitrary cwd, not from inside `ai-kit-spec-review`'s own directory the way `python3
   "$TOOLS_PY"` does (that script's own directory is added to `sys.path` automatically by the
   interpreter; a `python3 -c` snippet gets no such help):
   ```bash
   python3 -c "
import json, sys
sys.path.insert(0, '$(dirname "$TOOLS_PY")')
from ai_kit_spec.model_catalog import current_candidate_keys
from ai_kit_spec.model_ranker import load_ranking_weights, score_candidates
catalog = json.load(open('$CATALOG_JSON'))
fetch_result = json.load(open('/tmp/fetch-model-catalog-result.json'))
discovered = fetch_result['discovered']
current = current_candidate_keys(catalog, discovered)
entries = [{'key': k, **v} for k, v in catalog.items() if k in current]
weights = load_ranking_weights()
def field(e, path, label):
    v = e.get('scores', {}).get(path) if path in ('intelligence_index', 'coding_index', 'agentic_index') else e.get(path)
    if v is None:
        return None
    aa_sourced = path in ('intelligence_index', 'coding_index', 'agentic_index', 'tokens_per_sec')
    tag = ' [via Artificial Analysis]' if aa_sourced and e.get('source', {}).get('artificial_analysis') else ''
    return f'{label} {v}{tag}'

for purpose in ('review', 'execute'):
    ranked = score_candidates(entries, purpose, weights)[:5]
    print(purpose.upper())
    for i, e in enumerate(ranked, 1):
        ctx = max((rt.get('ctx_window') for rt in e.get('runtimes', {}).values()
                   if rt.get('ctx_window')), default=None)
        parts = [field(e, 'intelligence_index', 'intelligence'),
                 field(e, 'coding_index', 'coding'),
                 field(e, 'agentic_index', 'agentic'),
                 field(e, 'tokens_per_sec', 'speed'),
                 (f'ctx {ctx}' if ctx else None),
                 ('tool_call✓' if e.get('tool_calling') else None),
                 ('batch✓' if e.get('batch_mode') else None),
                 ('fallback✓' if e.get('fallback_quota') else None)]
        detail = ', '.join(p for p in parts if p)
        print(f\"  {i}. {e['key']}  score {e['score']}\" + (f'  ({detail})' if detail else ''))
"
   ```
   (The per-field breakdown is deliberate: each field is tagged individually, because `ctx` is
   always models.dev-sourced while `intelligence`/`coding`/`agentic`/`speed` are Artificial
   Analysis-sourced — a single whole-entry tag on the score line could not express that. `coding`
   in particular carries EXECUTE's largest weight, so it must be visible.)
6. Present the top candidates per purpose to the user in this shape (adapt scores/labels to what
   the catalog actually returned — illustrative, not literal output; the exact field set shown
   for a given candidate always matches whatever the `field()` calls above actually found
   non-`None` for it, never more than that). **Every candidate line must also show which
   runtime(s)/CLI(s) it's reachable through** — read this from the entry's own `runtimes` dict
   keys (e.g. `codex`, `opencode`) — never omit it; a user picking a candidate needs to know which
   installed CLI would actually run it, not just its catalog key. **Any field sourced from
   Artificial Analysis (scores, speed, or its pricing when models.dev had no match) carries the
   `[via Artificial Analysis]` tag verbatim, every time it's shown — this is a hard requirement,
   not a nicety: Artificial Analysis's API terms require attribution wherever its data is
   presented.**
   ```
   REVIEW (flagship/reasoning) — top candidates:
     1. openai/gpt-5.6-sol     via codex     score 87  (intelligence 91 [via Artificial Analysis], batch✓, ctx 400k)
     2. xai/grok-4.6           via grok      score 79  (intelligence 85 [via Artificial Analysis], agentic 88 [via Artificial Analysis])
     3. anthropic/router-env   via opencode  score 74  (fallback✓)

   EXECUTE (coding-agent) — top candidates:
     1. anthropic/router-env   via opencode  score 90  (coding 89 [via Artificial Analysis], tool_call✓)  — also ranked #3 in REVIEW above
     2. openai/gpt-5.6-sol     via codex     score 81  — also ranked #1 in REVIEW above
   Any preference not listed, or confirm this order for the ladder?
   ```
   **The SAME catalog key appearing in both lists is expected, not a mistake** — REVIEW and
   EXECUTE score the exact same candidate pool with genuinely different weight profiles
   (`references/ranking-weights.toml`: `coding_index` weight triples for EXECUTE, 0.10→0.30,
   while `intelligence_index` is halved, 0.30→0.15 — see `model_ranker.py`'s `DEFAULT_WEIGHTS`
   for the full table), and a model that's strong across every axis (a "combo" flagship, common
   among today's frontier models) can legitimately score well under both weightings at once. When
   one key shows up in both lists, **always annotate it** (`— also ranked #N in <OTHER_PURPOSE>
   above`, as above) so the user sees it's the same entry ranked twice on purpose, not a
   coincidence.

   **A DIFFERENT failure mode, and the more important one to catch: two DISTINCT keys landing in
   the WRONG or SAME list because the ranking axes couldn't tell them apart.** This happens for a
   router/gateway-style CLI whose own model id already declares its intended purpose in plain
   words — e.g. a provider exposing separate `<name>-plan-review` and `<name>-coding` (or
   `-review`/`-execute`) endpoints — where models.dev/Artificial Analysis has no distinct entry
   for each variant, so both resolve (exact or fuzzy) to the same generic source data and end up
   with near-identical `intelligence_index`/`coding_index`/`agentic_index` scores. The purpose
   the CLI's own name declares then has NO influence on the weighted score at all, and both
   variants can rank into the same list — or the wrong one — even though the CLI operator clearly
   intended them for different roles (confirmed live: a `-plan-review`-suffixed key and a
   `-coding`-suffixed key from the same router both ranked into EXECUTE, when only the
   `-coding` one belonged there). **Before presenting either list, check every candidate's raw
   CLI-reported model id for an explicit purpose word** (`review`, `plan-review`, `coding`,
   `execute`, or similarly unambiguous — not a generic effort/tier token like `high`/`fast`,
   which `_MODEL_TIER_SUFFIXES` already handles separately). If that word contradicts the list
   the axis-based score placed it in (a `-coding` id inside REVIEW, a `-review`/`-plan-review` id
   inside EXECUTE), **do not present it there** — move it to the list its own name declares, and
   say so explicitly to the user (e.g. `"<key> excluded from EXECUTE despite scoring #2 — its own
   name declares it a review-only endpoint"`), rather than trusting the generic score over the
   CLI's own explicit labeling. Ask the user to confirm or adjust. **Record, for every confirmed
   candidate, which list(s) it
   was confirmed from** — REVIEW only, EXECUTE only, or both — this becomes that entry's
   `purpose` value (`"review"`, `"execute"`, or `"both"`) carried forward into Step 2.4's
   command-building and Step 3's write below. **A candidate that comes through this ranked flow
   always gets an explicit `purpose` written — never left absent.** Absent `purpose` is reserved
   strictly for a pre-migration `review-spec.toml` entry that predates this design; every NEW
   entry this wizard writes, from this step or from Step 2.7's native-entry flow below, states
   its `purpose` explicitly (an absent `purpose` reads as "matches both roles" on the consumer
   side, which must never be an accident of a newly-written entry, only the documented
   legacy-compat default). This IS the answer to what used to be a separate `purpose`
   question — see Step 2.6 below.
7. **Before finalizing a CLI outside codegraph support (today: `grok`), check for a
   codegraph-capable alternative.** For each model confirmed onto such a CLI in the previous
   item, run:
   ```bash
   python3 "$TOOLS_PY" check-codegraph-alternative --cli <id> --model <model-id> \
     --runtimes-json "$RUNTIMES_JSON"
   ```
   When `alternative_cli` is non-null, tell the user in one line before they finalize: `"<model>
   is also reachable via <alternative_cli>, which supports codegraph_explore (grok CLI does
   not) — consider registering it through <alternative_cli> instead for grounding-heavy
   review/execute work."` This is informational only (best-effort substring match, per
   `find_codegraph_alternative`'s own docstring) — the user still makes the final call; never
   silently substitute the CLI or drop the original option.
8. Confirm `is_router`/`batch_mode`/`fallback_quota` for any candidate where the catalog set them
   via naming heuristic (never an external source, per the design) — **but skip any field
   already listed in that entry's `heuristic_confirmed` array** (a plain bool alone cannot
   distinguish "the heuristic's own untouched guess" from "the user already confirmed this exact
   value"; `heuristic_confirmed` is the provenance record that makes "don't ask again" actually
   work). For every field NOT yet in `heuristic_confirmed`, ask one line each: "`router-env`
   looks like a router with fallback — correct?" / "`gpt-5-mini` looks batch-suitable —
   correct?" **Persist the answer back to the catalog cache immediately — whether the user
   corrects the value OR simply confirms the heuristic's guess as-is** (so the NEXT run of this
   wizard doesn't ask again either way; calling this only on an actual *change* would leave a
   confirmed-but-unchanged field looking identical to a never-asked one), via the
   `apply-heuristic-correction` subcommand — never a raw `json.dump`/`open`, which bypasses this
   repo's atomic, validated cache-write path:
   ```bash
   cat > /tmp/heuristic-correction.json <<'JSON'
{"is_router": false}
JSON
   python3 "$TOOLS_PY" apply-heuristic-correction --catalog-path "$CATALOG_JSON" \
     --model-id "<key>" --corrections-json /tmp/heuristic-correction.json
   ```
   This call marks `is_router` confirmed in the catalog entry's `heuristic_confirmed` list
   regardless of whether `false` differs from the heuristic's original guess — the JSON body
   above always carries the field's FINAL value (corrected or reconfirmed), and
   `apply_heuristic_corrections` records every key present in that body as confirmed.

#### Step 2.3 — Resolve vendor attribution

**Vendor attribution is deterministic — never infer it from the model name yourself.** For every model id (whether picked from a multi-provider CLI's list or typed by the user for a single-provider CLI), resolve `vendor` by calling:
```bash
python3 "$TOOLS_PY" infer-vendor --model <model-id>
```
When this prints `{"vendor": null}` (no known prefix — e.g. an `ollama-cloud/*` id, or a genuinely new model this table hasn't seen yet), ask the user directly for the real vendor rather than guessing — this is the one case a human still has to supply the answer, and it should be rare (the table in `ai-kit-spec.py`'s `_MODEL_VENDOR_PREFIXES` already covers every model family confirmed live in the CLI profiles).

#### Step 2.4 — Build the command and model id

For each CLI the user wants, read its profile under `$CLI_PROFILES_DIR/<id>.md` for anything CLI-specific this step doesn't already cover (prerequisites, known quirks, plan/entitlement gating — `cursor-agent.md` documents several). **Load only the profile(s) for CLIs actually selected at Step 2.2 — do NOT read the whole `$CLI_PROFILES_DIR` directory or preemptively load profiles for CLIs the user declined.** Each profile is a few KB of quirks relevant to exactly one CLI; loading unselected ones adds noise without informing any decision in this run. **Prefer the factory subcommands below over hand-writing a `command` template or a bracket-parameter model string** — for the CLIs `build_reviewer_command`/`build_reviewer_model_id` already know (`ai-kit-spec.py`'s `_COMMAND_BUILDERS` registry — currently codex, claude, grok, opencode, cursor-agent), the factory encodes verified quoting a hand-written template is easy to get wrong:
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

#### Step 2.6 — Ask about the optional strength attribute; `purpose` comes from Step 2.2

**Also ask, for every entry (CLI or native), an optional `strength`**: `"ui"`, `"coding"`, `"planning"`, or left unset — free text otherwise, not validated. This is informational only — captured in `review-spec.toml` for a human (or a future version of this design) to read, but **not yet consumed by any resolution logic today** (`resolve_reviewers`/`resolve_ladder_pick` ignore it completely). Tell the user this plainly if they ask what it does: it doesn't change dispatch behavior yet, it just gets saved.

**`purpose` is NOT asked here** — it was already captured at Step 2.2 (which ranked list(s), REVIEW/EXECUTE/both, the user confirmed each candidate from). Carry that value forward unchanged into this entry's fields; do not re-ask, and do not silently drop it.

#### Step 2.7 — Ask about native reviewer entries

**Also ask, explicitly — do not skip this**: whether to register one or more **native** (`cli`-omitted) reviewer entries — dispatched via whatever runtime is hosting *this* session, not any one specific model or vendor. Today that host is Claude Code, whose own dispatch mechanism is the `Agent` tool's four tier aliases (`sonnet`/`opus`/`haiku`/`fable`) — but "native" itself is a runtime-agnostic concept: the same config shape (`cli` omitted) is what a future opencode-hosted or Antigravity-hosted run of this same skill would use for *its* own current-session model, whatever that host's own alias/selection mechanism turns out to be. Don't imply in prose or example keys that native means "Claude" or "opus" specifically — call it the current-runtime/native entry, and let its `key` describe the tier (e.g. `native-primary`, `native-fallback`), not the vendor.

Worth asking regardless of `policy.mode`, since it's the only zero-external-dependency reviewer option available (never rate-limited/API-gated the way an external CLI can be) — useful as either a primary pick or a pure fallback, depending on where the user places it in `policy.ladder` at Step 2.8. **A native entry is never automatically prioritized over external ones** — `resolve_reviewers` (`ai-kit-spec.py`) treats every ladder entry identically regardless of native/external; only its position in `policy.ladder` decides priority, and quota/availability failures (never native-vs-external status) decide fallback (changed 2026-08-29 — an earlier design gave native entries an automatic guaranteed-baseline slot in `double` mode regardless of ladder position; a real config hit this and got a silently reordered ladder, so it was removed). If the user wants a native entry as pure fallback, place it LAST in the ladder order at Step 2.8. For each native entry the user wants **on this Claude-Code-hosted run**, `model` must be one of the four `Agent`-tool aliases (`sonnet`/`opus`/`haiku`/`fable`), never a full model id like `"opus-5"`; ask the user to pick one of those four rather than typing a version string. (A different host runtime would substitute its own alias set here — this constraint is Claude Code's dispatch mechanism, not a property of "native" itself.)

**Also ask, for each native entry, the same `purpose` question Step 2.2 answers for CLI-sourced candidates**: should this native entry be used for review, execute, or both? (`"review"` | `"execute"` | `"both"`.) A native entry never goes through Step 2.2's catalog/ranking flow — there is no CLI model id to look up in models.dev/Artificial Analysis for a `sonnet`/`opus`/`haiku`/`fable` alias — so without this question it would get no `purpose` at all, and the consumer side reads an absent `purpose` as "matches both review and execute": an assumption that must be a deliberate, documented legacy-compat default, never an accident of how a brand-new entry happened to get written. A native entry is a real, always-available reviewer/executor choice — it deserves the same explicit curation as any ranked CLI candidate, not a silent default. Carry the answer into this entry's `purpose` field at Step 3's write, exactly like a Step 2.2-sourced entry — never leave it unset for a newly-registered native entry.

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
`strategy` key only when Step 2 asked for `local-only`). **Each object in
`reviewers` now also carries `purpose` (`"review"`/`"execute"`/`"both"`, from
Step 2.2 for a CLI-sourced entry or Step 2.7 for a native one — every entry
this wizard newly registers gets an explicit `purpose`, CLI-sourced or native
alike; absent `purpose` is reserved for a pre-migration entry this run is
merely carrying forward unchanged, never for a brand-new one), and
`is_router`/`fallback_quota` when Step 2.2/2.7 confirmed either as `true`**
(omit when `false`/unknown rather than writing a redundant `false` for every
entry — the consumer side already treats an absent field as "no preference,"
exactly like today's `task_affinity`; that fallback exists for legacy
compatibility, not as this wizard's normal path for a new entry). Write it to a
temp JSON file, then let `--out` do the write directly (via
`cfg_write_toml`, creating parent dirs as needed) rather than piping
stdout through a second write yourself:

```bash
python3 "$TOOLS_PY" render-toml --json-config <temp.json> --out <target path> \
  2> /tmp/render-toml-stderr.txt
```

`<target path>` is the write target Step 2 resolved and already
announced — `./.aikit/review-spec.toml` by default (or explicitly via
`--local`), `~/.config/ai-kit/review-spec.toml` only via `--global` or
because the user picked "update the existing global config" at Step 2's
ask. Never re-derive the target here independently of what Step 2
already resolved and told the user. (The runtimes snapshot was already
persisted in Step 1 via `--save` — no separate write needed here.)
**Capture stderr to `/tmp/render-toml-stderr.txt`** — `cfg_render_toml`
prints a `WARNING:` line there for every `[[reviewers]]` entry it
rejected-and-dropped instead of writing (e.g. a malformed entry), and
this is the ONLY place that warning is ever emitted — Step 4 below reads
this file to decide whether to surface it.

### Step 4 — Report

**First, check `/tmp/render-toml-stderr.txt` for any `WARNING:`-prefixed
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
explicit numbered list (the same list already echoed back during Step 2,
now confirmed as written) — e.g.:
```
Priority fallback order:
  1. codex-gpt
  2. sonnet-native
  3. grok-flagship
```
not folded into a single vague sentence about "reviewers configured in
some order" — the point of this report is that the user can see the
exact fallback sequence without having to open the file.
