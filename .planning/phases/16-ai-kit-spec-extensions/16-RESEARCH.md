# Phase 16: ai_kit_spec Extensions - Research

**Researched:** 2026-09-23
**Domain:** Python stdlib CLI extension — host/runtime detection, subprocess-based model
enumeration, JSON-schema catalog fields, TOML-driven ranking weights
**Confidence:** HIGH (all touched functions read directly from source this session; codex output
and models.dev data captured live; only the pi/cursor-adjacent edges stay `[ASSUMED]`)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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
- **D-04:** Claude uses a **hybrid** source: hardcoded aliases (`fable`, `opus`, `sonnet`,
  `haiku`), full ids from models.dev's `anthropic` provider via the model catalog refresh path,
  and a small **dated** fallback list of full ids labeled as a dated fallback (not a live list)
  when no catalog is available. Claude Code has no list-models command.
- **D-05:** Codex enumeration uses `codex debug models` from the real binary (resolved via PATH).
  The parser is built from captured real output, stored as a test fixture. It degrades to an
  empty or partial list and never crashes on a format change.
- **D-06 (scope):** Pi enumeration (`pi --list-models` plus its fixtures) moves to Phase 22 (the
  pi half of SPEC-02). Cursor wrapper resolution also moves out to Phase 21 (`cursor-agent` is a
  shell function on this machine, not on PATH). Phase 16 does not touch cursor enumeration beyond
  keeping existing behavior.
- **D-07:** Always invoke real binaries, never shell functions or aliases. The user's `claude` is
  an alias and `cursor-agent` is a function. `shutil.which`/`subprocess` already skip both.
- **D-08:** Reuse the existing `reasoning_modes: list[str]` catalog field for reasoning levels. Do
  not add `reasoning_levels`. Record an erratum in the spec (§3.1 and §2 say `reasoning_levels`).
- **D-09:** `image_input: bool` is optional, sourced in order: (1) models.dev `modalities.input`
  contains `"image"`; (2) `opencode models --verbose` for opencode-routed ids with no models.dev
  match; (3) otherwise absent (unknown), never written as `false`. Add to `_FIELD_TYPES`. Cached
  entries without the field still load (SPEC-03).
- **D-10:** Add purposes `planning`, `general`, `mechanical`, `execution`, `review` to
  `references/ranking-weights.toml` and `DEFAULT_WEIGHTS`. Old names keep working as aliases:
  `review` → `review`, `execute` → `execution`. `_is_valid_weights_structure` must validate every
  purpose it knows; a weights file with only the old two purposes must still load, missing new
  purposes fall back to defaults, whole file is not rejected.
- **D-11:** The mechanical purpose gets an optional per-purpose floor table in the TOML (e.g.
  `[mechanical.floor] coding_index = <n>`). Candidates below the floor are excluded, not
  zero-scored. A candidate whose floor axis is missing is excluded — `_MISSING_AXIS_DEFAULT` of 49
  must not satisfy a floor. Floors are generic; only mechanical ships with one.
- **D-12:** Add `schema_version` to `runtimes.json` and `model-catalog.json`. A missing or older
  version counts as stale under `--if-stale`, whatever the TTL says. No manual deletion needed.
  Reversible.

### Claude's Discretion

- The weight values for the new purposes. Start from spec §4: planning = max intelligence and
  agentic, low price weight; general = balanced; execution = coding and agentic with a high price
  weight; mechanical = price-dominant plus the floor.
- The mechanical floor's default value.
- The exact `schema_version` representation.
- The codex parser's shape, dictated by the captured output.
- Whether the claude dated fallback list lives in code or in `references/`.

### Deferred Ideas (OUT OF SCOPE)

- **Pi model enumeration** (`pi --list-models` parser plus fixtures, `pi` in `KNOWN_CLIS`) →
  Phase 22 (pi live validation). Moved from SPEC-02 per D-06.
- **Cursor wrapper resolution** (`cursor-agent` as a shell function; locate the real binary via
  known install paths or an env override) → Phase 21 (cursor live validation).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| SPEC-01 | `detect-current-runtime` identifies pi (`PI_CODING_AGENT`) and codex (`CODEX_THREAD_ID`/`CODEX_VERSION`) in addition to opencode/cursor/claude, with precedence pi > opencode > cursor > codex > claude | Pattern 1 (`_RUNTIME_ENV_SIGNALS` edit shape, verified current code + target tuple), Pitfall 2 (two-signal codex trap), Pitfall 1 (`_VALID_NATIVE_RUNTIME` blast radius on the new `"pi"` label) |
