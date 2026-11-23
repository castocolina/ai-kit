---
phase: 38-runner-hardening-and-run-safety
verified: 2026-11-22T15:53:37Z
verified_head: a1ed901
status: passed
score: 12/12 requirements verified
covered_files: [".planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-01-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-02-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-02-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-03-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-03-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-04-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-05-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-06-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-07-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-07-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-08-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-09-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-10-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-11-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-12-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-13-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-14-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-15-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-16-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-17-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-18-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-19-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-20-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-20-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-21-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-21-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-22-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-22-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-23-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-24-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-25-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-25-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-26-SUMMARY.md", ".planning/phases/38-runner-hardening-and-run-safety/38-27-PLAN.md", ".planning/phases/38-runner-hardening-and-run-safety/38-27-SUMMARY.md", ".pre-commit-config.yaml", "Makefile", "README.md", "skills/ai-kit-cross-ai/SKILL.md", "skills/ai-kit-cross-ai/evals/evals.json", "skills/ai-kit-cross-ai/references/launch-and-wait.md", "skills/ai-kit-gsd-curated-config/SKILL.md", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py", "skills/ai-kit-gsd-curated-config/references/runner.md", "skills/ai-kit-spec-execute-superpowers/SKILL.md", "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py", "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py", "skills/ai-kit-spec-execute-superpowers/references/design-notes.md", "skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md", "skills/ai-kit-spec-execute-superpowers/references/escalation.md", "skills/ai-kit-spec-execute-superpowers/references/state-management.md", "skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py", "skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py", "skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py", "skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py", "skills/ai-kit-spec-review/references/cli-profiles/codex.md", "skills/ai-kit-spec-review/references/cross-ai-dispatch.md", "skills/ai-kit-spec-review/references/cross-ai-selftest.mjs", "skills/ai-kit-spec-review/references/cross-ai.mjs", "tests/cross_ai_selftest.py", "tests/fixtures/cross_ai_selftest_secs.json", "tests/fixtures/curated_config_v2/golden/claude-mvp-adaptive.json", "tests/fixtures/curated_config_v2/golden/claude-rigorous-adaptive.json", "tests/fixtures/curated_config_v2/golden/claude-standard-adaptive.json", "tests/fixtures/curated_config_v2/golden/codex-mvp-adaptive.json", "tests/fixtures/curated_config_v2/golden/codex-mvp-budget.json", "tests/fixtures/curated_config_v2/golden/codex-rigorous-adaptive.json", "tests/fixtures/curated_config_v2/golden/codex-standard-adaptive.json", "tests/fixtures/no_hardcoded_models_baseline.json", "tests/fixtures/runner_describe_golden.json", "tests/fixtures/runner_host_protocol.json", "tests/test_ai_kit_spec.py", "tests/test_ai_kit_spec_runner_dispatch.py", "tests/test_ai_kit_spec_runtimes_table.py", "tests/test_ai_kit_spec_superpowers.py", "tests/test_arch.py", "tests/test_config_callers.py", "tests/test_cross_ai_docs_text.py", "tests/test_cross_ai_render_sync.py", "tests/test_cross_ai_runner_e2e.py", "tests/test_cross_ai_selftest_logic_1_e2e.py", "tests/test_cross_ai_selftest_logic_2_e2e.py", "tests/test_cross_ai_selftest_logic_3_e2e.py", "tests/test_cross_ai_selftest_logic_4_e2e.py", "tests/test_cross_ai_selftest_logic_5_e2e.py", "tests/test_cross_ai_selftest_runtime_1_e2e.py", "tests/test_cross_ai_selftest_runtime_2_e2e.py", "tests/test_cross_ai_selftest_runtime_3_e2e.py", "tests/test_cross_ai_selftest_runtime_4_e2e.py", "tests/test_cross_ai_selftest_runtime_5_e2e.py", "tests/test_cross_ai_selftest_runtime_6_e2e.py", "tests/test_cross_ai_selftest_runtime_7_e2e.py", "tests/test_cross_ai_settings_text.py", "tests/test_cross_ai_skill_text.py", "tests/test_curated_config_apply.py", "tests/test_curated_config_apply_e2e.py", "tests/test_curated_config_cross_ai.py", "tests/test_curated_config_e2e.py", "tests/test_curated_config_inventory.py", "tests/test_curated_config_plan_edit.py", "tests/test_curated_config_script.py", "tests/test_runner_describe.py", "tests/test_runner_host_protocol.py", "tests/test_runner_status_group.py", "tests/test_staged_mapper.py", "tools/run_unittest_parallel.py", "tools/staged_mapper.py"]
covered_digest: "v4:sha256:021c330feed17f073b33e2b7f25c0e5d2e67f1f5a5447f132eae39b8c374fadd"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 11/12
  gaps_closed:
    - "R12 (RUN-13): the state-home exclusion now holds from a subdirectory start (stateExclude anchored at the checkout top, fix in a1ed901)"
  gaps_remaining: []
  regressions: []
---

# Phase 38: Runner hardening and run safety, verification report

**Phase goal (ROADMAP):** A hung lane no longer burns the whole window, the Phase 25 review cleanup lands, and an execute run
neither starts on a checkout another run holds nor counts as done when its commits do not match its plan (plus RUN-13: a hosted
lane is as safe as a headless one).
**Verified:** 2026-11-22T15:53:37Z at HEAD a1ed901 (branch gsd/phase-38-runner-hardening-and-run-safety; first pass 2026-11-22T15:06:51Z at 97b214e)
**Status:** passed (12/12 requirements verified by evidence; the owner items below are NOT verified)
**Re-verification:** Yes, after the R12 gap closure in a1ed901. No `38-VALIDATION.md` exists for this phase, so none was written or updated.

## Summary

All twelve SPEC requirements are verified by evidence I ran myself. The first pass (97b214e) found one gap in R12: the state-home
exclusion worked only when the runner started at the checkout root. The fix in a1ed901 (`stateExclude`, anchored at the checkout
top) closes it; I re-ran my subdirectory reproduction and the new cases (Gaps Summary). The items under "Owner items" below are
NOT verified: the live herdr sweep proof, the 38-01 real-home probes, the install on the real machine, the three review-todo
decisions and the flagged judgment-tier prohibitions. None of them is a SPEC acceptance condition.

The SPEC does not require a live herdr proof for R12. Its acceptance text (SPEC lines 517-529) is a list of tests "with 37's fake
`herdr` on PATH", the Constraints (line 570-572) keep any live probe out of `make test`, and REQUIREMENTS.md RUN-13 has no live
clause. The live sweep therefore goes under Owner items and does not make the status `human_needed`.

## Goal Achievement

### Observable truths (SPEC R1 to R12, mapped to roadmap success criteria 1 to 7)

| # | Truth | Status | Evidence (ran by me at 97b214e; R12 re-run at a1ed901; "gate log" marks orchestrator logs) |
|---|-------|--------|---------------------------------------------------------------|
| R1 | Opt-in idle watchdog ends a silent lane through finalize; ladder unchanged (RUN-03, SC1) | VERIFIED | Cases idle-silent-ended (exact idle line, `status=timeout rule=idle-watchdog` attempt line, one spawn, group gone via deadCheck), idle-keeps-printing, idle-slow-quiet-default (`on timeout=900s`, not ended), idle-off-never-fires, idle-then-resume, idle-loses-to-deadline/limit/signal, pure-idle-parse, idle-print-off/default/config/notices: pass. `--print-argv`: `cross-ai: idle watchdog off`, `on timeout=900s` for `default`, `on timeout=30s` |
| R2 | Execute idle clock resets on tree/commit change; print-but-no-change reported, never ended (RUN-03, SC1) | VERIFIED | poll-quiet-commit, poll-quiet-edit, poll-quiet-idle, poll-chatty-nochange (notice + `findings=no_tree_change`, no idle line), poll-notes-once-per-run, poll-review-none, poll-head-only, poll-change-then-stall, poll-git-fail-once, poll-git-hang-stopped/capped, poll-non-git-note, baseline-owner-dirty (index bytes unchanged): pass |
| R3 | Run lock refuses a second execute run; stale cleared; released on every exit (RUN-07, SC3) | VERIFIED | lock-two-at-once (exits [0,75], loser `status=locked` with the held line and no `retry_after_s`, one spawn), lock-stale-cleared, lock-orphan-refuses, lock-foreign-refuses, lock-unreadable-refuses/-reread, lock-invalid-refuses, lock-stale-race, pure-lock-clear-race, lock-gone-after-failure/-signal, lock-review-note, lock-review-no-note-stale, lock-none-usage, lock-late-usage-no-lock, lock-record-fields, lock-held-redacts, lock-not-taken, pure-lock-start-ps, pure-lock-root, pure-lock-verdict: pass |
| R4 | Start-of-run baseline recorded, reused per task, replaced with a finding (RUN-07, SC3) | VERIFIED | baseline-fresh-recorded, baseline-reused, baseline-reused-equal, baseline-rebased, baseline-expired, baseline-flag-wins, baseline-flag-bad, baseline-unborn, baseline-unwritable, baseline-owner-dirty, baseline-kept-unchecked, baseline-kept-ancestry, pure-baseline-flag-parse, pure-baseline-verdict: pass |
| R5 | Execute result is `ok` only when commits, files and report agree with the plan (RUN-08, SC4) | VERIFIED (one owner decision, see Owner items) | plan-all-covered (`coverage=3/3 findings=-`), plan-one-of-three (`partial`, `task_uncovered detail=t2, t3`), plan-no-commit, plan-admits, plan-deviations-ok, plan-forbidden, plan-forbidden-uncommitted, plan-forbidden-named, plan-forbid-flag, plan-no-tasks (`n/a`), plan-id-match/short, plan-owner-dirty, plan-list-cap, plan-failed-lists-missing, plan-merge-clean, plan-git-log/show/diff-tree-fails, plan-config-seed-bad, plan-out-of-table, pure-tasks-types (tracer counted), pure-status-head-re, check-group-no-spawn, finding-lines-through-finish, all pure-admission-*, pure-cover-*, pure-findings-*: pass. `--describe` lists the 9 finding codes and `partial`/`locked`. Deviation: `parseTasks` counts every non-checkpoint type (pure-tasks-types pins `manual` as counted) while R5 names absent/auto/tdd/tracer |
| R6 | One confirmed-router rule for every caller (RUN-04, SC2) | VERIFIED (one owner decision, see Owner items) | `model_heuristics.router_statement` / `is_confirmed_router` (lines 37-74) read by `runner_dispatch.resolve_route` (line 260), curated-config `catalog_adapter._router_rule` -> `router_confirmed` (lines 285-293, 393, 414), which feeds `cross_ai.py` targets -> `router_backed` -> `routerBacked` render (`cross_ai_script.py:104-105`). TestRouterRuleMatrix in tests.test_curated_config_inventory (116 tests ok); runner cases overlay-router-row-live/-unconfirmed, router-quota-one-cycle: pass. Deviation: an owner-confirmed `is_router` alone with a heuristic `fallback_quota` true confirms (review LOW-9) |
| R7 | `quota_cycle` class; JSON `classify-dispatch-failure`; token `python3 -c` parses gone (RUN-04, SC2) | VERIFIED | Ran the CLI: `{"class": "quota_cycle", "retry_after_s": 600, "cycle": 1}` for a 75 with tokens (leading-zero string to int); `{"class": "real_error", ...null}` for a bare 75 `locked`. tests.test_ai_kit_spec_superpowers 173 ok. `dispatch-external-cli.md` has no `python3 -c` reading RETURNCODE / retry_after_s / cycle (the remaining `python3 -c` lines build wave-state JSON) |
| R8 | Harness in sibling file; rendered copies lack it and refuse `--self-test` (RUN-04, SC2) | VERIFIED | Template has no `blackBoxSelfTest`/fakes; one `export { ... }` list (line 6743); dynamic import (line 6324). Ran the live rendered copy `.planning/scripts/cross-ai.mjs` (no sibling): `--self-test` and `--self-test-list` both exit 2 with `cross-ai: the self-test is not shipped in this copy; run it from the template`. `--self-test-list` before the move (`36de90c^`) vs after (`0b37ab8`): 627 lines each, byte-equal. Arch test `test_selftest_imports_only_exported_runner_names`; runner baseline entry gone from `no_hardcoded_models_baseline.json`; render sync 11 ok |
| R9 | curated-config asks gsd-core which skills it would skip (RUN-04, SC2) | VERIFIED | `plan_io._GSD_SKILL_SCRIPT` calls `buildAgentSkillsBlock` per reference; child runs through `detection.bounded_run` (`run_in_own_group`). The twelve listed resolution helpers are gone (`rg -w`: 0 hits in skills/, tests/, tools/). `locate`, `needed_root`, `skip_reason`, `_kept_names` stay: 38-RESEARCH live fact, they also serve recommend/wiring and build today's fix text. tests.test_curated_config_e2e (21 ok, TestGsdSkillVerdicts against the real project-local gsd-core) and test_curated_config_skills/apply: pass |
| R10 | Phase 25 cleanup corrected; timeout shown, never silently changed (RUN-04, SC2, SC5) | VERIFIED | `watchChunk(relay, chunk)` (line 4910); `dropState` tests `!QUOTA_KEEP.has(status)` (line 5304); `build_runner_argv` returns the list directly (runner_dispatch.py 265-272); kept-helpers comment at cross-ai.mjs 2812-2813; `clampCapS`, `clampAttemptTimeout`, `liveMatch`, `armLimit` present. temp-dirs-gone, pure-ladder-cap-boundary/-clamp, quota-cap-clamp-child: pass. 1799/1800 plan-entry pins in tests.test_curated_config_cross_ai (55 ok) |
| R11 | Skill text, docs, closed lists, guard, judge bar (JDG-04, HUB-09, SC6) | VERIFIED | `skills/ai-kit-cross-ai/SKILL.md` names every new flag, status, finding code, `coverage=`/`findings=`, `run.json`, `setsid`; dispatch reference "Run safety" paragraph and status table carry `partial`/`locked`; README row names watchdog, lock, `partial`, `--sweep`. Doc-contract modules skill_text 30, docs_text 17, settings_text 23 ok; tests.test_arch_hardcoded_models 23 ok. Judge loop 38 round 1 (recorded below) meets the bar |
| R12 | Run safety for a hosted lane (RUN-13, SC7) | VERIFIED | Every acceptance clause has a passing fake-herdr case: sweep-sigkill-e2e (hosted path active in my scratch path; closes exactly t1, removes the directory, no key left), sweep-foreign-safe, sweep-down, sweep-host-none, sweep-env-none, sweep-live-untouched, sweep-pid-file-live, sweep-race, sweep-unreadable, sweep-fresh-unreadable, sweep-other-host, sweep-null-id, sweep-zero-tabs, sweep-notfound, sweep-claim-takeover, sweep-bad-record, sweep-herdr-hang, sweep-close-hang, sweep-empty, sweep-dead-closes, sweep-auto-run, host-idle-silent/-busy/-commits, host-state-in-checkout/-is-root, state-inside-*/state-root-nochange/state-idle-expires, host-cap, host-key-scan, host-findings-partial, host-lock-live-group, host-lock-stale-swept, host-rerun-lock-fields, host-no-herdr, host-fake-shapes; `--describe` lists `--sweep`. Gap closed at a1ed901: subdirectory repro excludes the state home from root, `src` and `src/deep`; new cases state-subdir-nochange, state-subdir-root-nochange, state-subdir-ignored, state-subdir-top-edit, state-subdir-local, state-plan-root, state-plan-subdir, state-idle-expires-subdir, host-state-subdir: pass |

**Score:** 12/12 requirements verified, 0 present-but-behavior-unverified.

Roadmap success criteria: SC1 (R1, R2) met; SC2 (R6 to R10) met; SC3 (R3, R4) met; SC4 (R5) met; SC5 (temp-dirs-gone) met;
SC6 (judge bar) met; SC7 (R12) met after the a1ed901 fix.

### Judge loop 38 (R11 / JDG-04 record)

| Skill | Judges | Percent / grade | Critical / high | Bar | Base | Regression |
|-------|--------|-----------------|-----------------|-----|------|------------|
| ai-kit-cross-ai | opencode router-env/my-referee-one, my-referee-two | 86.4 B, 89.6 B | 0 / 2 and 0 / 1 | met (grade B or better) | loop 37 r3 83.2 | none (+3.2) |
| ai-kit-gsd-curated-config | same | 85.6 B, 93.6 A | 0 / 3 and 0 / 0 | met (grade B or better) | loop 37 r1 88.0 | none (-2.4, limit 7.0 points, `REGRESSION_TENTHS = 70`) |

Three high findings per skill were fixed under the fix-3-or-fewer rule (`fixes.md` beside each round), so both digests are
stale by design. `ai-kit-spec-execute-superpowers` was not judged: its SKILL.md diff since 42bad13 is a 5-line rename of the
`quota` outcome into `quota_cycle` and `quota` (I read the diff). `python3 tools/judge_loop.py check .planning/judge` (ran):
both skills `loop 38 round 1 ... bar met: grade B or better`, plus stale-digest and facts-drift notes for 15 skills
(informational; check-dogfood still ends ok).

### Required artifacts and key links

| Artifact | Status | Details |
|----------|--------|---------|
| `skills/ai-kit-spec-review/references/cross-ai.mjs` (template 10, 6,880 lines) | VERIFIED | Watchdog, lock, baseline, planner checks, sweep, `--describe` keys; one export list |
| `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs` (10,823 lines, 787 cases) | VERIFIED | Loaded only for `--self-test`/`--self-test-list` |
| `.planning/scripts/cross-ai.mjs` (live copy) | VERIFIED | Re-rendered; check-dogfood ok; refuses `--self-test` |
| `ai_kit_spec/model_heuristics.py` router rule -> three callers | WIRED | See R6 |
| `ai_kit_spec_superpowers` classifier -> CLI -> reference | WIRED | See R7 |
| curated-config `plan_io` -> project-local gsd-core `buildAgentSkillsBlock` | WIRED | See R9; real gsd-core e2e passes |
| `HERDR_VERBS` / `HERDR_VERBS_ALLOWED` / fixture `herdr_verbs` | VERIFIED | All three hold `tab list` |

### Behavioral spot-checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--print-argv` byte-stability, 10 samples without new flags | scratch script under tmp/ (removed after the run): base template `git show 42bad13:<template>` vs HEAD, scratch HOME, real node, 10 sample argument sets | 10/10 byte-equal after normalizing the per-call random session UUID, dropping the one added `cross-ai: idle watchdog off` line and the trailing ` coverage=- findings=-`; those two are the only deltas (SPEC-locked) | PASS |
| `--describe` | same script | old 7 keys unchanged; new `statuses`, `findings`, `supervision_flags` (`--baseline --forbid --idle-timeout --plan-id --sweep`); `template_version` 9 -> 10 | PASS |
| Rendered copy refusal | live copy `--self-test`, `--self-test-list` | exit 2, named refusal | PASS |
| List unchanged by the move | `36de90c^` vs `0b37ab8` `--self-test-list` | 627 lines, byte-equal | PASS |
| `classify-dispatch-failure` JSON | superpowers CLI, two inputs | one JSON object with `class`, `retry_after_s`, `cycle` | PASS |
| State-home exclusion from a subdirectory | scratch script under tmp/ (removed after the run): a scratch copy of the template plus one `export { stateExcludeRel }` (later `stateExclude`) line, imported from a probe module with `XDG_STATE_HOME=<scratch repo>/.state` and cwd at the root, `src` and `src/deep` | 97b214e: root -> `".state/ai-kit/spec"`, `src` and `src/deep` -> `null`, `git add -A` from `src/` recorded `.state/ai-kit/spec/host/abc/out` (FAIL). a1ed901 (`stateExclude`, same probe plus `git add -A -- <pathspec>` from each start): all three return `:(top,exclude,literal).state/ai-kit/spec`, the snapshot records only `src/deep/work.txt` | PASS (gap closed) |

### Self-test cases and modules I ran

- Self-test: 224 cases in 19 calls of at most 12 (`AIKIT_XAI_SELFTEST_CASES`, real node, scratch HOME under the watchdog), every
  call `self-test ok`; the harness refuses a call unless every named case exists, so each count is exact. 108 cases chosen per
  requirement plus the 116 remaining cases that the 27 PLANs and 38-REVIEW.md name.
- Unit/e2e modules (run_unittest_parallel, two per call, under the watchdog): runner_describe 17, runner_facts 10,
  runner_host_protocol 13, runner_flags 15, runner_settings_argv 21, cross_ai_render_sync 11, cross_ai_skill_text 30,
  cross_ai_docs_text 17, cross_ai_settings_text 23, ai_kit_spec_runner_dispatch 80, curated_config_apply 119,
  curated_config_skills 90, curated_config_cross_ai 55, arch_hardcoded_models 23, staged_mapper 74, runner_fork_chain 4,
  curated_config_inventory 116, ai_kit_spec_superpowers 173, curated_config_e2e 21, arch 118: 20 modules, 1030 tests, all ok.
- `make check-dogfood` (ran): ends `check-dogfood: ok`. `python3 tools/judge_loop.py check .planning/judge` (ran): exit 0.
- Re-verification at a1ed901 (ran): the subdirectory repro (above); 21 self-test cases in 2 calls, both `self-test ok` (the 9 new
  subdirectory/state-plan cases, plus state-inside-*, state-root-nochange, state-idle-expires, host-state-in-checkout/-is-root,
  host-findings-partial, host-idle-silent/-commits, sweep-sigkill-e2e, poll-quiet-commit); `--self-test-list` 796 cases;
  tests.test_cross_ai_render_sync 11 ok and tests.test_arch 118 ok; `make check-dogfood` ends `check-dogfood: ok` (live copy
  re-rendered in the fold).
- Gate logs at 97b214e (orchestrator, read, not rerun): make test, lint, validate, test-unit, e2e-test (29/29 modules,
  install 48/0), e2e-test-modules, e2e-test-install, e2e-docker (clean-room PASS; the image has no node, so the self-test shards
  skip there and ran on the host), wizard PTY (14 OK), all exit 0.

### Probe execution

Checked: the repository has no `scripts/*/tests/probe-*.sh`. The 38-01 spike probes are real-home probes and were not run (Owner
items). `verify.artifacts` and `verify.key-links` were not run over the 27 plans; artifacts and links were checked by reading the
code (tables above).

### Requirements coverage

| Requirement | Plans | Status | Evidence |
|-------------|-------|--------|----------|
| RUN-03 | 38-01, 38-10, 38-11, 38-16 | SATISFIED | R1, R2 |
| RUN-04 | 38-02 to 38-09, 38-25, 38-27 | SATISFIED | R6 to R10 |
| RUN-07 | 38-01, 38-13, 38-14, 38-15 | SATISFIED | R3, R4 |
| RUN-08 | 38-12, 38-17, 38-18, 38-22 | SATISFIED (owner decision on task types open) | R5 |
| RUN-13 | 38-19, 38-20, 38-21, 38-22, 38-26 | SATISFIED | R12 (gap closed in a1ed901) |
| JDG-04 | 38-22 to 38-26 | SATISFIED | judge table above |
| HUB-09 | 38-07, 38-22, 38-23, 38-24, 38-26 | SATISFIED | runner baseline entry removed; guard 23 ok |

Plans column read from each PLAN's `requirements:` field. REQUIREMENTS.md traceability maps RUN-03, RUN-04, RUN-07, RUN-08 and
RUN-13 to Phase 38 (RUN-05, RUN-09 to RUN-11 and RUN-14 to 38.1); JDG-04 (traceability Phase 31/32) and HUB-09 (Phase 35) are
cross-cutting rows the roadmap names for this phase. No orphaned requirement.

### SPEC prohibitions (test tier, each mapped to a case I ran)

Seed lists never gate a runtime (plan-out-of-table); no end on a failed git read or on heartbeats alone (poll-git-fail-once,
poll-git-hang-*, idle-silent-ended); user index untouched (baseline-owner-dirty); no clear of an orphan, foreign or unreadable
lock (lock-orphan/foreign/unreadable-refuses); no `ok` or stdout answer on a blocking finding (plan-* cases); no second lane
(idle-silent-ended one spawn, lock-two-at-once); modes and redaction (lock-record-fields, lock-held-redacts, host-key-scan); no
jev/herdr outside the transport (arch rules, fake herdr only); clamp helpers kept (pure-ladder-cap-*); tab-close and live-run
safety (sweep-foreign-safe, sweep-live-untouched, sweep-pid-file-live); herdr never a liveness input (host-lock-stale-swept,
host-lock-live-group); no secret left (host-key-scan, sweep-down, sweep-sigkill-e2e); auto sweep with hosting off calls no herdr
(sweep-host-none, sweep-env-none); hosting parity (host-findings-partial, host-cap). All pass.

### Anti-patterns

Debt markers: 0 added lines with `TBD`, `FIXME` or `XXX` in the 79 changed files outside `.planning/` (scan of
`git diff -U0 42bad13 HEAD`). The review's open items are tracked in
`.planning/todos/pending/2026-11-22-review-notes-left-open-by-phase-38.md`.

| File | Item | Severity | Impact |
|------|------|----------|--------|
| cross-ai.mjs `stateExcludeRel` | exclusion relative to cwd (review LOW-11) | fixed in a1ed901 | gap closed |
| cross-ai.mjs `treeState` | from a subdirectory the ignored-file signature (`git ls-files -o -i --directory`) and the nested-repo walk still cover only the start folder (reported by the fix agent; read in the code) | WARNING | pre-existing snapshot scope (U-3), not a phase 38 requirement: R12 asks that the state home be excluded from the ignored-file signature, which holds (`ex.local` filter); an edit to an ignored file or a nested repo outside the start folder is not seen as a change |
| cross-ai.mjs admission seed | `remaining work` also matches "no remaining work" (LOW-14) | WARNING | a complete run can end `partial`; seed is owner-replaceable and labeled recall-unverified |
| cross-ai.mjs `acquireLock` | after three lost rounds prints `run lock held by pid -` (LOW-12) | WARNING | refusal names no holder |
| cross-ai.mjs `lockVerdict` | `own` branch unreachable (LOW-13) | INFO | dead branch |
| tools/staged_mapper.py | non-Python files under tools/, tests/, docs/ reach the model guard only at push (LOW-15) | INFO | push stage covers it |

## Owner items (not verifiable without the owner, real home or a live model; not requirement gaps)

These items are NOT verified. They do not count against the score and none of them is required by the SPEC's acceptance text.

1. **Live herdr sweep proof (38-26 part 1).** Not run: the consent line `p38-live-sweep real-home: allowed` is absent. The R12
   acceptance clauses ("a runner killed by SIGKILL in the middle of a hosted lane leaves a record, and the next sweep removes the
   env file at once, closes exactly the recorded tab by id and removes the directory", the foreign-tab, fake-down, `--host none`,
   live-run, race, unreadable-record and idle clauses) are covered only by fake-herdr cases (sweep-sigkill-e2e and the sweep-* and
   host-* cases above). The SPEC itself requires the fake (lines 517-529: "tests with 37's fake `herdr` on PATH") and keeps live
   probes out of the suite (line 570-572), so the live proof is not an acceptance condition. Not proven: a real herdr's answers,
   its live `tab_not_found` envelope and real pane timing.
2. **Real-home spike probes (38-01).** claude, opencode, pi text/json host output timing, hosted timing per host and the macOS
   start-time read: not probed (`38-SPIKE.md`). The idle default stays a judged 900 s.
3. **Install on the real machine.** Only the scratch-HOME installer dry run and headless install ran (gate log ship-install.log,
   ship38.log); the real install needs the owner's consent.
4. **Owner decision: curated-config `apply` vs the approved preview** (review LOW-8): apply recomputes its writes from the live
   config; the skill tells the agent to rerun the dry run first. Whether the plan carries a digest of the planned writes.
5. **Owner decision: router rule on an `is_router`-only confirmation** (review LOW-9): `router_statement` confirms when the owner
   confirmed only `is_router` and the `fallback_quota` heuristic is true but unconfirmed; D-17 keys the rule on `fallback_quota`
   with its label. Narrow the rule or amend D-17.
6. **Owner decision: task types counted by `parseTasks`** (review LOW-10): every non-checkpoint type counts (pinned by
   pure-tasks-types with `manual`), while SPEC R5 and D-12 name absent, `auto`, `tdd` and `tracer`. Amend R5/D-12 or narrow the code.

7. **Judgment-tier plan prohibitions, flagged (unverified-prohibition, human review recommended).** Non-authoritative verdict:
   all three held. 38-01: "MUST NOT call a real host from the runner or from its tests" (the spike ran no host call; the module
   tripwire and the arch rules pass) and "MUST NOT run a real-HOME probe without the anchored consent line" (`38-SPIKE.md`: real-home
   probes not run, no consent line). 38-26: "MUST NOT judge ai-kit-commit-fold, a project-rules skill, ai-kit-spec-execute or a
   skill whose SKILL.md this phase left materially unchanged" (loop 38 judged only ai-kit-cross-ai and ai-kit-gsd-curated-config;
   the superpowers SKILL.md diff is a 5-line rename).

