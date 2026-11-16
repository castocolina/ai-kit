---
phase: 32-re-judge-baseline
plan: 05
subsystem: testing
tags: [skill-text, pointer-check, skill-judge, stdlib, pre-commit]

requires:
  - phase: 32-re-judge-baseline
    provides: "32-03 tests/test_skill_text_history.py (history_hits, main_flow, version rule, non-vacuity class); 32-SPEC R9, 32-CONTEXT D-18, D-19"
provides:
  - "tests/test_skill_text_history.py: pointer rules (phase folders and files, backlog ids, decision ids, referee and router names) over every .md a kept skill ships, outside evals/"
  - "Pointers removed from curated-config, spec-config, usage-metrics, spec-discuss references and jev backends; the same limits stated in plain words or as placeholders"
  - "curated-config pins (test_cursor_label_lifted_with_evidence_pointer, test_pi_row_keeps_label_and_states_verdict) on the new phrases"
affects: [32-08 baseline judge run (judges the cleaned text), 32-07 full check]

actuals:
  tokens: 4990    # chars/4 over the base..HEAD diff (19963 chars, diff headers included)
  tasks: 2
  commits: 2      # measured before the SUMMARY commit: git rev-list --count c2faec5..HEAD

tech-stack:
  added: []
  patterns:
    - "Pointer rule: per line, URLs removed, code spans kept (a pointer in a code span still points); a decision id must be a whole token, and a bold format example (`**D-14: ...**`) passes"
    - "Shipped Markdown = every .md under the skill folder except evals/ and __pycache__"

key-files:
  created: []
  modified:
    - tests/test_skill_text_history.py
    - tests/test_curated_config_apply.py
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-usage-metrics/SKILL.md
    - skills/ai-kit-gsd-spec-discuss/references/log-formats.md
    - skills/ai-kit-gsd-spec-discuss/references/decision-table.md
    - skills/ai-kit-gsd-spec-discuss/references/worked-examples.md
    - skills/jev-fast-decision/backends/laya.md
    - skills/jev-fast-decision/backends/typesafe.md

key-decisions:
  - "The pointer rule scans code spans as text: a planning pointer inside backticks still points, so it fails"
  - "Reference pointers become placeholders (`D-<n>`, `NN-SPEC`, `NN D-xx`, `D-<first>..D-<last>`) so the log formats stay teachable; no instruction changed"
  - "Backlog and phase-file mentions are replaced by plain words (`a backlog entry with a goal`, `scheduling is not supported`)"
  - "Frontmatter of every skill is untouched"

patterns-established:
  - "Non-vacuity for the pointer rule: each failing kind (phase folder, phase file, backlog id, referee, decision id, reference-file hit, root README hit) has a fixture that must fail; generic layout paths, NN-SPEC, D-<n>, NN D-xx, bold format examples, JDG-04, ID-07 and URLs pass; evals/ is never read"

requirements-completed: [JDG-05]

duration: not recorded (no start timestamp captured for this plan)
completed: 2026-11-07
status: complete
commits: 2
plan_head_before: c2faec548a3bad0053b2d0c3f96d40e7d878cd56
plan_head_after: c033e40

coverage:
  - id: D1
    description: "Pointer rule over every kept SKILL.md main flow and Evidence section; the tree passes and fixtures fail or pass as the spec says"
    requirement: "JDG-05"
    verification:
      - kind: unit
        ref: "tests/test_skill_text_history.py#TestKeptSkillsCarryNoHistory.test_every_kept_skill_passes"
        status: pass
      - kind: unit
        ref: "tests/test_skill_text_history.py#TestHistoryRulesNonVacuity"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pointer rule over every shipped .md outside evals/; evals/ and root-level README fixtures behave as specified"
    requirement: "JDG-05"
    verification:
      - kind: unit
        ref: "tests/test_skill_text_history.py#TestHistoryRulesNonVacuity.test_evals_markdown_is_never_read"
        status: pass
      - kind: unit
        ref: "tests/test_skill_text_history.py#TestHistoryRulesNonVacuity.test_pointer_in_a_reference_file_fails"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pointers removed from the kept skills; the curated-config pins move to the new phrases"
    requirement: "JDG-05"
    verification:
      - kind: unit
        ref: "tests/test_curated_config_apply.py#test_cursor_label_lifted_with_evidence_pointer"
        status: pass
      - kind: unit
        ref: "tests/test_curated_config_apply.py#test_pi_row_keeps_label_and_states_verdict"
        status: pass
    human_judgment: true
    rationale: "That each edit keeps the instruction unchanged is a judgment on the diff (SPEC prohibition: no behaviour change); the baseline judge run (32-08) re-judges the edited text"

