# Hooks per host: events, ai-kit wiring, machine state, playbook proposal

Research date 2026-11-02. Read-only. Installed versions: Claude Code 2.1.316, Codex CLI
0.162.1, cursor-agent 2026.10.22, opencode 2.0.31, pi 1.3.0, GitHub Copilot CLI 1.0.105,
herdr 0.9.3.

Confidence labels: **doc** = stated in the host's official docs (fetched today); **local** =
read from the installed package or config on this machine; **inferred** = my reading, not
confirmed; **unverified** = open question, needs a spike.

Scripts in this folder: `24_scan.sh`, `24_scan2.sh` (ai-kit code scan), `24_pi_docs.sh` (pi
event list), `24_enabled_hooks.py` (per-host machine inventory, names only, output in
`24_enabled_hooks.out`), `24_post_checkout_probe.sh` (git worktree hook test in a temp repo).

---

## 1. Claude Code hooks (doc: code.claude.com/docs/en/hooks)

### Hook types
- `command` (stdin JSON, default 600 s), `http` (POST), `mcp_tool`, `prompt` (one model turn
  returns a decision, 30 s), `agent` (experimental verifier subagent with Read/Grep/Glob, 60 s).
- `prompt` and `agent` work only on: PreToolUse, PostToolUse, PostToolUseFailure,
  PostToolBatch, PermissionDenied, Stop, SubagentStop, TaskCreated, TaskCompleted,
  TeammateIdle, UserPromptSubmit, UserPromptExpansion (PermissionRequest takes `prompt` but
  not `agent`). SessionStart takes only `command` and `mcp_tool`.
- `async: true` (command only) runs in the background; output arrives next turn.
  `asyncRewake`: an async hook that exits 2 **wakes Claude immediately even when idle**. Under
  `-p`, running async hooks are killed at teardown.
- `once: true` on skill-frontmatter hooks (registered on skill invoke, kept for the session
  unless `once`).

### Exit and output contract
- Exit 0: stdout JSON applied; plain stdout becomes context only on UserPromptSubmit,
  UserPromptExpansion, SessionStart, PostModelSwitch. Exit 2: block (on blockable events),
  stderr is the reason. Other codes: non-blocking, unless `"onFailure": "block"`.
- `additionalContext` / `systemMessage` / `initialUserMessage` capped at 10,000 chars.
- `CLAUDE_ENV_FILE` (SessionStart, Setup, CwdChanged, FileChanged): append `export` lines to
  persist env for later Bash calls. `CLAUDE_PROJECT_DIR` = original project root, even inside a
  worktree session (input `cwd` follows the worktree).

### Every event (matcher in brackets; control after the colon)
- `SessionStart` [startup, resume, clear, compact, fork]: context only (`additionalContext`,
  `initialUserMessage`, `watchPaths`, `sessionTitle`, `reloadSkills`). Input has `source`,
  optional `model`, `agent_type` (with `--agent`).
- `Setup` [init, maintenance]: fires on `--init-only`, or `--init`/`--maintenance` with `-p`.
- `UserPromptSubmit`: block or add context. `UserPromptExpansion` [command name]: block.
- `PreToolUse` [tool]: allow/deny/ask/defer, `updatedInput`, context. `PermissionRequest`
  [tool]: allow/deny. `PermissionDenied` [tool]: `retry`.
- `PostToolUse`, `PostToolUseFailure` [tool]: block, `updatedToolOutput`, context.
  `PostToolBatch`: exit 2 stops the loop.
- `Notification` [permission_prompt, idle_prompt, agent_needs_input, agent_completed, ...]:
  side effects only. `MessageDisplay`: change displayed text.
- `SubagentStart` [agent type]: add context. `SubagentStop` [agent type]: block keeps it
  running, add context.
- `TaskCreated`: block cancels. `TaskCompleted`: block prevents completion. Input `task_id`,
  `task_subject`, optional `task_description`, `teammate_name`, `team_name`. Fires on the
  TaskUpdate tool or when an agent-team teammate ends with in-progress tasks. These are
  Claude's own todo/agent-team tasks, **not** GSD plans or phases (inferred).
