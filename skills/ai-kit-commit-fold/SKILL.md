---
name: ai-kit-commit-fold
description: "Folds a finished GSD or superpowers plan's commits into one commit per logical feature by one written policy, and runs the unit flow: start a unit branch, push its checkpoints, mark its PR ready, restack a stack, make a hotfix, run the merge chain, ask for push consent. Use when a finished plan should become one commit per logical feature, to start a unit branch, push a checkpoint, mark a PR ready, restack, hotfix, run the merge chain, ask for push consent, or install the GSD hooks. Not for squashing a branch or interactive rebases."
---

# ai-kit-commit-fold

Folds the commits of one finished plan into one commit per logical feature, and runs the unit flow
that pushes a unit's checkpoints and opens its PR. The rules live in `references/folding-policy.md`:
read it before folding by hand. The unit contract and the adapters are in
`references/unit-contract.md` and `references/adapter-guide.md`. This file does not restate the policy.

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

The fold's report has five lines: the unit, the counts with the grouping source, the tree check, the
backup tag and the outcome. A refusal changes nothing, so the branch stays where it was. Report the
reason to the user and stop:

| Reason | What to tell the user |
|--------|-----------------------|
| `dirty_tree` | Tracked files have uncommitted changes. Ask the user to commit or discard them, then re-run. |
| `branch_moved` | The branch is no longer at the tested tip. Re-run from its current tip. |
| `no_base_branch` | Neither the base branch nor its origin copy resolves. Ask which base branch to use. |
| `range_on_base_branch` | The range sits on the base branch, which is never rewritten. Do not fold. |
| `range_on_merged_branch` | The range is on a branch whose PR has merged, which is never rewritten. Do not fold. The unit flow's checkpoint passes the recorded merged unit branches and refuses it; the `gsd` and `superpowers` forms pass none, so check the PR yourself. |
| `foreign_merge` | A merge in the range is not one of the plan's own merge-backs. Ask the user to review it. |
| `plan_not_contiguous` | Another plan's commit sits inside this plan's run. Ask the user to review the history. |
| `detached_head` | HEAD is not on a branch. Ask the user to check out a branch. |
| `tree_mismatch` | The folded tree differs from the tested tree, so the branch did not move. Report it as a bug. |
| `tag_exists` | The backup tag name points at another commit. Report it; do not delete the tag. |
| `policy_missing` | The folding policy text is missing or empty. Report it; do not fold. |
| `bad_checkpoint` | The plan, phase, checkpoint or `--base` input does not parse or resolve. Fix the input. |
| `git_error` | Git failed. The report's first error line says how. Report it. |

## Unit flow

A unit is one planned piece of work: a GSD phase, or a superpowers plan. The flow takes it as unit
JSON (`--unit FILE|-`) or by selector: `--phase N` for GSD, `--plan FILE` for superpowers, and
`--unit-id ID` for a unit already recorded. Each command prints the flow report: its first line is
`flow <command> <unit>:` and its last line is `outcome:`.

- `fold.py start <selector>`: create the unit's branch on the stack top, or reuse it. Run it before
  the unit's first commit.
- `fold.py guard <selector>`: read-only. It refuses `wrong_parent` when the unit's recorded parent
  tip is not the merge base of its branch and its parent.
- `fold.py checkpoint <selector> [--checkpoint FILE|-] [--base REV] [--final]`: fold the
  checkpoint's commits, push the branch, and open the draft PR at the first push. `--final` marks the
  unit finished. `--base` is valid only with `--plan`.
- `fold.py ready <selector>`: mark the draft PR ready for review. It refuses `signal_order` before
  the unit is finished and `not_verified` until verification has passed.
- `fold.py show <selector>`: read-only. Prints the unit's `state:` and `pr:`.

The stack and settings commands:

- `fold.py hotfix --target BRANCH --name SLUG`: start a hotfix unit from its target. It never joins
  the stack.
- `fold.py restack [--continue [--note PATH=HOW ...] | --abort]`: finish or abort a paused restack.
  See Cascade conflicts.
- `fold.py merge-chain [--until UNIT_ID | --unit-id HOTFIX_ID]`: merge the stack's PRs in order. See
  Hotfix and merge chain.
- `fold.py settings show` and `fold.py settings set [--remote NAME] [--target BRANCH ...] [--gate "CMD" ...]`:
  read or set the remote, the target branches and the project's gates.
