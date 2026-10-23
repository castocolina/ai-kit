---
phase: "18"
slug: "cross-ai-skills-apply-pipeline"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
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

Task ids bound by the planner (2026-10-15, revision 1: 22 strictly serial plans); one row per plan or task group.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 18-01-T1/T2 | 01 | 1 | XAI-02, SPEC-05 | T-18-01 | pi RPC parser never raises; no `baseUrl` in fixture; D-45 router merge | unit | `python3 -m unittest tests.test_ai_kit_spec tests.test_curated_config_inventory` | ✅ | ✅ green |
| 18-01-T3 | 01 | 1 | APP-03, SKL-04 | T-18-02, T-18-03 | strict encoder refuses re-typable strings; secret presence is `bool(load_secret(...))` only | unit | `python3 -m unittest tests.test_ai_kit_spec_gsd_tools tests.test_ai_kit_spec` | ✅ | ✅ green |
| 18-02-T1..T3 | 02 | 2 | XAI-01, SKL-01, APP-04 | T-18-04, T-18-05, T-18-47, T-18-48 | lanes are data only; registry failure degrades with a warning | e2e + unit | `python3 -m unittest tests.test_curated_config_e2e -k TestRealGsdLanes`; `tests.test_curated_config_inventory` | ✅ | ✅ green |
| 18-03-T1/T2 | 03 | 3 | SKL-01, SKL-03 | T-18-06, T-18-49 | plain, symlink escape, project, plugin `<installPath>/skills/*/SKILL.md` (claude vs other host); `enabledPlugins` layering labelled unverified | unit | `python3 -m unittest tests.test_curated_config_skills` | ✅ | ✅ green |
| 18-03-T3 | 03 | 3 | SKL-04 | T-18-07..T-18-09 | key value and URL never in output (sentinel); bounded connect | unit | `python3 -m unittest tests.test_curated_config_skills tests.test_curated_config_inventory` | ✅ | ✅ green |
| 18-04-T1/T2 | 04 | 4 | XAI-02 | T-18-10, T-18-12 | script artifact `config{prefer, models, outer_timeout_s, router_backed}`; constant command; timeout >= 1800; purity guard | unit + goldens | `python3 -m unittest tests.test_curated_config_golden tests.test_curated_config_recommend` | ✅ | ✅ green |
| 18-05-T1/T2 | 05 | 5 | XAI-02 | T-18-11 | host/claude/retired CLI never targets; D-39 default matrix | unit | `python3 -m unittest tests.test_curated_config_cross_ai tests.test_curated_config_recommend` | ✅ | ✅ green |
| 18-06-T1/T2 | 06 | 6 | XAI-01 | T-18-13 | lane != host/pi, vendor rule, ranking, O7 claude alias, effort xhigh only under Rigorous | unit + goldens | `python3 -m unittest tests.test_curated_config_cross_ai tests.test_curated_config_golden` | ✅ | ✅ green |
| 18-07-T1/T2 | 07 | 7 | SKL-02, SKL-03 | T-18-15 | caps 2/3/5; missing skill never named; reference forms | unit + goldens | `python3 -m unittest tests.test_curated_config_skills tests.test_curated_config_golden` | ✅ | ✅ green |
| 18-08-T1/T2 | 08 | 8 | SKL-02, SKL-03, SKL-04 | T-18-14, T-18-46, T-18-50, T-18-51 | trusted root `needs_choice`, `~/`-relative; proposals capped at 10; jev note | unit + goldens | `python3 -m unittest tests.test_curated_config_skills tests.test_curated_config_golden tests.test_curated_config_recommend` | ✅ | ✅ green |
| 18-09-T1..T3 | 09 | 9 | XAI-02 | T-18-19, T-18-41 | hermetic self-test env; retired CLI absent outside the scrub list; one AIKIT-XAI line | e2e (node) + unit | `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test`; `python3 -m unittest tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 18-10-T1/T2 | 10 | 10 | XAI-02 | T-18-16..T-18-18, T-18-52, T-18-53, T-18-68 | stderr-only classification; tree id; fallback only on a clean tree; group kill | e2e (node) | `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test`; `python3 -m unittest tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 18-11-T1/T2 | 11 | 11 | XAI-02 | T-18-42, T-18-54 | preflight `bad_model`; zero ids = listing unavailable; retries end in capacity | e2e (node) | `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` | ✅ | ✅ green |
| 18-12-T1/T2 | 12 | 12 | XAI-02 | T-18-20, T-18-21, T-18-55, T-18-56, T-18-69 | review contract; claude block read-only; deadline < outer; knob values enumerated | e2e (node) | `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test`; `python3 -m unittest tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 18-13-T1..T3 | 13 | 13 | XAI-02 | T-18-22, T-18-23, T-18-57 | edited/unstamped/foreign -> `.new`; byte-stable render; shared bytes writer | unit + e2e | `python3 -m unittest tests.test_curated_config_script tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 18-14-T1/T2 | 14 | 14 | APP-01, SKL-03 | T-18-24..T-18-26, T-18-58 | refusals, `--force`, D-44 command guard, trusted-root approval | unit | `python3 -m unittest tests.test_curated_config_plan_edit` | ✅ | ✅ green |
| 18-15-T1/T2 | 15 | 15 | APP-01, XAI-02 | T-18-43, T-18-59 | script pseudo-keys; `prefer` ids only installed runner CLIs; plan-unset; v1 untouched | unit | `python3 -m unittest tests.test_curated_config_plan_edit tests.test_ai_kit_gsd_curated_config` | ✅ | ✅ green |
| 18-16-T1..T3 | 16 | 16 | APP-03 | T-18-27..T-18-30, T-18-60, T-18-61, T-18-70, T-18-71 | backup claim, keep 3, verbatim restore, apply marker | unit | `python3 -m unittest tests.test_curated_config_apply` | ✅ | ✅ green |
| 18-17-T1..T3 | 17 | 17 | APP-02 | T-18-31..T-18-33, T-18-62 | dry run writes nothing; needs_choice -> exit 2; `--inventory` digest | unit | `python3 -m unittest tests.test_curated_config_apply` | ✅ | ✅ green |
| 18-18-T1/T2 | 18 | 18 | APP-03, SKL-02 | T-18-34, T-18-35, T-18-63, T-18-64, T-18-72 | writes only via gsd-tools; marker refusal; render failure before writes; `warnings == []` (skipped on pi) | e2e (real gsd-tools) + unit | `python3 -m unittest tests.test_curated_config_apply_e2e tests.test_curated_config_apply` | ✅ | ✅ green |
| 18-19-T1..T3 | 19 | 19 | APP-03 | T-18-36, T-18-63, T-18-72 | Nth-key restore bytes; keep 3; re-apply per D-20; reconcile; AST write discipline | e2e (real gsd-tools) + unit | `python3 -m unittest tests.test_curated_config_apply_e2e tests.test_curated_config_apply` | ✅ | ✅ green |
| 18-20-T1..T3 | 20 | 20 | APP-04 | T-18-37..T-18-39, T-18-44, T-18-65, T-18-66, T-18-73 | nothing runs without `--approve`; pinned version + `--local`; one resolver; unverified notes | unit | `python3 -m unittest tests.test_curated_config_followups tests.test_curated_config_inventory` | ✅ | ✅ green |
| 18-21-T1/T2 | 21 | 21 | EVAL-06 | T-18-40, T-18-67 | docs-command drift; skill-judge self-check PASS (independent review authoritative) | unit + doc | `python3 -m unittest tests.test_curated_config_apply -k TestSkillDocCommands` | ✅ | ✅ green |
| 18-22-T1/T2 | 22 | 22 | EVAL-06 | T-18-45 | v1 suite and dogfood runner unmodified; amendments tagged | gate | `make test`; `make validate`; `make e2e-test`; `make e2e-docker` | ✅ | ✅ green |

