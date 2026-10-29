---
spike: 001
idea: session-self-resume
name: claude-timer-resume
type: standard
validates: "Given a recorded Claude Code session id, when a transient systemd user timer runs claude -p --resume <id>, then it re-enters that session"
verdict: VALIDATED
related: [002, 003, 004]
tags: [claude-code, systemd, resume]
---

# Spike 001: claude -p --resume from a transient systemd user timer

## What This Validates
Given a throwaway session that was asked to remember a word, when `systemd-run --user
--on-active=15` runs `claude -p --resume <id>` in the session's directory, then the reply is the
word and the session id is unchanged.

## Research
`claude --help` (2.1.310): `-r/--resume [value]` resumes by session id; `-c/--continue` picks the
most recent conversation in the directory (unsafe with parallel sessions, per 26-SPEC); `--bg`
starts a background session and, with `--resume <id>`, continues it in the background;
`--permission-prompts none` exists ("denied automatically"). A transient `systemd-run --user`
timer writes no unit file in the home (the units live in the user runtime dir and are removed
after the run).

## How to Run
`bash .planning/spikes/001-claude-timer-resume/run.sh <log dir>` (cheapest model `haiku`).

## Investigation Trail
- Seed: `claude -p "Remember the word KUMQUAT..."` returned `OK` and a session id.
- The timer fired 15 s later in the user manager's clean environment (no `CLAUDECODE`); the
  resumed run replied `KUMQUAT`, exit 0, same `session_id`. The transient timer and service were
  `inactive` afterwards (removed after the run).
- Control: the same `--resume <id>` from a different directory also replied `KUMQUAT` with the same
  session id. In 2.1.310 the session id alone selects the transcript; the directory does not have
  to match. (The resume still runs with that other directory as its cwd, so D-09's launch-directory
  rule stays right for the work it does.)
- Gotcha: `claude -p` without a stdin redirect waits 3 s and prints `Warning: no stdin data
  received in 3s`; a wake command uses `< /dev/null`.

## Results
VALIDATED: a transient systemd user timer re-enters the recorded Claude Code session by id
(2.1.310). The id, not the directory, selects the transcript. Throwaway session transcripts were
written by the CLI under the owner's Claude Code project store for the scratch directories, as any
`claude -p` run does; no config was edited.