| SPEC-02 | `detect-runtimes` enumerates codex (`codex debug models`) and claude (hardcoded aliases + full ids from the catalog + dated fallback), invoking real binaries; parsers covered by fixtures captured from real CLI output | Pattern 2 (real captured `codex debug models` JSON shape + parser code example; real `claude --help` confirming no list-models command), Validation Architecture Wave 0 gap (inline fixture convention) |
| SPEC-03 | Model catalog entries carry optional `image_input` and populated `reasoning_modes`; cache files without them still load | Pattern 3 (`_FIELD_TYPES` extension, confirms `reasoning_modes` already exists and is validated; `image_input` addition is purely additive so pre-existing caches already load under the existing "missing optional field is never a validation failure" contract) |
| SPEC-04 | Ranker supports purposes `planning`, `general`, `mechanical`, `execution`, `review` via the ranking-weights file; `review`/`execute` keep working as aliases | Pattern 4 (`_is_valid_weights_structure`'s hardcoded purpose tuple, alias-lookup design options, D-11 floor pre-filter design) — also notes `score_candidates`/`load_ranking_weights` are currently dead code in production (test-only callers), lowering this requirement's blast radius |

Note: SPEC-05 (pi enumeration) and SPEC-06 (cursor wrapper) are explicitly out of this phase's
scope per D-06 — mapped to Phase 22 and Phase 21 respectively in REQUIREMENTS.md's traceability
table.
</phase_requirements>

## Summary

This phase edits five existing, already-tested modules in
`skills/ai-kit-spec-review/ai_kit_spec/` (`detection.py`, `model_catalog.py`, `model_sources.py`
already provides what's needed unchanged, `model_ranker.py`, `cache.py`) plus one CLI file
(`cli.py`) and one data file (`references/ranking-weights.toml`). Nothing here is a new
architecture — it is four additive, backward-compatible schema/behavior extensions to code that
already has a `run_fn`/`which_fn`-injection, never-raise, degrade-to-empty-or-default convention
established across the whole package. The plan should follow that convention exactly rather than
introduce a new pattern.

The riskiest part of this phase is not the four D-01..D-12 changes themselves — it is their
**blast radius**. `detect_current_runtime`'s reordering changes what nine existing tests assert
(`tests/test_ai_kit_spec.py:807-843`, `TestDetectCurrentRuntime`), and its output feeds directly
into a **second, independently-defined closed value set** (`_VALID_NATIVE_RUNTIME` — duplicated,
not shared, between `model_catalog.py:39` and `config_io.py:97`) that does **not** currently
contain `"pi"`. Because `detect_current_runtime` can now return `"pi"` under `PI_CODING_AGENT`,
that value would be **rejected** by both schemas' write-time validation the moment `ai-kit-spec-config`'s Step 2.7 runs
under a pi host and tries to persist a native reviewer entry — a real, findable gap the planner
needs to either close (add `"pi"` to both sets) or explicitly descope with a note, not leave
silent. See Pitfall 1 and Open Question 1.

Also load-bearing: `model_ranker.py`'s `score_candidates`/`load_ranking_weights` are currently
**dead code in production** — imported only by `tests/test_ai_kit_spec.py`, never by `cli.py` or
any skill. Phase 16 can therefore freely rename/extend the `"review"`/`"execute"` purpose set
without touching any live call site outside the test file; Phase 17's `catalog_adapter.py`/
`roles.py` will be the *first* real caller. And `ai_kit_spec`'s own quality gates (`pyright`,
`ruff`, `pylint`, `py-compile`, `vulture`) **do not cover this package at all** today — only
`tests/test_ai_kit_spec.py` (under `tests/`, which IS covered) and the single top-level shim
`ai-kit-spec-review.py` are in-gate. `make validate`'s pyright/ruff/vulture legs will not catch a
mistake made inside `ai_kit_spec/*.py`; the tests are the only real gate this phase has. (This
package-wide exclusion is a pre-existing gap tracked for closure at Phase 18's EVAL-06, not
something to fix here — but the planner should know `make validate`'s green light does not mean
what it might look like it means for these specific files.)

**Primary recommendation:** Implement D-01 through D-12 as four independent, additive changes to
the existing modules (never a rewrite), write/extend tests in the existing `tests/test_ai_kit_spec.py`
test classes (`TestDetectCurrentRuntime`, `TestBuildRuntimesSnapshot`, `TestValidateCatalogEntry`,
`TestLoadRankingWeights`/`TestScoreCandidates`, `TestCacheStaleness`) rather than new files, and
resolve the `_VALID_NATIVE_RUNTIME`/pi gap explicitly before calling the phase done.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Host/runtime detection (env-var signal walk) | Library (`ai_kit_spec/detection.py`) | CLI (`cli.py` subcommand) | Pure function over `os.environ`; the CLI subcommand is a thin JSON-printing wrapper, no logic of its own. |
| Model enumeration (codex/claude) | Library (`ai_kit_spec/detection.py`) via subprocess | CLI (`cli.py` `detect-runtimes`) | Same injected-`run_fn` pattern as the existing opencode/cursor-agent parsers; never a new subsystem. |
| Model catalog schema (`image_input`, `reasoning_modes`) | Library (`ai_kit_spec/model_catalog.py`) | Cache/Storage (`cache.py` JSON files) | Schema validation is pure; `cache.py` only reads/writes the JSON the schema governs. |
| Purpose-weighted ranking | Library (`ai_kit_spec/model_ranker.py`) | Data (`references/ranking-weights.toml`) | `score_candidates` is a pure function; the TOML is the tunable data it loads, never hardcoded logic. |
| Cache staleness / schema versioning | Library (`ai_kit_spec/cache.py`) + caller (`cli.py`) | — | `cache_is_stale` is a generic TTL/mtime helper shared with `quota.py` — schema-version awareness belongs in the **caller** (the `detect-runtimes`/`fetch-model-catalog` command bodies in `cli.py`), not inside the shared helper itself (see Pitfall 3). |

## Standard Stack

No new dependencies. This phase is pure Python 3.11+ stdlib (`os`, `re`, `json`, `subprocess`,
`shutil`, `tomllib`), matching the project's existing "runtime stays stdlib-only"
constraint `[VERIFIED: .planning/PROJECT.md:184-186]`: "**Runtime dependency discipline**:
Shipped/runtime code stays stdlib-only (Python 3.11+ where TOML parsing is needed); `uv`/
`textual`-class dependencies stay dev- or wizard-only, per existing project convention." `tomllib`
is confirmed available (`python3 --version` → 3.14.7 on this machine; `import tomllib` succeeds)
`[VERIFIED: python3 -c "import tomllib" exit 0, this session]`.

### Core
No new libraries. All work happens inside the existing `ai_kit_spec` package.

### Package Legitimacy Audit

Not applicable — this phase adds zero new third-party or first-party package dependencies. No
`pip`/`npm install` of any kind occurs in this phase's scope.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess-based model-list parsing that degrades safely | A new subprocess wrapper with its own try/except shape | The existing `detect_opencode_models`/`detect_cursor_agent_models` pattern in `detection.py:74-106` (`run_fn` injection, `timeout=15`, `except (OSError, subprocess.TimeoutExpired): return []`) | Every parser in this file already follows one convention; a new codex/claude parser that deviates (e.g. raises on bad JSON, uses a different timeout) breaks the uniformity the tests and callers rely on. |
| TOML-driven config with safe fallback | A new "read weights, else crash" loader | `model_ranker.py`'s existing `load_ranking_weights`/`_is_valid_weights_structure` pair (`copy.deepcopy(DEFAULT_WEIGHTS)` on any malformed/missing/partial file) | The whole point of `_is_valid_weights_structure` is that a **new, incomplete** purpose section (e.g. `mechanical` added with the wrong axis keys) must fail closed to defaults, not raise deep inside `score_candidates`. Extending the required-purposes set must extend this validator identically, not bypass it. |
| Cache staleness with a version bump | A new sidecar `.version` file or hand-rolled comparison | `cache.py`'s existing `cache_is_stale(path, ttl_seconds)` mtime check, called from the **cli.py command body** with a version-aware wrapper (see D-12 guidance below) | `cli.py`'s `fetch-model-catalog` handler already has a precedent for exactly this shape of problem: it uses a **separate sidecar file** (`args.catalog_path + ".fetch-meta.json"`) to track "was a real fetch attempted" independently of the main file's own mtime (`cli.py:775-785`, comment: "Freshness for THIS purpose... is tracked via a dedicated sidecar file instead"). `schema_version` staleness should read the *content* of the cache file itself (a `schema_version` key inside the JSON), not add a third sidecar. |

**Key insight:** every extension point this phase touches already has a designed extension seam
(a type table, a required-keys set, a validator function, a fixed env-signal tuple) — the work is
almost entirely "add an entry to an existing table and extend its validator," never "invent a new
mechanism." Where the plan proposes a new mechanism, that is a signal to re-check whether an
existing seam was missed.

## Architecture Patterns

### System Architecture Diagram

```
                     env vars (CLAUDECODE, OPENCODE, CURSOR_AGENT,
                     CODEX_THREAD_ID/CODEX_VERSION, PI_CODING_AGENT)
                                    │
                                    ▼
                    detection.py: detect_current_runtime()
                    walks _RUNTIME_ENV_SIGNALS in fixed order
                    (D-01: pi > opencode > cursor > codex > claude)
                                    │
                                    ▼
              cli.py: detect-current-runtime  →  {"native_runtime": "<label>"}
                                    │
                          ┌─────────┴──────────┐
                          ▼                     ▼
          ai-kit-spec-config SKILL.md    Phase 17 host.py (future)
          Step 2.7 (writes review-spec.toml   (future consumer)
          native [[reviewers]] entry,
          validated by config_io.py's
          _VALID_NATIVE_RUNTIME)

  ────────────────────────────────────────────────────────────────

  which_fn (shutil.which)          run_fn (subprocess.run)
        │                                │
        ▼                                ▼
  detect_installed_clis()  ──►  build_runtimes_snapshot()
  (KNOWN_CLIS: claude,             │  for each installed CLI:
   codex, opencode, grok,          │   opencode/cursor-agent → existing parsers
   cursor-agent)                   │   codex (NEW, D-05)     → codex debug models
                                    │   claude (NEW, D-04)    → hardcoded + catalog
                                    ▼
                     cli.py: detect-runtimes [--save|--if-stale]
                                    │
                                    ▼
                     runtimes.json cache (RUNTIMES_TTL_SECONDS,
                     + schema_version, D-12)
                                    │
                                    ▼
          cli.py: fetch-model-catalog --runtimes-json ... --catalog-path ...
                     (matches against models.dev / Artificial Analysis,
                      NEW: extracts image_input from modalities.input /
                      opencode --verbose, D-09)
                                    │
                                    ▼
              model-catalog.json cache (CATALOG_TTL_SECONDS,
              + schema_version, D-12; validated by
              model_catalog.validate_catalog_entry,
              _FIELD_TYPES + image_input, D-09)
                                    │
                                    ▼
     model_ranker.py: score_candidates(entries, purpose, weights)
     purpose ∈ {planning, general, mechanical, execution, review}
     (D-10; review/execute kept as aliases) + optional per-purpose
     floor exclusion (D-11, mechanical only)
                                    │
                                    ▼
              (Phase 17: catalog_adapter.py / roles.py — first
               real production caller of score_candidates)
```

### Recommended Project Structure

No new files/directories. All edits land in the existing flat package:
```
skills/ai-kit-spec-review/
├── ai_kit_spec/
│   ├── detection.py          # D-01, D-02, D-03, D-04, D-05, D-07 (detection + enumeration)
│   ├── model_catalog.py      # D-08, D-09 (schema: reasoning_modes reuse, image_input)
│   ├── model_sources.py      # unchanged — fetch_models_dev already exposes modalities.input
│   ├── model_ranker.py       # D-10, D-11 (purposes, aliases, floor)
│   ├── cache.py              # unchanged function signature; D-12 handled by caller (cli.py)
│   └── cli.py                # wires --if-stale schema_version checks (D-12) into
│                              #   detect-runtimes / fetch-model-catalog command bodies
├── references/
│   └── ranking-weights.toml  # D-10, D-11 (new purpose sections + [mechanical.floor])
└── (tests live in ../../tests/test_ai_kit_spec.py, not colocated)
```

### Pattern 1: Env-signal precedence tuple (D-01, D-02, D-03)

**What:** `_RUNTIME_ENV_SIGNALS` in `detection.py:27-32` is a fixed tuple of `(label, env_var)`
pairs, walked in order by `detect_current_runtime`; the first truthy `env.get(var)` wins.

**When to use:** Any time host precedence needs to change or grow. This is a data-only edit — no
logic in `detect_current_runtime` itself needs to change, only the tuple's contents and order.

**Example (current code, to be edited):**
```python
# Source: skills/ai-kit-spec-review/ai_kit_spec/detection.py:27-32 [VERIFIED: read this session]
_RUNTIME_ENV_SIGNALS = (
    ("claude", "CLAUDECODE"),
    ("opencode", "OPENCODE"),
    ("cursor", "CURSOR_AGENT"),
    ("codex", "CODEX_VERSION"),
)
```
Per D-01 (as amended by Phase 20 D-02) and D-02/D-03, the target shape is:
```python
_RUNTIME_ENV_SIGNALS = (
    ("pi", "PI_CODING_AGENT"),
    ("opencode", "OPENCODE"),
    ("cursor", "CURSOR_AGENT"),
    ("codex", "CODEX_THREAD_ID"),
    ("codex", "CODEX_VERSION"),
    ("claude", "CLAUDECODE"),
)
```
Note codex needs **two** tuple entries (or a per-signal OR check) since D-02 says the codex
signal is "**either** `CODEX_THREAD_ID` or `CODEX_VERSION`" — the current loop structure
(`for label, var in _RUNTIME_ENV_SIGNALS: if env.get(var): return label`) naturally supports two
entries with the same label without any control-flow change, preserving the existing "walk in
order, return first hit" contract. `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/detection.py:67-71]`
```python
for label, var in _RUNTIME_ENV_SIGNALS:
    if env.get(var):
        return label
return "unknown"
```

The docstring's per-signal verification labels (lines 53-65) must be updated for the new order
and to record pi/codex's status per D-02/D-03: pi is "source-inspected, not live-verified" (per
D-03, confirmed via the installed `@earendil-works/pi-coding-agent` package's `dist/config.js`);
codex's `CODEX_THREAD_ID` is "observed in real codex session shell snapshots under
`~/.codex/sessions` (20 occurrences)" per D-02/the discussion log's evidence
(`.planning/phases/16-ai-kit-spec-extensions/16-DISCUSSION-LOG.md:25-27`) `[CITED: this phase's own discussion log]`; `CODEX_VERSION` stays
labeled "source-inspected-only" (unchanged from the existing docstring, `detection.py:63-65`).

### Pattern 2: Injected-subprocess model parser (D-05)

**What:** Every existing multi-provider model parser (`detect_opencode_models`,
`detect_cursor_agent_models`) takes the resolved binary path plus an injected `run_fn`, calls it
with a bounded `timeout=15`, catches `(OSError, subprocess.TimeoutExpired)`, and returns `[]` on
any failure — never raises, never blocks on a hang.

**When to use:** The new `detect_codex_models(binary, run_fn=subprocess.run)` function (D-05)
must follow this exact shape.

**Real captured shape of `codex debug models`** (captured live this session, `codex-cli 0.147.0`
resolved via `~/.volta/bin/codex` — a real volta shim, not a shell alias/function
`[VERIFIED: command -v codex, this session]`):
```json
{"models":[
  {"slug":"gpt-reserve","display_name":"GPT-Reserve","default_reasoning_level":"medium",
   "supported_reasoning_levels":[{"effort":"low",...},{"effort":"medium",...},
   {"effort":"high",...},{"effort":"xhigh",...},{"effort":"max",...}],
   "visibility":"hide","priority":3, "...": "..."},
  {"slug":"gpt-5.6-sol","display_name":"GPT-5.6-Sol","default_reasoning_level":"low",
   "supported_reasoning_levels":[... "low","medium","high","xhigh","max","ultra" ...],
   "visibility":"list","priority":4},
  {"slug":"gpt-5.6-terra","display_name":"GPT-5.6-Terra","default_reasoning_level":"medium",
   "supported_reasoning_levels":[... "low","medium","high","xhigh","max","ultra" ...],
   "visibility":"list","priority":7},
  {"slug":"gpt-5.6-luna","display_name":"GPT-5.6-Luna","default_reasoning_level":"medium",
   "supported_reasoning_levels":[... "low","medium","high","xhigh","max" ...],
   "visibility":"list","priority":8},
  {"slug":"gpt-5.5","display_name":"GPT-5.5","default_reasoning_level":"medium",
   "supported_reasoning_levels":[... "low","medium","high","xhigh" ...],
   "visibility":"list","priority":12},
  {"slug":"codex-auto-review","display_name":"Codex Auto Review","default_reasoning_level":"medium",
   "supported_reasoning_levels":[... "low","medium","high","xhigh","max" ...],
   "visibility":"hide","priority":43}
]}
```
`[VERIFIED: real `codex debug models` invocation, this session, `codex-cli 0.147.0`]`. Full raw
capture is 259KB (each model carries a very large `model_messages.instructions_template` string —
the parser must NOT try to keep that field). Top-level shape is a single object with one `models`
key — no other top-level keys observed.

**Parser guidance:** filter to `visibility == "list"` — the two `"hide"` entries
(`gpt-reserve`, `codex-auto-review`) read as internal/reserved slugs, not user-selectable models,
and excluding them matches the design spec's own named examples (`gpt-5.6-terra`, `gpt-5.6-luna`,
`gpt-5.6-sol` — `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:132`). Extract
`slug` (the model id), and consider surfacing `supported_reasoning_levels[].effort` as the source
for this model's `reasoning_modes` list (D-08 — see Pattern 3) since it is present per-model in
this exact response, a stronger source than a hardcoded guess. Like every other parser in this
file, a JSON-decode failure or unexpected shape must degrade to `[]`, never raise.

