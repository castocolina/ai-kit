# Phase 35: Model discovery and catalog - Research

**Researched:** 2026-11-19
**Domain:** stdlib-only Python catalog code in `skills/ai-kit-spec-review/ai_kit_spec/`, public model-data sources, test and guard infrastructure
**Confidence:** HIGH for code map, live probes and measured numbers; MEDIUM for class thresholds (calibrated without Artificial Analysis) and the Artificial Analysis terms reading; LOW for herdr output shapes (never executed)

Scratch work: `tmp/p35-research/` (scripts, downloaded data, never committed). Provenance tags: `[VERIFIED: ...]` = a command run or a file opened this session; `[CITED: url]` = official page read through WebFetch (a small model summarizes it, so quotes are as returned, not byte-checked, except where marked "PDF read directly"); `[ASSUMED]` = judgment, needs the owner or a spike.

<user_constraints>
## User Constraints (from 35-CONTEXT.md; headline sentences verbatim, full text in 35-CONTEXT.md)

### Locked Decisions
- **D-01: One small new module per concern, each with its own tests; `catalog_build.py` only calls them.**
- **D-02: Each source has its own cache age.** `[models] cache_days` per source (`models_dev`, `artificial_analysis`, `arena`), default 7 days for these three and the existing 30 days for host listings (`RUNTIMES_TTL_SECONDS`); `sources` defaults to all three; a source whose key or network is missing is skipped with a visible reason, never an error.
- **D-03: Arena is read through the datasets-server JSON rows API, config `text`, split `latest`.** Sequential fetch, page ceiling, timeout, cached by `cache_days`, prints progress; Arena names are display names (effort in parentheses) matched through D-04.
- **D-04: Identity is the models.dev canonical key; each runtime keeps its own id and an `efforts` list.** Existing normalization first; unmatched or ambiguous goes to jev as one item per name (host name and at most five candidate entry names, never configuration); confident answer is provisional and labeled judged with confidence, otherwise `unmatched`. Effort suffixes and brackets parsed by runtime style into `efforts`, never into identity; a name whose own id ends in an effort word and exists in models.dev stays whole.
- **D-05: Four named tiers plus unknown, as relative bands.** `frontier`, `strong`, `capable`, `light`, `unknown`: quartiles of the percentile rank inside the deciding source, recomputed on every refresh; a score on an edge goes to the higher band. Deciding source: Artificial Analysis when it has the model, else Arena; the output says which decided. Effort-aware: a row per (model, effort) when the source scores efforts apart, otherwise "effort not distinguished".
- **D-06: Class is a closed set, derived by rule first.** `flagship`, `coding`, `general`, `fast`, `small`, `router`, `unknown`; rules use measured fields; a model with no measured field gets a jev judgment when present (labeled judged), else `unknown`; `router` only for owner aliases (D-16); nothing is labelled review by default.
- **D-07: Cost is a band.** Quartiles of published input plus output price per million tokens: `low`, `medium`, `high`, `premium`, with `free_or_local` and `unknown` apart.
- **D-08: One label vocabulary.** `measured`, `judged`, `assumed`, `user-stated`; each value also carries source name and fetched-at time; unknown is shown as unknown.
- **D-09: Context per (runtime, model).** `runtimes[<id>]` holds the window with label and source: host figure (pi listing, opencode `/api/model` `limit.context` and `limit.input`, codex listing), else models.dev, else unknown; precedence user override, host, models.dev; exact integers only. Override is `[[models.context]]` with `runtime`, `model`, `tokens`, labeled user-stated. Phase 39 reads it from here.
- **D-10: `check-reviewer` records its own result** `{state, at, via, error line}` per (runtime, model); only chosen candidates are probed; opencode `enabled: false` shows "listed disabled by host"; error line = first line, control characters removed, key shapes redacted (reuse `secret_shapes.py`).
- **D-11: Optional sources are probed at runtime and never required.** Web: fixed query template filled only with the runtime's public product name, labeled "web, unverified" with URL and date, treated as data. herdr: only with `HERDR_ENV=1` and the CLI; spike first (copilot `/model` unverified). Seed row mapping runtime to models.dev provider is data with a `source` label.
- **D-12: Stale only after a successful live listing.** `last_seen` per (runtime, model); failed or skipped listing says "not checked"; catalogued provider no longer configured flagged apart; models.dev `status` shows as "marked by source"; `check-providers` says "absent" for a missing file.
- **D-13: `[models]` keys** `sources`, per-source `cache_days`, `[[models.context]]`, read by Phase 33's layered reader and written by its splicing writer; AA key stays in `secrets.env`. `_meta.schema_version` goes to 4: older caches rebuild keeping `heuristic_confirmed` fields and dated `verified` usability records. A `confirm-model` style subcommand writes one correction with provenance.
- **D-14: Recorded help fixtures.** `tests/fixtures/cli_help/` holds the recorded `--help` of opencode with version and date, refreshed by a maintainer command tests never run; a test extracts the flags named by the opencode profile, the runner's opencode argv formulas and its comments and fails on a flag the fixture lacks; stale comment and the 2.0.29 citations rewritten. Effort levels come from `variants` in `/api/model`.
- **D-15: router-env aliases are assumed.** Marked router with fallback quota, no models.dev or AA lookup, no heuristic question, label `assumed: router-env alias naming`.
- **D-16: The guard is position-based and needs no name list.** Values of keys named like `model`, the argument after a model flag, provider/model shaped literals in code and inline code, seed-row cells.
- **D-17: Allowed forms.** `router-env/<x>` (tests for pi and opencode only); for bare-id host formats invented structure-only placeholders (grammar fixed by the plan, for example `placeholder-model-<n>`, `placeholder-model-<n>-high`, `placeholder-alias-<n>`); marked examples (`model-example:` marker in a comment, docstring, doc or a field named `example`) only in comments, docstrings, docs and example fields, never in a branch, membership test, default or gate. **Needs owner confirmation.**
- **D-18: A committed baseline that can only shrink.** `tests/fixtures/no_hardcoded_models_baseline.json`: sorted, duplicate-free paths, each with the phase that cleans it; new violation fails, a baseline path that no longer violates also fails; arch-group module with non-vacuity cases; `cross-ai.mjs` examples carry the marker.
- **D-19: Todo folding.** Items 1, 6, 7 fold in; items 2-5 go to Phase 36.
- **D-20: jev, web and herdr are conditional.** Every path has a tested absent behavior; web queries carry no project, user or machine detail; fetched and pane text is data.

### Claude's Discretion
- Module names (D-01), placeholder grammar (D-17), class thresholds (D-06), `[models]` defaults tuning (D-02), the baseline JSON shape, how usability and labels are stored in the catalog entry.

### Deferred Ideas (OUT OF SCOPE)
- Coding and review proposal, jev ranking (Phase 36); removing the table-gating paths (Phases 36-39, 38.1); runner setting reports and prompt-size refusal (37, 39); cleaning every baseline file; probing every model; installing or upgrading any host CLI.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HUB-02 | Discovery per host with source, usability apart (R1, R2, R3) | Section 6 (listing code map), section 1 (opencode API facts), section 4 (herdr calls), section 6.7 (merge pitfall) |
| HUB-03 | Names, merged labeled values, context, attribution, `[models]` and schema (R4, R5, R6, R7, R10) | Sections 2, 3, 5, 6, 10 |
| HUB-06 | Stale flags on proof (R8) | Sections 6, 10 (`models` key semantics, `check-providers` already says absent) |
| HUB-08 | opencode profile matches installed help (R9) | Section 1 (help texts, flags), section 6 (comment and profile lines) |
| HUB-09 | Hardcoding guard with shrinking baseline (R11) | Section 8 (prototype and numbers), section 7 (arch group wiring) |
</phase_requirements>

## Summary

The code base already has everything the phase needs except small seams: a validated per-entry merge (`merge_catalog_entry`), a splicing TOML writer (`toml_splice.set_table/set_array/publish`), a layered reader (`cfg_layered_table`), a secret redactor (`secret_shapes.redact`), an injectable jev subprocess client pattern (`fold_group.find_jev/ask_jev`) and a fake for it (`tests/test_ai_kit_commit_fold.py:102 write_fake_jev`). The phase is mostly "add small pure modules and wire them in", with seven live traps found by probing (section 10): the opencode 2.3.2 `/api/model` first request answers HTTP 503 (verified) so the existing probe silently loses data; `merge_catalog_entry` replaces each `runtimes[<id>]` dict wholesale so any new per-runtime field (usability, last_seen, context label) is wiped on refresh unless the merge is made per-field; `variants` is a list of `{id, settings}` objects, not a name list; Artificial Analysis free tier terms forbid external distribution of derived data and raw data (so no AA data in any tracked file, and a non-distributable tier line must be shown only to the key holder); the Arena `/filter` route works and cuts 113 pages to 35 (7 categories) or 5 (overall only); the guard prototype flags 91 files on position rules alone; a new tests module must also be regenerated into the Makefile and pre-commit listings (`tools/gen_test_groups.py`).

**Primary recommendation:** build per-concern pure modules (names, bands, arena, usability, optional sources, models config, report), make `merge_catalog_entry` deep-merge `runtimes[<id>]` first (it unblocks usability, last_seen and context labels), add the `/api/model` full-record parser with a 503 retry, read Arena per category through `/filter` with retry-then-`/rows` fallback, and ship the guard as an arch-group module with the baseline generated from the prototype's rules.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Listing per host (R1) | `detection.py` listers (subprocess to host CLI) | runtimes cache `runtimes.json` | Facts come from host commands; cache is `cache_runtimes_path` |
| Usability record (R2) | `quota.probe_reviewer_quota` call in `check-reviewer` | catalog file | Only a real call may mark verified |
| Seed, web, herdr names (R3) | skill (agent) runs web search and herdr; Python validates and records | catalog file | stdlib code cannot call the host's WebSearch tool; it ingests a JSON file the agent wrote |
| Name matching, effort parsing (R4) | pure Python (`model_matcher` + new names module) | jev subprocess seam | deterministic first, jev only for the unmatched |
| Tier, class, cost band, strengths (R5) | pure Python bands module | Arena, AA, models.dev fetchers | recomputed on every refresh from this run's source rows |
| Context per runtime (R6) | listing parsers (pi, opencode API, codex) | models.dev, `[models]` override | precedence user, host, models.dev |
| `[models]` settings (R10) | `config_io.cfg_layered_table` reader, `toml_splice` writer | `local_secrets.load_secret` for the key | key never enters config.toml |
| Hardcoding guard (R11) | arch-group test module | baseline JSON fixture | read-only scan of tracked files |
| Skill text (R12) | `skills/ai-kit-spec-config/SKILL.md` + references | doc-contract tests, judge loop | |

## Standard Stack

Stdlib only (AGENTS.md: runtime code stays stdlib-only). No external package is installed by this phase.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `urllib.request`, `json`, `re`, `difflib`, `unicodedata`, `statistics` | Python 3.12+ (host 3.15 here) | fetch Arena rows, parse, NFKC normalize (R11 edge), percentiles | already used by `model_sources.py:9-11` |
| `tomllib` | stdlib 3.11+ | read `[models]` | `config_io.py` already guards it |
| `unittest` | stdlib | all tests (runner runs `python3 -m unittest <module>`, `tools/run_unittest_parallel.py:500`) | project convention |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON rows API | parquet reader | forbidden by SPEC constraint (stdlib only) |
| `numpy` percentiles | `statistics.quantiles` or manual index | a manual sorted-index quantile is 5 lines and matches the calibration scripts |

**Installation:** none.

## Package Legitimacy Audit

No external package is installed by this phase (stdlib only); `gsd_run query package-legitimacy check` not applicable.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| none | - | - | - | - | - | - |

**Packages removed due to [SLOP] verdict:** none. **Packages flagged [SUS]:** none.

## 1. opencode live facts (question 1)

