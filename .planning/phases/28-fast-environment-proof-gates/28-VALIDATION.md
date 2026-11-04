---
phase: "28"
slug: "fast-environment-proof-gates"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-03"
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest`, run through `tools/run_unittest_parallel.py` (one subprocess per module, 40 % CPU share); one Node self-test (`cross-ai.mjs --self-test`) |
| **Config file** | none (groups live in the runner; hooks in `.pre-commit-config.yaml`) |
| **Quick run command** | `python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_gate_scope tests.test_arch` |
| **Full suite command** | `make test` (then `make check-dogfood`, `make test-env-matrix`, `python3 tools/time_prepush.py` last) |
| **Estimated runtime** | quick ~20 s; `make test` several minutes; `make test-env-matrix` about six `make test` runs |

---

## Sampling Rate

- **After every task commit:** Run the quick run command plus the task's own `<automated>` command (from plan 28-06 on, the `staged-tests` commit hook also runs the covering modules of every commit)
- **After every plan wave:** Run `make test-unit arch-test` only once the wave's plans have all landed (never while a plan of the same wave is editing); the all-tier convergence run is 28-02 Task 4 (wave 2, alone, after Task 3 commits the runner's deadline code); every wait for a quiet machine is the bounded `python3 tmp/p28/wait_load.py` (600 s at most, 28-01 run rules), the full matrix runs all four tiers in 28-08 (wave 7), and 28-09 (wave 8) re-checks the long-path and custom-tmpdir environments (the full matrix when it changed a tier recipe, the runner or the install scripts)
- **Before `/gsd-verify-work`:** `make test`, `make validate`, `make check-dogfood` and `make test-env-matrix` green; push timing (`python3 tools/time_prepush.py`) measured last
- **Max feedback latency:** ~20 s for the quick command; the e2e, matrix and timing runs are long by nature and run in the background

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | GATE-02 | T-28-01, T-28-02 | a real host CLI call fails its module; callers use fakes | unit | `python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_ai_kit_spec_goal_prompt_evals tests.test_gsd_curated_eval tests.test_arch` | ✅ | ✅ green |
| 28-01-02 | 01 | 1 | GATE-03 | T-28-01, T-28-03 | modules start with no host signals, no git state, no config or status-line overrides, temp HOME | unit | `python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_status_line tests.test_cursor_status_line tests.test_ai_kit_spec_goal_prompt_evals tests.test_gsd_curated_eval` | ✅ | ✅ green |
| 28-01-03 | 01 | 1 | GATE-03 | T-28-01 | the real render skips only when Puppeteer finds no browser | unit + e2e | `python3 tools/run_unittest_parallel.py tests.test_markdown_to_pdf tests.test_gate_scope tests.test_run_unittest_parallel` and `uv run python tmp/p28/mermaid_e2e_check.py <probe-(a) outcome>` | ✅ | ✅ green |
| 28-03-01 | 03 | 1 | GATE-03 | T-28-06, T-28-07 | git never resolves the enclosing repo | e2e + unit | `mkdir -p tmp/p28/wt && TMPDIR="$PWD/tmp/p28/wt" uv run python tools/run_unittest_parallel.py tests.test_worktree_e2e tests.test_tool_substitution_hook` and `bash tmp/p28/longpath.sh` | ✅ | ✅ green |
| 28-03-02 | 03 | 1 | GATE-03 | — | N/A | unit | `python3 tools/run_unittest_parallel.py tests.test_precompact_core` | ✅ | ✅ green |
| 28-02-01 | 02 | 2 | GATE-04 | T-28-04, T-28-05 | injected load read only in the self-test, clamped 1..4 | e2e | `uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e.SelfTestLoadFactorTest` | ✅ (class new) | ✅ green |
| 28-02-02 | 02 | 2 | GATE-04 | T-28-04 | real run limits and floors pinned unchanged; Python guards safe on 3.12 | unit + e2e | `python3 tools/run_unittest_parallel.py tests.test_cross_ai_skill_text tests.test_curated_config_script` and `uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 28-02-03 | 02 | 2 | GATE-04 | T-28-22 | a stopped module gets SIGTERM, then SIGKILL after a grace; an interrupt starts no queued module and leaves no group; the self-test's detached case runners are reaped; committed before any long run | unit + e2e | `python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel` and `uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 28-02-04 | 02 | 2 | GATE-04, GATE-02, GATE-03 | T-28-22, T-28-01 | stress run cleaned up; four tiers green, no tripwire block; bounded waits recorded | stress + all tiers | `python3 tmp/p28/wait_load.py`, `bash tmp/p28/stress_selftest.sh`, `make test-unit arch-test test-integration` then `make e2e-test` | ✅ | ✅ green |
| 28-04-01 | 04 | 3 | GATE-05 | T-28-09 | runner-copy check reads only, prints no content | unit + make | `python3 tools/run_unittest_parallel.py tests.test_check_dogfood tests.test_curated_config_script tests.test_gate_scope` and `make check-dogfood` | ✅ | ✅ green |
| 28-04-02 | 04 | 3 | GATE-05 | T-28-08, T-28-23 | the guard tests touch only scratch projects; a do-nothing run fails; skipped guards are counted apart and the skipped apply is warned about; the matrix hashes the resolved gsd-core folder | unit + e2e + make | `python3 tools/run_unittest_parallel.py tests.test_check_dogfood`, `uv run python tools/run_unittest_parallel.py tests.test_curated_config_e2e tests.test_curated_config_apply_e2e tests.test_ai_kit_gsd_curated_config_matrix` and `make check-dogfood` | ✅ | ✅ green |
| 28-04-03 | 04 | 3 | GATE-05 | — | N/A | unit + make | `python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_ai_kit_project_rules_precommit tests.test_tool_substitution_hook` and `make check-dogfood` | ✅ | ✅ green |
| 28-06-01 | 06 | 4 | GATE-01 | T-28-13 | staged names are data; argv lists only | e2e | `uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e` | ✅ | ✅ green |
| 28-06-02 | 06 | 4 | GATE-01 | T-28-14 | mapper failure runs more tests, never zero; hook runs at commit only | unit + e2e | `python3 tools/run_unittest_parallel.py tests.test_staged_mapper tests.test_run_unittest_parallel tests.test_gate_scope` and `uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e` | ✅ | ✅ green |
| 28-05-01 | 05 | 5 | GATE-05 | T-28-10, T-28-11 | no test path into the repo's `.planning/` | arch + unit | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_phase26_owner_captures tests.test_gate_scope` | ✅ | ✅ green |
| 28-05-02 | 05 | 5 | GATE-05 | T-28-10, T-28-11 | fixtures hold no machine path; tests never rewrite them | arch + unit + e2e | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_pi_live_tools tests.test_tool_advisor_core tests.test_gsd_curated_eval tests.test_gate_scope` and `uv run python tools/run_unittest_parallel.py tests.test_ai_kit_spec_goal_prompt_e2e` | ✅ | ✅ green |
| 28-05-03 | 05 | 5 | GATE-03 | T-28-01 | literal host-CLI commands in tests fail the arch tier | arch | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_phase26_owner_captures tests.test_pi_live_tools tests.test_tool_advisor_core tests.test_gsd_curated_eval` | ✅ | ✅ green |
| 28-07-01 | 07 | 6 | GATE-01 | T-28-27 | an over-budget covering e2e module is deferred with a notice at commit, whatever the decision kind (selective, full run, mapper error) | unit + e2e | `python3 tools/run_unittest_parallel.py tests.test_staged_mapper tests.test_run_unittest_parallel tests.test_gate_scope` and `uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e` | ✅ | ✅ green |
| 28-07-02 | 07 | 6 | GATE-01 | T-28-26, T-28-27 | the pre-push hook runs the deferred modules; it narrows to the range only when the checkout is the pushed commit and no unpushed branch or worktree HEAD lies outside it (local tags left out); a two-ref push, no range or any error runs every over-budget e2e module; the proof counts no tag-only commit on this checkout; durations measured on the frozen tree | unit + e2e + proof | `python3 tools/run_unittest_parallel.py tests.test_staged_mapper tests.test_run_unittest_parallel tests.test_gate_scope`, `uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e` and `python3 tmp/p28/proof_count.py` | ✅ | ✅ green |
| 28-07-03 | 07 | 6 | GATE-01 | — | N/A | unit + CLI | `python3 tools/run_unittest_parallel.py tests.test_staged_mapper`, `python3 tools/staged_mapper.py --stats` and `bash tmp/p28/commit_stage_time.sh` | ✅ | ✅ green |
| 28-07-04 | 07 | 6 | GATE-01 | T-28-16 | both hooks, the shared machinery and the 60 s budget cap cannot drift unnoticed | unit | `python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_run_unittest_parallel` | ✅ | ✅ green |
| 28-08-01 | 08 | 7 | GATE-03 | T-28-17, T-28-24 | scratch HOME per environment; shim log empty; only top-level runners write reports | unit | `python3 tools/run_unittest_parallel.py tests.test_env_matrix tests.test_run_unittest_parallel tests.test_gate_scope` | ✅ | ✅ green |
| 28-08-02 | 08 | 7 | GATE-03, GATE-05 | T-28-18, T-28-25 | the source checkout is only read; the owner's venv is never re-synced; the long-path clone has no `.planning/` and the source's is never removed | unit | `python3 tools/run_unittest_parallel.py tests.test_env_matrix` | ✅ | ✅ green |
| 28-08-03 | 08 | 7 | GATE-02, GATE-03 | T-28-17, T-28-19 | six sequential environments identical, zero host calls | matrix | fix loop `python3 tools/env_matrix.py --only <differing env>`; final proof `make test-env-matrix` | ✅ | ✅ green |
| 28-09-01 | 09 | 8 | GATE-02 | T-28-21 | an invalid run (failed, missing, unexpected, duplicated or all-skipped module, a total off the inventory) cannot be recorded as a pass; the unrounded total is compared; a failed auxiliary hook fails the tool | unit | `python3 tools/run_unittest_parallel.py tests.test_time_prepush tests.test_gate_scope` | ✅ | ✅ green |
| 28-09-02 | 09 | 8 | GATE-05 | — | N/A | unit | `python3 tools/run_unittest_parallel.py --staged AGENTS.md README.md` and `python3 tools/run_unittest_parallel.py tests.test_gate_scope` | ✅ | ✅ green |
| 28-09-03 | 09 | 8 | GATE-02 | T-28-20 | matrix re-check (long-path, custom-tmpdir), then timing under a temp HOME with the runner's toolchain forwards at the 40 % share, then figures only | matrix + timing | `python3 tools/env_matrix.py --only long-path --only custom-tmpdir` (or `make test-env-matrix` per 28-09 Task 3 step 1), `python3 tools/time_prepush.py` and `python3 tools/run_unittest_parallel.py --staged AGENTS.md README.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