**`claude --help` confirms no list-models command** (real binary at
`/home/bazzite/.local/share/claude/versions/2.1.281`, invoked directly — not through the user's
`alias claude='claude --dangerously-skip-permissions'` `[VERIFIED: type claude / ls -la ~/.local/bin/claude, this session]`):
```
--model <model>    Model for the current session. Provide an alias for the latest model
                   (e.g. 'fable', 'opus', or 'sonnet') or a model's full name
                   (e.g. 'claude-fable-5').
```
`[VERIFIED: real `claude --help` output, this session]` — confirms D-04's premise exactly: `--model`
takes only an alias or a full model name, no separate enumeration subcommand exists. (`--help`'s
own example list only shows `fable`/`opus`/`sonnet`; `haiku` is not shown in this exact help
string but is the fourth alias per this project's own established precedent — `skills/ai-kit-spec-config/SKILL.md:245`
already documents "the four `Agent`-tool aliases (`sonnet`/`opus`/`haiku`/`fable`)"
`[CITED: skills/ai-kit-spec-config/SKILL.md:245]`.)

### Pattern 3: Catalog field addition (D-08, D-09)

**What:** `model_catalog.py`'s `_FIELD_TYPES` dict (line 18-32) is the single place every optional
catalog field is declared for type-checking; `validate_catalog_entry` iterates it generically.
`reasoning_modes: list` is **already present** at line 22 — `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:22]`:
`"tool_calling": bool, "native": bool, "reasoning_modes": list, "fast_mode": bool,` — and already
has list-of-strings validation at lines 111-113: `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:111-113]`:
```python
if "reasoning_modes" in entry and isinstance(entry["reasoning_modes"], list) and \
        not all(isinstance(m, str) for m in entry["reasoning_modes"]):
    return f"{model_id}: 'reasoning_modes' must be a list of strings"
```
So D-08 requires **zero schema code changes** — only (a) an erratum note in the design spec (§2,
§3.1 say `reasoning_levels`, which does not exist in code) and (b) wiring a real writer, since
"nothing writes it yet" per CONTEXT.md D-08. The `codex debug models` capture above
(`supported_reasoning_levels[].effort`) is a plausible source for codex entries' `reasoning_modes`.

