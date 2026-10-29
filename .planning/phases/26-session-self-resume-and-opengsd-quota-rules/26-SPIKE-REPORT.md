# Phase 26 — spike report (SPEC R2)

**Date:** 2026-10-25. **Versions:** Claude Code 2.1.310 (CLI; the measuring session itself ran
2.1.299), pi 1.3.0, opencode 2.0.31, codex-cli 0.162.1, systemd user manager with `Linger=yes`.
**Spikes:** `.planning/spikes/001`-`004` (scripts, logs outside the repo, READMEs with the trail).

Each item of 26-CONTEXT `<specifics>` "The spike must measure", with its finding:

1. **Timer re-entry (claude).** Verified (001): a transient `systemd-run --user --on-active` timer
   running `claude -p --resume <id> ... < /dev/null` re-enters the session (same id, prior context
   recalled). The id alone selects the transcript: the same resume from a different directory also
   re-entered it. Without `< /dev/null`, `-p` waits 3 s for stdin and warns.
2. **Original process alive.** Verified for `-p` (002): no lock or refusal; the concurrent resume
   runs and succeeds, but its turn is missing from the session afterwards (the live process wins).
   `--bg --resume <id>` exists in `--help`; not measured (unverified).
3. **Exit while the quota is exhausted.** The in-session reply is verified from this run's
   transcript (004): `You've hit your session limit · resets <time> (<IANA zone>)`, and for the
   weekly limit `You've hit your weekly limit · resets <Mon D>, <time> (<zone>)`. The headless
   `claude -p` exit code during a limit is **unverified** (it cannot be induced safely).
4. **CronCreate during a limit, and /goal.** Verified (004): a fire during a limit is delivered on
   schedule and consumed by the limit reply; it is never replayed after the reset. Recurring jobs
   expire after 7 days (observed). `/goal` pauses with `Goal paused · usage limit reached · send a
   message after it resets to continue` and does not resume by itself.
5. **Permission mode.** `--permission-mode <mode>` and `--permission-prompts none` ("denied
   automatically") exist in 2.1.310 `--help`; whether `none` prevents every hang is **unverified**.
6. **Auth after a reboot with linger and no login session.** **Unverified** (needs a reboot).
7. **`CLAUDE_CODE_CHILD_SESSION` in the main agent.** **Contradicted:** in this run's main agent,
   a background-job session (`CLAUDE_JOB_DIR` set), `CLAUDE_CODE_CHILD_SESSION=1`. D-24's marker
   would refuse `arm` in the main agent of every background session. Also: the process named by
   `CLAUDE_PID` has `comm` `2.1.299` (the version string), not `claude`, so D-08's `comm` check
   fails on this host.
8. **codex.** Help only (owner rule): `codex exec resume [SESSION_ID] [PROMPT]` or `--last`;
   `CODEX_THREAD_ID`, cwd filtering and limit exit are **unverified**.
9. **pi and opencode.** Verified (003): `pi -p --session-id <uuid>` and `opencode run --session
   <id>` from a transient timer re-enter the session on `router-env/my-coding`. Both create a
   missing session for an unknown id (their `--help`). Session env vars were not inspected
   (**unverified**).
10. **Fresh enable and self-removal.** Verified for transient units: `systemd-run --user
    --on-active=N` fires after N s and the timer and service are gone (`inactive`) after the run;
    no unit file is written in the home. Persistent unit files (D-14) were not tested.
11. **Versions.** Above.
12. **A main-agent turn after its own limit; `StopFailure`.** Verified that the main agent gets
    turns during a limit (each prompt, cron fire or task notification produces one), but every one
    ends at once with the limit line, so no model work happens. `StopFailure` (matcher
    `rate_limit`) and its fields are **unverified**.
13. **Reset-text grammar.** Verified (004): `resets 12:30am`, `resets 4:50pm`, `resets 1pm`,
    `resets 3am` (no date within the day; minutes omitted on the hour), `resets Oct 22, 10pm`
    (date for a later day), each followed by ` (America/Santiago)`.

## Consequences for the plan

- D-08: drop the `comm == claude` condition (or accept the version-string name); keep pid + start
  time + boot id.
- D-09: the resume's cwd stays the launch directory for the work it does, but the transcript is
  selected by id alone (claude 2.1.310).
- D-10 step 4 (liveness first) is load-bearing: a concurrent resume is silently lost (002).
- D-15: pi's row can be `-p --session-id <id>` (verified); claude's `--permission-prompts none` exists.
- D-20: the in-session companion must be a one-shot at the reset (+ margin) or an OS timer; a
  fire inside the limit is lost (004).
- D-24: `CLAUDE_CODE_CHILD_SESSION` cannot be the subagent marker as is: it is `1` in a
  background-job main agent. Needs a different discriminator (open question for the researcher).
