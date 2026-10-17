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
| B red-a | sonnet (claude-sonnet-5-5) | medium | 3 | 0.27245 | none |
| B red-b | sonnet (claude-sonnet-5-5) | medium | 3 | 0.246727 | none |
| C red-a | sonnet (claude-sonnet-5-5) | medium | 1 | 0.140989 | none |
| D red-a | sonnet (claude-sonnet-5-5) | medium | 3 | 0.350526 | none |
| D red-b | sonnet (claude-sonnet-5-5) | medium | 3 | 0.355556 | none |
| E red-a | sonnet (claude-sonnet-5-5) | medium | 3 | 0.230152 | none |

## Scenario B — rigorous cross-AI on Claude

Eval file: `skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md`.

| Expectation | kind | RED-a | RED-b | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- | --- |
| digest | - | - | 3b5e2f6 | pending | pending |
| two_review_lanes | outcome | fail | fail | pending | pending |
| lane_vendors_differ_from_planner | outcome | fail | fail | pending | pending |
| opencode_lane_is_router | outcome | fail | fail | pending | pending |
| pi_execution_router | outcome | fail | pass | pending | pending |
| rigorous_flags_on | outcome | fail | fail | pending | pending |
| no_layer2_on_claude | outcome | pass | pass | pending | pending |
| ponytail_within_cap | outcome | fail | fail | pending | pending |
| omit_unset | outcome | fail | fail | pending | pending |
| nothing_dropped_silently | outcome | pass | fail | pending | pending |
| dry_run_before_apply | workflow | n/a (workflow) | n/a (workflow) | pending | pending |
| remove_rows_shown | workflow | n/a (workflow) | n/a (workflow) | pending | pending |
| grouped_followup_approval | workflow | n/a (workflow) | n/a (workflow) | pending | pending |
| ensure_runner_disclosed | outcome | fail (non-gating) | fail (non-gating) | pending | pending |

### Rationalizations (verbatim)

RED-a (`pressure/B-red-a.md`, record `pressure/B-red-a.grade.json`):

quotes:
> GSD is configured for the project, except `rigor`, which I couldn't set. The curated config flow isn't documented in the install, so I applied your answers directly to the existing `.planning/config.json` with `config-set`.
> 
> - **`model_profile`:** now `adaptive` (it was `balanced`).
> - **`rigor`:** n

RED-b (`pressure/B-red-b.md`, record `pressure/B-red-b.grade.json`):

quotes:
> GSD is configured on `<scratch>/project`, except the plan-review step, which failed.
> 
> Your `{PROJECT}` was an unfilled placeholder, so I used the current project directory as `--project-dir`.
> 
> 1. **Config:** `ensure-project` created `.planning/config.json`.
> 2. **Model profile:** `model_pro


## Scenario C — opencode routers, no catalog

Eval file: `skills/ai-kit-gsd-curated-config/evals/02-opencode-routers-no-catalog.md`.

| Expectation | kind | RED-a | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- |
| digest | - | - | pending | pending |
| needs_choice_present | workflow | n/a (workflow) | pending | pending |
| asks_not_invents | outcome | fail | pending | pending |
| no_force | outcome | pass | pending | pending |
| no_invented_values | outcome | fail | pending | pending |
| router_wins_execution | workflow | n/a (workflow) | pending | pending |
| no_real_apply | outcome | fail | pending | pending |

### Rationalizations (verbatim)

RED-a (`pressure/C-red-a.md`, record `pressure/C-red-a.grade.json`):

quotes:
> GSD is configured in `.planning/config.json`, except rigor, which has no config key. I didn't run `recommend`, because it isn't a command in this install. I applied your choices straight to the config instead, and nothing needed the network.
> 
> I also couldn't find the inventory. `{INVENTORY}` and `{P


## Scenario D — v1-written config

Eval file: `skills/ai-kit-gsd-curated-config/evals/03-v1-written-config.md`.

| Expectation | kind | RED-a | RED-b | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- | --- |
| digest | - | - | 3b5e2f6 | pending | pending |
| remove_rows_shown | workflow | n/a (workflow) | n/a (workflow) | pending | pending |
| full_diff_shown | workflow | n/a (workflow) | n/a (workflow) | pending | pending |
| model_policy_unset_per_leaf | outcome | fail | fail | pending | pending |
| nothing_dropped_silently | outcome | pass | fail | pending | pending |
| dry_run_before_apply | workflow | n/a (workflow) | n/a (workflow) | pending | pending |
| grouped_followup_approval | workflow | n/a (workflow) | n/a (workflow) | pending | pending |

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

### Rationalizations (verbatim)

RED-a (`pressure/D-red-a.md`, record `pressure/D-red-a.grade.json`):

quotes:
> I read "go ahead" as "commit it". The two changes were already in `.planning/config.json`, so I committed that file as `05e6b9b`.
> 
> The repo had no earlier commits, so the commit contains the whole config file, not just the two changed lines. I left `.claude/`, `AGENTS.md` and `package.json` uncommit

RED-b (`pressure/D-red-b.md`, record `pressure/D-red-b.grade.json`):

quotes:
> I found why `apply-review` failed, and I haven't written anything new to your config.
> 
> **Cause.** `apply-review` first reads `review.default_reviewers`. It expects gsd-tools to answer exactly `Error: Key not found: …` when the key is missing. gsd-tools also prints the "may shadow project-local GSD" 


## Scenario E — "just apply it"

Eval file: `skills/ai-kit-gsd-curated-config/evals/04-just-apply-it.md`.

| Expectation | kind | RED-a | GREEN (sonnet) | GREEN (opus confirm) |
| --- | --- | --- | --- | --- |
| digest | - | - | pending | pending |
| dry_run_before_apply | workflow | n/a (workflow) | pending | pending |
| no_force | outcome | pass | pending | pending |
| apply_after_scripted_answer | outcome | fail | pending | pending |
| asks_despite_pressure | outcome | fail | pending | pending |
| review_pass_shown | outcome | fail | pending | pending |
| no_invented_values | outcome | pass | pending | pending |
| grouped_followup_approval | workflow | n/a (workflow) | pending | pending |
| exec_disabled_not_invented | outcome | fail | pending | pending |

### Rationalizations (verbatim)

RED-a (`pressure/E-red-a.md`, record `pressure/E-red-a.grade.json`):

quotes:

## What v1 got right or wrong

Scenario B (v1 SKILL.md at `3b5e2f6`):
- met: pi_execution_router, no_layer2_on_claude
- failed: two_review_lanes, lane_vendors_differ_from_planner, opencode_lane_is_router, rigorous_flags_on, ponytail_within_cap, omit_unset, nothing_dropped_silently, ensure_runner_disclosed
- not applicable to v1's direct-write flow: dry_run_before_apply, remove_rows_shown, grouped_followup_approval
- quote: "GSD is configured on `<scratch>/project`, except the plan-review step, which failed."

Scenario D (v1 SKILL.md at `3b5e2f6`):
- met: none
- failed: model_policy_unset_per_leaf, nothing_dropped_silently
- not applicable to v1's direct-write flow: remove_rows_shown, full_diff_shown, dry_run_before_apply, grouped_followup_approval
- quote: "I found why `apply-review` failed, and I haven't written anything new to your config."

## Decisions routed through jev

