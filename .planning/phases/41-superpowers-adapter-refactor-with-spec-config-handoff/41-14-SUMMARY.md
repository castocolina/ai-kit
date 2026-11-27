---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 14
subsystem: closing-gate
tags: [closing-gate, installed-layout, e2e-docker, check-dogfood, live-links]
requires: [41-13]
provides:
  - "Phase 41 verified on the installed layout and every test tier at dcea116; ROADMAP Phase 41 ticked"
affects: []
key-files:
  created: []
  modified:
    - .planning/ROADMAP.md
    - .planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md
requirements-completed: [EXE-01, EXE-04, EXE-05, EXE-08, EXE-09]  # marked by post-plan-p at this plan's SUMMARY commit c59423a; JDG-04 was already complete
duration: 25min
completed: 2026-11-26
executor: "orchestrator delegate in the main checkout (cross_ai false), natively"
---

# Phase 41 Plan 14: Closing gate

Commits: `dcea116` docs(41), the plan amendment below; `80fd2b2` docs(41-14): phase 41 complete (ROADMAP.md only).
Candidate SHA of the gate: `dcea1166e9fabad2deaf49595a4218aef8f8ab05`. No code fix was needed.

Precondition: 41-13-SUMMARY gives all three judged skills `bar met, then fixed under the no-rejudge rule`
(ai-kit-cross-ai `2a914c7`, ai-kit-spec-config `846f6b1`, ai-kit-spec-execute-superpowers `e00735a`). After that,
spec-config went through the c10-41 trim and judge loop 41.1 (bar met, no-rejudge fix `7e49979`). The tree was clean
at the start (HEAD `18a94ba`).

Unit brief: `.aikit/brief/SKILL.md` names unit phase-41 (point wave, head 1420a53561f0). It is our unit's brief and was read.

## Installed layout

