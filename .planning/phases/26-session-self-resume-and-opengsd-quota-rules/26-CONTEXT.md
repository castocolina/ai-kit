# Phase 26: Session self-resume and OpenGSD quota rules - Context

**Gathered:** 2026-10-14 (assumptions mode, `--analyze --all --batch`, jev screening, best over easy)
**Status:** Ready for the spike (SPEC R2), then planning

<domain>
## Phase Boundary

This phase covers two mechanisms.

- **Session wake.** An orchestrating session that stalls on its own quota is brought back by a
  wake that survives the stall: a systemd user timer that resumes the exact session id once the
  original process is gone.
- **AGENTS.md rules.** OpenGSD projects get two separately checked rules: R18 (session resume)
  and R19 (subprocess quota, worded from Phase 25's policy reference).

The WHAT is locked in `26-SPEC.md` (R1–R8, amended 2026-10-14 by this file); this file locks the
HOW. The spike runs before `/gsd-plan-phase 26`. Several decisions below name what the spike
must confirm.
</domain>

<decisions>
## Implementation Decisions

### Where the wake lives
- **D-01: A new skill, `skills/ai-kit-session-wake/`** (SKILL.md, shim script, package).
  - It has four callers:
    - the two executors;
    - an AGENTS.md directive in any OpenGSD project, which must name a discoverable skill;
    - Phase 27's prompt;
    - the user's manual `disarm`.
  - The executors import it with the same sibling `sys.path` pattern they already use
    (`ai-kit-spec-gsd.py:15`).
  - `_shared/` is unreachable on copy installs.
  - **Own reasoning** (Laya shared_lib 0.52 (fb), TypeSafe module_in_existing 0.55 (fb)): a
    module inside `ai-kit-spec-review` would send other projects' agents to a skill named for
    review. Ledger.
- **D-02: The CLI has six subcommands.** `arm`, `disarm`, `status`, `fire` (timer only),
  `done` (writes the done marker) and `matrix` (prints R1).
  - Run inside `fire`'s child, `disarm` falls back to writing the marker instead of waiting on
    its own parent's lock.
  - Laya no_wait_flag 0.43 (fb), TypeSafe done_command 0.94.
- **D-03: The wake always resumes the exact recorded session id.** It never uses "continue
  most recent" and never forks (SPEC R3). Settled at spec time; restated because ROADMAP and
  QTA-04 were amended to match.
- **D-04: Hosts are keyed by runtime labels (`claude`, `codex`, `pi`, `opencode`, `cursor`).**
  These are the labels of `detect_current_runtime` and `_VALID_NATIVE_RUNTIME`
  (`config_io.py:100`). `KNOWN_CLIS` lacks `pi` (`detection.py:20`). SPEC R1 amended.
  Analyzer: Confident.

### Wake state
- **D-05: State lives in `${XDG_STATE_HOME:-~/.local/state}/ai-kit/session-wake/`.**
  - Each session gets `<host>-<id>.json`, `.lock` and `.done`.
  - Phase 25's waits live in the cache directory, so "never share state" holds by path.
  - Cache directories are disposable, and lost state makes the next wake disarm silently.
  - Laya same_cache 0.38 (fb), TypeSafe xdg_state 0.78.
- **D-06: Writes use mkstemp + fsync + `os.replace`** (the `stack_cache.write_stack_cache`
  pattern), never `cache_write_json`'s fixed `.tmp` suffix. Analyzer: Confident.
- **D-07: The schema** holds:
  - `schema_version`, `host`, `session_id`, `launch_cwd`;
  - `pid`, `pid_start`, `boot_id`;
  - `armed_at`, `wake_count`, `cap` (24);
  - `cli_path` (the `which` result, symlinks not resolved, so auto-updates keep working);
  - `permission_mode` (D-21), `backend`;
  - `created`, the exact list of paths `arm` wrote;
  - `refs`, read-only pointers to the executor's or Phase 25's state.

  It never holds environment values. `disarm` removes exactly `created`.
  - **Laya overridden** (derive 0.89): deriving the list by naming convention can miss the
    wants-symlink and the stamp file, or delete files it did not create. TypeSafe second
    opinion record_list 0.98.

### Liveness and resume directory
- **D-08: A process counts as alive only when three things match:** the pid exists, its start
  time matches, and the boot id matches.
  - On Linux these come from `/proc/<pid>/stat` field 22 (parsed after the last `)`) and
    `/proc/sys/kernel/random/boot_id`.
  - Elsewhere the check falls back to `ps -o lstart=`, flagged unverified.
  - The pid comes from the host's env var where one is verified: `CLAUDE_PID`, live, whose
    `comm` is `claude`. Otherwise an ancestor walk finds the host binary, flagged unverified.
    The shell's own `os.getppid()` is never used.
  - Laya proc_bootid 0.52 (fb), TypeSafe proc_bootid 0.98. Laya env_then_walk 0.58 (fb),
    TypeSafe env_then_walk 0.95.
- **D-09: The resume runs in the host's launch directory** (`/proc/<pid>/cwd`). In this session
  that is the main checkout, while the shell is in a worktree, and the transcript is keyed by
  the launch directory. Before resuming, `fire` checks that the session exists, because pi and
  opencode create a missing one. SPEC R3 amended. **The spike confirms this.**

### Firing
- **D-10: Each wake runs these steps in order:**
  1. If the state file is missing, disarm and exit.
  2. If the done marker exists, disarm.
  3. Increment `wake_count` atomically.
  4. If the process is alive, log to the journal (stdout) and exit, disarming on the 24th wake.
  5. Take a non-blocking `fcntl.flock`; if it is held, exit.
  6. Run one resume as a child, holding the lock.
  7. Check the done marker again.

  The unit is `Type=oneshot`, so it has no start timeout.
- **D-11: Every wake counts toward the cap, including log-only wakes.** SPEC R5 and its MUST NOT
  require a hard stop at 24. Counting only resumes would loop forever while a stalled terminal
  stays open.
  - **Own reasoning** (Laya count_all 0.53 (fb), TypeSafe count_resumes 0.79): TypeSafe's
    choice contradicts the locked MUST NOT. Ledger.

### The OS timer
- **D-12: The units are `ai-kit-session-wake-<host>-<id>.timer` and `.service`, in
  `${XDG_CONFIG_HOME:-~/.config}/systemd/user/`.**
  - The timer uses `OnCalendar=hourly` with `Persistent=true`. `Persistent` only works with
    `OnCalendar=` (`man systemd.timer`, systemd 259); this machine's
    `llm-env-omniroute-heal.timer` uses the combination that has no effect.
  - Tests get a scratch unit directory through `XDG_CONFIG_HOME`.
  - The session id is checked against a safe character set before it enters a unit name.
  - Analyzer: Confident.
- **D-13: `arm` runs `daemon-reload` and `enable --now`; `disarm` cleans up fully.**
  - `disarm` runs `disable --now`, then `clean --what=state` (the persistent stamp), deletes the
    files, and runs `daemon-reload`.
  - From inside `fire`, `disarm` never stops its own service.
  - `ExecStart` uses absolute paths (the python3 that ran `arm`, the shim,
    `fire --session-id <id>`).
  - `Environment=` carries only `PATH` (per-shell entries such as `fnm_multishells` are
    filtered out), `HOME` and the XDG directories. It never dumps the environment. A sentinel
    key test guards this.
  - Laya enable_full_cleanup 0.82.
- **D-14: The cron fallback is dropped.** It would edit the user's crontab, which the write
  constraint forbids, and there is no cron here to verify against. Without systemd the wake
  reports "no surviving primitive" and falls back to the in-session primitive with a warning.
  Linger is read with `loginctl show-user $USER -p Linger --value`, falling back to
  `/var/lib/systemd/linger/$USER`; with linger off, `arm` warns. SPEC R6 amended. Laya
  amend_marked_line 0.48 (fb), TypeSafe drop_cron 0.88.

### Resume command, companion, permission mode
- **D-15: The resume argv comes from one per-host table, every row unverified until the spike.**

  | Host | Resume argv |
  |---|---|
  | claude | `-p --resume <id> --permission-prompts none` |
  | codex | `exec resume <id>` |
  | pi | `-p --session <recorded session file>` |
  | opencode | `run --session <id>` |

  The default is the headless one-shot resume. The spike also measures `claude --bg --resume
  <id>`, which "starts a copy … when the session is already running", together with `claude
  agents`, and may switch claude to it. Laya background_only 0.64 (fb), TypeSafe
  spike_decides_headless_default 0.90.
- **D-16: The resume prompt is a code constant, pinned by a test.** Only the state path is
  filled in. The prompt tells the agent to:
  - read the wake state and the state files it lists, including Phase 25's pending waits;
  - continue only unfinished work;
  - run `ai-kit-session-wake done` when nothing remains.

  The resumed agent re-runs `arm`, which refreshes the pid (the R3 idempotency row).
- **D-20: `arm` reports the host's in-session companion and the orchestrator creates it.** On
  Claude Code the companion is a one-shot `CronCreate`/`ScheduleWakeup` chain, or `/goal`. It
  covers a stall while the process is alive, which the OS timer only logs. **The spike
  (item 4) confirms** whether a fire during a usage limit runs later.
  - **Own reasoning** (Laya arm_reports_companion 0.40 (fb), TypeSafe document_gap 0.92):
    documenting the gap leaves a live, stalled session idle for 24 hours, and the design rule
    says best over easy. Ledger.
- **D-21: The permission mode is explicit at `arm`, recorded, and printed.** The resume never
  silently replays a bypass mode. **Deferred to uz:** the default value. One option is to
  copy the original session's flags (this session was launched with permission checks
  bypassed, read from `/proc` cmdline). The other is to require an explicit mode. TypeSafe
  explicit_at_arm 0.81 locks the explicit-and-printed part; the default is a safety call for
  uz and does not block the spike.

