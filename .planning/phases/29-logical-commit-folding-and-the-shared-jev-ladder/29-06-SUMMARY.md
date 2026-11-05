---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 06
subsystem: tooling
tags: [git, commit-fold, refusal-guards, merge-back, replay, grouping, stdlib]

# Dependency graph
requires:
  - phase: 29-01
    provides: fold engine tracer (temp index, tree proofs, backup tag, compare-and-swap, five-line report)
  - phase: 29-02
    provides: the one folding policy text that the policy_missing refusal reads
provides:
  - every refusal guard of the fold engine (policy, dirty tree, moved branch, base branch, ancestry, base and merged reachability, foreign merges)
  - GSD's own merge-back folded away; any other merge in base..end refused
  - tree-identical replay of commits after end, with the segment proof before the replay
  - shared-path and code-with-test merges in rule grouping, with a note in the report, and path-based placement of unmatched commits
affects: [29-09, 29-10, 29-12, 29-13]

# Actuals (#2632): chars/4 over the realized diff (git diff 7147059..HEAD, 43429 chars)
actuals:
  tokens: 10857
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "refusal guards run before any write, in a fixed order; each leaves branch, working tree and tags unchanged"
    - "replay re-creates each later commit on the proven segment with its own tree, message, author and non-first parents"
    - "rule grouping merges features with union rules (shared path, code file with its test), each merge recorded in the note"

key-files:
  created: []
  modified:
    - skills/ai-kit-commit-fold/scripts/fold_engine.py
    - skills/ai-kit-commit-fold/scripts/fold_group.py
    - tests/fold_fixtures.py
    - tests/test_ai_kit_commit_fold.py

key-decisions:
  - "The report's after count is the folded features plus the non-merge commits replayed after end (jev asked; needs_fallback, decided by the executor, verified by the tracking-commit test)"
  - "merged_refs entries must be full ref names (refs/...); a checkpoint entry that does not resolve would otherwise skip the reachability guard silently"
  - "An own merge-back is recognised by its subject prefix only, a framework hint; the ownership proof belongs to plan 29-09's checkpoint adapter"
  - "Merges after end are replayed with their second parents unchanged; the side commits behind them are kept, not folded"

patterns-established:
  - "Test fixtures that need a branch tip at a given commit build one repo per tip (the tracking-only and merge-after plans are separate repos)"
  - "A replay test checks the replayed commit's tree, raw message and author against the original"

requirements-completed: [FLOW-01]

coverage:
  - id: D1
    description: "Every refusal guard refuses with the branch, working tree and backup tags unchanged"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldGuards"
        status: pass
    human_judgment: false
  - id: D2
    description: "Own merge-back folds to a linear history; foreign merges refuse with foreign_merge"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldMerges.test_own_merge_back_folds_to_a_linear_history"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldMerges.test_foreign_merge_refuses_without_moving_the_branch"
        status: pass
    human_judgment: false
  - id: D3
    description: "A tracking commit after end is replayed tree-identically; a merge-back after end keeps its second parent; a wrong segment is refused before the replay"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldMerges.test_tracking_commit_after_end_is_replayed_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldMerges.test_merge_back_after_end_keeps_its_second_parent"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldMerges.test_bad_segment_with_tracking_commit_refused"
        status: pass
    human_judgment: false
  - id: D4
    description: "Shared paths and code-with-test pairs merge with a note; unmatched commits join the feature holding their path"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldGrouping"
        status: pass
    human_judgment: false
  - id: D5
    description: "Multi-line non-ASCII messages and non-ASCII paths survive the fold byte for byte"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldEncoding.test_raw_message_and_non_ascii_path_survive"
        status: pass
    human_judgment: false

# Metrics
duration: unmeasured (no start timestamp recorded before the first task)
completed: 2026-11-04
status: complete
commits: 2
plan_head_before: 7147059b7f9d1aef57a1244e310de6eca80090c2
plan_head_after: 6f2c4750861f4575fd4ebc8d557c31fa1108aa90
---

# Phase 29 Plan 06: Fold refusal guards, own merge-back folding, replay of later commits and shared-path grouping

**The fold engine refuses every unsafe fold before any write, folds GSD's own merge-backs, replays commits after `end` tree-identically behind a segment proof, and merges features that share a path or a code file with its test**

## Performance

