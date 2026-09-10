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
