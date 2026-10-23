# 10: Cross-AI runtimes reference (non-interactive execution and review)

Date: 2026-10-13. Scope: how to call cursor-agent, opencode, grok, pi and codex non-interactively. Each runtime gets (a) full-permission execution (no sandbox, no ask or plan mode, no permission waits) and (b) read-only review. Claude is the host and never a target.

This document is shaped to become `skills/ai-kit-spec-review/references/cross-ai-runtimes.md`. Sections 1–4 are the reusable reference. Sections 5–7 are the drift audit, the script and the generator design for ai-kit-gsd-curated-config.

Paths:
- `P/` = `scratchpad/xai-probe/` (probe logs: `<label>.argv.txt`, `.stdout.txt`, `.stderr.txt`, `.result.txt`; help captures in `P/help/`).
- `R/` = `scratchpad/research/`.

Confidence tags:
- **[L]** live-tested here;
- **[H]** local `--help` or `inspect` output;
- **[D]** official docs;
- **[06]/[08]** taken from an earlier report;
- **[I]** inference;
- **[U]** unverified.

---

## 0. Ranked findings

1. **All three of the user's installed runtimes ran a plan unattended on the first try, using the formulas below.** [L] Each created the file, ran the shell command and committed. None waited for permission.
   - cursor-agent `auto`: 45.9 s, commit `39bf976`.
   - opencode `opencode/big-pickle` (free Zen model): 26.7 s, commit `cff3781`.
   - grok `grok-4.7-build-fast`: 25.0 s with plain output and 12.5 s with JSON output; $0.066 per run.
   - Evidence: `P/{cursor,opencode,grok,grok-json}.result.txt`.
2. **Read-only review modes also held.** [L] cursor `--mode ask` and opencode `--agent plan` made no writes and no commit, and they did not stall. opencode `plan` without `--auto` still ran a read-only `git status` and exited 0 in 13.8 s. That answers report 08's open question about stalls. Evidence: `P/cursor-ask.result.txt`, `P/opencode-plan.result.txt`.
3. **grok cannot be expressed as a raw `cross_ai_command` with `-p`.**
   - `-p` is `--single <PROMPT>`, so it takes the prompt as its value [H]. The old ai-kit builder therefore needs `sh -c '... -p "$(cat)"'`, which GSD's no-shell word-split breaks [08].
   - The fix is `--prompt-file /dev/stdin` [L].
   - grok's `text` field concatenates every assistant message with no separator: `"...report the short hash.## Summary"` [L `P/grok-json.stdout.txt`]. The wrapper re-breaks the glued heading.
4. **grok silently imports the whole Claude Code setup.** `grok inspect` lists 191 skills (including `~/.claude/skills`), 5 Claude plugins (superpowers, ponytail, ...), 21 hooks, the `codegraph` MCP from `~/.claude.json`, and permissions from `~/.claude/settings.json` [H `P/help/grok-inspect.txt`].
   - The binary contains `GROK_CLAUDE_{SKILLS,HOOKS,MCPS,RULES,AGENTS}_ENABLED`. Setting them to `0` or `false` changed nothing in `grok inspect` [L]. **There is no verified per-run off switch.**
   - All three executors' replies carried the user's global "Skipped: ... Risk: ..." house style [L stdout files], so global rules and skills bleed into headless runs on every host.
5. **codex: an expired login is a fatal error that `codex login status` does not detect.** [L] The exec run failed in 8.2 s with exit 1 and `401 token_expired` / `invalid_refresh_token`, and made no commit (`P/codex.result.txt`). Yet `codex login status` printed "Logged in using ChatGPT".
   - The wrapper classifies this as fatal, never retries it, and falls back to the next CLI only because the repo is untouched.
   - The codex success path is therefore **unverified** in this session.
6. **pi is not installed now.** `command -v pi` fails. The pnpm global bin has only `gsd-pi`, which is `@opengsd/gsd-pi`, GSD's pi *installer*. The Volta pi 0.82.1 that report 06 used is gone. `~/.pi/agent/` config remains.
   - The pi formula below comes from report 06 (live on 0.82.1) and pi.dev docs. **pi was not live-tested in this session.**
