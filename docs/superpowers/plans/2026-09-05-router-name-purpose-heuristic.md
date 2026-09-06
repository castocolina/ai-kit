# Router/Gateway Name-Declared Purpose Heuristic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A router/gateway CLI candidate whose raw model id already declares its purpose in plain words (e.g. `router-env-plan-review`, `router-env-coding`) gets that purpose recorded as `name_declared_purpose`, skips `match_models_dev`/`match_artificial_analysis` entirely, and is presented directly under its declared list by the `ai-kit-spec-config` wizard — never scored, never at risk of landing in the wrong REVIEW/EXECUTE list.

**Architecture:** A new pure heuristic `infer_purpose_from_name` (`model_heuristics.py`) mirrors the existing `infer_is_router`/`infer_batch_mode`/`infer_fallback_quota` pattern — no network, string-matching only, and gated externally by callers on `infer_is_router` (never runs on a non-router candidate). `build_model_catalog` (`cli.py`) checks this at the very top of its per-candidate loop, before the existing `md_match`/`aa_match` calls; when it fires, the candidate takes a self-contained short-circuit path that derives `provider`/`key` from cache or the id's own vendor prefix (never from an external match), reuses the existing `_preserved_or_fresh_*` helpers with `models_dev_ok=False`/`aa_ok=False` to inherit their preserve-on-not-queried contract for free, and `continue`s before the existing body ever runs. The wizard (`ai-kit-spec-config/SKILL.md`) partitions ranking candidates by this new field before calling `score_candidates`, presenting name-declared entries directly under their declared list.

**Tech Stack:** Python 3.12, stdlib only, `unittest` (no pytest — `uv run python3 -m unittest`).

**Spec:** `docs/superpowers/specs/2026-09-05-router-name-purpose-heuristic-design.md`

## Global Constraints

- `infer_purpose_from_name` takes a bare `model_id: str` and returns `"review"`, `"execute"`, or `None` — it does NOT call `infer_is_router` itself; every caller gates on `infer_is_router` externally first.
- `_PURPOSE_NAME_HINTS` is exactly `{"review": ("review", "plan-review"), "execute": ("coding", "execute")}` — no additional tokens. `"plan-review"` is retained for documentation purposes only (it names the concrete operator-facing convention the design spec calls out, e.g. `router-env-plan-review`) — it is a strict substring superset of `"review"`, so under the `\b`-bounded matching below it can never change `infer_purpose_from_name`'s result versus `"review"` alone. `test_plan_review_hint_matches` (Task 1) therefore cannot fail independently of `test_review_hint_matches`; it exists to pin the documented convention in the test suite as an example, not to add independent coverage of the hint table.
- Every hint match in `infer_purpose_from_name` MUST be delimiter-bounded (`\b`-anchored regex via a `_hint_matches(hint, lowered)` helper — `re.search(rf"\b{re.escape(hint)}\b", lowered)`), never a raw `in` substring check. A raw substring check would let `"review"` fire inside `"preview"` (e.g. `router-env/gemini-3-pro-preview` would be wrongly declared review-purpose) and `"coding"` fire inside `"encoding"` — this is the exact defect an earlier draft of the underlying design had, fixed before this plan's Task 1.
- Both hint groups matching (a naming contradiction) returns `None`, same as neither matching.
- `build_model_catalog`'s existing body (from `md_match = match_models_dev(...)` onward) is never modified — the new logic is a pure prepend that `continue`s before reaching it. The effort-suffix-fallback logic (`md_enrich_match`) must remain byte-for-byte unchanged.
- A name-declared candidate must NEVER have `match_models_dev`/`match_artificial_analysis` called for it, under any circumstance — verified directly in tests (fixtures that WOULD match if queried, proving the entry's fields show no trace of that data), never just inferred from output shape.
- `name_declared_purpose` is optional on a catalog entry, defaults to absent, one of `"review"`/`"execute"` when present, and its presence/absence never changes validation behavior for any entry that doesn't set it.
- Tests live in `tests/test_ai_kit_spec.py` (no new test file), run via `uv run python3 -m unittest tests.test_ai_kit_spec.<TestClassName> -v` (scoped) or `uv run python3 -m unittest tests.test_ai_kit_spec -v` (whole file). Do **not** use `pytest`.
- Single-file-set change: `model_heuristics.py`, `cli.py`, `model_catalog.py`, `ai-kit-spec-config/SKILL.md`, plus tests. No new CLI flags, no schema migration.
- `name_declared_purpose` carried onto the `unmatched` payload (Task 3, bare-id-no-provider path) has no consumer added in this plan — `ai-kit-spec-config/SKILL.md` item 4's unmatched-confirmation flow is NOT modified to read or persist it. This is intentional, forward-compat-only scope: the field is preserved so a future change can wire it up without redesigning the payload shape, but this plan does not act on it once a candidate lands in `unmatched`. Only the catalog-entry path (Task 4's wizard partition) consumes `name_declared_purpose` in this change.
- A gateway-prefixed real (non-router) vendor model whose name happens to contain a purpose word (e.g. an `openrouter/<vendor>/<model>`-shaped id where `<vendor>` or the provider hint matches a router token, and `<model>`'s own name contains "review"/"coding"/"execute") is accepted as an over-trigger risk in this plan: `infer_is_router` gates on the id/provider hint, not on "is this candidate actually a router *endpoint* vs. a real model routed *through* a gateway," so such a model would skip `match_models_dev`/`match_artificial_analysis` and permanently lose its scores/ctx/pricing. This is a known, accepted limitation of the router-detection heuristic this plan builds on (unchanged from `infer_is_router`'s existing behavior) — not introduced by this plan and not fixed by it. No test pins this specific gateway-prefixed-real-vendor case; Task 3's tests cover the router/non-router boundary `infer_is_router` already draws, not this edge of it.

---

### Task 1: `infer_purpose_from_name` (pure heuristic, `model_heuristics.py`)

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Produces: `model_heuristics.infer_purpose_from_name(model_id: str) -> str | None`, and the module-level constant `model_heuristics._PURPOSE_NAME_HINTS`.

