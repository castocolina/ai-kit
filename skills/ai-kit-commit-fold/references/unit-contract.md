# Unit contract

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

## Checkpoint JSON (`--checkpoint FILE|-`)

The checkpoint file uses the Phase 29 schema: the commit range the checkpoint folds, the
feature candidates, the merged refs and the docs paths. Its keys and their meaning are in
`folding-policy.md`. The flow loads it with `fold_engine.load_checkpoint`. A checkpoint whose
`ref` is not the unit's branch refuses `ref_mismatch` and changes nothing.

## Signals

The adapter sends three signals, in this order. Each maps to one command:

1. **Checkpoint reached**: `checkpoint --unit FILE --checkpoint FILE`. The flow folds the
   checkpoint's commits into logical commits and pushes the unit branch.
2. **Unit finished**: `checkpoint --unit FILE --checkpoint FILE --final`. The same fold and
   push as a checkpoint; the unit is marked `finished`.
3. **Verification passed**: `ready --unit FILE`. The flow marks the unit's draft PR ready
   for review. It refuses `not_verified` unless the unit is `finished`, and `signal_order`
   when the signals arrive out of order.

What the flow does at each signal:

- Checkpoint: fold, then push the unit branch with its explicit refspec and lease. The first
  push of a unit opens a draft PR against the unit's target. A later push updates the branch.
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
  the backup tags of its folds, the title, the goal and the checkpoint count.
- Settings: `.aikit/flow.json` in the main worktree, ignored by git. Keys: `schema`, `repo`,
  push approval (`consent`), `granted`, `remote` (default `origin`), `targets` and `gates`. `gates` holds the
  project's own commands; each command is one argv list.

## Push consent

- Pushes and PRs need push consent, granted once per repository: `consent grant`
  (`--add-exclude` also ignores the settings file). `consent revoke` removes it;
  `consent status` reads it.
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
`stale_lease`, `push_failed`, `trunk_moved`, `dirty_tree`, `not_started`, `ref_mismatch`,
`restack_needed`, `mvp_below_unmerged`, `mvp_diverged`, `mvp_target_checked_out`, `no_gates`,
`restack_pending`, `bad_resolution`, `gate_failed`, `unknown_target`, `chain_locked`,
`base_mismatch`, `branch_in_worktree`, `unrecorded_branch`, `not_hotfix`, `bad_checkpoint`,
and every fold refusal reason, passed through unchanged.

## Exit codes

- `0`: done, or nothing to do.
- `1`: refused; nothing was changed.
- `2`: bad input, or the command is not available in this install.