**Installed version is v2.3.2, not 2.3.0** `[VERIFIED: opencode --version, 2026-11-19: "opencode v2.3.2"]`. Record that in the fixture.

### 1.1 `GET /api/model` shape (private server, names only)
Probe: the `detection.py` way (`serve --hostname 127.0.0.1 --port 0`, banner, Basic auth), run from `tmp/p35-research/scripts/opencode_variants.py` with `XDG_CACHE_HOME` pointed under `tmp/` and the real HOME (opencode itself needs its own login to list the reachable models). Servers were stopped by the script's `finally`; `pgrep` afterwards showed only the user's own `opencode serve --service`.

- **First request answered HTTP 503** `[VERIFIED: probe 2026-11-19]`: body `{"_tag":"ServiceUnavailableError","message":"Location plugins did not finish activating","service":"plugin"}`. The second try (2 s later) succeeded; total 7.3 s from launch. The production probe `_probe_from` (`detection.py:889-915`) does one request and catches `urllib.error.URLError` (HTTPError is a subclass) at `detection.py:910-912`, returning `{}`; `build_runtimes_snapshot` then records `image_input_probe: "failed"` (`detection.py:1090-1092`). The probe's deadline timer is `_OPENCODE_PROBE_DEADLINE_S = 15` (`detection.py:678`, timer at 896). **The phase must retry on 503 (bounded by the same deadline; 2 s pause, at most 6 tries).**
- Response top keys: `['data', 'location']`. 79 models, 5 providers (this machine). Item keys: `body, capabilities, compatibility, cost, enabled, family, id, limit, modelID, name, package, providerID, settings, status, time, type, variants`.
- `status`: all `active`. `enabled`: all `True` (so the "listed disabled by host" path is only fixture-tested here).
- `limit` keys `context, input, output`; `limit.input` is `null`/absent for 48 of 79 models, below `limit.context` for 29 (so `limit.input` is the prompt cap when present, else `limit.context`) `[VERIFIED]`.
- `cost` is a **list** (1 item for 38 models, 2 for 13, empty for the rest); items have keys `cache, input, output, tier`. Not a dict: models.dev's `cost` is a dict, so the two sources need separate readers.
- `capabilities` keys `freeform, input, output, temperature, tools`; input values seen `audio, image, pdf, text, video`.
- **`variants` is a list of objects `{"id": <name>, "settings": {"reasoningEffort": <name>}}`** (sample verified: `[{"id": "minimal", "settings": {"reasoningEffort": "minimal"}}, {"id": "low", ...`). It is an empty list for 15 of 79 models.
- **Variant names seen (the effort levels, closed list on this machine):** `high, low, max, medium, minimal, none, thinking, xhigh`. Name sets per model (count of models): `[]` 15; `high,low,max,medium,none,xhigh` 15; `high,low,max,medium,xhigh` 12; `high,low,medium` 8; `high,low,max` 5; `high,low,medium,xhigh` 5; `high,none` 4; `high,low,medium,none,xhigh` 3; `high,low,medium,minimal,xhigh` 2; `low,medium,none,xhigh` 2; plus 9 single-model sets (e.g. `max` alone, `none,thinking`). `none` and `thinking` are variant names too: the parser must store names as listed and not map them.
- `parse_opencode_api_models` (`detection.py:709-737`) keeps only `{"providerID/id": "image" in input}`. The phase needs a second parser returning `{id: {efforts, limit, enabled, status, family, cost}}`; keep the old one (its fixture `tests/fixtures/opencode_api_model.json`, 1372 bytes, has no `variants` and no `limit`; extend it with the real shape using `router-env/...` ids).
- A model id in `opencode models` output is `providerID/id`; the effort goes after `#` (`model_suffix=r"#[^#/]+$"`, `detection.py:96`; `opencode run --help`: "Model to use in the format provider/model#variant").

### 1.2 Recorded help (fixtures, 35 R9) `[VERIFIED: commands run 2026-11-19, v2.3.2]`
Flags (the test extracts `--name` tokens, so these are the sets to record):
- `opencode --help` FLAGS: `--standalone, --server, --auto, --continue/-c, --session/-s, --prompt`; GLOBAL FLAGS: `--help/-h, --version/-v, --wizard, --completions, --log-level, --print-logs`. SUBCOMMANDS include `models`, `run`, `serve`, `debug`, `auth`, `stats`, `service`.
- `opencode run --help` FLAGS: `--continue/-c, --session/-s, --fork, --worktree/-w, --model/-m, --agent, --format (default, json), --file/-f, --title, --archived, --thinking, --auto`; plus the same GLOBAL FLAGS and `--standalone`, `--server`.
- `opencode models --help`: no own flags; GLOBAL FLAGS only, **including `--standalone` and `--server`** (the stale comment is wrong, see 6.9).
- Runner formulas (`cross-ai.mjs:1363-1364`): `['run', '--model', m, '--auto', '--format', 'json', '--standalone']` and `['run', '--model', m, '--agent', 'plan', '--format', 'json', '--standalone']`: every flag is in the recorded help.
- Fixture layout to create: `tests/fixtures/cli_help/opencode/{version.txt,help.txt,run-help.txt,models-help.txt}` plus a `meta.json` `{"version": "2.3.2", "recorded": "2026-11-19"}`; maintainer command `tools/record_cli_help.py` (never run by tests). Contents are the three outputs above, byte-for-byte (they contain no key or account data).

## 2. Class thresholds (question 2)

