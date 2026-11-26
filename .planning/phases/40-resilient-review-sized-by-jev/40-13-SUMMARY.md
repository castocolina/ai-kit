---
phase: 40-resilient-review-sized-by-jev
plan: 13
subsystem: closing-gate
tags: [closing-gate, installed-layout, e2e-docker, check-dogfood, live-links]
requires: [40-12]
provides:
  - "Phase 40 verified on the installed layout and every test tier at 968b3ea; ROADMAP Phase 40 ticked"
affects: []
key-files:
  created: []
  modified:
    - .planning/ROADMAP.md
requirements-completed: [REV-01, REV-02, REV-06, REV-07, REV-08]  # marked by post-plan-p at this plan's SUMMARY commit; JDG-04 was already complete
duration: 20min
completed: 2026-11-25
executor: "orchestrator delegate in the main checkout (cross_ai false), natively"
---

# Phase 40 Plan 13: Closing gate

Commits: `7d8d9c5` docs(40-13): phase 40 complete (ROADMAP.md only). Candidate SHA of the gate:
`968b3ea6f1d76b0e2be6aaac9069ae3e2dc2e596`. No gate fix was needed.

Precondition: 40-12-SUMMARY gives all three judged skills `bar met, then fixed under the no-rejudge rule`
(ai-kit-spec-review `90b3fff`, ai-kit-cross-ai `fbd2ad1`, ai-kit-spec-review-fixer `cdaed6d`). Tree clean at the start.

Unit brief: `.aikit/brief/SKILL.md` names unit phase-40 (point wave, head 7106efbf223a): our unit, read.

## Installed layout

