---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 12
subsystem: closing-gate
tags: [closing-gate, installed-layout, e2e-docker, check-dogfood, live-links]
requires: [42-11]
provides:
  - "Phase 42 verified on the installed layout and every test tier at d328601; the ROADMAP Phase 42 tick is left to the orchestrator's phase completion"
affects: []
key-files:
  created:
    - .planning/phases/42-code-review-after-execution-and-jev-picked-executors/42-12-SUMMARY.md
  modified:
    - .planning/phases/42-code-review-after-execution-and-jev-picked-executors/42-12-PLAN.md
requirements-completed: [EXE-02, EXE-03, EXE-06, EXE-07, LENS-02]  # marked in this plan's SUMMARY fix commit; JDG-04 was already complete; EXE-06 carries the 2026-11-27 spike-skip amendment
duration: 20min
completed: 2026-11-27
executor: "orchestrator delegate in the main checkout (cross_ai false), natively"
---

# Phase 42 Plan 12: Closing gate

Commits: `d328601` docs(42-12), the plan amendment below; this SUMMARY commit. Candidate SHA of the gate:
`d3286019e08e0e4f155012988ba78a5fbe64f395`. No code fix was needed.

Precondition: 42-11-SUMMARY gives the one judged skill, ai-kit-spec-execute-superpowers, `bar met, then fixed under the
no-rejudge rule` (`b9aa7b3`). The tree was clean at the start (HEAD `f09cdb9`).

Unit brief: `.aikit/brief/SKILL.md` names unit phase-42 (point wave, head 5d32b7957387). It is our unit's brief and was
read.

## Installed layout

