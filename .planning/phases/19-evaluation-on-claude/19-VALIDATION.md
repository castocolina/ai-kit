---
phase: "19"
slug: "evaluation-on-claude"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-17"
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups `unit`, `e2e` real node, `arch`) |
| **Config file** | `tools/run_unittest_parallel.py` (`E2E_MODULES`), generated listing via `tools/gen_test_groups.py`, `tests/test_gate_scope.py` |
| **Quick run command** | `python3 -m unittest tests.test_gsd_curated_eval tests.test_curated_config_apply tests.test_gate_scope` |
| **Full suite command** | `make test && make validate` (phase gate adds `make e2e-docker`) |
| **Estimated runtime** | quick ~30 s; matrix module ~30 s (420 `resolve-model` calls); full suite ~10 min |

---

## Sampling Rate

- **After every task commit:** quick run command for the touched module plus `tests.test_gate_scope`
- **After every plan wave:** `python3 tools/run_unittest_parallel.py --group unit` and `--group e2e`
- **Before `/gsd-verify-work`:** `make test`, `make validate`, `make e2e-docker`, digest check, pid leak check, protected-set snapshot (repo set plus `~/.claude` config hashes and the worktree `.claude/gsd-core` tree hash) all clean
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-T1 | 01 | 1 | APP-05, EVAL-03 | T-19-01..03 | snapshot prints labels/hashes only; oracle independent of the product | unit + e2e | `python3 -m unittest tests.test_gsd_curated_eval tests.test_curated_config_apply_e2e` | ❌ W0 | ⬜ pending |
| 19-01-T2 | 01 | 1 | APP-05 | T-19-04 | Control 1 non-vacuous; runtime row informational | e2e (real node) | `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix tests.test_gate_scope` | ❌ W0 | ⬜ pending |
| 19-02-T1 | 02 | 2 | EVAL-01 | T-19-05..07, T-19-48..50 | exact `claude -p` argv; scratch home; harness failures exit 1; transcript dir deleted; v1 detect via launcher never runs a PATH binary; ambient review config ignored; ancestor chain spared | unit (injected run_fn) | `python3 -m unittest tests.test_gsd_curated_eval -k TestRun -k TestFixture` | ❌ W0 | ⬜ pending |
| 19-02-T2 | 02 | 2 | EVAL-01 | T-19-08 | fixtures self-check discrimination from real tools | unit + real node | `python3 -m unittest tests.test_gsd_curated_eval` | ❌ W0 | ⬜ pending |
| 19-03-T1 | 03 | 3 | EVAL-01 | T-19-09, T-19-10 | grader fails on wrong inputs; secret-scan canary; effective v1-hook target after flag overrides | unit | `python3 -m unittest tests.test_gsd_curated_eval -k TestGrader -k TestSecretScan` | ❌ W0 | ⬜ pending |
| 19-03-T2 | 03 | 3 | EVAL-01 | T-19-09, T-19-11 | C/D/E wrong-input pairs; eval names and answer counts pinned | unit | `python3 -m unittest tests.test_gsd_curated_eval` | ❌ W0 | ⬜ pending |
| 19-04-T1 | 04 | 4 | EVAL-03 | T-19-12, T-19-13 | repo-root refusal; fault injector on a copy | unit | `python3 -m unittest tests.test_gsd_curated_eval -k TestSmoke` | ❌ W0 | ⬜ pending |
| 19-04-T2 | 04 | 4 | EVAL-03, APP-05 | T-19-14, T-19-15 | placeholder-only evidence; key paths not values | unit + e2e group | `python3 -m unittest tests.test_gsd_curated_eval && python3 tools/run_unittest_parallel.py --group e2e` | ❌ W0 | ⬜ pending |
| 19-05-T1 | 05 | 5 | EVAL-03, APP-05 | T-19-16..18 | scratch-only apply; strict set unchanged; defect fix route | manual (claude host) + script | `smoke --evidence-out` then `snapshot --check` | ❌ W0 | ⬜ pending |
| 19-05-T2 | 05 | 5 | EVAL-03 | T-19-17, T-19-19 | secret scan; leak check | script | `python3 tests/gsd_curated_eval.py secret-scan .planning/phases/19-evaluation-on-claude/pressure .planning/phases/19-evaluation-on-claude/skill-judge .planning/phases/19-evaluation-on-claude/19-SMOKE.md .planning/phases/19-evaluation-on-claude/19-PRESSURE-TESTS.md .planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md` | ❌ W0 | ⬜ pending |
| 19-06-T1 | 06 | 6 | EVAL-01 | T-19-20, T-19-21, T-19-48 | harness-clean run.json; scratch confinement; RED-b only on `v1_listing_isolated: true` fixtures | manual (`claude -p`) + script | run.json assertion (`harness_failures == []`) | ❌ W0 | ⬜ pending |
| 19-06-T2 | 06 | 6 | EVAL-01 | T-19-22, T-19-23, T-19-48 | per-batch snapshot; secret scan; RED-b `fakebin.log` shows the logged `cursor-agent models` call | manual + script | `snapshot --check`; `secret-scan` | ❌ W0 | ⬜ pending |
| 19-07-T1 | 07 | 7 | EVAL-01 | T-19-24..26 | evidence-gated edits committed before GREEN | unit (doc contract) | `python3 -m unittest tests.test_curated_config_apply -k TestSkillDocCommands` | ✅ | ⬜ pending |
| 19-07-T2 | 07 | 7 | EVAL-01 | T-19-26, T-19-28 | one digest across live GREEN rows | script | `digest --check 19-PRESSURE-TESTS.md` | ❌ W0 | ⬜ pending |
| 19-07-T3 | 07 | 7 | EVAL-01 | T-19-26, T-19-27 | REFACTOR cap 3; UNRESOLVED never PASS; commit check from the recorded base exempts `fix(19-07):`; `product_commit` check | script + manual | `digest --check`; `secret-scan`; `snapshot --check` | ❌ W0 | ⬜ pending |
| 19-08-T1 | 08 | 8 | EVAL-02 | T-19-29, T-19-30 | no repo write during a judge run; only `tree=clean` attempts kept or `unavailable` | manual (runner review mode) | closing-lines grep + `git status --porcelain` empty | n/a | ⬜ pending |
| 19-08-T2 | 08 | 8 | EVAL-02 | T-19-30..32 | batch move; pass rule; allowed verdict forms; every attempt under `## Judge attempts` | script + in-session judge | `digest --check`; verdict grep | ❌ W0 | ⬜ pending |
| 19-09-T1 | 09 | 9 | EVAL-02, EVAL-01 | T-19-33, T-19-35 | fix committed before re-runs | unit (doc contract) + script | `TestSkillDocCommands`; `digest --check` | ✅ / ❌ W0 | ⬜ pending |
| 19-09-T2 | 09 | 9 | EVAL-02 | T-19-34, T-19-36 | cap 3; UNRESOLVED never PASS | script | verdict grep; `digest --check` | ❌ W0 | ⬜ pending |
| 19-09-T3 | 09 | 9 | EVAL-01 | T-19-37 | opus confirmation; re-sample rule; commit check from base; `tree=clean` grep | manual (`claude -p`) + script | `secret-scan`; `snapshot --check` | ❌ W0 | ⬜ pending |
| 19-10-T1 | 10 | 10 | EVAL-01/02/03, APP-05 | T-19-38, T-19-39 | gates incl. e2e-docker; JUDGED_COMMIT on clean judged paths | gate | `make test && make validate && make e2e-docker` + `digest --check` | ✅ / ❌ W0 | ⬜ pending |
| 19-10-T2 | 10 | 10 | R7/R8 | T-19-40, T-19-41 | owner-review index; ROADMAP unchanged and no added isolation-claim line; leak check | script | index/backlog greps; `git status --porcelain` empty | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/gsd_curated_eval.py` + `tests/test_gsd_curated_eval.py` — helper (`smoke`, `matrix`, `fixture`, `snapshot`, grader, plan-copy fault injector, ai-kit-root refusal) and its unit tests
- [ ] `tests/test_ai_kit_gsd_curated_config_matrix.py` + `E2E_MODULES` entry + `python3 tools/gen_test_groups.py`
- [ ] `skills/ai-kit-gsd-curated-config/evals/01..04-*.md` (B, C, D, E with scripted answers)
- [ ] digest-check script and pid-snapshot leak check
- [x] Harness spike (orchestrator, 2026-10-17): see `19-RESEARCH.md` "Harness Spike Results"

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RED/GREEN pressure runs B–E | EVAL-01 | needs a real Claude Code login (headless `claude -p`); orchestrator-only, graded by the scripted grader | run per `19-PRESSURE-TESTS.md` header flags; record init-event fields, digest, verdict per expectation |
| Live smoke from the claude host | EVAL-03 | host detection must be a real claude session | `python3 tests/gsd_curated_eval.py smoke`; record in `19-SMOKE.md` |
| In-session `/skill-judge` | EVAL-02 | needs the Skill tool in the host session | judge final digest; pi judges via the runner in review mode |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
