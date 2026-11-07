---
phase: 32-re-judge-baseline
plan: 09
subsystem: testing
tags: [skill-judge, judge-loop, baseline, rejudge-report, verdict-checker]

# Dependency graph
requires:
  - phase: 32-re-judge-baseline
    provides: 32-08 round-1 staging records (tmp/p32/judge/), tools/judge_loop.py report and check
provides:
  - .planning/judge/REJUDGE.md, the one current-judge report (15 judged, 8 excluded skills)
  - .planning/judge/ raw records: inputs.json, loops/32.json, 31 verdict files, committed byte for byte
affects: [32.1, 32.2, 32.3, 32.4 (each batch phase's regression base is its skill's verdict here)]

# Actuals (#2632)
actuals:
  tokens: 122551   # chars/4 over the 34 committed files (490207 chars); plan estimate was 50000 (low confidence)
  tasks: 2
  commits: 1       # MEASURED: git rev-list --count d5c0f29..HEAD before this SUMMARY commit

tech-stack:
  added: []
  patterns: [byte-for-byte publish of staged records, report generated and never hand-edited, checker run with every judge that ran]

key-files:
  created:
    - .planning/judge/REJUDGE.md
    - .planning/judge/inputs.json
    - .planning/judge/loops/32.json
    - .planning/judge/verdicts/32/ (31 verdict files, one per lane that ingested)
  modified: []

key-decisions:
  - "Publish copied 33 staged files byte for byte; no destination held different bytes, so nothing was refused. The report is the 34th file."
  - "The baseline's regression bases are the 31 committed verdicts; each judged skill's base is its round-1 verdict."
  - "check-dogfood and the commit hooks ran with TMPDIR outside the checkout, not under tmp/p32/09/tmp (deviation 2)."

patterns-established:
  - "The checker reads the skill list from inputs.json and the judge list from the verdict files, so no judge is named by hand."

requirements-completed: [JDG-01, JDG-04]   # recorded here only; REQUIREMENTS.md is owned by the orchestrator

# Metrics
duration: about 40 min (scope start to audit)
completed: 2026-11-07
status: complete

plan_head_before: d5c0f296a26dd5266016a2b58426ff51b1b13ca9
plan_head_after: a073b21f134cc7ff8266b6291fe9062418ad5921
commits: 1
---

# Phase 32 Plan 09: Baseline Re-judge Report Summary

**Baseline re-judge report committed: 15 judged skills (8 bars met, 7 not met) with 31 raw verdicts; `judge_loop.py check` exits 0 with every digest current.**

## Performance

