# Unit contract

Read this when a flow report ends `refused <reason>` with a reason `SKILL.md` does not list, when
writing a unit or checkpoint JSON file, or when reading the stack record.

The unit flow takes work from any planning system through one neutral contract. An adapter
(a planning system's own hook or script) writes the unit JSON, calls `start`, and sends the
flow its checkpoints and signals. The flow does not know which system produced them. The
adapters are in `adapter-guide.md`; the folding rules are in `folding-policy.md`.

## Terms

- **Unit**: one finished piece of planned work that gets one branch and one PR.
- **Checkpoint**: a point inside a unit where its work is folded into logical commits and
  pushed. A unit may have several checkpoints; its last one is marked `--final`.
- **Target branch**: a branch units merge into. Configured per project in the settings file;
  the default is the remote's HEAD branch, else `main`.
- **Trunk**: the target branch a stack is based on.
- **Stacked unit**: a unit that branches off the newest unmerged unit below it, or off the
  trunk when none is unmerged.
- **Hotfix unit**: a unit that branches off its own target and never joins the stack.

## Unit JSON (`--unit FILE|-`)

Required keys:

- `schema`: the integer `1`.
- `id`: a string matching `^[A-Za-z0-9._-]{1,64}$`. It names the unit in the stack record,
  the report and the backup tags.
- `kind`: `stacked` or `hotfix`.
- `branch`: the unit's branch name.
- `title`: a non-empty string; the draft PR title.

Optional keys:

- `target`: the target branch. Defaults to the trunk.
- `goal`: a one-line description for the PR body.
- `mvp`: a boolean. Enables the MVP fast path (below).

An unknown key, a missing required key or a bad value refuses the call (`unknown_field`,
`missing_field`, `bad_value`) and changes nothing.

## Start and local planning commits

`start` creates the unit branch on the stack top and checks it out. With `--plan` or `--phase`
the adapter also names the unit's plan paths: for `--plan`, the plan file and the spec its
`**Spec:**` line names (when that file is in the repo); for `--phase`, the phase directory. When HEAD has commits that touch those paths and
that no remote branch and no recorded unit holds (a plan committed only locally), `start` keeps
them on the unit branch: the branch starts at HEAD when HEAD sits on the stack top with only
such plan commits between; otherwise only those plan commits are cherry-picked onto the stack
top, from a clean tree only (`dirty_tree` otherwise), so unrelated local commits stay off the
unit and out of its PR. A pick that fails is aborted, HEAD is restored, the
new branch is deleted and `start` refuses `plan_not_carried`, naming the commands for the
owner to run; the agent stops and shows them. The record keeps their count as `carried`; a plan-file checkpoint without
`--base` folds from above them, so the planning commits are never folded.

## Boundary (`boundary`)

`fold.py boundary <selector> --point start|plan|wave`, or `boundary --next --point plan` before a
unit exists, runs the boundary step: it refreshes this checkout's code index and graph under the
index lock shared with the worktree job, then rewrites `.aikit/brief/SKILL.md`, the brief the
next agents read. The three points are the unit's start (`start` runs it itself, last), before
planning, and before the first execution wave; the `wave` point is skipped once every wave-1 plan
of the unit has its summary. A tool that is missing or fails is one report line, never a refusal.
The report lines are `codegraph:`, `graphify:`, at most one `note:`, `brief:` and `outcome:`; the
brief lists the previous unit's range and changed files, an explore instruction for the agents,
and the tracked documents that mention the changed names. The brief says which documents mention
a name, never what a document describes. A recorded unit whose branch is not HEAD is refused
(`ref_mismatch`) before any refresh or write.

## Checkpoint JSON (`--checkpoint FILE|-`)

Read this when writing a checkpoint file for `--checkpoint` or for `fold.py fold`. One JSON
object; unknown keys are ignored. `fold_engine.load_checkpoint` validates it, and a bad value
refuses `bad_checkpoint`. A checkpoint whose `ref` is not the unit's branch refuses
`ref_mismatch`. Neither changes anything.

- `schema`: the integer `1`.
- `unit`: the id (the pattern of the unit JSON `id`); it names the backup tag.
- `ref`: `refs/heads/<branch>`, the branch to fold.
- `base`: the full sha below the first commit to fold.
- `end`: the full sha of the last commit to fold; defaults to `tip`. Commits in `end..tip` are
  replayed unchanged on top of the folded ones.
- `tip`: the full sha of the branch tip that was tested.
- `base_branch`: the branch never rewritten (its local and `origin/` copies).
- `merged_refs`: optional full ref names whose commits are never rewritten.
- `own_merge_subjects`: optional subject prefixes of the merges that fold away; any other
  merge in the range refuses `foreign_merge`.
- `candidates`: the features, in order: each has `id`, `title`, `files` (paths) and an optional
  `summary`. Each commit joins the candidate whose files it touches most.
- `docs_paths`: optional path prefixes that go into the last folded commit.

```json
{"schema": 1, "unit": "unit-a", "ref": "refs/heads/demo/unit-a",
 "base": "<40-hex sha>", "tip": "<40-hex sha>", "base_branch": "main",
 "candidates": [{"id": "t1", "title": "Feature A", "files": ["a.py", "tests/test_a.py"]}],
 "docs_paths": ["docs/"]}
```

## Signals

The adapter sends three signals, in this order. Each maps to one command:

1. **Checkpoint reached**: `checkpoint --unit FILE --checkpoint FILE`. The flow folds the
   checkpoint's commits into logical commits and pushes the unit branch.
2. **Unit finished**: `checkpoint --unit FILE --checkpoint FILE --final`. The same fold and
   push as a checkpoint; the unit is marked `finished`.
3. **Verification passed**: `ready --unit FILE`. The flow marks the unit's draft PR ready
   for review. It refuses `signal_order` before `checkpoint --final` or while a unit below is
   not ready, and `not_verified` while the unit's verification has not passed.

What the flow does at each signal:

- Checkpoint: fold, then push the unit branch with its explicit refspec and lease. The first
  push of a unit opens a draft PR against its parent unit's branch while that parent is
  unmerged, else against the unit's target. A later push updates the branch.
- Unit finished: as a checkpoint, then the unit is complete and waits for verification.
- Verification passed: marks the draft PR ready. A PR is never marked ready before the unit
  is finished.
- MVP fast path (unit `mvp: true`, and no unmerged unit below it): each checkpoint
  fast-forwards the target to the unit tip and pushes the target. No PR is opened. An MVP unit
  above an unmerged unit is refused `mvp_below_unmerged` and opens a draft PR instead.
- A checkpoint with no new commits makes no push.

## Stack record and settings

- Stack record: `ai-kit-stack.json` in the git common directory. Schema `1`, with a `units`
  list in stack order. Each entry holds the unit's id, kind, target, branch, parent, the
  parent tip at start, the PR number, the state (`open`, `finished`, `ready`, `merged`), the
  `mvp` flag, the remote sha last pushed by the flow, any pending sha left by a skipped push,
  the backup tags of its folds, the title, the goal, the checkpoint count and `carried` (the
  local planning commits `start` kept below the fold range).
- Settings: `.aikit/flow.json` in the main worktree, ignored by git. Keys: `schema`, `repo`,
  push approval (`consent`), `granted`, `remote` (default `origin`), `targets` and `gates`. `gates` holds the
  project's own commands; each command is one argv list.

## Push consent

- Pushes and PRs need push consent, granted once per repository: `fold.py consent grant`
  (`--add-exclude` also adds `.aikit/` to `.git/info/exclude`, so git ignores the settings
  file). `fold.py consent revoke` removes it; `fold.py consent status` reads it.
- Without push consent a checkpoint still folds the branch locally and the report lists
  `skipped: <unit> push <branch>` and `outcome: <unit> skipped (no consent)`. The folded sha
  is kept as the unit's pending sha.
- When push consent is granted later, the skipped checkpoints are pushed in stack order,
  bottom up, through the normal checkpoint and cascade rules.

## Report

Plain text. The first line is `flow <command> <unit>: <branch>`. The last line is
`outcome: <unit> <done | nothing to do | skipped (no consent) | refused <reason>>`. Between them
at most six lines, plus one `skipped:` line per skipped push. Token-shaped strings are
redacted.

## Reason codes (refused)

`missing_field`, `unknown_field`, `bad_value`, `signal_order`, `not_verified`, `wrong_parent`,
`no_trunk`, `no_remote`, `settings_not_ignored`, `target_branch_push`, `merged_branch_push`,
`stale_lease`, `push_failed`, `not_descendant`, `dirty_tree`, `not_started`, `ref_mismatch`,
`branch_missing`, `mvp_below_unmerged`, `mvp_diverged`, `mvp_target_checked_out`, `no_gates`,
`restack_pending`, `bad_resolution`, `gate_failed`, `unknown_target`, `chain_locked`,
`base_mismatch`, `branch_in_worktree`, `unrecorded_branch`, `not_hotfix`, `bad_checkpoint`,
`plan_not_carried`, `no_consent`, `no_pr`, `pr_failed`, `rebase_conflict`, `restack_not_paused`,
and every fold refusal reason, passed through unchanged.

## Exit codes

- `0`: done, or nothing to do.
- `1`: refused. Steps finished before the refusal (a catch-up push, a fold, earlier merges)
  stay done and are listed in the report.
- `2`: bad input, or the command is not available in this install.
