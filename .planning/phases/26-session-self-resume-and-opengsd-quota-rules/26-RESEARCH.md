# Phase 26: Session self-resume and OpenGSD quota rules - Research

**Researched:** 2026-10-25
**Domain:** stdlib-only Python CLI (`ai-kit-session-wake`), systemd user timers, Claude Code host internals, AGENTS.md rule catalog
**Confidence:** MEDIUM-HIGH (repo facts and systemd/Claude docs verified; cross-host re-entry for codex and unattended auth are unverified)

Tag legend: `[VERIFIED: x]` = read or ran it this session, with the evidence cited. `[CITED: url]` = official doc fetched this
session. `[ASSUMED]` = inference or training knowledge; goes to the Assumptions Log. `unverified` = no observation was possible.

<user_constraints>
## User Constraints (from CONTEXT.md)

Full text: `26-CONTEXT.md` (decisions D-01..D-37, including the 2026-10-25 spike amendments). Locked headlines, copied verbatim:

### Locked Decisions
- **D-01: A new skill, `skills/ai-kit-session-wake/`** (SKILL.md, shim script, package).
- **D-02: The CLI has six subcommands.** `arm`, `disarm`, `status`, `fire` (timer only), `done` (writes the done marker) and `matrix` (prints R1). `matrix --json` is a public contract for Phase 27.
- **D-03: The wake always resumes the exact recorded session id.** It never uses "continue most recent" and never forks.
- **D-04: Hosts are keyed by runtime labels (`claude`, `codex`, `pi`, `opencode`, `cursor`).**
- **D-05: State lives in `${XDG_STATE_HOME:-~/.local/state}/ai-kit/session-wake/`.** Each session gets `<host>-<id>.json`, `.lock` and `.done`.
- **D-06: Writes use mkstemp + fsync + `os.replace`** (the `stack_cache.write_stack_cache` pattern).
- **D-07: The schema** holds `schema_version`, `host`, `session_id`, `launch_cwd`; `pid`, `pid_start`, `boot_id`; `armed_at`, `wake_count`, `cap` (24); `cli_path`; `permission_mode`, `backend`; `created`; `refs`; plus (D-29) `not_before`, `wake_source`, `reset_evidence`. It never holds environment values. `disarm` removes exactly `created`.
- **D-08: A process counts as alive only when three things match:** the pid exists, its start time matches, and the boot id matches. *(Amended 2026-10-25: the `comm` condition is dropped.)*
- **D-09: The resume runs in the host's launch directory** (`/proc/<pid>/cwd`); `fire` checks that the session exists first.
- **D-10: Each wake runs these steps in order:** (1) no state file: disarm, exit; (2) done marker: disarm; (3) increment `wake_count` atomically; (4) process alive: log to the journal and exit, disarming on the 24th wake; (5) non-blocking `fcntl.flock`, held: exit; (6) run one resume as a child, holding the lock; (7) check the done marker again. Type=oneshot.
- **D-11: Every wake counts toward the cap, including log-only wakes** (refined by D-29: fires before a host-reported reset are logged, not counted).
- **D-12: Units `ai-kit-session-wake-<host>-<id>.timer`/`.service` in `${XDG_CONFIG_HOME:-~/.config}/systemd/user/`;** `OnCalendar=hourly` + `Persistent=true`; session id checked against a safe charset.
- **D-13: `arm` runs `daemon-reload` and `enable --now`; `disarm` cleans up fully** (`disable --now`, `clean --what=state`, delete files, `daemon-reload`); from inside `fire` it never stops its own service; `Environment=` carries only `PATH`, `HOME` and the XDG dirs.
- **D-14: The cron fallback is dropped.** Without systemd: "no surviving primitive" plus the in-session fallback with a warning. Linger via `loginctl show-user $USER -p Linger --value`, fallback `/var/lib/systemd/linger/$USER`.
- **D-15: The resume argv comes from one per-host table** (claude `-p --resume <id> --permission-prompts none`; codex `exec resume <id>`; pi `-p --session-id <id>` (spike 003); opencode `run --session <id>`).
- **D-16: The resume prompt is a code constant, pinned by a test** (read wake state + listed state files; continue only unfinished work; run `ai-kit-session-wake done`; continue pending cross-AI hard-tier waits from their own state, never restart at cycle 0, never switch harness/provider/model; D-36).
- **D-17: The identity check is a separate probe, `ai_kit_rules_common/gsd_identity.py`** (`env`, `search_path`, `run_fn`; returns `ok | unverified | absent`); only the agents skill's `cli.check` calls it; `check_tool_presence` stays PATH-only.
- **D-18: A shared resolver follows upstream's lookup order** (project-local `gsd-core/`, `.claude/gsd-core/`, `.codex/gsd-core/`; host homes; `gsd_run` on PATH); strict `packageName == "@opengsd/gsd-core"`; extends the 16.1 D-18 resolver in `ai_kit_spec/gsd_tools.py`, no second resolver.
- **D-19: When identity is `unverified`, R18 and R19 come out `not_applicable` with `unverified: true` and a reason;** `build_remediation` copies them into `notices`; the rules-all aggregate merges `notices`.
- **D-20: `arm` reports the host's in-session companion and the orchestrator creates it** (one-shot at the known reset + margin, or the OS timer; spike 004).
- **D-21: The permission mode is explicit at `arm`, recorded and printed;** default copies the original session's permission flags (host process command line); `--permission-mode` overrides.
- **D-22: The two new rules are R18 and R19.** Both `workflow`, HIGH, condition `opengsd`, appended after R17. R18 flat signals `session wake`, `self-resume`, `resume by session id`; R19 plain groups; the signal sets share no phrase; "17 rules" strings become 19.
- **D-23: Arming is threshold-based:** `-gsd` arms when the phase has two or more PLAN.md files; `-superpowers` when the plan has two or more tasks; both executors get an explicit end step that writes `done`; executors call only `arm` and `done`.
- **D-24: `arm` refuses inside a subagent or a cross-AI child** (marker detection). *(Contradicted by spike; see Open Question 1 and the Summary: the marker is replaced.)*
- **D-25: An AST rule in `tests/test_arch.py`, with a non-vacuity case,** enforces isolation (the wake package never imports `write_resumable_state` or references Phase 25's wait paths; Phase 25 code never imports the wake package).
- **D-26: Tests run on fakes and scratch directories only** (fake `systemctl`/`loginctl`/host CLIs; scratch HOME/XDG; real `sleep` child liveness; two concurrent `fire` processes; fake `gsd_run`).
- **D-27: R20, the parallel-test CPU-share rule (QTA-06),** `workflow`, appended after R19, NOT gated on `opengsd` (condition: a stack is detected); per-stack form from one table keyed by the `tool_catalog` "test-runner" group; unknown stack gets the generic sentence with an `unverified` flag; a literal core count next to a test command is a finding; every per-stack flag is live-verified at plan time.
- **D-28: A host-reported reset becomes a second `OnCalendar=` entry** (absolute UTC, reset + 60 s) on the same persistent timer; re-running `arm` rewrites the unit; `fire` never rewrites units.
- **D-29: State gains `not_before`, `wake_source` (`hourly` | `reset_inferred`), `reset_evidence`** (verbatim, redacted, capped at 2000 characters); a reset in the past, malformed, or more than 7 days away is refused and the hourly wake stands.
- **D-30: The reset reaches the wake through `arm --reset-at <epoch|ISO>` or `arm --reset-text <text>`;** on Claude Code a `StopFailure` hook row (matcher `rate_limit`) in `HOOK_REGISTRY` calls `arm --reset-text`.
- **D-31: The wake's own notice is sent by `fire`:** journal line always, plus best-effort `notify-send`; fires when the 24-wake cap disarms; never fails `fire`.
- **D-32: Phase 26 notifies only about its own give-up.**
- **D-33/D-34: R19's signal groups come from the policy reference's `## Pointer for instruction files` block and its summary is that pointer verbatim; R19 (and a fixed-block R18) carry `verbatim: true`** and agents SKILL.md Step C inserts verbatim entries unchanged.
- **D-35: The executors call only the wake CLI** (`arm`, `done`), so 25-09's text test stays green.
- **D-36: The fixed resume prompt names hard-tier continuation;** the wake code still passes only the `refs` it was given and never reads Phase 25/25.1 paths.
- **D-37: Phase 26 owns its reset-text parser and fixtures,** labelled inferred.

### Claude's Discretion
- Log line format, the `status` output layout, the exact R18 phrase list beyond the three named.

### Deferred Ideas (OUT OF SCOPE)
- Research questions (does `claude --resume <id>` look up sessions across projects and worktrees; what exactly do `--bg --resume` and `claude agents` do; can a lingering user service read each host's credentials without a login session) - these stay unverified; the spike answered the first (id alone selects the transcript, claude 2.1.310).
- Phase 25's final R19 wording comes from its policy reference, written during Phase 25 execution.
- Out of scope per SPEC: subprocess limit detection/policy (Phase 25/25.1), the goal-prompt skill (Phase 27), cloud routines as a wake, changing any host's own pause-and-continue behavior.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QTA-04 | Orchestrating session sets a self-wake that survives its own quota stall, chosen per host by survival, exact session id, unverified flagged | Q1-Q4 and Q6 below: discriminator, liveness tuple, systemd persistent units, reset parser, skill layout, test tiers |
| QTA-05 | `ai-kit-project-rules-agents` gains OpenGSD-only R18/R19, checked and remediated separately | Q5: rule structure, identity probe, `opengsd` condition and `unverified` notice plumbing, pointer sync test |
| QTA-06 | Language-agnostic parallel-test CPU-share rule (R20) active for every detected stack | Q5: R20 design, verified per-stack flag table, `tool_catalog` gap |
</phase_requirements>

## Summary

The phase is mostly assembly of verified pieces, but four CONTEXT assumptions are wrong or incomplete and the plan must change for them:

1. **`CLAUDE_CODE_CHILD_SESSION` cannot discriminate anything useful.** Claude's own docs say it is set to `1` in every subprocess Claude Code spawns through the Bash, PowerShell and Monitor tools, hooks and status-line commands [CITED: code.claude.com/docs/en/env-vars]. Every `arm` invoked from an agent's Bash tool therefore carries it, main agent or subagent, foreground or background. An in-process subagent is **indistinguishable from the main agent** by env or process tree: this researcher is a subagent, its bash's parent is the process named by `CLAUDE_PID`, and `CLAUDE_CODE_SESSION_ID` equals the main session's [VERIFIED: /proc walk this session; 26-CONTEXT.md code_context]. The harm D-24 fears (a second timer for the wrong host) does not occur for in-process subagents, because `arm` is keyed by (host, session id) and a subagent shares both: its `arm` is the idempotent refresh (R3). It *does* occur for cross-AI children, which are separate processes. The reliable, verifiable discriminator for those is an **ancestor-process scan for the cross-AI runner** (`cross-ai.mjs` in an ancestor's cmdline); the runner scrubs `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT` but not `CLAUDE_PID` or `CLAUDE_CODE_SESSION_ID` and sets no ai-kit marker (`grep -c AI_KIT_` on `cross-ai.mjs` is 0). The residual risk (a subagent calling `done` or `disarm`) is mitigated by SKILL.md text only; state it plainly.
2. **The permission-mode default (D-21) cannot be read from the host command line in a background job.** `CLAUDE_PID`'s cmdline here is `claude bg-spare --bg-spare <sock>` with no permission flags [VERIFIED: /proc/788055/cmdline this session]. Only a foreground launch shows `--dangerously-skip-permissions` (pid 786941's cmdline). Plan: parse flags when present; when absent record `permission_mode: "unknown"`, print it, and resume with the safe default (`--permission-prompts none`, no bypass) unless `--permission-mode` is passed.
3. **`StopFailure` is officially documented** (input fields `error`, `error_details`, `last_assistant_message`; matcher `rate_limit`; observational, output ignored) [CITED: code.claude.com/docs/en/hooks], so D-30 is no longer reverse-engineered-only. What is still unverified: whether the reset text ("resets 1pm (zone)") appears in `error_details` or `last_assistant_message` (the doc examples show `"API Error: Rate limit reached"` and `"429 Too Many Requests"`, not the in-session limit line), and whether `CLAUDE_PID` reaches the hook. The hook must tolerate both and fall back to hourly.
4. **The `test-runner` group in `tool_catalog` is a bare marker list, not a per-stack flag table** [VERIFIED: tool_catalog.py:309-325]; R20 needs a new table added beside it. Also the Makefile/pre-commit test lists are generated by `tools/gen_test_groups.py` (not hand-edited as D-26 says).

**Primary recommendation:** build `skills/ai-kit-session-wake/` as a stdlib package with a pure-function core (state, liveness, reset parser, unit renderer, matrix) and thin subprocess seams (`systemctl`, `loginctl`, host CLI, `notify-send`) injected as callables, exactly like `gsd_tools.py` does; add R18/R19/R20 by extending the shared classification engine (an `opengsd`/`stack-detected` condition and an `unverified` outcome) rather than special-casing in `cli.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Wake state, arm/disarm/fire/done/status/matrix | CLI (`ai-kit-session-wake` package, local) | OS (systemd user manager) | Survives the stalled process; stdlib only |
| Re-fire after process death | OS timer (systemd user, linger) | - | Only primitive that outlives the host (spike 004, SPEC R1) |
| Stall while process alive | Host in-session primitive (one-shot at reset + margin) | OS timer log-only wake | `CronCreate` fires inside a limit are lost (spike 004) |
| Reset time capture | Host hook / agent text | CLI parser (`zoneinfo`) | Runner never parses reset (25.1); wake owns the parser (D-37) |
| Executors arm/done | SKILL.md steps of `-gsd` / `-superpowers` | wake CLI | Executors call only the CLI (D-35) |
| R18/R19/R20 detection | `ai_kit_rules_common` engine + agents skill | `gsd_identity` probe | Shared engine already classifies; identity is a separate probe (D-17) |
| Notice on give-up | `fire` (journal + best-effort `notify-send`) | - | D-31/D-32 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`json`, `os`, `fcntl`, `zoneinfo`, `tempfile`, `subprocess`, `shutil`, `datetime`, `re`) | 3.12 target (3.14.7 on this host) [VERIFIED: `python3 --version`, pyproject.toml pythonVersion] | Whole runtime | AGENTS.md: runtime code stays stdlib-only |
| systemd user manager | 259 (259.9-1.fc44) [VERIFIED: `systemctl --version`] | Persistent timer + oneshot service | The only surviving primitive on this host |
| `unittest` + `tools/run_unittest_parallel.py` | repo | Tests | Repo test runner |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `notify-send` | 0.8.8 [VERIFIED: `notify-send --version`] | Best-effort desktop notice | Only when on PATH and a session bus exists (D-31) |
| `loginctl` | present [VERIFIED: `command -v`] | Linger read | `show-user $USER -p Linger --value` returned `yes` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Persistent unit files (D-12) | Transient `systemd-run --user` | Transient timers write no file in the home and are gone after the run (spike 003, item 10) but do not survive reboot; keep unit files (locked) |
| `tzdata` PyPI package | system `/usr/share/zoneinfo` | `import tzdata` fails here and `/usr/share/zoneinfo/America/Santiago` exists [VERIFIED]; no dependency allowed, so a missing zone must refuse with a reason |

**Installation:** none (no external packages).

## Package Legitimacy Audit

No external package is installed or recommended by this phase (stdlib-only runtime; dev tooling is the existing `uv.lock`). Disposition: nothing to audit. Packages removed (SLOP): none. Flagged (SUS): none.

## Architecture Patterns

### System Architecture Diagram

```
 orchestrator (host session)                         user manager (systemd --user, Linger=yes)
 ---------------------------                         -----------------------------------------
 executor SKILL step --arm--> ai-kit-session-wake arm
   (>=2 plans/tasks)            |  resolve host + session id + host pid (env, else ancestor walk)
                                |  refuse if ancestor cmdline has cross-ai.mjs  (child)
                                |  parse --reset-text/--reset-at (zoneinfo) -> not_before (<=7d)
                                |  write state <host>-<id>.json (mkstemp+fsync+replace) --> $XDG_STATE_HOME/ai-kit/session-wake/
                                |  write .timer/.service  ----------------------------->  $XDG_CONFIG_HOME/systemd/user/
                                '-- systemctl --user daemon-reload; enable --now <timer>
 StopFailure hook (rate_limit) --arm --reset-text--> (re-arm rewrites unit with 2nd OnCalendar)

                                   timer elapses (hourly | reset+60s, Persistent=true)
                                          |
                                   service (Type=oneshot): python3 shim fire --session-id <id>
                                          |
        no state ---> disarm, exit        v
        .done ------> disarm       increment wake_count (counted only if now >= not_before)
        cap(24) hit -> notify + disarm   |
        pid+starttime+boot_id alive? --yes--> journal line, exit  (concurrent resume would be lost, spike 002)
                                          no
                                   flock(.lock, LOCK_NB) --held--> exit
                                          |
                                   session exists? --no--> disarm + notice
                                          |
                                   <host CLI> resume <id> in launch_cwd, stdin=/dev/null, minimal env
                                          |
                                   .done now? --yes--> disarm (never stops own service)
```

### Recommended Project Structure
```
skills/ai-kit-session-wake/
├── SKILL.md                      # frontmatter + when to arm/done/disarm + companion text
├── ai-kit-session-wake.py        # thin shim (sibling sys.path pattern of ai-kit-spec-gsd.py:15)
└── ai_kit_session_wake/
    ├── cli.py            # argparse-free dispatcher, six subcommands (rules-agents cli.py style)
    ├── state.py          # schema, atomic write, flock, path helpers
    ├── liveness.py       # /proc stat parse, boot id, ps fallback, ancestor walk
    ├── matrix.py         # R1 data + ranking + --json contract (source label per row)
    ├── reset_parse.py    # grammar -> aware UTC datetime or refusal reason
    ├── units.py          # render .timer/.service, safe-charset check, linger read
    ├── fire.py           # D-10 sequence, resume argv table, fixed prompt constant, notice
    └── hosts.py          # per-host session-id env var, resume argv, session-exists check
tests/test_ai_kit_session_wake.py (+ split modules as needed)
```

### Pattern 1: Seams as injected callables
**What:** every external effect (`systemctl`, `loginctl`, host CLI, `notify-send`, clock, `/proc` reads) is a parameter with the real default, as `ai_kit_spec/gsd_tools.py` does with `run_fn`/`which_fn`/`isfile_fn` [VERIFIED: gsd_tools.py:113-134].
**When to use:** all modules; tests then need no real systemd (D-26).

### Pattern 2: Rules engine extension, not special-casing
**What:** extend `ai_kit_rules_common.classification` so a condition can resolve to `met | unmet | unverified`. Today `evaluate_condition` returns `bool` and any unknown condition string returns `False` [VERIFIED: classification.py:15-22 `return False` at the end], so a new `opengsd` condition would silently be `not_applicable` with the generic reason and the `unverified: true` flag from D-19 would be lost.
**Example (shape only):**
```python
# classification.py: new outcome, keeps the existing bool path for always/tool-presence
def evaluate_condition(condition, tool_presence):  # presence["opengsd"] in {"ok","unverified","absent"}
    ...
# check_rules: when the condition is unverified -> finding {"status": "not_applicable",
#   "unverified": True, "reason": "..."}; build_remediation copies those into report["notices"].
```

### Anti-Patterns to Avoid
- **Reading `/proc/<pid>/comm` or `exe` for identity:** comm is the version string `2.1.299` and exe points at `.../versions/2.1.299` [VERIFIED], both change on auto-update.
- **`os.getppid()` as the host pid:** it is the shell, not the host (D-08).
- **Counting a fire inside the arm window:** see Pitfall 3.
- **Hand-editing the Makefile/pre-commit test lists:** run `tools/gen_test_groups.py`; `tests/test_gate_scope.py` fails on a stale listing.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic JSON write | custom tmp+rename | `stack_cache.write_stack_cache` pattern (mkstemp+fsync+replace) / `_atomic_write_json` | AGENTS.md rule; `cache_write_json` uses a fixed `.tmp` suffix (D-06) |
| Time zones | offset tables | `zoneinfo.ZoneInfo` | DST and the Santiago zone; refuse when the zone is unknown |
| Cross-process mutual exclusion | pid files | `fcntl.flock(LOCK_EX\|LOCK_NB)` | Kernel releases on crash |
| Persistent scheduling | own daemon loop | systemd `OnCalendar=` + `Persistent=true` | Survives reboot |
| gsd-tools lookup | second resolver | `ai_kit_spec.gsd_tools` (16.1 D-18) | CONTEXT D-18 |
| Stack detection | marker scan | `ai_kit_rules_common.stack_detect.detect_stacks` (go, python, node, java, rust) | Already shared |
| Runtime ids/binaries | new host list | `RUNTIMES` in `ai_kit_spec/detection.py` | AGENTS.md: single source of truth |

**Key insight:** this phase has no hard algorithmic problem; the risk is in unverified host and OS behavior, so every row the CLI shows must carry its source label.

## Research Findings by Question

### Q1. Discriminating subagent / cross-AI child from a main agent (D-24)

Evidence:
- This process (a subagent) sees `CLAUDE_CODE_CHILD_SESSION=1`, `CLAUDE_JOB_DIR` set, `CLAUDE_CODE_SESSION_ATTENDED=0`, `CLAUDE_CODE_AGENT_ID` unset, and `CLAUDE_CODE_SESSION_ID=4f4fa173-...` [VERIFIED: `printenv` this session]. Its bash's parent is pid 788055 = `CLAUDE_PID` (comm `2.1.299`, cmdline `claude bg-spare --bg-spare <sock>`), under `daemon run --origin transient` [VERIFIED: /proc walk]. A main agent's Bash tool has the same parent and the same env; nothing in env or tree separates them.
- The docs: `CLAUDE_CODE_CHILD_SESSION` "Set to `1` in subprocesses Claude Code spawns via the Bash, PowerShell, and Monitor tools, hook commands, and status line commands" [CITED: https://code.claude.com/docs/en/env-vars]. `CLAUDE_PID`, `CLAUDE_JOB_DIR`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_SESSION_ATTENDED` are not documented in the part of the page read (first 100000 of 185449 characters; the rest unread).
- Hook input has `agent_id`/`agent_type` for subagents [CITED: hooks doc, SubagentStart and common fields], but that reaches hooks, not a CLI run from Bash.
- The runner: `cross-ai.mjs` `scrubEnv` is `AI_AGENT, CLAUDECODE, CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_SSE_PORT, CODEX_SANDBOX, CODEX_THREAD_ID, CODEX_VERSION, CURSOR_AGENT, GROK_AGENT, OPENCODE, PI_CODING_AGENT` [VERIFIED: cross-ai.mjs:96-107]. `childEnv` only deletes those keys [VERIFIED: cross-ai.mjs:3638-3642]. It adds no marker: `grep -c "AI_KIT_" cross-ai.mjs` = 0 [VERIFIED]. CONTEXT D-24's "runner marker that Phase 25/18 sets on children" does not exist. A cross-AI child therefore inherits `CLAUDE_PID`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION` from the parent claude (not scrubbed).

Recommendation (replace D-24's marker):
1. `arm` refuses when any ancestor process (walk `/proc/<pid>/stat` ppid chain, read `cmdline`) has `cross-ai.mjs` as an argv element. That is how every runner child is spawned (AGENTS.md: all subprocesses go through the runner template). Linux verified approach; the `ps -o args= -p` fallback on other OSes is unverified.
2. Do not use `CLAUDE_CODE_CHILD_SESSION` at all (document why in SKILL.md and a test comment).
3. In-process subagents: not detectable. `arm` stays idempotent for them (same host + id + pid), and SKILL.md says "only the orchestrator calls arm/done/disarm". State the residual risk (a subagent calling `done` disarms early) in the SKILL.md and Open Question 1.
4. Optional, not required: ask the 25.1 owner to add one `AI_KIT_CROSS_AI_CHILD=1` entry in `childEnv` (additive, cheap). 25.1 is in execution (STATE.md: `status: executing`, `stopped_at: Completed 25.1-15-PLAN.md`), so do not take a dependency on it.

### Q2. Host-process liveness (D-08)

- Linux: pid = `CLAUDE_PID` for claude (live here, 788055). Read `/proc/<pid>/stat`, take the text after the **last** `)`, split, field 22 (`starttime`, clock ticks since boot) is `rest[19]`; here `44143625` [VERIFIED: parsed this session]. Boot id: `/proc/sys/kernel/random/boot_id` (36 chars) [VERIFIED]. Alive iff pid exists and starttime and boot id equal the recorded ones. Do not check `comm`, `exe` or `cmdline` (they change with auto-update and are the version string here). Launch dir: `os.readlink("/proc/<pid>/cwd")` returned the main checkout while the shell was in a worktree [VERIFIED].
- A `(deleted)` suffix or a permission error on `/proc/<pid>/cwd` must degrade to "unknown launch dir": `arm` then records the shell cwd and flags it unverified.
- Portable fallback (no `/proc`): `ps -o lstart= -p <pid>` (works here: `Wed Oct 14 14:07:23 2026` [VERIFIED]) compared as a string, and boot time via `sysctl -n kern.boottime` on macOS; flagged **unverified** (never run on macOS).
- Hosts other than claude: no verified pid env var. `arm` walks ancestors for the first process whose `comm`/`exe` basename or argv contains a `RUNTIMES[host].binaries` name; if none matches it must refuse with a clear message and accept an explicit `--pid`, never guess (label unverified for codex, pi, opencode). In a bg job the host pid is the `bg-spare` process, still the session's real process (the agent's bash is its direct child).

### Q3. OS-timer layer (D-12..D-14)

- Both `OnCalendar=hourly` and `OnCalendar=<ISO UTC>` normalise: `hourly` -> `*-*-* *:00:00`; `2026-10-26 15:30:01 UTC` accepted with "Next elapse" shown [VERIFIED: `systemd-analyze calendar`]. A timer file with two `OnCalendar=` lines, `Persistent=true`, `Unit=` and `[Install] WantedBy=timers.target` passed `systemd-analyze --user verify` with no output [VERIFIED, scratch files outside the repo, since deleted].
- Docs: `OnCalendar=` "May be specified more than once ... the timer unit will trigger whenever any of the specified expressions elapse" [VERIFIED: `man systemd.timer`]; `Persistent=` stores the last trigger time on disk and "the service unit is triggered immediately if it would have been triggered at least once during the time when the timer was inactive"; `systemctl clean --what=state` on the timer removes that timestamp file [VERIFIED: man systemd.timer lines 334-346, man systemctl `clean`]. The stamp files live at `~/.local/share/systemd/timers/stamp-<timer>` [VERIFIED: `ls`]. Record that path class in the printed `arm` output; `disarm` uses `clean --what=state` (the supported route), not a raw delete.
- `Type=oneshot` without `RemainAfterExit=` goes `activating` -> `dead`, never "active" [VERIFIED: man systemd.service]; there is no start timeout by default for oneshot (CONTEXT D-10; not re-read in man this session, treat as documented-by-CONTEXT).
- The user manager's environment has none of the `CLAUDE_*`/`CODEX_*` variables (`systemctl --user show-environment`, names only) [VERIFIED], so the resume child starts clean; `Environment=` carries only `PATH`, `HOME`, XDG dirs (D-13).
- Persistence across reboot: an `enable`d user unit is symlinked into `timers.target.wants` (standard systemd behavior, not exercised this session: **unverified live**). Transient `systemd-run --user` timers leave no file in the home (spike item 10) and are therefore not reboot-safe (inference).
- A running oneshot removing its own unit files: **unverified** (the spike tested transient units only). The design (D-13) never stops its own service: from inside `fire`, run `disable --now` on the **timer** only, `clean --what=state` on the timer, delete both files, `daemon-reload`. Whether `daemon-reload` while the service is `activating` leaves a stale unit is not known. Mitigation: the plan schedules one `checkpoint:human-verify` where uz runs a real arm/fire/disarm of a throwaway session with a unique prefix on this machine (tests must not touch real systemd; the researcher was also barred from creating units).
- First-fire risk: whether a fresh `enable --now` of a `Persistent=true` + `OnCalendar` timer triggers the service immediately is **unverified** (no stamp exists on first start, so likely not, but untested). Pitfall 3 covers the mitigation.
- Linger: `loginctl show-user $USER -p Linger --value` -> `yes` [VERIFIED]; `/var/lib/systemd/linger/$USER` exists (`bazzite`) [VERIFIED: `ls /var/lib/systemd/linger`]. `crontab`, `at` absent [VERIFIED: `command -v` printed only notify-send/loginctl/systemd-run].
- Tests: scratch `XDG_CONFIG_HOME`/`XDG_STATE_HOME`/`HOME`, fake `systemctl` and `loginctl` on a scratch `PATH` (reuse `fake_bin`/`scoped_env`, tests/test_ai_kit_project_rules_agents.py:34-53 [VERIFIED]). Assert the fake logs `--user daemon-reload`, `enable --now <timer>`, `disable --now <timer>`, `clean --what=state <timer>`, argv in that order, and that nothing is ever written outside the scratch tree.

### Q4. Reset-time parser (D-37)

Grammar observed (spike 004 README, quoted): `resets 12:30am (America/Santiago)`, `resets 4:50pm (...)`, `resets 1pm (...)`, `resets 3am (...)` (no date within the day; minutes omitted on the hour), `resets Oct 22, 10pm (America/Santiago)` (date for a later day, weekly limit) [VERIFIED: 004 README]. Weekly line: `You've hit your weekly limit · resets <Mon D>, <time> (<zone>)` [26-SPIKE-REPORT item 3].

Prototype run in this session (logic only, not committed), `now` = 2026-10-25T22:44Z (19:44 in Santiago, UTC-3):
`12:30am -> 2026-10-26T03:30Z`, `1pm -> 2026-10-26T16:00Z`, `3am -> 2026-10-26T06:00Z`, `Oct 22, 10pm -> 2026-10-23T01:00Z` (3 days in the past: refuse), `Jan 3, 9am -> 2027-01-03T12:00Z` (year rolled; 69 days: refuse as >7 d) [VERIFIED: output of the prototype].

Plan:
- Regex anchored on the literal `resets`, optional `Mon D,` (3-letter English month), `H(:MM)?(am|pm)`, and a parenthesised IANA name; decode as UTF-8; the `·` separator is irrelevant.
- No date: next occurrence strictly after now in the named zone (add 1 day if not later). With a date and no year: current year in the named zone; if that is more than ~180 days in the past use the next year (`shortcut:` comment: year heuristic, upgrade if a year ever appears in the text).
- DST: construct with `ZoneInfo`, convert to UTC and round-trip; a nonexistent local time (spring-forward gap) or ambiguous one (fall-back, `fold`) is refused or takes the first occurrence with a flag (decide in plan; both are rare, label inferred).
- Bounds (D-29): after computing the reset `r`: refuse if `r <= now`, malformed, unknown zone (`ZoneInfoNotFoundError`; no `tzdata` package here [VERIFIED]), or `r - now > 7 days` (exactly 7 d accepted, +1 s refused). `not_before = r + 60 s`; written to the unit as `OnCalendar=YYYY-MM-DD HH:MM:SS UTC`.
- QTA-09 flag: `wake_source: "reset_inferred"`, `reset_evidence` = redacted text capped at 2000 code points; `arm` and `status` print the word "inferred" and the sentence "wake time = host-reported reset + 60 s margin; the host did not state this wake time". Everything derived (the +60 s, the year, the date-less day rollover) is inference; only the quoted evidence is observed.
- `--reset-at` accepts epoch seconds or ISO 8601 with an explicit offset/Z; naive ISO is refused.

### Q5. ai-kit-project-rules-agents: R18/R19/R20

Structure [VERIFIED: rules.py read in full]: `RULES` is a tuple of dicts `id, category, criticality, condition, signals, summary`; signals are flat tuples (classified present if all, or >=ceil(n/2) when n>=3, else near_miss/missing), plain groups (R04, tuple of tuples; every group must hit), or tool-scoped groups (R06). `check_rules` filters by non-empty signals, evaluates the condition, and returns only non-present findings unless `include_present`. `CONDITION_ALWAYS = "always"`; conditions are `always` or `tool-presence:<name>`; `check_tool_presence` returns `gsd = os.path.isdir(.planning)` only [VERIFIED: tool_presence.py].

Concrete changes:
- **`opengsd` condition (R18/R19):** `gsd_identity.probe(env, search_path, run_fn)` -> `ok | unverified | absent` (D-17), called only from the agents skill `cli.check`, merged into the presence dict as `presence["opengsd"]`. Live check: `node .claude/gsd-core/bin/gsd-tools.cjs runtime-identity --raw` -> `{"packageName":"@opengsd/gsd-core","version":"1.17.0"}` in 63 ms [VERIFIED] (CONTEXT said 1.16.0 / 78 ms; update the fixtures, do not hardcode the version). Parse strictly: `json.loads`, dict, `packageName == "@opengsd/gsd-core"`; other valid JSON -> `absent`; non-zero exit, no verb, timeout, invalid JSON -> `unverified`. The 3 required test cases (proven, other package, unverified) map to this.
- **Resolver reuse:** `resolve_gsd_tools` lives in `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py` (another skill), while `gsd_identity.py` is to live in `_shared`. `_shared` currently depends on nothing outside itself. Choose one and record it: (a) `gsd_identity` takes the resolved tools path (or candidate list) as an argument and the agents `cli.py` does the sibling `sys.path` import of `ai_kit_spec.gsd_tools` (the pattern `tests/test_sibling_resolution.py` and `ai_kit_gsd_curated_config.model_detect.resolve_ai_kit_spec_path` already use [VERIFIED]); (b) the resolver is imported inside `_shared` via the same sibling trick. Recommend (a): `_shared` stays dependency-free and hermetic. The candidate order is pinned to `edge_floor.engine_candidates` by an existing drift test (gsd_tools.py module docstring), so do not copy the list.
- **`unverified` plumbing:** `check_rules` must emit `{"status": "not_applicable", "unverified": True, "reason": ...}`; `build_remediation` (`ai_kit_rules_common/remediation.py`) today skips every non-missing/near_miss finding, so add a `notices` list; `aggregate.py` merges `remediate`/`blocked`/`failed` only [VERIFIED: aggregate.py:30-60] so add `notices` there. Existing tests assert the dict keys of `build_remediation` (`test_returns_dict_never_bare_list`); additive key `notices` must not break them (check in plan).
- **R18/R19 text:** `workflow`, `CRITICALITY_HIGH`, condition `opengsd`, appended after R17 [VERIFIED: criticality constants]. R18 flat signals `("session wake", "self-resume", "resume by session id")` (3 signals: 2 of 3 = present). R19 plain groups built from the pointer block, which exists now: `## Pointer for instruction files` at subprocess-quota-policy.md:171-180, text `Cross-AI runs go through .planning/scripts/cross-ai.mjs. / The runner owns the soft ladder and the hard tier, and never switches CLI or model. / Read its last AIKIT-XAI line and the ai-kit-cross-ai skill before acting.` [VERIFIED]. Candidate groups: `("cross-ai.mjs",)`, `("never switches", "never switch")`, `("aikit-xai",)`, `("ai-kit-cross-ai",)`. The pointer is still subject to 25.1 R7 (CONTEXT D-33), so derive groups from the file at test time and pin summary == pointer in a repo-only sync test. The R18/R19 signal sets must share no phrase (test).
- **`verbatim: true`:** add the key to the rule dict, carry through `check_rules` finding and `build_remediation` entry; update agents SKILL.md Step C, which currently says summaries are "paraphrased, never the todo/rule text pasted verbatim" [VERIFIED: SKILL.md Step C] - that sentence must be amended for verbatim entries.
- **R20:** condition `stack-detected` (presence key from `detect_stacks(repo_root)` non-empty), `workflow`, appended after R19. The classification needs per-stack clauses, which none of the three signal shapes expresses (tool-scoped groups hard-code the `modern-cli:` presence-key prefix [VERIFIED: classification.py `_classify_tool_scoped_groups`]). Generalise that prefix to a field of the group or add a dedicated `check_stack_clauses`; do not add per-language `if` branches (SPEC R9).
  - Table to add in `tool_catalog.py` beside `OUT_OF_TAXONOMY_GROUPS` (which only lists markers `pytest, unittest, jest, vitest, go test, cargo test, mvn test` [VERIFIED]); a guard test asserts every table runner is in the `test-runner` markers. Stacks from `detect_stacks`: go, python, node, java, rust [VERIFIED].
  - Per-stack forms, live-verified this session:
    - node/jest: `--maxWorkers=40%` (percent form documented) [CITED: jestjs.io/docs/cli]; node/vitest: `--maxWorkers=40%` [CITED: vitest.dev/config/maxworkers].
    - go: `go test -p N` (`go help build`: "-p n ... number of programs ... that can be run in parallel. The default is GOMAXPROCS") and `-parallel n` for `t.Parallel` tests [VERIFIED: `go help build`, `go help testflag`, go1.27.1].
    - rust: `cargo test -- --test-threads=N` [CITED: doc.rust-lang.org/book/ch11-02-running-tests.html]; `RUST_TEST_THREADS` was not on that page (unverified, do not emit it).
    - java/maven: `-T 0.4C` (`mvn -h`: "-T,--threads <arg> Thread count, for instance 4 (int) or 2C/2.5C (int/float) where C is core multiplied") [VERIFIED: `mvn -h`]; surefire `forkCount` per core is unverified.
    - python/pytest-xdist: `-n N` with a computed integer; `-n auto` uses **physical** cores, `--maxprocesses` caps [CITED: pytest-xdist.readthedocs.io]; there is no percent form, so the clause must show a computed count (e.g. floor 40% of `nproc`, at least 1). python/unittest: no stdlib parallel runner; point at the 16.1 D-06 pattern (`tools/run_unittest_parallel.py`, `os.process_cpu_count()`, 40% cap) [VERIFIED: runner header].
  - Hardcoded-count finding: regex a literal integer next to a test command (`-n 12`, `-j 8`, `-p 4`, `--test-threads=8`, `--maxWorkers=4`) while accepting `40%` and a command substitution; boundary 40% passes, 41% flags (SPEC edge). Non-vacuity case for each.
- **String updates** (grep this session): "17 rules/17-rule" appears in `rules.py:1`, `rule_checker.py:9`, `ai-kit-project-rules-agents/SKILL.md:3` and `:10` (twice), `README.md:39` (CONTEXT says :38) and `ai-kit-project-rules-makefile/SKILL.md:17` [VERIFIED: grep]. Historic `.planning/milestones/**` mentions are history, leave them.
- Tests that pin the catalog: `test_ai_kit_project_rules_agents.py` (TestRuleChecker, TestCliCheck line 251-252 asserting `R17` presence/order, TestRemediation, TestGateRegistration), `test_ai_kit_rules_common.py:148-154` (hermetic `check_tool_presence`), `test_ai_kit_project_rules_all.py` (aggregate). Extend, do not replace.

### Q6. Layout, install, test tiers

- Skills are auto-discovered: a skill is any directory with `SKILL.md` (`tools/setup.py` validate_entry, lines ~812-816 [VERIFIED]); no registry edit for claude. `PI_SKILLS = frozenset({"ai-kit-cross-ai", "jev-fast-decision"})` (setup.py:47 [VERIFIED]) mirrors skills into pi; add `ai-kit-session-wake` because pi is a primary host and the AGENTS.md directive must name a discoverable skill; update `tests/test_setup.py` (lines ~1560-1690, 4422) and `tests/test_jev_skill_install_e2e.py:69` expectations that name the pi set.
- Tools config that must list the new package (else gates fail): `pyproject.toml` `[tool.pyright] extraPaths` (add `skills/ai-kit-session-wake`; `include`/vulture already cover `skills`) [VERIFIED: pyproject.toml 95-135]; pre-commit ruff/py-compile `files:` regexes cover `skills/...` generally (the agents test asserts a match for its path; mirror for the new package); pylint covers `skills/` (limits max-args 5, max-branches 12, max-statements 50 shape the module splits above).
- Test groups: `tools/run_unittest_parallel.py` discovers `tests/test_*.py`; a new module joins `unit` automatically. D-26 says "go into the test-unit and lint lists in the Makefile": the lists are **generated** (`# unit: ...` header, `tools/gen_test_groups.py`), so run `python3 tools/gen_test_groups.py` and let `tests/test_gate_scope.py` verify [VERIFIED: gen_test_groups.py header]. Two-process overlap test: real subprocesses with fakes are fine in `unit` (no real systemd, no network). Anything running real `node` against gsd-core goes in `E2E_MODULES` by name.
- Arch rule (D-25): `tests/test_arch.py` today is the status-line suite (module docstring "AST architecture-fitness test for tools/claude-status-line.py", classes `TestArchitecture`, `TestArchNonVacuity`) [VERIFIED]. Add a new class with AST checks (imports and string literals via `ast`, no execution) plus a `TestArchNonVacuity`-style negative case, or a new `ARCH_MODULES` entry; the AGENTS.md rule requires the non-vacuity counterpart.
- Import path: the package reaches `RUNTIMES` through the sibling pattern used by `ai-kit-spec-gsd.py:15` (`sys.path.insert(0, ../ai-kit-spec-review)`) [VERIFIED]; `_shared` is unreachable on copy installs (D-01), so do not put wake logic there.
- Executors: SKILL.md-driven (the orchestrator runs Bash steps); `ai-kit-spec-execute-gsd/SKILL.md` (487 lines) and `-superpowers/SKILL.md` (460 lines) get an `arm` step before the first dispatch (threshold from D-23) and a `done` step at the end. Constraint: 25-09's text test (`tests/test_quota_policy_text.py`, `WAKE_RE = \bhourly\b|every hour|recurring`, `cron_lines`) must stay green, so no such words and no unqualified `CronCreate` in the new executor text [VERIFIED: test_quota_policy_text.py:38-60]. Both SKILL.md files must pass the skill-judge loop (AGENTS.md; memory: judges = clean-context native Opus + the two referee lanes).
- `StopFailure` hook: add `HookRow(id="session-wake", host="claude", event="StopFailure", matcher="rate_limit", script="tools/hooks/claude_session_wake.py", default=..., experimental=True, verdict=None, timeout=...)` to `HOOK_REGISTRY` (tools/setup.py:1765-1815 [VERIFIED row shape]) plus `HOOK_SUMMARIES["session-wake"]`; the hook script is runtime code (stdlib-only) reading stdin JSON (`session_id`, `error`, `error_details`, `last_assistant_message` [CITED: hooks doc]) and calling `arm --reset-text`. Default off until the reset text is observed in a real StopFailure (unverified); `tests/test_hook_registry.py` and `test_hook_registry_e2e.py` pin rows.

### Survival matrix content (R1) with labels

| Host | Primitive | Survives stall (process alive) | Survives process death | Survives reboot | Source |
|------|-----------|-------------------------------|------------------------|-----------------|--------|
| claude | `CronCreate` one-shot at reset+60 s | yes only if scheduled after the reset; a fire inside a limit is lost | no | no | verified (spike 004; docs 7-day expiry observed) |
| claude | `/goal` | pauses, needs a message after reset | no | no | verified (spike 004) |
| claude | systemd user timer + `claude -p --resume <id>` | log only while alive | yes | yes (unverified live; enabled unit file) | re-entry verified (spike 001); reboot unverified |
| pi, opencode | systemd user timer + resume argv | same | yes | unverified | re-entry verified (spike 003) |
| codex | systemd user timer + `codex exec resume <id>` | same | unverified | unverified | help only |
| cursor | none known | - | - | - | unverified; row says "no surviving primitive" |
| any | cloud routine | - | cannot re-enter a local session | - | inference from docs (SPEC) |

## Common Pitfalls

### Pitfall 1: Trusting `CLAUDE_CODE_CHILD_SESSION`
**What goes wrong:** `arm` refuses in every Bash-tool call. **Why:** the documented marker means "spawned by Claude Code", not "subagent". **Avoid:** Q1's ancestor scan; test that `arm` succeeds with the marker set and fails under a fake `cross-ai.mjs` ancestor. **Warning sign:** `arm` never works in a real run.

### Pitfall 2: Identity from `comm`
**What goes wrong:** liveness says "dead" for a live host (comm `2.1.299`) so `fire` starts a concurrent resume whose turn is silently lost (spike 002). **Avoid:** pid + starttime + boot id only; test with a `sleep` child whose comm is arbitrary.

### Pitfall 3: A fire inside the arm window burns a wake
**What goes wrong:** `Persistent=true` can trigger the service at enable time (unverified), consuming one of 24. **Avoid:** do not count a fire within a small window after `armed_at` (log it); label as inference; cover with a test using a fake clock. Also `OnCalendar=hourly` lands on the hour, so cap exhaustion takes about 24 h of continuous stall.

### Pitfall 4: Permission mode default
**What goes wrong:** resuming with bypass because the original was launched with it, or silently dropping it. **Avoid:** parse the foreground cmdline when present, record `unknown` for bg hosts, never enable bypass implicitly (Summary point 2).

### Pitfall 5: Resuming a session id that does not exist
pi and opencode create a missing session for an unknown id (their `--help`, spike 003), so `fire` must check existence first. claude: transcript at `~/.claude/projects/<launch dir with / replaced by ->/<id>.jsonl`; this session's file exists at that path [VERIFIED: `ls`]. Because the id alone selects the transcript on 2.1.310 (spike 001), glob `projects/*/<id>.jsonl` under `CLAUDE_CONFIG_DIR` or `~/.claude`; layout is reverse-engineered, flag it. Existence checks for codex/pi/opencode are unverified: refuse to resume if the check cannot be made.

### Pitfall 6: `-p` waits on stdin
Spike 001: without `< /dev/null`, `-p` waits 3 s for stdin and warns. Always `stdin=subprocess.DEVNULL`.

### Pitfall 7: Unit-name injection
Session ids go into unit names and `ExecStart`; validate `^[A-Za-z0-9_-]{1,128}$` (UUIDs pass), reject everything else, and never build commands through a shell (AGENTS.md arch: no `shell=True`; `check_no_shell_true` in test_arch.py [VERIFIED name]).

### Pitfall 8: Timer accuracy
`AccuracySec=` default is 1 min (D-28 cites it; not re-read in `man` this session beyond the OnCalendar passage), so the reset+60 s margin can still fire ~1 min late; fine, and the cap logic is `now >= not_before`.

## Code Examples

### Liveness (field 22 after the last `)`), verified shape
```python
# Source: run this session against CLAUDE_PID; stdlib only
def read_start_ticks(pid, proc="/proc"):
    stat = open(f"{proc}/{pid}/stat").read()
    return int(stat[stat.rindex(")") + 2:].split()[19])  # field 22
```

### Unit rendering (verified accepted by `systemd-analyze --user verify`)
```ini
# ai-kit-session-wake-<host>-<id>.timer
[Unit]
Description=ai-kit session wake (<host> <id>)
[Timer]
OnCalendar=hourly
OnCalendar=2026-10-26 15:30:01 UTC
Persistent=true
Unit=ai-kit-session-wake-<host>-<id>.service
[Install]
WantedBy=timers.target
```
Service: `Type=oneshot`, absolute `ExecStart=<python3> <shim> fire --session-id <id>`, `Environment=` limited to PATH/HOME/XDG (D-13; the service body was verified only as `ExecStart=/usr/bin/true` in a verify run).

### Resume argv table (spike-labelled)
```python
RESUME = {  # (argv builder) -> label
  "claude": ["-p", "--resume", "{id}", "--permission-prompts", "none"],   # verified 2.1.310 (spike 001/--help)
  "pi": ["-p", "--session-id", "{id}"],                                    # verified (spike 003), pi 1.3.0
  "opencode": ["run", "--session", "{id}"],                                # verified (spike 003), 2.0.31
  "codex": ["exec", "resume", "{id}"],                                     # help only: unverified
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hourly in-session `CronCreate` as the stall wake | One-shot at reset+60 s, or OS timer | spike 004, 2026-10-25 | A fire inside the limit is lost |
| `StopFailure` known from binary strings | Documented hook with `error`/`error_details`/`last_assistant_message` | observed on docs this session | D-30's "unverified" narrows to the reset text content |
| D-24 marker detection | Runner-ancestor scan | this research | See Q1 |

**Deprecated/outdated:** cron fallback (dropped, D-14); `Persistent=true` with `OnUnitActiveSec=` (no effect, D-12).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | An enabled user unit file survives reboot via `timers.target.wants` | Q3 | Wake lost after reboot; needs the human-verify checkpoint |
| A2 | A fresh `enable --now` of a `Persistent=true`+`OnCalendar` timer does not fire immediately | Q3 / Pitfall 3 | One wake counted early (mitigated by the arm-window rule) |
| A3 | Removing unit files from inside the running oneshot (timer disabled, service not stopped) is safe | Q3 | Orphaned or killed resume; human-verify |
| A4 | `StopFailure` hook receives `CLAUDE_PID` and the reset text appears in `error_details`/`last_assistant_message` for subscription limits | Q5 / Summary 3 | Hook cannot arm with a reset; hourly stands |
| A5 | A cross-AI child's ancestor chain always contains `cross-ai.mjs` | Q1 | Child could arm; add the optional env marker |
| A6 | `ps -o lstart=` and `sysctl kern.boottime` give a stable start/boot identity off Linux | Q2 | Liveness wrong on macOS; flagged unverified |
| A7 | pi, opencode, codex hosts: ancestor walk by binary name finds the host process | Q2 | `arm` refuses; user passes `--pid` |
| A8 | Date-less "resets 3am" always means the next such time (< 24 h) | Q4 | Off by a day only if the host prints a past time |
| A9 | The DST gap/fold handling choice (refuse vs first occurrence) | Q4 | Wake an hour off, inferred |
| A10 | Claude transcript path layout `projects/<encoded cwd>/<id>.jsonl` and that `--permission-prompts none` prevents every hang | Pitfall 5 / Q5 | Resume starts a fresh session or hangs; `fire` must fail closed |
| A11 | `nproc`-based shell form for the pytest clause is acceptable for the rule text | Q5 R20 | Non-Linux projects get a form that does not run |

## Open Questions (RESOLVED)

1. **Subagent safety of `done`/`disarm`.**
   - **RESOLVED (CONTEXT D-24, 2026-10-25): SKILL.md forbids `done`/`disarm` from a subagent; a subagent `arm` is an idempotent refresh; residual risk stated.**
   - Known: in-process subagents are indistinguishable by env or process tree; `arm` is idempotent for them.
   - Unclear: whether a subagent can be stopped from calling `done`.
   - Recommendation: SKILL.md prohibition + test of idempotent `arm`; accept the residual risk; optionally ask for a hook-based `agent_id` guard later (backlog).
2. **Does the StopFailure payload carry the reset text?** Unverified. Recommendation: ship the hook `default=False`, `experimental=True`; on first real capture, record the payload (redacted) in a follow-up.
   - **RESOLVED (plan 26-07): the StopFailure hook ships opt-in and experimental; the payload capture is an owner item in 26-12.**
3. **Persistent-unit behavior (reboot, first fire, self-removal).** Unverified. Recommendation: one `checkpoint:human-verify` in the plan for uz to run a throwaway arm/fire/disarm and reboot check; do not block plan creation.
   - **RESOLVED (CONTEXT D-26, 2026-10-25): fake-backed tests plus an owner capture under human_verification; no blocking checkpoint.**
4. **Which `gsd_identity` import shape (Q5 option a vs b)?** Recommend (a); plan confirms.
   - **RESOLVED (plan 26-08): option (a).**
5. **PI_SKILLS addition and the optional `AI_KIT_CROSS_AI_CHILD` marker** need owner confirmation (the latter touches 25.1 code in execution).
   - **RESOLVED (CONTEXT D-24 and D-26, 2026-10-25): `PI_SKILLS` gains the skill (owner confirmation staged in 26-12); the runner sets `AI_KIT_CROSS_AI_CHILD` (plan 26-01).**
6. **Permission default for background hosts.** Recommendation above (record `unknown`, never bypass); needs uz's confirmation since D-21's earlier resolution assumed the cmdline is readable.
   - **RESOLVED (CONTEXT D-21, 2026-10-25; plan 26-04): record `unknown`, never bypass; owner confirmation staged in 26-12.**

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| systemd user manager | OS timer | yes | 259 | none: report "no surviving primitive" (D-14) |
| `systemd-analyze` | unit verification in tests/planning | yes | 259 | skip verify test |
| `loginctl` | linger | yes (Linger=yes) | - | `/var/lib/systemd/linger/$USER` |
| `notify-send` | notice | yes | 0.8.8 | journal line only |
| `python3` | runtime | yes | 3.14.7 (target 3.12) | - |
| `node` + project-local gsd-core | identity probe, e2e | yes | gsd-core 1.17.0 | fake `gsd_run` in tests |
| `claude` | resume | yes | 2.1.310 | - |
| `cron`/`crontab`/`at` | none (dropped) | no | - | n/a |
| `go`, `mvn` | R20 flag verification | yes | go1.27.1; mvn `-h` ok | - |

**Missing dependencies with no fallback:** none for planning. Reboot and real-unit behavior need a human step (Open Question 3).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest`, one subprocess per module via `tools/run_unittest_parallel.py` |
| Config file | none; groups in `tools/run_unittest_parallel.py`, listings generated by `tools/gen_test_groups.py` |
| Quick run command | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_session_wake tests.test_ai_kit_project_rules_agents tests.test_ai_kit_rules_common` |
| Full suite command | `make test` (and `make validate` for lint/type gates) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QTA-04 | matrix: every row has a source label; no-primitive host reports so; rank order pinned | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_session_wake` | Wave 0 |
| QTA-04 | arm: missing/empty id fails; twice = one state, one timer pair; atomic write; sentinel secret absent from state and units | unit | same | Wave 0 |
| QTA-04 | liveness: live `sleep` child alive; missing pid dead; mismatched starttime dead; mismatched boot id dead | unit | same | Wave 0 |
| QTA-04 | fire: alive = log only; gone = one resume of the recorded id (two sessions in one dir); two concurrent `fire` = one resume; done marker; 24th wake disarms, no 25th | unit (real subprocesses, fakes) | same | Wave 0 |
| QTA-04 | disarm: three triggers each remove exactly `created`; nothing armed = success; order disable -> clean -> delete -> reload (fake systemctl log) | unit | same | Wave 0 |
| QTA-04 | reset parser: grammar fixtures from spike 004, rollover, 7 d boundary (exact ok, +1 s refused), past refused, unknown zone refused, 2000-code-point cap, "inferred" printed | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_session_wake_reset` | Wave 0 |
| QTA-04 | arm refuses under a fake `cross-ai.mjs` ancestor, succeeds with `CLAUDE_CODE_CHILD_SESSION=1` | unit | session-wake module | Wave 0 |
| QTA-04 | isolation AST rule + non-vacuity (wake pkg vs Phase 25 paths) | arch | `python3 tools/run_unittest_parallel.py --group arch` | extend `tests/test_arch.py` |
| QTA-04 | executors: arm threshold (2 plans/tasks), done step, text test stays green | unit | `python3 tools/run_unittest_parallel.py tests.test_quota_policy_text tests.test_ai_kit_spec_gsd tests.test_ai_kit_spec_superpowers` | exist; extend |
| QTA-04 | PI_SKILLS / hook row / install | unit | `... tests.test_setup tests.test_hook_registry` | exist; extend |
| QTA-05 | opengsd/other package/unverified/no AGENTS.md; one directive present, other missing; notices reach remediate and aggregate; R19 summary equals pointer; signal sets disjoint; non-vacuity each | unit | `... tests.test_ai_kit_project_rules_agents tests.test_ai_kit_rules_common tests.test_ai_kit_project_rules_all` | exist; extend |
| QTA-06 | python/node/go/rust fixtures, multi-stack one clause each in `detect_stacks` order, no stack = not applicable, hardcoded count flagged, 40% passes/41% flags, unknown stack = generic + unverified, table markers subset of test-runner | unit | same | exist; extend |
| all | listings not stale; skill-judge evidence committed | unit/manual | `python3 tools/run_unittest_parallel.py tests.test_gate_scope`; `/skill-judge` | exist |

### Sampling Rate
- **Per task commit:** the quick command for the touched modules.
- **Per wave merge:** `make test-unit` plus `make arch-test`.
- **Phase gate:** `make test` and `make validate` green before `/gsd-verify-work`; for UI none; real behavior check from the branch (memory: ship each phase to the machine) including the human-verify unit checkpoint.

### Wave 0 Gaps
- [ ] `tests/test_ai_kit_session_wake.py` (+ `..._reset.py`) - covers QTA-04
- [ ] fake `systemctl`/`loginctl`/host-CLI fixtures (reuse `fake_bin`/`scoped_env` shape)
- [ ] `tests/test_arch.py` new rule class + non-vacuity
- [ ] `skills/_shared/ai_kit_rules_common/gsd_identity.py` with `ok|unverified|absent` fixtures (fake `run_fn`, sentinel secret)
- [ ] R18-R20 fixtures (python, node, go, rust, multi-stack, none) in the agents test
- [ ] `pyproject.toml` pyright `extraPaths`; run `tools/gen_test_groups.py`

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (resumed CLI uses its own auth; unattended auth after reboot is unverified) | none stored |
| V3 Session Management | partly (session ids are identifiers, not credentials) | exact-id resume, charset check |
| V4 Access Control | yes | writes only to ai-kit-prefixed unit files and the state dir, all printed and removed |
| V5 Input Validation | yes | session id charset, reset text regex + bounds, `--reset-at` strictness |
| V6 Cryptography | no | none |
| V8/V12 Data and Files | yes | atomic writes (mkstemp, fsync, replace), 0600 state files, no env values stored, evidence redacted and capped |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unit-file or argv injection via session id or reset text | Tampering | allowlist charset, no shell, argv lists |
| Secrets in unit files/state/journal (env dump) | Information disclosure | `Environment=` limited to PATH/HOME/XDG; sentinel-key test; redact evidence |
| Resume replaying a bypass permission mode | Elevation of privilege | explicit, recorded, printed mode; never implicit bypass; `--permission-prompts none` |
| Stale/foreign pid taken as the host | Spoofing | pid + starttime + boot id |
| Runaway wake | Denial of service | hard cap 24, 7-day reset bound, done marker |
| Executor/test touching real configs | Tampering | scratch HOME/XDG; `AI_KIT_REFUSE_REAL_HOME=1` in cross-AI executor runs (memory) |

## Project Constraints (from CLAUDE.md / AGENTS.md)

Directives that bind the plan (AGENTS.md is the project file; `./CLAUDE.md` was not separately read, and the global CLAUDE.md only adds tool-usage hints):
- English only in every written artifact; stdlib-only runtime code; atomic config writes; no more certainty than sourced; labels for reverse-engineered or unverified behavior.
- Any new or changed `SKILL.md` passes the skill-judge loop (no Critical/Important finding or score >= 96/120).
- One coherent, buildable commit per logical change with tests and docs; never `--no-verify`; no real config files as fixtures; no hardcoded absolute paths in source, tests, assets or generated commands (plan commands must be path-agnostic).
- Tests: `make test` aggregate; one subprocess per module through `tools/run_unittest_parallel.py`; worker count = floor(40% of CPUs), never hardcoded; non-vacuity counterpart for every structural rule; kill any process spawned for verification.
- Update README and nested docs after feature changes (README.md:39 count and new skill row); scratch files under `./tmp/`; keep commits and docs concise.
- Do not run `gsd update` or any global GSD install; use project-local `.claude/gsd-core`.
- Cross-AI executors: export `AI_KIT_REFUSE_REAL_HOME=1` and audit real-config mtimes after runs (memory).

## Sources

### Primary (HIGH confidence)
- Repo files read this session: 26-CONTEXT.md, 26-SPEC.md, 26-SPIKE-REPORT.md, spikes/004 README, `rules.py`, `classification.py`, `remediation.py`, `stack_detect.py`, `tool_presence.py`, `tool_catalog.py` (test-runner group), `cli.py` (agents), `aggregate.py`, `gsd_tools.py`, `detection.py`, `cross-ai.mjs` (scrubEnv, childEnv), `run_unittest_parallel.py`, `gen_test_groups.py`, `tools/setup.py` (PI_SKILLS, HOOK_REGISTRY), `pyproject.toml`, `subprocess-quota-policy.md`, `test_quota_policy_text.py`.
- Live commands: `/proc` walk and `printenv` (names; values only for non-secret markers), `systemctl --version`, `loginctl show-user`, `systemd-analyze calendar` and `verify`, `man systemd.timer/systemctl/systemd.service`, `claude --version/--help` (2.1.310), `node .claude/gsd-core/bin/gsd-tools.cjs runtime-identity --raw`, `go help build/testflag`, `mvn -h`.
- Official docs: https://code.claude.com/docs/en/env-vars (CHILD_SESSION), https://code.claude.com/docs/en/hooks (StopFailure, agent_id).

### Secondary (MEDIUM confidence)
- https://jestjs.io/docs/cli, https://vitest.dev/config/maxworkers, https://pytest-xdist.readthedocs.io/en/stable/distribution.html, https://doc.rust-lang.org/book/ch11-02-running-tests.html.

### Tertiary (LOW confidence)
- Binary-string observation of `CLAUDE_CODE_CHILD_SESSION` lists in the 2.1.310 binary (consistent with the docs; no further reliance).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib plus verified systemd 259.
- Architecture: MEDIUM-HIGH - seams proven by existing modules; persistent-unit lifecycle unverified.
- Pitfalls: MEDIUM - several are from unverified host behavior (listed in the Assumptions Log).

**Research date:** 2026-10-25
**Valid until:** 2026-11-08 (Claude Code and pi/opencode versions move fast; re-check `claude --help` flags and the StopFailure doc before planning if later)
