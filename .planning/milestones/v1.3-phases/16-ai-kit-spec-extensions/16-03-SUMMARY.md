---
phase: 16-ai-kit-spec-extensions
plan: 03
subsystem: ai_kit_spec
executor: cross-ai (opencode run --model router-env/my-coding)
actuals:
  commits: 3
key-files:
  created:
    []
  modified:
    - AGENTS.md
    - docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py
    - tests/test_ai_kit_opencode_providers.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_usage_metrics.py
completed: 2026-09-24
---

# Phase 16 Plan 03: Cache schema_version (runtimes.json, model-catalog.json) Summary

## What changed

- **Versioned runtimes.json (16 D-12)**: `build_runtimes_snapshot` now stamps
  `{"schema_version": 2, "clis": {...}}` (`detection.RUNTIMES_SCHEMA_VERSION = 2`);
  new `runtimes_schema_is_current()` predicate accepts only a non-bool int `>= 2`.
  `detect-runtimes --if-stale` now skips only when the cached file is fresh **AND**
  version-current (refresh = stale **OR** version not current, Pitfall 3), so the 30-day
  pre-Phase-16 caches get exactly one automatic re-detect/re-stamp; a failed refresh stays
  stale and is retried next run. No new flag; TTL still honored for current-version files.
- **Versioned model-catalog.json via a reserved `_meta` object (16 D-12)**: new
  `model_catalog.CATALOG_SCHEMA_VERSION = 2` / `CATALOG_META_KEY = "_meta"`,
  `split_catalog_meta()`/`join_catalog_meta()`/`catalog_schema_is_current()` (never raising,
  never mutating), and `merge_catalog_entry` now rejects `_meta` as a model id
  ("reserved catalog key"). `fetch-model-catalog` splits `_meta` off before catalog
  building, re-fetches when `_meta.schema_version` is missing/older whatever the fetch-meta
  sidecar says, stamps version current **only when models.dev answered**, and writes via
  `join_catalog_meta`; `confirm-catalog-entry` and `apply-heuristic-correction` preserve
  `_meta` verbatim. Legacy (unversioned) catalogs load unchanged.
- **Sibling-reader pins + contract docs**: regression tests pin that
  ai-kit-opencode-providers' `scan_catalog` never reports `_meta` as a reference and that
  ai-kit-usage-metrics' `estimate_price` is undisturbed by `_meta` (price found; absent
  model → `(None, "unknown")`). AGENTS.md Architecture gained the `_meta` reservation
  bullet; the design spec's §11 Errata gained a **Cache** group documenting the version
  semantics and that cache writes are **single-writer atomic** (one fixed `<path>.tmp` +
  `os.replace`) — concurrent writers to the same cache file are unsupported.

## Files

- `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- `tests/test_ai_kit_spec.py`
- `tests/test_ai_kit_opencode_providers.py`
- `tests/test_ai_kit_usage_metrics.py`
- `AGENTS.md`
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`

`cache.py` was not modified (verified: `git show --stat` on both feature commits is empty for it).

## Commits

```
39df249 test(16-03): pin sibling catalog readers against _meta and document the cache contract
f7057df feat(16-03): version model-catalog.json via a reserved _meta object
35ba028 feat(16-03): version runtimes.json and refresh unversioned snapshots under --if-stale
```

## Test results

- Task 1 verify (`TestRuntimesSchemaVersion TestMainCli TestBuildRuntimesSnapshot
  TestCacheStaleness`): `Ran 53 tests` — `OK` (TestRuntimesSchemaVersion ran 8 tests)
- Task 2 verify (`TestCatalogSchemaVersion TestFetchModelCatalogCli TestMergeCatalogEntry
  TestCurrentCandidateKeys TestApplyHeuristicCorrections`): `Ran 40 tests` — `OK`
  (TestCatalogSchemaVersion ran 15 tests)
- Task 3 verify 1 (`TestCrossReferenceCatalog TestPricing`): `Ran 12 tests` — `OK`
- Task 3 verify 2 (broad regression across the six spec/config skill test modules):
  `Ran 968 tests` — `OK`
