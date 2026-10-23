# 08 — Curated cross-AI command wrapper (design research)

Scope: design an ai-kit-curated wrapper that `workflow.cross_ai_command` points at, so agents stop slipping on per-CLI flags. It adds pi when installed and loads only the skills each execution role needs.

Review tree: `review-v13` (tip `0acbd06`, branch `gsd/v1.3-curated-config-v2`). All `skills/...` paths below are relative to that tree unless marked otherwise. GSD paths are under `~/.claude/gsd-core` (gsd-core 1.14.0).

Confidence tags:
- **[V]** verified: I read the code, ran a local command, or quoted official docs.
- **[I]** inference.
- **[U]** unverified; needs a live probe.

---

## 0. TL;DR (ranked)

1. **A nearly curated wrapper already exists, but only one of the two writers uses it.** [V]
   - The wrapper is `ai-kit-spec.py dispatch-execute ... --prompt-file - --stdout-only`. It lives in `skills/ai-kit-spec-review/ai_kit_spec/cli.py:797-831`, with the handler at `:1234-1268`.
   - `ai-kit-spec-execute-gsd/SKILL.md:129-169` writes it into `workflow.cross_ai_command`.
   - **curated-config does not use it.** Both v1 `apply-execution` (`ai_kit_gsd_curated_config/cli.py` `_cmd_apply_execution`) and the planned v2 XAI-02 write the **raw** `build_execute_command` string (`cross_ai_build.py:46-60`).
   - Result: two writers produce two different command shapes for the same key. That divergence is the root of the slipping.
2. **The raw strings for `claude` and `grok` are broken under GSD's expansion.** [V]
   - GSD runs `${CROSS_AI_CMD}` unquoted through `run-with-timeout`, which uses an argv spawn with no shell (`execute-phase/detail/elaboration.md:99`, `gsd-tools.cjs:4871-4900`). Bash word-splits the string and never re-parses quotes.
   - The claude builder emits `sh -c 'cd /p && exec claude ...'` and the grok builder emits `sh -c 'grok ... -p "$(cat)"'` (`commands.py:203-226`).
   - Reproduced locally: `CMD="sh -c 'echo inner-ok && echo two'"; ${CMD}` fails with `unexpected EOF while looking for matching '` (exit 2).
   - `dispatch-execute` only works because it runs the same string with `shell=True` (`dispatch.py:70`).
3. **The live project config shows the slip.** [V]
   - `.planning/config.json` (on both main and the review tree) has `workflow.cross_ai_command = "opencode run --model router-env/my-coding"`. It was hand-written and has no `--auto`, while the ai-kit builder does emit `--auto` (`commands.py:268`).
   - It worked in Phase 16 only because `~/.config/opencode/opencode.jsonc` has no `permission` block, so opencode's permissive defaults apply. Under those defaults `external_directory` is `ask` (opencode docs, permissions page).
   - [I] Any read outside the repo will stall or be denied without `--auto`. That includes the `~/.claude/skills/...` SKILL.md files that GSD's `agent_skills` block points at.
4. **codex: `--full-auto` is gone locally.** [V]
   - Local `codex exec --full-auto` gives `error: unexpected argument '--full-auto' found` (codex-cli 0.153.4).
   - Official docs still call it "a deprecated compatibility flag", so the docs lag the binary.
   - `~/.claude/skills/codex/SKILL.md:15,28-29` still recommends `--full-auto`, so an agent following that skill slips.
   - `-a/--ask-for-approval` exists only on top-level `codex`, not on `codex exec` (local probe: `unexpected argument '-a'`).
   - The ai-kit codex builder is already correct: `--sandbox workspace-write --skip-git-repo-check -C` (`commands.py:176`).
5. **The claude execute builder cannot serve the gsd-executor role.** [V] help + [I] impact
   - It uses `--restricted --permission-mode acceptEdits` (`commands.py:225`).
   - Per `claude --help`, `--restricted` "removes the built-in tools that run commands or code (Bash ...)". It also "lets only a person or the configured permission handler approve writes to settings, git and tool-configuration files".
   - GSD cross-AI plans require running verify commands and `git commit` (see the `xai_exec.sh:25` prompt). So a claude target can neither run tests nor commit.
6. **The wrapper orphans its child CLI when GSD's outer timeout fires first.** [V] code + [I] behaviour
   - `run-with-timeout` sends SIGTERM to its child's process group (`gsd-tools.cjs` `killTree`, `process.kill(-child.pid, ...)`) and escalates to SIGKILL after 3 s.
   - `dispatch_with_heartbeat` launches the CLI with `start_new_session=True` (`dispatch.py:70-71`). That puts the CLI in a **different** group, and Python installs no SIGTERM handler.
   - So the Python wrapper dies and the CLI keeps running unsupervised.
   - The SKILL avoids this only by hardcoding inner 840 s against outer 900 s (`SKILL.md:144-148`). curated-config never writes a matching inner value, and GSD's default `cross_ai_timeout` is 300 s (`elaboration.md:74`).
7. **Timeout exit codes are opaque.** [V]
   - On timeout the wrapper returns the CLI's `-9` (SIGKILL) through `sys.exit` (`cli.py:1257-1265`), which the shell sees as **247**.
   - GSD's own convention is **124** (`gsd-tools.cjs:4880-4889`).
8. **Review lanes do not need the wrapper.** [V]
   - GSD review lanes are GSD-owned argv descriptors that already carry the right flags. The cursor lane is `-p --mode ask --trust --output-format text`, and the opencode lane is `run --format json` with a handler (`bin/lib/review-lane-descriptor.cjs`).
   - `review.reviewer_instances.<n>.cli` "MUST be a known adapter (never an arbitrary shell command)" (`review-reviewer-selection.cjs:158`; validated in `config.cjs:1058-1069`).
   - So curated-config only writes `review.models.<slug>`, and there is no review command string to slip on. The only way to add a pi review lane is a GSD overlay reviewer capability (ADR-2782 D8, `mergeReviewerLanes`). Defer it.
