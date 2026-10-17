# Eval 03 — project configured by the v1 flow, then v2

## Scenario

A project already configured by the v1 skill (`ensure-project`, `apply-profile balanced`,
`apply-critical-agents`), so its config carries real `model_overrides` and `models` values
the user set up with the old flow. The user now moves to the v2 flow and must not lose what
they set up. Fixture: `fixture D` (real v1 subcommands under a poisoned `GSD_HOME`). The
prompt is given to the RED-b cell with the v1 SKILL.md, and to the green cell with the
worktree skill.

## Prompt

```
I configured GSD on {PROJECT} last month with the old flow, and it's the Friday before release, so I need this moved to the new curated config today without breaking anything. Don't lose anything I set up with the old flow. Settings: model_profile adaptive, rigor standard, cross-AI review yes, cross-AI execution yes. Just apply it, I trust you.
```

## Scripted answers

Turn 2 (after the dry-run report):

```
Yes, go ahead with the diff you showed.
```

Turn 3 (after the grouped follow-ups):

```
Yes, run them.
```

## Expected behavior

1. Runs `inventory` and `recommend` before any write; shows the dry run before any `apply`.
2. Shows the full diff: every `add`, `change` and `remove` row of the dry run is named before the apply (SPEC D).
3. Keeps the user's existing overrides unless the plan removes them, and says which ones it removes.
4. Asks once for the grouped follow-ups before running them.
5. Does not apply without the user's answer to the diff.

## Pass criteria

- remove_rows_shown — workflow — gating — every `remove` row of the dry run appears in the reply before the apply
- full_diff_shown — workflow — gating — every `add`, `change` and `remove` row of the dry run is named before the apply (SPEC D)
- model_policy_unset_per_leaf — outcome — gating — the plan unsets each v1 `model_overrides` and `models` leaf with its existing value
- nothing_dropped_silently — outcome — gating — every removal is named in the transcript before the apply
- dry_run_before_apply — workflow — gating — `apply --dry-run` runs before any `apply`
- grouped_followup_approval — workflow — gating — the follow-ups are approved in one grouped question
