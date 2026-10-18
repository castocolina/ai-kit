---
created: 2026-10-18T17:21:10.347Z
title: Visible tool-advisory hooks (SessionStart, PreToolUse, PostToolUse) as setup knobs
area: tooling
severity: major
files:
  - tools/hooks/claude_session_start.py
  - tools/hooks/detect.py
  - tools/hooks/README.md
  - tools/setup.py
  - tools/wizard_app.py
---

## Problem

The previous milestone's tool-substitution hook works but has no visible effect:

- Verified 2026-10-18: `~/.claude/settings.json` wires `SessionStart` (`startup|compact`) to
  `python3 -S <ai-kit>/tools/hooks/claude_session_start.py`; a manual run exits 0 and emits
  `additionalContext` naming bat/rg/fd/sd/eza; the text reached the model of the v1.3 session
  after its compaction.
- It is model-only context, so the user never sees it, and the setup wizard does not show it as
  its own knob.
- One line at session start does not change behavior over a long session: agents (including the
  v1.3 orchestrator) keep using cat, grep, sed and find. Phase 03 deliberately deferred any
  PreToolUse mechanism.
- The briefing names rtk; the owner has uninstalled rtk (it truncates output and agents then
  report errors or miss results), so the hooks must not mention rtk at all.

## Solution

- Each hook is its own install/uninstall knob in ai-kit setup (wizard row and headless flag):
  tool advisory at SessionStart, a PreToolUse advisor, a PostToolUse reminder, plus the
  decision-system and PreCompact hooks from the sibling todos.
- Make the SessionStart briefing visible to the user (a user-facing message, if the host
  supports one) as well as to the model.
- PreToolUse advisor, never a command replacer: when a Bash call uses grep/cat/sed/find and the
  better tool is installed, say so ("someone pointing out a non-recommended habit"), e.g. rg,
  `bat --plain` (no color overhead; also `--paging=never`, an explicit `-l <lang>` to skip
  format guessing, `-r N:M` ranges), sd, fd.
- Before reading a file: report its size, line count and estimated tokens (wc-style) and suggest
  a ranged Read or `bat -r`.
- PostToolUse reminder: "you used grep; next time use rg", only for tools that are installed
  and known to help.
- Advice only names tools that are actually installed (reuse `detect.py`'s live presence
  check); drop the rtk parse.

## Research notes (2026-10-18, fast pass; docs read via a summarizing fetch, confirm wording)

- SessionStart `systemMessage` is shown to the user; `additionalContext` is model-only. The compact
  matcher re-fires after compaction.
- PreToolUse: `hookSpecificOutput.additionalContext` adds context to the model; do NOT return
  `permissionDecision: "allow"` for advice, because it skips the permission prompt. Advice only
  must omit `permissionDecision` (verify live that `additionalContext` alone is honored).
- PostToolUse: `hookSpecificOutput.additionalContext` lands next to the tool result ("you used
  grep; next time rg"); plain stdout is not added as context for this event.
- UI visibility of `additionalContext` on tool events is not documented; verify live.
- Output cap 10,000 characters per field; keys outside `hookSpecificOutput` are silently ignored.