9. **Minimal skills can reuse GSD's own resolver.** [V]
   - `gsd-tools query agent-skills gsd-executor` emits `<agent_skills>\nRead these user-configured skills:\n- @/abs/SKILL.md ...` (`init.cjs:3748-3754`).
   - The native executor gets that block (`execute-phase.md:94,719`). The cross-AI prompt does not: it is built only from `<objective>`/`<tasks>` plus PROJECT.md (`elaboration.md:84-88`).
   - `@path` is a Claude-Code include convention. The wrapper should inline those files for non-claude CLIs and switch off each host's own skill discovery where a flag exists.
10. **The smallest fix for the slipping:** one GSD-adapter subcommand, `ai-kit-spec-gsd.py xai --cli X --model Y`, that both writers emit.
    - It is a thin shell around the existing `dispatch_execute`.
    - It fixes the target dir to the cwd, holds the GSD SUMMARY format block in code, and maps timeout to 124.
    - It forwards SIGTERM and scrubs host-signal env vars.
    - About 60 LOC plus tests. Retry/resume and skill isolation are increment 2.

---

## 1. Inventory of what exists

### 1.1 Command builders: the per-CLI flag profiles already exist [V]

`skills/ai-kit-spec-review/ai_kit_spec/commands.py`:
- `_COMMAND_BUILDERS` is keyed by `(kind, cli)`, with kind `review` or `execute` (`:289-300`).
- `build_execute_command(cli, target_dir=..., effort=..., service_tier=...)` returns a `{model}` template (`:329-332`).

Rendered output for `target_dir=/home/u/proj`, `model=M` (I ran `python3 -B` against the review tree):
```
claude:       sh -c 'cd /home/u/proj && exec claude -p --restricted --permission-mode acceptEdits --model M --output-format text'
grok:         sh -c 'grok --sandbox workspace --cwd /home/u/proj -m M --always-approve --output-format plain -p "$(cat)"'
opencode:     opencode run -m M --dir /home/u/proj --auto
cursor-agent: cursor-agent --sandbox enabled --workspace /home/u/proj -p --output-format text --model M --trust --force
codex:        codex exec --sandbox workspace-write --skip-git-repo-check -C /home/u/proj -m M
pi:           ValueError no execute-mode (write-capable) command builder registered for cli='pi'
```
- `NO_HARD_SANDBOX_CLIS = {"cursor-agent", "opencode"}` (`:276`). These targets get soft-confinement prose instead (`execute_dispatch.py:19-29`).
- Each builder's docstring records its live finding, for example cursor `--trust` (`:123-128`) and opencode `--auto` (`:261-263`). That makes the builders the right single source for argv. Rewriting them as a data table would be gold-plating; see §3.2.

### 1.2 Dispatch engine [V]

`ai_kit_spec/dispatch.py`:
- `dispatch_with_heartbeat` (`:46-98`):
  - delivers the prompt over stdin without deadlocking (`communicate(input=...)`);
  - prints a heartbeat to **stderr** every `heartbeat_interval`;
  - on timeout, kills the process group and drains output;
  - runs the CLI under `shell=True, start_new_session=True` (`:70-71`).
- `dispatch_with_polling` (`:101-198`) uses file-backed stdout, tiered timeouts, and an "+N bytes since last check" progress line. Reviewers use it.
- There is no signal handler, no env scrub, and no retry.

`ai_kit_spec/execute_dispatch.py` `dispatch_execute` (`:32-72`):
- builds the execute command;
- prepends the reinforcement guidance (model override, incremental progress, failure reporting, optional format block), the tooling guidance, and the soft-confinement prose;
- runs everything through `dispatch_with_heartbeat`.

`ai_kit_spec/reviewer_dispatch.py`: reviewer counterpart built on `dispatch_with_polling`.

### 1.3 The existing wrapper subcommand [V]

`ai-kit-spec.py dispatch-execute` (`cli.py:797-831` parser, `:1234-1268` handler):
- Arguments: `--cli --model [--effort --service-tier] --target-dir --prompt-file - --timeout [--heartbeat-interval 30] [--format-block-file] [--tool-availability-json --agents-tooling-path --codegraph-registered] --stdout-only`.
- `--stdout-only` prints only the CLI's stdout and returns the CLI's real returncode, or 1 when it is None.

`ai-kit-spec.py dispatch-reviewer`: same contract for reviewers.

`ai-kit-spec-execute-gsd/SKILL.md:152` is the "instrumented dispatch wrapper" the SKILL description mentions:
```
python3 $TOOLS_PY dispatch-execute --cli $RESULT_CLI --model $RESULT_MODEL --target-dir $CWD --prompt-file - --stdout-only --timeout $DISPATCH_TIMEOUT_SECONDS --format-block-file $FORMAT_BLOCK_PATH
```
- It writes the format-block file to `.planning/.ai-kit-spec-execute-gsd-summary-format.md` using `print-summary-format-block` (`ai_kit_spec_gsd/cli.py`).
- It sets `cross_ai_timeout=900` and the inner timeout to 840.
- `references/dispatch-notes.md:6-22` documents that GSD's `${CROSS_AI_CMD}` is word-split with no re-parse. So no quoting is possible, and **any value containing whitespace breaks**. Both `--target-dir $CWD` and `--format-block-file <path in project>` are exposed to that.

`ai_kit_spec_gsd/gsd_cross_ai.py:8-36` `build_cross_ai_command` returns the **raw** builder string. `adapter.resolve_gsd_dispatch` uses it only as `RESULT_CROSS_AI_COMMAND`; the SKILL then deliberately ignores it in favour of the wrapper (`SKILL.md:129-130`).

### 1.4 curated-config [V]

