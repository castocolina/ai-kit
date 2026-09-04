# Model Discovery — Producer-Side (`ai-kit-spec-config`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `ai-kit-spec-config` a real model-discovery/curation mechanism — deterministic enrichment from models.dev and Artificial Analysis, local naming heuristics for router/batch-mode/fallback fields, purpose-weighted ranking, and a ranked user-facing presentation — replacing today's lightweight per-model WebSearch at Step 2.2.

**Architecture:** New, focused modules under `skills/ai-kit-spec-review/ai_kit_spec/` (the shared package `ai-kit-spec-config`'s wizard already calls into via `ai-kit-spec.py`, per its own Step 0 resolution): a catalog schema/cache module, an HTTP-fetch module for the two external sources, a matcher, a local-heuristics module, and a ranker — wired together by two new CLI subcommands, `fetch-model-catalog` (automatic discover→match→enrich→merge, never persists an unconfirmed candidate) and `confirm-catalog-entry` (the only path that persists a wizard-confirmed, previously-unmatched candidate). `ai-kit-spec-config/SKILL.md`'s Step 2.2 is rewritten to call these and present ranked, current-snapshot-filtered output instead of doing its own ad-hoc WebSearch; Step 2.6/Step 3 are rewritten to carry the `purpose` decided at Step 2.2 through to the `review-spec.toml` write, closing the handoff Plan B's consumer-side filters depend on.

**Tech Stack:** Python 3.12, stdlib only (`urllib.request` for HTTP — this repo's runtime has zero external dependencies, per `pyproject.toml`'s own comment), `tomllib` for reading the weights file, `unittest` for tests.

**Spec:** `docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md`

**Independent of** `docs/superpowers/plans/2026-09-02-ai-kit-model-discovery-consumers.md` (Plan B) — this plan produces `purpose`/`is_router`/`fallback_quota` fields and a curated catalog; Plan B only reads `purpose` from `review-spec.toml`. Either can land first.

## Global Constraints

- **models.dev**: `GET https://models.dev/api.json` — free, unauthenticated, single call, whole catalog. Confirmed live (2026-09-02) shape: top-level keys are provider ids (e.g. `"openai"`, `"xai"`, `"deepseek"`); each provider object has a `"models"` dict keyed by bare model id (e.g. `"gpt-4o"`), whose value has `id` (bare, same as the key), `reasoning` (bool), `tool_call` (bool), `structured_output` (bool), `limit: {context, output}`, `cost: {input, output, cache_read}` (USD per 1M tokens), among other fields.
- **Artificial Analysis**: `GET https://artificialanalysis.ai/api/v2/language/models/free`, header `x-api-key: <key>`, paginated (`?page=N`, `pagination.has_more`/`pagination.total_pages`, 200 entries/page, confirmed live ~4 pages / ~800 models 2026-09-02). Confirmed live response shape per entry: `id`, `name`, `slug`, `release_date`, `model_creator: {id, name}`, `evaluations: {artificial_analysis_intelligence_index, artificial_analysis_coding_index, artificial_analysis_agentic_index}`, `pricing: {price_1m_input_tokens, price_1m_output_tokens, price_1m_cache_hit_tokens, price_1m_cache_write_tokens}`, `performance: {median_output_tokens_per_second, median_time_to_first_token_seconds, median_time_to_first_answer_token_seconds, median_end_to_end_response_time_seconds}`. Free tier: 100 requests/24h, no `context_window`/tool-calling field.
- **Secrets file**: `~/.config/ai-kit/secrets.env`, flat `KEY=VALUE` lines, key name `ARTIFICIAL_ANALYSIS_API_KEY`. A real key already lives there (created 2026-09-02, outside this plan's scope to manage/rotate) — code must read it, never write or overwrite it. Env var of the same name takes precedence when set.
- **Catalog cache**: `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/spec/model-catalog.json` (same `cache_base` helper `runtimes.json`/`quota.json` already use). TTL ~30 days (`CATALOG_TTL_SECONDS = 30 * 24 * 3600`), same pattern as `detection.RUNTIMES_TTL_SECONDS`.
- **Catalog identity is a canonical `vendor/model` key, not a raw CLI id** (spec §5's own example key, `"openai/gpt-5.6-sol"`): two different CLIs can report the same real model under different raw strings (opencode's `openai/gpt-5.6-sol` vs. codex's bare `gpt-5.6-sol`) — these must collapse to ONE catalog entry with BOTH runtimes merged in, never two entries or a last-write-wins overwrite of `runtimes`. `model_catalog.canonical_key(provider: str, bare_model_id: str) -> str` (Task 2) is the single place this normalization happens; every writer of `model-catalog.json` goes through it.
- **Catalog schema — mandatory fields** (spec §5): `provider` (`str`), `runtimes` (non-empty `dict[str, dict]`, keyed by CLI name), `source` (`dict`), `confidence` (`str`, one of `"high"`/`"medium"`/`"low"`), `last_verified` (`str`, `YYYY-MM-DD`). Every other field (`scores`, `pricing`, `tokens_per_sec`, `batch_mode`, `is_router`, `fallback_quota`, etc.) is optional; a missing optional field never blocks a write or a rank — it just doesn't contribute to that axis. Both mandatory and optional fields are **type-checked when present**, not just checked for presence — `model_catalog.validate_catalog_entry` (Task 2) and `config_io.validate_reviewer_fields` (Task 2, the `review-spec.toml`-side sibling covering `purpose`/`is_router`/`fallback_quota`) share this contract, and both `fetch-model-catalog` (Task 7) and `render-toml` (Task 2) enforce it — matching the design spec §5's explicit requirement ("enforced in both `render-toml` and the new `fetch-model-catalog` subcommand").
- **A model discovered by a CLI but never confidently matched to either external source is never written to `model-catalog.json` automatically** (spec §4 step 2 / §8): it is surfaced to the wizard (Task 8) as an *unmatched candidate* requiring one targeted search + explicit user confirmation before `merge_catalog_entry` ever runs on it. `fetch-model-catalog`'s own automatic write only ever persists candidates that matched at least one source, plus untouched pass-through of `existing_catalog` entries.
- **Ranking only ever considers models present in the CURRENT runtime snapshot** (spec §4/§7 intent — a curated ladder must reflect what's actually installed right now): a catalog entry for a CLI/model no longer discovered by the latest `detect-runtimes` run is kept in the cache (cheap, avoids re-fetching if it comes back) but excluded from what Task 8 ranks and presents.
- **Ranking weights** (spec §6, copied verbatim — write these exact numbers into the TOML in Task 1):

  | Axis | REVIEW | EXECUTE |
  |---|---|---|
  | `intelligence_index` | 0.30 | 0.15 |
  | `coding_index` | 0.10 | 0.30 |
  | `agentic_index` | 0.15 | 0.25 |
  | `context_window` | 0.15 | 0.10 |
  | `tool_calling` | 0.05 | 0.15 |
  | `price` | 0.15 | 0.15 |
  | `speed` | 0.05 | 0.10 |

  Bonuses: `batch_mode = 8`, `fallback_quota = 5`, `bonus_cap = 15` (combined bonus never exceeds 15 points on the final 0–100 score). The design spec §6 also names a `task_affinity_match = 2` bonus scoped to "the plan/doc's scope (frontend/backend/mixed)" — that scope only exists at *dispatch* time (a specific plan/doc being reviewed or executed), never at `ai-kit-spec-config` wizard time (Task 8), which ranks models generically, before any specific plan exists. Wiring a bonus with no real value at either of this plan's two `score_candidates` call sites would be dead code with a fabricated always-`None` input — **this plan deliberately omits `task_affinity_match` from `score_candidates`/`ranking-weights.toml`**, but the bonus itself is NOT dropped: it is implemented where the scope it needs actually exists — `docs/superpowers/plans/2026-09-02-ai-kit-model-discovery-consumers.md` (Plan B) Task 1 applies it as a tie-break ranking term inside `execute_selection.resolve_execute_candidates`, at real dispatch time, when a real `task_type` is known (see that plan's Task 1 for the exact mechanism). This is a coordinated, cross-plan resolution of the design's single bonus, not two independent decisions — round-2 review flagged the earlier phrasing ("handled by `filter_by_affinity`'s hard filter") as not actually equivalent to the spec's additive bonus; it now is.
- Never enumerate OpenRouter as a candidate source (spec §2 non-goals) — candidates come only from each installed CLI's own model list (`detect-runtimes`, already exists).
- Every network call degrades to an empty/cached result on failure — **never raises**, **never blocks the wizard** (spec §8). This means more than "returns `{}`/`[]`" — **a failed fetch of one source must never overwrite that same source's already-cached fields on an existing catalog entry.** `fetch_models_dev`/`fetch_artificial_analysis` (Task 4) each return an explicit `(data, ok: bool)` pair, not just data — `ok=False` on any exception (including a mid-pagination failure for Artificial Analysis), `ok=True` on a completed call (even one that legitimately returns nothing, e.g. no API key configured for Artificial Analysis). `build_model_catalog` (Task 7) uses `ok` to decide whether that source's fields are refreshed or left exactly as they were in `existing_catalog` for this run.
- No new third-party dependencies. `urllib.request`/`json`/`tomllib` only.
- **Artificial Analysis attribution is mandatory wherever its data is shown to the user** — the [Artificial Analysis API docs](https://artificialanalysis.ai/data-api/docs) require attribution across all API tiers, free included. Every place this plan surfaces `scores`/`pricing`(when Artificial-Analysis-sourced)/`tokens_per_sec` to the user (Task 8's ranked presentation) carries a visible "(via Artificial Analysis)" tag on those fields — see Task 8.
- `pytest` is **not** installed in this repo's dev environment (`pyproject.toml`'s `dev` group has no `pytest`; `python3 -m pytest --version` fails with `No module named pytest`) — every test-run command in this plan uses `python3 -m unittest tests.test_ai_kit_spec -k <pattern> -v` (module dotted path, no `.py`; `unittest`'s CLI has supported `-k` substring matching since Python 3.7) instead of `pytest -k`. Full-suite runs use `python3 -m unittest discover -s tests -v`.
- Follow this repo's existing test style: `unittest.TestCase`, one `class Test<Thing>` per function, `test_<behavior>` method names, dependency-injected I/O functions (`fetch_fn=`, `run_fn=`, matching this codebase's existing `which_fn`/`run_fn` convention) so tests never hit the real network.
- Prefer this repo's confirmed-available modern tools over legacy ones in every runnable command in this plan: `rg` not `grep`, `bat` (with `--line-range`) not `cat`/`sed -n`, `sd` not `sed` for substitutions.
- Every commit made while executing this plan ends with:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
  ```

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/ai-kit-spec-review/references/ranking-weights.toml` | Versioned default ranking weights + bonuses (Global Constraints table, verbatim). |
| `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` | Load weights; score+rank a set of catalog entries for one purpose. Pure functions, no I/O. |
| `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` | Catalog cache path, canonical `vendor/model` key, mandatory+optional-field type-checked schema validation, single-entry merge (reject-and-report, never abort-the-whole-write), current-snapshot ranking filter, heuristic-correction writeback. |
| `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` | **Modify.** Add `validate_reviewer_fields` (type-checks `purpose`/`is_router`/`fallback_quota` when present) and call it from `cfg_render_toml`, rejecting-and-reporting one bad `[[reviewers]]` entry rather than aborting the whole write — mirrors `model_catalog.validate_catalog_entry`'s contract on the `review-spec.toml` side. |
| `skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py` | Read `ARTIFICIAL_ANALYSIS_API_KEY` from env or `~/.config/ai-kit/secrets.env`. |
| `skills/ai-kit-spec-review/ai_kit_spec/model_sources.py` | HTTP fetchers for models.dev and Artificial Analysis. Dependency-injected `fetch_fn` for testability. |
| `skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py` | Match a CLI-native model id against the flattened models.dev index and the Artificial Analysis list; merge matched fields into one candidate-enrichment dict. |
| `skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py` | Naming heuristics for `is_router`/`batch_mode` (no external source exists for these — spec §3). |
| `skills/ai-kit-spec-review/ai-kit-spec.py` + `ai_kit_spec/cli.py` | New `fetch-model-catalog` subcommand orchestrating the above: discover → match → enrich → heuristics → validate → cache-write, TTL-aware. |
| `skills/ai-kit-spec-config/SKILL.md` | Step 2.2 rewritten to call `fetch-model-catalog` and present its ranked, purpose-labeled output instead of doing an ad-hoc WebSearch per model. |
| `tests/test_ai_kit_spec.py` | New test classes for every module above. |

---

### Task 1: Ranking weights file + ranker

**Files:**
- Create: `skills/ai-kit-spec-review/references/ranking-weights.toml`
- Create: `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing (pure functions + a static TOML file).
- Produces: `DEFAULT_RANKING_WEIGHTS_PATH: str` (module constant, the real file's absolute-resolvable path via `os.path.join(os.path.dirname(__file__), "..", "references", "ranking-weights.toml")`), `load_ranking_weights(path: str = DEFAULT_RANKING_WEIGHTS_PATH) -> dict`, `score_candidates(entries: list, purpose: str, weights: dict) -> list` — returns entries (shallow-copied dicts) each with an added `"score": float` key, sorted descending. No `task_affinity` parameter — see Global Constraints' note on why that spec-§6 bonus is deliberately omitted from this plan (no real value exists at either call site). `ai-kit-spec-config`'s Step 2.2 (Task 8) is the only real caller; Task 7's `fetch-model-catalog` subcommand only builds/persists the catalog, it never ranks.

- [ ] **Step 1: Write the failing tests**

Add a new class to `tests/test_ai_kit_spec.py` (add `model_ranker` to the existing
`from ai_kit_spec import (...)` bare-module-import block at the top of the file first):

```python
class TestLoadRankingWeights(unittest.TestCase):
    def test_loads_the_real_bundled_weights_file(self):
        weights = model_ranker.load_ranking_weights()
        self.assertAlmostEqual(weights["review"]["intelligence_index"], 0.30)
        self.assertAlmostEqual(weights["execute"]["coding_index"], 0.30)
        self.assertEqual(weights["bonuses"]["batch_mode"], 8)
        self.assertEqual(weights["bonuses"]["bonus_cap"], 15)

    def test_missing_file_falls_back_to_default_weights(self):
        weights = model_ranker.load_ranking_weights("/nonexistent/path.toml")
        self.assertIn("review", weights)
        self.assertIn("execute", weights)
        self.assertIn("bonuses", weights)

    def test_fallback_returns_an_independent_copy_each_call(self):
        # HIGH finding: a caller mutating one fallback result must never corrupt the next.
        w1 = model_ranker.load_ranking_weights("/nonexistent/path.toml")
        w1["review"]["intelligence_index"] = 999.0
        w2 = model_ranker.load_ranking_weights("/nonexistent/path.toml")
        self.assertEqual(w2["review"]["intelligence_index"], 0.30)

    def test_syntactically_valid_toml_missing_a_purpose_section_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n")
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            self.assertIn("review", weights)
            self.assertIn("execute", weights)
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_missing_an_axis_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[review]\nintelligence_index = 0.99\n"  # missing every other axis --
                    # MEDIUM finding (round-4): deliberately 0.99, NOT 0.30 (the real default's
                    # own value) -- an earlier draft used 0.30 here too, so this assertion could
                    # pass whether load_ranking_weights actually fell back OR just happened to
                    # read this partial file's own intelligence_index value back verbatim,
                    # proving nothing about the fallback path actually running.
                    "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                    "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                    "price = 0.15\nspeed = 0.10\n"
                    "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n")
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            # Asserting the REAL default's value (0.30), distinguishable from the fixture's
            # own 0.99, is what actually proves the fallback path discarded the incomplete
            # file rather than silently using its partial values as-is.
            self.assertAlmostEqual(weights["review"]["intelligence_index"], 0.30)
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_with_a_non_numeric_axis_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write('[review]\nintelligence_index = "high"\ncoding_index = 0.10\n'
                    "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                    "price = 0.15\nspeed = 0.05\n"
                    "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                    "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                    "price = 0.15\nspeed = 0.10\n"
                    "[bonuses]\nbatch_mode = 8\nfallback_quota = 5\nbonus_cap = 15\n")
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            self.assertIsInstance(weights["review"]["intelligence_index"], (int, float))
        finally:
            os.remove(path)

    def test_syntactically_valid_toml_missing_a_bonus_field_falls_back(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[review]\nintelligence_index = 0.30\ncoding_index = 0.10\n"
                    "agentic_index = 0.15\ncontext_window = 0.15\ntool_calling = 0.05\n"
                    "price = 0.15\nspeed = 0.05\n"
                    "[execute]\nintelligence_index = 0.15\ncoding_index = 0.30\n"
                    "agentic_index = 0.25\ncontext_window = 0.10\ntool_calling = 0.15\n"
                    "price = 0.15\nspeed = 0.10\n"
                    "[bonuses]\nbatch_mode = 8\n")  # missing fallback_quota/bonus_cap
            path = f.name
        try:
            weights = model_ranker.load_ranking_weights(path)
            self.assertIn("bonus_cap", weights["bonuses"])
        finally:
            os.remove(path)


class TestScoreCandidates(unittest.TestCase):
    def setUp(self):
        self.weights = model_ranker.load_ranking_weights()

    def test_higher_intelligence_index_ranks_first_for_review(self):
        entries = [
            {"key": "low", "scores": {"intelligence_index": 40, "coding_index": 40,
                                       "agentic_index": 40}},
            {"key": "high", "scores": {"intelligence_index": 90, "coding_index": 40,
                                        "agentic_index": 40}},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual([e["key"] for e in ranked], ["high", "low"])

    def test_missing_axis_excluded_never_zeroes_the_score(self):
        # "no_scores" has NO scores dict at all -- must not be treated as 0 on every axis;
        # its score comes only from whatever axes it does have (tool_calling here).
        entries = [
            {"key": "no_scores", "tool_calling": True},
            {"key": "has_scores", "scores": {"intelligence_index": 1, "coding_index": 1,
                                              "agentic_index": 1}, "tool_calling": False},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        by_key = {e["key"]: e["score"] for e in ranked}
        self.assertGreater(by_key["no_scores"], 0)

    def test_batch_mode_bonus_can_flip_the_ranking(self):
        entries = [
            {"key": "no_batch", "scores": {"intelligence_index": 50, "coding_index": 50,
                                            "agentic_index": 50}, "batch_mode": False},
            {"key": "batch", "scores": {"intelligence_index": 48, "coding_index": 48,
                                         "agentic_index": 48}, "batch_mode": True},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual(ranked[0]["key"], "batch")

    def test_bonus_is_capped(self):
        entries = [{"key": "everything", "scores": {"intelligence_index": 100,
                                                      "coding_index": 100, "agentic_index": 100},
                    "batch_mode": True, "fallback_quota": True}]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertLessEqual(ranked[0]["score"], 100.0)

    def test_price_is_normalized_within_the_candidate_set_and_inverted(self):
        entries = [
            {"key": "cheap", "pricing": {"input_per_1m": 1.0}},
            {"key": "expensive", "pricing": {"input_per_1m": 100.0}},
        ]
        ranked = model_ranker.score_candidates(entries, "review", self.weights)
        self.assertEqual(ranked[0]["key"], "cheap")

    def test_score_never_exceeds_100_even_with_full_axes_and_bonuses(self):
        entries = [{"key": "maxed", "scores": {"intelligence_index": 100, "coding_index": 100,
                                                 "agentic_index": 100}, "tool_calling": True,
                    "batch_mode": True, "fallback_quota": True}]
        ranked = model_ranker.score_candidates(entries, "execute", self.weights)
        self.assertLessEqual(ranked[0]["score"], 100.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestLoadRankingWeights -k TestScoreCandidates -v`
Expected: FAIL — `ImportError`/`AttributeError`, `model_ranker` does not exist yet.

- [ ] **Step 3: Create the weights file**

`skills/ai-kit-spec-review/references/ranking-weights.toml`:

```toml
# Default weighted-ranking configuration for ai-kit-spec-config's model discovery
# (docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md, Section 6).
# Fixed defaults -- the user is never asked to tune these per wizard run.

[review]
intelligence_index = 0.30
coding_index = 0.10
agentic_index = 0.15
context_window = 0.15
tool_calling = 0.05
price = 0.15
speed = 0.05

[execute]
intelligence_index = 0.15
coding_index = 0.30
agentic_index = 0.25
context_window = 0.10
tool_calling = 0.15
price = 0.15
speed = 0.10

[bonuses]
# Applied additively to the 0-100 weighted score, capped combined at bonus_cap.
# NOTE: design spec 2026-09-02 Section 6 also names a task_affinity_match=2 bonus, scoped to
# a specific plan/doc's task_affinity -- that context does not exist at this wizard's
# config-time ranking (Task 8), so it is deliberately omitted here rather than wired to a
# fabricated always-None input (see the plan's Global Constraints for the full rationale).
batch_mode = 8
fallback_quota = 5
bonus_cap = 15
```

- [ ] **Step 4: Implement `model_ranker.py`**

```python
"""Purpose-weighted ranking of model-catalog entries (design spec 2026-09-02, Section 6).
Pure functions -- no network, no file writes. score_candidates never mutates its inputs."""
import copy
import math
import os

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:          # Python < 3.11 -- degrade to the hardcoded defaults.
    tomllib = None  # type: ignore[assignment]

DEFAULT_RANKING_WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "references", "ranking-weights.toml")

# Mirrors ranking-weights.toml exactly -- used only when the file is missing/unreadable/
# malformed, so ranking never blocks on a corrupted or absent weights file.
DEFAULT_WEIGHTS = {
    "review": {"intelligence_index": 0.30, "coding_index": 0.10, "agentic_index": 0.15,
               "context_window": 0.15, "tool_calling": 0.05, "price": 0.15, "speed": 0.05},
    "execute": {"intelligence_index": 0.15, "coding_index": 0.30, "agentic_index": 0.25,
                "context_window": 0.10, "tool_calling": 0.15, "price": 0.15, "speed": 0.10},
    "bonuses": {"batch_mode": 8, "fallback_quota": 5, "bonus_cap": 15},
}

_REQUIRED_AXES = {"intelligence_index", "coding_index", "agentic_index", "context_window",
                   "tool_calling", "price", "speed"}
_REQUIRED_BONUS_FIELDS = {"batch_mode", "fallback_quota", "bonus_cap"}


def _is_valid_weights_structure(weights) -> bool:
    """HIGH finding: syntactically-valid TOML that doesn't match the shape score_candidates
    actually needs (a missing purpose section/axis, a non-numeric axis value, or a missing
    bonus field) must not reach score_candidates -- it would raise a KeyError/TypeError deep
    inside ranking instead of degrading to defaults up front, breaking the "malformed
    configuration never blocks ranking" promise this module makes. Checked eagerly, once, at
    load time -- score_candidates itself trusts its `weights` argument completely."""
    if not isinstance(weights, dict):
        return False
    for purpose in ("review", "execute"):
        axes = weights.get(purpose)
        if not isinstance(axes, dict) or _REQUIRED_AXES - axes.keys():
            return False
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in axes.values()):
            return False
    bonuses = weights.get("bonuses")
    if not isinstance(bonuses, dict) or _REQUIRED_BONUS_FIELDS - bonuses.keys():
        return False
    if not all(isinstance(bonuses[f], (int, float)) and math.isfinite(bonuses[f])
               for f in _REQUIRED_BONUS_FIELDS):
        return False
    return True


def load_ranking_weights(path: str = DEFAULT_RANKING_WEIGHTS_PATH) -> dict:
    """Never raises: missing file, unreadable file, malformed TOML, no tomllib (<3.11), or
    syntactically-valid-but-structurally-wrong TOML (missing section/axis/bonus field, or a
    non-numeric axis value) all fall back to an INDEPENDENT COPY of DEFAULT_WEIGHTS -- a
    `copy.deepcopy`, never the shared module-level dict, so one caller mutating its result
    (e.g. a test) can never corrupt what the next call returns."""
    if tomllib is None:
        return copy.deepcopy(DEFAULT_WEIGHTS)
    try:
        with open(path, "rb") as f:
            weights = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return copy.deepcopy(DEFAULT_WEIGHTS)
    if not _is_valid_weights_structure(weights):
        return copy.deepcopy(DEFAULT_WEIGHTS)
    return weights


def _max_context_window(entry: dict) -> float | None:
    windows = [rt.get("ctx_window") for rt in entry.get("runtimes", {}).values()
               if rt.get("ctx_window") is not None]
    return max(windows) if windows else None


def _normalize_minmax(raw: dict, invert: bool = False) -> dict:
    """raw: {key: float|None}. None stays None (excluded from scoring downstream, never
    treated as 0). A set with no present values, or where every present value is identical,
    normalizes every present value to 100 -- there is no meaningful spread to rank by, and a
    single-candidate set must never divide by zero."""
    present = {k: v for k, v in raw.items() if v is not None}
    if not present:
        return dict.fromkeys(raw)
    lo, hi = min(present.values()), max(present.values())
    if hi == lo:
        return {k: (100.0 if v is not None else None) for k, v in raw.items()}

    def scale(v):
        if v is None:
            return None
        pct = (v - lo) / (hi - lo) * 100.0
        return 100.0 - pct if invert else pct

    return {k: scale(v) for k, v in raw.items()}


def score_candidates(entries: list, purpose: str, weights: dict) -> list:
    """purpose: "review" or "execute". Absent axes are excluded from the weighted sum and the
    remaining weights renormalize proportionally (spec Section 6) -- missing data never
    penalizes, it just contributes no signal. price and context_window/speed are normalized
    RELATIVE TO THIS CALL'S entries (never a fixed global ceiling) -- price inverted (cheaper
    scores higher). Returns shallow copies of `entries`, each with an added "score" (0-100,
    rounded to 1 decimal), sorted descending; never mutates the input list/dicts. No
    task_affinity bonus -- see ranking-weights.toml's own note on why that spec-named bonus is
    deliberately absent from this implementation."""
    axis_weights = weights[purpose]
    price_raw = {e["key"]: e.get("pricing", {}).get("input_per_1m") for e in entries}
    price_norm = _normalize_minmax(price_raw, invert=True)
    speed_norm = _normalize_minmax({e["key"]: e.get("tokens_per_sec") for e in entries})
    ctx_raw = {e["key"]: (math.log10(w) if (w := _max_context_window(e)) else None)
               for e in entries}
    ctx_norm = _normalize_minmax(ctx_raw)

    scored = []
    for e in entries:
        tool_call = e.get("tool_calling")
        axis_values = {
            "intelligence_index": e.get("scores", {}).get("intelligence_index"),
            "coding_index": e.get("scores", {}).get("coding_index"),
            "agentic_index": e.get("scores", {}).get("agentic_index"),
            "tool_calling": 100.0 if tool_call is True else (0.0 if tool_call is False else None),
            "context_window": ctx_norm[e["key"]],
            "price": price_norm[e["key"]],
            "speed": speed_norm[e["key"]],
        }
        present = {a: v for a, v in axis_values.items() if v is not None}
        weight_sum = sum(axis_weights[a] for a in present)
        base = (sum(axis_weights[a] * v for a, v in present.items()) / weight_sum
                if weight_sum else 0.0)
        bonus = 0.0
        if e.get("batch_mode"):
            bonus += weights["bonuses"]["batch_mode"]
        if e.get("fallback_quota"):
            bonus += weights["bonuses"]["fallback_quota"]
        bonus = min(bonus, weights["bonuses"]["bonus_cap"])
        score = min(100.0, base + bonus)
        scored.append({**e, "score": round(score, 1)})
    return sorted(scored, key=lambda e: e["score"], reverse=True)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestLoadRankingWeights -k TestScoreCandidates -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/ai-kit-spec-review/references/ranking-weights.toml \
        skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add purpose-weighted model ranker

score_candidates weighs catalog entries per purpose (review/execute),
excluding+renormalizing missing axes, with batch_mode/fallback_quota
bonuses capped at 15 (spec's task_affinity_match bonus is deliberately
omitted -- no real value exists at any call site in this plan). Weights
live in a versioned references/ranking-weights.toml, never asked of the
user per run.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 2: Catalog schema validation, canonical key, cache path

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` (add `validate_reviewer_fields`, call it from `cfg_render_toml`)
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py` (extend `cache-path --kind` to accept `catalog`)
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `ai_kit_spec.cache.cache_base`, `cache_read_json`, `cache_write_json`, `cache_is_stale` (existing, `cache.py`).
- Produces:
  - `CATALOG_TTL_SECONDS: int`
  - `cache_catalog_path(env: dict) -> str`
  - `canonical_key(provider: str, bare_model_id: str) -> str` — always `f"{provider}/{bare_model_id}"`; the ONE place catalog identity is computed, so two CLIs naming the same model differently (opencode's `openai/gpt-5.6-sol` vs. codex's bare `gpt-5.6-sol`) collapse to one key.
  - `validate_catalog_entry(model_id: str, entry: dict) -> str | None` (returns a rejection reason string, or `None` if valid) — checks mandatory-field **presence AND type**, and **type** (not just presence) of every optional field that IS present.
  - `merge_catalog_entry(catalog: dict, model_id: str, entry: dict) -> tuple[dict, str | None]` — invalid entries are never merged; a valid entry's `runtimes` dict is **merged into**, not replacing, any existing entry's `runtimes` at that key (Task 7 relies on this to combine multiple CLIs' runtime mappings under one canonical key).
  - `current_candidate_keys(catalog: dict, discovered_models: list) -> set[str]` — the subset of `catalog`'s keys whose `runtimes` contain at least one `(cli, model_id)` pair present in `discovered_models` (`[{"cli": ..., "model_id": ...}, ...]`, the same shape Task 7 builds from a runtimes snapshot). Task 8's ranking step uses this to exclude catalog entries for CLIs/models no longer installed.
  - `apply_heuristic_corrections(catalog: dict, model_id: str, corrections: dict) -> tuple[dict, str | None]` — merges a small dict of user-corrected fields (`is_router`/`batch_mode`/`fallback_quota`, any subset) into one existing catalog entry, returning `(new_catalog, rejection_reason)` (never mutates the input); raises no exception for an unknown `model_id` — returns `(catalog, None)` unchanged (nothing to correct). **CRITICAL finding: a correction is routed through the exact same `validate_catalog_entry` contract `merge_catalog_entry` already enforces** — `cache_write_json` only writes atomically, it does not validate, so a heuristic correction that would produce a schema-invalid merged entry (e.g. a non-bool `is_router`) is rejected and reported, exactly like `merge_catalog_entry`'s own contract, never silently written. Task 7's `apply-heuristic-correction` subcommand is the only caller and propagates the rejection (nonzero exit, no write) the same way `confirm-catalog-entry` already does.
- `config_io.validate_reviewer_fields(entry: dict) -> str | None` — the `review-spec.toml` sibling of `validate_catalog_entry`: when present, `purpose` must be one of `"review"`/`"execute"`/`"both"`, `is_router`/`fallback_quota` must be `bool`. Absent is always valid (pre-migration configs). Called from `cfg_render_toml` (Step 5 below) — an invalid `[[reviewers]]` entry is dropped with a reported reason, not written, and never aborts the rest of the TOML write.

- [ ] **Step 1: Write the failing tests**

Add `model_catalog` to the bare-module-import block, then:

```python
class TestCacheCatalogPath(unittest.TestCase):
    def test_uses_cache_base_convention(self):
        path = model_catalog.cache_catalog_path({"HOME": "/home/u"})
        self.assertEqual(path, "/home/u/.cache/ai-kit/spec/model-catalog.json")


class TestCanonicalKey(unittest.TestCase):
    def test_builds_vendor_slash_model(self):
        self.assertEqual(model_catalog.canonical_key("openai", "gpt-5.6-sol"),
                          "openai/gpt-5.6-sol")


class TestValidateCatalogEntry(unittest.TestCase):
    def _valid_entry(self, **overrides):
        entry = {"provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                  "source": {"models_dev": True}, "confidence": "high",
                  "last_verified": "2026-09-02"}
        entry.update(overrides)
        return entry

    def test_valid_entry_returns_none(self):
        self.assertIsNone(model_catalog.validate_catalog_entry(
            "openai/gpt-5.6-sol", self._valid_entry()))

    def test_missing_mandatory_field_is_rejected(self):
        entry = {"provider": "openai", "runtimes": {"opencode": {}}}
        reason = model_catalog.validate_catalog_entry("openai/gpt-5.6-sol", entry)
        self.assertIsNotNone(reason)
        self.assertIn("source", reason)

    def test_empty_runtimes_is_rejected(self):
        entry = {"provider": "openai", "runtimes": {}, "source": {}, "confidence": "low",
                  "last_verified": "2026-09-02"}
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)

    def test_missing_optional_fields_never_rejected(self):
        entry = {"provider": "openai", "runtimes": {"opencode": {}}, "source": {},
                  "confidence": "low", "last_verified": "2026-09-02"}
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))

    def test_wrong_type_provider_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(provider=123))
        self.assertIsNotNone(reason)
        self.assertIn("provider", reason)

    def test_non_dict_runtimes_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(runtimes=["opencode"]))
        self.assertIsNotNone(reason)

    def test_unrecognized_confidence_value_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(confidence="very-sure"))
        self.assertIsNotNone(reason)
        self.assertIn("confidence", reason)

    def test_wrong_type_optional_field_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(batch_mode="yes"))
        self.assertIsNotNone(reason)
        self.assertIn("batch_mode", reason)

    def test_wrong_type_scores_subfield_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(scores={"intelligence_index": "high"}))
        self.assertIsNotNone(reason)
        self.assertIn("scores", reason)

    def test_correct_type_optional_fields_pass(self):
        entry = self._valid_entry(batch_mode=True, is_router=False, fallback_quota=False,
                                   tokens_per_sec=142.3, native=False,
                                   reasoning_modes=["low", "medium", "high"], fast_mode=False,
                                   speed_tier="standard",
                                   scores={"intelligence_index": 68.4, "coding_index": 74.1,
                                           "agentic_index": 61.2},
                                   pricing={"input_per_1m": 3.5, "output_per_1m": 14.0})
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))

    def test_wrong_type_reasoning_modes_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(reasoning_modes="high"))
        self.assertIsNotNone(reason)
        self.assertIn("reasoning_modes", reason)

    def test_reasoning_modes_with_a_non_string_element_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(reasoning_modes=["low", 3]))
        self.assertIsNotNone(reason)
        self.assertIn("reasoning_modes", reason)

    def test_wrong_type_fast_mode_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(fast_mode="no"))
        self.assertIsNotNone(reason)
        self.assertIn("fast_mode", reason)

    def test_wrong_type_speed_tier_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(speed_tier=3))
        self.assertIsNotNone(reason)
        self.assertIn("speed_tier", reason)

    def test_malformed_last_verified_date_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(last_verified="09/02/2026"))
        self.assertIsNotNone(reason)
        self.assertIn("last_verified", reason)

    def test_runtime_entry_wrong_type_model_id_is_rejected(self):
        entry = self._valid_entry(runtimes={"opencode": {"model_id": 123}})
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)
        self.assertIn("model_id", reason)

    def test_runtime_entry_wrong_type_ctx_window_is_rejected(self):
        entry = self._valid_entry(runtimes={"opencode": {"model_id": "m", "ctx_window": "big"}})
        reason = model_catalog.validate_catalog_entry("x", entry)
        self.assertIsNotNone(reason)
        self.assertIn("ctx_window", reason)

    def test_runtime_entry_correct_types_pass(self):
        entry = self._valid_entry(
            runtimes={"opencode": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}})
        self.assertIsNone(model_catalog.validate_catalog_entry("x", entry))


class TestMergeCatalogEntry(unittest.TestCase):
    def test_valid_entry_is_added(self):
        entry = {"provider": "openai", "runtimes": {"opencode": {}}, "source": {},
                  "confidence": "high", "last_verified": "2026-09-02"}
        catalog, reason = model_catalog.merge_catalog_entry({}, "openai/gpt-5.6-sol", entry)
        self.assertIsNone(reason)
        self.assertIn("openai/gpt-5.6-sol", catalog)

    def test_invalid_entry_is_rejected_and_catalog_unchanged(self):
        catalog, reason = model_catalog.merge_catalog_entry({"existing": {}}, "bad", {})
        self.assertIsNotNone(reason)
        self.assertEqual(catalog, {"existing": {}})

    def test_does_not_mutate_input_catalog(self):
        original = {"existing": {}}
        entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                 "last_verified": "2026-09-02"}
        model_catalog.merge_catalog_entry(original, "new", entry)
        self.assertNotIn("new", original)

    def test_runtimes_merge_across_two_cli_writes_for_the_same_key(self):
        entry_a = {"provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
                   "source": {}, "confidence": "high", "last_verified": "2026-09-02"}
        catalog, _ = model_catalog.merge_catalog_entry({}, "openai/gpt-5.6-sol", entry_a)
        entry_b = {"provider": "openai", "runtimes": {"codex": {"model_id": "gpt-5.6-sol"}},
                   "source": {}, "confidence": "high", "last_verified": "2026-09-02"}
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "openai/gpt-5.6-sol", entry_b)
        self.assertIsNone(reason)
        self.assertIn("opencode", catalog["openai/gpt-5.6-sol"]["runtimes"])
        self.assertIn("codex", catalog["openai/gpt-5.6-sol"]["runtimes"])

    def test_explicit_none_in_the_incoming_entry_clears_the_existing_field(self):
        # CRITICAL finding: a source's provenance flipping to false must actually clear the
        # field it used to own, not leave it behind under plain dict-spread's "absent key
        # means preserve" semantics.
        existing_entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                           "last_verified": "2026-09-02", "scores": {"intelligence_index": 91.0}}
        catalog = {"k": existing_entry}
        entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                  "last_verified": "2026-09-02", "scores": None}
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNone(reason)
        self.assertNotIn("scores", catalog["k"])

    def test_key_absent_from_incoming_entry_still_preserves_the_existing_value(self):
        # Contrast with the test above: OMITTING a key (a source that's simply down this run,
        # never claiming anything about the field) must still preserve the cached value --
        # only an explicit None is a clear signal.
        existing_entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                           "last_verified": "2026-09-02", "scores": {"intelligence_index": 91.0}}
        catalog = {"k": existing_entry}
        entry = {"provider": "p", "runtimes": {"c": {}}, "source": {}, "confidence": "high",
                  "last_verified": "2026-09-02"}  # no "scores" key at all
        catalog, reason = model_catalog.merge_catalog_entry(catalog, "k", entry)
        self.assertIsNone(reason)
        self.assertEqual(catalog["k"]["scores"], {"intelligence_index": 91.0})


class TestCurrentCandidateKeys(unittest.TestCase):
    def test_keeps_only_keys_with_a_currently_discovered_runtime(self):
        catalog = {
            "openai/gpt-5.6-sol": {"runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}}},
            "xai/grok-old": {"runtimes": {"opencode": {"model_id": "xai/grok-old"}}},
        }
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        self.assertEqual(model_catalog.current_candidate_keys(catalog, discovered),
                          {"openai/gpt-5.6-sol"})


class TestApplyHeuristicCorrections(unittest.TestCase):
    def test_merges_corrected_fields_into_existing_entry(self):
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": False, "batch_mode": True})
        self.assertIsNone(reason)
        self.assertFalse(updated["router-env/x"]["is_router"])
        self.assertTrue(updated["router-env/x"]["batch_mode"])

    def test_marks_every_corrected_field_confirmed_even_when_value_is_unchanged(self):
        # HIGH finding: the wizard must be able to tell "never asked" apart from "asked, and
        # the user's answer happened to match the heuristic's own guess" -- so a field must
        # be recorded as confirmed even when the "correction" leaves its value unchanged.
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": True})  # confirmed as-is, not corrected
        self.assertIsNone(reason)
        self.assertTrue(updated["router-env/x"]["is_router"])
        self.assertEqual(updated["router-env/x"]["heuristic_confirmed"], ["is_router"])

    def test_heuristic_confirmed_accumulates_across_separate_calls(self):
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True,
                                     "heuristic_confirmed": ["is_router"]}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"batch_mode": False})
        self.assertIsNone(reason)
        self.assertEqual(updated["router-env/x"]["heuristic_confirmed"],
                          ["batch_mode", "is_router"])

    def test_unknown_key_is_a_no_op(self):
        catalog = {"existing": {}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "nonexistent", {"is_router": True})
        self.assertIsNone(reason)
        self.assertEqual(updated, catalog)

    def test_does_not_mutate_input_catalog(self):
        catalog = {"k": {"provider": "p", "runtimes": {"c": {}}, "source": {},
                          "confidence": "high", "last_verified": "2026-09-02", "is_router": True}}
        model_catalog.apply_heuristic_corrections(catalog, "k", {"is_router": False})
        self.assertTrue(catalog["k"]["is_router"])

    def test_correction_that_would_produce_a_schema_invalid_entry_is_rejected(self):
        # CRITICAL finding: apply_heuristic_corrections must not bypass the same type-checked
        # schema validation merge_catalog_entry already enforces -- cache_write_json only writes
        # atomically, it never validates, so this is the ONLY gate before a bad correction reaches
        # the cache.
        catalog = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                     "source": {}, "confidence": "low",
                                     "last_verified": "2026-09-02", "is_router": True}}
        updated, reason = model_catalog.apply_heuristic_corrections(
            catalog, "router-env/x", {"is_router": "not-a-bool"})
        self.assertIsNotNone(reason)
        self.assertIn("is_router", reason)
        self.assertTrue(updated["router-env/x"]["is_router"])  # unchanged -- rejected correction never applied
```

Add to `tests/test_ai_kit_spec.py`, in whichever `TestCase` class already covers `cfg_render_toml`
(confirmed live: `class TestRenderAndWriteToml(unittest.TestCase):` — `rg "class TestRenderAndWriteToml"
tests/test_ai_kit_spec.py`):

```python
    def test_render_toml_rejects_invalid_purpose_value(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"}]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("not-a-real-purpose", output)

    def test_render_toml_rejects_non_string_purpose_without_raising(self):
        # HIGH finding: a non-string (unhashable) purpose value must be REJECTED, never crash
        # cfg_render_toml with an unhandled TypeError from a bare `in <set>` membership test.
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "purpose": ["review", "execute"]}]}
        output = config_io.cfg_render_toml(config)  # must not raise
        self.assertNotIn("[[reviewers]]", output)

    def test_render_toml_keeps_valid_purpose_value(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "purpose": "execute"}]}
        output = config_io.cfg_render_toml(config)
        self.assertIn('purpose = "execute"', output)

    def test_render_toml_rejects_non_bool_is_router(self):
        config = {"policy": {}, "reviewers": [
            {"key": "a", "model": "m", "vendor": "v", "is_router": "yes"}]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn("is_router", output)

    def test_render_toml_drops_rejected_reviewer_from_the_ladder_too(self):
        # HIGH finding: a dangling policy.ladder reference to a dropped reviewer key produces
        # a config that LOOKS valid (parses fine) but resolve_ladder_pick can never satisfy.
        config = {"policy": {"mode": "single", "ladder": ["bad", "good"]}, "reviewers": [
            {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
            {"key": "good", "model": "m2", "vendor": "v2"},
        ]}
        output = config_io.cfg_render_toml(config)
        self.assertNotIn('"bad"', output)
        ladder_line = next(line for line in output.splitlines() if line.startswith("ladder"))
        self.assertNotIn("bad", ladder_line)
        self.assertIn("good", ladder_line)

    def test_render_toml_no_dangling_ladder_warning_when_rejected_key_not_in_ladder(self):
        # MEDIUM finding: a rejected reviewer whose key was never referenced in policy.ladder
        # at all must not trigger the "dropped dangling reference" stderr warning -- only an
        # actual ladder/reviewers divergence should. cfg_render_toml prints rejections to
        # stderr (Step 5's implementation), not into its returned string, so capture stderr.
        config = {"policy": {"mode": "single", "ladder": ["good"]}, "reviewers": [
            {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
            {"key": "good", "model": "m2", "vendor": "v2"},
        ]}
        import io
        from contextlib import redirect_stderr
        captured = io.StringIO()
        with redirect_stderr(captured):
            config_io.cfg_render_toml(config)
        self.assertNotIn("dangling", captured.getvalue())

    def test_render_toml_result_resolves_cleanly_through_cfg_resolve(self):
        # The dropped-entry write must be USABLE, not just superficially valid TOML -- round-trip
        # it through cfg_write_toml + cfg_resolve (this repo's real resolution path) and confirm
        # the ladder cfg_resolve sees contains no reference to the dropped key.
        config = {"policy": {"mode": "single", "ladder": ["bad", "good"]}, "reviewers": [
            {"key": "bad", "model": "m", "vendor": "v", "purpose": "not-a-real-purpose"},
            {"key": "good", "model": "m2", "vendor": "v2", "cli": "opencode",
             "command": "opencode run -m {model}"},
        ]}
        with tempfile.TemporaryDirectory() as d:
            path = config_io.cfg_local_path(d)  # ./.aikit/review-spec.toml under d
            config_io.cfg_write_toml(path, config)
            resolved = config_io.cfg_resolve(d, {"HOME": d})
            self.assertNotIn("bad", resolved["policy"]["ladder"])
            self.assertIn("good", resolved["policy"]["ladder"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestCacheCatalogPath -k TestCanonicalKey -k TestValidateCatalogEntry -k TestMergeCatalogEntry -k TestCurrentCandidateKeys -k TestApplyHeuristicCorrections -v`
Expected: FAIL — `model_catalog` module not found.

- [ ] **Step 3: Implement `model_catalog.py`**

```python
"""Model catalog cache: canonical identity, type-checked schema validation, single-entry
merge, current-snapshot filtering, and heuristic-correction writeback (design spec
2026-09-02, Sections 4/5/8). One bad entry is rejected and reported; it never aborts the
whole catalog write."""
import os
import re

from ai_kit_spec.cache import cache_base

CATALOG_TTL_SECONDS = 30 * 24 * 3600     # ~30 days -- spec Section 8, same order as RUNTIMES_TTL_SECONDS

_MANDATORY_CATALOG_FIELDS = {"provider", "runtimes", "source", "confidence", "last_verified"}
_VALID_CONFIDENCE = {"high", "medium", "low"}
_LAST_VERIFIED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# type checks for every field this design names -- mandatory AND optional. A field not in this
# table (there shouldn't be one; every field the design spec names is listed) is left unchecked
# rather than rejected, so an unrecognized-but-harmless future field never blocks a write.
_FIELD_TYPES = {
    "provider": str, "source": dict, "confidence": str, "last_verified": str,
    "batch_mode": bool, "is_router": bool, "fallback_quota": bool,
    "tokens_per_sec": (int, float), "max_output_tokens": int, "structured_output": bool,
    "tool_calling": bool, "native": bool, "reasoning_modes": list, "fast_mode": bool,
    "speed_tier": str,
    # HIGH finding: is_router/batch_mode/fallback_quota have no external source (spec §3) --
    # they are ALWAYS either a naming heuristic's guess or a user's explicit confirmation of
    # that guess, and a plain bool alone cannot tell those two provenances apart. This list
    # records which of those three field names the user has actually been asked about and
    # answered (Step 8 of ai-kit-spec-config, Task 8) -- whether they left the heuristic's
    # value unchanged or corrected it -- so the wizard never re-asks about a field already
    # confirmed. Written exclusively by apply_heuristic_corrections below.
    "heuristic_confirmed": list,
}
_NUMERIC_SUBFIELD_TABLES = {
    "scores": {"intelligence_index", "coding_index", "agentic_index"},
    "pricing": {"input_per_1m", "output_per_1m"},
}
_RUNTIME_FIELD_TYPES = {"model_id": str, "ctx_window": (int, float)}


def cache_catalog_path(env: dict) -> str:
    return os.path.join(cache_base(env), "model-catalog.json")


def canonical_key(provider: str, bare_model_id: str) -> str:
    """The ONE place catalog identity is computed -- every writer of model-catalog.json goes
    through this, so two CLIs naming the same real model differently (opencode's
    "openai/gpt-5.6-sol" vs. codex's bare "gpt-5.6-sol") always collapse to one key."""
    return f"{provider}/{bare_model_id}"


def validate_catalog_entry(model_id: str, entry: dict) -> str | None:
    """Mandatory fields per spec Section 5: provider, runtimes (non-empty dict), source,
    confidence, last_verified -- checked for PRESENCE and TYPE (last_verified additionally
    checked for YYYY-MM-DD shape). Every optional field IS type-checked when present (a
    missing optional field is never a validation failure -- only a reduced ranking signal
    later, model_ranker.py); a present-but-wrong-typed one is. Every `runtimes` value's own
    `model_id`/`ctx_window` sub-fields are type-checked too when present, not just the
    top-level "is it a dict" shape check."""
    missing = _MANDATORY_CATALOG_FIELDS - entry.keys()
    if missing:
        return f"{model_id}: missing mandatory field(s) {sorted(missing)}"
    if not isinstance(entry.get("runtimes"), dict) or not entry["runtimes"]:
        return f"{model_id}: 'runtimes' must be a non-empty object"
    for cli_name, rt in entry["runtimes"].items():
        if not isinstance(rt, dict):
            return f"{model_id}: every 'runtimes' value must be an object"
        for field, expected_type in _RUNTIME_FIELD_TYPES.items():
            if field in rt and rt[field] is not None and not isinstance(rt[field], expected_type):
                return f"{model_id}: 'runtimes.{cli_name}.{field}' must be of type {expected_type}"
    if entry.get("confidence") not in _VALID_CONFIDENCE:
        return f"{model_id}: 'confidence' must be one of {sorted(_VALID_CONFIDENCE)}"
    if "last_verified" in entry and isinstance(entry["last_verified"], str) and \
            not _LAST_VERIFIED_RE.match(entry["last_verified"]):
        return f"{model_id}: 'last_verified' must be YYYY-MM-DD"
    for field, expected_type in _FIELD_TYPES.items():
        # HIGH finding: an explicit None on an OPTIONAL field means "no value" (and, per
        # merge_catalog_entry below, "clear this field on merge") -- it must never be rejected
        # as a type mismatch, the same way a runtime sub-field's None is already exempted above.
        if field in entry and entry[field] is not None and not isinstance(entry[field], expected_type):
            return f"{model_id}: '{field}' must be of type {expected_type}"
    if "reasoning_modes" in entry and isinstance(entry["reasoning_modes"], list) and \
            not all(isinstance(m, str) for m in entry["reasoning_modes"]):
        return f"{model_id}: 'reasoning_modes' must be a list of strings"
    if "heuristic_confirmed" in entry and isinstance(entry["heuristic_confirmed"], list) and \
            not all(isinstance(f, str) for f in entry["heuristic_confirmed"]):
        return f"{model_id}: 'heuristic_confirmed' must be a list of strings"
    for table_field, subfields in _NUMERIC_SUBFIELD_TABLES.items():
        table = entry.get(table_field)
        if table is None:
            continue
        if not isinstance(table, dict):
            return f"{model_id}: '{table_field}' must be an object"
        for k, v in table.items():
            if k in subfields and v is not None and not isinstance(v, (int, float)):
                return f"{model_id}: '{table_field}.{k}' must be numeric"
    return None


def merge_catalog_entry(catalog: dict, model_id: str, entry: dict) -> tuple:
    """Returns (new_catalog, rejection_reason). Never mutates `catalog`. An invalid entry is
    rejected and reported (spec Section 8: "that single entry is rejected and reported; the
    rest of the write proceeds") -- the caller (fetch-model-catalog, Task 7) collects
    rejections across a whole discovery run and reports them together, never aborting.
    `runtimes` is MERGED into any existing entry at this key, never replaced wholesale --
    this is what lets two different CLIs' runtime mappings for the same real model coexist
    under one canonical key (HIGH finding: catalog identity must not lose runtime mappings)."""
    reason = validate_catalog_entry(model_id, entry)
    if reason:
        return catalog, reason
    updated = dict(catalog)
    existing = updated.get(model_id)
    if existing:
        merged = {**existing, **entry}
        merged["runtimes"] = {**existing.get("runtimes", {}), **entry.get("runtimes", {})}
        # CRITICAL finding: an explicit None in the INCOMING `entry` means "this field's owning
        # source no longer confirms it -- clear it", not "leave whatever's cached untouched".
        # Plain dict-spread (`{**existing, **entry}`) cannot express that distinction on its
        # own: a key entirely ABSENT from `entry` is correctly preserved from `existing` (a
        # source that's simply down this run never wrote the key at all), but a key PRESENT in
        # `entry` with value None is a deliberate clear -- stripped here so a later re-query
        # that flips a source's provenance to false can never leave stale scores/pricing/etc.
        # behind under a now-false `source.*` flag.
        merged = {k: v for k, v in merged.items() if not (k in entry and entry[k] is None)}
        updated[model_id] = merged
    else:
        # A brand-new entry never needs the clear-signal: strip any None-valued optional field
        # so the catalog stays free of meaningless nulls for a key that never had a prior value.
        updated[model_id] = {k: v for k, v in entry.items() if v is not None}
    return updated, None


def current_candidate_keys(catalog: dict, discovered_models: list) -> set:
    """The subset of catalog keys whose `runtimes` contain at least one (cli, model_id) pair
    from `discovered_models` (the same [{"cli", "model_id"}, ...] shape Task 7 builds from a
    fresh runtimes snapshot). Used to exclude stale entries -- a model no longer installed --
    from ranking/presentation (Task 8) without deleting them from the cache."""
    discovered_pairs = {(c["cli"], c["model_id"]) for c in discovered_models}
    return {
        key for key, entry in catalog.items()
        if any((cli, rt.get("model_id")) in discovered_pairs
               for cli, rt in entry.get("runtimes", {}).items())
    }


def apply_heuristic_corrections(catalog: dict, model_id: str, corrections: dict) -> tuple:
    """Merges user-confirmed heuristic fields (is_router/batch_mode/fallback_quota, any
    subset) into one existing entry. Never mutates `catalog`. A `model_id` not already in
    `catalog` is a no-op -- correcting a field on an entry that doesn't exist has nothing to
    do (the wizard, Task 8, only ever corrects an entry it just displayed, which is always
    already in the catalog by then). Returns (new_catalog, rejection_reason) -- CRITICAL
    finding: a correction is validated through validate_catalog_entry BEFORE it is applied,
    exactly like merge_catalog_entry's own contract, since cache_write_json only writes
    atomically and never validates. A rejected correction leaves the existing entry
    untouched and is reported, never silently written.

    HIGH finding: is_router/batch_mode/fallback_quota have no external source (spec §3) --
    every value on these three fields is either the naming heuristic's own guess or a value
    this function has recorded as user-confirmed; a plain bool alone cannot distinguish the
    two, so a re-run of the wizard could never tell "never asked" apart from "asked and the
    user's answer happened to match the heuristic's guess." EVERY key present in
    `corrections` is therefore added to the merged entry's `heuristic_confirmed` list --
    regardless of whether the corrected value actually differs from what was already stored
    -- because it is the act of asking-and-answering that matters, not whether the answer
    changed anything. Callers (Task 7's `apply-heuristic-correction` subcommand, and Task 8's
    wizard Step 8) MUST call this for every field they present to the user, even when the
    user simply confirms the heuristic's guess as correct -- calling it only on an actual
    correction would leave confirmed-but-unchanged fields indistinguishable from
    never-asked ones, defeating the whole point of this field."""
    if model_id not in catalog:
        return catalog, None
    candidate = {**catalog[model_id], **corrections}
    already_confirmed = set(catalog[model_id].get("heuristic_confirmed", []))
    candidate["heuristic_confirmed"] = sorted(already_confirmed | set(corrections.keys()))
    reason = validate_catalog_entry(model_id, candidate)
    if reason:
        return catalog, reason
    updated = dict(catalog)
    updated[model_id] = candidate
    return updated, None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestCacheCatalogPath -k TestCanonicalKey -k TestValidateCatalogEntry -k TestMergeCatalogEntry -k TestCurrentCandidateKeys -k TestApplyHeuristicCorrections -v`
Expected: PASS.

- [ ] **Step 5: Wire type-checked validation into `render-toml` (`config_io.py`)**

In `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`, add above `cfg_render_toml`:

```python
_VALID_PURPOSE = {"review", "execute", "both"}


def validate_reviewer_fields(entry: dict) -> str | None:
    """The review-spec.toml-side sibling of model_catalog.validate_catalog_entry (design spec
    2026-09-02 Section 5: "enforced in both render-toml and the new fetch-model-catalog
    subcommand"). Only checks the THREE fields this design adds -- purpose/is_router/
    fallback_quota -- when present; every pre-existing field's validation is unchanged.
    Absent is always valid (pre-migration configs keep working exactly as before)."""
    key = entry.get("key", "<unknown>")
    # HIGH finding: `entry["purpose"] not in _VALID_PURPOSE` raises TypeError when `purpose` is
    # an unhashable value (a list/dict) rather than rejecting it as a schema-validation error --
    # the type check MUST run first, short-circuiting before the set-membership test ever sees
    # an unhashable value (spec Section 8: "schema-invalid... entry is rejected and reported",
    # never an unhandled exception).
    if "purpose" in entry and (
            not isinstance(entry["purpose"], str) or entry["purpose"] not in _VALID_PURPOSE):
        return f"{key}: 'purpose' must be one of {sorted(_VALID_PURPOSE)}"
    for field in ("is_router", "fallback_quota"):
        if field in entry and not isinstance(entry[field], bool):
            return f"{key}: '{field}' must be a boolean"
    return None
```

Then modify `cfg_render_toml`'s reviewer loop to validate-and-report rather than blindly
serialize, and — HIGH finding: rejecting a reviewer must not leave a dangling reference to
its key in `policy.ladder` — validate reviewers FIRST, computing the surviving key set, then
render `policy.ladder` filtered to that set before ever writing the `[policy]` block (the
ladder comment/value and the reviewers loop must agree on the same surviving-keys set, so
render this in two passes: validate all reviewers, then render):

```python
def cfg_render_toml(config: dict) -> str:
    """... (docstring unchanged, plus:) A reviewer entry that fails validate_reviewer_fields is
    dropped individually (never aborts the rest of the write) AND removed from policy.ladder --
    a valid-looking ladder that references a key with no corresponding [[reviewers]] entry is
    unusable (resolve_ladder_pick can never satisfy it), so the two must never diverge."""
    lines = []
    rejections = []
    reviewers = config.get("reviewers", [])
    valid_reviewers = []
    dropped_keys = set()
    for r in reviewers:
        reason = validate_reviewer_fields(r)
        if reason:
            rejections.append(reason)
            if "key" in r:
                dropped_keys.add(r["key"])
            continue
        valid_reviewers.append(r)

    if "strategy" in config:
        lines.append(f"strategy = {_toml_value(config['strategy'])}")
        lines.append("")
    policy = config.get("policy", {})
    if policy:
        raw_ladder = policy.get("ladder") or []
        ladder = [key for key in raw_ladder if key not in dropped_keys]
        # MEDIUM finding: a rejected reviewer's key that was never actually referenced in
        # policy.ladder must never trigger this warning -- `dropped_keys` alone doesn't mean
        # the ladder had a dangling reference, only their INTERSECTION does. Computing it once
        # avoids both the false-positive-on-empty-intersection bug and a redundant second
        # `dropped_keys & set(raw_ladder)` computation on the line below.
        dangling = dropped_keys & set(raw_ladder)
        if dangling:
            rejections.append(
                f"policy.ladder: dropped dangling reference(s) to rejected reviewer key(s) "
                f"{sorted(dangling)}")
        if ladder:
            lines.append("# Priority fallback order (first available reviewer wins the")
            if policy.get("mode") == "double":
                lines.append("# primary slot; double mode also seats an independent secondary):")
            else:
                lines.append("# primary slot):")
            for i, key in enumerate(ladder, 1):
                lines.append(f"#   {i}. {key}")
        lines.append("[policy]")
        for k, v in policy.items():
            v = ladder if k == "ladder" else v
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    for r in valid_reviewers:
        lines.append("[[reviewers]]")
        for k, v in r.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    if rejections:
        import sys
        print(f"WARNING: {len(rejections)} issue(s) found and NOT written: "
              f"{'; '.join(rejections)}", file=sys.stderr)
    return "\n".join(lines).rstrip("\n") + "\n"
```

(A rejected entry is dropped individually — never aborts the rest of the write, matching
`merge_catalog_entry`'s contract exactly; `cfg_write_toml`'s caller, `render-toml`'s CLI
command, already prints whatever `cfg_render_toml` prints to stderr, so no further wiring is
needed there. `policy.ladder` is filtered by iterating `raw_ladder` — the user's original
order — never by iterating `dropped_keys`, so the surviving order is preserved exactly.)

- [ ] **Step 6: Add `cache-path --kind catalog`**

In `skills/ai-kit-spec-review/ai_kit_spec/cli.py`, extend the existing `cache-path` command
(avoids a hand-written `sed`/`sd` path substitution in Task 8's wizard prose later). **CRITICAL
fix: the existing block's `env = dict(os.environ)` line (the one already there today, above the
`print(...)`) must be kept — it is not shown redundantly below, but every branch's `print(...)`
still depends on it, including the new `catalog` branch:**

```python
    if args.command == "cache-path":
        env = dict(os.environ)
        from ai_kit_spec.model_catalog import cache_catalog_path
        if args.kind == "runtimes":
            print(cache_runtimes_path(env))
        elif args.kind == "catalog":
            print(cache_catalog_path(env))
        else:
            print(cache_quota_path(env))
        return 0
```

Also add `"catalog"` to the `p_cache_path.add_argument("--kind", choices=[...])` list (find the
existing `choices=` list for this argument and add the new value alongside `"runtimes"`/`"quota"`).

- [ ] **Step 7: Run the full test suite and manually verify the render-toml rejection behavior**

Run: `bash -o pipefail -c 'python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -20'`
(`-o pipefail` makes the pipeline's exit status the LAST failing stage's, not `tail`'s always-0
status — MEDIUM finding: a bare `... | tail -20` silently reports success even when the
`unittest` run failed, since only `tail`'s own exit code is checked.)
Expected: PASS (exit 0), including all seven new `cfg_render_toml` tests from Step 1 (three
rejection cases, one valid-value-is-kept case, one no-false-positive-warning case, plus the
two dangling-ladder-entry cases).

- [ ] **Step 8: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py \
        skills/ai-kit-spec-review/ai_kit_spec/config_io.py \
        skills/ai-kit-spec-review/ai_kit_spec/cli.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add type-checked model catalog schema + review-spec.toml field validation

validate_catalog_entry/merge_catalog_entry enforce the mandatory+optional
field TYPES (not just presence) from the 2026-09-02 model-discovery design
spec, merge runtimes across CLIs under one canonical vendor/model key
(canonical_key), and add current_candidate_keys/apply_heuristic_corrections
for Task 8's ranking-filter and correction-writeback needs. config_io's
new validate_reviewer_fields gives render-toml the same type-checked
rejection contract for purpose/is_router/fallback_quota. An invalid entry
on either side is rejected individually and reported, never aborting the
rest of the write.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 3: Secrets loader for the Artificial Analysis API key

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `secrets_env_path(env: dict) -> str`, `load_secret(env: dict, key: str) -> str | None`. Task 7's orchestration calls `load_secret(os.environ, "ARTIFICIAL_ANALYSIS_API_KEY")`.

- [ ] **Step 1: Write the failing tests**

Add `local_secrets` to the import block, then:

```python
class TestLoadSecret(unittest.TestCase):
    def test_env_var_takes_precedence(self):
        env = {"ARTIFICIAL_ANALYSIS_API_KEY": "from-env"}
        self.assertEqual(
            local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"), "from-env")

    def test_reads_from_secrets_file_when_env_absent(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_dir = os.path.join(d, ".config", "ai-kit")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "secrets.env"), "w", encoding="utf-8") as f:
                f.write("# comment\nARTIFICIAL_ANALYSIS_API_KEY=from-file\nOTHER=ignored\n")
            env = {"HOME": d}
            self.assertEqual(
                local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"), "from-file")

    def test_missing_file_returns_none(self):
        env = {"HOME": "/nonexistent-home-dir-xyz"}
        self.assertIsNone(local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"))

    def test_missing_key_in_existing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            cfg_dir = os.path.join(d, ".config", "ai-kit")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "secrets.env"), "w", encoding="utf-8") as f:
                f.write("OTHER=ignored\n")
            env = {"HOME": d}
            self.assertIsNone(local_secrets.load_secret(env, "ARTIFICIAL_ANALYSIS_API_KEY"))
```

(`tempfile` is already imported at the top of `tests/test_ai_kit_spec.py`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestLoadSecret -v`
Expected: FAIL — `local_secrets` module not found.

- [ ] **Step 3: Implement**

```python
"""Reads local, never-committed secrets (design spec 2026-09-02, Section 3/8) -- currently
just the Artificial Analysis API key. Not a general dotenv parser: flat KEY=VALUE lines only,
no quoting/escaping, matching the one real use case (an opaque API key string)."""
import os


def secrets_env_path(env: dict) -> str:
    return os.path.join(env.get("HOME", ""), ".config", "ai-kit", "secrets.env")


def load_secret(env: dict, key: str) -> str | None:
    """Env var takes precedence over the file. Missing file, missing key, or any read error
    -> None, never raises -- callers (model_sources.fetch_artificial_analysis) already treat
    a missing key as "skip this source", not a fatal error."""
    if env.get(key):
        return env[key]
    try:
        with open(secrets_env_path(env), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    return v.strip()
    except OSError:
        return None
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestLoadSecret -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add local secrets loader for the Artificial Analysis API key

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 4: External source fetchers (models.dev, Artificial Analysis)

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/model_sources.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `ai_kit_spec.local_secrets.load_secret` (Task 3, used only by Task 7's orchestration to obtain the key — this module itself just takes `api_key` as a plain argument, keeping it free of any env/file concerns).
- Produces: `MODELS_DEV_URL: str`, `ARTIFICIAL_ANALYSIS_URL: str`, `fetch_models_dev(fetch_fn=None) -> tuple[dict, bool]`, `fetch_artificial_analysis(api_key: str | None, fetch_fn=None) -> tuple[list, bool]`. **Both now return `(data, ok)`, not bare data** — `ok=False` means "this source's data this run cannot be trusted, do not use it to overwrite anything," `ok=True` means "this is what the source actually said" (which may legitimately be empty/no-key). Task 7's `build_model_catalog` uses `ok` to decide whether to refresh a source's fields on an existing entry or leave them exactly as cached (CRITICAL finding: a network failure must never silently downgrade an already-enriched cached entry).

- [ ] **Step 1: Write the failing tests**

Add `model_sources` to the import block, then:

```python
class TestFetchModelsDev(unittest.TestCase):
    def test_returns_parsed_json_and_ok_true_on_success(self):
        def fake_fetch(url, headers):
            self.assertEqual(url, model_sources.MODELS_DEV_URL)
            return {"openai": {"models": {"gpt-4o": {"id": "gpt-4o"}}}}
        data, ok = model_sources.fetch_models_dev(fetch_fn=fake_fetch)
        self.assertTrue(ok)
        self.assertEqual(data["openai"]["models"]["gpt-4o"]["id"], "gpt-4o")

    def test_fetch_failure_returns_empty_dict_and_ok_false(self):
        def failing_fetch(url, headers):
            raise urllib.error.URLError("no network")
        data, ok = model_sources.fetch_models_dev(fetch_fn=failing_fetch)
        self.assertEqual(data, {})
        self.assertFalse(ok)


class TestFetchArtificialAnalysis(unittest.TestCase):
    def test_no_api_key_returns_empty_list_and_ok_true_without_fetching(self):
        def should_not_be_called(url, headers):
            self.fail("must not fetch with no api key")
        data, ok = model_sources.fetch_artificial_analysis(None, fetch_fn=should_not_be_called)
        self.assertEqual(data, [])
        self.assertTrue(ok)  # deliberately skipped is NOT a failure -- nothing to preserve/lose

    def test_single_page_response(self):
        def fake_fetch(url, headers):
            self.assertEqual(headers, {"x-api-key": "aa_test"})
            return {"data": [{"id": "1", "name": "Model A"}],
                    "pagination": {"has_more": False}}
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=fake_fetch)
        self.assertTrue(ok)
        self.assertEqual([m["id"] for m in data], ["1"])

    def test_paginates_until_has_more_is_false(self):
        pages = {
            1: {"data": [{"id": "1"}], "pagination": {"has_more": True}},
            2: {"data": [{"id": "2"}], "pagination": {"has_more": False}},
        }
        def fake_fetch(url, headers):
            page = 1 if "page=1" in url else 2
            return pages[page]
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=fake_fetch)
        self.assertTrue(ok)
        self.assertEqual(sorted(m["id"] for m in data), ["1", "2"])

    def test_fetch_failure_returns_ok_false_and_whatever_was_collected_so_far(self):
        def failing_fetch(url, headers):
            raise urllib.error.URLError("no network")
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=failing_fetch)
        self.assertEqual(data, [])
        self.assertFalse(ok)

    def test_mid_pagination_failure_returns_ok_false_even_with_partial_data(self):
        def flaky_fetch(url, headers):
            if "page=1" in url:
                return {"data": [{"id": "1"}], "pagination": {"has_more": True}}
            raise urllib.error.URLError("dropped mid-pagination")
        data, ok = model_sources.fetch_artificial_analysis("aa_test", fetch_fn=flaky_fetch)
        self.assertFalse(ok)  # partial data exists but is NOT trustworthy -- caller must not use it
```

Add `import urllib.error` near the top of `tests/test_ai_kit_spec.py` if not already present.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestFetchModelsDev -k TestFetchArtificialAnalysis -v`
Expected: FAIL — `model_sources` module not found.

- [ ] **Step 3: Implement**

```python
"""HTTP fetchers for the two external model-data sources (design spec 2026-09-02, Section 3).
Both return (data, ok) -- ok=False on any failure (network down, bad status, malformed JSON,
a mid-pagination drop), never raise. `ok` is what lets the caller (`build_model_catalog`, Task
7) tell "this source genuinely has nothing to say" from "this source is unreachable right
now, keep whatever was cached" -- collapsing both into a bare empty return would silently wipe
a previously-enriched catalog entry on every transient network blip. Real network access lives
ONLY behind the injectable `fetch_fn` (this repo's existing which_fn/run_fn dependency-
injection convention), so tests never touch the network."""
import json
import urllib.error
import urllib.request

MODELS_DEV_URL = "https://models.dev/api.json"
ARTIFICIAL_ANALYSIS_URL = "https://artificialanalysis.ai/api/v2/language/models/free"

_TIMEOUT_SECONDS = 15


def _http_get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_models_dev(fetch_fn=None) -> tuple:
    """Free, unauthenticated, single call -- the whole catalog. (dict, ok). ok=False on any
    failure -- caller must then leave models.dev-sourced fields on any existing catalog entry
    untouched rather than treat "no data this run" as "no match" (spec Section 8)."""
    fetch_fn = fetch_fn or _http_get_json
    try:
        return fetch_fn(MODELS_DEV_URL, {}), True
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return {}, False


def fetch_artificial_analysis(api_key: str | None, fetch_fn=None) -> tuple:
    """([], True) immediately when api_key is falsy -- never calls out with no key, and this is
    NOT a failure (ok=True): a deliberately-unconfigured source has nothing cached to protect
    either. Paginates (200/page, confirmed live shape) until pagination.has_more is false; ANY
    failure mid-pagination returns (whatever was collected, False) -- ok=False even with
    partial data, because a truncated page set is not a trustworthy "this model has no AA
    match" signal for the pages never reached."""
    if not api_key:
        return [], True
    fetch_fn = fetch_fn or _http_get_json
    collected = []
    page = 1
    while True:
        try:
            resp = fetch_fn(f"{ARTIFICIAL_ANALYSIS_URL}?page={page}", {"x-api-key": api_key})
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return collected, False
        collected.extend(resp.get("data", []))
        if not resp.get("pagination", {}).get("has_more"):
            break
        page += 1
    return collected, True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestFetchModelsDev -k TestFetchArtificialAnalysis -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_sources.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add models.dev and Artificial Analysis fetchers

Both return (data, ok) rather than bare data -- ok=False on any failure
(including a mid-pagination drop) lets the caller (Task 7) distinguish
"source unreachable, preserve cached fields" from "source reachable, no
match" instead of silently downgrading an already-enriched cached entry
on a transient network blip. Artificial Analysis is skipped (ok=True,
not a failure) entirely with no api_key. fetch_fn is dependency-injected
so tests never touch the network, matching this repo's which_fn/run_fn
convention.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 5: Local naming heuristics (`is_router`, `batch_mode`, `fallback_quota`)

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `infer_is_router(provider_or_key: str) -> bool`, `infer_batch_mode(model_id: str) -> bool`, `infer_fallback_quota(provider_or_key: str) -> bool` (spec §3: "same inference source as `is_router`" — a router entry, by definition, has internal multi-backend fallback, so this delegates directly to `infer_is_router`; kept as its own named function, not just an alias, so the schema field and the heuristic each have one clear owner and either can diverge later without a call-site rename). Task 7's orchestration calls all three per discovered candidate; all three results are always surfaced to the user for confirm/correct during the wizard (Task 8), and a correction is persisted back via `model_catalog.apply_heuristic_corrections` (Task 2) — never left un-persisted.

- [ ] **Step 1: Write the failing tests**

Add `model_heuristics` to the import block, then:

```python
class TestInferIsRouter(unittest.TestCase):
    def test_router_env_provider_name_matches(self):
        self.assertTrue(model_heuristics.infer_is_router("router-env"))

    def test_plain_vendor_name_does_not_match(self):
        self.assertFalse(model_heuristics.infer_is_router("openai"))

    def test_case_insensitive(self):
        self.assertTrue(model_heuristics.infer_is_router("Router-Env"))


class TestInferBatchMode(unittest.TestCase):
    def test_flash_suffix_matches(self):
        self.assertTrue(model_heuristics.infer_batch_mode("gemini-3.5-flash"))

    def test_batch_suffix_matches(self):
        self.assertTrue(model_heuristics.infer_batch_mode("gpt-5.6-batch"))

    def test_mini_suffix_matches(self):
        self.assertTrue(model_heuristics.infer_batch_mode("gpt-5-mini"))

    def test_flagship_model_does_not_match(self):
        self.assertFalse(model_heuristics.infer_batch_mode("gpt-5.6-sol"))


class TestInferFallbackQuota(unittest.TestCase):
    def test_matches_wherever_is_router_matches(self):
        self.assertTrue(model_heuristics.infer_fallback_quota("router-env"))

    def test_plain_vendor_name_does_not_match(self):
        self.assertFalse(model_heuristics.infer_fallback_quota("openai"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestInferIsRouter -k TestInferBatchMode -k TestInferFallbackQuota -v`
Expected: FAIL — `model_heuristics` module not found.

- [ ] **Step 3: Implement**

```python
"""Naming heuristics for fields no external source provides (design spec 2026-09-02, Section
3): is_router, batch_mode, and fallback_quota. All three are best-effort signals only -- the
wizard (ai-kit-spec-config Step 2.2, Task 8 of this plan) always surfaces them to the user for
confirm/correct, and a correction is written back to the catalog cache
(model_catalog.apply_heuristic_corrections); nothing here writes anything itself."""

_ROUTER_NAME_HINTS = ("router", "-env", "local-llm")
_BATCH_NAME_HINTS = ("batch", "flash", "mini", "-lite")


def infer_is_router(provider_or_key: str) -> bool:
    """E.g. a provider/key named 'router-env' self-identifies as a router."""
    lowered = provider_or_key.lower()
    return any(hint in lowered for hint in _ROUTER_NAME_HINTS)


def infer_batch_mode(model_id: str) -> bool:
    """Suffixes like -flash/-batch/-mini/-lite correlate with non-interactive/batch-suitable
    variants across vendors (observed pattern, not a guarantee)."""
    lowered = model_id.lower()
    return any(hint in lowered for hint in _BATCH_NAME_HINTS)


def infer_fallback_quota(provider_or_key: str) -> bool:
    """spec Section 3: "same inference source as is_router" -- a router entry, by definition,
    has internal multi-backend fallback. Delegates to infer_is_router rather than duplicating
    _ROUTER_NAME_HINTS, so the two heuristics can never silently drift apart."""
    return infer_is_router(provider_or_key)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestInferIsRouter -k TestInferBatchMode -k TestInferFallbackQuota -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add is_router/batch_mode/fallback_quota naming heuristics

No external source covers any of the three (design spec Section 3) --
fallback_quota shares is_router's inference source per spec, and all
three are always surfaced to the user for confirmation in the wizard,
with corrections persisted back to the catalog cache.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 6: Matcher — CLI-native id → models.dev / Artificial Analysis

**Files:**
- Create: `skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: the raw shapes `fetch_models_dev`/`fetch_artificial_analysis` (Task 4) return.
- Produces: `bare_model_part(cli_model_id: str) -> str` (public — no leading underscore, because Task 7's `cli.py` also needs it and a MEDIUM finding, round-2 native-opus review, flagged an earlier draft for defining this exact same one-line split TWICE, once here and once again in `cli.py`, instead of Task 7 importing this module's own copy), `match_models_dev(cli_model_id: str, models_dev_data: dict) -> dict | None` (the matched model's fields plus its resolved `"provider"`, or `None`), `match_artificial_analysis(cli_model_id: str, aa_models: list, provider_hint: str | None = None) -> dict | None`. Task 7 calls `match_models_dev` first, then passes its resolved `provider` (when it matched) as `provider_hint` into `match_artificial_analysis` — collision-safe disambiguation using `model_creator` evidence, not "first normalized match wins" (HIGH finding: a normalized slug/name collision across two different vendors' models must not silently pick the wrong one). **CRITICAL finding: both functions implement the design's actual normalization-AND-FUZZY-MATCH contract (spec §4 step 2, §6)** — an exact match on the normalized string is tried first; only when that finds nothing does a conservative `difflib.SequenceMatcher`-ratio fuzzy fallback run (`_fuzzy_candidate_indices`, shared by both functions, threshold 0.82 with a 0.05 no-close-runner-up margin), against the same pool the exact step already searched. The fuzzy fallback reuses the exact step's own collision-safety rule (a single match wins; more than one, even a near-tie, returns `None` unless `provider_hint` disambiguates it) — fuzzy and exact matching are one contract, not two.

- [ ] **Step 1: Write the failing tests**

Add `model_matcher` to the import block, then:

```python
class TestMatchModelsDev(unittest.TestCase):
    def setUp(self):
        self.data = {
            "openai": {"models": {"gpt-5.6-sol": {"id": "gpt-5.6-sol", "reasoning": True,
                                                    "tool_call": True,
                                                    "limit": {"context": 400000, "output": 128000},
                                                    "cost": {"input": 3.5, "output": 14.0}}}},
            "xai": {"models": {"grok-4.6": {"id": "grok-4.6", "tool_call": True,
                                             "limit": {"context": 256000}}}},
        }

    def test_matches_provider_prefixed_id_exactly(self):
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", self.data)
        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_matches_bare_id_by_searching_all_providers(self):
        result = model_matcher.match_models_dev("gpt-5.6-sol", self.data)
        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "openai")

    def test_no_match_returns_none(self):
        self.assertIsNone(model_matcher.match_models_dev("nonexistent-model", self.data))

    def test_provider_hint_wrong_still_falls_back_to_bare_search(self):
        # opencode namespaces as "<provider>/<model>" but the provider label opencode uses
        # isn't guaranteed to equal models.dev's own provider key -- must not give up early.
        result = model_matcher.match_models_dev("some-other-vendor/grok-4.6", self.data)
        self.assertIsNotNone(result)
        self.assertEqual(result["provider"], "xai")

    def test_bare_id_collision_across_two_providers_returns_none_rather_than_guess(self):
        # HIGH finding: "first provider in dict-iteration order wins" would silently attach
        # one vendor's fields (pricing/context/tool_calling) to a DIFFERENT vendor's model.
        collision_data = {
            "openai": {"models": {"sol": {"id": "sol", "cost": {"input": 3.5}}}},
            "xai": {"models": {"sol": {"id": "sol", "cost": {"input": 1.0}}}},
        }
        self.assertIsNone(model_matcher.match_models_dev("sol", collision_data))

    def test_fuzzy_match_finds_a_near_spelling_when_exact_lookup_finds_nothing(self):
        # CRITICAL finding: the design mandates a normalization + FUZZY-MATCH step, not just
        # direct/near-exact string equality -- a CLI's own id can differ from models.dev's id
        # by a short version token (here: a trailing "-2" models.dev carries that the CLI's own
        # id doesn't) that pure normalization (case/separator folding) alone never closes.
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {
            "id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}}
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", fuzzy_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_fuzzy_match_returns_none_when_no_candidate_is_close_enough(self):
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {"id": "gpt-5.6-sol-2"}}}}
        self.assertIsNone(model_matcher.match_models_dev("totally-different-vendor-model", fuzzy_data))

    def test_fuzzy_match_with_two_equally_close_candidates_returns_none_rather_than_guess(self):
        # Collision-safety extends to the fuzzy path too -- two near-ties (both an equally
        # plausible "-a"/"-b" variant of the target) must not silently pick either one.
        fuzzy_collision = {
            "openai": {"models": {"gpt-5.6-sola": {"id": "gpt-5.6-sola"}}},
            "xai": {"models": {"gpt-5.6-solb": {"id": "gpt-5.6-solb"}}},
        }
        self.assertIsNone(model_matcher.match_models_dev("gpt-5.6-sol", fuzzy_collision))

    def test_hinted_provider_prefix_disambiguates_a_bare_id_collision(self):
        # The SAME collision as above, but the caller gave a "<hint>/<model>" shaped id --
        # step-1 lookup already resolves this unambiguously, no fallback search needed.
        collision_data = {
            "openai": {"models": {"sol": {"id": "sol", "cost": {"input": 3.5}}}},
            "xai": {"models": {"sol": {"id": "sol", "cost": {"input": 1.0}}}},
        }
        result = model_matcher.match_models_dev("openai/sol", collision_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["cost"]["input"], 3.5)


class TestMatchArtificialAnalysis(unittest.TestCase):
    def setUp(self):
        self.models = [
            {"id": "abc", "name": "GPT-5.6 Sol", "slug": "gpt-5-6-sol",
             "model_creator": {"name": "OpenAI"},
             "evaluations": {"artificial_analysis_intelligence_index": 68.4,
                              "artificial_analysis_coding_index": 74.1,
                              "artificial_analysis_agentic_index": 61.2},
             "performance": {"median_output_tokens_per_second": 142.3}},
        ]

    def test_matches_by_normalized_slug(self):
        result = model_matcher.match_artificial_analysis("openai/gpt-5.6-sol", self.models)
        self.assertIsNotNone(result)
        self.assertEqual(result["evaluations"]["artificial_analysis_coding_index"], 74.1)

    def test_no_match_returns_none(self):
        self.assertIsNone(
            model_matcher.match_artificial_analysis("totally-unknown-model", self.models))

    def test_fuzzy_match_finds_a_near_spelling_when_exact_lookup_finds_nothing(self):
        # CRITICAL finding: same fuzzy fallback as match_models_dev, applied to AA's own
        # slug/name fields -- a short version token difference must not fall through to
        # "unmatched" when normalization + fuzzy similarity would confidently resolve it.
        near_models = [{"id": "1", "name": "GPT-5.6 Sol V2", "slug": "gpt-5-6-sol-v2",
                        "model_creator": {"name": "OpenAI"},
                        "evaluations": {"artificial_analysis_coding_index": 74.1}}]
        result = model_matcher.match_artificial_analysis("openai/gpt-5.6-sol", near_models)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "1")

    def test_collision_disambiguated_by_provider_hint_via_model_creator(self):
        # Two different vendors' models normalize to the SAME slug ("sol") -- a naive
        # "first normalized match wins" would silently pick whichever is listed first.
        collision_models = [
            {"id": "1", "name": "Sol", "slug": "sol", "model_creator": {"name": "Xai"},
             "evaluations": {"artificial_analysis_coding_index": 10.0}},
            {"id": "2", "name": "Sol", "slug": "sol", "model_creator": {"name": "OpenAI"},
             "evaluations": {"artificial_analysis_coding_index": 90.0}},
        ]
        result = model_matcher.match_artificial_analysis(
            "openai/sol", collision_models, provider_hint="openai")
        self.assertEqual(result["id"], "2")

    def test_collision_with_no_provider_hint_returns_none_rather_than_guess(self):
        collision_models = [
            {"id": "1", "name": "Sol", "slug": "sol", "model_creator": {"name": "Xai"}},
            {"id": "2", "name": "Sol", "slug": "sol", "model_creator": {"name": "OpenAI"}},
        ]
        self.assertIsNone(model_matcher.match_artificial_analysis("sol", collision_models))

    def test_provider_hint_with_no_creator_match_falls_back_to_the_sole_name_match(self):
        # Only one normalized match exists at all -- provider_hint has nothing to disambiguate,
        # so the single match still wins (matches today's real-data behavior: most models have
        # no collision).
        result = model_matcher.match_artificial_analysis(
            "openai/gpt-5.6-sol", self.models, provider_hint="some-unrelated-vendor")
        self.assertIsNotNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestMatchModelsDev -k TestMatchArtificialAnalysis -v`
Expected: FAIL — `model_matcher` module not found.

- [ ] **Step 3: Implement**

```python
"""Matches a CLI-native model id (e.g. opencode's "openai/gpt-5.6-sol", codex's bare
"gpt-5.6-sol") against models.dev's and Artificial Analysis's own naming -- neither source
shares a clean id with how CLIs name their models (design spec 2026-09-02, Section 3), so
this is a best-effort normalize-AND-FUZZY-MATCH lookup, not a guaranteed key lookup (spec
Section 3/6: "matching against external sources' own slug/name/model_creator fields requires
a normalization + fuzzy-match step, not a direct key lookup" -- CRITICAL finding: an earlier
draft only ever did exact comparison on the normalized string, silently missing any source
whose id spells the same model slightly differently, e.g. an extra version-suffix token or a
minor punctuation/ordering difference that survives normalization). A model this still can't
match either source is the "unmatched" case the wizard (Task 8) escalates to one targeted
search + user confirmation, never guessed here."""
import difflib
import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# Fuzzy fallback only ever runs after an exact normalized match already failed. Both knobs
# exist to keep fuzzy matching conservative -- a false match silently attaches one model's
# real scores/pricing to a completely different one, which is worse than an unmatched
# candidate falling through to the wizard's one-targeted-search-plus-confirmation path.
_FUZZY_THRESHOLD = 0.82   # difflib.SequenceMatcher ratio floor -- below this, "no match".
_FUZZY_MARGIN = 0.05      # top candidate must beat the runner-up by at least this much.


def _normalize(text: str) -> str:
    return _NON_ALNUM.sub("", text.lower())


def bare_model_part(cli_model_id: str) -> str:
    """Public (Task 7's cli.py imports this rather than redefining it -- a MEDIUM finding,
    round-2 native-opus review, flagged the earlier draft's copy-pasted duplicate)."""
    return cli_model_id.split("/", 1)[1] if "/" in cli_model_id else cli_model_id


def _fuzzy_candidate_indices(target: str, normalized_options: list) -> list:
    """Token/character-similarity fallback (difflib.SequenceMatcher ratio) used ONLY after an
    exact normalized-string match found nothing. Returns every index whose ratio clears
    _FUZZY_THRESHOLD, sorted by ratio descending -- the caller applies the SAME
    collision-disambiguation (single-match / provider-hint) it already applies to exact
    matches, so fuzzy and exact matching share one collision-safety contract rather than two
    separate ones. An empty result means "no fuzzy match either" -- never a guess."""
    scored = [(difflib.SequenceMatcher(None, target, opt).ratio(), i)
              for i, opt in enumerate(normalized_options)]
    ranked = sorted(scored, reverse=True)
    if not ranked or ranked[0][0] < _FUZZY_THRESHOLD:
        return []
    # A close runner-up makes the top pick itself ambiguous -- surface ALL near-ties to the
    # caller (never silently pick the marginal "winner") so provider_hint gets a chance to
    # disambiguate them, exactly as it already does for a multi-way exact match.
    return [i for score, i in ranked if score >= _FUZZY_THRESHOLD and
            (ranked[0][0] - score) < _FUZZY_MARGIN]


def match_models_dev(cli_model_id: str, models_dev_data: dict) -> dict | None:
    """Three-step lookup: (1) if cli_model_id has a "<hint>/<model>" shape, try
    models_dev_data[hint]["models"][model] directly -- an exact hinted hit is always
    unambiguous and returned immediately, no collision to consider. (2) Only when step 1
    didn't hit, search every provider's models dict for an EXACT bare-id match (a CLI's own
    provider label is not guaranteed to equal models.dev's provider key -- e.g. opencode
    namespaces differently than models.dev does). (3) CRITICAL finding: only when step 2 finds
    NOTHING AT ALL does a fuzzy fallback run -- normalized-string similarity across every
    provider's every model id, via _fuzzy_candidate_indices. COLLISION-SAFE at every step: if
    more than one provider's model matches (exact OR fuzzy), that's ambiguous -- returns None
    rather than "whichever came first in dict-iteration order" (a naive first-match would
    silently attach one vendor's fields to a different vendor's model). Returns the matched
    model's own dict with a "provider" key added, or None."""
    bare = bare_model_part(cli_model_id)
    if "/" in cli_model_id:
        hint = cli_model_id.split("/", 1)[0]
        provider_entry = models_dev_data.get(hint)
        if provider_entry and bare in provider_entry.get("models", {}):
            return {**provider_entry["models"][bare], "provider": hint}
    pool = [(provider_key, model_id, model)
            for provider_key, provider_entry in models_dev_data.items()
            for model_id, model in provider_entry.get("models", {}).items()]
    matches = [(provider_key, model) for provider_key, model_id, model in pool if model_id == bare]
    if not matches:
        normalized_bare = _normalize(bare)
        normalized_ids = [_normalize(model_id) for _, model_id, _ in pool]
        matches = [(pool[i][0], pool[i][2]) for i in
                   _fuzzy_candidate_indices(normalized_bare, normalized_ids)]
    if len(matches) == 1:
        provider_key, model = matches[0]
        return {**model, "provider": provider_key}
    return None


def match_artificial_analysis(cli_model_id: str, aa_models: list,
                               provider_hint: str | None = None) -> dict | None:
    """Matches by normalized (lowercased, non-alnum-stripped) comparison against AA's own
    `slug` and `name` fields -- AA's slugs (e.g. "gpt-5-6-sol") don't line up character-for-
    character with a CLI's own id (e.g. "gpt-5.6-sol"), so exact string equality would miss
    real matches. CRITICAL finding: when NO exact normalized match exists, a fuzzy fallback
    (_fuzzy_candidate_indices, same conservative threshold/margin as match_models_dev's) runs
    against the same slug/name fields before giving up. COLLISION-SAFE at either stage: if
    matching (exact or fuzzy) yields more than one candidate, `provider_hint` (typically
    match_models_dev's own resolved "provider" for this same cli_model_id, passed by the
    caller) is used to pick the one whose `model_creator.name` normalizes to the same value --
    never "first match wins," which could silently attribute one vendor's scores/pricing to a
    different vendor's model. If more than one candidate remains ambiguous (no hint, or the
    hint doesn't disambiguate), returns None rather than guess -- an ambiguous match becomes
    the wizard's "unmatched" case (Task 8), same as no match at all. A SINGLE match (exact or
    fuzzy) always wins regardless of hint (the common case -- no collision to resolve)."""
    bare = _normalize(bare_model_part(cli_model_id))
    candidates = [m for m in aa_models
                  if _normalize(m.get("slug", "")) == bare or _normalize(m.get("name", "")) == bare]
    if not candidates:
        normalized_options = [_normalize(m.get("slug", "")) or _normalize(m.get("name", ""))
                               for m in aa_models]
        candidates = [aa_models[i] for i in _fuzzy_candidate_indices(bare, normalized_options)]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    if provider_hint:
        hint = _normalize(provider_hint)
        creator_matches = [m for m in candidates
                            if _normalize(m.get("model_creator", {}).get("name", "")) == hint]
        if len(creator_matches) == 1:
            return creator_matches[0]
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestMatchModelsDev -k TestMatchArtificialAnalysis -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add CLI-native-id matcher for models.dev/Artificial Analysis

Neither external source shares a clean id with how CLIs name their own
models -- match_models_dev tries a provider-hinted lookup then falls back
to a full-catalog bare-id search, returning None (not a guess) when that
fallback search matches under more than one provider; match_artificial_analysis
normalizes against slug/name and disambiguates a normalized collision using
model_creator evidence via provider_hint, returning None when it can't
either. Both now also fall back to a conservative fuzzy match (difflib
ratio, threshold+margin, same collision-safety rule as the exact path)
when the exact normalized comparison finds nothing -- the design's actual
normalization-and-fuzzy-match contract, not direct/near-exact equality
alone. A model matching neither source, or matching either one
ambiguously (exact or fuzzy), is the wizard's "unmatched" case (Task 8),
never guessed here.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 7: `fetch-model-catalog` + `confirm-catalog-entry` + `apply-heuristic-correction` CLI subcommands

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `model_sources.fetch_models_dev`/`fetch_artificial_analysis` (Task 4, now `(data, ok)`-returning), `local_secrets.load_secret` (Task 3), `model_matcher.match_models_dev`/`match_artificial_analysis` (Task 6, collision-safe via `provider_hint`), `model_heuristics.infer_is_router`/`infer_batch_mode`/`infer_fallback_quota` (Task 5), `model_catalog.cache_catalog_path`/`canonical_key`/`merge_catalog_entry`/`CATALOG_TTL_SECONDS` (Task 2), `ai_kit_spec.config_io.cfg_resolve` (existing — reads already-registered `review-spec.toml` reviewers, the exact candidate source for single-provider CLIs), `ai_kit_spec.cache.cache_read_json`/`cache_write_json`/`cache_is_stale` (existing).
- Produces: `build_model_catalog(discovered_models: list, models_dev_data: dict, models_dev_ok: bool, aa_models: list, aa_ok: bool, existing_catalog: dict) -> tuple` — pure orchestration living directly in `cli.py` (thin glue over Tasks 1-6, not new domain logic; the subcommand below is its only real caller, called in tests as `cli.build_model_catalog(...)` — no separate `model_catalog_build` module, see the note in Step 2). Returns `(new_catalog, rejections: list[str], unmatched: list[dict])`. Each `unmatched` entry carries `cli`, `model_id`, `provider`, `key`, AND the locally-inferred `is_router`/`batch_mode`/`fallback_quota` heuristic fields (CRITICAL finding: these must be computed and surfaced for every candidate the wizard confirms, unmatched ones included — never only for already-matched ones). **`unmatched` candidates are NEVER added to `new_catalog`** — they matched neither external source AND have no existing catalog entry, so per spec §4/§8 they require one targeted search + explicit user confirmation (Task 8) before they're ever persisted. The `fetch-model-catalog` subcommand wires real I/O around it (reads the runtimes snapshot AND the resolved `review-spec.toml` for single-provider-CLI candidates, fetches both sources respecting `--if-stale` for NETWORK CALLS ONLY — candidate discovery/reconciliation always runs, every invocation, TTL never gates it — writes the result, prints rejections/unmatched, and prints the FULL reconciled `discovered` candidate list so Task 8's ranking step never has to recompute a partial one). A new `confirm-catalog-entry` subcommand is the ONLY way an unmatched candidate is ever persisted — it takes a wizard-confirmed entry (Task 8) and calls `merge_catalog_entry` directly. A third new subcommand, `apply-heuristic-correction`, is the ONLY way a user's is_router/batch_mode/fallback_quota correction is ever persisted — it calls `model_catalog.apply_heuristic_corrections` (Task 2) through the same atomic `cache_write_json`, never a raw `json.dump`.

- [ ] **Step 1: Write the failing tests for `build_model_catalog`**

Add to `tests/test_ai_kit_spec.py` (calling `cli.build_model_catalog` — this lives in `cli.py`
itself per the Interfaces note above, so no new bare-module import is needed; `cli` is already
in the existing bare-module-import block):

```python
class TestBuildModelCatalog(unittest.TestCase):
    def test_matched_candidate_is_enriched_and_added(self):
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        models_dev_data = {"openai": {"models": {"gpt-5.6-sol": {
            "id": "gpt-5.6-sol", "tool_call": True, "structured_output": True,
            "limit": {"context": 400000, "output": 128000},
            "cost": {"input": 3.5, "output": 14.0}}}}}
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])
        self.assertIn("openai/gpt-5.6-sol", catalog)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["provider"], "openai")
        self.assertTrue(entry["source"]["models_dev"])
        self.assertFalse(entry["source"]["artificial_analysis"])
        self.assertIn("opencode", entry["runtimes"])

    def test_unmatched_new_candidate_is_reported_but_never_persisted(self):
        # CRITICAL: an unmatched, never-before-seen candidate must NOT land in the catalog
        # automatically -- it needs research + user confirmation first (Task 8's wizard).
        discovered = [{"cli": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, rejections, unmatched = cli.build_model_catalog(discovered, {}, True, [], True, {})
        self.assertEqual(rejections, [])
        self.assertNotIn("vendor/totally-unknown", catalog)
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0]["model_id"], "vendor/totally-unknown")
        self.assertEqual(unmatched[0]["cli"], "opencode")

    def test_unmatched_candidate_carries_heuristic_fields_for_wizard_confirmation(self):
        # CRITICAL finding: an earlier draft returned unmatched candidates with NO heuristic
        # fields at all, and its own confirmation-payload test looked them up in `catalog`
        # (a KeyError, since unmatched entries are never added to catalog) -- both bugs fixed
        # here: heuristics are computed for unmatched candidates too, and returned inline on
        # the unmatched dict itself, never via a catalog lookup that can't succeed.
        discovered = [{"cli": "opencode", "model_id": "router-env/totally-unknown"}]
        _, _, unmatched = cli.build_model_catalog(discovered, {}, True, [], True, {})
        self.assertEqual(len(unmatched), 1)
        self.assertTrue(unmatched[0]["is_router"])
        self.assertTrue(unmatched[0]["fallback_quota"])
        self.assertIn("batch_mode", unmatched[0])

    def test_already_confirmed_manual_entry_is_not_re_reported_as_unmatched(self):
        # A candidate already persisted (via confirm-catalog-entry, a previous run) is known --
        # re-running discovery on it must refresh its runtimes, not flag it as needing
        # confirmation again every single run.
        existing = {"vendor/totally-unknown": {"provider": "vendor", "runtimes": {},
                                                 "source": {"manual": True}, "confidence": "low",
                                                 "last_verified": "2026-08-01"}}
        discovered = [{"cli": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, {}, True, [], True, existing)
        self.assertEqual(unmatched, [])
        self.assertIn("opencode", catalog["vendor/totally-unknown"]["runtimes"])
        self.assertEqual(catalog["vendor/totally-unknown"]["confidence"], "low")

    def test_router_batch_and_fallback_quota_heuristics_are_applied(self):
        # HIGH finding: a candidate that matches NEITHER external source is, by this function's
        # own contract, never added to `catalog` -- it goes to `unmatched` instead (see the
        # dedicated unmatched-candidate tests above). Asserting on catalog[key] for such a
        # candidate is a KeyError by construction. Give this candidate a real models.dev match
        # so it actually lands in `catalog`, exercising the heuristics on the MATCHED path
        # (the unmatched path's own heuristic fields are already covered separately, above).
        discovered = [{"cli": "opencode", "model_id": "router-env/my-plan-review"}]
        models_dev_data = {"router-env": {"models": {"my-plan-review": {"id": "my-plan-review"}}}}
        catalog, _, unmatched = cli.build_model_catalog(discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["router-env/my-plan-review"]
        self.assertTrue(entry["is_router"])
        self.assertTrue(entry["fallback_quota"])

    def test_existing_catalog_entries_are_preserved_when_not_rediscovered(self):
        existing = {"stale/model": {"provider": "p", "runtimes": {"c": {}}, "source": {},
                                     "confidence": "high", "last_verified": "2026-01-01"}}
        catalog, _, _ = cli.build_model_catalog([], {}, True, [], True, existing)
        self.assertIn("stale/model", catalog)

    def test_two_clis_reporting_the_same_model_merge_into_one_canonical_entry(self):
        # HIGH finding: catalog identity must not lose runtime mappings across CLIs.
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"},
                      {"cli": "codex", "model_id": "gpt-5.6-sol"}]
        models_dev_data = {"openai": {"models": {"gpt-5.6-sol": {"id": "gpt-5.6-sol"}}}}
        catalog, _, _ = cli.build_model_catalog(discovered, models_dev_data, True, [], True, {})
        self.assertEqual(len(catalog), 1)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertIn("opencode", entry["runtimes"])
        self.assertIn("codex", entry["runtimes"])

    def test_models_dev_fetch_failure_preserves_cached_models_dev_fields(self):
        # CRITICAL finding: a network failure must never overwrite already-cached enrichment.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": False}, "confidence": "high",
            "last_verified": "2026-08-01", "tool_calling": True,
            "pricing": {"input_per_1m": 3.5, "output_per_1m": 14.0}}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, False, [], True, existing)  # models_dev_ok=False: source is DOWN
        self.assertEqual(unmatched, [])
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertTrue(entry["tool_calling"])
        self.assertEqual(entry["pricing"]["input_per_1m"], 3.5)
        self.assertTrue(entry["source"]["models_dev"])  # still true -- not silently downgraded

    def test_total_source_failure_leaves_a_cached_entry_completely_unchanged_except_runtimes(self):
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01", "scores": {"intelligence_index": 91.0}}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, False, [], False, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)
        self.assertEqual(entry["confidence"], "high")
        self.assertEqual(entry["last_verified"], "2026-08-01")  # unchanged -- nothing re-verified

    def test_artificial_analysis_pricing_fills_in_when_models_dev_has_no_match(self):
        # HIGH finding: AA pricing must not be discarded when models.dev has no match.
        aa_models = [{"id": "1", "slug": "totally-unknown", "name": "Totally Unknown",
                      "model_creator": {"name": "Vendor"},
                      "pricing": {"price_1m_input_tokens": 2.0, "price_1m_output_tokens": 8.0}}]
        discovered = [{"cli": "opencode", "model_id": "vendor/totally-unknown"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, aa_models, True, {})
        entry = catalog["vendor/totally-unknown"]
        self.assertEqual(entry["pricing"]["input_per_1m"], 2.0)
        self.assertEqual(entry["pricing"]["output_per_1m"], 8.0)

    def test_models_dev_fetch_failure_preserves_cached_runtime_ctx_window(self):
        # CRITICAL finding: a models.dev outage must not blank out an already-cached
        # runtime's ctx_window by unconditionally recomputing it from a (necessarily absent)
        # md_match -- that silently corrupts ranking's context_window axis.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai",
            "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}},
            "source": {"models_dev": True, "artificial_analysis": False}, "confidence": "high",
            "last_verified": "2026-08-01"}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, False, [], True, existing)
        self.assertEqual(
            catalog["openai/gpt-5.6-sol"]["runtimes"]["opencode"]["ctx_window"], 400000)

    def test_missing_api_key_preserves_cached_aa_fields_rather_than_wiping_them(self):
        # CRITICAL finding: no API key configured (aa_ok=True, aa_models=[] per Task 4's own
        # "deliberately skipped is not a failure" contract) must NOT be treated identically to
        # "AA was queried and genuinely found no match" -- the CLI wiring in Step 5 passes
        # aa_ok=False to THIS function whenever no key was available, specifically so this
        # preserve-not-wipe path runs; this test exercises that resulting contract directly.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0},
            "tokens_per_sec": 142.3}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, [], False, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)
        self.assertEqual(entry["tokens_per_sec"], 142.3)
        self.assertTrue(entry["source"]["artificial_analysis"])

    def test_genuine_no_match_with_a_working_key_clears_aa_fields_and_flips_source_false(self):
        # The OTHER transition (contrast with the no-key test above): AA genuinely queried,
        # genuinely found no match for THIS candidate -- fields and provenance are cleared
        # together, consistently, not left stale.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0}}}
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, [], True, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertNotIn("scores", entry)
        self.assertFalse(entry["source"]["artificial_analysis"])

    def test_partial_aa_match_with_no_performance_data_clears_stale_tokens_per_sec(self):
        # MEDIUM finding (round-4): a PARTIAL match -- AA matched this candidate this run
        # (source.artificial_analysis is about to read True again) but this match's own
        # payload has no performance/median_output_tokens_per_second -- must clear a stale
        # cached tokens_per_sec, exactly like the full no-match case above. An earlier draft
        # only ever set "tokens_per_sec" in the returned fields dict when perf data existed,
        # silently retaining the old value via merge_catalog_entry's omission-preserves rule
        # even though this run's genuine query found nothing for it.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai", "runtimes": {"opencode": {"model_id": "openai/gpt-5.6-sol"}},
            "source": {"models_dev": True, "artificial_analysis": True}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0, "coding_index": 88.0, "agentic_index": 84.0},
            "tokens_per_sec": 142.3}}
        aa_models = [{"id": "1", "slug": "gpt-5-6-sol", "name": "GPT-5.6 Sol",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 91.0}}]
        # no "performance" key at all -- a genuine partial match
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, aa_models, True, existing)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertNotIn("tokens_per_sec", entry)
        self.assertTrue(entry["source"]["artificial_analysis"])

    def test_heuristic_correction_survives_a_later_catalog_rebuild(self):
        # HIGH finding: every refresh recomputed is_router/batch_mode/fallback_quota fresh
        # from the naming heuristic, silently overwriting a user's prior correction
        # (apply_heuristic_corrections, Task 2) on the very next run.
        existing = {"router-env/my-plan-review": {
            "provider": "router-env", "runtimes": {"opencode": {"model_id": "router-env/my-plan-review"}},
            "source": {}, "confidence": "low", "last_verified": "2026-08-01",
            "is_router": False}}  # user corrected this away from the heuristic default (True)
        discovered = [{"cli": "opencode", "model_id": "router-env/my-plan-review"}]
        catalog, _, _ = cli.build_model_catalog(discovered, {}, True, [], True, existing)
        self.assertFalse(catalog["router-env/my-plan-review"]["is_router"])

    def test_bare_model_matched_only_via_artificial_analysis_derives_vendor_from_model_creator(self):
        # HIGH finding: a bare model id (codex-style, no "<vendor>/" prefix) with NO
        # models.dev match must not become its own vendor ("gpt-5.6-sol/gpt-5.6-sol") just
        # because model_id.split("/", 1)[0] has nothing to split -- when Artificial Analysis
        # matched, its model_creator is the real vendor signal.
        aa_models = [{"id": "1", "slug": "gpt-5-6-sol", "name": "GPT-5.6 Sol",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 91.0}}]
        discovered = [{"cli": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(discovered, {}, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        self.assertIn("openai/gpt-5.6-sol", catalog)
        self.assertEqual(catalog["openai/gpt-5.6-sol"]["provider"], "openai")

    def test_discovered_candidates_include_single_provider_and_extra_candidates(self):
        # CRITICAL cross-doc finding: Task 8's ranking step must be able to reconstruct the
        # FULL candidate set (not just runtimes-with-a-"models"-array) without recomputing
        # cfg_resolve/--extra-candidate parsing itself -- build_model_catalog is given the
        # already-fully-reconciled `discovered_models` list by its caller (the CLI command,
        # Step 5) and this test only confirms it treats every one of them uniformly,
        # regardless of whether the candidate came from a runtimes snapshot, review-spec.toml,
        # or --extra-candidate -- there's no special-casing by origin inside this function.
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5.6-sol"},
                      {"cli": "codex", "model_id": "gpt-5.6-alt"}]  # e.g. from --extra-candidate
        catalog, _, unmatched = cli.build_model_catalog(discovered, {}, True, [], True, {})
        self.assertEqual({u["cli"] for u in unmatched}, {"opencode", "codex"})

    def test_bare_id_with_both_sources_unavailable_recovers_key_from_existing_catalog(self):
        # CRITICAL/HIGH fix (round-2 native-opus review): this is the `--if-stale` DEFAULT
        # path -- both sources skipped (models_dev_ok=False, aa_ok=False), a bare CLI-native
        # id (codex-style, no "<vendor>/" prefix) that was already matched and persisted on a
        # PRIOR run. Before the fix, this fell through to `provider = model_id`, minting an
        # unstable "gpt-5.6-sol/gpt-5.6-sol" key every such run -- never matching the real
        # cached entry, permanently orphaning it, and reclassifying an already-known model as
        # `unmatched` (needing manual research) on every single --if-stale run.
        existing = {"openai/gpt-5.6-sol": {
            "provider": "openai",
            "runtimes": {"codex": {"model_id": "gpt-5.6-sol", "ctx_window": 400000}},
            "source": {"models_dev": True, "artificial_analysis": False}, "confidence": "high",
            "last_verified": "2026-08-01",
            "scores": {"intelligence_index": 91.0}}}
        discovered = [{"cli": "codex", "model_id": "gpt-5.6-sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, False, [], False, existing)
        self.assertEqual(unmatched, [])
        self.assertEqual(len(catalog), 1)
        self.assertIn("openai/gpt-5.6-sol", catalog)
        self.assertNotIn("gpt-5.6-sol/gpt-5.6-sol", catalog)
        entry = catalog["openai/gpt-5.6-sol"]
        self.assertEqual(entry["provider"], "openai")
        self.assertEqual(entry["scores"]["intelligence_index"], 91.0)  # preserved, not wiped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestBuildModelCatalog -v`
Expected: FAIL — `AttributeError: module 'ai_kit_spec.cli' has no attribute 'build_model_catalog'`.
(This confirms the fix for the earlier draft's broken `model_catalog_build.build_model_catalog(...)`
reference, which raised `ModuleNotFoundError` — no such module was ever defined. The function
lives in `cli.py` and is called `cli.build_model_catalog(...)` everywhere, including here.)

- [ ] **Step 3: Implement `build_model_catalog` in `cli.py`**

`cli.py` does NOT have a single umbrella `from ai_kit_spec import (...)` block — every module
it uses gets its own direct `from ai_kit_spec.<module> import (...)` block (confirmed:
`rg -n "^from ai_kit_spec" skills/ai-kit-spec-review/ai_kit_spec/cli.py` shows one block per
module — `cache`, `commands`, `config_io`, `detection`, `execute_dispatch`, `quota`,
`review_reports`, ... — never a bare `from ai_kit_spec import`). Add three NEW blocks in that
same style, alphabetically among the existing ones (between the existing `execute_dispatch`
and `quota` blocks), plus a plain `re` import next to the existing `import json`/`import os`/
etc. block at the very top of the file:

```python
import re          # add alongside the existing import json / import os / import shutil / ...
import time         # new -- not previously imported in cli.py

from ai_kit_spec.model_catalog import canonical_key, merge_catalog_entry
from ai_kit_spec.model_heuristics import infer_batch_mode, infer_fallback_quota, infer_is_router
from ai_kit_spec.model_matcher import bare_model_part, match_artificial_analysis, match_models_dev
```

(`bare_model_part` is imported from `model_matcher` — Task 6 already defines this exact
one-line split as a public function specifically so `cli.py` never redefines its own copy; a
MEDIUM finding, round-2 native-opus review, caught an earlier draft doing exactly that.)

Then, further down in the file (anywhere above `main()` is fine — this repo's existing
convention, e.g. `dispatch_execute`, places helper functions between the imports and `main()`):

```python
def _find_existing_key_for_runtime(existing_catalog: dict, cli_name: str, model_id: str) -> str | None:
    """CRITICAL/HIGH fix (round-2 native-opus review): a bare CLI-native id (no "<vendor>/"
    prefix, e.g. codex's "gpt-5.6-sol") carries no provider signal of its own. When BOTH
    external sources are unavailable this run -- most commonly `--if-stale` skipping the
    network fetch entirely, which is the wizard's own DEFAULT path, not an edge case -- the
    only way to recover this candidate's real vendor/model key is to look up which existing
    catalog entry already claims this exact (cli, model_id) runtime pairing. Without this
    lookup, build_model_catalog fell through to `provider = model_id`, minting an unstable
    "gpt-5.6-sol/gpt-5.6-sol" key every such run: it never matched the real
    "openai/gpt-5.6-sol" entry (permanently orphaning it and duplicating the catalog), AND it
    reclassified an already-known, already-enriched model as a brand-new `unmatched`
    candidate needing manual research + user confirmation on every single `--if-stale` run --
    exactly the per-model WebSearch pattern this design exists to eliminate."""
    for existing_key, existing_entry in existing_catalog.items():
        rt = existing_entry.get("runtimes", {}).get(cli_name)
        if isinstance(rt, dict) and rt.get("model_id") == model_id:
            return existing_key
    return None


def _slugify(name: str) -> str:
    """Best-effort vendor-name -> slug, used ONLY to derive a canonical `provider` when a bare
    (no "<vendor>/" prefix) model id matched Artificial Analysis but NOT models.dev -- AA's own
    `model_creator.name` ("OpenAI", "xAI") is free text, never a models.dev provider key, so it
    needs normalizing before it can become half of a canonical_key(). Lowercases and collapses
    every run of non-alphanumeric characters to a single hyphen."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _infer_heuristics(provider: str, model_id: str) -> dict:
    """Local naming heuristics (Task 5) for a single candidate -- factored out so both the
    matched-entry path AND the unmatched-candidate path (CRITICAL finding: an earlier draft
    computed these ONLY for matched entries, leaving the wizard's unmatched-candidate
    confirmation payload with no heuristic fields to show/confirm at all) compute them
    identically."""
    return {
        "is_router": infer_is_router(provider) or infer_is_router(model_id),
        "batch_mode": infer_batch_mode(model_id),
        "fallback_quota": infer_fallback_quota(provider) or infer_fallback_quota(model_id),
    }


def _preserved_or_fresh_md_fields(md_match: dict | None, models_dev_ok: bool,
                                   existing_entry: dict | None) -> dict:
    """CRITICAL: a models.dev fetch failure must never overwrite already-cached models.dev-
    sourced fields. If the source is down (models_dev_ok=False), copy whatever the existing
    entry already had for these fields verbatim (a key simply absent here is left absent from
    the returned dict, which merge_catalog_entry then treats as "preserve" -- correct, since a
    down source made no claim either way); only ever compute fresh values when the source
    actually answered this run.

    CRITICAL finding (Cross-Document Consistency / fresh-source no-match): when the source WAS
    queried genuinely this run (models_dev_ok=True) but found no match for this candidate
    (md_match is None), any fields it previously owned are now stale under a provenance that
    is about to flip to source.models_dev=False -- returning explicit None (not omission) for
    each is what tells merge_catalog_entry's clear-on-None contract to actually drop them,
    instead of silently retaining last run's values via plain dict-spread. `pricing` is
    deliberately NOT included here -- build_model_catalog owns pricing's combined
    models.dev-or-Artificial-Analysis fallback logic itself, since either source can supply it."""
    if not models_dev_ok:
        existing_entry = existing_entry or {}
        return {k: existing_entry[k] for k in
                ("tool_calling", "structured_output", "max_output_tokens")
                if k in existing_entry}
    if not md_match:
        return {"tool_calling": None, "structured_output": None, "max_output_tokens": None}
    return {"tool_calling": md_match.get("tool_call"),
            "structured_output": md_match.get("structured_output"),
            "max_output_tokens": md_match.get("limit", {}).get("output")}


def _preserved_or_fresh_ctx_window(md_match: dict | None, models_dev_ok: bool,
                                    existing_entry: dict | None, cli_name: str):
    """CRITICAL: same preserve-on-source-down contract as _preserved_or_fresh_md_fields, but for
    a RUNTIME-level field (ctx_window lives inside runtimes[cli_name], not at the entry's top
    level) -- an earlier draft always recomputed this from `md_match`, which is unconditionally
    None whenever models_dev_ok is False, silently blanking an already-cached runtime's
    ctx_window on every models.dev outage."""
    if not models_dev_ok:
        existing_entry = existing_entry or {}
        return existing_entry.get("runtimes", {}).get(cli_name, {}).get("ctx_window")
    return (md_match or {}).get("limit", {}).get("context")


def _preserved_or_fresh_aa_fields(aa_match: dict | None, aa_ok: bool,
                                   existing_entry: dict | None) -> dict:
    """Same contract as _preserved_or_fresh_md_fields, for Artificial Analysis's fields.
    CRITICAL: `aa_ok` here means "this run's AA field values are trustworthy, use them as-is"
    -- the CALLER (fetch-model-catalog's command body, Step 5 below) is responsible for passing
    `aa_ok=False` not only on a real fetch failure but ALSO when no API key was configured at
    all (Task 4's fetch_artificial_analysis returns `ok=True` for "deliberately skipped," which
    is correct for that module's own contract, but wrong to treat as "AA was queried and found
    nothing" here -- those are different transitions and must not collapse into one)."""
    if not aa_ok:
        existing_entry = existing_entry or {}
        return {k: existing_entry[k] for k in ("scores", "tokens_per_sec") if k in existing_entry}
    if not aa_match:
        # CRITICAL finding (fresh-source no-match): aa_ok=True here means Artificial Analysis
        # WAS queried for real this run (the caller already collapsed "no API key" into
        # aa_ok=False, see this function's own docstring below) and genuinely found no match --
        # any scores/tokens_per_sec it previously supplied are now stale under a provenance
        # about to flip to source.artificial_analysis=False. Explicit None (not omission) is
        # what tells merge_catalog_entry's clear-on-None contract to actually drop them.
        return {"scores": None, "tokens_per_sec": None}
    evaluations = aa_match.get("evaluations", {})
    fields = {"scores": {
        "intelligence_index": evaluations.get("artificial_analysis_intelligence_index"),
        "coding_index": evaluations.get("artificial_analysis_coding_index"),
        "agentic_index": evaluations.get("artificial_analysis_agentic_index"),
    }}
    # MEDIUM finding (round-4): a genuine PARTIAL match -- aa_match exists (AA was queried and
    # matched this candidate this run) but this specific match's own performance payload has
    # no median_output_tokens_per_second -- must clear a stale cached tokens_per_sec the same
    # way a full no-match already does above, not silently retain it via omission.
    # merge_catalog_entry only preserves a field genuinely ABSENT from this dict; explicit None
    # is what tells it "queried, no value this run" and to actually drop it. An earlier draft
    # only ever set this key when a fresh value existed, leaving a stale tokens_per_sec
    # untouched under a source.artificial_analysis flag that's about to read True again --
    # the same staleness bug class the clear-on-None contract exists to prevent.
    perf = aa_match.get("performance", {})
    fields["tokens_per_sec"] = perf.get("median_output_tokens_per_second")
    pricing = aa_match.get("pricing", {})
    if pricing.get("price_1m_input_tokens") is not None:
        fields["aa_pricing"] = {"input_per_1m": pricing.get("price_1m_input_tokens"),
                                 "output_per_1m": pricing.get("price_1m_output_tokens")}
    return fields


def build_model_catalog(discovered_models: list, models_dev_data: dict, models_dev_ok: bool,
                         aa_models: list, aa_ok: bool, existing_catalog: dict) -> tuple:
    """Pure orchestration (design spec 2026-09-02, Section 4 steps 2-5): match each discovered
    {"cli", "model_id"} candidate against both external sources, enrich deterministically from
    whatever matched (or preserve cached fields when a source is down -- see the _preserved_
    or_fresh_* helpers), apply local naming heuristics for is_router/batch_mode/fallback_quota
    ONLY on first discovery (a value already present on `existing_entry` is a prior heuristic
    default or a user's own correction -- HIGH finding: every later rebuild must preserve it,
    never silently recompute over it), and merge into `existing_catalog` under a CANONICAL
    vendor/model key (model_catalog.canonical_key) so two CLIs reporting the same real model
    under different raw ids collapse into one entry with both runtimes merged in. A bare id
    (no "<vendor>/" prefix) with NEITHER source matched this run first tries
    `_find_existing_key_for_runtime` against `existing_catalog` before ever falling back to
    minting a fresh key (CRITICAL/HIGH fix, round-2 native-opus review) -- this is what keeps
    the `--if-stale` default path from orphaning an already-known model under an unstable
    "model_id/model_id" key and reclassifying it as needing manual research every run.
    Entries for candidates NOT in `discovered_models` this run are preserved untouched. Returns
    (new_catalog, rejections, unmatched): `unmatched` lists brand-new candidates that matched
    NEITHER source and have no prior catalog entry -- these are NEVER added to new_catalog here
    (spec Section 4/8: research + user confirmation must happen first, Task 8's wizard); each
    unmatched entry ALSO carries its own is_router/batch_mode/fallback_quota heuristic fields
    (CRITICAL finding: these must exist for the wizard's confirmation payload even though the
    candidate isn't in the catalog yet) computed via the same `_infer_heuristics` the matched
    path uses. A bare model id (no "<vendor>/" prefix, e.g. codex's own naming) that matched
    Artificial Analysis but NOT models.dev derives its `provider` from AA's `model_creator.name`
    (HIGH finding: it must never become its own vendor by falling through to the model id
    itself). Artificial Analysis pricing fills in when models.dev has no match for that
    candidate (HIGH finding: AA data must not be discarded just because models.dev didn't
    match)."""
    catalog = dict(existing_catalog)
    rejections = []
    unmatched = []
    today = time.strftime("%Y-%m-%d")
    for candidate in discovered_models:
        model_id = candidate["model_id"]
        cli_name = candidate["cli"]
        md_match = match_models_dev(model_id, models_dev_data) if models_dev_ok else None
        provider_hint = (md_match or {}).get("provider") or (
            model_id.split("/", 1)[0] if "/" in model_id else None)
        aa_match = (match_artificial_analysis(model_id, aa_models, provider_hint=provider_hint)
                    if aa_ok else None)
        existing_key = _find_existing_key_for_runtime(existing_catalog, cli_name, model_id)
        if md_match:
            provider = md_match["provider"]
        elif provider_hint:
            provider = provider_hint
        elif aa_match and aa_match.get("model_creator", {}).get("name"):
            provider = _slugify(aa_match["model_creator"]["name"])
        elif existing_key:
            # CRITICAL/HIGH fix: neither source matched this run (most commonly both were
            # skipped by `--if-stale`) and the raw id carries no vendor prefix -- recover the
            # real provider/key from the catalog entry that already claims this exact
            # (cli, model_id) runtime, instead of minting an unstable "model_id/model_id" key
            # that would orphan the real entry and misclassify it as unmatched every run.
            provider = existing_catalog[existing_key]["provider"]
        else:
            provider = model_id  # last resort: genuinely no vendor signal from any source
        key = existing_key or canonical_key(provider, bare_model_part(model_id))
        existing_entry = catalog.get(key)

        if md_match is None and aa_match is None and existing_entry is None:
            unmatched.append({"cli": cli_name, "model_id": model_id, "provider": provider,
                               "key": key, **_infer_heuristics(provider, model_id)})
            continue

        md_fields = _preserved_or_fresh_md_fields(md_match, models_dev_ok, existing_entry)
        aa_fields = _preserved_or_fresh_aa_fields(aa_match, aa_ok, existing_entry)
        aa_pricing = aa_fields.pop("aa_pricing", None)
        # CRITICAL finding (fresh-source no-match / pricing can come from EITHER source): a
        # models.dev match's own cost fields aren't returned via _preserved_or_fresh_md_fields
        # (pricing is combined here, not per-source), so recompute them directly from md_match.
        md_cost = (md_match or {}).get("cost", {}) if models_dev_ok and md_match else {}
        md_pricing = ({"input_per_1m": md_cost.get("input"), "output_per_1m": md_cost.get("output")}
                      if md_cost else None)
        pricing = md_pricing or aa_pricing
        clear_pricing = False
        if pricing is None:
            if not models_dev_ok or not aa_ok:
                # At least one source is down/unconfigured this run -- its silence says nothing
                # about whether pricing is still correct, so preserve whatever's cached (leave
                # the "pricing" key out of `entry` entirely below -- omission preserves).
                pricing = (existing_entry or {}).get("pricing")
            elif (existing_entry or {}).get("pricing") is not None:
                # CRITICAL finding: BOTH sources were genuinely queried this run and NEITHER
                # matched -- cached pricing is now stale under a provenance about to flip both
                # source.* flags to False. clear_pricing signals an explicit None below, which
                # merge_catalog_entry's clear-on-None contract then actually drops.
                clear_pricing = True
        ctx_window = _preserved_or_fresh_ctx_window(md_match, models_dev_ok, existing_entry,
                                                      cli_name)
        # MEDIUM finding: this used to reimplement _infer_heuristics' own three-line body
        # inline (a second, separately-maintained copy of the exact same heuristic calls),
        # contradicting that function's own docstring claim that both paths call it. Calling
        # it here instead removes the duplication -- an existing cached value still wins over
        # a freshly-inferred one wherever present, unchanged from before.
        heuristics = {
            field: (existing_entry or {}).get(field, inferred)
            for field, inferred in _infer_heuristics(provider, model_id).items()
        }

        matched_this_run = md_match is not None or aa_match is not None
        entry = {
            "provider": (existing_entry or {}).get("provider", provider),
            "runtimes": {cli_name: {"model_id": model_id, "ctx_window": ctx_window}},
            **heuristics,
            "source": {
                "models_dev": (md_match is not None) if models_dev_ok
                              else (existing_entry or {}).get("source", {}).get("models_dev", False),
                "artificial_analysis": (aa_match is not None) if aa_ok
                              else (existing_entry or {}).get("source", {}).get(
                                  "artificial_analysis", False),
                "manual": (existing_entry or {}).get("source", {}).get("manual", False),
            },
            "confidence": "high" if matched_this_run else (existing_entry or {}).get(
                "confidence", "low"),
            "last_verified": today if matched_this_run else (existing_entry or {}).get(
                "last_verified", today),
            **md_fields,
        }
        if pricing:
            entry["pricing"] = pricing
        elif clear_pricing:
            entry["pricing"] = None    # explicit clear signal -- see merge_catalog_entry
        entry.update(aa_fields)
        catalog, reason = merge_catalog_entry(catalog, key, entry)
        if reason:
            rejections.append(reason)
    return catalog, rejections, unmatched
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestBuildModelCatalog -v`
Expected: PASS.

- [ ] **Step 5: Wire the `fetch-model-catalog`, `confirm-catalog-entry`, and `apply-heuristic-correction` subcommands**

In `cli.py`'s `main()`, add the subparsers next to `p_detect` (`detect-runtimes`):

```python
    p_catalog = sub.add_parser("fetch-model-catalog")
    p_catalog.add_argument("--runtimes-json", required=True,
                            help="path to a detect-runtimes snapshot (as saved via --save/--if-stale)")
    p_catalog.add_argument("--catalog-path", required=True)
    p_catalog.add_argument("--cwd", default=None,
                            help="for resolving review-spec.toml's already-registered "
                                 "single-provider-CLI models; defaults to the process cwd")
    p_catalog.add_argument(
        "--extra-candidate", action="append", default=[], metavar="CLI:MODEL_ID",
        help="repeatable; a wizard-typed single-provider-CLI candidate not yet in "
             "review-spec.toml (e.g. a first-time codex/grok setup with nothing registered "
             "yet) -- still goes through the same matching/enrichment path as anything else.")
    p_catalog.add_argument(
        "--if-stale", action="store_true",
        help="gate NETWORK CALLS ONLY: when --catalog-path exists and is fresher than "
             "CATALOG_TTL_SECONDS, skip fetching models.dev/Artificial Analysis and reuse "
             "cached fields for every already-known candidate -- candidate DISCOVERY/"
             "RECONCILIATION (runtimes snapshot + registered single-provider-CLI models + "
             "--extra-candidate) always runs regardless of this flag, every invocation, so a "
             "brand-new candidate is never silently missed just because the catalog is fresh "
             "(CRITICAL finding: an earlier draft exited before even building the candidate "
             "list when fresh, which is wrong -- freshness should only ever skip re-fetching, "
             "never skip reconciling what's newly installed).")
    # MEDIUM finding: spec Section 8 names a `fetch-model-catalog --force` flag for manual
    # refresh. This plan deliberately does NOT add a separate `--force` flag: the command's
    # default behavior (no flag at all) already re-fetches both external sources unconditionally
    # -- `skip_fetch` below is only ever true when `--if-stale` is explicitly passed AND the
    # cache is fresh. So "run without `--if-stale`" IS the manual-refresh/force path the spec
    # names; a dedicated `--force` flag would be a same-effect alias, not new behavior, and is
    # intentionally omitted here rather than left as a silent, unrecorded gap.

    p_confirm = sub.add_parser("confirm-catalog-entry")
    p_confirm.add_argument("--catalog-path", required=True)
    p_confirm.add_argument("--entry-json", required=True,
                            help="path to a temp JSON file: {\"model_id\": ..., \"entry\": {...}} "
                                 "-- same JSON-temp-file convention as render-toml's --json-config")

    p_apply_correction = sub.add_parser("apply-heuristic-correction")
    p_apply_correction.add_argument("--catalog-path", required=True)
    p_apply_correction.add_argument("--model-id", required=True)
    p_apply_correction.add_argument(
        "--corrections-json", required=True,
        help="path to a temp JSON file: a flat object of any subset of "
             "is_router/batch_mode/fallback_quota, e.g. {\"is_router\": false}")
```

And the command bodies, alongside the other `if args.command == "...":` blocks. **`--if-stale`
gates ONLY the two network-fetch calls** (HIGH-severity fix from round-2 review) — candidate
discovery, single-provider-CLI reconciliation, and `--extra-candidate` parsing all run
unconditionally, every invocation, so `build_model_catalog` always sees the full, current
candidate set and can surface a brand-new one via `unmatched` even on a fresh-cache run (it
just won't have fresh external-source data to match against on that run — whatever's already
cached for existing entries is preserved via the `models_dev_ok=False`/`aa_ok=False`-when-
skipped path, same contract as a real fetch failure):

**HIGH finding: `env = dict(os.environ)` inlined directly inside this command body is
non-injectable** — this repo's own convention for I/O this design leans on elsewhere is a real
default with an override hook (`which_fn=shutil.which`, `run_fn=subprocess.run` on `main()`
itself; `fetch_fn=`/`run_fn=` on the new fetcher modules, Task 4/6). A hardcoded
`dict(os.environ)` reaching into `cfg_resolve`/`load_secret` here gives Step 5b's own CLI-level
tests (below) no way to isolate `HOME` from the real developer machine — a test resolving
`review-spec.toml`'s global-merge path would silently read whatever `~/.config/ai-kit/
review-spec.toml` actually exists on the machine running the suite. Fix: add an injectable
`env_fn` parameter to `main()` itself (same pattern as `which_fn`/`run_fn`), defaulting to the
real environment, and use it here instead of the two inline `dict(os.environ)` calls:

```python
def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run,
         dispatch_execute_fn=dispatch_execute, dispatch_reviewer_fn=dispatch_reviewer,
         env_fn=lambda: dict(os.environ)) -> int:
```

```python
    if args.command == "fetch-model-catalog":
        # MEDIUM finding: cache_is_stale is already imported at module level (`from
        # ai_kit_spec.cache import cache_is_stale, cache_read_json, cache_write_json` --
        # confirmed live in the current cli.py) -- no local re-import needed here, unlike
        # the four genuinely-new-to-this-subcommand imports below.
        from ai_kit_spec.config_io import cfg_resolve
        from ai_kit_spec.local_secrets import load_secret
        from ai_kit_spec.model_catalog import CATALOG_TTL_SECONDS
        from ai_kit_spec.model_sources import fetch_artificial_analysis, fetch_models_dev

        runtimes = cache_read_json(args.runtimes_json) or {}
        discovered = [
            {"cli": cli_name, "model_id": model_id}
            for cli_name, cli_data in runtimes.get("clis", {}).items()
            for model_id in cli_data.get("models", [])
        ]
        # Single-provider CLIs (codex, grok, claude/native, or any future CLI with no "models"
        # array -- confirmed live: detect_installed_clis' build_runtimes_snapshot only ever
        # populates "models" for opencode/cursor-agent) have no discoverable catalog to
        # enumerate. Their EXACT candidate source is whatever review-spec.toml already has
        # registered for that CLI -- re-running this subcommand re-enriches/re-ranks a model
        # the wizard already confirmed once. A model not yet registered for a single-provider
        # CLI stays on ai-kit-spec-config's existing manual per-model research path (SKILL.md
        # Step 2.2) until the user adds it as a reviewer -- the NEXT run of this subcommand
        # then picks it up here. This reconciliation ALWAYS runs -- see the --if-stale note
        # above; only the two external-source fetches below are gated by it.
        single_provider_clis = {name for name, data in runtimes.get("clis", {}).items()
                                 if data.get("installed") and "models" not in data}
        if single_provider_clis:
            cwd = args.cwd or os.getcwd()
            resolved = cfg_resolve(cwd, env_fn())
            for reviewer in resolved.get("reviewers", []):
                if reviewer.get("cli") in single_provider_clis and reviewer.get("model"):
                    discovered.append({"cli": reviewer["cli"], "model_id": reviewer["model"]})
        for raw in args.extra_candidate:
            cli_name, _, model_id = raw.partition(":")
            if cli_name and model_id:
                discovered.append({"cli": cli_name, "model_id": model_id})

        existing_catalog = cache_read_json(args.catalog_path) or {}
        skip_fetch = args.if_stale and not cache_is_stale(args.catalog_path, CATALOG_TTL_SECONDS)
        if skip_fetch:
            models_dev_data, models_dev_ok = {}, False
            aa_models, aa_ok = [], False
        else:
            api_key = load_secret(env_fn(), "ARTIFICIAL_ANALYSIS_API_KEY")
            models_dev_data, models_dev_ok = fetch_models_dev()
            aa_models, aa_fetch_ok = fetch_artificial_analysis(api_key)
            # CRITICAL finding: "no API key configured" (aa_fetch_ok=True, aa_models=[] --
            # Task 4's own "deliberately skipped, not a failure" contract) must NOT be treated
            # as "Artificial Analysis was queried and genuinely found no match" -- that would
            # silently wipe every already-cached AA score/pricing/attribution on every run
            # until a key is added. Both a real fetch failure AND no key at all take the same
            # "preserve whatever's cached, don't touch it" path inside build_model_catalog.
            aa_ok = aa_fetch_ok and bool(api_key)

        catalog, rejections, unmatched = build_model_catalog(
            discovered, models_dev_data, models_dev_ok, aa_models, aa_ok, existing_catalog)
        cache_write_json(args.catalog_path, catalog)
        print(json.dumps({"catalog_path": args.catalog_path, "entry_count": len(catalog),
                           "rejections": rejections, "unmatched": unmatched,
                           "discovered": discovered,
                           "models_dev_ok": models_dev_ok, "artificial_analysis_ok": aa_ok,
                           "fetch_skipped": skip_fetch}))
        return 0

    if args.command == "confirm-catalog-entry":
        from ai_kit_spec.model_catalog import merge_catalog_entry

        payload = cache_read_json(args.entry_json) or {}
        catalog = cache_read_json(args.catalog_path) or {}
        catalog, reason = merge_catalog_entry(catalog, payload["model_id"], payload["entry"])
        if reason:
            print(json.dumps({"confirmed": False, "reason": reason}))
            return 1
        cache_write_json(args.catalog_path, catalog)
        print(json.dumps({"confirmed": True, "model_id": payload["model_id"]}))
        return 0

    if args.command == "apply-heuristic-correction":
        from ai_kit_spec.model_catalog import apply_heuristic_corrections

        # HIGH finding: a raw json.dump(..., open(path, "w")) bypasses this repo's atomic,
        # validated cache-write path -- a crash mid-write can corrupt the catalog file, and
        # nothing here would ever re-validate the result. cache_write_json (already imported,
        # used by every other catalog-writing subcommand) is the ONE write path for
        # model-catalog.json; this subcommand is the ONLY way a heuristic correction is
        # ever persisted, matching confirm-catalog-entry's contract for unmatched candidates.
        # CRITICAL finding: apply_heuristic_corrections now returns (catalog, reason) -- a
        # correction that would produce a schema-invalid entry is rejected here exactly like
        # confirm-catalog-entry rejects an invalid new entry, never silently written.
        corrections = cache_read_json(args.corrections_json) or {}
        catalog = cache_read_json(args.catalog_path) or {}
        catalog, reason = apply_heuristic_corrections(catalog, args.model_id, corrections)
        if reason:
            print(json.dumps({"applied": False, "reason": reason}))
            return 1
        cache_write_json(args.catalog_path, catalog)
        print(json.dumps({"applied": True, "model_id": args.model_id}))
        return 0
```

(`json`, `os`, `cache_read_json`, `cache_write_json` are already imported at the top of
`cli.py` per Task 7's Interfaces list — no new top-level imports needed for those four.)

- [ ] **Step 5b: Write CLI-level tests for the subcommand wiring itself**

MEDIUM finding: `TestBuildModelCatalog` alone only ever exercises the pure function — it
cannot catch a bug in the argparse wiring, the `--if-stale` gate, or the JSON-file-based
`confirm-catalog-entry`/`apply-heuristic-correction` payload handling around it. Add, using
this repo's existing `rs.main([...])` CLI-invocation pattern (see `TestMainCli` in this same
file):

```python
class TestFetchModelCatalogCli(unittest.TestCase):
    def _write_runtimes(self, d, clis):
        path = os.path.join(d, "runtimes.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"clis": clis}, f)
        return path

    def test_if_stale_with_a_fresh_catalog_skips_fetch_but_still_reports_new_candidates(self):
        # CRITICAL finding: freshness must gate the network fetch only, never candidate
        # discovery -- a brand-new model must still surface as `unmatched`, not be silently
        # missed until the cache goes stale.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)  # exists -> "fresh" under --if-stale (mtime is now)
            runtimes_path = self._write_runtimes(
                d, {"opencode": {"installed": True, "models": ["vendor/brand-new"]}})
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["fetch-model-catalog", "--runtimes-json", runtimes_path,
                                 "--catalog-path", catalog_path, "--if-stale"])
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertTrue(result["fetch_skipped"])
            self.assertEqual(len(result["unmatched"]), 1)
            self.assertEqual(result["unmatched"][0]["model_id"], "vendor/brand-new")

    def test_extra_candidate_flag_is_included_in_discovery(self):
        # --if-stale + a pre-existing (fresh) catalog file keeps this test network-free (see
        # the skip-fetch test above) while still proving --extra-candidate reaches `discovered`
        # -- discovery/reconciliation runs unconditionally, network fetching is what's gated.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            runtimes_path = self._write_runtimes(d, {})
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["fetch-model-catalog", "--runtimes-json", runtimes_path,
                                 "--catalog-path", catalog_path, "--if-stale",
                                 "--extra-candidate", "codex:vendor/typed-in-model"])
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertIn({"cli": "codex", "model_id": "vendor/typed-in-model"},
                           result["discovered"])

    def test_single_provider_cli_candidate_pulled_from_review_spec_toml(self):
        # Same network-free technique as above (--if-stale + a fresh, pre-existing catalog).
        # HIGH finding: this resolves review-spec.toml's global-merge path too (cfg_resolve),
        # so `env_fn` MUST point HOME at this tempdir -- never the real dict(os.environ) --
        # or this test would silently read whatever global config exists on the machine
        # actually running the suite.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            runtimes_path = self._write_runtimes(
                d, {"codex": {"installed": True}})  # no "models" key -- single-provider
            local_cfg = os.path.join(d, ".aikit", "review-spec.toml")
            os.makedirs(os.path.dirname(local_cfg))
            with open(local_cfg, "w", encoding="utf-8") as f:
                f.write('[[reviewers]]\nkey = "codex-primary"\nmodel = "vendor/already-registered"\n'
                        'vendor = "vendor"\ncli = "codex"\n')
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["fetch-model-catalog", "--runtimes-json", runtimes_path,
                                 "--catalog-path", catalog_path, "--cwd", d, "--if-stale"],
                                env_fn=lambda: {"HOME": d})
            self.assertEqual(code, 0)
            result = json.loads(buf.getvalue())
            self.assertIn({"cli": "codex", "model_id": "vendor/already-registered"},
                           result["discovered"])

    def test_confirm_catalog_entry_rejects_invalid_entry_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
            entry_path = os.path.join(d, "entry.json")
            with open(entry_path, "w", encoding="utf-8") as f:
                json.dump({"model_id": "vendor/x", "entry": {"provider": "vendor"}}, f)  # missing fields
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["confirm-catalog-entry", "--catalog-path", catalog_path,
                                 "--entry-json", entry_path])
            self.assertEqual(code, 1)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["confirmed"])
            self.assertEqual(cache_read_json(catalog_path), {})  # unchanged, no partial write

    def test_apply_heuristic_correction_writes_through_the_atomic_cache_api(self):
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            existing = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                          "source": {}, "confidence": "low",
                                          "last_verified": "2026-09-02", "is_router": True}}
            cache_write_json(catalog_path, existing)
            corrections_path = os.path.join(d, "corrections.json")
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump({"is_router": False}, f)
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["apply-heuristic-correction", "--catalog-path", catalog_path,
                                 "--model-id", "router-env/x",
                                 "--corrections-json", corrections_path])
            self.assertEqual(code, 0)
            self.assertFalse(cache_read_json(catalog_path)["router-env/x"]["is_router"])

    def test_apply_heuristic_correction_rejects_invalid_correction_with_nonzero_exit(self):
        # CRITICAL finding: a correction that would make the merged entry schema-invalid must
        # be rejected (nonzero exit, no write) -- cache_write_json alone never validates.
        with tempfile.TemporaryDirectory() as d:
            catalog_path = os.path.join(d, "model-catalog.json")
            existing = {"router-env/x": {"provider": "router-env", "runtimes": {"opencode": {}},
                                          "source": {}, "confidence": "low",
                                          "last_verified": "2026-09-02", "is_router": True}}
            cache_write_json(catalog_path, existing)
            corrections_path = os.path.join(d, "corrections.json")
            with open(corrections_path, "w", encoding="utf-8") as f:
                json.dump({"is_router": "not-a-bool"}, f)
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = rs.main(["apply-heuristic-correction", "--catalog-path", catalog_path,
                                 "--model-id", "router-env/x",
                                 "--corrections-json", corrections_path])
            self.assertEqual(code, 1)
            result = json.loads(buf.getvalue())
            self.assertFalse(result["applied"])
            self.assertTrue(cache_read_json(catalog_path)["router-env/x"]["is_router"])  # unchanged
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_ai_kit_spec -k TestBuildModelCatalog -k TestFetchModelCatalogCli -v`
Expected: PASS.

- [ ] **Step 7: Manual smoke test against the real cache**

Run (uses the real, already-detected runtimes snapshot and the real secrets file from this
session — network calls go out for real here, this is a smoke test, not part of the
automated suite):

```bash
python3 skills/ai-kit-spec-review/ai-kit-spec.py fetch-model-catalog \
  --runtimes-json ~/.cache/ai-kit/spec/runtimes.json \
  --catalog-path /tmp/model-catalog-smoketest.json
