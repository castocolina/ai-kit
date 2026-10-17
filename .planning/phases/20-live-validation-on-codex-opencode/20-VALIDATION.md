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

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

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
| `CODEX_*` env names in the codex TUI shell | EVAL-04 (D-05) | Only the interactive TUI shows its own env | Names-only listing step in the codex script |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