---

# Phase 32 Plan 05: Shipped skill Markdown names no planning artifacts Summary

**Every Markdown file a kept skill ships fails the suite on phase folders and files, backlog ids, decision ids and referee names; the 22 pointers found (8 in SKILL.md files, 14 in references and jev backends) were replaced by placeholders or plain words, and no instruction changed.**

## Performance

- **Duration:** not recorded (no start timestamp captured for this plan)
- **Tasks:** 2 of 2 completed
- **Files modified:** 10

## Accomplishments

- `tests/test_skill_text_history.py`: `PHASE_DIR_RE`, `PHASE_FILE_RE`, `BACKLOG_RE`, `DECISION_RE`, `REFEREE_RE`, `pointer_hits`, `shipped_markdown`; `history_hits` scans every shipped `.md` (`evals/` and `__pycache__` excluded); 33 tests, the new ones are fixture cases that must fail or pass.
- Curated-config's pi and cursor rows keep `not live-validated`, `validated headless` and `pending` without the phase file names; the `(20 D-11)` mention is gone from the review-lane row.
- Spec-config loses `(D-04)`; usage-metrics loses `(D-07)` and both backlog mentions and keeps the manual-only limit in plain words.
- Spec-discuss references use `NN-SPEC`, `NN D-xx`, `D-<n>` and `D-<first>..D-<last>` placeholders; `worked-examples.md` loses backlog `999.2`.
- jev's `laya.md` loses the Phase 21.1 results path; `typesafe.md` loses `(D-07)`.

## Task Commits

1. **Task 1: pointer rules on each SKILL.md, with the SKILL.md pointers and curated-config pins updated** - `81aa4e2` (test)
2. **Task 2: pointer rules on every shipped Markdown outside evals/, with the reference pointers replaced** - `c033e40` (test)

**Plan metadata:** this SUMMARY commit (docs), made after the two task commits.

## Files Created/Modified

- `tests/test_skill_text_history.py` - pointer patterns, `pointer_hits`, `shipped_markdown`, pointer non-vacuity cases
- `tests/test_curated_config_apply.py` - two pins moved to the new phrases
- `skills/ai-kit-gsd-curated-config/SKILL.md` - pi, cursor and review-lane rows without phase file names or D-11
- `skills/ai-kit-spec-config/SKILL.md` - `(D-04)` removed
- `skills/ai-kit-usage-metrics/SKILL.md` - scheduling line and never-invent line without D-07 or backlog 999.2
- `skills/ai-kit-gsd-spec-discuss/references/log-formats.md` - placeholders for SPEC, decision ids and the kept range
- `skills/ai-kit-gsd-spec-discuss/references/decision-table.md` - `D-<n>` placeholders
- `skills/ai-kit-gsd-spec-discuss/references/worked-examples.md` - placeholders, backlog id removed, example line reworded
- `skills/jev-fast-decision/backends/laya.md` - results path removed from the eval paragraph
- `skills/jev-fast-decision/backends/typesafe.md` - `(D-07)` removed

## Decisions Made

- The pointer rule reads code spans as text, so a pointer in backticks fails; URLs are the only removal.
- Each replacement follows the plan's exact edit list; no skill's frontmatter or instruction changed.
- No jev call was made: every edit was fixed by the plan's action list.

## Verification Results

