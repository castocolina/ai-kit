---
phase: "16"
slug: "ai-kit-spec-extensions"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-24"
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `unittest` (stdlib) |
| **Config file** | none — invoked via `python3 -m unittest` |
| **Quick run command** | `python3 -m unittest tests.test_ai_kit_spec.TestDetectCurrentRuntime tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestValidateCatalogEntry tests.test_ai_kit_spec.TestLoadRankingWeights tests.test_ai_kit_spec.TestScoreCandidates tests.test_ai_kit_spec.TestCacheStaleness -v` |
| **Full suite command** | `python3 -m unittest tests.test_ai_kit_spec -v` (phase gate: `make test-unit`) |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (the classes for the module just touched)
- **After every plan wave:** Run `python3 -m unittest tests.test_ai_kit_spec -v`
- **Before `/gsd-verify-work`:** `make test-unit` must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Filled in by the planner per task. The requirement-level map (from 16-RESEARCH.md):

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| SPEC-01 | pi > opencode > cursor > codex > claude order; `CODEX_THREAD_ID`/`CODEX_VERSION`; `PI_CODING_AGENT`; `"pi"` accepted as `native_runtime` | unit | `python3 -m unittest tests.test_ai_kit_spec.TestDetectCurrentRuntime -v` | ✅ (tests to update) | ⬜ pending |
| SPEC-02 | codex (`codex debug models`) and claude (aliases + catalog ids + dated fallback) enumeration, fixture-validated, degrade to `[]` | unit | `python3 -m unittest tests.test_ai_kit_spec.TestBuildRuntimesSnapshot -v` | ❌ W0 | ⬜ pending |
| SPEC-03 | optional `image_input`; `reasoning_modes` populated; old cache entries still load | unit | `python3 -m unittest tests.test_ai_kit_spec.TestValidateCatalogEntry -v` | ❌ W0 | ⬜ pending |
| SPEC-04 | 5 purposes; `review`/`execute` aliases; optional per-purpose floor; old 2-purpose weights file still loads | unit | `python3 -m unittest tests.test_ai_kit_spec.TestLoadRankingWeights tests.test_ai_kit_spec.TestScoreCandidates -v` | ❌ W0 | ⬜ pending |
| D-12 | missing/older `schema_version` counts as stale under `--if-stale` | unit | `python3 -m unittest tests.test_ai_kit_spec.TestCacheStaleness tests.test_ai_kit_spec.TestMainCli -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Per-task map (planner, 2026-09-24)

All plans are cross-AI executed (`cross_ai: true`) and sequential (waves 1-6), since every plan
touches `tests/test_ai_kit_spec.py`. Each task commits once; the quick command runs after that
commit, and the broad stdlib regression command runs at each plan's final task. Broad regression:
`python3 -m unittest tests.test_ai_kit_spec tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_superpowers tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_opencode_providers tests.test_ai_kit_usage_metrics`

| Task | Wave | Req / Decisions (edges, prohibitions) | Type | Automated Command | Status |
|------|------|-----------------|------|-------------------|--------|
| 16-01-T1 | 1 | SPEC-02, SPEC-03 / D-05, D-07, D-08 | tracer | `python3 -m unittest tests.test_ai_kit_spec.TestCodexEnumerationEndToEnd tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestBuildModelCatalog tests.test_ai_kit_spec.TestFetchModelCatalogCli -v` | ⬜ pending |
| 16-01-T2 | 1 | SPEC-02 / D-05, D-06, D-07 (E4, P2) | tdd | `python3 -m unittest tests.test_ai_kit_spec.TestParseCodexDebugModels tests.test_ai_kit_spec.TestDetectCodexModels tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestCodexEnumerationEndToEnd -v` + broad regression | ⬜ pending |
| 16-02-T1 | 2 | SPEC-01 / D-01, D-02, D-03 | tracer | `python3 -m unittest tests.test_ai_kit_spec.TestPiHostEndToEnd tests.test_ai_kit_spec.TestDetectCurrentRuntime tests.test_ai_kit_spec.TestValidateCatalogEntry tests.test_ai_kit_spec.TestRenderAndWriteToml tests.test_ai_kit_spec.TestMainCli -v` | ⬜ pending |
| 16-02-T2 | 2 | SPEC-01 / D-01, D-02, D-06 (E1, E2, E3, P1) | tdd | `python3 -m unittest tests.test_ai_kit_spec.TestRuntimePrecedenceMatrix tests.test_ai_kit_spec.TestPiHostEndToEnd tests.test_ai_kit_spec.TestDetectCurrentRuntime -v` + broad regression | ⬜ pending |
| 16-03-T1 | 3 | SPEC-02 / D-12 (E5) | tracer | `python3 -m unittest tests.test_ai_kit_spec.TestRuntimesSchemaVersion tests.test_ai_kit_spec.TestMainCli tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestCacheStaleness -v` | ⬜ pending |
| 16-03-T2 | 3 | SPEC-03 / D-12 (E5) | tdd | `python3 -m unittest tests.test_ai_kit_spec.TestCatalogSchemaVersion tests.test_ai_kit_spec.TestFetchModelCatalogCli tests.test_ai_kit_spec.TestMergeCatalogEntry tests.test_ai_kit_spec.TestCurrentCandidateKeys tests.test_ai_kit_spec.TestApplyHeuristicCorrections -v` + broad regression | ⬜ pending |
| 16-04-T1 | 4 | SPEC-02 / D-04, D-05, D-07 | tracer | `python3 -m unittest tests.test_ai_kit_spec.TestClaudeEnumerationEndToEnd tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestCatalogSchemaVersion tests.test_ai_kit_spec.TestMainCli -v` | ⬜ pending |
| 16-04-T2 | 4 | SPEC-02 / D-04, D-07 (E4, P2, P3) | tdd | `python3 -m unittest tests.test_ai_kit_spec.TestClaudeFallback tests.test_ai_kit_spec.TestClaudeEnumerationEndToEnd tests.test_ai_kit_spec.TestBuildRuntimesSnapshot -v` + broad regression | ⬜ pending |
| 16-05-T1 | 5 | SPEC-03 / D-09 | tracer | `python3 -m unittest tests.test_ai_kit_spec.TestImageInputEndToEnd tests.test_ai_kit_spec.TestValidateCatalogEntry tests.test_ai_kit_spec.TestBuildModelCatalog tests.test_ai_kit_spec.TestFetchModelCatalogCli -v` | ⬜ pending |
| 16-05-T2 | 5 | SPEC-03 / D-06, D-07, D-09 (E4, P4) | tdd | `python3 -m unittest tests.test_ai_kit_spec.TestOpencodeVerboseImageInput tests.test_ai_kit_spec.TestImageInputEndToEnd tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestDetectOpencodeModels tests.test_ai_kit_spec.TestCodexEnumerationEndToEnd -v` + broad regression | ⬜ pending |
| 16-06-T1 | 6 | SPEC-04 / D-10 | tracer | `python3 -m unittest tests.test_ai_kit_spec.TestPurposeAliasesEndToEnd tests.test_ai_kit_spec.TestLoadRankingWeights tests.test_ai_kit_spec.TestScoreCandidates -v` | ⬜ pending |
| 16-06-T2 | 6 | SPEC-04 / D-10, D-11 (E6, P5) | tdd | `python3 -m unittest tests.test_ai_kit_spec.TestRankerPurposeFloor tests.test_ai_kit_spec.TestPurposeAliasesEndToEnd tests.test_ai_kit_spec.TestLoadRankingWeights tests.test_ai_kit_spec.TestScoreCandidates -v` + broad regression | ⬜ pending |

Orchestrator-only gates (use `uv run`, never run by the cross-AI executor): `make test-unit` after
each wave, `make validate` before `/gsd-verify-work`.

---

## Wave 0 Requirements

- [ ] New test methods in `tests/test_ai_kit_spec.py` for SPEC-02/03/04 and D-12 (no new test files needed)
- [ ] A codex `debug models` fixture built from real captured output (16 D-05)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Codex signal live-verified from a real codex host | SPEC-01 | Needs a real interactive codex session | Deferred to Phase 20 (EVAL-04, 20 D-05) — label stays "observed in session snapshots" |
| Real `fetch-model-catalog` populates `image_input`/`reasoning_modes` | SPEC-03 | Network + optional `ARTIFICIAL_ANALYSIS_API_KEY` | Run `fetch-model-catalog` once live after execution; record result in SUMMARY |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