- `cross_ai_build.build_execution_command(cli, model, project_dir)` returns the raw `build_execute_command(...).format(model=...)` (`cross_ai_build.py:46-60`).
- `_cmd_apply_execution` writes it with `config-set workflow.cross_ai_command` (`cli.py` around line 187-202). It never sets `cross_ai_timeout`, so GSD's default of 300 s applies.
- `_cmd_apply_review` writes `plan_review_convergence`, `review.effort.opencode=high`, `review.default_reviewers`, and `review.models.<slug>`. `CLI_TO_REVIEWER_SLUG` covers only opencode, cursor and claude (`cross_ai_build.py:43`).
- v2 plan (Phase 18 XAI-02, `REQUIREMENTS.md:40`; spec §6, `2026-09-23-gsd-curated-config-v2-design.md:185-207`): "`cross_ai_command` built by `build_execute_command` with the bare CLI name", timeout 300 for MVP and 600 otherwise. **That would carry the raw-string problem into v2.**
- `model_detect.resolve_ai_kit_spec_path` (`model_detect.py:26-46`) is a three-candidate skill-dir resolver. It generalises to `ai-kit-spec-execute-gsd` trivially.

### 1.5 Phase 16 real-run scripts and lessons [V]

`.planning/phases/16-ai-kit-spec-extensions/cross-ai-scripts/xai_exec.sh`:
- Runs `env -u CLAUDECODE node gsd-tools run-with-timeout "$TO" -- $CMD < prompt` (`:44-47`).
- On a nonzero exit it greps stderr for `temporarily unavailable|cooling down|is locked|rate limit` and retries up to 6 times with a 90 s sleep. Each retry **resumes** the session with `-s $SID` and a "continue from where you stopped; inspect git status/diff/log first" message (`:40,52-61`).
- It finds the SID with `opencode session list | awk '/^ses_/...'`, which is fragile: it picks the newest session (`:50`).
- It strips ANSI codes and keeps the output from the last `# Phase 16 Plan` heading onward (`:64-67`). That implies the default-format opencode stdout carries noise before the report. [I]

`xai_finalize.sh` writes the SUMMARY frontmatter from git diff facts, so the executor's own SUMMARY is not trusted.

`16-HANDOFF.md`:
- Router errors seen (`:118-129`). Transient: "Chat admission capacity is temporarily unavailable". **Non-transient**: 402 "requires an opencode API key", "all targets were skipped by pre-dispatch filters", "Credential gate blocked ...". The script does not retry the latter group (`:168`).
- The opencode reviewer fails at about 263 KB of prompt; about 18 KB works (`:174`).
- `CLAUDECODE` must be unset when invoking opencode (`:193`).
- Policy: retry once, then fall back to native Haiku (`:129`). A cap of one probe plus one retry, after a 45-minute quota wait (`:103`).
- From memory: the opencode xai lane hit a 403 spending limit, which is not retryable.

### 1.6 GSD side: the I/O contract the wrapper must satisfy [V]

From `execute-phase.md:414-420` and `execute-phase/detail/elaboration.md:54-140`:
- `CROSS_AI_CMD=$(gsd_run query config-get workflow.cross_ai_command --raw)` and `CROSS_AI_TIMEOUT` (default 300).
- Invocation: `echo "$TASK_PROMPT" | gsd_run run-with-timeout "${CROSS_AI_TIMEOUT}" -- ${CROSS_AI_CMD} > "$CANDIDATE_SUMMARY" 2>"$ERROR_LOG"`.
  - The prompt arrives on **stdin**.
  - **stdout is the SUMMARY candidate**, and stderr goes to a log.
  - The process runs from the **project root**.
  - The string is **word-split with no shell**.
- Success means exit 0 plus a non-empty summary with at least a heading and a description. Failure offers retry, skip (falls back to the native executor) or abort, and **GSD's retry is a fresh run**.
- `run-with-timeout` (`gsd-tools.cjs:4871-5070`) follows the GNU `timeout` exit contract: 124 on timeout, the child's own code otherwise, 127/126 on spawn failure. It sends SIGTERM to the child **group**, then SIGKILL after 3 s. It forwards SIGINT and SIGTERM.

gsd-config (`settings-advanced.md:122-124`): "A non-empty input is stored verbatim as a string." GSD's own wizard is therefore a free-text slip point that ai-kit cannot patch. It can only offer a correct string to paste.

### 1.7 Live CLI flag facts (local `--help` plus official docs)

**cursor-agent** (2026.10.01; `~/.local/bin/cursor-agent`):
- [V] `-p/--print` "Has access to all tools, including write and shell". `--output-format text|json|stream-json`. `--mode plan|ask` is read-only. `-f/--force` / `--yolo` "Force allow commands unless explicitly denied". `--trust` "Trust the current workspace without prompting". `--approve-mcps` "Automatically approve all MCP servers". `--sandbox enabled|disabled`. `--workspace`. `--resume [chatId]`. `create-chat` "Create a new empty chat and return its ID".
- [V] Docs (cursor.com/docs/cli/headless): "Without `--force`, changes are only proposed, not applied." `--trust` and MCP approval are not documented there; the trust need was found live (`commands.py:123-128`).
- [V] In the user's interactive shell, `cursor-agent` is a **function** that injects `--model gpt-5.6-sol-high` (`type cursor-agent`). GSD's argv spawn bypasses it and hits the real binary. Anything an agent tests by hand in a shell therefore differs from what GSD runs. This is the SPEC-06 issue (Phase 21).
- [I] Without `--approve-mcps`, headless MCP servers (for example codegraph) may be unusable. Yet the ai-kit tooling guidance tells the executor to use codegraph. [U] needs a live probe.

