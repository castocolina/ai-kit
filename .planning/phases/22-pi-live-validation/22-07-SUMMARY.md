---
phase: 22-pi-live-validation
plan: 07
subsystem: testing
tags: [pi, skill-judge, close-out]
executor: orchestrator
requirements-completed: []
key-files:
  modified:
    - .planning/phases/22-pi-live-validation/22-SKILL-JUDGE.md
    - .planning/phases/22-pi-live-validation/22-SMOKE-PI.md
---

# 22-07 Summary: skill-judge and the automated close-out

- The skill-judge loop ran with the owner's judge set (one clean-context native Opus subagent
  plus opencode router-env/my-plan-review): `22-SKILL-JUDGE.md` records PASS for the pi wording
  (b60899b).
- `22-SMOKE-PI.md` gained `## Phase status`: the automated part is complete and the phase is
  `human_needed` (9dc2ac8).
- The code review and its fixes followed (a53569b, cbf7214, 5262e92, 8bfa224; record in
  `22-REVIEW.md`, 3d0b800).
- Leak check (`ps` against `tmp/pids-22-07.before`, cross-ai/opencode run processes) printed
  nothing. `tmp/judge` and the snapshot file were removed.

## Owner items for `/gsd-verify-work 22`

- Required: C1 (real pi RPC capture), S1-S5 (interactive smoke) and D9 (environment
  confirmation) in `22-INTERACTIVE-PI.md`.
- Optional: L3a-L3c (live steering arms; only an L3a or L3c pass lifts the verdict).
- Then the kit's `## Orchestrator close-out`. Until then the SKILL.md pi label stays
  `not live-validated` and the verdict stays `session-steer (static + mock evidence)`.
