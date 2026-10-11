# System One decision skill (Plan B)

Moved here from llm-env on 2026-10-11. To be executed later, by another agent.

- `PLAN.md`: the implementation plan. It reworks the global skill `~/.claude/skills/jev-fast-decision` around three backends: local Laya, TypeSafe direct, and OpenCode Zen with a free→paid ladder. It also covers consent rules, the `needs_fallback` handoff, the calibration evals, and the skill-judge evaluation. Task 8's judge lanes are placeholders that the owner fills in at execution time.
- `scratchpad/`: working files from the review rounds.
  - `scratchpad/v3/skill/`: the plan's code (Tasks 0, 2–5 and 7) applied to a copy of the skill. On 2026-10-11 it ran 45 passed, 0 failed. It is reference only: the live skill was not modified.
  - `scratchpad/v3/skill.pre-calibrate/`: the same copy before Task 7.
  - `a_t*.txt`: Plan A (llm-env) snippets.
  - `t2_*` / `t3_*` / `lint/`: Plan B snippets.
- `review-history/`: prompts and reports from the 17 ai-kit-spec-review rounds (iterN-*), plus the owner rulings (`owner-free-decision.txt`, the fixer prompts).

Dependency: Plan B Tasks 5–8 need llm-env's System One, the local Laya service, enabled and healthy on `http://127.0.0.1:8010`. That service comes from llm-env's `docs/superpowers/plans/2026-10-10-system-one-provisioning.md` (Plan A).