- [ ] **Step 1: Write the failing tests**

Open `tests/test_ai_kit_spec.py` and insert a new test class immediately after `class TestInferFallbackQuota(unittest.TestCase):`'s last method (search for `class TestInferFallbackQuota` — its two methods are `test_matches_wherever_is_router_matches` and `test_plain_vendor_name_does_not_match`; insert this new class right after that second method, before whatever class comes next):

```python
class TestInferPurposeFromName(unittest.TestCase):
    def test_review_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-review"), "review")

    def test_plan_review_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-plan-review"), "review")

    def test_coding_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-coding"), "execute")

    def test_execute_hint_matches(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("router-env-execute"), "execute")

    def test_no_hint_returns_none(self):
        self.assertIsNone(model_heuristics.infer_purpose_from_name("router-env-fast"))

    def test_both_groups_matching_is_a_contradiction_returns_none(self):
        # A naming contradiction (both a review word and an execute word) must never be
        # silently resolved by picking one.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env-coding-review"))

    def test_case_insensitive(self):
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("Router-Env-Coding"), "execute")

    def test_hint_word_need_not_be_trailing(self):
        # A router operator's naming convention isn't guaranteed to put the purpose word
        # last -- token match anywhere in the id, not suffix-only.
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("review-router-env"), "review")

    def test_review_does_not_match_inside_preview(self):
        # Delimiter-boundary pin: "review" is a substring of "preview", but the "r" in
        # "review" is preceded by "p" (a word character), so no \b boundary exists there --
        # this must NOT match. Without the \b-bounded fix, this would wrongly return
        # "review", silently discarding a legitimate router-exposed model's real enrichment.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env/gemini-3-pro-preview"))

    def test_coding_does_not_match_inside_encoding(self):
        # Same class of false positive for the execute group: "coding" is a substring of
        # "encoding" but not a delimiter-bounded token there.
        self.assertIsNone(
            model_heuristics.infer_purpose_from_name("router-env/some-encoding-model"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestInferPurposeFromName -v`
Expected: FAIL with `AttributeError: module 'ai_kit_spec.model_heuristics' has no attribute 'infer_purpose_from_name'` (10 errors).

- [ ] **Step 3: Implement `infer_purpose_from_name`**

First, confirm the top of `skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py` already
has `import re`; if it doesn't (check the live file — as of this plan's revision it does NOT),
add `import re` at the top of the file alongside its existing imports.

