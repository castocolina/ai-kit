# Phase 38: Runner hardening and run safety - Discussion Log (standard discuss mode (`--analyze --all --batch`) for the interactive path)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-11-16
**Phase:** 38-runner-hardening-and-run-safety
**Mode:** interactive path: no owner question was unclear enough to relay (the owner answers only unclear gray areas in this
run); every gray area was screened with jev and decided by the decision table; no gsd-assumptions-analyzer run (the owner
did not ask for it; the scouting was done live in the phase subagent), best design over smallest diff
**Areas analyzed:** where the watchdog lives, tree polling cost, idle default and ending, execute versus review signals, lock
home, lock result, release paths, review and the lock, baseline scope, plan-versus-commits matching, task parsing, admission
list, forbidden default, result mapping, jev and herdr roles, the router rule, the quota-cycle class, the self-test home, the
gsd-core skill call, dead code and the timeout item, backlog 999.21, the spike, skills and docs

## Assumptions Presented

No analyzer ran. The scouting covered the runner's `runChild`, `runOnce`, `runCli`, `main`, `treeState`, `changedPaths`,
`rung2Gate`, `finish` and status table, GSD's cross-AI step and stall surveillance, the 999.15 incident catalogue, the Phase 25
review, the curated-config and superpowers code behind each cleanup item, and the hosts' help, all live on 2026-11-16 (SPEC
Background and Findings).

| Assumption | Confidence | Evidence |
|---|---|---|
| The watchdog can sit in `runOnce` with the ladder reached through the timed-out path | Likely | `runChild` has one finalize with reasons; an early kill leaves budget; one `idle-then-resume` case proves it |
| A tree read per check interval is cheap enough | Confident | 0.21 s for the same git commands on a 3,137-file repository, run live |
| pi prints nothing while working, so a review lane has no signal on it | Likely | 999.15-LESSONS 1.14 (26 phases), not re-probed; the spike records it |
| The Phase 25 cleanup list is still accurate | Unclear | three items verified dead, two kept (live caps), one item's code was removed in Phase 31, one is already fixed in code (999.21) |
| A prompt-only check can see the plan | Likely | GSD's prompt carries `<task>` blocks with files, no plan id; non-GSD prompts give `coverage=n/a` |
| Alias-assumed routers should get the quota cycles | Unclear | Phase 35 D-15 assumes them, Phase 25 required confirmation; flagged for the owner |

## jev screening

Three requests (spec items seven, a second opinion on two, discuss items six). Summaries only.

| Item | jev | Outcome |
|---|---|---|
| idle default | laya s1800 low 0.40; typesafe derived low 0.40 | **Own reasoning:** 900 s (D-03, ledger) |
| idle ending | ladder, choice 0.95 (laya low 0.42 agrees) | D-04 |
| execute signals | laya out low 0.48; typesafe out_tree low 0.72 | **Own reasoning:** D-05 (ledger) |
| lock home | state, choice 0.98 (laya tree low 0.46) | D-06 |
| lock result | laya e2 0.78; second opinion typesafe e75 choice 0.91 (second opinion) | **jev overridden:** D-07 |
| match rule | files, choice 0.99 (laya count low 0.47) | D-11 |
| admission effect | typesafe with 0.87 (laya note low 0.43); second opinion alone choice 0.99 (second opinion) | **jev overridden:** D-13 |
| self-test home | sibling, choice 0.82 (laya low 0.60 agrees) | D-19 |
| baseline scope | record, choice 0.95 (laya low 0.40 agrees) | D-10 |
| router rule | laya always low 0.66; typesafe confirmed low 0.62 | **Own reasoning:** D-17 (ledger) |
| forbidden default | orch, choice 0.94 (laya none low 0.52) | D-14 |
| herdr role | visible, choice 0.86 (laya liveness low 0.57) | D-16 |
| timeout restore | amend, choice 0.87 (laya only) | D-21 |

## Live facts that changed the plan

- WR-05's code (`clear-workflow-keys`) left with `ai-kit-spec-execute-gsd` in Phase 31, so "restored on cleanup" has nothing to
  restore from; the item becomes a visible, tested before and after (D-21).
- Backlog 999.21 (temp folders) is already fixed in code (c535683); only a proof case is missing (D-22).
- `clampCapS` and `clampAttemptTimeout` are live and security-relevant, `stoppedWhy`'s cooldown branch and `clampCooldownS` are
  already gone: the cleanup list shrinks to three dead items (D-21).
- `classify_dispatch_failure` already returns `quota`; what remains is the token parsing in the reference (D-18).
- GSD's cross-AI prompt has task blocks and no plan id, and its command string is fixed, so the check reads files, with
  `--plan-id` as an add-on (D-11, D-12).
- A GSD `exit 0` means done: a result with a blocking finding must be non-zero, with empty stdout (D-15).
- Python's `STATUS_TO_REASON` already holds an `idle_stall` key for old runners; no new status is needed for the watchdog.
- Phase 35 makes router aliases assumed, which would switch the Phase 25 quota cycles off for them under both existing rules
  (D-17).