- `make test-unit`: **exit 2** — its first unittest run: `Ran 2600 tests` —
  `FAILED (errors=1, skipped=20)`; the single error is listed under Pre-existing failures.

## Pre-existing failures

`make test-unit` (exit 2), one error — **(provisional)**: the failing test and its traceback
touch only `tests/test_markdown_to_pdf.py` and
`skills/markdown-to-pdf/scripts/render_mermaid.py`, neither of which this plan modified
(also reproduced in isolation: `python3 -m unittest tests.test_markdown_to_pdf.TestRenderRealMmdc`
→ 1 test, FAILED, errors=1):

```
ERROR: test_real_render_produces_image (tests.test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image)
Traceback (most recent call last):
  File "/var/home/bazzite/git/personal/ai-kit/tests/test_markdown_to_pdf.py", line 78, in test_real_render_produces_image
    out = rm.render_all(md, work, fmt="png")
  File "/var/home/bazzite/git/personal/ai-kit/skills/markdown-to-pdf/scripts/render_mermaid.py", line 86, in render_all
    raise MermaidRenderError(loc, (err or "").strip())
render_mermaid.MermaidRenderError: mermaid render failed at line 1: node:internal/modules/cjs/loader:1520
  throw err;
  ^

Error: Cannot find module '/home/bazzite/.local/share/pnpm/global/v11/ca026-19fa5b731c0-0ac52087022f9fc0/node_modules/@mermaid-js/mermaid-cli/src/cli.js'
    at Module._resolveFilename (node:internal/modules/cjs/loader:1517:15)
    at wrapResolveFilename (node:internal/modules/cjs/loader:1517:15)
    at Module._load (node:internal/modules/cjs/loader:1122:12)
    at Module.executeUserEntryPoint (node:internal/main/run_main_module:33:47)
    at node:internal/main/run_main_module:33:47 {
  code: 'MODULE_NOT_FOUND',
  requireStack: []
}

Node.js v24.18.0

----------------------------------------------------------------------
Ran 2600 tests in 11.699s

FAILED (errors=1, skipped=20)
make: *** [Makefile:46: test-unit] Error 1
```

All Phase 16 plan 16-03 test targets pass; only the `make test-unit` aggregate carries this
one environmental mermaid-cli (pnpm store) failure, reported verbatim per the objective's rule.

## Decisions honored

- **16 D-12**: `schema_version` added to both caches; a missing or older version counts as
  stale under `--if-stale` whatever the TTL; reversible (running without `--if-stale` is the
  forced refresh; no force flag added).
- **Representation (Claude's discretion, as recorded)**: integer, current value **2** for both
  files (pre-Phase-16 files implicitly version 1). In `runtimes.json` it is a top-level key; in
  `model-catalog.json` it lives in the reserved top-level `_meta` object, because every other
  top-level key there is a `provider/model` entry and existing readers iterate them.
- **The check lives in the cli.py command bodies, never inside cache.py** — `cache_is_stale`
  stays a generic mtime/TTL helper (pinned by `test_cache_is_stale_stays_schema_agnostic`);
  `cache.py` untouched by all three commits.
- **Refresh OR-semantics (Pitfall 3)**: refresh when stale **OR** version not current — never
  chained ANDs; both skip tests are single boolean expressions over the cached payload,
  ready for 16-04's third AND-ed condition.
- **One successful refresh**: only a models.dev-answering run stamps the catalog current;
  AA-only or failed fetches leave `_meta` untouched so the next `--if-stale` run retries.
- **Cache-write concurrency stated honestly**: `cache_write_json` is single-writer atomic
  (one fixed `<path>.tmp` + `os.replace`); simultaneous writers to the same cache file share
  that `.tmp` path and are **unsupported** — no comment, doc, or summary claims otherwise.

## Deviations

None.

## Cross-AI execution (orchestrator record)

- Executor: `opencode run --model router-env/my-coding` (cross_ai: true), prompt = plan <objective> + <tasks> via stdin.
- Automatic session resumes after transient provider errors: 0.
- Orchestrator verification: re-ran make test-unit independently: 2600 tests, only error = pre-existing mmdc environment test; commits 35ba028, f7057df, 39df249 reviewed.
