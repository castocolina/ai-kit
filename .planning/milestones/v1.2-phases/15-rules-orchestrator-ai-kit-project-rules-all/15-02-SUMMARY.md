---
phase: 15-rules-orchestrator-ai-kit-project-rules-all
plan: 02
subsystem: testing
tags: [skill-authoring, documentation, skill-judge, naming-analyzer, rules-orchestrator]

# Dependency graph
requires:
  - phase: 15-rules-orchestrator-ai-kit-project-rules-all (plan 15-01)
    provides: "ai-kit-project-rules-all's proven functional core (dispatch.py, aggregate.py, cli.py) -- this plan documents and installs it, changing no code"
provides:
  - "skills/ai-kit-project-rules-all/SKILL.md -- the skill's user-facing document, making the directory installable for the first time"
  - "Registration in README.md, .pre-commit-config.yaml, pyproject.toml (matching the 5 most recent sibling phases' own registration pattern)"
  - "/skill-judge evidence (15-SKILL-JUDGE.md): 97/120, 0 Critical/0 Important after one fix iteration, committed and reproducible"
  - "/naming-analyzer confirmation: ai-kit-project-rules-all kept as-is, no rename"
  - "15-CONTEXT.md's stale BLOCKED-on-Phases-9-14 claims corrected append-only"
affects: ["future phases that install or reference the ai-kit-project-rules-all skill"]

# Actuals (#2632)
actuals:
  tokens: 14246
  tasks: 3
  commits: 4
plan_head_before: f6b3dceeba694d5ef946173c1704d2581a9352ff

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Skill-authoring pipeline order: scaffold code (15-01) -> write SKILL.md against the shipped code -> /skill-judge as the code-review gate -> /naming-analyzer as confirmation -> context-sweep cleanup -- same order Phases 9-14 established"
    - "Self-referential evidence-hash problem solved by a two-commit split (fix commit first, evidence-file commit second, referencing the fix commit's now-known hash) -- the same pattern Phase 14's own git history used when its own fix loop needed a real edit"

key-files:
  created:
    - skills/ai-kit-project-rules-all/SKILL.md
    - .planning/phases/15-rules-orchestrator-ai-kit-project-rules-all/15-SKILL-JUDGE.md
  modified:
    - README.md
    - .pre-commit-config.yaml
    - pyproject.toml
    - .planning/phases/15-rules-orchestrator-ai-kit-project-rules-all/15-CONTEXT.md

key-decisions:
  - "D-07/D-08/D-09/D-10/D-11 (plan-authored, executed exactly as specified): SKILL.md describes the SHIPPED code (code wins over the SUMMARY where they'd disagree -- no disagreement found); Limits floor is 8, never a ceiling; naming-analyzer confirms rather than applies a rename; skill-judge bar is absolute (0 Critical/Important OR >=96/120); fix loop bounded at 3 iterations with no limit-softening allowed."
  - "Found and fixed one real Important-severity self-contradiction during Task 2's own pre-scoring read (not in the plan's anticipated findings): Scope and Limits #8 both overstated that every remediate/blocked entry is 'unchanged' from what a sibling produced, but aggregate() adds a hand_off key to workflow-kind entries -- fixed by naming the one documented exception in both locations, matching D-07's code-wins rule and D-11's no-softening rule (the fix made the affected sentences more specific, not shorter)."

patterns-established:
  - "Pattern 3: a skill-judge fix found during the executor's own pre-scoring read (before invoking the rubric) still counts as a real fix-loop iteration and must be recorded as such -- the loop isn't only for findings the rubric itself surfaces after a formal run."

requirements-completed: [REQ-rules-all]

coverage:
  - id: D1
    description: "SKILL.md exists, frontmatter name matches the directory basename, description carries the pinned cross-domain token and names all 6 siblings, and the Scope/Limits/Hand-off sections match the shipped code exactly (SKILL-SHAPE-OK)"
    requirement: "REQ-rules-all"
    verification:
      - kind: other
        ref: "python3 -c '...' (Task 1's SKILL-SHAPE-OK check) -- prints 'SKILL-SHAPE-OK 8 8', exits 0"
        status: pass
      - kind: integration
        ref: "python3 skills/ai-kit-project-rules-all/ai-kit-project-rules-all.py check . and ... remediate . -- confirmed top-level keys (remediate, blocked, failed) match the document"
        status: pass
    human_judgment: false
  - id: D2
    description: "The skill is registered in all 3 gate surfaces plus README (5 total edit sites)"
    requirement: "REQ-rules-all"
    verification:
      - kind: other
        ref: "git grep -c ai-kit-project-rules-all -- README.md .pre-commit-config.yaml pyproject.toml -- 1/2/2 respectively"
        status: pass
    human_judgment: false
  - id: D3
    description: "/skill-judge cleared as this phase's code-review gate: 0 Critical/0 Important after 1 fix iteration, 97/120, committed evidence naming the judged commit"
    requirement: "REQ-rules-all"
    verification:
      - kind: other
        ref: "python3 -c '...' (Task 2's JUDGE-GATE-OK check) -- prints 'JUDGE-GATE-OK 97/120 0 0 1/3 8 none', exits 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "/naming-analyzer confirmed the skill's name (no rename applied); 15-CONTEXT.md's stale claims corrected append-only (3 corrections, floor of 2)"
    requirement: "REQ-rules-all"
    verification:
      - kind: other
        ref: "python3 -c '...' (Task 3's CORRECTIONS-OK check) -- prints 'CORRECTIONS-OK 3 26 104f96cb', exits 0"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-09-15
