# Step 2.2 — Pick which CLIs and models to register

Loaded only when this wizard run is registering CLI-sourced reviewers (Step 2.2). Native-only runs skip this file.

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
    **The CLIs to consider were already chosen in SKILL.md's Step 2.2 stub** — do not re-ask.
    Group each kept multi-provider CLI's raw model list BEFORE any of it is
    discovered/matched/ranked. For each CLI the user kept, if it's multi-provider
    (`models` array present — e.g. `opencode`, `cursor-agent`), **never hand its raw
    model list to `fetch-model-catalog` as-is** — a
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
name_declared = [e for e in entries if e.get('name_declared_purpose')]
scored = [e for e in entries if not e.get('name_declared_purpose')]
weights = load_ranking_weights()
def field(e, path, label):
    v = e.get('scores', {}).get(path) if path in ('intelligence_index', 'coding_index', 'agentic_index') else e.get(path)
    if v is None:
        return None
    aa_sourced = path in ('intelligence_index', 'coding_index', 'agentic_index', 'tokens_per_sec')
    tag = ' [via Artificial Analysis]' if aa_sourced and e.get('source', {}).get('artificial_analysis') else ''
    return f'{label} {v}{tag}'

for purpose in ('review', 'execute'):
    ranked = score_candidates(scored, purpose, weights)[:5]
    print(purpose.upper())
    for e in [d for d in name_declared if d.get('name_declared_purpose') == purpose]:
        runtimes_str = '/'.join(e.get('runtimes', {}).keys())
        print(f\"  • {e['key']}  via {runtimes_str}  (declared by name -- not scored)\")
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
   **Before printing each purpose's ranked block, first list any `name_declared` entries
   whose `name_declared_purpose` matches that purpose** (e.g. `"review"` entries prepend
   to the REVIEW block, `"execute"` entries prepend to the EXECUTE block), each on its own
   bullet line marked `(declared by name -- not scored)`, showing its runtime/CLI the same
   way a scored candidate does. A name-declared entry never appears in the other purpose's
   block, never gets a numbered rank, and is never annotated with a cross-reference to the
   other list (unlike a genuine scored "combo" model, which can legitimately appear in
   both -- see below) -- its position is fixed by its own declared purpose, not earned by a
   score.
   ```
   REVIEW (flagship/reasoning) — top candidates:
     • router-env-plan-review  via opencode  (declared by name -- not scored)
     1. openai/gpt-5.6-sol     via codex     score 87  (intelligence 91 [via Artificial Analysis], batch✓, ctx 400k)
     2. xai/grok-4.6           via grok      score 79  (intelligence 85 [via Artificial Analysis], agentic 88 [via Artificial Analysis])
     3. anthropic/router-env   via opencode  score 74  (fallback✓)

   EXECUTE (coding-agent) — top candidates:
     • router-env-coding       via opencode  (declared by name -- not scored)
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
   coincidence. Ask the user to confirm or adjust. **Record, for every confirmed
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