python3 -m json.tool /tmp/model-catalog-smoketest.json | head -40
```

Expected: valid JSON, at least one entry with `"source": {"models_dev": true, ...}` for a
recognizable model (e.g. one of the `openai/gpt-*` or `xai/grok-*` ids already in this
session's `~/.cache/ai-kit/spec/runtimes.json`). Delete the smoke-test file afterward
(`rm /tmp/model-catalog-smoketest.json`) — it is not a fixture, just a manual check.

- [ ] **Step 8: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/cli.py tests/test_ai_kit_spec.py
git commit -m "$(cat <<'EOF'
feat(ai-kit-spec): add fetch-model-catalog, confirm-catalog-entry, and apply-heuristic-correction subcommands

build_model_catalog orchestrates discovery (runtimes snapshot + already-
registered review-spec.toml entries for single-provider CLIs +
--extra-candidate -- always reconciled, every invocation, --if-stale
gates network fetching only) -> matching against models.dev/Artificial
Analysis (collision-safe on both sides) -> local heuristics (computed
once, then preserved across later rebuilds -- never silently
recomputed over a user's correction) -> canonical-key schema-validated
merge. A source-fetch failure OR a missing API key preserves that
source's cached fields (including a runtime's ctx_window) rather than
overwriting them; a brand-new unmatched candidate is reported, with its
own heuristic fields, but never auto-persisted -- only
confirm-catalog-entry (fed by the wizard's research+confirmation step,
Task 8) ever writes one of those, and only apply-heuristic-correction
ever persists a heuristic correction, both through the atomic
cache_write_json path. A bare model id matched only via Artificial
Analysis derives its vendor from model_creator rather than becoming its
own vendor. fetch-model-catalog's own JSON output now also includes the
full reconciled `discovered` candidate list, so Task 8's ranking step
never has to (and previously incorrectly did) recompute a partial one.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 8: Rewrite `ai-kit-spec-config` Step 2.2 to use the catalog, and Step 2.6/Step 3 to write `purpose`

**Files:**
- Modify: `skills/ai-kit-spec-config/SKILL.md` (Step 2.2 section, currently the lightweight per-model WebSearch; Step 2.6's `strength` question; Step 2.7's native-reviewer question; Step 3's JSON-shape prose)

**Interfaces:**
- Consumes: `fetch-model-catalog`/`confirm-catalog-entry`/`apply-heuristic-correction`/`cache-path --kind catalog` (Task 7), `score_candidates`/`load_ranking_weights` (Task 1), `current_candidate_keys` (Task 2) — invoked the same way this SKILL.md already invokes other `ai-kit-spec.py` subcommands (via `python3 "$TOOLS_PY" <subcommand> ...`, per its Step 0's `TOOLS_PY` resolution).
- Produces: no new code — this task only changes wizard prose/instructions. **It DOES close the producer-to-consumer `purpose` handoff** (Cross-Document Consistency finding): Step 2.2 records which ranked list(s) (REVIEW/EXECUTE/both) the user confirmed each CLI-sourced candidate from, Step 2.6 is rewritten to no longer ask a separate `purpose` question (it's already known from Step 2.2), Step 2.7 is rewritten to ask the SAME review/execute/both question for every native entry (Cross-Document HIGH finding — native entries never go through Step 2.2's catalog/ranking flow at all, since there's no CLI model to look up, so without this fix they'd get no `purpose` and the consumer side would silently read that absence as "matches everything," never actually confirmed by the user), and Step 3's JSON-shape prose explicitly includes `purpose`/`is_router`/`fallback_quota` per reviewer entry in the object passed to `render-toml` — this is what Plan B's consumer-side `purpose_matches`/`filter_by_purpose`/`_filter_ladder_by_purpose` actually receive at read time. **It also closes the provider-confirmation/key-desync gap** (CRITICAL finding): Step 2.2's unmatched-candidate confirmation sub-step (item 4) now re-derives the catalog key from whatever provider the user actually confirms — via `canonical_key(confirmed_provider, bare_model_id)` — instead of reusing the pre-confirmation `unmatched.key`, so a corrected provider can never desync from the key it's filed under.

- [ ] **Step 1: Read the current Step 2.2, Step 2.6, and Step 2.7 sections in full**

Run: `bat --style=plain --line-range 164:244 skills/ai-kit-spec-config/SKILL.md` (the section
from Step 2.2's heading, confirmed live at line 164, through the end of Step 2.7 — confirmed
live at line 244, the line immediately before Step 2.8's own heading at line 245, so this
range covers Step 2.2 AND Step 2.6 AND Step 2.7 without spilling into Step 2.8, which this
task never touches — MEDIUM finding, round-4: an earlier draft's range (164:245) both
included Step 2.8's heading line and described itself as stopping "through Step 2.6's,"
undercounting the Step 2.7 content it actually needs, since Step 3b below rewrites Step 2.7
too. Confirm exact line numbers first, since Task 1-7 changes elsewhere in this repo do not
touch this file and line numbers here are stable from this plan's grounding pass).

- [ ] **Step 2: Replace Step 2.2's body**

Replace the existing Step 2.2 section (the ad-hoc "for each unfamiliar model, WebSearch..."
prose) with:

```markdown
#### Step 2.2 — Pick which CLIs and models to register

