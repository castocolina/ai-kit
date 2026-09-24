# Phase 16: ai_kit_spec Extensions - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning

<domain>
## Phase Boundary

The shared `ai_kit_spec` package (`skills/ai-kit-spec-review/ai_kit_spec/`) gains what the
curated-config v2 rewrite (Phases 17–18) needs:
- host detection for pi and codex, in a new precedence order;
- real model enumeration for **codex and claude** (opencode already exists);
- `image_input` and reasoning data in the model catalog;
- role-based ranker purposes.

Every existing caller keeps working.

**Host focus for this phase: claude, codex, opencode.** Cursor and pi work beyond one trivial
detection entry is deferred to their own phases (21 and 22). See D-06 and `<deferred>`.

</domain>

<decisions>
## Implementation Decisions

### Host detection
- **D-01:** Adopt the spec precedence **globally**: pi > opencode > cursor > claude > codex.
  - **AMENDED 2026-09-23 by Phase 20 D-02:** the order is now **pi > opencode > cursor > codex >
    claude**, with claude last. Claude is the user's usual outer orchestrator, so a codex
    launched from Claude must not read as claude.
  - This replaces decision 01.2 D-02 (claude > opencode > cursor > codex) in
    `detection.py` `_RUNTIME_ENV_SIGNALS`. It applies to every caller, including
    `ai-kit-spec-config`'s `detect-current-runtime` → `native_runtime`.
  - Rationale: when CLIs nest, env vars accumulate, and the innermost CLI should win. For
    example, claude spawning `opencode run` must read as opencode.
  - Update the docstring's per-signal verification labels and the tests that pin the old
    order.
  - **Reversibility:** costly — `native_runtime` values written into existing reviewer configs
    under a nested session would differ; tests and docs pin the order.
- **D-02:** The codex host signal is **either** `CODEX_THREAD_ID` or `CODEX_VERSION`.
  - `CODEX_THREAD_ID` was observed in real codex session shell snapshots under
    `~/.codex/sessions` (20 occurrences).
  - `CODEX_VERSION` stays; it was source-inspected in 01.2.
  - Drop `CODEX_SANDBOX` from the spec: it was never observed.
  - The codex label stays "not live-verified" until Phase 20 (EVAL-04) confirms it from a real
    codex host.
- **D-03:** The pi signal is `PI_CODING_AGENT`. It was source-inspected in the installed
  `@earendil-works/pi-coding-agent` `dist/config.js`, so label it source-inspected, not
  live-verified.
  - It is included in the precedence tuple now because it costs one line.
  - Pi enumeration is deferred (D-06).

### Model enumeration
- **D-04:** Claude uses a **hybrid** source:
  - the aliases `fable`, `opus`, `sonnet`, `haiku` are hardcoded, because they are what Claude
    Code's `--model` resolves;
  - full ids come from models.dev's `anthropic` provider through the model catalog refresh path;
  - a small **dated** fallback list of full ids is used when no catalog is available, and is
    labeled as a dated fallback rather than a live list (confidence labeling).
  - Claude Code has no list-models command (`claude --help` confirms that `--model` only
    accepts an alias or a full name).
- **D-05:** Codex enumeration uses `codex debug models` from the real binary (resolved via PATH,
  e.g. `~/.volta/bin/codex`).
  - The parser is built from captured real output, stored as a test fixture.
  - Like the existing parsers, it degrades to an empty or partial list and never crashes on a
    format change.
- **D-06 (scope):**
  - **Pi enumeration** (`pi --list-models` plus its fixtures) moves to **Phase 22**. This is the
    pi half of SPEC-02.
  - **Cursor wrapper resolution** also moves out: `cursor-agent` is a shell function on this
    machine and is not on PATH, so `shutil.which` can't see it. It moves to **Phase 21**.
  - Phase 16 does not touch cursor enumeration beyond keeping the existing behavior.
  - This follows the user's direction: "focus on opencode, codex and claude and defer cursor
    and Pi".