Threat refs refreshed 2026-10-15 from the PLAN files after the cycle-1..3 replans (T-18-46..T-18-73).

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] pi RPC fixture (trimmed, `baseUrl` stripped, provenance in a docstring) and the D-45 router-merge fixture test
- [x] skills/plugin fixtures: plain, symlink escape, project, plugin, claude vs other host
- [x] jev fixtures plus a sentinel test that the key value never appears in output
- [x] regenerated goldens; purity-guard allowlist update with its non-vacuity counterpart
- [x] `python3 tools/gen_test_groups.py` rerun; new real-node modules added to `E2E_MODULES`
- [x] fake CLIs on PATH for the runner `--self-test`
- [x] hermetic env builders: `hermeticEnv(tmp, extra)` in the template self-test and `runner_env(tmp)` in the Python E2E helpers (only fakes plus `node`/`git` on PATH, scratch HOME/XDG, no inherited variables)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Follow-up installer under the `pnpm dlx` shim | APP-04 | Downloads and runs an npm package (A2) | Approve the follow-up once in a scratch project; on failure the exact argv is printed |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-15

---

## Validation Audit 2026-10-15

| Metric | Count |
|--------|-------|
| Requirements mapped (XAI-01, XAI-02, SKL-01..04, APP-01..04, EVAL-06, SPEC-05) | 12/12 |
| SPEC edges with an automated test | 77/77 |
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

Gap: `TestPlanUnset.test_set_same_as_existing_is_keep` (R1 adjacency edge) skipped on every run because the golden inventory has no existing config. It now seeds `workflow.plan_review_convergence` and asserts `op: keep`, `source: user`.

All map commands run green (`make test` rc=0; `make e2e-docker` not rerun in this audit), including `cross-ai.mjs --self-test` and the real-gsd-tools e2e modules.
