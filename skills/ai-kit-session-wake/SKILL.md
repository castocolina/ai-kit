---
name: ai-kit-session-wake
description: "Resume a session after a usage limit or rate limit: arms, checks and disarms a per-session systemd user-timer wake that resumes this exact session id once the orchestrating agent's host process has exited (for example it died at a usage limit). Use when a long unattended run should resume after a usage limit or rate limit, when an AGENTS.md rule says to arm the session wake, when the host reports a usage-limit reset time, or to inspect or remove a wake. The ai-kit-spec-execute-* executors already arm one for multi-plan or multi-task runs. Not for cross-AI subprocess limits (ai-kit-cross-ai's hard tier)."
---

# ai-kit-session-wake

Arms one wake per session. A wake is a systemd user timer (Linux) that runs the host's resume
command with the recorded session id, so a session whose host process has exited continues where
it stopped. If the host process is still alive at a fire, the timer only logs it and the fire
still counts toward the cap (see "The wake cap"). The shim is `ai-kit-session-wake.py` beside
this file; it needs the sibling `ai-kit-spec-review` skill installed beside it (exit 2 names it
when missing).

**Never fail the run on the wake.** Every refusal or missing primitive is relayed, and the run
goes on without a wake.

## NEVER

- **Never arm, `done` or `disarm` from a cross-AI child.** Code refuses `arm` when
  `AI_KIT_CROSS_AI_CHILD` is set to a value other than `0` or a `cross-ai.mjs` ancestor exists.
  Only the orchestrating session arms its wake.
- **Never call `done` or `disarm` from a subagent.** Only the orchestrating session does that.
  Nothing detects a subagent by its environment or process tree, so this rule is enforced by this
  text alone. This is a stated residual risk: a subagent that runs `done` disarms the wake early.
  It never causes a wrong resume.
- **Never resume "most recent".** Every wake names one session id.
- **Never guess a session id.** Do not take the newest session file as this session's id.
- **Never hand-edit the systemd units or the state files.** Use `arm`, `done` and `disarm`;
  they keep state and units consistent.
- **Never guess a host pid.** Pass `--pid` only with the pid the host itself reports.
- **Never switch harness, provider or model** when a wake resumes: the resume replays the
  recorded host command for that session id, and a route change is the owner's call.
- **Never run `fire` by hand.** It is the timer's own entry point; one `fire` resumes the
  recorded session id once.

## Resolve the shim

Take the first existing candidate, in one `Bash` call (candidate 1 is where the executor skills
look):

```bash
for d in "$(dirname "<absolute path to THIS SKILL.md>")" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-session-wake}" \
         "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/ai-kit-session-wake" \
         "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills/ai-kit-session-wake"; do
  [ -n "$d" ] && [ -f "$d/ai-kit-session-wake.py" ] && { SHIM="$d/ai-kit-session-wake.py"; break; }
done
[ -n "$SHIM" ] || { echo "ai-kit-session-wake: shim not found; no wake, continue the run"; exit 1; }
printf 'SHIM=%s\n' "$SHIM"
```

On `shim not found`, relay that line and continue without a wake. Otherwise record the
printed `SHIM=` line as a literal value and use `python3 "$SHIM" <subcommand>` in every later
call. Each `Bash` call starts a fresh shell, so re-substitute the value.

## Arm

Arm by hand only when no executor does. A manual arm makes you own its `done`: an
executor that later arms the same session sees `refreshed`, treats the wake as not its own and
never closes it. A session resumed by its wake follows the resume prompt: it re-runs `arm` (a
`refreshed`) and runs `done` itself when nothing remains. On pi, opencode and codex (the resume
env scrubs `CODEX_THREAD_ID`) the resumed session has no session variable: it reads `host` and
`session_id` from the wake state file the resume prompt names and passes them as `--host` and
`--session-id` to `arm` and `done`.

Find the session id first:

- **claude**: nothing to pass. The shim reads `CLAUDE_CODE_SESSION_ID` and `CLAUDE_PID`.
- **pi**: pass `--session-id <id>` with this session's exact id. pi exposes no verified session
  variable. Use only an id the owner gave you, the host printed, or (in a resumed session) the
  wake state file the resume prompt names.
- **opencode**: pass `--session-id <id>`, same rule as pi.
- **codex**: the shim reads `CODEX_THREAD_ID` when `--session-id` is absent; that source and the
  codex resume command are unverified.

```bash
python3 "$SHIM" arm [--session-id "<id>"] [--pid <host pid>] [--ref "<state file>"]...
```

Pass `--ref` for each state file this run owns, so the resumed session reads them. For `--pid`,
`--permission-mode` (claude-only) and `--only-if-armed`, or when `arm` refuses with `pass --pid`,
load `references/arm-options.md`; do NOT load it for a plain `arm`.

Relay every line `arm` prints, at the certainty it carries, in particular:

- `armed <host>-<id>` or `refreshed <host>-<id>`, the `wrote` and `systemctl creates` lines.
- `resume argv: ... (verified: ...)` or `(unverified: ...)`.
- `host pid: <pid> (unverified: nearest ancestor ...)`, when the pid came from the scan.
- `permission_mode: ...`, `primitive: ... (unverified: ...)` and `companion: ...`.
- `reset: <time> (inferred); next wake ...`, or `reset refused: <reason>; the hourly wake stands`.
- `warning: linger is off` (the wake stops at logout) or `linger: unknown`.

One outcome per exit code:

- 0: armed, refreshed, or nothing to refresh. With `reset refused:` there is no reset-timed wake,
  only the hourly one; say so, and never report a wake after the reset.
- 2: refused, the run goes on. Relay the stderr line. MANDATORY on exit 2: load
  `references/arm-exit-codes.md` to tell a refusal before any write from a failed timer step
  (first arm and refresh differ) or an invalid state. The only follow-ups are continue, `status`,
  `disarm` (plus one re-`arm` after an invalid state). Do NOT load it for exit 0 or 3.
- 3: no surviving primitive (cursor, or no systemd user manager). Relay it and continue; the
  printed in-session fallback dies with the process, so do not count it as a wake.

`done` and `disarm` also exit 2 when no session id resolves or the host is unknown (for example
on pi without `--session-id`); relay it and continue.

### The wake cap

A wake fires hourly and gives up after 24 counted fires (`wakes: n/24` in `status`). Every fire
counts once the first wake time is reached, including a fire that only logs because the host is
still alive. A refresh keeps the count; `disarm` then `arm` resets it. The 24th counted fire is
the last: the wake then removes itself with a `gave up` notice. This is the locked hard stop, so a
run that may last past about 24 hours must expect it. To explain a count, an early `gave up` or
the done/disarm blocking, load `references/wake-cap.md`; do NOT load it for status or disarm.

### What resumes a stall

- **Host process gone** (died or was killed): the timer fire resumes the session.
- **Host process alive** (an interactive host waiting at its usage limit): the timer fire only
  logs `host alive; log only` and spends one of the 24 fires. Only the in-session companion can
  resume it, and `arm` prints a companion only while the wake is reset-timed (a reset time was
  given at this or an earlier arm). Without a reset time nothing resumes a live stall and the
  owner must; do not report such a run as covered.

### When `arm` prints a companion time

MANDATORY when `arm` prints `companion: create one one-shot in-session wake at <time>`: load
`references/companion.md` and follow it. It covers the duplicate check (`arm` prints that line on
every refresh of a reset-timed wake, so check before creating), the UTC conversion and the prompt.
Never create a repeated or fixed-interval job. Do NOT load it for `status`, `done` or `disarm`, or
when `arm` prints `companion: none`.

### Reset time

When the host reports a usage-limit reset time, pass `--reset-text "<the host's limit line>"` or
`--reset-at <epoch or ISO 8601>` so the first wake lands after the reset; it is recorded as
inferred, never as stated by the host. For the formats, the 60 s margin and the opt-in
StopFailure hook (experimental, unverified payload), load `references/reset-time.md`; do NOT load
it for status, done or disarm.

## Done and disarm

When the orchestrating session finishes its work, run `done` for a wake you own. Run `disarm` to
remove a wake you no longer want:

```bash
python3 "$SHIM" done [--host <host>] [--session-id <id>]
python3 "$SHIM" disarm [--host <host>] [--session-id <id>]
```

- `done` never blocks. With nothing armed it prints `nothing armed; no done marker written`. With
  no resume running it writes the done marker and removes the wake at once; while a resume runs
  it prints `a wake resume is running; it disarms when the resume exits`. A first `arm` clears a
  stale done marker.
- `disarm` waits for a running resume to finish (a resume may run up to 4 hours, so it can block
  that long; while a resume runs, prefer `done`), then removes everything.
- Inside a resumed wake, both only write the marker, and the resume's own finish step removes the
  wake.

A subagent must not call either (see NEVER).

## Status and matrix

```bash
python3 "$SHIM" status [--host <host> --session-id <id>]
python3 "$SHIM" matrix [--json]
```

`status` takes both `--host` and `--session-id`, or neither (then it lists every wake); one
without the other exits 2. `matrix` lists each host's wake primitive with its evidence
label; `--json` is a stable machine-readable contract.

## Unverified

Reboot survival, the first timer fire resuming the session, in-wake `done` removal, auth after a
reboot, the reverse-engineered session layouts and the StopFailure payload are not verified on
this machine. Before claiming any of them works, load `references/unverified.md`; do NOT load it
otherwise.

## Relation to ai-kit-cross-ai

This skill is separate from ai-kit-cross-ai's hard tier. Its state lives in its own files under `${XDG_STATE_HOME:-$HOME/.local/state}/ai-kit/session-wake` (read them with `status`, never hand-edit). After a
resume, the agent continues a pending cross-AI hard-tier wait from that wait's own state file
(cycle and due_at). It never restarts the wait at cycle 0; the resume prompt says so.