`tmp/run-2026-11-23/p41-14/layout_check.py` on dcea116. Isolation comes from the test runner itself:
`run_unittest_parallel.write_tripwire` and `baseline_env` (scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`). PATH holds
the stubs plus a `python3` link only. `ai-kit-spec-execute-superpowers`, `ai-kit-spec-review`, `ai-kit-spec-config` and
`ai-kit-cross-ai` are symlinked under the scratch `.claude/skills/`. The synthetic runtime cache is seeded fresh (codex
installed with both placeholder models, current runner fact) and checked with `routing.runtimes_cache_is_fresh`.
The doc and parser flag sets were read and compared before the run. `<layout>` = `tmp/run-2026-11-23/p41-14/layout`:

```
doc flags: escalation-gate ['--cwd', '--anchor-key', '--injection-file', '--out-dir']; executor-fallback ['--cwd', '--key', '--dispatch-result', '--exclude-keys-file', '--injection-file']; render-toml parser ['--catalog-path', '--json-config', '--keep-backup', '--out', '--replace', '--runtimes-json']
a escalation-gate: exit 0: {"escalate": false, "allowed": ["lane-a"], "exclude": ["lane-b"], "reason": "off"} | ai-kit-spec: fix round stays on lane-a: escalation is off for this lane
b1 print-guidance: exit 0: The owner's config files are never staged, committed or reverted, and a clean-tree check leaves them out: `git status --porcelain -- ':(top)' ':(top,exclude,literal).aikit/config.toml'`.
b2 print-guidance: exit 0: <empty stdout>
c1 host-config-audit: exit 0: snapshot written: True
c2 host-config-audit: exit 0: ai-kit-spec: observation: <layout>/tmpdir/home/.claude/settings.json changed during the lane; a host may rewrite its own config, so this does not show the lane changed it
d1 executor-fallback: exit 0: {"switched": true, "key": "lane-b", "exclude": ["lane-a"]}
d2 executor-fallback: exit 1: {"switched": false, "reason": "not quota"}
d3 executor-fallback: exit 1: {"switched": false, "reason": "unflagged"}
e1 render-toml: exit 0: policy.execute {'session_fallback': True, 'ladder': ['lane-b', 'lane-a']} lanes ['lane-a', 'lane-b']
e2 render-toml: exit 0: policy.execute {'ladder': ['lane-b', 'lane-a']} lanes ['lane-a', 'lane-b']
tripwire calls: 0
scratch gone: True
layout: ok
```

(b1) also asserts the order: `GATES_FRAME` first, then `make test-unit`, `GUARD_FRAME`, the guard rule and the clean-tree
command. (c2) asserts the not-checked line right after the observation. (e1) and (e2) parse the written file with `tomllib`.

Scope check (`scope_check.py`, base = the parent of the commit that added 41-01-PLAN.md): `scope: ok 129 files (base
b7ff220d001c)`. No path is under `.claude/agents/`, `.claude/gsd-core/`, `.claude/commands/` or `.claude/skills/gsd-`,
and none contains `superpowers/skills/`.

## Closing suites

Each suite ran once, one at a time, natively under `orch-guard.py`, through `run_suite.py`. Process groups are in
`pgids.txt`, tag `close41`. Before each suite `/tmp` was at 27.90% and `/var/home` at 58.00%, 57.60% and 57.78%.

- `make test` (make_test.sh, `AI_KIT_TEST_REPORT_DIR=.../reports-dcea1166...`, a new folder):
  `exit 0 peak_runner_procs 8 killed: no`.
  - unit `203/203 modules passed`; unit-uv `3/3 modules passed`.
  - integration `9/9 modules passed`, with `=== tests.test_wizard_pty: ok in 20.1s  Ran 14 tests in 20.087s`.
  - e2e `29/29 modules passed`; installer `48 passed, 0 failed`; arch `3/3 modules passed`.
- `make e2e-docker` (podman, image rebuilt with a network build):
  `exit 0 peak_runner_procs 0 killed: no`.
  - In the container: `203/203`, `3/3`, `=== tests.test_wizard_pty: ok in 23.9s`, `9/9`, `29/29`, `48 passed, 0 failed`,
    `3/3`, lint passed, `==> ai-kit clean-room E2E: PASS`.
  - New image `localhost/ai-kit-e2e`: id `cd16ec7d010d...`, 1545142851 bytes. It stays in the store for the orchestrator.
  - The image has no Node, so `tests.test_ai_kit_gsd_spec_discuss_e2e` reads `Ran 6 tests in 0.000s` there:
    `TestRealBranchPreflight` was skipped inside the clean room. That is a clean-room skip, not a pass; the case ran in
    `make test` (evidence below).
- `make check-dogfood` (dogfood.sh): `exit 0 peak_runner_procs 0 killed: no`;
  `check-dogfood: no-write guard: 3 attempted, 3 executed, 0 skipped`; `check-dogfood: ok`
  (`rg -c "check-dogfood: ok" dogfood.log` = 1). The 13 stale-digest lines are informational. The three phase-41 skills
  are stale by design after their no-rejudge fixes; the others have not changed since their loops.

Execution evidence (`evidence.txt`, from the 247 per-module reports of the one `make test` run; the shard set is
declared from `SHARD_COUNTS` `{'logic': 5, 'runtime': 7}`):

```
tests.test_adapter_single_definitions: rc 0 ran 11 skips []
tests.test_adapter_escalation_flags: rc 0 ran 32 skips []
tests.test_adapter_session_fallback: rc 0 ran 27 skips []
tests.test_host_config_audit: rc 0 ran 15 skips []
tests.test_adapter_executor_switch: rc 0 ran 24 skips []
tests.test_lane_settings: rc 0 ran 58 skips []
tests.test_spec_config_flow_text: rc 0 ran 41 skips []
tests.test_ai_kit_spec_superpowers: rc 0 ran 182 skips []
tests.test_dispatch_guidance_gates: rc 0 ran 32 skips []
tests.test_ai_kit_spec_e2e: rc 0 ran 4 skips []
tests.test_cross_ai_runner_e2e: rc 0 ran 28 skips []
tests.test_wizard_pty: rc 0 ran 14 skips []
tests.test_cross_ai_selftest_logic_1_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_logic_2_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_logic_3_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_logic_4_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_logic_5_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_runtime_1_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_runtime_2_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_runtime_3_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_runtime_4_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_runtime_5_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_runtime_6_e2e: rc 0 ran 1 skips []
tests.test_cross_ai_selftest_runtime_7_e2e: rc 0 ran 1 skips []
tests.test_ai_kit_gsd_spec_discuss_e2e: rc 0 ran 6 skips 0 TestRealBranchPreflight skips 0
non-zero rc modules: none
evidence: ok
```

Allowed skips, none of them in the modules above:
- tests.test_ai_kit_gsd_curated_config_matrix (x2): no cached pi package or installer.
- tests.test_ai_kit_project_rules_docker: `HOT_RELOAD_BASELINE_GAPS is empty`.
- tests.test_ai_kit_spec: the owner capture is pending.
- tests.test_curated_config_e2e (x2): gsd-core 1.22.0 against the 1.16.0 tables.
- tests.test_hook_registry (x2) and tests.test_setup (x38): `textual not installed`; the uv tier runs them.

HEAD equaled `candidate.txt` after the last suite, and `git status --porcelain` was empty.

## Ship order

Installer dry run, `tmp/run-2026-11-23/p41-14/dryrun.py` (`tools/install.sh install --headless --dry-run --skills=all
--with-hooks --examples=none`, every config root under a scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`):

