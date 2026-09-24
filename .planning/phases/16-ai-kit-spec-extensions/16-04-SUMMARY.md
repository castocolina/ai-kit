---
phase: 16-ai-kit-spec-extensions
plan: 04
subsystem: ai_kit_spec
executor: cross-ai (opencode run --model router-env/my-coding)
actuals:
  commits: 2
key-files:
  created:
    []
  modified:
    - docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - tests/test_ai_kit_spec.py
completed: 2026-09-24
---

# Phase 16 Plan 04: Claude hybrid model enumeration Summary

## What changed

- `detection.py`: added the 16 D-04 hybrid claude enumeration — `CLAUDE_MODEL_ALIASES` (`fable`, `opus`, `sonnet`, `haiku`), the dated `CLAUDE_FALLBACK_MODEL_IDS` / `CLAUDE_FALLBACK_AS_OF = 2026-09-23` in-code fallback, `claude_runtime_fields(catalog_raw)` (junk-tolerant id filtering, `models_source: catalog|dated-fallback` confidence labeling), a `catalog_fn` hook on `build_runtimes_snapshot` (called only for an installed claude; `run_fn` never called for claude — 16 D-07), and `claude_runtime_is_current` (the catalog → runtimes freshness edge that never loops).
- `cli.py`: `detect-runtimes --if-stale` gained `_read_default_catalog()` and a third AND-ed skip condition (`claude_runtime_is_current(cached_runtimes, catalog_fn=_read_default_catalog)`, help text updated); `_anthropic_model_ids` (row-shape filter: only dict rows with dict `limit`/`cost`); `_FIRST_PARTY_PROVIDER_BY_CLI = {"claude": "anthropic"}` passed as `provider_hint` on the ordinary `md_match` path only; same-fetch materialization (`claude_candidates` built from recorded ids not already listed, gated on `which_fn("claude")`, passed to `build_model_catalog`, filtered out of printed `unmatched`, never added to printed `discovered`); `anthropic_model_ids`/`anthropic_model_ids_as_of` recorded in `_meta` after `build_model_catalog` returns, narrowed when materialized to ids that really got an `anthropic/<id>` entry with a claude runtime.
- `tests/test_ai_kit_spec.py`: `TestClaudeEnumerationEndToEnd` (tracer over the REAL refresh order, five commands, ending `{}`), `TestClaudeFallback` (9), `TestClaudeRuntimeFreshness` (4), `TestClaudeCatalogMaterialization` (6).
- Design spec §11 Errata: new `**Enumeration**` group documenting the `clis.claude` / `clis.codex` shapes and the refresh-order/convergence behavior Phase 17 consumes.

## Files

- `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py`
- `tests/test_ai_kit_spec.py`
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`

## Commits

```
f3003db test(16-04): pin claude dated fallback labeling and document enumeration shapes
a034f0c feat(16-04): enumerate claude models from aliases plus catalog full ids
```

## Test results

- Task 1 verify (7 targeted classes): `Ran 115 tests in 0.127s` / `OK`
- Task 2 verify 1 (5 targeted classes): `Ran 27 tests in 0.042s` / `OK`
- Task 2 verify 2 (broad regression, 6 modules): `Ran 988 tests in 5.634s` / `OK`
- `python3 -m unittest tests.test_ai_kit_spec`: `Ran 541 tests in 0.255s` / `OK`
- `make test-unit` (first unittest run): exit 1 — `Ran 2620 tests in 11.907s`, `FAILED (errors=1, skipped=20)`; sole failure `test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image` (see below). Its second run `uv run python3 -m unittest tests.test_framework_profiles`: `Ran 6 tests in 0.042s` / `OK` (run directly, since make stopped at the first target's failure).
- All acceptance-criteria greps and `python3 -c` asserts pass; every `TestClaude*` count met (tracer 1 test, Fallback 9, Freshness 4, Materialization 6).

## Pre-existing failures

(provisional — per objective rule; test and traceback touch no file this plan modified)

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
    at Module._resolveFilename (node:internal/modules/cjs/loader:1517:11)
...
Node.js v24.18.0
```