**opencode run** (1.18.35):
- [V] `--auto` "auto-approve permissions that are not explicitly denied (dangerous!)". Other flags: `--agent`, `-m/--model`, `--variant` (effort), `--dir` (cwd only), `-s/--session`, `-c/--continue`, `--fork`, `--format default|json`, `--pure` ("run without external plugins"), `-f/--file`.
- [V] Docs: permissions are allow/ask/deny; most default to allow, while `doom_loop` and `external_directory` default to ask. Per-agent `permission`, including `permission.skill` (allow/deny/ask per skill pattern).
- [V] Env vars (docs/cli table): `OPENCODE_PERMISSION` "Inlined json permissions config", `OPENCODE_CONFIG_CONTENT`, `OPENCODE_DISABLE_CLAUDE_CODE` ("Disable reading from `.claude` (prompt + skills)"), `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS`.
- [V] `OPENCODE_DISABLE_EXTERNAL_SKILLS` and `OPENCODE_DISABLE_PROJECT_CONFIG` appear in the binary's strings but not in the docs. [U] Their semantics are unknown.
- [V] Skill discovery covers `.opencode/skills`, `.claude/skills`, `.agents/skills` (project walk-up) and `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`. Locally that is 135 entries under `~/.claude/skills` and 42 under `~/.agents/skills`, all visible to an opencode executor.
- [U] How an `ask` resolves in headless `run` without `--auto` (stall or auto-reject) is not documented. Web search found no official answer.

**codex exec** (0.153.4):
- [V] `-s/--sandbox read-only|workspace-write|danger-full-access`, `--approve-for-me` (new), `--dangerously-bypass-approvals-and-sandbox`, `-C/--cd`, `--add-dir`, `--skip-git-repo-check`, `--ephemeral`, `--ignore-user-config`, `--enable/--disable <FEATURE>`, `-o/--output-last-message`, `--json`, `resume`. The PROMPT is optional; `-` or no argument means stdin.
- [V] `--full-auto` and `-a` are rejected on `exec` (local probes above).
- [V] Docs (learn.chatgpt.com/docs/non-interactive-mode): "By default, `codex exec` runs in a read-only sandbox". `--full-auto` is "a deprecated compatibility flag". `--skip-git-repo-check` is needed outside git. Resume uses `codex exec resume <SESSION_ID>`.
- [U] Whether `.git` is writable under `workspace-write` (needed for executor commits), and whether network is enabled there by default. The docs page did not say, and no live commit test exists. The Phase 16/17 cross-AI runs used opencode.

**claude -p** (2.1.296):
- [V] `--permission-mode acceptEdits|auto|bypassPermissions|manual|dontAsk|plan`. Other flags: `--permission-prompts host|none`, `--dangerously-skip-permissions`, `--allowedTools`, `--disallowedTools`, `--tools`, `--restricted` (strips Bash, confines file tools, git writes need a person), `--bare` (skips hooks, skills auto-list, CLAUDE.md and MCP; **needs `ANTHROPIC_API_KEY`, never reads OAuth**), `--disable-slash-commands` ("Disable all skills"), `--strict-mcp-config`, `--mcp-config`, `--setting-sources`, `--session-id <uuid>`, `-r/--resume`, `--add-dir`, `--effort`, `--no-session-persistence`.
- [V] Docs (code.claude.com/docs/en/headless): `acceptEdits` auto-approves edits and common filesystem commands, but "other shell commands ... still need an `--allowedTools` entry". In a `-p` run with no host, prompts "are denied either way". Piped stdin is capped at 10 MB. SIGTERM exits 143.
- [V] In the user's interactive shell, `claude` is aliased to `claude --dangerously-skip-permissions`. That is another place where what an agent tests by hand differs from what GSD spawns.

**pi** (0.82.1; help level only, another agent covers pi in depth):
- [V] Flags: `-p/--print`, `--model provider/id[:thinking]`, `--thinking`, `--tools/-t`, `--exclude-tools`, `--no-tools`, `--skill <path>` (repeatable), `--no-skills`, `--no-context-files`, `--no-extensions`, `--session-id <id>` ("creating it if missing"), `--no-session`, `--approve/-a` (trust project-local files), `--mode text|json|rpc`, `--offline`.
- [V] README: "**No permission popups.**" Non-interactive modes "do not show a trust prompt"; project-local resources (including project `.agents/skills`) are ignored unless `defaultProjectTrust=always` or `--approve`.
- [V] Source (`dist/main.js:83-94,696-704`, `dist/cli/initial-message.js:5-20`): a non-TTY stdin forces print mode, and piped stdin alone becomes the initial message. So `pi -p --model X` with the prompt on stdin works with no positional message.
- [V] pi is not in `detection.KNOWN_CLIS` (`detection.py:19`). It only appears as a host signal (`:51`) and in `_VALID_NATIVE_RUNTIME` (`config_io.py:100`). Model enumeration is SPEC-05 (Phase 22).

---

## 2. Failure modes, with evidence

Ordered by how directly each one causes "slipping".

1. **Two writers, two shapes.** [V]
   - SKILL writes the wrapper (`SKILL.md:152`), curated-config writes the raw string (`cross_ai_build.py:60`), and the hand-written project config uses a third shape (`.planning/config.json`, no `--auto`).
   - XAI-02 as written keeps the raw shape.
2. **Raw `sh -c '...'` strings break under GSD word-splitting** (claude, grok). Reproduced (§0.2). A curated-config `apply-execution --cli claude` would write a command that can never run. [V]
3. **Missing permission flags in hand-written strings.**
   - opencode without `--auto` [V config; impact I].
   - cursor without `--trust` fails with "Workspace Trust Required" on a fresh directory [V `commands.py:123-128`]; without `--force` it "only proposes" changes [V docs].
   - codex with `--full-auto` is a hard error now [V].
4. **Interactive-shell wrappers mask the truth.** [V] The `cursor-agent` function and the `claude` alias. An agent that "verifies" a command in its own shell sees behaviour GSD's argv spawn never gets.
5. **The claude target has no Bash and no git under `--restricted`.** [V help + I] An executor via claude cannot run verify steps or commit.
6. **Timeout layering.**
   - Inner and outer values are hand-paired (840/900). curated-config never writes the inner one, and GSD defaults to 300 s. [V]
   - When the outer one fires first, the CLI in its own session survives the SIGTERM to GSD's group. [V code; I behaviour]
   - On the inner timeout the exit code is 247, not 124. [V]
