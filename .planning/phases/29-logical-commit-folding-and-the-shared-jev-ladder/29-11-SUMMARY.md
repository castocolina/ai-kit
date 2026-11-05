---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 11
subsystem: skills
tags: [jev-fast-decision, spec-discuss, gsd, black-box, decision-help]

# Dependency graph
requires:
  - phase: 29-03
    provides: the jev ladder tests copied into tests/test_jev_fast_decision.py
  - phase: 29-08
    provides: jev-fast-decision SKILL.md (Callers, Consent, item shape) that spec-discuss now points to
provides:
  - spec-discuss asks jev-fast-decision as a black box; decide.py deleted
  - spec-discuss decision table and logs work on one advisory jev answer per item
affects: [29-14 spec-discuss shape evals, 29-15 skill text tests]

# Actuals (#2632) — chars/4 over the realized diff (git diff 9e7f067..HEAD)
actuals:
  tokens: 31332
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns: [one advisory jev answer per item, own reasoning on needs_fallback, error or no answer]

key-files:
  created: []
  modified:
    - skills/ai-kit-gsd-spec-discuss/SKILL.md
    - skills/ai-kit-gsd-spec-discuss/references/decision-table.md
    - skills/ai-kit-gsd-spec-discuss/references/log-formats.md
    - skills/ai-kit-gsd-spec-discuss/references/worked-examples.md
    - skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md
    - tests/test_ai_kit_gsd_spec_discuss.py
  deleted:
    - skills/ai-kit-gsd-spec-discuss/scripts/decide.py

key-decisions:
  - "decide.py is deleted, not moved: client lookup, ladder, detect and consent live only in jev-fast-decision (D-14)"
  - "spec-discuss keeps phase_range.py and edge_floor.py only; its scripts never call jev"
  - "One item per gray area; one jev request per step that has open items (spec and discuss separately)"
  - "Decision table keeps rows 1-5 (row 3 second opinion, row 4 needs_fallback/error/no answer to own reasoning, row 5 jev not installed)"
  - "The forced flag and its (forced) log cell are removed from spec-discuss (jev internal); see Deviations"

patterns-established:
  - "Black-box jev: ask the jev-fast-decision skill and follow its SKILL.md; never name a backend, a consent step or a probe status in a caller"
  - "Log cells for jev answers: choice 0.NN, low 0.NN, choice 0.NN (second opinion), none, not installed, error: <code>"

requirements-completed: [JEV-06]

# Metrics
duration: approximately 25 min (start time not recorded; scope snapshot 22:37Z, last task commit 22:45Z)
completed: 2026-11-04
status: complete

# Commit ledger (#3968) — measured from the worktree base
commits: 3
plan_head_before: 9e7f0673c34fa9f5a1d1b9fc208986509169f185
plan_head_after: e94b39eb0f094bbf07b559eca694d7aed6923348
---

# Phase 29: Plan 11 Summary

**spec-discuss asks jev-fast-decision as a black box: decide.py is deleted, its 37 ladder tests live in jev, and every spec-discuss text reads one advisory jev answer per item**

## Performance

- **Duration:** approximately 25 min (not measured precisely)
- **Tasks:** 2 of 2, plus one follow-up test-naming commit
- **Files:** 6 modified, 1 deleted

## Accomplishments

- `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` deleted; spec-discuss's scripts folder holds only `phase_range.py` and `edge_floor.py`, and neither defines a ladder or client lookup.
- SKILL.md asks the `jev-fast-decision` skill and follows its SKILL.md (two occurrences); no backend name, consent step, probe status or `decide.py` remains. Its setup no longer detects backends or asks consent.
- Decision table, log formats, worked examples and the analyzer brief work on one advisory jev answer per item; a low, errored or missing answer goes to own reasoning.
- Ladder tests (37 across five classes) left this module; they already exist in `tests/test_jev_fast_decision.py` with identical per-class counts.
- Text test `TestNoLadderHere` (6 tests) pins the scripts folder, the absence of ladder functions, a jev-free `phase_range.py` run, the black-box sentence, and the forbidden-term list for SKILL.md and references.

## Task Commits

