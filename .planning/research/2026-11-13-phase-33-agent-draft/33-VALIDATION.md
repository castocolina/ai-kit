---
phase: "33"
slug: "one-config-design"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-13"
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `unittest` through `tools/run_unittest_parallel.py`; the runner's node self-test harness (`cross-ai.mjs --self-test`, sharded by `tests/cross_ai_selftest.py`) |
| **Config file** | none (`pyproject.toml` pins py312; generated group listings in `Makefile` and `.pre-commit-config.yaml` via `python3 tools/gen_test_groups.py`) |
| **Quick run command** | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py <touched modules>` (the plan names them) |
| **Full suite command** | `make test` |
| **Estimated runtime** | quick: ~10-60 seconds; runner shards: ~60-120 seconds; `make test`: several minutes |

---

## Sampling Rate

- **After every task commit:** the quick command for the modules the task touched (the staged-tests hook also runs the covering modules).
- **After every plan wave:** the moved roster tests (`tests.test_ai_kit_spec tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec_trust tests.test_ai_kit_spec_routing tests.test_ai_kit_spec_check_providers tests.test_ai_kit_spec_superpowers`) and, after a runner change, the eight `tests.test_cross_ai_selftest_*_e2e` shards plus `python3 tools/check_dogfood.py`.
- **Before `/gsd-verify-work`:** `make test` green, `make check-dogfood` ok, `python3 tools/judge_loop.py check .planning/judge` exit 0.
- **Max feedback latency:** 120 seconds per task.

---

## Per-Task Verification Map

Filled from the plans' `<verify>` blocks after planning; the requirement-to-test map is in `33-RESEARCH.md`
("Validation Architecture", Phase Requirements -> Test Map).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (per plan) | | | R1-R10 | per plan threat model | see plan | unit / self-test / judge | see plan | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test modules for the record (R1, R2), the layered reader and splicer (R3, R8), the roster migration (R4, R5), the doc-name scan (R6), the resolver parity (R9) and atomic publishing (R8), registered with `python3 tools/gen_test_groups.py`
- [ ] Existing roster tests moved to the new paths; `tests/test_cross_ai_skill_text.py` retry text pins updated
- [ ] New runner self-test cases (R7) with their kinds; `tests/fixtures/cross_ai_selftest_secs.json` and `E2E_RECORDED_SECS` refreshed

*Framework install: none.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Loop `33` judge rounds on `ai-kit-spec-config` and `ai-kit-gsd-curated-config` | R10 (JDG-04) | external referee lanes (opencode via router-env), run by the orchestrator at the checkpoint plan | the judge plan's steps; `python3 tools/judge_loop.py check .planning/judge` exits 0 afterwards |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