7. **Transient router errors.**
   - "temporarily unavailable / cooling down / is locked / rate limit" are retryable. 402, 403 spending limit, "pre-dispatch filters" and "Credential gate" are not. [V 16-HANDOFF]
   - GSD's retry is a fresh run over a dirty tree. The Phase 16 scripts needed **resume** instead.
8. **Env bleed.** [V] `CLAUDECODE` must be unset (16-HANDOFF:193). [I] Also ai-kit's own host detection keys on `CLAUDECODE`, `OPENCODE`, `CURSOR_AGENT` and `PI_CODING_AGENT` (`detection.py:~47-55`). A child that inherits the parent's signal will detect the wrong host if it runs ai-kit skills.
9. **Output noise.** [I from `xai_exec.sh:64-67`] Default-format opencode stdout needed ANSI stripping and heading extraction before it was a usable SUMMARY.
10. **Prompt size.** [V 16-HANDOFF:174] The opencode reviewer failed at about 263 KB. Execute prompts are smaller, but inlining skills increases them.
11. **Paths with whitespace cannot pass through `${CROSS_AI_CMD}`.** [V dispatch-notes.md:19-22] This hits `--target-dir $CWD` and `--format-block-file`.
12. **Cross-AI executors get none of the role's skills.** [V] The native executor gets `${AGENT_SKILLS}` (`execute-phase.md:94,719`). The cross-AI prompt does not (`elaboration.md:84-88`). Meanwhile opencode, cursor and codex auto-discover all global skills (§1.7).

---

## 3. Design

### 3.1 One entry point (smallest correct placement)

```
python3 <ABS>/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py xai --cli <cli> --model <model> [--effort E] [--role gsd-executor] [--timeout S] [--print-argv]
```

**Why the GSD adapter and not `ai-kit-spec.py`:**
- The GSD SUMMARY format block lives in `ai_kit_spec_gsd.cross_ai_guidance.GSD_SUMMARY_FORMAT_BLOCK`.
- `ai_kit_spec` is framework-agnostic by contract (`dispatch_guidance.py:10`), and the dependency arrow points gsd → ai_kit_spec.
- Holding the block in code removes the `--format-block-file` path and the extra file under `.planning/`.

**Why no `--target-dir`:** GSD always runs the hook from the project root (`elaboration.md:96`). The wrapper uses `os.getcwd()`, which removes the whitespace-path hazard.

**Stored value:** only `--cli`, `--model` and, optionally, `--effort`. These are short tokens without whitespace. The writer must **refuse** if the shim's absolute path or the model contains whitespace, because there is no way to quote it.

**No `review` verb in the MVP.** GSD lanes own review argv (§0.8), and `dispatch-reviewer` already covers ai-kit-spec-review. Named as skipped.

**No PATH-installed `ai-kit-xai` binary.** The installer only symlinks skills into `~/.claude/skills` (`tools/setup.py` `apply_additive_skills`, `os.symlink`). An absolute `python3 <shim>` path works under GSD's argv spawn. A PATH binary would need installer work for no functional gain.

**What `xai` does**, a thin body over existing code (~60 LOC):
1. `prompt = sys.stdin.read()`.
2. Increment 2: append the inlined role skills (§3.3).
3. Call `dispatch_execute({"cli", "model", "effort"}, prompt, os.getcwd(), heartbeat_interval=30, timeout=T, format_block=GSD_SUMMARY_FORMAT_BLOCK, ...)`. This reuses `execute_dispatch.py:32`, including the soft-confinement prose and tooling guidance.
4. Choose the timeout as follows:
   - `T` is `--timeout` when given;
   - otherwise `T = workflow.cross_ai_timeout - 30` (read via `gsd-tools query config-get`, with 300 as the fallback). That way a later edit to `cross_ai_timeout` cannot desynchronise inner from outer.
5. Write the stdout only, then map the exit code (§3.5).
6. `--print-argv` prints the resolved argv and env deltas, then exits 0 without running anything. This is the anti-slip debugging aid, for agents and for gsd-config users who want the string.

**Two small additions in `dispatch.py`** (shared, so `dispatch-execute` benefits too):
- `env=` parameter. The wrapper passes `os.environ` minus `CLAUDECODE` and the other host signals (`PI_CODING_AGENT`, `OPENCODE`, `CURSOR_AGENT`, `CODEX_THREAD_ID`), plus the per-CLI env from §3.2.
- SIGTERM/SIGINT forwarding. While a child is alive, a handler kills the child's group with `os.killpg` and lets the existing drain-and-return path finish. This closes failure mode 6. About 8 lines; keep `start_new_session=True`.

### 3.2 Per-CLI profiles "as data"

**The argv stays in the existing builders.** `commands.py` already is a per-CLI profile registry with live-verified docstrings, and rewriting builders into a table adds churn without fixing a bug.

**Add one small data dict** for the axes builders do not cover (`CLI_RUNTIME_PROFILE` in `commands.py`, next to `NO_HARD_SANDBOX_CLIS`):

```python
CLI_RUNTIME_PROFILE = {
  # extra_args: appended to the execute argv; env: set on the child; skills_off: host-discovery kill switch
  "opencode":     {"env": {"OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1"}, "skills_off": "env", "resume": "-s {sid}"},
  "cursor-agent": {"extra_args": ["--approve-mcps"], "skills_off": None,   "resume": "--resume {sid}"},
  "codex":        {"skills_off": None,  "resume": "exec resume {sid}"},
  "claude":       {"extra_args": ["--disable-slash-commands", "--strict-mcp-config"], "skills_off": "flag",
                   "resume": "--resume {sid}", "preassign_sid": "--session-id {sid}"},
  "pi":           {"extra_args": ["--no-skills"], "skills_off": "flag", "preassign_sid": "--session-id {sid}"},
}
TRANSIENT_PATTERNS = ("temporarily unavailable", "cooling down", "is locked", "rate limit", "overloaded", "529")
FATAL_PATTERNS = ("402", "403", "spending limit", "requires an opencode API key", "pre-dispatch filters",
                  "Credential gate", "authentication", "billing")
```

