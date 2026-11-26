---
phase: "40"
slug: "resilient-review-sized-by-jev"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-25"
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `unittest` through `tools/run_unittest_parallel.py` (one subprocess per module; groups `unit`, `unit-uv`, `integration`, `e2e`, `arch`) |
| **Config file** | none (groups are sets in `tools/run_unittest_parallel.py`; a new `tests/test_*.py` joins `unit`; `python3 tools/gen_test_groups.py` rewrites the Makefile and pre-commit listings) |
| **Quick run command** | `python3 tools/run_unittest_parallel.py tests.<module> [tests.<module> ...]` |
| **Full suite command** | `make test` (unit, integration, e2e incl. `bash tests/test_install.sh`, arch) |
| **Estimated runtime** | ~10 seconds per slice module set; `make test` several minutes |

---

## Sampling Rate

- **After every task commit:** the slice's modules (the commit-stage `staged-tests` hook runs the covering modules)
- **After every plan wave:** `python3 tools/run_unittest_parallel.py --group unit` and `--group arch`, plus `make check-dogfood`
- **Before `/gsd-verify-work`:** `make test`, `make e2e-docker` and `make check-dogfood` green
- **Max feedback latency:** 60 seconds (commit budget)

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| REV-07 (R3) | `REASONS` lock (13 keys); reason table in `references/lane-failure.md` equals `REASONS`, non-vacuity case | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec tests.test_ai_kit_spec_runtimes_table tests.test_lane_failure_text` | extend `tests/test_ai_kit_spec.py`; ❌ W0 `tests/test_lane_failure_text.py` |
| REV-07 (R4) | partial report, `Judged by:` line in roster order, `not reviewed`, survivors merge, all-clean not partial, any-round rule | unit | `python3 tools/run_unittest_parallel.py tests.test_review_log tests.test_ai_kit_spec` | ❌ W0 `tests/test_review_log.py` |
| REV-07 (R2) | concurrent ping (2 x 2 s fake probe < 3.5 s), replacement by key in owner order, TTL -1 s fresh / +1 s stale, no lane left exit 3, same key pinged once, `ping_timeout`, judge-style lane file pinged and never replaced, round 1 probes despite a fresh cache entry | unit (fake probe, fake clock) | `python3 tools/run_unittest_parallel.py tests.test_lane_ping` | ❌ W0 |
| REV-01 (R1) | flagged + quota switches via `lane_fallback`; unflagged quota / transient / crash never; no eligible fallback stays failed; earlier fallback taken; same-pool skipped; only quota switches | unit | `python3 tools/run_unittest_parallel.py tests.test_lane_switch tests.test_lane_settings tests.test_role_orders` | ❌ W0 `tests/test_lane_switch.py` |
| REV-01 (D-05, PROVISIONAL) | `--blocked-status` wrapper parse, no node, malformed, bad exit, equal time passes, blocked pool skipped at ping and at Step 0.7 probe, tried once after the time; `--pool` argv only for a flagged pooled lane | unit | `python3 tools/run_unittest_parallel.py tests.test_lane_switch tests.test_lane_ping tests.test_role_orders tests.test_runner_flags tests.test_ai_kit_spec_runner_dispatch` | ❌ W0 |
| REV-01 (doc) | narrowed hard rule pinned, old blanket sentence absent, pinned `Never switch harness, provider or model` kept | unit (doc contract) | `python3 tools/run_unittest_parallel.py tests.test_lane_failure_text tests.test_quota_policy_text tests.test_cross_ai_skill_text` | ❌ W0 |
| REV-02 (R5) | classes route as written, low -> owner, CRITICAL/HIGH always owner, no jev -> today's message, no items -> no call, recorded payload holds summaries only | unit (fake `run`) | `python3 tools/run_unittest_parallel.py tests.test_jev_review` | ❌ W0 |
| REV-06 (R6) | each signal trigger and none; signal forces two whatever jev says; jev one -> one lane + logged reason; no jev / low -> unchanged; pick outside roster discarded | unit | `python3 tools/run_unittest_parallel.py tests.test_review_signals tests.test_jev_review` | ❌ W0 `tests/test_review_signals.py` |
| REV-08 (R7) | fixture pair (with / without step), non-superpowers never, empty plan none, case-insensitive heading or checkbox, wording pinned against the adapter SKILL.md, finding parses with `_BULLET_RE` | unit | `python3 tools/run_unittest_parallel.py tests.test_fold_check` | ❌ W0 |
| JDG-04 (R8) | evals shape, text history, frontmatter, dogfood, judge records | unit + dogfood | `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape tests.test_skill_text_history tests.test_skill_frontmatter tests.test_ai_kit_spec_review_fixer tests.test_check_dogfood`; `make check-dogfood` | ✅ |
| Arch | rules 8, 9, 11, cross-skill reach, lookup copies, hardcoded models | arch | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_arch_hardcoded_models` | ✅ |
| E2E | spec-review CLI and runner unchanged | e2e | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_e2e tests.test_cross_ai_runner_e2e` | ✅ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_review_log.py`, `tests/test_lane_ping.py`, `tests/test_lane_switch.py`, `tests/test_jev_review.py`, `tests/test_review_signals.py`, `tests/test_fold_check.py`, `tests/test_lane_failure_text.py` (new, join the `unit` group; each ends with the main guard)
- [ ] Fixtures: fake lane tables with placeholder model names, a superpowers plan pair under `tests/fixtures/fold_step/`, held-out signal fixtures under `tests/fixtures/review_signals/`
- [ ] Update `tests/test_ai_kit_spec.py` (REASONS lock, merge-reports twins) in the same commits as the code

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Judge loop of the changed skills on the three referee lanes | JDG-04 | live model lanes (orchestrator plan, `cross_ai: false`) | the judge plan's steps; `make check-dogfood` validates the records |
| Installed-layout run of the new subcommands from linked skill folders | REV-01, REV-02, REV-06, REV-07, REV-08 | needs a scratch project with a scratch HOME | the closing plan's layout check |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