### The rules skill
- **D-17: The identity check is a separate probe, `ai_kit_rules_common/gsd_identity.py`.**
  It takes `env`, `search_path` and `run_fn`, and returns `ok | unverified | absent`. Only the
  agents skill's `cli.check` calls it and merges the result into the presence data.
  `check_tool_presence` stays PATH-only and hermetic (`test_ai_kit_rules_common.py:148-154`).
  There is no cache: the probe takes 78 ms.
  - **Laya overridden** (extend_shared 0.70 (fb)): TypeSafe separate_probe 0.95.
- **D-18: A new shared resolver follows upstream's lookup order** (`discuss-phase.md:118`):
  1. project-local `gsd-core/`, `.claude/gsd-core/`, `.codex/gsd-core/`;
  2. the host homes;
  3. `gsd_run` on PATH, never a bare `gsd-tools`.

  It strictly parses `packageName == "@opengsd/gsd-core"` with a short timeout.
  `gsd_catalog.resolve_gsd_tools_path`'s drifted 16-home list moves onto it. Laya
  new_shared_upstream 0.69 (fb), TypeSafe new_shared_upstream 1.00.
- **D-19: When identity is `unverified`, R18 and R19 come out `not_applicable` with
  `unverified: true` and a reason.** `build_remediation` copies them into `notices`, and the
  rules-all aggregate merges `notices`. Valid identity JSON naming another package is "not
  OpenGSD". An original-GSD install without the verb is indistinguishable from unverified
  (`runtime-identity.cjs`). SPEC R7 amended.
  - **Own reasoning** (Laya check_only 0.95; TypeSafe second opinion flag_through 0.68 (fb)):
    the remediation and aggregate outputs are what users see, and both drop `not_applicable`
    today. Ledger.