Per-entry status:
- opencode `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS`: [V] docs.
- cursor-agent `--approve-mcps`: [V] flag exists; [U] whether it is needed.
- claude `--disable-slash-commands` and `--strict-mcp-config`: [V] help.
- pi `--no-skills` and `--session-id`: [V] help.
- Resume shapes: [V] in each CLI's help. Session-id capture for opencode and codex is [U] (see §3.4).
- Transient and fatal strings: [V] 16-HANDOFF and memory for opencode. Claude's categories come from the docs' `api_retry` error list. Codex, cursor and pi patterns are [U] and need fixtures from real failures.

**New pi builder** in `_COMMAND_BUILDERS[("execute","pi")]`:
```python
def _build_pi_execute_command(target_dir=None, **_p):
    quoted = _require_target_dir("pi", target_dir)
    return f"sh -c 'cd {quoted} && exec pi -p --model {{model}}'"   # stdin → initial message (dist/cli/initial-message.js)
```
- pi has no cwd flag. The `sh -c` form is safe here only because the wrapper runs it with `shell=True`; never write it raw.
- Add `"pi"` to `NO_HARD_SANDBOX_CLIS`: pi has "No permission popups" and no sandbox [V README].
- Effort goes on the model suffix `:<thinking>` or through `--thinking` [V help]. Map `--effort` to `--thinking {effort}`.
- Add `"pi"` to `detection.KNOWN_CLIS` so `which pi` gates it. Model enumeration stays SPEC-05/Phase 22. Until then pi is a candidate only when the user supplies `--model`, or when the curated router or slot names it.

**Fix needed in the claude execute builder:**
- Problem: `--restricted` blocks Bash and git, which the executor role needs.
- Option A: `--permission-mode acceptEdits --allowedTools "Bash"`, drop `--restricted`, and move claude into `NO_HARD_SANDBOX_CLIS`. Softer confinement, but a usable executor.
- Option B: keep it and mark claude "not eligible for `gsd-executor`" in XAI-02 candidate selection.
- **This is a user decision.** The current builder's confinement was an explicit, live-tested choice (`commands.py:207-226`). Option B is zero code: only a filter in the Phase 18 candidate picker.

### 3.3 Minimal skills and MCP per role

**Source of truth:** GSD's own `agent_skills.<role>`, which Phase 18 SKL-02 already writes (18-CONTEXT D-02/D-04, with a rigor cap of 2/3/5).
- The wrapper runs `gsd-tools query agent-skills <role>`, defaulting to `gsd-executor`. GSD resolves `global:`, project paths and `trusted_global_roots` itself (`init.cjs:3627-3754`).
- So cross-AI executors get exactly the native executor's skill set, with no second resolver and no second config.

**Delivery (one rule, about 10 lines):**
- For each `- @<abs>/SKILL.md` line in the block, inline the file content under a `## Skill: <name>` heading. Drop plugin `directive` lines (`Load ... via the Skill tool`, Claude-only) unless `cli == "claude"`.
- **Why inline instead of passing paths:** paths under `~/.claude/skills` sit outside the workspace. That means `external_directory=ask` on opencode, file tools confined to the working dirs on claude under `--restricted`, and pi only expanding `@file` on argv. Inlining removes every per-CLI read-permission question.

**Switch off host discovery** where a verified kill switch exists:
- pi: `--no-skills`.
- claude: `--disable-slash-commands`. `--bare` is avoided because it refuses OAuth [V docs].
- opencode: `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`, which removes `~/.claude/skills`. `~/.agents/skills` would still load. [U] whether `OPENCODE_DISABLE_EXTERNAL_SKILLS` covers it; probe before relying on it. An alternative that is documented but needs the skill names: `OPENCODE_PERMISSION='{"skill":{"*":"deny"}}'`, which hides every skill "from agent, access rejected".
- cursor-agent and codex: no verified switch, so discovery stays on and is named as a residual risk. codex `--ignore-user-config` would also drop provider/model config, so it is rejected.
- Make discovery-off a profile flag that only the `gsd-executor` role sets.

**MCP:**
- claude: `--strict-mcp-config`, so no MCP unless `--mcp-config` is given.
- cursor: `--approve-mcps`, so headless MCP calls do not stall. [U]
- opencode: leave the config alone. `--pure` drops plugins, not MCP [V help]; skip it.
- The existing tooling guidance (`tooling_guidance.py`) already tells the CLI which MCPs and tools are confirmed. Keep it.

**How each host is "told":** the inlined block in the prompt is the universal channel. The flags and env above only *remove* noise; nothing extra needs to be installed per host.

### 3.4 Heartbeat, timeout, retry

- **Heartbeat:** keep `dispatch_with_heartbeat`'s 30 s stderr line, which lands in GSD's `$ERROR_LOG`. Upgrade: reuse `dispatch_with_polling`'s "+N bytes" growth report, so a tail of `ERROR_LOG` tells "slow" from "stuck" (the memory note on diagnosing killed dispatches).
- **Timeout:** inner deadline `T = cross_ai_timeout - 30` (§3.1), SIGTERM forwarding (§3.1), and on the inner timeout exit **124**.
- **Retry (increment 2), only for classified transient errors:**
  - Classify on the CLI's exit != 0, stderr matching `TRANSIENT_PATTERNS`, and no `FATAL_PATTERNS` match.
  - Retries are bounded by the remaining deadline. Use at most 2 retries with a 60 s backoff, in line with the 16-HANDOFF policy of retrying once and then falling back.
  - **Resume over re-run:** retry by resuming the same session with xai_exec.sh's RESUME_MSG ("inspect git status/diff/log first, do not redo completed steps").
  - Session ids:
    - pi and claude: pre-assign (`--session-id`; claude needs a UUID). [V flags]
    - cursor: `cursor-agent create-chat`, then `--resume <id>`. [V help]
    - opencode and codex: capture from `--format json` / `--json` events. [U] for the field names; `xai_exec.sh`'s `session list` hack is racy.
    - Where no id is available, re-run fresh with RESUME_MSG prepended.
  - When retries run out, exit **75** (EX_TEMPFAIL). GSD shows the stderr tail and offers retry, skip or abort.