7. **opencode 1.18.35 default-format stdout is now clean final text.** [L] The ANSI tool trace goes to stderr.
   - So `xai_exec.sh`'s ANSI strip and heading search [08] is no longer needed for `--format default`.
   - `--format json` (home-mobility's value) writes raw JSONL to stdout. GSD would store that event soup as SUMMARY.md.
8. **Five of the six hand-written project values are wrong** (§5). The commonest error is opencode without `--auto`. None of them scrub `CLAUDECODE`, which 16-HANDOFF says must be unset.
9. **The new `cross-ai.mjs` replaces report 08's Python `xai` wrapper.**
   - It is stdlib-only, about 480 lines, and generated per project.
   - Its self-test makes no model call: it checks the parsers, the classifier, the argv invariants, and spawn, retry and timeout with a fake CLI.
   - It was checked end to end through GSD's real `run-with-timeout`: fallback from pi to cursor, inner deadline exits 124, and no orphan is left when GSD's outer timeout fires first (§6).

---

## 1. The GSD contract every formula must satisfy

Source: `~/.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:74,99-120` (gsd-core 1.16.0) [H].

- Invocation: `echo "$TASK_PROMPT" | gsd_run run-with-timeout "${CROSS_AI_TIMEOUT}" -- ${CROSS_AI_CMD} > "$CANDIDATE_SUMMARY" 2>"$ERROR_LOG"`.
- The prompt arrives on **stdin**. stdout **is** the SUMMARY.md candidate, and stderr is only shown on failure.
- The cwd is the **project root**.
- `${CROSS_AI_CMD}` is **word-split with no shell**:
  - quotes, `$(...)`, `sh -c '...'` and any token containing whitespace cannot work;
  - absolute paths with spaces cannot work either [08 §1.3].
- `cross_ai_timeout` defaults to 300 s. `run-with-timeout` exits 124 on timeout, SIGTERMs the child's process group and SIGKILLs it 3 s later [08 §1.6].
- Success needs exit 0 plus a summary with "at least a heading and description". Failure offers retry, which is a **fresh run over a possibly dirty tree**, skip (native executor) or abort.

## 2. Cross-runtime rules (the slips agents keep making)

1. **Always pass `--model` / `-m` explicitly.** The user's interactive `cursor-agent` is a shell function that adds `--model gpt-5.6-sol-high`. Scripts and GSD's argv spawn never see it, so a command that "worked in my shell" runs a different model under GSD.
   - Defaults also differ per machine: pi defaults to gpt-5.6-terra at xhigh [06]; grok defaults to grok-4.7; codex's `config.toml` sets gpt-5.6-luna.
2. **Resolve the real binary on PATH and never rely on functions or aliases.**
   - `cursor-agent` and `agent` both point to `~/.local/share/cursor-agent/versions/2026.10.01-e373342/cursor-agent`.
   - `grok` points to `~/.grok/downloads/grok-1.0.52-linux-x86_64`.
   - `opencode` is `~/.opencode/bin/opencode`, and `codex` is `~/.local/bin/codex` (a second copy sits in the pnpm bin) [H].
3. **Close stdin.** Pipe the prompt, or use `< /dev/null`. pi waits forever on an open non-TTY stdin [06]. All probes here piped the prompt and hit EOF.
4. **Pass permission flags explicitly even when the local config already allows everything.** Local configs vary per machine:
   - `~/.cursor/cli-config.json` has `sandbox.mode: disabled` and `approvalMode: allowlist`;
   - `~/.grok/config.toml` has `[ui] permission_mode = "always-approve"`;
   - opencode has no `permission` block.

   A machine with different configs would sandbox or prompt.
5. **Scrub host env signals.** `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT` are set inside Claude Code [H `env`]. 16-HANDOFF:193 says `CLAUDECODE` must be unset for opencode. ai-kit's own host detection keys on `CLAUDECODE`, `OPENCODE`, `CURSOR_AGENT` and `PI_CODING_AGENT` [08].
6. **Never rely on a CLI's own timeout.** None of the four has a wall-clock limit flag; grok `--max-turns` limits turns, not time. Use an inner deadline below GSD's outer one, and kill the CLI's process group.
7. **Prefer machine-readable output, then extract the final message.** Never store raw JSON events as the SUMMARY.

## 3. Per-runtime reference

### 3.1 cursor-agent (2026.10.01-e373342)

**Execute, full permissions** [L `P/cursor.argv.txt`, rc 0, 45.9 s, no wait, commit `39bf976`]:
```
cursor-agent -p --model auto --output-format text --trust --force --sandbox disabled --approve-mcps   < prompt
```
- The wrapper uses `--output-format json` instead. It is the same run but returns `{type:"result", result, session_id, is_error, usage}` on one line [L `P/cursor-ask.stdout.txt`].
- The prompt is read from **stdin** with `-p` and no positional argument [L].
- `--workspace <dir>` defaults to the cwd [H]. The wrapper passes it explicitly.

**Review, read-only** [L `P/cursor-ask.result.txt`, rc 0, 14.8 s, no files, no commit]:
```
cursor-agent -p --model auto --mode ask --trust --output-format json   < prompt
```
- `--mode plan` is also read-only ("analyze, propose plans, no edits") [H].
- `--trust` is still needed, because the trust prompt is independent of the mode.

**Permissions:**
- `-p/--print`: "Has access to all tools, including write and shell" [H].
- `-f/--force` (alias `--yolo`): "Force allow commands unless explicitly denied" [H]. "Without --force, changes are only proposed, not applied" [D headless].
- `--trust`: "Trust the workspace without prompting (headless mode only)" [D parameters]. Without it a fresh directory stops at "Workspace Trust Required" [08, commands.py live finding].
- `--sandbox enabled|disabled` overrides config [H]. **Pass `disabled`.** `enabled` does not confine writes anyway [06].
- `--approve-mcps`: "Automatically approve all MCP servers" [H]. Without it, headless MCP calls may wait [U].
- Do not use `--auto-review`: its server classifier "prompts for the rest" [H], which stalls headless runs [I].
- Config-level `permissions.allow/deny` in `~/.cursor/cli-config.json` (`Shell(git log)`, ...). Explicit denies survive `--force` ("unless explicitly denied") [H].

**Strip or restrict:**
- Skills, rules and agents: no per-run flag [H]. Cursor loads its own `~/.cursor/skills-cursor` (22 bundled [07]) plus user rules. `--plugin-dir` only *adds*.
- MCP: `cursor-agent mcp disable <id>` persists to config, so it is not per run [H]. There is no `--no-mcp`.
- Tools: only by mode (`ask`/`plan` are read-only) or by config permissions.
- Slash commands: not applicable in `-p`.
- Hooks: `~/.cursor/hooks.json` exists on this machine. Whether hooks fire in `-p` is [U].

**Bash tool:** the shell tool runs everything under `--force` except explicit denies. To block `git push` while staying otherwise unlimited, add a config deny rule (a per-machine config edit). No per-run flag exists.

**Model:**
- `--model <id>` and `--list-models`, or `cursor-agent models` [H `P/help/cursor-models.txt`].
- On this machine: `auto` (the default), `composer-2.5`, `composer-2.5-fast`, `grok-4.7-{low..xhigh}[-fast]`, `cursor-grok-4.{5,6}-*`, gpt-5.x, claude-*, gemini-*.
- Parameterized ids such as `'claude-opus-4-8[effort=high]'` contain no spaces, so they survive word-split [H].

**Session:** `--resume [chatId]`, `--continue`, and `create-chat` (which returns an id) [H]. The JSON `session_id` is the chatId for `--resume` [L shape; resume itself U].

**Timeout and exit:** no time flag. Exit codes are undocumented [D]; 0 was observed on success. JSON `is_error:true` is the reliable failure signal.

### 3.2 opencode (1.18.35)

**Execute, full permissions** [L `P/opencode.argv.txt`, rc 0, 26.7 s, no wait, commit `cff3781`, cost 0]:
```
opencode run --model opencode/big-pickle --auto   < prompt
```
- Default format: stdout is clean final text (269 B, no ANSI), and the tool trace with ANSI goes to stderr [L].
- The wrapper uses `--format json` to also get `sessionID`. It rebuilds the answer from the last message's `type:"text"` parts, the same way GSD's own opencode lane does [08].
- The prompt comes from **stdin** [L]. `--dir` is only needed when the cwd differs.

**Review, read-only** [L `P/opencode-plan.result.txt`, rc 0, 13.8 s, no writes]:
```
opencode run --model opencode/big-pickle --agent plan --format json   < prompt
```
- The built-in `plan` agent declined to write ("Plan mode is active, so I can't write files"), ran a read-only bash command, and did **not stall** without `--auto`.

**Permissions** [D permissions]:
- Keys: `read`, `edit` (covers edit/write/patch), `glob`, `grep`, `bash` (matched by parsed command), `task` (subagents), `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, `doom_loop`.
- Most keys default to `allow`. `external_directory` and `doom_loop` default to `ask`. `.env` reads are denied.
- `--auto`: "auto-approve permissions that are not explicitly denied (dangerous!)" [H]. **Explicit `deny` rules are still enforced** [D]. That makes opencode the one runtime where "unlimited except `git push`" is a per-run flag:
  - `OPENCODE_PERMISSION='{"bash":{"git push*":"deny"}}'`, as an env var on the child; it is not in the GSD string.
  - The parsed-command pattern syntax is [D]; this particular rule is [U] live.
- Without `--auto`, an `ask` (for example reading `~/.claude/skills/...` through `external_directory`) has no human to answer it. The plan-agent run did not hit an `ask`, so stall-versus-reject for a real `ask` is still [U].

**Strip or restrict** [D cli env table]:
- Skills:
  - `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` hides `.claude/skills`.
  - `OPENCODE_DISABLE_CLAUDE_CODE=1` disables `.claude` prompt and skills.
  - `OPENCODE_PERMISSION='{"skill":"deny"}'` blocks skill loading entirely.
  - `~/.agents/skills` and `~/.config/opencode/skills` still load under the first two [08].
- Prompt: `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1` stops reading `~/.claude/CLAUDE.md`.
- Agents and subagents: `--agent <name>` picks the primary agent; `OPENCODE_PERMISSION='{"task":"deny"}'` stops subagents.
- MCP: `OPENCODE_CONFIG_CONTENT='{"mcp":{"<name>":{"enabled":false}}}'` (inline config merge) [D env var; the MCP `enabled` key is I]. Configured here: `codegraph` and `gsd` [07].
- Plugins: `--pure` "run without external plugins" [H]; `OPENCODE_DISABLE_DEFAULT_PLUGINS=1` [D].
- Slash commands: `--command <name>` runs one [H]. Nothing disables them, and nothing needs to in `run`.
- Noise: `OPENCODE_DISABLE_AUTOUPDATE=1` [D].

**Bash tool:** governed by `permission.bash`, which is pattern-matched on the parsed command. `--auto` plus targeted denies is the recommended shape.

**Model:**
- `-m provider/model`; `--variant` sets provider-specific effort (`high`, `max`, `minimal`) [H].
- `opencode models` lists 86 here [H `P/help/opencode-models.txt`]: providers `opencode` (Zen, 39), `opencode-go` (31), `xai` (13) and `router-env` (3).
- Free Zen models: `opencode/big-pickle` (used here; the JSON `step_finish` showed `cost:0`), `opencode/*-free` (`cat-jam-free`, `exo-free`, `mimo-v2.6-flash-free`, `nemotron-3.5-lightning-free`, ...).
- `xai/*` through opencode hit a 403 spending limit on 2026-09-14 (memory).

**Session:** `-s/--session <id>`, `-c/--continue`, `--fork` [H]. Every JSON event carries `sessionID` (`ses_...`) [L], which replaces `xai_exec.sh`'s racy `session list` scrape.

**Timeout and exit:** no time flag. Exit codes are undocumented [D]; 0 was observed. JSON `type:"error"` events are the failure signal [I].

**Known limits:** the router (`router-env/*`) errors in 16-HANDOFF:
- "temporarily unavailable" is transient;
- 402 "requires an opencode API key", "pre-dispatch filters" and "Credential gate" are fatal.

The reviewer prompt also failed at about 263 KB [08].

### 3.3 grok (Grok Build CLI 1.0.52)

**Execute, full permissions** [L `P/grok.argv.txt` and `P/grok-json.argv.txt`, rc 0, 25.0 s and 12.5 s, no wait, commits `c07d53d` and `611a57c`]:
```
grok --prompt-file /dev/stdin -m grok-4.7-build-fast --always-approve --permission-mode bypassPermissions --output-format json --no-alt-screen --no-auto-update   < prompt
```
- Run 2 dropped `--permission-mode bypassPermissions` and still passed. The local config already says `always-approve`, so this does not prove the flag is unnecessary elsewhere. Keep both.
- `--output-format json` returns `{text, stopReason:"end_turn", sessionId, usage, num_turns, total_cost_usd, modelUsage}` [L]. `plain` returns the same `text` [L].
- `--cwd <dir>` sets the working directory [H]. The wrapper passes it explicitly.
- `--no-auto-update` [D headless-scripting] and `--no-memory` [D reference] are hidden from `--help`, but the parser accepts them; unknown flags are rejected with `unexpected argument` [L].

**Review, read-only (not live-tested; [U]):**
```
grok --prompt-file /dev/stdin -m grok-4.7 --permission-mode plan --output-format json --no-alt-screen --no-auto-update --no-subagents
```
- `plan` is one of the `--permission-mode` values [H]. The argv parses [L `--version` probe], but the run was not tested.
- Alternative: `--permission-mode dontAsk --tools <read-only list>` [D enterprise via search; tool names U].

**Permissions:**
- `--always-approve`: "Auto-approve all tool executions" [H]; alias `--yolo` [D reference].
- `--permission-mode default|acceptEdits|auto|dontAsk|bypassPermissions|plan` [H].
- `--allow <RULE>` and `--deny <RULE>` (aliases `--allowedTools`/`--disallowedTools`, Claude-compatible) [H].
- `--sandbox <PROFILE>` (env `GROK_SANDBOX`) [H]. Third-party docs name the profiles `workspace`, `read-only` and `strict`, off by default [search, unofficial]. **Do not pass it, and unset `GROK_SANDBOX`.** The old ai-kit builder passed `--sandbox workspace`.
- grok also loads permissions from `~/.claude/settings.json` (6 rules here) [H inspect]. A Claude deny rule therefore also binds grok.

**Strip or restrict:**
- Tools: `--tools <list>` (allowlist) and `--disallowed-tools <list>` [H].
- Subagents: `--no-subagents` [H]. `--agent <NAME>` and `--agents <JSON>` pick or define agents [H].
- Plan mode: `--no-plan` [H]. Web: `--disable-web-search` [H]. Memory: `--no-memory` [L parses].
- Prompt: `--rules <text>` appends and `--system-prompt-override` replaces [H]. Both take text with spaces, so they are unusable in a raw GSD string but fine from the wrapper.
- **Skills, plugins, hooks and MCP: no per-run off switch found.**
  - `grok inspect` shows 191 skills, 38 agents, 5 Claude plugins, 21 hooks and MCP `codegraph` (from `~/.claude.json`) [H].
  - The `GROK_CLAUDE_*_ENABLED` and `GROK_CURSOR_*_ENABLED` env names exist in the binary, but `=0`/`=false` did not change `inspect` [L]. Config keys `import_claude`, `claude_compat` and `disable_plugins` exist as strings [H strings]. Testing them needs a config edit, so they are [U].
  - `--plugin-dir` only adds.

**Bash tool:** governed by `--allow`/`--deny` rules; `GROK_SANDBOX_AUTO_ALLOW_BASH` exists [H strings]. Recommended: `--always-approve` plus `--deny 'Bash(git push:*)'` (Claude rule syntax, [I]).

**Model:**
- `-m <id>` and `grok models`. Logged in with grok.com: `grok-4.7` (default), `grok-4.7-build-fast`, `grok-4.6`, `grok-4.5` [H `P/help/grok-models.txt`].
- `--reasoning-effort` (alias `--effort`) [H].
- Cost seen: $0.066 per probe on build-fast, at 100.7k total tokens (72k cache read) [L].

**Session:**
- `-s/--session-id <UUID>` names a **new** session [H]; the docs call it "create or resume" [D]. Local help is stricter: "Does not resume existing sessions".
- `-r/--resume <id|title>`, `-c/--continue`, `--fork-session` [H].
- JSON `sessionId` gives the resume id [L].

**Timeout and exit:** `--max-turns N` caps turns [H]. Exit codes are undocumented [D]; 0 was observed. `stopReason` is the failure signal [I].

**Gotchas:**
- `-p, --single <PROMPT>` takes the prompt as its **value** [H]. `grok -p --model x` sends "--model" as the prompt [I]. Use `--prompt-file /dev/stdin`.
- `text` concatenates all assistant messages without a separator (`"...hash.## Summary"`) [L].

### 3.4 pi (not installed; NOT live-tested in this session)

Source: report 06 (live on 0.82.1, 2026-10-13 morning) and pi.dev/docs/latest/cli [D]. The current npm version is 1.2.0, published as `@earendil-works/pi-coding-agent` [06].

**Execute, full permissions:**
```
pi -p --model openai-codex/gpt-5.6-terra:medium --session-id <uuid> --no-approve --offline   < prompt
```
- pi has **no permission prompts and no sandbox**: "Pi does not ask before every tool call" [D usage]; the README says "No permission popups" [06]. No flag is needed.
- `-p` writes only the last assistant message's text to stdout and exits 1 on error or abort [06 source].
- stdin is prepended to the first prompt [D]. **It blocks until EOF** [06 live].
- Pin `--model` (with an optional `:thinking` suffix) or `--thinking`. The user default is gpt-5.6-terra at xhigh [06].

**Review, read-only:**
```
pi -p --model <m> --tools read,grep,find,ls --no-approve --offline
```
- `--tools` "Replaces the default selection with a comma-separated allowlist" [D].

**Strip or restrict** [D cli]:
- Skills: `--no-skills` ("Explicit `--skill` paths still load"), and `--skill <path>` (repeatable).
- Extensions: `--no-extensions` (in 1.x also built-in MCP, codemode and tool-search), and `-e <path>`.
- Context: `--no-context-files` drops AGENTS.md and CLAUDE.md.
- MCP: `--no-mcp` (1.0.4+); 0.82.1 has no MCP at all [06].
- Tools: `--tools`, `--exclude-tools` (patterns, MCP included), `--no-tools`, `--no-builtin-tools`.
- Project trust: `--no-approve` / `--approve`.
- The user's pi config auto-loads the superpowers package, the `subagent` extension and the `rtk` bash rewriter [06]. Consider `--no-skills --no-extensions` for determinism. The prototype leaves them on because the user asked for "without limitations"; the comment shows the strip line.

**Session:** `--session-id <id>` "Opens the exact project session ID or creates it if absent" [D]. A pre-assigned id gives deterministic resume. `--no-session` keeps the session in memory.

**Timeout and exit:**
- Built-in provider retry: 3 attempts at 2, 4 and 8 s [06].
- SIGTERM exits 143.
- 0.82.1 exits 0 on a `length` stop; 1.2.0 exits 1 [06].
- JSON mode exits 0 even on error, so use `-p` [06].

### 3.5 codex (codex-cli 0.153.4; optional, not in the user's runtime list)

**Execute, full permissions** [L `P/codex.argv.txt`: the argv was accepted, the run failed on auth]:
```
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C <dir> -m gpt-5.4-mini --json -o <file> -   < prompt
```
- `--dangerously-bypass-approvals-and-sandbox` is the only exec mode with no sandbox and no approvals [H].
- `--full-auto` and `-a` are rejected by `exec` [08].
- `workspace-write` is a real sandbox; whether `.git` is writable under it is still [U].
- `--approve-for-me` routes approvals to automatic review *inside* workspace-write [H], so it is not unlimited.
- `-o` writes the last message to a file and still prints it [D]. `--json` gives a JSONL stream with `thread.started` [D].

**Review:** `codex exec --sandbox read-only ...` (the docs default) [D].

**Strip or restrict** [H]:
- `--ignore-user-config` drops `config.toml`, including MCP and provider config; auth still works.
- `--ignore-rules` drops execpolicy rules.
- `--disable <FEATURE>`.
- `-c key=value` overrides, for example `-c 'mcp_servers.codegraph.enabled=false'` [I key].
- `--ephemeral` keeps no session files.

**Model:** `-m`. `codex debug models` lists `gpt-6-astra`, `gpt-5.6-{sol,terra,luna}`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini` (the cheapest) and `gpt-5.2` [H `P/help/codex-models.json`].

**Session:** `codex exec resume <SESSION_ID|--last> [PROMPT|-]`. Resume accepts `--dangerously-bypass-approvals-and-sandbox`, `-m`, `--json` and `-o` [H].

**Exit and auth:**
- Auth failure: rc 1 after 8.2 s, with `401 token_expired` / `invalid_refresh_token` on stderr [L].
- `codex login status` still reported "Logged in using ChatGPT" [L]. **Do not use it as a preflight.**

## 4. Flag inventory

Full-permission and read-only flags:

| CLI | headless | prompt from stdin | full permissions | no sandbox | read-only review | model |
|---|---|---|---|---|---|---|
| cursor-agent | `-p` | yes [L] | `--force --trust --approve-mcps` | `--sandbox disabled` | `--mode ask` [L] / `plan` | `--model` |
| opencode | `run` | yes [L] | `--auto` | none exists | `--agent plan` [L] | `-m`, `--variant` |
| grok | `--prompt-file /dev/stdin` | via file [L] | `--always-approve --permission-mode bypassPermissions` | omit `--sandbox`, unset `GROK_SANDBOX` | `--permission-mode plan` [U] | `-m`, `--effort` |
| pi | `-p` | yes, needs EOF [06] | none needed | none exists | `--tools read,grep,find,ls` | `--model id[:thinking]` |
| codex | `exec` | `-` [D] | `--dangerously-bypass-approvals-and-sandbox` | same flag | `--sandbox read-only` | `-m` |

Strip-down and session flags:

| CLI | skills off | MCP off | subagents off | final answer | session id / resume |
|---|---|---|---|---|---|
| cursor-agent | none | none per run | none | json `.result` | json `.session_id` / `--resume` |
| opencode | `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`, `OPENCODE_PERMISSION` skill deny | `OPENCODE_CONFIG_CONTENT` [I] | permission `task: deny` | default stdout, or json last-message text | json `sessionID` / `-s` |
| grok | none verified | none verified | `--no-subagents` | json `.text` (re-break headings) | json `.sessionId` / `-r` |
| pi | `--no-skills` | `--no-mcp` (1.0.4+), `--no-extensions` | `--no-extensions` (the subagent ext) | stdout | pre-assigned `--session-id` |
| codex | none | `-c mcp_servers.*` [I], `--ignore-user-config` | none | `-o file` | `thread.started.thread_id` / `exec resume` |

## 5. Drift audit: the six hand-written `cross_ai_command` values

- **home-mobility:** `opencode run --model router-env/my-coding --format json`
  - No `--auto`, so `external_directory` and `doom_loop` asks are unanswered.
  - `--format json` sends raw JSONL into SUMMARY.md [L shape].
  - **Broken.**
- **tools-installer:** `opencode run --model xai/grok-4.7 --auto`
  - The flags are right.
  - The `xai` provider through opencode was blocked by a 403 spending limit on 2026-09-14 (memory). That is fatal, never retry it.
- **wezterm-setup:** `opencode run --model xai/grok-4.6`. No `--auto`, and the same xai billing risk.
- **kitty-setup:** `opencode run --auto --model router-env/my-coding`. **Correct** for opencode.
- **gitid and ai-kit:** `opencode run --model router-env/my-coding`. No `--auto`.

None of the six unset `CLAUDECODE` (16-HANDOFF:193). None of them have a retry, a fallback or an inner timeout. **All six collapse to `node .planning/cross-ai.mjs`**, with the model moved into the script's CONFIG.

## 6. `cross-ai.mjs` (prototype at `R/cross-ai.mjs`)

**Usage:**
- GSD sets `workflow.cross_ai_command = "node .planning/cross-ai.mjs"`.
- Manual or test runs add flags: `--prefer pi,cursor,opencode,grok`, `--model-<cli> <id>`, `--mode exec|review`, `--timeout S`, `--print-argv`, `--no-preamble` or `--self-test`.

**Behaviour:**
- **Candidates:**
  - Candidates are tried in order. A missing binary means skip; a missing model means skip and remember exit 2.
  - Binaries are resolved by a PATH scan, so shell functions are never seen.
  - After a failure it falls through to the next CLI **only if `git rev-parse HEAD` + `git status --porcelain` are unchanged**. A half-edited tree is never handed to a second agent.
- **Child process:**
  - The CLI is spawned detached in its own process group, with the prompt plus `EXEC_PREAMBLE` on stdin. The preamble covers: unattended run, really commit, no push, no `--no-verify`, and a SUMMARY-shaped reply.
  - Its env drops `CLAUDECODE` and the other host signals.
  - stderr streams live to GSD's error log, with a 30 s heartbeat that reports stdout byte growth.
- **Deadline:** the inner deadline is `cross_ai_timeout - min(30, floor(t/5))`: 300 s gives 270 s, and 20 s gives 16 s. When it hits, the script SIGTERMs the group, SIGKILLs it after 5 s, and exits **124**.
- **Signals:** SIGTERM, SIGINT and SIGHUP are forwarded to the CLI's group. The script SIGKILLs the group after 2 s, which beats GSD's 3 s escalation, and then exits 128+n.
- **Retry:**
  - Only when stderr, the parsed error or the stdout tail matches TRANSIENT and not FATAL.
  - At most 2 retries with 30 s and 60 s backoff, each only if 60 s or more of the deadline remain.
  - A retry **resumes** the captured session (cursor `--resume`, opencode `--session`, grok `--resume`, codex `exec resume`, pi's same `--session-id`) with a "check git status/diff/log first" message. Otherwise it re-runs fresh with that message prepended.
- **Output:**
  - stdout gets only the final answer, ANSI-stripped and with glued headings re-broken.
  - Exit codes: 0, the CLI's own code (1 when the CLI said 0 but `is_error` was set or the answer was empty), 124, 127 (none installed) and 2 (usage).

**Verification (model-free):**
- `node cross-ai.mjs --self-test` printed "self-test ok; header: pristine" in 1.6 s. It covers:
  - the argv invariants for all 5 runtimes (exec has its permission flags and a model; review has no bypass flag; no whitespace tokens);
  - the parsers on probe-captured shapes;
  - 6 classifier fixtures, including the real codex `token_expired` and the router "temporarily unavailable";
  - the inner-timeout arithmetic;
  - a fake CLI for pass-through exit 7, a transient retry that succeeds, and a hang that ends in 124.
- End to end through `gsd-tools.cjs run-with-timeout` with fake CLIs on PATH (`P/fakebin/`, `P/e2e/`):
  - `--prefer pi,cursor`, with pi missing, fell back to cursor and printed only the `.result` text, rc 0.
  - Inner deadline: config 10 s gives inner 8 s, and the run ended at rc 124 after 8.1 s.
  - Outer timeout first (5 s against inner 60 s): rc 124 after 5.08 s, and **no orphan** `sleep 300` remained (`pgrep -a sleep`).
- `--print-argv` shows the resolved command per CLI without a model call, which is the anti-slip debugging aid.

**Known limits** (also commented in the code):
- The TRANSIENT and FATAL regexes are heuristics. Cursor, grok and pi error strings were not captured.
- The resume argv is live-verified for no CLI. The session-id *capture* is verified for cursor, opencode and grok.
- grok review mode is [U]. The codex and pi success paths are [U].
- The fallback criterion uses git state. Outside a git repo it never falls back after a CLI has started.

## 7. Generator design (inside ai-kit-gsd-curated-config)

### 7.1 Inputs
- **Detected CLIs:** a PATH scan for `cursor-agent|agent`, `opencode`, `grok`, `pi` and `codex`. Add `pi` and `grok` to `detection.KNOWN_CLIS` [08]. Exclude the host runtime, and always exclude `claude` (user decision: Claude is never a cross-AI target).
- **Preference:**
  - Default order: Phase 18's best `execution` score first, then the remaining installed non-host CLIs by score.
  - The user may override it with one answer (a comma list).
  - On a cursor-only machine the order is just `cursor`.
- **Model per CLI:**
  - From the Phase 17 slots and router (D-04: `router-env/my-coding` for execution) where that CLI can reach the router (opencode, pi).
  - Otherwise from scoring: cursor `auto` or `composer-2.5`, grok `grok-4.7` or `-build-fast`, pi an OAuth model such as `openai-codex/gpt-5.6-terra:medium`.
  - A CLI with no resolvable model is left out of `prefer` rather than written with an empty model.
- **Timeout:** `workflow.cross_ai_timeout` stays 300 (MVP) or 600 (Standard, Rigorous) per spec §6, written in the same apply. The script derives its inner deadline, so the two never drift.

### 7.2 Where it lives
- **Template:** `skills/ai-kit-gsd-curated-config/templates/cross-ai.mjs` in ai-kit. The prototype becomes the template unchanged except for the `// <config>` JSON block.
- **Output:** `<project>/.planning/cross-ai.mjs`, with `workflow.cross_ai_command = "node .planning/cross-ai.mjs"`.
  - It is relative, has no whitespace and needs no ai-kit install at run time. GSD runs from the project root.
  - The file can be committed with the project's planning dir. It holds no secrets.
- **Rendering:**
  - `render(config)` replaces the text between `// <config>` and `// </config>` with `json.dumps(config, indent=2)`.
  - `stamp(text)` writes `sha256(lines[2:])` into line 2. The template version `template=N` sits on the same header line.

### 7.3 Regeneration without silent overwrite
`header_state(existing)` mirrors the JS `headerState`. Proven: the stamped prototype reports `pristine`, and a one-value edit reports `edited` [L].

- File absent: write it.
- **`pristine`** (hash matches): overwrite atomically (tmp file plus `os.replace`) if the rendered output differs. Report `updated` or `unchanged`.
- **`edited` or `unstamped`:**
  - Never overwrite. Write `.planning/cross-ai.mjs.new` and report `kept-edited` in the plan and report output, with a short unified diff of the config block and the template version.
  - `--force-cross-ai-script` overwrites after a `.bak-<ts>` copy, keeping the last 3 per Phase 18 D-06.
- After any write, run `node .planning/cross-ai.mjs --self-test` (no model call). On a non-zero result, refuse to write `cross_ai_command` (fail-closed, as in v1 D-05).
- Python side: about 40 LOC (`render`, `stamp`, `header_state`, `write_cross_ai_script`) in `cross_ai_build.py`, with the same injected `run_fn` pattern for the self-test call.

### 7.4 How this replaces report 08's Python wrapper
- Report 08 proposed `python3 <abs>/ai-kit-spec-gsd.py xai --cli X --model Y` around `dispatch_execute`. The generated script supersedes it:
  - **No absolute path to `~/.claude/skills`** in project config. That removes the whitespace hazard, the "branch code imports main" resolution problem (synthesis A3), and the breakage on machines where ai-kit is not installed.
  - **No Python at run time.** Node is guaranteed wherever GSD runs.
  - **The formula is editable in place,** with comments, as the user asked.
- Ported from 08's design: the inner timeout derived from config, exit 124 and 127 mapping, SIGTERM group forwarding (08's orphan bug, now tested), env scrub, transient-only retry with resume, `--print-argv`, and the in-code SUMMARY instructions (`EXEC_PREAMBLE` replaces `--format-block-file`).
- Not ported: `agent_skills` inlining (08 increment 2). It can be added later as an optional `gsd-tools query agent-skills gsd-executor` read inside the script.
- **Single writer shape:** execute-gsd SKILL Step 2 (`SKILL.md:152`) should call the same curated-config `write-cross-ai-script` subcommand instead of writing the `dispatch-execute` string. `dispatch-execute` stays for ai-kit-spec-review only.
- **`commands.py` execute builders:**
  - They are no longer the source of truth for GSD execution.
  - Fix or retire the broken grok and claude `sh -c` builders [08].
  - Add one parity test in ai-kit that runs `node templates/cross-ai.mjs --print-argv` and asserts each CLI's permission flags. This works without the CLIs installed, since MISSING rows still print their argv.

### 7.5 Mapping onto Phase 18 XAI-02
- **Current text** (`REQUIREMENTS.md:40`): "`cross_ai_command` (built by `build_execute_command`, bare CLI name) with a rigor-dependent timeout, picking the best `execution` score in another CLI; ...".
- **Proposed amendment:** "`cross_ai_command` = `node .planning/cross-ai.mjs`, generated from the curated template. `prefer` puts the best `execution`-score CLI first, then the other installed non-host CLIs, each with its scored model. The script is hash-stamped and is never silently overwritten when edited. The self-test gates the write. `cross_ai_timeout` is 300 or 600, written in the same apply."
- The rest of XAI-02 is unchanged: the defaults (yes on Claude/Codex, no on opencode/cursor/pi), the `--cross-ai` report line and `manager.flags.execute`.
- **Plan pipeline:** add one `plan.json` op, `{op:"write_file", path:".planning/cross-ai.mjs", state:"absent|pristine|edited", config:{...}}`, so the review pass shows the preference and models before `apply` (D-05 refuses while `needs_choice` remains).
- **Tests to add:**
  - render and stamp round-trip;
  - pristine overwrite versus edited `.new`;
  - the self-test gate;
  - `cross_ai_command` has no whitespace tokens;
  - claude and the host are never in `prefer`.

---

## 8. Probe log index (`P/`)

- `prompt.md` is the shared GSD-shaped prompt (`<objective>` + `<tasks>`). `run-probe.sh` is the harness: a fresh `git init`, repo-local identity and `core.hooksPath=/dev/null`, `env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT`, `timeout 180`, and the prompt on stdin.
- cursor: `cursor.*` (exec, rc 0, 45.9 s) and `cursor-ask.*` (review, rc 0, 14.8 s).
- opencode: `opencode.*` (exec, rc 0, 26.7 s) and `opencode-plan.*` (review, rc 0, 13.8 s).
- grok: `grok.*` (exec plain, rc 0, 25.0 s) and `grok-json.*` (exec json, rc 0, 12.5 s).
- codex: `codex.*` (exec, rc 1, 8.2 s, auth fatal). A second run was skipped because it would fail identically.
- `help/`: `--help` captures for every CLI and subcommand, model lists, and `grok-inspect.txt`.
- `fakebin/` and `e2e/`: the model-free end-to-end checks of `cross-ai.mjs` through `run-with-timeout`.
- Secret scan: 0 matches for bearer, JWT or `sk-` patterns across all probe stdout and stderr.

## 9. Sources

- Cursor: [headless](https://cursor.com/docs/cli/headless), [parameters](https://cursor.com/docs/cli/reference/parameters).
- opencode: [CLI and env vars](https://opencode.ai/docs/cli/), [permissions](https://opencode.ai/docs/permissions/).
- grok: [CLI reference](https://docs.x.ai/build/cli/reference), [headless scripting](https://docs.x.ai/build/cli/headless-scripting). Third-party sandbox profile names: [tessl grok-build skill](https://tessl.io/registry/skills/github/XiaomiMiMo/MiMo-Code/grok-build), [aiidelist cheatsheet](https://aiidelist.com/grok-build-cheatsheet). The enterprise and sandbox pages returned 404 through the fetcher.
- pi: [CLI](https://pi.dev/docs/latest/cli), [usage](https://pi.dev/docs/latest/usage), report 06.
- Codex: [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [sandboxing](https://learn.chatgpt.com/docs/sandboxing).
- GSD: `~/.claude/gsd-core/workflows/execute-phase/detail/elaboration.md` (1.16.0) and `bin/gsd-tools.cjs` `run-with-timeout`.
- ai-kit review tree: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py`, `.planning/REQUIREMENTS.md:40`, `.planning/phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md`, `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:197-207`.