- `Stop`: block continues the turn (8-in-a-row cap). `StopFailure` [rate_limit, overloaded,
  authentication_failed, billing_error, server_error, ...]: no control. Input `error`,
  optional `error_details`, `last_assistant_message` (the API error string). The docs list no
  reset-time field; whether `error_details` carries one stays **unverified** (same open
  question as ai-kit's session-wake row).
- `TeammateIdle`: exit 2 keeps the teammate working.
- `InstructionsLoaded` [session_start, nested_traversal, path_glob_match, include, compact].
- `ConfigChange` [user/project/local/policy settings, skills]: block. `CwdChanged`.
  `DirectoryAdded`. `FileChanged` [literal file names].
- `WorktreeCreate`: **replaces** git worktree creation; the hook must create the directory and
  print its path (non-zero exit fails creation). Input `name`. Fires for `claude --worktree`,
  the EnterWorktree tool, subagent `isolation: "worktree"`, workflow agents, background
  sessions, remote-control worktree mode. **Does not fire** for `git worktree add` run through
  Bash (use PreToolUse Bash), and a plugin's hook does not fire with `--worktree --tmux`.
- `WorktreeRemove`: input `worktree_path`; only for hook-created worktrees. Subagent and
  workflow worktrees are kept and do not fire it.
- `PreCompact` [manual, auto]: can block. `PostCompact` [manual, auto]: no control.
- `PreModelSwitch` / `PostModelSwitch` [model name]. `Elicitation` / `ElicitationResult`
  [MCP server]. `SessionEnd` [clear, resume, logout, prompt_input_exit, other]: 1.5 s budget.

### Where configured
- `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, managed
  policy, plugin `hooks/hooks.json` (or a `hooks` path in `plugin.json`), skill frontmatter
  (from invoke on), subagent frontmatter (only while it runs; its `Stop` becomes
  `SubagentStop`). All levels merge. `disableAllHooks`, `allowManagedHooksOnly`.
- The `/hooks` menu browses configured hooks (doc mention; not re-read in detail today).

### Does it fire there?
- **Subagents** (doc): settings, managed and plugin hooks run inside subagents; tool-event
  input carries `agent_id` and `agent_type`. SessionStart does not run per subagent;
  SubagentStart/SubagentStop do (inferred from the event split).
- **`claude -p` / SDK** (doc): settings hooks run; the folder is treated as trusted (a repo's
  committed `.claude/settings.json` hooks run without a trust prompt). Project subagent
  frontmatter hooks do not run under `-p` unless trust was accepted interactively.
  `--settings '{"disableAllHooks": true}'` or `--bare` turns them off. Whether Agent SDK
  sessions load file hooks depends on its setting sources (**unverified**).
- **Worktrees** (doc): hooks fire normally; `CLAUDE_PROJECT_DIR` stays the original root, so
  a script that needs the worktree must read `cwd` from the input.
- **herdr panes**: the host is a normal interactive process, so all user and project hooks
  fire (inferred). Identity: `HERDR_ENV=1`, `HERDR_PANE_ID`, `HERDR_SOCKET_PATH` (local, from
  `12-herdr-and-review-lanes.md`).

---

## 2. Other hosts (official docs, plus installed package where noted)

### Codex CLI (doc: learn.chatgpt.com/docs/hooks; redirect from developers.openai.com)
- Events: SessionStart [startup, resume, clear, compact, fork], SessionEnd, SubagentStart,
  SubagentStop, PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact
  [manual, auto], UserPromptSubmit, Stop, PreModelRequest, PostModelRequest (sees `status`,
  `error`, `token_usage`), Interrupt. Names and payloads mirror Claude's PascalCase style.
- Config: `~/.codex/hooks.json`, `~/.codex/config.toml [hooks]`, `<repo>/.codex/...` (only
  when the project layer is trusted), plugin `hooks/hooks.json`, managed `requirements.toml`.
  On by default; `[features] hooks = false` turns off (`codex_hooks` deprecated alias).
- **Trust gate**: non-managed hooks must be approved via `/hooks` before they run; changed
  hooks need re-approval. `--dangerously-bypass-hook-trust` skips it for one run. This matters
  for unattended `codex exec` lanes (behaviour under `exec` not stated: **unverified**).
- Subagents: SubagentStart/Stop fire; SessionEnd and Interrupt do not run for subagents.
- Gaps vs Claude: no WorktreeCreate/Remove, no StopFailure (PostModelRequest can observe an
  error, approximation), no TaskCompleted, no FileChanged/CwdChanged, no async/rewake, no
  prompt/agent hook types.

### Cursor (doc: cursor.com/docs/agent/hooks)
- Events: sessionStart (env + `additional_context`), sessionEnd, preToolUse, postToolUse,
  postToolUseFailure, subagentStart (allow/deny), subagentStop (`followup_message`),
  beforeShellExecution, afterShellExecution, beforeMCPExecution, afterMCPExecution,
  beforeReadFile, afterFileEdit, beforeSubmitPrompt, preCompact (observe only), stop
  (`followup_message` auto-submits a next message), afterAgentResponse, afterAgentThought,
  Tab events, workspaceOpen.
- Config: enterprise `/etc/cursor/hooks.json`, team (dashboard), project
  `<repo>/.cursor/hooks.json`, user `~/.cursor/hooks.json`, plugins.
- Cloud/background agents: only project hooks; no sessionStart/sessionEnd there.
  Whether agent hooks fire in the `cursor-agent` CLI is not stated (**unverified**; ai-kit's
  briefing is wired there anyway).
- Gaps: no worktree event, no post-compact, no rate-limit event, no task event.

### opencode (doc: opencode.ai/docs/plugins; installed v2.0.31)
- Plugin hooks: `tool.execute.before` (mutate args, block by throwing), `tool.execute.after`,
  `shell.env` (inject env), `experimental.session.compacting` (push context or replace the
  compaction prompt), `permission.*`.
- Bus events (observe): session.created, session.compacted, session.deleted, session.diff,
  session.error, session.idle, session.status, session.updated, message.*, file.edited,
  file.watcher.updated, command.executed, todo.updated, permission.asked/replied, lsp.*,
  tui.*, server.connected, installation.updated.
- Config: `~/.config/opencode/opencode.json(c)` `plugin` array (npm), project
  `opencode.json`, `~/.config/opencode/plugins/`, `<repo>/.opencode/plugins/`.
- The doc says nothing on child sessions (subagents) or `opencode run` (**unverified**;
  child sessions likely emit session.created with a parent id, inferred).
- No session-start context injection is documented (ai-kit README records this gap).
  `session.idle` is the nearest "turn done" signal; `session.error` the nearest quota signal.

### pi (local: installed `docs/extensions.md` and `dist/core/extensions/types.d.ts`)
- `pi.on()` events: project_trust, resources_discover, session_start, session_info_changed,
  session_before_switch, session_before_fork, session_before_compact, session_compact,
  session_compact_failed, session_shutdown, mcp_servers_change, session_before_tree,
  session_tree, context, context_with_system, cache_warming_decision,
  before_provider_request, before_provider_headers, after_provider_response,
  provider_stream_event, before_agent_start, agent_start, agent_end, agent_before_settle,
  agent_settled, ui_prompt_start/end, turn_start, turn_end, message_start/update/end,
  tool_execution_start/update/end, model_select, thinking_level_select, tool_call,
  tool_result, user_bash, input.
- Control: `tool_call` can mutate or block (a handler failure blocks the tool);
  `tool_result` composes; `before_agent_start` can add a message or change the prompt;
  `turn_end` / `agent_before_settle` can request one continuation.
- Config: `~/.pi/agent/extensions/`, project extensions dir, settings `packages`.
  Extensions load in interactive, RPC, JSON and print modes (doc: "Extensions load in
  interactive, RPC, JSON, and print modes").
- No native subagents (this machine has a user `subagent` extension), no worktree event, no
  stop-failure event (`after_provider_response` can observe a 429: approximation).
- **Finding**: ai-kit's README calls pi session-start a gap ("no verified session-start
  route"), but pi 1.3.0 has `session_start` plus `before_agent_start` for injection. Worth a
  re-check spike (inferred; the gap may have been recorded against an older pi).

### GitHub Copilot CLI (doc: docs.github.com/en/copilot/reference/hooks-configuration)
- Events: sessionStart (inject context), sessionEnd, userPromptSubmitted,
  userPromptTransformed, preToolUse (allow/deny/ask/modify), postToolUse, postToolUseFailure,
  permissionRequest, preCompact (observe), subagentStart (prepend context), subagentStop
  (block or replace response), agentStop (block), errorOccurred, notification.
- Config: policy `/etc/github-copilot/policy.d/*.json`, repo `.github/hooks/*.json`, user
  `~/.copilot/hooks/*.json`, inline `hooks` in `.github/copilot/settings*.json`,
  **`.claude/settings.json` and `.claude/settings.local.json`**, `~/.copilot/settings.json`,
  plugins, agent frontmatter. PascalCase names switch to Claude-style payloads.
- **Finding**: Copilot reads a repo's `.claude/settings*.json` hooks. A project-level Claude
  hook (for example GSD's hooks in this repo's `.claude/settings.local.json`) can fire under
  Copilot too. Scripts must tolerate that (inferred risk).
- Subagents: start/stop fire except for the built-in `general-purpose` agent. `-p` mode:
  `prompt` hooks do not fire.

### Mapping of the owner's example events
Status words: **native** (a real event), **approx** (a nearby event or a side effect),
**none**.

- **Session start** — Claude native (SessionStart startup/resume); Codex native; Cursor
  native (not in cloud); opencode approx (session.created, no injection); pi native
  (session_start + before_agent_start); Copilot native.
- **Worktree created → `make setup-dev` / `setup-docker`** — Claude native but only for
  Claude-made worktrees, and the hook *replaces* creation (it must run `git worktree add`
  itself, then set up, then print the path); every other host none. **Host-neutral approx**:
  git's own `post-checkout` hook runs after `git worktree add` (unless `--no-checkout`) with an
  all-zero previous ref, so one git hook covers every host and Bash-made worktrees (pre-commit
  supports a `post-checkout` stage). **Local, verified today** with
  `24_post_checkout_probe.sh` (git, throwaway repo): the hook ran inside the new worktree with
  `prev=0000…0000 flag=1`. Caveat (inferred): `.git/hooks` is shared by all worktrees of a
  repo, so it must be installed once per clone, and it does not exist in a fresh clone until
  `make dev` / `pre-commit install` runs. Also approx everywhere: SessionStart where `cwd` is a
  linked worktree with no setup marker.
- **Worktree destroy at end of phase/plan** — Claude WorktreeRemove only for hook-made
  worktrees; none elsewhere. This is a workflow step, not a host event.
- **End of phase / plan / task (compact commits, local or cloud e2e, wait for CI, PR review
  loop)** — no host has phase or plan events. Claude TaskCompleted is its own todo list
  (approx at best). Real approx on all hosts: PostToolUse on a Bash command matching the
  workflow's own markers (`gsd-tools ... phase complete`, `git push`, `gh pr create`); the
  GSD tree here already does this kind of thing (`gsd-phase-boundary.sh`). Best fit: the
  workflow skill calls the playbook at that step, the hook is only a safety net.
- **Wait for CI / read automated review** — none as an event anywhere. Claude approx:
  PostToolUse on `git push` starting an `asyncRewake` command that runs `gh run watch` and
  exits 2 when CI ends, waking the idle session (doc mechanism; this use is untested). Other
  hosts: poll inside the playbook.
- **Quota / rate-limit wake** — Claude native (StopFailure `rate_limit`, reset time not
  documented); Codex approx (PostModelRequest observes error); Cursor none; opencode approx
  (session.error); pi approx (after_provider_response); Copilot approx (errorOccurred).
- **Subagent stop** — Claude, Codex, Cursor, Copilot native; opencode approx (child session
  events, unverified); pi none (extension-defined).
- **Pre / post compact** — Claude both; Codex both; Cursor pre (observe); opencode pre
  (experimental.session.compacting) and post (session.compacted); pi both
  (session_before_compact, session_compact); Copilot pre (observe).

---

## 3. ai-kit today

### Shipped hooks (registry `tools/setup.py:1770-1823`, ids `HOOK_IDS` :1825)
- `session-briefing` — Claude SessionStart `startup|compact`
  (`CLAUDE_HOOK_EVENT/MATCHER` :1723-1724) → `tools/hooks/claude_session_start.py`; Cursor
  `sessionStart` (:1729) → `tools/hooks/cursor_session_start.py`. Default on.
- `tool-advisor` — Claude PreToolUse `Bash|Read` → `tools/hooks/claude_tool_advisor.py`;
  pi `tool_result` → `tools/hooks/pi/ai-kit-tool-advisor.ts:70`. Default on. Shared core
  `tools/hooks/advisor_core.py` (`advise` :393, `installed_tools` :153 via `detect.py`).
- `tool-reminder` — Claude PostToolUse `Bash` → `claude_tool_reminder.py`; pi `tool_result`
  → `pi/ai-kit-tool-reminder.ts:69`. Default on.
- `decision-probe` — Claude SessionStart `startup` → `claude_decision_probe.py`. Default off.
- `precompact` — Claude PreCompact `manual|auto` + SessionStart `compact` →
  `claude_precompact.py`; pi `session_before_compact` → `pi/ai-kit-precompact.ts:136`;
  opencode `experimental.session.compacting` → `opencode/ai-kit-precompact.ts:127`
  (experimental). Shared core `precompact_core.py`. Default derived from
  `PRECOMPACT_VERDICTS` (:1745), all `unmeasured`, so off.
- `session-wake` — Claude StopFailure `rate_limit` → `claude_session_wake.py`; experimental,
  default off. It calls `ai-kit-session-wake arm --only-if-armed`; the wake itself is a
  systemd user timer owned by `skills/ai-kit-session-wake/` (not a hook).
- "Tool-substitution" is now the briefing plus the two advisors; the old rtk probe was dropped
  (21.3 decision D-10). Status lines are not hooks: `wire_statusline` :2188 (Claude
  `statusLine`), `wire_statusline_cursor` :2484, hosts `STATUSLINE_HOSTS` :54 (claude, cursor).

### Knobs
- Registry row shape `HookRow` (:1734): id, host, event, matcher, script, default,
  experimental, verdict, timeout. One row per id × host × event (21.3 D-02/D-03).
- Headless: `install --headless --with-hooks[=<id[:host],...>]` (:4760-4764; bare wires
  defaults, additive only, 21.3 D-04/D-05); `uninstall --hooks=<id[:host],...>` (:4765,
  per-id removal). Parser `parse_hook_selector` :1828, `hook_rows` :1847.
- Wizard: the `hooks` category; `_hook_selection_items` :3435 (on = installed, or default and
  host dir present), `apply_hook_selection` :3617, row text `hook_description` :2868;
  `tools/wizard_app.py:810-824` keeps hooks out of the component count.
- Wiring: Claude via guarded JSON edit `wire_claude_rows` :2033; Cursor `wire_hook_cursor`
  :2082; pi and opencode via owned symlinks `hook_link_path` :4272 into
  `~/.pi/agent/extensions/` and `~/.config/opencode/plugins/`; `wire_hook_rows` :4292,
  `unwire_hook_rows` :2808; presence `hook_host_present` :4265 (config dir exists).
- Granularity today: per hook id × host, user scope only. No per-project, per-event or
  per-run-context (direct, herdr, subagent, subprocess) knob. Codex has no ai-kit row at all
  (README "gap (no verified hook route)", now outdated: Codex hooks are on by default and
  Claude-shaped).

### Reporting
- `hook_installed_hosts` (:2831) computes "installed on which hosts" per id, but only the
  wizard uses it. `setup.py doctor` / `check` (:4559, :4567) delegate to
  `statusline-doctor.py` (status line only). Config doctor reads Codex `features.hooks`
  (`tools/config_doctor_checks.py:460`, row :806) as a setting, not as a hook list.
- **Nothing reports "which hooks are enabled here" per host**, and nothing lists foreign hooks
  (GSD, herdr, plugins) or says whether a hook fires in a subagent or subprocess.
- Host coverage table: `tools/hooks/README.md:28-36`.

### Phase 21.3 decisions in brief (`.planning/milestones/v1.3-phases/21.3-*/21.3-CONTEXT.md`)
- Keep briefing script names; one entry script per id × host over shared cores; rows live in
  the wizard's hooks category; headless install additive with per-id uninstall; defaults
  briefing/advisor/reminder on, decision-probe off, precompact by verdict.
- Hooks advise only: never approve, deny, block or rewrite a tool call; fail-open.
- pi gets `tool_result`-only files (a `tool_call` failure would block the tool).
- opencode advisors were a spike (S-OC in `21.3-LIVE.md`) ending in README gap rows.

---

## 4. Enabled on this machine now (names only; `24_enabled_hooks.out`)

- **Claude, `~/.claude/settings.json`**: SessionStart `startup|compact` →
  claude_session_start.py; SessionStart (all sources) → herdr-agent-state.sh; SessionStart
  `startup` → claude_decision_probe.py (default-off row, turned on); SessionStart `compact` +
  PreCompact `manual|auto` → claude_precompact.py (default-off row, turned on);
  UserPromptSubmit → `codegraph prompt-hook`; PreToolUse `Bash|Read` → claude_tool_advisor.py;
  PostToolUse `Bash` → claude_tool_reminder.py. **session-wake not wired.**
- **Claude plugins** (6 enabled): ponytail (SessionStart, SubagentStart, UserPromptSubmit via
  `hooks/claude-codex-hooks.json`), superpowers (SessionStart); the other four ship no hooks.
- **Claude, this repo `.claude/settings.local.json`** (GSD, project-local): SessionStart →
  gsd-check-update.js, gsd-session-state.sh; PreToolUse → prompt/read/workflow/
  worktree-path/agent-isolation/write/secret-read guards, gsd-validate-commit.sh;
  PostToolUse → gsd-context-monitor.js, gsd-read-injection-scanner.js,
  gsd-graphify-update.sh, gsd-phase-boundary.sh; SubagentStop, Stop, PreCompact →
  gsd-context-monitor.js; FileChanged `config.json` → gsd-config-reload.js. No
  `.claude/settings.json` in the repo.
- **Cursor `~/.cursor/hooks.json`**: sessionStart → cursor_session_start.py,
  herdr-agent-state.sh. No project file.
- **Codex**: `~/.codex/hooks.json` is empty; `features.hooks = true`; `config.toml
  [hooks.state]` still holds 13 trust hashes for earlier hook entries (pre_tool_use,
  session_start, subagent_start, ...). No active Codex hooks.
- **opencode**: `~/.config/opencode/plugins/herdr-agent-state.js`; npm plugins superpowers
  and ponytail. The ai-kit precompact plugin is **not** linked (matches its default off).
- **pi** `~/.pi/agent/extensions/`: ai-kit-precompact.ts, ai-kit-tool-advisor.ts,
  ai-kit-tool-reminder.ts (all ai-kit links), plus a user `subagent/` extension.
- **Copilot**: no `~/.copilot/hooks/`, no `.github/hooks/`. It would still read this repo's
  `.claude/settings.local.json` hooks if run here (doc behaviour, not tested).
- Run context visible from env right now: `HERDR_ENV`, `HERDR_PANE_ID`, `CLAUDECODE`,
  `CLAUDE_CODE_ENTRYPOINT` are set (this session runs inside herdr).

---

## 5. Proposal outline (all of it is a proposal, not verified design)

### Event catalogue (common names, then per-host source)
- `session-start` — Claude SessionStart startup|resume; Codex SessionStart; Cursor
  sessionStart; pi session_start (+ before_agent_start to inject); Copilot sessionStart;
  opencode session.created (observe only, gap for injection).
- `session-compacted` — Claude SessionStart compact / PostCompact; Codex PostCompact; pi
  session_compact; opencode session.compacted; Cursor and Copilot gap.
- `before-compact` — Claude/Codex PreCompact; Cursor/Copilot preCompact; pi
  session_before_compact; opencode experimental.session.compacting.
- `worktree-created` — git `post-checkout` (host-neutral, primary); Claude WorktreeCreate as
  an optional wrapper for Claude-made worktrees only.
- `subagent-start` / `subagent-stop` — Claude, Codex, Cursor, Copilot native; pi and opencode
  gap.
- `turn-stop` — Claude/Codex Stop, Cursor stop, Copilot agentStop, pi agent_settled, opencode
  session.idle.
- `rate-limited` — Claude StopFailure rate_limit; approximations elsewhere as in section 2.
- `workflow-milestone` (phase-done, plan-done, task-done, pushed, pr-opened) — not a host
  event. Raised by the workflow skill itself, with a PostToolUse Bash marker match as backup.

### Knob model
- Keep host wiring as today (registry rows, one dispatcher entry per host × event), but make
  the wired script a **single thin dispatcher** that reads knobs at fire time. Toggling then
  needs no host-config rewrite, and a project can turn an event off without touching user
  config.
- Knob layers, last wins: built-in defaults → user `~/.config/ai-kit/hooks.toml` → project
  `<repo>/.aikit/hooks.toml` (same `.aikit/` home as `review-spec.toml`). Per event:
  `enabled`, `hosts = [...]`, `contexts = ["direct", "herdr", "subagent", "subprocess"]`,
  `playbook = "<name>"`.
- Run context detection, cheapest reliable first: an `AI_KIT_RUN_CONTEXT` env var set by
  ai-kit's own launchers (runner_dispatch, cross-ai runner, herdr pane `--env`); else
  `HERDR_ENV=1` → herdr; hook input `agent_id`/`agent_type` (Claude) or
  `agentId`/`parentAgentId` (Copilot) → subagent; else direct. `subprocess` without the env
  var is not reliably detectable (unverified; `CLAUDE_CODE_ENTRYPOINT` values untested).

### Status report command
- `setup.py hooks status [--project <dir>] [--json]` (name open). Per host: ai-kit rows
  installed (reuse `hook_installed_hosts`), the effective knob per event for this project and
  context, foreign hooks by name only (GSD, herdr, plugins, as `24_enabled_hooks.py` does),
  and a static "fires in subagent / `-p` / herdr" column marked doc, local or unverified. Also
  flag Codex trust-pending entries and Copilot reading `.claude/settings*.json`.
- Could also be a row group in config doctor; keep one source for the capability table
  (beside `HOOK_REGISTRY` or the `RUNTIMES` table in `detection.py`).

### Hand-off to the playbook skill
- The dispatcher holds no project logic. On an enabled event it emits one short context line,
  e.g. `ai-kit event worktree-created at <cwd>: load skill ai-kit-project-rules-playbook,
  playbook worktree-created`, through each host's injection field (Claude/Codex
  `additionalContext`, Cursor `additional_context`, pi appended message, Copilot context).
- Events where no agent is listening (git `post-checkout`, a dead session on rate limit) need
  a deterministic action. Let a playbook declare a small `run:` list (for example `make
  setup-dev`) that the dispatcher may execute with a timeout and fail-open, separate from the
  `advise:` text meant for the agent. Every `run:` stays opt-in per project.
- Keep 21.3's rule: hooks advise; they never block or rewrite. A future "block until tests
  pass" gate (TaskCompleted, Stop) would be a separate, explicitly opt-in knob.

### Open questions for a spike
- Does Claude's StopFailure `error_details` carry a reset time?
- Do pi `session_start` + `before_agent_start` deliver a visible briefing (README gap may be
  stale)?
- opencode: do plugins fire in child sessions and `opencode run`?
- Cursor: do agent hooks fire in `cursor-agent` CLI?
- Codex: do trusted hooks run under `codex exec`, and does an unattended lane need
  `--dangerously-bypass-hook-trust`?
- Copilot: confirm it runs a repo's `.claude/settings*.json` hooks, and with what payload.
- Does `asyncRewake` work for a CI-watch hook started from PostToolUse on `git push`?
