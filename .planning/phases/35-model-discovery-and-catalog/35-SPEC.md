# Phase 35: Model discovery and catalog — Specification

**Created:** 2026-11-16
**Ambiguity score:** 0.14 (gate: ≤ 0.20)
**Requirements:** 12 locked

## Goal

spec-config shows every model the machine can reach on claude, opencode, pi, cursor, codex and copilot, with where each
model was listed from, a usability state kept apart from the listing, and catalog facts (tier, class, relative cost,
modalities, strengths, context window per runtime) merged from models.dev, Artificial Analysis and the Arena leaderboard,
each value labeled measured or judged and carrying its source and cache time. Removed models are flagged stale only on
proof, the opencode profile matches the installed opencode's own help, and a guard keeps hardcoded provider and model
names out of the project.

## Background

Requirements HUB-02, HUB-03, HUB-06, HUB-08 (REQUIREMENTS.md "spec-config as the hub"), plus HUB-09 added for this
spec (the hardcoding rule). Phase 33 reserved `[models]` in `config.toml` for this phase (33 D-03) and the layered reader
and splicing writer are reused.

**The owner's decisions (2026-11-14 and 2026-11-16, highest priority):**

- Catalog first: spec-config catalogs every reachable model, downloads models.dev and Artificial Analysis, classifies;
  Phase 36 proposes a coding set and a review set from it. Nothing is labelled review by default (2026-11-14).
- Arena is merged whenever enabled in `[models]`. Reason: Artificial Analysis needs a key and some of its properties
  can be incomplete, so the sources complement each other. This replaces the 2026-11-14 wording "alternative when
  Artificial Analysis is unavailable" (owner-confirmed 2026-11-16).
- A runtime with no non-interactive model list gets a seed row (labeled unverified), and optionally a web search and,
  when herdr is available at runtime, an extraction from the host's interactive view. Both are optional sources labeled
  by how sure they are, never required; web queries carry no project, user or machine detail.
- The same model has different names per runtime (claude short aliases, copilot dashed ids, cursor names that carry
  the effort). Matching a host name to a models.dev entry asks jev-fast-decision when it is available at runtime
  (summaries only); without jev it is deterministic normalization plus a visible "unmatched" state. Effort suffixes
  are parsed out of a name as an effort setting, not part of the model identity.
- Context size is a per-runtime fact: the catalog keeps it per (runtime, model) with a source label, and Phase 39's
  prompt-size check reads the runtime's value.
- HARDCODING RULE: only `router-env/<x>` model names may be hardcoded (code, defaults, rails, skills, tests as
  expected values), and for tests only for pi and opencode, the hosts with a provider/model form. Every other provider or
  model name comes from live discovery, the catalog or the user's config. A guard with a committed baseline that can
  only shrink enforces it; `cross-ai.mjs` may hold clearly marked examples but no list that decides anything.
- A runtime table (`RUNTIMES` in `detection.py` and in `cross-ai.mjs`) is seed data and examples only, each row labeled
  with its source; it never decides. Live evidence beats a row.

**Live facts checked for this spec (2026-11-16, this machine; versions claude 2.1.325, opencode 2.3.0, pi 1.5.2,
cursor-agent 2026.11.13, codex 0.169.0, copilot 1.0.112):**

- Listings: `opencode models` (79 models, exit 0, also accepts `--standalone`; `--verbose` is no longer a flag),
  `pi --list-models --offline` (columns provider, model, context, max-out, thinking, images), `cursor-agent models`
  (284 lines), `codex debug models` (`--bundled` skips refresh). claude has no listing command (aliases only). copilot
  has no non-interactive listing (`copilot models` is not a command; only the interactive `/model`); it takes
  `--model`, `--reasoning-effort none..max` and `--session-id`.
- opencode 2.3.0 `GET /api/model` (through the private-server helper in `detection.py`): every model has `variants`
  (the effort levels), `limit.context/input/output`, `cost`, `status`, `enabled`, `family`,
  `capabilities.input/output`. The names inside `variants` were not recorded (unverified).
