# Phase 28: Fast, environment-proof gates - Discussion Log (standard discuss mode (`--analyze --all --batch`))

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-03
**Phase:** 28-fast-environment-proof-gates
**Mode:** interactive path: standard discuss mode (`--analyze --all --batch`) with the owner answering through
the orchestrator, decision ladder not used, best design wins over the smallest diff (DESIGN-01)
**Areas analyzed:** commit-stage test selection; host-CLI fakes and enforcement; environment baseline and proof;
self-test load reading; live-project checks and archived checkers

## Assumptions Presented

No analyzer ran: in the interactive path `gsd-assumptions-analyzer` runs only when the owner asks, and the owner
did not. The orchestrating agent presented three batches (10 questions), each with 2-3 options, the
recommended one first, and trade-offs. The owner chose the recommended option for every question.

| Question | Options offered | Owner's choice | Decision |
|---|---|---|---|
| A1 How a staged file maps to tests | name index per commit; recorded trace map; imports only | name index per commit | D-01 |
| A2 How the commit hook runs uv tests | one hook, runner splits by group; two hooks; skip wizard at commit | one hook, refuse without uv | D-02 |
| A3 Where the shared-machinery list lives | explicit set in the runner; derived by use count | explicit set, pinned by gate-scope test | D-03 |
| B1 How real host calls are made impossible | runner tripwire PATH plus shared fakes; per-test PATH | tripwire PATH plus one shared fake helper | D-04 |
| B2 Shape of the host-CLI structural test | AST plus tripwire; AST only; tripwire only | AST rule with non-vacuity, runner fails on tripwire log | D-05 |
| B3 Baseline env and the six-environment proof | runner baseline plus separate matrix target; matrix in `make test`; per-test only | runner baseline plus `make test-env-matrix` | D-06, D-07 |
| B4 Tests of wall-clock-budget code | fix clock or budget in tests; env var budget; load scaling | fix through `_monotonic` or the constant | D-08 |
| C1 How the self-test reads load | loadavg per CPU clamped 1-4; plus Linux pressure; calibration spin | loadavg per CPU, injection only under `--self-test` | D-10 |
| C2 Home of the live-project checks | `make check-dogfood` plus pre-push hook; doctor step; make target only | `make check-dogfood` plus pre-push hook | D-11 |
| C3 Archived-phase checkers | copy checker and data into fixtures; move checkers into `tools/` | copy with frozen-history header | D-12 |

## jev screening

The owner asked for no item to be screened, so no backend was called.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| All ten questions | – | – | **Owner answered directly:** D-01..D-08, D-10..D-12 |
| Outside-tool move (SPEC R6) | – | – | **Own reasoning:** follows SPEC R6 directly; module split left to the planner (D-09, not ledgered, blocks nothing) |
| `.planning/` rule home (SPEC R9) | – | – | **Own reasoning:** either structural file fits; planner's choice (D-13, not ledgered) |
| Before-time record (SPEC R3) | – | – | **Own reasoning:** the spec-step measurement is the before time (D-14, not ledgered) |

## Live facts that changed the plan

- The goal-prompt eval module takes 163 s with host CLIs installed and 4 s without; it makes all 80 of its host
  calls through the product CLI it runs as a subprocess, so a structural rule over test sources alone cannot see
  them. This made the runtime tripwire a required layer (D-04, D-05).
- 81 of 95 test modules reach code without imports, so the requirement's "mapped through imports" is amended in
  REQUIREMENTS.md (GATE-01) and ROADMAP.md (criterion 1) to name the name index (D-01).
- The push wait re-measured at 184 s against the 2.5 minutes recorded on 2026-11-02; GATE-02 and ROADMAP
  criterion 2 carry the re-measured baseline and the 60 s target (SPEC R3).
- The precompact header-count failure did not recur under CPU load; shortening its 8 s budget in-process
  reproduced it, so the fix pins the clock or budget in tests instead of scaling it (D-08).

## Corrections Made

None. Every answer was the recommended option.

## External Research

None needed; every fact came from the checkout and live runs (`tmp/p28/`, gitignored).
