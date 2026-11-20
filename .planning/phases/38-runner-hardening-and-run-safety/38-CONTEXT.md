# Phase 38: Runner hardening and run safety - Context

**Gathered:** 2026-11-16 (interactive path, no owner question needed, jev screening, after 38-SPEC.md); updated 2026-11-16 (re-run 2, herdr hosting, interactive path, jev screening, after the 38-SPEC.md R12 addition)
**Status:** Ready for planning (after Phase 37 lands: this phase edits the runner file that phase rewrites, moves the self-test
cases it adds, and extends the status line group it adds)

<domain>
## Phase Boundary

The runner gains the safety half of unattended execution: an opt-in idle watchdog whose execute-lane clock also watches the
checkout, a per-checkout run lock with a recorded baseline, and a deterministic check that turns an execute result whose
commits, files or report disagree with its plan into `partial` or `contract_violation`. The Phase 25 review cleanup lands with
its stale items corrected, and the self-test harness leaves the runner file so rendered copies stay small.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**11 requirements are locked.** See `38-SPEC.md` for full requirements, boundaries, and acceptance criteria.
*(Refined 2026-11-16, re-run 2: 12 requirements are locked; R12 is the run safety of a lane Phase 37 hosts in a herdr tab, RUN-13.)*

Downstream agents MUST read `38-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope:** the idle watchdog (R1); execute progress signals (R2); the run lock (R3); the baseline (R4); the plan-versus-commits
and execute result checks (R5); one router rule (R6); the quota-cycle class (R7); the self-test sibling file (R8); curated-config
asking gsd-core for skipped skills (R9); the corrected Phase 25 cleanup (R10); skill text, docs, closed lists and the judge bar
(R11).

**Out of scope:** error classes and the retry policy (38.1); capability blocks and prompt-size refusal (39); lane switching,
resilient review and routing custom lanes through the runner (40); the adapter's use of locks, baselines, plan ids or a task list
(41); jev classifying execute results, effort by task and the real-home mtime audit (42).
</spec_lock>

<decisions>
## Implementation Decisions

### The watchdog (SPEC R1, R2)

- **D-01: The watchdog lives in `runOnce`/`runChild`, planned by one pure function.** `runOnce` already owns the byte counters,
  the heartbeat and the `runChild` call; `runChild` already has one finalize path with a reason (`timeout`, `limit`, `exit`).
  `runChild` gains an optional idle hook that finalizes with reason `idle` (same SIGTERM, grace, SIGKILL, drain), sets
  `timedOut` and `idle`, and `runCli` writes `rule=idle-watchdog` into the attempt line when `r.idle` is set. A pure
  `planIdle(call, config, role)` returns `{idleS, checkS, pollTree, notices}` so the flag, the baked value, the default and the
  notices are table-tested without a spawn (`pure-idle-*` cases, logic kind). A `--print-argv` line prints the plan. Live check
  by reading (not yet run): an idle kill happens well before the deadline, so `attemptCapMs`'s 60 s reserve leaves room and
  `ladderNext` admits the same-session rung; one self-test case (`idle-then-resume`) proves it, because the WR-03 note says a
  timeout reaches a rung only when budget remains. **Own reasoning** (jev none: structure, not a gray choice).
- **D-02: Tree polling reuses `treeState`; its cost is small.** Live 2026-11-16: the same commands (private index, `add -A`,
  `write-tree`, the ignored-file stat listing, `ls-files -s`) took 0.21 s on this 3,137-file repository, so a read per check
  interval (`idle/10` seconds, 1 to 60) is cheap, and the existing 10 s per-git-command cap bounds a slow one. A cheaper
  head-only first step was considered and dropped because uncommitted edits are the signal an executor gives before its first
  commit. The first read after the spawn is the previous-read value; reads happen only when no output arrived since the last
  check, one at a time. The heartbeat line reuses the last read (`commits +N, tree changed|unchanged`; the commit count is
  `rev-list --count <baseline head>..HEAD` taken in the same read, one extra git call per read, not per heartbeat).
  `no_tree_change` repeats once per idle period, never kills. **Own reasoning** (live measurement).
- **D-03: The idle default is 900 s, labeled judged.** Evidence: healthy review lanes took 288 to 579 s in total, observed stalls
  printed nothing for 1800 s, GSD asks the owner after 10 minutes without commits, and an execute lane's quiet stretches are
  covered by the tree signal. Not a derived value (a share of the deadline would make the default depend on a setting the owner
  changes for other reasons). A value under 60 only prints a notice: the owner decides, a floor would be a rule the runner
  made up. jev laya s1800 low 0.40, typesafe derived low 0.40. **Own reasoning.** Ledger.
- **D-04: An idle kill is a timed-out attempt (the existing ladder).** jev ladder choice 0.95. It keeps the vocabulary closed
  (`timeout`/124 when no rung fits, otherwise the ladder's `transient`/75 and hard tier) and adds no status. The Python
  `idle_stall` entry stays for old runners. The cost: a persistently silent lane walks the whole ladder (up to the deadline and
  cap); the SKILL says an owner who wants an earlier stop sets a lower `max_retries` in the retry settings.
- **D-05: Execute lanes reset on tree or commit change; review lanes on output only.** The owner's 2026-11-16 amendment; jev
  typesafe out_tree low 0.72 agrees, laya out low 0.48. CPU time is rejected (a slow network answer and a hang look the same).
  A silent host has no review signal: stated as a limit. `pi --mode json` is a possible future activity stream (listed by
  `pi --help`; whether it streams while working is unverified) and is not adopted here. **Own reasoning.** Ledger.

### Lock and baseline (SPEC R3, R4)

- **D-06: One state record per checkout, under the state home the quota records use.** `<state>/ai-kit/spec/locks/<sha16
  root>.json`, written with `wx` (the atomic step), mode 0600 in a 0700 directory, reusing `writeCycleState`'s temp-and-rename
  for later updates (the child group, once spawned). jev state choice 0.98 (laya tree low 0.46): a file in the working tree
  would enter the tree snapshot, and the git directory does not exist outside git. The root is the git top level, else the
  working directory's real path. Linked worktrees get separate locks (separate checkouts). Pid start time comes from
  `/proc/<pid>/stat` (proc(5): field 22) on Linux and `ps -o lstart= -p` elsewhere; macOS is unverified here. Where neither
  reads, pid liveness alone decides (a stated limit: pid reuse is not detected there).
- **D-07: `locked` is a new status with a bare exit 75.** jev second opinion e75 choice 0.91; the first answer (usage, exit 2,
  laya 0.78) is overridden because every caller maps exit 2 to a configuration problem and a held lock is not one. A bare 75
  carries no `retry_after_s`, so the SKILL's rule (only a hinted 75 is the caller's wait) makes it a report or serialize.
  Python `STATUS_TO_REASON` maps `locked` and `partial` to `real_error`.
- **D-08: Release in `finish()` plus an `exit` backstop.** `finish` is the one place every status passes (usage, signal and
  failure included), so a synchronous remove there covers every exit the runner controls; the `exit` handler covers an
  uncaught throw. A SIGKILL leaves the record, and the stale rule (dead pid, dead recorded group, same host) handles it. The
  record also carries the child group so a dead runner with a live executor is never cleared (the `--child-pgid-file`
  concern). Unreadable records are never cleared automatically.
- **D-09: Review lanes neither take nor check the lock, except one notice.** Parallel review lanes are by design, and the
  existing tree guard already voids a review whose tree changed (RUN-215). The notice costs one file read. **Own reasoning**
  (the owner asked to think about review and execute separately).
- **D-10: The baseline record is keyed by task digest and reused until `ok`.** jev record choice 0.95 (laya low 0.40 agrees).
  It reuses `taskDigest` and the cycle-state directory conventions. Why it must persist: a fix round is a new runner call and a
  fresh baseline would make tasks finished earlier look uncovered. The ancestor check (`merge-base --is-ancestor`) catches a
  rebase or reset. `--baseline <sha>` is for callers that track their own (Phase 41's adapter may). The baseline's write-tree
  already contains the owner's uncommitted files, so changed paths come from `diff-tree <baseline tree> <end tree>` (the
  existing `changedPaths`) and an untouched owner edit never appears; an owner edit made during the run still does (stated).

### The execute result checks (SPEC R5)

- **D-11: The check is runner code, not Python.** GSD's hook path has no Python layer and runs one fixed command string, so the
  prompt is the only plan the runner sees. New pure functions in the template (`parseTasks`, `coverageOf`, `admissionHits`,
  `forbiddenHits`, `planFindings`) are covered by `pure-*` cases plus spawn-level fake lanes; one git call
  (`git log -z --name-only` over `<baseline head>..HEAD`) supplies commits. jev files choice 0.99 (laya count low 0.47).
  The GSD-side equivalent (`check evaluation-scope`, subject-based) is not called: the runner is standalone and the call would
  need a plan id the fixed command cannot carry; `--plan-id` ports its subject rule (zero-padding tolerant) for callers that
  know the id.
- **D-12: Task parsing is a plain scan of the caller's part of the prompt.** `<task ...>` blocks (the part before the runner's
  own preamble, as `runCli` already splits it), `type` absent, `auto` or `tdd`; `<name>` and `<files>` read as `promptFiles`
  reads `<files>`; an unclosed block is skipped and counted unchecked. No `<task>` block (a free-form or superpowers-style
  prompt) gives `coverage=n/a`: the runner claims nothing about a plan it cannot see. A task list input for the superpowers
  adapter is a Phase 41 decision.
- **D-13: The admission seed list is short, lowercase substrings, labeled judged.** Initial seed (the plan may tune it against
  the 26-03 report text): `not implemented`, `not completed`, `did not implement`, `did not complete`, `didn't implement`,
  `didn't complete`, `left unimplemented`, `left for later`, `deferred to a later`, `deferred to a follow-up`, `could not
  finish`, `could not complete`, `could not implement`, `unable to complete`, `unable to implement`, `remaining work`,
  `skipped the task`, `skipped task`. Text inside fenced and inline code is removed first. A Deviations or Auto-fixed heading
  is never a match (26-05 and 26-06 were harmless). Recall is unverified; the printed phrase lets the owner judge. The list
  lives in `CONFIG.admissionPhrases` so it is owner-replaceable. **jev overridden** (first answer `with`, typesafe 0.87, laya
  note low 0.43): the requirement lists the admission as its own trigger; second opinion `alone` choice 0.99. A false partial costs GSD's retry, skip or abort prompt; a
  missed admission cost a stopped chain in 26-03. **Own reasoning on the list content.** Ledger.