No separate Wave 0 plan: each new test file is created by the task that needs it, test first where the task is `tdd="true"`.

- [x] `tests/host_fakes.py` — shared host fake helper (28-01-01)
- [x] `tests/test_markdown_to_pdf_e2e.py` — real Mermaid render, e2e, named skips decided by a probe render (28-01-03)
- [x] `tests/test_check_dogfood.py` — runner-copy and no-write checks on temp roots (28-04-01, 28-04-02)
- [x] `tests/fixtures/archived/{26,22,21.3}/` — frozen copies with headers (28-05-01, 28-05-02)
- [x] `tests/test_staged_commit_e2e.py`, `tests/test_staged_mapper.py` — commit stage (28-06-01, 28-06-02; commit budget cases 28-07-01, pre-push deferral and local-tag cases 28-07-02)
- [x] `tests/test_env_matrix.py` — matrix logic (28-08-01, 28-08-02)
- [x] `tests/test_time_prepush.py` — timing verdict (28-09-01)

No framework install: stdlib `unittest` and the existing runner cover everything.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| One self-test run under real CPU stress passes | GATE-04 | needs a machine under real load (stress-ng), not a unit fixture | the executor runs `./tmp/p28/stress_selftest.sh` (28-02-04 step 2, alone in wave 2) and records factor, load and exit code |
| Push test hooks 60 s or less on the owner's machine | GATE-02 | wall time depends on this machine; recorded, not asserted by a unit test | `python3 tools/time_prepush.py` as the last measurement of the phase (28-09-03); the record line carries cpus, share, workers and load, and check-dogfood's time beside the test-hook subtotal |
| All four tiers identical in six environments (plain, host-session, no-host-cli, long-path, custom-tmpdir, outside-git) | GATE-02, GATE-03 | one run is six full `make test` runs (about 45 min); the matrix logic is pinned by `tests.test_env_matrix` (38 tests, 0.4 s) | `make test-env-matrix`; recorded `identical in 6 environments` in 28-08-SUMMARY, subset re-check `identical in 3` in 28-09-SUMMARY |
| One-off proof scripts under the gitignored `tmp/p28/` (long-path clone, Mermaid probe, proof count, commit-stage times, stress run) | GATE-01, GATE-03, GATE-04 | throwaway evidence runs, not committed tests; each task's committed module covers the same behavior and is green | results recorded in the 28-01, 28-02, 28-03 and 28-07 summaries |

The first two are run by the executor on the owner's machine (no owner action needed); the last two are recorded proofs; everything else is automated.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (no MISSING sentinel is used; new test files are created by their tasks)
- [x] No watch-mode flags
- [x] Feedback latency < 28s (the quick command measured 27 s on 2026-11-04, set by `tests.test_run_unittest_parallel` at 26 s; e2e, matrix and timing runs are long by nature)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-04

## Validation Audit 2026-11-04

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
