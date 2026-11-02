---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 07
subsystem: infra
tags: [cross-ai, runner, dogfood, template-7, gates]

requires:
  - phase: 25-06
    provides: runner template 7 with the failure ladder
provides:
  - the dogfood runner .planning/scripts/cross-ai.mjs on template 7, pristine, CONFIG kept
  - project-wide gates green on template 7
affects: [25-08, 25-09, 25-10, 25-11]

actuals:
  tasks: 2
  commits: 1

key-files:
  created: []
  modified:
    - .planning/scripts/cross-ai.mjs

key-decisions:
  - "The router route for router-env/* lanes is confirmed by the owner (25.1 D-15); the dispatch passes --route-pi router instead of editing the dogfood CONFIG, so the copy stays pristine"
  - "The real-home mtime baseline the plan assumed (recorded before 25-01) did not exist; it was recorded late, after 25-06"

duration: about 15 min of orchestrator work, plus the gate runs
completed: 2026-10-24
---

# Phase 25 Plan 07: dogfood runner on template 7 — Summary

**The live supervisor of the delegated plans now runs template 7 (the owner's failure ladder),
re-rendered by `ensure-runner` with the project's CONFIG kept; every project-wide gate is
green.**

## Task 1: re-render (5b4ec21)

- Before: template 6, `pristine`; CONFIG `prefer` `pi, cursor, opencode`, `outerTimeoutS`
  1800, `routerBacked` `{}` (`tmp/p25/07/before.json`).
- `ensure-runner --cwd .`: `{"ready": true, "runner": "change", "guidance": null, "notes": []}`.
- After: line 2 `template=7 sha256=<64 hex>`, `script_state` `pristine`; the four kept keys are
  byte-equal to before; `attemptTimeoutS` 0 and the older `retries` key kept; the non-CONFIG
  body equals the template's apart from line 2. The plan's `<automated>` check printed
  `dogfood ok`.
- `node .planning/scripts/cross-ai.mjs --self-test`: `self-test ok`. `--print-argv`:
  `cross-ai: a run uses pi only`.
- `--classify-only` on `router-env/my-coding`, cli `pi`, stderr `429: {"type":
  "usage_limit_reached"}`: `{"status":"quota","rule":"vendor-usage-limit-reached",
  "pattern":"verified","route":"router-inferred"}`.

## Task 2: project-wide gates

| Gate | Result |
|---|---|
| `uv run ruff check tools skills tests` | exit 0 |
| `uv run pyright` | exit 0 (0 errors) |
| `uv run vulture` | exit 0 |
| `make test` | exit 0 (second run; unit 54/54 modules, then the integration, e2e and arch tiers) |
| `make validate` | exit 0 (second run) |

The first run of `make test`/`make validate` failed on one module,
`tests.test_pi_live_tools`: Phase 22's skill-judge gate compared its evidence with the
curated-config skill at HEAD, so the skill change in quick task 261024-ryk broke a closed
phase's test. Fixed at the cause in 8513b1f (the digest is checked at the evidence's
`JUDGED_COMMIT`, with a non-vacuity case); both gates then passed.

## Deviations

- The real-home mtime baseline `tmp/p25/real-home-mtimes.txt` was recorded at this plan, not
  before 25-01 as the plan says. Real-config audits at 18:20 and 20:23 found no executor write;
  the two 17:35 changes (`~/.cursor/cli-config.json`, `~/.config/ai-kit/review-spec-trust`) came
  from another session (an agent-toolkit spec-review trust record and Cursor's cache).
- The dispatch for 25-08..25-10 passes `--route-pi router` (owner confirmation, 25.1 D-15).

## Issues Encountered

- See Task 2: the stale Phase 22 digest gate.