- models.dev: 324 providers, 9895 models; fields include `limit.context/output`, `cost`, `modalities`, `reasoning`,
  `reasoning_options` (7781 models), `status` (966 models), `family`. Repository license MIT; no attribution request
  found in its README.
- Arena: Hugging Face dataset `lmarena-ai/leaderboard-dataset`, license cc-by-4.0 (Hugging Face API, 2026-11-16). The
  datasets-server JSON rows API returns config `text`, split `latest`: 11177 rows with model_name (display names),
  organization, license, rating, rating_lower/upper, variance, vote_count, rank, category,
  leaderboard_publish_date. Plain HTTP and JSON reach it, so no parquet reader is needed.
- Artificial Analysis: its free API page says "Attribution is required for all use of our free API" (credit
  artificialanalysis.ai). Its terms of use and any redistribution rule were not read (unverified).
- Existing code: `build_model_catalog` merges models.dev and Artificial Analysis (key from `secrets.env`) into
  `scores`, `pricing`, `image_input`, `reasoning_modes`, `tokens_per_sec` and a per-runtime `ctx_window` (models.dev
  `limit.context`, pi's exact integer); `current_candidate_keys` silently drops unlisted entries; there is no Arena
  source, no usability state, no tier, class or strengths, no listing for copilot; the cross-ai opencode comments and the
  opencode profile cite opencode 2.0.29 (profile `last_verified` 2026-08-28).

**Findings (existing code, listed for later phases; this phase changes none of the gating paths):**

- Code that gates on the runtime tables (against the "a table never decides" rule): `routing.py` `unknown_runtime`
  (line 141), `no_inventory` (156) and `review_only` (177); `config_io.py` lines 104-105 and `_RUNNER_RUNTIMES` (713);
  `cli.py` 476 and 928-929; `commands.py` 66 (the execute set excludes `review_only`); `detection.py` `review_only`
  and `runner=False` fields; `cross-ai.mjs` lines 5321 and 5327 (unknown runtime or cli throws), 12583 (the `modelId`
  regex gate), claude `exec: null` and `list: null`. Phases 36-39 and 38.1 own these (see CONTEXT).
- Hardcoded provider or model names outside `router-env`: 17 files in `skills/`, 2 in `tools/`, 34 in `tests/`, 18 in
  `docs/` (names matched by a family pattern, 2026-11-16). Notable: `CLAUDE_FALLBACK_MODEL_IDS` and
  `_FIRST_PARTY_PROVIDER_BY_CLI` in `detection.py` and `catalog_build.py`, name literals in `model_matcher.py`,
  `vendor.py`, `quota.py`, `commands.py`, `gsd_tools.py`, 11 matching lines in `cross-ai.mjs`, the opencode, cursor and
  codex profiles, `spec-config/SKILL.md` and `references/cli-model-selection.md`, curated-config `roles.py` and
  `preference_match.py`, a referee name in a goal-prompt eval fixture, and the self-test names in the runner and tests.

## Requirements

1. **Discovery per host with its source (HUB-02)**: spec-config lists providers and models from claude, opencode, pi,
   cursor, codex and copilot, and records per (runtime, model) where it was listed from.
   - Current: claude (aliases), opencode, pi, cursor and codex are enumerated in the runtimes snapshot; copilot has
     no listing; the catalog entry does not say which command or source listed a model or when.
   - Target: each (runtime, model) carries `listed_from` (the listing command and host version, or a named optional source of
     R3) and the listing time; opencode's providers come from its own `/api/model`, pi's and codex's from their listings;
     a runtime missing from the table with an installed binary shows as "installed, no listing" with no models until the
     user names some; a failed listing is reported with its error and leaves the cached entries untouched.
   - Acceptance: fixture-driven tests (recorded listings from fake hosts) cover each host's listing, a failed listing,
     an installed runtime that is not in the table, and a model listed by two hosts under different names.

2. **A usability state kept apart from the listing (HUB-02)**: every (runtime, model) shows `verified` (with the date and
   how), `rejected` (with the error) or `unverified`, visibly.
   - Current: a listed model is treated as available; Step 2.5 tests a pair before saving but records nothing in the catalog.
   - Target: the state lives beside the listing facts; only a real call that answered marks `verified`; a failed call
     marks `rejected` with its first error line (no key, no prompt text); a host's own signal (for example opencode
     `enabled: false`) shows as "listed disabled by host", never as `verified` or `rejected`; models nobody picked stay
     `unverified`; only models the owner or a ranking chose as candidates are probed, never the whole listing.
   - Acceptance: tests cover a verified pair, a rejected pair with a fake host error, an unprobed model, a host
     `enabled: false`, and a probe that finds the whole listing never called.