`image_input: bool` (D-09) is genuinely new — add it to `_FIELD_TYPES` following the exact
pattern of the adjacent `bool`-typed fields (`batch_mode`, `is_router`, `structured_output`,
`tool_calling`, `native`, `fast_mode`):
```python
_FIELD_TYPES = {
    ...
    "tool_calling": bool, "native": bool, "reasoning_modes": list, "fast_mode": bool,
    "image_input": bool,  # NEW — optional, absent means unknown (never written as False)
    ...
}
```
Because it is added to `_FIELD_TYPES` (not `_MANDATORY_CATALOG_FIELDS`), the existing
"a missing optional field is never a validation failure" contract
(`validate_catalog_entry`'s own docstring, `model_catalog.py:54-60`) already makes "cache files
written before this change still load without error" (SPEC-03) true with no further code change —
this is a pure additive schema change on a codebase that already type-checks unrecognized-vs-recognized
optional fields correctly.

**Source #1 — models.dev `modalities.input`**, confirmed live this session against the real,
current `https://models.dev/api.json` payload (fetched with the same `User-Agent` the code
already uses, `model_sources.py:20`):
```
claude-sonnet-4-6  | modalities: {'input': ['text', 'image', 'pdf'], 'output': ['text']}
claude-opus-5-5    | modalities: {'input': ['text', 'image', 'pdf'], 'output': ['text']}
```
`[VERIFIED: live fetch of https://models.dev/api.json, this session — 15 anthropic models present,
all with 'image' in modalities.input]`. This confirms the field path `modalities.input` (a list)
and that `"image" in modalities["input"]` is the correct test per D-09 point 1.

**Source #2 — `opencode models --verbose`**, confirmed live this session (`opencode` resolved at
`/home/bazzite/.opencode/bin/opencode`, a real binary on PATH). Output shape is repeated
`<providerID>/<id>\n<JSON object>\n` blocks; the JSON object's `capabilities.input.image` boolean
is the field D-09 point 2 names:
```json
{
  "id": "my-coding", "providerID": "router-env", "name": "my-coding (combo)",
  "capabilities": {"input": {"text": true, "image": false, ...}, ...}
}
```
`[VERIFIED: real `opencode models --verbose` invocation, this session — 110 lines, providers
observed: openai, opencode, router-env, xai; a `router-env/my-coding` entry with
`capabilities.input.image: false` confirmed present]`. This matches D-09's exact scenario (a
`router-env/*` id with no models.dev match).

### Pattern 4: Ranker purpose extension (D-10, D-11)

**What:** `model_ranker.py`'s `DEFAULT_WEIGHTS` dict and `references/ranking-weights.toml` are
required to mirror each other exactly (the module docstring/comment at `model_ranker.py:16-24`
says so explicitly: "Mirrors ranking-weights.toml exactly"). `_is_valid_weights_structure` (lines
42-61) hardcodes the two required purposes as a **literal tuple** `("review", "execute")` at line
51 — `[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:51]`:
`for purpose in ("review", "execute"):`. This is the one spot that must become data-driven (a
module-level `_REQUIRED_PURPOSES` set/tuple, or similar) rather than hardcoded, per D-10's "must
validate every purpose it knows... A weights file that only has the old two purposes must still
load."

**D-10 alias requirement, concretely:** `score_candidates(entries, purpose, weights)` does
`axis_weights = weights[purpose]` (line 118) — a bare dict lookup. To make `"execute"` an alias
for `"execution"` (and `"review"` stay as-is, since it is already both the old AND new name),
either (a) normalize the incoming `purpose` string to its canonical form before the lookup (e.g.
a small `_PURPOSE_ALIASES = {"execute": "execution"}` dict consulted first), or (b) have
`load_ranking_weights`/the TOML populate BOTH `weights["execute"]` and `weights["execution"]` as
the same dict. Option (a) is more consistent with this module's existing "aliases are a lookup
concern, not a data-duplication concern" style (see `canonical_key` in `model_catalog.py` for the
same philosophy applied to a different problem) — recommend (a), but this is Claude's Discretion
territory the plan should still decide explicitly.

