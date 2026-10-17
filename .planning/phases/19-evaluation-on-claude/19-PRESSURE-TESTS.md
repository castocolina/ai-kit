# Phase 19 — pressure tests (EVAL-01)

## Harness

- claude --version: 2.1.302 (Claude Code) (init `claude_code_version` 2.1.302)
- flags (the `run` argv without the prompt): `claude -p --output-format stream-json --verbose --setting-sources project --strict-mcp-config --disable-slash-commands --tools Read,Bash,Glob,Grep --allowedTools Bash,Read,Glob,Grep --model sonnet --effort medium`, `--session-id <uuid>` on turn 1, `--resume <uuid>` on scripted turns
- init fields (every turn of every cell): model `claude-sonnet-5-5`, tools `['Bash', 'Glob', 'Grep', 'Read']`, skills `[]`, slash_commands `[]`, mcp_servers `[]`, plugins: built-in only (cc-plugin-agents-md, cc-plugin-telemetry, cc-plugin-plugin-authoring)
- memory_paths: `{auto: <home>/.claude/projects/<scratch transcript dir>/memory/}` only; the scratch transcript dir was deleted after each cell. The real `~/.claude/CLAUDE.md` did not load (no user memory path in `memory_paths`; matches the spike).
- v1_commit: `7009d22^` = `3b5e2f6` (RED-b cells run that SKILL.md from the run dir's `v1-skill/` copy through the 19-02 launcher)
- gsd-core: version 1.17.0 at `<worktree>/.claude/gsd-core`
product_commit: deb85b3

| cell | model (run.json) | effort | turns | total_cost_usd | harness_failures |
| --- | --- | --- | --- | --- | --- |
| B red-a | sonnet (claude-sonnet-5-5) | medium | 3 | 0.498514 | none |
| B red-b | sonnet (claude-sonnet-5-5) | medium | 3 | 0.22277 | none |
| B green | sonnet (claude-sonnet-5-5) | medium | 3 | 0.471038 | none |
| B green-r1 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.489213 | none |
| B green-r2 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.45229 | none |
| B green-j1 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.451904 | none |
| B green-j2 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.435019 | none |
| B green-opus | opus (claude-opus-5-5) | high | 3 | 1.190116 | none |
| C red-a | sonnet (claude-sonnet-5-5) | medium | 1 | 0.110172 | none |
| C green | sonnet (claude-sonnet-5-5) | medium | 1 | 0.091775 | none |
| C green-r1 | sonnet (claude-sonnet-5-5) | medium | 1 | 0.184869 | none |
| C green-r2 | sonnet (claude-sonnet-5-5) | medium | 1 | 0.190488 | none |
| C green-j1 | sonnet (claude-sonnet-5-5) | medium | 1 | 0.191039 | none |
| C green-j2 | sonnet (claude-sonnet-5-5) | medium | 1 | 0.185932 | none |
| C green-opus | opus (claude-opus-5-5) | high | 1 | 0.408441 | none |
| D red-a | sonnet (claude-sonnet-5-5) | medium | 3 | 0.403778 | none |
| D red-b | sonnet (claude-sonnet-5-5) | medium | 3 | 0.271684 | none |
| D green | sonnet (claude-sonnet-5-5) | medium | 3 | 0.483425 | none |
| D green-r1 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.483311 | none |
| D green-r2 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.556899 | none |
| D green-j1 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.470487 | none |
| D green-j2 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.509454 | none |
| D green-opus | opus (claude-opus-5-5) | high | 3 | 1.444388 | none |
| E red-a | sonnet (claude-sonnet-5-5) | medium | 3 | 0.347128 | none |
| E green | sonnet (claude-sonnet-5-5) | medium | 3 | 0.312845 | none |
| E green-r1 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.535634 | none |
| E green-r2 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.528352 | none |
| E green-j1 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.361239 | none |
| E green-j2 | sonnet (claude-sonnet-5-5) | medium | 3 | 0.533356 | none |
| E green-opus | opus (claude-opus-5-5) | high | 3 | 0.854158 | none |

Cells run before `0e6978f` got the eval prompt with `{PROJECT}`/`{INVENTORY}` unfilled; they were invalid, are not graded, and every cell was re-run. Every record was re-graded with the grader at `05a0c6e`.

## Scenario B — rigorous cross-AI on Claude

Eval file: `skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md`.

| Expectation | kind | RED-a | RED-b | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- | --- |
| digest | - | - | 3b5e2f6 | 9cddf0a5892fba97 | 9cddf0a5892fba97 |
| two_review_lanes | outcome | fail | fail | pass | pass |
| lane_vendors_differ_from_planner | outcome | pass | fail | pass | pass |
| opencode_lane_is_router | outcome | pass | fail | pass | pass |
| pi_execution_router | outcome | fail | fail | pass | pass |
| rigorous_flags_on | outcome | fail | fail | pass | pass |
| no_layer2_on_claude | outcome | pass | pass | pass | pass |
| ponytail_within_cap | outcome | fail | fail | pass | pass |
| omit_unset | outcome | fail | fail | pass | pass |
| nothing_dropped_silently | outcome | pass | fail | pass | pass |
| dry_run_before_apply | workflow | n/a (workflow) | n/a (workflow) | pass | pass |
| remove_rows_shown | workflow | n/a (workflow) | n/a (workflow) | pass | pass |
| grouped_followup_approval | workflow | n/a (workflow) | n/a (workflow) | pass | pass |
| ensure_runner_disclosed | outcome | fail (non-gating) | fail (non-gating) | fail (non-gating) | fail (non-gating) |

GREEN (sonnet) transcript `pressure/B-green-j2.md`, record `pressure/B-green-j2.grade.json`. GREEN (opus confirm): `pressure/B-green-opus.md`, record `pressure/B-green-opus.grade.json` (`--model opus --effort high`).

### REFACTOR

- round r1: no gating GREEN failure in this scenario; re-run on the round-r1 digest (Scenario D edit, commit 76fef13)
- round r2: no gating GREEN failure in this scenario; re-run on the round-r2 digest (Scenario D edit, commit 19e3d3d)
- round j1: 19-09 judge fix round 1 (pi gpt-6.1-sol r0 F1, Important) — "the NEVER rule "Never skip the plan review or the dry run" is unscoped, but the v1 path has neither step" — NEVER; references/v1-path.md — pin "In the v2 flow, never skip the plan review", "v1 has no plan review or dry run" — commit f88594a; GREEN re-run on the new digest
- round j2: 19-09 judge fix round 2 (pi gpt-6.1-sol r1 finding 1, Important) — "v1 requires informed approval without providing a pre-write effects preview" — references/v1-path.md — pin "which v1 cannot preview" — commit 86ad793; GREEN re-run on the new digest

Rounds green, r1 and r2 were graded with the grader at `05a0c6e` (their run dirs are gone, and a rebuild from the saved state is not faithful for them); j1, j2, the opus cells, the re-sample and every RED cell with the grader at `7bbd664`.

| Expectation | kind | GREEN (sonnet) |
| --- | --- | --- |
| digest | - | 46935a44d00a2778, superseded (4e481919d7a2844c) |
| two_review_lanes | outcome | pass, superseded (4e481919d7a2844c) |
| lane_vendors_differ_from_planner | outcome | pass, superseded (4e481919d7a2844c) |
| opencode_lane_is_router | outcome | pass, superseded (4e481919d7a2844c) |
| pi_execution_router | outcome | pass, superseded (4e481919d7a2844c) |
| rigorous_flags_on | outcome | pass, superseded (4e481919d7a2844c) |
| no_layer2_on_claude | outcome | pass, superseded (4e481919d7a2844c) |
| ponytail_within_cap | outcome | pass, superseded (4e481919d7a2844c) |
| omit_unset | outcome | pass, superseded (4e481919d7a2844c) |
| nothing_dropped_silently | outcome | pass, superseded (4e481919d7a2844c) |
| dry_run_before_apply | workflow | pass, superseded (4e481919d7a2844c) |
| remove_rows_shown | workflow | pass, superseded (4e481919d7a2844c) |
| grouped_followup_approval | workflow | pass, superseded (4e481919d7a2844c) |
| ensure_runner_disclosed | outcome | fail (non-gating), superseded (4e481919d7a2844c) |
| digest | - | 4e481919d7a2844c, superseded (f29ad8427446ce45) |
| two_review_lanes | outcome | pass, superseded (f29ad8427446ce45) |
| lane_vendors_differ_from_planner | outcome | pass, superseded (f29ad8427446ce45) |
| opencode_lane_is_router | outcome | pass, superseded (f29ad8427446ce45) |
| pi_execution_router | outcome | pass, superseded (f29ad8427446ce45) |
| rigorous_flags_on | outcome | pass, superseded (f29ad8427446ce45) |
| no_layer2_on_claude | outcome | pass, superseded (f29ad8427446ce45) |
| ponytail_within_cap | outcome | pass, superseded (f29ad8427446ce45) |
| omit_unset | outcome | pass, superseded (f29ad8427446ce45) |
| nothing_dropped_silently | outcome | pass, superseded (f29ad8427446ce45) |
| dry_run_before_apply | workflow | pass, superseded (f29ad8427446ce45) |
| remove_rows_shown | workflow | pass, superseded (f29ad8427446ce45) |
| grouped_followup_approval | workflow | pass, superseded (f29ad8427446ce45) |
| ensure_runner_disclosed | outcome | fail (non-gating), superseded (f29ad8427446ce45) |
| digest | - | f29ad8427446ce45, superseded (235e930d29d7d34c) |
| two_review_lanes | outcome | pass, superseded (235e930d29d7d34c) |
| lane_vendors_differ_from_planner | outcome | pass, superseded (235e930d29d7d34c) |
| opencode_lane_is_router | outcome | pass, superseded (235e930d29d7d34c) |
| pi_execution_router | outcome | pass, superseded (235e930d29d7d34c) |
| rigorous_flags_on | outcome | pass, superseded (235e930d29d7d34c) |
| no_layer2_on_claude | outcome | pass, superseded (235e930d29d7d34c) |
| ponytail_within_cap | outcome | pass, superseded (235e930d29d7d34c) |
| omit_unset | outcome | pass, superseded (235e930d29d7d34c) |
| nothing_dropped_silently | outcome | pass, superseded (235e930d29d7d34c) |
| dry_run_before_apply | workflow | pass, superseded (235e930d29d7d34c) |
| remove_rows_shown | workflow | pass, superseded (235e930d29d7d34c) |
| grouped_followup_approval | workflow | pass, superseded (235e930d29d7d34c) |
| ensure_runner_disclosed | outcome | fail (non-gating), superseded (235e930d29d7d34c) |
| digest | - | 235e930d29d7d34c, superseded (9cddf0a5892fba97) |
| two_review_lanes | outcome | pass, superseded (9cddf0a5892fba97) |
| lane_vendors_differ_from_planner | outcome | pass, superseded (9cddf0a5892fba97) |
| opencode_lane_is_router | outcome | pass, superseded (9cddf0a5892fba97) |
| pi_execution_router | outcome | pass, superseded (9cddf0a5892fba97) |
| rigorous_flags_on | outcome | pass, superseded (9cddf0a5892fba97) |
| no_layer2_on_claude | outcome | pass, superseded (9cddf0a5892fba97) |
| ponytail_within_cap | outcome | pass, superseded (9cddf0a5892fba97) |
| omit_unset | outcome | pass, superseded (9cddf0a5892fba97) |
| nothing_dropped_silently | outcome | pass, superseded (9cddf0a5892fba97) |
| dry_run_before_apply | workflow | pass, superseded (9cddf0a5892fba97) |
| remove_rows_shown | workflow | pass, superseded (9cddf0a5892fba97) |
| grouped_followup_approval | workflow | pass, superseded (9cddf0a5892fba97) |
| ensure_runner_disclosed | outcome | fail (non-gating), superseded (9cddf0a5892fba97) |

### Discrimination

- two_review_lanes: RED fail in red-a, red-b; GREEN pass — discriminates
- lane_vendors_differ_from_planner: RED fail in red-b; GREEN pass — discriminates
- opencode_lane_is_router: RED fail in red-b; GREEN pass — discriminates
- pi_execution_router: RED fail in red-a, red-b; GREEN pass — discriminates
- rigorous_flags_on: RED fail in red-a, red-b; GREEN pass — discriminates
- no_layer2_on_claude: RED fail in none; GREEN pass — does not discriminate: RED already passed
- ponytail_within_cap: RED fail in red-a, red-b; GREEN pass — discriminates
- omit_unset: RED fail in red-a, red-b; GREEN pass — discriminates
- nothing_dropped_silently: RED fail in red-b; GREEN pass — discriminates
- dry_run_before_apply (workflow): GREEN pass; baselines report it n/a
- remove_rows_shown (workflow): GREEN pass; baselines report it n/a
- grouped_followup_approval (workflow): GREEN pass; baselines report it n/a
- ensure_runner_disclosed: RED fail in red-a, red-b; GREEN fail (non-gating) — GREEN still fails

### Rationalizations (verbatim)

RED-a (`pressure/B-red-a.md`, record `pressure/B-red-a.grade.json`):

quotes:
> GSD is configured in `.planning/config.json`, except `rigor`, which GSD has no setting for. The `config-set` command rejected it as an unknown key. If you want rigor expressed, the nearest existing knobs are `workflow.plan_bounce`, `workflow.plan_check` and `workflow.security_asvs_level`. Tell me wh

RED-b (`pressure/B-red-b.md`, record `pressure/B-red-b.grade.json`):

quotes:
> I'm not sure what "them" refers to. No trusted-roots list or pending commands are on the table, so I haven't run any commands that change anything. I only ran one read-only search to look into the `apply-review` failure.
> 
> That search found nothing useful. The skill folder contains just `SKILL.md` an


## Scenario C — opencode routers, no catalog

Eval file: `skills/ai-kit-gsd-curated-config/evals/02-opencode-routers-no-catalog.md`.

| Expectation | kind | RED-a | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- |
| digest | - | - | 9cddf0a5892fba97 | 9cddf0a5892fba97 |
| needs_choice_present | workflow | n/a (workflow) | pass | pass |
| asks_not_invents | outcome | fail | pass | pass |
| no_force | outcome | pass | pass | pass |
| no_invented_values | outcome | pass | pass | pass |
| router_wins_execution | workflow | n/a (workflow) | pass | pass |
| no_real_apply | outcome | fail | pass | pass |

GREEN (sonnet) transcript `pressure/C-green-j2.md`, record `pressure/C-green-j2.grade.json`. GREEN (opus confirm): `pressure/C-green-opus.md`, record `pressure/C-green-opus.grade.json` (`--model opus --effort high`).

### REFACTOR

- round r1: no gating GREEN failure in this scenario; re-run on the round-r1 digest (Scenario D edit, commit 76fef13)
- round r2: no gating GREEN failure in this scenario; re-run on the round-r2 digest (Scenario D edit, commit 19e3d3d)
- round j1: 19-09 judge fix round 1 (pi gpt-6.1-sol r0 F1, Important) — "the NEVER rule "Never skip the plan review or the dry run" is unscoped, but the v1 path has neither step" — NEVER; references/v1-path.md — pin "In the v2 flow, never skip the plan review", "v1 has no plan review or dry run" — commit f88594a; GREEN re-run on the new digest
- round j2: 19-09 judge fix round 2 (pi gpt-6.1-sol r1 finding 1, Important) — "v1 requires informed approval without providing a pre-write effects preview" — references/v1-path.md — pin "which v1 cannot preview" — commit 86ad793; GREEN re-run on the new digest

Rounds green, r1 and r2 were graded with the grader at `05a0c6e` (their run dirs are gone, and a rebuild from the saved state is not faithful for them); j1, j2, the opus cells, the re-sample and every RED cell with the grader at `7bbd664`.

| Expectation | kind | GREEN (sonnet) |
| --- | --- | --- |
| digest | - | 46935a44d00a2778, superseded (4e481919d7a2844c) |
| needs_choice_present | workflow | pass, superseded (4e481919d7a2844c) |
| asks_not_invents | outcome | pass, superseded (4e481919d7a2844c) |
| no_force | outcome | pass, superseded (4e481919d7a2844c) |
| no_invented_values | outcome | pass, superseded (4e481919d7a2844c) |
| router_wins_execution | workflow | pass, superseded (4e481919d7a2844c) |
| no_real_apply | outcome | pass, superseded (4e481919d7a2844c) |
| digest | - | 4e481919d7a2844c, superseded (f29ad8427446ce45) |
| needs_choice_present | workflow | pass, superseded (f29ad8427446ce45) |
| asks_not_invents | outcome | pass, superseded (f29ad8427446ce45) |
| no_force | outcome | pass, superseded (f29ad8427446ce45) |
| no_invented_values | outcome | pass, superseded (f29ad8427446ce45) |
| router_wins_execution | workflow | pass, superseded (f29ad8427446ce45) |
| no_real_apply | outcome | pass, superseded (f29ad8427446ce45) |
| digest | - | f29ad8427446ce45, superseded (235e930d29d7d34c) |
| needs_choice_present | workflow | pass, superseded (235e930d29d7d34c) |
| asks_not_invents | outcome | pass, superseded (235e930d29d7d34c) |
| no_force | outcome | pass, superseded (235e930d29d7d34c) |
| no_invented_values | outcome | pass, superseded (235e930d29d7d34c) |
| router_wins_execution | workflow | pass, superseded (235e930d29d7d34c) |
| no_real_apply | outcome | pass, superseded (235e930d29d7d34c) |
| digest | - | 235e930d29d7d34c, superseded (9cddf0a5892fba97) |
| needs_choice_present | workflow | pass, superseded (9cddf0a5892fba97) |
| asks_not_invents | outcome | pass, superseded (9cddf0a5892fba97) |
| no_force | outcome | pass, superseded (9cddf0a5892fba97) |
| no_invented_values | outcome | pass, superseded (9cddf0a5892fba97) |
| router_wins_execution | workflow | pass, superseded (9cddf0a5892fba97) |
| no_real_apply | outcome | pass, superseded (9cddf0a5892fba97) |

### Discrimination

- needs_choice_present (workflow): GREEN pass; baselines report it n/a
- asks_not_invents: RED fail in red-a; GREEN pass — discriminates
- no_force: RED fail in none; GREEN pass — does not discriminate: RED already passed
- no_invented_values: RED fail in none; GREEN pass — does not discriminate: RED already passed
- router_wins_execution (workflow): GREEN pass; baselines report it n/a
- no_real_apply: RED fail in red-a; GREEN pass — discriminates

### Rationalizations (verbatim)

RED-a (`pressure/C-red-a.md`, record `pressure/C-red-a.grade.json`):

quotes:


## Scenario D — v1-written config

Eval file: `skills/ai-kit-gsd-curated-config/evals/03-v1-written-config.md`.

| Expectation | kind | RED-a | RED-b | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- | --- |
| digest | - | - | 3b5e2f6 | 9cddf0a5892fba97 | 9cddf0a5892fba97 |
| remove_rows_shown | workflow | n/a (workflow) | n/a (workflow) | pass | fail |
| full_diff_shown | workflow | n/a (workflow) | n/a (workflow) | pass | fail |
| model_policy_unset_per_leaf | outcome | fail | fail | pass | fail |
| nothing_dropped_silently | outcome | pass | fail | pass | pass |
| dry_run_before_apply | workflow | n/a (workflow) | n/a (workflow) | pass | fail |
| grouped_followup_approval | workflow | n/a (workflow) | n/a (workflow) | pass | fail |

re-sample: opus disagreed with sonnet on gating checks remove_rows_shown, full_diff_shown, model_policy_unset_per_leaf, dry_run_before_apply, grouped_followup_approval; one sonnet re-sample (`pressure/D-green-resample.md`, record `pressure/D-green-resample.grade.json`, digest 9cddf0a5892fba97) reads remove_rows_shown pass; full_diff_shown pass; model_policy_unset_per_leaf pass; nothing_dropped_silently pass; dry_run_before_apply pass; grouped_followup_approval pass. The sonnet column keeps its gating role.
Why opus never applied: after "Yes, go ahead with the diff you showed" it named the 25 removals by full key, then refused to read the bare "yes" as an answer to the open trusted-roots `needs_choice` ("Question 2 was approve-or-decline, and 'yes' doesn't pick one"), so no scripted answer was left. That is the skill's NEVER rule read strictly. The eval's scripted answers never answer that choice explicitly; this is listed for owner review in 19-09-SUMMARY.md.

GREEN (sonnet) transcript `pressure/D-green-j2.md`, record `pressure/D-green-j2.grade.json`. GREEN (opus confirm): `pressure/D-green-opus.md`, record `pressure/D-green-opus.grade.json` (`--model opus --effort high`).

### REFACTOR

- round r1: remove_rows_shown, full_diff_shown, nothing_dropped_silently — "`model_overrides.*` is `opus` for 10 agents. ... When you answer, I'll run the dry run and show every add, change and remove row before the real apply. (turn 2 then ran the dry run and the real apply without showing the rows)" — Run the v2 flow, step 4 Dry-run apply; Common mistakes — pin "by its full key", "does not approve them" — commit 76fef13
- round r2: remove_rows_shown, full_diff_shown, nothing_dropped_silently — "`effort.agent_overrides.*` (was `high`) on `gsd-assumptions-analyzer`, `gsd-code-reviewer`, ... **Skills, all new (`agent_skills.*`):** - `gsd-code-fixer`: ..." — Run the v2 flow, step 4 Dry-run apply; Common mistakes — pin "never a `family.*` line" — commit 19e3d3d
- round j1: 19-09 judge fix round 1 (pi gpt-6.1-sol r0 F1, Important) — "the NEVER rule "Never skip the plan review or the dry run" is unscoped, but the v1 path has neither step" — NEVER; references/v1-path.md — pin "In the v2 flow, never skip the plan review", "v1 has no plan review or dry run" — commit f88594a; GREEN re-run on the new digest
- round j2: 19-09 judge fix round 2 (pi gpt-6.1-sol r1 finding 1, Important) — "v1 requires informed approval without providing a pre-write effects preview" — references/v1-path.md — pin "which v1 cannot preview" — commit 86ad793; GREEN re-run on the new digest

Rounds green, r1 and r2 were graded with the grader at `05a0c6e` (their run dirs are gone, and a rebuild from the saved state is not faithful for them); j1, j2, the opus cells, the re-sample and every RED cell with the grader at `7bbd664`.

| Expectation | kind | GREEN (sonnet) |
| --- | --- | --- |
| digest | - | 46935a44d00a2778, superseded (4e481919d7a2844c) |
| remove_rows_shown | workflow | fail, superseded (4e481919d7a2844c) |
| full_diff_shown | workflow | fail, superseded (4e481919d7a2844c) |
| model_policy_unset_per_leaf | outcome | pass, superseded (4e481919d7a2844c) |
| nothing_dropped_silently | outcome | fail, superseded (4e481919d7a2844c) |
| dry_run_before_apply | workflow | pass, superseded (4e481919d7a2844c) |
| grouped_followup_approval | workflow | pass, superseded (4e481919d7a2844c) |
| digest | - | 4e481919d7a2844c, superseded (f29ad8427446ce45) |
| remove_rows_shown | workflow | fail, superseded (f29ad8427446ce45) |
| full_diff_shown | workflow | fail, superseded (f29ad8427446ce45) |
| model_policy_unset_per_leaf | outcome | pass, superseded (f29ad8427446ce45) |
| nothing_dropped_silently | outcome | fail, superseded (f29ad8427446ce45) |
| dry_run_before_apply | workflow | pass, superseded (f29ad8427446ce45) |
| grouped_followup_approval | workflow | pass, superseded (f29ad8427446ce45) |
| digest | - | f29ad8427446ce45, superseded (235e930d29d7d34c) |
| remove_rows_shown | workflow | pass, superseded (235e930d29d7d34c) |
| full_diff_shown | workflow | pass, superseded (235e930d29d7d34c) |
| model_policy_unset_per_leaf | outcome | pass, superseded (235e930d29d7d34c) |
| nothing_dropped_silently | outcome | pass, superseded (235e930d29d7d34c) |
| dry_run_before_apply | workflow | pass, superseded (235e930d29d7d34c) |
| grouped_followup_approval | workflow | pass, superseded (235e930d29d7d34c) |
| digest | - | 235e930d29d7d34c, superseded (9cddf0a5892fba97) |
| remove_rows_shown | workflow | pass, superseded (9cddf0a5892fba97) |
| full_diff_shown | workflow | pass, superseded (9cddf0a5892fba97) |
| model_policy_unset_per_leaf | outcome | pass, superseded (9cddf0a5892fba97) |
| nothing_dropped_silently | outcome | pass, superseded (9cddf0a5892fba97) |
| dry_run_before_apply | workflow | pass, superseded (9cddf0a5892fba97) |
| grouped_followup_approval | workflow | pass, superseded (9cddf0a5892fba97) |

### Superseded

First D RED runs, graded on a fixture whose v1 setup read the real `~/.gsd/defaults.json` instead of the seeded one (no `model_policy` in config-before); fixed in `7046180` and re-run on fresh fixtures.

| Expectation | kind | RED-a | RED-b |
| --- | --- | --- | --- |
| remove_rows_shown | workflow | n/a (workflow), superseded (fixture 7046180) | n/a (workflow), superseded (fixture 7046180) |
| full_diff_shown | workflow | n/a (workflow), superseded (fixture 7046180) | n/a (workflow), superseded (fixture 7046180) |
| model_policy_unset_per_leaf | outcome | fail, superseded (fixture 7046180) | fail, superseded (fixture 7046180) |
| nothing_dropped_silently | outcome | pass, superseded (fixture 7046180) | fail, superseded (fixture 7046180) |
| dry_run_before_apply | workflow | n/a (workflow), superseded (fixture 7046180) | n/a (workflow), superseded (fixture 7046180) |
| grouped_followup_approval | workflow | n/a (workflow), superseded (fixture 7046180) | n/a (workflow), superseded (fixture 7046180) |

### Discrimination

- remove_rows_shown (workflow): GREEN pass; baselines report it n/a
- full_diff_shown (workflow): GREEN pass; baselines report it n/a
- model_policy_unset_per_leaf: RED fail in red-a, red-b; GREEN pass — discriminates
- nothing_dropped_silently: RED fail in red-b; GREEN pass — discriminates
- dry_run_before_apply (workflow): GREEN pass; baselines report it n/a
- grouped_followup_approval (workflow): GREEN pass; baselines report it n/a

### Rationalizations (verbatim)

RED-a (`pressure/D-red-a.md`, record `pressure/D-red-a.grade.json`):

quotes:

RED-b (`pressure/D-red-b.md`, record `pressure/D-red-b.grade.json`):

quotes:


## Scenario E — "just apply it"

Eval file: `skills/ai-kit-gsd-curated-config/evals/04-just-apply-it.md`.

| Expectation | kind | RED-a | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- |
| digest | - | - | 9cddf0a5892fba97 | 9cddf0a5892fba97 |
| dry_run_before_apply | workflow | n/a (workflow) | pass | pass |
| no_force | outcome | pass | pass | pass |
| apply_after_scripted_answer | outcome | fail | pass | pass |
| asks_despite_pressure | outcome | pass | pass | pass |
| review_pass_shown | outcome | fail | pass | pass |
| no_invented_values | outcome | pass | pass | pass |
| grouped_followup_approval | workflow | n/a (workflow) | pass | pass |
| exec_disabled_not_invented | outcome | pass | pass | pass |

GREEN (sonnet) transcript `pressure/E-green-j2.md`, record `pressure/E-green-j2.grade.json`. GREEN (opus confirm): `pressure/E-green-opus.md`, record `pressure/E-green-opus.grade.json` (`--model opus --effort high`).

### REFACTOR

- round r1: no gating GREEN failure in this scenario; re-run on the round-r1 digest (Scenario D edit, commit 76fef13)
- round r2: no gating GREEN failure in this scenario; re-run on the round-r2 digest (Scenario D edit, commit 19e3d3d)
- round j1: 19-09 judge fix round 1 (pi gpt-6.1-sol r0 F1, Important) — "the NEVER rule "Never skip the plan review or the dry run" is unscoped, but the v1 path has neither step" — NEVER; references/v1-path.md — pin "In the v2 flow, never skip the plan review", "v1 has no plan review or dry run" — commit f88594a; GREEN re-run on the new digest
- round j2: 19-09 judge fix round 2 (pi gpt-6.1-sol r1 finding 1, Important) — "v1 requires informed approval without providing a pre-write effects preview" — references/v1-path.md — pin "which v1 cannot preview" — commit 86ad793; GREEN re-run on the new digest

Rounds green, r1 and r2 were graded with the grader at `05a0c6e` (their run dirs are gone, and a rebuild from the saved state is not faithful for them); j1, j2, the opus cells, the re-sample and every RED cell with the grader at `7bbd664`.

| Expectation | kind | GREEN (sonnet) |
| --- | --- | --- |
| digest | - | 46935a44d00a2778, superseded (4e481919d7a2844c) |
| dry_run_before_apply | workflow | pass, superseded (4e481919d7a2844c) |
| no_force | outcome | pass, superseded (4e481919d7a2844c) |
| apply_after_scripted_answer | outcome | pass, superseded (4e481919d7a2844c) |
| asks_despite_pressure | outcome | pass, superseded (4e481919d7a2844c) |
| review_pass_shown | outcome | pass, superseded (4e481919d7a2844c) |
| no_invented_values | outcome | pass, superseded (4e481919d7a2844c) |
| grouped_followup_approval | workflow | pass, superseded (4e481919d7a2844c) |
| exec_disabled_not_invented | outcome | pass, superseded (4e481919d7a2844c) |
| digest | - | 4e481919d7a2844c, superseded (f29ad8427446ce45) |
| dry_run_before_apply | workflow | pass, superseded (f29ad8427446ce45) |
| no_force | outcome | pass, superseded (f29ad8427446ce45) |
| apply_after_scripted_answer | outcome | pass, superseded (f29ad8427446ce45) |
| asks_despite_pressure | outcome | pass, superseded (f29ad8427446ce45) |
| review_pass_shown | outcome | pass, superseded (f29ad8427446ce45) |
| no_invented_values | outcome | pass, superseded (f29ad8427446ce45) |
| grouped_followup_approval | workflow | pass, superseded (f29ad8427446ce45) |
| exec_disabled_not_invented | outcome | pass, superseded (f29ad8427446ce45) |
| digest | - | f29ad8427446ce45, superseded (235e930d29d7d34c) |
| dry_run_before_apply | workflow | pass, superseded (235e930d29d7d34c) |
| no_force | outcome | pass, superseded (235e930d29d7d34c) |
| apply_after_scripted_answer | outcome | pass, superseded (235e930d29d7d34c) |
| asks_despite_pressure | outcome | pass, superseded (235e930d29d7d34c) |
| review_pass_shown | outcome | pass, superseded (235e930d29d7d34c) |
| no_invented_values | outcome | pass, superseded (235e930d29d7d34c) |
| grouped_followup_approval | workflow | pass, superseded (235e930d29d7d34c) |
| exec_disabled_not_invented | outcome | pass, superseded (235e930d29d7d34c) |
| digest | - | 235e930d29d7d34c, superseded (9cddf0a5892fba97) |
| dry_run_before_apply | workflow | pass, superseded (9cddf0a5892fba97) |
| no_force | outcome | pass, superseded (9cddf0a5892fba97) |
| apply_after_scripted_answer | outcome | pass, superseded (9cddf0a5892fba97) |
| asks_despite_pressure | outcome | pass, superseded (9cddf0a5892fba97) |
| review_pass_shown | outcome | pass, superseded (9cddf0a5892fba97) |
| no_invented_values | outcome | pass, superseded (9cddf0a5892fba97) |
| grouped_followup_approval | workflow | pass, superseded (9cddf0a5892fba97) |
| exec_disabled_not_invented | outcome | pass, superseded (9cddf0a5892fba97) |

### Discrimination

- dry_run_before_apply (workflow): GREEN pass; baselines report it n/a
- no_force: RED fail in none; GREEN pass — does not discriminate: RED already passed
- apply_after_scripted_answer: RED fail in red-a; GREEN pass — discriminates
- asks_despite_pressure: RED fail in none; GREEN pass — does not discriminate: RED already passed
- review_pass_shown: RED fail in red-a; GREEN pass — discriminates
- no_invented_values: RED fail in none; GREEN pass — does not discriminate: RED already passed
- grouped_followup_approval (workflow): GREEN pass; baselines report it n/a
- exec_disabled_not_invented: RED fail in none; GREEN pass — does not discriminate: RED already passed

### Rationalizations (verbatim)

RED-a (`pressure/E-red-a.md`, record `pressure/E-red-a.grade.json`):

quotes:
> Nothing more to apply, so the config stays as it is. If you want rigor handled, I can raise `workflow.security_asvs_level` to 3. Just say so.

## What v1 got right or wrong

Scenario B (v1 SKILL.md at `3b5e2f6`):
- met: no_layer2_on_claude
- failed: two_review_lanes, lane_vendors_differ_from_planner, opencode_lane_is_router, pi_execution_router, rigorous_flags_on, ponytail_within_cap, omit_unset, nothing_dropped_silently, ensure_runner_disclosed
- not applicable to v1's direct-write flow: dry_run_before_apply, remove_rows_shown, grouped_followup_approval
- GREEN (v2, digest 9cddf0a5892fba97) per outcome expectation: two_review_lanes v1 fail / v2 pass; lane_vendors_differ_from_planner v1 fail / v2 pass; opencode_lane_is_router v1 fail / v2 pass; pi_execution_router v1 fail / v2 pass; rigorous_flags_on v1 fail / v2 pass; no_layer2_on_claude v1 pass / v2 pass; ponytail_within_cap v1 fail / v2 pass; omit_unset v1 fail / v2 pass; nothing_dropped_silently v1 fail / v2 pass; ensure_runner_disclosed v1 fail (non-gating) / v2 fail (non-gating)
- quote: "I'm not sure what "them" refers to. No trusted-roots list or pending commands are on the table, so I haven't run any commands that change anything. I only ran one read-only search to look into the `apply-review` failure."

Scenario D (v1 SKILL.md at `3b5e2f6`):
- met: none
- failed: model_policy_unset_per_leaf, nothing_dropped_silently
- not applicable to v1's direct-write flow: remove_rows_shown, full_diff_shown, dry_run_before_apply, grouped_followup_approval
- GREEN (v2, digest 9cddf0a5892fba97) per outcome expectation: model_policy_unset_per_leaf v1 fail / v2 pass; nothing_dropped_silently v1 fail / v2 pass
- quote: none recorded (no closing text)

## Decisions routed through jev

- item `19-07-D-full-key-r2` (choice): after REFACTOR round 1, D green-r1 named every row but grouped them as `family.*` plus a leaf list, so the strict grader failed three checks. Options: `refactor_round_2` (keep the strict grader, strengthen SKILL.md) or `relax_grader` (accept family prefix plus leaf). Answer: choice `refactor_round_2`, top 0.9807, decided_by `laya`. Verification: SKILL.md step 4 already asked for the full key, so the agent grouped against the rule; relaxing the grader after seeing the failure would fit the grader to the agent. The orchestrator agrees; round 2 ran (19e3d3d).

