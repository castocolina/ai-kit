# Adapter guide

Read this when wiring a planning system other than GSD or superpowers to the unit flow, or when
a GSD or superpowers run's flow step needs its hook point or command order.

An adapter connects one planning system to the unit flow. It maps the system's own units and
finished steps onto the neutral contract in `unit-contract.md`. Two adapters ship with
ai-kit: GSD and superpowers. A third system uses the same two inputs (`--unit` and
`--checkpoint`).

## GSD adapter

Mapping: a GSD phase is one unit; each finished plan of the phase is one checkpoint. The
phase's last plan is the unit-finished signal. The adapter's unit id is the phase number.

GSD dispatches three hook points that the flow uses:

1. `discuss:pre` step: `ai-kit-fold start --phase N`. It creates the unit's branch on the
   stack top and checks it out before the phase's first commit. Phase-directory commits made
   only locally before it stay on the unit branch (`unit-contract.md`, "Start and local
   planning commits").
2. `execute:wave:post` step: `ai-kit-fold checkpoint --phase N`. After each wave it folds the
   finished plans and pushes the unit branch.
3. `ship:pre` gate (blocking): `ai-kit-fold ship`. It always refuses GSD's own ship. It
   refuses `not_ready` until the unit's state is `ready`, then `ship_redirect`, which tells the
   owner to run `fold.py merge-chain`. The gate reads the state with `fold.py show`. The
   install prompt does not show gates, so this gate is named here and in `SKILL.md`.

GSD does not dispatch the flow at three points, so the orchestrator runs these commands itself
as numbered instructions:

- `gsd-tools ai-kit-fold start --phase N`, before plan-phase when discuss was skipped. GSD's
  `plan:pre` point has no command arm, only skill and agent arms, so a step cannot run there.
- `gsd-tools ai-kit-fold guard --phase N`, before execute-phase. GSD's `execute:wave:pre` point
  dispatches contributions and steps only and never evaluates a gate, so a guard cannot run
  there. The guard refuses `wrong_parent` when the unit's recorded parent tip is not the merge
  base of its branch.
- `gsd-tools ai-kit-fold ready --phase N`, after the verifier reports `passed`. GSD's
  `verify:post` point runs before `VERIFICATION.md` is written, so the ready signal cannot be
  read there.

The GSD adapter does not set `git.base_branch`; it stays unset. When GSD worktrees are on,
`start` sets `worktree.baseRef` to `head`.

## Superpowers adapter

Mapping: a superpowers plan is one unit, with one checkpoint at its end. The checkpoint's
`--base` is the commit before the plan's first task, so the fold covers only this plan's
commits.

The `ai-kit-spec-execute-superpowers` skill runs these commands, in this order:

1. Step 1, before the first task: `fold.py start --plan <plan file>`. The unit's branch is
   created on the stack top and checked out, or reused when it already sits there. The plan
   file and the other local-only planning commits stay on the unit branch, below the fold
   range; `plan_not_carried` names the commands for the owner to run; stop and show them.
2. Step 5, after the final review passes: `fold.py checkpoint --plan <plan file> --base "$FOLD_BASE" --final`.
   The flow report is relayed verbatim. A refusal changes nothing.
3. After the final review: `fold.py ready --plan <plan file>`, once verification has passed.

The finishing step's merge, push and PR options are not used for a unit. A plan run inline,
without that skill, follows the same three commands.

Planning commits: superpowers' brainstorming and writing-plans skills commit the spec and the
plan before Step 1, and ai-kit owns no hook in them. `start` carries those local-only commits
onto the unit branch, so the PR holds them and `FOLD_BASE` (HEAD after `start`) sits above them.

## Adding a third system

A system that is not GSD or superpowers needs no change to the flow's code:

1. Write the unit JSON (`--unit FILE`) with the required keys and any optional ones from
   `unit-contract.md`.
2. Call `fold.py start --unit FILE` before the unit's first commit.
3. For each finished checkpoint, call `fold.py checkpoint --unit FILE --checkpoint CP.json`.
   Pass `--final` on the unit's last checkpoint.
4. On the system's verification signal, call `fold.py ready --unit FILE`.

The checkpoint file's keys are in `unit-contract.md` (Checkpoint JSON). The flow prints one
report per call and exits with the codes in `unit-contract.md`.