status: complete
---

# Phase 15 Plan 02: Rules Orchestrator SKILL.md, Registration, and Gates Summary

**`ai-kit-project-rules-all/SKILL.md` written against the shipped code, registered in README/pre-commit/pyproject, cleared `/skill-judge` at 97/120 (0 Critical/0 Important after fixing one self-contradiction), confirmed by `/naming-analyzer`, and 15-CONTEXT.md's stale blocked-on-Phases-9-14 claims corrected append-only.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-09-14T21:51:57-04:00 (first task commit)
- **Completed:** 2026-09-15T02:01:07Z
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments
- `SKILL.md` (215 lines): Scope naming all 6 siblings by real name; a dual-layer entrypoint-resolution section (this skill's own, plus the internal 6x per-domain walk `dispatch.py` performs); `Run the check` with two real worked JSON examples pulled from a purpose-built fixture repo dogfood run (one `hand_off`-tagged `workflow` entry, one without); a Hand-off mechanism section pointing at `ai-kit-project-rules-agents/SKILL.md`'s real Step A/B/C sequence by name; 8 honesty-about-limits statements (the floor, never trimmed); 5 anti-patterns; a reporting rule
- Registered in `README.md` (1 row), `.pre-commit-config.yaml` (ruff `files:`, py-compile `files:`, unittest `entry:` -- 3 locations), `pyproject.toml` (`[tool.pyright]` `include`, `[tool.vulture]` `paths` -- 2 locations) -- matching every sibling's own registration pattern exactly
- `/skill-judge` run as this phase's code-review gate: found and fixed one real Important-severity self-contradiction (Scope/Limits #8 claimed every entry is "unchanged" but `aggregate()` adds a `hand_off` key to `workflow`-kind entries) before formal scoring completed; final score 97/120, 0 Critical, 0 Important, 1/3 fix iterations used; no-baseline claim verified via 2 history searches; evidence committed at `.planning/phases/15-rules-orchestrator-ai-kit-project-rules-all/15-SKILL-JUDGE.md`
- `/naming-analyzer` confirmed `ai-kit-project-rules-all` (shortest name in the family at 24 characters, no misleading-scope tension unlike several siblings' own recorded findings); 3 live name-dependency sites re-verified and recorded
- `15-CONTEXT.md` swept: 3 dated, append-only corrections (floor was 2) -- the stale `**Status:**` header, the stale "NONE of Phases 9-14 have a plan or execution yet" claim, and a stale code path (`skills/ai-kit-agents-md-rules-checker` renamed by Phase 9 to `skills/ai-kit-project-rules-agents`) -- every original word preserved, confirmed by a zero-removed-lines diff check

## Task Commits

Each task was committed atomically (Task 2 split into 2 commits to solve the self-referential evidence-hash problem -- the fix must land, and be known, before the evidence file that names its hash):

1. **Task 1: Write SKILL.md and register across README/pre-commit/pyproject** - `3183c96` (feat)
2. **Task 2a: Fix the unchanged-entry self-contradiction found during pre-scoring read** - `8f231d0` (fix)
2. **Task 2b: Run /skill-judge, commit evidence** - `00bf502` (docs)
3. **Task 3: Confirm naming, sweep 15-CONTEXT.md** - `104f96c` (docs)

**Plan metadata:** _(final commit below)_

## Files Created/Modified
- `skills/ai-kit-project-rules-all/SKILL.md` - the skill's user-facing document
- `README.md` - one new skill-table row after `ai-kit-project-rules-cicd`
- `.pre-commit-config.yaml` - ruff `files:`, py-compile `files:`, unittest `entry:` module list all gain `ai-kit-project-rules-all`
- `pyproject.toml` - `[tool.pyright]` `include` and `[tool.vulture]` `paths` both gain `skills/ai-kit-project-rules-all`
- `.planning/phases/15-rules-orchestrator-ai-kit-project-rules-all/15-SKILL-JUDGE.md` - skill-judge scoring evidence + naming-analyzer verdict
- `.planning/phases/15-rules-orchestrator-ai-kit-project-rules-all/15-CONTEXT.md` - 3 append-only, dated corrections

## Decisions Made
- D-07 through D-11 (plan-authored, see plan frontmatter) were implemented exactly as specified -- no deviation from the plan's own pre-authored decisions.
- The one real judgment call this plan's executor made: whether a defect found DURING preparation to invoke `/skill-judge` (rather than a finding the rubric itself surfaced after a formal run) still counts as a fix-loop iteration. Treated it as YES -- recorded as Iteration 1 with full before/after text, since the substance (an Important-severity factual self-contradiction, caught and fixed before the document was "final") is identical regardless of which step in the process surfaced it, and D-11's "record each iteration" requirement does not distinguish by who/what found the issue.
- Reused Phase 14's own real commit-history pattern (fix commit, then a separate evidence-file commit referencing the fix's now-known hash) to solve the self-referential `JUDGED_COMMIT` problem -- writing the evidence file and the SKILL.md fix in the SAME commit is impossible without predicting a commit hash before it exists, so this plan follows the same 2-commit split Phase 14's real git history used when it needed a post-score fix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a factual self-contradiction in SKILL.md before formal skill-judge scoring**
- **Found during:** Task 2, while re-reading the committed `SKILL.md` in preparation to run `/skill-judge`
- **Issue:** The Scope section's closing sentence and Limits #8 both claimed every `remediate`/`blocked` entry "is exactly what that sibling produced, unchanged" -- but `aggregate.py`'s own code (`aggregate.py:47-49`) adds a `hand_off` key to every `workflow`-kind entry, which the document's own Hand-off mechanism section correctly describes two sections later. The document contradicted itself about its own shipped behavior.
- **Fix:** Both locations reworded to name the `hand_off` key as the one documented exception, matching `aggregate.py`'s real behavior and D-07's rule that the code wins. No limit statement was deleted, merged, or softened (D-11) -- the affected sentences became more specific, not shorter, and `LIMIT_COUNT_FINAL` stayed at 8.
- **Files modified:** `skills/ai-kit-project-rules-all/SKILL.md`
- **Verification:** `SKILL-SHAPE-OK` re-run after the fix, still prints `SKILL-SHAPE-OK 8 8` and exits 0; both edited passages re-read against `aggregate.py`'s real behavior and confirmed consistent with the Hand-off mechanism section.
- **Committed in:** `8f231d0936d6a798d9f34475e60f8551cd9f3ac3`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 - bug)
**Impact on plan:** The fix corrected a real documentation-accuracy defect before the phase's code-review gate scored it -- exactly the kind of issue the gate exists to catch, caught one step earlier than the rubric itself would have surfaced it. No scope creep; no code file touched.

