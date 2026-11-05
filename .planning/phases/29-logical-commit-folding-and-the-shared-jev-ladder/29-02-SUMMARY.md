---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 02
subsystem: testing
tags: [folding-policy, doc-contract, arch-test, reset-hard, agents-md]

# Dependency graph
requires: []
provides:
  - "One folding policy text, skills/ai-kit-commit-fold/references/folding-policy.md, stating FOLD-1..FOLD-10"
  - "Doc-contract check that names each missing policy rule, with removal, reordering and rewrapping non-vacuity cases"
  - "Structural rule: no fold skill code or instruction uses reset --hard (text or argv form)"
  - "Shell-true rule extended to the fold skill folder"
  - "AGENTS.md Workflow folding sentence points at the policy instead of restating it"
affects: [29-01 (fold engine scripts land in the scanned folder), 29-06 (engine policy_missing refusal)]

# Actuals (#2632): chars/4 over the realized diff (git diff 358113ad..HEAD, 11275 bytes)
actuals:
  tokens: 2819
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Policy rules pinned by stable phrase, normalized (lowercase, no emphasis, no list markers, collapsed whitespace), so layout changes do not fail the check"
    - "Structural text/AST rule for banned commands, with non-vacuity cases per form"

key-files:
  created:
    - skills/ai-kit-commit-fold/references/folding-policy.md
  modified:
    - tests/test_arch.py
    - AGENTS.md

key-decisions:
  - "The policy text is the single copy; AGENTS.md names the path and restates nothing, so the two cannot drift"
  - "The doc-contract matches phrases after normalization, not Markdown structure, so re-wrapping and reordering pass"
  - "reset --hard is banned by a structural check over fold skill files (not only the policy text, which is exempt because it states the prohibition)"

patterns-established:
  - "Each doc-contract rule ships with a removal subTest that names the removed rule id"

requirements-completed: [FLOW-01]

coverage:
  - id: D1
    description: "FOLD-1..FOLD-10 stated once in the folding policy, each pinned by a doc-contract check"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_arch.py#TestArchitecture.test_folding_policy_states_every_rule"
        status: pass
      - kind: unit
        ref: "tests/test_arch.py#TestArchNonVacuity.test_policy_rule_removal_is_caught"
        status: pass
    human_judgment: false
  - id: D2
    description: "AGENTS.md folding sentence points at the policy path and no longer restates the rule"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_arch.py#TestArchitecture.test_agents_md_points_to_the_folding_policy"
        status: pass
    human_judgment: false
  - id: D3
    description: "No fold skill code or instruction uses reset --hard; shell-true rule covers the fold skill"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_arch.py#TestArchitecture.test_fold_skill_never_resets_hard"
        status: pass
      - kind: unit
        ref: "tests/test_arch.py#TestArchNonVacuity.test_reset_hard_flags_each_form"
        status: pass
      - kind: unit
        ref: "tests/test_arch.py#TestArchitecture.test_rule8_no_shell_true_in_spec_family"
        status: pass
    human_judgment: false

# Metrics
duration: 5min (18:55:47 to 19:00:22 -03:00, start to last task commit)
completed: 2026-11-04
status: complete
---

# Phase 29 Plan 02: One folding policy, pinned rule by rule, and a reset --hard ban for the fold skill

**Folding policy FOLD-1..FOLD-10 written once and pinned by a doc-contract check, AGENTS.md points at it, and fold skill files are structurally barred from reset --hard**

## Performance

- **Duration:** 5 min through the last task commit (18:55:47 to 19:00:22 -03:00)
- **Started:** 2026-11-04T18:55:47-03:00
- **Completed:** 2026-11-04T19:00:22-03:00 (last task commit)
- **Tasks:** 2 of 2
- **Files modified:** 3 (plus the new policy file)

## Accomplishments
- `skills/ai-kit-commit-fold/references/folding-policy.md` states every SPEC R1 rule once, one rule per bullet with its id in bold, plus the grouping limit and the enforcement map.
- `tests/test_arch.py` pins each rule by a stable phrase. Removing a rule's bullet names that rule id (one subTest per rule). Reordering the bullets and re-wrapping the text at 40 columns both keep the check green.
- `AGENTS.md` Workflow now names the policy path and keeps the word "compaction". The restated sentence is gone.
- `check_no_reset_hard` flags `reset --hard` in text and the argv form in list or tuple literals. `update-ref` is not flagged. The live scan covers the fold skill folder, excluding the policy text and `evals/`.
- `test_rule8_no_shell_true_in_spec_family` now also scans `skills/ai-kit-commit-fold`.

## Task Commits

1. **Task 1: policy text, doc-contract pins, AGENTS.md pointer** - `8431540` (docs)
2. **Task 2: reset --hard structural rule, shell-true scope, full run and close** - `7e5b387` (test)

**Plan metadata:** this SUMMARY is committed as a third commit after the two task commits; it is not counted in `commits:` above (measured at write time, per protocol).

