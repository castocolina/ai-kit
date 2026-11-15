---
phase: "33"
slug: "one-config-design"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| R1, R2 (CFG-01) | every settings file name from the path functions is in `docs/config/design.md` with one assignment; neutral names | unit | `... tests.test_config_design_record` | ❌ W0 (plan creates) | ⬜ pending |
| R3 (CFG-05) | unknown table kept byte-equal through a write; review and execute lanes under their roles | unit | `... tests.test_toml_splice tests.test_config_layers` | ❌ W0 | ⬜ pending |
| R4 (CFG-02) | local, global, both, local-only, comments+legacy, purpose execute/both (D-24), second run, old-and-new, interrupted | unit | `... tests.test_config_migrate` | ❌ W0 | ⬜ pending |
| R5 | trust carried, untrusted stays, unrelated edit keeps, command edit drops | unit | `... tests.test_ai_kit_spec_trust tests.test_config_migrate` | ✅ / ❌ W0 | ⬜ pending |
| R6 (CFG-02) | no runtime code or doc outside migration names `review-spec.toml`; roster tests on new paths | unit | `... tests.test_config_callers` + updated roster modules | ❌ W0 | ⬜ pending |
| R7 (CFG-03) | runner retry sources and both migrations (self-test `logic` cases) | e2e | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py --group e2e` | ✅ (shards) | ⬜ pending |
| R8 (CFG-06) | no `.planning/` created; no foreign key written to a GSD config | unit + e2e | `... tests.test_config_no_planning` + runner case | ❌ W0 | ⬜ pending |
| R9 (CFG-04) | diff limited to written key; interrupted write keeps old file; status-line recovery atomic | unit + e2e | `... tests.test_toml_splice tests.test_setup` + runner cases | ✅ / ❌ W0 | ⬜ pending |
| R10 | resolver parity (absolute, relative, empty, whitespace XDG; no home) | unit (+ node part) | `... tests.test_config_dir_parity` | ❌ W0 | ⬜ pending |
| R11 (JDG-04) | docs updated; loop `33` records valid | unit + judge | `python3 tools/judge_loop.py check .planning/judge` | ✅ | ⬜ pending |
| dogfood | rendered runner pristine; live `.planning/` untouched | pre-push | `AI_KIT_REFUSE_REAL_HOME=1 make check-dogfood` | ✅ | ⬜ pending |

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
