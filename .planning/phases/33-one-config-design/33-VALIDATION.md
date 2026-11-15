---
phase: "33"
slug: "one-config-design"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-14"
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 33-RESEARCH.md
> "Validation Architecture"; module names are proposals until the plans fix them.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest`, one subprocess per module via `tools/run_unittest_parallel.py`; runner template `cross-ai.mjs --self-test` shards |
| **Config file** | groups in `tools/run_unittest_parallel.py` (regenerate `Makefile` / `.pre-commit-config.yaml` with `python3 tools/gen_test_groups.py`) |
| **Quick run command** | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.<module> [...]` |
| **Full suite command** | `AI_KIT_REFUSE_REAL_HOME=1 make test` |
| **Estimated runtime** | quick ~10-30 s per module set; full several minutes |

---

## Sampling Rate

- **After every task commit:** the module(s) the task touched (quick run command)
- **After every plan wave:** `AI_KIT_REFUSE_REAL_HOME=1 make test-unit`
- **Before `/gsd-verify-work`:** `AI_KIT_REFUSE_REAL_HOME=1 make test`, `AI_KIT_REFUSE_REAL_HOME=1 make check-dogfood`, `python3 tools/judge_loop.py check .planning/judge` green
- **Max feedback latency:** 60 seconds (commit budget)

---

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| R1, R2 (CFG-01) | every settings file name from the path functions is in `docs/config/design.md` with one assignment; neutral names; no secret value | unit | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_config_design_record` | ✅ | ✅ green |
| R3 (CFG-05) | unknown table kept byte-equal through a write; review and execute lanes under their roles; section comments kept (WR-02) | unit | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_toml_splice tests.test_config_layers` | ✅ | ✅ green |
| R4 (CFG-02) | local, global, both, local-only, comments+legacy, purpose execute/both (D-24), second run, old-and-new, interrupted; `[lanes]`-only post-publish check (WR-04) | unit | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_config_migrate` | ✅ | ✅ green |
| R5 | trust carried, untrusted stays, unrelated edit keeps, command edit drops; dated command entry (WR-01); one-read trust-local (WR-03); linked project config refused (CR-01) | unit | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_trust tests.test_config_migrate tests.test_config_layers` | ✅ | ✅ green |
| R6 (CFG-02) | no runtime code or doc outside migration names `review-spec.toml`; roster tests on new paths | unit | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_config_callers tests.test_ai_kit_spec tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec_check_providers` | ✅ | ✅ green |
| R7 (CFG-03) | runner retry sources and both migrations, key-by-key migration (WR-52), subset reader per D-07 (CR-51, WR-51), `--print-argv` writes nothing (WR-53), linked `.aikit` refused (SEC-W1) (self-test `logic` cases) | e2e | `AI_KIT_REFUSE_REAL_HOME=1 make e2e-test` (shards `tests/test_cross_ai_selftest_*`) | ✅ | ✅ green |
| R8 (CFG-06) | no `.planning/` created; no foreign key written to a GSD config | unit + e2e | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_config_callers` (TestNoPlanning, TestForeignKeys) + runner cases | ✅ | ✅ green |
| R9 (CFG-04) | diff limited to written key; interrupted write keeps old file; status-line recovery atomic | unit + e2e | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_toml_splice tests.test_setup` + runner cases | ✅ | ✅ green |
| R10 | resolver parity (absolute, relative, empty, whitespace XDG; no home); jev consent with no home exits 2 (IN-05) | unit (+ node part) | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_config_dir_parity tests.test_jev_fast_decision` | ✅ | ✅ green |
| R11 (JDG-04) | docs updated; loop `33` records valid (spec-config round 2 bar met, curated-config round 1 bar met) | unit + judge | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge` | ✅ | ✅ green |
| dogfood | rendered runner pristine; live `.planning/` untouched | pre-push | `AI_KIT_REFUSE_REAL_HOME=1 make check-dogfood` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements; the new test modules are created by the plans that need
them (test first where practical).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First post-install run migrates this machine's two rosters | R4, R5 | real config, read-only re-check only | after install from the phase branch tip, read `.aikit/config.toml` and the user `config.toml`, confirm `review-spec.toml.migrated` exists and `trust-local --show` reports the expected state |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-15

---

## Validation Audit 2026-11-15

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Every map row names an existing module (the proposed `tests.test_config_no_planning` became the
`TestNoPlanning` class in `tests/test_config_callers.py`). The code-review fixes (CR-01, CR-51, WR-01..WR-04,
WR-51..WR-53, SEC-W1, IN-05, IN-06, IN-51) each landed with a regression test, so no gap needed a new test from
the auditor. Run on the close-out tree: the twelve unit modules above 12/12 passed
(`tmp/auto/r325/c33-validate.sh`, exit 0); `judge_loop.py check .planning/judge` exit 0; the e2e and full tiers
run in the close-out gate (`make test`).
