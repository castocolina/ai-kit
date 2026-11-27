---
phase: "41"
slug: "superpowers-adapter-refactor-with-spec-config-handoff"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-25"
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `unittest` through `tools/run_unittest_parallel.py` (one subprocess per module; groups `unit`, `unit-uv`, `integration`, `e2e`, `arch`) |
| **Config file** | none (groups are sets in `tools/run_unittest_parallel.py`; a new `tests/test_*.py` joins `unit`; `python3 tools/gen_test_groups.py` rewrites the Makefile and pre-commit listings) |
| **Quick run command** | `python3 tools/run_unittest_parallel.py tests.<module> [tests.<module> ...]` |
| **Full suite command** | `make test` (unit, integration, e2e incl. the runner self-test shards and `bash tests/test_install.sh`, arch) |
| **Estimated runtime** | ~10 seconds per slice module set; `make test` several minutes |

---

## Sampling Rate

- **After every task commit:** the slice's modules (the commit-stage `staged-tests` hook runs the covering modules)
- **After every plan wave:** `python3 tools/run_unittest_parallel.py --group unit` and `--group arch`, plus `make check-dogfood`
- **Before `/gsd-verify-work`:** `make test`, `make e2e-docker`, `python3 -m unittest tests.test_wizard_pty` (through `make test-integration`) and `make check-dogfood` green
- **Max feedback latency:** 60 seconds (commit budget)

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| EXE-01 (R1) | exactly one `## Pinned resume` and one `## Owner stop`; quoted rules only in their home; a planted second copy fails; SKILL.md <= 300 lines; the 14 evals still pass shape | unit (doc contract) | `python3 tools/run_unittest_parallel.py tests.test_adapter_single_definitions tests.test_ai_kit_spec_superpowers tests.test_skill_evals_shape` | ❌ W0 `tests/test_adapter_single_definitions.py` |
| EXE-01 (R2) | each flag alone, both, neither, no eligible target keeps the lane, non-boolean refused with the key named, unknown anchor exit 3; guard rows | unit (fake lanes) | `python3 tools/run_unittest_parallel.py tests.test_adapter_escalation_flags tests.test_lane_settings tests.test_spec_config_flow_text` | ❌ W0 `tests/test_adapter_escalation_flags.py` |
| EXE-04 (R3) | flag round trip through render-toml and resolve; false dropped; non-boolean refused; flag on and every lane unavailable runs native; jev haiku/sonnet pick when confident on a Claude Code host; low/missing/other answer keeps the session model; flag off names ai-kit-spec-config; an available lane never replaced; jev payload holds summaries only | unit (fake jev `run`, scratch HOME) | `python3 tools/run_unittest_parallel.py tests.test_adapter_session_fallback tests.test_lane_settings tests.test_config_role_write tests.test_spec_config_flow_text` | ❌ W0 `tests/test_adapter_session_fallback.py` |
| EXE-05 (R4) | builders return caller text framed once, nothing when none; braces verbatim; fixed order; no framework name in the module; dispatch fixture carries both blocks | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec tests.test_ai_kit_spec_superpowers` | extend existing |
| EXE-05 (R5) | (a) exit-code sentence; (b) owner-config pathspec; (c) no `<task>` block in the Compose template, coverage n/a documented; (d)(e) identical blocks on first, fix-round, resumed and native print; (f) gates block | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_superpowers tests.test_adapter_single_definitions` | extend |
| EXE-08 (R6) | runner exec lane gets `AI_KIT_REFUSE_REAL_HOME=1` in a marker folder, its subdirectory and with an inherited other value; absent in a plain repo and in review mode | e2e (runner self-test shards) | `python3 tools/run_unittest_parallel.py --group e2e` (the `tests.test_cross_ai_selftest_*` shards) | extend runner self-test |
| EXE-08 (R6 dogfood) | project runner copy pristine at template version 14, same outside the config block | dogfood | `make check-dogfood` | ✅ |
| EXE-08 (R7) | changed synthetic file in a scratch HOME reported with its path and the observation label; untouched reports nothing; two files in list order; spaces and non-ASCII verbatim; folders never listed; return code unchanged | unit (scratch HOME) | `python3 tools/run_unittest_parallel.py tests.test_host_config_audit tests.test_ai_kit_spec_superpowers` | ❌ W0 `tests/test_host_config_audit.py` |
| EXE-09 (R8) | flagged lane on quota switches to a different-pool fallback; blocked pool skipped at selection; expired pool tried once; unflagged lane stops; no eligible fallback reported; same-pool skipped; earlier of two fallbacks taken; review callers unchanged | unit (fake reader, fake clock) | `python3 tools/run_unittest_parallel.py tests.test_adapter_executor_switch tests.test_lane_switch tests.test_lane_failure_text tests.test_cross_ai_skill_text tests.test_quota_policy_text` | ❌ W0 `tests/test_adapter_executor_switch.py` |
| EXE-01/04/08 (R9) | one detailed home per new topic, SKILL.md pointer only | unit (doc contract) | `python3 tools/run_unittest_parallel.py tests.test_adapter_single_definitions tests.test_skill_text_history` | ❌ W0 (same module as R1) |
| JDG-04 (R10) | 18 evals, shape, text history, judge records | unit + dogfood | `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape tests.test_skill_text_history tests.test_check_dogfood`; `make check-dogfood` | ✅ |
| Arch | lane-setting guard, lookup copies, hardcoded models, gate scope | arch | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_arch_hardcoded_models tests.test_lane_settings tests.test_gate_scope` | ✅ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_adapter_single_definitions.py` with its non-vacuity case (41-01)
- [ ] `ALLOWED_READERS` / `READERS` / `FLAGS` rows for each new reader and caller, each with a non-vacuity row (41-02, 41-03, 41-04, 41-10)
- [ ] A marker-folder fixture for the runner self-test (two marker files in a temp folder) (41-07)
- [ ] Scratch-HOME fixtures for the audit (41-09)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Installed-layout run of the new adapter subcommands from linked skill folders | EXE-01, EXE-04, EXE-08, EXE-09 | needs a scratch project with linked skills, not a module | closing plan 41-14 layout check |
| Skill-judge loop of the changed skills | JDG-04 | judge lanes are external models | judge plan 41-13 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
