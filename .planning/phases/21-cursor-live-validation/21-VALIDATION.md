---
phase: "21"
slug: "cursor-live-validation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: true) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-18"
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups unit, unit-uv, integration, e2e, arch) |
| **Config file** | `Makefile`, `.pre-commit-config.yaml`; group lists pinned by `tests/test_gate_scope.py` |
| **Quick run command** | `python3 -m unittest <touched test module>` |
| **Full suite command** | `make test && make validate` |
| **Estimated runtime** | ~600 seconds (full); quick < 30 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched module
- **After every plan wave:** Run `python3 tools/run_unittest_parallel.py --group unit` and `--group arch`
- **Before `/gsd-verify-work`:** `make test` and `make validate` must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Filled from the PLAN files (`21-RESEARCH.md` §Validation Architecture maps each requirement to its test).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | SPEC-06 | scan-all PATH, no shell, real_path, SC5 pin | cursor found without running the wrapper | unit | `python3 -m unittest tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_spec_routing` | yes | green (57+27) |
| 21-01-02 | 01 | 1 | SPEC-06 | parse_cursor_models, fixtures, schema bump | ANSI/nameless/empty/failure tolerated | unit | `python3 -m unittest tests.test_ai_kit_spec` | yes | green (701) |
| 21-07-01 | 07 | 2 | SPEC-06 | runner resolveBin scan-all mirror (template 5) | grok-first PATH still finds cursor | unit/self-test | `python3 -m unittest tests.test_gate_scope tests.test_ai_kit_spec_runtimes_table` | yes | green |
| 21-02-01 | 02 | 3 | AGT-01 | pinned files parse, non-fast pins, names, node parity | no `-fast`, no `gsd-*` names | unit | `python3 -m unittest tests.test_cursor_agents` | yes | green (10) |
| 21-02-02 | 02 | 3 | AGT-01 | module registered in gate groups | n/a | unit | `python3 -m unittest tests.test_gate_scope` | yes | green (34) |
| 21-03-01 | 03 | 4 | EVAL-07 | cursor first-root (G1) | no worktree gsd-core mismatch | unit | `python3 -m unittest tests.test_curated_config_inventory` | yes | green (107) |
| 21-03-02 | 03 | 4 | EVAL-07 | baked chain, generated paths, protected set (G2-G4) | semantic cursor guard | unit | `python3 -m unittest tests.test_gsd_curated_eval` | yes | green (302) |
| 21-03-03 | 03 | 4 | EVAL-07 | matrix cursor class 5x35 | no `-fast` pick | e2e | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix` | yes | green (36, 222s) |
| 21-05-01 | 05 | 6 | EVAL-07 | qualified label lift pin | no bare lift | unit | `python3 -m unittest tests.test_curated_config_apply` | yes | green (98) |
| 21-04-01 | 04 | 5 | EVAL-07 | headless live smoke through runner | scratch home, process reap | manual/live | evidence `21-SMOKE-CURSOR.md` (`headless verdict: green`, 10/10) | yes | green (recorded) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/fixtures/cursor_models.txt` (from the 2026.10.14 capture), an empty-account fixture and a failure fixture — SPEC-06
- [x] `tests/test_cursor_agents.py` — AGT-01 (frontmatter parser port, non-fast pins, name collisions)
- [x] `cursor-agents/composer-worker.md`, `cursor-agents/grok-worker.md` — AGT-01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive cursor TUI run (mandatory human item) | EVAL-07 | user session is acceptance evidence | `21-INTERACTIVE-CURSOR.md` |
| Cursor usage-dashboard check | EVAL-07 | needs the real cursor account UI | `21-INTERACTIVE-CURSOR.md` |
| Optional SC5 probe (native selectors) | SPEC-06 | live cursor probe, optional | `21-INTERACTIVE-CURSOR.md` |
| Cursor smoke from the user's interactive cursor session | EVAL-07 | SPEC R1: the user's own session is the acceptance evidence; headless runner evidence is labeled as such | `21-INTERACTIVE-CURSOR.md` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-19; automated coverage complete, manual items remain open (phase stays human_needed)