- **D-07:** Always invoke real binaries, never shell functions or aliases. The user's `claude`
  is an alias (`claude --dangerously-skip-permissions`) and `cursor-agent` is a function.
  `shutil.which`/`subprocess` already skip both; keep it that way and never run through
  `bash -i`.

### Catalog fields
- **D-08:** **Reuse the existing `reasoning_modes: list[str]`** catalog field for reasoning
  levels (e.g. `["low","medium","high","xhigh"]`). Do not add `reasoning_levels`.
  - Record an erratum in the spec (§3.1 and §2 say `reasoning_levels`).
  - The field is already type-validated in `model_catalog.py` but nothing writes it yet.
- **D-09:** `image_input: bool` is optional and sourced in this order:
  1. models.dev `modalities.input` contains `"image"`;
  2. `opencode models --verbose` for opencode-routed ids that have no models.dev match (e.g.
     `router-env/*`);
  3. otherwise the field is **absent**, meaning unknown, and is never written as `false`.
     Consumers (Phase 17's vision rule) treat absent as not eligible.
  - Add `image_input` to `_FIELD_TYPES`.
  - Cached entries without the field still load (SPEC-03).

### Ranker
- **D-10:** Add the purposes `planning`, `general`, `mechanical`, `execution` and `review` to
  `references/ranking-weights.toml` and `DEFAULT_WEIGHTS`.
  - The old purpose names keep working as aliases: `review` → `review`,
    `execute` → `execution`.
  - `_is_valid_weights_structure` must validate every purpose it knows. A weights file that
    only has the old two purposes must still load; the missing new purposes fall back to
    defaults, and the whole file is not rejected.
- **D-11:** The **mechanical** purpose gets an **optional per-purpose floor table** in the TOML,
  e.g. `[mechanical.floor] coding_index = <n>`.
  - Candidates below the floor are **excluded** from the result, not zero-scored.
  - A candidate whose floor axis is **missing** is excluded. The existing
    `_MISSING_AXIS_DEFAULT` of 49 must not satisfy a floor, because unknown does not prove it
    is above the floor.
  - Floors are generic, so any purpose may declare one. Only mechanical ships with a floor.

### Cache
- **D-12:** Add `schema_version` to `runtimes.json` and `model-catalog.json`.
  - A missing or older version counts as **stale** under `--if-stale`, whatever the TTL says.
    This forces one automatic refresh, so existing 30-day caches (which lack codex/claude model
    lists and new fields) are not trusted.
  - No manual deletion is needed.
  - **Reversibility:** reversible.

### Claude's Discretion
- The weight values for the new purposes. Start from spec §4:
  - planning: max intelligence and agentic, low price weight;
  - general: balanced;
  - execution: coding and agentic with a high price weight;
  - mechanical: price-dominant plus the floor.
- The mechanical floor's default value.
- The exact `schema_version` representation.
- The codex parser's shape, which is dictated by the captured output.
- Whether the claude dated fallback list lives in code or in `references/`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md` §2, §3.1, §4, §9 — the
  approved design. §3.1 is this phase's scope. It needs errata per D-02 (codex signals),
  D-06 (pi/cursor scope) and D-08 (`reasoning_modes`).
- `.planning/REQUIREMENTS.md` — SPEC-01..04. The pi enumeration half of SPEC-02 is re-mapped to
  Phase 22 per D-06.
- `.planning/ROADMAP.md` — the Phase 16 success criteria.

### Prior decisions being superseded or extended
- `.planning/milestones/v1.0-phases/01.2-multi-cli-runtime-foundation/` (CONTEXT/RESEARCH) — the
  original D-01..D-09 for runtime detection (fixed order, never-cached `detect_current_runtime`,
  per-signal verification labels). D-01 here replaces its order.
- `AGENTS.md` §`detect_installed_clis()`/`detect_current_runtime()` — the project-level contract
  text. Update it if the order is described there.

### Project constraints
- `.planning/PROJECT.md` Constraints — confidence labeling (drives D-03, D-04, D-09), the
  stdlib-only runtime, and English-only artifacts.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ai_kit_spec/detection.py`:
  - `_RUNTIME_ENV_SIGNALS`, `detect_current_runtime` (edit the order and add signals);
  - `detect_opencode_models` / `detect_cursor_agent_models`, which show the parser pattern
    (injected `run_fn`, `timeout=15`, degrade to `[]`);
  - `build_runtimes_snapshot` (add codex and claude model entries);
  - `KNOWN_CLIS` (has no `pi` yet; adding it is Phase 22's concern).
- `ai_kit_spec/model_catalog.py`: `_FIELD_TYPES` (add `image_input`; `reasoning_modes` already
  present), `validate_catalog_entry`, `merge_catalog_entry`, `CATALOG_TTL_SECONDS`.
- `ai_kit_spec/model_sources.py`: `fetch_models_dev`, `match_models_dev`, the source of
  modalities (D-09) and of anthropic full ids (D-04).
- `ai_kit_spec/model_ranker.py`: `DEFAULT_WEIGHTS`, `load_ranking_weights` (never raises),
  `_is_valid_weights_structure`, `score_candidates`, `_MISSING_AXIS_DEFAULT`.
- `ai_kit_spec/cache.py`: `cache_read_json` / `cache_write_json` / `cache_is_stale`. This is
  where the `schema_version` staleness check (D-12) hooks in.
- `skills/ai-kit-spec-review/references/ranking-weights.toml`: the data file for D-10 and D-11.
- `ai_kit_spec/cli.py`: the `detect-runtimes --if-stale PATH` and `fetch-model-catalog` wiring.

### Established Patterns
- Subprocess calls take an injected `run_fn`/`which_fn` for tests. They time out and degrade to
  empty results; they never raise.
- Detection docstrings record, per signal, whether it was live-verified or only
  source-inspected. Keep that for the new pi and codex signals.
- Weights and catalog loading "never block": malformed input falls back to defaults or rejects a
  single entry.
- Tests: `tests/test_ai_kit_spec.py` (detection/catalog/ranker), `tests/fixtures/`. Fixtures
  come from real CLI output.

### Integration Points
- `skills/ai-kit-spec-config/SKILL.md` Step 2.7 consumes `detect-current-runtime`. It is
  affected by D-01's order change.
- Phase 17's `catalog_adapter.py` / `roles.py` will consume the new purposes, the floor, the
  catalog fields and the host model lists.

</code_context>

<specifics>
## Specific Ideas

- **Codex evidence:** the codex shell-snapshot preamble in real sessions contains
  `export CODEX_THREAD_ID="${__CODEX_SNAPSHOT_OVERRIDE_1}"`. Cite it in the detection docstring
  as the source of the "observed in session snapshots" label.
- **Current model generation** (per this environment): Fable 5.1, Opus 5.5, Sonnet 5, Haiku 4.5.
  Seed the claude dated fallback list from the ids current at implementation time, and date it.
- **Current machine state:** the catalog cache `~/.cache/ai-kit/spec/model-catalog.json` does
  not exist yet; only `runtimes.json` and `quota.json` do. The live verification of this phase
  should run a real `fetch-model-catalog` (it needs `ARTIFICIAL_ANALYSIS_API_KEY` for the AA
  source; models.dev needs no key).

</specifics>

<deferred>
## Deferred Ideas

- **Pi model enumeration** (`pi --list-models` parser plus fixtures, `pi` in `KNOWN_CLIS`) →
  Phase 22 (pi live validation). Moved from SPEC-02 per D-06.
- **Cursor wrapper resolution** (`cursor-agent` as a shell function; locate the real binary via
  known install paths or an env override) → Phase 21 (cursor live validation).

</deferred>

---

*Phase: 16-ai-kit-spec-extensions*
*Context gathered: 2026-09-23*
