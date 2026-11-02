---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 11
subsystem: infra
tags: [skill-judge, amendments, gates, cross-ai, runner]

requires:
  - phase: 25-10
    provides: the four skills and docs on the template-7 failure ladder
provides:
  - skill-judge verdicts and twelve reports for the four changed skills (all BLOCKED)
  - the ROADMAP, 25-SPEC and 16.1/18/18.1 amendments for the shipped ladder
  - green phase-tip gates, make e2e-docker included, and the phase status for the owner
affects: [25.1, 26]

actuals:
  tasks: 3
  commits: 26

key-files:
  created:
    - .planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-SKILL-JUDGE.md
    - .planning/phases/25-quota-aware-cross-ai-subprocess-supervision/skill-judge/
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
    - skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py
    - the four SKILL.md files and their references

key-decisions:
  - "Five judge rounds instead of the planned two (orchestrator call after the jev ladder fell back): the findings were concrete defects, several in code"
  - "Verdicts record the round-5 Opus score, the only lane that completed; both referee lanes are BLOCKED with the runner's evidence"
  - "A pristine runner now takes a same-version template fix; the readiness floor is template 7"

duration: about 1 h 30 min
completed: 2026-10-25
---

# Phase 25 Plan 11: skill-judge, amendments, gates — Summary

**All four changed skills are `BLOCKED` at the skill-judge gate: both referee lanes stopped and the
runner switched nothing. The judge rounds found and fixed real runner, hook and readiness
defects. The amendments landed, and every phase-tip gate is green.**

## Task 1: skill-judge (09599b1)

Opus round-5 scores against the bases:
- spec-review: 100 against 97 (passes on the numbers);
- execute-gsd: 96 against 104;
- execute-superpowers: 100 against 110;
- curated-config: 104 against 106.

Both referee lanes stopped:
- my-referee-two crashed in rounds 3 to 5 on an OmniRoute 404 `Combo has no executable
  targets`. It is not in the pattern table, so it is a candidate row for 25.1.
- my-referee-one hit `quota` exit 75 in rounds 1, 2 and 5. Its 5-hour session resets after the
  4-hour cap, so it can't recover in this run.

Code fixes the rounds found, each with tests:
- **Runner** (fdd16bc, with two self-test cases proven red on the old logic):
  - it no longer removes `$HOME/.fake-git-hang` outside the self-test;
  - cycle state is read and deleted only on a confirmed router route;
  - the cap wins over a deadline stop.
- **execute-gsd hook:** `--min cross_ai_timeout=1800` (5fdf76a), and the hook carries the
  catalog-confirmed `--route-<cli>` (bddc455).
- **curated-config:** `router_backed` requires purpose `execute` (1a20c14); readiness floor 7
  (41dbc4b); a pristine runner takes a same-version template fix (b7b0b11).

Text fixes landed in 1faaded..e2bb140, plus ed63b5e after the evidence round (not re-judged).

## Task 2: amendments (6742c8e)

- **ROADMAP:** the Phase 25 line names the shipped ladder.
- **25-SPEC:** `## Acceptance after the owner decision (2026-10-24)` maps each criterion and
  edge. R5 concurrency and idempotency are adapted to the cycle state file. The D-21
  `billing_or_access` behavior is superseded.
- **Upstream decisions:** 18 D-27, 18.1 D-12 and 16.1 D-13 get dated notes.
- `edge_floor check` reports 41 of 41 rows.

## Task 3: gates (78be452)

These all logged `exit=0`:
- `uv run ruff check tools skills tests`;
- `uv run pyright`;
- `uv run vulture`;
- `make test`: unit 55/55, e2e 11/11 modules plus 45 installer checks;
- `make validate`;
- `make e2e-docker`: clean-room PASS.

The container ran with `--rm`. No e2e build process, self-test fake or scratch-rooted `node`
process survived.

## Deviations

- Five judge rounds, not two. The jev ladder fell back on both backends (Laya a 0.61, TypeSafe
  b 0.78), so the orchestrator decided. It fixed rather than recorded, because the findings were
  real defects.
- The 25-08 pin "the GSD hook never carries a route flag" was replaced. It was a scope guard, and
  the per-CLI `routerBacked` gave a direct model router cycles.
- A stale `.pyc` once masked the readiness-floor change. Swapping two same-length values within
  one second keeps the bytecode's mtime and size. Fixed by deleting the bytecode; noted for
  red/green swaps.

## Owner items

- Re-run the referee lanes when they recover.
- The base-score bar for skills that grew with the Phase 25 policy.
- C1-C7.