Data (all fetched 2026-11-19, public, no key): models.dev `api.json` 6,782,295 bytes: **324 providers, 10027 model rows** (the spec's 9895 was 2026-11-16) `[VERIFIED: tmp/p35-research/scripts/modelsdev_stats.py]`; Arena `text/latest` overall 422 models.

### 2.1 Measured distributions
| Quantity | n | p10 | p25 | p50 | p75 | p90 |
|----------|---|-----|-----|-----|-----|-----|
| models.dev input+output USD per 1M, per bare-id median across providers | 3769 ids | 0.375 | **0.75** | **2.475** | **8** | 19.8 |
| same, per row (not deduped) | 8990 rows | 0.42 | 0.9258 | 3.2156 | 11.25 | 24 |
| models.dev `limit.context`, per bare-id median | 4247 ids | 65536 | 131072 | 262144 | 1000000 | 1048576 |
| Arena `overall` rating | 422 | 1084.5 | **1218.1** | **1352.8** | **1425.0** | 1461.8 |
| Arena coding rating minus overall rating | 417 | -20.9 | -5.7 | 13.4 | **26.6** | 41.5 |

- models.dev cost: 8990 priced rows, **588 rows `input == 0 and output == 0`** (free), 449 rows with no or invalid `cost`, 73 rows with `input > 0` and `output == 0`. Cost dict keys: `input, output, cache_read, cache_write, tiers, context_over_200k, reasoning, input_audio, output_audio` `[VERIFIED]`.
- models.dev `limit.context`: 154 rows are `0`, 6 rows are `>= 10,000,000` (placeholder-looking, max `99999999`); **603 of 4247 ids state different contexts on different providers**, so context is a per-runtime fact (D-09) and is a poor model-class signal.
- models.dev fields (counts of 10027): `reasoning` true 7938, `tool_call` true 9036, `open_weights` true 4723, `status` present 950 (`deprecated` 868, `beta` 81, `alpha` 1), `canonical_model_id` present 8628 (658 distinct values, each of the shape `vendor/model`), `reasoning_options` present 6770 as a list (sample `[{"type": "toggle"}]`), `family` 9535, modalities input `text 9986, image 6577, pdf 2842, video 1899, audio 883`, output `text 9813, image 194, audio 78, video 72`.
- **Finding:** `canonical_model_id` is models.dev's own cross-provider identity (86 percent of rows). D-04 says "identity is the models.dev canonical key"; the existing code builds `provider/bare-id` from the matched row's provider (`catalog_build.py:469-470`, `canonical_key` at `model_catalog.py:116-120`) which can be a reseller. Recommendation `[ASSUMED]`: store `canonical_model_id` as `identity` on the entry when the matched row has it and keep `canonical_key` unchanged as the cache key (no key migration); ask in confirmation only if the planner wants the key itself to change.
- Arena names with parentheses: 180 of 422. Parenthetical tokens: effort words `high` 30, `max` 13, `thinking` 7, `xhigh` 6, `non-thinking` 2, `reasoning` 2, `medium` 1, versus **date or quantization tokens** (`001`, `2025-04-14`, `20250514`, `nvfp4`, `bf16`, `1106`, `08-2024`, ...). So the Arena effort parse must use a closed effort vocabulary (`minimal low medium high xhigh max thinking non-thinking reasoning`) and leave every other parenthetical as part of the identity.
- Effort words inside real ids: of 2889 unique models.dev bare ids, **72 end in an effort word** (`thinking` 35, `max` 25, `medium` 4, `high` 4, `low` 3, `xhigh` 1); for **27 the stripped base also exists** and for **45 it does not** (suffix is part of the identity: `max` 22, `thinking` 15, `medium` 4, `high` 2, `low` 2). Rule from D-04: if the whole id exists in models.dev keep it whole; else strip.
- Exact-normalized-name join Arena to models.dev (`_normalize` = lowercase, drop non-alphanumerics, `model_matcher.py:24-27`; Arena name with parentheses removed) matched **245 of 422 (58 percent)**; the rest need jev or stay `unmatched` (expected, not a bug).

### 2.2 Proposed rule set (measured fields only)
Inputs per catalog entry, all recomputed on every refresh: `tier` (D-05), `cost_band` (D-07), `coding_edge` (source-relative), `tps_pct` (Artificial Analysis tokens-per-second percentile rank, absent without the key).

```python
# cut points are NOT constants: they are percentiles of THIS refresh's rows (D-05, D-07).
def quartile_cuts(values):                  # sorted ascending, n >= 4
    return [values[int(len(values) * p)] for p in (0.25, 0.50, 0.75)]   # tie/edge goes UP (>=)

def tier(score, cuts):                      # source = AA if it has the model else Arena
    if score is None: return "unknown"
    return "frontier" if score >= cuts[2] else "strong" if score >= cuts[1] \
        else "capable" if score >= cuts[0] else "light"

def cost_band(in_plus_out, cuts, free):     # cuts over per-bare-id median price of priced models
    if free: return "free_or_local"         # cost.input == 0 and cost.output == 0 as reported
    if in_plus_out is None: return "unknown"
    return "premium" if in_plus_out >= cuts[2] else "high" if in_plus_out >= cuts[1] \
        else "medium" if in_plus_out >= cuts[0] else "low"

def klass(entry):                           # first match wins; every branch cites measured fields
    if entry.alias_router: return "router"          # owner alias router-env/<x>, assumed (D-15)
    t, b = entry.tier, entry.cost_band
    if t == "unknown" and b == "unknown" and entry.tps_pct is None and entry.coding_edge is None:
        return "unknown"                             # then jev judgment if present (labeled judged)
    if t == "frontier": return "flagship"
    if t in ("strong", "capable") and entry.coding_edge is not None \
            and entry.coding_edge >= EDGE_P75:       # p75 of the edge over this source's rows
        return "coding"
    if t in ("strong", "capable", "light") and entry.tps_pct is not None and entry.tps_pct >= 0.75:
        return "fast"                                # needs the AA key; never assigned without it
    if t == "light" and b in ("low", "free_or_local"): return "small"
    return "general"
```
Numeric justification (today's data):
- Tier cuts on Arena `overall`: `1218.1 / 1352.8 / 1425.0` gives tiers `frontier 106, strong 105, capable 106, light 105` of 422 (quartiles by construction; ties share a tier because the comparison is on the score).
- Cost cuts `0.75 / 2.475 / 8` USD per 1M (3769 unique ids; computed on the per-id median so a model resold by 100 providers counts once). A joined recomputation on the Arena-matched names gave `0.725 / 2.34 / 8`: the band edges are stable to about 3 percent.
- `EDGE_P75`: Arena coding-minus-overall p75 = **26.6** (n=417); within the top half by overall it is 32.6 (n=211). Use the unfiltered p75 of the source's own delta list, recomputed per refresh, never the number 26.6. For Artificial Analysis the same rule applies to `coding_index - intelligence_index` (no absolute number: no AA call was made).
- `fast`: AA `median_output_tokens_per_second` percentile rank >= 0.75 among models that have it; no absolute number (AA not called).
- `small` is deliberately narrow (tier light AND price low or free): on the 245 Arena models matched to models.dev it yields **8**.
- Calibration result on the Arena-only join (no AA, `tps` absent): `flagship 106 (25.1%), coding 60 (14.2%), general 248 (58.8%), small 8 (1.9%), fast 0, unknown 0`. `general` is large because 177 of 422 models have no price match (`cost_band` unknown); a light model with unknown price stays `general` (it has a measured tier, so `unknown` would be wrong) `[VERIFIED: tmp/p35-research/scripts/class_calibrate.py]`.
- Context is **not** a class input: 603/4247 ids carry different windows per provider, so it is a runtime fact (D-09); stating this in the plan keeps D-06's "context" wording from creating a second source of truth. `[ASSUMED]` that the owner accepts dropping context from the rule (it is a deviation from the D-06 field list; flag in the Assumptions Log).
- Strength flags (Arena categories, measured): a category strength is set when the model's `category rating - overall rating` is >= that category's own p75 delta. Today's p75 deltas for the kept categories: coding +26.6, math +17.4, hard_prompts +10.6, instruction_following -8.9, creative_writing -11.3, multi_turn +5.4 (instruction following and creative writing sit below 0 for most models, so a p75 rule is the only comparable one).
- models.dev `reasoning`/`reasoning_options`/`modalities` map directly to `modalities` and `reasoning` facts (label `measured`, source `models.dev`).

## 3. Arena: a cheaper read (question 3)

All probes against `https://datasets-server.huggingface.co`, 2026-11-19 `[VERIFIED: tmp/p35-research/scripts/arena_probe.py, arena_fetch.py, arena_or.py]`.

| Route | Result |
|-------|--------|
| `/rows` (config `text`, split `latest`, `length=100`) | works; 0.62 s, 35,331 bytes per page; **11202 rows today** (11177 on 2026-11-16), so 113 pages |
| `/statistics` | works, 0.22 s: counts, histograms, `n_unique`, **category frequencies**; returns no rows, so it is a free preflight for the row count and category list |
| `/size`, `/splits` | work; list 23 configs (`text`, `text_style_control`, `text_factuality`, `webdev`, `vision`, `agent`, ...); `text/latest` num_rows 11202, 29 categories |
| `/first-rows` | works; only the first 100 rows; useful only for the column list |
| `/filter` with `where="category"='overall'` (double-quoted column) | **works: 422 rows, 5 pages** |
| `/filter` with single-quoted column or `IN (...)` | HTTP 422 `Parameter 'where' contains errors or invalid symbols` (IN) / invalid symbols (single-quote column) |
| `/filter` with `"category"='a' OR "category"='b'` | works (839 rows for two categories) |
| `/filter` where `"leaderboard_publish_date"='2026-11-18'` | works but returns all 11202 rows: **the `latest` split holds a single publish date** (statistics min = max = 2026-11-18), so a date slice buys nothing |
| `/filter` HTTP 500 reported in the spec | **not reproduced**: 0 errors in 48 sequential `/filter` pages plus the probes; keep retry (3 tries, 1 s) and a fallback to `/rows` pages |

Measured fetch plans:
- 10 categories, one `=` query per category, 100-row pages: **48 pages, 20.8 s, 1,499,818 bytes**, 4122 rows (0.43 s per page).
- 7 categories in one `OR` query: 2928 rows, **30 pages but 28.4 s**, 1.06 MB (0.95 s per page): the OR form is slower per page than separate `=` queries. **Recommendation: one `=` query per category (7 categories = 35 pages, about 15 s, about 1.2 MB).**
- Full `/rows` crawl: 113 pages, about 50 s, about 4 MB.

Categories to keep (row counts today; every `(model_name)` is unique inside a category, so rows = models): `overall` 422 (decides the tier and is the base for deltas), `coding` 417, `math` 405, `hard_prompts` 422, `instruction_following` 422, `creative_writing` 420, `multi_turn` 420. Skip (not needed for the closed class set): `expert` 372, `longer_query` 400, the 9 `industry_*` (fine-grained and 292 to 422 rows each), language categories (`chinese, english, french, german, japanese, korean, polish, russian, spanish, non_english`), `exclude_ties`, `hard_prompts_english`. Put the category names in one constant tuple in the Arena module (they are Arena's own labels, not provider or model names).
Rating field: **`rating`** (Elo-like, 833.5 to 1538.2 in `overall`); keep `rating_lower`, `rating_upper` (median CI width 10.3) and `vote_count` (median 23,741, min 819) beside it as measured context; `rank` has no ties inside `overall`. Rows carry `organization` (blank for 49 of 422) and `license`; do not use them for identity.
Note `[ASSUMED]`: config `text` versus `text_style_control` are both 11202 rows today; D-03 locks `text`. Record the config name in the cached source record so a later switch is visible.

## 4. herdr (question 4)

`herdr` is installed `[VERIFIED: command -v herdr -> /home/bazzite/.local/bin/herdr; herdr --version -> "herdr 0.9.5"]`; `HERDR_ENV=1` is set in this session `[VERIFIED: printenv HERDR_ENV]`. Nothing was opened, started or closed; only `--help` and `--skill` (read-only) were run. No code in `tools/` or `tests/` mentions `HERDR` today (`rg` returned nothing), so the new code must take `env` and a `run_fn` as parameters.

Commands the code would call (flags from `herdr pane split|run|send-keys|read|wait-output|close --help` and `herdr tab create --help`, `herdr agent start --help`):
| Step | Command | Output expectation |
|------|---------|--------------------|
| open a pane beside the caller | `herdr pane split --current --direction right --cwd <cwd> --no-focus` | JSON; new id at `.result.pane.pane_id` `[CITED: herdr --skill]` |
| start copilot | `herdr pane run <pane_id> "<copilot command with permission prompts off>"` or `herdr agent start <name> --kind copilot --pane <pane_id>` (kind list includes `copilot`) | `agent start` returns after herdr detects the agent ready (default timeout 30000 ms) |
| open the model view | `herdr pane send-text <pane_id> "/model"` then `herdr pane send-keys <pane_id> enter` (or `pane run`, which sends text plus Enter) | no output contract |
| wait for the list | `herdr pane wait-output <pane_id> --match <text> --timeout <ms>` (also `--regex`) | exit code carries match or timeout |
| read it | `herdr pane read <pane_id> --source recent-unwrapped --lines 120` | plain text |
| leave the view | `herdr pane send-keys <pane_id> esc` (`esc` is canonical) | |
| close | `herdr pane close <pane_id>` | the pane the code created only |
CLI server errors are JSON on stderr with exit 1; syntax errors exit 2 `[CITED: herdr --skill]`.
Test fake: a script on PATH named `herdr` that answers an exact argv table, like `tests/host_fakes.py:32-42` (`_FAKE` logs each call as JSON and answers only exact argv tuples). `host_fakes.HOST_NAMES` (`host_fakes.py:21-23`) derives from `RUNTIMES` binaries, so herdr needs its own writer, not `write_host_fakes`. `write_cbm_registration`-style helpers do not apply. The tripwire stubs only `HOST_CLI_NAMES` (`run_unittest_parallel.py:230-233`: `agent, claude, codex, copilot, cursor-agent, grok, opencode, pi`), so a test that must run the herdr path puts its own fake first on PATH and passes `env={"HERDR_ENV": "1", ...}` explicitly (the runner baseline strips host signals; whether it strips `HERDR_ENV` is not verified: do not rely on it).
Copilot `/model` output is **unverified** (spike stays an open item, label "interactive view, unverified").

## 5. Artificial Analysis terms (question 5)

Fetched 2026-11-19. Three sources, in order of authority:

**A. Data Platform Terms and Conditions, Version 1.1, last revised 2026-08-19** `[VERIFIED: PDF read directly, pages 1-6, https://artificialanalysiscdn.com/legal/ProDataPlatformTerms.pdf (linked from https://artificialanalysis.ai/data-api/docs)]`:
- Scope: "These Terms also govern access to and use of the Artificial Analysis API on the free tier".
- 1.8 "External Distribution" means "any act of making raw Data files (including CSV, Excel, JSON, or other structured data exports) available to any person or entity that is not an Authorized User, whether by direct access, transfer, embedding, or any other means."
- 2.3 All Tiers: "(a) use Data for Internal Use; (b) share charts and visualizations publicly, subject to the attribution requirements in Section 5; and (c) make brief citations of individual Data points in publicly available content ... provided such citations include the attribution "Source: Artificial Analysis (artificialanalysis.ai)" with a hyperlink where technically feasible and do not reproduce Data in a structured, tabular, or machine-readable format."
- 2.3 Pro and Commercial only: "(b) create and externally distribute Derived Data". Free tier is not listed there.
- 2.4 Redistribution Restrictions include: "(a) Distribute, transfer, sell, sublicense, or otherwise make raw Data files available to any third party." and "(c) Embed or otherwise make raw Data available through any customer-facing product, API, dashboard, or service." and "(d) Combine Data with data from third-party sources to create a product, dataset, or service that is made available to any third party."
- 2.5: "Customer shall not use the Data to develop, operate, or improve any product or service made available to third parties whose primary purpose is benchmarking, ranking, comparison, competitive intelligence, or model/provider selection guidance, without Company's prior written consent."
- 2.6(d): no use of Data "to develop, train, fine-tune, or improve any artificial intelligence or machine learning model".
- 3.1: no alteration of Data values; 5.1: "Attribution is required at all subscription tiers and in all use cases where Data or Derived Data is shared, published, displayed, or otherwise made available outside of Customer's own internal systems." Required text: Data and metrics "Source: Artificial Analysis (artificialanalysis.ai)" with hyperlink where feasible; Derived Data "Based on data from Artificial Analysis" plus a non-endorsement statement (5.2).
- No caching clause exists in this document `[VERIFIED: pages 1-6 read; the PDF has more pages, 7 onward not read]`.

**B. Free API page** `[CITED: https://artificialanalysis.ai/api-reference, WebFetch 2026-11-19]`: "Attribution is required for all use of our free API." "Please provide attribution to https://artificialanalysis.ai/." "Use of the API is subject to our Terms of Use and Data Platform Terms." Rate limits stated as "Default limit of 10 requests per 24-hour window" **but** the data-api docs page says "Free: 100 requests per window" `[CITED: https://artificialanalysis.ai/data-api/docs]` (conflict: both quoted; treat the quota as unknown and cache hard). That page also says "For redistribution rights or bespoke contract terms, contact the team." and "Use of the API requires attribution across all tiers." "A visible byline or footer link is sufficient."

**C. Terms of Use** `[CITED: https://artificialanalysis.ai/terms-of-use, "Last revised: September 15 2026", WebFetch]`: personal noncommercial license; no caching clause; scraping the site prohibited (3.3(b)(vi)).

**Verdict on R7 (honest):** redistribution of raw AA data and external distribution of derived data are **not granted on the free tier** (verified from A); caching on the user's own machine is **not addressed** anywhere read (unverified absence, so keep the cache in the user's `~/.cache`, never in the repo). Consequences for the plan:
1. No AA response data in any tracked file (matches SPEC R7); the arch rule needs a definition of "AA response shape with real-looking values": recommend flagging any tracked file that contains the key `artificial_analysis_intelligence_index` unless it is a `tests/*.py` module carrying a one-line marker `# synthetic: Artificial Analysis shapes, invented values` (today `tests/test_ai_kit_spec.py:7157-7665` holds shape-valid values such as `68.4`, `70.0`, `142.3`; add the marker there).
2. Printed AA-derived tier and class lines go to the key holder's own terminal (Internal Use) and carry: "Source: Artificial Analysis (artificialanalysis.ai)" and for derived bands "Based on data from Artificial Analysis. Not endorsed by Artificial Analysis." If a report is written to a tracked or shared file the AA values must be dropped. `[ASSUMED]` reading of Internal Use for a local CLI; legal reading is the owner's.
3. Term 2.5 (a ranking or model-selection product offered to third parties) is a risk for a publicly distributed skill that integrates AA: keep AA optional and key-gated, each user their own customer, and record it as an owner-confirmation item (Assumptions Log A5).
4. Redistribution status in output: "Artificial Analysis redistribution terms: not granted for raw data or externally distributed derived data (free tier); caching rule not stated."

## 6. Existing code map (question 6)

Every row verified by opening the file this session. `file:line` cites the definition.

### 6.1 `detection.py` (1348 lines)
| Symbol | Where | What the phase does |
|--------|-------|---------------------|
| `RUNTIMES_TTL_SECONDS = 30 * 24 * 3600` | `detection.py:29` | keep (host listings stay 30 days, D-02) |
| `RUNTIMES_SCHEMA_VERSION = 7` | `detection.py:40` | bump to 8 when `listed_from` is added to each cli row (comment block 31-39 records each bump; add "Version 8 (35)") |
| `Runtime` NamedTuple | `detection.py:72-81` (fields `binaries, host_signals, scrub_signals, list_argv, native_selectors, review_only, model_suffix, multi_provider, runner`) | add a `seed_provider`-like seed field only as labeled example data; never branch on it |
| `RUNTIMES` | `detection.py:85-127`: pi `model_suffix=r":(?:off|minimal|low|medium|high|xhigh|max)$"` (:90), opencode `r"#[^#/]+$"` (:96), cursor `r"\[[^\]]*\]$"` (:103), claude `native_selectors=("fable", "opus", "sonnet", "haiku")` (:116), copilot `Runtime(("copilot",), (), runner=True)` (:120), grok (:121-126) | table is seed data: add the seed-row source label and the `model-example:` marker; `native_selectors` cells are seed-row cells for the guard |
| `CLAUDE_FALLBACK_MODEL_IDS`, `CLAUDE_FALLBACK_AS_OF = "2026-09-23"` | `detection.py:141-143` | moves to a labeled seed example; used only by `claude_runtime_fields` (:1030-1031) when the catalog has no `anthropic_model_ids` |
| `_list_argv` | `:281-286` | |
| `detect_opencode_models` | `:297-307` (`opencode models`, one id per line; `[]` possible; `None` on failure) | keep; add `listed_from` |
| `parse_cursor_models` / `detect_cursor_agent_models` | `:316-362` | keep |
| `parse_codex_debug_models` / `detect_codex_models` | `:392-440` (keeps `visibility == "list"`; returns `{"id", "reasoning_modes"}`) | codex listing has no context field read today (only `slug`, `visibility`, `supported_reasoning_levels[].effort`, docstring :408-410); R6 asks for "codex listing" window: **unverified that `codex debug models` states one** (payload is about 260 KB of prompt text; fixture `tests/fixtures/codex_debug_models.json`, 7064 bytes); the plan must check the live key names before promising it |
| `_parse_one_pi_model` | `:460-481` returns `context_window`, `max_tokens` exact ints | already the pi host figure |
| `detect_pi_models` | `:576-593`: pi is listed through RPC `get_available_models` (`PI_RPC_ARGS`, `detection.py:44-48`), **not** `pi --list-models --offline` as the SPEC says | no change; fix the SPEC wording in the Phase 35 amendment |
| `_listing_fields` | `:542-565` returns `models` only on success; failure returns `None` | `models` key presence means "listing succeeded" (docstring :1063-1065): this is the stale proof (R8) |
| `parse_opencode_api_models`, `_probe_from` | `:709-737`, `:889-915` | add a records parser and a 503 retry (section 1) |
| `build_runtimes_snapshot` | `:1054-1100` | add `listed_from` `{command, version, at}` per cli row and one opencode server start that returns images, limits, variants, enabled together |
| `normalize_runtime_keys`, `runtime_id` | `:154-172` | reuse |
| `claude_runtime_fields` | `:1000-1031` | claude lists no models: its rows come from the catalog `_meta.anthropic_model_ids` or the dated fallback; both stay seed-labeled |

### 6.2 `catalog_build.py` (731 lines)
- `CatalogSources` (`:22-26`: `models_dev_data, models_dev_ok, aa_models, aa_ok`) needs an Arena member; `CatalogBuildCtx` (`:29-33`). Pylint caps (max-args=5): pass new data in NamedTuples.
- `_FIRST_PARTY_PROVIDER_BY_CLI = {"claude": "anthropic"}` (`:290`) and `_anthropic_model_ids` (`:293-321`): hardcoded provider name; becomes a labeled seed row consumed from data.
- `_preserved_or_fresh_ctx_window` (`:155-169`) is the only ctx writer: returns `md_match.limit.context` for every runtime (pi's exact figure never reaches it); R6 replaces it with the precedence function (user override, host, models.dev, unknown) returning a `{tokens, label, source, at}` record while keeping the `ctx_window` int for existing readers (6.8).
- `_preserved_or_fresh_aa_fields` (`:172-213`) builds `scores` (3 indexes) and `tokens_per_sec`, `aa_pricing`; `_preserved_or_fresh_md_fields` (`:96-152`) builds `tool_calling, structured_output, max_output_tokens, image_input, image_input_source`.
- `_process_catalog_candidate` (`:660-673`): router path only when `infer_purpose_from_name` returns something; a router alias with no purpose word still goes through models.dev matching. D-15 needs a new first branch: `router-env/` prefix means router, `fallback_quota` true, no lookup, label `assumed: router-env alias naming`. `infer_is_router` today is a substring heuristic: `_ROUTER_NAME_HINTS = ("router", "-env", "local-llm")` (`model_heuristics.py:9`).
- `build_model_catalog` (`:676-731`) is the one entry; keep it a thin caller of the new modules (D-01).
- Tests pinning it: `tests/test_ai_kit_spec.py` (`TestBuildModelCatalog`, e.g. `test_models_dev_fetch_failure_preserves_cached_runtime_ctx_window`).

### 6.3 `model_catalog.py` (305 lines)
- `CATALOG_TTL_SECONDS = 30 * 24 * 3600` (:11); `CATALOG_SCHEMA_VERSION = 3` (:17); `CATALOG_META_KEY = "_meta"` (:18).
- `_FIELD_TYPES` (:26-44) is the top-level type table (unlisted fields are left unchecked, comment :23-25); `_NUMERIC_SUBFIELD_TABLES` (:45-48); `_RUNTIME_FIELD_TYPES = {"model_id": str, "ctx_window": (int, float)}` (:49) (extra per-runtime keys are accepted).
- `_runtime_migration_needed` (:58-63) returns True for `version < CATALOG_SCHEMA_VERSION`; after the bump every v3 file takes the runtime-key rewrite once (`_entry_with_id_runtimes`, idempotent via `normalize_runtime_keys`), which is harmless. `split_catalog_meta` (:78-92), `join_catalog_meta` (:95-102), `catalog_schema_is_current` (:105-113, `>=`).
- **`merge_catalog_entry` (:223-255): `merged["runtimes"] = {**existing.get("runtimes", {}), **entry.get("runtimes", {})}` (:240) replaces each `runtimes[<id>]` dict as a whole.** Any new per-runtime field written by a previous run (usability, last_seen, ctx label, override) is lost when a refresh passes `{model_id, ctx_window}` for that runtime. Fix first: deep-merge `runtimes[<id>]` per key with the same explicit-`None`-clears rule used at :249.
- `apply_heuristic_corrections` (:271-305) writes `heuristic_confirmed` (sorted union) after validation; `_confirmed_quota` (`runner_dispatch.py:218-232`) reads it. `confirm-model` should reuse this shape for the new fields (`heuristic_confirmed` stays the "user answered" list; add the provenance dict `confirmed_fields` `{field: {by, at, note}}`).
- `current_candidate_keys` (:258-268) is used by the wizard reference (`skills/ai-kit-spec-config/references/cli-model-selection.md:181-202`) and tests (`tests/test_ai_kit_spec.py:873, 8916-8921, 9408, 11280`), not by production code. R8 stale output must not change its return (it "silently drops"); add a separate report function instead.

### 6.4 `model_matcher.py` (178 lines)
`_NON_ALNUM` (:15), `_FUZZY_THRESHOLD = 0.82` (:20), `_FUZZY_MARGIN = 0.05` (:21), `_normalize` (:24-27), `bare_model_part` (:30-33), `_EFFORT_TOKENS = {"minimal", "low", "medium", "high", "xhigh", "thinking"}` (:55), `_strip_known_effort_suffix` (:63-93; "max" only as `thinking-max`), `match_models_dev` (:96-142), `match_artificial_analysis` (:145-178). Ambiguity returns `None` (never first-wins), which is what feeds the new "two equally good candidates give `unmatched` with both named" edge (R4): the new names module needs a variant that returns the candidate list. The effort vocabulary here differs from the per-runtime style regexes in `RUNTIMES.model_suffix` and from Arena's parentheses; the names module becomes the one parser.

### 6.5 `model_sources.py` (62 lines) and `cache.py` (92 lines)
- `MODELS_DEV_URL`, `ARTIFICIAL_ANALYSIS_URL` (`model_sources.py:13-14`), `_TIMEOUT_SECONDS = 15` (:16), `_USER_AGENT` (:20), `_http_get_json` (:23-27), `fetch_models_dev` (:30-38), `fetch_artificial_analysis` (:41-62: returns `([], True)` with no key, `(partial, False)` on mid-pagination failure). Add `arena_source.fetch_arena(fetch_fn)` with the same `(data, ok)` contract and the same injectable `fetch_fn`; Arena sends no key. The host `datasets-server` answers 200 to the same UA.
- `cache_base` (`cache.py:9-12`: `$XDG_CACHE_HOME/ai-kit/spec` else `$HOME/.cache/ai-kit/spec`), `cache_write_json` (:23-24, `json.dumps(data, indent=2)`, **no `sort_keys`**), atomic `cache_write_bytes` (:27-46), `cache_is_stale(path, ttl)` (:88-92, mtime based).
- Catalog fetch freshness today: one sidecar `<catalog>.fetch-meta.json` holding `{"last_fetched": time.time()}` (`cli.py:510-523`) gated by `CATALOG_TTL_SECONDS` (`cli.py:513`). D-02 needs per-source ages: store `{"sources": {"models_dev": {"last_fetched": t, "ok": true}, ...}}` in that sidecar and read the old shape as "all sources fetched at `last_fetched`".

### 6.6 `cli.py` (1108 lines) and commands
- Parser registration is split into `_register_cache_detect_parsers` (:144-174), `_register_catalog_parsers` (:177-244), `_register_report_parsers` (:247-323), `_register_dispatch_parsers` (:326-402); `_build_parser` (:406-413); `_COMMANDS` dict (:1066-1090); `_dispatch` (:1092-1098); `main` wraps `ConfigError` into exit 2 (:1101-1108). Add new subcommands through one new registration function in a new module and two one-line edits (call in `_build_parser`, entries in `_COMMANDS`), not by growing `cli.py`.
- `check-providers`: parser `cli.py:168-174`, handler `_cmd_check_providers` (:429-433) calling `provider_check.check_providers_report` (`provider_check.py:285-289`). **Verified live 2026-11-19 (scratch HOME, `env -i`): a missing project config prints `cross-reference: <path>/.aikit/config.toml absent`, the missing user file `absent`, the missing catalog `absent`** (`provider_check.py:127-132` `_scan_pending` returns `SourceStatus("absent")`; the untrusted status exists only for an existing file, `_gated`:106-110). The R8 "absent, not untrusted" item is therefore already true at HEAD and pinned by `tests/test_ai_kit_spec_check_providers.py:104-105, 323-324`; the phase needs no code change there, only keeping those tests green.
- `check-reviewer`: parser `cli.py:393-402` (`--key --model --vendor --runtime --command --extra-json`), handler `_cmd_check_reviewer` (:1058-1065) calls `probe_reviewer_quota` (`quota.py:267-282`) which returns `{"available", "checked_at", "reason", "detail"}` (`_probe_entry`, `quota.py:214-219`; detail capped by `_DETAIL_MAX_CHARS`). R2: add `--catalog-path` (optional) and, when given, record `{state, at, via, error}` into `runtimes[<id>]["usability"]` through the validated merge; map `available true` to `verified`, false to `rejected`, a native or custom-less entry (`quota.py:274-275` returns available without a call) must **not** become `verified` (SPEC prohibition: only a real call marks verified).
- Existing confirm commands: `confirm-catalog-entry` (`cli.py:213-217`, `_cmd_confirm_catalog_entry` :651-673: payload file `{"model_id", "entry"}`, merges through `merge_catalog_entry`) and `apply-heuristic-correction` (`cli.py:219-225`, :675-695). The owner todo asks for a documented correction subcommand: add `confirm-model --catalog-path P --model-id K --field F --value V [--note N]` in the new module, validated, with provenance, so the wizard never edits the cache by script.
- `fetch-model-catalog` flow: `_discovered_catalog_candidates` (:479-504), `_fetch_catalog_external_sources` (:507-530; sets `schema_version` only `if models_dev_ok`, :524-525: an offline run never upgrades the schema, so the v4 upgrade must not depend on a fetch), `_run_fetch_catalog_build` (:579-605), `_cmd_fetch_model_catalog` (:608-649), `_write_fetch_catalog_result` (:552-563; the JSON printed has `models_dev_ok`, `artificial_analysis_ok`, `fetch_skipped`; add `arena_ok`, per-source skip reasons, attribution lines).

### 6.7 `routing.py` (359 lines) and `commands.py` (135 lines)
Gating lines the SPEC lists are intact: `routing.py:36` (reason names), `:138` (`return "review_only" if mode == "exec" else "custom"`), `:141-142`, `:156-157` (`no_inventory`), `:174`, `:177-178` (`RUNTIMES[runtime].review_only` -> `review_only`); `commands.py:65-67` (`SUPPORTED_EXECUTE_CLIS` excludes `review_only`). This phase only **lists**; do not change them. `runtimes_cache_is_fresh` (`routing.py:241-248`) = TTL + schema + claude-current; bumping `RUNTIMES_SCHEMA_VERSION` re-detects every cache once (intended).

### 6.8 Readers of catalog fields the phase must not break
- `model_ranker._max_context_window` (`model_ranker.py:190-193`): reads `rt.get("ctx_window")` per runtime and takes the max -> keep `runtimes[<id>].ctx_window` as an int.
- `runner_dispatch._confirmed_quota` (`runner_dispatch.py:218-232`) reads `runtimes[runtime].model_id`, `heuristic_confirmed`, `fallback_quota`; `resolve_route` (:235-) uses it.
- `catalog_adapter._build_join_index` (`ai_kit_gsd_curated_config/catalog_adapter.py:332-344`) joins on `runtimes[cli].model_id`; `_entry_scores` (:409-422) reads `scores`.
- `provider_check.scan_catalog` (`provider_check.py:173-192`) reads `runtimes.opencode.model_id`.
- `cross-ai.mjs` does not read `model-catalog.json` (`rg "model-catalog|ctx_window|schema_version"` on it: no match).

### 6.9 Comments and profile lines to rewrite (R9)
- `cross-ai.mjs:1355-1359`: "opencode 2.0.29 run --help formulas; ... listModels (`opencode models`) has no such flag and still reads the shared service, read-only." **Wrong on 2.3.2** (`models --help` lists `--standalone`). Also `cross-ai.mjs:1367` "the listing has no variants" (now false: `/api/model` has `variants`), `:1502` and `:5953` cite 2.3.0.
- `references/cli-profiles/opencode.md`: front matter `last_verified: 2026-08-28` (:7), "The runner formula (opencode 2.0.29 `run --help`)" (:24) and the formula block (:26-29) omits `--standalone` that the runner passes, "the listing has no variants" (:32-33), plus provider/model ids in prose (:17-22 and the `source:` front matter :8-10).
- `detection.py:57-58, 261, 692` cite v2.0.31 and "opencode v2.0.29" (docstring examples).
- cross-ai.mjs is a **template**: the project's own runner copy must be a pristine render (`make check-dogfood`); re-render after editing comments or the dogfood check fails.

### 6.10 Phase 33 reader and writer to reuse
- Reader: `config_io.cfg_layered_table(cwd, env, *table_path)` (`config_io.py:554-558`) = `{**user_table, **project_table}` per key, built on `cfg_load_layers` (:540-542), `_table_at` (:545-551), `cfg_load_toml` (:312-329, missing file is `{}`, other problems raise `ConfigError`, :296-309). Its docstring names `[models]` explicitly. Shallow merge means a project `[[models.context]]` array replaces the user's whole array (document it, test it).
- Writer: `toml_splice.set_table(text, path, values, remove=())` (`toml_splice.py:429-448`; inline values only, refuses arrays of tables, :416-420), `set_array(text, path, entries, match="key")` (:727-753), `remove_table` (:756-774), `publish(path, text)` (:780-792; checks the text parses, writes atomically through `cache_write_bytes`, existing file keeps its mode, new file 0600). Model for the wrapper: `config_io._splice_roster` (:881-895) and `cfg_write_toml` (:941-949: read bytes, parse to fail early on broken TOML, splice, publish).
- `[[models.context]]` entries carry `runtime` and `model` strings and no `key`; `set_array` pairs by a unique **string** `match` field (`_match_value`/`_pair_entries`, `toml_splice.py:508-527`) and otherwise by position. A composite key is not supported: pass `match="model"` only if models are unique across runtimes, else accept position pairing (comments stay with their position) and test it.
- Per-source cache days: write a sub-table `[models.cache_days]` with `set_table(text, ("models", "cache_days"), {...})` and the scalars with `set_table(text, ("models",), {"sources": [...]})`.
- The AA key: read with `local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY")` (`cli.py:518`, `CliDeps.load_secret_fn` :133); never write it to config (SPEC R10 test: key absent from the file).
- Existing docs line: `docs/config/design.md:52` "`[models]`: catalog sources, cache age and classification settings. Phase 35. Not read in Phase 33." (update it).

### 6.11 `secret_shapes.py` (117 lines)
`SHAPES` (:17), `detect(text)` (:94-96) names shapes, `redact(text, marker)` (:99-) replaces matches. Canonical file is `skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py` and no `ai_kit_spec` module imports it today (`rg` shows imports only in goal-prompt, fold, wake, jev scripts through byte-identical copies, `tests/test_secret_shapes.py:16`). In `ai_kit_spec` a plain `from ai_kit_spec import secret_shapes` is fine (same package, no cross-skill copy). Error line recipe: first line of the detail, strip control characters (`re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s)`), `redact(line, "[redacted]")`, cap 200 characters.

### 6.12 spec-config text
`skills/ai-kit-spec-config/SKILL.md` (479 lines): Step 1 Detect `:84-119` (runs `detect-runtimes`, `detect-tools`, `--check-only` branch, `detect-runtimes --save`, `check-providers`), Step 2 Ask `:121-` with the 8-row table (:133-142), Step 2.2 `:156-185` (catalog flow, MANDATORY read of `references/cli-model-selection.md`, 347 lines), Step 2.5 `:254-280` (write-risk question, `check-reviewer`, the point where D-10's record is written), Step 3 Write `:366`, Step 4 Report `:409`, Evidence `:476`. References: `check-only.md` (89 lines), `cli-model-selection.md` (347), `config-file.md` (66). Add the catalog step between Step 1 and Step 2 (discover, label, optional sources, classify, attribution, stale and usability report); the 8-item procedure in `cli-model-selection.md` already numbers fetch and ranking, so add one item instead of renumbering SKILL.md steps. Doc-contract tests that pin these texts: `tests/test_ai_kit_spec_check_providers.py` (reads `CLI_MODEL_SELECTION_MD`), `tests/test_cross_ai_skill_text.py`, `tests/test_ai_kit_spec_runtimes_table.py`; evals live in `skills/ai-kit-spec-config/evals/` (`evals.json`, `files/`, `trigger-queries.json`).

### 6.13 jev seam (question 9)
No `ai_kit_spec` module calls jev today (`rg` over `ai_kit_spec/` finds only comments). The repo precedent is `skills/ai-kit-commit-fold/scripts/fold_group.py`: `skills_roots(env, own_root)` (:209-217), `find_jev(env, own_root)` (:225-231; looks for `jev-fast-decision/scripts/jev_review.py`, `JEV_ENTRY_REL` at :27), `jev_item` (:234-247: one `choice` item `{id, type, instructions, context, criteria}`), `ask_jev(entry, item, env, run=subprocess.run, timeout)` (:250-273: `[sys.executable, entry, "ladder"]`, JSON on stdin, parses `items[<id>].decided_by` then the column's `choice`; returns `(None, "old")` on exit 2 with "invalid choice", `(None, "timeout")`, `(None, "no answer")`). Public contract: `python3 -B <skill-dir>/scripts/jev_review.py ladder` with stdin `{"items": [...]}` `[VERIFIED: skills/jev-fast-decision/SKILL.md:20-30]`; lookup order `skills/jev-fast-decision/reference.md:218-229`.
Fake: `tests/test_ai_kit_commit_fold.py:102 write_fake_jev(skills_root, table, log_path)` writes `jev-fast-decision/scripts/jev_review.py` under a scratch skills root (also imported by `tests/test_ai_kit_commit_fold_adapters.py:28`), plus a no-jev case (`_no_jev`, :759) and an old-client case (`_old_jev`, :771). Reuse it by import for the confident, low and absent cases.
**Arch trap:** a new file that assigns `JEV_ENTRY_REL` or `SKILLS_ROOTS` is a "lookup copy" and `tests/test_arch.py:1688-1697 LOOKUP_COPIES` plus its drift check (`_LOOKUP_NAMES`, :1698; `uncompared_lookup_files`, :1797) require it to be listed and to follow the documented root order; naming `ai-kit-spec-review`-external skills is also policed by `check_cross_skill_refs` (:1495) with a frozen allowlist that "only shrinks" (`_CROSS_SKILL_FROZEN`, :1632-1668). So: write the jev client as a faithful copy of `fold_group.py:209-273` in `ai_kit_spec/jev_names.py`, add that path to `LOOKUP_COPIES`, and run `python3 tools/run_unittest_parallel.py tests.test_arch` early.
Advisory rule: a confident answer is provisional and labeled judged with its confidence; `needs_fallback` or "own_reasoning" means `unmatched` (SKILL.md:38-39).

### 6.14 Proposed module layout (question 9, names are the plan's to fix)
All in `skills/ai-kit-spec-review/ai_kit_spec/`, stdlib only, each under about 250 lines, functions under pylint caps (`max-statements=50`, `max-branches=12`, `max-args=5`, `max-locals=15`, `max-returns=6`; `pyproject.toml`, AGENTS.md "Tools and Stack"):
| Module | Concern | Budget |
|--------|---------|--------|
| `arena_source.py` | category constant, `fetch_arena(fetch_fn, ...)` per category with 3 retries then `/rows` fallback, page ceiling, progress callback, parse to `{display_name: {category: row}}` | 200 |
| `model_names.py` | per-runtime effort parsing (styles of section 2.1), identity decision (whole id exists in models.dev stays whole), candidate list for ambiguity | 220 |
| `jev_names.py` | jev lookup copy and one `choice` item per name (host name, at most five candidate names) | 120 |
| `catalog_bands.py` | `quartile_cuts`, `tier`, `cost_band`, `klass`, strengths; pure, no I/O | 220 |
| `usability.py` | record, read, sanitize error line, label order verified, host listing, interactive view, web, seed | 120 |
| `optional_sources.py` | web query template and result ingestion (JSON file the agent wrote), herdr driver (`run_fn` injectable), name sanitizer (control and escape characters removed, id pattern) | 240 |
| `models_config.py` | `[models]` reader (defaults, source-name validation with a named error) and splicing writer | 160 |
| `catalog_report.py` | sorted display rows, `listed_from`, stale/not-checked/stale-provider/marked-by-source, attribution lines | 220 |
| `catalog_cmds.py` | argparse registration and handlers for `catalog-report`, `models-config`, `confirm-model`, `record-web-names`, `herdr-names` | 220 |
| `cli_help_fixture.py` (tools or tests helper) | flag extraction `--[a-z][a-z0-9-]*` as whole tokens | 60 |
The web search itself is run by the agent (the skill), never by Python: stdlib code cannot reach the host's WebSearch tool, so R3(b) is "agent writes a JSON file `{runtime, query, url, date, names[]}`, Python validates and records it", with a unit test that the query text holds no path, user name or host name and that a hostile instruction string in `names` is dropped by the id-pattern filter. `[ASSUMED]` design; consistent with D-20.

## 7. Test infrastructure (question 7)

- **Group membership:** `tools/run_unittest_parallel.py` defines `ARCH_MODULES` (:92), `UNIT_UV_MODULES` (:94-98), `INTEGRATION_MODULES` (:100-112), `E2E_MODULES` (:115-150); everything else discovered under `tests/` is `unit` (`discover_modules`/`group_modules`, :286-298; `tests/test_gate_scope.py:498 test_every_module_in_exactly_one_group`). A new `tests/test_*.py` joins `unit` automatically; to be an arch module add its dotted name to `ARCH_MODULES`.
- **Listing regeneration (trap):** the Makefile (comment block at line 12) and `.pre-commit-config.yaml` carry a generated module listing between `# BEGIN GENERATED test groups` and `# END GENERATED test groups`; `tests/test_gate_scope.py:570-583` fails with "stale listing; run: python3 tools/gen_test_groups.py" unless it is regenerated. Run `python3 tools/gen_test_groups.py` after adding or renaming any test module, and commit both files (they are `SHARED_MACHINERY`, `run_unittest_parallel.py:217-220`, so staging them runs the full unit and arch groups at commit).
- **Run commands:** one module `python3 tools/run_unittest_parallel.py tests.test_x` (main, :872-901, takes dotted module names; `--group unit|arch|unit-uv|integration|e2e`); tier `make test-unit`, `make arch-test`, full `make test`; the runner executes `python3 -m unittest <module>` per module (:497-500).
- **Isolation:** every module runs under a tripwire and a baseline env (host stubs for `HOST_CLI_NAMES`, :230-233; temporary HOME with `AI_KIT_REFUSE_REAL_HOME=1`, AGENTS.md "Testing"). No test may read `.planning/` (arch rule; the guard baseline therefore lives in `tests/fixtures/`, as D-18 says).
- **Fakes that exist:** `tests/host_fakes.py` (`write_host_fakes`, `host_path`, `fake_calls`, `write_cbm_registration`; fakes answer exact argv tables and log calls), `tests/index_fakes.py` (`write_index_fakes`, `tool_path`, `no_tool_path`, `set_state`, `index_calls`: a stateful fake for codebase-memory-mcp and graphify, the model for a stateful herdr fake), `tests/cursor_fakes.py`, `tests/forge_fakes.py`, `tests/session_wake_fakes.py`. Fake jev: `write_fake_jev` (6.13). Fake web: none exists; the web path takes a JSON file, so a test writes that file. Fake herdr: none; write `tests/herdr_fakes.py` modeled on `index_fakes.py` (needs per-command JSON answers).
- **Arch conventions:** `tests/test_arch.py` (3500+ lines): `check_*` functions over `ast`/text, `TestArchitecture` (:2087), `TestArchNonVacuity` (:2656) proving each rule fails on a planted violation, banner-delimited helper groups, repo-wide scanners with a **frozen allowlist that only shrinks** (`_CROSS_SKILL_FROZEN`, :1632-1668, whose `cross_skill_allowlist_problems` :1671-1680 is the pattern for the baseline "only shrinks" check), and `KEY_SHAPE_COPY_RX` scanning `skills/` and `tools/` for key-shaped secrets (`_SHAPE_SCAN_ROOTS`, :1882). The hardcoding guard follows `check_*` + non-vacuity.
- **Skill front matter:** `tests/test_skill_frontmatter.py` limits: `MAX_DESCRIPTION = 1024` (:38), `MAX_NAME = 64` (:39); a strict parse runs on every `skills/*/SKILL.md`; the `uv` twin is `tests/test_skill_frontmatter_pyyaml.py` (unit-uv). `tests/test_skill_evals_shape.py` pins evals JSON shape.
- **Fixtures layout:** `tests/fixtures/` holds `codex_debug_models.json`, `cursor_models.txt` (+ `_empty`, `_auth_failed`), `opencode_api_model.json`, `opencode_models_verbose.txt`, `pi_rpc_get_available_models.json`, `model_catalog_null_index.json`, `curated_config_v2/` (golden outputs, `model-catalog.json`, `runtimes.json`, `gsd_tables_1_16.json`), `archived/` (the only place archived planning data may live), `jev/`, `cursor/`, `golden/` and more. New: `cli_help/opencode/`, `no_hardcoded_models_baseline.json`, synthetic `arena_rows.json`, `models_dev_small.json`, `opencode_api_model_v2.json` (real shape, `router-env/...` ids).
- **Tests that mention schema 3 and will need updating when `CATALOG_SCHEMA_VERSION` becomes 4:** `tests/test_ai_kit_spec.py:2807, 2810, 6636 (`assertEqual(meta.get("schema_version"), 3)`), 8420 (uses the constant), 8883-8897 (`catalog_schema_is_current`; its `for good in ({"schema_version": 3}, {"schema_version": 4})` list must move to 4 and 5), 8964, 9002-9028, 9220, 9354, 9682, 10352`; `tests/test_ai_kit_spec_runtimes_table.py:175`, `tests/test_ai_kit_spec_runner_dispatch.py:1024, 1076-1079`, `tests/test_cross_ai_runner_e2e.py:855`, fixtures `tests/fixtures/curated_config_v2/model-catalog.json:24` and `tests/fixtures/model_catalog_null_index.json:3`; `tests/gsd_curated_eval.py:2785` calls `catalog_schema_is_current(meta)`. Fixtures that write `{"schema_version": 3}` just to look "current" must follow the bump or be rewritten through the constant.
- **Tests that mention `ctx_window`:** `tests/test_ai_kit_spec.py` (20 occurrences), `tests/test_curated_config_inventory.py` (1), fixtures `curated_config_v2/model-catalog.json` (39) and `model_catalog_null_index.json` (4).
- **Tests that mention `scores`:** `tests/test_ai_kit_spec.py:7157-7665` AA-shaped payloads (see 5.1).
- **Hardcoded names:** 55 test files per the prototype (section 8). `tests/test_ai_kit_spec_runtimes_table.py` has `TestConfigDoctorRuntimeLiterals` and `tests/test_runtime_list_drift.py` exists: both are runtime-literal drift tests; read them before editing `RUNTIMES` rows.

## 8. The hardcoding guard (question 8)

Prototype: `tmp/p35-research/scripts/guard_proto.py` (not committed), run over `git ls-files` for `skills/`, `tools/`, `tests/`, `docs/`, `README.md`, `AGENTS.md`, `.planning/goals/`, suffixes `.py .mjs .cjs .js .sh .md .json .jsonc .toml .yaml .yml .txt`, skipping `tests/fixtures/archived/`; text NFKC-normalized before matching (SPEC edge) `[VERIFIED: run 2026-11-19]`.

### 8.1 Result: 91 violating files, 1370 hits
| Directory | Files | Notes |
|-----------|-------|-------|
| `skills/` | 9 | `ai-kit-spec-review/references/cross-ai.mjs` (109 hits: flag 38, slash 69, key 2), `ai_kit_spec/detection.py` (5), `catalog_build.py`, `model_catalog.py`, `model_matcher.py`, `cli-profiles/opencode.md` (6), `cli-profiles/codex.md`, `ai-kit-spec-config/SKILL.md`, `evals/files/stale-opencode/config.toml` |
| `tools/` | 0 | the SPEC's 2 tool files come from a family-name pattern in prose or comments; position rules find none |
| `tests/` | 55 | largest: `test_ai_kit_spec.py` 247, `test_ai_kit_spec_superpowers.py` 117, `test_jev_fast_decision.py` 72, `test_curated_config_inventory.py` 51, `test_curated_config_recommend.py` 40, plus 20 generated or recorded fixtures under `tests/fixtures/curated_config_v2/` and `tests/e2e/docker/fixtures/opencode/*.jsonc` |
| `docs/` | 27 | 23 under `docs/superpowers/` (historic plans and specs), 4 under `docs/prds/` |
Hit kinds: `slash` 765, `keyval` 553, `flag` 48, `seedrow` 4.

### 8.2 Position rules that work (keep all four)
1. **keyval**: `(model|model_id|model_name|modelId|base_model|reviewer_model)` followed by `:` or `=` and a quoted value (JSON, TOML, Python dict, kwargs, YAML quoted). Flag when the value is not an allowed form and is "model-ish" (has a letter and one of `- . / : 0-9`).
2. **flag**: `--model` followed by a space or `=` or the argv form `"--model", "x"`; same value test.
3. **slash**: a quoted literal or inline-code span `[a-z][a-z0-9_-]{1,30}/[a-z0-9][a-z0-9._-]{3,60}` whose second segment has a letter and a digit, is not a file name (`.py .md .json ...`), and whose first segment is not a top-level repo directory.
4. **seedrow**: every quoted cell in a Python assignment whose name contains `MODEL`, `ALIAS` or `SELECTOR`, and in `native_selectors=`, `models=`, `aliases=` keyword rows. **No model-ish filter for seed rows** (the four hits were all caught, but bare aliases such as the claude `native_selectors` cells have no digit or dash and the model-ish test would miss them; apply "any string cell" there).
Allowed forms in the prototype: `router-env/<x>`, `placeholder-(model|alias)-<n>[-suffix]`, template slots (`{ } < > $ % *`, `...`), empty, and any line carrying or directly preceded by a `model-example:` marker (adjacency edge: only that line and the next, so a name beside the marker in code still fails).

### 8.3 False-positive classes and the fix for each
| Class | Hits (examples) | Fix |
|-------|-----------------|-----|
| git branch names matching `slash`: first segment `feat`, `fix`, `hotfix`, `gsd`, `demo`, `chore`, `docs`, `release` (about 70 hits in `tests/test_flow_*`, `docs/prds`) | `feat/e7-loop` 18, `gsd/phase-07-demo` 15, `hotfix/fix-1` 8 | closed exclusion list of branch prefixes in the guard (data about git, not about models) |
| test doubles: `fake/ok` 10, `fake-ok` 14, `fake/event400` 54, `fake-flaky-cursor`, `m-1` 14, `x/y`, `vendor/x`, `zen/x`, `gpt-x` | about 130 | these are invented names. **Owner confirmation needed:** extend the D-17 grammar with `fake/<token>`, `fake-<token>` and `vendor/<token>`-free forms, or force everything to `placeholder-*`. Recommendation: allow `fake/` and `fake-` prefixes plus `placeholder-*`, reject everything else (so `m-1`, `x/y` get baselined or renamed) |
| jev's own service model ids: `jev-1.13.0` 43, `jev-1.14.0` 11, `jev-1.15.0` 3 (`tests/test_jev_fast_decision.py`, `test_jev_typesafe_models.py`) | 57 | real vendor model names of a backend, in tests of the jev skill: baseline with cleaning phase `backlog` |
| recorded or generated fixtures (`tests/fixtures/curated_config_v2/*`, `tests/e2e/docker/fixtures/opencode/*.jsonc`, `cursor_models.txt` flag hit) | 20 files | baseline; propose a recorded-fixture exemption only for `tests/fixtures/cli_help/` and files whose name starts `recorded_`, decided by the owner |
| docs history (`docs/superpowers/*`, `docs/prds/*`) | 27 files | baseline with phase `backlog` (prose that quotes real ids as history) |
| regex capture truncation at `]` (`fake-ok-cursor[effort=high`) | 3 | capture to the closing quote, not to the bracket |
No rule had to be dropped. Rules not tried: prose mentions (a vendor-stem list is rejected by D-16).

### 8.4 Recommended final rule set and baseline shape
- Module: `tests/test_arch_hardcoded_models.py` (arch group: add to `ARCH_MODULES`; then `python3 tools/gen_test_groups.py`). Pure helpers `scan_text(path, text) -> list[Hit]`, `scan_tree(root, files) -> dict[path, list[Hit]]`, `baseline_problems(found, baseline) -> list[str]`; test classes `TestHardcodedModels` (live tree), `TestHardcodedModelsNonVacuity` (planted: membership test fails, default value fails, marked example in a comment passes, `router-env/x` passes, a new file fails, a fixed file fails until its baseline entry is removed, a name beside a marker still fails, NFKC look-alike fails). Size budget: about 260 lines, each function under 12 branches (split `scan_text` into one function per rule).
- File set: `git ls-files` filtered by the roots above (the guard must not read `.planning/`; the repo rule is an arch rule with no exceptions; if it needs the goal files, point it at `git ls-files` roots excluding `.planning/`). `[ASSUMED]`: rails and goal files live under `.planning/` or `tmp/` so they are outside the scan; confirm with the owner whether a rails copy under `docs/` or `skills/` must be covered.
- Baseline: `tests/fixtures/no_hardcoded_models_baseline.json`:
  ```json
  {"schema": 1, "files": [{"path": "skills/ai-kit-spec-review/references/cross-ai.mjs", "cleaned_by": "37"}, ...]}
  ```
  `files` sorted by `path` (byte order), no duplicate paths, `cleaned_by` in `{"35","36","37","38","39","backlog"}`; the test fails on unsorted or duplicate content (SPEC edge), on a violating file not in the baseline, and on a baseline path that no longer violates or no longer exists. Suggested owners: Phase 35 for `detection.py`, `catalog_build.py`, `model_catalog.py`, `model_matcher.py`, `cli-profiles/opencode.md`, `cli-profiles/codex.md`, `ai-kit-spec-config/SKILL.md` and its eval fixture (this phase rewrites them, so they leave the baseline in this phase); Phase 37/38 for `cross-ai.mjs` (CONTEXT: 37 gating, 38 runner file entries); Phase 36 for `tests/test_curated_config_*`, `tests/fixtures/curated_config_v2/*`; `backlog` for docs and jev tests.
- Runtime: the scan read about 1500 tracked files inside one tool call under the 120 s limit; wall time was not measured (add `AI_KIT_TEST_REPORT_DIR` timing in the first plan task and record it in `HOOK_RECORDED_SECS` if it reaches 5 s).

## 9. Architecture Patterns

### System Architecture Diagram
```
host CLIs (claude, opencode, pi, cursor, codex, copilot)
   | list commands, opencode private server (/api/model, retry on 503)
   v
detect-runtimes  --writes--> runtimes.json   (schema 8: models, listed_from, reasoning_modes,
   |                                           opencode records: efforts, limit, enabled)
   v
fetch-model-catalog <--- [models] settings (cfg_layered_table, project over user)
   |   sources, per-source cache age:  models.dev (json), Artificial Analysis (key, secrets.env),
   |   Arena (/filter, 7 categories, 35 pages)    each: (data, ok), skipped with a visible reason
   |   per candidate: names (normalize -> jev one item per unmatched name -> unmatched)
   |                  bands (tier, cost band, class, strengths)  context (override > host > models.dev)
   |   merge per entry (deep merge of runtimes[<id>])  --atomic-->  model-catalog.json (schema 4)
   v
catalog-report (sorted by runtime, id): listed_from | usability | stale / not checked |
   marked by source | facts with label, source, time | attribution lines
   ^                         ^
   | check-reviewer --catalog-path records usability (only a real call)
   | confirm-model writes one correction with provenance (survives refresh)
optional (agent runs, Python validates): web names JSON file, herdr pane read
```

### Recommended structure
New modules and tests per 6.14 and section 11; no new top-level directories except `tests/fixtures/cli_help/`.

### Pattern: injectable fetch with `(data, ok)`
`model_sources.py:30-62` pattern: `fetch_fn=None` default to a stdlib call, return `(data, ok)`, never raise, tests inject `fetch_fn`. Arena and the AA-less path reuse it. Source: `skills/ai-kit-spec-review/ai_kit_spec/model_sources.py`.

### Pattern: write one config table without touching other bytes
```python
# Source: ai_kit_spec/config_io.py:881-895 and toml_splice.py:429-448, 727-753, 780-792
text = toml_splice.set_table(text, ("models",), {"sources": ["models_dev", "arena"]})
text = toml_splice.set_table(text, ("models", "cache_days"), {"models_dev": 7, "arena": 7})
text = toml_splice.set_array(text, ("models", "context"), entries)   # entries: runtime, model, tokens
toml_splice.publish(path, text)                                       # atomic, parses first
```

### Anti-patterns to avoid
- **Marking `verified` from a listing, seed row, web page or pane view** (SPEC prohibition): only `probe_reviewer_quota` returning no reason marks `verified`; a native entry (no runtime, no command) returns `available: True` without a call (`quota.py:274-275`), so map it to `unverified`.
- **Treating a failed or skipped listing as stale** (R8): use `"models" in cli_row` as the proof, `last_seen` only moves forward on a successful listing.
- **Overwriting per-runtime fields through the shallow merge** (6.3).
- **Parsing the pi human table's `400K` form** (R6): the pi RPC gives exact ints (`_exact_int`, `detection.py:456-457`).
- **Branching on a table row** (`RUNTIMES`, seed rows): they never decide.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config file edits | a new TOML writer | `toml_splice.set_table/set_array/publish` | byte-preserving, verified round trip |
| Layered config read | own merge | `cfg_layered_table` | project over user already tested |
| Key redaction | new regexes | `secret_shapes.redact` | byte-identical shapes shared with the runner |
| Atomic cache write | `open(...,"w")` | `cache_write_json` / `cache_write_bytes` | mkstemp + fsync + replace |
| jev call | a second client protocol | copy of `fold_group.ask_jev` | arch-tested lookup order |
| Fuzzy matching | new similarity code | `model_matcher._fuzzy_candidate_indices` thresholds 0.82/0.05 | existing collision-safe contract |
| Percentiles | numpy | sorted-index quartile (5 lines) | stdlib only; same as the calibration scripts |
| Flag extraction in R9 test | argparse emulation | one regex `--[a-z][a-z0-9-]*` matched as whole tokens | SPEC edge: whole token only |

## Runtime State Inventory

Not a rename phase, but the schema bump changes stored data:
| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `model-catalog.json` schema 3 files under `$XDG_CACHE_HOME/ai-kit/spec/`; `runtimes.json` schema 7; `<catalog>.fetch-meta.json` single `last_fetched` | code: v3 to v4 upgrade keeps `heuristic_confirmed` and any dated `verified` record; runtimes schema 8 forces one re-detect; fetch-meta old shape read as "all sources at `last_fetched`" |
| Live service config | none | none |
| OS-registered state | none | none |
| Secrets/env vars | `ARTIFICIAL_ANALYSIS_API_KEY` in `secrets.env` (name unchanged) | none |
| Build artifacts | the project's own rendered runner copy (`make check-dogfood`) after `cross-ai.mjs` comment edits | re-render, then run `make check-dogfood` |

## Common Pitfalls

### Pitfall 1: opencode 503 on the first `/api/model` request
**What goes wrong:** `image_input_probe: "failed"` and no effort or limit data. **Why:** "Location plugins did not finish activating" for about 5 s after the banner. **Avoid:** retry every 2 s inside the 15 s deadline; test with a fake `urlopen_fn` that raises `HTTPError(503)` once then answers. **Sign:** `image_input_probe` equals `"failed"` on a healthy host.

### Pitfall 2: shallow runtime merge wipes new per-runtime fields
(6.3). **Avoid:** deep-merge `runtimes[<id>]`, then add the test "usability and last_seen survive a refresh that passes only model_id and ctx_window".

### Pitfall 3: `ctx_window` consumers
`model_ranker._max_context_window` expects a number per runtime. Keep the int and add siblings `ctx_label`, `ctx_source`, `ctx_at`; `None` stays "unknown".

### Pitfall 4: schema bump and offline runs
`cli.py:524-525` upgrades `schema_version` only when models.dev answered. Move the upgrade out of the network branch, else an offline user rebuilds forever and the v3-to-v4 "keep confirmed fields" path is untested offline.

### Pitfall 5: sorted output
`cache_write_json` does not sort (`cache.py:24`); sort only in `catalog-report` (runtime then id, SPEC R1 edge), never change `cache_write_json` (used by every cache).

### Pitfall 6: Arena effort versus date parentheses
Only a closed effort vocabulary leaves identity; `(2025-04-14)` or `(bf16)` stay in the name.

### Pitfall 7: Arena `text` and `text_style_control` both exist
Record the config name in the source record; do not mix rows from both.

### Pitfall 8: AA quota is unclear (10 or 100 per 24 h, two pages disagree)
Default cache 7 days (D-02), one paginated fetch, and a visible skip reason on HTTP 429 (never an error).

### Pitfall 9: the arch lookup-copy rule
(6.13) a new jev client file must be added to `LOOKUP_COPIES`.

### Pitfall 10: test module registration
Run `python3 tools/gen_test_groups.py` and add the guard to `ARCH_MODULES`, or `tests/test_gate_scope.py` fails.

### Pitfall 11: Phase 36/39 readers of `runtimes[<id>]`
Phase 39 reads the prompt window from `runtimes[<id>]`; Phase 36 reads tier, class, cost band, strengths, usability. Keep these exact keys stable: `runtimes[<id>].ctx_window` (int), `runtimes[<id>].usability` `{state, at, via, error}`, `runtimes[<id>].last_seen` (ISO date), top-level `facts` dict (each value `{value, label, source, fetched_at}`), `identity`, `efforts` list on the runtime row. Document them in `docs/config/design.md`.

### Pitfall 12: dogfood runner copy
Editing `cross-ai.mjs` comments requires re-rendering the project's runner copy (`make check-dogfood`, AGENTS.md "Testing").

## Code Examples

### 503-tolerant opencode request (replace the single call in `_probe_from`)
```python
# shape of the change at detection.py:903-909; verified behavior: first call 503, second 200 (7.3 s)
for attempt in range(6):
    try:
        with urlopen_fn(request, timeout=10) as response:
            body = response.read()
        break
    except urllib.error.HTTPError as exc:
        if exc.code != 503 or attempt == 5:
            raise
        time.sleep(2)            # the deadline Timer (15 s) still kills a stuck server
```
The `except` tuple at `detection.py:910-912` already catches `urllib.error.URLError`; HTTPError reaches it only after the last retry.

### Variants parser (names as listed, no mapping)
```python
def _efforts(item) -> list[str]:
    raw = item.get("variants")
    return [v["id"] for v in raw if isinstance(v, dict) and isinstance(v.get("id"), str)] \
        if isinstance(raw, list) else []
```

### Arena fetch (per category, retry, fallback)
```python
WHERE = '"category"=\'%s\''   # double-quoted column; single-quoted column and IN() return HTTP 422
url = f"{BASE}/filter?" + urlencode({"dataset": DS, "config": "text", "split": "latest",
                                     "where": WHERE % cat, "offset": off, "length": 100})
```
Source: `tmp/p35-research/scripts/arena_fetch.py`, run 2026-11-19 (48 pages, 0 errors).

## State of the Art

| Old approach | Current | Impact |
|--------------|---------|--------|
| `opencode models --verbose` for images (1.x) | `GET /api/model` on opencode >= 2 with `variants`, `limit`, `enabled` | one server start serves image, effort, context and enabled facts |
| single catalog TTL | per-source cache age | skip reason per source |
| ctx from models.dev for all runtimes | host figure first | pi is exact, opencode `limit`, codex only if its listing states one (unverified) |
| `models.dev` provider-keyed identity | `canonical_model_id` exists on 86% of rows | optional identity field |

**Deprecated/outdated:** the spec's "9895 models" (now 10027), "11177 Arena rows" (now 11202), "opencode 2.3.0" (installed 2.3.2), "pi `--list-models --offline`" (code uses RPC).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Context is dropped from the class rule (runtime fact, not a model-class signal) although D-06 lists "context" as a rule field | 2.2 | owner may want a context-based `small`/`fast` branch; add a branch with a percentile cut |
| A2 | Store models.dev `canonical_model_id` as an `identity` field and keep `canonical_key` as the cache key | 2.1 | owner may want the key itself changed (cache migration) |
| A3 | Allow `fake/` and `fake-` test-double prefixes in the D-17 grammar | 8.3 | more names to baseline or rename; owner confirmation is already required by D-17 |
| A4 | R3(b) web names arrive as an agent-written JSON file validated by Python | 6.14 | if the owner expects Python to search, no stdlib route exists |
| A5 | Local CLI use of AA data on the user's own key counts as Internal Use; shipping an AA-integrated ranking skill may touch term 2.5 | 5 | legal reading is the owner's; keep AA optional and key-gated |
| A6 | herdr `agent start --kind copilot` and `pane run` can open copilot with permission prompts off and `/model` is readable | 4 | spike may show the list is paged or not printable; keep label "interactive view, unverified" |
| A7 | `codex debug models` states a context window (R6 "codex listing") | 6.1 | the parser reads no such key today; if absent codex falls to models.dev |
| A8 | Arena config `text` (not `text_style_control`) is the intended default | 3 | tiers shift slightly |
| A9 | rails and goal files stay outside the guard's scan roots | 8.4 | uncovered rail files |

## Open Questions

1. **Does `codex debug models` list a context window?** Known: parser reads only `slug`, `visibility`, `supported_reasoning_levels`. Unknown: whether the live payload has a context key. Recommendation: first plan task prints the key names of one live item (names only) before writing the codex branch of R6.
2. **Does copilot print its model list in `/model` under herdr?** Not run (owner rule). Recommendation: keep the spike as a labeled-unverified, optional step; test only against the fake.
3. **Does opencode ever report `enabled: false` or a `status` other than `active`?** All 79 here are `active` and `true`; only a fixture can cover it.
4. **AA quota** (10 vs 100 per 24 h) and **caching** (no clause read, PDF pages 7 onward not read): treat as unknown; cache 7 days.
5. **Which files does the owner want under the guard** (rails copies in `docs/`?), see A9.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | everything | yes | 3.15 here (project targets 3.12) | - |
| opencode | R1, R6, R9 live record | yes | v2.3.2 | recorded fixtures only |
| pi, codex, cursor-agent, copilot, claude | listings | yes (on PATH) | not re-versioned this session | fakes |
| herdr | R3(c) | yes | 0.9.5, `HERDR_ENV=1` | optional source skipped, "absent" tested |
| network (models.dev, datasets-server.huggingface.co) | live source reads | yes | public, no key | skip with visible reason, cached values kept |
| Artificial Analysis key | tier decider | not read, not called | - | Arena decides, output says which |
| jev-fast-decision | name matching | present in repo skills | - | `unmatched` |

**Missing with no fallback:** none. Tests must use fakes for every row above.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib), one subprocess per module through `tools/run_unittest_parallel.py` |
| Config file | none; groups in `tools/run_unittest_parallel.py:92-150`, listings generated by `tools/gen_test_groups.py` |
| Quick run command | `python3 tools/run_unittest_parallel.py tests.test_<module>` |
| Full suite command | `make test` (tiers: `make test-unit`, `make arch-test`, `make test-integration`, `make e2e-test`); never run `make validate` before each commit (AGENTS.md) |

### Phase Requirements to Test Map
| Req | Behavior | Test type | Automated command | File exists? |
|-----|----------|-----------|-------------------|--------------|
| R1 | listing per host with `listed_from`, failed listing keeps cache, installed-not-in-table shows "installed, no listing", empty listing vs failed, two hosts one identity, sorted output | unit | `python3 tools/run_unittest_parallel.py tests.test_catalog_listing` | Wave 0 |
| R2 | verified pair, rejected pair (fake error), unprobed, host `enabled: false`, native entry never verified, error line sanitized | unit | `... tests.test_catalog_usability` | Wave 0 |
| R3 | seed alone, web absent, herdr absent, hostile web string ignored, query text clean, pane names sanitized | unit | `... tests.test_catalog_optional_sources` | Wave 0 |
| R4 | confident, low, absent jev; effort suffix removed (six name styles); id ending in effort word kept; two runtimes one identity; blank name error; tie gives `unmatched` with both | unit | `... tests.test_catalog_names` | Wave 0 |
| R5 | both/one/neither source, AA outage keeps cache, Arena disabled, class judged with and without jev, boundary goes up, tie shares tier, empty catalog no tiers, labels and times | unit | `... tests.test_catalog_bands`, `tests.test_catalog_arena` | Wave 0 |
| R6 | two windows on two runtimes, host beats models.dev, unknown stays unknown, override beats both, zero/negative/float invalid, one output line per runtime | unit | `... tests.test_catalog_context` | Wave 0 |
| R7 | attribution lines per enabled source, none when none enabled, AA terms line, AA-shape arch rule | unit + arch | `... tests.test_catalog_attribution`, `tests.test_arch_hardcoded_models` | Wave 0 |
| R8 | removed after good listing, same after failed listing is "not checked", removed provider, source-marked status, reappears clears flag, `check-providers` absent stays | unit | `... tests.test_catalog_stale`, `tests.test_ai_kit_spec_check_providers` | partly exists |
| R9 | flags of profile, runner argv formulas and comments all in recorded help; planted stale flag fails; fixture records version; whole-token matching | unit | `... tests.test_opencode_help_flags` | Wave 0 |
| R10 | project over user, unknown source named error, comments kept on write, v3 upgrade keeps confirmed fields and verified records, key absent from file, confirm-model survives refresh, offline upgrade | unit | `... tests.test_models_config`, `tests.test_catalog_schema4` | Wave 0 |
| R11 | planted membership, default, marked example, router-env, new file, fixed-file-needs-baseline-removal, empty baseline, sorted and duplicate-free, NFKC look-alike, adjacency | arch | `python3 tools/run_unittest_parallel.py tests.test_arch_hardcoded_models` | Wave 0 |
| R12 | doc-contract pins for the catalog step; evals shape; judge loop record | unit + judge | `... tests.test_spec_config_catalog_text`, `tests.test_skill_evals_shape`; `python3 tools/judge_loop.py check` | Wave 0 |

### Sampling Rate
- **Per task commit:** the touched module's command above (the hook runs the staged modules).
- **Per wave merge:** `make test-unit` and `make arch-test`.
- **Phase gate:** `make test` green, `make check-dogfood`, `python3 tools/gen_test_groups.py` leaves no diff, then `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] fixtures: `tests/fixtures/cli_help/opencode/*` + `meta.json`; `tests/fixtures/opencode_api_model_v2.json` (real shape, `router-env/...` ids, one `enabled: false`); synthetic `arena_rows` and `models_dev_small` payloads (labeled synthetic); `tests/fixtures/no_hardcoded_models_baseline.json`
- [ ] `tests/herdr_fakes.py` (stateful fake herdr, modeled on `tests/index_fakes.py`)
- [ ] the new test modules above (placeholder names; the plan fixes them) and `ARCH_MODULES` + `gen_test_groups.py` regeneration
- [ ] bump the schema-3 expectations listed in section 7 in the same commit as the constant
- [ ] `tools/record_cli_help.py` maintainer command (never run by tests)

## Security Domain

`security_enforcement` is not set to false in `.planning/config.json` (not read; treated as enabled).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | - |
| V3 Session Management | no | - |
| V4 Access Control | partial | private opencode server: loopback, Basic auth, own session group, killed after (already in `detection.py:769-915`) |
| V5 Input Validation | yes | fetched JSON, web names and pane text are data: type-checked, id-pattern filtered, control and escape characters removed, length capped |
| V6 Cryptography | no | never hand-roll; key shapes through `secret_shapes` |
| V8 Data Protection | yes | AA key only in `secrets.env`; no AA data in tracked files; cache in user cache dir |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| prompt injection through web or pane text | Tampering | text never reaches a prompt except as an `items[].context` summary; names filtered by the model-id pattern; hostile-string test |
| leaking a key in the stored error line | Information disclosure | first line only, control characters removed, `redact`, length cap |
| leaking project, user or host detail to a web query | Information disclosure | fixed template filled only with the public product name; test asserts no path, user or host name |
| redirect or proxy capturing the opencode password | Information disclosure | existing `LOOPBACK_URLOPEN` (no proxy) and unredirected auth header (`detection.py:903-906`) |
| runaway or hostile network response | DoS | timeout 15 s (`model_sources.py:16`), page ceiling (115), byte cap per page |
| tampered cache | Tampering | validate through `validate_catalog_entry` before write; atomic write |

## Sources

### Primary (HIGH confidence)
- Source files opened this session: `ai_kit_spec/{catalog_build,model_catalog,model_matcher,model_sources,cache,provider_check,secret_shapes,quota}.py`, `detection.py` (25-600, 676-1127), `cli.py` (1-230, 390-823, 1055-1108), `config_io.py` (296-358, 536-566, 873-950), `toml_splice.py` (416-453, 505-537, 725-793), `tools/run_unittest_parallel.py` (84-233, 495-500, 872-901), `tests/test_gate_scope.py` (560-590), `tests/test_arch.py` (1620-1705 and symbol list), `tests/host_fakes.py` (14-84), `skills/jev-fast-decision/SKILL.md`, `skills/ai-kit-commit-fold/scripts/fold_group.py` (205-300), `skills/ai-kit-spec-config/SKILL.md` (80-285), `cli-profiles/opencode.md`, `cross-ai.mjs` (1352-1368)
- Live commands 2026-11-19: `opencode --version/--help/run --help/models --help`, private-server `/api/model` probe, `herdr --version/--help/pane|tab|agent ... --help/--skill`, `check-providers` in a scratch HOME
- Public data downloaded under `tmp/p35-research/data/`: models.dev `api.json`, Arena `/statistics`, `/size`, `/splits`, `/first-rows`, `/rows`, `/filter`
- Artificial Analysis Data Platform Terms v1.1 PDF (read directly): https://artificialanalysiscdn.com/legal/ProDataPlatformTerms.pdf (linked from https://artificialanalysis.ai/data-api/docs)

### Secondary (MEDIUM confidence)
- https://artificialanalysis.ai/api-reference, https://artificialanalysis.ai/data-api/docs, https://artificialanalysis.ai/terms-of-use (WebFetch summaries, 2026-11-19)

### Tertiary (LOW confidence)
- herdr command outputs (never executed); `herdr --skill` text for response shapes.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (stdlib only, patterns exist)
- Architecture: HIGH (every integration point opened) except the herdr and web seams (MEDIUM, design)
- Class thresholds: MEDIUM (Arena and models.dev measured; AA fields by percentile only)
- Pitfalls: HIGH (503, shallow merge, schema tests, arch traps verified in source or live)

**Research date:** 2026-11-19
**Valid until:** 2026-11-26 for Arena and models.dev numbers (they move daily), 30 days for code facts