- **D-14: The forbidden default is the three orchestrator-owned planning files, unless the plan names them.** Source:
  `elaboration.md` step 4 (the orchestrator writes STATE and ROADMAP after a successful external lane) plus REQUIREMENTS in
  the 999.15 list. A plan that lists a file in `<files>` exempts it (an ai-kit plan that amends the roadmap says so). The
  runner copy itself is not default-forbidden because an ai-kit plan re-renders it (37 D-18). jev orch choice 0.94 (laya none
  low 0.52). Callers add paths with `--forbid`; baked additions go in `CONFIG.forbiddenPaths`.
- **D-15: Results and output.** `partial` (exit 1) for `no_commit`, `task_uncovered`, `admits_skipped`; `contract_violation`
  for `forbidden_path` and it wins; `no_change` wins over both. Informational findings never change a status. Findings print
  before the status line; the status line gets `coverage=` and `findings=` after Phase 37's group. stdout stays empty for
  `partial` so GSD cannot write it as a SUMMARY (exit 1 already stops it). An execute run that fails for another reason still
  prints findings: they are the resume's missing list. `uncommitted_edits` is informational on purpose: executors may leave
  scratch files and a false `partial` would stop good runs; the finding still shows. **Own reasoning.** Ledger.
- **D-16: jev and herdr per concern *(amended 2026-11-16, re-run 2, D-25 to D-27: the runner may host a lane in a herdr tab through Phase 37's transport and calls `herdr tab list` in its sweep; what still holds, verbatim below: herdr's screen text, agent status and wait output, and the existence of a tab, are never a verdict or a liveness signal, and the lane stays supervised by its own files and process group)*.** Stalled versus slow: neither (silence has no text to classify, herdr's agent status does
  not describe a headless child), the deterministic idle and tree rule decides. Commits versus tasks: deterministic; jev may
  screen an admission-only `partial` in a calling skill (Phase 42 owns classifying execute results) and low confidence falls
  back to `partial`, never to done; no-jev behavior is the tested default. A long lane in a visible pane: herdr may be used by
  a calling skill when `HERDR_ENV=1` and the CLI exist (`herdr pane run`/`pane read`), ~~never inside the runner~~ *(superseded
  2026-11-16, D-25: the runner itself may host through Phase 37's transport)* and never as a
  signal; the lane stays supervised by its caller *(refined 2026-11-16, D-26 and D-28: a hosted lane is supervised by the runner through its pid, group and files)*. jev visible choice 0.86 (herdr item; laya liveness low 0.57). Absent
  behavior of both is the documented path in the SKILL.

### The cleanup (SPEC R6 to R10)

- **D-17: One router function in `model_heuristics.py`, `is_confirmed_router(entry)`.** Reads `fallback_quota` with its label:
  `user-stated` or alias-`assumed` confirms, `judged` hints stay advisory, an owner `false` wins, disagreeing fields do not
  confirm. Its callers are `resolve_route`, curated-config's `router_confirmed` and the `routerBacked` render; the
  name-declared-purpose check stays where it is. This depends on how Phase 35 stores the label (it executes first; the plan
  adapts). **Own reasoning** (jev low both: laya always 0.66, typesafe confirmed 0.62): Phase 35 D-15 says router aliases are
  assumed and the owner is not asked, so a rule that requires confirmation would turn the long quota waits off for every
  `router-env/<x>` lane. **Needs owner confirmation**: this changes when a lane gets the router quota cycles (the Phase 25 rule
  said a naming hint never does; a label `assumed` by the owner's own alias convention is not a naming hint). Ledger.
- **D-18: `classify_dispatch_failure` gains `quota_cycle`.** The one-shot re-invoke case only; `quota` keeps the owner stops;
  the subcommand prints `{class, retry_after_s, cycle}`; the reference's three `python3 -c` parses go. Phase 41 rewrites the
  adapter around it. Own reasoning (ponytail item 4 of the Phase 25 review, still open in the code).
- **D-19: The harness moves to a sibling file by a scripted line-range splice.** jev sibling choice 0.82 (laya low 0.60 agrees).
  A one-off script under `tmp/` cuts the ranges at the plan's recorded markers and the runner gains an explicit export list;
  `blackBoxSelfTest`, `STATUS_HEAD_RE`, the fakes, the case table and the classifier fixtures move. The plan measures how
  many runner symbols the harness imports (unknown today: about 430 cases call runner internals in scope). The runner reaches
  the sibling through `await import(new URL('./cross-ai-selftest.mjs', import.meta.url))`, only for the two self-test flags.
  Because the render is a config splice of the whole file, Phase 37's sync test needs no relaxation (this amends the 37 SPEC R8
  and 37 D-18 sentences that say it will relax). The template version is bumped, shard times are re-recorded, the live copy is
  re-rendered, and `make check-dogfood` closes the step.
- **D-20: curated-config's skipped-skill check calls gsd-core.** Mechanism for the researcher: a node call of the project-local
  gsd-core's exported `buildAgentSkillsBlock` with the candidate config (it takes `config`, `agentType`, `projectRoot` and a
  diagnostics array) versus the `query agent-skills <agent> --json` verb (it reads the live config, so a candidate plan would
  need a scratch project). Own reasoning prefers the first (no scratch). No gsd-core: skip with a note. The ponytail estimate
  was about -100 lines; the plan measures it.