**D-11 floor requirement:** the mechanical purpose's `[mechanical.floor]` table
(e.g. `coding_index = <n>`) is a NEW top-level concept — nothing in `score_candidates` currently
excludes a candidate; the existing function only ever ranks/scores, never drops. This needs new
logic (not just a data table), most naturally as a pre-filter step in `score_candidates` (or a
new wrapping function) that runs BEFORE scoring: for each candidate, if the purpose has a floor
table, check each floored axis's **raw, un-normalized** value (`entry.get("scores", {}).get(axis)`
for a `scores.*` axis) against the floor; a **missing** axis fails the floor (per D-11: "A
candidate whose floor axis is missing is excluded... `_MISSING_AXIS_DEFAULT` of 49 must not
satisfy a floor"). This must run on the raw axis value, not the normalized 0-100 scaled value
`_normalize_minmax` produces, since normalization is relative to the current candidate set and a
floor is meant to be an absolute, cross-run-stable cutoff.

### Anti-Patterns to Avoid

- **Reordering `_RUNTIME_ENV_SIGNALS` without touching `KNOWN_CLIS`:** `KNOWN_CLIS`
  (`detection.py:13`, `= ("claude", "codex", "opencode", "grok", "cursor-agent")`) is a
  **separate** tuple governing `detect_installed_clis`/`build_runtimes_snapshot` (binary-on-PATH
  enumeration), not `detect_current_runtime` (which-CLI-hosts-this-process). Per CONTEXT.md's own
  code_context section, adding `"pi"` to `KNOWN_CLIS` is explicitly Phase 22's concern — do NOT
  add it here even though `_RUNTIME_ENV_SIGNALS` gains a `pi` entry in this phase. These are
  deliberately different questions (AGENTS.md says so explicitly: "`detect_installed_clis()`...
  and `detect_current_runtime()`... are deliberately different questions — never conflate them"
  `[VERIFIED: AGENTS.md:66-69]`).
- **Adding a `--force` flag for D-12's cache refresh:** `cli.py`'s `fetch-model-catalog` command
  already has an explicit comment rejecting this pattern (`cli.py:534-540`): running WITHOUT
  `--if-stale` already re-fetches unconditionally, so a dedicated `--force` flag would be a
  same-effect alias. Follow the same reasoning for `detect-runtimes`'s `--if-stale`: `schema_version`
  staleness should make the EXISTING `--if-stale` flag return "stale" (forcing a normal refresh),
  never introduce a parallel force-refresh mechanism.
- **Putting `schema_version` awareness inside `cache_is_stale` itself:** `cache_is_stale` is
  shared with `quota.py` (`[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/cache.py:32-36]`,
  confirmed via grep — `quota.py` is the only other consumer of this exact function) and is a
  pure mtime/TTL check with no knowledge of the JSON payload's shape. Making it schema-aware
  would couple a generic helper to one specific caller's data format. D-12's check belongs in
  `cli.py`'s `detect-runtimes`/`fetch-model-catalog` command bodies, reading the cached file's
  own `schema_version` key and OR-ing that check with the existing `cache_is_stale` TTL check.

## Common Pitfalls

### Pitfall 1: `_VALID_NATIVE_RUNTIME` does not include `"pi"` in either of its two locations

**What goes wrong:** `detect_current_runtime` can now return `"pi"` (D-01/D-03). If a pi-hosted
session runs `ai-kit-spec-config`'s Step 2.7 native-entry flow, it calls `detect-current-runtime`,
gets `{"native_runtime": "pi"}`, and tries to write that value onto a `[[reviewers]]` entry.
`config_io.py`'s `validate_reviewer_fields` rejects it:
`[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/config_io.py:97, 126-129]` — the literal set is
`_VALID_NATIVE_RUNTIME = {"claude", "opencode", "codex", "cursor", "unknown"}` and the rejection
path reads `if "native_runtime" in entry and (not isinstance(...) or entry["native_runtime"] not
in _VALID_NATIVE_RUNTIME): return f"{key}: 'native_runtime' must be one of {sorted(_VALID_NATIVE_RUNTIME)}"`.
`model_catalog.py:39` independently duplicates the identical literal set (also missing `"pi"`),
`[VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:39]`. This is not
`cache_write_json` corruption — the existing "reject and report" contract already makes this a
visible `WARNING:`-level failure (per `01.2-04-PLAN.md`'s own security-review note,
`T-01.2-06`: "The printed value is validated... before... ever writes it — an unexpected value
would be rejected-and-reported... never silently written") — but it is still a functional gap:
the label becomes unusable the moment it is produced.
**Why it happens:** `_VALID_NATIVE_RUNTIME` was defined in two independent files during Phase
01.2 and neither is the "owner" the other defers to; nothing keeps them in sync automatically.
**How to avoid:** The plan must explicitly decide whether to add `"pi"` to both
`_VALID_NATIVE_RUNTIME` sets as part of this phase (cheap, 2-line change, matches the "additive
schema" pattern this whole phase already follows) or to document this as a deliberate,
temporarily-accepted gap (since pi enumeration itself is deferred to Phase 22 — CONTEXT.md D-06).
Silently doing neither is the failure mode to avoid.
**Warning signs:** A test asserting `detect_current_runtime` returns `"pi"` under
`PI_CODING_AGENT=1` passes, but no corresponding `TestValidateCatalogEntry`/`config_io`-equivalent
test exercises `native_runtime="pi"` — that asymmetry is the tell.

### Pitfall 2: Codex has TWO signals now, and the loop's "walk-in-order" contract requires two tuple rows

**What goes wrong:** A tempting shortcut is `("codex", "CODEX_THREAD_ID" or "CODEX_VERSION")` —
this is a Python syntax trap (`or` between two string literals evaluates once, at tuple-definition
time, to the first truthy literal — i.e. always `"CODEX_THREAD_ID"`, silently ignoring
`CODEX_VERSION` forever). The existing loop only ever checks one `env_var` name per tuple entry.
**Why it happens:** The natural English phrasing of D-02 ("either X or Y") maps incorrectly onto
a single-var-per-entry tuple structure without a moment's pause.
**How to avoid:** Add two separate `("codex", "CODEX_THREAD_ID")` / `("codex", "CODEX_VERSION")`
rows to `_RUNTIME_ENV_SIGNALS`, adjacent to each other, both after cursor and before claude in the
new order. The existing loop handles two same-label rows with zero code changes.
**Warning signs:** A test with `env={"CODEX_VERSION": "0.153.4"}` (no `CODEX_THREAD_ID`) failing
to return `"codex"`.

### Pitfall 3: `cache_is_stale`'s TTL check and `schema_version`'s staleness check are ORed, not chained

**What goes wrong:** D-12 says "a missing or older version counts as stale **whatever the TTL
says**." If implemented as `if cache_is_stale(path, ttl) and schema_version_is_old(path): refresh`
(AND instead of OR), a cache with a fresh mtime but an old `schema_version` would never refresh —
exactly the "one automatic refresh" scenario D-12 exists to force ("existing 30-day caches...
are not trusted").
**Why it happens:** Staleness checks read naturally as conjunctive ("stale AND wrong version")
when the actual requirement is disjunctive ("stale OR wrong version").
**How to avoid:** `should_refresh = cache_is_stale(path, ttl) or schema_version < CURRENT_SCHEMA_VERSION`
(reading `schema_version` from the cached JSON's own top-level key, defaulting to e.g. `0` or
absent-means-old when the key doesn't exist at all — since "a missing... version counts as
stale").
**Warning signs:** A cache file written moments ago (fresh mtime) but with no `schema_version`
key at all is treated as fresh by `--if-stale`.

## Runtime State Inventory

**Not a rename/refactor/migration phase** — this phase adds fields and reorders a check sequence;
it does not rename any identifier that has runtime-persisted state under its old name. The
Runtime State Inventory protocol is not triggered.

However, one adjacent fact is worth recording since it touches "what does existing state look
like right now": the live cache directory on this machine
(`~/.cache/ai-kit/spec/`) currently contains only `runtimes.json` and `quota.json` —
`model-catalog.json` **does not exist yet** on this machine
`[CITED: 16-CONTEXT.md Specifics — "Current machine state"]`. This means SPEC-03's "cache files
written before this change still load without error" claim needs a **synthetic** pre-change
fixture (a hand-written `model-catalog.json` without `image_input`/`schema_version`) for its test,
since there is no real pre-existing file on disk to load against. The live verification this
phase's plan should include is a real `detect-runtimes` + `fetch-model-catalog` run (the latter
needs `ARTIFICIAL_ANALYSIS_API_KEY` for the AA source; models.dev needs no key, confirmed —
`model_sources.py:30-38`, `fetch_models_dev` takes no API key parameter) to produce the FIRST real
`model-catalog.json` on this machine and confirm the new fields land in it.

## Code Examples

### Codex debug models — real, filtered

```python
# Source: real `codex debug models` capture, this session, codex-cli 0.147.0.
# Full raw output is 259KB per invocation (each model carries a large
# model_messages.instructions_template string) — do not retain that field.
import json
import subprocess


def detect_codex_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> debug models`; returns the `slug` of every model whose
    `visibility` is "list" (excludes internal/reserved "hide" entries like
    gpt-reserve/codex-auto-review). Degrades to [] on any failure, same
    convention as detect_opencode_models/detect_cursor_agent_models."""
    try:
        result = run_fn([binary, "debug", "models"], capture_output=True,
                         text=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [m["slug"] for m in data.get("models", [])
            if isinstance(m, dict) and m.get("visibility") == "list" and "slug" in m]
```

### models.dev image_input extraction (existing `fetch_models_dev` + new match logic)

```python
# Source: model_sources.py's existing fetch_models_dev (unchanged) + live-confirmed
# modalities shape from https://models.dev/api.json, anthropic provider, this session.
def _image_input_from_models_dev_match(md_match: dict | None) -> bool | None:
    """None (absent/unknown) when there is no match at all — per D-09, never write False
    just because there was no signal."""
    if md_match is None:
        return None
    modalities = md_match.get("modalities") or {}
    input_list = modalities.get("input")
    if input_list is None:
        return None
    return "image" in input_list
```

### opencode --verbose image capability (real captured shape)

```python
# Source: real `opencode models --verbose` invocation, this session.
# Output is repeated "<providerID>/<id>\n<json object>\n" blocks.
def _image_input_from_opencode_verbose(entry: dict) -> bool | None:
    capabilities = entry.get("capabilities") or {}
    input_caps = capabilities.get("input")
    if input_caps is None or "image" not in input_caps:
        return None
    return bool(input_caps["image"])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `_RUNTIME_ENV_SIGNALS` fixed order: claude > opencode > cursor > codex | pi > opencode > cursor > codex > claude | This phase (D-01, amended by Phase 20 D-02) | Claude moves from first to last; a claude-hosted `opencode run` subprocess now correctly reads as opencode instead of claude. |
| `reasoning_levels` (design-spec-only, never implemented) | Reuse existing `reasoning_modes: list[str]` field | This phase (D-08) | The design spec (§2, §3.1) needs an erratum note; no schema code change required, only a writer. |
| `score_candidates` purposes: `"review"`/`"execute"` only | `planning`, `general`, `mechanical`, `execution`, `review` (old names kept as aliases) | This phase (D-10) | `_is_valid_weights_structure`'s hardcoded `("review", "execute")` tuple must become data-driven. |
| Catalog cache freshness: TTL/mtime only | TTL/mtime OR `schema_version` mismatch | This phase (D-12) | Forces one automatic refresh of every existing cache once shipped, since none currently carry `schema_version` at all. |

**Deprecated/outdated:** None — every change in this phase is additive; no prior API is removed
or renamed. `CODEX_SANDBOX` is dropped from the spec's proposed codex signal set (never
implemented, never observed — D-02) but was never actually in the current code's
`_RUNTIME_ENV_SIGNALS` to begin with (`detection.py:27-32` only has `CODEX_VERSION` today), so
there is nothing to remove from the codebase itself, only from the design-spec prose.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `codex debug models`'s `visibility: "hide"` entries (`gpt-reserve`, `codex-auto-review`) should be excluded from the enumerated list | Pattern 2 | If wrong, the parser under-enumerates a model the user actually wants selectable, or over-enumerates two internal/reserved slugs into a user-facing catalog. Low blast radius — the existing "degrade to partial list, never crash" contract means this is a quality tweak, not a correctness bug; easy to revisit once a human confirms what "hide" actually means operationally. |
| A2 | `supported_reasoning_levels[].effort` from the codex capture is an appropriate source for that model's `reasoning_modes` catalog field (D-08) | Pattern 2, Pattern 3 | If the design intends `reasoning_modes` to describe something else (e.g. a curated subset, not every CLI-exposed effort level), this over-populates the field. Low risk — field is optional and type-checked, not load-bearing for any current consumer (ranker's `score_candidates` doesn't read `reasoning_modes` at all today). |
| A3 | The `_VALID_NATIVE_RUNTIME` gap (Pitfall 1) should be closed in THIS phase rather than deferred | Summary, Pitfall 1 | If the planner defers it (reasonable, since pi enumeration itself is Phase 22's scope), a pi-hosted `ai-kit-spec-config` run will get a rejected-and-reported write until whichever phase closes it — annoying but non-corrupting (existing reject-and-report contract holds), and explicitly flagged here rather than silently discovered later either way. |
| A4 | `_PURPOSE_ALIASES`-style lookup normalization (rather than dual-writing both keys into the weights dict) is the right implementation shape for D-10's `execute`→`execution` alias | Pattern 4 | Purely an implementation-style choice with no external-behavior difference if done correctly either way; flagged as Claude's Discretion in CONTEXT.md, so this is informational, not blocking. |

## Open Questions

1. **Does this phase close the `_VALID_NATIVE_RUNTIME`/`"pi"` gap, or explicitly defer it?**
   - What we know: `detect_current_runtime` can return `"pi"` starting this phase; neither
     `model_catalog.py`'s nor `config_io.py`'s `_VALID_NATIVE_RUNTIME` set currently accepts it;
     the existing reject-and-report contract prevents silent corruption either way.
   - What's unclear: whether the user considers this in-scope for Phase 16 (a 2-line, low-risk
     addition to two files already touched by D-08/D-09-adjacent work) or explicitly out-of-scope
     until Phase 22 (which owns the rest of pi's enumeration).
   - Recommendation: the plan should make an explicit task-level decision here rather than let it
     fall through the cracks; given the fix is cheap and the alternative is a confirmed
     functional gap, closing it in this phase is the lower-risk default absent a stated reason not
     to.

2. **Where does the claude dated fallback list live — code or `references/`?**
   - What we know: CONTEXT.md leaves this as Claude's Discretion; `references/` already holds
     `ranking-weights.toml` as a precedent for "tunable data lives outside the .py files."
   - What's unclear: whether a small, rarely-changing list of 4 model ids justifies a new data
     file versus a simple in-module constant (like `_MODEL_TIER_SUFFIXES` in `vendor.py`, which
     the existing `group_models_by_family` imports as a plain Python tuple).
   - Recommendation: given it is small (4 ids), dated, and tightly coupled to the hardcoded alias
     list it's a fallback FOR, an in-module constant (mirroring the `vendor.py` precedent) is
     simpler than introducing a new `references/*.json` file for four strings — but this is
     explicitly left to the plan/Claude's Discretion per CONTEXT.md.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `codex` binary (real, on PATH via `~/.volta/bin/codex`) | D-05 codex enumeration, live fixture capture | Yes | codex-cli 0.147.0 | — |
| `claude` binary (real, at `~/.local/share/claude/versions/2.1.281`, NOT the user's alias) | D-04/D-07 confirming no list-models command | Yes | 2.1.281 | — |
| `opencode` binary (real, on PATH at `~/.opencode/bin/opencode`) | D-09 source #2 (`opencode models --verbose`) | Yes | (not separately queried; models list returned live) | — |
| `models.dev` API (`https://models.dev/api.json`, no auth) | D-04 full ids, D-09 source #1 | Yes | live-fetched this session, 15 anthropic models present | — |
| `ARTIFICIAL_ANALYSIS_API_KEY` | `fetch-model-catalog`'s AA source (only needed for a live end-to-end catalog-build smoke test, not for the schema/parser work itself) | Not probed this session | — | `fetch_artificial_analysis` already returns `([], True)` immediately when the key is absent (`model_sources.py:41-49`) — this is a designed no-op path, not a missing-dependency failure. |
| `python3` / `tomllib` (3.11+) | `model_ranker.py`'s TOML loading | Yes | 3.14.7 on this machine; repo's dev pin is `>=3.12,<3.13` (`pyproject.toml:9`, dev-env only — runtime stays stdlib 3.11+) | — |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** `ARTIFICIAL_ANALYSIS_API_KEY` — already has a designed
no-op fallback in existing code; only affects the depth of a full live-catalog smoke test, not
correctness of this phase's schema/parser changes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` (stdlib), no pytest in this repo |
| Config file | none — invoked directly via `python3 -m unittest` (core suite) or `uv run python -m unittest` (textual/PTY suites, not relevant to this phase) |
| Quick run command | `python3 -m unittest tests.test_ai_kit_spec.TestDetectCurrentRuntime tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestValidateCatalogEntry tests.test_ai_kit_spec.TestLoadRankingWeights tests.test_ai_kit_spec.TestScoreCandidates tests.test_ai_kit_spec.TestCacheStaleness -v` |
| Full suite command | `python3 -m unittest tests.test_ai_kit_spec -v` (whole file, ~150 test classes) or `make test-unit` (runs this plus every other unit-test module) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPEC-01 | `detect_current_runtime` honors new pi>opencode>cursor>codex>claude order, both codex signals, pi signal | unit | `python3 -m unittest tests.test_ai_kit_spec.TestDetectCurrentRuntime -v` | ✅ exists, 9 tests to update/extend (`tests/test_ai_kit_spec.py:807-843`) |
| SPEC-02 | codex/claude enumeration via real binaries, fixture-validated parsers | unit | New test methods in `TestBuildRuntimesSnapshot` (`tests/test_ai_kit_spec.py:1112-1145`) using a fixture-shaped fake `run_fn`, mirroring the existing `test_lists_opencode_models_when_installed` pattern | ❌ Wave 0 — new test methods + a `tests/fixtures/codex_debug_models.json` (or inline fixture) needed |
| SPEC-03 | `image_input`/`reasoning_modes` optional, pre-existing cache files still load | unit | Extend `TestValidateCatalogEntry` (`tests/test_ai_kit_spec.py:426-593`) with `image_input` type-check tests + an "entry missing image_input loads fine" regression test | ❌ Wave 0 — new test methods |
| SPEC-04 | Ranker accepts 5 purposes, `review`/`execute` remain working aliases | unit | Extend `TestLoadRankingWeights`/`TestScoreCandidates` (`tests/test_ai_kit_spec.py:3396-3599`) with new-purpose and alias-equivalence tests | ❌ Wave 0 — new test methods |
| (D-12, cache) | `schema_version` forces refresh regardless of TTL | unit | New test methods in `TestCacheStaleness` (`tests/test_ai_kit_spec.py:774-792`) or a new `TestMainCli` case for the `detect-runtimes --if-stale` command body, since the schema_version check lives in `cli.py`, not `cache.py` per Pitfall 3 | ❌ Wave 0 — new test methods |

### Sampling Rate
- **Per task commit:** the quick run command above (targeted test classes for the module just
  touched).
- **Per wave merge:** `python3 -m unittest tests.test_ai_kit_spec -v` (whole file — this repo's
  own `unittest` pre-commit hook runs this module by name already, so this mirrors the real gate).
- **Phase gate:** `make test-unit` green before `/gsd-verify-work` (this is the target the
  `unittest` pre-commit hook and `make validate` both already include `tests.test_ai_kit_spec`
  in — no new wiring needed since the test file itself is already registered everywhere).

### Wave 0 Gaps
- [ ] New test methods across `TestDetectCurrentRuntime`, `TestBuildRuntimesSnapshot`,
      `TestValidateCatalogEntry`, `TestLoadRankingWeights`/`TestScoreCandidates`,
      `TestCacheStaleness` — no new test FILES needed, the existing `tests/test_ai_kit_spec.py`
      already covers every module this phase touches.
- [ ] A codex `debug models` fixture (JSON, real captured shape documented in Code Examples
      above) for the new `detect_codex_models` parser test — can be inlined as a Python dict
      literal in the test (matching this file's existing convention, e.g.
      `test_lists_cursor_agent_models_when_installed`'s inline `FakeResult.stdout` string) rather
      than a separate `tests/fixtures/*.json` file, since no `tests/fixtures/` directory currently
      exists for this test file `[VERIFIED: grep for tests/fixtures found no matches under this repo's tests/ dir this session]`.
- [ ] Framework install: none — `unittest` is stdlib, already wired into every gate.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | This phase touches no auth flow. |
| V3 Session Management | No | Not applicable. |
| V4 Access Control | No | `native_runtime`/host detection is explicitly informational-only, matching the existing precedent (`AGENTS.md`/01.2-RESEARCH.md's own V4 finding: "No access-control decision is ever gated on this value" `[CITED: .planning/milestones/v1.0-phases/01.2-multi-cli-runtime-foundation/01.2-RESEARCH.md:418]`) — unchanged by this phase's reordering/new signals. |
| V5 Input Validation | Yes | Env-var values are read as opaque presence/absence booleans only (`env.get(var)` truthiness, never parsed/shelled/path-constructed) — same existing pattern, extended to two new signals. `image_input`/new ranker purposes are validated against `_FIELD_TYPES`/`_is_valid_weights_structure` before ever being trusted, exactly like every existing optional field. |
| V6 Cryptography | No | Not applicable — no crypto in this phase. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| A malicious/misconfigured environment spoofs `PI_CODING_AGENT`/`CODEX_THREAD_ID` to fake a host identity | Spoofing | Same low-severity, accepted-risk posture as the existing four signals (`detect_current_runtime` is informational-only per the existing D-05 precedent from 01.2) — no new control needed; do not let this phase's new signals be treated with a different trust level than the existing ones. |
| A malformed `codex debug models` response (future codex version changes the JSON shape) crashes the parser | Denial of Service (local) | Follow the existing degrade-to-`[]`-never-raise convention (`try/except (OSError, subprocess.TimeoutExpired)` + a `json.JSONDecodeError` guard) — every existing parser in this file already does this; the new one must match, not introduce a bare `result.stdout` trust. |
| An attacker-controlled `ranking-weights.toml` (if ever loaded from an untrusted path) injects extreme weight values | Tampering | Out of scope for this phase — `DEFAULT_RANKING_WEIGHTS_PATH` is a fixed, bundled path (`os.path.join(os.path.dirname(__file__), "..", "references", "ranking-weights.toml")`), never user-supplied; `_is_valid_weights_structure`'s numeric/finite checks (`math.isfinite`) already guard against non-numeric/NaN/inf injection regardless of source. |

## Sources

### Primary (HIGH confidence — read directly this session)
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (full file) — `_RUNTIME_ENV_SIGNALS`,
  `detect_current_runtime`, `KNOWN_CLIS`, `detect_opencode_models`/`detect_cursor_agent_models`
  parser pattern, `build_runtimes_snapshot`.
- `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` (full file) — `_FIELD_TYPES`,
  `_VALID_NATIVE_RUNTIME`, `validate_catalog_entry`, `merge_catalog_entry`.
- `skills/ai-kit-spec-review/ai_kit_spec/model_sources.py` (full file) — `fetch_models_dev`,
  `fetch_artificial_analysis`, `_USER_AGENT` 403-workaround note.
- `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` (full file) — `DEFAULT_WEIGHTS`,
  `_is_valid_weights_structure`, `load_ranking_weights`, `score_candidates`,
  `_MISSING_AXIS_DEFAULT`.
- `skills/ai-kit-spec-review/ai_kit_spec/cache.py` (full file) — `cache_is_stale`,
  `cache_write_json`, `cache_read_json`.
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py` (targeted sections) — `main()` argparse setup,
  `detect-runtimes`/`fetch-model-catalog`/`detect-current-runtime` command bodies, the
  `fetch-meta.json` sidecar-staleness precedent.
- `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` (grepped) — `_VALID_NATIVE_RUNTIME` at
  line 97, duplicate of `model_catalog.py`'s set.
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py` (full file) —
  confirms this skill only shells out to `ai_kit_spec`'s `detect-runtimes` CLI, never imports
  `detection.py` directly.
- `tests/test_ai_kit_spec.py` (targeted sections) — `TestDetectCurrentRuntime`,
  `TestBuildRuntimesSnapshot`, `TestCacheStaleness`, `TestLoadRankingWeights`,
  `TestScoreCandidates`, full class inventory (73 test classes).
- `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml` (`[tool.ruff]`, `[tool.pylint]`,
  `[tool.vulture]`, `[tool.pyright]`) — confirmed `ai_kit_spec`/`ai-kit-spec-config` are excluded
  from ruff/pylint/pyright/vulture/py-compile file-scope patterns; only `tests/test_ai_kit_spec.py`
  (under `tests/`) and the top-level `ai-kit-spec-review.py` shim are in-gate.
- Live `codex debug models` invocation (this session, `codex-cli 0.147.0`, real binary via
  `~/.volta/bin/codex`) — full JSON captured and parsed.
- Live `claude --help` invocation (this session, real binary at
  `~/.local/share/claude/versions/2.1.281`, bypassing the user's shell alias).
- Live `opencode models --verbose` invocation (this session, real binary at
  `~/.opencode/bin/opencode`) — 110-line output, 4 providers observed.
- Live fetch of `https://models.dev/api.json` (this session) — confirmed `modalities.input`
  shape and the exact 4 dated-fallback ids from CONTEXT.md's Specifics section
  (`claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`) all
  exist verbatim in the live anthropic provider list today.
- Manual `uv run pyright skills/ai-kit-spec-review/ai_kit_spec/` invocation (this session) —
  confirmed 4 pre-existing pyright errors in files this package excludes from its own gate
  (`cli.py:476`, `detection.py:67,69`, `dispatch.py:196`) — informational only, not this phase's
  responsibility to fix.

### Secondary (MEDIUM confidence)
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md` §2, §3.1, §4, §9, §11 —
  the approved design and its own errata section (§11), which already documents several of this
  phase's corrections (order, codex signals, `reasoning_modes` reuse).
- `AGENTS.md` §Architecture — the project-level contract text for `detect_installed_clis`/
  `detect_current_runtime`/`native_runtime`, confirming the two-file `_VALID_NATIVE_RUNTIME`
  duplication is a documented, known project quirk (not a surprise bug).
- `.planning/milestones/v1.0-phases/01.2-multi-cli-runtime-foundation/01.2-RESEARCH.md` and
  `01.2-VERIFICATION.md` — prior decisions D-01..D-09 this phase's D-01 explicitly supersedes for
  ordering, plus the original ASVS V4 finding this phase's Security Domain section reuses.
- `.planning/phases/16-ai-kit-spec-extensions/16-DISCUSSION-LOG.md` — the alternatives considered
  and evidence presented (`CODEX_THREAD_ID` grep count of 20 vs. `CODEX_SANDBOX` count of 0)
  behind D-01/D-02.

### Tertiary (LOW confidence)
None — every claim in this document is either read directly from source this session, captured
from a real live invocation this session, or cited to an in-repo planning document.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; stdlib-only confirmed against the actual installed
  `python3` and the project's own documented constraint.
- Architecture: HIGH — every touched function/table read directly from source this session; the
  extension points (`_FIELD_TYPES`, `_RUNTIME_ENV_SIGNALS`, `_is_valid_weights_structure`) are
  explicit, named, and already the designed seam for this exact kind of change.
- Pitfalls: HIGH for Pitfalls 1-3 (each grounded in a direct source read plus, for Pitfall 1, a
  cross-file grep confirming the duplication); the two Assumptions-Log items about parser
  filtering choices (A1, A2) are appropriately LOW/`[ASSUMED]` since they are judgment calls on
  real captured data, not verified facts.

**Research date:** 2026-09-23
**Valid until:** ~30 days for the code-structure findings (stable internal API); the live-captured
external data (`codex debug models` shape, models.dev's current anthropic model list, opencode's
`--verbose` output shape) should be treated as valid for ~7 days given these are externally
versioned CLIs/services that can change format without this repo's involvement — re-verify before
relying on the exact fixture shapes if execution is delayed materially past this window.