## Corrections Made

- ROADMAP Phase 38 gains dated notes (code anchors, criteria 1 to 4, a new criterion 5 for the temp-folder proof with the judge
  bar moving to 6); RUN-03, RUN-04, RUN-07 and RUN-08 gain dated notes; backlog 999.21 is marked absorbed.
- 37-SPEC R8 and 37-CONTEXT D-18 and its Phase 38 handoff: the render is a plain config splice because the harness becomes a
  sibling file, so the sync test is not relaxed.

## External Research

None. No web source was needed; every claim is from the installed tools, the repository and GSD's installed workflows.

# Update 2026-11-16 (re-run 2, herdr hosting, interactive path)

**Input:** `38-SPEC.md` with the new R12 (RUN-13) and the 38 CONTEXT of the same day (D-01 to D-24 kept verbatim; D-16 amended in
place; D-25 to D-33 added). Owner directive: the runner may host a lane in a herdr tab (Phase 37 R12, D-22 to D-29); the open
design points handed to this phase are the lock, the sweep, the idle clock, the execute checks and the secret files.
**Mode:** interactive path, no owner question was unclear enough to relay; jev screening (ten items, one request per backend; typesafe
answers came back forced on the ten-item batch, so the items were re-asked in batches of four and five), live checks on herdr 0.9.5,
best design over smallest diff. No analyzer ran.
**Areas analyzed:** what identifies a running hosted lane for the lock, a stale lock with a surviving tab, when the sweep runs, what
proves a tab is closable, a dead run's directory when herdr is unreachable, the hosted idle signal, env-file lifetime, unbounded
output files, a state home inside the checkout, the sweep under a hosting switch-off

## jev screening

| Item | jev | Outcome |
|---|---|---|
| lock identity | typesafe runner_plus_launcher_group low 0.50; laya runner_only low 0.48 (forced) | **Own reasoning:** D-26 (ledger) |
| stale lock with a tab | typesafe clear_lock_and_sweep_tab low 0.47; laya none_of_these low 0.42 | **Own reasoning:** D-26 (ledger) |
| sweep trigger | laya every_run_plus_explicit_flag low 0.27; typesafe none_of_these low 0.52 | **Own reasoning:** D-27 (ledger) |
| sweep proof | laya none_of_these 0.77 (contradicts the evidence); second opinion typesafe dead_run_record_id_and_label 0.94 | **jev overridden** (first answer): D-27 |
| herdr unreachable | laya none_of_these low 0.64; typesafe drop_secrets_keep_record low 0.41 | **Own reasoning:** D-27 (ledger) |
| idle signal | typesafe file_size_growth 0.90 (laya none_of_these low 0.52) | D-28 |
| env file lifetime | typesafe launcher_deletes_at_start low 0.78; laya until_directory_removed low 0.49 | **Own reasoning:** D-31 (ledger) |
| output files | laya end_lane_at_ceiling low 0.66; typesafe end_lane_at_ceiling low 0.65 | **Own reasoning, jev not followed:** D-30 (ledger) |
| state home in the checkout | laya refuse_hosting low 0.31; typesafe exclude_path_from_snapshot low 0.77 | **Own reasoning:** D-29 (ledger) |
| sweep under switch-off | laya none_of_these low 0.39; typesafe never_close low 0.48 | **Own reasoning:** D-27 (ledger) |

## Live facts that changed the plan

- The launcher is its own group's leader and its parent is the pane shell, so the lock's child group for a hosted lane is the
  launcher's group (D-26); `tab close` ended plain and `nohup` children but not a `setsid` grandchild (D-32).
- `tab list` and `tab get` carry the label and `tab close` of an unknown id and an unreachable server give distinct error codes, so
  one `tab list` per sweep gives the id and label proof, and "herdr unreachable" is told from "tab already gone" (D-27).
- Polling the three files costs 0.08 % of a core at 250 ms (D-28); a launcher can delete its env and prompt files as its first steps
  (D-31); an append-mode file can be truncated under a writer without a sparse file (D-30).
- Reading the snapshot design: a state home inside the checkout would turn a hosted lane's growing `out` into a tree change (D-29).

## Corrections Made

- 38 SPEC: R12 and its edge rows and prohibitions added; R1, R3, R5 and R11 gain dated amendment bullets; the Background, Boundaries,
  Constraints and the herdr prohibition amended in place; Phase 38 ROADMAP gains criterion 7 and RUN-13; REQUIREMENTS gains RUN-13
  (186 total) with notes on RUN-03, RUN-07 and EXE-06; ROADMAP Phase 42 criterion 3 notes that the sweep is the runner's.
- 37 CONTEXT D-25 (the env file's lifetime shrinks) and D-26 (the record is `run.json`, the verb set grows by `tab list`) and its
  researcher questions (poll interval, `pid` file, grandchild) carry dated notes; 37 SPEC's constraint gains the sweep's `tab list`.

## External Research

None. Every claim is from herdr 0.9.5, node 24.21.0 and Linux 7.3 on this machine, the repository and the installed skills.
