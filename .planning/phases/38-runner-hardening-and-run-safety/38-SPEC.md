# Phase 38: Runner hardening and run safety — Specification

**Created:** 2026-11-16
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 11 locked; 12 locked after the 2026-11-16 re-run 2 (R12, run safety of a hosted lane)

## Goal

The runner (`cross-ai.mjs`) stops burning a window on a hung lane, refuses to start an execute run on a checkout another
run holds, and never reports an execute result as done when its commits do not match its plan. An opt-in idle watchdog ends
a silent lane's process group (for an execute lane, silence means no output and no change of the checkout's tree or
commits), an execute run takes a per-checkout run lock and records a start-of-run baseline, and a deterministic check of
planned tasks, commits, forbidden files and the lane's own admissions turns an incomplete result into `partial` or
`contract_violation`. The Phase 25 review cleanup lands with its stale parts corrected against the live code.
*(added 2026-11-16, re-run 2, owner directive "herdr hosting": the same lock, idle clock and checks cover a lane the runner hosts
in a herdr tab (Phase 37 R12), and a sweep removes the run directories, secret files and tabs that a runner killed hard leaves
behind, closing only a tab it can prove a dead run created (R12).)*

## Background

Requirements RUN-03, RUN-04, RUN-07, RUN-08 (REQUIREMENTS.md "Shared runner"), the 2026-11-16 GSD lane-handling amendments
(the idle clock of an execute lane also resets on tree or commit change), the evidence in
`.planning/phases/999.15-cross-ai-chain-skill-for-execute-and-review-runs/999.15-LESSONS.md` (26 phases of unattended runs:
silent stalls, partial delivery behind a passing verify, owner edits read as lane edits), and the Phase 25 reviews
(`.planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-REVIEW.md`). Phases 35 to 37 are inputs:
the label vocabulary and the hardcoding guard (35), the per-lane config (36), the call vocabulary, settings report and status
line group (37).

**The owner's decisions (highest priority):**

- A table is seed data and examples only, each row labeled with its source; it never decides which runtime or model may run
  (2026-11-16 directive, in every phase it touches). This phase adds no runtime table. Its two seed lists (admission phrases,
  default forbidden paths) are policy seeds about text and paths, shown with their source and replaceable from `CONFIG`;
  interpretation to confirm with the owner (see Ambiguity Report).
- Only `router-env/<x>` model names may be hardcoded; no new provider or model name enters the runner, its tests or its docs
  (HUB-09, 35 D-16 to D-18). Phase 38 cleans the runner file's self-test baseline entries when the harness moves.
- Never switch harness, provider or model on failure unless the owner opted in per lane; one lane per call (unchanged).
- The idle watchdog stays opt-in with a default that a slow, quiet model does not trip. For an execute lane the idle clock
  also resets on tree or commit change (GSD's stall check keys on commits since dispatch, and `pi -p` prints no stdout while
  working).
- jev and herdr only when available at the caller's runtime and never required; every path has a tested behavior without
  them. The runner is stdlib Node rendered into projects and calls neither. *(amended 2026-11-16, re-run 2, 38 D-16 and D-25 to
  D-27: the runner never calls jev; it calls herdr only through Phase 37's optional hosting transport (`tab create`, `pane run`,
  `tab close`) and, in the sweep of R12, `tab list` to prove which tab a dead run created. Herdr's screen text, agent status and
  wait output are still never a verdict or a liveness signal.)*
- *(added 2026-11-16, re-run 2, owner directive "herdr hosting")* A tab the runner opens is closed by the runner when its lane ends,
  and a tab that a killed run left open is closed only when the sweep can prove, from a record in the state home, that a dead run
  created it, and never any other pane or tab.

**Live facts checked for this spec (2026-11-16, this machine: node 24.21.0, git 2.56.0, pi 1.5.2, herdr 0.9.5):**

- The runner has no idle watchdog: its header says "No idle watchdog in this version (D-43); only the overall deadline bounds
  each child", and D-43 (18-CONTEXT) sent it to the backlog. `--idle-timeout` is `unknown argument` today (run live). A child
  is bounded by the deadline and by `attemptTimeoutS` (an attempt cap that makes a timed-out attempt a transient rung of
  the retry ladder). Its heartbeat line prints only elapsed seconds and `stdout +N bytes`, which stays `+0` for the whole
  run on a host that prints nothing until the end (999.15-LESSONS 1.14, observed in 26-02 to 26-08, not re-probed today).
- The runner already takes a start-of-run snapshot in `main` (`treeState` into `before`, a `git add -A` into a temporary index
  that never touches the user's index, plus a stat signature of ignored files) and compares it after the run (`tree=`).
  Nothing is recorded to disk, no run lock exists, and an execute run with a clean tree ends `no_change`. `rung2Gate` already
  reads the plan's `<files>` union from the prompt (`promptFiles`) and `changedPaths` diffs two write-tree ids.
- GSD's cross-AI step builds the prompt from the plan's `<objective>` and `<tasks>` (task blocks with `<name>` and `<files>`)
  plus PROJECT.md context, with no plan id, and runs one fixed command string for every plan
  (`execute-phase/detail/elaboration.md` step 2.5, read 2026-11-16). On success it writes stdout as the plan's SUMMARY and
  marks the plan complete; on a non-zero exit it offers retry, skip or abort. Exit 0 therefore means done to GSD.
- GSD keys its own stall surveillance for native executors on `git log <branch> --since=<dispatch>` every
  `executor.stall_detect_interval_minutes` (default 5) and asks the owner after `executor.stall_threshold_minutes` (live
  `config-get`: 10) without commits, a SUMMARY or a completion signal, measured from the last sign of progress
  (`execute-phase.md` step 4 and `steps/executor-progress-policy.md`). It never kills.
- GSD resolves a plan's commits by the subject `<type>(<phase>-<plan>):` (`gate-evaluation-scope.cjs`; live call
  `check evaluation-scope --plan 37-01 --commits-only --raw` returns `commits`, `changedFiles`, `outsideUnion`). The runner is
  standalone and cannot import it.
- The existing status vocabulary (`STATUS_TABLE`) has no `partial` and no `locked`; Python's `STATUS_TO_REASON` mirrors the
  table and still holds `idle_stall` for "runners older than template 7". `contract_violation` means a review lane changed
  the tree.
- herdr 0.9.5 is present (`HERDR_ENV=1`). `herdr pane current` returns `agent_status` for the pane's detected agent and
  `herdr agent wait` waits on agent states, but a headless lane started by the runner is not a pane agent; whether herdr
  reports it is unverified, so herdr is never a liveness signal here.
- pi 1.5.2 `--help` lists `--mode <text|json|rpc>` (default text). Whether `-p --mode json` streams events while working is
  unverified; the runner's pi formula uses text mode.

**Live facts added 2026-11-16 (re-run 2, herdr 0.9.5, node 24.21.0, Linux 7.3; probes in a tab labeled `aikit-live38`, closed by the
probe itself; the scripts and outputs are under `tmp/spec-discuss-35-39/`, not committed):**

- A launcher run in a pane as `sh <path>` is its own process group's leader: its group id equalled its pid and its parent was the
  pane shell, not the caller. Its plain and `nohup` children shared its group. `herdr tab close` returned in 0.29 s and ended the
  launcher and both of those children, but a grandchild that called `setsid` (its own session and group) survived the close
  (it was killed by the probe afterwards). A headless lane's group kill has the same limit, so it is stated, not solved.
- `herdr tab get` returns the tab's `label`; `herdr tab list` returns every tab of every workspace with `tab_id`, `workspace_id`
  and `label`. A tab created with a label was found again by the exact label, with the id of its own `tab create`. Tab ids
  counted up across the probes (`w7:tG`, then `w7:tH`) and were never seen reused; one run is not proof, so the sweep matches the
  label as well as the id. `tab close` and `tab get` of a closed or unknown id exit 1 with a JSON error code `tab_not_found`;
  with an unreachable socket (`HERDR_SOCKET_PATH` pointed nowhere) both exit 1 with the code `server_not_running`.
- Polling the three files of a run directory (a size check of `out` and `err` plus an existence check of `rc`, reading only new
  bytes) in a Node process for 10 s: 100 ms interval 0.18 % of one core, 250 ms 0.08 %, 500 ms 0.04 %. Reading a pid's start
  ticks from `/proc/<pid>/stat` (field 22, parsed after the last `)`) took 0.004 ms; `ps -o lstart= -p` took about 12 ms and
  resolves to whole seconds.
- A launcher that sources its env file, opens the prompt file on file descriptor 3 and deletes both as its first steps still gave
  the lane its environment and its stdin (checked in a scratch run directory).
- A writer appending through a `>>` redirect kept writing correctly while another process truncated the file to zero after each
  read: 3 MiB written, all 3 MiB read, two truncations, final file not sparse.

**Live facts added 2026-11-21 (cross-phase amendment: what Phase 37 shipped; read at HEAD 5cf21ac, unit 38 stacked on Phase 37's
code-review fold 42bad13; every line below was read in the code, `cross-ai.mjs` = `skills/ai-kit-spec-review/references/cross-ai.mjs`):**

- *Size and shape.* The template is 15,179 lines at template version 9 (`cross-ai.mjs:2`, `cross_ai.py:60` `TEMPLATE_VERSION = 9`);
  `--self-test-list` prints 626 cases (567 `logic`, 59 `runtime`, 19 `host-`). The harness now runs from `FAKE_PRELUDE`
  (`cross-ai.mjs:6433`) through the fakes (`writeFakePi` :6468 to `writeFakeHerdr` :7133), `STATUS_HEAD_RE` (:7187), the case
  runners (`reapUnder` :7315, `runSelfTestCase` :7524, `selfTestRoot` :7581) and `blackBoxSelfTest` (:7591 to :14783); `callOf`
  (:14785) and `main` (:14831) follow it. The 2026-11-16 figures (lines 5400 to 12550 of 12,840, about 430 cases) are superseded.
- *Findings line numbers.* `watchChunk(cli, source, relay, state, chunk)` is at `cross-ai.mjs:5310` (callers :5357, :5365), the
  `dropState` test `STATE_DELETE.has(status) || (status !== 'quota' && !QUOTA_KEEP.has(status))` at :5624, and the redundant
  assignment before `return argv` in `build_runner_argv` at `runner_dispatch.py:273-277`. `clampAttemptTimeout` (:3775), `clampCapS`
  (:3781), `liveMatch` (:5287) and `armLimit` (:5300) are present.
