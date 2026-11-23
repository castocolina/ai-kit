# Tool Preferences

Prefer these modern replacements when the task involves searching, listing, viewing, or
editing files. Each is confirmed on this lane's own PATH only when the `TOOL_AVAILABILITY = {…}`
line in this dispatch's capability block reports it `true`, and usable only when the block says
this lane has a shell; when it says `unknown: make no assumption`, try a tool only if you
find that you have a shell, and never assume one is available just because it's listed here.

| Instead of | Prefer | Why |
|---|---|---|
| `grep` (recursive) | `rg` | Faster, respects `.gitignore` by default, better defaults for code search. |
| `find` | `fd` | Simpler syntax, faster, respects `.gitignore` by default. |
| `cat` (for viewing code) | `bat` | Syntax highlighting, line numbers, git-diff markers in the gutter. |
| `ls` | `eza` | Clearer, more readable directory listings. |
| `sed` (in-place edits) | `sd` | Simpler find/replace syntax, fewer regex-escaping surprises. |
| `diff` | `delta` or `difftastic` | Readable, syntax-aware diffs. |

## codebase-memory-mcp

When the block's `CODE INDEX` section names codebase-memory-mcp, use its graph before broad file reads for architecture, cross-reference, "where is X used" and doc-to-code questions: the MCP tools `search_graph`, `trace_path`, `get_code_snippet`, `query_graph`, `get_architecture` and `check_index_coverage` when that section lists them (enabled for this call, read from the host's config, or for pi inferred from its extension file; an applied setting does not prove the server started, so fall back to direct reads when the tools are absent), otherwise, when it gives the CLI form and you have a shell, the same tools through `codebase-memory-mcp cli <tool> --flag value`. When `list_projects` shows no project for this checkout, run `index_repository` on it first. Fall back to `rg`/`fd`/direct reads when a narrow lookup is simpler than a graph query.

Use whichever of the above tools are genuinely confirmed present and useful for the task at
hand — this is a preference list, not a requirement to use every tool listed.