`tmp/run-2026-11-23/p40-13/layout_check.py` on 968b3ea. Isolation from the test runner itself:
`run_unittest_parallel.write_tripwire` and `baseline_env` (scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`), PATH = the stubs plus a
`python3` link only. `ai-kit-spec-review`, `-checklist`, `-fixer` and `ai-kit-cross-ai` symlinked under the scratch
`.claude/skills/`; synthetic runtime cache checked fresh before the first command. `<layout>` =
`tmp/run-2026-11-23/p40-13/layout`:

```
check-fold-step (superpowers): exit 0: - **Plan has no fold step** — Location: <layout>/project/docs/superpowers/plans/plan.md, last ### Task. Required: ...
check-fold-step (none): exit 0: <empty stdout>
merge-reports (partial): exit 0: ### Status: Approved (partial) | Judged by: a; not judged: b (never_resolved)
  lanes.jsonl new events: [('b', 'never_resolved'), ('a', 'judged')]
merge-reports (extra findings): exit 0: ### Status: Issues Found — fix and re-invoke
merge-reports (no --cwd): exit 2: merge-reports: --lane-log needs --round <N >= 1> and --cwd
size-review: exit 0: sizing: 2 lane(s): signal security
ping-lanes (native): exit 0: ping session-default: ok
switch-lane: exit 1: not switched session-default: chosen
classify-disagreements: exit 0: {"jev": "not needed", "owner": [], "fixer": [], "skipped": []}
ping-lanes (empty): exit 3: ai-kit-spec: no lane left: (empty reviewers file)
tripwire calls: 0
scratch gone: True
layout: ok
```

The (a) first line was `### HIGH`; the merge printed no plain `### Status: Approved`; `size.jsonl` held one round-0 event
with a `sizing` object; `native.json` bytes were unchanged after `switch-lane`.

## Closing suites

Each suite ran once, one at a time, natively under `orch-guard.py` (process groups in `pgids.txt`, tag `close40`).
Before each suite `/tmp` was at 39.84% and `/var/home` at 69.35%, 69.35% and 69.49%.

- `make test` (make_test.sh, `AI_KIT_TEST_REPORT_DIR=.../reports-968b3ea6...`, a new folder):
  `exit 0 peak_runner_procs 8 killed: no`.
  - unit `197/197 modules passed`; unit-uv `3/3 modules passed`.
  - integration `9/9 modules passed`, with `=== tests.test_wizard_pty: ok in 18.3s  Ran 14 tests in 18.233s`.
  - e2e `29/29 modules passed` (12 runner self-test shards, each rc 0 ran 1); installer `48 passed, 0 failed`;
    arch `3/3 modules passed`.
- `make e2e-docker` (podman): `exit 0 peak_runner_procs 0 killed: no`.
  - In the container: `197/197`, `3/3`, `=== tests.test_wizard_pty: ok in 23.7s`, `9/9`, `29/29`, `48 passed, 0 failed`,
    `3/3`, lint passed, `==> ai-kit clean-room E2E: PASS`.
  - The image has no Node: `tests.test_ai_kit_gsd_spec_discuss_e2e` reads `Ran 6 tests in 0.000s` there, so
    `TestRealBranchPreflight` was skipped inside the clean room. That is a clean-room skip, not a pass. The case ran in
    `make test` (evidence below).
- `make check-dogfood` (dogfood.sh): `exit 0 peak_runner_procs 0 killed: no`;
  `check-dogfood: no-write guard: 3 attempted, 3 executed, 0 skipped`; `check-dogfood: ok`
  (`rg -c "check-dogfood: ok" dogfood.log` = 1). The 13 stale-digest lines are informational: the three phase-40 skills
  are stale by design, and ai-kit-spec-review-checklist has not changed since 39.2.

Execution evidence (`evidence.txt`, from the 241 per-module reports of the one `make test` run):

```
reports: 241 modules (reports-968b3ea6f1d76b0e2be6aaac9069ae3e2dc2e596)
tests.test_review_log: rc 0 ran 16 skips []
tests.test_lane_ping: rc 0 ran 34 skips []
tests.test_lane_switch: rc 0 ran 30 skips []
tests.test_jev_review: rc 0 ran 31 skips []
tests.test_review_signals: rc 0 ran 11 skips []
tests.test_fold_check: rc 0 ran 18 skips []
tests.test_lane_failure_text: rc 0 ran 31 skips []
tests.test_ai_kit_spec_e2e: rc 0 ran 4 skips []
tests.test_cross_ai_runner_e2e: rc 0 ran 28 skips []
tests.test_wizard_pty: rc 0 ran 14 skips []
tests.test_ai_kit_gsd_spec_discuss_e2e: rc 0 ran 6 skips 0 TestRealBranchPreflight skips 0
non-zero rc modules: none
evidence: ok
```

Allowed skips (none in the modules above): tests.test_ai_kit_gsd_curated_config_matrix (`no cached pi package; ...`,
`node or cached installer package is missing`); tests.test_ai_kit_project_rules_docker (`HOT_RELOAD_BASELINE_GAPS is
empty ...`); tests.test_ai_kit_spec (`owner capture pending: 22-INTERACTIVE-PI.md C1 ...`); tests.test_curated_config_e2e
(2, `checkout-local gsd-core is 1.22.0; gsd_tables_1_16.json pins 1.16.0`); tests.test_hook_registry (x2) and
tests.test_setup (x38), `textual not installed (run under uv)` (the uv tier runs them).

HEAD equaled `candidate.txt` after the last suite; `git status --porcelain` was empty.

## Ship order

Installer dry run, `tmp/run-2026-11-23/p40-13/dryrun.py` (`tools/install.sh install --headless --dry-run --skills=all
--with-hooks --examples=none`, every config root under a scratch HOME):

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

This phase adds no hook: `git diff --stat gsd/phase-39.2-... HEAD -- tools/hooks tools/setup.py` prints nothing.

Judged digests (orchestrator step 1): `judge_loop.py check .planning/judge --skills ai-kit-cross-ai ai-kit-spec-review
ai-kit-spec-review-fixer --require-current` exited 1. Its only problem lines are the three `stale digest` lines, and all three
skills read `bar met: grade B or better`. For `fbd2ad1`, `90b3fff` and `cdaed6d`, `merge-base --is-ancestor` exits 0 and
`git log <fix>..HEAD -- skills/<skill>/` prints nothing, so all three are stale by design. Ledger: `judged digests: ok 968b3ea6...`.

Live install (orchestrator step 2, link-only). HEAD, the unit-branch tip and `candidate.txt` were all 968b3ea6 before the
step. `tmp/run-2026-11-23/p40-13/live_links.py`:

```
ok ai-kit-spec-review: ~/.claude/skills/ai-kit-spec-review -> <checkout>/skills/ai-kit-spec-review (no write)
ok ai-kit-spec-review-fixer: ~/.claude/skills/ai-kit-spec-review-fixer -> <checkout>/skills/ai-kit-spec-review-fixer (no write)
ok ai-kit-cross-ai: ~/.claude/skills/ai-kit-cross-ai -> <checkout>/skills/ai-kit-cross-ai (no write)
ok ai-kit-spec-review-checklist: ~/.claude/skills/ai-kit-spec-review-checklist -> <checkout>/skills/ai-kit-spec-review-checklist (no write)
live links: ok
```

No symlink was created. Live re-check: `readlink -f` on all four links resolves into this checkout, and the installed
`ai-kit-spec.py check-fold-step --doc <checkout>/tests/fixtures/fold_step/without_fold.md --framework superpowers
--archetype plan` prints `### HIGH` and the `Plan has no fold step` finding. Ledger: `p40-13 install: ok 968b3ea6...` and
`p40-13 live re-check: ok 968b3ea6...`.

## Real-config audit

- Before the suites (marker written just before): `flagged=3`, `~/.codex/{logs_2.sqlite-shm,logs_2.sqlite-wal,models_cache.json}`.
- After the suites, and again after the live step: `flagged=8`.
  - `~/.claude/settings.json`, mtime 20:30:06. The writer is NOT identified, but it was not a suite of this run. Only
    `make e2e-docker` was running at that time (20:28:18 to 20:31:26), and its `podman run --rm ai-kit-e2e` mounts no
    host path. The mtime did not change across the live step. This needs owner attention.
  - Known host-session paths: `~/.claude/plugins/store/cc-plugin-{diff,you-should-know}_builtin-*.json`,
    `~/.claude/skills/synced/<id>/{.last-complete-round,manifest.json}`, `~/.codex/{logs_2.sqlite-shm,logs_2.sqlite-wal,models_cache.json}`.
  - Noise: `.claude/{backups,cache,file-history,projects,sessions}`.
  - The live step wrote nothing.
- Final audit, after the tick and SUMMARY commits: `flagged=10`. It holds the same eight paths, plus
  `~/.claude/jobs/892a2729/{state.json,timeline.jsonl}` (20:38, host job state, seen before in this run). `settings.json` was
  still at 20:30:06.

## Requirement checklist

SPEC Acceptance Criteria, each with its proof:
- Flagged lane on quota replaced by `lane_fallback`, unflagged failure not replaced: 40-03 `tests/test_lane_switch.py`
  (rc 0, ran 30, no skip); installed layout (e): a native row is never switched.
- Blocked pool skipped at selection, tried once after its time: 40-04, 40-05 `tests/test_lane_switch.py`,
  `tests/test_lane_ping.py`, `tests/test_role_orders.py`.
- Narrowed hard rule pinned, old blanket wording fails: 40-09 `tests/test_lane_failure_text.py` (rc 0, ran 31).
- Concurrent ping before round 1, only blocked lanes replaced, no lane left stops with a reason: 40-02
  `tests/test_lane_ping.py` (rc 0, ran 34); installed layout (d) and (g).
- A lane that answered last round is not pinged again, a failed one is: 40-02 `tests/test_lane_ping.py`.
- Reason-list lock: 40-01 `tests/test_ai_kit_spec.py` and 40-09 `tests/test_lane_failure_text.py`.
- Partial report names the judged lanes, `Approved (partial)`, one failure keeps the other result: 40-01
  `tests/test_review_log.py` (rc 0, ran 16), `tests/test_ai_kit_spec.py`; installed layout (b).
- jev classification of escalated, skipped and cap-open findings, never closing CRITICAL/HIGH, no-jev message: 40-06
  `tests/test_jev_review.py` (rc 0, ran 31); installed layout (f).
- Sizing (signals force two lanes, jev sizes within the roster and logs why, no jev keeps the count): 40-07
  `tests/test_review_signals.py` (rc 0, ran 11), `tests/test_jev_review.py`; installed layout (c).
- Fold-step HIGH finding with `Required:` for superpowers plans, none with the step or for other frameworks: 40-08
  `tests/test_fold_check.py` (rc 0, ran 18); installed layout (a) and the live re-check.
- Every changed SKILL.md meets the judge bar: 40-12 records (three skills `bar met`, fixed under the no-rejudge rule;
  `check-dogfood: ok`).

The new evals of plan 40-11 are transcript-assessed (scored as skill text by plan 40-12's judges), not executed evidence.

## Deviations

- `run_suite.py` (new, under the run folder) wraps `orch-guard.py`: a disk check (stop above 70.0%), the pgid lines, the
  `<name>.guard` file and the stripped count and tail lines. orch-guard itself writes no `pgids.txt` line.
- `make e2e-docker` ran as `make -C <checkout> e2e-docker` without `AI_KIT_REFUSE_REAL_HOME=1` exported. No ai-kit code
  runs on the host there, and the container gets no host mount.
- `evidence.py` also checks `tests.test_ai_kit_spec_e2e`, `tests.test_cross_ai_runner_e2e` and `tests.test_wizard_pty` (plan
  step 2b) and reads `reports-<candidate SHA>`. `shards.py` confirmed the 12 self-test shards.
- Ledger: `ledger_add_tag.py` puts the tag in brackets, so the install and re-check lines read `- <time> [close40] p40-13 install: ok <SHA> ...`.
- No fold, checkpoint, push or ready step was run (the orchestrator does those after verification). 40-VERIFICATION.md is
  not written here (orchestrator step).
- The podman image `ai-kit-e2e` stays in the local image store.

## Self-Check: PASSED