```
skipped Claude Code hook rows — no claude dir
skipped tool-advisor for pi — no pi dir
skipped tool-reminder for pi — no pi dir
headless summary: 23 linked, 0 relinked, 0 foreign-skipped, 0 real-skipped
(dry-run — no changes were made)
dryrun rc 0
scratch HOME entries before/after: 0 0
dryrun: ok
scratch gone: True
```

This phase adds no hook: `git diff --stat 762df77 HEAD -- tools/hooks tools/setup.py` prints nothing.

Judged digests (orchestrator step 1, `digests.sh`): `judge_loop.py check .planning/judge --skills ai-kit-cross-ai
ai-kit-spec-config ai-kit-spec-execute-superpowers --require-current` exited 1. Its only problem lines are the three
`stale digest` lines, and all three skills read `bar met: grade B or better`. spec-config's line is loop 41.1 round 1
(worst 86.4 B). The last no-rejudge fixes are `2a914c7`, `7e49979` (loop 41.1) and `e00735a`. For each one,
`merge-base --is-ancestor` exits 0, the fix commit holds its round's `fixes.md`, and `git log <fix>..HEAD --
skills/<skill>/` prints nothing. All three are stale by design. Ledger: `judged digests: ok dcea1166...`.

Live install (orchestrator step 2, link-only, read-only in this run). HEAD, the unit-branch tip and `candidate.txt` were
all dcea1166. `tmp/run-2026-11-23/p41-14/live_links.py` printed `ok` with `(no write)` for each of the five skills:
- ai-kit-spec-execute-superpowers, ai-kit-spec-review, ai-kit-spec-config and ai-kit-cross-ai (the changed skills).
- ai-kit-gsd-curated-config (checked read-only).

Each `~/.claude/skills/<name>` resolves to `<checkout>/skills/<name>`, and the script ended `live links: ok`.

No symlink was created, and `created-links.txt` is empty. Live re-check (`live_recheck.py`):
- `readlink -f` on the installed ai-kit-spec-execute-superpowers link resolves into this checkout.
- The installed `ai-kit-spec-superpowers.py host-config-audit --snapshot tmp/run-2026-11-23/p41-14/live-hc.json`
  exits 0. The file did not exist before the call. It parses as a JSON object whose keys are exactly the ten
  `HOST_CONFIG_FILES`, and the output has no `audit unavailable` line.
- The audit does not cover config folders moved by `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `XDG_CONFIG_HOME` or
  `OPENCODE_CONFIG_DIR`.

Ledger: `p41-14 install: ok dcea1166...` and `p41-14 live re-check: ok dcea1166...`.

Post-fold runner-version agreement (orchestrator step 3): not run here. It runs after the orchestrator's fold and before
any push. `tmp/run-2026-11-23/p41-14/postfold_check.py` and the exact commands are in
`tmp/run-2026-11-23/p41-14/history-check.md`. A pre-fold dry run on dcea116 exited 1, as expected for unfolded history.
Four commits fail with `outside-config differs, template 13, TEMPLATE_VERSION 13, copy 13`: feat, test and docs(41-07),
and test(41-08) re-record. Every commit from 41-08's bump on passes. The `postfold:` line goes here once the
orchestrator runs it.

## Real-config audit

- Before the suites (marker written just before): `flagged=0`.
- One after-audit covers the suites and the live step together: `flagged=7`. Every path is a host-session path that
  this run's earlier audits also flagged (`logs_2.sqlite` in the p40-12 audits):
  - `~/.claude/plugins/store/cc-plugin-you-should-know_builtin-*.json`
  - `~/.claude/skills/synced/<id>/{.last-complete-round,manifest.json}`
  - `~/.codex/{logs_2.sqlite,logs_2.sqlite-shm,logs_2.sqlite-wal,models_cache.json}`
- The writers were not identified one by one. No suite runs a host CLI on the real home (tripwire, scratch HOMEs), and
  the container has no host mount.
- Final audit, after the tick and SUMMARY commits: `flagged=7`, the same seven paths.
- Noise: `.claude/{backups,file-history,projects,sessions}`.
- No `settings.json` change. "The live step wrote nothing" holds by construction, not by an audit diff: `live_links.py`
  and `live_recheck.py` only call readlink and stat on the real home, and write only under `tmp/`.

## Requirement checklist

Each SPEC Acceptance Criteria item, credited only with what its proof tests:
- One definition each of the pinned-resume and owner-stop paths; the 14 existing evals still pass: 41-01
  `tests/test_adapter_single_definitions.py` (doc contract; rc 0, ran 11).
