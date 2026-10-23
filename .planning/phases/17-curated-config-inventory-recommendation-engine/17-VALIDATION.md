---
phase: "17"
slug: "curated-config-inventory-recommendation-engine"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: true) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-15"
validated: "2026-10-15"
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` tiers (CPU-share-capped, one subprocess per module) |
| **Config file** | `tools/run_unittest_parallel.py` (`EXPLICIT_GROUPS`); listings from `tools/gen_test_groups.py`; enforced by `tests/test_gate_scope.py` |
| **Quick run command** | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_inventory -v` |
| **Full suite command** | `make test` (plus `make validate` before close) |
| **Estimated runtime** | ~10 seconds quick, ~120 seconds full |

---

## Sampling Rate

- **After every task commit:** run the quick command for the touched module(s)
- **After every plan wave:** `make test-unit && make arch-test`
- **Before `/gsd-verify-work`:** `make test` and `make validate` must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

### Requirement → Test Map

| Req ID | Behavior | Test Type | Automated Command | Status |
|--------|----------|-----------|-------------------|--------|
| INV-01 / R1 | read-only project byte-identical; inventory shape | unit + e2e (real node) | `python3 -m unittest tests.test_curated_config_inventory` (TestReadOnly, TestCompleteInventory); `python3 -m unittest tests.test_curated_config_e2e` (TestReadOnlyRealGsd, TestRealGsdInventory) | ✅ green |
| R2 | local gsd-core beats global + scope; exit 2 with searched paths; probe null/fail exits 2 | unit | `python3 -m unittest tests.test_curated_config_inventory` (TestGsdCoreResolution, TestProbeFailures) | ✅ green |
| INV-02 / R3 | fresh / stale+warning / none markers; refresh argv and order | unit | `python3 -m unittest tests.test_curated_config_inventory` (TestCatalogStates, TestGracefulRefreshTimeout) | ✅ green |
| R4 | unscored catalog: no catalog-score source; claude/codex no overrides; opencode/cursor needs_choice | unit | `python3 -m unittest tests.test_curated_config_recommend` (TestSlotEdges: unscored_price_order, codex_unscored_keeps_native, cursor_no_catalog_needs_choice); `python3 -m unittest tests.test_curated_config_inventory` test_unscored_catalog_scored_false | ✅ green |
| INV-03 / R5 | conflict matrix incl. GSD_HOME, latent global omit, runtime mismatch, global info | unit + e2e | `python3 -m unittest tests.test_curated_config_inventory` (TestConflictMatrix); `python3 -m unittest tests.test_curated_config_recommend` (TestReconcileConflicts); `python3 -m unittest tests.test_curated_config_golden` (TestConflictsEndToEnd) | ✅ green |
| R6 | AGENTS-only / CLAUDE-only / both / neither; frontend; db | unit | `python3 -m unittest tests.test_curated_config_inventory` (TestProjectFacts) | ✅ green |
| REC-01 / R7 | byte-identical reruns; build_plan purity patch; AST import guard; CLI recommend reads only its inventory and writes only --out; bad schema exit 2 | unit | `python3 -m unittest tests.test_curated_config_recommend` (TestRecommendTracer, TestPurity, TestCliRecommendIo, TestInventoryValidation) | ✅ green |
| REC-02 / R8 | models.* only on whole-phase shifts | unit + golden | `python3 -m unittest tests.test_curated_config_recommend` (TestPhaseShifts); `python3 -m unittest tests.test_curated_config_golden` | ✅ green |
| REC-03 / R9 | native kept, anthropic/* replaced, -fast never chosen, router wins, cap fallback, at-ceiling, family percentile, effort variants | unit + golden | `python3 -m unittest tests.test_curated_config_recommend` (TestSlotTracer, TestSlotEdges, TestRolesHelpers); `python3 -m unittest tests.test_curated_config_inventory` (TestBuildCandidates); `python3 -m unittest tests.test_curated_config_golden` | ✅ green |
| REC-04 / R10 | <=7 overrides; counterpart vendor; vision note; single-provider note; pi no overrides | unit + golden | `python3 -m unittest tests.test_curated_config_recommend` (TestSpecialistRules, TestSpecialistProperties); `python3 -m unittest tests.test_curated_config_golden` (TestGoldenProperties) | ✅ green |
| REC-05 / R11 | every spec section 5 key/value per rigor | unit | `python3 -m unittest tests.test_curated_config_recommend` (TestPresets, TestCrossAi, TestEffectLabels) | ✅ green |
| REC-06 / R12 | unknown keys dropped with notes; unprobed key fails closed | unit + e2e | `python3 -m unittest tests.test_curated_config_recommend` (TestKeyDrop, TestPerLayerDrop, TestUnprobedKeys); `python3 -m unittest tests.test_curated_config_e2e` (TestGoldenTables) | ✅ green |
| R13 | order-independent ties; leftover managed keys unset; model_policy unset per leaf incl. runtime_tiers | unit | `python3 -m unittest tests.test_curated_config_recommend` (TestDeterminism, TestReconcileTracer, TestReconcileConflicts, TestReconcileComposition) | ✅ green |
| D-15 | score_exact present, unrounded; score unchanged | unit | `python3 -m unittest tests.test_ai_kit_spec` -k score_exact | ✅ green |
| D-24 | opencode 2.x parser, version gate, server stopped on every path, password never output, 1.x unchanged | unit | `python3 -m unittest tests.test_ai_kit_spec` (TestOpencodeApiImageInput) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/fixtures/curated_config_v2/gsd_tables_1_16.json`: tables captured once from the installed 1.16 (D-20), placeholder paths only
- [x] `tests/fixtures/curated_config_v2/` trimmed model lists (cursor, opencode, codex, claude) plus a synthetic pi list (labelled)
- [x] `tests/fixtures/opencode_api_model.json`: the spike sample (4 entries)
- [x] the four test modules (`inventory`, `recommend`, `golden`, `e2e`), then `python3 tools/gen_test_groups.py`
- [x] golden regeneration flag (env `UPDATE_GOLDEN=1`), never on by default

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| opencode 2.x probe against a real `opencode serve` (D-24/D-32) | INV-01 | the suite uses a fake server; a live run needs opencode 2.x | run `inventory` under a scratch HOME/XDG, then check that `image_input_source` is the 2.x API and that no probe server is still running (`pgrep`) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-15 (Nyquist audit: 1 gap filled, `TestCliRecommendIo`)