`tmp/run-2026-11-23/p42-12/layout_check.py` on d328601. Isolation comes from the test runner itself:
`run_unittest_parallel.write_tripwire` and `baseline_env` (scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`, `HERDR_ENV`
unset). The child PATH holds the stubs plus `python3` and `git` links only. `ai-kit-spec-execute-superpowers`,
`ai-kit-spec-review`, `ai-kit-spec-config` and `ai-kit-cross-ai` are symlinked under the scratch `.claude/skills/`. The
synthetic runtime cache is seeded fresh (codex installed with both placeholder models, current runner fact) and checked
with `routing.runtimes_cache_is_fresh`. The scratch project's config holds one execute lane `lane-a` (codex,
`fake/placeholder-model-1`). The flag sets were read from the real parsers (`_build_parser` of the adapter CLI,
`register_parsers` of `code_review` and `jev_review`) and compared before the run. Invocation (e) runs a copied, not
linked, `ai-kit-spec-review` folder; `jev_names.find_jev` on its real sibling root and the scratch HOME found no jev.

```
flags lite-block: parser required ['--cwd']; passed ['--cwd']: match
flags close-transports: parser required ['--transport-record']; passed ['--transport-record']: match
flags code-review-verdict: parser required ['--report', '--round']; passed ['--report', '--round']: match
flags code-review-paths: parser required ['--base', '--cwd', '--head']; passed ['--base', '--cwd', '--head']: match
flags classify-execute-result: parser required ['--cwd', '--status']; passed ['--cwd', '--status']: match
jev: absent
a lite-block: exit 0: {"lite": false, "key": "lane-a", "decided_by": "default", "path": null, "removed_stale": false} | lite-executor.md exists False | SKILL.md unchanged True
b close-transports: exit 0: {"closed": [], "failed": [], "busy": [], "sweep": "skipped: no transport record"}
c code-review-verdict --round 1: exit 1: state fix blocking 1 listed 0
c2 code-review-verdict --round 3: exit 3: state cap_stop blocking 1 listed 0
c3 code-review-verdict --round 1: exit 0: state pass blocking 0 listed 1
d code-review-paths: exit 0: ["d.py", "e.py"]
e classify-execute-result: exit 0: ai-kit-spec: lane result: partial (default) | note 'not a DONE report'
tripwire calls: 0
scratch gone: True
layout: ok
```

- (a) also asserts `key` `lane-a`, so the lane routed and was not skipped. (b) also asserts no `.lock` file beside the
  missing record. (d) runs on a scratch repo: `a.py`, `b.py`, `c.py` committed, then `d.py` added, `b.py` renamed to
  `e.py`, `c.py` deleted; the deleted file is dropped and the renamed one appears under its new name.
- (e) shows the status default: `classify_execute_result` returns before any jev lookup for a report other than DONE
  (note `not a DONE report`). jev absence is shown by the `jev: absent` line, not by (e).
- Scope check (`scope_check.py`, base = the parent of the commit that added 42-01-PLAN.md): `scope: ok 96 files (base
  9450ff62a6b8)`. No path is under `.claude/agents/`, `.claude/gsd-core/`, `.claude/commands/`, `.claude/skills/gsd-` or
  `skills/ai-kit-commit-fold/`, and none contains `superpowers/skills/`.

## Closing suites

Each suite ran once, one at a time, natively under `orch-guard.py`, through `run_suite.py`. Process groups are in
`pgids.txt`, tag `gate42`; each suite's record (command, exit code, count lines, last 20 lines) is in
`tmp/run-2026-11-23/gate-42/<name>.record.txt`. Before each suite `/tmp` was at 28.15% and the run tmpdir on
`/var/home` at 57.45%, 57.48% and 57.65%.

- `make test` (make_test.sh, `AI_KIT_TEST_REPORT_DIR=.../reports-d3286019...`, a new folder):
  `exit 0 peak_runner_procs 8 killed: no`.
  - unit `208/208 modules passed`; unit-uv `3/3 modules passed`.
  - integration `9/9 modules passed`, with `=== tests.test_wizard_pty: ok in 18.3s  Ran 14 tests in 18.220s`.
  - e2e `30/30 modules passed`; installer `48 passed, 0 failed`; arch `3/3 modules passed`.
- `make e2e-docker` (podman, image rebuilt): `exit 0 peak_runner_procs 0 killed: no`.
  - In the container: `208/208`, `3/3`, `=== tests.test_wizard_pty: ok in 24.3s`, `9/9`, `30/30`, `48 passed, 0 failed`,
    `3/3`, lint passed, `==> ai-kit clean-room E2E: PASS`.
  - New image `localhost/ai-kit-e2e`: id `80be6fa86046...`, 1666436674 bytes. It stays in the store for the orchestrator.
  - The image has no Node, so `tests.test_ai_kit_gsd_spec_discuss_e2e` reads `Ran 6 tests in 0.000s` there:
    `TestRealBranchPreflight` was skipped inside the clean room. That is a clean-room skip, not a pass; the case ran in
    `make test` (evidence below).
- `make check-dogfood` (dogfood.sh): `exit 0 peak_runner_procs 0 killed: no`;
  `check-dogfood: no-write guard: 3 attempted, 3 executed, 0 skipped`; `check-dogfood: ok`
  (`rg -c "check-dogfood: ok" dogfood.log` = 1). The 13 stale-digest lines are informational;
  ai-kit-spec-execute-superpowers is stale by design after its loop-42 no-rejudge fix.

Execution evidence (`evidence.txt`, from the 253 per-module reports of the one `make test` run; the shard set is
declared from `SHARD_COUNTS` `{'logic': 5, 'runtime': 7}`):

```
tests.test_code_review: rc 0 ran 70 skips []
tests.test_executor_pick: rc 0 ran 27 skips []
tests.test_lane_transport: rc 0 ran 93 skips []
tests.test_herdr_pane: rc 0 ran 42 skips []
tests.test_herdr_pane_sweep_e2e: rc 0 ran 1 skips []
tests.test_jev_review: rc 0 ran 64 skips []
tests.test_lens_delivery: rc 0 ran 11 skips []
tests.test_lane_settings: rc 0 ran 63 skips []
tests.test_adapter_single_definitions: rc 0 ran 11 skips []
tests.test_ai_kit_spec_superpowers: rc 0 ran 217 skips []
tests.test_spec_config_flow_text: rc 0 ran 43 skips []
tests.test_lite_block: rc 0 ran 17 skips []
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
allowed skip: tests.test_ai_kit_gsd_curated_config_matrix: no cached pi package; pass --installer-dir to the matrix (x1)
allowed skip: tests.test_ai_kit_gsd_curated_config_matrix: node or cached installer package is missing (x1)
allowed skip: tests.test_ai_kit_project_rules_docker: HOT_RELOAD_BASELINE_GAPS is empty -- no stack has a deliberately-empty marker tuple today, so 'stack_without_baseline' cannot be reached via a real detected stack yet. (x1)
allowed skip: tests.test_ai_kit_spec: owner capture pending: 22-INTERACTIVE-PI.md C1 writes this fixture (x1)
allowed skip: tests.test_curated_config_e2e: checkout-local gsd-core is 1.22.0; gsd_tables_1_16.json pins 1.16.0 (x1)
allowed skip: tests.test_curated_config_e2e: fixture not re-validated: checkout-local gsd-core is 1.22.0; gsd_tables_1_16.json pins 1.16.0 (x1)
allowed skip: tests.test_hook_registry: textual not installed (run under uv) (x2)
allowed skip: tests.test_setup: textual not installed (run under uv) (x38)
evidence: ok
```

The block omits only the first two lines of `evidence.txt` (`reports: 253 modules (...)` and `declared shards:
SHARD_COUNTS {'logic': 5, 'runtime': 7} -> 12 modules`).

HEAD equaled `candidate.txt` after the last suite, and `git status --porcelain` was empty.

## Ship order

Installer dry run, `tmp/run-2026-11-23/p42-12/dryrun.py` (`tools/install.sh install --headless --dry-run --skills=all
--with-hooks --examples=none`, every config root under a scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`):