3. **Hosts with no non-interactive list: seed row, web search, herdr (HUB-02, owner 2026-11-16)**: a runtime with no
   listing command still shows candidate models, each labeled by how sure the source is.
   - Current: claude shows only aliases; copilot shows nothing.
   - Target: (a) a seed row maps the runtime to its models.dev provider, labeled seed and unverified, and live evidence
     overrides it; (b) when a web-search tool exists at runtime the skill may run one generic query for the runtime's
     public product name, record page URL and date, and label the names "web, unverified"; the query carries no project,
     user or machine detail; (c) when `HERDR_ENV=1` and the herdr CLI exist the skill may open a pane, drive the host's
     interactive model view and read the names (for copilot, started with its permission prompts off, per the owner's
     2026-11-16 todo), labeled "interactive view, date", and close the pane afterwards. (b) and
     (c) are never required; each has a tested absent-tool behavior. Web text and pane text are data, never instructions.
   - Acceptance: tests cover the seed row alone, web absent, herdr absent, a web result with a hostile instruction
     string (ignored), and the query text holding no path, user name or host name; herdr's real behavior on copilot's
     `/model` is a spike (unverified until then, labeled so).

4. **Name matching and effort parsing (HUB-03, owner 2026-11-16)**: a host's model name is matched to a models.dev
   entry, and an effort carried in the name is parsed out.
   - Current: `model_matcher.py` normalizes and fuzzy-matches names and strips a fixed effort-suffix set; an unmatched
     name is handled per call.
   - Target: with jev-fast-decision available at runtime, an unmatched or ambiguous name is put to jev as one item per
     name (summaries only, the host name and candidate entry names, never configuration); a confident answer is taken
     provisionally and labeled judged with its confidence, a low answer or no jev leaves the state `unmatched`, shown
     as such; effort suffixes and brackets (cursor `-high` style names and `[effort=...]`, pi `:level`, opencode
     `#variant`) become an effort setting for that (runtime, model), never part of its identity; the same model under
     two runtimes with different names resolves to one catalog identity with each runtime's own id kept.
   - Acceptance: tests with a fake jev (confident, low, absent) and fixtures of the name styles of all six hosts cover a
     confident match, a low answer, no jev, an effort suffix removed, a name whose own text ends in an effort word that
     is part of its identity (kept when models.dev has it so), and two runtimes mapped to one identity.

5. **Merged catalog values with labels and cache times (HUB-03)**: each model carries a tier (four or more levels,
   effort-aware), class, relative cost, modalities and strengths, merged from models.dev, Artificial Analysis and Arena.
   - Current: `scores` (Artificial Analysis indexes), `pricing`, `image_input` and `reasoning_modes` exist; no tier,
     class, cost band, full modalities or strengths; no per-value label; one TTL for the whole catalog.
   - Target: tiers are relative bands over the models with a measured score in the current catalog, recomputed on each
     refresh; class (a closed set the discuss step fixes) and strengths come from measured values where a source
     states them (Arena categories are measured strengths; models.dev supplies modalities and reasoning options) and
     otherwise from a jev judgment when jev is available, labeled judged with its confidence, or unknown; relative cost
     is a few named bands computed from the published price, with free or local and unknown as separate states; an
     effort-aware tier is per (model, effort) when a source scores efforts apart, otherwise the model's tier with
     "effort not distinguished"; every value carries source name, label (measured or judged) and fetched-at time; each
     source is cached by its own age from `[models]`; Arena and Artificial Analysis complement each other per property;
     an owner router alias (`router-env/<x>`) is assumed, not asked: it is marked router with fallback quota, gets no
     models.dev or Artificial Analysis lookup and no per-model heuristic question, and carries the label
     `assumed: router-env alias naming`, never verified (owner todo 2026-11-16, item 6).
   - Acceptance: tests with synthetic source payloads cover a model scored by both, by one only, by neither (unknown tier,
     never a guess), an Artificial Analysis outage keeping cached values, Arena disabled in `[models]`, a judged class
     with a fake jev and without jev, and each value's label and time.

