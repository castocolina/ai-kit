# Catalog inputs before the proposal

Loaded from `wizard-flow.md` step 2 only: when a preferred runtime has no `models` list, or the catalog step printed unmatched candidates. Each candidate registered from here is a
(runtime, model) pair: Step 2.4 stores `runtime` and `model` (plus that runtime's knobs),
and the runner builds the argv. Only a runtime outside the runner table, grok today,
stores a `command` instead. `$TOOLS_PY`, `$RUNTIMES_JSON` and `$SCRATCH` are the literal
paths SKILL.md's Step 0 printed; every temporary file here goes under `$SCRATCH`. Every `Bash`
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
     --catalog-path "$CATALOG_JSON" --cwd "<project root>" --if-stale \
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
   itself even though the candidate isn't in the catalog yet): show the owner the candidate with its labels, ask the owner to confirm or correct each uncertain field, and write nothing before that answer. A key the catalog already holds takes one correction per field with `confirm-model --catalog-path <catalog> --model-id <key> --field <field> --value <value>`; `confirm-model` refuses a key the catalog lacks (`unknown catalog key`), so a genuinely new candidate is written once with `confirm-catalog-entry --catalog-path <catalog> --entry-json <file>` (`{"model_id": ..., "entry": {...}}`, keeping any effort data the runtime reported), which rejects an invalid entry. Check the command's result before proposing the candidate. Web names come only through `web-query`'s fixed query and `record-web-names`. Never write a catalog entry by hand and never auto-persist an unmatched candidate.

5. **The ranked shortlist comes from `propose-lanes`, never from a hand-built ranking.** Return to [`wizard-flow.md`](wizard-flow.md) step 3: it runs `propose-lanes` once per purpose over the catalog refreshed above, limited to the preferred runtimes, and shows its rows as printed. A runtime-table row never decides which pairs may review or execute: a pair the runner cannot run in a mode is skipped at dispatch with its named reason (route `no_formula`), never dropped from the proposal here.

6. **Before finalizing a CLI where ai-kit cannot read a codebase-memory-mcp registration
   (today: `grok`), check for an alternative whose registration it can read.** For each model the owner kept on such a CLI (`wizard-flow.md` step 6 runs this check for every kept lane), run:
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
7. Router aliases defined by the owner (for example `placeholder-alias-1`) are assumed router with fallback quota and get no heuristic question; the report shows them as assumed.

