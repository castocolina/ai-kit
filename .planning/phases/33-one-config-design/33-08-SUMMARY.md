---
phase: 33-one-config-design
plan: 08
subsystem: docs
tags: [config.toml, lanes, roster-rename, skill-text, evals, spec-review, cross-ai]

requires:
  - phase: 33-05
    provides: "config.toml as the one roster file, the legacy review-spec.toml migration and the trust digest these docs describe"
provides:
  - "spec-review SKILL.md and two references name ai-kit's config.toml and its [lanes] roster"
  - "spec-review evals 01-04, the superpowers resolution-stops reference and the checklist orchestrator eval name config.toml"
  - "no Markdown file in the three skill trees names review-spec.toml (scan: md hits 0)"
affects:
  - "Plan 11 SPEC R6 doc scan (this plan removes the .md hits it would flag)"
  - "loop 33 judging of the three skills (stale-digest notes, not judged)"

# Actuals (#2632): chars/4 over the realized diff since the spawn base, not a harness token count.
actuals:
  tokens: 1114
  tasks: 2
  commits: 2
plan_head_before: a55e6af9cca83b527427cda79ed6580cf5c892aa
plan_head_after: cbcb1909d81192a1a31286d9d8d4967c9cd84a53

tech-stack:
  added: []
  patterns:
    - "Fact-only name and path swaps; the untrusted-config warning prefix is left unchanged"

key-files:
  created:
    - ".planning/phases/33-one-config-design/33-08-SUMMARY.md"
  modified:
    - "skills/ai-kit-spec-review/SKILL.md"
    - "skills/ai-kit-spec-review/references/cross-ai-dispatch.md"
    - "skills/ai-kit-spec-review/references/cli-profiles/cursor.md"
    - "skills/ai-kit-spec-review/evals/01-superpowers-plan-routes-writing-plans.md"
    - "skills/ai-kit-spec-review/evals/02-gsd-plan-routes-native-cmd.md"
    - "skills/ai-kit-spec-review/evals/03-generic-doc-direct-edit.md"
    - "skills/ai-kit-spec-review/evals/04-ambiguous-detection-fallback.md"
    - "skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md"
    - "skills/ai-kit-spec-review-checklist/evals/orchestrator-integration.md"

key-decisions:
  - "Applied the exact wording in the plan's context block; no sentence beyond the named lines changed"
  - "The trust prefix `ignoring untrusted project-local config` stays byte-identical in every file, so agents still show trust-local --show before any trust"
  - "The three skills are not judged in loop 33 (D-21); their digests are stale-digest notes"

patterns-established:
  - "Doc and eval renames verified by a scan for the old name in Markdown only; .py hits belong to Plans 07 and 09"

requirements-completed: [CFG-02]

coverage:
  - id: D1
    description: "spec-review SKILL.md, cross-ai-dispatch.md, cursor.md and the superpowers and checklist docs and evals name config.toml and [lanes] instead of review-spec.toml"
    requirement: "CFG-02"
    verification:
      - kind: other
        ref: "python3 tmp/p33/08/scope.py scan (md hits: 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The skill text suite still passes after the renames (trust prefix and frontmatter unchanged)"
    requirement: "CFG-02"
    verification:
      - kind: unit
        ref: "tools/run_unittest_parallel.py tests.test_skill_text_history tests.test_skill_frontmatter tests.test_skill_evals_shape tests.test_ai_kit_spec_superpowers tests.test_cross_ai_skill_text (5/5 modules passed, tests rc: 0)"
        status: pass
    human_judgment: false

duration: unmeasured
completed: 2026-11-15
status: complete
---

# Phase 33 Plan 08: spec-review and related skill docs name config.toml

**Nine Markdown files in three skill trees now name ai-kit's config.toml and its [lanes] roster; no Markdown in those trees still names review-spec.toml.**

## Performance

- **Duration:** unmeasured (no start timestamp was recorded at execution start)
- **Tasks:** 2 of 2 completed
- **Files modified:** 9 (plus this SUMMARY)

## Accomplishments

- spec-review SKILL.md: the `vendor` field now refers to a lane entry in ai-kit's `config.toml`; the untrusted-config trigger names a project-local `.aikit/config.toml` with command-bearing lanes.
- spec-review references (cross-ai-dispatch.md, cli-profiles/cursor.md): roster and trust wording moved to `config.toml` and lanes.
- spec-review evals 01-04, the superpowers `resolution-stops.md` reference and the checklist `orchestrator-integration.md` eval: Step 0.7 and roster wording moved to `config.toml` / `[lanes]`.

