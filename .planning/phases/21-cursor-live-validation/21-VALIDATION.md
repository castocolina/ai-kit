---
phase: "21"
slug: "cursor-live-validation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/cursor_models.txt` (from the 2026.10.14 capture), an empty-account fixture and a failure fixture — SPEC-06
- [ ] `tests/test_cursor_agents.py` — AGT-01 (frontmatter parser port, non-fast pins, name collisions)
- [ ] `cursor-agents/composer-worker.md`, `cursor-agents/grok-worker.md` — AGT-01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cursor smoke from the user's interactive cursor session | EVAL-07 | SPEC R1: the user's own session is the acceptance evidence; headless runner evidence is labeled as such | `21-INTERACTIVE-CURSOR.md` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
