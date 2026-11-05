---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 14
subsystem: testing
tags: [evals, skill-judge, trigger-queries, commit-fold, spec-discuss, jev]

# Dependency graph
requires:
  - phase: 29-11
    provides: "the spec-discuss SKILL.md and references the spec-discuss evals are written against"
  - phase: 29-12
    provides: "the commit-fold SKILL.md the fold evals are written against"
  - phase: 29-08
    provides: "tests/test_skill_evals_shape.py, the generic shape check every evals/evals.json must pass"
provides:
  - "ai-kit-commit-fold evals: six output evals and 20 trigger queries (10 should-trigger, 10 near-miss)"
  - "ai-kit-gsd-spec-discuss evals: six output evals and 20 trigger queries (10 should-trigger, 10 near-miss)"
  - "synthetic input files for both skills, each named by at least one eval"
affects: [29-16]

# Actuals (chars/4 over the ten changed files, 18114 bytes)
actuals:
  tokens: 4528
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns: [eval input files under evals/files/ named by evals, one jev call per item with JEV_BACKEND pinned to laya]

key-files:
  created:
    - skills/ai-kit-commit-fold/evals/evals.json
    - skills/ai-kit-commit-fold/evals/trigger-queries.json
    - skills/ai-kit-commit-fold/evals/files/gsd-plan/07-01-PLAN.md
    - skills/ai-kit-commit-fold/evals/files/git-log-07-01.txt
    - skills/ai-kit-commit-fold/evals/files/superpowers-plan.md
    - skills/ai-kit-commit-fold/evals/files/report-refused.txt
    - skills/ai-kit-gsd-spec-discuss/evals/evals.json
    - skills/ai-kit-gsd-spec-discuss/evals/trigger-queries.json
    - skills/ai-kit-gsd-spec-discuss/evals/files/roadmap-analyze.json
    - skills/ai-kit-gsd-spec-discuss/evals/files/locked-context.md
  modified: []

key-decisions:
  - "The fold refusal eval follows the skill's own wording (commit or discard the tracked changes), not the plan's 'commit or stash', so the eval judges the text that ships"
  - "The trigger split was decided by reasoning against each skill's scope and its 'Not for' list, not by jev (see the call log: the screen did not discriminate)"
  - "Eval text names neither a jev backend nor the consent step (SPEC R10), checked by rg with no match"

patterns-established:
  - "Eval input files are synthetic and each is listed by at least one eval; the shape test rejects unlisted files and machine paths"

requirements-completed: [FLOW-01, JEV-06]

# Metrics
duration: unrecorded (start time not captured in this run)
completed: 2026-11-04
status: complete

plan_head_before: 53ce2dfdf0c6a89071434caac34081ad5f42cf51
plan_head_after: 45f2f2bb8469c7b3aecf7ff4bf0af7d1172a5f05
commits: 2
---

# Phase 29 Plan 14: Judge-ready evals for the commit-fold and spec-discuss skills

**Six output evals and 20 trigger queries for each of the commit-fold and spec-discuss skills, with synthetic inputs, all accepted by the generic evals shape test; the jev screen could not validate the trigger split, so that split rests on each skill's stated scope.**

## Performance

- **Tasks:** 2 of 2 complete
- **Task commits:** 2 (40d4d20, 45f2f2b); this SUMMARY is the plan's docs commit
- **Files changed:** 10 (all new, under `skills/*/evals/`)
- **Plan base:** 53ce2df; HEAD before the SUMMARY commit: 45f2f2b

## Accomplishments

- `ai-kit-commit-fold/evals/evals.json`: `casual-fold-my-plan`, `precise-install-gsd-hook`, `precise-superpowers-plan`, `edge-refused-dirty-tree`, `edge-nothing-to-fold`, `edge-missed-fold-status`, each with a prompt, expected output, input files and 2-4 concrete assertions.
- `ai-kit-commit-fold/evals/trigger-queries.json`: 20 queries, 10 true and 10 near-miss false.
- `ai-kit-gsd-spec-discuss/evals/evals.json`: `casual-spec-discuss-range`, `precise-auto-mode`, `precise-interactive-mode`, `edge-jev-absent`, `edge-locked-decision-conflict`, `edge-blocking-unresolved`.
- `ai-kit-gsd-spec-discuss/evals/trigger-queries.json`: 20 queries, 10 true and 10 near-miss false.
- Four synthetic fold inputs (a GSD plan, a five-commit log, a superpowers plan, a five-line refused report) and two spec-discuss inputs (a roadmap analysis, a locked CONTEXT excerpt with decision D-04).
- `tests/test_skill_evals_shape.py` passes with both skills in its subtests; the banned-word check (laya, typesafe, zen, consent) matches nothing in either `evals/` folder.

## Task Commits

1. **Task 1: fold evals, checked by the generic shape test** - `40d4d20` (test)
2. **Task 2: spec-discuss evals, then the plan's full run and close** - `45f2f2b` (test)

## Files Created/Modified

See `key-files` in the frontmatter. No file outside `skills/*/evals/` changed. No `STATE.md`, `ROADMAP.md` or orchestrator artifact was touched.

## Decisions Made

See `key-decisions` in the frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Accuracy] The refusal eval's expected wording follows the shipped skill**
- **Found during:** Task 1, writing `edge-refused-dirty-tree`
- **Issue:** The plan says the agent tells the user to "commit or stash" tracked changes. The shipped `ai-kit-commit-fold/SKILL.md` says "commit or discard".
- **Fix:** The eval asserts the skill's wording. The plan text was not edited.
- **Files modified:** `skills/ai-kit-commit-fold/evals/evals.json`
- **Commit:** 40d4d20

