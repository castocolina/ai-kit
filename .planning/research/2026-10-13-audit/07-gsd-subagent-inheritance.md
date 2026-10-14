# 07: What GSD subagents actually inherit

Scope: gsd-core 1.16.0 at `~/.claude/gsd-core` (`~/.claude/gsd-core/VERSION`). Review tree: `review-v13` at 0acbd06.

Host versions (from `--version`):
- Claude Code 2.1.296
- opencode 1.18.35
- codex-cli 0.153.4
- cursor-agent 2026.10.01
- pi 0.82.1

Confidence tags:
- **[V]**: verified from local source, config or command output.
- **[D]**: stated in official docs.
- **[O]**: observed live in this research agent's own context. I am a Claude Code `general-purpose` subagent.
- **[I]**: inference.

## 1. Short answer

The answer is none of the three options in the question. Each surface works differently.

1. **On Claude Code (case a, in-session), tools and MCP are a minimal set per agent.**
   - Each `~/.claude/agents/gsd-*.md` has an explicit `tools:` allowlist, and some also have `disallowedTools`. [V]
   - Claude Code only grants MCP tools that the allowlist names. [D]
   - The only MCP names in GSD allowlists are `mcp__context7__*`, the research MCPs (`firecrawl`, `exa`, `tavily`, `ref`, `jina`, `perplexity`), and `mcp__chrome-devtools__*` / `mcp__claude-in-chrome__*` for `gsd-dom-verifier`. None of context7 or the research MCPs is configured on this machine. **So in practice every GSD agent except dom-verifier runs with zero MCP tools.** That includes `codegraph`, even though `~/.claude/CLAUDE.md` tells agents to use it. [V]
2. **Everything else is inherited wholesale on Claude Code.** That covers CLAUDE.md/AGENTS.md, hooks, the skills catalogue (through the `Skill` tool) and the git status snapshot.
   - Docs: subagents load "every level of the CLAUDE.md hierarchy" (except Explore/Plan, or with `omitClaudeMd`). [D]
   - Docs: "Hooks from settings files, managed policy settings, and plugins all apply inside subagents." [D]
   - Docs: subagents "can still invoke unlisted project, user, and plugin skills through the Skill tool." [D]
3. **`agent_skills` is additive prompt text. It never restricts anything.**
   - It is a `<agent_skills>` block that tells the agent to Read listed SKILL.md files, or to call the Skill tool for plugin skills.
   - It does not limit which skills the agent can invoke.
   - It is not Claude Code's native `skills:` preload field, which no GSD agent uses. [V]
4. **On opencode and Cursor, GSD's installer strips the tool contract, so GSD subagents inherit the parent's full tool and MCP surface.**
   - opencode: the agent converter drops `tools:` and `disallowedTools:` (`runtime-artifact-conversion.cjs:1969-1987`). [V]
   - Cursor: the converter keeps only `name` and `description` (`runtime-artifact-conversion.cjs:2413-2421`). [V]
   - Read-only checkers lose their read-only guarantee on both hosts. [I]
5. **On Codex, the tool contract survives only as prose plus a derived `sandbox_mode`.** The mode is `workspace-write` only when Write or Edit is declared (`codex-agent-toml.cjs:425-445`). No `mcp_servers` key is emitted, so MCP is inherited from the parent. [V][D]
6. **Cross-AI subprocesses (case b) get the full default surface of the target CLI.**
   - That surface is all of its MCP, skills, plugins, hooks and AGENTS.md.
   - The single exception is the Claude review lane, which sets `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` (`review-lane-descriptor.cjs:120-129`). [V]
   - No restricting flags are passed: no `--strict-mcp-config`, `--pure`, `--ignore-user-config` or `--no-skills`. [V]
   - The `cross_ai_command` prompt carries no `agent_skills` block at all (`workflows/execute-phase/detail/elaboration.md:83-97`). [V]

## 2. Current state of this machine

GSD install footprint:
- **Claude Code** is the only host with live GSD artifacts:
  - `~/.claude/agents/gsd-*.md`: 35 files.
  - `~/.claude/skills`: 72 `gsd-*` skills out of 134.
  - The base checkout also has a project-local copy at `~/git/personal/ai-kit/.claude/{agents,commands,gsd-core}`, gitignored (`.gitignore:8`). It is the same 1.16.0 with absolute `@` paths, so in the base checkout it overrides the user scope. [V]