6. **Context size per (runtime, model) (HUB-03 amended 2026-11-16)**: the catalog keeps the context window per
   (runtime, model) with a source label; Phase 39 reads the runtime's value.
   - Current: `runtimes[rid].ctx_window` exists but comes from models.dev for every runtime except pi (exact), with no
     label; opencode's own `limit` and codex's listing are not read.
   - Target: the value is the host's own figure when the host states one (pi listing, opencode `/api/model`
     `limit.context` and `limit.input`, codex listing), else models.dev's, labeled by source and measured or judged, else
     unknown, shown as unknown; never guessed from a name; `[models]` may hold a user-stated override per (runtime, model);
     output states which value and label applies to which runtime.
   - Acceptance: tests cover one model with two different windows on two runtimes, a host value beating models.dev, an
     unknown shown as unknown, a user override beating both, and an output line per runtime.

7. **Attribution shown, no Artificial Analysis data shipped (HUB-03)**: every source's required attribution appears in
   the catalog output and no Artificial Analysis data is committed or shipped.
   - Current: no attribution is shown; fixtures are synthetic but nothing guards it.
   - Target: the output names each used source with its credit line (Artificial Analysis: credit to artificialanalysis.ai,
     required by its free API page; Arena: dataset name, CC BY 4.0, and "values derived from it" because tiers are derived;
     models.dev: name and URL, repository license MIT, no attribution request found) and marks the Artificial Analysis
     redistribution terms unverified; Arena data comes from the official CC-BY-4.0 dataset read at runtime and kept in the
     user's cache; no response data of Artificial Analysis enters the repository or an installed package.
   - Acceptance: a test checks the attribution lines per enabled source; an arch test fails when a tracked file holds
     an Artificial Analysis response shape with real-looking values (fixtures must be synthetic and say so).

8. **Stale flags on proof (HUB-06)**: removed models and providers no longer configured are flagged stale in the output.
   - Current: `current_candidate_keys` drops unlisted entries from ranking without saying so.
   - Target: a (runtime, model) is `stale` only when a live listing for that runtime succeeded this run and no longer
     holds it, shown with its last-seen time; a failed or skipped listing shows "not checked", never stale; a provider with
     catalogued models but no longer configured in the host shows as stale-provider; models.dev `status` values show as
     "marked by source" apart from stale; stale entries stay in the cache and out of ranking; the existing
     `check-providers` report says "absent" for a config file that does not exist, never "untrusted" (owner todo
     2026-11-16, observed defect).
   - Acceptance: tests cover removed model after a good listing, the same entry after a failed listing (not stale), a
     removed provider, a source-marked status, and a model that reappears (stale flag cleared).

9. **The opencode profile and runner comments match the installed help (HUB-08)**: they match opencode's own `--help`, the
   effort levels its model API lists and the `opencode models` flags, and a test fails on a flag the recorded help lacks.
   - Current: the profile and runner comments cite 2.0.29 and say `opencode models` has no `--standalone` flag; the
     installed 2.3.0 lists it as a global flag; the profile names provider and model ids.
   - Target: recorded help texts of `opencode --help`, `run --help` and `models --help` (with version and date) are
     fixtures refreshed by a maintainer command; the profile and the runner's opencode comments are rewritten to
     the recorded help; opencode's effort levels come from `variants` in `/api/model` into the catalog's reasoning modes;
     provider ids in docs are examples marked as such (R11).
   - Acceptance: a test extracts the flags named by the opencode profile, the runner's opencode argv formulas and
     its comments and fails when one is missing from the recorded help; a planted stale flag makes it fail; the
     fixture records its version.

