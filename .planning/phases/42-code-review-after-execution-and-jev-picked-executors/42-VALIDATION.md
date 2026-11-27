---
phase: "42"
slug: "code-review-after-execution-and-jev-picked-executors"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-26"
---

# Phase 42 — Validation Strategy

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
| EXE-02 (R1) | HIGH fixed in round 1 passes in round 2; never clears -> `cap_stop` at round 3 with the last report; MEDIUM/LOW never block; empty report passes in round 1 with no jev call; superpowers Critical/Important/Minor read as CRITICAL/HIGH/LOW; gray areas through `classify-disagreements --kind code` (owner for owner_decision, low, no jev, CRITICAL/HIGH); doc contract pins cap and pass rule | unit (fake lanes, fake jev) | `python3 tools/run_unittest_parallel.py tests.test_code_review tests.test_jev_review tests.test_ai_kit_spec_superpowers tests.test_adapter_single_definitions` | ❌ W0 `tests/test_code_review.py` |
| LENS-02 (R2) | `.tsx` path -> both lenses; `.py` -> `ponytail-review` only; upper-case `.TSX` -> both; lens row absent -> lane runs with the `not_present` note; no UI path never loads `impeccable`; deleted path dropped before `--files` | unit (fixture path lists) | `python3 tools/run_unittest_parallel.py tests.test_lens_delivery tests.test_code_review` | extend existing |
| EXE-03 (R3) | confident pick moves the candidate first and logs it; low/missing/needs_fallback keeps today's order and logs `default`; outside-roster token discarded; filtered candidate never offered; one candidate -> no jev call; asked once per resolve-injection on the plain first resolution only; `ladder_keys` unchanged; payload holds tokens and labels only | unit (fake jev `run`) | `python3 tools/run_unittest_parallel.py tests.test_executor_pick tests.test_ai_kit_spec_superpowers` | ❌ W0 `tests/test_executor_pick.py` |
| EXE-03 (R4) | lite pick writes `.aikit/brief/lite-executor.md` with the fixed text; strong/absent/unknown/router class writes nothing and removes a stale file; brief bytes unchanged; no file under `skills/ai-kit-commit-fold/` changed; doc contract pins the text and its `unverified` label | unit (scratch cwd, catalog fixture) | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_superpowers tests.test_adapter_single_definitions` | extend |
| EXE-06 (R5) | skipped by the owner on 2026-11-27 (SPEC amendment 13): no spike record, no host probe, no label flip; the skip is recorded in the SPEC, REQUIREMENTS and ROADMAP and the spike is backlog Phase 999.36 | recorded decision (plan 42-01) | `python3 skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py check <42-SPEC.md>` | ⬜ plan 42-01 |
| EXE-06 (R6) | unverified transport never chosen; verified resume reused in round 2 and renewed at `TRANSPORT_RENEW_ROUNDS`; different host version reads unverified; herdr absent -> subprocess; interactive + verified pane -> pane; two lanes same runtime/model keep separate sessions; pane closes at plan close, a dead leftover is closed by `--sweep`; verdict from `rc`/result file only; protocol constants equal the fixture; no `--transport-record` -> today's dispatch | unit (fake herdr, fake clock, fake runner) | `python3 tools/run_unittest_parallel.py tests.test_lane_transport tests.test_herdr_pane tests.test_lane_settings tests.test_spec_config_flow_text tests.test_ai_kit_spec_superpowers` | ❌ W0 `tests/test_lane_transport.py`, `tests/test_herdr_pane.py` |
| EXE-07 (R7) | each execute class and each review fit routes as written; no jev -> `default` logged; needs_fallback is low; CRITICAL/HIGH never lowered; no lane result -> no jev call; payload-recording seam proves summaries only | unit (fake jev) | `python3 tools/run_unittest_parallel.py tests.test_jev_review tests.test_code_review` | extend |
| JDG-04 (R8) | 22 evals, shape, text history, judge records | unit + dogfood | `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape tests.test_skill_text_history`; `make check-dogfood` | ✅ |
| Arch | frozen cross-skill allowlist, lane-setting guard, lookup copies, hardcoded models, gate scope | arch | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_arch_hardcoded_models tests.test_lane_settings tests.test_gate_scope` | ✅ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_executor_pick.py` (42-02), `tests/test_code_review.py` (42-04), `tests/test_lane_transport.py` (42-07), `tests/test_herdr_pane.py` (42-08), each listed by `python3 tools/gen_test_groups.py`
- [ ] `READERS` / `ALLOWED_READERS` rows for `lane_interactive` and its caller (42-07)
- [ ] A catalog fixture with `facts.class` values on placeholder models (42-03) and fake-herdr answer tables (42-08)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live session-id and headless-resume spike | EXE-06 | skipped by the owner on 2026-11-27; costs model quota and needs the owner's chosen authentication | backlog Phase 999.36 (plan 42-01 records the skip) |
| Installed-layout run of the new subcommands from linked skill folders | EXE-02, EXE-03, EXE-06, EXE-07 | needs a scratch project with linked skills, not a module | closing plan 42-12 layout check |
| Skill-judge loop of the changed skill | JDG-04 | judge lanes are external models | judge plan 42-11 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
