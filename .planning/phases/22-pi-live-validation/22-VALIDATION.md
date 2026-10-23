---
phase: "22"
slug: "pi-live-validation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-23"
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups unit, unit-uv, integration, e2e, arch); phase-dir checkers with `--self-test` |
| **Config file** | `Makefile`, `.pre-commit-config.yaml`; group lists pinned by `tests/test_gate_scope.py` |
| **Quick run command** | `python3 -m unittest <touched test module>` |
| **Full suite command** | `make test && make validate` |
| **Estimated runtime** | ~600 seconds (full); quick < 30 seconds; the real-node pi matrix a few minutes |

---

## Sampling Rate

- **After every task commit:** the touched module's quick command (the commit hook also runs the unit and arch groups)
- **After every plan wave:** `python3 tools/run_unittest_parallel.py --group unit` and `--group arch`; e2e under uv when the harness or fixtures changed
- **Before `/gsd-verify-work`:** `make test` and `make validate` green (22-07 Task 3)
- **Max feedback latency:** 30 seconds (quick)

---

## Per-Task Verification Map

Filled from the PLAN files (`22-RESEARCH.md` §Validation Architecture maps each requirement to its test).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | EVAL-08 (R2) | T-22-01 / T-22-02 | scratch HOME and agent dir, dummy key only | live (local mock) | `python3 -m unittest tests.test_pi_live_tools` (wraps `pi_mock_provider.py --self-test`) | ✅ | ✅ green |
| 22-01-02 | 01 | 1 | EVAL-08 (R2) | T-22-03 / T-22-04 | one-shot `--approve`, no persisted trust, no orphan process | evidence check | verdict consistency script in the task verify (not in a test module) | ❌ | ⬜ gap, not closed |
| 22-02-01 | 02 | 2 | SPEC-05 | T-22-05 | untrusted RPC text never raises, exact ints, one envelope | unit | `python3 -m unittest tests.test_ai_kit_spec -k PiRpc -k RuntimesSchemaVersion -k version_predicate` | yes (class exists) | ⬜ pending |
| 22-02-02 | 02 | 2 | SPEC-05 | T-22-06 | fail-closed trimmer, no transport or key field committed | unit | `python3 -m unittest tests.test_pi_live_tools` (synthetic trimmer cases, green); `tests.test_ai_kit_spec -k trimmed_real_capture` skips until C1 | ✅ | ✅ green |
| 22-03-01 | 03 | 3 | EVAL-08 (R3) | T-22-08 / T-22-09 | bare ids only, labels at evidence level | unit + golden | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_golden` | yes | ⬜ pending |
| 22-03-02 | 03 | 3 | EVAL-08 (R3) | T-22-07 | `--force` cannot pin an unserved or qualified id | unit | `python3 -m unittest tests.test_curated_config_plan_edit tests.test_curated_config_inventory` | yes | ⬜ pending |
| 22-03-03 | 03 | 3 | EVAL-08 (R3, R6) | T-22-08 | label kept, verdict stated | unit | `python3 -m unittest tests.test_curated_config_apply` | yes | ⬜ pending |
| 22-04-01 | 04 | 4 | APP-05 | T-22-10 / T-22-11 | discriminating oracle, scratch applies only | e2e (real node) | `python3 tests/gsd_curated_eval.py matrix --host pi` | yes (harness) | ⬜ pending |
| 22-04-02 | 04 | 4 | APP-05 | T-22-10 / T-22-21 | hook probe pinned both directions | unit + e2e | `python3 -m unittest tests.test_gsd_curated_eval tests.test_ai_kit_gsd_curated_config_matrix` | yes | ⬜ pending |
| 22-05-01 | 05 | 5 | EVAL-08, APP-05 | T-22-12 / T-22-13 | pi credentials never read; real home unchanged | unit + headless smoke | `python3 -m unittest tests.test_gsd_curated_eval` + `smoke --host pi` under a scratch HOME | yes | ⬜ pending |
| 22-05-02 | 05 | 5 | EVAL-08 | T-22-14 | headless evidence never claims R4 | evidence check | verdict-line script + `secret-scan` (not in a test module) | ❌ | ⬜ gap, not closed |
| 22-06-01 | 06 | 6 | EVAL-08 (R6) | T-22-15 | no unearned label lift | self-test | `python3 -m unittest tests.test_pi_live_tools` (wraps `check_pi_live.py --self-test`) | ✅ | ✅ green |
| 22-06-02 | 06 | 6 | EVAL-08, SPEC-05 | T-22-16 / T-22-17 | names-only env, raw capture never leaves tmp | doc check | task verify (headings, commands, no absolute path) (not in a test module) | ❌ | ⬜ gap, not closed |
| 22-07-01 | 07 | 7 | EVAL-08 (R6) | T-22-18 | report digests bind the judged bytes | evidence check | `python3 tests/gsd_curated_eval.py digest --check .planning/phases/22-pi-live-validation/22-SKILL-JUDGE.md` (prints `digests ok`) | ✅ | ✅ green |
| 22-07-02 | 07 | 7 | EVAL-08 (R6) | T-22-18 | pass rule per judge vs its own baseline | evidence check | judge-gate script in the task verify (not in a test module) | ❌ | ⬜ gap, not closed |
| 22-07-03 | 07 | 7 | EVAL-08 (R7) | — | gates green, checker armed | full suite | `make test && make validate` | yes | ⬜ owned by 22-07 Task 3, not run by this audit |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `live/pi_mock_provider.py` with `--self-test` (22-01), wrapped by `tests/test_pi_live_tools.py`
- [x] `live/trim_pi_capture.py` synthetic cases in `tests/test_pi_live_tools.py`; `TestPiRpcModels.test_trimmed_real_capture` still awaits C1 (22-02)
- [ ] pi branches in `tests/gsd_curated_eval.py` (matrix, controls, `pi_hook_probe`, smoke chain, protected entries) (22-04, 22-05)
- [ ] `TestResolveModelMatrixPi` and `TestPiHookProbe` in `tests/test_ai_kit_gsd_curated_config_matrix.py` (22-04)
- [x] `live/check_pi_live.py` with `--self-test` (22-06), wrapped by `tests/test_pi_live_tools.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real RPC capture of the user's pi models trimmed into the fixture | SPEC-05 (R1 acceptance, ROADMAP SC3) | needs the real pi agent dir and credentials, which this run never reads (ruling Q2) | `22-INTERACTIVE-PI.md` C1 |
| Interactive smoke from the user's pi session with the skill loaded | EVAL-08 (R4, R5; ROADMAP SC1) | needs the user's interactive pi session (D-10) | `22-INTERACTIVE-PI.md` S1-S5 |
| `PI_CODING_AGENT` present in the live session env | EVAL-08 (D-09) | only a real pi session exports it to its bash tool | `22-INTERACTIVE-PI.md` S2, D9 |
| Served-model change on a real provider (L3) | EVAL-08 (R2 upgrade) | spends real model calls; owner approval (ruling Q3) | `22-INTERACTIVE-PI.md` L3a-L3c (optional) |
| Label lift and close-out | EVAL-08 (R6; ROADMAP SC2) | follows the owner's evidence | `22-INTERACTIVE-PI.md ## Orchestrator close-out`; `check_pi_live.py` exits 0 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (evidence-check rows 22-01-02, 22-05-02, 22-06-02, 22-07-02 are still open)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

**Audit (2026-10-23):** nyquist_compliant is false. Automated and green: 22-01-01, 22-02-02 (synthetic trimmer), 22-06-01, 22-07-01. Not closed: 22-01-02, 22-05-02, 22-06-02, 22-07-02 are evidence checks with no test module; they are reported as gaps, not as covered. 22-07-03 is owned by 22-07.

## Validation Audit 2026-10-23

| Metric | Count |
|---|---|
| Gaps found | 6 |
| Resolved | 2 |
| Escalated | 0 |
