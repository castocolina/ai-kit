# Phase 35: Model discovery and catalog - Context

**Gathered:** 2026-11-16 (interactive path, owner answers on four questions, jev screening, after 35-SPEC.md)
**Status:** Ready for planning (after Phase 34 lands; Phase 33's reader and writer are reused)

<domain>
## Phase Boundary

spec-config catalogs every model the machine can reach on six hosts, keeps listing facts apart from a usability state,
merges models.dev, Artificial Analysis and Arena into labeled tier, class, cost band, modalities, strengths and a
context window per (runtime, model), flags stale entries only on proof, keeps the opencode profile honest against the
installed help, and guards the project against hardcoded provider and model names. It proposes no lane set (Phase 36).
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**12 requirements are locked.** See `35-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `35-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope:** discovery with source (R1); usability state (R2); seed, web and herdr sources (R3); name matching and effort
parsing (R4); merged values with labels (R5); context per (runtime, model) (R6); attribution (R7); stale flags (R8); the
opencode profile test (R9); `[models]` and the schema (R10); the hardcoding guard (R11); skill text and the judge bar (R12).

**Out of scope:** the coding and review proposal and jev ranking (Phase 36); removing the table-gating paths (Phases 36-39,
38.1); the runner's setting reports and prompt-size refusal (Phases 37, 39); cleaning every baseline file; probing every model.
</spec_lock>

<decisions>
## Implementation Decisions

### Layout and sources (SPEC R1, R5, R10)

- **D-01: One small new module per concern, each with its own tests; `catalog_build.py` only calls them.** Modules (names
  are the plan's to fix): Arena source (fetch, parse, match), usability records, bands (tier, class, cost), names
  (identity, effort parsing, the jev matching seam), optional sources (web, herdr), the `[models]` reader and writer.
  Evidence: `catalog_build.py` is 731 lines and `detection.py` 1348, both near the pylint caps (`max-statements=50`). choice 0.99
  (typesafe; laya low 0.36 one_big_new).
- **D-02: Each source has its own cache age.** `[models] cache_days` per source (`models_dev`, `artificial_analysis`,
  `arena`), default 7 days for these three (scores move) and the existing 30 days for host listings (`RUNTIMES_TTL_SECONDS`);
  `sources` defaults to all three, and a source whose key or network is missing is skipped with a visible reason, never
  an error. **Own reasoning** (no jev item: a default the plan may tune). Ledger.
- **D-03: Arena is read through the datasets-server JSON rows API, config `text`, split `latest`.** Live 2026-11-16: the
  cap is 100 rows per request (500 returns HTTP 422), 0.43 s and 35 KB per page, so about 112 pages (~50 s, ~4 MB)
  for 11177 rows; the `/filter` route returned HTTP 500 once (unverified either way), so the plan must not depend on it.
  The fetch is sequential, bounded by a page ceiling and a timeout, cached by `cache_days`, and prints progress. Arena
  model names are display names (effort in parentheses), matched through D-04. choice 0.96 (typesafe; laya low 0.41
  parquet). Open question for the phase researcher: a cheaper way to the same rows (fewer pages) and which categories
  to keep for strengths.
- **D-04: Identity is the models.dev canonical key; each runtime keeps its own id and an `efforts` list.** A host name is
  matched by the existing normalization first; an unmatched or ambiguous name goes to jev as one item per name (the host
  name and at most five candidate entry names, never configuration), a confident answer is provisional and labeled
  judged with its confidence, otherwise the state is `unmatched` and shown. Effort suffixes and brackets are parsed by
  runtime style (cursor `-high` names and `[effort=...]`, pi `:level`, opencode `#variant`, copilot and claude by flag)
  into `efforts`, never into the identity; a name whose own id ends in an effort word and exists in models.dev stays whole.
  Owner's words (2026-11-16).

### Bands and labels (SPEC R5, R6)

- **D-05: Four named tiers plus unknown, as relative bands.** `frontier`, `strong`, `capable`, `light`, `unknown`: quartiles of
  the percentile rank inside the deciding source, recomputed on every refresh; a score on an edge goes to the higher
  band (SPEC edge). The deciding source is the keyed one (Artificial Analysis) when it has the model, else Arena, and the
  output says which decided. Effort-aware: a row per (model, effort) when the source scores efforts apart (Arena's names
  carry the effort in parentheses, live fact), otherwise "effort not distinguished". relative bands choice 0.93. Deciding
  source: choice 0.85 on the second opinion; **jev overridden**: the first answer, average of both ranks (laya 0.86),
  contradicts the evidence (percentile ranks of two sources are not comparable, and a model rated by one source would
  have no tier). Second opinion primary_then_fill (typesafe 0.85).
- **D-06: Class is a closed set, derived by rule first.** `flagship`, `coding`, `general`, `fast`, `small`, `router`,
  `unknown`; rules use measured fields (tier, coding score against the overall score, price band, tokens per second,
  context); a model with no measured field gets a jev judgment when jev is present, labeled judged with its confidence,
  else `unknown`; `router` only for owner aliases (D-16). The thresholds are an open question for the phase researcher,
  calibrated on the live catalog; nothing is labelled review by default (owner, 2026-11-14). **Own reasoning.** Ledger.
- **D-07: Cost is a band.** Over priced models, quartiles of the published input plus output price per million tokens:
  `low`, `medium`, `high`, `premium`, with `free_or_local` and `unknown` apart (jev banded 0.88).
- **D-08: One label vocabulary.** `measured` (a host's own output or a source's published number), `judged` (an ai-kit
  rule or jev, with its confidence), `assumed` (router alias naming), `user-stated`; each value also carries its source name
  and fetched-at time. An unknown value is shown as unknown.
- **D-09: Context per (runtime, model).** `runtimes[<id>]` holds the window with its label and source: the host's figure
  (pi listing, opencode `/api/model` `limit.context` and `limit.input`, codex listing), else models.dev's, else unknown;
  precedence user override, host, models.dev (SPEC edge); exact integers only. jev per_runtime 1.00. The override is
  `[[models.context]]` with `runtime`, `model`, `tokens`, labeled user-stated (jev models_table 0.97). Phase 39 reads the
  runtime's value from here.

### Usability, optional sources, stale (SPEC R2, R3, R8)

- **D-10: `check-reviewer` records its own result.** The one real call it already makes (after Step 2.5's write-risk
  question) writes `{state, at, via, error line}` per (runtime, model) into the catalog; only chosen candidates are
  probed (jev chosen 0.94); an opencode `enabled: false` shows as "listed disabled by host". jev command_records 0.90
  (typesafe; laya low 0.54 agrees). The error line is the first line with control characters removed and key shapes
  redacted (reuse `secret_shapes.py`).
- **D-11: Optional sources are probed at runtime and never required.** Web: a fixed query template filled only with the
  runtime's public product name (jev fixed_template 0.98; laya low 0.59 free_text); the result is labeled "web, unverified"
  with URL and date and treated as data. herdr: only with `HERDR_ENV=1` and the CLI; a spike comes first because copilot's
  interactive `/model` output is unverified here, and the todo says to start copilot with its permission prompts off,
  read `/model`, and close the pane. The seed row mapping a runtime to its models.dev provider is data with a `source`
  label (owner answer 3A). **Own reasoning** for the spike-first order. Ledger.
- **D-12: Stale only after a successful live listing.** `last_seen` per (runtime, model); a failed or skipped listing says
  "not checked"; a catalogued provider the host no longer configures is flagged apart; models.dev `status` shows as
  "marked by source"; `check-providers` says "absent" for a missing file, never "untrusted" (owner todo). **Own
  reasoning** (jev low both rungs: laya age 0.49, typesafe success_only 0.54). Ledger.

### Config, schema, honesty (SPEC R9, R10)

- **D-13: `[models]` keys.** `sources`, per-source `cache_days`, `[[models.context]]` (D-09), read by Phase 33's layered
  reader and written by its splicing writer; the Artificial Analysis key stays in `secrets.env`. The catalog `_meta.schema_version`
  goes to 4: older caches rebuild, keeping `heuristic_confirmed` fields and dated `verified` usability records (jev bump 0.85).
  A `confirm-model` style subcommand writes one correction with provenance (owner todo: the wizard hand-edited the cache).
- **D-14: Recorded help fixtures.** `tests/fixtures/cli_help/` holds the recorded `--help` of opencode with its version and date
  (2.3.0 today), refreshed by a maintainer command that tests never run; a test extracts the flags named by the opencode
  profile, the runner's opencode argv formulas and its comments and fails on a flag the fixture lacks; the stale
  comment ("models has no `--standalone`") and the 2.0.29 citations are rewritten (jev recorded 0.88). Effort levels come
  from `variants` in `/api/model`; their names were not recorded and the executor records them from a live run.
- **D-15: router-env aliases are assumed.** Marked router with fallback quota, no models.dev or Artificial Analysis
  lookup, no heuristic question, label `assumed: router-env alias naming` (owner todo item 6).

### The hardcoding guard (SPEC R11)

- **D-16: The guard is position-based and needs no name list.** It checks the places a model name is expected: values of
  keys named like `model`, the argument after a model flag, provider/model shaped literals in code and inline code, and
  seed-row cells; each must match an allowed form. A vendor-stem list would itself hardcode names and go stale. jev
  positions 0.84 (typesafe; laya low 0.51 name_list).
- **D-17: Allowed forms.** `router-env/<x>` (tests for pi and opencode only, owner answer 1); for the bare-id host formats
  (cursor, codex, claude) invented structure-only placeholders, grammar fixed by the plan (for example
  `placeholder-model-<n>`, `placeholder-model-<n>-high`, `placeholder-alias-<n>`) that are not real names and that the guard
  recognizes; marked examples (a `model-example:` marker in a comment, docstring, doc, or a field named `example`) only in
  comments, docstrings, docs and example fields, never in a branch, membership test, default or gate. **Needs owner
  confirmation** (placeholders: jev laya marker low 0.55, typesafe placeholders low 0.57; own reasoning: placeholders keep
  the owner's rule intact for formats that cannot carry `router-env/`). Ledger.
- **D-18: A committed baseline that can only shrink.** `tests/fixtures/no_hardcoded_models_baseline.json`: sorted, duplicate-free
  paths, each with the phase that cleans it; a new violation fails, and a baseline path that no longer violates also
  fails; this phase cleans the files it rewrites (detection, catalog, matcher, spec-config SKILL.md and references, the opencode
  profile). It is an arch-group module with non-vacuity cases, extending `tests/test_arch.py`'s convention (owner answer 2).
  `cross-ai.mjs` examples must carry the marker; its decision-making lists (SPEC findings) go to Phases 37-38.

### Scope notes and todo folding

- **D-19: Todo folding.** From the 2026-11-16 wizard todo: items 1 (complete catalog with TTL), 6 (router aliases assumed) and 7
  (copilot through herdr) fold into this phase (R3, R5, R10, D-11, D-15); item 2 (ranked short choice per purpose) is
  Phase 36's proposal and takes this catalog as input; items 3-5 go to Phase 36 with the 2026-10-29 lane-TOML todo. The
  other 12 matched todos concern other skills, not folded.
- **D-20: jev, web and herdr are conditional.** Each is probed at runtime; every path has a tested absent behavior (rails).
  Web queries carry no project, user or machine detail; fetched and pane text is data.

### Handoffs to later phases

- **Phase 36**: takes tiers, classes, cost bands, strengths and usability as inputs; its hardcoded-referee test is the same
  guard family (D-16 to D-18), not a second mechanism; owns the gating paths in `config_io.py`, `commands.py:66` and the
  `routing.py` `review_only` route that this phase only lists.
- **Phase 37**: owns `cross-ai.mjs` gating (unknown runtime and cli throws, the `modelId` regex gate, claude `exec: null`)
  and its marked-example cleanup; the settings report reads the catalog's learned facts.
- **Phase 38.1**: a `rejected` usability line holds the first error line today; it adopts the closed reason list when 38.1 lands.
- **Phase 39**: reads the prompt window from `runtimes[<id>]` (D-09) or the `[[models.context]]` override.
- **Phase 38**: its baseline entries for the runner file are cleaned there.

### Open questions for the phase researcher

- Names inside `variants` of opencode's `/api/model` (not recorded).
- Class thresholds against the live catalog (D-06).
- A cheaper Arena read and the category set for strengths (D-03).
- Whether herdr can read copilot's `/model` list reliably (D-11 spike).
- Artificial Analysis terms of use: redistribution and caching rules (unverified).

### Plan-time amendments (2026-11-19, from 35-RESEARCH.md; each is a live-verified fact or an own-reasoning call)

These answer the open questions above and refine the decisions without reopening them. Source for every number: 35-RESEARCH.md.

- **Amend-1 (D-06, class inputs):** the class rule reads tier, the coding edge (coding rating minus overall rating, source
  relative), cost band and tokens-per-second percentile; context is not a class input, because 603 of 4247 models.dev ids
  state different windows on different providers, so a window is a per-runtime fact (D-09), not a model-class fact. Cut
  points are percentiles of the current refresh's rows, never absolute numbers. Own reasoning.
- **Amend-2 (D-04, identity):** the cache key stays `canonical_key` (no key migration); models.dev's own `canonical_model_id`
  (present on 86 percent of rows) is stored as the entry's `identity` field when the matched row has it. Own reasoning.
- **Amend-3 (D-17, grammar):** allowed invented forms are `placeholder-model-<n>[-<effort>]`, `placeholder-alias-<n>`,
  `fake/<token>` and `fake-<token>`; every other non-`router-env/` name fails the guard or sits in the baseline. Own reasoning;
  it was already flagged for owner confirmation (OWNER-DECISIONS-2026-11-16.md accepted invented neutral names).
- **Amend-4 (D-11, web source):** stdlib code cannot call a host's web-search tool, so the skill (the agent) runs the one
  generic query and writes a JSON file `{runtime, query, url, date, names[]}`; Python validates the file, filters names by
  the model-id pattern and records them labeled "web, unverified". Own reasoning, consistent with D-20.
- **Amend-5 (R7, Artificial Analysis terms):** read live (Data Platform Terms v1.1, revised 2026-08-19): free-tier use is
  Internal Use only; raw data redistribution and external distribution of derived data are not granted; attribution
  "Source: Artificial Analysis (artificialanalysis.ai)" is required; no caching clause was found (PDF pages 7 onward unread).
  The output line therefore says "not granted for redistribution (free tier); caching rule not stated" instead of
  "unverified", AA stays optional and key-gated (each user is their own customer), and its values never enter a tracked file.
  Term 2.5 (model-selection products offered to third parties) is a risk the owner may want to read; it is reported, not decided here.
- **Amend-6 (R6, codex):** `codex debug models --bundled` states `context_window` (int) per model (verified 2026-11-19), so the
  codex host figure is that key; `max_context_window` is kept beside it as a separate measured fact, never mixed into one value.
- **Amend-7 (R1/R9, opencode):** the installed opencode is 2.3.2 (the fixture records the version it was recorded with); the first
  `/api/model` request can answer HTTP 503 for about 5 s, so the probe retries (2 s pause, 6 tries, inside the 15 s deadline);
  `variants` is a list of `{id, settings}` objects whose ids are stored as listed (`high, low, max, medium, minimal, none,
  thinking, xhigh` seen); `cost` there is a list, not models.dev's dict.
- **Amend-8 (R1, pi):** pi is listed through RPC `get_available_models` (`detection.py`), not `pi --list-models --offline`; no change to that path.
- **Amend-9 (R8):** `check-providers` already prints "absent" for a missing config file at HEAD (verified in a scratch HOME,
  pinned by `tests/test_ai_kit_spec_check_providers.py`); the phase keeps those tests green and adds no code there.
- **Amend-10 (D-03, Arena):** one `/filter` query per category with `"category"='<name>'` (double-quoted column; `IN` and a
  single-quoted column answer HTTP 422), seven categories (overall, coding, math, hard_prompts, instruction_following,
  creative_writing, multi_turn), about 35 pages and 15 s, retry 3 times then fall back to `/rows` pages; field `rating`.
- **Amend-11 (D-11, herdr):** the copilot `/model` spike is not run in planning; the herdr code path is written and tested against a
  fake and its output stays labeled "interactive view, unverified" until the spike is run.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/35-model-discovery-and-catalog/35-SPEC.md` (requirements, live facts, findings)
- `.planning/phases/33-one-config-design/33-CONTEXT.md` (D-03 `[models]`, D-22 reader), `docs/config/design.md`
- `.planning/todos/pending/2026-11-16-spec-config-wizard-owner-observations.md`
- `skills/ai-kit-spec-review/ai_kit_spec/` (`detection.py`, `catalog_build.py`, `model_catalog.py`, `model_matcher.py`,
  `model_sources.py`, `cache.py`, `routing.py`), `skills/ai-kit-spec-review/references/cross-ai.mjs`,
  `skills/ai-kit-spec-review/references/cli-profiles/opencode.md`, `skills/ai-kit-spec-config/SKILL.md`
</canonical_refs>
