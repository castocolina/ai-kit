# The in-session companion

MANDATORY when `arm` prints `companion: create one one-shot in-session wake at <time>`. Do NOT
load it for `status`, `done`, `disarm`, or when `arm` prints `companion: none`.

A host process that is alive at a fire (an interactive host waiting at its usage limit) is never
resumed by the timer. The companion is the only thing that can resume that live stall, and `arm`
prints it only while the wake is reset-timed.

## Procedure

1. Skip it when the printed time has already passed.
2. Never create a repeated or fixed-interval job: one one-shot, on a host that has a scheduler (on
   Claude Code, a one-shot CronCreate).
3. `arm` prints the companion line on every arm or refresh of a reset-timed wake, including a
   refresh without reset flags (the executor's stop re-arm, a resumed session's re-arm). So
   check before creating, or two companions will run the same continue prompt:
   - List the scheduler's jobs (on Claude Code, the CronList tool). Skip if a one-shot job at
     the same UTC time exists whose prompt names this shim path and session id.
   - If the host cannot list jobs, create it on an `arm` that printed `armed <host>-<id>`
     unconditionally. On a `refreshed`, create it only when the conversation holds no
     job-creation result for the same UTC time whose prompt text names this shim path and session
     id (the marker).
4. The printed time is UTC (`Z`); convert it to the scheduler's local time. An in-session fire
   inside the usage limit is lost (the output cites this as spike 004), which is why the companion
   is set for after the reset.
5. Cancel it at `done` or `disarm` where the scheduler allows.

## Companion prompt

With the literal values substituted:

> Run `python3 "<literal shim path>" status --host <host> --session-id <id>`. If it prints any
> `invalid state:` line (`invalid state: missing` means no wake is recorded), stop and do nothing
> else. Otherwise read the state file whose path `status` prints first and every state file in
> its refs, continue only unfinished work (continue a pending cross-AI hard-tier wait from its own
> state file, cycle and due_at, never at cycle 0; never switch harness, provider or model), and
> run `python3 "<literal shim path>" done --host <host> --session-id <id>` when nothing remains.
