# Model Catalog Effort-Suffix Cross-Source Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover `context_window`/`tool_calling`/`structured_output`/`max_output_tokens` for a CLI-reported model that matches Artificial Analysis but not models.dev, when the gap is caused by an AA/CLI-only reasoning-effort suffix (e.g. `-high`, `-thinking-xhigh`) that models.dev's entry for that same model family omits.

**Architecture:** A new pure `_strip_known_effort_suffix` helper in `model_matcher.py` strips a recognized trailing effort token/compound from a bare model id. `match_models_dev` gains an `allow_fuzzy` parameter (default preserves today's behavior everywhere) so a caller can force exact-only matching. `cli.py`'s `build_model_catalog` gains a new enrichment-only retry block, entirely separate from the primary match (`md_match`), that tries an exact hinted match first and then the effort-stripped id, both exact-only — its result (`md_enrich_match`) is consumed only by the two field-preservation helpers and can never influence provider, canonical key, or pricing.

**Tech Stack:** Python 3.12, stdlib `difflib`/`re`, `unittest` (no pytest — `uv run python3 -m unittest`).

**Spec:** `docs/superpowers/specs/2026-09-05-model-catalog-effort-suffix-fallback-design.md` (approved after 7 cross-AI review rounds — opencode/xai-grok-4.6 + native Claude Opus, in parallel, each round).

## Global Constraints

- `match_models_dev` itself must gain NO effort-awareness at all — `_strip_known_effort_suffix` is called only from `cli.py`'s new enrichment block, never from inside `model_matcher.py`.
- `allow_fuzzy` defaults to `True` — every existing call site (in particular the primary call in `build_model_catalog`) is unaffected unless it explicitly passes `allow_fuzzy=False`.
- The enrichment retry's result (`md_enrich_match`) must NEVER be assigned into `md_match`, and must never be read by `provider` derivation, canonical `key` derivation, or `md_cost`/pricing — it is consumed exclusively by `_preserved_or_fresh_md_fields` and `_preserved_or_fresh_ctx_window`.
- Both retry attempts pass `allow_fuzzy=False` — fuzzy matching is never used anywhere in the retry, only (unchanged) in the primary call.
- `_EFFORT_TOKENS = {"minimal", "low", "medium", "high", "xhigh", "thinking"}` — bare `"max"` is never a standalone effort token (collides with `qwen-max`/`qwen3-max`); it only strips as the two-token compound `"thinking-max"`.
- No schema migration, no new config surface, no new CLI flags. Single-file-pair change (`model_matcher.py` + `cli.py`).
- Tests live in `tests/test_ai_kit_spec.py` (no new test file) and run via `uv run python3 -m unittest tests.test_ai_kit_spec.<TestClassName> -v` (scoped) or `uv run python3 -m unittest tests.test_ai_kit_spec -v` (whole file). Do **not** use `pytest` — it isn't installed in this project's venv.
- When a field-preservation helper (or the merged catalog entry) clears a field, `merge_catalog_entry`'s clear-on-`None` contract *removes the key entirely* from the returned entry — assert absence with `assertNotIn("<field>", entry)`, never `assertIsNone(entry["<field>"])` (that raises `KeyError`). This does **not** apply to a nested runtime field like `ctx_window` (nested inside `entry["runtimes"][cli_name]`, never top-level-stripped) — that one really does end up as literal `None` and `assertIsNone` is correct there.

---

### Task 1: `_strip_known_effort_suffix` (pure function, `model_matcher.py`)

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Produces: `model_matcher._strip_known_effort_suffix(bare: str) -> str | None` — repeatedly strips trailing reasoning-effort tokens (a single token from `_EFFORT_TOKENS`, or the two-token compound `"thinking-max"`) from a bare model id. Returns the stripped id, or `None` when nothing was stripped. Also produces the module-level constant `model_matcher._EFFORT_TOKENS`.

- [ ] **Step 1: Write the failing tests**

Open `tests/test_ai_kit_spec.py` and insert a new test class immediately before `class TestMatchModelsDev(unittest.TestCase):` (search for that exact line):

```python
class TestStripKnownEffortSuffix(unittest.TestCase):
    def test_strips_a_single_trailing_effort_token(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-high"),
            "claude-opus-5")

    def test_strips_a_two_token_effort_compound(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-xhigh"),
            "claude-opus-5")

    def test_strips_the_thinking_max_compound(self):
        self.assertEqual(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-max"),
            "claude-opus-5")

    def test_no_strippable_trailing_token_returns_none(self):
        self.assertIsNone(model_matcher._strip_known_effort_suffix("claude-opus-5"))

    def test_a_service_tier_suffix_as_trailing_token_is_never_touched(self):
        # "fast" is not a recognized effort word -- the loop never even starts, so this is
        # untouched for a structural reason, not a separate tier denylist.
        self.assertIsNone(
            model_matcher._strip_known_effort_suffix("claude-opus-5-thinking-low-fast"))

    def test_bare_max_without_a_preceding_thinking_token_is_not_stripped(self):
        # Real base model qwen3-max must never be misattributed to "qwen3".
        self.assertIsNone(model_matcher._strip_known_effort_suffix("qwen3-max"))

    def test_a_real_base_model_ending_in_an_effort_word_is_preserved_after_stripping(self):
        # o3-mini-high is a genuine, different-from-o3 model -- "mini" must survive the strip.
        self.assertEqual(model_matcher._strip_known_effort_suffix("o3-mini-high"), "o3-mini")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestStripKnownEffortSuffix -v`
Expected: FAIL with `AttributeError: module 'ai_kit_spec.model_matcher' has no attribute '_strip_known_effort_suffix'` (7 errors).

- [ ] **Step 3: Implement `_strip_known_effort_suffix`**

In `skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py`, insert the following immediately after the end of `_fuzzy_candidate_indices` (after its closing `return [...]` line, before `def match_models_dev(...)`):

```python
_EFFORT_TOKENS = {"minimal", "low", "medium", "high", "xhigh", "thinking"}
# "max" is deliberately NOT a standalone effort token -- it collides with real base-model
# names that end in "-max" (e.g. Alibaba's qwen-max / qwen3-max, a genuinely different,
# smaller-catalog model). It is only ever stripped as part of the two-token compound
# "thinking-max" (Anthropic's own reasoning-effort naming, e.g. "claude-opus-5-thinking-max"),
# never as a bare trailing "-max".


def _strip_known_effort_suffix(bare: str) -> str | None:
    """Repeatedly strips trailing reasoning-EFFORT tokens from a bare model id -- a single
    token from _EFFORT_TOKENS, or the two-token compound "thinking-max". Returns the
    stripped id, or None when nothing was stripped. Vendor-agnostic: OpenAI's own
    reasoning-effort models use the same minimal/low/medium/high vocabulary.

    Safety against crossing a SERVICE-TIER boundary is structural, not a denylist: the loop
    only ever pops a token it positively recognizes as a reasoning-effort word, and stops at
    the first token that isn't one -- a service-tier suffix (`-fast`), a real size/tier
    designation that is simply part of the base model's own name (`-mini`, `-flash`), or
    anything unrecognized is left exactly where it was, never stripped away."""
    parts = bare.split("-")
    stripped_any = False
    while len(parts) > 1:
        last = parts[-1].lower()
        if last == "max" and len(parts) > 2 and parts[-2].lower() == "thinking":
            parts.pop()
            parts.pop()
            stripped_any = True
            continue
        if last in _EFFORT_TOKENS:
            parts.pop()
            stripped_any = True
            continue
        break
    return "-".join(parts) if stripped_any else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestStripKnownEffortSuffix -v`
Expected: `OK` (7 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py tests/test_ai_kit_spec.py
git commit -m "feat(model-matcher): add _strip_known_effort_suffix pure helper

Recognizes a trailing reasoning-effort token (minimal/low/medium/high/xhigh/thinking) or
the two-token thinking-max compound and strips it from a bare model id. Bare \"max\" is
never stripped standalone (qwen-max/qwen3-max collision). Not yet wired into any matching
path -- that's the next task."
```

---

### Task 2: `allow_fuzzy` parameter on `match_models_dev` (`model_matcher.py`)

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing new from Task 1 (independent addition to the same file).
- Produces: `model_matcher.match_models_dev(cli_model_id, models_dev_data, provider_hint=None, allow_fuzzy=True) -> dict | None` — new `allow_fuzzy` keyword-only-by-convention parameter (positional is fine too); when `False`, the pool-fuzzy step (step 3) is skipped entirely, so only the hinted-exact and pool-exact steps run.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ai_kit_spec.py`, insert a new test class immediately after `class TestMatchModelsDev(unittest.TestCase):`'s closing (i.e. right before `class TestMatchArtificialAnalysis(unittest.TestCase):`):

```python
class TestMatchModelsDevAllowFuzzy(unittest.TestCase):
    def test_default_preserves_existing_fuzzy_behavior_unchanged(self):
        # The primary call site in build_model_catalog never passes allow_fuzzy -- the
        # default must keep resolving a fuzzy-only match exactly as it did before this spec.
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {
            "id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}}
        result = model_matcher.match_models_dev("openai/gpt-5.6-sol", fuzzy_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["cost"]["input"], 3.5)

    def test_allow_fuzzy_false_skips_the_pool_fuzzy_step(self):
        fuzzy_data = {"openai": {"models": {"gpt-5.6-sol-2": {
            "id": "gpt-5.6-sol-2", "cost": {"input": 3.5}}}}}
        result = model_matcher.match_models_dev(
            "openai/gpt-5.6-sol", fuzzy_data, allow_fuzzy=False)
        self.assertIsNone(result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestMatchModelsDevAllowFuzzy -v`
Expected: FAIL — `TypeError: match_models_dev() got an unexpected keyword argument 'allow_fuzzy'`.

- [ ] **Step 3: Implement `allow_fuzzy`**

In `skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py`, change `match_models_dev`'s signature and body:

```python
def match_models_dev(cli_model_id: str, models_dev_data: dict,
                      provider_hint: str | None = None,
                      allow_fuzzy: bool = True) -> dict | None:
    """... (existing docstring, unchanged) ..."""
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
    if not matches and allow_fuzzy:
        normalized_bare = _normalize(bare)
        normalized_ids = [_normalize(model_id) for _, model_id, _ in pool]
        matches = [(pool[i][0], pool[i][2]) for i in
                   _fuzzy_candidate_indices(normalized_bare, normalized_ids)]
    if len(matches) == 1:
        provider_key, model = matches[0]
        return {**model, "provider": provider_key}
    if provider_hint:
        hint = _normalize(provider_hint)
        provider_matches = [(provider_key, model) for provider_key, model in matches
                            if _normalize(provider_key) == hint]
        if len(provider_matches) == 1:
            provider_key, model = provider_matches[0]
            return {**model, "provider": provider_key}
    return None
```

(The only change from the current body: `if not matches:` becomes `if not matches and allow_fuzzy:`, plus the new `allow_fuzzy: bool = True` parameter. Everything else is byte-for-byte identical.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestMatchModelsDevAllowFuzzy tests.test_ai_kit_spec.TestMatchModelsDev -v`
Expected: `OK` (2 new + all existing `TestMatchModelsDev` tests, no regressions).

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py tests/test_ai_kit_spec.py
git commit -m "feat(model-matcher): add allow_fuzzy param to match_models_dev

Default True preserves existing behavior for every current call site. When False, skips
the pool-fuzzy step so a caller can force exact-only matching. Not yet consumed by any
caller -- that's the next task."
```

---

### Task 3: Enrichment retry orchestration + field-preservation wiring (`cli.py`)

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `model_matcher._strip_known_effort_suffix` (Task 1), `match_models_dev(..., allow_fuzzy=False)` (Task 2).
- Produces: `build_model_catalog`'s per-candidate loop now computes a local `md_enrich_match: dict | None` after `aa_match`. `_preserved_or_fresh_md_fields` and `_preserved_or_fresh_ctx_window` each gain a new optional `md_enrich_match=None` keyword parameter, consulted only when the primary `md_match` is falsy.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ai_kit_spec.py`, add these test methods to `class TestBuildModelCatalog(unittest.TestCase):` (anywhere inside the class body — e.g. right after `test_matched_candidate_is_enriched_and_added`):

```python
    def test_attempt_1_exact_id_with_hint_resolves_a_cross_provider_collision(self):
        # No effort suffix at all here -- Attempt 1 (exact id + hint) must resolve this on
        # its own, without ever reaching Attempt 2's effort-stripping.
        models_dev_data = {
            "openai": {"models": {"sol": {
                "id": "sol", "tool_call": True, "structured_output": True,
                "limit": {"context": 400000, "output": 128000}}}},
            "some-reseller": {"models": {"sol": {
                "id": "sol", "tool_call": False, "structured_output": None,
                "limit": {"context": 400000, "output": 128000}}}},
        }
        aa_models = [{"id": "1", "slug": "sol", "name": "Sol",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 70.0}}]
        discovered = [{"cli": "codex", "model_id": "sol"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = next(iter(catalog.values()))
        self.assertTrue(entry["tool_calling"])          # openai's row, not some-reseller's
        self.assertTrue(entry["structured_output"])

    def test_attempt_2_strips_the_effort_suffix_and_picks_the_hinted_provider_row(self):
        # Mirrors this spec's own motivating case: the raw id ("claude-opus-5-high") has no
        # exact match anywhere (Attempt 1 -> None, both providers tie on the UNSTRIPPED id
        # only via fuzzy which the primary call also can't use unambiguously), but its
        # effort-stripped base id ("claude-opus-5") collides across two providers whose
        # payloads genuinely disagree on structured_output -- proving the hint picks a
        # SPECIFIC row, not just "a" row from the collision (spec's round-6 safety property).
        models_dev_data = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000}}}},
        }
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertTrue(entry["structured_output"])         # anthropic's row, not the reseller's
        self.assertEqual(entry["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertFalse(entry["source"]["models_dev"])     # enrichment, not an exact match

    def test_attempt_2_never_falls_back_to_fuzzy_matching(self):
        # The stripped id here only fuzzy-matches (a trailing version-token difference) --
        # allow_fuzzy=False on both retry attempts means this must stay unresolved, never a
        # guessed match.
        models_dev_data = {"anthropic": {"models": {"claude-opus-5-2": {
            "id": "claude-opus-5-2", "tool_call": True, "structured_output": True,
            "limit": {"context": 1000000, "output": 128000}}}}}
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertNotIn("tool_calling", entry)
        self.assertNotIn("structured_output", entry)
        self.assertNotIn("max_output_tokens", entry)
        self.assertIsNone(entry["runtimes"]["cursor-agent"]["ctx_window"])

    def test_lifecycle_across_runs_clears_previously_recovered_fields_on_a_later_no_signal_run(self):
        # Round-3's accepted, documented tradeoff (spec Section 3.2): an Artificial Analysis
        # outage on a LATER run clears fields this spec's own enrichment retry recovered on
        # an earlier run -- exactly like today's existing contract for any candidate whose
        # primary match disappears. A second, unrelated candidate whose fields came from a
        # genuine PRIMARY match (never touched md_enrich_match at all) must clear identically,
        # proving the enrichment mechanism doesn't special-case fields it never touched.
        models_dev_data_run1 = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000}}}},
            "openai": {"models": {"gpt-5.6-sol": {
                "id": "gpt-5.6-sol", "tool_call": True, "structured_output": True,
                "limit": {"context": 400000, "output": 128000}}}},
        }
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"},
                      {"cli": "opencode", "model_id": "openai/gpt-5.6-sol"}]
        catalog_run1, _, unmatched_run1 = cli.build_model_catalog(
            discovered, models_dev_data_run1, True, aa_models, True, {})
        self.assertEqual(unmatched_run1, [])
        enriched_key = "anthropic/claude-opus-5-high"      # recovered via this spec's retry
        primary_key = "openai/gpt-5.6-sol"                 # recovered via the ordinary primary match
        self.assertTrue(catalog_run1[enriched_key]["structured_output"])
        self.assertTrue(catalog_run1[primary_key]["structured_output"])

        # Run 2: Artificial Analysis is down (aa_ok=False) and models.dev genuinely no longer
        # lists either model (models_dev_ok=True -- a real, empty re-query, not a skip).
        catalog_run2, _, unmatched_run2 = cli.build_model_catalog(
            discovered, {}, True, [], False, catalog_run1)
        self.assertEqual(unmatched_run2, [])
        for key in (enriched_key, primary_key):
            entry = catalog_run2[key]
            self.assertNotIn("tool_calling", entry)
            self.assertNotIn("structured_output", entry)
            self.assertNotIn("max_output_tokens", entry)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestBuildModelCatalog -v`
Expected: FAIL — the new assertions fail (e.g. `KeyError: 'structured_output'` or a `KeyError` on `catalog["anthropic/claude-opus-5-high"]`, since the enrichment retry doesn't exist yet and these candidates currently route to `unmatched` or a different key). The pre-existing tests in this class must still pass.

- [ ] **Step 3: Implement the retry block and wire it into the field-preservation helpers**

In `skills/ai-kit-spec-review/ai_kit_spec/cli.py`:

**3a.** Add `_strip_known_effort_suffix` to the existing import (line ~34):

```python
from ai_kit_spec.model_matcher import (
    _strip_known_effort_suffix,
    bare_model_part,
    match_artificial_analysis,
    match_models_dev,
)
```

**3b.** In `_preserved_or_fresh_md_fields`, add the `md_enrich_match` parameter and consult it when `md_match` is falsy:

```python
def _preserved_or_fresh_md_fields(md_match: dict | None, models_dev_ok: bool,
                                   existing_entry: dict | None,
                                   md_enrich_match: dict | None = None) -> dict:
    """... (existing docstring, plus:) NEW: md_enrich_match is this spec's effort-suffix
    enrichment retry result (cli.py's build_model_catalog loop) -- consulted ONLY when the
    PRIMARY md_match found nothing this run. It never overrides a real md_match."""
    if not models_dev_ok:
        existing_entry = existing_entry or {}
        return {k: existing_entry[k] for k in
                ("tool_calling", "structured_output", "max_output_tokens")
                if k in existing_entry}
    if md_match:
        return {"tool_calling": md_match.get("tool_call"),
                "structured_output": md_match.get("structured_output"),
                "max_output_tokens": md_match.get("limit", {}).get("output")}
    source = md_enrich_match
    if not source:
        return {"tool_calling": None, "structured_output": None, "max_output_tokens": None}
    return {"tool_calling": source.get("tool_call"),
            "structured_output": source.get("structured_output"),
            "max_output_tokens": source.get("limit", {}).get("output")}
```

**3c.** In `_preserved_or_fresh_ctx_window`, add the same parameter:

```python
def _preserved_or_fresh_ctx_window(md_match: dict | None, models_dev_ok: bool,
                                    existing_entry: dict | None, cli_name: str,
                                    md_enrich_match: dict | None = None):
    """... (existing docstring, plus:) NEW: falls back to md_enrich_match's own context
    limit only when md_match itself is falsy."""
    if not models_dev_ok:
        existing_entry = existing_entry or {}
        return existing_entry.get("runtimes", {}).get(cli_name, {}).get("ctx_window")
    return (md_match or md_enrich_match or {}).get("limit", {}).get("context")
```

**3d.** In `build_model_catalog`'s per-candidate loop, insert the new retry block immediately after the existing `aa_match = (...)` assignment and before `existing_key = _find_existing_key_for_runtime(...)`:

```python
        aa_match = (match_artificial_analysis(model_id, aa_models, provider_hint=provider_hint)
                    if aa_ok else None)
        # NEW: an ENRICHMENT-ONLY retry (design spec 2026-09-05) -- deliberately kept in its
        # own variable, never assigned into md_match itself, and using ONLY the ordinary,
        # unmodified match_models_dev (no effort-awareness lives inside that function at
        # all). Consumed exclusively by the two field-preservation helpers below; never read
        # by provider/key/pricing derivation.
        md_enrich_match = None
        if models_dev_ok and md_match is None and aa_match:
            aa_provider_hint = _slugify(
                (aa_match.get("model_creator") or {}).get("name", "")) or None
            if aa_provider_hint:
                md_enrich_match = match_models_dev(model_id, models_dev_data,
                                                    provider_hint=aa_provider_hint,
                                                    allow_fuzzy=False)
                if md_enrich_match is None:
                    stripped = _strip_known_effort_suffix(bare_model_part(model_id))
                    if stripped:
                        md_enrich_match = match_models_dev(stripped, models_dev_data,
                                                            provider_hint=aa_provider_hint,
                                                            allow_fuzzy=False)
        existing_key = _find_existing_key_for_runtime(existing_catalog, cli_name, model_id)
```

**3e.** Update the two call sites to pass `md_enrich_match` through:

```python
        md_fields = _preserved_or_fresh_md_fields(md_match, models_dev_ok, existing_entry,
                                                   md_enrich_match=md_enrich_match)
```

```python
        ctx_window = _preserved_or_fresh_ctx_window(md_match, models_dev_ok, existing_entry,
                                                      cli_name, md_enrich_match=md_enrich_match)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestBuildModelCatalog -v`
Expected: `OK` (all new tests plus every pre-existing `TestBuildModelCatalog` test, no regressions).

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/cli.py tests/test_ai_kit_spec.py
git commit -m "feat(model-catalog): add effort-suffix enrichment retry to build_model_catalog

Adds an enrichment-only retry (md_enrich_match) that tries an exact hinted match on the
raw id, then on its effort-stripped form, both exact-only (allow_fuzzy=False). Wires it
into _preserved_or_fresh_md_fields/_preserved_or_fresh_ctx_window as a new optional
parameter, consulted only when the primary md_match is None. Never touches
provider/key/pricing derivation."
```

---

### Task 4: Invariant and end-to-end regression tests

**Files:**
- Test: `tests/test_ai_kit_spec.py`

No production code changes in this task — these tests exercise invariants the spec calls out explicitly (§4, bullets 5-6) that Task 3's fixtures don't yet cover: `md_enrich_match`'s structural inertness on provider/key derivation even when its own resolved provider disagrees with the hint, pricing coming from AA (never the base model's models.dev cost), a vendor-prefixed id also reaching the retry, and a combined regression fixture mirroring the real motivating case alongside its `-fast` sibling.

**Interfaces:**
- Consumes: `cli.build_model_catalog` (Task 3), `model_catalog.canonical_key` (existing).

- [ ] **Step 1: Write the failing tests**

Add these test methods to `class TestBuildModelCatalog(unittest.TestCase):` in `tests/test_ai_kit_spec.py`:

```python
    def test_md_enrich_match_provider_field_never_influences_provider_or_key_derivation(self):
        # md_enrich_match's OWN "provider" field can legitimately differ from
        # aa_provider_hint (a single, non-colliding models.dev row always wins regardless of
        # hint) -- this must never leak into provider/key derivation, which read only
        # md_match/provider_hint/AA's model_creator.name. Uses a raw id
        # ("claude-opus-5-thinking-xhigh") whose fuzzy ratio against the single stripped-form
        # candidate ("claude-opus-5") is ~0.63 -- well under the PRIMARY call's own 0.82
        # threshold -- so the primary call cannot resolve this on its own; only the retry's
        # exact match on the STRIPPED id (Attempt 2) can. (Verified against a real 16-provider
        # single-row-per-provider case would behave the same way, but a single provider is
        # enough to isolate this specific invariant.)
        models_dev_data = {"some-other-provider": {"models": {"claude-opus-5": {
            "id": "claude-opus-5", "tool_call": True, "structured_output": True,
            "limit": {"context": 1000000, "output": 128000}}}}}
        aa_models = [{"id": "1", "slug": "claude-opus-5-thinking-xhigh",
                      "name": "Claude Opus 5 Thinking XHigh",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-thinking-xhigh"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        self.assertIn("anthropic/claude-opus-5-thinking-xhigh", catalog)
        entry = catalog["anthropic/claude-opus-5-thinking-xhigh"]
        self.assertEqual(entry["provider"], "anthropic")   # from AA's model_creator, not
        self.assertTrue(entry["structured_output"])        # "some-other-provider"

    def test_pricing_after_a_successful_retry_still_comes_from_aa_never_the_base_models_cost(self):
        # A real multi-provider collision on the STRIPPED id ("claude-opus-5") is required
        # so the PRIMARY call (no hint, fuzzy-enabled) can't resolve the raw suffixed id on
        # its own -- with only one provider, a single fuzzy match would win regardless of
        # hint AT THE PRIMARY STAGE, meaning pricing would legitimately come from that
        # primary match's own models.dev cost instead of exercising this spec's
        # enrichment-only retry at all.
        models_dev_data = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 6.0, "output": 30.0}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 0.0, "output": 0.0}}}},
        }
        aa_models = [{"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
                      "model_creator": {"name": "Anthropic"},
                      "evaluations": {"artificial_analysis_intelligence_index": 61.5},
                      "pricing": {"price_1m_input_tokens": 15.0,
                                  "price_1m_output_tokens": 75.0}}]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"}]
        catalog, _, _ = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        entry = catalog["anthropic/claude-opus-5-high"]
        self.assertEqual(entry["pricing"]["input_per_1m"], 15.0)   # AA's effort-specific price
        self.assertEqual(entry["pricing"]["output_per_1m"], 75.0)  # never the base model's 6.0/30.0

    def test_vendor_prefixed_id_with_an_effort_suffix_also_reaches_the_retry(self):
        # A prefixed id doesn't skip the need for this fallback either -- step 1's exact
        # lookup misses the suffix exactly as the bare case does, and the pool-fuzzy step
        # also finds nothing for this example (ratio("gpt5high","gpt5") ~= 0.667, well under
        # the 0.82 threshold).
        models_dev_data = {"openai": {"models": {"gpt-5": {
            "id": "gpt-5", "tool_call": True, "structured_output": True,
            "limit": {"context": 400000, "output": 128000}}}}}
        aa_models = [{"id": "1", "slug": "gpt-5-high", "name": "GPT-5 High",
                      "model_creator": {"name": "OpenAI"},
                      "evaluations": {"artificial_analysis_intelligence_index": 70.0}}]
        discovered = [{"cli": "opencode", "model_id": "openai/gpt-5-high"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["openai/gpt-5-high"]
        self.assertTrue(entry["structured_output"])
        self.assertEqual(entry["runtimes"]["opencode"]["ctx_window"], 400000)

    def test_end_to_end_regression_claude_opus_5_high_shape_and_its_fast_sibling(self):
        # Regression fixture mirroring the real motivating case: claude-opus-5-high
        # backfills via this spec's retry; its -fast-suffixed sibling
        # (claude-opus-5-high-fast) resolves via the PRIMARY call's own fuzzy step directly
        # (never reaching this spec's retry at all) and must never have its price/context
        # conflated with the non-fast base model's.
        models_dev_data = {
            "anthropic": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 6.0, "output": 30.0}}}},
            "some-reseller": {"models": {"claude-opus-5": {
                "id": "claude-opus-5", "tool_call": True, "structured_output": None,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 0.0, "output": 0.0}}}},
            "venice": {"models": {"claude-opus-5-fast": {
                "id": "claude-opus-5-fast", "tool_call": True, "structured_output": True,
                "limit": {"context": 1000000, "output": 128000},
                "cost": {"input": 12.0, "output": 60.0}}}},
        }
        aa_models = [
            {"id": "1", "slug": "claude-opus-5-high", "name": "Claude Opus 5 High",
             "model_creator": {"name": "Anthropic"},
             "evaluations": {"artificial_analysis_intelligence_index": 61.5},
             "pricing": {"price_1m_input_tokens": 15.0, "price_1m_output_tokens": 75.0}},
            {"id": "2", "slug": "claude-opus-5-high-fast", "name": "Claude Opus 5 High Fast",
             "model_creator": {"name": "Anthropic"},
             "evaluations": {"artificial_analysis_intelligence_index": 61.5},
             "pricing": {"price_1m_input_tokens": 30.0, "price_1m_output_tokens": 150.0}},
        ]
        discovered = [{"cli": "cursor-agent", "model_id": "claude-opus-5-high"},
                      {"cli": "cursor-agent", "model_id": "claude-opus-5-high-fast"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])

        base = catalog["anthropic/claude-opus-5-high"]
        self.assertTrue(base["structured_output"])              # anthropic's row, not the reseller's
        self.assertEqual(base["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertFalse(base["source"]["models_dev"])          # enrichment, not an exact match
        self.assertEqual(base["scores"]["intelligence_index"], 61.5)
        self.assertEqual(base["pricing"]["input_per_1m"], 15.0)  # AA's, never models.dev's 6.0

        fast = catalog["venice/claude-opus-5-high-fast"]
        self.assertTrue(fast["source"]["models_dev"])           # resolved by the PRIMARY fuzzy step
        self.assertEqual(fast["runtimes"]["cursor-agent"]["ctx_window"], 1000000)
        self.assertEqual(fast["pricing"]["input_per_1m"], 12.0)  # its own tier's price, not the
                                                                  # base model's 6.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestBuildModelCatalog -v`

If Task 3 was implemented exactly as specified, these should actually all **pass already** (this task adds coverage, not new behavior). Run them first to confirm; if any fails, that's a real gap in Task 3's implementation to fix now — do not weaken these assertions to make them pass.

- [ ] **Step 3: (Only if Step 2 found a real gap) fix `cli.py`**

Diagnose against the exact assertion that failed and Task 3's code — do not add new mechanisms beyond what Task 3 already specifies; a failure here almost certainly means Task 3's edit was applied incorrectly (e.g. a typo, a missed call-site update) rather than a genuine missing feature.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestBuildModelCatalog -v`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ai_kit_spec.py
git commit -m "test(model-catalog): add invariant + end-to-end regression coverage

Covers md_enrich_match's structural inertness on provider/key derivation, pricing always
coming from AA (never the base model's models.dev cost) after a successful retry, a
vendor-prefixed id also reaching the retry, and a combined regression fixture mirroring
the real claude-opus-5-high / claude-opus-5-high-fast shape."
```

---

### Task 5: Full-suite verification

**Files:** none modified — verification only.

- [ ] **Step 1: Run the full `ai_kit_spec` test file**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -40`
Expected: `OK`, with the total test count higher than before this plan (Task 1: +7, Task 2: +2, Task 3: +4, Task 4: +4 = 17 new tests) and zero failures/errors anywhere in the file (not just the classes touched by this plan — a regression in an unrelated class would mean an import or shared-fixture mistake).

- [ ] **Step 2: Run the project's full test suite**

Run: `uv run make test 2>&1 | tail -60`
Expected: `OK` across every test module the Makefile's `test` target runs (`test_setup`, `test_status_line`, `test_external_segments`, `test_statusline_doctor`, `test_arch`, `test_markdown_to_pdf`, `test_worktree_e2e`, `test_wizard_pty`, `test_system_memory_e2e`, `test_ai_kit_spec`, `test_ai_kit_spec_gsd`) — confirms this plan's changes to shared modules (`model_matcher.py`, `cli.py`) haven't broken anything outside `ai_kit_spec`'s own test file.

- [ ] **Step 3: Manual smoke check against a bare-metal invocation (optional but recommended)**

If a real `models-dev` cache and Artificial Analysis credentials are available in this environment, run:

```bash
cd skills/ai-kit-spec-review
python3 ai-kit-spec.py fetch-model-catalog \
  --runtimes-json <path to a real detect-runtimes snapshot> \
  --catalog-path <scratch path>.json
```

and inspect the resulting catalog's `anthropic/claude-opus-5-high` entry (or whatever the real installed effort-suffixed model is) for a non-null `context_window`/`tool_calling`. Skip this step if no real credentials/cache are available in this environment — the unit test suite above is the authoritative verification.

No commit for this task (verification only).