## Task Commits

1. **Task 1: spec-review SKILL.md and references name config.toml** - `339d898` (docs)
2. **Task 2: evals and the other skills' references** - `cbcb190` (docs)

## Files Created/Modified

- `skills/ai-kit-spec-review/SKILL.md` - lines 23 and 176: `vendor` lane wording; command-bearing lanes trust wording
- `skills/ai-kit-spec-review/references/cross-ai-dispatch.md` - lines 143 and 192: roster and `.aikit/config.toml` lanes
- `skills/ai-kit-spec-review/references/cli-profiles/cursor.md` - lines 76 and 103: `config.toml` names
- `skills/ai-kit-spec-review/evals/01..04` - Step 0.7 line: `config.toml` `[lanes]` double-mode wording
- `skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md` - line 10: malformed `config.toml` or an old roster that fails to migrate
- `skills/ai-kit-spec-review-checklist/evals/orchestrator-integration.md` - lines 32-33: `config.toml [lanes]` and "a `config.toml` lane pins one"

## Decisions Made

- Applied the plan's exact replacement text; the rest of each file is untouched.
- The warning prefix `ignoring untrusted project-local config` is unchanged everywhere (SKILL.md line 175, cross-ai-dispatch.md line 191).
- Skill judging was not run (D-21: fact-only edits).

## Deviations from Plan

None - plan executed exactly as written.

Process notes (not deviations from the plan's content):

- The scratch scope checker treats a non-zero `git grep` rc as a failure. It was not triggered: `skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py` still holds `LEGACY_NAME = "review-spec.toml"` (D-10), so `git grep` matched with rc 0.
- The `.venv` directory was created inside the worktree by the pre-commit `uv` step. It is gitignored and not part of the commits.

## Issues Encountered

- The first-action worktree check compares HEAD with the spawn base `a55e6af`. After commit `339d898` it reported a base mismatch (exit 42), which is expected once the worktree has its own commits. Before the second commit I verified the invariant directly with `git merge-base --is-ancestor a55e6af HEAD` (passed) and then committed. The orchestrator's check is for spawn time only.
- CFG-02 is not marked complete in REQUIREMENTS.md. `requirements.ready-ids` reports it `blocked`, because a sibling plan also declares CFG-02 and has no SUMMARY yet. The shared-ID gate will let the last declaring plan mark it. This plan lists CFG-02 in `requirements-completed` as the template requires.

## Verification Results

| Command | Exit | Result |
|---|---|---|
| `python3 tmp/p33/08/scope.py test` (after Task 1) | 0 | `5/5 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/08/scope.py scan` (after Task 2) | 0 | `md hits: 0` |
| `python3 tmp/p33/08/scope.py test` (after Task 2) | 0 | `5/5 modules passed`, `tests rc: 0` |
| `git commit` 339d898 (pre-commit: staged-tests, 72 modules) | 0 | `72/72 modules passed` |
| `git commit` cbcb190 (pre-commit: staged-tests, 77 modules) | 0 | `77/77 modules passed` |

Trust prefix check: `rg -n "ignoring untrusted project-local config"` still matches SKILL.md:175 and cross-ai-dispatch.md:191.

## Stale-digest notes (D-21, loop 33)

Not judged in loop 33; these digests are stale for the three skills:

- `ai-kit-spec-review` (SKILL.md, two references, cursor profile, evals 01-04)
- `ai-kit-spec-execute-superpowers` (resolution-stops.md)
- `ai-kit-spec-review-checklist` (orchestrator-integration eval only; the skill body is unchanged)

## Threat Flags

None. Docs and evals only; no new endpoint, auth path, file access or schema.

## Known Stubs

None.

## Next Phase Readiness

- Plan 11 SPEC R6 doc scan has no `.md` hits in these three skill trees for `review-spec.toml`.
- Remaining `review-spec.toml` references in those trees are in `.py` files (Plans 07 and 09, per the plan).
- CFG-02 checkbox waits for the sibling plan that also declares it.

## Self-Check

Checked after writing this file:

- `skills/ai-kit-spec-review/SKILL.md`, `cross-ai-dispatch.md`, `cursor.md`, evals 01-04, `resolution-stops.md`, `orchestrator-integration.md`: present and modified as listed.
- Commits `339d898` and `cbcb190` are ancestors of HEAD.
- `scope.py scan` reports `md hits: 0`; `scope.py test` reports `tests rc: 0`.

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*