- **Tasks:** 2 (Task 1 committed; Task 2 is an audit with no tracked change)
- **Tracked files changed by this plan:** 34, all under `.planning/judge/`
- **Base:** d5c0f29 (orchestrator fix, made before this plan's tasks); task commit a073b21

## Commits

- `d5c0f29` fix(32-09): show a failed attempt's error in the judge report's lane status cell. Orchestrator change, made before this plan's tasks (deviation 1).
- `a073b21` docs(32-09): baseline re-judge report and raw verdicts. Task 1, 34 files, hooks passed (staged tests: 0 modules).
- Task 2: no tracked change, no commit.

## Task 1: records published, report generated, checker green, one commit

Steps, in order:

0. `scope.py start`, `scope.py selftest` (`selftest ok`), `base_sha` = d5c0f29. Precondition: `lanes.py status` ended with `all lanes ended`; `git status --porcelain --untracked-files=no` was empty.
1. `publish.py`: `published 33 files` (inputs.json, loops/32.json, 31 verdicts).
2. `judge_loop.py report .planning/judge`: `report written` (REJUDGE.md).
3. `check.py`: exit 0 (output below).
4. `make check-dogfood`: `check-dogfood: ok`, no `judge records:` problem line (TMPDIR outside the checkout, see deviation 2).
5. Staged `.planning/judge` only (34 files), reviewed with `git diff --cached --stat`, committed as a073b21. Records scanned for machine paths (`/var/home`, `/home/bazzite`) and key-shaped tokens: none.

### check.py output (`judge_loop.py check --skills <15> --judges <3> --require-current`)

```
skills 15: judges ['native:opus-xhigh', 'opencode:router-env/my-referee-three', 'opencode:router-env/my-referee-two']
judge-loop: ai-kit-cross-ai: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 76.8 C; critical 0; high 1; bar not met; digest current
judge-loop: ai-kit-gsd-curated-config: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 82.4 B; critical 0; high 0; bar met: no critical or high finding; digest current
judge-loop: ai-kit-gsd-spec-discuss: loop 32 round 1 (rounds 1); judges native:opus-xhigh; worst 84.8 B; critical 0; high 0; bar met: no critical or high finding; digest current
judge-loop: ai-kit-session-wake: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, native:opus-xhigh; worst 87.2 B; critical 0; high 1; bar met: grade B or better; digest current
judge-loop: ai-kit-spec-config: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 79.2 C; critical 0; high 0; bar met: no critical or high finding; digest current
judge-loop: ai-kit-spec-execute: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 85.6 B; critical 0; high 1; bar met: grade B or better; digest current
judge-loop: ai-kit-spec-execute-superpowers: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-three, native:opus-xhigh; worst 86.4 B; critical 0; high 0; bar met: no critical or high finding; digest current
judge-loop: ai-kit-spec-goal-prompt: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two; worst 92.8 A; critical 0; high 0; bar met: no critical or high finding; digest current
judge-loop: ai-kit-spec-review: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 75.2 C; critical 0; high 2; bar not met; digest current
judge-loop: ai-kit-spec-review-checklist: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-three, native:opus-xhigh; worst 75.2 C; critical 0; high 2; bar not met; digest current
judge-loop: ai-kit-spec-review-fixer: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 75.2 C; critical 0; high 1; bar not met; digest current
judge-loop: ai-kit-usage-metrics: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 72.0 C; critical 0; high 1; bar not met; digest current
judge-loop: cst-refactor: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 72.8 C; critical 0; high 1; bar not met; digest current
judge-loop: jev-fast-decision: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 87.2 B; critical 0; high 0; bar met: no critical or high finding; digest current
judge-loop: markdown-to-pdf: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, native:opus-xhigh; worst 71.2 C; critical 0; high 2; bar not met; digest current
check exit=0
```

Every skill line ends `digest current`; no `stale`, `differs`, `not judged` or `not in the judge list` line.

## Audit (Task 2): SPEC R7 fields of REJUDGE.md

`audit.py` output (exit 0, no FAIL line):

```
ok judged skills table has 15 rows
ok excluded skills table has 8 rows
ok judged rows equal inputs skills
ok excluded rows equal inputs excluded
ok verdict rows name judge and lane status
ok no-verdict rows show their error
ok substitute reasons
ok five lane failures recorded
ok no old score in judged skills section
ok rubric names version 4 and a spec_sha
ok no live judge worker or probe
```

## Baseline bar results (work list for 32.1-32.4; each verdict is the skill's new base, 32 D-12)

```
ai-kit-spec-review-fixer | batch 32.1 | judges 2 | worst 75.2 C | bar not met
ai-kit-usage-metrics | batch 32.1 | judges 2 | worst 72.0 C | bar not met
cst-refactor | batch 32.1 | judges 2 | worst 72.8 C | bar not met
jev-fast-decision | batch 32.1 | judges 2 | worst 87.2 B | bar met: no critical or high finding
markdown-to-pdf | batch 32.1 | judges 2 | worst 71.2 C | bar not met
ai-kit-spec-config | batch 32.2 | judges 2 | worst 79.2 C | bar met: no critical or high finding
ai-kit-spec-execute | batch 32.2 | judges 2 | worst 85.6 B | bar met: grade B or better
ai-kit-spec-review | batch 32.2 | judges 2 | worst 75.2 C | bar not met
ai-kit-spec-review-checklist | batch 32.2 | judges 2 | worst 75.2 C | bar not met
ai-kit-cross-ai | batch 32.3 | judges 2 | worst 76.8 C | bar not met
ai-kit-session-wake | batch 32.3 | judges 2 | worst 87.2 B | bar met: grade B or better
ai-kit-spec-execute-superpowers | batch 32.3 | judges 2 | worst 86.4 B | bar met: no critical or high finding
ai-kit-gsd-curated-config | batch 32.4 | judges 2 | worst 82.4 B | bar met: no critical or high finding
ai-kit-gsd-spec-discuss | batch 32.4 | judges 1 | worst 84.8 B | bar met: no critical or high finding
ai-kit-spec-goal-prompt | batch 32.4 | judges 1 | worst 92.8 A | bar met: no critical or high finding
```

Bars: 8 met (jev-fast-decision, ai-kit-spec-config, ai-kit-spec-execute, ai-kit-session-wake, ai-kit-spec-execute-superpowers, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-spec-goal-prompt); 7 not met (ai-kit-spec-review-fixer, ai-kit-usage-metrics, cst-refactor, markdown-to-pdf, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-cross-ai). A baseline holds unmet bars by design (D-11); none is a gate failure here.

**D-12 base statement:** the 31 committed round-1 verdicts are the regression bases of the batch phases. Each batch phase compares its skill against that verdict. The older 120-point scores are history and appear only in the report's History section.

## Lane failures in the report

Copied from REJUDGE.md `## Verdicts` (lane = skill and round; judge = the failed judge):

- ai-kit-spec-review-checklist r1 | opencode:router-env/my-referee-two | failed: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=43s out=204525 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0; its not-judged row's Lane status adds `error: finding D5-1 line 156 is beyond the file's 150 lines`
- ai-kit-spec-execute-superpowers r1 | opencode:router-env/my-referee-two | failed: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=56s out=382568 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0; its not-judged row's Lane status adds `error: D3 is below its max but has no finding`
- ai-kit-gsd-spec-discuss r1 | opencode:router-env/my-referee-two | failed: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=57s out=274150 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0; its not-judged row's Lane status adds `error: D3 is below its max but has no finding`
- markdown-to-pdf r1 | opencode:router-env/my-referee-three | failed: ingest refused: judge-loop: verdict judge 'o\u200dpencode:router-env/my-referee-three' is not the lane's judge 'opencode:router-env/my-referee-three' (the zero-width joiner is shown escaped)
- ai-kit-session-wake r1 | opencode:router-env/my-referee-three | failed: ingest refused: judge-loop: verdict judge 'o\u200dpencode:router-env/my-referee-three' is not the lane's judge 'opencode:router-env/my-referee-three' (the zero-width joiner is shown escaped)

Each failed lane has a native substitute (`native:opus-xhigh`, `replaces <judge>: <reason>`). The three referee-two validation failures show `not judged` in the Score column, with no score. The two ZWJ refusals leave no record, so the substitute reason is their only report.

## Judge pool and judge count

- Pool: `opencode:router-env/my-referee-two` and `opencode:router-env/my-referee-three` (both probes usable); no pool-level substitute.
- Count (R4): 13 skills count 2; `ai-kit-gsd-spec-discuss` and `ai-kit-spec-goal-prompt` count 1 (no deterministic trigger, jev `needs_fallback`). Per-skill inputs and reasons are in REJUDGE.md `## Judge count inputs`.

## Report fields (SPEC R7)

- 15 judged skills, 8 excluded skills with reasons.
- Every verdict row names its judge and lane status; every substitute row has a reason.
- No old 120-point score in the Judged skills section.
- Rubric version 4, spec_sha 69ef37e9424c0a7ea9dd2293b559e43ec8176379.
- Every skill: round 1, digest current.

## check-dogfood

- With TMPDIR outside the checkout (`dogfood.sh`, scratch session folder): `check-dogfood: ok`, exit 0, no `judge records:` problem.
- With TMPDIR inside the checkout (`tmp/p32/09/tmp`): FAIL. The no-write guard's child failed `tests.test_curated_config_e2e.TestRealIntegration.test_tracer_against_real_installed_gsd_tools`: `apply-profile` returned `applied: false` (`AssertionError: 1 != 0`). The same test run alone passes with TMPDIR outside the checkout. The tree and the records were identical in both runs; only the temp location changed.

## Scope close result

`scope.py close` did NOT print `clean` (exit 1). The close reported:

- leftover (this run): `pid 320638 cwd tmp/compact-291: sleep 3`. A `sleep 3` loop with a rotating pid (320274 and 320638 in consecutive runs), parent pid 3423848 in the same `tmp/compact-291` folder. This is another session's wait loop; this run started no sleep. It was not killed.
- reported (not this run): other sessions and earlier leftovers (pid 2888315 under `tmp/wt-301`, pid 1834804 for a deleted worktree, codegraph children, pid 2988613 zsh, VS Code processes, `opencode`/codegraph node processes). None was killed.

This run's own scratch: the empty run directory `tmp/p32/09/run-cfa2985b` was removed by hand after the close. The start snapshot, `run_id`, `base_sha` and the scripts stay under `tmp/p32/09/` (ignored, scratch).

## Deviations from Plan

1. **Orchestrator change before this plan's tasks:** commit `d5c0f29` (judge report lane-status error cell, `tools/judge_loop.py` and one unit test) was applied before dispatch; this plan changed no code.
2. **TMPDIR outside the checkout (deviation from orchestrator note 3):** `check-dogfood` and the Task 1 commit hooks ran with TMPDIR set to the session scratch folder, not under `tmp/p32/09/tmp`. Reason: the real-tool integration test fails when its temp project sits inside a repo (A/B above). Not fixed here: the fix belongs to `tests/test_curated_config_e2e.py` or the no-write guard, outside this plan's scope (no `tools/` or `tests/` edits). **Owner decision needed:** make the real-tool tests create their temp project outside any repo, or have `check-dogfood` set TMPDIR itself. Until then, the pre-push check passes only with a temp dir outside the checkout.
3. **Scope close not clean** (see Scope close result): one other-session `sleep 3` loop. Recorded, not killed.
4. **Actuals above the plan estimate:** 122551 tokens against an estimate of 50000 (low confidence). Recorded as measured.

## jev calls

One call (rails: 2-4 option choice). Item `dogfood-tmpdir-choice`, type `choice`, options `inside_checkout` and `outside_checkout`. Payload: a summary of the observed failure and the two rules, no code, skill text or config values. Answer: Laya, `inside_checkout`, top 0.8273, `decided_by: laya`, not forced, advisory. I verified before acting (the A/B run above) and kept the outside-checkout TMPDIR, which overrides the advice; this is deviation 2. The recommendation's rationale ("the check reports failing for a reason outside this plan") is recorded as the alternative: `check-dogfood` would then fail in this plan's own run.

## Threat model

- T-32-22 (publish tampering): mitigated. Byte-for-byte copy with a refusal on differing bytes; the report is generated, not hand-edited; the checker with `--require-current` exits 0 before the commit; check-dogfood ran on the committed records.
- T-32-23 (information disclosure): mitigated. Scan of `.planning/judge/` for `/var/home`, `/home/bazzite` and key-shaped tokens: no matches. Staged list reviewed (34 files, all under `.planning/judge/`).

## Threat Flags

None.

## Known Stubs

None.

## Requirements

- JDG-01 (one committed report): records and report committed; the checker reproduces every number.
- JDG-04 (bar result per skill): every judged skill's bar result is in REJUDGE.md and the table above.
- Not marked complete here: REQUIREMENTS.md is owned by the orchestrator.

## Self-Check

- FOUND: `.planning/judge/REJUDGE.md`, `.planning/judge/inputs.json`, `.planning/judge/loops/32.json`, 31 verdict files under `.planning/judge/verdicts/32/`.
- FOUND: commit `a073b21` is an ancestor of HEAD; `d5c0f29` is its parent.
- `git status --porcelain --untracked-files=no` empty before the SUMMARY; STATE.md, ROADMAP.md and REQUIREMENTS.md untouched (`git status` on those paths empty).
- Self-check: PASSED. The scope close is not clean (see above); it is reported, not hidden.