- *Run record and run directory (plan 37-19, fixed; Phase 38 reads them and renames nothing).* `tests/fixtures/runner_host_protocol.json`
  pins `run_dir` `<state home>/ai-kit/spec/host/<token>`, `dir_mode` 700, `file_mode` 600, the files `run.json`, `launch.sh`, `env`,
  `prompt`, `out`, `err`, `pid`, `rc` (`HOST_FILES`, `cross-ai.mjs:4706`), `token_pattern` `^[0-9a-f]{12}$`, the label
  `aikit:(review|execute):<runtime>:<token>` (pattern and `max_length` 63 in the fixture), `typed_line` `sh <launcher path>`,
  `done_line` `AIKIT-HOST-DONE <token> rc=<rc>`, `verdict` `rc`, and `run_record_fields`, exactly: `checkout_root`, `created_ms`,
  `host_name`, `label`, `launcher_pgid`, `launcher_pid`, `launcher_start`, `pane_id`, `role`, `runner_pid`, `runner_start`,
  `runtime`, `tab_id`, `token`, `version` (`RUN_RECORD_VERSION = 1`; written by `writeRunDir`, :4828-4846, through
  `writeCycleState`). `launcher_pgid` is a field R12's list did not name. The record is rewritten at `tab create` (:4943) and at the
  first pid read (`adoptPid`, :4982-4993), also from a `finalize` that runs before the first poll (37 review MEDIUM-6).
- *The launcher's group.* The launcher re-execs itself under `/usr/bin/env -i ... /usr/bin/setsid /bin/sh "$0"` (`buildLauncher`,
  :4808); util-linux `setsid` forks when the caller already leads its group (a pane job does), and the `pid` file is written by the
  forked shell (`$$`, :4815), so it holds the real launcher pid, which leads its own session and group (session id = group id = pid).
  `launcher_pgid` is `procGroup(launcher pid)` at adoption. Any liveness test or signal of Phase 38 for a hosted lane (the R3/R12
  lock's "child group", the R12 idle kill, the sweep's "launcher group is gone") targets the recorded `launcher_pgid` with the rule
  37 shipped: a verified leader (`launcherVerified`, :4891: recorded start not `-`, unchanged start, group id equal to pid) or, when
  the leader is gone, a live member of that group and session (`groupMembers(pgid, sid)`, :4768, a `/proc` scan; neither id is
  reused while a member lives); a launcher that was already gone at adoption is unverified and only members of the session it made
  itself (sid = pgid = pid) count. Since the 37 review (MEDIUM-1) `hostedChild.finalize` ends that group on every exit (SIGTERM,
  wait unless the lane exited, SIGKILL) and the idle kill must reuse that finalize path, not a second kill routine.