- **Tasks:** 2 of 2
- **Commits:** 2 task commits (measured with `git rev-list --count` at write time, before this file's commit)
- **Duration:** unmeasured

## Accomplishments

- Refusals run in a fixed order before any write: `policy_missing`, `dirty_tree` (tracked changes only), `branch_moved`, `no_base_branch`, `bad_checkpoint` (base an ancestor of end; end on the tip's first-parent chain), `range_on_base_branch`, `range_on_merged_branch`, `foreign_merge`.
- A guard refusal leaves the branch sha, `git status --porcelain` and `ai-kit-fold/*` tags unchanged (asserted in every guard test).
- Merges in `base..end`: only merges whose subject starts with an `own_merge_subjects` prefix are allowed; they fold away into a linear history.
- Commits after `end` on the tip's first-parent chain are re-created on the folded segment with their own tree, raw message, author and non-first parents. The committer is the current identity.
- The segment proof (`<segment>^{tree}` against `<end>^{tree}`) runs before the replay, so a wrong segment followed by a tracking commit is refused.
- Rule grouping merges features that share a changed path, or that hold a code file and its `test_<stem>.py`. The report note says why (`merged t1+t2: shared shared.py`, `merged t1+t2: x.py with its test`).
- An unmatched commit joins the feature holding one of its paths before the nearest-earlier fallback.
- Tests: `TestFoldGuards`, `TestFoldMerges`, `TestFoldGrouping`, `TestFoldEncoding`, plus the replay case in `TestFoldTracer`.

## Task Commits

1. **Task 1: refusal guards end to end** - `f94540a` (feat)
2. **Task 2: own merge-backs, replay, grouping and encoding** - `6f2c475` (feat)

**Plan metadata:** this SUMMARY is committed after the two task commits and is not counted in `commits:`.

## Files Created/Modified

- `skills/ai-kit-commit-fold/scripts/fold_engine.py` - `POLICY_PATH` and `_check_policy`, the `_guard` sequence (dirty tree, base and merged reachability, ancestry, merges), `_segment`, `_replayed`, `_replay`, the `after` count, merged-refs validation
- `skills/ai-kit-commit-fold/scripts/fold_group.py` - first-appearance grouping, path-based placement, union merges with notes (rewritten)
- `tests/fold_fixtures.py` - `merge_no_ff` and `set_ref` helpers
- `tests/test_ai_kit_commit_fold.py` - 44 tests (guards, merges, grouping, encoding, shape, report)

## Decisions Made

- The `after` count is the folded features plus the non-merge commits replayed after `end`. This is the one choice the executor sent to jev; see the call log.
- `merged_refs` entries must match `refs/...` at load time. An entry that does not resolve would otherwise skip the reachability guard without a trace, so the checkpoint is refused instead.
- Own merge-back recognition is a subject-prefix hint, as the policy states. The ownership proof is the job of plan 29-09's checkpoint adapter.
- An empty `own_merge_subjects` entry matches nothing; an empty prefix would otherwise match every merge.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] merged_refs must be full ref names**
- **Found during:** Task 1, planning the reachability guard
- **Issue:** The plan lists the guard behaviour but not the validation of its input. An entry such as `--output=...` or `plan` would resolve to nothing, and the guard would skip it silently.
- **Fix:** `load_checkpoint` validates `merged_refs` with the `refs/...` pattern and refuses `bad_checkpoint`. Test: `TestCheckpointShape.test_merged_refs_must_be_full_ref_names`.
- **Committed in:** `f94540a`

**2. [Rule 2 - Missing critical] empty own_merge_subjects prefix ignored**
- **Found during:** Task 2, writing `_check_merges`
- **Issue:** An empty prefix would match every merge subject, which would fold a foreign merge.
- **Fix:** Empty prefixes are skipped in the match.
- **Committed in:** `6f2c475`

### Process deviations (no change to the plan's behaviour)

**3. Commit ledger stored in the plan's tmp directory, not the git directory**
- **Found during:** Step 0c (plan commit ledger)
- **Issue:** The Write tool refused the shared git directory path for the worktree.
- **Fix:** The base sha was written to `tmp/p29/06/plan-head-before-29-06` (gitignored) before the first commit. It records `7147059b`, the base verified by the spawn-time check. `commits:` above is measured from that file.

**4. Worktree lacked the gitignored GSD tree**
- **Found during:** Setup
- **Issue:** The worktree had no `.claude/` directory.
- **Fix:** Created `.claude/` and copied `gsd-core/` and `scripts/` from the main checkout. Both are gitignored and not committed.

**5. Two commit attempts refused by hooks, then fixed**
- **Found during:** Task 1 commit (ruff E501 on two lines); Task 2 commit (ruff UP012 on an `.encode()` of an ASCII literal)
- **Fix:** Wrapped the lines and used a bytes literal. Each retry ran all hooks. Nothing was committed by the refused attempts, and `--no-verify` was not used.

**6. Tracer test behaviour changed on purpose**
- **Found during:** Task 2
- **Issue:** `test_end_before_tip_refuses_without_moving_the_ref` expected a refusal, which 29-01 noted would change once replay existed.
- **Fix:** Renamed to `test_end_before_tip_replays_the_later_commits`; it asserts a folded result, the tip tree, three commits and the tag.

**7. Test fixture error caught by the red run (test-only)**
- **Found during:** Task 2 green run
- **Issue:** The tracking fixture's branch tip was the merge, so a checkpoint with `tip` at the tracking commit correctly refused `branch_moved`.
- **Fix:** Split into two fixtures: `tracking` (ends at the tracking commit) and `merge-after` (adds the merge-back). No engine change.

**Total deviations:** 2 auto-fixed (Rule 2), 5 process or test notes. **Impact on plan:** scope unchanged; every acceptance criterion met.

## Issues Encountered

- The Bash tool refused compound `git` forms and `$HOME` expansions in this worktree. Each step ran as a plain command from the worktree path.
- Estimate versus actual: the plan estimated 52000 tokens; the realized diff is 43429 characters, about 10857 tokens by chars/4. The estimate was about five times high for this plan.

## Verification

- Red runs before implementation: Task 1, 11 guard tests failed (the rest passed). Task 2, 9 merge, replay, grouping and foreign-merge tests failed.
- `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold tests.test_arch`: both modules ok (44 and 84 tests). The fold module runs in 1.1 s, inside the 10 s budget.
- `python3 tmp/p29/06/scope.py test` (`make test`): exit 0. Tiers: unit 81/81 (including `tests.test_ai_kit_commit_fold: ok, Ran 44 tests`), unit-uv 1/1, integration 6/6, e2e 23/23 (`tests/test_install.sh` 45 passed, 0 failed), arch 1/1. Log at `tmp/p29/06/make-test.log`.
- Acceptance: `rg "untracked-files=no"` and `rg "is-ancestor"` both match in `fold_engine.py`; `def _replay` matches; in `_fold` the segment proof (inside `_segment`) runs before `_replay(` is called.
- `scope.py close` after the last task commit printed `clean` as its last line (exit 0). The `reported (not this run)` block lists other agents' processes and `ai-kit-p29-run-05-*` from plan 29-05; none were touched.

## jev-fast-decision call log

- c1 | after-count semantics for replayed commits (features plus replayed non-merge commits / features only / non-merge count of base..new) | answer `a`, confidence 0.19 (TypeSafe, `needs_fallback: true`; Laya 0.08, `needs_fallback: true`) | decided myself: kept `a`, because it is the count of commits the branch holds after the fold. Check: `test_tracking_commit_after_end_is_replayed_unchanged` asserts `after == 3` and `rev-list --count base..plan` is 3.

## Known Stubs

None.

## Threat Flags

None. T-29-02 (main and merged-branch rewrite) and T-29-26 (merge-back and replay) are covered by the guard tests, the foreign-merge tests and `test_bad_segment_with_tracking_commit_refused`.

## Known limits

- Rule grouping has no import analysis. A feature that depends on a file a later feature adds is not merged with it, so an intermediate folded commit is not proven to build alone; only the folded tip's tree is proven (FOLD-4). This is a `shortcut:` marker in `fold_group.py`, and the folding policy states it.
- Side commits behind a merge after `end` keep their old identity (the second parent is kept, not folded or replayed).
- `dirty_tree` checks tracked files only, by design. Untracked files do not refuse.
- Own merge-backs are recognised by subject; the ownership proof is plan 29-09's job.

## Self-Check

- Changed files exist: `skills/ai-kit-commit-fold/scripts/fold_engine.py`, `skills/ai-kit-commit-fold/scripts/fold_group.py`, `tests/fold_fixtures.py`, `tests/test_ai_kit_commit_fold.py` (all FOUND).
- Commits are ancestors of HEAD: `f94540a` and `6f2c475` (both FOUND); `git rev-list --count 7147059..HEAD` is 2 before this file's commit.
- `scope.py close`: `clean` (exit 0) after the last task commit.
- STATE.md and ROADMAP.md were not modified.

## Self-Check: PASSED

---
*Phase: 29-logical-commit-folding-and-the-shared-jev-ladder*
*Plan: 06*
*Completed: 2026-11-04*
