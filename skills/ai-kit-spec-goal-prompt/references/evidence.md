# Evidence and limits

Where each closed claim in SKILL.md comes from, and what it does not prove.

Load when: a rule looks arbitrary, or you must re-verify a claim before relying on it.

Each source is an earlier run or an installed binary, not a run of this skill. Re-check a claim
before you rely on it for a different version of the host.

## The `/goal` limit

- Claim: a `/goal` condition of 4,000 characters is accepted.
- Source: the strings of the installed Claude Code binary (version 2.1.314) show a refusal when the
  condition length is greater than 4000 UTF-16 units (JavaScript `length`). Read from binary
  strings, not run live.
- Limit: the renderer counts code points and keeps its own 1,800-character budget as a margin. An
  emoji counts as two UTF-16 units, so a condition full of emoji reaches the host limit sooner than
  the renderer's count suggests.

## A pasted multi-line block

- Claim: a pasted multi-line `/gsd-autonomous` block arrives whole as `ARGUMENTS`.
- Source: observed in two real past sessions of the owner.
- Limit: the flag parse stays simulated (the upstream `grep` lines applied to the generated block).
  The first line must use ASCII `--`; a typographic dash is not a flag.

## Other hosts' primitives

- Claim: codex has `/goal`; opencode, pi and cursor have no goal, loop or schedule primitive.
- Source: the usage text `/goal [<objective>|clear|edit|pause|resume]` is in the codex binary
  strings, and a real codex session used `/goal` (its log holds `thread_goal_updated` events). The
  `--help` output of opencode, pi and cursor was searched for goal, loop and schedule keywords on
  2026-11-02 and none matched.
- Limit: community wrappers are unchecked. A non-current host stays `unverified` in detect by rule.

## `ToolSearch`

- Claim: only Claude has `ToolSearch`.
- Source: codex has a lowercase `tool_search` for MCP apps, and the opencode and pi tool lists have
  no such tool.

## GSD queries and the template delimiter

- `runtime-identity` and `init.phase-op` answered in other OpenGSD projects (gsd-tools 1.17.0 and
  1.16.0). Original GSD stays `unverified`.
- The `§§` template delimiter works under Python 3.12.12: the goal-prompt tests pass there.

## The pointer form

- Nothing shows that a host follows `/goal read document ... at section ...`. The form is coded and
  tested for its text only, and render warns each time it is used.