- **Prompt-size guard:** when the composed prompt exceeds 200 KB, print a one-line stderr warning (the 263 KB failure). Never truncate.

### 3.5 stdout and exit-code contract

stdout:
- Only the CLI's final answer (the SUMMARY candidate).
- MVP strips ANSI codes (`\x1B\[[0-9;]*[A-Za-z]`, as in `xai_exec.sh:65`).
- Upgrade: extract the last assistant message per CLI. Use `codex -o <tmp>` (as the GSD codex lane does), `opencode --format json` text-part rebuild (as the GSD opencode handler does), and claude/cursor `--output-format text`, which print only the result [V docs].

stderr:
- The first line is `ai-kit xai: cli=<c> model=<m> argv=<shlex-joined> timeout=<T>s skills=<n>`.
- Then the heartbeats and the classified error, so a GSD failure is diagnosable from `$ERROR_LOG` alone.

Exit codes:
- `0`: the CLI exited 0. GSD validates the summary itself.
- `1..123`: the CLI's own code, passed through.
- `124`: the wrapper's deadline hit (GNU and `run-with-timeout` parity).
- `2`: usage or config error, such as an unknown CLI, no builder, a whitespace path, or a missing `--model`.
- `127`: CLI binary not on PATH. Pre-check with `shutil.which`.
- `75`: transient error and retries exhausted (increment 2).
- `128+n`: the wrapper itself was signalled.

### 3.6 How the writers write it

- **curated-config v1 `apply-execution` and v2 XAI-02:**
  - `cross_ai_build.build_execution_command(cli, model, project_dir)` returns `python3 <shim> xai --cli <cli> --model <model>`.
  - It resolves `<shim>` to `ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py` with `model_detect.resolve_ai_kit_spec_path` generalised to a skill-name parameter.
  - It still calls `build_execute_command` first as the "is there a live builder?" gate (keeps D-05 fail-closed). It returns `None` when the shim or the builder is missing, or a value contains whitespace.
  - It also writes `workflow.cross_ai_timeout` (300 for MVP, 600 otherwise, per spec §6) in the same apply. It does **not** write `cross_ai_execution` twice.
  - This satisfies XAI-02's wording ("built by `build_execute_command`, bare CLI name") in spirit. The amendment needed is "wrapped by the `xai` entry point".
- **execute-gsd SKILL.md Step 2:** replace the `WRAPPER_COMMAND` line (`:152`) and the `FORMAT_BLOCK_PATH` / `print-summary-format-block` lines with the same `xai` string. Delete the 840/900 pairing prose. Keep the ownership-marker writes.
- **GSD's own gsd-config (free text):** ai-kit cannot change it.
  - Provide `ai-kit-spec-gsd.py xai --cli X --model Y --print-command`, which prints the exact string to paste.
  - Optional lint: the config-doctor PRD, or a `xai --check-config` that shlex-splits the current `workflow.cross_ai_command` and flags known slips. The slips: opencode without `--auto`, cursor without `--trust`/`--force`, codex with `--full-auto` or `-a`, `sh -c '` in a raw string, and a raw string instead of the wrapper. About 20 lines; increment 2.

### 3.7 Phase 18 overlap

**XAI-02 (execution):**
- This design *is* the `cross_ai_command` half. Fold it into Phase 18's XAI-02 plan as one task ("wrapper entry point + writer switch") ahead of the scoring and timeout work.
- Amend XAI-02 and spec §6 from "built by `build_execute_command`" to "an ai-kit `xai` wrapper command (builder-gated)".
- The claude-as-executor decision from §3.2 belongs in XAI-02's candidate filter.

**XAI-01 (review):** no overlap beyond extending `CLI_TO_REVIEWER_SLUG`, which 18-CONTEXT already notes. GSD descriptors own lane argv. pi has no lane (18-CONTEXT:26).

**SKL-01..03:** the wrapper consumes `agent_skills.gsd-executor` as SKL-02 writes it. The D-04 cap (2/3/5) bounds the inlined prompt growth. Adding `--role` costs nothing extra.

**SPEC-05 (Phase 22, pi enumeration) and SPEC-06 (Phase 21, cursor wrapper):**
- The pi builder can land in 18. Pi *candidate selection* waits on SPEC-05 unless the user pins a model.
- SPEC-06 does not affect the wrapper, because it always passes `--model` and GSD spawns the real binary. It affects only detection.

**v1 kept (D-08):** v1 `apply-execution` switches to the wrapper string too, since it is the same function. Update the v1 tests rather than fork the function; failure mode 2 is a live bug in v1 today.

---

## 4. Ponytail lens: increments

**Increment 1 (fixes the slipping; about 60–80 LOC plus tests):**
1. `ai_kit_spec_gsd/cli.py`: `xai` subcommand. It covers stdin to `dispatch_execute`, cwd target, the in-code format block, the timeout default from config, exit-code mapping (124, 127, 2), the stderr argv line, ANSI strip, `--print-argv`, and `--print-command`.
2. `dispatch.py`: `env=` passthrough plus SIGTERM/SIGINT group forwarding. The wrapper scrubs `CLAUDECODE` and the other host signals.
3. `cross_ai_build.build_execution_command` returns the wrapper string, and `_cmd_apply_execution` also writes `cross_ai_timeout`.
4. SKILL.md Step 2: one-line swap; delete the format-file and timeout-pair prose; trim `dispatch-notes.md`.
5. pi: the builder plus a `KNOWN_CLIS` entry.

**Increment 2:**
- `agent_skills` inline and discovery-off flags (`CLI_RUNTIME_PROFILE`).
- Transient-only retry with resume.
- Per-CLI final-message extraction.
- The `--check-config` lint.

**Skipped on purpose:**
- `review` verb: GSD lanes own it.
- PATH binary.
- Rewriting builders as a data table.
- GSD overlay reviewer capability for pi.
- Model fallback chains inside the wrapper: GSD's skip falls back to native, and the 16-HANDOFF policy says the same.
- Retry for non-transient errors.

