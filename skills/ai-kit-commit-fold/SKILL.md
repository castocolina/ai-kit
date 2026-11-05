---
name: ai-kit-commit-fold
description: "Folds a finished GSD or superpowers plan's commits into one commit per logical feature, by one written policy. Use when a finished plan should become one commit per logical feature, to install the GSD wave-end fold, or to see which plans of a phase are unfolded. Not for squashing a branch, interactive rebases, pushing or opening PRs."
---

# ai-kit-commit-fold

Folds the commits of one finished plan into one commit per logical feature. The rules live in
`references/folding-policy.md`: read it before folding by hand. This file says how to run the fold
and read its report; it does not restate the policy.

## Run the fold

The engine is `scripts/fold.py` in this skill's folder. It has three forms:

- `fold.py gsd --phase N` folds each finished plan of a GSD phase, in plan order.
- `fold.py superpowers --plan FILE [--base SHA]` folds a finished superpowers plan branch.
- `fold.py fold <checkpoint.json|->` folds one checkpoint that another spec system supplies.

Add `--repo DIR` for another repository. Where the host has a subagent, dispatch the fold to it
with this instruction: "run `python3 <skill>/scripts/fold.py <form> --repo <repo> --mode subagent`
and reply with its output only", then relay its report verbatim. On a host without subagents, run
the same command yourself with `--mode inline`. The report's last line says which mode ran.

## Read the report

The report has five lines: the unit, the counts with the grouping source, the tree check, the backup
tag and the outcome. A refusal changes nothing, so the branch stays where it was. Report the reason
to the user and stop:

| Reason | What to tell the user |
|--------|-----------------------|
| `dirty_tree` | Tracked files have uncommitted changes. Ask the user to commit or discard them, then re-run. |
| `branch_moved` | The branch is no longer at the tested tip. Re-run from its current tip. |
| `no_base_branch` | Neither the base branch nor its origin copy resolves. Ask which base branch to use. |
| `range_on_base_branch` | The range sits on the base branch, which is never rewritten. Do not fold. |
| `range_on_merged_branch` | The range is on a branch whose PR has merged, which is never rewritten. Do not fold. The script refuses it only when the caller supplies merged refs; the `gsd` and `superpowers` forms pass none, so check the PR yourself. |
| `foreign_merge` | A merge in the range is not one of the plan's own merge-backs. Ask the user to review it. |
| `plan_not_contiguous` | Another plan's commit sits inside this plan's run. Ask the user to review the history. |
| `detached_head` | HEAD is not on a branch. Ask the user to check out a branch. |
| `tree_mismatch` | The folded tree differs from the tested tree, so the branch did not move. Report it as a bug. |
| `tag_exists` | The backup tag name points at another commit. Report it; do not delete the tag. |
| `policy_missing` | The folding policy text is missing or empty. Report it; do not fold. |
| `bad_checkpoint` | The plan, phase, checkpoint or `--base` input does not parse or resolve. Fix the input. |
| `git_error` | Git failed. The report's first error line says how. Report it. |

## GSD: fold after every wave

Installing the fold into a GSD project takes two steps, both run with the project's own gsd-tools:

1. `node .claude/gsd-core/bin/gsd-tools.cjs capability install <this skill>/gsd/ai-kit-commit-fold --scope project`.
   It stops and asks for approval, because the capability loads a command module into the GSD
   CLI process. Ask the owner.
2. Only after the owner says yes, run the same command with `--yes`.

Then commit `.gsd/capabilities/ai-kit-commit-fold/` and `.gsd-capabilities.json`. A fresh clone
repeats the `--yes` step, because GSD keeps the approval in its own home, not in the repo. Never use
`--scope global`.

After each wave's merge-back, tests and tracking update, GSD runs `ai-kit-fold run --phase N`
inline. The command's report ends with `(inline)`.

## Missed folds

The GSD hook is advisory and can be skipped. Phase verification runs `fold.py status --phase N`,
which lists each plan as folded, unfolded or unfinished. It is read-only and reports only; it never
gates anything. To fold an unfolded plan, run the `gsd --phase N` form by hand. That is the same
command the hook runs.

## Grouping

Features are grouped by rule. When the `jev-fast-decision` skill is installed, the grouping choice
can be proposed through its entry point. A `needs_fallback` answer or no answer means the rule-based
grouping decides. Nothing needs configuring.

## NEVER

- Never move a branch by hand after a refusal.
- Never fold the base branch or a branch whose PR has merged.
- Never push, force-push or open a PR from this skill.
- Never install the capability at global scope.
- Never remove the `Ai-Kit-Fold:` trailer from a folded commit.