## Files Created/Modified
- `skills/ai-kit-commit-fold/references/folding-policy.md` - the one folding policy text (new)
- `tests/test_arch.py` - `POLICY_RULES`, `normalize_policy`, `missing_policy_rules`, `drop_policy_bullet`, `reverse_policy_bullets`, `rewrap_policy`, `check_no_reset_hard`; tests `test_folding_policy_states_every_rule`, `test_agents_md_points_to_the_folding_policy`, `test_fold_skill_never_resets_hard`, `test_policy_rule_removal_is_caught`, `test_policy_rules_survive_reordering`, `test_policy_rules_survive_rewrapping`, `test_reset_hard_flags_each_form`, `test_reset_hard_allows_update_ref`; shell-true scope extended
- `AGENTS.md` - Workflow folding bullet now points at the policy

## Decisions Made
- One policy copy, referenced from AGENTS.md (no restated rule text), so drift is caught by the pin rather than by review.
- Phrase matching after normalization (lowercase, emphasis and list markers removed, whitespace collapsed): layout is not part of the contract.
- The reset --hard ban is structural and covers the fold skill folder. The policy text is exempt because it states the prohibition, and `evals/` is exempt because prompts may quote a user asking for it.

## Deviations from Plan

### Process deviations (no code change)

**1. Commit ledger written after the first commit, not before**
- **Found during:** Step 0c (plan commit ledger), checked at SUMMARY time
- **Issue:** Protocol 0c says to write `gsd-plan-head-before-29-02` before the first commit. I did not write it until after the two task commits.
- **Fix:** Wrote it from the base commit `358113ad9a4aa1cfa49436075b488461f96112f8`, which the spawn-time branch check had verified as HEAD before any commit. HEAD did not move before the first commit, so the recorded base is the same value the ledger would have held.
- **Files modified:** none in the repo (ledger lives in the worktree git directory)
- **Commit:** n/a

**2. Cwd-drift check run as a top-level comparison, not the full sentinel block**
- **Found during:** Task 1 commit (protocol 0a)
- **Issue:** I checked `git rev-parse --show-toplevel` against the worktree path before staging, but did not run the full sentinel-file block verbatim.
- **Fix:** Top-level matched the worktree path before every staging step. No drift occurred.
- **Commit:** n/a

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff B905 on `zip()` without `strict=`**
- **Found during:** Task 1 commit (pre-commit ruff hook)
- **Issue:** `reverse_policy_bullets` used `zip()` without `strict=`, which the ruff config (B905) rejects.
- **Fix:** Added `strict=True`. Both sides of the zip have the same length (both come from the same slot list), so the flag cannot change behavior. Re-staged and re-ran the hooks; no `--no-verify`.
- **Files modified:** `tests/test_arch.py`
- **Verification:** ruff passed; `tests.test_arch` and `tests.test_ai_kit_project_rules_agents` passed.
- **Committed in:** `8431540` (Task 1)

**Total deviations:** 1 auto-fixed (Rule 1), 2 process notes. **Impact on plan:** none on scope; all acceptance criteria met.

## Verification

- `grep -cE '\*\*FOLD-(10|[1-9])\*\*'` on the policy file: 10
- `is not detected` on the policy file: 1 match
- `folding-policy.md` in AGENTS.md: 1 match
- `logically-grouped, buildable commits` in AGENTS.md: 0 matches
- `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_ai_kit_project_rules_agents`: exit 0 after Task 1 (test_arch 81 tests, test_ai_kit_project_rules_agents 84 tests); after Task 2 test_arch runs 84 tests, exit 0
- `scope.py test` (the plan's one `make test`): exit 0; log at `tmp/p29/02/make-test.log` (unit 80/80, unit-uv 1/1, integration 6/6, e2e 23/23, `tests/test_install.sh` 45 passed 0 failed, arch 1/1)
- `scope.py close`: last line `clean`, exit 0. Its `reported (not this run)` block lists other plans' temp dirs and other sessions' processes; those are not this run's leftovers and were not touched.

## Issues Encountered
- The first Task 1 commit attempt failed on the ruff B905 finding above; fixed and re-committed.
- The Bash tool refused compound `git` forms in this worktree. I split them into plain per-command calls, all from the worktree path.
- The pre-commit ruff hook created a gitignored `.venv` at the worktree root. It is not staged and disappears with the worktree.

## Known limits
- The live fold-skill scan currently covers only the exempt policy file in this checkout, because the fold scripts come from plan 29-01 and have not merged here. The check gains coverage when they do.
- The policy's grouping limit is a documented limit, not a test: a feature that imports a file a later feature adds is not detected by rule grouping.

## Known Stubs
None.

## Threat Flags
None. T-29-25 is mitigated by the per-rule doc-contract pins and the AGENTS.md pointer-only sentence.

## jev-fast-decision call log
None. No genuine 2-4 option choice came up during execution. The one classification (the ruff B905 failure) was read straight from the hook output as a real defect and fixed with `strict=True`; it was not sent to jev.

## Next Phase Readiness
- The policy text is ready for plan 29-06's `policy_missing` refusal, which reads the same rule ids.
- Plan 29-01's fold scripts will fall under the reset --hard scan and the shell-true rule once merged.

## Self-Check: PASSED

- Files exist: `skills/ai-kit-commit-fold/references/folding-policy.md`, `tests/test_arch.py`, `AGENTS.md`
- Commits exist and are ancestors of HEAD: `8431540`, `7e5b387`
- `scope.py close`: `clean`

---
*Phase: 29-logical-commit-folding-and-the-shared-jev-ladder*
*Completed: 2026-11-04*