**Total deviations:** 1 auto-fixed (accuracy). **Impact:** None on the plan's deliverables or checks.

### Process Notes (not code deviations)

- **Co-author trailer corrected.** My first two commits (697d95a, f7ce570) ended with a `Co-Authored-By` line that named the wrong model and that no attribution instruction supplied. Both were unpushed commits on this worktree branch, so I rewrote them with `git rebase --exec` (a script that only removes that line; hooks ran through `commit --amend`). The rewritten commits 40d4d20 and 45f2f2b have trees identical to the originals (`git diff --stat` empty for both pairs).
- **Plan commit ledger.** `gsd-plan-head-before-29-14` holds 53ce2df, written before the first commit. `git rev-list --count 53ce2df..HEAD` gives 2 at SUMMARY write.
- **Scratch files.** The jev scripts, their logs and the make-test log sit in `tmp/p29/14/` (gitignored). The start snapshot, run id and per-run temp dir were created by `scope.py` as the plan says.

## Issues Encountered

- **jev did not discriminate on this classification.** The near-miss screen answered "yes" to all ten near-miss queries (0.82-0.90), and it also answered "yes" to an unrelated control question (0.88). A two-option choice (fold or other) answered "fold" for every case, including the unrelated control (0.93-0.95). Neither shape separates in-scope from out-of-scope queries, so no jev answer was used as evidence for the trigger split. The split follows the skills' own scope text and "Not for" lists. Details in the call log.
- **Shell guard.** The Bash tool refused a few compound or inline `python3 -c` commands as too complex to verify inside the worktree. I split them into plain commands or small script files under `tmp/p29/14/`.
- **Commit hook created `.venv`.** The first commit's staged-tests hook created `.venv` in the worktree. It is gitignored, and the close check ignores it.

## Verification

- Task 1 verify: `tests.test_skill_evals_shape` and `tests.test_arch` passed (6 and 84 tests). Acceptance: `jq` gives 20 queries with 10 true; `rg -n -i "laya|typesafe|\bzen\b|consent"` on `skills/ai-kit-commit-fold/evals` matches nothing.
- Task 1 commit hook: staged-tests ran 5 modules, all passed (`tests.test_ai_kit_commit_fold`, `_adapters`, `_e2e`, `tests.test_arch`, `tests.test_setup`).
- Task 2 verify: `tests.test_skill_evals_shape` and `tests.test_ai_kit_gsd_spec_discuss` passed (6 and 41 tests). Acceptance: the same checks for spec-discuss match nothing and count 10 true of 20.
- Task 2 commit hook: staged-tests ran 7 modules, all passed.
- `make test` through `python3 tmp/p29/14/scope.py test` (TMPDIR set to this run's temp dir): exit 0, with no `failed:` lines. Unit 83/83, unit-uv 1/1, integration 6/6, e2e 24/24 plus `tests/test_install.sh` 45 passed / 0 failed, arch 1/1. Log: `tmp/p29/14/make_test.log`.
- `scope.py close` after the last task commit (and before this SUMMARY was written): `clean`, exit 0. Reported, not this run: other agents' `make test` and shells in sibling worktrees, the main checkout's processes, and one `ai-kit-p29-run-13-*` temp dir. Nothing was killed.

## Known Stubs

None.

## Threat Flags

None. The evals and inputs are synthetic; no machine path, secret or copy of `.planning/` entered the evals (T-29-28 mitigated and checked by the shape test).

## Self-Check

- FOUND: all ten files listed under `key-files` exist in the worktree.
- FOUND: commits 40d4d20 (Task 1) and 45f2f2b (Task 2) are ancestors of HEAD.
- FOUND: `git rev-list --count 53ce2df..HEAD` prints 2, matching the ledger-measured count.

## Self-Check: PASSED

## jev-fast-decision call log

Backend pinned with `JEV_BACKEND=laya` on every call. Every call was one item, one ladder call. Scripts: `tmp/p29/14/jev_classify.py`, `tmp/p29/14/jev_controls.py`, `tmp/p29/14/jev_choice.py`; logs: `tmp/p29/14/jev_classify.jsonl`, `tmp/p29/14/jev_controls.jsonl`, `tmp/p29/14/jev_choice.jsonl`.

- P-01 `--probe`: laya usable and selected; typesafe listed usable with a consent record dated 2026-10-14; opencode missing its key. No remote call.
- J-01..J-10 (noul, the ten near-miss queries): all `yes`, confidence 0.82-0.90, `decided_by` laya, no fallback. Did: judged each out of scope by my own reasoning against the skill's "Not for" list; kept `should_trigger: false`. The answers were not used as evidence, because the controls below showed the screen says "yes" to everything.
- J-11..J-13 (noul controls): two in-scope positives `yes` 0.88 and 0.88; an unrelated question (boiling point of water) `yes` 0.88. Did: confirmed the two-way screen does not discriminate.
- J-14..J-17 (choice, fold or other): in-scope positives `fold` 0.95 and 0.94; unrelated question `fold` 0.95; near-miss `fold` 0.93. Did: confirmed the two-option choice does not discriminate either; no answer used.
- Remote: every response listed a typesafe consent record (2026-10-14) in `consent_used`, but typesafe and opencode answered no item (`remote_available` empty). Nothing was sent off-machine.

## Open Items for the Orchestrator

- **Trigger split is not verified by jev.** If a stronger check of the near-miss negatives is wanted, it needs a screen that discriminates; neither shape tried here does.
- **Judge scoring of these evals** belongs to plan 29-16 (rubric D7). No `skill-judge` run was done here, and neither skill's SKILL.md changed.
- **`make test-env-matrix`** was not run; it is not part of this plan's verification.

*Phase: 29-logical-commit-folding-and-the-shared-jev-ladder*
