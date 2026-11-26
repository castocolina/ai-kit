# Catalog inputs before the proposal

Loaded from `wizard-flow.md` only: step 2 reads items 1 to 4 when a preferred runtime has no `models` list or the catalog step printed unmatched candidates; step 6 reads item 6 for every kept lane. Each candidate registered from here is a
(runtime, model) pair: Step 2.4 stores `runtime` and `model` (plus that runtime's knobs),
and the runner builds the argv. Only a CLI outside the runtime table
stores a `command` instead. `$TOOLS_PY` and `$RUNTIMES_JSON` are the literal paths SKILL.md's
Step 0 printed; every temporary file here goes under `$SCRATCH`, made at its first need as
Step 0 says (item 3 below is usually that first need). Every `Bash`
call starts a fresh shell, so no value set in one block survives into the next: `$CATALOG_JSON`
(item 1) is a literal path too, substituted directly into every later block, never a shell
variable.

**Order matters here: unmatched candidates are researched and confirmed BEFORE the proposal runs** — an unconfirmed guess must never appear in a list the user is about to trust.

1. Ensure a runtimes snapshot exists (Step 1 already produces one via `detect-runtimes
   --save`) — reuse `$RUNTIMES_JSON` from Step 0. Resolve the catalog cache path (no manual
   path-string surgery — a dedicated `--kind` exists precisely so this skill never has to
   derive one cache filename from another):
    ```bash
    python3 "$TOOLS_PY" cache-path --kind catalog
    ```
    Record the printed line as the literal absolute path `$CATALOG_JSON` stands for below. Step 1.5
    printed the same path first (`catalog.md` `## Catalog path`); carry it forward.
    **The runtimes to consider are the preferred runtimes of `wizard-flow.md` step 1** — do not re-ask.
    Build the catalog from the whole snapshot: see [`catalog.md`](catalog.md) `## Build and classify` (the fetch reads the whole snapshot and caches each source by its own age).
2. **For any kept CLI with no `models` array (a CLI without a listing command; codex or pi when its listing
   failed) that has NO existing lane entry in `config.toml` yet** (first-time setup): ask the
   user for a candidate model id now (never guess or trust training knowledge; web names come only from `web-query`'s fixed query and `record-web-names`, never from a model-specific search). Collect these as `--extra-candidate <cli>:<model-id>`
   flags (repeatable) for the next command — this is what lets a brand-new
   single-provider-CLI candidate flow through the SAME matching/enrichment/ranking path as
   everything else, instead of being registered blind.
3. Refresh the catalog (this also picks up, automatically, every model already registered in
   the `config.toml` roster for a kept CLI with no `models` array — a pair's `runtime`, or a custom
   command wrapping a binary of a current RUNTIMES row, recognized by that binary through its `{model}` command; any other custom command is not discovered). **Capture its printed JSON to a
   file** — `fetch-model-catalog` prints the FULL reconciled `discovered` candidate list
   (runtimes snapshot + registered single-provider-CLI models + `--extra-candidate`, exactly
   what the subcommand itself used) alongside `unmatched`/`rejections`, so this step never has
   to recompute a partial version of that list later (rebuilding `discovered` from
   `$RUNTIMES_JSON`'s own `models` arrays alone would silently exclude codex/every
   single-provider-CLI candidate from ranking):
   ```bash
   python3 "$TOOLS_PY" fetch-model-catalog --runtimes-json "$RUNTIMES_JSON" \
     --catalog-path "$CATALOG_JSON" --cwd "<project root>" --if-stale \
     [--extra-candidate <cli>:<model-id> ...] > "$SCRATCH/fetch-model-catalog-result.json"
   ```
   On the keep form of `catalog.md`'s "Pending old roster" section, prefix it with
   `AI_KIT_KEEP_MIGRATION_BACKUP=1`, as every fetch; when that section ruled fetching out, skip
   this item.
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
   `ARTIFICIAL_ANALYSIS_API_KEY=<key>` to `secrets.env` in the user config folder,
   `${XDG_CONFIG_HOME:-~/.config}/ai-kit/` (an absolute `XDG_CONFIG_HOME` only, the same rule as
   the config reader), yourself, or export it as an environment variable (this skill never writes
   that file), then re-run the command above without `--if-stale` so the fresh key
   gets used." **Never write, create, or edit `secrets.env` from this skill** — reading it is
   `local_secrets.load_secret`'s job; writing it is out of scope everywhere in this design.
   The printed JSON's `unmatched` list drives the next item (item 4 below). `rejections` is not
   currently consumed anywhere in this wizard flow — it's diagnostic output from
   `fetch-model-catalog` only; there is no step today that reads or acts on it.
4. **Unmatched-candidate research and confirmation — BEFORE ranking, never after.** For every
   entry in the captured JSON's `unmatched` list (a candidate that matched neither models.dev
   nor Artificial Analysis and has no prior catalog entry — each entry already carries its own
   locally-inferred `is_router`/`batch_mode`/`fallback_quota`, computed by `fetch-model-catalog`
   itself even though the candidate isn't in the catalog yet): show the owner the candidate with its labels, ask the owner to confirm or correct each uncertain field, and write nothing before that answer. A key the catalog already holds takes one correction per field with `confirm-model --catalog-path <catalog> --model-id <key> --field <field> --value <value>`; `confirm-model` refuses a key the catalog lacks (`unknown catalog key`), so a genuinely new candidate is written once with `confirm-catalog-entry --catalog-path <catalog> --entry-json <file>` (keeping any effort data the runtime reported as that runtime's `efforts` list), which rejects an invalid entry. Check the command's result before proposing the candidate. Web names come only through `web-query`'s fixed query and `record-web-names`. Never write a catalog entry by hand and never auto-persist an unmatched candidate.

   The `<file>` (written under `$SCRATCH`) holds the canonical key `<provider>/<bare model id>` and the five fields the validator requires (`provider`, a non-empty `runtimes` map from each runtime id to that runtime's own `model_id`, `source` as an object, `confidence` of `high`, `medium` or `low`, and `last_verified` as `YYYY-MM-DD`), plus the heuristic fields the owner confirmed. This shape, with invented placeholders and today's date in `last_verified`, passes `confirm-catalog-entry` against a scratch catalog:

   ```json
   {"model_id": "fake/placeholder-model-1",
    "entry": {"provider": "fake",
              "runtimes": {"opencode": {"model_id": "fake/placeholder-model-1"}},
              "source": {}, "confidence": "low", "last_verified": "2026-11-25",
              "is_router": false, "batch_mode": false, "fallback_quota": false,
              "heuristic_confirmed": ["is_router", "batch_mode", "fallback_quota"]}}
   ```

   When the owner cannot give a required value (the provider, or the runtime's own id), write no entry: the candidate is not proposed, and the owner names another model or takes the session default (`wizard-flow.md` step 7).

5. **The ranked shortlist comes from `propose-lanes`, never from a hand-built ranking.** Return to [`wizard-flow.md`](wizard-flow.md) step 3: it runs `propose-lanes` once per purpose over the catalog refreshed above, limited to the preferred runtimes, and shows its rows as printed. A runtime-table row never decides which pairs may review or execute: a pair the runner cannot run in a mode is skipped at dispatch with its named reason (route `no_formula`), never dropped from the proposal here.

6. **Before finalizing each kept lane, check for an alternative CLI whose codebase-memory-mcp
   registration ai-kit can read** (`wizard-flow.md` step 6 runs this for every kept lane). Only a CLI
   whose registration ai-kit cannot read (a custom entry or a CLI outside the runtime table) can get
   a non-null `alternative_cli`; a table runtime with a readable registration prints null and needs no
   owner line. Run:
   ```bash
   python3 "$TOOLS_PY" check-code-index-alternative --runtime <id> --model <model-id> \
     --runtimes-json "$RUNTIMES_JSON"
   ```
   When `alternative_cli` is non-null, tell the user in one line before they finalize: `"<model>
   is also reachable via <alternative_cli>, which can carry the codebase-memory-mcp MCP tools
   (<id> gets only its CLI form) — consider registering it through <alternative_cli> instead
   for grounding-heavy review/execute work."` This is informational only (best-effort substring
   match, per `find_code_index_alternative`'s own docstring) — the user still makes the final call; never
   silently substitute the CLI or drop the original option.
7. Router aliases defined by the owner (for example `placeholder-alias-1`) are assumed router with fallback quota and get no heuristic question; the report shows them as assumed.

