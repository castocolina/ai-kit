---
created: 2026-10-24T21:47:44.799Z
title: Make the ai-kit session hooks dynamic (worktree indexing advice, install-relative docs, compact metrics)
area: tooling
severity: minor
resolves_phase: 49
files:
  - tools/hooks/detect.py:45-90
  - tools/hooks/claude_session_start.py
  - tools/hooks/cursor_session_start.py
  - tools/hooks/claude_precompact.py
  - tools/hooks/precompact_core.py
  - tools/hooks/opencode/
  - tools/hooks/pi/
  - tools/hooks/README.md
  - tools/install.sh:49
---

## Problem

Owner request (2026-10-24). Every ai-kit hook should detect what is actually installed and point
the agent at reference docs or scripts by their real, install-relative location, never a static
string. Three asks:

1. **New worktree / new codebase indexing advice.** When a session starts in a freshly created
   worktree (or any checkout with no index), check whether `codegraph` and `graphify` are on PATH
   and tell the agent how to index it (`codegraph init`/`codegraph sync` when no `.codegraph/`;
   graphify's `graphify-out/` when the owner uses it). Only name the tools that are installed.
2. **Dynamic SessionStart line.** The current user line reads
   `ai-kit: prefer these modern tools: bat over cat, ... Usage: ~/git/personal/ai-kit/tools/hooks/README.md`.
   Make sure it stays dynamic, including the path: a `curl ... | bash` install lives at
   `${AI_KIT_DIR:-${XDG_DATA_HOME:-~/.local/share}/ai-kit}` (`tools/install.sh:49`), so the line
   must show that location there.
3. **Compact metrics.** After a compaction, report how large the context window was and how long
   the compaction took.

## Current state (verified 2026-10-24)

- Item 2 is already partly dynamic: `compose_message()` in `tools/hooks/detect.py` lists only the
  installed tool pairs, and the README path comes from the hook file's own `realpath` with the home
  collapsed to `~` (83e25d2). An install under `~/.local/share/ai-kit` should therefore already
  print `~/.local/share/ai-kit/tools/hooks/README.md`. This is not yet proven by a test that runs
  from a non-checkout install location.
- Gap in item 2: the model context (the guidance block the agent actually reads) carries no doc
  path, only the user line does. The 200-char cap silently drops the `Usage:` suffix on a long path.
- Item 3: the PreCompact core already records its own `elapsed_ms` (classification time, e.g. 8003)
  in the injected block. That is not the compaction's duration and not the window size.
- `codegraph` and `graphify` are installed under `~/.local/bin` on this machine.

## Solution

Approach hints, all to be confirmed in research:

- **Worktree hook.** In Claude Code, a `WorktreeCreate` hook *replaces* the default git worktree
  creation (the hook must create the worktree and print its path). Using it just for advice would
  take over worktree creation. Prefer a SessionStart check that detects a linked worktree
  (`git rev-parse --git-dir` differs from `--git-common-dir`) or a missing `.codegraph/`, and emit
  the advice there. That also works on hosts with no worktree event (Cursor, opencode, pi; to
  verify per host).
- **Install-relative paths.** Resolve every referenced `.md`/script from the hook's own location
  (the `detect.py` pattern) and add the doc path to the model context too. Add a test that copies
  the hooks into a scratch `XDG_DATA_HOME/ai-kit` and asserts the printed path.
- **Compact metrics.** The PreCompact hook writes a small state file: start time, transcript bytes,
  the last assistant turn's usage tokens (input + cache read + cache creation) when the transcript
  carries them. The SessionStart `compact` hook reads it and prints window size and duration
  (`now - start`). Open question for the researcher: does each host (Claude Code, opencode, pi,
  Cursor) expose a post-compact event or token counts directly? Flag any inferred number as
  inferred.
- Keep the hooks stdlib-only, keep the output within the existing size caps, and stay silent
  when nothing is installed.

## Note 2026-11-03 (Phase 30 discuss)

Phase 30 now indexes automatically: a new worktree gets `codegraph init -y` or `codegraph sync` and
`graphify update .` through ai-kit's `post-checkout` hook, and every unit boundary refreshes both. Item 1
here shrinks to advice: the session-start line reports what was indexed (or which CLI is missing), and no
longer tells the agent how to index. Not folded into Phase 30.

Done: worktree indexing, by Phase 30 (FLOW-04, FLOW-13, 30-VERIFICATION): the `post-checkout` hook and the unit
boundary index new worktrees. Still open (HOOK-03, Phase 49): the session-start report of what was indexed,
install-relative doc paths and compact metrics.