```
skipped Claude Code hook rows — no claude dir
skipped tool-advisor for pi — no pi dir
skipped tool-reminder for pi — no pi dir
headless summary: 23 linked, 0 relinked, 0 foreign-skipped, 0 real-skipped
(dry-run — no changes were made)
==> local checkout — skipping fetch (<checkout>)
dryrun rc 0
scratch HOME entries before/after: 0 0
dryrun: ok
scratch gone: True
```

This phase adds no hook: `git diff --stat 7af5a8a HEAD -- tools/hooks tools/setup.py` prints nothing.

Judged digests (orchestrator step 1, `digests.sh`, run by this delegate): `judge_loop.py check .planning/judge --skills
ai-kit-spec-execute-superpowers --require-current` exited 1. Its only problem line is `stale digest`; the loop line reads
`loop 42 round 1 ... worst 84.0 B; critical 0; high 3; bar met: grade B or better; lowest percent 84.0, loop 41 base
84.0`. The no-rejudge fix `b9aa7b3` adds `verdicts/42/ai-kit-spec-execute-superpowers/r1/fixes.md`,
`merge-base --is-ancestor b9aa7b3 <candidate>` exits 0, and `git log b9aa7b3..<candidate> --
skills/ai-kit-spec-execute-superpowers/` prints nothing. Ledger: `judged digests: ok d3286019...`.

