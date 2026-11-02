# Model catalog and discovery: what exists, what the sources offer, what is missing

Research date: 2026-11-02. Read-only. Helper scripts in this folder: `7-catalog-sample.py`
(summarizes the real cache), `7-fetch-sources.py` (models.dev field census),
`7-arena-hf-probe.py` (official Arena dataset over JSON), `7-arena-probe.py` (third-party
mirror, got HTTP 429). Downloads are in `7-downloads/` (AA OpenAPI YAML, models.dev api.json).

## Main findings

1. **The next real refresh will break the cheap-execution ranking.** Artificial Analysis no
   longer publishes a Coding Index or an Agentic Index. Its OpenAPI spec says both fields are
   "Always null". The ranker gives both axes weight in every purpose, and the `mechanical`
   purpose has a floor on raw `coding_index` (35), where a missing value excludes the
   candidate. The cache is on schema 2 and the code is on schema 3, so the next
   `fetch-model-catalog --if-stale` run fetches again whatever the TTL says. That run writes
   null coding/agentic scores, and from then on every mechanical candidate is excluded. Source:
   the OpenAPI spec only. I did not call the live API with the key.
2. The catalog stores no tier, class or strengths, and no video/audio/output modalities. It
   keeps only one flag, `image_input`. Effort levels (`reasoning_modes`) are stored for 7 of 195
   entries. Both models.dev and the official Arena dataset carry the data needed for most of the
   owner's list.
3. Nothing that built the catalog recorded the owner's capability wishes. The catalog was built
   outside GSD (a superpowers design spec, 2026-09-02, and commit `b9c14aa` on 2026-09-04), and
   later extended in v1.3 phase 16. Neither one mentions tiers, video, UI, security or a planning
   strength.
4. Copilot CLI is installed (1.0.105) and has a `RUNTIMES` row, but it has no model-list command.
   Its model list exists only as the documented enum in `copilot help config`.

## 1. Existing catalog code

**Fetchers.** `skills/ai-kit-spec-review/ai_kit_spec/model_sources.py`:
- `fetch_models_dev()`: one unauthenticated GET of `https://models.dev/api.json`, sent with a
  custom User-Agent (urllib's default UA gets a 403).
- `fetch_artificial_analysis(api_key)`: `GET /api/v2/language/models/free?page=N` with an
  `x-api-key` header. It keeps paging while `pagination.has_more` is true. With no key it
  returns `([], True)` and is skipped. A failure partway through paging returns `ok=False`.
- Both return `(data, ok)` and never raise.

**Key loading.** `local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY")` checks the env
var first, then `~/.config/ai-kit/secrets.env` (flat KEY=VALUE lines).

**Build.** `catalog_build.build_model_catalog(discovered, sources, existing, runtime_meta)`:
- matches each `{runtime, model_id}` from the runtimes snapshot against both sources (fuzzy,
  in `model_matcher.py`);
- merges the result under `provider/model` through `model_catalog.merge_catalog_entry`, which
  validates the entry and merges `runtimes`; an explicit None clears a field;
- adds name heuristics on first discovery (`model_heuristics.py`);
- returns candidates that match neither source as `unmatched`. These go to the wizard for
  confirmation and are not written.

**CLI entry.** `ai-kit-spec.py fetch-model-catalog --runtimes-json <snapshot> --catalog-path
<path> [--if-stale] [--cwd] [--extra-candidate CLI:MODEL]`. It is handled by
`_cmd_fetch_model_catalog` in `ai_kit_spec/cli.py`.

**Callers:**
- the `ai-kit-spec-config` wizard (SKILL.md and `references/cli-model-selection.md`);
- `ai-kit-gsd-curated-config` through `catalog_adapter._run_refresh`, which runs
  detect-runtimes and then fetch-model-catalog as subprocesses.

**Readers:**
- `model_ranker.py`, with weights in `references/ranking-weights.toml`;
- `routing.py` and `runner_dispatch.py`;
- curated-config's `inventory.py`, `roles.py` and `gsd_catalog.py`;
- `ai-kit-usage-metrics/pricing.py`;
- `ai-kit-opencode-providers/cross_reference.py`.

**Location.** `${XDG_CACHE_HOME:-~/.cache}/ai-kit/spec/model-catalog.json`, plus the sidecar
`model-catalog.json.fetch-meta.json` (`{"last_fetched": <epoch>}`).

**Cache rule.** `CATALOG_TTL_SECONDS` is 30 days. A fetch is skipped only when `--if-stale` is
set, the sidecar's mtime is younger than 30 days, and `_meta.schema_version` is at least the
code's version (3). The sidecar is written only when a source answered, so frequent catalog
writes do not keep it looking fresh.

**`_meta` today:** `schema_version` (the code writes 3; the live cache still holds 2),
`anthropic_model_ids` (17 entries), `anthropic_model_ids_as_of` (2026-10-15).

### Fields stored per entry

Coverage counts are from the live cache: 195 entries, last fetched 2026-10-15.
- **Required (5):** `provider`, `runtimes` (`{<runtime>: {model_id, ctx_window}}`),
  `source` (`{models_dev, artificial_analysis, manual}` booleans), `confidence`
  (high/medium/low), `last_verified` (YYYY-MM-DD).
- **Heuristics:** `is_router`, `batch_mode`, `fallback_quota` (195 each, from naming),
  `heuristic_confirmed`.
- **From models.dev:** `tool_calling` (164), `structured_output` (135), `max_output_tokens`
  (164), `image_input` and `image_input_source` (164).
- **Pricing:** `pricing` `{input_per_1m, output_per_1m}` (192). models.dev comes first, AA
  fills in when models.dev has no match.
- **From AA:** `scores` `{intelligence_index, coding_index, agentic_index}` (150),
  `tokens_per_sec` (140).
- **From the CLI:** `reasoning_modes` (7: codex `debug models`, opencode/pi via the snapshot).
- **From the name:** `name_declared_purpose` (review/execute; 2 entries).
- **Validated but unused in the cache:** `native`, `fast_mode`, `speed_tier`.

Runtime keys in the cache: cursor-agent 143, opencode 35, claude 17, codex 7, **pi 0**. The cache
predates pi enumeration and still uses the old `cursor-agent` key, which the schema-3 split
renames. In the 2026-10-30 runtimes snapshot, pi lists 180 models, opencode 39, codex 8,
claude 17, cursor **0** and copilot 0. Why cursor shows 0 there was not checked.

**Category derivation today.** There is no tier field. The user's convention (flagship → review,
coding-agentic → execute, a router combo → one entry) appears only as:
- `name_declared_purpose`, set by name heuristics (router names such as `*referee*` and
  `*coding*`, in `model_heuristics.py`);