- **D-22: The two new rules are R18 and R19.** Both are `workflow`, criticality HIGH, condition
  `opengsd`, appended after R17.
  - R18 uses flat signals: `session wake`, `self-resume`, `resume by session id`.
  - R19 uses plain groups, one per policy clause: subprocess quota, 10-minute, 4-hour,
    route-aware.
  - The two signal sets share no phrase. "unfinished work", "quota" and "hourly" are not
    signals. A test pins all of this.
  - R19's summary quotes Phase 25 D-23's policy reference.
  - The "17 rules" strings become 19: the `rules.py` docstring, `rule_checker.py`, the agents
    SKILL.md, `README.md:38` and `ai-kit-project-rules-makefile/SKILL.md:17`.
  - **Laya overridden** (flat 0.88): a flat list counts half the clauses as present. TypeSafe
    second opinion groups 0.94.

### Executors
- **D-23: Arming is threshold-based, and both executors get an explicit end step that writes
  `done`.**
  - `-gsd` arms before `Skill(gsd-execute-phase)` when the phase has two or more PLAN.md
    files.
  - `-superpowers` arms when the plan has two or more tasks.
  - SPEC R8 amended.
  - **Laya overridden** (always 0.79): it contradicts the locked edge "a single-plan run arms
    nothing". TypeSafe second opinion per_framework_units 0.87.