- The escalation flags decide rounds 4 and 5: 41-02 `tests/test_adapter_escalation_flags.py` (rc 0, ran 32). These are
  the gate unit tests plus the doc block run against a scratch roster. The round itself is doc contract, not an executed
  controller run. Installed layout (a) shows both flags off.
- The fallback flag round-trips and the jev pick works: 41-03 and 41-04, `tests/test_lane_settings.py` (rc 0, ran 58)
  and `tests/test_adapter_session_fallback.py` (rc 0, ran 27). Unit tests with a fake jev; installed layout (e1) and (e2).
- The gate and guard builders and the six requirement-5 items: 41-05 and 41-06, `tests/test_dispatch_guidance_gates.py`
  (rc 0, ran 32) and `tests/test_ai_kit_spec_superpowers.py` (rc 0, ran 182). This proves the print command and the doc
  contract, not an equivalent native brief. Installed layout (b1) and (b2).
- The real-home guard: 41-07 self-test cases `realhome-*` (runner-spawned exec lanes in an ai-kit checkout; the 12
  self-test shards each rc 0) and 41-08 `make check-dogfood`.
- The audit: 41-09 `tests/test_host_config_audit.py` (unit; rc 0, ran 15); installed layout (c1) and (c2).
- The flagged switch, the blocked pool and the unflagged stop: 41-10 and 41-11, `tests/test_adapter_executor_switch.py`
  (rc 0, ran 24). These are unit tests of the subcommand's choice. The fake-flow doc-block tests of
  `tests/test_ai_kit_spec_superpowers.py` cover the switch block's file transitions; the same-round dispatch itself is doc
  contract. Installed layout (d1) to (d3).
- The judge bar: the 41-13 records (three skills `bar met`, fixed under the no-rejudge rule) and the loop 41.1 record for
  spec-config (bar met, `7e49979`); `check-dogfood: ok`.

The new evals of plan 41-12 are transcript-assessed (scored as skill text by plan 41-13's judges), not executed evidence.

## Owner handoffs

1. The `EXEC_PREAMBLE` question (41-SPEC amendment 1: should the runner's exec preamble also name the gates and the
   guard?) was answered by the owner on 2026-11-25: leave it unchanged. GSD executors keep today's brief, and this phase
   did not change the preamble.
2. The open-gsd note (41-SPEC Boundaries, 41-CONTEXT): open-gsd's plan template lacks the gates and a uniform
   commit-guard block. This repo cannot fix that; the note is for the owner and starts no implementation work.
3. Grade A for ai-kit-spec-config: the owner accepted grade B for phase 41 on 2026-11-26 (loop 41.1: referee-one B 86.4,
   referee-three A 92.8). Backlog 999.35 carries the follow-up loop until it reaches A.

## Deviations

- **Plan amended (`dcea116`, docs only, before any suite).** (b1) of the plan expected the guard's clean-tree pathspec
  `':!.aikit/config.toml'`, but the code prints `':(top)' ':(top,exclude,literal).aikit/config.toml'`. Review fix WR-01
  (`16114c4`, 41-REVIEW.md) anchored that pathspec at the checkout top after the plan was written (`1420a53`), and
  `tests/test_dispatch_guidance_gates.py` pins the new text. `rg -F "':!" skills/` finds no skill text that still teaches
  the old form. (d1) of the plan omitted the `exclude` key, which a switched answer carries per
  dispatch-external-cli.md. The layout check asserts the exact pinned sentence and the full d1 answer. The orchestrator
  may veto this amendment.
- `run_suite.py` (copied from p40-13) uses this run's disk lines: stop above 70% on `/tmp` and 75% on `/var/home`.
- `make e2e-docker` ran without `AI_KIT_REFUSE_REAL_HOME=1` exported (as in 40-13). No ai-kit code runs on the host
  there, and the container gets no host mount.
- `live_links.py` is a read-only copy: it reports a missing link and never creates one, since a creation would be a
  real-config write. All links already resolved, so nothing was skipped.
- `live re-check: ok` was recorded while the after-audit showed `flagged=7`. Plan step 2 stops on any flagged write other
  than an authorized link. As in 40-13, the seven known host-session paths were read as host activity, not as a write
  by the live step; this is an orchestrator item.
- Before Task 1, `tmp/run-2026-11-23/p40-13/wait.sh` was started by mistake: a file-wait loop on a file that does not
  exist. It was stopped at once and had no side effect.
- No fold, checkpoint, push, ready or merge step was run, and `phase.complete` was not run. 41-VERIFICATION.md is not
  written here (an orchestrator step).
- The podman image `localhost/ai-kit-e2e` stays in the local image store.

## Self-Check: PASSED
