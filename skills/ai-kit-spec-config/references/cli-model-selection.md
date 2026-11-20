# Step 2.2 — Pick which runtimes and models to register

Loaded only when this wizard run is registering subprocess reviewers (Step 2.2). A
session-default-only run skips this file. Each candidate registered from here is a
(runtime, model) pair: Step 2.4 stores `runtime` and `model` (plus that runtime's knobs),
and the runner builds the argv. Only a runtime outside the runner table, grok today,
stores a `command` instead. `$TOOLS_PY`, `$RUNTIMES_JSON` and `$SCRATCH` are the literal
paths SKILL.md's Step 0 printed; every temporary file here goes under `$SCRATCH`. Every `Bash`
call starts a fresh shell, so no value set in one block survives into the next: `$CATALOG_JSON`
(item 1) is a literal path too, substituted directly into every later block, never a shell
variable.

For every CLI the user wants to consider (from Step 1's detection), build the ranked
candidate list via the model-discovery catalog rather than guessing or searching per model.
**Order matters here: unmatched candidates are researched and confirmed BEFORE anything is
ranked** — an unconfirmed guess must never appear in a ranked list the user is about to trust.

1. Ensure a runtimes snapshot exists (Step 1 already produces one via `detect-runtimes
   --save`) — reuse `$RUNTIMES_JSON` from Step 0. Resolve the catalog cache path (no manual
   path-string surgery — a dedicated `--kind` exists precisely so this skill never has to
   derive one cache filename from another):
    ```bash
    python3 "$TOOLS_PY" cache-path --kind catalog
    ```
    Record the printed line as the literal absolute path `$CATALOG_JSON` stands for below.
    **The CLIs to consider were already chosen in SKILL.md's Step 2.2 stub** — do not re-ask.
    Build the catalog from the whole snapshot: see [`catalog.md`](catalog.md) `## Build and classify` (the fetch reads the whole snapshot and caches each source by its own age).
2. **For any kept CLI with no `models` array (grok always; codex or pi when its listing
   failed) that has NO existing lane entry in `config.toml` yet** (first-time setup): ask the
   user for a candidate model id now (never guess or trust training knowledge; web names come only from `web-query`'s fixed query and `record-web-names`, never from a model-specific search). Collect these as `--extra-candidate <cli>:<model-id>`
   flags (repeatable) for the next command — this is what lets a brand-new
   single-provider-CLI candidate flow through the SAME matching/enrichment/ranking path as
   everything else, instead of being registered blind.
3. Refresh the catalog (this also picks up, automatically, every model already registered in
   the `config.toml` roster for a kept CLI with no `models` array — a pair's `runtime`, or a custom
   grok entry, recognized by the binary its `{model}` command launches). **Capture its printed JSON to a
   file** — `fetch-model-catalog` prints the FULL reconciled `discovered` candidate list
   (runtimes snapshot + registered single-provider-CLI models + `--extra-candidate`, exactly
   what the subcommand itself used) alongside `unmatched`/`rejections`, so this step never has
   to recompute a partial version of that list later (rebuilding `discovered` from
   `$RUNTIMES_JSON`'s own `models` arrays alone would silently exclude codex/grok/every
   single-provider-CLI candidate from ranking):
   ```bash
   python3 "$TOOLS_PY" fetch-model-catalog --runtimes-json "$RUNTIMES_JSON" \
     --catalog-path "$CATALOG_JSON" --cwd "$(pwd)" --if-stale \
     [--extra-candidate <cli>:<model-id> ...] > "$SCRATCH/fetch-model-catalog-result.json"
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
   itself even though the candidate isn't in the catalog yet): show the owner the candidate with its labels, ask the owner to confirm or correct each uncertain field, and write one correction only with `confirm-model --catalog-path <catalog> --model-id <key> --field <field> --value <value>`. Web names come only through `web-query`'s fixed query and `record-web-names`. Never write a catalog entry by hand and never auto-persist an unmatched candidate.

5. Read `catalog-report` (Step 1.5): use only rows that are not stale; show labels as printed.
6. **Rank only what's actually installed right now** — load the catalog, filter to
   `current_candidate_keys` using the SAME `discovered` list item 3's captured JSON already has
   (never recomputed from `$RUNTIMES_JSON` alone — that would silently drop every
   single-provider-CLI candidate), THEN rank per purpose. A catalog entry for a CLI/model no
   longer present in the current snapshot is excluded from ranking and from anything shown to
   the user, without being deleted from the cache; a kept entry's in-memory `runtimes` is
   narrowed to the pairs in the current snapshot, so a stale cached mapping never makes it
   eligible, shown, or sized through a runtime it no longer runs on. This is a Python call,
   not a subcommand; run it inline via `python3 -c` — note the explicit `sys.path.insert`, required because this runs
   from an arbitrary cwd, not from inside `ai-kit-spec-review`'s own directory the way `python3
   "$TOOLS_PY"` does (that script's own directory is added to `sys.path` automatically by the
   interpreter; a `python3 -c` snippet gets no such help):
   ```bash
   python3 -c "
import json, sys
sys.path.insert(0, '$(dirname "$TOOLS_PY")')
from ai_kit_spec.detection import RUNTIMES
from ai_kit_spec.model_catalog import current_candidate_keys
from ai_kit_spec.model_ranker import load_ranking_weights, score_candidates
catalog = json.load(open('$CATALOG_JSON'))
fetch_result = json.load(open('$SCRATCH/fetch-model-catalog-result.json'))
discovered = fetch_result['discovered']
current = current_candidate_keys(catalog, discovered)
pairs = {(c['runtime'], c['model_id']) for c in discovered}
# Keep only this snapshot's runtime/model pairs: a stale cached mapping must not route.
entries = [{'key': k, **v, 'runtimes': {r: rt for r, rt in v.get('runtimes', {}).items()
                                        if (r, rt.get('model_id')) in pairs}}
           for k, v in catalog.items() if k in current]
name_declared = [e for e in entries if e.get('name_declared_purpose')]
scored = [e for e in entries if not e.get('name_declared_purpose')]
weights = load_ranking_weights()
# Review-only (claude as a subprocess) and runner-less (grok) runtimes never execute.
no_exec = {rid for rid, row in RUNTIMES.items() if row.review_only or not row.runner}
def via(e, purpose):
    return '/'.join(r for r in e.get('runtimes', {}) if purpose == 'review' or r not in no_exec)
def field(e, path, label):
    v = e.get('scores', {}).get(path) if path in ('intelligence_index', 'coding_index', 'agentic_index') else e.get(path)
    if v is None:
        return None
    aa_sourced = path in ('intelligence_index', 'coding_index', 'agentic_index', 'tokens_per_sec')
    tag = ' [via Artificial Analysis]' if aa_sourced and e.get('source', {}).get('artificial_analysis') else ''
    return f'{label} {v}{tag}'

for purpose in ('review', 'execute'):
    ranked = score_candidates([e for e in scored if via(e, purpose)], purpose, weights)[:5]
    print(purpose.upper())
    for e in [d for d in name_declared
              if d.get('name_declared_purpose') == purpose and via(d, purpose)]:
        print(f\"  • {e['key']}  via {via(e, purpose)}  (declared by name -- not scored)\")
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
        print(f\"  {i}. {e['key']}  via {via(e, purpose)}  score {e['score']}\"
              + (f'  ({detail})' if detail else ''))
"
   ```
   (The per-field breakdown is deliberate: each field is tagged individually, because `ctx` is
   always models.dev-sourced while `intelligence`/`coding`/`agentic`/`speed` are Artificial
   Analysis-sourced — a single whole-entry tag on the score line could not express that. `coding`
   in particular carries one of EXECUTE's largest weights, so it must be visible.)

   **EXECUTE lists only pairs that can execute.** `via(e, 'execute')` drops every runtime the
   runtime table marks review-only or runner-less — claude as a subprocess, and grok, whose
   custom command runs only as a reviewer — so a candidate reachable only through those never
   appears in the EXECUTE block, and its EXECUTE-side `via` names only executable runtimes.
   Execution routing would skip such a pick anyway (`review_only`). The one claude pair that
   does execute is a Claude Code alias on a Claude Code host, registered through Step 2.7's
   session-default ask, not this ranked flow.
7. Present the top candidates per purpose to the user in this shape (adapt scores/labels to what
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
   (`load_ranking_weights()` reads `ai-kit-spec-review`'s `references/ranking-weights.toml`:
   EXECUTE weights `coding_index` well above REVIEW and `intelligence_index` well below it —
   read that file for the current values rather than quoting numbers here), and a model that's strong across every axis (a "combo" flagship, common
   among today's frontier models) can legitimately score well under both weightings at once. When
   one key shows up in both lists, **always annotate it** (`— also ranked #N in <OTHER_PURPOSE>
   above`, as above) so the user sees it's the same entry ranked twice on purpose, not a
   coincidence. Ask the user to confirm or adjust. **Record, for every confirmed
   candidate, which list(s) it
   was confirmed from** — REVIEW only, EXECUTE only, or both — this becomes that entry's
   `purpose` value (`"review"`, `"execute"`, or `"both"`) carried forward into Step 2.4's
   pair and Step 3's write below. **A candidate that comes through this ranked flow
   always gets an explicit `purpose` written — never left absent.** Absent `purpose` is reserved
   strictly for an entry migrated from an old roster that predates this design; every NEW
   entry this wizard writes, from this step or from Step 2.7's session-default flow below, states
   its `purpose` explicitly (an absent `purpose` reads as "matches both roles" on the consumer
   side, which must never be an accident of a newly-written entry, only the documented
   legacy-compat default). This IS the answer to the separate `purpose` question — see Step 2.6 below.
8. **Before finalizing a CLI where ai-kit cannot read a codebase-memory-mcp registration
   (today: `grok`), check for an alternative whose registration it can read.** For each model
   confirmed onto such a CLI in item 7, run:
   ```bash
   python3 "$TOOLS_PY" check-code-index-alternative --runtime <id> --model <model-id> \
     --runtimes-json "$RUNTIMES_JSON"
   ```
   When `alternative_cli` is non-null, tell the user in one line before they finalize: `"<model>
   is also reachable via <alternative_cli>, which can carry the codebase-memory-mcp MCP tools
   (grok gets only its CLI form) — consider registering it through <alternative_cli> instead
   for grounding-heavy review/execute work."` This is informational only (best-effort substring
   match, per `find_code_index_alternative`'s own docstring) — the user still makes the final call; never
   silently substitute the CLI or drop the original option.
9. Router aliases defined by the owner (for example `placeholder-alias-1`) are assumed router with fallback quota and get no heuristic question; the report shows them as assumed.