1. **Task 1: decide.py deleted; SKILL.md rewired to the black-box jev instruction; ladder tests gone** - `72e1e2e` (refactor)
2. **Task 2: the four references rewritten for one advisory jev answer per item** - `48be3f9` (docs)
3. **Follow-up: comment and test name say jev, not ladder** - `e94b39e` (test)

**Plan metadata:** written after the scope close (see Scope close below); committed separately as the docs commit for this SUMMARY.

## Files Created/Modified

- `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` - deleted (`git rm`)
- `skills/ai-kit-gsd-spec-discuss/SKILL.md` - description, opening, mindset, §0 steps 1/3/5, §1-§2 jev references, §3 rewritten as "Asking jev", NEVER list, references list
- `skills/ai-kit-gsd-spec-discuss/references/decision-table.md` - rows 1-5 on one jev answer; per-backend columns, forced-column section and backend names removed; ledger row with one jev column
- `skills/ai-kit-gsd-spec-discuss/references/log-formats.md` - jev cell format; Interview Log, CONTEXT entry, DISCUSSION-LOG jev screening rewritten
- `skills/ai-kit-gsd-spec-discuss/references/worked-examples.md` - cases 1-5 told with "jev answered"; case 6 now a low-answer illustration
- `skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md` - the orchestrator asks jev; the analyzer never calls it
- `tests/test_ai_kit_gsd_spec_discuss.py` - ladder classes removed; `_TmpHome` trimmed; `TestNoLadderHere` added; `TestSkillContract` pins re-pointed to the moved wording

## Decisions Made

- Delete `decide.py` outright. Its ladder, client lookup, detect and consent behaviour is covered by `tests/test_jev_fast_decision.py` (D-14).
- The decision table keeps its row numbers, so existing cross-references (row 1 needs-confirmation rule, row 3 second opinion, row 4 and row 5 in the worked examples) still resolve.
- Cell formats for logs: `choice 0.NN` (confident), `low 0.NN` (`needs_fallback`), `choice 0.NN (second opinion)`, `none`, `not installed`, `error: <code>`.
- `JEV_LAYA_URL` stays in the test environment as a belt, although no spec-discuss script reaches jev any more.

## Deviations from Plan

### Judgment calls

**1. [Rule 4 - architectural, flagged for owner] Forced-column rule removed from spec-discuss; classification disputed by jev**
- **Found during:** Task 2 (the decision-table rewrite); the plan said to remove the forced-fallback rule.
- **Issue:** Removing it changes what the skill documents about forced answers, so it could count as a rule change. jev-fast-decision classified it as a rule change needing owner sign-off (answer `a`, top 0.72).
- **Resolution:** The executor checked `skills/jev-fast-decision/reference.md` line 44: `needs_fallback` is true whenever an answer is forced, so a forced answer already routes to row 4 (own reasoning). The routing outcome is unchanged. The executor classified the change as a wording and log-format change (the `(forced)` cell is gone) and disagrees with jev's `a` on the facts. **The owner should confirm this classification.** The jev answer is advisory and the executor overrode it on evidence.
- **Files modified:** `references/decision-table.md`, `references/log-formats.md`, `references/worked-examples.md`, `SKILL.md`
- **Commit:** `48be3f9`

### Auto-fixed or non-plan changes

**2. [Rule 2 - test pins moved with the wording]** Pins that asserted removed wording were re-pointed to the same rule, not deleted: the forced-column pin became a routing pin (`(needs_fallback, an error or no answer) → own reasoning`); the `reference.md` pin became `follow its SKILL.md`; the "backends that answered" pin was removed (consent announcement moved to jev); the call-count pin became the one-jev-request-per-step pin and was renamed `test_jev_call_count_and_prose_minors`.
- **Commits:** `72e1e2e`, `48be3f9`, `e94b39e`

**3. [Rule 3 - wording the plan did not list]** The description's "Works with no decision backend installed" became "Works without `jev-fast-decision` installed"; the Laya anecdote became "one real run" with no backend name; the `(fb)` example markers became `low 0.NN`; `§0` step 1 now tests for `phase_range.py` (the deleted script was the old marker).
- **Commit:** `72e1e2e` (SKILL.md), `48be3f9` (references)

**4. [Additive] `TestNoLadderHere.test_references_name_no_backend_or_client_internal`** checks the references too, not only SKILL.md. Plan 29-15's text test also enforces this; this one fails fast on this plan's own text.
- **Commit:** `48be3f9`