- *Liveness helpers are runtime code.* `pidAlive` (zombie-aware, :4712), `procStartTime` (field 22 after the last `)`, `-` when
  unreadable, :4741), `procGroup` (:4749), `procSession` (:4758) and `groupMembers` (:4768) live in the runner's hosted-lane block,
  not only in the self-test; R3's start-time read and R12's checks reuse them. Linux only: there is no `ps -o lstart=` fallback in
  the code yet (R3's non-Linux read is new work).
- *What R12 already has.* The launcher sources `env`, opens `prompt` on file descriptor 3 (or reads it for an argv prompt) and
  deletes both before it writes `pid` (:4810-4815); it appends to `out` and `err` (`>>`, :4817); the runner's `dropSecrets` and
  `keepRecordOnly` (:4871-4880) run on every exit path it controls, and `exitFlushed` (:1334-1343) retries the tabs in `openTabs`
  and keeps only `run.json` when a close is not confirmed ("kept ... for the sweep"). Not shipped: the sweep, `--sweep`, `tab list`,
  the 2x-cap truncation (`hostedChild.readNew`, :4963-4972, reads into `pushCapped` buffers but never truncates a file), the idle
  hook, and a lock. The runner has no `process.on('exit')` handler; `exitFlushed` is its one exit path (R3's release joins it).
- *herdr verbs, three places.* `HERDR_VERBS = ['tab create', 'pane run', 'tab close']` (:4674, comment "Phase 38 adds tab list"),
  the arch rule `HERDR_VERBS_ALLOWED` (`tests/test_arch.py:1860-1862`) and the fixture's `herdr_verbs` move together when `tab
  list` joins; `herdrCall` (:4678) stays the one herdr spawn site. The fake herdr (`writeFakeHerdr`, :7133) answers `tab create`,
  `pane run`, `tab close` and exits 2 on any other verb; it already holds a foreign tab `t0` labelled `aikit:review:pi:000000000000`.
- *Status line, settings report, sessions, `--describe`.* Phase 37's group is `session=<id|-> applied=<..> ignored=<..> unknown=<..>
  escalate=<..>` after `attempts= cycles=` and before `retry_after_s= cycle=` (`finish`, :1288-1313; `STATUS_HEAD_RE`, :7187-7190);
  R5's `coverage= findings=` group goes between `escalate=` and `retry_after_s=` and `STATUS_HEAD_RE` gains it as one optional group.
  Python reads the line token by token (`parse_status_line`, `runner_dispatch.py:280-286`). The settings report prints `cross-ai:
  setting <name>=<value> applied|ignored reason=<r>` for the closed names `SETTING_NAMES` (:1570: model, provider, role, effort,
  context, session, escalate_runtime, escalate_model, host, skill, mcp) and reasons `SETTING_REASONS` (:1569); the idle watchdog,
  the lock, `--baseline`, `--plan-id`, `--forbid` and `--sweep` are runner supervision flags, not lane settings, so neither list
  changes (R11: "Phase 37's reason list unchanged"). `--describe` prints `{schema: 1, template_version, settings, reasons, states,
  runtimes, host}` (`describeJson`, :14810-14829; golden `tests/fixtures/runner_describe_golden.json`) and has no status, flag or
  finding key today, so "`--describe` lists" (R5, R11, R12) means new keys added beside the existing ones, which stay unchanged.
- *`--print-argv` stability.* Python reads `--print-argv` stdout and stderr lines (`print_argv_lines`, `runner_dispatch.py:301-323`;
  `preview_model_id` reads the `cross-ai: model-id` line). For a call that passes none of the new flags, the stdout argv line and
  every existing stderr line stay byte-identical; the only differences allowed are the ones this SPEC adds: R1's one idle line and
  R5's status-line group (`coverage=- findings=-` on a no-spawn call).
- *Node children (Volta shim hazard).* `node` on PATH here is a Volta shim that forks a chain a plain `subprocess.run` timeout does not
  stop. Product code that spawns node runs it through `run_in_own_group` (`ai_kit_spec/detection.py:951`: own session, group killed on
  timeout), as `print_argv_lines` does; tests take node from `tests.cross_ai_selftest._real_node_executable()` (:39). This binds R9's
  gsd-core call and every new test that runs the runner.
- *Runner copy rule.* The live `.planning/scripts/cross-ai.mjs` (header `sha256=` stamp) is re-rendered through curated-config
  `ensure-runner` (`cross_ai_script.ensure_runner`); `make check-dogfood` must end `check-dogfood: ok` (the 37 review's first fold
  push was refused on a stale copy). A phase 38 template change therefore ends with a re-render of the live copy and a re-record of
  the self-test shard times (`python3 tests/cross_ai_selftest.py --record-times`, `tests/fixtures/cross_ai_selftest_secs.json`), as
  plan 37-23 did; the template version goes from 9 to 10 (`TEMPLATE_VERSION` and the header) in the same step.
- *Hardcoding baseline.* `tests/fixtures/no_hardcoded_models_baseline.json` still holds the runner entry with 14 hits and
  `"cleaned_by": "37"` (Phase 37 did not clean it). The guard is shrink-only and scans `skills/`, so moving harness text into
  `cross-ai-selftest.mjs` cannot carry a hit to a new path: R8's "entries removed" means each hit is rewritten to an allowed form
  (`router-env/<x>`, `fake/<token>`, `fake-<token>`, `placeholder-model-<n>`) or removed with the runner entry.
- *Judge state.* `ai-kit-cross-ai` met the bar in Phase 37 (loop 37 round 3, worst 83.2 B, critical 0; three high findings fixed under
  the fix-3-or-fewer rule; digest stale by design; `37-VERIFICATION.md` on the unit 37 branch). R11's material SKILL.md update still
  runs the judge loop (AGENTS.md), with no regression beyond run-to-run variation against 83.2 B.
- *Grok.* Grok is not a target (owner, 2026-11-19; Phase 39.1 removes it). No Phase 38 plan, test, fixture, list or doc adds or extends
  a line naming grok; existing grok text stays untouched.

**Findings (existing code paths; some Phase 25 items are stale):**

- `watchChunk(cli, source, relay, state, chunk)` uses only `relay` and `chunk` (cross-ai.mjs:4611); the `dropState` test
  `STATE_DELETE.has(s) || (s !== 'quota' && !QUOTA_KEEP.has(s))` equals `!QUOTA_KEEP.has(s)` (:4901);
  `runner_dispatch.py:260` ends `return argv` after an assignment (to re-check at plan time). Already gone: the `stoppedWhy`
  cooldown branch and `clampCooldownS`. Not dead: `clampCapS` (the 4-hour bound, T-25-13) and `clampAttemptTimeout` (read by
  `attemptCapMs`); `liveMatch`, `armLimit` and the stdout limit watcher are live (CR-01). *(Line numbers amended 2026-11-21: the
  items now sit at `cross-ai.mjs:5310`, `:5624` and `runner_dispatch.py:273-277`; see Live facts added 2026-11-21.)*
- WR-05 (a user's lower `cross_ai_timeout` lost on cleanup) lived in `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py`
  (`clear-workflow-keys`), removed in Phase 31 (commit d1f0f9f). No flow today unsets the key. The only raise is curated-config's
  `timeout_value` (`cross_ai.py:166`, a value below 1800 becomes 1800) shown in the plan entry, with a per-apply backup.
- Two rules decide "router-backed": Python `runner_dispatch.resolve_route` (route `router` only when `fallback_quota` is a
  boolean the owner confirmed in `heuristic_confirmed`) and curated-config `catalog_adapter.py:381-405` (`router_confirmed` =
  `is_router` confirmed and a name-declared purpose). Phase 35 D-15 makes `router-env/<x>` aliases assumed with no heuristic
  question, so neither rule would ever confirm one.
- `classify_dispatch_failure` already returns `quota` for a spent ladder, but the reference
  `ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md` (lines 169-171) still parses `RETURNCODE`,
  `RETRY_AFTER_S` and `CYCLE` with three `python3 -c` calls.
- curated-config re-implements gsd-core's skill resolution in `plan_io.py` (`skipped_skill_problem`, `_skipped_items`,
  `_skip_message`, `_kept_names`, plus `skills.py` `locate` and `needed_root`) while gsd-core exports
  `buildAgentSkillsBlock(config, agentType, projectRoot, diagnostics)` (`init.cjs:3826`, exported at :4359) and a
  `query agent-skills <agent> --json` verb that reports `reason` and `warnings`.
- The embedded self-test harness runs from about line 5400 to line 12550 of the 12,840-line template and holds about 430
  cases (`--self-test-list`, run live). Rendering is a config-block splice plus a hash header (`cross_ai_script.py`).
  *(Amended 2026-11-21: 15,179 lines and 626 cases after Phase 37, harness from `:6433` to `:14783`; see Live facts added
  2026-11-21.)*

## Requirements

1. **An opt-in idle watchdog ends a silent lane (RUN-03)**: with it on, a lane that prints nothing for the idle time has its
   process group ended through the existing finalize path, and the call follows the existing timeout rules.
   - Current: no watchdog; only the deadline and `attemptTimeoutS` end a child, so a stall such as the observed 1800 s
     `out=0` timeouts burns the whole window.
   - Target: `--idle-timeout <seconds|default>` (integer 0 to 86400, 0 = off, or the word `default`), and the baked
     `CONFIG.idleTimeoutS` (integer, 0 = off) beneath the call. Neither set means off. `default` is the constant
     `IDLE_DEFAULT_S = 900`, labeled `judged` with its evidence (healthy review lanes took 288 to 579 s in total, observed
     stalls printed nothing for 1800 s, GSD asks the owner after 10 minutes without commits). The clock starts at each
     attempt's spawn and resets on any byte on the child's stdout or stderr (heartbeat lines the runner prints itself do not
     count). A value below 60 prints a notice that a slow, quiet model may be ended; a value at or above the attempt's
     remaining budget prints a notice that it cannot fire before the deadline. At the idle time the runner prints
     `cross-ai: idle watchdog: <cli> printed nothing for <N>s; ending its process group`, ends the group (SIGTERM, grace,
     SIGKILL, drain: the same path as a timeout), and the attempt counts as a timed-out attempt, so the retry ladder and the
     deadline behave exactly as for an attempt cap (resume the same session, then a new session, then the hard tier); the
     attempt log line reads `status=timeout rule=idle-watchdog`. The final exit is whatever the ladder yields from the
     existing vocabulary (`timeout`/124 when no rung is admitted, otherwise `transient`/75 with its hint). A review lane's idle
     signal is output only (a review lane is read-only and a changed tree already voids it). `--print-argv` prints the resolved
     setting (`cross-ai: idle watchdog off` or `on timeout=<N>s`) and starts nothing. A host that prints nothing until the end
     (pi in text mode) has no activity signal on a review lane: the default leaves room, and the limit is documented.
   - Acceptance: self-test cases with fake lanes: a lane that stops printing is ended after the idle time and its group is
     gone, with an exit and status from the existing vocabulary and the attempt line above; a slow, quiet fake (silent for a
     few seconds, then an answer) with `--idle-timeout default` is not ended; with the flag absent and `CONFIG.idleTimeoutS`
     0 the watchdog never fires; `default` resolves to 900 in the `--print-argv` line; the flag against the baked value (the
     call wins, 0 turns it off); a non-integer, negative or empty value is a usage error naming the flag; the two notices;
     the watchdog never ends a lane that keeps printing.
   - *Amended 2026-11-16 (38 D-28, R12):* "byte on the child's stdout or stderr" also means growth of `out` or `err` for a lane
     Phase 37 hosts in a herdr tab; the clock, the notices, the attempt line and the ladder are unchanged.
   - *Amended 2026-11-21 (Phase 37 shipped; Live facts added 2026-11-21):* the idle line printed by `--print-argv` is one added
     stderr line; the stdout argv line and every other existing line of a call without the new flags stay byte-identical. A hosted
     lane's idle end goes through `hostedChild`'s own `finalize` (37 review MEDIUM-1), which signals the recorded `launcher_pgid`.

2. **An execute lane's idle clock also resets on tree or commit change, and a lane that prints but changes nothing is
   reported (RUN-03)**.
   - Current: the runner reads the tree only before and after a run, and the heartbeat reports output bytes only.
   - Target: with the watchdog on and role execute, the runner reads `treeState` (the existing read-only snapshot through a
     temporary index) at most once per check interval (`idle/10` seconds, clamped to 1 to 60), never two reads in flight and
     only when no output arrived since the last check. A changed `head` or `tree` against the previous read resets the idle
     clock; the first read is the baseline's own value. When output keeps arriving (so the output clock never expires) but the
     snapshot has not changed for the idle time, the runner prints once per period `cross-ai: <cli> printed output but changed
     nothing in the checkout for <N>s` and records the informational finding `no_tree_change`; it never ends such a lane. A
     read that fails or times out is no signal at all: it resets nothing, is logged once, and never ends the lane. The heartbeat
     line gains `commits +<n> since the baseline, tree changed|unchanged` from the last read while polling is active (no
     extra git call). A review lane never polls. Reads never touch the user's index or working tree.
   - Acceptance: a fake execute lane that prints nothing but keeps committing (or editing a tracked file) for longer than the
     idle time is not ended; one that prints nothing and changes nothing is ended; one that prints steadily and changes nothing
     is reported with the notice and `no_tree_change` and not ended; a git read made to fail (the existing `git-hang` and
     `git-after-fail` fakes) ends nothing and logs once; a review-role fake performs no tree polling; the user's index file is
     byte-identical after a run.

3. **A run lock refuses a second execute run on one checkout (RUN-07)**.
   - Current: nothing stops two execute runs from sharing a checkout and its pre-commit stash.
   - Target: an execute run acquires the lock after its arguments and prompt are validated and before its first snapshot or
     spawn, as a record created atomically (`open` with `wx`, mode 0600) under the runner's state directory
     (`<state>/ai-kit/spec/locks/<sha16 of the checkout root>.json`, the same state home and 0700 directory rules as the quota
     records; the checkout root is the git top level, else the working directory's real path). The record holds the runner pid,
     its start time (`/proc/<pid>/stat` start ticks on Linux, `ps -o lstart=` elsewhere, `-` when neither reads), the host
     name, the start time of the run, the lane, the role, the run id, the child process group once spawned, and the baseline of
     R4. A second execute run that finds a live record prints `cross-ai: run lock held by pid <p> (lane <cli>/<model>, since
     <time>); not starting` and ends with the new status `locked` and exit 75 with no `retry_after_s` (a bare 75: the caller
     reports or serializes, never loops). A record is stale when its host is this host, its pid is dead (or alive with a
     different start time) and its recorded child group is dead too: the runner prints `cross-ai: stale run lock from pid <p>
     (since <time>) cleared` and takes the lock (the removal is a rename to a unique name, then a fresh `wx` create, so two
     runners clearing one stale lock leave one winner). A dead runner whose child group still lives is reported as
     `cross-ai: run lock: pid <p> is gone but its child group <g> still runs; not starting` and refuses with `locked`; a record
     from another host cannot be probed and refuses with the host named; an empty or unparseable record is re-read for up to
     2 s, then refused naming the file and its age, and is never cleared automatically. The lock is released on every exit path (ok, any
     failure status, signal exit) and by an `exit` handler backstop. The lock is advisory against other runners only: it does
     not stop a human's commit or another tool. Review lanes take no lock (parallel lanes are by design); a review that starts
     while a live execute lock holds the checkout prints `cross-ai: note: an execute run holds this checkout; the tree check may
     void this review` and runs. `--print-argv`, `--classify-only`, `--self-test` and every usage error take no lock.
   - *Amended 2026-11-16 (38 D-26, R12):* for a lane Phase 37 hosts in a herdr tab, "the child process group once spawned" is the
     launcher's process group (with the run token and tab id beside it) and "its recorded child group is dead too" reads that
     group; a surviving tab is not a live lane and does not keep a lock.
   - *Amended 2026-11-21 (Phase 37 shipped; Live facts added 2026-11-21):* the start-time read reuses the runner's `procStartTime`
     and the group test reuses `pidAlive`, `launcherVerified` and `groupMembers` (runtime code since 37-19/37-20); the hosted lane's
     group is the recorded `launcher_pgid`. The runner has no `exit` handler today: the backstop is new, beside `exitFlushed`.
   - Acceptance: a self-test case starts two execute runs on one fake checkout at the same moment: exactly one runs, the other
     prints the message and ends `locked`/75 with no spawn; a record with a dead pid is cleared with the stale notice and the
     run proceeds; a dead runner with a live recorded group refuses; a record of another host refuses; the lock file is absent
     after ok, failure and signal exits; two runners racing to clear one stale record leave one winner; a review run takes no
     lock and prints the note when an execute lock is live.

4. **A start-of-run baseline is recorded and later checks compare against it (RUN-07)**.
   - Current: `before` lives in memory for one call; a fix round in a new call starts a new snapshot.
   - Target: after acquiring the lock the runner takes `treeState` (HEAD and the write-tree of the working tree, which already
     holds files the owner left dirty) and stores `{head, tree, at, role, cli, model}` in the lock record. A second record
     keyed by the task digest (`taskDigest`, the hash of the plan's `<objective>`) is kept under
     `<state>/ai-kit/spec/baselines/<sha16 of the checkout root>/<digest>.json` and reused by a later call for the same task
     while it is younger than the quota cap (`capS`), the checkout's HEAD still descends from its `head` (`git merge-base
     --is-ancestor`), and the task has not ended `ok`; otherwise it is replaced with the informational finding
     `baseline_replaced` and its reason. A finished task (`ok`) deletes its record. `--baseline <sha>` (hex, 7 to 64 characters,
     checked against the repository) overrides the stored one for callers that track it. An unborn HEAD gives a baseline with no
     head (all commits count). A record that cannot be read or written leaves an in-memory baseline for this call, prints one
     note, and does not stop the run. R2 and R5 compare against this baseline: owner-dirty files that did not change since the
     baseline are never the lane's.
   - Acceptance: tests show the baseline written on start and equal to the in-run snapshot; a second call for the same task
     reuses it (commits of the first call count in the second); a rebased or reset HEAD replaces it with the finding; an `ok`
     run deletes the task record; `--baseline` with a bad value is a usage error and with a good value wins; an unwritable
     state directory still runs with the note; a file the owner left dirty and never touched is absent from the changed paths.

5. **An execute result counts as done only when its commits, files and report agree with its plan (RUN-08)**.
   - Current: an execute run with a changed tree and exit 0 ends `ok` and GSD marks the plan complete, whatever the commits
     cover (26-03: report admitted unimplemented cases; 26-04: one commit for three tasks).
   - Target: for role execute, after a run that reached its spawn, the runner computes findings from the prompt's plan, the
     commits since the baseline, the changed paths and the lane's report, and prints them as `cross-ai: finding reason=<code>
     detail=<text>` (values redacted, control characters removed, at most 10 paths or phrases shown) before the status line.
     Planned tasks are the `<task>` blocks of the caller's prompt whose `type` is absent, `auto` or `tdd` (checkpoint types
     excluded), each with its `<name>` and `<files>` (comma list, as `promptFiles` reads it). A task is covered when a commit
     since the baseline touched one of its listed paths (a listed path ending `/` covers its whole directory); a task with no
     paths, or only glob characters, is unchecked, not covered and not uncovered. `--plan-id <id>` (optional, `^[0-9]+(\.[0-9]+)*-[0-9]+[A-Za-z0-9.-]*$`) adds the
     GSD subject rule: the commits whose subject is `<type>(<id>):` (zero padding tolerated) must number at least the planned
     task count. No `<task>` block in the prompt gives `coverage=n/a` and no task finding. The closed finding list, locked by a
     test against the runner source, the SKILL.md table and `--describe`'s output:
     - blocking, result `partial` (new status, exit 1): `no_commit` (exit 0 with an answer, planned tasks, and no commit since
       the baseline), `task_uncovered` (a checkable task without a covering commit, or the plan-id count short),
       `admits_skipped` (a phrase from the admission seed list in the answer, outside fenced and inline code);
     - blocking, result `contract_violation` (existing status, exit 1): `forbidden_path` (a path that changed between the
       baseline and the end, committed or not, is in the forbidden set and not named by the prompt's `<files>`);
     - informational, never change the status: `no_tree_change` (R2), `outside_plan_files` (paths changed outside the prompt's
       `<files>`, counted), `uncommitted_edits` (the end tree differs from HEAD in paths that were clean at the baseline),
       `baseline_replaced` (R4), `coverage_unchecked` (tasks it could not check).
     The forbidden set is `CONFIG.forbiddenPaths`, default the three GSD orchestrator-owned files (`.planning/STATE.md`,
     `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, source: elaboration.md step 4, verified 2026-11-16), plus each
     `--forbid <path>` (repeatable, repo-relative, trailing `/` for a directory). The admission seed is `CONFIG.admissionPhrases`
     (lowercase substrings, default a short list labeled `judged` with its evidence, 999.15-LESSONS 1.3, recall unverified);
     the matched phrase is printed. `contract_violation` wins over `partial`; `no_change` wins over both (a clean tree). The
     status line gains the group `coverage=<covered>/<checkable>|n/a|- findings=<codes|->` after Phase 37's group and before
     `retry_after_s` (`-` when no check ran: review role, no spawn). An execute run that is not `ok` keeps its status and still
     prints the findings, so the resume knows what is missing. No answer text is written to stdout for `partial`.
     `STATUS_TABLE`, Python's `STATUS_TO_REASON` (`partial` and `locked` map to `real_error`), `cross-ai-dispatch.md` and the
     SKILL.md status tables gain the two statuses.
   - Acceptance: fake execute lanes, one case each: all tasks committed and a clean report is `ok` with `coverage=3/3
     findings=-`; a lane that commits one of three tasks is `partial`/exit 1 with `task_uncovered` and the missing task names;
     a lane that exits 0 with an answer and no commit is `partial` with `no_commit`; a report saying a task was not
     implemented is `partial` with `admits_skipped` and the phrase, while a report with a Deviations heading and no phrase is
     `ok`; a lane whose diff touches `.planning/STATE.md` is `contract_violation` with `forbidden_path`, and the same path
     named in the plan's `<files>` is `ok`; a prompt with no task blocks gives `coverage=n/a`; the plan-id rule with a matching
     and a short commit count; the closed list lock; the status-line group parses with `parse_status_line` and `_trailer_counts`
     unchanged; a file the owner left dirty and untouched is never reported.
   - *Amended 2026-11-16 (38 D-29, R12):* a lane Phase 37 hosts in a herdr tab is checked by the same functions on the same
     inputs (the captured `out` is the answer, `rc` is the verdict, the reads are against the checkout); the finding list and the
     status-line group are unchanged, and a state home inside the checkout is excluded from the snapshot.
   - *Amended 2026-11-21 (Phase 37 shipped; Live facts added 2026-11-21):* the group `coverage= findings=` sits between Phase 37's
     `escalate=` and `retry_after_s=` (`finish`, `cross-ai.mjs:1288-1313`), `STATUS_HEAD_RE` (:7187) gains it as one optional group,
     and `--describe` lists the statuses and finding codes under new keys beside its existing ones (golden updated in the same plan).

6. **One confirmed-router rule (RUN-04)**.
   - Current: `resolve_route` and `router_confirmed` are two rules (Findings), and Phase 35 D-15 leaves router aliases
     assumed, never confirmed.
   - Target: one function, in `model_heuristics.py`, decides whether a catalog entry is a confirmed router lane: its
     `fallback_quota` is true and its label is `user-stated` (the owner confirmed it) or `assumed` by the alias naming rule of
     Phase 35 D-15; a `judged` name hint stays advisory (`route=router-inferred`, never the quota cycles), as the runner's own
     comment requires. `resolve_route`, curated-config's `router_confirmed` and the `routerBacked` render read it. The
     name-declared purpose check of curated-config stays separate (it decides execute eligibility, not router-ness).
   - Acceptance: one fixture matrix (owner-confirmed, alias assumed, hint only, not a router, both fields disagreeing) gives the
     same answer through every caller; the second rule's code is deleted; the existing runner pin of the hint list still passes.

7. **A quota-cycle class from the classifier (RUN-04)**.
   - Current: `classify_dispatch_failure` returns `ok`, `quota` or `real_error`, and the reference parses the retry tokens with
     three shell JSON calls.
   - Target: the class `quota_cycle` is the one case that gets the single re-invoke (exit 75 with whole-number `retry_after_s`
     and `cycle`); `quota` keeps the owner-stop quota outcomes (69, a bare 75, a dropped hint); the `classify-dispatch-failure`
     subcommand prints one JSON object with `class`, `retry_after_s` and `cycle`, and the three `python3 -c` token parses of
     `dispatch-external-cli.md` are deleted. The SKILL.md and reference wording follow.
   - Acceptance: table-driven tests over dispatch results (75 with tokens, 75 bare, 69 with tokens, a malformed token, a
     non-dict status, exit 0, other exits) for the class and the printed object; the reference holds no `python3 -c` for tokens;
     the text pins of the class names updated.

8. **The self-test harness leaves the runner file; rendered copies do not carry it (RUN-04)**.
   - Current: the 12,840-line template holds the harness, and every rendered project copy carries it.
   - Target: the harness (the self-test constants, fakes, case table and drivers, from `blackBoxSelfTest` and its helpers
     through the case list, and the classifier fixtures that only it reads) moves to the sibling file
     `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs`. The runner exports, by one explicit `export { ... }` list,
     what the harness imports, loads the sibling only for `--self-test` and `--self-test-list` through a dynamic `import` of
     the file next to itself, and prints a named refusal (`cross-ai: the self-test is not shipped in this copy; run it from the
     template`) with exit 2 when the sibling is absent. The render path (`cross_ai_script.py`) is unchanged: a rendered copy
     is the template's bytes with the config block replaced, so Phase 37's sync test keeps comparing every byte outside the
     config block (nothing is relaxed). The case list, names, kinds and order, `STATUS_HEAD_RE`, the sample lines in
     `skills/ai-kit-cross-ai/SKILL.md` and `launch-and-wait.md`, and `tests/cross_ai_selftest.py`'s interface stay as Phase 37
     leaves them; the shard times are re-recorded. The live `.planning/scripts/cross-ai.mjs` is re-rendered after the move.
   - Acceptance: `--self-test-list` before and after the move is byte-equal; every case passes; a rendered scratch copy is
     smaller by the harness, runs `--print-argv` and one fake lane, and `--self-test` on it prints the refusal; the sync test
     passes unchanged; a test fails when the harness names a runner symbol the export list lacks; `make check-dogfood` passes
     on the re-rendered live copy; the hardcoding baseline entries for the runner's self-test are removed.
   - *Amended 2026-11-21 (Phase 37 shipped; Live facts added 2026-11-21):* the harness range is now `FAKE_PRELUDE`
     (`cross-ai.mjs:6433`) to the end of `blackBoxSelfTest` (:14783), about 8,350 of 15,179 lines, 626 cases; the runtime liveness
     helpers (`pidAlive`, `procStartTime`, `procGroup`, `procSession`, `groupMembers`) stay in the runner and are exported to the
     harness. The 14 runner baseline hits are rewritten to allowed forms (a shrink-only guard cannot move them to the sibling's path).
     Tests that run the runner or the sibling take node from `_real_node_executable()`.

9. **curated-config asks gsd-core which skills it would skip (RUN-04)**.
   - Current: `plan_io.py` and `skills.py` re-implement gsd-core's skill-resolution rules (Findings).
   - Target: the skipped-skill check calls gsd-core's own `buildAgentSkillsBlock` (through a node call of the project-local
     gsd-core, resolved the way the repository's other gsd-core calls resolve it) against the candidate config and reads its
     diagnostics; the cause and fix text of each skipped entry is built from those diagnostics. The re-implemented resolution
     code is deleted. With no gsd-core present the check is skipped with a named note and never blocks or crashes.
   - *Amended 2026-11-21 (Phase 37 shipped; Live facts added 2026-11-21):* the node child runs through `run_in_own_group`
     (`ai_kit_spec/detection.py:951`), never a bare `subprocess.run` of PATH `node`; `buildAgentSkillsBlock` is at
     `.claude/gsd-core/bin/lib/init.cjs:3828`, exported at :4361.
   - Acceptance: with the real project-local gsd-core a skipped entry (a missing path, an untrusted root) yields its cause from
     gsd-core's diagnostics and the same fix command as today; without gsd-core a plan edit proceeds with the note; the deleted
     functions are gone; the existing `skipped_skill_problem` tests pass or are replaced by tests of the same cases.

10. **The remaining Phase 25 cleanup, corrected against the live code (RUN-04)**.
    - Current: the roadmap lists dead state, live-detection plumbing, clamp helpers and a timeout restore; part of that is stale
      (Findings).
    - Target: remove exactly what is dead today: the unused `watchChunk` parameters, the redundant `STATE_DELETE ||` term of the
      `dropState` test, and the redundant assignment before `return argv` in `runner_dispatch.py` (re-checked at plan time);
      keep `clampCapS`, `clampAttemptTimeout`, `liveMatch` and `armLimit`, and record that in the SKILL or code comment. The
      timeout item is amended: the cleanup that restored the value no longer exists (Phase 31), so the criterion becomes that a
      workflow timeout below the 1800 s minimum is never changed without being shown: the curated-config plan entry carries the
      current and the new value, a test pins it, and no document says a flow "never touches" or "restores" the user's value.
      ROADMAP Phase 38 criterion 2 and RUN-04 are amended in the same commit as this SPEC's decision.
    - Acceptance: grep shows the dead items gone and the kept helpers present; the self-test and unit suites pass unchanged in
      outcome; the plan-entry test for a lower timeout passes; a doc scan finds no restore claim.
    - *Amended 2026-11-16 (38 D-22):* backlog 999.21 folds in as a proof only: the runner already drops its `cross-ai-*` and
      `xai-idx-*` temp folders on every exit (commit c535683, 2026-11-14); one self-test case shows that a run leaves no such
      entry in its temp folder after an ok, a failure, a timeout and a signal exit.

11. **Skill text, docs, the closed lists, the guard and the judge bar (JDG-04, HUB-09)**.
    - Current: `ai-kit-cross-ai` (judged below the bar at Phase 32; Phase 37 is to bring it to the bar) and the runner docs have
      no watchdog, lock, baseline or check text; the runner file's self-test holds the guard's baseline entries.
    - Target: `skills/ai-kit-cross-ai/SKILL.md` documents `--idle-timeout`, `CONFIG.idleTimeoutS`, the lock and its `locked`
      status, `--baseline`, `--plan-id`, `--forbid`, the finding list, `partial`, the two new status-line keys, how to read each,
      what a caller does on `locked` and `partial` (report or serialize; resume the same session with the missing list; never
      loop), the stated limits (a silent host has no review-lane signal; the lock stops runners, not humans; a human edit during
      a run is indistinguishable from the lane's), and the conditional helpers: a calling skill may show a long lane in a
      herdr pane and may screen an admission-only `partial` with jev, each only when present at its runtime, with the
      deterministic result as the tested default (jev classification of execute results is Phase 42). `cross-ai-dispatch.md`,
      curated-config `runner.md`, the READMEs and the curated-config SKILL.md wording (timeout) match. `ai-kit-cross-ai` reaches
      the judge bar here if Phase 37 did not bring it there. The two closed lists (finding codes; with Phase 37's reason list
      unchanged) are locked by tests; the seed lists carry source labels; the hardcoding guard passes on every file this phase
      rewrites and the runner's self-test baseline entries shrink away.
    - Acceptance: the judge loop for `ai-kit-cross-ai` ends with no critical or high finding or a B or better (recorded in
      38-VERIFICATION.md); doc-contract tests pin the new keys, statuses and the finding list in the SKILL.md; the guard passes;
      `make test` passes.
    - *Amended 2026-11-16 (38 D-25 to D-33, R12):* the SKILL.md, `cross-ai-dispatch.md`, `runner.md` and the READMEs also document
      the hosted-lane rules of R12 (the run record, the lock with a hosted lane, `--sweep` and the automatic sweep, the idle clock
      on the lane's files, the output bound, the secret-file lifetime and what is not guaranteed). The sentence above that lets a
      calling skill "show a long lane in a herdr pane" now reads: the runner itself may host a lane (Phase 37); a calling skill
      that drives herdr by hand stays unchanged and is never read as a liveness or verdict signal.

12. **Run safety for a hosted lane (RUN-13; added 2026-11-16, re-run 2, owner directive "herdr hosting")**: where Phase 37's
    transport hosts a lane in a herdr tab, the lock, the idle clock, the execute checks and the cleanup of secret files work as they
    do for a headless lane, and a run killed hard leaves nothing that a later run cannot clean up by proof.
    - Current: 37 R12 opens a tab per hosted spawn and closes it by id on every exit path the runner controls. R3's lock record
      names a child process group of the runner, R1's idle clock reads pipes, and nothing removes a run directory, a secret file or
      a tab that a runner killed by SIGKILL (or a power loss) leaves behind. 38 D-16 (locked on 2026-11-16 before the directive)
      says herdr is never used inside the runner.
    - Target:
      - **Run record.** Before any other file of a run directory, the runner writes `run.json` (UTF-8 JSON, mode 0600, by temp file
        and rename): version, run token, runner pid, runner start time (read as R3 reads it, `-` when neither source reads), host
        name, checkout root, role, runtime, the label `aikit:<role>:<runtime>:<token>` of 37 R12, the tab id and pane id (null until
        `tab create` answers), the launcher pid and its start time (null until the `pid` file appears) and the creation time. The
        runner rewrites it the same way when `tab create` answers (before the launcher line is typed) and when the launcher pid is
        first read. Order of creation: record, then env file and prompt, then the tab. The record never holds a secret.
      - **Lock with a hosted lane.** The lock key (the checkout root's hash), the pid and the start-time read are unchanged: the
        runner stays a live process while it supervises the hosted lane. A hosted lane's "child group" in the lock record is the
        launcher's process group (live: the launcher is its group's leader, its group id equals its pid, and its parent is the pane
        shell, not the runner), stored with the run token and tab id. A hosted lane is running while that group is alive with the
        recorded start time; the tab's existence, its screen text and its agent status are never an input. R3's stale rule is
        unchanged: a dead runner and a dead launcher group on this host is stale, cleared with the R3 notice, and the same step
        sweeps that run's directory; a dead runner whose launcher group lives is refused as `locked` with the message naming the
        group and the tab id. A refused run opens no run directory and no tab (the lock is taken before the first spawn).
      - **Idle clock on files.** For a hosted lane the activity signal is growth in size of `out` or `err`, polled every 250 ms (a
        poll of the three files measured 0.08 % of one core; 100 ms measured 0.18 %). The launcher's header and herdr's screen are
        never in those files and never count; the runner's own heartbeat lines still do not count; R2's tree and commit reset reads
        the checkout and is unchanged. The idle kill signals the launcher's group (SIGTERM, grace, SIGKILL) only after pid and start
        time still match the record, then closes the tab by id and takes a last read of both files; the attempt line, the status and
        the ladder are R1's (`rule=idle-watchdog`). A launcher gone with no `rc` and no live group is a lane killed by a signal.
      - **Execute checks for a hosted lane** use the same functions on the same inputs: the answer is the captured `out`, the
        verdict is `rc`, and the commits, forbidden-path, admission and baseline reads are against the checkout, never the run
        directory. When the state home (locks, baselines, run directories) lies inside the checkout, the tree snapshot excludes it
        from both the added paths and the ignored-file signature, so a growing `out` is never a tree change, never an
        `outside_plan_files` path and never resets the idle clock. `partial` writes no answer to stdout (R5) and the hosted answer
        is gone with its run directory, as the headless answer is gone with the process.
      - **Output bound.** The launcher opens `out` and `err` in append mode. The runner reads new bytes into the same capture
        buffers and, past twice `CAPTURE_MAX_BYTES` in one file, truncates that file to zero and continues from offset zero, printing
        the headless "kept the newest" line. A hosted lane's disk use stays near two caps per stream and its classification equals
        the headless one. Limit: bytes appended between the last read and the truncation are lost (the headless buffer also keeps
        only the newest bytes).
      - **Secret files.** The launcher sources the env file, opens the prompt on a file descriptor and deletes both as its first
        steps; the runner removes any remainder on every exit path it controls (finish, deadline, signal, spawn error, and the `exit`
        handler); the sweep removes it for a run that was killed hard, with or without herdr. Not guaranteed, and stated in the SKILL:
        a SIGKILL or power loss before the launcher ran leaves the file until the next runner call of any kind (any real run or
        `--sweep`); an unlinked file's blocks are not overwritten; and the lane's own process environment holds the same values as a
        headless lane's does.
      - **Sweep.** At the start of every real run (after validation and before the lock; never for `--print-argv`, `--describe`,
        `--classify-only`, `--self-test`, `--self-test-list` or a usage error) and on demand with `--sweep` (spawns nothing, takes no
        lock, exit 0, a usage error is exit 2), the runner examines only `<state home>/ai-kit/spec/host/<token>/` directories. A run is
        dead when its record reads, its host is this host, its runner pid is gone or has another start time, and its launcher group is
        gone or has another start time. A record under 2 s old that does not read is re-read; an unreadable record older than that is
        left alone and reported with its age, never cleared automatically. For each dead run: claim the directory by a rename to a unique
        name (so two sweeps leave one winner), remove everything in it except `run.json` at once (secrets first), then deal with the
        tab. The sweep calls `herdr tab list` once and closes, by id with `herdr tab close`, only a listed tab whose id and complete
        label both equal the record (a record with a null id matches only a tab whose complete label equals the record's, which holds
        the unique token). A tab that is not listed, or `tab_not_found`, is already gone. Once the tab is gone or closed the record and the
        directory are removed. It never closes a tab of an unreadable or live run, a tab matched by the label prefix alone, or any tab
        it cannot match to a record of this state home. When herdr cannot be reached (no `herdr` on PATH, `HERDR_ENV` not `1`,
        `server_not_running`, a failing call), or when the automatic sweep runs with hosting switched off (`--host none` or
        `AIKIT_HOST=none`), the record is kept and counted; the explicit `--sweep` is the owner's request and ignores the switch (it
        still needs herdr to be reachable). A dead runner whose launcher group lives is reported and left alone (R3's rule); the result
        of a lane whose runner died is not recovered, the baseline record of R4 lets the fix round count its commits. The report
        line `cross-ai: sweep: closed <n> tab(s), removed <m> run director(ies), kept <k> (<reasons>)` prints when n, m or k is not zero
        (always for `--sweep`), with values redacted and control characters removed.
      - **Herdr verbs.** The runner's herdr calls are 37's `tab create`, `pane run` and `tab close`, plus `tab list` in the sweep only,
        read for the id and label match. No call reads a live lane's screen, status or wait output; the existence of a tab is never
        evidence that its lane is alive or done.
    - Acceptance: tests with 37's fake `herdr` on PATH extended with `tab list`, the `tab_not_found` and `server_not_running` error
      shapes recorded live and a second foreign tab: a runner killed by SIGKILL in the middle of a hosted lane leaves a record, and
      the next sweep removes the env file at once, closes exactly the recorded tab by id and removes the directory; a foreign tab, a
      tab with the recorded id but another label and a tab with the recorded label but another id are never closed; with the fake
      down the secrets are gone, the record is kept and counted, and a later sweep with the fake up closes the tab; the automatic
      sweep under `--host none` keeps the record and `--sweep` closes it; a live runner's directory and a dead runner's live launcher
      group are never touched; two sweeps started together leave one winner; an unreadable record is reported and kept; a hosted lane
      that stops writing is ended at the idle time through its group and one that keeps writing is not; a hosted execute lane that
      writes nothing but commits is not ended; a state home inside the checkout does not reset the idle clock or add a changed path;
      a hosted lane with a 3-times-cap `out` leaves a file under the bound and the same status and answer as headless; the launcher
      deletes env and prompt before the lane runs and a planted key shape is in no file after the run; a hosted and a headless run of
      the same fake execute lane give the same findings, status line and exit code; the lock record of a hosted lane names the
      launcher group and `locked` names it; `--describe` lists `--sweep`; the headless path with no herdr is unchanged.
    - *Amended 2026-11-21 (Phase 37 shipped; Live facts added 2026-11-21):* the run record, its order of creation, the launcher's
      deletion of `env` and `prompt`, the append mode and the runner's secret removal on its own exit paths shipped in Phase 37
      (37-19, 37-20, 37-25, review MEDIUM-1 and MEDIUM-6); Phase 38 reads `run.json` with the 15 field names of the protocol fixture
      (including `launcher_pgid`) and renames none. New in Phase 38: `tab list` in `HERDR_VERBS`, the arch rule and the fixture
      together; the fake herdr's `tab list` and the two recorded error shapes; the sweep and `--sweep`; the 2x-cap truncation in
      `hostedChild.readNew`; the idle hook in `hostedChild`; the lock and baseline for a hosted lane. The sweep's "launcher group is
      gone" uses the verified-leader and `groupMembers` rule of the Live facts, against `launcher_pgid`; a record whose
      `launcher_pgid` is null (the launcher never wrote `pid`) has no group to test, so only the runner's liveness decides.

## Boundaries

**In scope:**
- The idle watchdog and the execute progress signals (R1, R2), the run lock and baseline (R3, R4), the plan-versus-commits
  and execute result checks (R5), the Phase 25 cleanup with its corrections (R6 to R10), skill text, docs, closed lists and
  the judge bar (R11).
- *(added 2026-11-16, re-run 2)* The run safety of a lane Phase 37 hosts in a herdr tab: the run record, the lock and idle clock with
  a hosted lane, the output bound, the secret-file lifetime and the sweep with `--sweep` (R12).

**Out of scope:**
- Error classes, stdout limit matching, router cooldown wording and the retry policy (Phase 38.1; `partial` and `locked` are
  runner outcomes, not host error classes).
- Capability blocks, prompt-size refusal against a window, lens skills (39); lane switching, resilient review and routing
  custom lanes through the runner (40); the superpowers adapter's use of locks, baselines, `--plan-id` or a task list (a
  handoff to 41); jev classifying execute results and picking effort, and EXE-08's real-home mtime audit (42).
- Streaming pi activity through `--mode json`, herdr or CPU time as liveness signals, killing for a quiet tree without the
  watchdog, any change to GSD's own native-executor stall check, stopping a human's commit or the pre-commit stash hazard
  (documented only), and an execute check for prompts that carry no task blocks beyond `coverage=n/a`.
- *(added 2026-11-16, re-run 2)* Hosting an interactive agent TUI, a TUI app or an e2e run, and reusing a pane across calls (Phase
  42, which reads the same run record and label, so this sweep also covers what it opens); a lane's usage-limit class and its
  fallback lane (38.1, 40); finding or killing a grandchild that detached with `setsid` (a headless group kill has the same limit,
  stated in the SKILL); recovering the result of a lane whose runner died; and a config key for hosting (37 D-23).

## Constraints

- Runtime code stays stdlib-only (the runner is plain Node with no package; Python modules use the standard library).
- The runner never calls jev, herdr, the network or the catalog; helpers appear only in caller skills, conditional on presence.
  *(amended 2026-11-16, re-run 2, 38 D-16 and D-27: the runner never calls jev, the network or the catalog; it calls the `herdr`
  CLI only through Phase 37's hosting transport and the sweep of R12, with `tab create`, `pane run`, `tab close` and the sweep's
  read-only `tab list`, and learns nothing about a lane from herdr.)*
- Records (lock, baseline) are written atomically with `wx` or a temp file and rename, mode 0600 in a 0700 directory, under the
  state home the quota records already use; tests run in a scratch HOME and state directory with `AI_KIT_REFUSE_REAL_HOME=1`,
  read no `.planning/` path and call no real host (fake CLIs only). A live idle or lock probe on a real host is a spike under
  `tmp/`, never part of `make test`.
- A seed list (admission phrases, forbidden paths, the idle default) carries its source label and never gates a runtime, model
  or setting; the owner replaces it from `CONFIG`.
- The runner prints values only after `redactSecrets` and control-character removal.
- English only; no provider or model name other than `router-env/<x>` in code, defaults, rails, skills, docs or tests.
- A SKILL.md describes behaviour; provenance and version history live in a trailing section. The template version is bumped by
  the plan so pristine project copies upgrade.

## Acceptance Criteria

- [ ] With the watchdog on, a silent fake lane's process group is ended after the idle time with an exit from the existing
      vocabulary, the default does not end a slow, quiet fake, and the self-test has a case for each (R1).
- [ ] An execute fake that prints nothing but commits or edits is not ended, one that changes nothing and prints nothing is,
      and one that prints but changes nothing is reported and not ended (R2).
- [ ] Two execute runs started at once on one checkout leave one running and one `locked`; a stale lock is reported and
      cleared; the lock is gone after every exit (R3).
- [ ] The baseline is recorded, survives a fix round for the same task, is replaced with a finding when HEAD no longer
      descends from it, and never counts an untouched owner edit (R4).
- [ ] An execute fake whose commits miss a task, that exits with no commit, whose report admits skipped work, or whose diff
      touches a forbidden path is `partial` or `contract_violation`, never `ok`; a complete one is `ok` (R5).
- [ ] One router rule serves every caller, `classify-dispatch-failure` prints the quota-cycle fields, the harness lives in a
      sibling file that rendered copies lack with the case list unchanged, and curated-config asks gsd-core for skipped skills
      (R6 to R9).
- [ ] The dead items are gone, the kept helpers stay, and the timeout item is amended and pinned by a test (R10).
- [ ] `ai-kit-cross-ai` meets the judge bar; docs updated; the guard passes; `make test` passes (R11).
- [ ] *(added 2026-11-16, re-run 2)* A runner killed hard in the middle of a hosted lane leaves nothing that the next run or
      `--sweep` cannot clean: the secret files go at once, the recorded tab is closed by id only when its id and label match the
      record of a dead run, no other tab is touched, an unreachable herdr keeps only the secret-free record, and the lock, idle
      clock and execute checks behave for a hosted lane as for a headless one (R12).

## Edge Coverage

**Coverage:** 73/73 applicable edges resolved · 0 unresolved (73 engine rows from `edge_floor.py floor`; the 10 rows marked `(added 2026-11-16, re-run 2)` came with R12 and R11's amendment)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | ✅ covered | An idle time of 1 and of 86400 passes, 0 is off, 86401 and -1 are usage errors; a value equal to the attempt's remaining budget prints the cannot-fire notice; one second under the limit is not ended, the limit is |
| adjacency | R1 | ✅ covered | A byte arriving at the very second of the limit resets the clock before the check (the reset wins the tie); stdout and stderr both count; two attempts never share a clock |
| empty | R1 | ✅ covered | An empty value is a usage error; a lane that prints nothing at all is ended at the idle time like any silent one; no flag and `CONFIG.idleTimeoutS` 0 means off |
| encoding | R1 | ✅ covered | Only byte arrival counts (a split multi-byte character still resets); the flag value is ASCII digits or `default` |
| ordering | R1 | 🧪 backstop | The order of stdout and stderr chunks inside one tick does not matter: any byte resets |
| precision | R1 | ✅ covered | Seconds are whole numbers (`1.5` is a usage error); the check runs at least once a second, so the real silence may pass the limit by up to one check interval, which the SKILL states |
| idempotency | R1 | ✅ covered | Each attempt (retry rung) starts a fresh clock; the watchdog fires at most once per child because finalize settles once |
| concurrency | R1 | ✅ covered | A deadline, attempt cap, live limit match or signal that ends the child first wins; the idle reason never overrides a live quota hit |
| adjacency | R2 | ✅ covered | A change at a check boundary counts at that read; a new commit of already-staged content changes `head` and still resets the clock |
| empty | R2 | ✅ covered | An unborn HEAD polls the tree only; a non-git working directory polls nothing (output-only clock, noted once); no change ever means the R1 rule |
| ordering | R2 | ✅ covered | Each read is compared with the previous read, not with the baseline, so a lane that changed once and stalled is ended one idle time after its last change |
| concurrency | R2 | ✅ covered | At most one read is in flight and a read still running at the next tick is skipped; reads use a private index, so a lane committing at the same moment is never disturbed; a change by anyone counts as progress (documented limit) |
| adjacency | R3 | ✅ covered | Two linked worktrees hold separate locks; a start from a subdirectory resolves to the same root as the top level; a symlinked path resolves by real path |
| empty | R3 | ✅ covered | An empty or unparseable record is re-read for up to 2 s, then refused naming the file and its age; it is never cleared automatically |
| encoding | R3 | ✅ covered | The record is UTF-8 JSON; host and lane strings lose control characters when printed; the root hash covers the real path bytes |
| ordering | R3 | ✅ covered | The lock is taken before the baseline snapshot and released after the end-of-run checks, before the process exits |
| idempotency | R3 | ✅ covered | A clean exit leaves no record, so the next run starts clean; a record whose run id is the current run is never refused |
| concurrency | R3 | ✅ covered | The `wx` create is the atomic step, stale clearing is a rename then a fresh create, and the two-runs-at-once self-test case proves one winner |
| boundary | R4 | ✅ covered | A task record exactly `capS` old is replaced; `--baseline` of 7 hex characters passes, 6 and 65 fail |
| adjacency | R4 | ✅ covered | A HEAD equal to the baseline head counts as descending (zero commits, no replacement) |
| empty | R4 | ✅ covered | An unborn HEAD gives a baseline with no head; an empty `--baseline` value is a usage error; a prompt with no objective block hashes its whole body as `taskDigest` does today |
| encoding | R4 | ✅ covered | Shas and signatures are ASCII; the records are strict UTF-8 JSON |
| ordering | R4 | ✅ covered | `--baseline` wins, then a valid task record, then the fresh snapshot (stored as the task record) |
| precision | R4 | ✅ covered | Times are whole milliseconds compared with `capS` x 1000; an abbreviated `--baseline` is expanded by `git rev-parse` before it is stored and compared in full |
| concurrency | R4 | ✅ covered | Records are written by temp file and rename; two calls for one task are serialized by the R3 lock |
| boundary | R5 | ✅ covered | One task and one covering commit is covered; zero task blocks is `n/a`; a plan-id count equal to the task count passes and one short is `task_uncovered`; at most 10 items print, then `(+N more)` |
| adjacency | R5 | ✅ covered | One commit touching two tasks' files covers both; paths match by whole component (`src/a` never matches `src/ab`); a trailing `/` entry covers its directory |
| empty | R5 | ✅ covered | An empty `<files>` makes a task unchecked; an empty answer stays `empty_answer`; no tasks and no commits give `coverage=n/a findings=-`; an empty `--forbid` value is a usage error |
| encoding | R5 | ✅ covered | Git path lists are read NUL-separated (no quoting) as UTF-8; admission phrases match as lowercase substrings |
| ordering | R5 | ✅ covered | Findings print in the fixed order of the closed list, paths sorted, so the status line list is stable |
| precision | R5 | ✅ covered | Counts are integers printed as `c/p`; there are no ratios or rounding |
| concurrency | R5 | 🧪 backstop | A commit made by a human during the run reads as the lane's (the lock does not stop humans); the SKILL states the limit and a fake case shows the documented effect |
| adjacency | R6 | ✅ covered | An entry whose `fallback_quota` and `is_router` disagree is not confirmed; the matrix test pins it |
| empty | R6 | ✅ covered | An entry with no heuristic fields or no label is not a router (unknown is not router); a missing entry is safe |
| encoding | R6 | 🧪 backstop | Names compare as lowercase ASCII through the existing hint list; no new comparison |
| ordering | R6 | ✅ covered | An owner statement beats an assumed label, and an explicit owner `false` beats an alias assumption |
| boundary | R7 | ✅ covered | `retry_after_s` of 0 passes; a negative, a float or a single token is not a `quota_cycle` (a single token is the owner-stop `quota`) |
| empty | R7 | ✅ covered | A missing, empty or non-dict `status` gives the same classes as today; the printed object always carries the three keys, null when absent |
| encoding | R7 | ✅ covered | Tokens arrive as integers or digit strings and print as integers |
| precision | R7 | ✅ covered | Whole numbers only; a digit string with leading zeros prints as its integer; no float coercion |
| idempotency | R7 | ✅ covered | The classifier is a pure function: the same result on every call |
| concurrency | R7 | ✅ covered | It reads one dispatch result and shares no state; the one-shot re-invoke belongs to the caller (Phase 41) |
| adjacency | R8 | ✅ covered | A symbol missing from both the export list and the harness is a load error; an exported but unused symbol is allowed |
| empty | R8 | ✅ covered | A zero-byte or unreadable sibling fails the dynamic import with the named refusal and exit 2, never a crash |
| encoding | R8 | 🧪 backstop | Both files are UTF-8, LF, no BOM; the byte comparison is on the template, not the harness |
| ordering | R8 | ✅ covered | The case table moves unchanged (golden `--self-test-list`); the sibling loads after the runner module is evaluated, so no cycle at load |
| concurrency | R8 | ✅ covered | Shard modules run in parallel as today, each in its own node process, and the sibling is read-only |
| adjacency | R9 | ✅ covered | An entry gsd-core resolves with a warning but does not skip is not reported as skipped |
| empty | R9 | ✅ covered | No `agent_skills.*` entries means no node call |
| encoding | R9 | 🧪 backstop | The candidate config is handed to node without a shell and the diagnostics are read as UTF-8 |
| ordering | R9 | ✅ covered | Messages join in plan entry order, as today |
| boundary | R10 | ✅ covered | The plan-entry test covers 1799 (raised) and 1800 (kept) |
| adjacency | R10 | ✅ covered | Only the three named dead items go; the kept helpers are listed and a test keeps the cap cases passing |
| empty | R10 | ✅ covered | A config with no timeout shows the 1800 default as the new value with no current value |
| ordering | R10 | 🧪 backstop | The order of the dead-code removal and the harness move is the plan's; the case list stays green after each |
| precision | R10 | ✅ covered | A non-integer or boolean timeout is shown as invalid with its value by the existing `timeout_problem`, never rounded |
| idempotency | R10 | ✅ covered | Applying the same plan twice leaves the same timeout; the second apply shows current equal to new |
| concurrency | R10 | 🧪 backstop | Apply is serialized by curated-config's marker and backup; unchanged here |
| adjacency | R11 | ✅ covered | Each status and each finding has one SKILL.md row and the doc-contract test compares the sets exactly |
| empty | R11 | ✅ covered | A skill with no evals fails the judge bar |
| encoding | R11 | 🧪 backstop | Plain Markdown and test text |
| ordering | R11 | 🧪 backstop | The finding list's order is pinned by the doc-contract test |
| concurrency | R11 | 🧪 backstop | The judge loop runs per skill and shares no state |
| boundary | R11 | ✅ covered | (added 2026-11-16, re-run 2) The doc-contract test compares the SKILL.md's flag, status and finding sets with `--describe` exactly, so `--sweep`, `--idle-timeout`, `--baseline`, `--plan-id` and `--forbid` are each present once and a missing or extra one fails; the 250 ms poll, the 2 s record re-read and the twice-the-cap bound are stated once each with their source labels |
| precision | R11 | 🧪 backstop | (added 2026-11-16, re-run 2) The SKILL states each measured figure (0.08 % of one core at 250 ms, 0.29 s tab close) with its date and as a measurement of one machine, never as a guarantee |
| boundary | R12 | ✅ covered | (added 2026-11-16, re-run 2) A record 1 s old that does not read is re-read and one older than 2 s is reported and kept; a file at exactly twice `CAPTURE_MAX_BYTES` is kept and one byte over is truncated; a poll at 250 ms against an idle time of 60 s cannot make the clock fire early; a tab list of zero tabs closes nothing; a state home exactly equal to the checkout root is excluded like one inside it |
| adjacency | R12 | ✅ covered | (added 2026-11-16, re-run 2) A foreign tab whose label differs from the record by one character, a tab with the recorded id and another label, a tab with the recorded label and another id, and a tab whose label only starts with `aikit:` are never closed; two run directories with adjacent tokens are handled independently |
| empty | R12 | ✅ covered | (added 2026-11-16, re-run 2) An empty state home or no `host/` directory sweeps nothing and prints nothing; a run directory with no `run.json` or an empty one is reported with its age and left alone; a record with a null tab id and no listed tab with its label removes the directory with no close; `tab list` returning no tabs is a clean "already gone" |
| encoding | R12 | ✅ covered | (added 2026-11-16, re-run 2) `run.json` is UTF-8 JSON and the label is ASCII by its grammar, so the comparison is byte equality; a label, host name or path from a record loses control characters and is redacted when printed; the `/proc/<pid>/stat` command name is skipped by parsing after the last `)` so a name holding spaces or parentheses cannot shift the start-time field |
| ordering | R12 | ✅ covered | (added 2026-11-16, re-run 2) The record is written before the env file, the env file before the tab, the tab id into the record before the launcher line is typed, and on cleanup secrets go first, then the tab is closed, then the record and directory are removed; a sweep that dies after the secrets and before the close leaves a record that the next sweep still closes |
| precision | R12 | ✅ covered | (added 2026-11-16, re-run 2) A start time is a whole number of clock ticks on Linux (compared for equality, never as a time) and whole seconds from `ps` elsewhere, where two processes starting in one second could share a value (pid reuse inside one second is the stated residual risk there); sizes and offsets are integers of bytes |
| idempotency | R12 | ✅ covered | (added 2026-11-16, re-run 2) A second sweep over the same state home finds nothing to do; closing a tab already closed (`tab_not_found`) counts as gone, not as an error; `--sweep` twice prints the same report once the first has cleaned |
| concurrency | R12 | ✅ covered | (added 2026-11-16, re-run 2) Two sweeps race for a directory through the rename (one winner, the other skips); a sweep tests deadness before it claims and a dead runner cannot come back, so the directory of a live run is never renamed or touched, including one created after the sweep listed `host/`; a runner starting while another's sweep runs creates its own token, so directories never collide |

## Prohibitions (must-NOT)

**Coverage:** 15/15 applicable prohibitions resolved · 0 unresolved (the 5 rows marked `(added 2026-11-16, re-run 2)` came with R12)

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT let a seed list (idle default, admission phrases, forbidden paths) or any table decide which runtime or model may run, and MUST NOT apply a seed without printing what matched | R1, R5 | resolved | verification: test — a fake lane on a runtime absent from every table meets the same checks, and the matched phrase and path appear in the finding line |
| MUST NOT end a lane because a git read failed or because only the runner's own heartbeat lines were printed | R1, R2 | resolved | verification: test — `git-hang` and `git-after-fail` fakes under the watchdog end nothing, and a silent lane is ended although heartbeats printed |
| MUST NOT touch the user's git index, working tree or refs in a snapshot, lock or baseline step | R2, R3, R4, R5 | resolved | verification: test — the index file is byte-identical after a run, and reads use a private index |
| MUST NOT clear a lock whose runner is dead while its child group lives, one from another host, or an unreadable record | R3 | resolved | verification: test — each of the three refuses with its named message and keeps the file |
| MUST NOT report `ok` or exit 0 for an execute result that has a blocking finding, and MUST NOT write the answer to stdout for `partial` | R5 | resolved | verification: test — each blocking finding ends non-zero with empty stdout, so GSD never writes it as a SUMMARY |
| MUST NOT start a second lane, runtime or model because the watchdog ended a lane or a lock refused a run | R1, R3 | resolved | verification: test — an idle-ended call ends on the same lane through the ladder's own rungs, and a refused run spawns nothing |
| MUST NOT write a record outside the state home or with permissions wider than 0600 (0700 directory), and MUST NOT print a key, token or control character in a lock, finding or idle line | R3, R4, R5 | resolved | verification: test — the modes are asserted and a planted key shape in a lane name, path or phrase comes out redacted |
| MUST NOT call jev, herdr, the network or a real host from the runner or its tests | R1 to R11 | resolved | verification: test — the module tripwire, fake CLIs only, and an arch rule that the template names neither client *(amended 2026-11-16, re-run 2, 38 D-16, D-27: the arch rule says the template names no jev client and calls `herdr` only inside Phase 37's hosting transport and the sweep, with `tab create`, `pane run`, `tab close` and `tab list` and nothing else; tests use the fake `herdr`, never a real one)* |
| MUST NOT read `.planning/` from the new tests | R8 | resolved | verification: test — the existing arch rule that no test reads `.planning/` |
| MUST NOT remove `clampCapS`'s 4-hour bound or `clampAttemptTimeout` while deleting dead code | R10 | resolved | verification: test — the cap and clamp self-test cases still pass |
| MUST NOT close a tab that the sweep cannot match, by id and complete label, to the record of a dead run in this state home, and MUST NOT close, rename or remove anything of a live run *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — a foreign tab, a recorded id with another label, a recorded label with another id, a label-prefix match and a live runner's tab and directory all survive a sweep |
| MUST NOT read herdr's screen text, agent status or wait output, or the mere existence of a tab, as a lane's liveness, its verdict or an input to the lock *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — a fake whose tab list and screen say "alive" while the launcher group is dead gives a stale lock and a cleaned run, and the reverse gives `locked` |
| MUST NOT leave an env file or prompt file behind after a run that the runner controls to its end, and MUST NOT write a key, token or prompt text into `run.json` or the sweep report *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — a planted key shape is in no file of the run directory after the launcher started, after a kill plus a sweep (with the fake up and down) and in no printed line; the cases that are not guaranteed (a kill before the launcher ran, an interval before the next runner call, unlinked blocks) are listed in the SKILL |
| MUST NOT clear an unreadable record, a record of another host or a directory whose launcher group lives, and MUST NOT call herdr from the automatic sweep when hosting is switched off *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — each of the three is reported and kept; a fake `herdr` records no call during an automatic sweep with `--host none` or `AIKIT_HOST=none`, and `--sweep` does call it |
| MUST NOT let hosting change a lane's status, answer, findings or exit code through the output bound, the state-home exclusion or the file polling, and MUST NOT let a hosted lane's output files grow past twice the capture cap *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — hosted and headless runs of the same fakes (success, failure, a 3-times-cap output) give identical results, and the file stays under the bound |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.86  | 0.75 | ✓      | Roadmap goal, four requirements, the 2026-11-16 amendments, the 999.15 evidence and live runner reads |
| Boundary Clarity   | 0.84  | 0.70 | ✓      | Error classes to 38.1, adapter use to 41, jev classification to 42, lane switching to 40 |
| Constraint Clarity | 0.82  | 0.65 | ✓      | stdlib runner, no jev or herdr in it, atomic records, seed lists labeled, redaction |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Each requirement ties to fake-lane self-test cases, table-driven unit tests or doc-contract pins |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      | 1 − (0.35×0.86 + 0.25×0.84 + 0.20×0.82 + 0.20×0.82) |

Open interpretation for the owner (not blocking): the admission-phrase seed and the default forbidden paths are lists that
decide a result (`partial`, `contract_violation`). The 2026-11-16 rule is written for runtimes, models and settings; this SPEC
treats them as policy seeds with source labels and an owner override, never as a runtime gate.

*(added 2026-11-16, re-run 2)* Re-scored after R12: Goal 0.86, Boundary 0.84 (hosting of TUI apps, e2e and pane reuse stays with
Phase 42), Constraint 0.82 ("no jev in the runner; herdr only through the hosting transport and the sweep"), Acceptance 0.82;
ambiguity stays 0.16. Open for the owner (not blocking; provisional answers in 38 CONTEXT, the ledger and the report): the output
bound that truncates a hosted lane's files (a small difference in the file, none in the result), the automatic sweep that stays
away from herdr when hosting is switched off, and the secret-file lifetime that shrinks 37 D-25's exposure.

## Interview Log

Interactive path, one round in the phase subagent; no owner question was unclear enough to relay (the owner answers only
unclear gray areas, 2026-11-16 run mode). The open items went through jev (one advisory answer per item; a low answer is
decided by own reasoning). Summaries only, advisory. Rule: `mvp-mode` inactive, so the best design wins over the smallest
diff.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | What does the runner do today about idle time, a lock, a baseline and plan coverage, and what do GSD and the hosts do? | none; live runs, source reads and the 999.15 evidence | Facts in Background; the findings list (R1 to R10) |
| 1 | Boundary Keeper | Default idle time when the owner turns the watchdog on | laya s1800 low 0.40; typesafe derived low 0.40 | **Own reasoning:** 900 s, labeled judged with its evidence; healthy lanes took 288 to 579 s, observed stalls 1800 s (R1, ledger) |
| 1 | Simplifier | What happens when the watchdog ends a lane | ladder, typesafe 0.95 (laya low 0.42 agrees) | A timed-out attempt entering the existing retry ladder (R1) |
| 1 | Boundary Keeper | Which signals reset an execute lane's idle clock | laya out low 0.48; typesafe out_tree low 0.72 | **Own reasoning:** output plus tree or commit change, as the owner's 2026-11-16 amendment says; CPU time cannot tell a slow answer from a hung one (R2, ledger) |
| 1 | Simplifier | Where the run lock lives | state, typesafe 0.98 (laya tree low 0.46) | A record under the runner's state directory keyed by the checkout root (R3) |
| 1 | Failure Analyst | Result of a second run that finds a live lock | laya e2 0.78; second opinion typesafe e75 0.91 | **jev overridden (first answer):** exit 2 reads as a configuration problem to every caller; new status `locked`, bare exit 75 (R3) |
| 1 | Researcher | How the runner matches tasks against commits | typesafe files 0.99 (laya count low 0.47) | Task files against files in commits since the baseline, plus an optional plan-id subject rule (R5) |
| 1 | Failure Analyst | What a report that admits skipped work does to the result | typesafe with 0.87 (laya note low 0.43); second opinion alone 0.99 | **jev overridden (first answer):** the owner's requirement lists the admission as its own trigger; a strong phrase alone makes `partial` (R5) |
| 1 | Boundary Keeper | What the baseline is in a later fix round | record, typesafe 0.95 (laya low 0.40 agrees) | A per-task record keyed by the objective hash, reused until `ok` or stale or not an ancestor (R4) |
| 1 | Boundary Keeper | Which files an execute result may never touch | orch, typesafe 0.94 (laya none low 0.52) | The three GSD orchestrator-owned files unless the plan names them, plus caller paths (R5) |
| 1 | Boundary Keeper | The one router rule against Phase 35's assumed aliases | laya always low 0.66; typesafe confirmed low 0.62 | **Own reasoning:** a label of user-stated or assumed (alias naming) confirms; a judged hint stays advisory; flagged for the owner (R6, ledger) |
| 1 | Boundary Keeper | What the timeout-restore item becomes now that its code is gone | amend, laya 0.87 | Amend: show before and after in the plan, pin it, drop the restore claim (R10) |
| 1 | Simplifier | Where the self-test harness goes | sibling, typesafe 0.82 (laya low 0.60 agrees) | A sibling file loaded on demand; the render stays a config splice (R8) |
| 1 | Boundary Keeper | The role of herdr and jev | visible, typesafe 0.86 (laya liveness low 0.57) | Only a calling skill, only when present, never a liveness or verdict signal (R11) *(superseded 2026-11-16, round 2: the runner may host a lane through Phase 37's transport; herdr is still never a liveness or verdict signal, R12)* |
| 2 (re-run 2, 2026-11-16) | Failure Analyst | Which facts say a hosted lane is still running when the lock is checked | typesafe runner_plus_launcher_group low 0.50 (laya low 0.48 runner_only) | **Own reasoning:** the launcher's process group with its start time (live: group id equals its pid); a tab is never an input (R12, ledger) |
| 2 | Failure Analyst | A dead runner and dead launcher group but an open tab: what does the lock do | typesafe clear_lock_and_sweep_tab low 0.47 (laya none_of_these low 0.42) | **Own reasoning:** the lock is stale and cleared, the sweep handles the tab (R12, ledger) |
| 2 | Simplifier | When the sweep runs | laya every_run_plus_explicit_flag low 0.27; typesafe none_of_these low 0.52 | **Own reasoning:** at the start of every real run and on demand with `--sweep` (R12, ledger) |
| 2 | Failure Analyst | What proves a tab is the runner's to close | laya none_of_these 0.77 (contradicts the evidence); second opinion typesafe dead_run_record_id_and_label 0.94 | **jev overridden (first answer):** a dead run's record in this state home plus a listed tab whose id and label both match (R12) |
| 2 | Failure Analyst | A dead run's directory when herdr cannot be reached | laya none_of_these low 0.64; typesafe drop_secrets_keep_record low 0.41 | **Own reasoning:** secrets removed at once, the secret-free record kept and counted for a later sweep (R12, ledger) |
| 2 | Boundary Keeper | What the idle clock reads for a hosted lane | typesafe file_size_growth 0.90 (laya none_of_these low 0.52) | Growth of `out` or `err` at a 250 ms poll (R12) |
| 2 | Failure Analyst | How long the env file may exist | typesafe launcher_deletes_at_start low 0.78 (laya low 0.49 until_directory_removed) | **Own reasoning:** the launcher deletes env and prompt as its first steps (checked live); amends 37 D-25's exposure (R12, ledger) |
| 2 | Failure Analyst | Unbounded output files of a hosted lane | laya end_lane_at_ceiling low 0.66; typesafe end_lane_at_ceiling low 0.65 | **Own reasoning, jev not followed:** ending the lane would make hosting change an exit code (37 prohibition); truncate the append-mode file at twice the cap instead (checked live) (R12, ledger, needs owner awareness) |
| 2 | Boundary Keeper | A state home inside the checkout | laya refuse_hosting low 0.31; typesafe exclude_path_from_snapshot low 0.77 | **Own reasoning:** exclude the state home from the snapshot; it also protects the lock and baseline records (R12, ledger) |
| 2 | Boundary Keeper | The automatic sweep when hosting is switched off | laya none_of_these low 0.39; typesafe never_close low 0.48 | **Own reasoning:** files only, records kept; `--sweep` closes tabs on the owner's request (R12, ledger) |

---

*Phase: 38-runner-hardening-and-run-safety*
*Spec created: 2026-11-16*
