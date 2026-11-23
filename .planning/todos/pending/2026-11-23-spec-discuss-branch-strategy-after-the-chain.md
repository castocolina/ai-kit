---
created: 2026-11-23T14:45:00Z
title: Give spec-discuss a branch strategy for the stacked units it starts, and for every step after the chain
area: skills
severity: major  # suggested by the capture agent, not confirmed by the owner
files:
  - skills/ai-kit-gsd-spec-discuss/SKILL.md:96-117
  - skills/ai-kit-gsd-spec-discuss/SKILL.md:188-192
  - skills/ai-kit-gsd-spec-discuss/SKILL.md:234-240
  - skills/ai-kit-gsd-spec-discuss/evals/evals.json
  - skills/ai-kit-commit-fold/SKILL.md:57-83
  - skills/ai-kit-commit-fold/SKILL.md:173-183
  - skills/ai-kit-commit-fold/references/unit-contract.md:43-59
  - skills/ai-kit-commit-fold/scripts/flow_unit.py:205-222
  - skills/ai-kit-commit-fold/scripts/flow_git.py:164-173
  - tests/test_flow_docs.py
---

## Problem

Owner request (2026-11-23, translated from Spanish): for each phase it is given, spec-discuss creates the
branch, which is not wrong; the problem is that afterwards the orchestrator does not know how to go back, or
assumes each document must live in its own branch, and gets confused when it implements or plans. We need a
strategy for these conflicts, taken from how the transcripts resolved them.

What the skill says today (read 2026-11-23):
- `SKILL.md:102-117`: run `fold.py start --phase <N>` before each phase's first commit; `start` creates the unit
  branch on the stack top and checks it out (`unit-contract.md:45`). So a run over phases N..M leaves N..M as
  stacked branches and the checkout on M.
- `SKILL.md:236-240`: a fact found in phase K that contradicts phase J's SPEC/CONTEXT, REQUIREMENTS.md or
  ROADMAP.md "amends them in K's commit". On a stack, K's commit sits on K's branch, above J. J's own branch
  never sees the amendment.
- `SKILL.md:188-192`: the `docs(state)` commit and the goal-prompt file are committed at the end of the range,
  so on the last phase's branch (the stack top).
- Nothing in SKILL.md or its five references says which branch a later step (plan, execute, a re-discuss, an
  amendment) must be on, how to get back to phase J's branch, or what the end report must say about branches.
  The words branch, stack and unit do not appear in `references/` (grep, 2026-11-23).
- None of the 8 evals in `evals/evals.json` covers a branch question after the chain (ids: casual range,
  auto mode, interactive mode, jev absent, locked-decision conflict, blocking unresolved, start before the
  spec commit, start skill missing).

## Evidence from the transcripts

Transcripts are read-only, quoted in a few words, owner words translated. Session files are under
`~/.claude/projects/<project folder>/<id>.jsonl`; numbers are JSONL line numbers.

### home-mobility, session 3adfa2df (one session, one skill load at line 5004)

