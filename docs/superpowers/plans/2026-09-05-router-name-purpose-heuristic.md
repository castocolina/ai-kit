# Router/Gateway Name-Declared Purpose Heuristic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A router/gateway CLI candidate whose raw model id already declares its purpose in plain words (e.g. `router-env-plan-review`, `router-env-coding`) gets that purpose recorded as `name_declared_purpose`, skips `match_models_dev`/`match_artificial_analysis` entirely, and is presented directly under its declared list by the `ai-kit-spec-config` wizard — never scored, never at risk of landing in the wrong REVIEW/EXECUTE list.

**Architecture:** A new pure heuristic `infer_purpose_from_name` (`model_heuristics.py`) mirrors the existing `infer_is_router`/`infer_batch_mode`/`infer_fallback_quota` pattern — no network, string-matching only, and gated externally by callers on `infer_is_router` (never runs on a non-router candidate). `build_model_catalog` (`cli.py`) checks this at the very top of its per-candidate loop, before the existing `md_match`/`aa_match` calls; when it fires, the candidate takes a self-contained short-circuit path that derives `provider`/`key` from cache or the id's own vendor prefix (never from an external match), reuses the existing `_preserved_or_fresh_*` helpers with `models_dev_ok=False`/`aa_ok=False` to inherit their preserve-on-not-queried contract for free, and `continue`s before the existing body ever runs. The wizard (`ai-kit-spec-config/SKILL.md`) partitions ranking candidates by this new field before calling `score_candidates`, presenting name-declared entries directly under their declared list.

**Tech Stack:** Python 3.12, stdlib only, `unittest` (no pytest — `uv run python3 -m unittest`).

**Spec:** `docs/superpowers/specs/2026-09-05-router-name-purpose-heuristic-design.md`

## Global Constraints

- `infer_purpose_from_name` takes a bare `model_id: str` and returns `"review"`, `"execute"`, or `None` — it does NOT call `infer_is_router` itself; every caller gates on `infer_is_router` externally first.
- `_PURPOSE_NAME_HINTS` is exactly `{"review": ("review", "plan-review"), "execute": ("coding", "execute")}` — no additional tokens.
- Both hint groups matching (a naming contradiction) returns `None`, same as neither matching.
- `build_model_catalog`'s existing body (from `md_match = match_models_dev(...)` onward) is never modified — the new logic is a pure prepend that `continue`s before reaching it. The effort-suffix-fallback logic (`md_enrich_match`) must remain byte-for-byte unchanged.
- A name-declared candidate must NEVER have `match_models_dev`/`match_artificial_analysis` called for it, under any circumstance — verified directly in tests (fixtures that WOULD match if queried, proving the entry's fields show no trace of that data), never just inferred from output shape.
- `name_declared_purpose` is optional on a catalog entry, defaults to absent, one of `"review"`/`"execute"` when present, and its presence/absence never changes validation behavior for any entry that doesn't set it.
- Tests live in `tests/test_ai_kit_spec.py` (no new test file), run via `uv run python3 -m unittest tests.test_ai_kit_spec.<TestClassName> -v` (scoped) or `uv run python3 -m unittest tests.test_ai_kit_spec -v` (whole file). Do **not** use `pytest`.
- Single-file-set change: `model_heuristics.py`, `cli.py`, `model_catalog.py`, `ai-kit-spec-config/SKILL.md`, plus tests. No new CLI flags, no schema migration.

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
        # last -- substring match anywhere in the id, not suffix-only.
        self.assertEqual(
            model_heuristics.infer_purpose_from_name("review-router-env"), "review")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestInferPurposeFromName -v`
Expected: FAIL with `AttributeError: module 'ai_kit_spec.model_heuristics' has no attribute 'infer_purpose_from_name'` (8 errors).

- [ ] **Step 3: Implement `infer_purpose_from_name`**

In `skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py`, append the following at the end of the file (after `infer_fallback_quota`'s closing line):

```python
_PURPOSE_NAME_HINTS = {
    "review": ("review", "plan-review"),
    "execute": ("coding", "execute"),
}


def infer_purpose_from_name(model_id: str) -> str | None:
    """Only meaningful for a candidate ALREADY confirmed as a router/gateway via
    infer_is_router -- this function does not check is_router itself (keeps the two
    heuristics independently testable/composable; every caller gates on infer_is_router
    first). Checks for an explicit, unambiguous purpose word in the id:
    "review"/"plan-review" -> "review"; "coding"/"execute" -> "execute". Returns None when
    neither group matches, OR when both do (a genuine naming contradiction must never be
    silently resolved by picking one) -- callers that get None fall through to the ordinary
    external-matching path, exactly as if this heuristic didn't exist."""
    lowered = model_id.lower()
    is_review = any(h in lowered for h in _PURPOSE_NAME_HINTS["review"])
    is_execute = any(h in lowered for h in _PURPOSE_NAME_HINTS["execute"])
    if is_review == is_execute:   # neither matched, or both did (contradiction) -> None
        return None
    return "review" if is_review else "execute"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestInferPurposeFromName -v`
Expected: `OK` (8 tests).

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

In `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`, add a new constant immediately after `_RUNTIME_FIELD_TYPES = {"model_id": str, "ctx_window": (int, float)}` (the line right after the `_FIELD_TYPES` dict's closing `}`):

```python
_VALID_NAME_DECLARED_PURPOSE = {"review", "execute"}
```

Then, in `validate_catalog_entry`, add this check immediately after the existing `confidence` check block (`if entry.get("confidence") not in _VALID_CONFIDENCE: return f"..."`):

```python
    if "name_declared_purpose" in entry and entry["name_declared_purpose"] is not None \
            and entry["name_declared_purpose"] not in _VALID_NAME_DECLARED_PURPOSE:
        return (f"{model_id}: 'name_declared_purpose' must be one of "
                f"{sorted(_VALID_NAME_DECLARED_PURPOSE)}")