## Issues Encountered

- This session's worktree branch (`worktree-agent-a03c75d8ebed79b96`) was spawned from a base commit 186 commits behind `main` -- predating plan 15-01's entire execution (and Phases 9-14's real implementations this plan's SKILL.md documents). Confirmed `HEAD` was a strict ancestor of `main` (`git merge-base --is-ancestor HEAD main`), then fast-forwarded (`git merge --ff-only main`) before starting Task 1 -- the worktree branch carried zero unique commits of its own, so this was a clean, lossless fast-forward, matching the same situation plan 15-01's own SUMMARY recorded for its worktree.
- `make validate` fails with 25 pre-existing `ruff`/`vulture` errors, all in files this plan never touches (`tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py`) -- confirmed by grepping every reported file path against this plan's own edited files (zero overlap). Out of scope per this plan's own scope note and the deviation rules' scope boundary; reported honestly per Task 1's and Task 3's acceptance criteria rather than fixed or suppressed. Run twice (after Task 1's commit and after Task 3's commit), same 25 errors both times -- confirmed pre-existing, not introduced by this plan.

## User Setup Required

None - no external service configuration required. This plan writes only documentation, registration-file edits, and planning records.

## Next Phase Readiness

- `ai-kit-project-rules-all` is now fully installable: `SKILL.md` exists, is registered in all 3 gate surfaces plus README, and has cleared `/skill-judge` as this phase's code-review gate with committed evidence.
- This is the LAST phase in the v1.2 rules-family's strict dependency chain (per `15-CONTEXT.md`'s Phase Boundary, now corrected to reflect that all 6 prerequisite domain checkers are complete). No further phase in this family is blocked on this one.
- `/naming-analyzer` confirmed the name; no rename-propagation work is needed for any future phase.

---
*Phase: 15-rules-orchestrator-ai-kit-project-rules-all*
*Completed: 2026-09-15*

## Self-Check: PASSED

All 4 created/modified deliverable files confirmed present on disk (`skills/ai-kit-project-rules-all/SKILL.md`,
`15-SKILL-JUDGE.md`, `15-CONTEXT.md`, `15-02-SUMMARY.md`); all 4 task commit hashes (`3183c96`,
`8f231d0`, `00bf502`, `104f96c`) confirmed present in `git log --oneline --all`.
