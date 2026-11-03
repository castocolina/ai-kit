# Phase 29: Logical-commit folding and the shared jev ladder - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-03
**Phase:** 29-logical-commit-folding-and-the-shared-jev-ladder
**Mode:** interactive path: standard discuss mode (`--analyze --all --batch`) with the owner through the orchestrator, decision ladder (owner-requested items only; none requested), best over easy (`mvp-mode` inactive, DESIGN-01)
**Areas analyzed:** where the folding step lives and when it runs; how features are grouped; the jev ladder move; fold mechanics

## Assumptions Presented

The analyzer was not run: in the interactive path it runs only when the owner asks, and the owner answered the
batches directly. No advisor researcher was spawned (no `USER-PROFILE.md`).

| Assumption | Confidence | Evidence |
|---|---|---|
| GSD offers no per-plan lifecycle point | Confident | `loop-hook-dispatch.md` lists the points; `execute:wave:post` is the closest |
| A third-party GSD capability can run the fold at `execute:wave:post` | Unclear | `capability install <spec>` exists; which hook form can run a script is unproven, so D-02 spikes it |
| Worktree mode puts a merge commit in each plan's range | Confident | `worktree-safety.cjs` merges with `--no-ff`; `use_worktrees` defaults to true |
| No caller may reach into another skill's files | Confident | owner rule; DIST-03 copy installs |

## jev screening

The owner asked for no item to be screened, so no ladder call was made.

| Item | laya | typesafe | Outcome |
|---|---|---|---|
| Fold home | – | – | Owner choice after a clarification round: temporary skill, moved in Phase 45 (D-01) |
| GSD call point | – | – | Owner choice (recommended), spike first, back to the owner on failure (D-02) |
| superpowers call point | – | – | Owner choice (recommended) plus the plan's explicit fold step and REV-08 (D-03) |
| Plan range and merge-back | – | – | **Own reasoning:** follows the live merge-back fact (D-04, D-05) |
| Rule-based grouping source | – | – | Owner choice (recommended) (D-06) |
| jev's role in grouping | – | – | Owner choice (recommended) (D-07) |
| Plan-docs placement | – | – | Owner choice (recommended) (D-08) |
| Tangled features | – | – | Owner choice (recommended) (D-09) |
| Fold mechanics | – | – | Proposed as discretion, accepted by the owner (D-10) |
| Policy text home | – | – | **Own reasoning:** one copy in the fold skill, a drift-tested copy in Phase 47 (D-11); not ledgered, nothing blocks |
| jev entry point | – | – | Owner choice (recommended) (D-12) |
| Lookup for code callers | – | – | Owner choice (recommended) (D-13) |
| `decide.py` | – | – | Owner choice (recommended) (D-14) |
| Consent ask | – | – | **Own reasoning:** follows SPEC R10's black-box rule (D-15); not ledgered |
| Judge bar list | – | – | **Own reasoning:** every SKILL.md D-01..D-14 change (D-16) |

## Live facts that changed the plan

- gsd-core 1.18.0 merges each executor worktree back with `git merge --no-ff` ("chore: merge executor worktree");
  the SPEC's edge row "a merge commit inside the range refuses the fold" would refuse every worktree-mode plan.
  SPEC R5 was amended and the row superseded (D-05).
- A `step` hook's `ref.command` runs only gsd-tools subcommands, and `ref.skill` is dispatched as `gsd-<skill>`;
  so the GSD extension's hook form is the spike's open question (D-02).
- `ai-kit-spec-execute-gsd` is removed in Phase 31, so no fallback is planned through it (D-02).

## Corrections Made

- The owner asked for an analysis of skill versus rules for the fold's home before choosing; the result moved the
  decision from "a standalone skill" to "a temporary standalone skill that moves into `ai-kit-project-rules` in
  Phase 45" (D-01; RULE-27 and Phase 45 criterion 7 added).
- The owner added: superpowers plans carry an explicit fold step, and spec-review flags a plan without it (D-03;
  REV-08 and Phase 40 criterion 6 added).
- The owner added: a failed `execute:wave:post` spike returns to the owner instead of falling back (D-02).

## External Research

None in discuss. The spec step's gh-stack 0.3.0 probe and the GitHub stacked-PR public preview feed Phase 29.1.
