---
phase: "24"
slug: "spec-and-discuss-chain-skill"
status: validated
nyquist_compliant: false
wave_0_complete: true
created: "2026-10-24"
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for `ai-kit-gsd-spec-discuss`. Reconstructed (state B) from
> `24-SPEC.md`, `24-01-PLAN.md` and `24-01-SUMMARY.md`; the skill was later extended in Phase
> 21.1, so the tests here cover the current code.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` (stdlib), run through the parallel runner |
| **Config file** | none (runner: `tools/run_unittest_parallel.py`) |
| **Unit module** | `tests/test_ai_kit_gsd_spec_discuss.py` (49 tests) |
| **E2E module** | `tests/test_ai_kit_gsd_spec_discuss_e2e.py` (1 test: real `node` + gsd-core `edge-probe.cjs`) |
| **Quick run command** | `timeout 300 uv run python tools/run_unittest_parallel.py tests.test_ai_kit_gsd_spec_discuss` |
| **E2E run command** | `timeout 120 uv run python -m unittest tests.test_ai_kit_gsd_spec_discuss_e2e` |
| **Full suite command** | `make test` (not run in this audit) |
| **Estimated runtime** | ~3 seconds (unit), ~1 second (e2e) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the quick run command and the e2e command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Requirement Coverage (SPEC R1–R13, SDC-01..SDC-04)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| R1 Skill identity (SDC-04) | COVERED | `TestSkillContract.test_frontmatter_names_the_skill_and_triggers_on_use_when` |
| R2 Range selection (SDC-01) | COVERED | `TestPhaseRange` (explicit range, list, none, decimal order, nothing left, equal timestamps) |
| R3 Spec step: engine floor (SDC-01) | COVERED for the script | `TestEdgeFloor` and `TestRealEdgeFloor` (real engine); the `/gsd-spec-phase --auto` run itself is MANUAL-ONLY |
| R4 Discuss step (SDC-01) | PARTIAL | Route text pinned by `test_discuss_uses_assumptions_workflow_and_records_session`; locked-decision survival, dated amendments and commit ordering are MANUAL-ONLY |
| R5 Ladder script (SDC-02) | COVERED | `TestItemError`, `TestTypedAnswer`, `TestFindClient`, `TestLadderCli` (Laya then remote batch, one Laya call per item, errored Laya to batch, second opinion, invalid item alone, no key in output) |
| R6 Consent and data (SDC-02) | COVERED | `test_ladder_no_consent_zero_remote`, `test_typesafe_consent_does_not_open_opencode` (added), no-backend `own_reasoning` tests |
| R7 Decision logging (SDC-03) | PARTIAL | Backend columns and override/second-opinion evidence are format-only (log-formats.md, worked-examples.md); MANUAL-ONLY |
| R8 Ledger and stop rule (SDC-03) | PARTIAL | Decision table covers blocking × confidence (`test_decision_table_covers_blocking_by_confidence`); ledger printing at run end is MANUAL-ONLY |
| R9 Quality rule (SDC-04) | COVERED | `test_quality_rule_reads_mode_and_states_both_branches` (both branches, `phase.mvp-mode` and config fallback) |
| R10 CodeGraph in every brief (SDC-04) | PARTIAL | Presence gate pinned by `test_codegraph_block_is_gated_on_the_binary_and_an_index`; see open finding O-1 |
| R11 Live facts and amendments | MANUAL-ONLY | Prose step with examples; no executable surface |
| R12 Pacing | MANUAL-ONLY | Prose rule; no executable surface |
| R13 Registration and gates (SDC-04) | PARTIAL | README row pinned by `test_readme_registers_the_skill`; skill-judge evidence in `24-SKILL-JUDGE.md`; gate runs (`make test`, `make validate`) not re-run in this audit |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-T1 | 01 | 1 | SDC-02 (R5, R6, R7) | unit + subprocess (stub HTTP) | `timeout 300 uv run python tools/run_unittest_parallel.py tests.test_ai_kit_gsd_spec_discuss` | ✅ | ✅ green |
| 24-01-T2 | 01 | 1 | SDC-01 (R2, R3) | unit + real engine (e2e) | `timeout 300 uv run python tools/run_unittest_parallel.py tests.test_ai_kit_gsd_spec_discuss` and `uv run python -m unittest tests.test_ai_kit_gsd_spec_discuss_e2e` | ✅ | ✅ green |
| 24-01-T3 | 01 | 1 | SDC-03, SDC-04 (R1, R4, R7–R10) | doc contract (text) | `timeout 300 uv run python tools/run_unittest_parallel.py tests.test_ai_kit_gsd_spec_discuss` | ✅ | ✅ green |
| 24-01-T4 | 01 | 1 | SDC-04 (R13) | doc contract + gates | README test in the unit module; `make test`, `make validate` (not run here) | ✅ | ⚠️ partial |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ partial (gate not re-run in this audit)*

Gaps filled by this audit (all in the existing module, no implementation file changed):
`test_nothing_left_to_discuss_proposes_nothing`, `test_equal_timestamps_count_as_discussed`,
`test_typesafe_consent_does_not_open_opencode`, and the `TestSkillContract` class (six tests).

---

## Wave 0 Requirements

- [x] `tests/test_ai_kit_gsd_spec_discuss.py` — present, fixtures and `JevStub` reused
- [x] `tests/test_ai_kit_gsd_spec_discuss_e2e.py` — present
- [x] Framework — stdlib `unittest`, no install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Range question asked exactly once, carrying the remote consent question | R2, R6 | Prompt-driven host behavior; no script owns the question | Run the skill on a fixture project with no recorded consent; count the questions asked before the first remote call (expect one) |
| `/gsd-spec-phase N --auto` runs, reuses an existing SPEC, and writes Edge Coverage equal to the engine floor plus marked additions | R3 | Drives the gsd-core workflow end to end (an AI run) | Dry run on a fixture project; diff the SPEC's Edge Coverage against `edge_floor.py floor` output |
| Discuss writes `NN-CONTEXT.md` and `NN-DISCUSSION-LOG.md`, keeps locked decisions verbatim, dates amendments, commits before `state.record-session` | R4 | Assumptions-mode analyzer run (an AI run) | Fixture with a prior CONTEXT; confirm locked lines unchanged and amendments dated; check commit order in `git log` |
| Decision rows carry one column per backend and override/second-opinion rows match the log formats | R7 | Written by the model into the log | Compare the rows of a finished run against `references/log-formats.md` |
| Provisional items reach the end-of-run ledger; stop only on blocking unresolvable items | R8 | Run-time behavior of the orchestrator | Fixture with one provisional low-confidence non-blocking item; expect it in the printed ledger and no stop |
| Live-fact amendment step and background-analyzer pacing | R11, R12 | Orchestrator prose; examples only | Read `SKILL.md` sections against the milestone's two examples |

These are not verified by an automated test. Under the adversarial stance they stay unverified
requirements until a live run is recorded.

---

## Open Findings

- **O-1 (WARNING, spec deviation, needs developer decision).** SPEC R10 and CONTEXT D-17 say
  `codegraph init <path>` when `.codegraph/` is missing. `references/analyzer-brief.md` says
  "Never run `codegraph init`" and gates the block on an existing index. The implementation
  follows the brief, not the locked decision. Not fixed here (implementation is read-only for
  this audit). Decide which one wins and amend the other.
- **O-2 (WARNING, environment-specific).** `test_real_engine_floor` skips silently when `node` or
  gsd-core's `edge-probe.cjs` is absent. It ran green here; on a machine without gsd-core the
  real-engine check is not exercised.
- **O-3 (open, manual).** The SPEC-R3/R4/R8 orchestration (see Manual-Only) has no automated
  test. Phase-level compliance is therefore partial.

---

## Validation Sign-Off

- [x] All tasks have an automated verify command (T4's gate run is still manual)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all automatable references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [ ] `nyquist_compliant: true` — NOT set: R3/R4/R7/R8/R11/R12 are manual-only (O-3)

**Verdict:** PARTIAL — automated coverage green (unit 49/49, e2e 1/1); manual-only items open.

**Approval:** pending (partial; developer review of O-1 and the manual-only list required)