**5. [Ordering] decision-table.md still named `decide.py` between the two task commits.** The Task 1 acceptance grep for `decide.py` only passes after Task 2 (`48be3f9`). The final state is clean; the intermediate commit `72e1e2e` leaves one stale reference until `48be3f9`.

## Issues Encountered

- The worktree bash guard refused several combined git commands ("too complex to verify"). Each was split into plain commands run from the worktree. No repository state was affected.
- jev item `f1` was answered by TypeSafe (the remote backend), under consent recorded 2026-10-14 (reported as `consent_used`). The item was summary-only: no code, no paths with secrets, no config values. The owner should know a remote call happened during this plan.
- The jev response for item `c1` carried `top` 0.7241 with `needs_fallback` false, but its `confidence` field read 0.1503 for the same item. The two fields do not read as the same measure; noted for the jev owner, not acted on here.

## Test Results

- `python3 tmp/p29/11/scope.py test` (the plan's one `make test`, per-run TMPDIR): exit 0. Each runner group printed "modules passed" with no failures (82/82, 1/1, 6/6, 23/23, 1/1); the install shell tests printed 45 passed, 0 failed. Log: `tmp/p29/11/make-test.log` (gitignored).
- Module runs after the final edits: `tests.test_ai_kit_gsd_spec_discuss` 41 tests ok (base had 72 tests: 37 moved to jev, 6 added, 72 - 37 + 6 = 41); `tests.test_jev_fast_decision` 212 tests ok; `tests.test_ai_kit_gsd_spec_discuss_e2e` 1 test ok.
- Per-class counts, base spec-discuss module vs `tests/test_jev_fast_decision.py`: TestItemError 3 / 3, TestPartitionIds 2 / 2, TestTypedAnswer 8 / 8, TestFindClient 1 / 1, TestLadderCli 23 / 23.
- Acceptance: `decide.py` absent; no forbidden term in SKILL.md or references (case-insensitive); "follow its SKILL.md" occurs twice in SKILL.md.

## jev call log

- **jev-1** (reviewed_head `48be3f9`; one request, two items; advisory):
  - `c1` (choice: rule change vs wording change for the forced-column removal): answered `a` ("rule change, flag for owner"), Laya, top 0.7241, needs_fallback false. **Executor action:** read jev reference.md line 44 (forced implies needs_fallback, so row 4 routing is unchanged) and classified the change as wording and log-format; disagreed with `a`, flagged it for the owner.
  - `f1` (yes/no: a low, errored or missing answer still routes to own reasoning, and no backend or client flag is named): answered "supported", TypeSafe, top 0.81 (Laya's first rung was `needs_fallback` true at top 0.36). **Executor action:** verified by reading decision-table row 4 and SKILL.md §3 and by a text grep (no matches); agreed.
- No other jev calls.

## Scope close

- `python3 tmp/p29/11/scope.py start` and `selftest` ("selftest ok") at the start; `close` run after the last task commit and before this SUMMARY was written: `clean`, exit 0. The reported lines were other sessions' processes in the main checkout and another plan's temp directory; none were touched.
- The commit ledger `gsd-plan-head-before-29-11` was written with the base sha `9e7f0673c34fa9f5a1d1b9fc208986509169f185`, and `commits: 3` is measured from it.

## Open items (not done by this plan)

- `skill-judge` review of the updated `SKILL.md`: AGENTS.md requires the judge loop before a materially updated skill is marked complete. This plan did not run it; it belongs to the phase code review.
- `tests/test_ai_kit_spec_goal_prompt_host.py` line 804 has a test named `test_jev_never_calls_the_ladder`, outside this plan's scope. It names the word "ladder" for the goal-prompt skill and is unchanged here.

## Self-Check: PASSED

- Files present: `SKILL.md`, `references/decision-table.md`, `references/log-formats.md`, `references/worked-examples.md`, `references/analyzer-brief.md`, `tests/test_ai_kit_gsd_spec_discuss.py`.
- `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` absent (expected).
- Commits present in history: `72e1e2e`, `48be3f9`, `e94b39e`.
- Worktree clean before this SUMMARY was written.

---
*Phase: 29-logical-commit-folding-and-the-shared-jev-ladder*
*Completed: 2026-11-04*