- the ranker's per-purpose weights: review, execution, planning, general, mechanical;
- the wizard's free-text `strength` field ("ui"/"coding"/"planning") in spec-config Step 2.6.

### Redacted sample entry (real cache, no secrets in it)

```json
"anthropic/claude-fable-5-1": {
  "provider": "anthropic",
  "runtimes": {"claude": {"model_id": "claude-fable-5-1", "ctx_window": 1000000}},
  "is_router": false, "batch_mode": false, "fallback_quota": false,
  "source": {"models_dev": true, "artificial_analysis": true, "manual": false},
  "confidence": "high", "last_verified": "2026-10-15",
  "tool_calling": true, "structured_output": true, "max_output_tokens": 128000,
  "image_input": true, "image_input_source": "models_dev",
  "pricing": {"input_per_1m": 10, "output_per_1m": 50},
  "scores": {"intelligence_index": 53.4, "coding_index": 81.6, "agentic_index": 57.9},
  "tokens_per_sec": 71.08
}
```

### The owner's wanted properties: stored, derivable, or missing

- **Tier, 4 or more levels, shifting with effort.** Missing. It can be derived:
  - The Arena dataset rates each effort variant separately ("Claude Opus 5.5 (Max)", "Claude
    Sonnet 5.5 (xHigh)").
  - models.dev `reasoning_options` lists the effort values per model.
  - The AA intelligence index is per model, and AA lists effort variants as separate models
    (e.g. "GLM-5.3 (Max)").
  - So the tier has to be stored per (model, effort), not per model.
- **Class (agentic, lightweight or frontier).** Missing. It can be derived from the
  intelligence index, price, speed and the Arena `agent` board. `name_declared_purpose` covers
  only router names.
- **Relative cost.** Stored as absolute USD per 1M tokens. A relative band can be derived.
  Cache read/write prices are dropped today, although both sources offer them. Subscription
  plans are not encoded anywhere (models.dev has none; see the llm-env research).
- **Modalities.** Only `image_input` (a bool) is stored. models.dev has full
  `modalities.input` (text, image, video, audio, pdf) and `modalities.output` (text, image,
  audio, video), plus `attachment`. "View versus edit images" maps to an image input versus an
  image output, or to the Arena `image_edit` board. Not stored today.
- **Strength: UI web.** Missing. Derivable from Arena `webdev` (categories `webdev`,
  `webdev-html`, `webdev-react`, `image_to_webdev`).
- **Strength: TUI.** Missing, and no source measures it. It would need a manual or jev
  classification, flagged as such.
- **Strength: security.** Missing, and no public per-model security index was found. Arena has
  none. The AA free tier has domain indexes (engineering, legal and others) but no security
  index. It would need a manual or jev classification, flagged.
- **Strength: agentic plan execution.** Partly stored (`agentic_index`), but that field is now
  always null upstream. Derivable from the Arena `agent` boards (task outcome, tool
  hallucination, steerability, bash reliability) and from AA Pro's terminalbench and tau2 scores
  (Pro only).
- **Strength: planning.** Missing. A proxy is the intelligence index plus Arena `text` with the
  `hard_prompts`, `expert` or `coding` categories.
- **Cache time.** Stored: one global 30-day TTL and the sidecar epoch. Not per source.
- **Per-runtime discovery.**
  - Stored: claude, codex, opencode, cursor and pi through the snapshot.
  - Not stored: copilot.
- **Other source fields the catalog drops today:**
  - from models.dev: `release_date`, `knowledge`, `open_weights` and `status`;
  - from AA: TTFT and the six domain indexes.

## 2. The phase that built it, and whether the owner's wishes were recorded

- **Original build.** No GSD phase built the catalog. `docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md`
  (commit `f9a6d75`) and the implementation (`b9c14aa`, 2026-09-04) have no discussion log.
  Their goal was "rank candidates by *purpose* (review/analysis vs. execution)". Their sources
  section names only context, pricing, tool calling, structured output, "modalities" and the
  three AA indexes.
- **Extension.** `.planning/milestones/v1.3-phases/16-ai-kit-spec-extensions/16-DISCUSSION-LOG.md`
  (2026-09-23) has a "Catalog fields" area with two questions only: reuse `reasoning_modes`,
  and source `image_input` from "models.dev modalities, then opencode `--verbose`; absent means
  unknown". Its "Ranker & cache" area settled the mechanical floor and the `schema_version` bump.
- **Verdict.** Neither one recorded tiers, effort-dependent tiers, the agentic/lightweight/frontier
  class, video or edit modalities, or the UI, security or planning strengths. These wishes
  appear for the first time in `.planning/milestones/NEXT-MILESTONE-INPUTS.md` (around line 451).
  The only earlier trace is the 2026-08-29 memory note (flagship → review, coding-agentic →
  execute, a router combo → one entry). The note itself says it is "not yet fully encoded into"
  Step 2.6, which only offers a free-text `strength`.

## 3. Artificial Analysis

Sources: https://artificialanalysis.ai/data-api/docs and the OpenAPI spec at
`https://artificialanalysis.ai/api/v2/openapi` (YAML, saved as `7-downloads/aa-openapi.yaml`).

- **Auth and limits.** Auth is the `x-api-key` header. The free tier allows 100 requests per
  fixed 24-hour window. The window starts at the first request, and the quota is shared across
  the user's or org's keys. Rate-limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
  `X-RateLimit-Reset`, `X-AA-Tier`.
- **Attribution and terms.** Attribution is required on every tier ("credit Artificial Analysis
  as the source; a visible byline or footer link is sufficient"). Use is also subject to the
  Terms of Use and Data Platform Terms, and redistribution needs a contract. For ai-kit, keep
  the downloaded file private in the user's cache, never commit it, and credit AA wherever its
  numbers are shown.
- **Free endpoints:**
  - `/api/v2/language/models/free`;
  - media `.../models/free` endpoints for text-to-image, image-editing, text-to-video,
    image-to-video, text/image-to-video-audio, text-to-speech, speech-to-speech,
    speech-to-text, and music (instrumental, with vocals).
  - The image and video media boards carry an Arena-style `elo`. It is AA's own media arena,
    not LMArena text or code.
- **Pro and Commercial only.** `/language/models` (full shape), `/language/models/{slug}`,
  `/{slug}/performance`, and `/language/providers*` (Commercial).
- **Free language model fields:**
  - identity: `id`, `name`, `slug`, `release_date`, `model_creator{id,name}`;
  - `evaluations`: `artificial_analysis_intelligence_index` (now index version 5);
    `..._coding_index` and `..._agentic_index`, **always null**; and six domain indexes
    (finance_and_accounting, strategy_and_ops, legal, healthcare_and_medical, engineering,
    economics);
  - `artificial_analysis_intelligence_index_cost{total_cost, cost_per_task}`;
  - `pricing{price_1m_input_tokens, price_1m_output_tokens, price_1m_cache_hit_tokens,
    price_1m_cache_write_tokens}`;
  - `performance{median_output_tokens_per_second, median_time_to_first_token_seconds,
    median_time_to_first_answer_token_seconds, median_end_to_end_response_time_seconds}`.
- **Pro only.** `reasoning_model`, `context_window_tokens`, `parameters`, `modalities`,
  `licensing`, `openrouter_api_id`, token counts, and per-benchmark scores such as
  terminalbench, tau2, scicode, ifbench, hle, gpqa_diamond, frontiercode, gdpval_aa_elo and
  aa_briefcase_elo.
- **What ai-kit uses today.** The intelligence/coding/agentic indexes, output tokens per second
  and input/output price. The coding and agentic values now come back null.
- **Key location (path and size only):**
  - `/var/home/bazzite/git/llm-env/tmp/aa-key.txt`, 36 bytes. Its name suggests the AA key.
  - `~/.config/ai-kit/secrets.env`, 132 bytes, with exactly one `ARTIFICIAL_ANALYSIS_API_KEY=`
    line. This is where ai-kit already reads the key from.
  - Nothing matched in this repo's `tmp/`.
  - `.planning/PROJECT.md` says "Artificial Analysis key: set". Whether the two files hold the
    same value was not compared.

## 4. Arena ELO (the OmniRoute source)

- **What OmniRoute uses.** Already researched in llm-env
  (`/var/home/bazzite/git/llm-env/docs/prds/omniroute-smart-routing-research/data-sources-quota.md`
  §2 and `strategies-fusion.md` §5, read from OmniRoute's source and the running container).
  - `src/lib/arenaEloSync.ts` fetches
    `https://api.wulong.dev/arena-ai-leaderboards/v1/leaderboard?name={text|code}` daily
    (`ARENA_ELO_SYNC_INTERVAL` 86400 s, on by default).
  - That endpoint is a **third-party, unofficial mirror** (GitHub `oolong-tea-2026/arena-ai-leaderboards`,
    MIT code, data scraped from arena.ai). It covers only the top 20 per board.
  - OmniRoute min-max normalizes the ratings into a `taskFit` factor.
  - The mirror returned HTTP 429 to my probe today.
- **Official, stable source.** The Hugging Face dataset `lmarena-ai/leaderboard-dataset`
  (announced on the arena.ai blog "Arena Leaderboard Dataset").
  - **License:** CC-BY-4.0, so attribution is required.
  - **Format:** parquet on HF, but readable as plain JSON through
    `https://datasets-server.huggingface.co/rows?dataset=lmarena-ai/leaderboard-dataset&config=<board>&split=latest&offset=0&length=100`.
    That keeps the code stdlib-only; verified live with `7-arena-hf-probe.py`.
  - **Splits:** `latest` and `full` (history).
  - **Cadence:** not stated. The latest `leaderboard_publish_date` is 2026-10-28, i.e. a few
    days old.
  - **Boards (23 configs):** `text`, `text_style_control`, `text_factuality`, `webdev`,
    `vision` (and style control), `search*`, `document*`, `agent` plus six agent sub-signals
    (bash_recovery_steps, bash_reliability, praise_complaint, steerability,
    task_outcome_explicit, tool_hallucination), and `text_to_image`, `image_edit`,
    `text_to_video`, `image_to_video`, `video_edit`. There is no separate `code` board in the
    official dataset: code is `webdev` plus the text `coding` category.
  - **Columns:** `model_name`, `organization`, `license`, `rating`, `rating_lower`,
    `rating_upper`, `variance`, `vote_count`, `rank`, `category`, `leaderboard_publish_date`.
    The agent boards use `score`, CI, `observation_count` and `session_count` instead.
  - **Categories:** `text` has 29 (coding, hard_prompts, expert, math, instruction_following,
    multi_turn, creative_writing, industry_software_and_it_services, languages, and others).
    `webdev` has 5 (overall, webdev, webdev-html, webdev-react, image_to_webdev). `vision` has
    11 (ocr, diagram, and others).
  - **Size:** `webdev` latest is 655 rows and `text` latest is 11,132 rows, across all
    categories. Coverage is far wider than the mirror's top 20.
- **Caveats** (from the llm-env research): votes reward length and style unless the
  style-control boards are used; private-variant selection bias (arXiv 2504.20879); new models
  have wide confidence intervals; ratings are per effort variant. Use Arena as a secondary
  "taste" signal with the confidence shown, not as the main score.

## 5. models.dev fields (live census: 235 providers, 8,931 provider-models)

- **Every entry has:** `id`, `name`, `description`, `attachment`, `reasoning`, `tool_call`,
  `release_date`, `last_updated`, `modalities.input`, `modalities.output`, `open_weights`,
  `limit.context`, `limit.output`.
- **Most entries have:** `temperature`, `cost.input` and `cost.output` (8,533), `family`
  (8,487), `canonical_model_id` (7,615; the cross-provider join key), `reasoning_options`
  (6,844, e.g. `[{type: effort, values: [low, medium, high, xhigh, max]}]`),
  `structured_output` (6,788), `cost.cache_read` (6,246), `knowledge` (5,206).
- **Fewer entries have:** `cost.cache_write`, `limit.input`, `interleaved`, `status`,
  `cost.tiers`, `cost.context_over_200k`, `cost.reasoning`, `cost.input_audio`/`output_audio`,
  `experimental.modes`.
- **Input modalities:** text 8,891, image 5,655, pdf 2,368, video 1,652, audio 803.
- **Output modalities:** text 8,719, image 189, audio 78, video 69.
- **Providers relevant here:** `github-copilot` exists (36 models, e.g. claude-opus-5.5,
  claude-fable-5.1, gemini-3.5-flash), and so do `anthropic` and `opencode`. `cursor` is absent.
- No upstream refresh cadence is published. OmniRoute syncs daily.

## 6. Copilot CLI and the other runtimes' model listing

- **Copilot.** `command -v copilot` gives `/home/linuxbrew/.linuxbrew/bin/copilot`, version
  "GitHub Copilot CLI 1.0.105".
  - Model-related flags: `--model <model>` (`auto` lets Copilot pick),
    `--reasoning-effort none|minimal|low|medium|high|xhigh|max`,
    `--context default|long_context`, `--auto-tier <profile>` (efficiency, balance or
    intelligence), and per-subagent model/effort settings in config.
  - BYOK through `COPILOT_PROVIDER_BASE_URL`, `COPILOT_PROVIDER_TYPE` and `COPILOT_MODEL`
    (`copilot help providers`).
  - **No list-models subcommand.** The only machine-readable list is the `model` enum in
    `copilot help config` (31 ids, e.g. claude-opus-5.5, gpt-6.1-sol, gemini-4-argon, grok-4.7,
    kimi-k3). Parsing that help text is fragile and should be flagged as reverse-engineered.
    The interactive `/model` picker may show what is actually entitled, but that was not
    checked.
  - **In `RUNTIMES`:** yes, `"copilot": Runtime(("copilot",), (), runner=True)`. It has no
    host signal, no `list_argv` and no `model_suffix`, and the code comments say its runner rows
    are unverified. The snapshot shows `installed: true`, `models: 0`.
- **Claude.** There is no list command. The four native aliases (fable, opus, sonnet, haiku)
  are hardcoded. Full ids come from models.dev's anthropic provider via the catalog
  (`models_source: catalog`), with a dated in-code fallback.
- **Cursor.** `cursor-agent models` (or `agent models`), with an effort suffix in brackets
  `[...]`; multi-provider.
- **Pi.** `pi --mode rpc --offline --no-session ...` with the RPC request
  `{"type":"get_available_models"}`. The effort suffix is `:off|minimal|low|medium|high|xhigh|max`.
  The response also carries `context_window`, `max_tokens`, `image_input` and
  `reasoning_modes`.
- **Opencode.** For comparison only: `opencode models`, effort suffix `#<variant>`. See note 6
  for opencode v2.

## Proposal: the catalog file shape (a proposal, not decided)

The goal is one file that covers the owner's list. Every derived or judged field carries its
provenance so its confidence is visible.

```jsonc
{
  "_meta": {
    "schema_version": 4,
    "sources": {                       // per-source fetch time + TTL, replaces one global TTL
      "models_dev":   {"fetched_at": "...", "ttl_days": 7,  "ok": true},
      "artificial_analysis": {"fetched_at": "...", "ttl_days": 7, "ok": true,
                              "index_version": 5, "attribution": "Artificial Analysis"},
      "arena":        {"fetched_at": "...", "ttl_days": 7, "publish_date": "2026-10-28",
                       "license": "CC-BY-4.0", "boards": ["text","webdev","vision","agent"]},
      "runtimes":     {"fetched_at": "...", "ttl_days": 1}   // CLI listings change fastest
    }
  },
  "anthropic/claude-opus-5-5": {
    // identity and the existing required fields stay as they are
    "provider": "anthropic", "family": "claude-opus", "canonical_model_id": "...",
    "release_date": "...", "knowledge": "...", "open_weights": false, "status": null,
    "runtimes": {                      // every runtime that lists it, incl. copilot
      "claude":  {"model_id": "opus", "ctx_window": 1000000, "efforts": ["low","medium","high","xhigh","max"]},
      "copilot": {"model_id": "claude-opus-5.5", "efforts": [...], "listing": "help-enum"}
    },
    "modalities": {"input": ["text","image","pdf"], "output": ["text"]},   // full lists
    "capabilities": {"tool_calling": true, "structured_output": true, "reasoning": true},
    "pricing": {"input_per_1m": 5, "output_per_1m": 25, "cache_read_per_1m": 0.5,
                "relative": "high"},   // relative band derived from the price distribution
    "scores": {                        // raw numbers, each with its source
      "aa": {"intelligence_index": 0, "engineering_index": 0, "tokens_per_sec": 0, "ttft_s": 0},
      "arena": {"text": {"rating": 0, "ci": [0, 0], "votes": 0},
                "webdev": {...}, "vision": {...}, "agent": {...}}
    },
    "by_effort": {                     // the tier shifts with effort
      "high": {"tier": 3, "arena_variant": "Claude Opus 5.5 (High)"},
      "max":  {"tier": 4, "arena_variant": "Claude Opus 5.5 (Max)"}
    },
    "classification": {                // judged, never shown as measured
      "class": "frontier",             // frontier | agentic | lightweight
      "strengths": ["planning", "ui-web", "agentic-execution"],  // + tui, security when judged
      "suggested_role": "review",      // review | execute | both
      "by": "rule|jev|manual", "confidence": "high|medium|low", "as_of": "YYYY-MM-DD"
    },
    "source": {...}, "confidence": "...", "last_verified": "..."
  }
}
```

How the proposal works:
- **Sources.** models.dev is the identity, join key, modality and price backbone. The AA free
  tier supplies the intelligence index, the domain indexes, speed and TTFT. The official Arena
  dataset (over HF datasets-server JSON, `latest` split) supplies per-effort ratings for
  `text` (with categories), `webdev`, `vision` and `agent`. The runtime CLIs supply what is
  actually selectable and at which efforts.
- **Tier rule.** A proposed rule: rank-normalize each source, give it a confidence weight, and
  cut the result into 4 or 5 bands per (model, effort).
- **What only jev or the user can fill.** TUI and security have no public measure, so they get
  `by: jev` or `by: manual` with a visible confidence.
- **Cache.** One TTL per source in `_meta.sources`, so a slow source never blocks a fast one.
  Using 7 days for the external sources (instead of 30) is a suggestion, to be decided.
- **Then the TOML.** After jev classifies the catalog, the user picks entries. The reviewers
  and executors TOML that comes next (see note 6) refers to these keys plus an effort. It
  never copies the catalog's numbers.
- **Fix needed in any case.** Drop or re-weight `coding_index` and `agentic_index` and the
  mechanical floor before the next real refresh. The Arena `webdev`/`agent` boards or the AA
  engineering index can take their place.

Sources:
- [AA Data API docs](https://artificialanalysis.ai/data-api/docs)
- [AA OpenAPI spec](https://artificialanalysis.ai/api/v2/openapi)
- [models.dev api.json](https://models.dev/api.json)
- [Arena Leaderboard Dataset blog](https://arena.ai/blog/arena-leaderboard-dataset/)
- [HF lmarena-ai/leaderboard-dataset](https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset)
- [Unofficial mirror repo](https://github.com/oolong-tea-2026/arena-ai-leaderboards)
- [Arena rank blog](https://arena.ai/blog/arena-rank)