For every CLI the user wants to consider (from Step 1's detection), build the ranked
candidate list via the model-discovery catalog rather than guessing or searching per model.
**Order matters here: unmatched candidates are researched and confirmed BEFORE anything is
ranked** — an unconfirmed guess must never appear in a ranked list the user is about to trust.

1. Ensure a runtimes snapshot exists (Step 1 already produces one via `detect-runtimes
   --save`/`--if-stale`) — reuse `$RUNTIMES_JSON` from Step 0. Resolve the catalog cache path
   (no manual path-string surgery — a dedicated `--kind` exists precisely so this skill never
   has to derive one cache filename from another):
   ```bash
   CATALOG_JSON="$(python3 "$TOOLS_PY" cache-path --kind catalog)"
   ```
   **CRITICAL finding: ask which CLIs to consider, and group each multi-provider CLI's raw
   model list, BEFORE any of it is discovered/matched/ranked.** For each installed CLI (beyond
   the current session's own runtime), use `AskUserQuestion` to ask whether the user wants it
   available as a cross-AI reviewer at all (this ask was silently dropped from an earlier draft
   of this step — it must stay: registering every installed CLI indiscriminately, unfiltered,
   is exactly what this skill's own opening framing at the top of Step 2 warns against). For
   each CLI the user keeps, if it's multi-provider (`models` array present — e.g. `opencode`,
   `cursor-agent`), **never hand its raw model list to `fetch-model-catalog` as-is** — a
   multi-provider CLI's raw list can be very long (confirmed live: cursor-agent's catalog is
   ~200 ids, a handful of base model families each multiplied out by effort/thinking/fast-tier
   variants), and most of those tier variants will not exact-match models.dev/Artificial
   Analysis, which would otherwise turn Step 4 below into hundreds of individual unmatched
   searches and confirmation prompts for what is really only a handful of base families. Group
   it first:
   ```bash
   python3 "$TOOLS_PY" group-models --runtimes-json "$RUNTIMES_JSON" --cli <id>
   ```
   This prints `{"<family>": ["<variant-id>", ...], ...}`. Present the **families**, not the raw
   ids, and let the user pick a family (defaulting to its base id) or drill into a specific
   tier/effort variant only if they want one. Collect the chosen model id(s) per CLI, then write
   a FILTERED runtimes snapshot — a copy of `$RUNTIMES_JSON` whose `clis.<cli>.models` arrays
   are narrowed to only the CLIs kept and models chosen above (single-provider CLIs, which have
   no `models` array to narrow, pass through unchanged) — and use that filtered file, not the
   raw `$RUNTIMES_JSON`, as `--runtimes-json` in Step 3's `fetch-model-catalog` call below:
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
   This is also what closes the separate HIGH finding that `fetch-model-catalog` itself has no
   per-CLI/model selection flag: rather than adding one to Task 7's subcommand (which would
   duplicate the family-grouping judgment call this step already has to make with the user),
   this step scopes discovery upstream, at the input snapshot, before `fetch-model-catalog` ever
   runs — the subcommand's own contract (discover everything a runtimes snapshot lists) is
   unchanged; only the snapshot it's given is narrowed to what was actually asked for.
