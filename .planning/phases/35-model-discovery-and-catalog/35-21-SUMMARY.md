---
phase: 35-model-discovery-and-catalog
plan: 21
subsystem: catalog
tags: [context, precedence, user-stated, runtime-rows]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-04 ContextOverride, 35-14 apply_facts and runtime_updates, 35-15 snapshot figures, 35-16 tier pass, 35-19 and 35-20 report rows"
provides:
  - "catalog_context.py: valid_tokens, host_figures, models_dev_figure, override_for, resolve_context"
  - "catalog_facts.runtime_updates(entry, inputs, known_ids, key, sources): per-runtime context fact, ctx_window and ctx_note"
  - "catalog_facts.keep_user_stated: a user-stated fact is never overwritten by pass 1 or pass 2 of apply_facts"
  - "tests/test_catalog_context.py: 14 tests (TestContextPerRuntime 2, TestContextRules 12)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_context.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py
    - tests/test_catalog_context.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (705 s, status=ok exit=0, attempts=1, cycles=0); a second lane run (lane-35-21-fix, 216 s, status=ok exit=0) tried a fix-up that was reverted, see below"
---

# Phase 35 Plan 21: context per runtime and user-stated facts kept

One commit, `d6ab9d8 feat(35-21): resolve context per runtime` (pre-fold); the commit hook ran 98/98 modules green. The executor's first test and lint
runs found issues, which it fixed before committing.

## Accomplishments

- Context precedence per (runtime, model): `[[models.context]]` override (user-stated), then the host figure (pi `context_window`; opencode
  `limit.input`, then `limit.context`; codex `context_window`), then the entry's own models.dev row (or a unanimous bare-id row across
  providers), else unknown. Only positive ints count; an invalid value is skipped and named in `ctx_note`; a host value keeps its listing's own
  time. With models.dev down and no other source, the cached context and `ctx_window` stay.
- `keep_user_stated` filters the new facts of pass 1 (models.dev facts and the router class) and of pass 2 (tier, class, strengths), so a
  `confirm-model` correction labeled user-stated survives every refresh; a removed override is recomputed from the host or models.dev.

## Deviations and notes for the code review

- Plan versus validator: the plan (Task 1 step 4, SPEC R6) says a runtime with no window, while models.dev answered, gets `context: None` (key
  cleared). The code writes `fact(None, "measured", "models.dev", <time>)` instead, so the row holds a context fact with value None. I tried the
  literal plan text through a fix-up lane: `model_catalog._context_problem` (plan 35-03, `value is None or a positive int`) and
  `catalog_labels.show(fact(None, ...)) == "unknown"` make a None-valued context fact the validated representation of unknown, and an explicit
  `context: None` on an incoming row is rejected by `fact_problem` before the merge (nine tests of `test_catalog_build_sources` and
  `test_catalog_context` failed). I reverted that attempt (no commit). Decision for the orchestrator: keep the None-valued fact, or change the
  validator to accept an explicit None and the row writer to clear the key; neither belongs in this plan. The report and `show` read both as
  `unknown`; a consumer that tests `row.get("context")` for truthiness must test `["value"]` instead.
- `TestContextRules` holds 12 tests (the plan text says eleven in one place and lists twelve in another).
- No file outside `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_context tests.test_catalog_build_sources tests.test_catalog_tiers tests.test_catalog_stale tests.test_ai_kit_spec tests.test_arch_hardcoded_models tests.test_skill_text_history tests.test_arch`:
  exit 0, 8/8 modules (14, 19, 20, 15, 693, 14, 45 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: all rc 0.
- I read `catalog_context.py` whole and the `catalog_facts.py` diff.
- Real-config audit (`audit_c2.py` against the wave 8 marker): two pi session logs and the Claude host's own files (`.ponytail-active`,
  `daemon.log`, `daemon/roster.json`, `ponytail-modes`); nothing from the lane.

## Self-Check: PASSED