- **opencode, Codex and Cursor**: `agents/` and `skills/` are empty and there is no `gsd-core/`. Only `gsd-install-state.json` migration ledgers remain. **GSD agents are not installed on those hosts today.** [V]
  - Command: `ls ~/.config/opencode/agents ~/.codex/agents ~/.cursor/agents` → 0 files.
- **pi**: `~/.pi/agent/agents` holds 10 non-GSD agents (planner, worker, sdd-*). [V]

Configured MCP servers (names only):

| Host | MCP servers |
|---|---|
| Claude Code | user: `codegraph` (`~/.claude.json`). Plugin: `playwright` (`@playwright/mcp@latest`). Built-in: `claude-in-chrome`. No project `.mcp.json`. |
| opencode | `codegraph`, `gsd` (`npx -y -p @opengsd/gsd-core gsd-mcp-server`, 3 tools) |
| Codex | `codegraph` |
| Cursor | `codegraph` (`~/.cursor/mcp.json`) |
| pi | none. pi has "No MCP" by design (pi README:495). |

Skills (count of SKILL.md files) [V]:

| Location | Count | Notes |
|---|---|---|
| `~/.claude/skills` | 134 | 60 are symlinks; 72 are `gsd-*` |
| `~/.agents/skills` | 42 | **fully contained in `~/.claude/skills`** (overlap 42). The brief's "~112" is out of date. |
| `~/.pi/agent/skills` | 33 | 33 symlinks into `~/.agents/skills` |
| `~/.cursor/skills-cursor` | 22 | Cursor-bundled |
| Claude plugins | 37 | superpowers is installed twice (6.4.1 with 15 skills, 6.2.0 with 14), ponytail 6, frontend-design 1, typesafe 1 |

Project config (`review-v13/.planning/config.json`) [V]:
- `"agent_skills": {}`, so the block is empty for every agent:
  - Command: `query agent-skills gsd-executor --json` → `"reason": "not_configured"`.