---

## 5. Migration

1. Land increment 1 behind the existing tests, and add the new ones from §6.
2. Re-run curated-config `apply-execution` (or v2 `apply`) on target projects, and the execute-gsd SKILL also overwrites its ownership-marked value on its next run. Old raw strings keep "working" exactly as badly as today, so nothing breaks.
3. For **this repo's** hand-set value `opencode run --model router-env/my-coding`: per the user rule of no real curated `apply` on ai-kit itself during v1.3, report it and let the user change it with `config-set`. The proposed value is `python3 ~/.claude/skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py xai --cli opencode --model router-env/my-coding`, which needs the absolute path expanded.
4. Leave `dispatch-execute` in place as the generic primitive. `xai` is its GSD-shaped caller, so there is no deprecation churn.
5. Retire `cross-ai-scripts/xai_exec.sh` once increment 2's resume-retry passes the live check. Keep `xai_finalize.sh`'s git-fact frontmatter idea as a separate todo, because GSD writes the SUMMARY itself.

---

## 6. Test plan

Unit (`tests/test_ai_kit_spec_gsd.py`, `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_gsd_curated_config.py`; same injected `*_fn` pattern as today). Currently 25, 41 and 10 references to the touched functions respectively (`grep -c`).

- `xai`:
  - stdin reaches `dispatch_execute` with `target_dir == cwd` and `format_block == GSD_SUMMARY_FORMAT_BLOCK`;
  - stdout carries only the CLI stdout, ANSI-stripped;
  - `timed_out` maps to 124, a missing binary to 127, an unknown CLI to 2, a whitespace model to 2;
  - the CLI's own code is passed through;
  - with no `--timeout`, T is read from `cross_ai_timeout - 30`.
- `dispatch.py`:
  - the child env lacks `CLAUDECODE`;
  - a SIGTERM delivered to the wrapper kills the child group. Use a real `sleep` grandchild, like the existing live-reproduction tests in `dispatch.py`'s docstrings.
- **Word-split invariant (the bug class):**
  - for every CLI and both writers, `shlex.split` of the stored value equals `value.split()` (no quotes, no whitespace in tokens);
  - executing `value.split()` as argv with a stub `python3` that echoes argv yields the intended `xai` arguments.
- The curated-config writer returns the wrapper string, returns `None` when the shim or builder is missing, and writes `cross_ai_timeout`. Update the v1 tests that assert the raw string.
- The pi builder renders `cd <dir> && exec pi -p --model M`, and pi is in `NO_HARD_SANDBOX_CLIS`.
- Increment 2:
  - inline expansion of `- @path` lines;
  - directive lines dropped for non-claude;
  - transient classifier fixtures, one per real error string from 16-HANDOFF plus the 403 spending-limit message;
  - resume argv per CLI.

Live checks (cheap, in a throwaway git repo outside `/tmp`, because codex's `/tmp` carve-out is noted at `commands.py:156-160`):
1. `echo "create a.txt with 'ok' and git commit it" | node gsd-tools.cjs run-with-timeout 120 -- python3 <shim> xai --cli <c> --model <m>` for opencode, cursor, codex and pi. Assert the file exists, a commit landed, stdout is SUMMARY-shaped, and the exit is 0.
   - This also answers the [U] codex question of whether `.git` is writable under workspace-write.
2. Outer timeout 20 s with an inner deadline derived: assert exit 124 and no orphan (`pgrep -f <cli>` is empty).
3. opencode without `--auto`, with a prompt that reads `~/.claude/skills/x/SKILL.md`. Observe stall or deny, to settle the [U] in §1.7.
4. cursor with and without `--approve-mcps`, calling one MCP tool.
5. Phase 19 gate: `/skill-judge` on the edited `ai-kit-spec-execute-gsd/SKILL.md` (memory: skill-judge in code review).

---

## 7. Open questions for the user

- Claude as a cross-AI executor target: Option A (allow Bash, soft confinement) or Option B (exclude it)? See §3.2.
- Increment 2's discovery-off for opencode: accept the documented `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS`, which leaves `~/.agents/skills` loading, or probe `OPENCODE_DISABLE_EXTERNAL_SKILLS` first?

## Sources

- Code (review tree): `skills/ai-kit-spec-review/ai_kit_spec/{commands.py,dispatch.py,execute_dispatch.py,cli.py,detection.py,config_io.py}`, `skills/ai-kit-spec-execute-gsd/{SKILL.md,references/dispatch-notes.md,ai_kit_spec_gsd/*.py}`, `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/{cross_ai_build.py,cli.py,model_detect.py,workflow_defaults.py}`, `.planning/phases/16-*/cross-ai-scripts/*.sh`, `16-HANDOFF.md`, `18-CONTEXT.md`, `REQUIREMENTS.md`, `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`.
- GSD: `~/.claude/gsd-core/workflows/{execute-phase.md,execute-phase/detail/elaboration.md,review.md,settings-advanced.md}`, `bin/gsd-tools.cjs` (run-with-timeout), `bin/lib/{review-lane-descriptor.cjs,review-reviewer-selection.cjs,config.cjs,init.cjs}`.
- Local CLIs: `cursor-agent --help`, `opencode run --help`, `codex exec --help`, `codex --help`, `codex features list`, `claude --help`, `pi --help`, pi `README.md` and `dist/` source.
- Official docs:
  - [opencode permissions](https://opencode.ai/docs/permissions/)
  - [opencode skills](https://opencode.ai/docs/skills/)
  - [opencode agents](https://opencode.ai/docs/agents/)
  - [opencode CLI/env](https://opencode.ai/docs/cli/)
  - [Cursor headless](https://cursor.com/docs/cli/headless)
  - [Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode)
  - [Codex sandboxing](https://learn.chatgpt.com/docs/sandboxing)
  - [Claude Code headless](https://code.claude.com/docs/en/headless)
