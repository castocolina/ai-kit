---
spike: 003
idea: session-self-resume
name: pi-opencode-timer-resume
type: standard
validates: "Given a pi or opencode session id, when a transient systemd user timer resumes it headless, then it re-enters that session"
verdict: VALIDATED
related: [001]
tags: [pi, opencode, systemd, resume]
---

# Spike 003: pi and opencode re-entry from a transient timer

## Research
- pi 1.3.0 `--help`: `--session-id <id>` "Use exact project session ID, creating it if missing";
  `--session <path|id>` takes a session file or partial UUID; `-p/--print` is non-interactive.
- opencode 2.0.31 `run --help`: `--session/-s <id>` "Session ID to continue, or to create if it
  does not exist"; `--format json` emits events carrying `sessionID`.
- codex-cli 0.162.1 (help only, owner rule: no codex interactive checks): `codex exec resume
  [SESSION_ID] [PROMPT]`, or `--last` for the most recent session; `-` reads the prompt from stdin.
  Re-entry from a timer is unverified.

## How to Run
`bash .planning/spikes/003-pi-opencode-timer-resume/run.sh <log dir>` (lane `router-env/my-coding`).

## Investigation Trail
- pi: a seed with a fresh `--session-id <uuid>` replied `OK`; the timer-fired
  `pi -p --session-id <same uuid>` 10 s later replied `LOQUAT` (exit 0).
- opencode: a seed `opencode run --format json` replied `OK` with session `ses_...`; the
  timer-fired `opencode run --session <id>` replied `MEDLAR` (exit 0) with the same session id.
- Both CLIs create a missing session for an unknown id (help text), so a wake must check the
  session exists before resuming (D-09 already says so).

## Results
VALIDATED for pi 1.3.0 and opencode 2.0.31 on the router lane: a transient systemd user timer
re-enters the recorded session by id. pi's `--session-id <uuid>` works as the resume argv, so the
D-15 pi row does not need the session file path. codex stays unverified.
