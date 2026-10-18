---
phase: "20"
slug: "live-validation-on-codex-opencode"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-17"
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Seeded from
> `20-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups `unit`, `e2e`, `arch`) |
| **Config file** | `tools/run_unittest_parallel.py`; `tests/test_gate_scope.py` enforces group membership |
| **Quick run command** | `python3 -m unittest tests.test_gsd_curated_eval tests.test_ai_kit_spec_runtimes_table tests.test_curated_config_followups tests.test_curated_config_recommend tests.test_gate_scope` |
| **Full suite command** | `make test && make validate` |
| **Estimated runtime** | ~60 seconds quick, several minutes full |

---

## Sampling Rate

- **After every task commit:** the quick run command for the touched module plus `tests.test_gate_scope`
- **After every plan wave:** `python3 tools/run_unittest_parallel.py --group unit` and `--group e2e`
- **Before `/gsd-verify-work`:** `make test`, `make validate`, snapshot `--check` clean, `secret-scan` clean, no orphan `codex`/`opencode` processes started by the run
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled by the planner and executor from the PLAN.md `<automated>` commands.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-T1 | 01 | 1 | EVAL-04 (R4) | T-20-01 | matrix applies only to scratch projects | unit + real node | `python3 -m unittest tests.test_gsd_curated_eval -k TestOracle -k TestMatrixEnv && python3 tests/gsd_curated_eval.py matrix --host codex` | exists (extend) | ⬜ |
| 20-01-T2 | 01 | 1 | EVAL-05 (R7) | T-20-02 | labels-only matrix output | unit + e2e | `python3 -m unittest tests.test_gsd_curated_eval && python3 tests/gsd_curated_eval.py matrix --host opencode && python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` | exists (extend) | ⬜ |
| 20-02-T1 | 02 | 2 | EVAL-04 (R1, R2, R5) | T-20-03, T-20-05 | throwaway HOME install; scratch under system temp | unit + real node | `python3 -m unittest tests.test_gsd_curated_eval -k TestSmoke && python3 tests/gsd_curated_eval.py smoke --host codex --evidence-out tmp/p20/local-codex.md` | exists (extend) | ⬜ |
| 20-02-T2 | 02 | 2 | EVAL-04/05 (D-10) | T-20-04, T-20-06 | allowlist guard never names credential files | unit | `python3 -m unittest tests.test_gsd_curated_eval -k TestSnapshot -k TestSmoke && python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/snap.json` | exists (extend) | ⬜ |
| 20-02-T3 | 02 | 2 | EVAL-05 (R1, R5) | T-20-04 | no managed-service call; `--keep-scratch` leaves only a system-temp dir | unit + real node | `python3 -m unittest tests.test_gsd_curated_eval && python3 tests/gsd_curated_eval.py smoke --host opencode --evidence-out tmp/p20/local-opencode.md && python3 tools/run_unittest_parallel.py --group unit && python3 tools/run_unittest_parallel.py --group e2e` | exists (extend) | ⬜ |
| 20-03-T1 | 03 | 1 | EVAL-05 (R8) | T-20-07 | opencode executes on a private server (the `opencode models` preflight stays read-only on the shared service); this repo's runner re-rendered | self-test + e2e | `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test && node .planning/scripts/cross-ai.mjs --self-test && python3 -m unittest tests.test_cross_ai_runner_e2e tests.test_curated_config_script` | exists | ⬜ |
| 20-03-T2 | 03 | 1 | EVAL-05 (R6) | T-20-08 | host slug never a lane | unit | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_plan_edit -k never_a_review_lane` | exists (extend) | ⬜ |
| 20-04-T1 | 04 | 3 | EVAL-04 (R2, R3, R4, R8) | T-20-09..12 | names-only env; snapshot before/after | live headless | `grep -q 'AIKIT-XAI status=ok cli=codex' 20-SMOKE-CODEX.md && python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/plan04.before.json` | new evidence | ⬜ |
| 20-04-T2 | 04 | 3 | EVAL-05 (R5, R7, R8) | T-20-09..12 | standalone server; no service touch | live headless | `grep -q 'AIKIT-XAI status=ok cli=opencode' 20-SMOKE-OPENCODE.md && grep -q -- '--standalone' 20-SMOKE-OPENCODE.md` | new evidence | ⬜ |
| 20-04-T3 | 04 | 3 | EVAL-04/05 (R8; 18 #6, #11, #12) | T-20-11 | group kill, ps proof | live headless | `grep -q 'status=signal' 20-SMOKE-CODEX.md && grep -q 'runtime_enumeration' 20-SMOKE-OPENCODE.md` | new evidence | ⬜ |
| 20-05-T1 | 05 | 4 | EVAL-04 (R3; SC3) | T-20-13 | labels never exceed the evidence | unit | `python3 -m unittest tests.test_ai_kit_spec_runtimes_table && python3 -m unittest tests.test_ai_kit_spec -k TestDetectCurrentRuntime -k TestRuntimePrecedenceMatrix -k TestChildEnv -k TestDispatchReviewerRealChild` | exists (update) | ⬜ |
| 20-05-T2 | 05 | 4 | EVAL-05 (R5, R6; D-12) | T-20-13 | report-only gitignore note | unit | `python3 -m unittest tests.test_curated_config_followups tests.test_curated_config_cross_ai tests.test_curated_config_apply tests.test_curated_config_recommend` | exists (extend) | ⬜ |
| 20-05-T3 | 05 | 4 | EVAL-05 (skill rule) | T-20-14 | judge reports scanned before the move | live judge | `python3 tests/gsd_curated_eval.py digest --check 20-SKILL-JUDGE.md && python3 tests/gsd_curated_eval.py secret-scan skill-judge` | new evidence | ⬜ |
| 20-06-T1 | 06 | 5 | EVAL-04/05 (D-01) | T-20-15, T-20-16 | names-only scripts; scratch-only commands | doc + secret-scan | `python3 tests/gsd_curated_eval.py secret-scan .planning/phases/20-live-validation-on-codex-opencode` | new | ⬜ |
| 20-06-T2 | 06 | 5 | EVAL-04/05 (R9) | T-20-SC | gates with counts; snapshot against the plan's own baseline | full | `make test && make validate && make e2e-docker && python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/plan06.before.json` (`make test` already runs the e2e tier) | exists | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence paths in the Automated Command column are relative to `.planning/phases/20-live-validation-on-codex-opencode/` where a bare file name is given.

---

## Wave 0 Requirements

- [ ] host-aware `promised`/Control tests replacing the non-claude refusal test
- [ ] smoke install-step seam tests (installer argv, cwd, HOME, ordering, failure stops before inventory)
- [ ] allowlist snapshot tests, including the TOML semantic compare
- [ ] planned == baked readers with fixtures (frontmatter, TOML)
- [ ] `live_tables` exports `RUNTIME_PROFILE_MAP`
- [ ] host-parametrized "never the host lane" test in recommend

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Smoke from the user's interactive codex session | EVAL-04 | SPEC constraint: only the user's own interactive session counts | The per-host script produced by this phase |
| Smoke from the user's interactive opencode session | EVAL-05 | Same | The per-host script produced by this phase |
| `CODEX_*` env names in the codex TUI shell | EVAL-04 (D-05) | Only the interactive TUI shows its own env | Names-only listing step in the codex script; afterwards the `TUI confirmation pending` labels in `detection.py` are updated with the table test (20-06 `## What happens next`) |
| Project agents win over global ones in the opencode loader | EVAL-05 (R5 precedence) | `opencode debug agents` has no `--standalone` and would read the user's managed service | Optional step 7 of the opencode script: `smoke --host opencode --keep-scratch`, ask opencode inside the kept scratch project, delete it |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