```

Also add `"name_declared_purpose": str` to the `_FIELD_TYPES` dict (anywhere in the dict body, e.g. right after `"speed_tier": str,`) — this makes a non-string value (e.g. a list or int) rejected by the existing generic type-check loop even before the literal-value check above runs.

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
- Produces: `build_model_catalog`'s per-candidate loop now short-circuits before `md_match`/`aa_match` for any candidate where the new logic fires; the resulting catalog entry carries `name_declared_purpose` when applicable.

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python3 -m unittest tests.test_ai_kit_spec.TestBuildModelCatalog -v`
Expected: `test_router_candidate_with_coding_hint_never_calls_external_matching` and
`test_router_candidate_with_review_hint_gets_review_purpose` FAIL with `KeyError:
'name_declared_purpose'` (the field is never set yet, and today's unchanged code
actually calls `match_models_dev`/`match_artificial_analysis` for these candidates —
run this before Step 3 to confirm, then note it, since after Step 3 those same fixtures
must no longer show a real match). The other three tests
(`test_router_candidate_with_no_purpose_word_...`,
`test_non_router_candidate_with_a_purpose_word_...`,
`test_lifecycle_preserves_prior_cached_fields_...`) already PASS against today's
unchanged code — these are guard/regression tests proving the existing path is
untouched, not red-phase tests; do not treat their passing before Step 3 as a mistake.

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
        name_purpose = (infer_purpose_from_name(model_id)
                        if infer_is_router(provider_hint or "") or infer_is_router(model_id)
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
                unmatched.append({"cli": cli_name, "model_id": model_id, "provider": None,
                                   "key": None, "vendor_unknown": True,
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
            aa_fields = _preserved_or_fresh_aa_fields(None, False, existing_entry)
            aa_fields.pop("aa_pricing", None)
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
Expected: `OK` (all 5 new tests plus every pre-existing `TestBuildModelCatalog` test, no regressions).

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

Then change the ranking loop's own input from `entries` to `scored`:

```python
for purpose in ('review', 'execute'):
    ranked = score_candidates(scored, purpose, weights)[:5]
```

(Only the `entries` argument on that one line changes to `scored` — everything else in
that loop stays as-is.)

- [ ] **Step 2: Update item 6's presentation instructions**

In Step 2.2 item 6, immediately before the illustrative `REVIEW (flagship/reasoning) —
top candidates:` code block, add this instruction paragraph:

> **Before printing each purpose's ranked block, first list any `name_declared` entries
> whose `name_declared_purpose` matches that purpose** (e.g. `"review"` entries prepend
> to the REVIEW block, `"execute"` entries prepend to the EXECUTE block), each on its own
> bullet line marked `(declared by name — not scored)`, showing its runtime/CLI the same
> way a scored candidate does. A name-declared entry never appears in the other purpose's
> block, never gets a numbered rank, and is never annotated with a cross-reference to the
> other list (unlike a genuine scored "combo" model, which can legitimately appear in
> both — see below) — its position is fixed by its own declared purpose, not earned by a
> score.

Update the illustrative code block to show this:

```
REVIEW (flagship/reasoning) — top candidates:
  • router-env-plan-review  via opencode  (declared by name — not scored)
  1. openai/gpt-5.6-sol     via codex     score 87  (intelligence 91 [via Artificial Analysis], batch✓, ctx 400k)
  2. xai/grok-4.6           via grok      score 79  (intelligence 85 [via Artificial Analysis], agentic 88 [via Artificial Analysis])
  3. anthropic/router-env   via opencode  score 74  (fallback✓)

EXECUTE (coding-agent) — top candidates:
  • router-env-coding       via opencode  (declared by name — not scored)
  1. anthropic/router-env   via opencode  score 90  (coding 89 [via Artificial Analysis], tool_call✓)  — also ranked #3 in REVIEW above
  2. openai/gpt-5.6-sol     via codex     score 81  — also ranked #1 in REVIEW above
Any preference not listed, or confirm this order for the ladder?
```

- [ ] **Step 3: Remove the now-superseded post-hoc mitigation**

Still in Step 2.2 item 6, find the paragraph beginning **"A DIFFERENT failure mode, and
the more important one to catch: two DISTINCT keys landing in the WRONG or SAME list
because the ranking axes couldn't tell them apart."** (added earlier the same day as a
prose-only mitigation) through its end (the sentence ending "...rather than trusting the
generic score over the CLI's own explicit labeling."). Delete this entire paragraph —
this task's `name_declared`/`scored` partition (Step 1 above) prevents the
misclassification at its source, before a name-declared candidate ever reaches
`score_candidates`, so the old detect-after-the-fact prose is now unreachable/dead
guidance. Leave the paragraph immediately before it (beginning **"The SAME catalog key
appearing in both lists is expected, not a mistake"**) exactly as-is — it addresses a
different, still-real condition (a single key genuinely scoring well under both weight
profiles) that this task does not change.

- [ ] **Step 4: Verify the edit reads coherently**

Read the full Step 2.2 item 6 section back (`Read` the file, or `sed -n` the relevant
line range) and confirm: the partition code is in place, the illustrative block shows
both a `•`-bulleted name-declared line and numbered scored lines per purpose, the
removed paragraph is gone with no orphaned sentence fragments, and the "same key in both
lists" guidance immediately follows the illustrative block unchanged.

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
higher than before this plan (Task 1: +8, Task 2: +4, Task 3: +5 = 17 new tests) and zero
failures/errors anywhere in the file.

- [ ] **Step 2: Run the project's full test suite**

Run: `set -o pipefail; uv run make test 2>&1 | tail -60; echo "exit=$?"`
Expected: the final `exit=0` line, `OK` across every test module the Makefile's `test`
target runs, plus `bash tests/test_install.sh`'s own pass count — confirms this plan's
changes to shared modules (`model_heuristics.py`, `model_catalog.py`, `cli.py`) haven't
broken anything outside `ai_kit_spec`'s own test file.

No commit for this task (verification only).