| Command | Exit | Result |
|---|---|---|
| branch check (worktree HEAD, base) | 0 | `branch-check ok: worktree-agent-a1e3af70af2667f58 at c2faec54` |
| `scope.py start` | 0 | `start eb350241 .../tmp/p32/05/run-eb350241` |
| `scope.py selftest` | 0 | `selftest ok` |
| RED Task 1: `tests.test_skill_text_history` before SKILL fixes | 1 | `test_every_kept_skill_passes` failed with 8 hits: curated-config 333 (phase file 22-INTERACTIVE-PI.md), 334 (phase files 21-SMOKE-CURSOR.md, 21-INTERACTIVE-CURSOR.md), 338 (D-11); spec-config 330 (D-04); usage-metrics 43 (backlog 999.2, D-07), 313 (backlog 999.2) |
| GREEN Task 1 targeted: `tests.test_skill_text_history tests.test_curated_config_apply tests.test_ai_kit_usage_metrics tests.test_cross_ai_skill_text` | 0 | 4/4 modules ok (30, 111, 163, 30 tests) |
| Commit `81aa4e2` hooks | 0 | staged-tests 31/31 modules passed |
| RED Task 2: `tests.test_skill_text_history` before reference fixes | 1 | 14 hits: spec-discuss decision-table 64, 70 (D-24); log-formats 51 (20-SPEC.md), 60 (D-08), 95 (D-14), 96 (D-24), 114 (D-01, D-06); worked-examples 14 (D-16), 24 (D-19), 47 (backlog 999.2), 54 (D-21); laya 57 (phase folder 21.1-...); typesafe 18 (D-07) |
| `hits.py` over the kept skills after all fixes | 0 | `total 0` |
| GREEN Task 2 targeted: `tests.test_skill_text_history tests.test_ai_kit_gsd_spec_discuss tests.test_jev_fast_decision tests.test_curated_config_apply` | 0 | 4/4 modules ok (33, 41, 214, 111 tests) |
| Commit `c033e40` hooks | 0 | staged-tests 26/26 modules passed |
| `scope.py test` (`make test`, TMPDIR inside the worktree run dir) | 0 | unit 102/102; unit-uv 1/1; integration 8/8; e2e 25/25; `tests/test_install.sh` 48 passed, 0 failed; arch 1/1; no `failed:` line |
| `make pyright` (TMPDIR set) | 0 | `pyright ... Passed` |
| `grep -c "validated headless from a cursor-agent session (local install"` on curated-config | 0 | 1 (baseline 0) |
| `grep -c "manual only.$"` on usage-metrics | 0 | 1 (baseline 0) |
| `grep -c "D-<n>"` on log-formats | 0 | 2 (baseline 0) |
| `grep -c "a backlog entry with a goal"` on worked-examples | 0 | 1 (baseline 0) |
| `scope.py close` | see return message | run after this SUMMARY commit |

## Issues Encountered

- The planner's note said execute-superpowers keeps a `18.1-...` pointer. It is in Python comments (`ai_kit_spec_superpowers/cli.py`), not a shipped `.md`, so the rule does not reach it and it was left as is.
- Spec-config's coverage line moved from 332 to 330 since the planning run; found by text, as the plan's rails require.

## Known Stubs

None.

## Threat Flags

None. The change touches skill text, pins and the history check; no new endpoint, auth path or write path.

## Out-of-scope pointers (not changed; for a follow-up)

These are not shipped `.md` files, so SPEC R9 does not reach them. They still name planning artifacts:

- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (lines 53-54, 263-264) carries `21-SMOKE-CURSOR.md` and `21-INTERACTIVE-CURSOR.md` in a runtime label. `tests/test_ai_kit_spec_runtimes_table.py:109` pins `21-SMOKE-CURSOR.md`. Both are shown-text code, so the label needs a plan of its own.
- `tests/test_ai_kit_spec.py` (comments and a `skipTest` reason) and `tests/test_pi_live_tools.py:309` name `22-INTERACTIVE-PI.md`.
- `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/*.py` comments name phase ids (`18.1`, `D-20`, `B-IN-05`).
- `tests/fixtures/archived/**` is frozen history, not read by the check.

## Commit ledger note

The protocol's pre-first-commit ledger (`gsd-plan-head-before-32-05` in the git dir) was not written before the first commit. `commits` and `plan_head_before` are measured from `tmp/p32/05/base_sha` (`c2faec5...`, the HEAD before this plan's first commit), which gives the same count.

## Self-Check: PASSED

- `tests/test_skill_text_history.py`, `tests/test_curated_config_apply.py` and the seven Markdown edits are present in the worktree.
- Commits `81aa4e2` and `c033e40` are ancestors of HEAD on `worktree-agent-a1e3af70af2667f58`.

---
*Phase: 32-re-judge-baseline*
*Completed: 2026-11-07*