- `fold.py consent grant [--add-exclude] | revoke | status`: push consent. See Push consent.

## Push consent

The flow pushes branches and opens PRs only with push consent, which is granted once per repository.

1. Before the first push, ask the owner once. Name what is pushed (the unit branches, to the remote,
   with their PRs) and the revoke command, `fold.py consent revoke`.
2. Never grant push consent yourself. Run `fold.py consent grant` only after the owner says yes.
   `--add-exclude` also ignores the settings file; use it only when the owner asks.
3. Without push consent the flow still folds locally and lists each skipped push as
   `skipped: <unit> push <branch>`; the outcome is `skipped (no consent)`. When push consent is
   granted later, the skipped checkpoints are pushed in stack order.

## Cascade conflicts

A `restack` that stops on a conflict leaves the stack paused. Dispatch the resolution to a subagent
where the host has one, otherwise do it yourself:

1. For each listed file, keep both sides' intent; merge `.planning/` files by content, keeping both
   sides' entries. Never edit a file outside the conflict list.
2. Run `fold.py restack --continue --note <path>=<how>` once, with one `--note` per resolved file.
   If a file cannot be resolved with confidence, run `fold.py restack --abort` and report it.
3. Read the `gates:` line of the report: it names every gate that ran (a GSD project adds
   `gsd-tools validate health`).
4. On a `no_gates` refusal the stack stays local and unpushed. Tell the owner to set a gate with
   `fold.py settings set --gate "CMD"`; set gates yourself only when the owner asks. Then rerun
   `fold.py restack --continue`.

## Hotfix and merge chain

- Hotfix targets come from the settings. `fold.py hotfix` branches a hotfix unit off its target.
- `fold.py merge-chain` (or `--unit-id <hotfix id>` for one hotfix) merges PRs. Run it only when the
  owner asks, and report where the chain stopped.

## GSD install

Install the fold into a GSD project with the project's own gsd-tools:

1. `node .claude/gsd-core/bin/gsd-tools.cjs capability install <this skill>/gsd/ai-kit-commit-fold --scope project`.
   It asks for approval, because the capability loads a command module into the GSD CLI. Ask the owner.
2. After a yes, run the same command with `--yes`, then commit `.gsd/capabilities/ai-kit-commit-fold/`
   and `.gsd-capabilities.json`. A fresh clone repeats `--yes`. Never use `--scope global`.

## GSD hooks

The installed capability registers these GSD hook points:

- `discuss:pre` step: `ai-kit-fold start`. It creates the unit's branch before the phase's first
  commit.
- `execute:wave:post` step: `ai-kit-fold checkpoint`. After each wave's merge-back it folds the
  finished plans and pushes the branch, under push consent.
- `ship:pre` gate (blocking): `ai-kit-fold ship`. It always refuses GSD's own ship: `not_ready`
  until the unit is ready, then `ship_redirect`, which sends the owner to `fold.py merge-chain`. The
  install prompt does not show gates, so this one is named here.

GSD dispatches no flow command at three points, so run these yourself, as numbered instructions:

1. Before plan-phase, when discuss was skipped: `gsd-tools ai-kit-fold start --phase N`.
2. Before execute-phase: `gsd-tools ai-kit-fold guard --phase N`. On `wrong_parent`, stop.
3. After the verifier reports `passed`: `gsd-tools ai-kit-fold ready --phase N`.

When the `start` step's report ends `refused`, stop before the next planning commit and show the
report to the owner.

## Missed folds

A GSD hook can be skipped. Phase verification runs `fold.py status --phase N` (read-only: it lists
each plan as folded, unfolded or unfinished). To fold an unfolded plan by hand, run `gsd --phase N`.

## Grouping

Features are grouped by rule. When the `jev-fast-decision` skill is installed, the grouping choice
can be proposed through its entry point. A `needs_fallback` answer or no answer means the rule-based
grouping decides. Nothing needs configuring.

## NEVER

- Never move a branch by hand after a refusal.
- Never fold the base branch or a branch whose PR has merged.
- Never push without push consent.
- Never force-push by hand; the flow pushes with an explicit lease.
- Never merge a PR outside the owner-started merge chain, and never squash or rebase-merge.
- Never set gates yourself unless the owner asks, and never install the capability at global scope.
- Never remove the `Ai-Kit-Fold:` trailer from a folded commit.