- **D-21: Dead code and the timeout item, corrected.** Remove the three verified dead items; keep `clampCapS` (T-25-13) and
  `clampAttemptTimeout`. The timeout restore is amended (laya amend choice 0.87): the code that restored it left with
  `ai-kit-spec-execute-gsd` in Phase 31 (d1f0f9f), so the criterion becomes a visible, tested before and after in the plan
  entry. ROADMAP Phase 38 criterion 2 and RUN-04 are amended in this commit. **Needs owner awareness** (a scope correction to
  an owner-listed item).
- **D-22: Backlog 999.21 folds in as a proof case.** Live 2026-11-16: temp folders are already dropped on every exit
  (c535683, 2026-11-14: `dropTemp`, the `exit` flush), and the only case about them covers a SIGKILL leftover. This phase adds
  one self-test case that a run leaves no `cross-ai-*` or `xai-idx-*` entry after ok, failure, timeout and signal, and marks
  the backlog item absorbed. SPEC R10 gets an additive amendment.
- **D-23: A spike comes first, at execute start.** Theory (the 999.15 evidence, the hosts' help) says pi prints nothing while
  working; the spike records, in `tmp/`, one cheap call on each primary host (claude, opencode, pi) in a scratch repository:
  when stdout and stderr first appear, and whether `pi -p --mode json` streams events. Findings go into the SKILL's limit text.
  It also records the pid start-time reads (`/proc` on this Linux; macOS stays unverified). herdr may drive a host for it where
  `HERDR_ENV=1` and the CLI exist; the fake-lane tests depend on none of it. **Own reasoning.** Ledger.
  - **Refined 2026-11-16 (re-run 2, D-25 to D-31):** the spike also records one hosted call per primary host through Phase 37's
    transport (when the lane's files first grow, whether `rc` appears after a slow answer) and one run killed by SIGKILL followed by
    `--sweep`, against a real herdr, in a tab labeled for the spike and closed by it; the fake-herdr tests depend on none of it.
- **D-24: Skills and docs.** `ai-kit-cross-ai/SKILL.md` is the one SKILL.md that changes (new sections for the watchdog, the lock,
  the checks, the two statuses and keys, the limits, the conditional helpers; evals in the new shape; a trailing provenance
  section) and meets the judge bar if Phase 37 did not bring it there. `ai-kit-spec-execute-superpowers` changes only through
  its reference (the parses go) and joins the judge loop if its SKILL.md changes. `cross-ai-dispatch.md`, curated-config
  `runner.md`, the curated-config SKILL.md timeout wording and the READMEs follow. Closed lists (finding codes) are locked by
  one test against the runner, `--describe` and the SKILL.md table; the guard baseline for the runner's self-test entries shrinks
  to nothing when the harness moves.
  - **Refined 2026-11-16 (re-run 2, D-25 to D-33):** the same SKILL.md gains a section for a hosted lane (the run record, the lock
    with a hosted lane, `--sweep` and the automatic sweep with their proof rule, the idle clock on files, the output bound, the
    secret-file lifetime with its unguaranteed cases, the `setsid` limit), `--describe` lists `--sweep`, and the doc-contract test
    pins them; the new self-test cases (fake `herdr`, killed-runner sweep) live in the sibling harness like the others.

### Added 2026-11-16 (re-run 2, herdr hosting, after the R12 addition)

Live checks first (herdr 0.9.5, SPEC "Live facts added 2026-11-16"): the launcher is its own group's leader; `tab close` ended its
plain and `nohup` children but not a `setsid` grandchild; `tab get`/`tab list` carry the label; a closed or unknown id and an
unreachable server give distinct JSON error codes; file polling costs 0.08 % of a core at 250 ms; `/proc` start ticks read in 4 us;
a launcher can delete its env and prompt files as its first steps; an append-mode file can be truncated under a writer.

- **D-25: A run record, `run.json`, makes a killed run provable.** Phase 37 D-26 says the tab id is written to the run directory
  but names no file or fields. The record holds the version, token, runner pid and start time, host name, checkout root, role,
  runtime, the label, tab and pane ids (null until `tab create` answers), the launcher pid and start time (null until the `pid`
  file appears) and the creation time; it is written first (before the env file and the tab), rewritten by temp file and rename
  when the ids and the launcher pid are known, mode 0600 in the 0700 directory, and never holds a secret. Without it a sweep
  would have to trust a label prefix, which any foreign tab can carry. Phase 37's protocol fixture test (file names and label
  grammar) gains `run.json`; Phase 42 writes the same record for what it opens. **Own reasoning** (no jev: a structural
  consequence of 37 D-26, not a gray choice). Ledger.
- **D-26: The lock keeps its key, its pid and its start-time read; a hosted lane's "child group" is the launcher's group.** Live:
  the launcher is the leader of its group (group id equals its pid, parent is the pane shell) and the runner stays alive while it
  supervises, so the lock record is written by the runner as before and gains the run token, tab id and launcher group once the
  `pid` file appears (the same temp-and-rename update as the headless child group). A hosted lane runs while that group is alive with
  the recorded start time; a surviving tab, its screen and its agent status are never an input (D-16). A dead runner with a dead
  launcher group on this host is stale and cleared (R3's rule) and the same step sweeps that token's directory; a dead runner whose
  launcher group lives is refused as `locked` naming the group and the tab id (the lane is still working, as with a headless child).
  The lock is taken before the first spawn, so a refused run opens no directory and no tab. jev typesafe runner_plus_launcher_group
  low 0.50 (laya runner_only low 0.48, forced); typesafe clear_lock_and_sweep_tab low 0.47. **Own reasoning.** Ledger.
- **D-27: The sweep proves, then removes; it never guesses.** Triggers: the start of every real run (after validation, before the
  lock; the cost is one directory listing and, only for a dead run, a few file operations and one `tab list`) and `--sweep` for a
  caller or an owner who closes a plan (no spawn, no lock, exit 0). Scope: only `<state home>/ai-kit/spec/host/<token>/` of this state
  home. A run is dead by D-26's identity rules plus its record; for each dead run the sweep claims the directory by a rename to a unique
  name (one winner, as with the stale lock), removes secrets first, then closes the tab. The proof for a tab is a listed tab whose id
  and complete label both equal the record (a null id matches only the tab whose complete label equals the record's, which holds the
  unique token); `tab_not_found`, or no listed match, means already gone. `tab list` is the sweep's one new herdr verb (read-only; it
  reads id and label only) and is why 37's verb set grows by it; `tab get` is not needed because one list serves every record.
  Herdr unreachable (no CLI, `HERDR_ENV` not `1`, `server_not_running`) or the automatic sweep under a hosting switch-off: secrets go
  at once, the small secret-free record stays and is counted (`kept ... (herdr unreachable)`), a later sweep closes the tab; the
  explicit `--sweep` ignores the switch because it is the owner's request. An unreadable record is reported with its age and left
  alone (R3's rule for locks); a dead runner's live launcher group is left alone and reported. A lane's result is never recovered
  (nobody is waiting for it; the baseline record lets the fix round count its commits). Unlimited keeping of a record whose herdr never
  comes back costs a few hundred bytes; an age cap is left to the plan only if it finds the count grows in practice. jev: laya
  none_of_these 0.77 for the proof item contradicted the evidence, second opinion typesafe dead_run_record_id_and_label 0.94
  (**jev overridden** for the first answer); trigger, herdr-unreachable and switch-off items all low (laya 0.27, typesafe 0.52 and 0.41;
  laya 0.39, typesafe 0.48), decided by **own reasoning**. Ledger. The `never_close` answer of the switch-off item would leave tabs
  open for ever, against the owner's "close what it opened".
- **D-28: The idle clock reads the hosted lane's files.** Activity is growth in size of `out` or `err`, polled at 250 ms (a separate
  cadence from R1's check interval; 0.08 % of one core measured, 100 ms measured 0.18 %). The launcher's header and herdr's screen are
  outside those files, so neither counts; the runner's heartbeat lines still do not count; R2's tree and commit reset reads the
  checkout and is unchanged. The idle kill signals the launcher's group (SIGTERM, grace, SIGKILL) only after pid and start time still
  match the record (pid reuse), closes the tab by id, and takes a last read; the status, attempt line and ladder are R1's. jev typesafe
  file_size_growth 0.90 (laya none_of_these low 0.52). A hosted lane's silence is not the launcher's death: pid and start time say
  alive, `rc` says finished, and only the idle watchdog (opt-in) turns silence into an end. This answers 37's open question on what
  the `pid` file holds: the launcher's pid, with its start time read by the runner from `/proc` on first sight.
- **D-29: The execute checks and the tree snapshot for a hosted lane.** Same functions, same inputs: the answer is the captured
  `out`, the verdict is `rc`, the commits, forbidden-path, admission and baseline reads are against the checkout. New hazard found by
  reading the snapshot design: a state home inside the checkout (an `XDG_STATE_HOME` the owner points at the repository, or a
  test scratch folder) puts growing `out` files, lock records and baselines into the tree state and the ignored-file signature, which
  would reset an execute lane's idle clock and print `outside_plan_files`. The snapshot therefore excludes the state home when it
  lies inside the checkout (a pathspec exclude with literal matching for the add, and a filter on the signature; the plan verifies the
  exact git form). This protects lock and baseline records too, which D-06 already put under the state home. jev refuse-hosting low
  0.31 (laya), exclude-from-snapshot low 0.77 (typesafe, taken as evidence). **Own reasoning.** Ledger.
- **D-30: The output bound truncates; it does not end the lane.** A headless lane's capture keeps the newest `CAPTURE_MAX_BYTES` in
  memory; a hosted lane's files would grow without limit on the disk the checkout and the state home share, and the idle watchdog
  never fires on a lane that keeps printing. Ending the lane at a ceiling (both jev answers, low 0.66 and 0.65) would make hosting
  change an exit code, against 37's prohibition; instead the launcher opens `out` and `err` in append mode and the runner, past twice the
  cap in one file, truncates it to zero and carries on from offset zero, printing the headless "kept the newest" line. Live: an
  append-mode writer under a reader that truncated after each read wrote 3 MiB, the reader saw 3 MiB, and the file was not sparse. Cost:
  bytes appended between the last read and the truncation are lost, which the headless buffer's drop of the oldest bytes already
  accepts. **Own reasoning, jev not followed.** Ledger. **Needs owner awareness** (a hosted lane's files hold at most about two caps).
- **D-31: Secret files live for as short a time as the launcher takes to start.** This amends 37 D-25's exposure ("a key touches disk for
  the length of a hosted lane"): the launcher sources the env file, opens the prompt on file descriptor 3 and deletes both as its
  first steps (checked in a scratch run: the lane kept its environment and its stdin). The runner removes any remainder on every exit
  path it controls (finish, deadline, signal, spawn error, the `exit` handler), and the sweep removes it after a hard kill, with or
  without herdr. Not guaranteed, and the SKILL says so: a SIGKILL or power loss before the launcher ran leaves the 0600 file in the
  0700 directory until the next runner call of any kind; an unlinked file's blocks are not overwritten; the lane's own process
  environment holds the same values as a headless lane's. jev typesafe launcher_deletes_at_start low 0.78 (laya low 0.49 for the
  opposite). **Own reasoning.** Ledger. **Needs owner awareness** (the exposure shrinks from the lane's duration to about a second).
- **D-32: Limits stated, not solved.** A grandchild that detaches with `setsid` survives `tab close` and a headless group kill alike
  (live); the sweep never looks for it. A tab the owner closes by hand ends the launcher and the lane without an `rc`, which the
  existing killed-by-a-signal branch reads. A lane whose runner died keeps running to its own end and its result is not recovered.
  Linux is the verified platform for the pid start-time read; elsewhere `ps -o lstart=` has a one-second resolution, so pid reuse
  inside one second is the residual risk there.
- **D-33: Naming and sharing stay as Phase 37 chose; Phase 38 pins them for the sweep.** One tab per hosted spawn, never reused, label
  `aikit:<role>:<runtime>:<12-character token>`; the token is unique per spawn, so two runs, two attempts or two parallel review lanes
  never share a tab, and no lock is involved for panes (the checkout lock of D-06 is for execute runs only). The sweep matches the
  complete label, so the grammar is part of the protocol fixture. Pane reuse across calls is Phase 42's and would need its own record.

### Handoffs to later phases

- **Phase 37** (executes first): the new self-test cases and the pinned status-line expression move with the harness; the
  status line group this phase adds follows Phase 37's; `--describe` lists the new statuses and the finding codes; the sync
  test is not relaxed.
- **Phase 38.1**: its error classes use their own list; `partial` and `locked` are runner outcomes, not host errors, and are not
  in the catalogue; the status line grows after `coverage= findings=`.
- **Phase 40**: a `locked` status is not a lane failure to switch on; lane switching reads `escalate=` as before.
- **Phase 41**: the adapter decides whether it takes a lock per task, passes `--baseline`, `--plan-id` or a task list, resumes a
  `partial` with the printed findings and session, and consumes `quota_cycle`.
- **Phase 42**: jev classification of execute results (including an admission-only `partial`) and the real-home mtime audit
  (EXE-08); the findings and the printed phrase are its inputs.
- *Added 2026-11-16 (re-run 2):* **Phase 37**: `run.json` joins the protocol fixture (D-25), the herdr verb set grows by the
  sweep's read-only `tab list` and the arch rule says so, the env file is deleted by the launcher (D-31, amends 37 D-25), the poll
  interval is 250 ms from the measurement in D-28, the launcher appends to `out` and `err` (D-30) and the `pid` file holds the
  launcher's pid (D-28); all recorded as dated notes in 37 CONTEXT. **Phase 38.1**: nothing changes; a hosted lane's classes are the
  headless ones, and the free-limit capture stays its fixture source. **Phase 40**: a `locked` status and a sweep report are not lane
  failures to switch on. **Phase 41**: executors run hosted through the builder, so each plan's call sweeps at its start and the
  adapter may call `--sweep` when it closes a plan; a hosted lane's lock record names the launcher group. **Phase 42**: its panes
  (interactive agent, TUI app, e2e) write the same `run.json` and label so this sweep closes what a killed run left of them; its own
  leftover sweep (ROADMAP criterion 3) calls `--sweep` instead of a second implementation; pane reuse needs its own record rule.

### Open questions for the phase researcher

- How many runner symbols the harness imports, and whether any needs a runner refactor rather than an export (D-19).
- Which of the two gsd-core call routes works from Python without a scratch project (D-20).
- The 26-03 report text against the admission seed: recall and false-positive rate (D-13).
- Whether pi's text mode prints nothing for the whole run and whether `--mode json` streams (D-23).
- The exact set of Python and doc places that mirror the status vocabulary (`STATUS_TO_REASON`, `cross-ai-dispatch.md`, SKILL
  tables, the runtimes-table test) for `partial` and `locked`.
- *Added 2026-11-16 (re-run 2):* the exact git form that excludes the state home from the snapshot's add and from the ignored-file
  signature (D-29); whether the sweep's `tab list` needs a per-call timeout shorter than the 10 s git cap so a hung herdr cannot delay
  every run's start (a plan default and a test with a hanging fake); whether `kill(-group, 0)` and the leader's start time are enough
  when the leader is dead but a member lives (D-26); whether a record whose herdr never answers needs an age cap (D-27); what a pane
  whose shell is not at a prompt does with the typed launcher line, and how the runner tells that from a slow start (the launcher
  never started, so `pid` never appears: a start-wait limit and the same host_failed rule of 37 D-26 decide); fish and nushell panes.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md` (requirements, live facts, findings)
- `.planning/phases/37-shared-runner-options-and-session-ids/37-CONTEXT.md` (D-11, D-12, D-13, D-18 and its Phase 38 handoff),
  `37-SPEC.md` (R2, R8)
- `.planning/phases/999.15-cross-ai-chain-skill-for-execute-and-review-runs/999.15-LESSONS.md` (incidents 1.1 to 1.14, gates A,
  classification C.2)
- `.planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-REVIEW.md` (WR-05, IN-01, IN-03, ponytail
  items 4 to 10), `18-CONTEXT.md` D-43
- `skills/ai-kit-spec-review/references/cross-ai.mjs` (`runChild`, `runOnce`, `runCli`, `treeState`, `changedPaths`, `rung2Gate`,
  `promptFiles`, `finish`, `STATUS_TABLE`, `cycleFilePath`, `taskDigest`, `blackBoxSelfTest`), `ai_kit_spec/` (`error_classifier.py`,
  `runner_dispatch.py`, `model_heuristics.py`), `ai_kit_spec_superpowers/dispatch_injection.py`,
  `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md`, curated-config `plan_io.py`, `skills.py`,
  `catalog_adapter.py`, `cross_ai.py`, `cross_ai_script.py`, `tests/cross_ai_selftest.py`
- GSD: `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md` (step 2.5), `execute-phase.md` (stall surveillance),
  `steps/executor-progress-policy.md`, `bin/lib/gate-evaluation-scope.cjs`, `bin/lib/init.cjs` (`buildAgentSkillsBlock`)
- *(added 2026-11-16, re-run 2)* `.planning/phases/37-shared-runner-options-and-session-ids/37-CONTEXT.md` (D-22 to D-29) and
  `37-SPEC.md` (R12, "Live facts added 2026-11-16"); herdr 0.9.5 `tab list`, `tab get`, `tab close`, `tab create` help; the probe
  scripts and outputs under `tmp/spec-discuss-35-39/` (`probe38*.py|sh|mjs`, not committed)
- `skills/ai-kit-cross-ai/SKILL.md` and `references/`, `skills/ai-kit-spec-review/references/cross-ai-dispatch.md`,
  `skills/ai-kit-gsd-curated-config/references/runner.md`
</canonical_refs>