10. **`[models]` settings and the catalog schema (HUB-03, 33 D-03)**: `config.toml` `[models]` holds the catalog
    settings and the cache schema moves to a new version.
    - Current: `[models]` is documented, not read; the catalog is schema 3 with one TTL; Artificial Analysis's key lives in
      `secrets.env`.
    - Target: `[models]` keys `sources` (any of models.dev, artificial-analysis, arena), per-source `cache_days`, and
      `[[models.context]]` overrides per (runtime, model), read through Phase 33's layered reader (project over user)
      and written through its splicing writer; the key never enters `config.toml`; the catalog `_meta.schema_version` rises so
      older caches rebuild on the next run while user-confirmed heuristic fields and dated `verified` usability records
      are kept.
    - Acceptance: tests cover project over user, an unknown source name (named error), a write that keeps comments, a
      v3 cache upgraded with confirmed fields and verified records kept, and the key absent from the file.
    - Also: a subcommand confirms or corrects one catalog entry with its provenance, so no run edits the cache with an
      ad-hoc script or guesses the key format (owner todo 2026-11-16: the wizard hand-edited the catalog); a test
      covers a confirmed correction surviving a refresh.

11. **Hardcoding guard with a shrinking baseline (HUB-09, owner 2026-11-16)**: a test fails when a skill, rail, doc,
    default or test hardcodes a provider or model name other than `router-env/<x>`.
    - Current: nothing guards it; the findings above exist.
    - Target: only `router-env/<x>` may be hardcoded as an expected model name, and in tests only for pi and opencode;
      tests for cursor, codex and claude formats use structure-only invented placeholders that are not real provider or
      model names, recognized by the guard (needs owner confirmation); a runtime table row may hold names only as examples
      carrying a source label; `cross-ai.mjs` may hold clearly marked examples but no list that decides anything (a list
      read by a branch, membership test, default value or gate fails); the guard ships with a committed baseline of
      today's violating files, each naming the phase that cleans it; a new violation fails, and a baseline file that no
      longer violates also fails until it is removed from the list; this phase cleans the files it rewrites.
    - Acceptance: tests with planted fixtures show a literal name in a membership test failing, in a default value
      failing, a marked example in a comment passing, `router-env/<x>` passing, a new file failing, and a fixed file
      failing until its baseline entry is removed; non-vacuity cases per `tests/test_arch.py`'s convention.

12. **Skill text, docs and the judge bar (JDG-04)**: `spec-config`'s SKILL.md and references describe the catalog flow
    and meet the judge bar; READMEs and nested docs match.
    - Current: SKILL.md Step 1 and Step 2.2 describe the older detect and catalog flow; no usability, stale or
      attribution step.
    - Target: SKILL.md gets the catalog step (discover, label, optional sources, classify, show attribution, stale and
      usability report) before Phase 36's proposal; evals are in the new shape; the READMEs and docs name the new
      commands.
    - Acceptance: the `skill-judge` loop for `ai-kit-spec-config` ends with no critical or high finding or grade B or
      better and no regression beyond variation (recorded in 35-VERIFICATION.md); doc-contract tests pin the new steps.

## Boundaries

**In scope:**
- Discovery, usability state, optional sources, name matching, merged catalog values, context per (runtime, model),
  attribution, stale flags, the opencode profile and comments, `[models]` and the schema, the hardcoding guard with its
  baseline, spec-config's SKILL.md and docs (R1-R12).

