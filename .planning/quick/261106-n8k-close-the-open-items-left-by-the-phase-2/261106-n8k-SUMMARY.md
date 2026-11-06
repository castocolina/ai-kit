---
phase: quick-261106-n8k
plan: 01
subsystem: gates, commit-fold, planning
status: complete
tags: [curated-config, check-dogfood, unit-flow, backlog, review-notes]
key-files:
  modified:
    - tests/test_curated_config_apply_e2e.py
    - tests/gsd_curated_eval.py
    - tools/check_dogfood.py
    - skills/ai-kit-commit-fold/scripts/flow_unit.py
    - skills/ai-kit-commit-fold/SKILL.md
    - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
    - .planning/ROADMAP.md
  created:
    - .planning/todos/pending/2026-11-06-low-risk-review-and-judge-notes-from-phases-28-31.md
commits: [320aafc, 5c375bd, 896fd21, 4c68491]
---

# Quick task 261106-n8k summary

- **Apply no-write guard (320aafc):** gsd-core 1.20.0's curated-config tables are value-equal to the
  1.16.0 fixture; the guarded tests ran 50/0 skipped with the rule widened. The prefix allowlist is now
  a minimum version (1.16.0 or newer runs; older or unparsable skips with a named reason). Backlog
  999.18 moved to Backlog Done.
- **Fold unit flow (5c375bd):** wave:post checkpoint starts an unrecorded unit when HEAD is on its
  branch (jev a, 0.91); `start` on a recorded unit never blocks a re-discuss (open reused, finished or
  ready reused while the branch checks out, merged reported). Amendments in 29.1-CONTEXT D-03.
- **Review and judge notes (896fd21):** one pending todo lists every low-risk item; the goal prompt's
  cleanup line no longer deletes finished backlog entries or directories.
- **Backlog (4c68491):** 999.1 moved to Done (Phase 30.1, FEAT-01).

Verification: `make pyright` passed; `make test` exit 0 in 323 s (unit 100/100, unit-uv 1/1,
integration 8/8, e2e 25/25, install 48/0, arch 1/1); `make check-dogfood` exit 0 with
`no-write guard: 3 attempted, 3 executed, 0 skipped`.

SKILL.md changed materially: `skills/ai-kit-commit-fold/SKILL.md` (needs the judge bar; left to the
orchestrator).
