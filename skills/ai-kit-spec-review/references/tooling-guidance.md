# Tool Preferences

Prefer these modern replacements when the task involves searching, listing, viewing, or
editing files. Each is confirmed installed only when the `TOOL_AVAILABILITY = {…}` line in
this dispatch's own prompt reports it `true` — never assume one is available just because it's
listed here.

| Instead of | Prefer | Why |
|---|---|---|
| `grep` (recursive) | `rg` | Faster, respects `.gitignore` by default, better defaults for code search. |
| `find` | `fd` | Simpler syntax, faster, respects `.gitignore` by default. |
| `cat` (for viewing code) | `bat` | Syntax highlighting, line numbers, git-diff markers in the gutter. |
| `ls` | `eza` | Clearer, more readable directory listings. |
| `sed` (in-place edits) | `sd` | Simpler find/replace syntax, fewer regex-escaping surprises. |
| `diff` | `delta` or `difftastic` | Readable, syntax-aware diffs. |

## codegraph_explore (MCP)

When `codegraph_explore` is available and confirmed registered for the CLI running this
dispatch (never assumed — confirmed via a live per-client health check), prefer it over broad
file reads for architecture, cross-reference, or "where is X used" questions. Fall back to
`rg`/`fd`/direct reads when a specific, narrow lookup is simpler than a graph query.

Use whichever of the above tools are genuinely confirmed present and useful for the task at
hand — this is a preference list, not a requirement to use every tool listed.