The only home-mobility transcript that loaded the skill (the other file, d52aaa07, is 2 lines). One run of
phases 2-7, 2026-11-23 14:17-14:28 UTC. It never finished a phase, so it shows nothing about the steps after
the chain; it shows a collision at the first `start`. Lines 5502-5648 are a replay after a context compaction
(no timestamps), not a second run.
- 2026-09-07 14:18 (line 2330): the project set GSD's own `git.branching_strategy` to `phase`. At 21:28
  (line 3912) gsd-tools' commit helper printed `phase branch "gsd/phase-01-pwa-project-scaffold" created;
  switched to it for this commit`. This branch is GSD's, not a recorded unit of the fold flow.
- 2026-11-23 13:58-14:12: config, docs and a todo were committed on that phase-01 branch, never pushed.
- 14:21:10 (line 5156): `fold.py start --phase 2` reported `started unit phase-02 on main` at the old trunk
  tip d5b43de. `start_point` (`flow_git.py:164-173`) stacks on the remote trunk tip when no unmerged unit is
  recorded, and only commits that touch phase 2's directory are carried (`unit-contract.md:47-51`). Phase 1's
  CONTEXT, the MVP-mode config and the new todo were silently left behind on the phase-01 branch.
- 14:22-14:24 (lines 5222-5421): the orchestrator saw it, fast-forwarded `main` by hand, deleted both branches,
  got `refused: branch_missing` (the record still held phase-02), overwrote `.git/ai-kit-stack.json` with an
  empty record by `echo >` twice, re-ran `start` (again on the old remote tip), then tried `git push origin
  main`, which the host's auto-mode classifier denied (line 5415).
- 14:28 (line 5439): owner answered "Wait, I need more config"; the run stopped with no spec written, `main`
  5 commits ahead of origin, no unit, and a hand-reset stack record. Unresolved.
- Cost: about 7 minutes and one owner stop; the hand moves break the fold skill's NEVER list
  (`ai-kit-commit-fold/SKILL.md:202`, "Never move a branch ... the owner decides").

### ai-kit, session 635881b5 (the phases 35-39 runs; loads at lines 654 and 2132)

- 2026-11-16 13:13 (line 765): `start --phase 35` refused `bad_checkpoint: phase dir not found`; handled by the
  skill's row. Phases 35, 36, 37, 38, 38.1, 39 were each specced and discussed on their own stacked branch.
- 15:58 (lines 1891-1905): a fold refused `ref_mismatch` because HEAD was on the stack top, not on unit 35;
  the orchestrator switched to 35 and repeated. Fine, but it shows the checkout is left on the top.
- Re-run for herdr items, 17:02-17:48 (lines 2146-2459): amendments were made on each earlier phase's own
  branch (36, then 37) and the stack was folded and restacked upward after each. Each restack needed push
  consent (line 2209, asked of the owner). At 17:24 (line 2345) the restack of 37 paused on a conflict:
  37's new decision numbers collided with numbers that 38.1 had already added to the same file. A resolver
  subagent kept both sides and renumbered; two stale references were fixed at the top (line 2459).
- The goal file for 35-39 was rendered at the end of the range; the run ledger
  (`tmp/run-2026-11-19/ledger.md`) shows where everything ended up:
  - Ledger line 7 (2026-11-19 22:12): "the 5 local docs commits sat only on top of unit 39, so units 35 to
    38.1 would plan against stale REQUIREMENTS/ROADMAP/STATE and stale 36/38.1 SPEC+CONTEXT". The orchestrator
    tagged a backup and carried the shared docs down to unit 35 as its first commit.
  - Ledger lines 9, 11, 21, 22: the carry made the cascade restack conflict in six rounds, then nine rounds;
    the first cascade was discarded by the health gate; the second passed after about 6 minutes.
  - Ledger line 177 (11-20 20:06): planning phase 36 found 36-SPEC and 36-CONTEXT on branch 36 stale (the
    owner-accepted amendments lived only on unit 39 and in ROADMAP/REQUIREMENTS); the planner amended them
    again inside plan 36-02.
  - Ledger lines 195-208 (21:49-23:00): two wave checkpoints of phase 36 refused `conflict` in 36-SPEC and
    36-CONTEXT, because unit 39 held a carry commit editing the same text. Resolver agents, an abort, a
    prepared resolution, and line 199: "no fold.py command restacks a lower unit without a fold rewrite".
- 2026-11-20 01:26 (line 5406): owner saw local/remote conflicts in the IDE; ledger line 14 traces it to a
  stray `git pull` in the shared checkout during planning.
- Cost: the ledger records carry and restack conflict work from 2026-11-19 22:12 to 2026-11-20 23:00, plus
  resolver subagents and owner attention.

### ai-kit, session 58b3c85b (loads at lines 2393 and 17409)

- 2026-11-14 03:27-09:56 (lines 24889, 24954, 25371): the owner asked whether 33's spec and discuss were
  really written; the autonomous run had specced, discussed and planned 33 on its own branch without the
  owner's spec-discuss. Owner (translated): "I asked for spec-discuss 32 to 34 ... but you wrote nothing to
  disk for 33 and 34".
- 10:45-10:47 (lines 25981-26109): an inserted phase 32.5 was started on the stack top, above 33 (the flow
  always starts on top). The orchestrator wrote `tmp/cbm/reorder_stack.py`, rewrote the stack record by hand
  to put 32.5 below 33, and switched branches; a stale `index.lock` error followed.
- 11:17-11:24 (lines 27140-27616): `fold.py restack`, then several switches between 34, 33 and 32.5; the
  34 branch was rebuilt with only its own three files. The goal file was first rendered on the top (34), then
  committed on 32.5 "so it exists in all branches" (line 27592) and restacked once more.
- Owner, mid-turn (line 26151, translated): "wait, when did we go from no specs to plans?"

### tools-installer, session 84904837 (load at line 98)

- 2026-11-19 10:15 (line 304): `start --phase 27` refused `no_trunk: gsd/phase-26-commit-and-push-quality-
  hooks does not resolve to a commit`, with HEAD on `main`. The message comes from `flow_unit.py:222`: the
  newest unmerged unit in the record had a deleted branch (the agent's ledger says "milestone archived"; not
  checked further). After one fetch the skill's row turned the unit flow off; phases 27-35 all refused the same
  way (lines 653-1317) and their documents were committed on the current branch.
- 2026-11-20 01:48 and 02:28 (lines 2425, 2930), owner (translated): "push the branch, but for now it is not
  worth merging to main if we are not delivering anything"; "the idea was not to merge into main if there were
  only specs and discuss; later, when we have the features, we can start merging after compacting the commits".

## Diagnosis

### 1. Cross-phase amendments land above the phase they amend
- Kind: skill ambiguity (`SKILL.md:236-237`, "in K's commit", written before the stacked flow).
- Evidence: 635881b5 ledger lines 7, 177, 195-208; 635881b5 line 2345 (decision numbers collided).
- How it was resolved: carry down with a backup tag and conflict loops, then re-amend at plan time; costly.

### 2. Shared planning files, STATE and the goal file end up on the stack top
- Kind: skill gap (`SKILL.md:188-192` names no branch).
- Evidence: 635881b5 ledger line 7; 58b3c85b line 27592 (goal file moved to the lowest unit by hand).
- How it was resolved: hand carry to the lowest unit, then restack.

### 3. No "where am I" step, and no rule for going back to phase J's branch
- Kind: skill gap; partly flow behaviour (no all-units read-only view: `show` takes one selector, so
  orchestrators read `.git/ai-kit-stack.json` by hand: 3adfa2df line 5354, 58b3c85b line 26082, 635881b5
  line 1838).
- Evidence: 635881b5 lines 1891-1905 (`ref_mismatch` from the top); 58b3c85b lines 27192-27597 (many switches).
- Note: the existing command already covers going back: `fold.py start --phase J` on a recorded open unit
  reuses and checks out its branch (`unit-contract.md:57-59`), and `guard` checks its parent. The skill and
  the end report just never say so.

### 4. GSD's own phase branching fights the fold flow
- Kind: flow behaviour plus skill gap (neither skill reads `git.branching_strategy`: grep 2026-11-23).
- Evidence: 3adfa2df lines 2330, 3912, 5156-5421.
- How it was resolved: not resolved; the orchestrator moved branches and edited the record by hand.

### 5. `start` leaves local-only work behind without saying so
- Kind: flow behaviour (`start_point` uses the remote trunk tip; unrelated local commits are kept off by
  design, `unit-contract.md:50-51`, but nothing reports them).
- Evidence: 3adfa2df line 5156 (phase 1's CONTEXT and config missing on the new branch).

### 6. A stale unit in the record reads as `no_trunk`, and the skill turns the flow off
- Kind: flow behaviour (misleading reason) and skill ambiguity (the `no_trunk` row covers a missing remote,
  not a deleted unit branch).
- Evidence: 84904837 lines 304-1317.

### 7. An inserted phase cannot go below open units
- Kind: flow behaviour; the hand rewrite of the record was an orchestrator mistake (NEVER list).
- Evidence: 58b3c85b lines 25981-26109; ROADMAP Phase 39.1 is numbered after 39 "because the unit flow puts a
  new unit on top of the stack".

### 8. Hand moves after a refusal
- Kind: orchestrator mistake, made likely by items 3-5 (no recipe in the skill).
- Evidence: 3adfa2df lines 5240-5421; 58b3c85b line 26092.

### 9. No eval or test covers any of the above
- Kind: eval gap (8 evals, none about branches after the chain; `tests/test_flow_docs.py` pins only the
  start rows: start before the spec commit, fetch once on `no_trunk`, proposed phase without a directory).

## Proposed strategy

One rule decides every write: **a file is committed on the branch of the lowest open unit that owns it, and
the units above are restacked right after.**
- A phase's own files (its SPEC, CONTEXT, DISCUSSION-LOG) belong to that phase's unit.
- A cross-phase amendment of phase J's files is written on J's branch, never on K's.
- Shared files (REQUIREMENTS.md, ROADMAP.md, STATE.md, todos, config, the goal file) belong to the lowest open
  unit of the stack.
- Upper units then hold only their own phase directory, so a restack cannot conflict on shared text (the
  conflicts in items 1 and 2 came from the same shared or amended file edited on two units).
- Batch the writes: one switch and one restack per phase step, not per amendment.

The steps the skill adds, all built from existing commands:
1. **Where-am-I preamble (read-only, at setup and before each phase).** Print the current branch, the stack
   order with each unit's state, and for each phase of the range whether its unit exists and which branch
   holds its SPEC and CONTEXT. Until the fold tool has an all-units view, run `fold.py show --phase <N>` per
   phase and `git branch --show-current`; never edit the record.
2. **Start-time checks (before the first `start`).** If `.planning/config.json` sets `git.branching_strategy`
   to anything but `none`, stop and tell the owner that two branchers would fight (item 4). If HEAD is a
   branch that is not a recorded unit and holds commits the trunk lacks, stop and show them (item 5): the owner
   pushes, merges or shelves them; the agent moves nothing.
3. **Going to phase J.** Before reading or writing J's files, run `fold.py start --phase J` (reuses and checks
   out an open unit) and `fold.py guard --phase J`; a refusal goes to the recipe table, never to a hand move.
4. **Cross-phase amendments.** Write them on J's branch with step 3, commit, then restack the units above
   with the fold tool. Ledger the amendment with both phases named.
5. **End-of-range state report (written, in the end report and the ledger).** The branch the checkout is left
   on (the lowest phase of the range, because the next step is planning that phase), the stack order with
   tips, which branch holds each phase's documents, the goal file's path and the branch that holds it (the
   lowest open unit, so every unit above has it), and every `unit flow off` line.
6. **Recipe table** (refusal or symptom, then what to do): `ref_mismatch` (switch with step 3 and repeat),
   `wrong_parent` (stop, show the owner), `plan_not_carried` (show the printed commands, never run them),
   `branch_missing` (stop; the record names a deleted branch), `no_trunk` with a named unit branch (stale
   unit: show the owner, do not turn the flow off silently), GSD branching on, unrecorded HEAD branch with
   local commits, inserted phase that must go below open units (ask the owner; number it after the top
   otherwise), a paused restack (the fold skill's cascade section).
7. **Plan or execute an earlier phase after the chain.** The goal-prompt rails and the GSD hook instructions
   say: step 3 first, then `boundary-plan` or `guard`, and the planner reads only that branch's files.

Fold tool behaviour this needs (smallest set, reusing existing commands):
- A restack of the units above after a plain commit on a lower unit, with no fold rewrite and no push
  (ledger line 199 says none exists; 58b3c85b line 27140 ran `fold.py restack` with no flag after a hand
  record edit, so check first whether that already does it).
- A read-only all-units view (for example `fold.py show --all`), printing id, branch, parent, state, and
  whether the branch exists.
- `start` names a stale parent unit as its own reason instead of `no_trunk` (item 6), refuses or reports an
  unrecorded HEAD branch with commits the trunk lacks (item 5), and refuses when GSD's
  `git.branching_strategy` is on (item 4).
- Optional, owner decides: an insert-below for a decimal phase (item 7).

Rejected on the owner's design rule:
- Keeping today's "amend in K's commit" and carrying down at plan time: the evidence shows repeated conflicts
  and stale plans.
- Writing all documents of the range on one branch: it breaks the one-unit-per-phase flow and the
  `discuss:pre` hook that starts a unit per phase.

## What goes where

- SKILL.md (rules the agent follows): the ownership rule, steps 1-5 and 7 in short form, replacing the
  "in K's commit" sentence (`SKILL.md:236-237`) and naming branches in the end-of-range paragraph
  (`SKILL.md:188-192`).
- A reference file (new, for example `references/branches.md`): the recipe table of step 6, the where-am-I
  output shape, and the end-of-range report template.
- ai-kit-commit-fold (`flow_unit.py`, `flow_git.py`, `flow_stack.py`, `fold.py`, `SKILL.md`,
  `unit-contract.md`): the four behaviour items above. Phase 45 later moves this engine into
  `ai-kit-project-rules` with its tests (ROADMAP Phase 45 criterion 7).
- goal-prompt: one rail line for step 7 (ties to Phase 47.2's `rail_sections` work and the goal-file todos).
- Evals and tests: below. The SKILL.md change needs the skill-judge loop (AGENTS.md).

## Candidate acceptance checks and eval scenarios

Evals (new-shape, in `skills/ai-kit-gsd-spec-discuss/evals/evals.json`):
- Amendment of an earlier phase: run 35..37, phase 37 finds a fact that contradicts 35's SPEC. Expected: the
  amendment is committed on 35's branch, the units above are restacked, 36 and 37 see it, no conflict.
- Resume to plan the first phase: after a chain of 35..39 the user asks to plan 35. Expected: `start --phase
  35` (reuse), `guard`, then `boundary-plan`; nothing is read from 39's branch.
- End report: expected to name the branch left on, the stack order, the branch of each phase's documents and
  the goal file's path and branch.
- GSD branching on: `.planning/config.json` with `git.branching_strategy: phase`. Expected: stop before the
  first `start`, with the reason.
- Unrecorded HEAD branch with local commits: expected stop with the list; no branch move, no record edit.
- Stale unit: the record's newest unit has a deleted branch. Expected: the stale unit is named and shown to
  the owner; the flow is not turned off silently.

Tests (names are suggestions):
- `test_spec_discuss_amendment_goes_on_the_owning_unit_branch` (doc contract on SKILL.md).
- `test_spec_discuss_end_report_names_branches_and_goal_file` (doc contract).
- `test_spec_discuss_refuses_when_gsd_branching_strategy_is_on` (doc contract).
- `test_start_reports_unrecorded_head_branch_with_local_commits` (fold, fixture repo).
- `test_start_names_a_stale_parent_unit` (fold, fixture repo; today it prints `no_trunk`).
- `test_restack_cascades_after_a_plain_commit_on_a_lower_unit` (fold, fixture repo; no push).
- `test_show_all_lists_every_unit_read_only` (fold).

## Which phase should take it and why

- No phase of milestone v2.0 edits `ai-kit-gsd-spec-discuss` (grep of ROADMAP.md, 2026-11-23). The last phase
  that did is 32.4 (done 2026-11-13); on 2026-11-03 the owner asked the same "which phase" question and was
  pointed to 32.4 (58b3c85b line 2506). Backlog 999.11 (spec-discuss polish) was absorbed on 2026-11-07.
- Phases that touch neighbours: 45 (moves the fold engine into `ai-kit-project-rules`), 47 (end-of-unit and
  session-start playbooks), 47.2 (goal-prompt rails).
- Recommended: insert one phase before the next spec-discuss run, after 39.1 and before 40's spec step
  (for example 39.2, numbered after the stack top as the flow requires), covering the SKILL.md rules, the
  reference, the fold behaviour and the evals together. Reason: phases 40 to 54 have no SPEC yet, so the next
  spec-discuss run meets this problem before Phase 45 or 47 lands, and a half (skill text without the fold
  restack) would leave the rule unusable.
- Fallback if the owner prefers no insert: Phase 47 (its end-of-unit and session-start playbooks are the
  nearest scope), with the fold items done before Phase 45 moves the engine.
- Owner decision 2026-11-23: inserted as Phase 39.2 after 39.1.

## Open questions for the owner

1. Amendment branch (recommended first): write a cross-phase amendment on the amended phase's own branch and
   restack upward (recommended: each unit plans against correct documents; costs a switch and a restack per
   phase step), or keep today's "amend in the later phase's commit" and carry down before planning (no switch
   during the chain; the evidence shows repeated conflicts and stale plans).
2. Shared files (REQUIREMENTS, ROADMAP, STATE, the goal file) on the lowest open unit: agreed? That unit's PR
   then carries them.
3. GSD branching on together with the unit flow: should spec-discuss stop and ask, or should the fold install
   set `git.branching_strategy` to `none` (a config write)?
4. Inserted decimal phases: always on top (renumber), or should the fold tool support insert-below?
5. Should the restack after a lower-unit commit run without push consent (local only, pushed at the next
   checkpoint)?
6. home-mobility: the record was reset by hand and `main` is 5 commits ahead of origin; who repairs it?

## Scheduling note

- Nothing before the editing phase depends on this capture.
- Phase 39 (now executing: lane capability blocks and lens skills) and Phase 40 (resilient review) do not
  touch spec-discuss or the fold flow and do not depend on it.
- The next spec-discuss run (for phases 40 onward, none of which has a SPEC) will meet the problem, so the
  rules should land before that run; until then, an orchestrator brief can carry steps 3 and 5 as rails.
- Related pending todos: `2026-11-20-run-ledger-and-resume-state-in-gitignored-tmp.md` (same SKILL.md, ledger
  location) and the goal-file todos (goal file placement).
- Not read (limits): subagent sidechains, ai-kit session 4f4fa173 (one load at line 44522), tools-installer
  sessions 954c3fb8 (four loads), bd756f6b and 892a2729; the spec-discuss references were grepped, not read.