Cause: the real-mermaid test shells out to `mmdc`, whose pnpm-installed module directory no longer exists on this machine (environment, not code). `tests/test_markdown_to_pdf.py` last changed in `e7eb73d` (2026-06-21, pre-Phase-16) and is unrelated to 16-04; 16-06 Task 3 reproduces it at the pre-phase base commit.

## Decisions honored

- **16 D-04**: hybrid sourcing — aliases hardcoded (`claude --help` v2.1.281: fable/opus/sonnet; haiku from ai-kit-spec-config SKILL.md), full ids from models.dev's `anthropic` provider via the catalog refresh path, dated `2026-09-23` fallback labeled `models_source: "dated-fallback"` — never presented as a live list.
- **16 D-07**: real binaries only; for claude nothing is executed at all — the tracer asserts the recording `run_fn` was never called; `claude_runtime_fields` never runs a subprocess.
- **16 D-12**: the catalog-derived claude edge composes with (never bypasses) the TTL and schema gates; `models_source`/`models_as_of` ride the existing schema-stamped caches.
- **Orchestrator resolution 2**: the dated fallback is an in-module constant, dated and labeled as a fallback.
- **Aliases-separate choice**: `aliases` is its own key, never inside `models`, so catalog discovery never matches a bare alias against models.dev or mints bogus `anthropic/opus` keys.
- **Ids-in-`_meta` choice**: anthropic ids live in the reserved `_meta` object (16-03) and are materialized as `anthropic/<id>` entries in the same fetch; never added to printed `discovered`/`unmatched`, so a wizard's narrowed ranking scope never widens.
- **Catalog → runtimes freshness edge**: runtimes.json's claude portion is derived from model-catalog.json `_meta`, so `detect-runtimes --if-stale` re-detects when the recorded ids/as-of change; an unchanged catalog (including "no recorded ids" vs a stored fallback) is current, so the edge never loops. Rejected: re-stamping `clis.claude` from inside `fetch-model-catalog` (would write into its `--runtimes-json` INPUT); fetching the catalog before detection (catalog discovery needs the runtimes snapshot first).
- **Same-fetch materialization (option a)**: gated on `which_fn("claude")` rather than the snapshot (a wizard-narrowed `--runtimes-json` may omit claude while still refreshing the shared fetch-meta sidecar); option b rejected (changes `--if-stale`'s documented network-only contract for every CLI, spends an extra network + AA quota call, and still needs a second adapter run).
- **Claude-only `anthropic` match hint**: `_FIRST_PARTY_PROVIDER_BY_CLI` passed only on the ordinary `md_match` path for `claude`; every other CLI keeps the unhinted collision behavior (pinned by `test_anthropic_hint_is_claude_only`). Malformed models.dev rows are skipped by `_anthropic_model_ids`, never crash the fetch, and are never recorded without an entry (`test_malformed_anthropic_rows_never_crash_or_get_recorded`).

## Deviations

None functional. Two incidental notes: (1) the repo's pre-commit hook is not executing on this checkout (its `.venv` python path, `/home/user-zero/...`, no longer exists, and no `pre-commit` binary is on PATH), so the Task 1/Task 2 commits ran without hooks; I verified the equivalent checks manually — `python3 -m unittest` green, ruff clean on every line this plan added (all standalone ruff findings sit on pre-existing lines and are reported here, not suppressed). (2) `make test-unit` reports the one provisional pre-existing failure above; nothing it flags touches a file this plan modified.

## Cross-AI execution (orchestrator record)

- Executor: `opencode run --model router-env/my-coding` (cross_ai: true), prompt = plan <objective> + <tasks> via stdin.
- Automatic session resumes after transient provider errors: 0.
- Orchestrator verification: re-ran make test-unit independently: 2620 tests, only error = pre-existing mmdc environment test; commits a034f0c, f3003db reviewed. Environment finding: .git/hooks/pre-commit points to a missing .venv, so phase commits ran without pre-commit hooks; covered by 16-06 make validate.
