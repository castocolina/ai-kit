---
phase: 35-model-discovery-and-catalog
plan: 26
subsystem: judge loop
tags: [skill-judge, loop-35, ai-kit-spec-config, referee-one, referee-two]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-25 spec-config catalog step (the one SKILL.md this phase changes materially)"
provides:
  - ".planning/judge/loops/35.json, verdicts/35/ai-kit-spec-config/r1/{referee-one,referee-two}.json, regenerated REJUDGE.md and facts.json (commit 57859c7)"
  - "verdicts/35/ai-kit-spec-config/r1/fixes.md with the fix commit ad6e7a5 (three high findings fixed under the 3-or-fewer rule)"

key-files:
  created:
    - .planning/judge/loops/35.json
    - .planning/judge/verdicts/35/ai-kit-spec-config/r1/opencode_router-env_my-referee-one.json
    - .planning/judge/verdicts/35/ai-kit-spec-config/r1/opencode_router-env_my-referee-two.json
    - .planning/judge/verdicts/35/ai-kit-spec-config/r1/fixes.md
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json

requirements-completed: []

executor: "orchestrator action (cross_ai false): drivers copied from tmp/judge-34 to tmp/judge-35 with 34 -> 35, no substitute.py; judges opencode:router-env/my-referee-one and my-referee-two only"
---

# Phase 35 Plan 26: loop 35, the judge loop for ai-kit-spec-config

One round. Records commit `57859c7 docs(35-26): loop 35 round 1 re-judge records and report` (only `.planning/judge/` paths); fix commit
`ad6e7a5 fix(35-26): loop 35 round 1 judge findings in ai-kit-spec-config` (commit hook 8/8 modules green). Nothing was pushed by hand.

## Loop 35 bar results

- Round: 1 (of at most 3). Judged set: `ai-kit-spec-config` alone (diff base: the parent of `2614a84`, the commit that added `35-01-PLAN.md`);
  fact-only: `ai-kit-spec-review` (references only, SKILL.md unchanged); `ai-kit-commit-fold` and the project-rules skills were not judged.
- Judges, both configured referees, no substitute, no native judge, no referee-three: `opencode:router-env/my-referee-one`
  (AIKIT-XAI `status=ok cli=opencode exit=0 elapsed=60s attempts=1 cycles=0 tree=clean`) and `opencode:router-env/my-referee-two`
  (`status=ok cli=opencode exit=0 elapsed=90s attempts=1 cycles=0 tree=clean`). Probes: both usable (16 s and 15 s).

| Skill | Round | Worst percent | Grade | Bar | Lowest percent | Prior loop base | Delta |
|---|---|---|---|---|---|---|---|
| ai-kit-spec-config | 1 | 88.8 | B | met | - | - | - |

- Per judge: referee-one 88.8 B (critical 0, high 3), referee-two 88.0 B (critical 0, high 0). `bar_table.py` printed `regex self-check: ok` and
  `unmet.txt: 0 skill(s) not met`. The tool reports the bar as met through the grade clause (grade B or better), so it printed no lowest-percent
  and base cells; both judges' percents (88.8 and 88.0) are above the prior loop's lowest valid percent that the plan names (loop 33: 83.2), so
  no regression beyond judge variation (my comparison, not a tool line; `lanes.py count` printed its own base `last percent 77.6, within 7.0 points of 80`).
- Findings under the fix rule (critical, important, high; `findings.py`): 3, all from referee-one: D8-1 (ranking snippet did not narrow `discovered`
  to the kept runtimes), D8-2 (migrate-only gate sat after Step 1 saved the snapshot and Step 1.5 ran), D8-3 (catalog path resolved only at Step 2.2
  while Step 1.5 commands need it). Row (2) of step 8: bar met, 1 to 3 findings: fix commit, no further round.
- Fix commit `ad6e7a5` (files: SKILL.md, references/catalog.md, references/cli-model-selection.md, evals/evals.json, the two test modules that pin
  the changed eval list and the allowed command list, and `fixes.md`). Two new evals: `edge-declined-runtime-never-presented`,
  `edge-migrate-only-runs-no-setup`. Own run after the fix: 9/9 modules (catalog_text 6, evals_shape 6, check_providers 29, arch_hardcoded_models 14,
  skill_text_history 45, frontmatter 7, cross_ai_skill_text 30, judge_loop 152, gate_scope 62) and `make ruff`, `make pyright`, `make vulture` rc 0.
- Medium and low findings (D1-1, D1-2, D2-1, D3-1, D4-1, D5-1, D6-1, D7-1, D7-2, D8-1 and D8-2 of referee-two, D8-4, D8-5 of referee-one) are not
  fixed: below the fix rule's severity. Notable: description trigger wording (D4-1), SKILL.md length 484 lines (D5-1), trigger-queries count (D7-1).
- Evals gate (`evals_gate.py`): `evals gate: ok` (ai-kit-spec-config holds 12 cases; the scratch skill without evals fails).

## Loop 35 facts for the verifier

- Probes and pool: members `opencode:router-env/my-referee-one`, `opencode:router-env/my-referee-two`; native null; substitutes none.
- `python3 tools/judge_loop.py check .planning/judge`: exit 0 (after the fix commit it prints `ai-kit-spec-config: stale digest (the skill changed after
  loop 35 round 1)` and `facts drift (evals, trigger queries or test modules changed after the last report ...)`, both expected after a fix commit).
- `check .planning/judge --skills ai-kit-spec-config --require-current --gate`: exit 1 after the fix commit (stale digest, by design until the skill's
  next loop; before the fix commit the same form, run as `tmp/judge-35/check.py` at Task 3 step 3, exited 0 with `digest current`).
- `make check-dogfood`: `check-dogfood: ok` (before the round commit and again after the fix commit; the judge-records lines are notes).
- `stale_after.py` (before the fix commit: `stale ok`): after the fix only `ai-kit-spec-config` is additionally stale, by design.

## Stale-digest notes

- `ai-kit-spec-review`: fact-only (cli-profiles opencode.md and codex.md, cross-ai.mjs comments; its SKILL.md is unchanged), never judged.
- Carried from before the loop: ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-execute-superpowers,
  ai-kit-spec-review-checklist, ai-kit-usage-metrics, jev-fast-decision (each changed after its last loop).
- `ai-kit-spec-config`: stale by design after fix commit `ad6e7a5` until its next loop.

## Notes for the orchestrator

- The plan's must-have says both closing commands exit 0, while its Task 3 verification says the `--require-current` form fails after a fix commit; the
  second holds, so that form exits 1 after the fix (recorded above, not worked around).
- `facts drift` on `ai-kit-spec-config` is left in place: the plan does not say to regenerate the report after the fix commit and a regeneration would be a
  further `.planning/judge/` commit; `judge_loop.py report .planning/judge` clears it if the orchestrator wants that.
- Real-config audit (marker-c7a-w13): see the ledger; only the host's own files.

## Self-Check: PASSED
