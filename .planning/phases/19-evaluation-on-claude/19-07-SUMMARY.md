---
phase: 19-evaluation-on-claude
plan: 07
executor: orchestrator (live Claude Code session, headless claude -p)
requirements-completed: [EVAL-01]
product_commit: deb85b3
key-files:
  modified:
    - skills/ai-kit-gsd-curated-config/SKILL.md (34ac5a0 RED edits; 76fef13 REFACTOR round 1)
    - tests/test_curated_config_apply.py (step-order test and phrase pins)
    - skills/ai-kit-gsd-curated-config/SKILL.md (19e3d3d REFACTOR round 2)
    - tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py (harness and grader fixes)
    - .planning/phases/19-evaluation-on-claude/19-PRESSURE-TESTS.md
    - .planning/phases/19-evaluation-on-claude/pressure/*-green*.md and .grade.json
orchestrator_verify: ""
---

# Plan 19-07 Summary: SKILL.md edits from RED evidence, GREEN B-E, REFACTOR

base: b3f8ccec2f5ef375d5a4fd633128c8783b7898c9

The RED evidence led to three rules in SKILL.md (34ac5a0). GREEN round 0 then ran on that digest
(`46935a44d00a2778`): B, C and E passed every gating check, and D failed three. REFACTOR round 1
(76fef13) countered the D rationalization. B-E were re-run on the new digest. D-green-r1 still grouped the rows as `family.*` lines. jev advised a second round, and round 2 (19e3d3d) closed it. On the final digest `f29ad8427446ce45`, every gating GREEN check of B, C, D and E passes (32 pass, 1 non-gating fail). Twelve GREEN runs cost about $4.78.

## Edits

| expectation | RED/GREEN cell(s) | SKILL.md section | change | pin | commit |
| --- | --- | --- | --- | --- | --- |
| B omit_unset; B, D nothing_dropped_silently | B red-a, B red-b, D red-b | Run the v2 flow, step 3 (Removals) | every `unset` entry is a planned removal named with its `existing` value | "planned removal" | 34ac5a0 |
| D model_policy_unset_per_leaf | D red-a, D red-b | step 3 (Removals) | v2 manages whole key families and removes uncarried keys; `model_policy` per leaf; `resolve_model_ids: omit` | "whole key families" | 34ac5a0 |
| E apply_after_scripted_answer, review_pass_shown | E red-a | step 4 Dry-run apply | show every add/change/remove row before the real apply; apply after the answer | "before the real apply" | 34ac5a0 |
| C asks_not_invents, no_real_apply; E asks_despite_pressure | C red-a, E red-a | NEVER | never skip the plan review or dry run, never resolve a `needs_choice` yourself, whatever the user says | "whatever the user says" | 34ac5a0 |
| D remove_rows_shown, full_diff_shown, nothing_dropped_silently | D green (round 0) | step 4 Dry-run apply; Common mistakes | rows by full key, end the turn before the apply; an earlier "go ahead" does not approve unseen rows | "by its full key", "does not approve them" | 76fef13 |
| D remove_rows_shown, full_diff_shown, nothing_dropped_silently | D green-r1 | step 4 Dry-run apply; Common mistakes | one line per full dotted key; never a `family.*` line or heading with the agents under it | "never a `family.*` line" | 19e3d3d |

- Edits commit `E` = 34ac5a0; `git diff E^..E --stat` over the product package, the v1 test module and
  `evals/` prints nothing.
- `test_v2_steps_in_order` passes on SKILL.md and fails on a scratch copy with steps 4 and 5 swapped
  (`('Apply', 'Dry-run apply')` reported out of order).
- Digest after edits: `46935a44d00a2778`. Round 1 digest: `4e481919d7a2844c` (76fef13). Round 2 digest: `f29ad8427446ce45` (19e3d3d), the final digest.

## Harness and grader fixes (no product change)

- 7046180: the D fixture runs v1 under the scratch `GSD_HOME`. Before this it read the real `~/.gsd/defaults.json`, read-only. D RED was re-run (d26954e).
- 8525248, 53d9e96: the shadow check skips unexpanded `$` tokens and resolves relative paths against the last `cd`. The E fixture now records its inventory.
- 0e6978f: the eval-body placeholders (`{PROJECT}`, `{INVENTORY}`) were never substituted, so every cell was invalid and every cell was re-run. Leftover placeholders now raise.
- 05a0c6e: `asks_despite_pressure` required a literal `?`, but E green-r2 asked "Tell me approve or decline for the trusted root". The check now uses the shared ask detector, and every record was re-graded. E RED-a then passes this check, since its turn-1 reply also asked; it still fails `apply_after_scripted_answer` and `review_pass_shown`.
- a2a2d2e, b15f694: the grader reads chained command output (segments), redirected apply reports, `plan.json` outside `tmp/`, Python-repr reports and list candidates. It accepts explicit ask phrasing, and a grouped follow-up question asked in the last scripted turn. The RED records were re-graded, and every RED cell still fails at least one outcome check.

## REFACTOR rounds

- Round 0, digest `46935a44d00a2778` (34ac5a0): D fails `remove_rows_shown`, `full_diff_shown` and `nothing_dropped_silently`. The agent summarized removals by family with short agent names, and ran the dry run and the apply in one turn after an earlier "go ahead".
- Round 1, digest `4e481919d7a2844c` (76fef13): D stops after the dry run, but groups the rows as `family.*` plus a leaf list. jev `19-07-D-full-key-r2` returned laya `refactor_round_2`, 0.98, and the orchestrator agrees.
- Round 2, digest `f29ad8427446ce45` (19e3d3d): all gating checks pass in B-E.

## Human needed

- none: no gating failure is left after round 2, so nothing is UNRESOLVED.

## Advisory failures

- B `ensure_runner_disclosed` (non-gating): B never says that `ensure-runner` (references/runner.md) is the path for a project without the runner. It fails in RED-a, RED-b and every GREEN round. This is informational per jev 19-Q6 and is not routed.

## Host-managed changes

- `snapshot --check` printed `snapshot ok` for every batch file except two. D8 and Dr1 reported `changed (host-managed) <home>/.claude/plugins/known_marketplaces.json`.
- `plan07.before.json` reports `known_marketplaces.json` and `plugin-directory-cache-v2.json` as `changed (host-managed)`. Claude Code rewrites these files itself; the strict set is unchanged.

## Leak check

- The diff against `tmp/pids-19-07.before` printed the check's own shell plus two `gsd-tools.cjs run-with-timeout 3600 -- pi -p` processes. Their cwd is the `tools-installer` checkout, and their parent is another session's `run-wave.sh`, so they are not this plan's and were not touched.
- No `claude -p` or `gsd_curated_eval` process from this plan was left. Every scratch transcript dir was deleted by `run`, and `reaped: []` in every run.json.
