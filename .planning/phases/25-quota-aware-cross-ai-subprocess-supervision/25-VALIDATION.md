---
phase: "25"
slug: "quota-aware-cross-ai-subprocess-supervision"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-24"
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Re-scoped by the owner
> decision of 2026-10-24 (External Agent Runs ladder, Placement, Rule adjustment): the ladder lives
> in the runner template and is pinned by its own `--self-test`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Runner `--self-test` (hermetic fake CLIs, named cases, pure in-process cases); stdlib `unittest` via `tools/run_unittest_parallel.py` (groups unit, unit-uv, integration, e2e, arch) |
| **Config file** | `Makefile`, `.pre-commit-config.yaml` (generated groups, pinned by `tests/test_gate_scope.py`), `tools/run_unittest_parallel.py` (`E2E_MODULES` lists `tests.test_cross_ai_runner_e2e`) |
| **Quick run command** | `AIKIT_XAI_SELFTEST_CASES=<cases> node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test`; `python3 tools/run_unittest_parallel.py <module>` (an e2e module takes `uv run python3 tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e`, as the Makefile runs it) |
| **Full suite command** | `make test && make validate` (plus `make e2e-docker` at the phase tip) |
| **Estimated runtime** | runner self-test 47 s standalone at the phase base, budget 120 s; full suite ~600 s |

---

## Sampling Rate

