---
phase: "19"
slug: "evaluation-on-claude"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-17"
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups `unit`, `e2e` real node, `arch`) |
| **Config file** | `tools/run_unittest_parallel.py` (`E2E_MODULES`), generated listing via `tools/gen_test_groups.py`, `tests/test_gate_scope.py` |
| **Quick run command** | `python3 -m unittest tests.test_gsd_curated_eval tests.test_curated_config_apply tests.test_gate_scope` |
| **Full suite command** | `make test && make validate` (phase gate adds `make e2e-docker`) |
| **Estimated runtime** | quick ~30 s; matrix module ~30 s (420 `resolve-model` calls); full suite ~10 min |

---

## Sampling Rate

- **After every task commit:** quick run command for the touched module plus `tests.test_gate_scope`
- **After every plan wave:** `python3 tools/run_unittest_parallel.py --group unit` and `--group e2e`
- **Before `/gsd-verify-work`:** `make test`, `make validate`, `make e2e-docker`, digest check, pid leak check, protected-set snapshot (repo set plus `~/.claude` config hashes and the worktree `.claude/gsd-core` tree hash) all clean
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

Task IDs are filled by the planner; one row per requirement behavior until then.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 1 | APP-05 | — | N/A | e2e (real node) | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` (5 combos × P1/P2 × 35 agents; Control 1 fails, Control 2 passes; oracle asserts equal agent keys) | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | EVAL-03 | T-19-* | scratch-only apply; refuses real apply on the ai-kit root; protected set byte-identical | unit + e2e | `python3 -m unittest tests.test_gsd_curated_eval tests.test_curated_config_apply_e2e` | ❌ W0 (helper) / ✅ (apply e2e) | ⬜ pending |
| TBD | TBD | 1 | EVAL-01 | T-19-* | headless runs confined to scratch dirs; no `~/.claude` config change | unit (grader, non-vacuity on a wrong transcript) | `python3 -m unittest tests.test_gsd_curated_eval` | ❌ W0 | ⬜ pending |
| TBD | TBD | 2+ | EVAL-01 | — | N/A | unit (doc contract) | `python3 -m unittest tests.test_curated_config_apply -k TestSkillDocCommands` | ✅ | ⬜ pending |
| TBD | TBD | 3+ | EVAL-02 | — | N/A | script | digest check of final SKILL.md (+ `references/`) against every non-superseded judge row | ❌ W0 | ⬜ pending |
| TBD | TBD | last | R7/R8 | — | N/A | unit + gate | evidence field-presence check; `make test && make validate` | ❌ W0 / ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/gsd_curated_eval.py` + `tests/test_gsd_curated_eval.py` — helper (`smoke`, `matrix`, `fixture`, `snapshot`, grader, plan-copy fault injector, ai-kit-root refusal) and its unit tests
- [ ] `tests/test_ai_kit_gsd_curated_config_matrix.py` + `E2E_MODULES` entry + `python3 tools/gen_test_groups.py`
- [ ] `skills/ai-kit-gsd-curated-config/evals/01..04-*.md` (B, C, D, E with scripted answers)
- [ ] digest-check script and pid-snapshot leak check
- [x] Harness spike (orchestrator, 2026-10-17): see `19-RESEARCH.md` "Harness Spike Results"

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RED/GREEN pressure runs B–E | EVAL-01 | needs a real Claude Code login (headless `claude -p`); orchestrator-only, graded by the scripted grader | run per `19-PRESSURE-TESTS.md` header flags; record init-event fields, digest, verdict per expectation |
| Live smoke from the claude host | EVAL-03 | host detection must be a real claude session | `python3 tests/gsd_curated_eval.py smoke`; record in `19-SMOKE.md` |
| In-session `/skill-judge` | EVAL-02 | needs the Skill tool in the host session | judge final digest; pi judges via the runner in review mode |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
