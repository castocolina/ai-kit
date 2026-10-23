# Session-start tool-substitution hooks

## What these hooks do

At session start and after compaction, the wrapper scripts inject a compact
briefing that names which curated `rtk` tool substitutions are genuinely
available on this machine right now. `detect.py` composes that briefing through
`detect_substitutions()` and `compose_message()`. Detection is ai-kit's own
curated pair list crossed with live binary presence and a parse of
`rtk init --show`. That last signal is reverse-engineered from a third-party
CLI's human-readable output, not a documented machine contract, so a parse miss
reports "not active" rather than guessing.

## Host coverage

| Host | Injection point | Status |
|------|-----------------|--------|
| Claude Code | `hooks.SessionStart` in `settings.json`, matcher `startup\|compact` | Wired |
| Cursor | `hooks.sessionStart` in `hooks.json`, flat array, no matcher | Wired. Live-verified during Phase 4's discussion; Cursor is not a gap (D-09). |
| opencode | none | Accepted gap. opencode has no documented session-start injection point today. This is recorded in `.planning/PROJECT.md` (Out of Scope) and `REQ-tool-substitution-hook-wiring`, not an oversight. The gap is pending upstream support; nothing in this directory has an opencode code path. |
| Claude Code | `hooks.PreCompact` (matcher `manual\|auto`) + `hooks.SessionStart` (matcher `compact`) in `settings.json`, via `claude_precompact.py` | Wired in Phase 21.2; see `## PreCompact pre-summary` below. Both entries are separate from the briefing rows above, so unwiring one never removes the other. |

## PreCompact pre-summary

Before a Claude Code compaction, the `PreCompact` entry hands the session's
transcript to `precompact_core.py`: the core splits the active conversation
part (everything after the last recognized `compact_boundary`) into chunks,
classifies each chunk keep/summarize/discard through the 21.1 decision client
on a loopback backend only, and writes an extractive pre-summary of at most
9,500 characters. The file is `{session_id}-{slug}-compact.md` in
`$XDG_RUNTIME_DIR/ai-kit/compact/` (cache fallback), 0600 in a 0700 dir,
deleted after injection and swept after 24 h. Its header records the session
id, host, per-label chunk counts, skipped-line counters and elapsed time.

The `compact`-matcher `SessionStart` entry then injects that session's file as
`additionalContext` and deletes it. Neither entry ever blocks: every path
exits 0, no output carries a `decision` field, and Claude Code still writes
its own compaction summary — the pre-summary only adds context after it. The
transcript format is undocumented and internal to Claude Code; the reader is
defensive (malformed, truncated, unknown and foreign lines are skipped and
counted, never raised) and no test reads a real transcript.

## Non-goals

- No `PreToolUse` mechanism. These hooks never intercept, rewrite, or block a
  command. They only add context at session start, through a channel entirely
  separate from any command's stdout, so they cannot alter a command's expected
  output shape (D-01). Real-time per-command enforcement was raised and
  explicitly deferred (`.planning/phases/03-tool-substitution-awareness-hook/03-CONTEXT.md`,
  Deferred Ideas).
- No modification of `rtk`'s own hook registration. ai-kit's entry is an
  additional, independent array entry. `rtk hook claude` and `rtk hook cursor`
  live under each host's `preToolUse`-family event and are never read, edited,
  or removed by ai-kit (D-02).

Phase 4's config doctor folds this non-goals note in as its cross-runtime
`rtk`-integration check, so this section is a downstream contract, not just
prose.