- **D-24: `arm` refuses inside a subagent or a cross-AI child**, detected through environment
  markers: `CLAUDE_CODE_CHILD_SESSION`, plus a runner marker that Phase 25/18 sets on children.
  **The spike confirms** the marker is unset in the main agent.
  - **Laya overridden** (instructions_only 0.84): an inherited environment makes a child arm a
    second timer for the wrong host. TypeSafe second opinion refuse_markers 0.97.
- **D-25: An AST rule in `tests/test_arch.py`, with a non-vacuity case, enforces the isolation:**
  - the session-wake package never imports `write_resumable_state` or references Phase 25's
    wait paths;
  - Phase 25's code never imports the session-wake package.

  Laya ast_rule 0.74.

### Tests
- **D-26: Tests run on fakes and scratch directories only.**
  - Fake `systemctl`, `loginctl` and fake host CLIs on a scratch PATH append their argv, cwd
    and env-var names to a log.
  - A scratch HOME, `XDG_CONFIG_HOME` and `XDG_STATE_HOME` hold every file.
  - Liveness is tested with a real `sleep` child, a missing pid and a mismatched start time.
  - Overlap is tested with two concurrent `fire` processes.
  - R7 is tested with a fake `gsd_run` and `run_fn`, plus a sentinel secret.
  - No test touches real systemd.
  - New modules go into the `test-unit` and `lint` lists in the Makefile.

### Claude's Discretion
- Log line format, the `status` output layout, the exact R18 phrase list beyond the three
  named.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/26-session-self-resume-and-opengsd-quota-rules/26-SPEC.md` — locked WHAT
- `.planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-CONTEXT.md` — D-16 (in-session one-shot chain), D-23 (policy reference R19 quotes), D-24 (coupling)
- `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py` — R01–R17 shapes (R04 groups)
- `skills/_shared/ai_kit_rules_common/{classification,tool_presence,remediation,stack_cache}.py`
- `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/aggregate.py:51` — drops not_applicable
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py` — drifted resolver
- `~/.claude/gsd-core/workflows/discuss-phase.md:118` and `bin/lib/runtime-identity.cjs` — upstream resolver and identity (read-only)
</canonical_refs>

<code_context>
## Existing Code Insights

- `detect_current_runtime` and its nesting order (codex wins when nested), relevant to D-24.
- `fake_bin`/`scoped_env` helpers in `tests/test_ai_kit_project_rules_agents.py:34-53`.
- Live: `CLAUDE_PID`'s `comm` is `claude`. A subagent's `CLAUDE_CODE_SESSION_ID` equals the main
  session's id.
</code_context>

<specifics>
## Specific Ideas

The spike must measure:
1. whether `claude -p --resume <id>` from a systemd user service appends to the same
   transcript, from the launch directory and from a worktree;
2. what happens while the original process is alive, for both `-p` and `--bg`;
3. the exit code and output while the quota is still exhausted;
4. whether an in-session `CronCreate` that fires during a limit runs later, and whether `/goal`
   resumes on its own;
5. permission-mode inheritance, and whether `--permission-prompts none` prevents hangs;
6. auth after a reboot with linger on and no login session;
7. whether `CLAUDE_CODE_CHILD_SESSION` is unset in the main agent;
8. codex `CODEX_THREAD_ID`, cwd filtering and limit exit;
9. whether pi and opencode session env vars are exposed, and whether they create a missing
   session;
10. whether a fresh enable fires immediately, and whether a running oneshot can safely remove
    its own unit;
11. the CLI version for every finding.
</specifics>

<deferred>
## Deferred Ideas

- **For uz:** the default permission mode for an unattended resume (D-21).
- Research questions:
  - Does `claude --resume <id>` look up sessions across projects and worktrees?
  - What exactly do `--bg --resume` and `claude agents` do?
  - Can a lingering user service read each host's credentials without a login session?
- Phase 25's final R19 wording comes from its policy reference, which is written during Phase
  25 execution.
</deferred>
