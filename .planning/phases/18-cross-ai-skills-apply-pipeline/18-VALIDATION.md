---
phase: "18"
slug: "cross-ai-skills-apply-pipeline"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-15"
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups unit / unit-uv / integration / e2e / arch) |
| **Config file** | `Makefile`, `tools/gen_test_groups.py`, `E2E_MODULES` in the runner |
| **Quick run command** | `python3 -m unittest tests.<touched module>` |
| **Full suite command** | `PATH="$HOME/.local/bin:$PATH" UV_NO_SYNC=1 UV_OFFLINE=1 make test` |
| **Estimated runtime** | ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** the touched module's `python3 -m unittest tests.<module>`, plus `tests.test_arch` and `tests.test_gate_scope` when gates or purity allowlists change
- **After every plan wave:** `make test-unit`; also `make e2e-test` for waves touching the runner, apply or real gsd-tools
- **Before `/gsd-verify-work`:** `make test` and `make validate` green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Requirement-level map from 18-RESEARCH.md §Validation Architecture. The planner binds task ids.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-xx | tbd | tbd | XAI-01 | — | lane ≠ host, vendor rule, empty → convergence off + note | unit + goldens | `python3 -m unittest tests.test_curated_config_cross_ai tests.test_curated_config_golden` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | XAI-02 | runner | byte-deterministic render; header sha256; `.new` on edit; self-test exit classes 0/1/2/69/75/124/127; one `AIKIT-XAI` line; process-group kill; git rules | unit + e2e (node) | `python3 -m unittest tests.test_curated_config_script`; e2e module for `--self-test` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | SKL-01 | path escape | plain, symlink escape, project, plugin (claude vs other host) | unit | `python3 -m unittest tests.test_curated_config_skills` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | SKL-02 | — | caps 2/3/5, facts gating, reference translation, `agent-skills` verification (`warnings == []`, skipped on pi) | unit + e2e | `tests.test_curated_config_skills` + apply e2e | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | SKL-03 | — | missing recommended skill never named; unknown → proposal; empty description skipped | unit | `tests.test_curated_config_skills` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | SKL-04 | secrets | jev only with skill + backend; key value never in output | unit | `tests.test_curated_config_skills` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | APP-01 | cross_ai_command | plan-set/unset refusals, `--force`, `source: user`, sorted, atomic, cross_ai_command guard (D-44) | unit | `python3 -m unittest tests.test_curated_config_plan_edit` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | APP-02 | — | dry run writes nothing; `needs_choice` → exit 2; 4-kind diff; `--inventory` digest check (D-42) | unit | `python3 -m unittest tests.test_curated_config_apply` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | APP-03 | data loss | backup, keep 3, verbatim restore naming failing key, apply marker (D-40) | unit + e2e (real gsd-tools) | `tests.test_curated_config_apply` + apply e2e | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | APP-04 | installer | nothing runs without approval; pinned version + `--local`; effort sync only claude/codex/opencode | unit | `python3 -m unittest tests.test_curated_config_followups` | ❌ W0 | ⬜ pending |
| 18-xx | tbd | tbd | EVAL-06 | — | v1 suite unmodified; gates cover new modules; SKILL.md skill-judge | gate | `python3 -m unittest tests.test_ai_kit_gsd_curated_config tests.test_gate_scope`; `make test`; `make validate` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] pi RPC fixture (trimmed, `baseUrl` stripped, provenance in a docstring) and the D-45 router-merge fixture test
- [ ] skills/plugin fixtures: plain, symlink escape, project, plugin, claude vs other host
- [ ] jev fixtures plus a sentinel test that the key value never appears in output
- [ ] regenerated goldens; purity-guard allowlist update with its non-vacuity counterpart
- [ ] `python3 tools/gen_test_groups.py` rerun; new real-node modules added to `E2E_MODULES`
- [ ] fake CLIs on PATH for the runner `--self-test`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Follow-up installer under the `pnpm dlx` shim | APP-04 | Downloads and runs an npm package (A2) | Approve the follow-up once in a scratch project; on failure the exact argv is printed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