Live install (orchestrator step 2, read-only, run by this delegate). HEAD, the unit-branch tip and `candidate.txt` were
all d3286019. `live_links.py` printed `ok ... (no write)` for ai-kit-spec-execute-superpowers, ai-kit-spec-review,
ai-kit-spec-config, ai-kit-cross-ai and (read-only) ai-kit-gsd-curated-config, then `live links: ok`. No link was
created; `created-links.txt` is empty. Live re-check (`live_recheck.py`): `readlink -f` on the installed adapter link
resolves into this checkout; the installed shim's `close-transports --transport-record
tmp/run-2026-11-23/p42-12/live-none.json` (absent) exits 0 with `{"closed": [], "failed": [], "busy": [], "sweep":
"skipped: no transport record"}` and creates neither the record nor a lock. Ledger: `p42-12 install: ok d3286019...` and
`p42-12 live re-check: ok d3286019...`.

Post-fold runner-version agreement (orchestrator step 3): `postfold: not needed (no template change)`.
`git diff --name-only 7af5a8a HEAD -- skills/ai-kit-spec-review/references/cross-ai.mjs .planning/scripts/cross-ai.mjs`
prints nothing (7af5a8a is the unit base, the phase-41 tip).

## Real-config audit

- Before the suites (marker written just before): `flagged=0`.
- One after-audit covers the suites and the live step together: `flagged=6`, all host-session paths that this run's
  earlier audits also flagged (loop 42 r1 audits):
  - `~/.claude/plugins/store/cc-plugin-you-should-know_builtin-*.json`
  - `~/.claude/skills/synced/<id>/{.last-complete-round,manifest.json}`
  - `~/.codex/{logs_2.sqlite-shm,logs_2.sqlite-wal,models_cache.json}`
- None is one of the five checked skill links, and no `settings.json` changed. Noise: `.claude/{backups,projects,
  sessions}`, `.pi/agent/sessions`. The writers were not identified one by one; no suite runs a host CLI on the real home
  (tripwire, scratch HOMEs) and the container has no host mount. The live step only calls readlink, stat and the
  no-record close on the real home, and writes only under `tmp/`.
- Final audit, after the SUMMARY and state commits: `flagged=6`, the same six paths.

## Requirement checklist

Each SPEC Acceptance Criteria item, credited only with what its proof tests:
- Review loop: a HIGH fixed in round 1 passes in round 2, a never-clearing review stops at round 3, MEDIUM and LOW never
  block. 42-04 `tests/test_code_review.py` verdict transitions (`test_empty_report_passes_round_one`,
  `test_high_fixed_in_round_one_passes_in_round_two`, `test_clears_exactly_in_round_three`,
  `test_never_clearing_stops_at_round_three`, `test_medium_and_low_never_block`; unit; rc 0, ran 70). Fake-lane
  transitions of 42-05, `tests/test_ai_kit_spec_superpowers.py` `class TestCodeReviewTransitions`: the committed 42-05
  SUMMARY names the class but no test ids, so the ids are taken from the tree: `test_high_fixed_before_round_two_passes_in_round_two`,
  `test_lanes_are_fitted_before_the_merge`, `test_fit_failure_falls_back`, `test_clean_round_three_passes`,
  `test_cap_stop_at_round_three`, `test_a_moved_head_after_the_cap_stop_offers_a_fresh_review`,
  `test_an_unmoved_head_keeps_the_cap_stop_and_the_accept`, `test_failed_sibling_gives_a_partial_report`,
  `test_incomplete_lane_report_is_a_failed_lane`, `test_resume_ignores_a_stale_exit`. They run the published bash blocks
  through a `TOOLS_PY` wrapper that calls the real CLI main, with a run seam that refuses every jev call for
  `classify-findings` and `classify-disagreements`; those are the only jev-reaching subcommands the blocks of
  `references/code-review.md` call (`rg 'TOOLS_PY" <subcommand>'` finds no `size-review` or `classify-execute-result`),
  so no real jev runs. Fold restart on an equal tree with a different
  commit id: `class TestFoldStep` `test_same_tree_rewrite_still_folds` (named in the 42-05 SUMMARY). Doc contract:
  `class TestCodeReviewStep`. The loop itself is not an executed controller run. Installed layout (c), (c2), (c3).
- jev classifies gray areas and lane results, no jev falls back and the log says which decided: 42-04 and 42-06
  `tests/test_jev_review.py` (unit, fake jev; rc 0, ran 64). Installed layout (e) shows the logged default (`partial
  (default)`) for a DONE_WITH_CONCERNS report; jev absence itself is the layout's `jev: absent` line.
- Lenses: 42-04 `tests/test_code_review.py` `class TestReviewPaths` and `class TestMissingLenses` (changed paths and
  missing lenses; unit) beside the lens selection of `tests/test_lens_delivery.py` (rc 0, ran 11). Installed layout (d).
- Executor pick: 42-02 `tests/test_executor_pick.py` (unit, fake jev; rc 0, ran 27).
- Lite block: 42-03 `tests/test_lite_block.py` (rc 0, ran 17) and installed layout (a) (one lane, no lite pick, brief
  bytes unchanged). The lite block's effect on a lite model is unverified by design. Scope check: no third-party file.
- Spike record: none. The owner skipped the resume spike on 2026-11-27; 42-01 records the skip as SPEC amendment 13 and
  backlog Phase 999.36. Every resume label stays unverified. Evidence kind: recorded decision, never a run.
- Transport: 42-07, 42-08, 42-09 `tests/test_lane_transport.py` (rc 0, ran 93) and `tests/test_herdr_pane.py` (rc 0,
  ran 42): unit, fake herdr and clock, no live pane. Runner boundary of pane rounds: 42-08 `tests/test_herdr_pane.py`
  `class TestPaneBoundary` and `tests/test_arch.py` `check_pane_round_boundary` with its non-vacuity test
  `test_pane_round_boundary_flags_direct_rounds` (every pane round is one `run_runner` call; unit plus arch). 42-08
  `tests/test_herdr_pane_sweep_e2e.py` `test_sweep_closes_the_pane_leftover` (e2e: the real runner's `--sweep` closes a
  `herdr_pane` leftover; fake herdr). The committed 42-09 SUMMARY names only
  `test_a_lane_log_record_never_opens_a_pane` (and says it ends with a vacuous assertion; the `opened == []` check
  carries the proof); the other ids below come from the tree:
  - Review-lane record default: `TestDispatchReviewerTransport.test_lane_log_writes_transport_json_beside_it`
    (`dispatch-reviewer` with `--lane-log` and no `--transport-record` keeps `transport.json` beside the lane log) and
    `TestPaneThroughDispatchReviewer.test_a_lane_log_record_never_opens_a_pane`.
  - Record lock: `TestRecordRefusal.test_the_record_lock_has_one_implementation` (the source holds exactly one
    `fcntl.LOCK_EX` site), `TestLockedUpdate.test_none_update_removes_the_record_and_keeps_the_lock` and
    `TestCloseTransports.test_one_closed_pane_removes_the_record_and_keeps_the_lock`. These pin the single lock site and
    the kept `<record>.lock`; no test races two writers.
  - Busy-pane rule: `TestPaneRunner.test_a_live_busy_pid_falls_back_and_stays` (a busy pane with a live `busy_pid`
    sends that round to a subprocess; the fallback's `end_round` leaves the owner's `busy_pid`),
    `TestBeginEndRound.test_busy_mark_rules` (`end_round` clears only its own `busy_pid`) and
    `TestCloseTransports.test_a_live_busy_pid_is_listed_busy_and_not_closed` (`close_record` skips a live busy pane).
  This is the pane-ownership evidence; the runner's exec lock proves only one execute child per plan. Installed layout
  (b) and the live re-check.
- Judge bar: 42-11 records (ai-kit-spec-execute-superpowers loop 42 r1, B 84.0 and B 87.2, bar met, three highs fixed
  under the no-rejudge rule `b9aa7b3`); `check-dogfood: ok`; judged digests ok.

The four new evals of plan 42-10 (`precise-code-review-loop-caps-at-three`, `precise-executor-pick-logs-why`,
`edge-lite-block-only-for-lite-pick`, `edge-transport-subprocess-without-verified-resume`) and the four changed ones
(`precise-fold-after-review`, `precise-start-before-first-task`, `precise-no-config-once-native`,
`edge-no-way-to-ask-notice`) are transcript-assessed, not executed evidence. Running all eight on a fresh world at the
candidate SHA is the orchestrator's verification-time work (orchestrator Step 4) and gates the ROADMAP tick.

## Owner handoffs

1. The skipped resume spike (42-SPEC amendment 13, 42-01): now backlog Phase 999.36. Every resume label stays unverified
   until it runs with the owner's chosen authentication.
2. A herdr pane stays unverified (`lane_transport.PANE_LABEL` reads `unverified`) until a recorded live run flips it
   (42-08, 42-09).
3. The lite block's effect on a lite model is unverified (42-03, `references/lite-block.md`).
4. Record lock coverage (42-09, plan 42-12 requirement checklist): the tests pin a single `fcntl.LOCK_EX` site and the
   kept `<record>.lock`, but no test proves every read-modify-write holds the lock or races two writers; whether that is
   enough is the owner's call.

## Deviations

- **Plan amended (`d328601`, docs only, before any suite).** Installed layout (b) expected
  `{"closed": [], "failed": [], "sweep": "skipped: no transport record"}`, but `lane_transport.close_record` also returns
  `"busy": []`. 42-09's `6b3e335` added that key after this plan was written, and `tests/test_lane_transport.py`
  `test_a_missing_record_skips_the_sweep_and_creates_no_lock` pins it. The check asserts the full pinned answer. The
  orchestrator may veto this amendment.
- Scratch: the plan names `tmp/run-2026-11-23/p42-12/` (scripts, logs, reports, candidate); the brief named
  `tmp/run-2026-11-23/gate-42/`, which holds the per-suite records.
- `run_suite.py` (copied from p41-14) uses this run's disk lines (stop above 70% on `/tmp`, 75% on `/var/home`), tags
  its process groups `gate42`, and fails a suite with no count line, a failing count line or `NO TESTS RAN`.
- Orchestrator steps 1 to 3 were run by this delegate in their read-only forms, as at the phase-41 gate; 42-VERIFICATION.md,
  the eight evals, the ROADMAP tick and `phase.complete` are left to the orchestrator.
- `make e2e-docker` ran without `AI_KIT_REFUSE_REAL_HOME=1` exported (as in 41-14). No ai-kit code runs on the host
  there, and the container gets no host mount. The podman image `localhost/ai-kit-e2e` stays in the local image store.
- Post-plan state steps ran after the SUMMARY commit `6664f75` (which holds only this file, parent = the candidate) as
  `038d1cd` docs(42): advance-plan (last plan, ready for verification), metric, session, and ROADMAP plan-progress rows
  only (12/12, the 42-12 plan box, the progress table); the `- [ ] **Phase 42:` line is untouched. The requirement marks
  were added afterwards with this SUMMARY fix (all six ready; EXE-06 carries the spike-skip amendment).
- The podman rebuild moved the `ai-kit-e2e` tag; phase 41's image `cd16ec7d010d` is untagged and still in the store.
- No fold, checkpoint, push, ready or merge step was run.

## Self-Check: PASSED
