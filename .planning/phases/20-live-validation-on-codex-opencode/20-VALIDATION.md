---
phase: "20"
slug: "live-validation-on-codex-opencode"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
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
| 20-01-T1 | 01 | 1 | EVAL-05 (R8) | T-20-07, T-20-17 | opencode executes on a private server (template 4 renders `--standalone`; the `opencode models` preflight stays read-only); this repo's runner re-rendered through `ensure-runner` only via `.new`; one bootstrap dispatch recorded | self-test + argv + e2e | `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test && echo x \| node skills/ai-kit-spec-review/references/cross-ai.mjs --print-argv --mode exec --prefer opencode --model-opencode fake/ok \| grep '^opencode' \| grep -q -- '--standalone' && node .planning/scripts/cross-ai.mjs --self-test && python3 -m unittest tests.test_cross_ai_runner_e2e tests.test_curated_config_script tests.test_ai_kit_gsd_curated_config` | exists (pins to 4) | ✅ |
| 20-01-T2 | 01 | 1 | EVAL-05 (R6) | T-20-08 | host slug never a lane (codex, opencode parametrized) | unit | `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_plan_edit -k never_a_review_lane` | exists (extend) | ✅ |
| 20-02-T1 | 02 | 2 | EVAL-04 (R4) | T-20-01 | matrix applies only to scratch projects; four-case tier rule keeps the claude matrix green; non-claude refuses a missing `runtime_profiles`; a non-zero resolve-model exit never passes; the empty promise needs the omit gate | unit + real node | `python3 -m unittest tests.test_gsd_curated_eval -k TestOracle -k TestMatrixEnv && python3 tests/gsd_curated_eval.py matrix --host codex && python3 tests/gsd_curated_eval.py matrix --host claude` | exists (extend) | ✅ |
| 20-02-T2 | 02 | 2 | EVAL-05 (R7) | T-20-02 | labels-only matrix output; informational row claude-only | unit + e2e | `python3 -m unittest tests.test_gsd_curated_eval && python3 tests/gsd_curated_eval.py matrix --host opencode && python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix && python3 tools/run_unittest_parallel.py --group unit` | exists (extend) | ✅ |
| 20-03-T1 | 03 | 3 | EVAL-04 (R1, R2, R5) | T-20-03, T-20-05, T-20-18 | throwaway HOME plus XDG_* install (the installer's `opencode debug paths` / `opencode.db` probes stay inside it); `_project_env` drops `RUNTIME_DIR` so inventory resolves the scratch root, asserted exactly | unit + real node | `python3 -m unittest tests.test_gsd_curated_eval -k TestSmoke && python3 tests/gsd_curated_eval.py smoke --host codex --evidence-out tmp/p20/local-codex.md && grep -q '^- root: <scratch-a>/.codex/gsd-core' tmp/p20/local-codex.md` | exists (extend) | ✅ |
| 20-03-T2 | 03 | 3 | EVAL-04/05 (D-10) | T-20-04, T-20-06 | allowlist guard never names credential files; TOML `projects` exemption limited to this run's scratch roots (an emptied table normalized away; `snapshot --check --scratch-root` is the one outer exemption); agents/commands hashed as trees | unit | `python3 -m unittest tests.test_gsd_curated_eval -k TestSnapshot -k TestSmoke && python3 tests/gsd_curated_eval.py snapshot --out tmp/p20/snap.json && python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/snap.json` | exists (extend) | ✅ |
| 20-03-T3 | 03 | 3 | EVAL-05 (R1, R5; D-01) | T-20-04, T-20-19 | no managed-service call; `--keep-scratch` leaves only a system-temp dir; `--artifacts-out` writes plan/config/resolve-model/baked through the placeholders | unit + real node | `python3 -m unittest tests.test_gsd_curated_eval && python3 tests/gsd_curated_eval.py smoke --host opencode --evidence-out tmp/p20/local-opencode.md --artifacts-out tmp/p20/local-opencode-artifacts && python3 tools/run_unittest_parallel.py --group unit && python3 tools/run_unittest_parallel.py --group e2e` | exists (extend) | ✅ |
| 20-04-T1 | 04 | 4 | EVAL-04 (R2, R3, R4, R8) | T-20-09, T-20-10, T-20-12 | names-only env (pattern covers every HOST_SIGNAL_ENV_VARS name; four-set check, generic markers owned); snapshot before/after with `--scratch-root` from the smoke's `scratch work dir:` line; smoke 900/930 s and every child bounded inside the 1800 s dispatch (sum 1690 s, remaining-time check); `ok` or `no_change` accepted | live headless | `grep -Eq 'AIKIT-XAI status=(ok\|no_change) cli=codex .* cli_rc=0 ' 20-SMOKE-CODEX.md && grep -q 'smoke exit=0' 20-SMOKE-CODEX.md && python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/plan04.before.json $(sed -n 's/^scratch work dir: \([^ ]*\).*/--scratch-root \1/p' tmp/p20/headless/codex-smoke.log)` | new evidence | ✅ |
| 20-04-T2 | 04 | 4 | EVAL-04 (R8; 18 #6, #11) | T-20-20 | codex event types from a scrubbed direct run under `run-with-timeout 120`; C-W12 enumeration under a controlled PATH and `run-with-timeout 120` (`installed_runtimes == ["codex"]`, `cursor-agent models` never reached) | live headless | `grep -q 'turn.completed' 20-SMOKE-CODEX.md && grep -q 'enumeration scoped' 20-SMOKE-CODEX.md` | new evidence | ✅ |
| 20-04-T3 | 04 | 4 | EVAL-04 (R8; 18 #12) | T-20-11 | readiness = the one `spawn` pid without an `exit` line names `codex exec` and the `sleep 170` tool call is observed (or its absence recorded); group kill by the runner's own pgid file, run-owned TMPDIR, `cross-ai-*`/`xai-*` temp check, ps proof; `run-with-timeout 200` per probe | live headless | `test "$(grep -c 'status=signal' 20-SMOKE-CODEX.md)" -ge 2 && grep -q 'codex-signal1.pgid' 20-SMOKE-CODEX.md && test "$(grep -c '^- readiness: live child [0-9]* (codex exec)' 20-SMOKE-CODEX.md)" -eq 2` | new evidence | ✅ |
| 20-05-T1 | 05 | 5 | EVAL-05 (R5, R7, R8) | T-20-22, T-20-23, T-20-25 | standalone server (`--print-argv` shows `--standalone`; a `Managed service port` line stops the plan); bounds sum 1600 s with a remaining-time check; outer snapshot with `--scratch-root`; lane trials and loader proof routed to 20-07 required steps 6 and 7 | live headless | `grep -Eq 'AIKIT-XAI status=(ok\|no_change) cli=opencode .* cli_rc=0 ' 20-SMOKE-OPENCODE.md && grep -q 'smoke exit=0' 20-SMOKE-OPENCODE.md && grep -q -- '--standalone' 20-SMOKE-OPENCODE.md` | new evidence | ✅ |
| 20-05-T2 | 05 | 5 | EVAL-05 (R7, R8; 18 #6) | T-20-26 | `#high` suffix probe recorded as accepted / rejected / not reached (never `verified`); C-W12 enumeration scoped on opencode under `run-with-timeout 120`, naming `opencode models` and the private `opencode serve --port 0` probe, both gone afterwards | live headless | `grep -q '^## Effort suffix probe' 20-SMOKE-OPENCODE.md && grep -q 'runtime_enumeration' 20-SMOKE-OPENCODE.md && grep -q 'opencode serve' 20-SMOKE-OPENCODE.md` | new evidence | ✅ |
| 20-05-T3 | 05 | 5 | EVAL-05 (R8; 18 #12) | T-20-24 | readiness per 20-04 (live child names `opencode run`, tool call observed); group kill, run-owned TMPDIR, ps proof (opencode mirror); `run-with-timeout 200` per probe | live headless | `test "$(grep -c 'status=signal' 20-SMOKE-OPENCODE.md)" -ge 2 && grep -q 'opencode-signal1.pgid' 20-SMOKE-OPENCODE.md && test "$(grep -c '^- readiness: live child [0-9]* (opencode run)' 20-SMOKE-OPENCODE.md)" -eq 2` | new evidence | ✅ |
| 20-06-T1 | 06 | 6 | EVAL-04 (R3; SC3 default branch) | T-20-13, T-20-21 | labels never exceed the evidence; a dropped name leaves `HOST_SIGNAL_ENV_VARS`, the template `scrubEnv` literal and every pin in one commit | unit + self-test | `python3 -m unittest tests.test_ai_kit_spec_runtimes_table && python3 -m unittest tests.test_ai_kit_spec && node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` | exists (update) | ✅ |
| 20-06-T2 | 06 | 6 | EVAL-05 (R5, R6; D-12) | T-20-13 | report-only gitignore note; each note PASS or KEPT, never half-edited; installer note claims only the exercised path | unit | `python3 -m unittest tests.test_curated_config_followups tests.test_curated_config_cross_ai tests.test_curated_config_apply tests.test_curated_config_recommend` | exists (extend) | ✅ |
| 20-06-T3 | 06 | 6 | EVAL-05 (skill rule) | T-20-14 | judge reports scanned before the move; pi judge 600/630 s inside the 1800 s dispatch with a remaining-time check before every attempt; one decision table, per judge CRITICAL 0 / IMPORTANT 0 / >= 96 / >= its Phase 19 baseline (the floor); unavailable pi = BLOCKED, never PASS | live judge | `python3 tests/gsd_curated_eval.py digest --check 20-SKILL-JUDGE.md && python3 tests/gsd_curated_eval.py secret-scan skill-judge` | new evidence | ✅ |
| 20-07-T1 | 07 | 7 | EVAL-04/05 (D-01, D-11, R5) | T-20-15, T-20-16 | names-only scripts; scratch-only commands; `$OUT` captured before any `cd`; required lane trials with `/gsd-review --phase 20` and `ran`/`skipped`/`blocked` outcomes; loader-output precedence with a first-observation branch and a `precedence pending` outcome that keeps EVAL-05 pending; shadow case user opt-in; D-07 (with per-agent scope), R5 row and ROADMAP SC3 amended | doc + secret-scan | `grep -Eq '^(6\|7)\. .*REQUIRED' 20-INTERACTIVE-OPENCODE.md && test "$(grep -c 'gsd-review --phase 20' 20-INTERACTIVE-OPENCODE.md)" -ge 2 && grep -q 'precedence pending' 20-INTERACTIVE-OPENCODE.md && grep -q 'debug agents' 20-CONTEXT.md && grep -q 'clarified' .planning/ROADMAP.md && python3 tests/gsd_curated_eval.py secret-scan .planning/phases/20-live-validation-on-codex-opencode` | new | ✅ |
| 20-07-T2 | 07 | 7 | EVAL-04/05 (R9) | T-20-SC | gates with `exit=0` recorded in test.txt / validate.txt / validate-unittest.txt and counts read from the files that carry them (no second matrix run); docker `exit=0` or the verbatim no-engine message; snapshot against the plan's own baseline | full | `grep -qx 'exit=0' tmp/p20/gates/test.txt && grep -qx 'exit=0' tmp/p20/gates/validate.txt && grep -qx 'exit=0' tmp/p20/gates/validate-unittest.txt && { grep -qx 'exit=0' tmp/p20/gates/docker.txt \|\| grep -q 'neither docker nor podman found on PATH' tmp/p20/gates/docker.txt; } && python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/plan07.before.json` (`make test` already runs the e2e tier; each gate's log gets `echo "exit=$?"` appended) | exists | ✅ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence paths in the Automated Command column are relative to `.planning/phases/20-live-validation-on-codex-opencode/` where a bare file name is given.

---

## Wave 0 Requirements

- [x] host-aware `promised`/Control tests replacing the non-claude refusal test
- [x] smoke install-step seam tests (installer argv, cwd, HOME, ordering, failure stops before inventory)
- [x] allowlist snapshot tests, including the TOML semantic compare
- [x] planned == baked readers with fixtures (frontmatter, TOML)
- [x] `live_tables` exports `RUNTIME_PROFILE_MAP`
- [x] host-parametrized "never the host lane" test in recommend

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Smoke from the user's interactive codex session | EVAL-04 | SPEC constraint: only the user's own interactive session counts | The per-host script produced by this phase |
| Smoke from the user's interactive opencode session | EVAL-05 | Same | The per-host script produced by this phase |
| `CODEX_*` env names in the codex TUI shell | EVAL-04 (D-05) | Only the interactive TUI shows its own env | Names-only listing step in the codex script; afterwards the `TUI confirmation pending` labels in `detection.py` are updated with the table test (20-07 `## What happens next`) |
| Opencode review lane from an opencode host, two trials per route | EVAL-05 (D-11) | gsd-core's self-skip is LLM-judged (`auto`) on opencode; each trial is a model call from the user's session | REQUIRED step 6 of the opencode script, in the kept scratch project made reviewable (PROJECT/ROADMAP/STATE and the phase plans copied in): `/gsd-review --phase 20 --opencode` twice, `review.default_reviewers=["opencode"]` twice with `/gsd-review --phase 20`, key restored; each trial `ran`, `skipped (...)` or `blocked (prerequisite: ...)`, a blocked trial repeated after the fix; status lines sent back |
| Project agents win over global ones in the opencode loader | EVAL-05 (R5 precedence) | `opencode debug agents` has no `--standalone` and would read the user's managed service; whether `run --format json` events carry model ids is unverified | REQUIRED step 7 of the opencode script: `smoke --host opencode --keep-scratch`, then `opencode run --standalone --agent gsd-planner --format json` redirected to `$OUT` (captured before any `cd`) with a first-observation grep for a model field, else the `debug agents` listing (recorded as shared-service; compared per agent against baked.json when it names every agent) compared with the baked `model:` line; outcome `precedence proved` / `contradicted` / `pending (no loader field observed)`, and EVAL-05 is checked off only on `proved`; model self-report never accepted; the same-named-global shadow case only if the user opts in (SPEC R5 row amended) |
| Native per-call model selection from the host | ROADMAP SC3 (optional) | SC3 is an OR already satisfied by the pinned `native_selectors == ()` default | Optional step 8 of both scripts; can only upgrade a label later |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-18 (Nyquist audit)

## Validation Audit 2026-10-18

| Metric | Count |
|--------|-------|
| Rows audited | 18 |
| COVERED | 18 |
| PARTIAL | 0 |
| MISSING | 0 |
| Tests added | 0 |

- Unit/self-test rows (01, 02, 03, 06-T1/T2): commands re-run on HEAD, exit 0. 20-03 evidence greps use the superseded strings from 20-REVIEW-FIX.md.
- Live rows (04, 05, 06-T3, 07): evidence greps re-run on the committed files, exit 0; `tmp/p20/gates/*.txt` all end `exit=0`. The `snapshot --check` parts were not re-run (they hash the real host config; the audit stays hermetic), so they rest on the recorded run.
- 20-06-T2's branch-consistency verify script is superseded by `test_phase_20_evidence_notes_claim_only_what_the_smoke_ran`.
- Manual-only (human_verification, not faked): the interactive codex run (20-INTERACTIVE-CODEX.md) and the interactive opencode run (20-INTERACTIVE-OPENCODE.md), which cover the TUI `CODEX_*` names, required steps 6 (lane trials) and 7 (loader precedence), and optional step 8 (SC3).