- **After every task commit:** the task's targeted self-test cases or touched module (its `<verify>`)
- **After every plan:** the full runner `--self-test` (runner plans) and the orchestrator barrier `make test && make validate`
- **Before `/gsd-verify-work`:** 25-11 Task 3: ruff, pyright, vulture, `make test`, `make validate`, `make e2e-docker`
- **Max feedback latency:** about 60 s for a targeted self-test subset

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | QTA-03 | T-25-01 | only the first CLI spawns | self-test | `node <template> --self-test` + removed-literal gate | ✅ | ✅ green |
| 25-01-02 | 01 | 1 | QTA-03 | T-25-01 / T-25-02 | no second CLI after any class; missing first choice reported | self-test | `AIKIT_XAI_SELFTEST_CASES=no-second-cli-*,config-prefer-first-only,not-installed-first,no-model-first,review-only-*` (plus `review-only-later-menu-ok`) | ✅ | ✅ green |
| 25-02-01 | 02 | 2 | QTA-01 | T-25-03 / T-25-05 | answer text never matched; no provider text in composed lines | self-test + JSON parse | full `--self-test` + patterns-block parse | ✅ | ✅ green |
| 25-02-02 | 02 | 2 | QTA-01 | T-25-04 | table order pinned (mutation) | pure self-test | `pure-classify-*` cases | ✅ | ✅ green |
| 25-03-01 | 03 | 3 | QTA-01 | T-25-06 / T-25-07 | classify-only spawns nothing; route flag is an enum | self-test | `classify-only-*`, `route-*` cases | ✅ | ✅ green |
| 25-03-02 | 03 | 3 | QTA-01 | T-25-06 | Python reads the shipped classifier | e2e + unit | `tests.test_cross_ai_runner_e2e` (uv), `tests.test_ai_kit_spec_runtimes_table` | ✅ extend | ✅ green |
| 25-04-01 | 04 | 4 | QTA-02 | T-25-08 | live kill only on terminal signals | self-test | `live-limit-kill`, `live-partial-kill`, `post-hoc-timeout-429`, `post-hoc-timeout-codex-error`, `hang` | ✅ | ✅ green |
| 25-04-02 | 04 | 4 | QTA-02 | T-25-08 / T-25-09 | answers, notices, bare codex errors never kill; capped buffers | self-test | `answer-only-ok`, `retry-notice-no-kill`, `live-limit-flood`, `live-codex-*` | ✅ | ✅ green |
| 25-05-01 | 05 | 5 | QTA-03 | T-25-11 | 3 + 3 rungs, same CLI and model | self-test + unit + e2e | `ladder-transient-exhausted`, `ladder-timeout-then-ok`, `ladder-timeout-no-budget` et al.; `tests.test_ai_kit_spec_runner_dispatch`, `tests.test_ai_kit_spec_runtimes_table`, `tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 25-05-02 | 05 | 5 | QTA-03 | T-25-10 | new session only over the plan's own changed files | self-test | `ladder-dirty-*`, `ladder-non-git`, `pure-prompt-files` | ✅ | ✅ green |
| 25-05-03 | 05 | 5 | QTA-03 | T-25-12 | codex review never resumes; pure ladder sequence | pure + self-test | `pure-ladder-*`, `ladder-*-cursor/codex/review` | ✅ | ✅ green |
| 25-06-01 | 06 | 6 | QTA-03 | T-25-13 | cooldown cycles, 4-hour cap clamp | pure + self-test | `pure-ladder-cap-*`, `router-quota-*`, `stale-state-fresh-start`, `expired-state-cap-stop`, `quota-deadline-cycle`, `plain-quota-no-retry` | ✅ | ✅ green |
| 25-06-02 | 06 | 6 | QTA-03, QTA-01 | T-25-14 / T-25-15 | evidence lines carry no key | self-test | `sentinel-evidence`, `sentinel-failed-line` | ✅ | ✅ green |
| 25-06-03 | 06 | 6 | QTA-03 | — | template 7 pinned without literals | self-test + unit + e2e | full `--self-test`; `tests.test_curated_config_script`, `tests.test_ai_kit_gsd_curated_config`, `tests.test_cross_ai_runner_e2e` | ✅ | ✅ green |
| 25-07-01 | 07 | 7 | QTA-03 | T-25-16 / T-25-17 | dogfood re-rendered pristine, CONFIG kept | rendered self-test | `node .planning/scripts/cross-ai.mjs --self-test` + state check | ✅ | ✅ green |
| 25-07-02 | 07 | 7 | QTA-03 | — | gates green on the new runner | full suite | ruff, pyright, vulture, `make test`, `make validate` | ✅ | ✅ green |
| 25-08-01 | 08 | 8 | QTA-01, QTA-03 | T-25-18 | only a confirmed boolean becomes a flag | unit | `tests.test_ai_kit_spec_runner_dispatch` | ✅ extend | ✅ green |
| 25-08-02 | 08 | 8 | QTA-01, QTA-03 | T-25-19 | route through the real runner; no real cache read | e2e + unit | `tests.test_cross_ai_runner_e2e` (uv), `tests.test_ai_kit_spec_env_scrub`, `tests.test_ai_kit_spec` | ✅ extend | ✅ green |
| 25-09-01 | 09 | 8 | QTA-03 | T-25-21 | no wake in the GSD skill; pointer 3-4 lines | text | `tests.test_quota_policy_text`, `tests.test_gate_scope` | ✅ | ✅ green |
| 25-09-02 | 09 | 8 | QTA-03 | T-25-20 | superpowers stops, never re-dispatches | text | literal gates in the task | ✅ | ✅ green |
| 25-09-03 | 09 | 8 | QTA-03 | T-25-20 / T-25-21 | Python messages match | unit + text | `tests.test_quota_policy_text`, `tests.test_ai_kit_spec_superpowers`, `tests.test_ai_kit_spec_runtimes_table` | ✅ | ✅ green |
| 25-10-01 | 10 | 9 | QTA-03 | T-25-22 | review skill relays evidence | text | `tests.test_quota_policy_text` | ✅ extend | ✅ green |
| 25-10-02 | 10 | 9 | QTA-03 | T-25-22 | no prefer-order fallback text anywhere | text | `tests.test_quota_policy_text` + stale-text gate | ✅ extend | ✅ green |
| 25-10-03 | 10 | 9 | QTA-01 | T-25-23 | owner kit redacts; results pending | doc check | results-section parse in the task | ✅ | ✅ green |
| 25-11-01 | 11 | 10 | QTA-03 | T-25-24 | judge lanes read-only; verdicts cited | judge evidence | report files + `tests.test_quota_policy_text` | ✅ | ✅ green |
| 25-11-02 | 11 | 10 | all | — | amendments recorded | doc check | grep gates in the task | ✅ | ✅ green |
| 25-11-03 | 11 | 10 | all | T-25-25 | gates logged, clean room green | full suite | ruff, pyright, vulture, `make test`, `make validate`, `make e2e-docker` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement and Edge Map

- QTA-01 (pattern table, labels, route only for router lanes and evidence): 25-02, 25-03, 25-08; edges SPEC R1 (all), R2 adjacency, boundary, empty, precision and the backstops.
- QTA-02 (live and after-the-fact detection feeding the typed reason and the status line): 25-04; edges SPEC R4 (all).
- QTA-03 (the owner ladder, no automatic fallback, same policy in the skills, documented in skill, README and runner tests): 25-01, 25-05, 25-06, 25-07, 25-09, 25-10, 25-11; edges SPEC R3 adjacency and empty (adapted to the cooldown cap), R5 boundary, precision, concurrency and idempotency (adapted to 25-06's cross-call state file: atomic 0600 write, quota budget keyed by lane and model, resumed session id stored per task key, early re-entry refused, a stale episode replaced and noted), R6 boundary and empty (adapted), R6 precision, R7 empty and idempotency, R8 adjacency, empty and ordering.
- Superseded by the owner decision (listed in the 25-SPEC acceptance mapping by 25-11): R3 encoding, R6 adjacency and ordering, R7 adjacency, encoding (adapted backstop) and ordering, R8 concurrency.
- Prohibitions: 4-hour cap (25-06), no wait or retry off a router lane (25-06), no answer-text classification (25-02, 25-04), no key in any composed line (25-02, 25-06); owner additions: no second CLI (25-01), no harness/provider/model switch (25-05), no repeated or fixed-interval skill wake and no re-dispatch (25-09; the ruled exception is one one-shot re-invoke at `retry_after_s` for a confirmed-router exit 75).

---

## Wave 0 Requirements

- [x] Pure-case support in the runner self-test harness (`spec.pure`) and `CLASSIFY_CASES` (25-02)
- [x] `tests/test_quota_policy_text.py`, followed by `python3 tools/gen_test_groups.py` (25-09)
- No framework install: Node built-ins and the Python stdlib only

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cursor limit channel, exit code and `session_id` | QTA-01, QTA-02 | needs the owner's live Cursor account at its limit | `25-OWNER-CAPTURES.md` C1 |
| pi weekly-limit wording (`zai-coding-cn`) | QTA-01 | live provider text | C2 |
| Router bodies, including a combo member | QTA-01, QTA-03 evidence | live router errors | C3 |
| claude overloaded and reset wording | QTA-01 | live review lane | C4 |
| codex reconnect `error` then a good turn | QTA-02 | live stream retry | C5 |
| Router quota recovery time (cooldown sizing) | QTA-03 | live lane | C6 |
| Owner confirmation of A1, A2, A4 and the auth interpretation | QTA-03 | owner decision | C7 |
| Skill-judge verdicts (real model calls) | QTA-03 | orchestrator-only judge lanes; recorded BLOCKED on 2026-10-25 (both referee lanes stopped; base-score bar is an owner decision) | `25-SKILL-JUDGE.md`; re-run when the lanes recover |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [ ] Feedback latency < 30s (the targeted self-test subsets take up to about 60 s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-25 (automated map green; the skill-judge gate and C1-C7 stay manual-only)

## Validation Audit 2026-10-25

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Every cited self-test case and test module exists. All gates, `make e2e-docker` included, passed at the 25-11 phase tip. After the code-review fixes (8c3dbfa, 5b28f21), the runner self-test (template and dogfood copy), `make test` and `make validate` passed again; `make e2e-docker` was not re-run.