Then, in `skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py`, append the following at
the end of the file (after `infer_fallback_quota`'s closing line):

```python
_PURPOSE_NAME_HINTS = {
    "review": ("review", "plan-review"),
    "execute": ("coding", "execute"),
}


def _hint_matches(hint: str, lowered: str) -> bool:
    """Delimiter-bounded match: `hint` must not be embedded inside a larger
    alphanumeric run. Plain substring matching would let "review" fire on
    "preview" or "coding" fire on "encoding" -- both real router/gateway
    naming collisions, not purpose declarations."""
    return re.search(rf"\b{re.escape(hint)}\b", lowered) is not None


def infer_purpose_from_name(model_id: str) -> str | None:
    """Only meaningful for a candidate ALREADY confirmed as a router/gateway via
    infer_is_router -- this function does not check is_router itself (keeps the two
    heuristics independently testable/composable; every caller gates on infer_is_router
    first). Checks for an explicit, unambiguous purpose word in the id, as a
    delimiter-bounded token (never a raw substring): "review"/"plan-review" -> "review";
    "coding"/"execute" -> "execute". Returns None when neither group matches, OR when both
    do (a genuine naming contradiction must never be silently resolved by picking one) --
    callers that get None fall through to the ordinary external-matching path, exactly as
    if this heuristic didn't exist."""
    lowered = model_id.lower()
    is_review = any(_hint_matches(h, lowered) for h in _PURPOSE_NAME_HINTS["review"])
    is_execute = any(_hint_matches(h, lowered) for h in _PURPOSE_NAME_HINTS["execute"])
    if is_review == is_execute:   # neither matched, or both did (contradiction) -> None
        return None
    return "review" if is_review else "execute"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestInferPurposeFromName -v`
Expected: `OK` (10 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py tests/test_ai_kit_spec.py
git commit -m "feat(model-heuristics): add infer_purpose_from_name pure heuristic

Recognizes an explicit review/coding purpose word in a model id -- meant to be called
only after infer_is_router already confirmed the candidate is a router/gateway (this
function does not check is_router itself). A naming contradiction (both hint groups
match) returns None, same as neither matching. Not yet wired into any caller -- that's
the next task."
```

---

### Task 2: `name_declared_purpose` catalog field (`model_catalog.py`)

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: nothing new from Task 1 (independent addition to a different file).
- Produces: `model_catalog._VALID_NAME_DECLARED_PURPOSE = {"review", "execute"}`; `validate_catalog_entry` now rejects a present-but-invalid `name_declared_purpose` value.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ai_kit_spec.py`, add these methods to `class TestValidateCatalogEntry(unittest.TestCase):` (anywhere inside the class body — e.g. right after `test_unrecognized_confidence_value_is_rejected`; that class already has a `_valid_entry(self, **overrides)` helper returning a minimal valid entry dict, used here unchanged):

```python
    def test_unrecognized_name_declared_purpose_value_is_rejected(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="planning"))
        self.assertIsNotNone(reason)
        self.assertIn("name_declared_purpose", reason)

    def test_review_name_declared_purpose_is_accepted(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="review"))
        self.assertIsNone(reason)

    def test_execute_name_declared_purpose_is_accepted(self):
        reason = model_catalog.validate_catalog_entry(
            "x", self._valid_entry(name_declared_purpose="execute"))
        self.assertIsNone(reason)

    def test_absent_name_declared_purpose_is_never_rejected(self):
        reason = model_catalog.validate_catalog_entry("x", self._valid_entry())
        self.assertIsNone(reason)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestValidateCatalogEntry -v`
Expected: `test_unrecognized_name_declared_purpose_value_is_rejected` FAILS (`self.assertIsNotNone(reason)` fails because `reason` is `None` — the field isn't checked yet). The other three pass already (an unrecognized field is currently left unchecked, so `review`/`execute`/absent all already return `None`) — this is expected; only the rejection test is red.

- [ ] **Step 3: Implement the field check**

In `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`, add a new constant immediately after the line `_RUNTIME_FIELD_TYPES = {"model_id": str, "ctx_window": (int, float)}` (line 37 — three lines below `_FIELD_TYPES`'s closing `}` at line 32, itself following `_NUMERIC_SUBFIELD_TABLES` at lines 33-36):

```python
_VALID_NAME_DECLARED_PURPOSE = {"review", "execute"}
```

Add `"name_declared_purpose": str` to the `_FIELD_TYPES` dict (anywhere in the dict body, e.g. right after `"speed_tier": str,`).

Then, in `validate_catalog_entry`, add the literal-value check **immediately after the existing generic `_FIELD_TYPES` loop** (`for field, expected_type in _FIELD_TYPES.items(): ...`, ending with the `return f"{model_id}: '{field}' must be of type {expected_type}"` line) and **before** the `reasoning_modes` check that follows it:

```python
    if "name_declared_purpose" in entry and entry["name_declared_purpose"] is not None \
            and entry["name_declared_purpose"] not in _VALID_NAME_DECLARED_PURPOSE:
        return (f"{model_id}: 'name_declared_purpose' must be one of "
                f"{sorted(_VALID_NAME_DECLARED_PURPOSE)}")
```

Ordering matters here, and it runs the OPPOSITE direction from an earlier draft of this step: the generic `_FIELD_TYPES` loop runs FIRST (because it appears first in the function, and this check is placed after it, not before). A non-string `name_declared_purpose` (e.g. a list or int) is therefore already rejected by that loop's `isinstance(entry[field], expected_type)` check — with a `'name_declared_purpose' must be of type <class 'str'>` message — before this literal-value check ever runs. By the time this check executes, `entry["name_declared_purpose"]` is guaranteed to be either absent, `None`, or an actual `str` — never a list, int, or other type that would raise `TypeError` out of the `not in _VALID_NAME_DECLARED_PURPOSE` membership test. Placing this check BEFORE the `_FIELD_TYPES` loop (as an earlier draft did) would let a non-string value reach the membership test first and crash with `TypeError: unhashable type` instead of returning the intended rejection reason — do not place it there.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestValidateCatalogEntry -v`
Expected: `OK` (all 4 new tests plus every pre-existing `TestValidateCatalogEntry` test, no regressions).

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py tests/test_ai_kit_spec.py
git commit -m "feat(model-catalog): add name_declared_purpose optional catalog field

Optional per-entry field, one of 'review'/'execute' when present. An absent value is
never a validation failure, consistent with every other optional field. Not yet
written by any caller -- that's the next task."
```

---

### Task 3: Wire the heuristic into `build_model_catalog` (`cli.py`)

**Files:**
- Modify: `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- Test: `tests/test_ai_kit_spec.py`

**Interfaces:**
- Consumes: `model_heuristics.infer_purpose_from_name` (Task 1), `model_catalog`'s `name_declared_purpose` field (Task 2, no code call needed — just a recognized key), the already-imported `infer_is_router` (`cli.py` already imports it: `from ai_kit_spec.model_heuristics import infer_batch_mode, infer_fallback_quota, infer_is_router`), `canonical_key`/`merge_catalog_entry` (already imported), `bare_model_part` (already imported), `_find_existing_key_for_runtime`/`_infer_heuristics`/`_preserved_or_fresh_md_fields`/`_preserved_or_fresh_aa_fields`/`_preserved_or_fresh_ctx_window` (all already defined earlier in `cli.py`, unchanged).
- Produces: `build_model_catalog`'s per-candidate loop now short-circuits before `md_match`/`aa_match` for any candidate where the new logic fires; the resulting catalog entry carries `name_declared_purpose` when applicable. A name-declared candidate that has no resolvable provider (bare id, no existing catalog entry to recover one from) lands in the `unmatched` list as before, but its dict now also carries `name_declared_purpose` — the ONLY change to the `unmatched` payload shape in this task — so the declaration is never silently lost before Task 4's wizard partition (which only inspects catalog entries) or the unmatched-confirmation flow can see it.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ai_kit_spec.py`, add these test methods to `class TestBuildModelCatalog(unittest.TestCase):` (anywhere inside the class body — e.g. right after `test_matched_candidate_is_enriched_and_added`):

```python
    def test_router_candidate_with_coding_hint_never_calls_external_matching(self):
        # models_dev_data/aa_models both contain an EXACT match for this candidate's bare id --
        # if match_models_dev/match_artificial_analysis were called, source.models_dev and
        # source.artificial_analysis would come back True and tool_calling/scores would be
        # populated. Proving they stay False/absent proves the lookup never ran.
        models_dev_data = {"opencode-go": {"models": {"router-env-coding": {
            "id": "router-env-coding", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        aa_models = [{"id": "1", "slug": "router-env-coding", "name": "Router Env Coding",
                      "model_creator": {"name": "SomeVendor"},
                      "evaluations": {"artificial_analysis_coding_index": 89.0}}]
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-coding"}]
        catalog, rejections, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, aa_models, True, {})
        self.assertEqual(rejections, [])
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding"]
        self.assertEqual(entry["name_declared_purpose"], "execute")
        self.assertFalse(entry["source"]["models_dev"])
        self.assertFalse(entry["source"]["artificial_analysis"])
        self.assertNotIn("tool_calling", entry)
        self.assertNotIn("scores", entry)

    def test_router_candidate_with_review_hint_gets_review_purpose(self):
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-plan-review"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-plan-review"]
        self.assertEqual(entry["name_declared_purpose"], "review")

    def test_router_candidate_with_no_purpose_word_takes_the_unchanged_normal_path(self):
        # "router-env-fast" is a router (infer_is_router matches "-env") but has no purpose
        # word -- infer_purpose_from_name returns None, so this must fall through to ordinary
        # md_match/aa_match matching, unaffected by this feature.
        models_dev_data = {"opencode-go": {"models": {"router-env-fast": {
            "id": "router-env-fast", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-fast"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-fast"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])   # normal matching DID run
        self.assertTrue(entry["tool_calling"])

    def test_non_router_candidate_with_a_purpose_word_in_its_name_is_unaffected(self):
        # A real vendor model whose name happens to contain "coding" must never trigger this
        # heuristic -- infer_is_router gates it, and this id matches none of
        # _ROUTER_NAME_HINTS ("router", "-env", "local-llm").
        models_dev_data = {"openai": {"models": {"gpt-5-coding-assistant": {
            "id": "gpt-5-coding-assistant", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        discovered = [{"cli": "codex", "model_id": "openai/gpt-5-coding-assistant"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["openai/gpt-5-coding-assistant"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])
        self.assertTrue(entry["tool_calling"])

    def test_lifecycle_preserves_prior_cached_fields_across_a_later_name_declared_run(self):
        # A candidate already in the catalog (e.g. from before this feature existed, or from a
        # manual correction) keeps its cached ctx_window/pricing/tool_calling when a LATER run
        # recognizes it as name-declared-purpose -- the new code path must never clear fields
        # it didn't itself populate, exactly like every other preserve-on-not-queried path in
        # this function.
        existing_catalog = {"opencode-go/router-env-coding": {
            "provider": "opencode-go",
            "runtimes": {"opencode": {"model_id": "opencode-go/router-env-coding",
                                       "ctx_window": 128000}},
            "is_router": True, "batch_mode": False, "fallback_quota": True,
            "tool_calling": True, "structured_output": True, "max_output_tokens": 8000,
            "pricing": {"input_per_1m": 1.0, "output_per_1m": 2.0},
            "source": {"models_dev": True, "artificial_analysis": False, "manual": False},
            "confidence": "high", "last_verified": "2026-08-01"}}
        # models_dev_data/aa_models both WOULD match if queried -- proving they weren't.
        models_dev_data = {"opencode-go": {"models": {"router-env-coding": {
            "id": "router-env-coding", "tool_call": False, "structured_output": False,
            "limit": {"context": 9999, "output": 9999}}}}}
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-coding"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, existing_catalog)
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding"]
        self.assertEqual(entry["name_declared_purpose"], "execute")
        self.assertEqual(entry["runtimes"]["opencode"]["ctx_window"], 128000)
        self.assertTrue(entry["tool_calling"])
        self.assertTrue(entry["structured_output"])
        self.assertEqual(entry["max_output_tokens"], 8000)
        self.assertEqual(entry["pricing"]["input_per_1m"], 1.0)
        self.assertTrue(entry["source"]["models_dev"])   # preserved from cache, not re-derived

    def test_router_candidate_with_contradictory_purpose_words_falls_through_to_normal_matching(self):
        # design spec Section 5(c): a naming CONTRADICTION (both a review word and an execute
        # word present) must fall through to the unchanged md_match/aa_match path, exactly like
        # the no-purpose-word case above -- verified here at the WIRING level (build_model_catalog
        # itself), not just at infer_purpose_from_name's own unit level (Task 1), since it's the
        # wiring's job to actually route on the heuristic's None result.
        models_dev_data = {"opencode-go": {"models": {"router-env-coding-review": {
            "id": "router-env-coding-review", "tool_call": True, "structured_output": True,
            "limit": {"context": 128000, "output": 8000}}}}}
        discovered = [{"cli": "opencode", "model_id": "opencode-go/router-env-coding-review"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, models_dev_data, True, [], True, {})
        self.assertEqual(unmatched, [])
        entry = catalog["opencode-go/router-env-coding-review"]
        self.assertNotIn("name_declared_purpose", entry)
        self.assertTrue(entry["source"]["models_dev"])   # normal matching DID run
        self.assertTrue(entry["tool_calling"])

    def test_name_declared_bare_id_with_no_provider_lands_in_unmatched_with_purpose_carried(self):
        # The short-circuit's only failure path: a name-declared router candidate reported as a
        # BARE id (no "<vendor>/" prefix -- e.g. a CLI that reports its own raw model name) with
        # no existing catalog entry to recover a provider from. It must land in `unmatched` with
        # `vendor_unknown: True` (same convention as the ordinary unmatched path), AND it must
        # still carry `name_declared_purpose` on that payload -- otherwise the wizard's Task 4
        # partition, which only inspects catalog entries, would silently lose the declaration
        # for any candidate that never makes it into the catalog.
        discovered = [{"cli": "customcli", "model_id": "router-env-coding"}]
        catalog, _, unmatched = cli.build_model_catalog(
            discovered, {}, True, [], True, {})
        self.assertEqual(catalog, {})
        self.assertEqual(len(unmatched), 1)
        candidate = unmatched[0]
        self.assertTrue(candidate["vendor_unknown"])
        self.assertIsNone(candidate["provider"])
        self.assertEqual(candidate["name_declared_purpose"], "execute")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestBuildModelCatalog -v`
Expected (four of the seven new tests are RED; three are already green):

- `test_router_candidate_with_coding_hint_never_calls_external_matching` FAILS with
  `KeyError: 'name_declared_purpose'` at `entry["name_declared_purpose"]` — the field is
  never set yet, and today's unchanged code actually calls `match_models_dev`/
  `match_artificial_analysis` for this candidate and finds a real match for both (its
  fixture is an intentional exact match, to prove the post-change code stops using it).
- `test_router_candidate_with_review_hint_gets_review_purpose` FAILS, but NOT with
  `KeyError` — today's unchanged code has no name-declared short-circuit, so with
  `models_dev_data={}` and `aa_models=[]` neither source matches, there is no existing
  catalog entry to recover a key from, and the candidate falls through to
  `unmatched.append(...)` at the routing check in `build_model_catalog` (the `provider
  is None or (md_match is None and aa_match is None and existing_entry is None)`
  branch — `provider_hint` here still resolves to `"opencode-go"` from the id's own
  `<vendor>/` prefix, but that alone doesn't stop the `existing_entry is None` clause
  from being true). The test fails at `self.assertEqual(unmatched, [])`, since
  `unmatched` is `[{"cli": "opencode", ...}]`, not `[]` — it never reaches the
  `entry["name_declared_purpose"]` line at all.
- `test_lifecycle_preserves_prior_cached_fields_across_a_later_name_declared_run` FAILS
  with `KeyError: 'name_declared_purpose'` at the same line as the first test, for the
  same reason (field doesn't exist pre-change) — do NOT treat this as a passing
  guard/regression test. If that assertion were removed, the remaining assertions would
  ALSO fail: today's unchanged code finds a real `md_match` for this fixture's
  `"router-env-coding"` (models_dev_ok=True) and treats it as a genuine fresh match, so
  `_preserved_or_fresh_md_fields`/`_preserved_or_fresh_ctx_window` overwrite the cached
  `tool_calling`/`structured_output`/`ctx_window` with this run's fixture values
  (`False`/`False`/`9999`) instead of preserving the existing entry's `True`/`True`/
  `128000` — proving today's code does NOT already implement the short-circuit's
  preserve-cache behavior.
- `test_name_declared_bare_id_with_no_provider_lands_in_unmatched_with_purpose_carried`
  FAILS with `KeyError: 'name_declared_purpose'` at `candidate["name_declared_purpose"]`
  — today's unchanged `unmatched.append(...)` payload has no such key (the field is only
  ever added by this task's new short-circuit block).
- `test_router_candidate_with_no_purpose_word_takes_the_unchanged_normal_path`,
  `test_non_router_candidate_with_a_purpose_word_in_its_name_is_unaffected`, and
  `test_router_candidate_with_contradictory_purpose_words_falls_through_to_normal_matching`
  already PASS against today's unchanged code — these three are genuine guard/regression
  tests (each only asserts `assertNotIn("name_declared_purpose", entry)`, which is
  trivially true when the field doesn't exist yet, plus that ordinary matching ran)
  proving the existing path is untouched; do not treat their passing before Step 3 as a
  mistake.

- [ ] **Step 3: Implement the short-circuit**

In `skills/ai-kit-spec-review/ai_kit_spec/cli.py`:

**3a.** Change the existing import line (currently `from ai_kit_spec.model_heuristics import
infer_batch_mode, infer_fallback_quota, infer_is_router`) to also import the new function:

```python
from ai_kit_spec.model_heuristics import (
    infer_batch_mode,
    infer_fallback_quota,
    infer_is_router,
    infer_purpose_from_name,
)
```

**3b.** In `build_model_catalog`, immediately after the existing `for candidate in
discovered_models:` / `model_id = candidate["model_id"]` / `cli_name =
candidate["cli"]` lines (the loop's first three lines — do not change them), insert this
block **before** the existing `md_match = match_models_dev(model_id, models_dev_data) if
models_dev_ok else None` line:

```python
        provider_hint = model_id.split("/", 1)[0] if "/" in model_id else None
        # Gate on infer_is_router(model_id) alone -- provider_hint is always a prefix of
        # model_id and infer_is_router is a plain substring test (model_heuristics.py), so
        # infer_is_router(provider_hint or "") can never be true when infer_is_router(model_id)
        # is false. A two-argument OR here would be redundant, not defensive.
        name_purpose = (infer_purpose_from_name(model_id)
                        if infer_is_router(model_id)
                        else None)
        if name_purpose:
            # Skip match_models_dev/match_artificial_analysis ENTIRELY for this candidate --
            # its purpose is unambiguous from its own name, and neither external source
            # models a router's operator-assigned routing label as a scorable capability
            # anyway, so querying either would spend a network call (Artificial Analysis:
            # quota-limited) for data this candidate will never use to decide its role.
            existing_key = _find_existing_key_for_runtime(existing_catalog, cli_name, model_id)
            provider = (existing_catalog[existing_key]["provider"] if existing_key
                        else provider_hint)
            if provider is None:
                # HIGH-adjacent fix (review MEDIUM finding): a bare id with no existing catalog
                # entry to recover a provider from still has a real, unambiguous
                # name_declared_purpose -- carry it onto the unmatched payload rather than
                # silently discarding it, since Task 4's wizard partition can only act on a
                # field it can actually see. `_infer_heuristics("", model_id)` is unchanged from
                # the existing unmatched-path convention (an empty provider is the existing
                # convention for "no vendor to infer from," used identically by the ordinary
                # unmatched path a few lines below in the function's existing body).
                unmatched.append({"cli": cli_name, "model_id": model_id, "provider": None,
                                   "key": None, "vendor_unknown": True,
                                   "name_declared_purpose": name_purpose,
                                   **_infer_heuristics("", model_id)})
                continue
            key = existing_key or canonical_key(provider, bare_model_part(model_id))
            existing_entry = catalog.get(key)
            heuristics = {field: (existing_entry or {}).get(field, inferred)
                          for field, inferred in _infer_heuristics(provider, model_id).items()}
            # Reuses the EXISTING preserve-on-source-down contract by passing
            # models_dev_ok=False / aa_ok=False for THIS candidate specifically -- exactly
            # matches that contract's own semantics ("the source wasn't queried this run,
            # keep whatever's cached"), which is literally true here: neither source was
            # ever called. No new field-preservation helper needed.
            md_fields = _preserved_or_fresh_md_fields(None, False, existing_entry)
            # NOTE: no `aa_fields.pop("aa_pricing", None)` here (an earlier draft had one) --
            # `_preserved_or_fresh_aa_fields(None, False, existing_entry)` always takes its
            # `not aa_ok` branch, which returns only cached `scores`/`tokens_per_sec` and can
            # never contain an `aa_pricing` key, so the pop would always be a no-op.
            aa_fields = _preserved_or_fresh_aa_fields(None, False, existing_entry)
            ctx_window = _preserved_or_fresh_ctx_window(None, False, existing_entry, cli_name)
            entry = {
                "provider": (existing_entry or {}).get("provider", provider),
                "runtimes": {cli_name: {"model_id": model_id, "ctx_window": ctx_window}},
                **heuristics,
                "name_declared_purpose": name_purpose,
                "source": {
                    "models_dev": (existing_entry or {}).get("source", {}).get(
                        "models_dev", False),
                    "artificial_analysis": (existing_entry or {}).get("source", {}).get(
                        "artificial_analysis", False),
                    "manual": (existing_entry or {}).get("source", {}).get("manual", False),
                },
                "confidence": (existing_entry or {}).get("confidence", "low"),
                "last_verified": (existing_entry or {}).get("last_verified", today),
                **md_fields,
            }
            entry.update(aa_fields)
            pricing = (existing_entry or {}).get("pricing")
            if pricing:
                entry["pricing"] = pricing
            catalog, reason = merge_catalog_entry(catalog, key, entry)
            if reason:
                rejections.append(reason)
            continue
```

The line immediately after this new block must remain the existing, completely
unmodified `md_match = match_models_dev(model_id, models_dev_data) if models_dev_ok else
None` — do not touch anything from that line through the end of the loop body.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestBuildModelCatalog -v`
Expected: `OK` (all 7 new tests plus every pre-existing `TestBuildModelCatalog` test, no regressions).

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-review/ai_kit_spec/cli.py tests/test_ai_kit_spec.py
git commit -m "feat(model-catalog): skip external enrichment for name-declared router purposes

When a router/gateway candidate's own model id declares its purpose (review/coding),
build_model_catalog now short-circuits before match_models_dev/match_artificial_analysis
are ever called for it -- provider/key come from cache or the id's own vendor prefix,
and existing fields are preserved via the same _preserved_or_fresh_* contract used for a
genuinely-down source. The existing md_match/aa_match body is completely untouched for
every other candidate."
```

---

### Task 4: Wizard presentation (`ai-kit-spec-config/SKILL.md`)

**Files:**
- Modify: `skills/ai-kit-spec-config/SKILL.md`

No test file for this task — it is prose/instructions for an agent to follow, not
executable code (consistent with this skill's own nature: the wizard has no Python test
harness of its own).

**Interfaces:**
- Consumes: catalog entries carrying `name_declared_purpose` (Task 3).

- [ ] **Step 1: Partition entries before ranking**

In `skills/ai-kit-spec-config/SKILL.md`, find the inline `python3 -c` snippet in Step
2.2 item 5 (search for `entries = [{'key': k, **v} for k, v in catalog.items() if k in
current]` immediately followed by `weights = load_ranking_weights()`). Insert two new
lines between them:

```python
entries = [{'key': k, **v} for k, v in catalog.items() if k in current]
name_declared = [e for e in entries if e.get('name_declared_purpose')]
scored = [e for e in entries if not e.get('name_declared_purpose')]
weights = load_ranking_weights()
```

Then change the ranking loop's own input from `entries` to `scored`, and add the print
statements that emit each purpose's `name_declared` entries (the presentation instruction
in Step 2 below depends on this snippet actually printing them — without this, `Before
printing each purpose's ranked block, first list any name_declared entries...` in Step 2
would have no data to act on). The existing loop already reads:

```python
for purpose in ('review', 'execute'):
    ranked = score_candidates(entries, purpose, weights)[:5]
    print(purpose.upper())
    for i, e in enumerate(ranked, 1):
```

Change it to:

```python
for purpose in ('review', 'execute'):
    ranked = score_candidates(scored, purpose, weights)[:5]
    print(purpose.upper())
    for e in [d for d in name_declared if d.get('name_declared_purpose') == purpose]:
        runtimes_str = '/'.join(e.get('runtimes', {}).keys())
        print(f\"  • {e['key']}  via {runtimes_str}  (declared by name -- not scored)\")
    for i, e in enumerate(ranked, 1):
```

(Two changes: the `score_candidates` call's first argument changes from `entries` to
`scored`; and a new `for e in [d for d in name_declared ...]` block is inserted between
the existing `print(purpose.upper())` line and the existing `for i, e in
enumerate(ranked, 1):` line. Everything else in the loop, including the per-field
`detail`/`parts` construction under `for i, e in enumerate(ranked, 1):`, stays as-is.)

The new `print(f\"  • {e['key']}  via {runtimes_str}  (declared by name -- not scored)\")`
line uses `\"` for its inner double quotes — this is not optional stylistic preference,
it's required by the enclosing shell string: the whole snippet lives inside a
`python3 -c "..."` block (a bash double-quoted string), so every inner `"` in the embedded
Python must itself be escaped as `\"` or the shell string terminates early. Every existing
`print(f"...")` call already in this snippet uses `\"` this exact way (see the pre-existing
`print(f\"  {i}. {e['key']}  score {e['score']}\" + ...)` line a few lines below) — match
that convention exactly, do not write a bare `print(f"...")` here.

- [ ] **Step 2: Update item 6's presentation instructions**

In Step 2.2 item 6, immediately before the illustrative `REVIEW (flagship/reasoning) —
top candidates:` code block, add this instruction paragraph:

> **Before printing each purpose's ranked block, first list any `name_declared` entries
> whose `name_declared_purpose` matches that purpose** (e.g. `"review"` entries prepend
> to the REVIEW block, `"execute"` entries prepend to the EXECUTE block), each on its own
> bullet line marked `(declared by name -- not scored)`, showing its runtime/CLI the same
> way a scored candidate does. A name-declared entry never appears in the other purpose's
> block, never gets a numbered rank, and is never annotated with a cross-reference to the
> other list (unlike a genuine scored "combo" model, which can legitimately appear in
> both -- see below) -- its position is fixed by its own declared purpose, not earned by a
> score.

(Use the double-hyphen `--` form consistently for this label, matching the literal Python
string the Step 1 code prints -- not an em-dash. An em-dash inside a terminal-printed label
is more likely to render as a mangled byte in some locales; the double-hyphen is plain
ASCII and matches what the code actually emits.)

Update the illustrative code block to show this:

```
REVIEW (flagship/reasoning) — top candidates:
  • router-env-plan-review  via opencode  (declared by name -- not scored)
  1. openai/gpt-5.6-sol     via codex     score 87  (intelligence 91 [via Artificial Analysis], batch✓, ctx 400k)
  2. xai/grok-4.6           via grok      score 79  (intelligence 85 [via Artificial Analysis], agentic 88 [via Artificial Analysis])
  3. anthropic/router-env   via opencode  score 74  (fallback✓)

EXECUTE (coding-agent) — top candidates:
  • router-env-coding       via opencode  (declared by name -- not scored)
  1. anthropic/router-env   via opencode  score 90  (coding 89 [via Artificial Analysis], tool_call✓)  — also ranked #3 in REVIEW above
  2. openai/gpt-5.6-sol     via codex     score 81  — also ranked #1 in REVIEW above
Any preference not listed, or confirm this order for the ladder?
```

- [ ] **Step 3: Remove the now-superseded post-hoc mitigation**

Still in Step 2.2 item 6, delete an EXACT range of text, and only that range — the
markdown paragraph this text sits in continues, without a blank line, past the sentence
that names the range's end, into text that must be RETAINED (it is the only place the
wizard is told to record `purpose`; deleting it would break Steps 2.4, 2.6, and 3). Do
not use "delete the whole paragraph" as your boundary — use the exact start and end
markers below.

- **Delete, verbatim, starting from:** `**A DIFFERENT failure mode, and the more
  important one to catch: two DISTINCT keys landing in the WRONG or SAME list because
  the ranking axes couldn't tell them apart.**` (added earlier the same day as a
  prose-only mitigation)
- **through, and including, this exact sentence's end:** `...rather than trusting the
  generic score over the CLI's own explicit labeling.`
- **RETAIN everything from the very next sentence onward** — starting at `Ask the user
  to confirm or adjust.` and continuing through `...This IS the answer to what used to
  be a separate `purpose` question — see Step 2.6 below.` — unchanged, word-for-word.

Unambiguous result (there is exactly one correct resulting text, not two valid readings):
after the deletion, the retained sentence `Ask the user to confirm or adjust.` becomes the
very next sentence in the SAME paragraph as the still-untouched text before it (the
paragraph beginning **"The SAME catalog key appearing in both lists is expected, not a
mistake"**, which currently ends "...not a coincidence."). There is **no blank line**
between them — the blank line that currently separates that paragraph from the (now
partially-deleted) `**A DIFFERENT failure mode...**` paragraph is *also* deleted, along
with the deleted range itself, so the two remaining paragraphs merge into one continuous
paragraph run with a single space (not a blank line) between sentences: "...not a
coincidence. Ask the user to confirm or adjust. Record, for every confirmed candidate,
...". Concretely: delete the deleted range's text AND the blank line immediately preceding
it (the one separating it from the "not a coincidence." paragraph) as one contiguous
span; do not leave a blank line there, and do not leave the retained sentence starting its
own new paragraph.

Why this deletion is safe despite keeping the "record `purpose`" text: this task's
`name_declared`/`scored` partition (Step 1 above) prevents the axis-based misclassification
this deleted text was reacting to at its source **only for candidates already confirmed
router-like by `infer_is_router`** — a router candidate whose id also declares a purpose
word never reaches `score_candidates` at all, so for that specific case the old "detect a
purpose-word/list mismatch after scoring and move it" prose is genuinely superseded. This
is NOT a full replacement, though, and must not be described as simply "now-dead
guidance": the deleted prose's mitigation covered **every** candidate's raw id (router or
not), whereas the new partition only covers candidates `infer_is_router` already confirms
(design spec §3 Non-Goals: this design does not infer purpose for a non-router candidate's
name). A non-router candidate whose name happens to contain a purpose word (e.g. a real
vendor model coincidentally named with "review" or "coding" in it) now loses the old
prose-level mitigation entirely, with no replacement — the axis-based score is the only
thing placing it, same as before this deleted prose existed. This is a deliberate, accepted
scope narrowing, matching the design spec's own Non-Goals framing, not an oversight — but
it must be stated as such, not glossed over as "dead code." The RETAINED
`purpose`-recording sentences are a separate, still-load-bearing concern (documenting the
`purpose` field every ranked-flow confirmation writes) unrelated to the deleted detection
logic, which is why they must survive this edit even though the paragraph they were
originally embedded in is being cut. Leave the paragraph immediately before the deleted
range (beginning **"The SAME catalog key appearing in both lists is expected, not a
mistake"**) exactly as-is in its own content — it addresses a different, still-real
condition (a single key genuinely scoring well under both weight profiles) that this task
does not change; only the blank line that used to separate it from the now-deleted
paragraph is removed, per the merge above.

- [ ] **Step 4: Verify the edit reads coherently, then actually run the edited snippet**

First, read the full Step 2.2 item 6 section back (`Read` the file, or `bat
--line-range <start>:<end>` the relevant line range) and confirm: the partition code is in
place (Step 1's print statements included); the illustrative block shows both a
`•`-bulleted name-declared line and numbered scored lines per purpose; the deleted range
is gone in full, starting exactly at "A DIFFERENT failure mode..." and ending exactly at
"...explicit labeling."; the retained sentence "Ask the user to confirm or adjust." through
"...see Step 2.6 below." is present, unmodified, and reads as a natural continuation
directly after "...not a coincidence." with no blank line, no orphaned fragment, and no
duplicated text; and the "same key in both lists" guidance immediately precedes this
retained text unchanged.

Reading the text back only confirms it parses as valid Python and reads coherently — it
does NOT prove the edited snippet actually behaves as intended. Verify that by building a
small stub catalog fixture and actually running the edited `python3 -c` block's logic
against it:

```bash
TOOLS_PY="skills/ai-kit-spec-review/ai-kit-spec.py"   # standalone verification, not a live wizard run --
                                                       # set explicitly rather than relying on the wizard's
                                                       # own $TOOLS_PY (only defined inside a real run)
mkdir -p /tmp/aikit-task4-verify
cat > /tmp/aikit-task4-verify/catalog.json <<'JSON'
{
  "router-env/router-env-plan-review": {
    "provider": "router-env", "name_declared_purpose": "review",
    "runtimes": {"opencode": {"model_id": "router-env/router-env-plan-review"}},
    "is_router": true, "batch_mode": false, "fallback_quota": true,
    "source": {"models_dev": false, "artificial_analysis": false, "manual": false},
    "confidence": "low", "last_verified": "2026-09-05"
  },
  "router-env/router-env-coding": {
    "provider": "router-env", "name_declared_purpose": "execute",
    "runtimes": {"opencode": {"model_id": "router-env/router-env-coding"}},
    "is_router": true, "batch_mode": false, "fallback_quota": true,
    "source": {"models_dev": false, "artificial_analysis": false, "manual": false},
    "confidence": "low", "last_verified": "2026-09-05"
  },
  "openai/gpt-5.6-sol": {
    "provider": "openai",
    "runtimes": {"codex": {"model_id": "openai/gpt-5.6-sol", "ctx_window": 400000}},
    "is_router": false, "batch_mode": true, "fallback_quota": false,
    "tool_calling": true, "structured_output": true,
    "scores": {"intelligence_index": 91.0},
    "source": {"models_dev": true, "artificial_analysis": true, "manual": false},
    "confidence": "high", "last_verified": "2026-09-05"
  }
}
JSON
cat > /tmp/aikit-task4-verify/fetch-result.json <<'JSON'
{"discovered": [
  {"cli": "opencode", "model_id": "router-env/router-env-plan-review"},
  {"cli": "opencode", "model_id": "router-env/router-env-coding"},
  {"cli": "codex", "model_id": "openai/gpt-5.6-sol"}
]}
JSON
python3 -c "
import json, sys
sys.path.insert(0, '$(dirname "$TOOLS_PY")')
from ai_kit_spec.model_catalog import current_candidate_keys
from ai_kit_spec.model_ranker import load_ranking_weights, score_candidates
catalog = json.load(open('/tmp/aikit-task4-verify/catalog.json'))
fetch_result = json.load(open('/tmp/aikit-task4-verify/fetch-result.json'))
discovered = fetch_result['discovered']
current = current_candidate_keys(catalog, discovered)
entries = [{'key': k, **v} for k, v in catalog.items() if k in current]
name_declared = [e for e in entries if e.get('name_declared_purpose')]
scored = [e for e in entries if not e.get('name_declared_purpose')]
weights = load_ranking_weights()
def field(e, path, label):
    v = e.get('scores', {}).get(path) if path in ('intelligence_index', 'coding_index', 'agentic_index') else e.get(path)
    if v is None:
        return None
    aa_sourced = path in ('intelligence_index', 'coding_index', 'agentic_index', 'tokens_per_sec')
    tag = ' [via Artificial Analysis]' if aa_sourced and e.get('source', {}).get('artificial_analysis') else ''
    return f'{label} {v}{tag}'

for purpose in ('review', 'execute'):
    ranked = score_candidates(scored, purpose, weights)[:5]
    print(purpose.upper())
    for e in [d for d in name_declared if d.get('name_declared_purpose') == purpose]:
        runtimes_str = '/'.join(e.get('runtimes', {}).keys())
        print(f\"  • {e['key']}  via {runtimes_str}  (declared by name -- not scored)\")
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

Expected output (order of scored entries may vary if weights change upstream, but the
`•`-bulleted name-declared lines must appear first in each block, exactly one per purpose,
with no numbered rank and no score):

```
REVIEW
  • router-env/router-env-plan-review  via opencode  (declared by name -- not scored)
  1. openai/gpt-5.6-sol  score 83.8  (intelligence 91.0 [via Artificial Analysis], ctx 400000, tool_call✓, batch✓)
EXECUTE
  • router-env/router-env-coding  via opencode  (declared by name -- not scored)
  1. openai/gpt-5.6-sol  score 74.0  (intelligence 91.0 [via Artificial Analysis], ctx 400000, tool_call✓, batch✓)
```

(Verified live against the actual `model_ranker.score_candidates`/`load_ranking_weights` --
exact scores above (83.8, 74.0) may shift if `ranking-weights.toml`'s defaults change later,
but the shape -- one `•`-bulleted name-declared line per purpose, followed by the scored
entry with no missing fields -- will not.)

This confirms, by actually executing the edited code (not just reading it), that: (1) both
name-declared entries are excluded from `score_candidates`'s input (`scored`, not
`entries`) yet still printed via the new loop; (2) each appears under its own declared
purpose only — `router-env-plan-review` never appears under EXECUTE, `router-env-coding`
never appears under REVIEW; (3) the `openai/gpt-5.6-sol` scored entry (no
`name_declared_purpose`) still ranks normally in both blocks, unaffected; (4) the print
statement's escaped quoting (from the HIGH #2 fix above) is valid — a quoting bug there
would raise a `SyntaxError` from the shell/interpreter before any output was produced, not
silently print nothing.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-config/SKILL.md
git commit -m "docs(ai-kit-spec-config): present name-declared-purpose candidates without scoring

Partitions ranking candidates by name_declared_purpose before calling score_candidates,
so a router/gateway endpoint whose id already declares its purpose is shown directly
under that list -- never scored, never at risk of landing in the wrong list. Replaces
the earlier same-day post-hoc detect-and-reroute mitigation, now superseded since the
misclassification is prevented at its source."
```

---

### Task 5: Full-suite verification

**Files:** none modified — verification only.

- [ ] **Step 1: Run the full `ai_kit_spec` test file**

Run: `set -o pipefail; uv run python3 -m unittest tests.test_ai_kit_spec -v 2>&1 | tail -40; echo "exit=$?"`
Expected: the final `exit=0` line, `OK` in the tail output, with the total test count
higher than before this plan (Task 1: +10, Task 2: +4, Task 3: +7 = 21 new tests) and zero
failures/errors anywhere in the file.

- [ ] **Step 2: Run the project's full test suite**

Run: `set -o pipefail; uv run make test 2>&1 | tail -60; echo "exit=$?"`
Expected: the final `exit=0` line, `OK` across every test module the Makefile's `test`
target runs, plus `bash tests/test_install.sh`'s own pass count — confirms this plan's
changes to shared modules (`model_heuristics.py`, `model_catalog.py`, `cli.py`) haven't
broken anything outside `ai_kit_spec`'s own test file.

No commit for this task (verification only).
