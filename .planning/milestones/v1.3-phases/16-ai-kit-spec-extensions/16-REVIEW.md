---
phase: 16-ai-kit-spec-extensions
reviewed: 2026-09-24T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - AGENTS.md
  - docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py
  - skills/ai-kit-spec-config/SKILL.md
  - skills/ai-kit-spec-config/references/cli-model-selection.md
  - skills/ai-kit-spec-review/ai_kit_spec/cli.py
  - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
  - skills/ai-kit-spec-review/ai_kit_spec/detection.py
  - skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py
  - skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py
  - skills/ai-kit-spec-review/references/ranking-weights.toml
  - tests/fixtures/codex_debug_models.json
  - tests/fixtures/opencode_models_verbose.txt
  - tests/test_ai_kit_opencode_providers.py
  - tests/test_ai_kit_spec.py
  - tests/test_ai_kit_usage_metrics.py
findings:
  critical: 0
  warning: 4
  info: 1
  total: 5
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-09-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

This phase adds pi/codex host-detection signals, real `codex debug models` /
`opencode models --verbose` enumeration, a hybrid claude alias+catalog-id model list,
`image_input`/`reasoning_modes` catalog fields with source provenance, five ranker
purposes with alias back-compat and an optional per-purpose floor, and `schema_version`
staleness gating for both caches. The diff is unusually well-documented (module/function
docstrings cite the originating decision IDs, and several functions carry "review cycle
N" notes recording prior findings that were already fixed before this submission), and
is backed by ~140 new/updated tests plus two real-capture fixtures
(`codex_debug_models.json`, `opencode_models_verbose.txt`).

I traced the full `build_model_catalog`/`_apply_runtime_meta`/`_preserved_or_fresh_md_fields`
interaction for `image_input` provenance (models.dev vs. opencode-runtime precedence),
the `claude_runtime_fields`/`claude_runtime_is_current`/`--if-stale` freshness chain, the
anthropic-id materialization block in `fetch-model-catalog`, the purpose-alias resolution
in `model_ranker.py`, and the new `_RUNTIME_ENV_SIGNALS` ordering against
`16-CONTEXT.md` D-01 (amended by Phase 20 D-02) — no correctness, security, or
data-loss defect was found in any of these paths. `_VALID_NATIVE_RUNTIME` was updated
consistently in both `model_catalog.py` and `config_io.py` (the file itself flags them as
required to change together). The full `test_ai_kit_spec.py` (594 tests),
`test_ai_kit_opencode_providers.py`/`test_ai_kit_usage_metrics.py` (229 tests), and
`test_arch.py` (22 tests) suites all pass locally; `vulture`/targeted `pylint` checks on
the changed modules are clean.

The one class of real issue found is lint hygiene: `ruff check` (the project's own gating
rule set, `select = [E, F, W, I, UP, B, SIM, RUF]`) reports violations in four of the
newly-changed source regions that were not caught before commit. One of these
(`tests/test_ai_kit_usage_metrics.py`) sits squarely inside the pre-commit `ruff` hook's
configured `files:` scope and currently fails `pre-commit run ruff` at HEAD — i.e.
`make validate` does not pass clean on this diff today. The other three sit in
`skills/ai-kit-spec-review/ai_kit_spec/*.py`, which a pre-existing (out-of-diff)
`.pre-commit-config.yaml` scoping gap excludes from the ruff hook entirely, so they
never triggered a hook failure but are still genuine violations of the project's
configured ruff ruleset. None of the five findings below affect behavior.

## Warnings

### WR-01: Unsorted import block fails the gated ruff hook

**File:** `tests/test_ai_kit_usage_metrics.py:22-47`
**Issue:** The two new imports added for this phase's `_meta`-key regression tests
(`from ai_kit_usage_metrics.paths import catalog_path` and
`from ai_kit_usage_metrics.pricing import estimate_price`) were appended after the
pre-existing `from ai_kit_usage_metrics.raw_store import CaptureResult` line instead of
being merged alphabetically. `tests/*.py` is inside the pre-commit `ruff` hook's `files:`
regex (`.pre-commit-config.yaml`), so this is a real, currently-failing gate: running
`uv run pre-commit run ruff --files tests/test_ai_kit_usage_metrics.py` reports
`I001 Import block is un-sorted or un-formatted` on this exact block. AGENTS.md's
Non-Negotiable Rules require every commit to pass its hooks without `--no-verify`.
**Fix:**
```bash
uv run ruff check --fix tests/test_ai_kit_usage_metrics.py
```
which reorders the block to:
```python
from ai_kit_usage_metrics.cli import CAPTURE_SOURCES, main
from ai_kit_usage_metrics.cwd_state import CwdState
from ai_kit_usage_metrics.dashboard import generate
from ai_kit_usage_metrics.decomposer import classify_segment, decompose, scan_command
from ai_kit_usage_metrics.paths import catalog_path
from ai_kit_usage_metrics.pricing import estimate_price
from ai_kit_usage_metrics.raw_store import CaptureResult
from ai_kit_usage_metrics.refiner import refine_all
```

### WR-02: Two new `_FIELD_TYPES` comment lines exceed the 100-column ruff limit

**File:** `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:30-31`
**Issue:** The two new `image_input`/`image_input_source` field-type entries carry
inline comments that push the lines to 106 and 104 columns; the project's ruff config
(`pyproject.toml`, `line-length = 100`, `E` selected) rejects both
(`E501 Line too long`). This module is not currently inside the pre-commit `ruff` hook's
`files:` scope (a pre-existing gap unrelated to this diff), so the violation was never
caught by the gate, but it is a real violation of the project's own configured ruleset.
**Fix:**
```python
    # 16 D-09 -- optional; absent means unknown; written only from a source statement.
    "image_input": bool,
    # 16 D-09 (review cycle 2 MEDIUM) -- field-level provenance of image_input.
    "image_input_source": str,
```

### WR-03: Nested `if` in `_apply_runtime_meta` (SIM102)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/cli.py:304-305`
**Issue:** `ruff` (`SIM102`) flags the nested `if "image_input" in meta and
isinstance(meta["image_input"], bool): / if runtime_wins_image_input or not
isinstance(...):` as collapsible into one condition. Not currently caught by the hook
for the same pre-existing scoping-gap reason as WR-02.
**Fix:**
```python
    if ("image_input" in meta and isinstance(meta["image_input"], bool)
            and (runtime_wins_image_input or not isinstance(entry.get("image_input"), bool))):
        entry["image_input"] = meta["image_input"]
        entry["image_input_source"] = "opencode"
```

### WR-04: Nested `if` and if/else block flagged in `model_ranker.py` (SIM102/SIM108)

**File:** `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:141-142, 219-222`
**Issue:** `_is_valid_weights_structure`'s `for purpose in CANONICAL_PURPOSES: if purpose
in weights: if not _is_valid_purpose_section(...): return False` nests two `if`s
(`SIM102`), and `score_candidates`'s `if canonical in weights: axis_weights =
weights[canonical] else: axis_weights = weights[purpose]` is flagged as preferring a
ternary (`SIM108`). Same pre-existing hook-scoping gap as WR-02/WR-03.
**Fix:**
```python
    for purpose in CANONICAL_PURPOSES:
        if purpose in weights and not _is_valid_purpose_section(weights[purpose]):
            return False
```
```python
    axis_weights = weights[canonical] if canonical in weights else weights[purpose]
```

## Info

### IN-01: Awkward `json.dump` call formatting in a new test helper

**File:** `tests/test_ai_kit_usage_metrics.py:66-80` (`_write_meta_catalog`)
**Issue:** The new helper writes `json.dump(\n {...}\n ,\n handle,\n)` with a
dangling comma on its own line before `handle`, which reads oddly next to the rest of
the file's formatting even though it is not itself a lint violation.
**Fix:**
```python
json.dump(
    {"_meta": {"schema_version": 2},
     "anthropic/claude-x": {"pricing": {"input_per_1m": 3.0, "output_per_1m": 15.0}}},
    handle,
)
```

---

_Reviewed: 2026-09-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
