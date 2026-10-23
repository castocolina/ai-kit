# Claude Code noise: connectors, synced skills, subagent MCP (2026-10-13)

Source: a claude-code-guide agent reading the official docs. These are not live-tested in build 2.1.296.

- **claude.ai connectors** (Claude docs, Google Docs, Gmail, Calendar). Disable them for the CLI only; claude.ai is unaffected.
  - `"disableClaudeAiConnectors": true` in any settings scope: user, or one project's `.claude/settings.local.json`.
  - Per session: the env var `ENABLE_CLAUDEAI_MCP_SERVERS=false`.
  - Per connector: `deniedMcpServers`.
  - The `/mcp` toggle is per project; it persists in `~/.claude.json` `disabledMcpServers`.
  - Docs: https://code.claude.com/docs/en/mcp and https://code.claude.com/docs/en/settings-reference
- **Cost of deferred MCP.** With tool search on (the default), only tool names and server instructions load at session start; full schemas load on demand. Unused connectors still cost their names and instructions every session. `ENABLE_TOOL_SEARCH` controls this. `claude plugin details <name>` shows a plugin's always-on token cost.
- **`anthropic-skills:*` (pdf, docx, xlsx, pptx, docs, deep-research, …)** are synced from the claude.ai account into `~/.claude/skills/synced/`.
  - Stop syncing with `"syncClaudeAiSkills": false` in user settings. The next start moves them to `~/.claude/skills/.trash/`. pdf and xlsx "always sync" while syncing is enabled; the rest can be toggled on claude.ai.
  - `disableBundledSkills` is a different setting: it covers skills that ship with Claude Code (`/code-review`, `/loop`, `/run`, …).
  - `skillOverrides` (`on` / `name-only` / `user-invocable-only` / `off`) does not apply to plugin skills.
  - Every skill's description (up to 1,536 characters) is in context on every turn.
  - Docs: https://code.claude.com/docs/en/skills
- **Subagent MCP inheritance.**
  - No `tools` field (e.g. general-purpose): the subagent inherits the main agent's built-in and MCP tools, including plugin MCP such as playwright and claude-in-chrome.
  - A `tools` allowlist excludes any MCP tool it doesn't name. This is how the GSD agents work.
  - The `mcpServers` frontmatter adds servers per subagent.
  - Whether claude.ai connectors reach subagents is not stated.
  - For a backend-only agent use `tools: Read, Edit, Bash`, plus `disallowedTools` or `permissions.deny` Bash rules.
  - Docs: https://code.claude.com/docs/en/sub-agents
- **Browser MCPs.**
  - claude-in-chrome (the extension's native-messaging bridge) and Playwright (`@playwright/mcp`) do not depend on each other.
  - Verify Chrome with `/chrome`: it should show Status: Enabled and Extension: Installed. Then `/mcp` → claude-in-chrome → View tools. Both sides must be signed in to the same org.
  - Disable either one per project in `/mcp`. Disable Playwright through `/plugin`, or with `deniedMcpServers`.
  - Docs: https://code.claude.com/docs/en/chrome
- **Project-local plugins and skills.**
  - `claude plugin install … --scope project|local` writes `enabledPlugins` to `.claude/settings(.local).json`. Precedence: local > project > user.
  - Skills in project `.claude/skills/` load only in that repo; a personal skill of the same name wins.
  - Hooks from user and project scope both run; no per-hook disable is documented, and `disableAllHooks` is all-or-nothing.
  - Workaround for a user-scope hook: make the script exit early when `$CLAUDE_PROJECT_DIR` is not a GSD repo.
  - Docs: https://code.claude.com/docs/en/discover-plugins and https://code.claude.com/docs/en/hooks-guide