## Gaps Summary

No gap remains. The one gap of the first pass, R12 (RUN-13, success criterion 7), is closed:

- First pass (97b214e): `stateExcludeRel(cwd)` resolved the state-home exclusion against the working directory, so from a
  subdirectory it returned null and `git add -A` recorded the state home (38 D-29 locks the exclusion "when it lies inside the
  checkout").
- Fix (a1ed901, folded unit 38 commit): `stateExclude(cwd)` (cross-ai.mjs:4742-4760) resolves the state path from the checkout
  top (`checkoutRoot`, the lock's root) and `treeState` passes `:(top,exclude,literal)<path>` to the snapshot's `git add`
  (line 4777); the ignored-file filter uses the cwd-relative form (`ex.local`).
- Re-verified by me: the scratch repro excludes the state home from the root, `src` and `src/deep`; the 9 new cases (8 logic,
  `state-idle-expires-subdir` and `host-state-subdir` with a real clock) and the existing state-home and hosted cases pass;
  render sync, arch and check-dogfood are green.
- Remaining limit, a warning and not a gap (Anti-patterns): from a subdirectory the ignored-file signature and the nested-repo
  walk cover only the start folder. The SPEC asks only that the state home be excluded from both; it sets no scope for the
  ignored-file check, and that scope predates this phase.

---

_Verified: 2026-11-22T15:53:37Z (first pass 2026-11-22T15:06:51Z)_
_Verifier: Claude (gsd-verifier)_
