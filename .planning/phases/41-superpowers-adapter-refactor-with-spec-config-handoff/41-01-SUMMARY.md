---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 01
subsystem: ai-kit-spec-execute-superpowers (skill text consolidation)
tags: [superpowers, adapter, pinned-resume, owner-stop, doc-contract]
requires: []
provides:
  - "references/state-management.md `## Pinned resume`: the one home of the pinned-resume rule (renamed from `## Initial and resume values`)"
  - "references/resolution-stops.md `## Owner stop` (title `# Steps 2 and 3 reference: owner stops`): the one stop-versus-continue list, subsections Exit codes and the untrusted-config line, `no_candidate` and `quota_exhausted`, Rounds 4–5 re-resolution, Dispatch-time stops"
  - "tests/test_adapter_single_definitions.py: one marker per home, each quoted rule only in its home (per occurrence), home links resolve, required source links present, non-vacuity by planted copies"
affects: [41-02, 41-04, 41-06, 41-09, 41-11]
key-files:
  created:
    - tests/test_adapter_single_definitions.py
  modified:
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/state-management.md
    - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
    - skills/ai-kit-spec-execute-superpowers/references/escalation.md
    - skills/ai-kit-spec-execute-superpowers/references/quota-wake.md
    - skills/ai-kit-spec-execute-superpowers/references/session-wake.md
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - tests/test_ai_kit_spec_superpowers.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "Plan base for the scope check is d4e9989 (HEAD at lane start: the neutral docs(41) commit that set STATE.md's plan line before the first lane), not 1420a53"
metrics:
  tasks: 3
  commits: 3
---

# Phase 41 Plan 01: one home for the pinned resume and the owner stop Summary

The superpowers execute adapter's pinned resume is defined once, under `## Pinned resume` in
references/state-management.md, and every stop-versus-continue decision of Steps 2 and 3 once, under `## Owner stop` in
references/resolution-stops.md (resolve-time exit codes, `no_candidate`, both `quota_exhausted` branches, the rounds 4–5
re-resolution stops including the empty or unknown anchor, and the dispatch-time `ok` / `quota_cycle` / `quota` / `real_error`
outcomes, the report rule and the failed native dispatch). SKILL.md, escalation.md, quota-wake.md, session-wake.md,
state-management.md and dispatch-external-cli.md keep only mechanics and link the homes (`references/...#anchor` from SKILL.md,
sibling-relative inside references/). Schedule-or-stop keeps only its pointer, the re-arm block and the `CronCreate` paragraph;
Classify keeps the `ok` handling in order. The quota-wake prompt block is byte-identical. Behaviour does not change.
SKILL.md went from 300 to 279 lines (294 after Task 1, 286 after Task 2); body 3406 -> 3265 words.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | e8c3377 | docs(41-01): define the pinned resume once and pin it with a doc-contract test |
| 2 | ad9acca | docs(41-01): define the owner stop once and move the dispatch outcomes into it |
| 3 | ccb2b78 | docs(41-01): move the rounds 4-5 and resumable-state stops into the owner stop |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 344 s,
Task 2 129 s, Task 3 148 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Acceptance: SKILL.md 294 / 286 / 279 lines after Tasks 1 / 2 / 3; `## Pinned resume` 1, old heading 0; `## Owner stop` 1;
  `### Rounds 4–5 re-resolution` 1; `references/resolution-stops.md#owner-stop` in SKILL.md 2 then 6; "Do NOT load it for any
  other mode at this mode check." 1; "Only a classified" and "a failed external dispatch stops for the owner" gone from
  dispatch-external-cli.md; every quoted rule (`re-dispatches unchanged at any`, `is only the source of `ladder_keys``, the
  dispatch outcomes, `not a stop; Classify continues`, the resumable-state stop, `cannot honor the capability bump`,
  `no pick is a verified bump`) found only in its home; plan-base.txt holds the full sha d4e9989...; scope check from it lists only
  `files_modified` paths.
- `tests.test_adapter_single_definitions` (9), `tests.test_ai_kit_spec_superpowers` (174), `tests.test_quota_policy_text` (20),
  `tests.test_spec_chain_text` (40), `tests.test_skill_evals_shape` (6), `tests.test_skill_text_history` (45),
  `tests.test_gate_scope` (62): each `1/1 modules passed` after every task.
- Text review of the diffs: the moved `False` bullet is verbatim (only "there" -> "above"); details dropped from SKILL.md
  (Seed keeps the round and anchor, Restore prints the injection scalars, the `ok` line's "2. Handle the report") are still stated
  in state-management.md and in Classify.
- Gates after the plan: unit + arch groups under the watchdog `201/201 modules passed` (peak 6 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each. No e2e module covers the changed
  files (staged mapper), so nothing was deferred to push.

## Deviations

- The lane wrapped two lines of the new test module to pass ruff E501 (docstring and `SKILL_DIR`); no other deviation from the
  plan text. No other existing assertion needed rewriting.
- quota-wake.md's resume paragraph drops "An owner's plain resume keeps it pinned too; Step 2 re-resolves only when the owner
  names a replacement pair", as the plan's replacement text specifies; `## Pinned resume` (pinned at any resume) and
  "Owner-named replacement pair" in state-management.md state it.
