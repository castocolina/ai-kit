# Branches in a spec-discuss run

Read this at the first refusal of a fold command, before going back to an earlier phase, and when writing the end report. `<FOLD_PY>`, `<REPO>` and `<S>` are the §0 step 1 literals. Every switch between units goes through `fold.py start` and `fold.py guard`. Never edit `.git/ai-kit-stack.json`, and never move, delete or reset a branch by hand.

## Where am I (read-only)

1. `git -C <REPO> branch --show-current`
2. `python3 <FOLD_PY> show --all --repo <REPO>`, its output saved to the run file `<tmp>-units.txt` (`<tmp>` is the same run scratch prefix as the `<tmp>.json` roadmap file of SKILL.md §0 step 4; the branch preflight reads this file through `--units`); the run file is written only after `show --all` exits 0.
3. For each phase N of the range: its padded number `<P>` (the integer part zero-padded to two digits, a decimal suffix kept: `5` gives `05`, `2.1` gives `02.1`, the fold tool's rule) and its unit from the `show --all` lines (the unit whose id is `phase-<P>`); for a phase with a unit, its directory `<D>` read from that unit's branch, never from the current checkout: `git -C <REPO> ls-tree --name-only refs/heads/<unit branch> .planning/phases/` prints repo-relative paths, and `<D>` is the one whose last part starts with `<P>-` (none: `docs none`; two or more: show them and stop); then the separate checks `git -C <REPO> cat-file -e refs/heads/<unit branch>:<D>/<P>-SPEC.md` and, for the CONTEXT, `git -C <REPO> cat-file -e refs/heads/<unit branch>:<D>/<P>-CONTEXT.md`, else `git -C <REPO> cat-file -e refs/heads/<unit branch>:<D>/CONTEXT.md` (GSD also reads a bare `CONTEXT.md`).

```
current: <branch, or (detached)>
stack:
unit <id> branch <branch> parent <parent> state <state> exists <yes|no> tip <sha12|none>
phase <N> unit <id|none> docs <branch|none|split>
```

`stack:` is followed by the `show --all` lines verbatim (or `units: none`), and there is one `phase` line per phase of the range. `docs <branch>`: both the SPEC and the CONTEXT are on the unit's branch. `docs split`: exactly one of them is (for example the SPEC is committed and discuss has not run), and the line goes on with `(SPEC on <branch>, CONTEXT none)` or `(SPEC none, CONTEXT on <branch>)`. `docs none`: neither is, or the phase has no unit. The step moves no branch and writes nothing but its run file.

## Writing a file on its owning unit

A file is committed on the branch of the lowest open unit that owns it: a phase's own SPEC, CONTEXT and DISCUSSION-LOG on its unit; an amendment of an earlier phase J on J's unit; REQUIREMENTS.md, ROADMAP.md, STATE.md, todos, config and the goal file on the lowest open unit (the first line under `stack:` in the where-am-I output whose unit id starts with `phase-` and whose state is `open`, so a hotfix unit beside the stack is skipped and a `finished` or `ready` unit never receives them; they reach the units above by restack; with no such unit, the current branch, as with the unit flow off). Batch one phase step's writes by owner unit, lowest first, into one switch per unit and one restack:

1. `python3 <FOLD_PY> start --phase <J> --repo <REPO>`
2. `python3 <FOLD_PY> guard --phase <J> --repo <REPO>`
3. `git -C <REPO> branch --show-current` must print J's unit branch from `show --all`; otherwise show both and stop, before any read or write of J's files
4. one commit of J's files with the resolved GSD command `query commit "docs(<J>): ..." --files <J's files>`
5. the same four steps for the next owner unit up, if any
6. `python3 <FOLD_PY> restack --repo <REPO>`: after a commit on a lower unit it pushes nothing in that run, its trunk cascade included; a restacked unit that was pushed before is recorded `pending` (a never-pushed unit stays unpushed) and goes out once every unit below it is pushed at its local tip
7. `python3 <FOLD_PY> start --phase <K> --repo <REPO>`, back to the unit the step came from; going back up it refuses `bad_checkpoint: phase dir not found` when K's directory exists only on the units above J (J's tree lacks it): create only that directory (`mkdir`, nothing written in it) and re-run this `start` once
8. `python3 <FOLD_PY> guard --phase <K> --repo <REPO>`
9. `git -C <REPO> branch --show-current` must print K's unit branch from `show --all`; otherwise show both and stop

An intermediate `start` may already restack the units above locally, and a `start` run with the owner's push go-ahead publishes a `pending` tip only when every unit below it is pushed at its local tip, so after a commit on a lower unit it publishes nothing above it (the fold skill's rule). Commit before running `restack` or `start`: a modified tracked file refuses `dirty_tree` when a restack is due.

## Recipe

A refusal prints `refused: <reason>: <detail>` and a last line `refused <reason>`. Every next step ends in one of three ways: retry once after the stated change, wait for the owner, or stop. Never re-run a command unchanged while its cause is still there. A refusal or failure not in this table: show the report and stop.

| Refusal or symptom | Next step |
|---|---|
| `no_trunk` | From `start`: run `git -C <REPO> fetch` once, then re-run `start`; still refused: append the ledger line `unit flow off for phase <N>: no_trunk` and continue on the current branch (SKILL.md §1). From `restack`: run `git -C <REPO> fetch` once and retry `restack` once; still refused: show the report and stop (the commits stay on their owner unit). |
| `no_remote` | From `start`: append the ledger line `unit flow off for phase <N>: no_remote` and continue on the current branch. From `restack`: show the report and stop. |
| `stale_parent` | The newest unmerged unit's branch is gone. Show the report to the owner and stop the run. Never append a `unit flow off` line for it and never recreate the branch. |
| `unrecorded_head` | HEAD is an unrecorded branch with commits the trunk lacks. Show the listed commits to the owner and stop; the owner moves them or switches branch, then re-run. |
| `gsd_branch_mismatch` | From `branch_preflight.py`: GSD's phase branch differs from the unit branch. Stop before the first `start`; change nothing and write no config. Show both names; the owner aligns `git.phase_branch_template` or the branching strategy. |
| `wrong_parent` | The branch left its recorded parent. Show the owner and stop; never move the branch. |
| `plan_not_carried` | Show the owner the commands the report prints; never run them yourself. After the owner carries the commits, re-run `start`. |
| `branch_missing` | An open unit's branch is gone. When the report says the record holds no tip for it, show the report and stop. Otherwise run `start --phase <N>` and `guard --phase <N>` once for that unit's phase (`start` recreates the branch at its recorded tip), then re-run the refused command once; refused again: show the report and stop. |
| `ref_mismatch` | Reaches the run only as a `boundary: skipped:` note of `start`. Run `start --phase <N>` and `guard --phase <N>` for the phase being worked on; never check a branch out by hand. |
| `dirty_tree` | From `start` or `restack`: run the branch check first. Only when `git -C <REPO> branch --show-current` prints the owner unit's branch of every modified file this step wrote, commit those files and retry the refused command once. A modified file whose owner unit is not checked out, or any file this step did not write: show it to the owner and stop; never commit, stash or discard it. |
| `detached_head` | HEAD is detached. Show the report to the owner and wait; after the owner checks out a branch, retry `start --phase <N>` once. A second `detached_head`: stop. |
| `bad_checkpoint` | `phase dir not found`: create only the directory as SKILL.md §0's branch checks say (`mkdir` of GSD's directory name, nothing written in it), then re-run `start`. Any other `bad_checkpoint`: fix the input; show the report and stop if it persists. |
| `bad_value` | A wrong selector or flag. Fix the command; show the report and stop if it persists. |
| `not_started` | The phase has no unit yet. Run `start --phase <N>` first. |
| `restack_pending` | A restack is paused. Resolve it with the fold skill's cascade-conflict steps (`restack --continue --note <path>=<how>`), or `restack --abort`, then re-run the refused command once (a `start` again with its `guard` and branch check). When a later restack pass was refused without a conflict, `restack --continue` refuses `restack_not_paused`: run `restack --abort` (it restores every branch and the record to the command-entry state), fix the cause the refusal named, then re-run the refused command once. |
| paused restack (`refused conflict` from `start`, or `conflict:` lines from `restack`) | Follow the fold skill's cascade-conflict steps: resolve only the listed files, then `restack --continue --note <path>=<how>`; when the paused command was a `start`, re-run that `start` with its `guard` and branch check after the continue succeeds, before any write. Or `restack --abort` (it returns every branch to its tip at command entry) and stop. |
| `rebase_conflict` | The restore returned every branch the command moved to its tip at command entry; compare the report's tips with `show --all`. Show the report and stop. |
| `restack_not_paused` | Nothing is paused. Retry plain `restack` once if units above a moved unit still need it; else continue. |
| `bad_resolution` | It names a file or a branch tip. A named file: fix it, then retry `restack --continue` once. A moved tip: show the report and stop. |
| `gate_failed` | The restore returned every branch the command moved to its tip at command entry; compare the report's tips with `show --all`. Show the failing gate to the owner and stop. |
| `no_gates` | The resolved stack stays local. Tell the owner to set a gate; stop. |
| `branch_in_worktree` | Another worktree holds the branch. Ask the owner to switch it away and wait. Then, from `start`: retry it once; from `restack`: run `restack --abort` (it returns every branch to its tip at command entry), then retry plain `restack` once. |
| `unrecorded_branch` | A local branch outside the record sits in the restack range. Show it to the owner and stop. |
| `stale_lease`, `push_failed`, `not_descendant`, `no_consent` | A push inside `start`'s catch-up failed or was not allowed. Show the report to the owner and stop; never force or push by hand. |
| inserted phase that must sit below open units | Ask the owner. Number it after the top open unit; there is no insert-below command. |
| a phase's documents are on another unit's branch (where-am-I) | Run `start --phase <N>` and `guard --phase <N>` for the owning unit and read them there; never copy files between branches by hand. |

The `unrecorded_head` check of `branch_preflight.py` is stricter than `start`'s on purpose: it also checks a HEAD on the local trunk, exempts no phase-directory commit and counts a commit held only by a non-trunk remote branch, so it can stop a run in a state that `start` alone would accept.

## Reasons that never reach spec-discuss

`missing_field`, `unknown_field`, `signal_order`, `not_verified`, `settings_not_ignored`, `target_branch_push`, `merged_branch_push`, `mvp_below_unmerged`, `mvp_diverged`, `mvp_target_checked_out`, `unknown_target`, `chain_locked`, `base_mismatch`, `not_hotfix`, `no_pr`, `pr_failed`

They belong to checkpoint, ready, hotfix, merge-chain and settings, which this skill never runs. If one appears anyway, show the report to the owner and stop.

## End report

```
checkout: <branch>
stack:
<the show --all lines>
docs <N>: <branch>
goal file: <path> on <branch>
unit flow off: <ledger line>
```

`checkout:` is the lowest phase's unit, where the run leaves the checkout (`start --phase <lowest>` and `guard` last). One `docs` line per phase, with the where-am-I meaning of `<branch>`, `split` and `none`. Every value comes from a fresh where-am-I after the final switch. Without a goal file write `goal file: none`; without any `unit flow off` ledger line write `unit flow off: none`. With the unit flow off (a `unit flow off` ledger line) the run makes no final switch and prints `checkout: <current branch> (unit flow off)`. With the fold skill not installed the report still has five fields: `checkout:` the current branch, `stack: none (fold not installed)`, each `docs <N>:` the current branch, `unit flow off: fold not installed`.