2. **For any single-provider CLI (no `models` array — e.g. codex, grok) the user wants to
   consider that has NO existing `review-spec.toml` entry yet** (first-time setup): ask the
   user for a candidate model id now, the same way this step always has (never guess or trust
   training knowledge — WebSearch it for recency first, per this skill's `NEVER` list). Collect
   these as `--extra-candidate <cli>:<model-id>` flags (repeatable) for the next command — this
   is what lets a brand-new single-provider-CLI candidate flow through the SAME
   matching/enrichment/ranking path as everything else, instead of being registered blind.
3. Refresh the catalog (also picks up anything already in `review-spec.toml` for an
   already-configured single-provider CLI automatically — see Task 7's own discovery rule).
   **Capture its printed JSON to a file** — Task 7's `fetch-model-catalog` now prints the FULL
   reconciled `discovered` candidate list (runtimes snapshot + registered single-provider-CLI
   models + `--extra-candidate`, exactly what this subcommand itself used) alongside
   `unmatched`/`rejections`, so this step never has to recompute a partial version of that list
   later (CRITICAL finding: an earlier draft's ranking step, further down, only ever rebuilt
   `discovered` from `$RUNTIMES_JSON`'s own `models` arrays, silently excluding codex/grok/
   every single-provider-CLI candidate from ranking):
   ```bash
   python3 "$TOOLS_PY" fetch-model-catalog --runtimes-json "$FILTERED_RUNTIMES_JSON" \
     --catalog-path "$CATALOG_JSON" --cwd "$(pwd)" --if-stale \
     [--extra-candidate <cli>:<model-id> ...] > /tmp/fetch-model-catalog-result.json
   ```
   `--if-stale` here gates the models.dev/Artificial Analysis NETWORK calls only — candidate
   discovery/reconciliation always runs, so a brand-new model is reflected in this run's
   `unmatched`/`discovered` output even when the catalog itself is still fresh and nothing was
   re-fetched (Task 7's own contract; see its `--if-stale` help text).
   If this is the very first run (no catalog yet, `python3 "$TOOLS_PY" cache-path --kind
   catalog` didn't already exist before this command ran) and the printed JSON's
   `artificial_analysis_ok` is `false` with `rejections`/`unmatched` non-trivial, or the user
   asks about richer scores, mention: "Artificial Analysis (artificialanalysis.ai) adds
   intelligence/coding/agentic index scores and speed data to model ranking — optional,
   models.dev alone still gives context window, pricing, and tool-calling data. If you have a
   key, add `ARTIFICIAL_ANALYSIS_API_KEY=<key>` to `~/.config/ai-kit/secrets.env` yourself (this
   skill never writes that file — Global Constraints), then re-run the command above without
   `--if-stale` so the fresh key gets used." Never write, create, or edit `secrets.env` from
   this skill — reading it is Task 3's `local_secrets.load_secret`'s job, writing it is
   explicitly out of scope everywhere in this design (Global Constraints).
   The printed JSON's `unmatched` list and `rejections` list drive the next two steps.
4. **Unmatched-candidate research and confirmation — BEFORE ranking, never after.** For every
   entry in the captured JSON's `unmatched` list (a candidate that matched neither models.dev
   nor Artificial Analysis and has no prior catalog entry — each entry already carries its own
   locally-inferred `is_router`/`batch_mode`/`fallback_quota`, computed by `fetch-model-catalog`
   itself even though the candidate isn't in the catalog yet): do ONE targeted WebSearch for
   that specific model id + vendor name, summarize what you find in one line, and use
   `AskUserQuestion` to have the user confirm or correct the provider AND the three heuristic
   fields before any of it is ever persisted — this is the only per-model search this step ever
   does now, reserved for genuinely new/unrecognized models (e.g. one released after
   models.dev/Artificial Analysis last indexed it).

   **CRITICAL finding: the catalog key MUST be re-derived from whatever provider the user
   actually confirms, never reused from `unmatched.key` (which was computed from the
   PRE-confirmation provider GUESS).** If the user corrects the provider, `unmatched.key`
   and the confirmed `provider` would otherwise disagree — violating the catalog's own
   `vendor/model` key invariant (spec §5). Recompute the key the same way `fetch-model-catalog`
   itself would, via `canonical_key(confirmed_provider, bare_model_id)` — `bare_model_id` is
   `unmatched.model_id` with any `"<cli-provider-label>/"` prefix stripped (the same split
   `model_matcher.bare_model_part`/Task 7's `build_model_catalog` already use: everything
   after the first `/`, or the whole string if there's no `/`). Do this with the same inline `python3 -c` `sys.path.insert`
   convention Step 5 below already uses (no separate CLI subcommand needed for a pure string
   computation):
   ```bash
   CONFIRMED_KEY="$(python3 -c "
import sys
sys.path.insert(0, '$(dirname "$TOOLS_PY")')
from ai_kit_spec.model_catalog import canonical_key
bare = '<unmatched.model_id>'.split('/', 1)[-1]
print(canonical_key('<confirmed provider>', bare))
")"
   ```
   Once confirmed, persist it under `$CONFIRMED_KEY` — never under the stale `unmatched.key` —
   (this is the ONLY path that ever writes an unmatched candidate to the catalog —
   `fetch-model-catalog` itself deliberately never does):
   ```bash
   cat > /tmp/confirm-entry.json <<'JSON'
   {"model_id": "<value of $CONFIRMED_KEY>",
    "entry": {"provider": "<confirmed provider>",
              "runtimes": {"<cli>": {"model_id": "<unmatched.model_id>"}},
              "source": {"models_dev": false, "artificial_analysis": false, "manual": true},
              "confidence": "low", "last_verified": "<today, YYYY-MM-DD>",
              "is_router": <confirmed is_router>, "batch_mode": <confirmed batch_mode>,
              "fallback_quota": <confirmed fallback_quota>}}
   JSON
   python3 "$TOOLS_PY" confirm-catalog-entry --catalog-path "$CATALOG_JSON" \
     --entry-json /tmp/confirm-entry.json
   ```
   (When the user does NOT correct the provider — the common case — `$CONFIRMED_KEY` always
   equals `unmatched.key` exactly, since both are `canonical_key` applied to the same provider
   and bare model id; nothing changes for that path.)
5. **Rank only what's actually installed right now** — load the catalog, filter to
   `current_candidate_keys` using the SAME `discovered` list Step 3's captured JSON already
   has (never recomputed from `$RUNTIMES_JSON` alone — that would silently drop every
   single-provider-CLI candidate, the exact CRITICAL finding Step 3's capture above fixes),
   THEN rank per purpose. This is a Python call, not a subcommand; run it inline via
   `python3 -c` — note the explicit `sys.path.insert` below, required because this runs from an
   arbitrary cwd, not from inside `ai-kit-spec-review`'s own directory the way `python3
   "$TOOLS_PY"` is (that script's own directory is added to `sys.path` automatically by the
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
weights = load_ranking_weights()
def field(e, path, label):
    # MEDIUM finding: item 6 below mandates a per-field breakdown (intelligence/coding/agentic/
    # speed/ctx/batch), each tagged '[via Artificial Analysis]' individually when THAT field
    # came from Artificial Analysis -- a single whole-entry aa_tag on the score line cannot
    # express that 'ctx' is always models.dev-sourced while 'intelligence'/'coding'/'agentic'
    # are AA-sourced. MEDIUM finding (round-4): an earlier draft of this loop never called
    # field() for 'coding_index' at all, even though it carries EXECUTE's largest weight (0.30,
    # ranking-weights.toml) -- and never displayed 'tokens_per_sec'/'tool_calling' either, so
    # the sample output below (item 6) was promising fields this script could never produce.
    v = e.get('scores', {}).get(path) if path in ('intelligence_index', 'coding_index', 'agentic_index') else e.get(path)
    if v is None:
        return None
    aa_sourced = path in ('intelligence_index', 'coding_index', 'agentic_index', 'tokens_per_sec')
    tag = ' [via Artificial Analysis]' if aa_sourced and e.get('source', {}).get('artificial_analysis') else ''
    return f'{label} {v}{tag}'

for purpose in ('review', 'execute'):
    ranked = score_candidates(entries, purpose, weights)[:5]
    print(purpose.upper())
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
6. Present the top candidates per purpose to the user in this shape (adapt scores/labels to
   what the catalog actually returned — illustrative, not literal output; the exact field set
   shown for a given candidate always matches whatever the `field()` calls above actually
   found non-`None` for it, never more than that). **Any field sourced from Artificial Analysis (scores,
   speed, or its pricing when models.dev had no match) carries the `[via Artificial Analysis]`
   tag verbatim, every time it's shown — this is a hard requirement, not a nicety: Artificial
   Analysis's API terms require attribution wherever its data is presented.**
   ```
   REVIEW (flagship/reasoning) — top candidates:
     1. gpt-5.6-sol            score 87  (intelligence 91 [via Artificial Analysis], batch✓, ctx 400k)
     2. grok-4.6                score 79  (intelligence 85 [via Artificial Analysis], agentic 88 [via Artificial Analysis])
     3. router-env (fallback✓)  score 74

   EXECUTE (coding-agent) — top candidates:
     1. router-env (fallback✓)  score 90  (coding 89 [via Artificial Analysis], tool_call✓)
     2. gpt-5.6-sol              score 81
   Any preference not listed, or confirm this order for the ladder?
   ```
   Ask the user to confirm or adjust. **Record, for every confirmed candidate, which list(s)
   it was confirmed from** — REVIEW only, EXECUTE only, or both — this becomes that entry's
   `purpose` value (`"review"`, `"execute"`, or `"both"`) carried forward into Step 2.4's
   command-building and Step 3's write below. **A candidate that comes through this ranked
   flow always gets an explicit `purpose` written — never left absent.** Absent `purpose` is
   reserved strictly for a pre-migration `review-spec.toml` entry that predates this design;
   every NEW entry this wizard writes, from this step or from Step 2.7's native-entry flow
   below, states its `purpose` explicitly (Cross-Document Consistency HIGH finding — an absent
   `purpose` reads as "matches both roles" to the consumer side, which must never be an
   accident of a newly-written entry, only the documented legacy-compat default). This IS the
   answer to what used to be a separate `purpose` question — see Step 2.6's rewrite further
   down.
7. **HIGH finding: before finalizing a CLI outside codegraph support (today: `grok`), check for
   a codegraph-capable alternative** — this check existed in the pre-catalog version of this
   step and is preserved here unchanged, never silently dropped just because ranking replaced
   the ad-hoc WebSearch around it. For each model confirmed onto such a CLI in the previous
   step, run:
   ```bash
   python3 "$TOOLS_PY" check-codegraph-alternative --cli <id> --model <model-id> \
     --runtimes-json "$RUNTIMES_JSON"
   ```
   When `alternative_cli` is non-null, tell the user in one line before they finalize:
   `"<model> is also reachable via <alternative_cli>, which supports codegraph_explore (grok
   CLI does not) — consider registering it through <alternative_cli> instead for
   grounding-heavy review/execute work."` This is informational only (best-effort substring
   match, per `find_codegraph_alternative`'s own docstring) — the user still makes the final
   call; never silently substitute the CLI or drop the original option.
8. Confirm `is_router`/`batch_mode`/`fallback_quota` for any candidate where the catalog set
   them via naming heuristic (never an external source, per the design) — **but skip any
   field already listed in that entry's `heuristic_confirmed` array** (HIGH finding: a plain
   bool alone cannot distinguish "the heuristic's own untouched guess" from "the user already
   confirmed this exact value" — `heuristic_confirmed` is the provenance record that makes
   "don't ask again" actually work, not just an aspiration; see `apply_heuristic_corrections`,
   Task 2). For every field NOT yet in `heuristic_confirmed`, ask one line each:
   "`router-env` looks like a router with fallback — correct?" / "`gpt-5-mini` looks
   batch-suitable — correct?" **Persist the answer back to the catalog cache immediately —
   whether the user corrects the value OR simply confirms the heuristic's guess as-is** (so
   the NEXT run of this wizard doesn't ask again either way; only calling this on an actual
   *change* would leave a confirmed-but-unchanged field looking identical to a never-asked
   one), via the `apply-heuristic-correction` subcommand (Task 7) — never a raw
   `json.dump`/`open`, which bypasses this repo's atomic, validated cache-write path (HIGH
   finding):
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
```

- [ ] **Step 3: Rewrite Step 2.6 to stop asking `purpose` from scratch**

Replace Step 2.6's body (currently: "Also ask, for every entry (CLI or native), an optional
`strength` attribute...") with:

```markdown
#### Step 2.6 — Ask about the optional strength attribute; `purpose` comes from Step 2.2

**Also ask, for every entry (CLI or native), an optional `strength`**: `"ui"`, `"coding"`,
`"planning"`, or left unset — free text otherwise, not validated. This is informational only —
captured in `review-spec.toml` for a human (or a future version of this design) to read, but
**not yet consumed by any resolution logic today** (`resolve_reviewers`/`resolve_ladder_pick`
ignore it completely). Tell the user this plainly if they ask what it does: it doesn't change
dispatch behavior yet, it just gets saved.

**`purpose` is NOT asked here** — it was already captured at Step 2.2 (which ranked list(s),
REVIEW/EXECUTE/both, the user confirmed each candidate from). Carry that value forward
unchanged into this entry's fields; do not re-ask, and do not silently drop it.
```

- [ ] **Step 3b: Also ask `purpose` explicitly for every native entry in Step 2.7**

Cross-Document Consistency HIGH finding: a native (`cli`-omitted) reviewer entry, registered
at Step 2.7, never goes through Step 2.2's catalog/ranking flow — there's no CLI model id to
look up in models.dev/Artificial Analysis for a `sonnet`/`opus`/`haiku`/`fable` alias. Without
an explicit question here, a native entry would get NO `purpose` at all, and the consumer side
(Plan B) reads an absent `purpose` as "matches both review and execute" — an assumption that
must be a deliberate, documented legacy-compat default, never an accident of how a brand-new
entry happened to get written.

In `skills/ai-kit-spec-config/SKILL.md`'s Step 2.7 ("Ask about native reviewer entries"),
locate the existing prose that has the user pick one of the four `Agent`-tool aliases for each
native entry, and add immediately after it:

```markdown
**Also ask, for each native entry, the same `purpose` question Step 2.2 answers for CLI-sourced
candidates**: should this native entry be used for review, execute, or both? (`"review"` |
`"execute"` | `"both"`.) A native entry is a real, always-available reviewer/executor choice —
it deserves the same explicit curation as any ranked CLI candidate, not a silent default. Carry
the answer into this entry's `purpose` field at Step 3's write, exactly like a Step 2.2-sourced
entry — never leave it unset for a newly-registered native entry.
```

- [ ] **Step 4: Update Step 3's JSON-shape description to include the new fields**

In the "### Step 3 — Write" section, the sentence describing the JSON shape
`render-toml` expects currently reads: `{"strategy": "...", "policy": {...}, "reviewers":
[...]}`. Update it to be explicit that each `[[reviewers]]` object now carries the three new
flat fields this design adds:

```markdown
Build the JSON shape `skills/ai-kit-spec-review/ai-kit-spec.py`'s `render-toml` subcommand
expects (`{"strategy": "...", "policy": {...}, "reviewers": [...]}` — the `strategy` key only
when Step 2 asked for `local-only`). **Each object in `reviewers` now also carries `purpose`
(`"review"`/`"execute"`/`"both"`, from Step 2.2 for a CLI-sourced entry or Step 2.7 for a
native one — every entry this wizard newly registers gets an explicit `purpose`, CLI-sourced
or native alike; absent `purpose` is reserved for a pre-migration entry this run is merely
carrying forward unchanged, never for a brand-new one), and `is_router`/`fallback_quota` when
Step 2.2/2.7 confirmed either as `true`** (omit when `false`/unknown rather than writing a
redundant `false` for every entry — `purpose_matches`/`filter_by_purpose` on the consumer side
already treat an absent field as "no preference," exactly like today's `task_affinity` — that
fallback exists for legacy compatibility, not as this wizard's normal path for a new entry),
write it to a temp JSON file, then let `--out` do the write directly (via `cfg_write_toml`,
creating parent dirs as needed) rather than piping stdout through a second write yourself:
```

(The `render-toml` command line itself is unchanged — `config_io.validate_reviewer_fields`,
Task 2, now rejects-and-reports any malformed `purpose`/`is_router`/`fallback_quota` value
individually rather than writing it, so no additional check is needed in this skill's prose.)

- [ ] **Step 5: Update the Step 2 summary table**

Locate the summary table just above Step 2.1 (`| Decide where the config gets written |
Step 2.1 |` etc., confirmed present in this file). No row changes needed — Step 2.2's row
already reads "Pick which CLIs/models to register" and Step 2.6's reads "Tag a reviewer as
UI/coding/planning-oriented"; the mechanism behind both changed, not their name or position.

- [ ] **Step 6: Manual read-through**

Read the full modified Step 2.2/2.6/2.7/Step 3 sections back and confirm they read coherently
end-to-end (references to `$TOOLS_PY`, `$RUNTIMES_JSON`, `$CATALOG_JSON`, and
`/tmp/fetch-model-catalog-result.json` all resolve to values this SKILL.md's Step 0/Step
1/Step 2.2 already establish, `purpose` flows from Step 2.2's ranked-list confirmation through
Step 2.6 unchanged into Step 3's write, a native entry gets `purpose` from Step 2.7's own new
question, and no step anywhere instructs writing to `~/.config/ai-kit/secrets.env`) — this is
a prose/instructions file, there is no automated test for it; this read-through is the
verification step.

- [ ] **Step 7: Commit**

```bash
git add skills/ai-kit-spec-config/SKILL.md
git commit -m "$(cat <<'EOF'
docs(ai-kit-spec-config): rewrite Step 2.2 to use the model discovery catalog

Replaces the ad-hoc per-model WebSearch with fetch-model-catalog +
purpose-weighted ranking (score_candidates), presenting a ranked,
purpose-labeled candidate list with required Artificial Analysis
attribution. Unmatched candidates are researched and confirmed (via
confirm-catalog-entry, heuristic fields included) BEFORE ranking, never
after. Ranking reuses fetch-model-catalog's own printed `discovered`
list (never recomputed from the runtimes snapshot alone, which would
drop every single-provider-CLI candidate) filtered to models actually
present right now (current_candidate_keys). Step 2.6 no longer asks a
separate `purpose` question -- it's now carried forward from Step 2.2's
ranked-list confirmation into Step 3's write; Step 2.7's native entries
now get the same explicit purpose question, closing the producer-to-
consumer purpose handoff Plan B's filters depend on for BOTH CLI-sourced
and native entries. Heuristic corrections persist via the new
apply-heuristic-correction subcommand (atomic cache_write_json), never a
raw json.dump. This skill never writes ~/.config/ai-kit/secrets.env --
only reads it (Global Constraints); a missing Artificial Analysis key is
surfaced as a one-line suggestion, not an auto-write.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```

---

### Task 9: Full-suite regression check

**Files:**
- None modified — verification only.

- [ ] **Step 1: Run the full test suite**

Run: `cd /var/home/bazzite/git/personal/ai-kit && python3 -m unittest discover -s tests -v`

Expected: PASS, 0 failures — every new module's tests plus the entire pre-existing suite.
(Task 2's `cfg_render_toml`/`cache-path` edits and Task 7's discovery-loop change to
`fetch-model-catalog` are the only touches to pre-existing, already-tested functions — both
are additive, so every pre-existing test for those two still passes unchanged; Task 8 is a
docs-only change with no test surface.)

- [ ] **Step 2: Lint check (if the dev environment is set up)**

Run: `cd /var/home/bazzite/git/personal/ai-kit && make validate` (per `pyproject.toml`'s
`ruff`/`pylint`/`pyright`/`vulture` dev toolchain) if a `Makefile` target named `validate`
exists (`rg -n "^validate:" Makefile`); otherwise run `uv run ruff check
skills/ai-kit-spec-review/ai_kit_spec/model_*.py skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py skills/ai-kit-spec-review/ai_kit_spec/config_io.py skills/ai-kit-spec-review/ai_kit_spec/cli.py` directly. Fix any findings before
proceeding — this repo's own `pyproject.toml` config (line-length 100, `ruff` rule set
`E,F,W,I,UP,B,SIM,RUF`) applies to every new file in this plan.

- [ ] **Step 3: If anything fails, fix forward and commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(ai-kit-spec): address lint/regression findings from model discovery work

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BTyXKFjfkGWdjGoLWFdgiU
EOF
)"
```
(Skip if Steps 1-2 passed clean — no empty commits.)

---

## Self-Review Notes

**Spec coverage:**
- §2 (candidates only from CLI catalogs, never OpenRouter enumeration) → Task 7 (`build_model_catalog` only ever consumes `discovered_models` built from a `detect-runtimes` snapshot plus already-registered/wizard-typed single-provider-CLI candidates — never an OpenRouter-style enumeration).
- §3 (data sources, confirmed URLs/shapes, local-only fields) → Tasks 3-6 (fetchers, matcher, heuristics), verified against live payloads during this plan's own grounding pass. `fallback_quota`'s local-only heuristic → Task 5.
- §4 (data flow: discover → match → enrich → infer → persist → rank → write) → Tasks 6-8 end to end; unmatched candidates are researched+confirmed BEFORE persistence/ranking (Task 8 Steps 2/4), matching §4 step 2's ordering exactly (a prior draft had this backwards — fixed).
- §5 (schema, mandatory+optional field types, canonical identity, `render-toml` enforcement) → Task 2.
- §6 (ranking, weights table, bonuses, normalization) → Task 1, with structural validation (not just TOML-syntax validation) of the weights file before it's trusted. `task_affinity_match` is omitted from `score_candidates` itself (no real plan/doc scope at wizard time) but IS implemented as a dispatch-time tie-break in Plan B's Task 1 — see this plan's Global Constraints for the coordinated cross-plan resolution (round-2 fix: an earlier draft called this "handled by a hard filter," which round-2 review correctly flagged as not equivalent to the spec's additive bonus).
- §7 (consumer-side changes) → out of scope, Plan B's responsibility (explicitly noted in this plan's header) — but the `purpose` field Plan B reads is now actually WRITTEN here (Task 8, for BOTH CLI-sourced entries at Step 2.2 and native entries at Step 2.7 — round-2 fix: an earlier draft left native entries with no `purpose` at all), closing the cross-plan handoff.
- §8 (errors/staleness) → Task 4 (fetch failures now return explicit `ok` so a failure never silently overwrites cached enrichment), Task 2 (type-checked schema rejection, both catalog and `review-spec.toml` sides, including the previously-unchecked `reasoning_modes`/`fast_mode`/`speed_tier`/runtime sub-fields/`last_verified` format), Task 7 (`--if-stale` gates network fetching only — candidate discovery/reconciliation always runs; a source-down AND a no-API-key run both preserve that source's cached fields identically rather than wiping them; a runtime's `ctx_window` is preserved, not blanked, when models.dev is down; unmatched-never-auto-persisted, with heuristic fields included for the wizard's confirmation payload; a models.dev bare-id collision returns no match rather than guessing; a bare-id AA-only match derives its vendor from `model_creator`; a bare id with BOTH sources unavailable — the `--if-stale` default path — now recovers its real vendor/model key via `_find_existing_key_for_runtime` instead of minting an unstable `model_id/model_id` key that would orphan the cached entry and misreport it as unmatched every run — CRITICAL/HIGH fix, round-2 native-opus review, applied directly post-loop).
- §9 (testing: ranker/matcher/fetchers mocked, no live network in the suite) → every task's Step 1-2 use injected `fetch_fn`/fixture dicts, never real network calls inside `tests/test_ai_kit_spec.py`; Task 7's Step 7 live smoke test is explicitly manual and separate from the automated suite. `pytest` is not installed in this repo — every test-run command uses `python3 -m unittest ... -k` instead (Global Constraints).
- §10 (this plan is Plan A, independent of Plan B) → stated in the header.

**Placeholder scan:** No TBD/TODO. Every step has runnable code or an exact shell command.

**Type consistency:** `score_candidates(entries: list, purpose: str, weights: dict) -> list` (Task 1, no `task_affinity` param — see Global Constraints) is called identically in Task 8's inline Python. `merge_catalog_entry(catalog: dict, model_id: str, entry: dict) -> tuple` (Task 2) is called identically in Task 7's `build_model_catalog` and in Task 8's `confirm-catalog-entry` calls. `apply_heuristic_corrections(catalog: dict, model_id: str, corrections: dict) -> tuple[dict, str | None]` (Task 2, round-3 fix: was a bare-`dict`-returning function with no validation gate — now mirrors `merge_catalog_entry`'s own `(catalog, reason)` contract) is called identically in Task 7's `apply-heuristic-correction` subcommand, which propagates a rejection with a nonzero exit exactly like `confirm-catalog-entry` already does. `canonical_key`/`current_candidate_keys` (Task 2) are called with the exact signatures Task 7/Task 8 use them with — Task 8's unmatched-candidate confirmation (Step 2.2 item 4) now calls `canonical_key` itself, inline, to re-derive the catalog key from whatever provider the user actually confirms (round-3 fix: an earlier draft persisted a corrected provider under the pre-confirmation `unmatched.key`, letting the key and `provider` field disagree). `fetch_models_dev`/`fetch_artificial_analysis` (Task 4) now return `(data, ok)` tuples everywhere they're called (Task 7's `build_model_catalog` orchestration) — no caller anywhere in this plan still expects bare data. `match_models_dev`/`match_artificial_analysis(..., provider_hint=...)` (Task 6) return shapes are consumed exactly as defined in Task 7's `entry[...]` construction; both now try an exact normalized match first and only fall back to `_fuzzy_candidate_indices`'s fuzzy match when that finds nothing (round-3 fix: an earlier draft only ever did exact/near-exact comparison, never the fuzzy-match step spec §4/§6 explicitly requires). `build_model_catalog` is called as `cli.build_model_catalog(...)` everywhere (Task 7's own tests, its subcommand body) — no reference anywhere to a nonexistent `model_catalog_build` module (an earlier draft's bug, fixed). `merge_catalog_entry` now treats an explicit `None` value on a field PRESENT in the incoming `entry` as a clear-on-merge signal, distinct from that field being absent from `entry` entirely (which still preserves the cached value) — `_preserved_or_fresh_md_fields`/`_preserved_or_fresh_aa_fields`/Task 7's pricing-combination logic all emit that `None` signal specifically when a source was genuinely queried this run (`*_ok=True`) and found no match, so a source's provenance flipping to `false` always actually clears the fields it used to own (round-3 fix: a prior draft's plain dict-spread merge silently retained stale scores/pricing under a now-false `source.*` flag). `_find_existing_key_for_runtime(existing_catalog: dict, cli_name: str, model_id: str) -> str | None` (defined alongside `_slugify` in Task 7's `cli.py` additions) is called exactly once, inline, at the top of `build_model_catalog`'s per-candidate loop, and its result (`existing_key`) is consumed by both the provider-resolution `elif` chain and the final `key = existing_key or canonical_key(...)` line — no other call site needed it, since `confirm-catalog-entry`/`apply-heuristic-correction` (Task 7) always operate on an already-known key, never a freshly-discovered bare id. `bare_model_part(cli_model_id: str) -> str` (Task 6, `model_matcher.py`) is now defined exactly once and imported by `cli.py` (Task 7) rather than redefined — a MEDIUM finding, round-2 native-opus review, caught the earlier draft's copy-pasted duplicate. No drift between task boundaries.
