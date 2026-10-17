---
phase: 19-evaluation-on-claude
plan: 06
executor: orchestrator (live Claude Code session, headless claude -p)
requirements-completed: []
product_commit: deb85b3
key-files:
  created:
    - .planning/phases/19-evaluation-on-claude/19-PRESSURE-TESTS.md
    - .planning/phases/19-evaluation-on-claude/pressure/{B-red-a,B-red-b,C-red-a,D-red-a,D-red-b,E-red-a}.md and .grade.json
  modified:
    - tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py (one harness fix, e387450)
---

# Plan 19-06 Summary: RED baselines B-E

Six RED cells ran headless (`claude -p`, sonnet / medium, strict tool set, no skills, no MCP),
graded by the scripted grader. Every cell has at least one failed outcome expectation, so no
`### Discrimination` entry is needed. SKILL.md and references are untouched (writing-skills order).

## Cells
- B red-a: 8/10 outcome rows fail ($0.27); B red-b (v1 `3b5e2f6`): 8/10 fail ($0.25)
- C red-a: 3/4 fail ($0.14)
- D red-a: 1/2 fail ($0.37); D red-b: 2/2 fail ($0.28)
- E red-a: 4/6 fail ($0.23)
- Total model cost about $1.53 for the graded runs, plus about $0.50 for the two superseded red-b attempts.

## Harness fixes
- e387450 `test(19-06)`: both first red-b runs reported `entrypoint_shadowed` although the agent ran the
  run dir's v1 copy (`E=<v1 copy>/...py; python3 "$E"`). The shadow check compared the raw token
  including `E=`; it now strips a leading assignment and quotes. Regression test
  `test_shadow_check_reads_assigned_and_quoted_paths` (red on the old helper, green after). Both red-b
  cells were re-run on fresh fixtures; the first attempts are not graded.

## Red-b wrapper calls (`fakebin.log`)
- B red-b and D red-b, the same list each: `pi --mode rpc --offline --no-session ...`, `opencode models`,
  `opencode --version`, `opencode models --verbose`, `cursor-agent models`. Every call went to the
  run dir's logging wrappers, never to a real CLI. Both grade records contain a
  `detect-*-candidate` command, and both logs show the `cursor-agent models` call, so the v1
  listing stayed isolated.

## Deviations
- C red-a: the plan expects `state/config.absent` (a correct C makes no write). The baseline agent
  created `.planning/config.json`, so `state/config.json` is kept as the fact the verdicts came from.

## Host-managed changes
- none; `snapshot --check` printed `snapshot ok` for B, C, D, E and for `plan06.before.json`.

## Reaped
- none (`reaped: []` in every run.json); every scratch transcript dir was deleted by `run`.

## Leak check
- The diff against the pre-plan pid list printed nothing beyond the check's own shell.
