# Phase 26: Session self-resume and OpenGSD quota rules — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

An orchestrating agent session that stalls on its own quota resumes by itself. The wake that
brings it back is chosen by what survives the stall: an OS timer outlives the process, while
in-session primitives die with it. OpenGSD projects get both quota directives in their AGENTS.md
as two separately checked rules. The first is session resume (this phase); the second is
subprocess quota (Phase 25).

## Background

- **Source:** todo `2026-10-14-agents-md-quota-schedule-rules-and-goal-prompt-skill.md`, part 1:
  mechanism A (the main agent's own quota) and the rules-skill rule. uz's clarification says
  mechanism A and mechanism B (subprocess quota, Phase 25) must never be conflated.
- **Live facts on this machine (2026-10-14):**
  - Claude Code 2.1.299 has `--resume <session-id>`, `-c/--continue` (most recent conversation
    in the directory), `--fork-session` and `-p/--print`. The session id is available in the
    session's environment as `CLAUDE_CODE_SESSION_ID`;
  - codex-cli 0.162.1 has `codex exec resume <id>` or `--last`; pi has `--session-id <id>`,
    `--session` and `-c`; opencode `run` has `--session/-s <id>` and `-c`. Only the flags were
    checked in `--help`; headless behavior from a timer is **unverified** for all four;
  - systemd user manager running, `Linger=yes`; no `crontab`, no `at`.
- **Primitive survival (Claude Code official docs, via the todo's research):**
  - `CronCreate`: session-scoped, recurring tasks expire after 7 days, restored on `--resume`,
    no catch-up;
  - `ScheduleWakeup` / `/loop`: 1 min to 1 h, not restored on resume;
  - `/goal`: a rate or usage limit pauses it and it continues after the reset; auth failure,
    exhausted credits or an unavailable model clear it;
  - routines (`RemoteTrigger`, `/schedule`): cloud-run, 1 h minimum. They run in the cloud, so
    they cannot re-enter a local session (inference from the docs, flagged).

  So a quota stall with the process alive can be survived in-session. Process death (terminal
  closed, crash, reboot) needs an OS timer.
- **`--continue` is unsafe as a wake target.** Several sessions share one directory here
  (parallel sessions, worktrees), so "most recent" can pick the wrong one.
- **Current code:**
  - `ai-kit-spec-execute-superpowers` schedules an hourly `CronCreate` wake only for
    subprocess quota (Phase 25 R8 replaces that). Nothing arms a wake for the session's own
    quota;
  - `ai-kit-project-rules-agents` has 17 rules (R01–R17). Rule conditions are `always` or
    `tool-presence:<name>`, where `gsd` means only that `.planning/` exists. That check cannot
    tell OpenGSD from the original GSD;
  - `gsd-tools.cjs runtime-identity --raw` prints
    `{"packageName":"@opengsd/gsd-core","version":"1.16.0"}`.

## Requirements

1. **Survival matrix** (QTA-04).
   - Current: none.
   - Target: a per-host table of wake primitives. Each row records:
     - whether it survives a quota stall while the process lives;
     - whether it survives process death;
     - whether it survives a reboot;
     - its source, `verified` (live or official docs) or `unverified`.

     Hosts: Claude Code, codex, pi, opencode and the OS timers (systemd user timer, cron, at).
     The wake picks the strongest primitive the host has; unverified rows are shown as
     unverified.
   - Acceptance: the matrix is data with a test that every row has a source label; a host with
     no surviving primitive reports that instead of claiming one.
   - *Amended 2026-10-14 (26 D-04):* hosts are keyed by runtime labels (`claude`, `codex`, `pi`, `opencode`, `cursor`, the native-runtime vocabulary), not `KNOWN_CLIS`, which has no `pi`. The OS-timer rows are systemd only (D-14).

2. **Spike before planning** (QTA-04).
   - Current: the headless re-entry behavior is untested.
   - Target: a `/gsd-spike` runs in a scratch directory. It records five things:
     - whether `claude -p --resume <id>` started from a systemd user timer re-enters the
       recorded session in its directory;
     - what it does while the original process is alive;
     - what exit and message it gives while the quota is still exhausted;
     - whether an in-session `CronCreate` that fires during a usage limit runs later or is lost;
     - the same re-entry facts for `codex exec resume`, `pi --session-id` and
       `opencode run --session`, where a free or cheap model is reachable.

     Its findings set R1's labels and amend this SPEC where a fact contradicts it.
   - Acceptance: a committed spike report. Each R1 row's label points to a spike finding or to
     an official doc.

3. **Arm by session id** (QTA-04).
   - Current: none.
   - Target: `arm` writes a wake-state file outside the working tree. It holds the host, the
     exact session id, the working directory, the original process id, the arm time, the wake
     count and the cap. The wake resumes that id only. It never uses "continue most recent" and
     never forks.
   - Acceptance: a test with two sessions in one directory resumes the recorded one; arming
     without a session id fails with a clear message.
   - *Amended 2026-10-14 (26 D-08, D-09):* "working directory" is the host process's launch directory (from `/proc/<pid>/cwd`), not the shell's: the transcript is keyed by it. Because pi `--session-id` and opencode `--session` create a missing session, the wake checks that the session exists before resuming.

4. **Layered firing** (QTA-04).
   - Current: none.
   - Target: on each wake:
     - if the original process is alive, the wake only logs. The in-session primitive (or the
       host's own pause-and-continue) owns the resume;
     - if it is gone, the wake starts one headless resume of the recorded session. The resume
       prompt is fixed: read the wake-state file and the session's own state files, then
       continue only unfinished work.

     A lock prevents two resumes at once.
   - Acceptance: tests for an alive process (log only), a gone process (one resume), and two
     overlapping wakes (one resume).

5. **Disarm** (QTA-04).
   - Current: none.
   - Target: the wake disarms itself on any of three events:
     - the agent writes a done marker;
     - the user runs `disarm`;
     - the hard cap is reached (24 wakes).

     Disarming removes every file and timer that `arm` created. The wake never runs forever.
   - Acceptance: tests for each of the three triggers; after disarm, no ai-kit timer or unit
     file remains.

6. **OS timer** (QTA-04).
   - Current: none.
   - Target: on Linux with systemd, `arm` writes persistent user unit files: an hourly timer
     with `Persistent=true` and its service. They are named with an ai-kit prefix and the
     session id, `arm` prints exactly what it wrote, and `disarm` removes them. With lingering
     off, it warns that the wake stops at logout. Hosts without systemd use cron when present.
     Otherwise they report "no surviving primitive" and fall back to the in-session primitive
     with a visible warning (launchd and Windows are unverified).
   - Acceptance: tests against a scratch unit directory and a fake `systemctl` on `PATH`; the
     user's real systemd directory is never touched in tests.
   - *Amended 2026-10-14 (26 D-12..D-14):* the timer uses `OnCalendar=hourly` (`Persistent=true` has no effect with `OnUnitActiveSec=`, `man systemd.timer`); `arm` enables it, and `disarm` also removes the wants-symlink and the persistent stamp (`clean --what=state`). The cron fallback is dropped: it would edit the user's crontab, which the write constraint forbids. Without systemd the wake reports "no surviving primitive" and falls back to the in-session primitive with a warning.

7. **Two mechanisms, two rules** (QTA-05).
   - Current: no OpenGSD-only rule.
   - Target: `ai-kit-project-rules-agents` gains two rules under a new `opengsd` condition:
     - session resume: the main agent arms the hourly session wake per R3–R6;
     - subprocess quota: cross-AI child limits follow Phase 25's policy (10-minute re-checks,
       a 4-hour cap, the route-aware classes, resuming only unfinished work).

     Each rule is checked and remediated on its own. The condition is true only when `.planning/`
     exists and `gsd-tools runtime-identity` proves `@opengsd/gsd-core`. When the identity
     cannot be proven, both rules are skipped with an unverified notice.
   - *Amended 2026-10-14 (26 D-17..D-19):* the identity tool is found in upstream's order (project-local installs, then host homes, then `gsd_run` on `PATH`; never a bare `gsd-tools`). An original-GSD install without the identity verb is indistinguishable from "unverified", so the test cases are: proven OpenGSD; valid identity JSON naming another package (not OpenGSD); no identity (unverified, skipped). The unverified notice reaches the remediation and aggregate outputs.
   - Acceptance: tests for an OpenGSD project, an original-GSD project, a project with no GSD
     tool on `PATH`, and AGENTS.md text that has one directive and lacks the other. Each rule
     gets a non-vacuity case.

8. **Executors arm the session wake** (QTA-04).
   - Current: the execute skills only wake for subprocess quota.
   - Target: `ai-kit-spec-execute-gsd` and `-superpowers` arm the session wake at the start of
     a multi-plan run and disarm it at the end. The session wake and Phase 25's re-checks keep
     separate state files. The session wake never re-dispatches a cross-AI child itself; after
     a resume, the orchestrator does that from Phase 25's state. Each touched SKILL.md passes
     `/skill-judge`.
   - Acceptance: tests show arm and disarm around a run. No code path writes the other
     mechanism's state file. Skill-judge evidence is committed.
   - *Amended 2026-10-14 (26 D-23):* "multi-plan" means two or more work units: PLAN.md files for `-gsd`, tasks for `-superpowers` (which always runs one plan).

9. **Parallel tests capped at a CPU share** (QTA-06). *Added 2026-10-14 by uz.*
   - Current: no rule; ai-kit's own runner is fixed in 16.1 D-06, but projects get no such rule.
   - Target: `ai-kit-project-rules-agents` gains a rule that is active whenever `detect_stacks`
     finds a stack. AGENTS.md must state that unit tests run in parallel, that the worker count
     is a share of the available CPUs capped at 40% (never a hardcoded core or worker count), and
     the stack's own form of it. For example: `pytest -n` with a computed count, `go test -p`,
     jest/vitest `--maxWorkers=40%`, `cargo test -- --test-threads`, Maven `-T` per core, and the
     stdlib unittest runner pattern from 16.1 D-06. Remediation writes the form for each detected
     stack into the rules section. Each stack's form comes from one table keyed by the shared
     `tool_catalog` test-runner group, never from code branches per language. A stack without a
     known form gets the generic sentence and an `unverified` flag.
   - Acceptance: tests for a python, a node, a go and a rust fixture, a multi-stack repo (one
     clause per stack), a repo with no stack (rule not applicable), and AGENTS.md text that
     hardcodes a core count (flagged). Each case has a non-vacuity counterpart.

## Boundaries

**In scope:**
- The survival matrix, the spike, the wake-state file and `arm`/`disarm`, layered firing, the OS
  timer
- The two OpenGSD rules and the executor wiring

**Out of scope:**
- Subprocess limit detection, classes and re-check policy (Phase 25)
- The goal-prompt skill (Phase 27)
- Changing any host's own pause-and-continue behavior (upstream)
- Cloud routines as a wake for local sessions (they cannot re-enter one)

## Constraints

- Runtime code stays stdlib-only.
- Unit files and the wake-state file carry no key or token. The resumed CLI uses its own normal
  auth.
- Writes outside the repository are limited to ai-kit-prefixed unit files and ai-kit's own state
  directory. All of them are printed on arm and removed on disarm.
- Unverified host behavior is labelled as such everywhere it is shown.

## Acceptance Criteria

- [ ] Every survival-matrix row carries a source label; unverified rows are shown as unverified
- [ ] The spike report is committed and R1's labels point to it or to official docs
- [ ] The wake resumes the recorded session id, never "most recent"
- [ ] Alive process: log only; gone process: one headless resume; overlap: one resume
- [ ] Done marker, `disarm` and the 24-wake cap each disarm and remove every created file
- [ ] systemd unit files are written with an ai-kit prefix, printed, and removed on disarm
- [ ] The two OpenGSD rules are checked and remediated separately; original GSD and unproven
  identity skip them
- [ ] Executors arm and disarm the session wake; the two mechanisms never share state
- [ ] Touched SKILL.md files pass `/skill-judge`
- [ ] `make test` and `make validate` are green
- [ ] MUST NOT: the wake never runs past its cap or after a done marker
- [ ] MUST NOT: two resumes of one session never run at once

## Edge Coverage

**Coverage:** 37/37 applicable edges resolved · 0 unresolved (floor recomputed 2026-10-14 after the R1/R3/R6/R7/R8 amendments)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | A primitive that survives a stall but not process death is its own survival class, never merged with the stronger one |
| empty | R1 | ✅ covered | A host with no row, or with no surviving primitive, reports "no surviving primitive" |
| encoding | R1 | 🧪 backstop | ~~Hosts are keyed by `KNOWN_CLIS` names, never by display text~~ *(superseded, D-04)* Hosts are keyed by runtime labels, never by display text |
| ordering | R1 | ✅ covered | Primitives rank by survival (reboot > process death > stall only); equal rank keeps table order, pinned by a test |
| boundary | R2 | ✅ covered | A spike step that cannot run (no free model reachable) records `unverified`, never a guess |
| adjacency | R2 | ✅ covered | A spike finding that contradicts this SPEC amends it before planning |
| empty | R2 | ✅ covered | A host whose CLI is not installed keeps every row `unverified` |
| encoding | R2 | 🧪 backstop | The spike report quotes messages only; no token or key is recorded |
| ordering | R2 | 🧪 backstop | The spike runs before `/gsd-plan-phase 26` |
| precision | R2 | ✅ covered | Each finding names the CLI version it was observed on |
| boundary | R3 | ✅ covered | Arming twice for the same session id updates the one state file; it never creates a second timer |
| empty | R3 | ✅ covered | An empty or missing session id fails `arm` with a clear message |
| encoding | R3 | ✅ covered | The session id is used verbatim and validated against a safe charset before it enters a unit-file name |
| precision | R3 | ✅ covered | The state file records the exact id, never a prefix or "most recent" |
| concurrency | R3 | ✅ covered | The wake-state file is written atomically (mkstemp + replace) |
| idempotency | R3 | ✅ covered | Re-arming the same session (for example from the resumed agent) refreshes the recorded process id and keeps the wake count (added after the 2026-10-14 amendment) |
| adjacency | R4 | ✅ covered | A recorded process id reused by an unrelated process does not count as alive (the start time is checked too) |
| empty | R4 | ✅ covered | A missing wake-state file at fire time disarms the timer and exits |
| ordering | R4 | 🧪 backstop | Each wake checks done marker, cap, liveness, then the lock, in that order |
| concurrency | R4 | ✅ covered | A lock file makes a second overlapping wake exit without resuming |
| boundary | R5 | ✅ covered | The 24th wake runs and then disarms; there is no 25th |
| adjacency | R5 | ✅ covered | A done marker written during a resume disarms at the next wake |
| empty | R5 | ✅ covered | `disarm` with nothing armed succeeds and reports nothing removed |
| ordering | R5 | 🧪 backstop | Disarm stops the timer before removing unit and state files |
| precision | R5 | ✅ covered | The wake count lives in the state file, not in the timer's own counters |
| concurrency | R5 | ✅ covered | `disarm` during a running resume waits for the lock, then removes everything |
| concurrency | R6 | ✅ covered | Two armed sessions get two distinctly named timers that never touch each other |
| boundary | R7 | ✅ covered | A `.planning/` with no provable identity skips both rules with an unverified notice that reaches remediation and aggregate output |
| adjacency | R7 | ✅ covered | AGENTS.md with only one directive yields one present and one missing rule, never a merged result |
| empty | R7 | ✅ covered | No AGENTS.md: both rules are missing (when the condition holds) |
| encoding | R7 | 🧪 backstop | Signals match the same lowercase phrase heuristic as R01–R17 |
| ordering | R7 | 🧪 backstop | The two new rules follow R17 in catalog order |
| precision | R7 | ✅ covered | The identity check accepts only `packageName == "@opengsd/gsd-core"`, never a substring |
| adjacency | R8 | ✅ covered | A run that arms a session wake and also hits a subprocess limit keeps both state files separate |
| empty | R8 | ✅ covered | A single-plan run arms no session wake |
| ordering | R8 | 🧪 backstop | Arm happens before the first dispatch; disarm after the final summary |
| concurrency | R8 | 🧪 backstop | Only the orchestrator arms or disarms; subagents never do |

## Prohibitions (must-NOT)

**Coverage:** 4/4 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT run past the 24-wake cap or after a done marker | R5 | resolved | test |
| MUST NOT start two resumes of one session at once | R4 | resolved | test (lock) |
| MUST NOT resume by "most recent" or fork | R3 | resolved | test (two sessions in one directory) |
| MUST NOT write a key or token into a unit file or the wake-state file | R3, R6 | resolved | test (sentinel key absent) |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | One wake, chosen by survival; two rules |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | Subprocess policy is Phase 25; prompts are Phase 27 |
| Constraint Clarity | 0.82  | 0.65 | ✓      | Writes outside the repo are prefixed, printed, removed |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 12 pass/fail criteria; spike findings may amend R1 |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      | Initial 0.27; one round |

## Interview Log

`--auto`, one round. The open items went through `ai-kit-gsd-spec-discuss`'s ladder (`decide.py`: Laya per item, `needs_fallback` to TypeSafe). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Failure Analyst | How does the timer address the session? | continue_most_recent 0.55 (fb) | resume_by_id 0.98 | Exact session id; never "most recent" (R3) |
| 1 | Researcher | Original process alive or gone at wake time? | in_session_only 0.38 (fb) | layered 0.99 | Alive: log only; gone: one headless resume (R4) |
| 1 | Boundary Keeper | When does the wake stop? | done_marker_or_cap 0.44 (fb) | done_marker_or_cap 1.00 | Done marker, disarm, or the 24-wake cap (R5) |
| 1 | Simplifier | Transient timer or unit files? | transient_timer 0.35 (fb) | unit_files 0.98 | Persistent prefixed unit files, removed on disarm (R6) |
| 1 | Seed Closer | How to detect an OpenGSD project? | planning_dir_only 0.45 (fb) | identity_proven 1.00 | `.planning/` plus proven identity; else skip, unverified (R7) |

---

*Phase: 26-session-self-resume-and-opengsd-quota-rules*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 26 — implementation decisions (how to build what's specified above)*