- `model_profile: "balanced"`, with no `model_overrides`.
- `claude_md_path: "./CLAUDE.md"`, but ai-kit has **no CLAUDE.md**. It has `AGENTS.md` (13.5 KB).
- `~/.gsd/defaults.json` sets `runtime: "codex"`. gsd-tools ignores it here and prints `warning: ... a project config takes precedence here — those global keys are ignored` (#3532).

Resolved models (`query resolve-model <agent> --raw`, balanced profile):

| Agent | Model |
|---|---|
| executor | sonnet |
| planner | opus |
| plan-checker | sonnet |
| verifier | sonnet |
| phase-researcher | sonnet |
| code-reviewer | sonnet |
| codebase-mapper | haiku |

With `GSD_RUNTIME=opencode` the executor resolves to `anthropic/claude-sonnet-5`. [V]

## 3. Per-runtime fact matrix

### (a) GSD subagents spawned in-session

**Claude Code: `Agent(subagent_type="gsd-*")`**
- **Tools** [V][D]
  - Per-agent `tools:` allowlist from frontmatter, for example:
    - executor: `Read, Write, Edit, Bash, Grep, Glob, Skill, mcp__context7__*, mcp__plugin_context7_context7__*`.
    - plan-checker: `Read, Bash, Glob, Grep, Skill` with `disallowedTools: Write, Edit, MultiEdit`.
  - `gsd-nyquist-auditor` and `gsd-security-auditor` use YAML list form.
  - 13 agents have no `Skill` tool: ai-researcher, debug-session-manager, doc-classifier, doc-synthesizer, doc-verifier, domain-researcher, dom-verifier, eval-planner, framework-selector, intel-updater, mempalace-curator, pattern-mapper, user-profiler.
  - Only `gsd-debug-session-manager` has `Agent`.
- **MCP** [V][D]
  - Only the servers named in `tools`. Docs: "`mcp__<server>__*` grants ... every tool from the named server."
  - None of the named servers is configured except `claude-in-chrome`, which only dom-verifier gets. **Effective MCP is 0 for 34/35 agents.**
  - `codegraph` and `playwright` are never granted.
- **Skills** [D][V][I]
  - No `skills:` preload field on any GSD agent.
  - Agents with `Skill` can invoke any user, project or plugin skill. That is 134 + 37 plugin + built-ins here.
  - The skills listing (names and descriptions) is budgeted at 1% of the context window, and descriptions are dropped first. [D]
  - [I] The listing probably reaches only agents whose tool set includes `Skill`. Not confirmed by docs.
- **Slash commands** [D][I]
  - There is no slash-command dispatch inside a subagent.
  - GSD commands are installed as skills (`~/.claude/skills/gsd-*`), so they are reachable through the Skill tool. [V]
- **Instruction files** [D][V]
  - CLAUDE.md hierarchy (user, project, local, managed), plus `AGENTS.md` when no CLAUDE.md exists (memory docs, "When Claude Code reads AGENTS.md"). For ai-kit that means `AGENTS.md`.
  - Auto memory is not loaded (docs). See uncertainty U1.
  - Git status snapshot is included.
  - Settings and plugin hooks apply. Here that means 8 user hook events plus ponytail's `SubagentStart`.
- **Model** [D][V]
  - Resolution order: per-call `model=` → frontmatter `model` (absent in all 35 GSD agents) → `CLAUDE_CODE_SUBAGENT_MODEL` → parent model.
  - GSD passes `model=` from the profile, or omits it on `inherit` (`references/model-profile-resolution.md`).
  - `effort:` comes from frontmatter (low/high/xhigh per agent).

**opencode: GSD agents converted to `mode: subagent` (not installed today)**
- **Tools** [V][D]
  - `tools:` and `disallowedTools:` are **stripped** ("Agents: strip tools entirely", `runtime-artifact-conversion.cjs:1969-1987`).
  - No `permission` is emitted, so the agent inherits global permissions. opencode docs say per-agent `permission` "overrides" global; unset means global.
- **MCP** [D][V]
  - Inherited from the parent, because no `"<mcp>_*": "deny"` permission is emitted.
  - Today: `codegraph` and `gsd`.
- **Skills** [D]
  - The `skill` tool lists every skill in `~/.claude/skills`, `~/.agents/skills` and project equivalents, plus plugin skills.
  - Can be removed with `tools.skill:false` or `permission.skill` deny.
- **Slash commands** [I]
  - Not available to subagents. GSD commands would be installed as skills.
- **Instruction files** [D][I]
  - `AGENTS.md` (project, then `~/.config/opencode/AGENTS.md`) plus `~/.claude/CLAUDE.md` fallback.
  - The docs don't say whether this applies to subagents. [I] Likely yes, since subagents are child sessions built from the same prompt assembly.
- **Model** [V][D]
  - `model:` comes from `~/.gsd/defaults.json` overrides baked at install time. Otherwise the invoking agent's model (docs).
  - `variant:` carries effort (`runtime-artifact-conversion.cjs:2044-2066`).

**Codex: GSD agents converted to `~/.codex/agents/*.toml` (not installed today)**
- **Tools** [V]
  - The `tools:` list is copied as prose in a `<codex_agent_role>` header (`runtime-artifact-conversion.cjs:2707-2721`).
  - Enforcement exists only through `sandbox_mode`: `read-only`, or `workspace-write` when Write or Edit is declared.
- **MCP** [D][V]
  - "`sandbox_mode`, `mcp_servers`, and `skills.config` inherit from the parent when the custom agent file omits them" (learn.chatgpt.com subagents page).
  - GSD emits no `mcp_servers`, so the agent inherits `codegraph`.
- **Skills** [D]
  - Inherited from the parent.
  - Codex scans `.agents/skills` (repo) and `~/.agents/skills` (42 here), plus `/etc/codex/skills` and bundled skills.
  - The listing is capped at 2% of context.
- **Slash commands** [V]
  - GSD commands are converted to Codex skills (`convertClaudeCommandToCodexSkill`).
- **Instruction files** [I]
  - `~/.codex/AGENTS.md` and the project `AGENTS.md`. Docs don't state this for subagents; inheritance is likely.
- **Model** [D]
  - Explicit spawn value → `[agents]` default → parent model and effort.

**Cursor (cursor-agent): GSD agents converted to name and description only (not installed today)**
- **Tools** [V][D]
  - Frontmatter is reduced to `name` and `description` (`runtime-artifact-conversion.cjs:2413-2421`).
  - Docs: "Subagents inherit all tools from the parent, including MCP tools."
  - Cursor has no `tools` field, only `readonly`.
- **MCP** [D]
  - All of the parent's MCP servers. Today that is `codegraph`.
- **Skills** [D]
  - `~/.agents/skills`, `~/.cursor/skills`, plus `~/.claude/skills` and `~/.codex/skills` "for compatibility".
- **Slash commands** [I]
  - Skills only. With `disable-model-invocation`, a skill becomes a slash command.
- **Instruction files** [D][I]
  - Docs say only "clean context". Rules and AGENTS.md are not documented for subagents.
- **Model** [D]
  - Frontmatter `model` (any catalog id).

**pi: subagent extension (`~/.pi/agent/extensions/subagent`)**
- **Tools** [V]
  - Each subagent is a **separate `pi` process**: `pi --mode json -p --no-session [--model M] [--tools a,b] --append-system-prompt <file> "Task: …"` (extension `index.ts:294-330`).
  - `--tools` is passed only when the agent's frontmatter declares `tools`. Otherwise the process gets all of pi's default tools.
- **MCP** [D]
  - None. pi has no MCP.
- **Skills** [V][I]
  - The child process does full discovery: `~/.pi/agent/skills` (33), `~/.agents/skills` and pi packages (superpowers). None of the `--no-skills` or `--no-extensions` flags is passed.
- **Slash commands** [D]
  - Not used inside a `-p` run.
- **Instruction files** [V][D]
  - `AGENTS.md`/`CLAUDE.md` from `~/.pi/agent` and cwd upward, because `--no-context-files` is not passed.
  - The extension appends the agent body with `--append-system-prompt`.
- **Model** [V]
  - Frontmatter `model` → `--model`.

### (b) Cross-AI subprocesses (`workflow.cross_ai_command`, `/gsd-review` lanes, ai-kit dispatch)

Each one is a **fresh top-level CLI session**. It loads the target host's complete default surface, as if the user had typed the command. GSD's prompt carries no `agent_skills` block and no persona. The execution prompt is `<objective>` + `<tasks>` + PROJECT.md context, piped on stdin (`elaboration.md:83-97`).

**claude**
- Commands used:
  - GSD lane: `claude --model M --effort E -p -` (`review-lane-descriptor.cjs:116`).
  - ai-kit review: `claude -p --model … --output-format text`.
  - ai-kit execute: `claude -p --restricted --permission-mode acceptEdits` (`commands.py:93-95, 225`).
- Tools: all defaults. `--restricted` drops Bash and WebFetch and "loads only managed settings and `--settings`" [D].
- MCP: all of user, plugin and project MCP. With `--restricted` this is unclear (U4).
- Skills: all skills and plugins.
- Instruction files: the GSD lane disables CLAUDE.md and auto memory via env [V]. ai-kit's builders do not.
- Model: `--model`.

**codex**
- Commands used:
  - GSD: `codex exec --ephemeral --model M <effort> --skip-git-repo-check -o F -`.
  - ai-kit: `codex exec --sandbox read-only|workspace-write --skip-git-repo-check -m M`.
- Tools: sandboxed shell.
- MCP: `codegraph`.
- Skills: 42 from `~/.agents/skills`, plus system skills and plugins (ponytail).
- Instruction files: `~/.codex/AGENTS.md` (which @-imports `RTK.md`) plus the repo `AGENTS.md`.
- Model: `--model` / `-m`.

**opencode**
- Commands used:
  - GSD lane: `opencode run --model M --format json -`.
  - `cross_ai_command`: `opencode run --model router-env/my-coding`.
  - ai-kit: `opencode run -m M [--dir D --auto]`.
- Tools: all.
- MCP: `codegraph` and `gsd`.
- Plugins: superpowers and ponytail.
- Skills: 134 skills (Claude-compat paths) plus superpowers.
- Instruction files: the project `AGENTS.md` and `~/.config/opencode/AGENTS.md`.
- Model: `--model`.

**cursor-agent**
- Commands used:
  - GSD lane: `cursor-agent -p --model M --mode ask --trust --output-format text`.
  - ai-kit: the same, or `--sandbox enabled --workspace D --force --trust`.
- Tools: all.
- MCP: `codegraph`. Neither GSD nor ai-kit passes `--approve-mcps`, so availability is uncertain (U5).
- Skills: `~/.claude/skills` + `~/.agents/skills` + skills-cursor.
- Subagents: **the 35 GSD agents from `~/.claude/agents` are visible** through Cursor's Claude-compat path [D], with their `tools:` ignored.
- Model: `--model`.

**pi**
- No GSD lane; there is no `pi` slug in `review-lane-descriptor.cjs`.
- Through ai-kit, a session would use its full default surface.

## 4. What `agent_skills` does, exactly

Source: `buildAgentSkillsBlock` / `cmdAgentSkills` in `~/.claude/gsd-core/bin/lib/init.cjs:3626-3880`, plus `references/agent-skills-bootstrap.md`. [V]

1. **Shape.** `config.agent_skills.<agent-type>` is a string or an array. Malformed values are warned about and ignored. Config merges from defaults, user and project (`config.cjs:435-438`).
2. **Path form** (`"skills/foo"`).
   - The path must resolve inside the project root (`tryWithinRoot`). Otherwise: "Skipping unsafe path".
   - `<path>/SKILL.md` must exist. If a global skill with the same basename exists, the warning hints "use `global:<name>`".
   - Output line: `- @skills/foo/SKILL.md`.
3. **`global:<name>` form.**
   - The name must match `^[A-Za-z0-9_-]+(:[A-Za-z0-9_-]+)*$`.
   - It resolves to the **current runtime's** global skills dir (`getGlobalSkillsBase(runtime)`). Runtimes without a skills dir warn "does not use a skills directory".
   - The file must exist and pass a containment check. Symlinks that escape are rejected unless `agent_skills_security.trusted_global_roots` covers them.
   - **Relevant here:** 60 of the 134 `~/.claude/skills` entries are symlinks [V]. Any that point outside `~/.claude/skills` need `trusted_global_roots`.
   - Output line: `- @/home/…/.claude/skills/<name>/SKILL.md`.
4. **`global:<plugin>:<skill>` form, Claude only.**
   - When runtime is `claude`, it emits the natural-language directive "Load the `<plugin>:<skill>` skill via the Skill tool before proceeding (plugin-provided)."
   - On any other runtime it is **skipped with a warning** ("requires a Skill-tool-capable runtime (claude)").
   - Implicit constraint: the receiving agent needs the `Skill` tool. **13 GSD agents lack it**, so a plugin directive aimed at, say, `gsd-pattern-mapper` cannot be honoured. [V][I]
5. **Wrapper.** The block is emitted as `<agent_skills>\nRead these user-configured skills:\n…\n</agent_skills>`.
6. **Injection mechanism**, through two seams:
   - **Orchestrator seam.** 44 workflow files run `AGENT_SKILLS_X=$(gsd_run query agent-skills <agent>)` and paste `${AGENT_SKILLS_X}` into the `Agent()` prompt (for example `execute-phase.md:94, 719`; `plan-phase.md:91-93, 782, 1029`).
   - **Self-load seam.** Each consumer agent's init step runs the same query itself, with a dedup guard that skips it when a block is already in the prompt (`agent-skills-bootstrap.md`; `gsd-executor.md:70`).
   - **The `@` lines are not expanded by Claude Code inside an `Agent()` prompt.** GSD's own note: "`@path` never expands inside an Agent() `prompt="..."` string (#3324), so an include arrives as literal text" (`execute-phase.md:693`).
   - So the effect is "here are paths, Read them": one Read tool call per skill, and the full SKILL.md lands in context. Docs on the bootstrap: "`Read` each one before starting work." [V]
7. **Persona fallback on non-Claude runtimes.**
   - When nothing is configured and runtime ≠ `claude`, the query returns the installed agent's `.md` body, or `.compact.md` when `workflow.compact_content` is set. Kimi-style built-in dispatch then carries the GSD persona (`init.cjs:3757-3810`).
   - Today this returns empty on opencode, Codex and Cursor, because no GSD agents are installed there. [V]
   - Command: `GSD_RUNTIME=opencode … query agent-skills gsd-executor --json` → `"block": ""`.
8. **Runtime selection** follows `config.runtime` → `GSD_RUNTIME` env → per-install marker (`config-loader.cjs:1084-1112`).
9. **What it does not do.**
   - It does not restrict the agent's skills, tools or MCP.
   - It does not use Claude Code's native `skills:` preload, which would inject full content at startup with no tool call, capped at 32 names. [D]
   - It does not reach cross-AI subprocesses.

## 5. Knobs that restrict each surface

**Claude Code: per agent (frontmatter or `--agents` JSON)** [D]
- `tools:` allowlist. MCP needs explicit `mcp__<server>` or `mcp__<server>__*`.
- `disallowedTools:`. `mcp__*` removes all MCP tools; `mcp__github` removes one server.
- `mcpServers:`: inline servers that the parent never loads. Ignored for plugin agents.
- `skills:`: preload full content.
- `omitClaudeMd: true` (v2.1.271+): drops user, project and local CLAUDE.md.
- `model`, `effort`, `permissionMode`, `hooks`, `memory`, `isolation`, `background`.
- Plugin agents ignore `hooks`, `mcpServers` and `permissionMode`.

**Claude Code: session-wide** [D]
- `skillOverrides` (`on` / `name-only` / `user-invocable-only` / `off`; not for plugin skills).
- `skillListingBudgetFraction`, `skillListingMaxDescChars`, `SLASH_COMMAND_TOOL_CHAR_BUDGET`.
- Permission rules `Skill` / `Skill(name)`.
- `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (default 3).
- `CLAUDE_CODE_SUBAGENT_MODEL`.
- `PONYTAIL_SUBAGENT_MATCHER`: a ponytail plugin env var that scopes its SubagentStart injection (`hooks/ponytail-subagent.js:8-11`). [V]

**Claude Code: `claude -p` subprocess** [D]
- `--tools` (built-ins only).
- `--disallowedTools "mcp__*"`.
- `--strict-mcp-config --mcp-config <file>`.
- `--setting-sources user,project,local`.
- `--disable-slash-commands`: "Disable all skills and commands".
- `--bare`: skips hooks, skills, commands, subagents, plugins, MCP, auto memory and CLAUDE.md.
- `--safe-mode`, `--restricted`.
- `--append-system-prompt[-file]`.
- `--append-subagent-system-prompt[-file]`.
- `--agents`.
- Env: `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.

**opencode** [D]
- Per agent: `permission` with globs (`"codegraph_*": "deny"`, `skill`, `task`). `tools` is deprecated.
- `opencode run --pure` runs without external plugins. `--agent <name>` selects a restricted agent. [V]
- Env: `OPENCODE_DISABLE_CLAUDE_CODE`, `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT`, `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS`.

**Codex** [D][V]
- Per agent TOML: `mcp_servers`, `sandbox_mode`, `skills.config`.
- `[[skills.config]] enabled=false`.
- `mcp_servers.<n>.enabled=false`, plus `enabled_tools` / `disabled_tools`.
- `codex exec -c key=value`, `-p <profile>`, `--ignore-user-config`, `--ignore-rules`, `--ephemeral`.

**Cursor**
- Per subagent: only `readonly`, `model` and `is_background`. There is no per-subagent tool or MCP filter. [D]
- CLI: `--mode plan|ask`, `--sandbox`, `--approve-mcps`. [V]

**pi**
- `--tools`, `--no-skills`, `--skill <path>`, `--no-extensions`, `--no-context-files`, `--system-prompt`. [D]
- The subagent extension passes only `--tools`, when frontmatter declares it. [V]

## 6. Token-cost implications

Character counts are local measurements; tokens are estimated as chars ÷ 4. [V][I]

**GSD's own payload per spawn dwarfs the inherited surface.**
- `gsd-executor.md` system prompt: 46,790 chars, about 11.7k tokens. planner, plan-checker and verifier are 47–49 KB each.
- The executor's orchestrator-embedded `<execution_context>` adds about 127 KB, roughly 32k tokens: `execute-plan.md` 39 KB, `checkpoints.md` 36 KB, `worktree-path-safety.md` 34 KB, `summary.md` 12 KB, `executor-examples.md` 6 KB.
- Then come the `<required_reading>` files.

**Inherited by a GSD agent on Claude Code:**
- CLAUDE.md files:
  - `~/.claude/CLAUDE.md`: 1.2 KB, about 300 tokens.
  - The ai-kit `AGENTS.md`: 13.5 KB, about 3.4k tokens, when loaded (see U2).
- Skills listing:
  - The full name+description text is 33 KB, about 8.3k tokens, for `~/.claude/skills`, plus 37 plugin skills.
  - Claude Code caps it at 1% of context: about 2k tokens at 200k, about 10k at 1M. [D]
  - [O] In this 1M-context subagent, many entries (most `gsd-*`) arrived **name-only**, which confirms the cap binds.
- MCP schemas: about 0 for GSD agents, because the allowlist excludes all configured servers.
- Hooks: about 715 tokens of ponytail injection on every subagent (`getPonytailInstructions('full')` = 2,859 chars). [V][O]
- Git status snapshot: small.

**Inherited by a default (no `tools:`) Claude subagent, for comparison** [O]
- 48 MCP tools: 22 claude-in-chrome, 25 playwright and 1 codegraph. All arrive **deferred** (names only, schemas fetched through ToolSearch).
- MCP server instructions: codegraph about 344 tokens, plus chrome.
- The agent-type roster in the Agent tool description: about 40 agents with their tool lists, several thousand tokens.
- Measured codegraph schema: 1 tool, 1,762 chars, about 440 tokens. The `gsd` MCP: 3 tools, 961 chars. [V]
- [I] Without tool search, the playwright and chrome schemas would be on the order of 10k+ tokens.

**`agent_skills` cost** is one Read per skill, at full SKILL.md size.
- Ponytail's core SKILL.md is 3,492 chars, about 870 tokens.
- All six ponytail skills total 20,969 chars, about 5.2k tokens.
- Cheap next to the roughly 44k-token executor baseline.
- On Claude, ponytail already reaches every GSD subagent through its SubagentStart hook. Adding `global:ponytail:ponytail` would mostly duplicate that. (This bears on ROADMAP 999.4.) [V][I]

**Cross-AI subprocesses pay the host's full default surface on every call.**
- opencode lists all 134 Claude-compat skills plus superpowers in its `skill` tool, about 8k+ tokens. The docs give no budget (U6).
- Codex caps its skills listing at 2% of context.
- Cursor merges `~/.claude/skills` and `~/.agents/skills` (duplicates) with skills-cursor, and exposes the 35 GSD agents as subagents.

## 7. Open uncertainties

- **U1: Auto memory in subagents.** The docs say "the main conversation's auto memory isn't loaded" for subagents. Yet this research subagent received `MEMORY.md` content in its context [O]. That may be harness- or SDK-specific. Unresolved.
- **U2: AGENTS.md loading.** The docs say ai-kit's `AGENTS.md` should load when there is no CLAUDE.md (v2.1.277+). It was **not** present in this subagent's context [O]. Possible causes: the Agent SDK's setting sources, or the built-in `cc-plugin-agents-md` being unavailable or disabled.
  - Separately, GSD's `claude_md_path: ./CLAUDE.md` points at a missing file. The executor's explicit "Read ./CLAUDE.md" step therefore does nothing.
- **U3: Skills listing scope.** I could not find docs saying whether a subagent without `Skill` in `tools` receives the listing. I did not spawn agents to test this.
- **U4: `@` lines in agent bodies.** GSD's own note confirms that `@` does not expand inside `Agent()` prompt strings. Whether `@~/…` lines inside the **agent definition body** (for example `gsd-executor.md:22, 66, 70`) are expanded is undocumented. [I] They are probably literal, with the agent reading them on demand.
  - Also unclear: what `claude --restricted` does to MCP and skills (the docs mention only settings and tools).
- **U5: Headless MCP without approval.** Whether `cursor-agent -p` loads MCP servers without `--approve-mcps` is not verified. No live run was made.
- **U6: opencode listing limits.** Whether opencode budgets its skill listing, and whether opencode and Codex subagents receive AGENTS.md, are not documented.
- **U7: Deferred MCP with an allowlist.** Not confirmed whether a Claude agent with a `tools:` allowlist that names MCP tools (but not `ToolSearch`) can use them when MCP tools are deferred. It is moot today, since none of the named servers exists.
- **U8: Codex agent files.** The Codex TOML generator itself (`bin/install.js`) is not in the local install. The "no `mcp_servers` emitted" finding is inferred from `codex-agent-toml.cjs` (it handles only `model`, `model_reasoning_effort`, `sandbox_mode` and `developer_instructions`) and the converter.

## Sources

- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code CLI reference: https://code.claude.com/docs/en/cli-reference
- Claude Code memory and AGENTS.md: https://code.claude.com/docs/en/memory
- Claude Code skills: https://code.claude.com/docs/en/skills
- Claude Code env vars: https://code.claude.com/docs/en/env-vars
- opencode: https://opencode.ai/docs/agents/ , https://opencode.ai/docs/skills/ , https://opencode.ai/docs/rules/
- Codex subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex skills: https://learn.chatgpt.com/docs/build-skills.md
- Codex MCP: https://developers.openai.com/codex/mcp
- Cursor: https://cursor.com/docs/agent/subagents , https://cursor.com/docs/context/skills
- pi: local `@earendil-works/pi-coding-agent` README and `examples/extensions/subagent/{index.ts,agents.ts}`
