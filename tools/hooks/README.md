# Session-start briefing and advisory hooks

## What these hooks do

- **Session briefing (`session-briefing`)** runs at session start and after compaction. It names installed modern tools from ai-kit's curated pairs crossed with `shutil.which`; Claude Code shows the user one `systemMessage` line, while the model receives the useful flags as context.
- **Tool advisor (`tool-advisor`)** advises on Bash uses of grep, cat, sed and find when their replacements are installed, and reports the size of an unranged large Read. Advice only: the large-read note arrives alongside that read's result and applies to the next read.
- **Tool reminder (`tool-reminder`)** reports output size and a better installed tool after a matching command. It appears on the first occurrence and every tenth repeat; shared state lives in `$XDG_RUNTIME_DIR/ai-kit/advisor/` (with the cache fallback).
- **Decision probe (`decision-probe`)** runs the `startup` probe, off by default, and names usable backends only. It performs one bounded probe of at most 3 seconds.
- **PreCompact pre-summary (`precompact`)** is described below; its host behavior and default follow the recorded verdicts.

No hook rewrites, approves, denies or blocks a tool call. Hook results are fail-open.

## Modern tools: how to use them

These flags are the session briefing's guidance for installed tools:

- `bat --plain --paging=never; use -l <lang> and -r N:M for a slice` — `-l` skips language detection, plain/no-paging keeps agent output clean, and `-r` reads a line range.
- `rg -n for line numbers, rg -l for file names, and --glob to filter` — search output is concise and can be limited to matching paths or file patterns.
- `fd --type f --glob to find files by pattern` — filter directly by file type and glob.
- `sd -p to preview before writing` — inspect replacements before changing files.
- `--long --git` — show eza's detailed listing with repository status.

## Host coverage

Every cell gives an explicit status. PreCompact delivery/default wording reflects `PRECOMPACT_VERDICTS` in `tools/setup.py` at the time this table was written; a live result in `21.3-LIVE.md` can change a cell.

| Host | session-briefing | tool-advisor | tool-reminder | decision-probe | precompact |
|------|------------------|--------------|---------------|----------------|------------|
| Claude Code | wired | wired | wired | wired (default off) | wired; default off: unmeasured |
| Cursor | wired (model context only; no user-visible field) | gap (secondary host, SPEC R7) | gap (secondary host, SPEC R7) | gap (secondary host) | gap (no verified PreCompact route) |
| pi | gap (no verified session-start route) | wired (tool_result) | wired (tool_result) | gap (no verified session-start route) | wired; default off: unmeasured (`session_before_compact`) |
| opencode | gap (no documented session-start injection point) | gap (tool.execute.after append unverified; spike S-OC in 21.3-LIVE.md) | gap (tool.execute.after append unverified; spike S-OC in 21.3-LIVE.md) | gap (no documented session-start injection point) | experimental; default off: unmeasured (`experimental.session.compacting`) |
| Codex | gap (no verified hook route) | gap (no verified hook route) | gap (no verified hook route) | gap (no verified hook route) | gap (no verified hook route) |

The precompact delivery verdict and default are separate: a `gap: <reason>` verdict is shown as `gap (<reason>)`; a non-gap route is `wired` (opencode is `experimental`), with `default on` only for `positive` and `default off: <verdict>` otherwise. A live result in `21.3-LIVE.md` can change a cell.

## PreCompact pre-summary

Before a Claude Code compaction, the `PreCompact` entry hands the session's
transcript to `precompact_core.py`: the core splits the active conversation
part (everything after the last recognized `compact_boundary`) into chunks,
classifies each chunk keep/summarize/discard through the 21.1 decision client
on a loopback backend only, and writes an extractive pre-summary of at most
9,500 characters. Low-confidence `needs_fallback` decisions keep an explicit keep
and downgrade summarize/discard to summarize; the header counts those downgrades as
summarize. User text is preserved verbatim ahead of non-user content when applying
the cap. Oversized Claude transcripts are read from the last bounded window, with
`head_truncated` recorded in the header. The file is `{session_id}-{slug}-compact.md` in
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

The same core serves the pi and opencode routes. On pi (D-08), the previous
compaction summary that the event hands over is pinned first in the
replacement summary and never trimmed — when the header, the previous summary
and the newest kept chunk cannot fit the cap whole, the pi entry returns
nothing so pi's default compaction runs; a replacement summary never drops
earlier-compacted history. The pi summary also ends with `<read-files>` /
`<modified-files>` blocks computed the way pi's own file lists are (modified =
edited plus written, read = read minus modified, sorted), because pi does not
carry file lists from an extension summary into later compactions; over the
cap the lists are trimmed path by path, ending with a `(+N more)` line. On
opencode the pre-summary is one extra `output.context` string and the
compaction prompt stays opencode's own.

## Non-goals

No ai-kit hook approves, denies, blocks or rewrites a tool call or its output.
The advisors only add context. Other tools' hook entries are separate array
entries; ai-kit never reads, edits or removes them. This preserves the Phase 03
D-02 boundary documented in `.planning/milestones/v1.0-phases/03-tool-substitution-awareness-hook/03-CONTEXT.md`.