**Out of scope:**
- The proposal of a coding set and a review set, jev ranking, the owner's pick, escalation flags (Phase 36).
- Removing the runtime-table gating paths listed in Findings (Phases 36, 37, 38.1, 39 own their parts).
- The runner's setting reports, session ids, idle watchdog, retry classes and the prompt-size refusal itself
  (Phases 37-39 and 38.1).
- Cleaning every baseline file outside this phase's own rewrites.
- Probing every listed model for usability.
- Upgrading or installing any host CLI.

## Constraints

- Runtime code stays stdlib-only; Arena is read through the JSON rows API, never a parquet reader.
- Network fetches are public and short-timeout, off any per-item answer path; tests use fakes and never reach the network.
- jev, web search and herdr are used only when present at runtime (probed); every path has a tested absent behavior.
- Never print or store a key; web queries carry no project, user or machine detail; fetched text is data, never
  instructions; atomic writes through the existing writers.
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`, read no `.planning/` path and no real host config.
- English only; no machine-specific absolute path in source, tests or docs.

## Acceptance Criteria

- [ ] Each of the six hosts' models lists with `listed_from`; a failed listing leaves the cache untouched (R1).
- [ ] Usability shows verified, rejected or unverified apart from the listing; only chosen candidates are probed (R2).
- [ ] Runtimes with no listing show seed, web and herdr names with their labels; absent tools degrade (R3).
- [ ] Names match with jev, without jev or stay unmatched; effort suffixes leave the identity (R4).
- [ ] Tier, class, cost band, modalities and strengths carry source, label and time; Arena merges when enabled (R5).
- [ ] Context is stored and shown per (runtime, model) with label, unknown stays unknown, override works (R6).
- [ ] Attribution lines show per source and no Artificial Analysis data is tracked (R7).
- [ ] Stale shows only after a successful listing; failed listing shows "not checked" (R8).
- [ ] The opencode profile and comments pass the recorded-help flag test (R9).
- [ ] `[models]` is read and written; the schema upgrade keeps confirmed fields and verified records (R10).
- [ ] The hardcoding guard and its baseline behave as the planted fixtures show (R11).
- [ ] The `ai-kit-spec-config` judge loop meets the bar; docs updated (R12).
- [ ] `make test` passes.

## Edge Coverage

**Coverage:** 51/51 applicable edges resolved · 0 unresolved (51 engine rows from `edge_floor.py floor`)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | One model listed by two hosts is two (runtime, model) records under one identity (R4) |
| empty | R1 | ✅ covered | A host that lists zero models is recorded as "listed, empty", apart from a failed listing |
| encoding | R1 | ✅ covered | Listed ids are compared as exact strings after the host's own suffix rule; matching to models.dev is R4's |
| ordering | R1 | ✅ covered | Output is sorted by runtime, then id; host listing order is never relied on |
| concurrency | R1 | 🧪 backstop | Cache writes are atomic and merge per entry; last write wins |
| adjacency | R2 | ✅ covered | The state is per (runtime, model); verified on one runtime is never shared with another |
| empty | R2 | ✅ covered | No chosen candidate: nothing is probed and every model stays unverified |
| encoding | R2 | ✅ covered | The stored error line has control characters removed, key shapes redacted and a length cap |
| ordering | R2 | 🧪 backstop | Each probe result is stored by key; probe order does not matter |
| adjacency | R3 | ✅ covered | The same model named by seed, web and pane is one record listing every source, strongest label shown |
| empty | R3 | ✅ covered | All optional sources absent: the seed row alone; no seed row: "no candidates", the user may name one |
| encoding | R3 | ✅ covered | Web and pane names lose control and escape characters and must fit the model-id pattern before use |
| ordering | R3 | ✅ covered | Label strength order for display: verified, host listing, interactive view, web, seed |
| adjacency | R4 | ✅ covered | A name equal to a models.dev id plus an effort suffix is parsed; a name whose own id ends in an effort word is kept whole |
| empty | R4 | ✅ covered | An empty or blank name is refused with a named error |
| encoding | R4 | ✅ covered | Matching lowercases and collapses non-alphanumerics (the existing normalization); the stored id stays as the host wrote it |
| ordering | R4 | ✅ covered | Two equally good candidate entries give `unmatched` with both named, never first-wins |
| boundary | R5 | ✅ covered | A score exactly on a band edge falls in the higher band; one step below falls in the lower |
| adjacency | R5 | ✅ covered | Models with an identical score share a tier |
| empty | R5 | ✅ covered | No scored model in the catalog: no tiers, every tier unknown |
| encoding | R5 | 🧪 backstop | Numeric values only; display names reach scores through R4 |
| ordering | R5 | ✅ covered | Ties are ordered by id for display only; the tier never depends on that order |
| precision | R5 | 🧪 backstop | One fixed band formula with a named tie rule; held-out edge test for plan-phase |
| boundary | R6 | ✅ covered | Zero, negative or non-integer windows are invalid: shown unknown with a note |
| adjacency | R6 | ✅ covered | A host value equal to models.dev keeps the host label |
| empty | R6 | ✅ covered | No source states a window: unknown |
| encoding | R6 | ✅ covered | Only exact integers are accepted (the pi human table's "400K" form is never parsed) |
| ordering | R6 | ✅ covered | Precedence: user override, host figure, models.dev, unknown |
| precision | R6 | ✅ covered | Integers only; a float is rejected, never rounded |
| concurrency | R6 | 🧪 backstop | Same atomic cache write as R1 |
| adjacency | R7 | 🧪 backstop | Static credit text |
| empty | R7 | ✅ covered | No source enabled: no attribution lines |
| encoding | R7 | 🧪 backstop | ASCII credit lines |
| ordering | R7 | 🧪 backstop | Sources listed in one fixed order |
| concurrency | R7 | 🧪 backstop | Output only; no shared state |
| concurrency | R8 | 🧪 backstop | Stale flags are computed per run from that run's own listings; two parallel runs merge per entry and the later successful listing wins |
| adjacency | R9 | ✅ covered | A flag that prefixes another (a session flag and its id form) is matched as a whole token |
| empty | R9 | ✅ covered | A profile naming no flag passes the test |
| encoding | R9 | 🧪 backstop | Flags are ASCII `--name` tokens extracted by one pattern |
| ordering | R9 | 🧪 backstop | Order of flags is irrelevant |
| concurrency | R9 | 🧪 backstop | The test reads recorded fixtures only |
| empty | R10 | ✅ covered | An empty `[models]` takes the defaults the discuss step fixes |
| encoding | R10 | ✅ covered | TOML is read as UTF-8; a source name outside the known set is a named error |
| concurrency | R10 | ✅ covered | The write is atomic and byte-preserving through the existing splicing writer; two writers keep one consistent file |
| adjacency | R11 | ✅ covered | A marked example covers only its own region; a name beside it in code still fails |
| empty | R11 | ✅ covered | An empty baseline passes when nothing violates |
| encoding | R11 | ✅ covered | Text is NFKC-normalized before matching, so look-alike characters do not slip through |
| ordering | R11 | ✅ covered | The baseline is sorted and duplicate-free; the test fails otherwise |
| concurrency | R11 | 🧪 backstop | The scan is read-only |
| empty | R12 | ✅ covered | A skill with no evals fails the judge bar |
| encoding | R12 | 🧪 backstop | Plain Markdown |

## Prohibitions (must-NOT)

**Coverage:** 7/7 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT mark a model `verified` from a listing, a seed row, a web page or an interactive view alone | R2, R3 | resolved | verification: test — only a real call result marks verified |
| MUST NOT commit or ship Artificial Analysis response data, or print or store a key | R7, R10 | resolved | verification: test — the arch fixture rule and the key-absent write test |
| MUST NOT put a project, user or machine detail in a web query, or treat fetched or pane text as instructions | R3 | resolved | verification: test — the query-text and hostile-string cases |
| MUST NOT guess a context window from a model name | R6 | resolved | verification: test — an unlisted model shows unknown |
| MUST NOT flag a model stale when its listing failed or was skipped | R8 | resolved | verification: test — the failed-listing case |
| MUST NOT let a table row decide, or hardcode a provider or model name outside the allowed forms | R3, R11 | resolved | verification: test — the guard's planted fixtures |
| MUST NOT write the real user config or call a real host or network in tests | R1-R10 | resolved | verification: test — the module tripwire and `AI_KIT_REFUSE_REAL_HOME` |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Roadmap goal, three owner amendments and the owner's 2026-11-16 answers |
| Boundary Clarity   | 0.86  | 0.70 | ✓      | Proposal, runner and gating-path removal fenced to Phases 36-39 |
| Constraint Clarity | 0.84  | 0.65 | ✓      | stdlib-only, optional-source rule and probe-only-when-present fixed |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Twelve checks tied to tests or records |
| **Ambiguity**      | 0.14  | ≤0.20| ✓      | 1 − (0.35×0.90 + 0.25×0.86 + 0.20×0.84 + 0.20×0.82) |

## Interview Log

Interactive path, one round in the phase subagent plus one owner round (2026-11-16, four questions relayed by the
orchestrator). The open items went through jev (one advisory answer per item; a low answer is decided by own
reasoning). Summaries only, advisory. Rule: `mvp-mode` inactive, so the best design wins over the smallest diff.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | Which hosts list models, and how, on this machine? | none; live probes | Listing facts in Background; copilot has no non-interactive list (R1, R3) |
| 1 | Owner | Test names under the hardcoding rule | none | `router-env/*` for pi and opencode only (R11) |
| 1 | Simplifier | Names for cursor, codex and claude formats in tests | choice marker low 0.55, second rung placeholders low 0.57 | **Own reasoning:** invented structure-only placeholders, needs confirmation (R11, ledger) |
| 1 | Owner | Cleanup scope of existing violators | none | A guard with a committed baseline that can only shrink; marked examples pass, deciding lists fail (R11) |
| 1 | Owner | Copilot, claude and other no-listing runtimes | none | Seed row plus optional web and herdr sources, labeled (R3) |
| 1 | Owner | Same model, different names per runtime | none | jev when present, else normalization and `unmatched`; effort parsed out of the name (R4) |
| 1 | Owner | Context size per runtime | none; jev choice per_runtime 1.00 agrees | Per (runtime, model) with source label (R6) |
| 1 | Owner | Arena merged always or only as an alternative | none | Merged whenever enabled in `[models]`; owner-confirmed, no flag (R5, R10) |
| 1 | Boundary Keeper | When is a real call made to check usability? | chosen candidates only, choice 0.94 | Probe chosen candidates only (R2) |
| 1 | Simplifier | How are tiers derived? | relative bands, choice 0.93 | Relative bands over measured scores (R5) |
| 1 | Failure Analyst | When is a model stale? | laya low (age 0.49), second rung success_only low 0.54 | **Own reasoning:** only after a successful live listing (R8, ledger) |
| 1 | Simplifier | How is Arena read with stdlib only? | json_api, choice 0.96 | JSON rows API (R5, Constraints) |
| 1 | Boundary Keeper | How is the opencode profile kept honest? | recorded help fixtures, choice 0.88 | Recorded help plus a flag test (R9) |
| 1 | Failure Analyst | What happens to existing cache files? | bump, choice 0.85 | Schema version rises, confirmed fields and verified records kept (R10) |
| 1 | Simplifier | How is relative cost shown? | banded, choice 0.88 | Named bands with free or local and unknown apart (R5) |
| 1 | Boundary Keeper | Where does a user correct a context window? | models table, choice 0.97 | Per (runtime, model) override in `[models]` (R6, R10) |
| 1 | Researcher | What does the owner's 2026-11-16 wizard todo add for this phase? | none | Router aliases assumed (R5), copilot through herdr (R3), a confirm subcommand (R10), `check-providers` absent-file defect (R8); items 2-5 go to Phase 36 |

---

*Phase: 35-model-discovery-and-catalog*
*Spec created: 2026-11-16*
