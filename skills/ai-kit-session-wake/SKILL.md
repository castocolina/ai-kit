---
name: ai-kit-session-wake
description: "Arms, checks and disarms a per-session systemd user-timer wake that resumes this exact session id after the orchestrating agent stalls on its own usage limit or its process dies. Use before a multi-plan GSD phase or multi-task superpowers plan, when an AGENTS.md rule says to arm the session wake, when the host reports a usage-limit reset time, or to inspect or remove a wake. Not for cross-AI subprocess limits (ai-kit-cross-ai's hard tier)."
---

# ai-kit-session-wake

Arms one wake per session. A wake is a systemd user timer (Linux) that runs the host's resume
command with the recorded session id, so a stalled orchestrating session continues where it
stopped. The shim is `ai-kit-session-wake.py` beside this file.

## NEVER

- **Never arm, `done` or `disarm` from a cross-AI child.** Code refuses `arm` when
  `AI_KIT_CROSS_AI_CHILD` is set or a `cross-ai.mjs` ancestor exists. Only the orchestrating
  session arms its wake.
- **Never call `done` or `disarm` from a subagent.** Only the orchestrating session does that.
  Nothing detects a subagent by its environment or process tree, so this rule is enforced by this
  text alone. This is a stated residual risk: a subagent that runs `done` disarms the wake early.
  It never causes a wrong resume.
- **Never resume "most recent".** Every wake names one session id.
- **Never guess a session id.** Do not take the newest session file as this session's id.
- **Never hand-edit the systemd units or the state files.** Use `arm`, `done` and `disarm`.
- **Never switch harness, provider or model** when a wake resumes.

## Resolve the shim

Take the first existing candidate, in one `Bash` call (the same order the executor skills use):

```bash
for d in "$(dirname "<absolute path to THIS SKILL.md>")" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-session-wake}" \
         "$HOME/.claude/skills/ai-kit-session-wake" \
         "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills/ai-kit-session-wake"; do
  [ -n "$d" ] && [ -f "$d/ai-kit-session-wake.py" ] && { SHIM="$d/ai-kit-session-wake.py"; break; }
done
[ -n "$SHIM" ] || { echo "ai-kit-session-wake: shim not found; STOP and tell the user"; exit 1; }
printf 'SHIM=%s\n' "$SHIM"
```

Record the printed `SHIM=` line as a literal value and use `python3 "$SHIM" <subcommand>` in
every later call. Each `Bash` call starts a fresh shell, so re-substitute the value.

## Arm

Find the session id first:

- **claude**: nothing to pass. The shim reads `CLAUDE_CODE_SESSION_ID` and `CLAUDE_PID`.
- **pi**: pass `--session-id <id>` with this session's exact id. pi exposes no verified session
  variable. Use only an id the owner gave you or the host printed. Without it, `arm` refuses
  (exit 2) and this run has no wake.
- **opencode**: pass `--session-id <id>`, same rule as pi.
- **codex**: the session-id source is unverified. Pass `--session-id` only from a value you were
  given.

```bash
python3 "$SHIM" arm [--session-id "<id>"] [--ref "<state file>"]...
```

Pass `--ref` for each state file this run owns (for example a cross-AI resumable-state file), so
the resumed session reads them. Relay these lines from the output: `armed <host>-<id>` or
`refreshed <host>-<id>`, the `wrote` and `systemctl creates` lines, `permission_mode`, the
`warning: linger is off` line when it prints, and `primitive`. Exit codes:

- 0: armed or refreshed (or nothing to do).
- 2: refused. The message names the cause, such as a missing session id or a cross-AI child.
- 3: no surviving primitive for this host (cursor, or no systemd user manager).

### When `arm` prints a companion time

When `arm` prints `companion: create one one-shot in-session wake at <time>`, create one one-shot
in-session wake at that time with a short resume prompt, where the host has a scheduler. On Claude
Code that is a one-shot CronCreate. Never create a repeated or fixed-interval job. A fire inside
the usage limit is lost (spike 004), so the systemd timer is the wake and the one-shot is only a
companion.

### Reset time

When the host reports a usage-limit reset time, pass it so the first wake lands after the reset:

- `--reset-text "<the host's limit line>"`: parsed into a reset time (inferred, D-30).
- `--reset-at <epoch or ISO 8601 with Z or an offset>`: an explicit time.

A reset the shim cannot read is refused, and the hourly wake stands. Every reset time is inferred,
not stated by the host, and `arm` prints it as such.

### Opt-in StopFailure hook

The `session-wake` StopFailure hook arms the wake when a Claude Code session stops on a rate
limit. It is opt-in: enable it through the ai-kit installer's hook selection. It is experimental,
and its payload is unverified.

## Done and disarm

When the orchestrating session finishes its work, run `done` so the next wake removes itself. Run
`disarm` only to remove a wake at once:

```bash
python3 "$SHIM" done [--host <host>] [--session-id <id>]
python3 "$SHIM" disarm [--host <host>] [--session-id <id>]
```

Inside a resumed wake, `done` only writes a marker, and the resume's own finish step disarms. A
subagent must not call either (see NEVER).

## The six subcommands

`arm`, `done`, `disarm`, `status`, `fire` and `matrix` are the only subcommands. `fire` is the
timer's own entry point (`fire` runs one wake: it resumes the recorded session id once); an agent
never runs it by hand.

## Status and matrix

```bash
python3 "$SHIM" status [--host <host>] [--session-id <id>]
python3 "$SHIM" matrix [--json]
```

`matrix --json` is the contract Phase 27 reads. It lists each host's wake primitive with its
evidence label.

## Unverified

Nothing below is verified on this machine. Each is labelled where it appears:

- That a wake survives a reboot.
- That the first timer fire resumes the session.
- That the timer removes itself after `done`.
- That auth still works after a reboot.
- The session-store layouts for pi, opencode and codex (they are reverse-engineered or from help
  text).
- The StopFailure hook payload.
- A live stall whose reset time is unknown.

## Relation to ai-kit-cross-ai

This skill is separate from ai-kit-cross-ai's hard tier. Its state lives in its own files. After a
resume, the agent continues a pending cross-AI hard-tier wait from that wait's own state file
(cycle and due_at). It never restarts the wait at cycle 0 (`ai-kit-cross-ai/SKILL.md`).
