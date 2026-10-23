# 06 - pi coding agent as GSD's cross-AI executor

Date: 2026-10-13. Scope: read-only analysis. No config or repo was modified. Live runs: 2 pi prompts and 1 opencode prompt, all "Reply with exactly: OK" on the local `router-env/my-coding` model, which costs $0 according to pi's own usage record (`cost.total: 0`).

## TL;DR

1. **pi is a good fit for cross-AI execution. Verified locally.**
   - Same model, same router, same prompt: pi took 3.94 s wall and 188 MB RSS. `opencode run` took 16.52 s and 668 MB.
   - pi used 16.9k total tokens; opencode used 36.5k.
   - Print mode (`-p`) writes only the final assistant text to stdout. That is exactly the shape GSD needs for a SUMMARY.
   - pi never shows permission prompts.
2. **MCP: the user is right that it changed.**
   - pi **0.99.0 (2026-09-29)** added native MCP as a built-in extension (`builtin:mcp`, `mcp.json`, `pi mcp add|list|login`).
   - The **installed pi 0.82.1 predates it.** Its own README says "**No MCP.**"
   - npm `latest` is **1.2.0** (2026-10-12).
3. **Switching the CLI does not fix the router.** The Phase 16 failures (capacity, 402 billing, credential gate) came from `router-env`, not from opencode.
   - pi on `router-env/my-coding` will see the same errors.
   - The real reliability win is pi's direct OAuth subscriptions, which skip the router: `openai-codex/*` and `anthropic/*` are both logged in.
4. **Top hazard found live: pi blocks forever on an open non-TTY stdin.** It reads stdin until EOF.
   - GSD's normal path pipes a prompt, so EOF arrives and the run is fine.
   - Any resume or retry call (like `xai_exec.sh:44,59`, which passes the prompt as an argument) **must** add `< /dev/null`. Otherwise it hangs until `run-with-timeout` kills it.
5. **Unattended-safety gaps:**
   - No sandbox and no permission gate.
   - The user's pi config auto-loads the superpowers package skills, the subagent extension and the rtk bash rewriter.
   - Disable them per run with `-ns -ne`. Contain writes the way the opencode and cursor lanes already do.

## 1. Identity: package, owner, version

- npm package: `@earendil-works/pi-coding-agent`. Installed: 0.82.1 under Volta. The repo is `git+https://github.com/earendil-works/pi.git`, directory `packages/coding-agent`, author Mario Zechner.
  - Evidence: installed `package.json` at `~/.volta/tools/image/packages/@earendil-works/pi-coding-agent/lib/node_modules/@earendil-works/pi-coding-agent/package.json`.
- Owner and maintainers on npm: `mitsuhiko`, `badlogic`, `rwachtler`.
  - Dist-tags: `latest: 1.2.0`, `legacy-node20: 0.74.2`.
  - Release dates: 1.2.0 on 2026-10-12, 1.1.0 on 2026-10-07, 1.0.0 on 2026-10-01.
  - Evidence: `curl https://registry.npmjs.org/@earendil-works%2fpi-coding-agent`.
- The old package `@mariozechner/pi-coding-agent` stops at 0.73.1 and is deprecated: "please use @earendil-works/pi-coding-agent instead going forward" (npm registry).
- GitHub: `github.com/earendil-works/pi` returns 200, MIT, about 115k stars. Both `earendil-works/pi-mono` and `badlogic/pi-mono` return 301 to `earendil-works/pi`.
  - The docs still link to `pi-mono` paths, for example `docs/json.md` and `docs/security.md:57`.
- **Confidence: high.** Everything here comes from registry and GitHub HTTP responses.

## 2. Headless modes and stdin

All findings below were checked against the installed 0.82.1 source and the 1.2.0 docs.

- **Modes** (`pi --help`, scratchpad `pi-help.txt:21-22`; 1.2.0 `docs/cli-integration.md`):
  - `-p/--print` writes the final text to stdout.
  - `--mode json` writes a JSONL event stream.
  - `--mode rpc` is a long-lived bidirectional JSONL protocol.
  - The SDK embeds pi in-process.
- **Auto print mode:** if stdin or stdout is not a TTY, pi picks print mode even without `-p`.
  - `dist/main.js` `resolveAppMode`: `if (parsed.print || !stdinIsTTY || !stdoutIsTTY) return "print"`.
- **stdin is merged into the initial prompt** in print and json modes. Example: `cat README.md | pi -p "Summarize"` (`docs/usage.md:176`).
  - `readPipedStdin()` (`dist/main.js:43-58`) skips reading only when stdin is a TTY. Otherwise it waits for the `end` event, with **no timeout**.
  - **Verified live:** under the agent harness, stdin was an open socket (`/proc/<pid>/fd/0 -> socket:[...]`). pi printed nothing for more than 180 s and opened no connection to the router. With `< /dev/null` the same command finished in 3.94 s.
  - Consequence: GSD's documented contract (prompt piped on stdin, `execute-phase.md:417`) is safe. **Every other invocation needs `< /dev/null`**, including resume, retry and probe calls.
- **Print-mode output:**
  - `dist/modes/print-mode.js:100-116` prints only the `text` blocks of the **last assistant message**. Tool output, thinking and intermediate turns never reach stdout.
  - This is cleaner than opencode, whose stdout needed ANSI stripping and a heading search (`xai_exec.sh:64-67`).
- **Exit codes:**
  - Print mode exits 1 when the final message's `stopReason` is `error` or `aborted`; the error text goes to stderr (`print-mode.js:105-107`). Any thrown error also exits 1 (`:120-122`).
  - SIGTERM exits 143 and SIGHUP exits 129, after killing tracked detached children (`:28-43`). `run-with-timeout` adds 124 for a timeout (`gsd-tools.cjs:4880-4890`).
  - **New in 1.2.0:** a `length` stop (output-token cap reached) now prints the partial text, warns on stderr and exits 1. Before that fix it exited 0 (CHANGELOG 1.2.0, issue #10799).
  - **JSON mode exits 0 even when the assistant errors.** The 1.2.0 `docs/cli-integration.md` says to inspect the events. Use `-p` text mode for GSD.
- **Confidence: high.** Source-verified and reproduced live.

## 3. Tools and permissions

- **Built-in tools** (`pi --help`, `pi-help.txt:162-169`):
  - On by default: `read`, `bash`, `edit`, `write`.
  - Read-only and off by default: `grep`, `find`, `ls`.
  - Tool selection flags: `--tools/-t`, `--exclude-tools/-xt`, `--no-tools/-nt`, `--no-builtin-tools/-nbt`.
  - 1.1.0 added `*` patterns and `+name/-name` edits to the defaults.
- **No permission prompts in any mode.** README Philosophy: "**No permission popups.** Run in a container, or build your own confirmation flow with extensions." Also `docs/usage.md:296`.
  - Headless runs therefore need no `--yolo`, `--force` or `--auto` flag.
- **Project trust is not a sandbox** (`docs/security.md:7,29,31-37`).
  - In `-p`, json and rpc modes, project-local `.pi/*` resources are ignored unless trusted (`defaultProjectTrust: ask` acts like never). `--approve/-a` and `--no-approve/-na` override this per run.
  - `AGENTS.md` and `CLAUDE.md` load regardless of trust.
- **No built-in sandbox** (`docs/security.md:31-35`): "Built-in tools can read files, write files, edit files, and run shell commands with the permissions of the pi process." The 1.2.0 `docs/security.md:16,99` says the same.
- **pi sets `PI_CODING_AGENT=true`** in its own process env (`dist/cli.js:12`), so every bash child (make, unittest, gsd-tools) inherits it.
  - Verified harmless for ai-kit tests: `tests.test_ai_kit_spec`, `tests.test_ai_kit_spec_gsd` and `tests.test_ai_kit_gsd_curated_config` gave "Ran 751 tests ... OK" both with and without `PI_CODING_AGENT=true`. The run was in the review tree, which stayed clean.
  - Inference, medium confidence: gsd-tools commands run *by* the executor may now detect host runtime = pi. ai-kit's own detection order puts pi first (`detection.py:51`; design doc line 18-19).

## 4. Extensions, skills and context

- **Extensions:** TypeScript modules with `registerTool`, `registerCommand` and `pi.on(...)` events.
  - Discovered from `~/.pi/agent/extensions/`, `.pi/extensions/` (trust-gated) and packages.
  - `-e <path>` loads one explicitly. `-ne/--no-extensions` disables discovery (README:370-397; `pi-help.txt:40-41`).
  - In 1.x, `-ne` also disables the built-ins (`builtin:mcp`, `builtin:codemode`, `builtin:tool-search`). `-ne -e builtin:mcp` keeps only MCP (1.2.0 `docs/cli.md:195-199`, `docs/settings.md:162`).
- **The user's active extensions** (read-only inspection):
  - `extensions/rtk.ts` rewrites every `bash` tool command through `rtk rewrite` and fails open (`rtk.ts:59-79`). It can be disabled with `RTK_DISABLED=1` (`rtk.ts:67`).
  - `extensions/subagent/` is a symlink to the package's example subagent extension. It registers a tool that spawns more `pi` processes.
  - `settings.json` `packages: ["git:github.com/obra/superpowers"]` loads the 14 superpowers skills.
- **Skills:** pi implements the Agent Skills standard (agentskills.io) and is lenient on name and directory mismatch (`docs/skills.md:7`).
  - Discovery locations: `~/.pi/agent/skills/`, `~/.agents/skills/`, project `.pi/skills/` and `.agents/skills/` (trust-gated), packages, the settings `skills` array, and `--skill`.
  - Loading is progressive: names and descriptions go into the system prompt as XML, and the model `read`s SKILL.md on demand. This happens only when the `read` tool is enabled (`dist/core/system-prompt.js`: "Append skills section (only if read tool is available)").
  - `-ns/--no-skills` disables discovery.
  - Local count: 33 entries in `~/.pi/agent/skills`, 42 in `~/.agents/skills`, 14 superpowers skills.
- **Context files:** `~/.pi/agent/AGENTS.md`, plus `AGENTS.md` and `CLAUDE.md` walking up from the cwd (`docs/usage.md:100-107`). `-nc` disables them.
  - ai-kit's `AGENTS.md` is 13,587 bytes and loads automatically. That is desirable: it carries the house rules.
  - Note: the user's `~/.pi/AGENTS.md` (155 bytes) sits outside `~/.pi/agent/`, so pi does not read it. Inference from the documented path list.
- **Confidence: high** for the docs and the config inspection. **Medium** that the superpowers "using-superpowers / brainstorming" skills would derail a headless executor; that is inference from their mandatory-use descriptions and was not tested.

## 5. MCP: exact status

- **pi 0.82.1 (installed): no native MCP.**
  - README:495: "**No MCP.** Build CLI tools with READMEs..., or build an extension that adds MCP support."
  - `docs/usage.md:296`: "intentionally does not include built-in MCP".
  - The only route was a third-party extension such as `pi-mcp-adapter` by nicobailon: npm latest 5.3.0, created 2026-01-19, repo `github.com/nicobailon/pi-mcp-adapter`.
- **pi ≥ 0.99.0 (2026-09-29): native MCP as a built-in extension.**
  - CHANGELOG 0.99.0: "Added codemode, tool search, and MCP support as built-in extensions... MCP servers over stdio or streamable HTTP, with OAuth, come from `mcp.json` (global, or per project once trusted) or `pi.registerMcpServer()` and are managed with `/mcp` and `pi mcp add|remove|list|login|logout`" (#10040).
  - Config: `~/.pi/agent/mcp.json` and project `.pi/mcp.json` (trust-gated), in the standard `mcpServers` format with `command/args/env/cwd` or `url/headers/oauth`. Legacy SSE is not supported (1.2.0 `docs/mcp.md:30-73`).
  - **Exposure model** (`docs/mcp.md:189-200`). Tools are named `mcp__<server>__<tool>`.
    - `codemode` is the **default**: tools are callable only from JavaScript the model writes in the `codemode` tool, which runs in a QuickJS sandbox.
    - `deferred`: the model finds tools via `tool_search`.
    - `direct`: the tools are declared to the model like built-ins.
    - `hidden`: registered but unreachable.
  - **Headless behaviour:** servers connect in the background. "The first prompt waits up to 10 seconds only for servers with `direct` tools." HTTP transient errors are retried twice (`docs/mcp.md:100`).
  - **Per-run controls:** `--no-mcp` (1.0.4+); `--exclude-tools 'mcp__*'`; `--tools read,bash,'mcp__srv__*'` (1.2.0 `docs/cli.md:120-138`).
  - **Validation:** `pi mcp list` exits 1 when an entry is invalid or an enabled server is not connected (`docs/cli.md:327`). It suits a pre-flight check.
  - **Permissions:** MCP calls pass through `tool_call` and `tool_result` extension hooks, so a permission-gate extension also covers MCP (`docs/mcp.md:250-254`).
  - 1.0 to 1.2 shipped many MCP OAuth fixes (CHANGELOG 1.0.0-1.2.0), so the feature is two weeks old and still moving.
- **Relevance to GSD cross-AI execution: low.** A cross-AI plan's prompt is self-contained: objective plus tasks, then bash, make, unittest and git. The Phase 16 executions needed no MCP (`xai_exec.sh` prompt, lines 17-32).
  - Recommendation: run executors with MCP **off** for determinism (`-ne`, or `--no-mcp` on 1.x). Upgrade to ≥1.0.4 only if a future plan genuinely needs an MCP tool.
- **Confidence: high.** Changelog and docs come from the 1.2.0 npm tarball, saved under scratchpad `dl-pi-1.2.0/package/`.

## 6. Models and providers

- `--model provider/id[:thinking]`, `--provider`, `--thinking off|minimal|low|medium|high|xhigh|max`, `--api-key` and `--list-models` (`pi-help.txt:16-50`). `pi --list-models` took 0.389 s.
- **User's providers:**
  - `auth.json` keys only: `anthropic` (oauth) and `openai-codex` (oauth). No secrets were printed.
  - `models.json` defines a custom provider `router-env` at `http://127.0.0.1:20128/v1` with `api: openai-completions`, `supportsReasoningEffort: false`, and the models `my-planning`, `my-plan-review` and `my-coding`.
  - The router was up: unauthenticated `/v1/models` returned 401, and the port listened via `rootlessport`.
- **Defaults to override:**
  - `settings.json` sets `defaultProvider: openai-codex`, `defaultModel: gpt-5.6-terra`, `defaultThinkingLevel: xhigh`.
  - An executor command must pin `--model` and `--thinking`. Otherwise it silently runs a frontier model at xhigh.
- **Custom providers** (`docs/models.md:132-170`): `baseUrl`, `api`, `apiKey`, `headers` and `compat`.
  - `apiKey` supports `"$ENV"`, `"!shell-command"` and literal values. The router entry above uses this same mechanism.
- **Built-in retry** (`docs/settings.md:134-147`): `retry.enabled=true`, `maxRetries=3`, backoff 2, 4 and 8 s.
  - The classifier matches `overloaded`, `rate.?limit`, `429`, `5xx`, `service.?unavailable`, `timeout`, ... and **never** retries `billing`, `quota exceeded` or `insufficient_quota` (`pi-ai/dist/utils/retry.js:4-50`).
  - The router's "temporarily unavailable", "cooling down" and "is locked" strings are not in the list unless they arrive with a 5xx code. Inference, medium confidence.
  - So pi's internal retry covers about 14 s of blips. The wrapper still needs its own longer resume loop.

## 7. Sessions, resume and retries

- Flags: `-c`, `-r`, `--session <path|id>`, `--session-id <id>` (opens the exact ID or **creates it**), `--fork`, `--session-dir <dir>`, `--no-session`, `-n <name>` (`pi-help.txt:23-30`; 1.2.0 `docs/cli.md:85-107`).
  - `--session-id` cannot be combined with `--session`, `-c` or `-r`.
- **Best retry pattern:** the wrapper picks a deterministic ID up front, such as `gsd-<phase>-<plan>-<epoch>`, and passes `--session-id $SID` on both the first run and every resume.
  - This removes the fragile `opencode session list | sed | awk` scrape (`xai_exec.sh:50`).
  - Verified live: `--session-dir` created `2026-10-13T13-38-50-999Z_<uuid>.jsonl` holding `session`, `model_change`, `thinking_level_change` and the user and assistant messages with `usage`.
- Session files are JSONL with per-message `usage` (input, output, cacheRead, cacheWrite, cost). That gives free token accounting for the usage-metrics pipeline.

## 8. Live measurements (n=1 each, so medium confidence on the timing deltas)

Host: Linux (Bazzite). All runs were in `~/git/personal/ai-kit` (`main`), so the repo `AGENTS.md` applied. Raw outputs are in scratchpad `pi-measure/`.

- **`time pi --version`:** 0.354 s real.
- **`time pi --help`:** 0.465 s real.
- **pi run 1:** `pi --mode json --no-tools --no-session --model router-env/my-coding "Reply with exactly: OK" < /dev/null`
  - Exit 0, **wall 3.94 s**, maxrss 188 MB, output `OK`.
  - Usage: `input 5093, output 26, cacheRead 11776, totalTokens 16895, cost 0`.
- **pi run 2:** `printf 'Reply with exactly: OK' | pi -p --no-tools -nc -ne -ns --offline --session-dir <scratch> --model router-env/my-coding`
  - Exit 0, **wall 5.27 s**, maxrss 179 MB, stdout exactly `OK\n` and stderr empty.
  - Usage: `input 535, output 18, cacheRead 11776, total 12329`.
  - This confirms stdin delivery, clean text capture and session persistence.
- **opencode:** `printf 'Reply with exactly: OK' | opencode run --model router-env/my-coding --format json`. This is the current `cross_ai_command` model; opencode has no default `model` key in `opencode.jsonc`.
  - Exit 0, **wall 16.52 s**, maxrss **668 MB**.
  - Tokens: `total 36459, input 32593, output 26, cache.read 3840`.
- **The other CLIs, `--version` only** (no prompts; the brief did not allow them):
  - opencode 1.18.35: 0.27 s.
  - cursor-agent 2026.10.01: 0.25 s.
  - codex-cli 0.153.4: 0.00 s.
  - claude 2.1.296: 0.01 s.
  - These numbers do **not** measure agent cold start.
- **Token analysis:**
  - pi's own default system prompt is small: a template of about 2.3 KB in `dist/core/system-prompt.js`, plus tool snippets and the skills XML.
  - Run 2 drops context, skills and extensions. Of its 12.3k prompt tokens, only 535 were uncached input; **11,776 cached tokens appear in every router-env call.**
  - Inference, medium confidence: the router or its upstream adds an approximately 11.7k-token prefix. pi's own floor is about 0.5-0.6k tokens. ai-kit's `AGENTS.md` adds about 4.6k (5093 - 535).
  - opencode's request carried about 32.6k uncached input, roughly 2x pi's 16.9k for the same task. 1.2.0 CHANGELOG notes a default tools+codemode GPT-5.6 request of about 3,300 tokens; this applies only to 1.x with codemode on.
- **Wall-clock interpretation:** opencode spent about 12.6 s more than pi on an identical one-token answer over the same router. Since the model call is shared, that gap is mostly opencode startup, plugins and the larger prompt. Inference, medium confidence because n=1.
  - For multi-minute plans this fixed overhead matters less than router reliability, but it adds up across retries.

## 9. GSD integration facts

- GSD core 1.16.0 already knows pi as a **runtime**. `capability-registry.cjs:3144-3200` has `"pi": {role: runtime, supportTier: 2, sandboxTier: "none", hooksSurface: "none", configHome ~/.pi/agent, env PI_CODING_AGENT_DIR, runtime: "bun", transport: "native-extension"}`. The pi home also appears in the workflow shim's home list.
- pi is **not a `/gsd-review` lane**. Design doc `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:55`: "**pi is not a lane.**"
  - This does not block execution: `workflow.cross_ai_command` is a generic shell hook (`execute-phase.md:414-417`).
- **GSD hook contract** (`execute-phase.md:417`; `gsd-tools.cjs:4871-4990`):
  - The prompt is piped on stdin, never interpolated.
  - `run-with-timeout` inherits stdio and spawns detached so it can tree-kill.
  - Exit 0 plus a non-empty, structurally valid stdout becomes SUMMARY.md. Anything else triggers retry, skip or abort.
  - The stored command is **word-split on whitespace only, with no shell quoting** (`skills/ai-kit-spec-execute-gsd/references/dispatch-notes.md:6-20`). Values with spaces are impossible. pi flags have none, so that is fine.
- ai-kit's execute-builder registry (`skills/ai-kit-spec-review/ai_kit_spec/commands.py:290-299`) has entries for codex, grok, claude, cursor-agent and opencode. **pi has none yet.**
  - pi has no `--cwd` flag (1.2.0 `docs/cli.md:39`: the cwd controls everything). A pi builder should therefore follow the claude pattern: `sh -c 'cd {dir} && exec pi ...'` (`commands.py:205-223`).
  - It should join `NO_HARD_SANDBOX_CLIS = {"cursor-agent", "opencode"}` (`commands.py:276`).
- **Can pi run GSD plan tasks (git commit, make)?**
  - Yes. `bash` is a default tool with no approval gate, and pi's own example agents do exactly this. `~/.pi/agent/agents/sdd-implementer-terra.md` uses `tools: read, bash, edit, write` and says "Run the task verification commands ... and commit".
  - Not live-tested end to end on a real GSD plan here, because the brief allowed no tool runs. **Confidence: medium-high**, from design and docs.
  - Pre-commit hooks run normally because there is no sandbox. The repo's `--no-verify` ban must stay in the prompt.

## 10. Recommended `cross_ai_command`

### Option A: drop-in, no wrapper (router parity with today)

```
pi -p --model router-env/my-coding --thinking off --no-extensions --no-skills --no-approve --offline
```

- `-p`: final assistant text only goes to stdout, and error or aborted exits 1.
- `--model router-env/my-coding --thinking off`: pins away from the `openai-codex/gpt-5.6-terra` + `xhigh` defaults. The router model reports `supportsReasoningEffort: false`.
- `--no-extensions`:
  - Drops `rtk.ts`, which rewrites `make` and test output.
  - Drops the `subagent` tool, which spawns nested pi processes.
  - On 1.x it also turns MCP and codemode off.
- `--no-skills`: keeps the superpowers and personal skills out of an unattended run. The repo `AGENTS.md` still loads.
- `--no-approve`: never loads project `.pi/*`, whatever `trust.json` says.
- `--offline`: no startup network calls (catalog refresh or update check). The router is localhost, so inference is unaffected; verified in run 2.
- Sessions persist to `~/.pi/agent/sessions/` by default, so a manual `pi --session <id>` resume is possible.

### Option B, recommended: direct OAuth model, which bypasses the router failures

```
pi -p --model openai-codex/gpt-5.6-terra:medium --no-extensions --no-skills --no-approve --offline
```

- This uses the user's existing ChatGPT subscription OAuth, the same model as their `sdd-implementer-terra` agent. None of the four Phase 16 router errors apply.
- Cheaper option on the same subscription: `openai-codex/gpt-5.4-mini`. Inference: whether it is good enough for multi-task plans is unverified.
- Caveat: subscription rate limits still apply. pi's retry classifier already refuses to retry `quota exceeded` and `billing` (`retry.js:4-15`).
- Not run live here (the brief allowed one cheap model).

### Option C: wrapper-backed (needed for resume, retry and validation)

Store `workflow.cross_ai_command` as `sh -c 'cd <repo> && exec <tools>/ai-kit-pi-exec <model>'`, or as an ai-kit `dispatch-execute` subcommand, matching the existing SKILL.md Step 2 pattern.

## 11. Wrapper outline (`ai-kit-pi-exec`, replacing `xai_exec.sh` for pi)

```bash
#!/usr/bin/env bash
set -u
MODEL="${1:?model}"; ROOT="$(git rev-parse --show-toplevel)" || exit 2
OUT="${AIKIT_XAI_OUT:-$ROOT/.planning/.xai}/$(date +%Y%m%dT%H%M%S)-$$"; mkdir -p "$OUT"
SID="gsd-xai-$(date +%s)-$$"                 # deterministic, reused for every resume
PI=(pi -p --model "$MODEL" --no-extensions --no-skills --no-approve --offline --session-id "$SID")
cat > "$OUT/prompt.md"                        # GSD pipes the prompt; capture it before anything else
git diff --quiet HEAD || echo "WARN dirty tree" >&2
BASE=$(git rev-parse HEAD)
"${PI[@]}" < "$OUT/prompt.md" > "$OUT/stdout.txt" 2> "$OUT/stderr.log"; EXIT=$?
RESUME='Interrupted by a transient provider error. Inspect git status/diff/log, do not redo finished steps, finish remaining tasks incl. verify + commits, end with the SUMMARY report.'
for i in 1 2 3; do
  [ "$EXIT" -eq 0 ] && break
  grep -qiE 'temporarily unavailable|cooling down|is locked|rate.?limit|overloaded|5[0-9][0-9]|timed? ?out' "$OUT/stderr.log" || break
  sleep $((60 * i))
  "${PI[@]}" "$RESUME" < /dev/null > "$OUT/stdout.txt" 2> "$OUT/stderr.log"; EXIT=$?   # </dev/null is mandatory
done
git log --oneline "$BASE..HEAD" > "$OUT/commits.txt"
[ "$EXIT" -eq 0 ] && [ -s "$OUT/stdout.txt" ] && [ -s "$OUT/commits.txt" ] || { cat "$OUT/stderr.log" >&2; exit "${EXIT/#0/3}"; }
cat "$OUT/stdout.txt"                         # final assistant text only -> GSD SUMMARY
```

- Key properties:
  - stdout carries only the SUMMARY.
  - Diagnostics go to stderr and `$OUT`.
  - Resume is ID-based, and `< /dev/null` sits on every non-initial call.
  - Exit 3 means "pi said OK but made no commits". GSD then offers retry, skip or abort instead of accepting an empty SUMMARY.
- Optional hardening:
  - Pre-flight `curl -s -o /dev/null -w '%{http_code}' 127.0.0.1:20128/v1/models` before a router-env run. 401 means the router is up.
  - Model fallback: router-env, then openai-codex, on a non-retryable router error such as 402 or a credential gate.
  - Set `RTK_DISABLED=1` if extensions are ever re-enabled.
- `shortcut:` the retry regex is a heuristic copied from `xai_exec.sh:53` plus pi's classifier terms. Upgrade by reading `stopReason`/`errorMessage` from the session JSONL instead.

## 12. Risks

### MCP
- Installed 0.82.1 has **no native MCP**. Native MCP needs ≥0.99.0; ≥1.0.4 is the first with `--no-mcp` and tool patterns.
- Upgrading is a user decision. The changelog lists many breaking changes between 0.82.1 and 1.2.0, though none touch `-p`, the session flags or stdin. Examples:
  - 1.0.3 renamed the Azure provider.
  - 0.87.0 and 0.86.0 changed extension and provider APIs.
  - 0.84.0 changed JSON `message_update` to deltas.
- The user's `rtk.ts` and the subagent symlinks should be re-checked after an upgrade. The subagent files are symlinks into the package `examples/`, so they change with the install.
- Default MCP exposure is `codemode`: tools are reachable only through model-written JS. Models unfamiliar with that pattern may not use MCP tools at all unless set to `direct`. Inference.
- MCP OAuth is two weeks old; expect churn. CHANGELOG 1.0.0-1.2.0 has about 15 MCP OAuth fixes.

### Skills
- Global skill discovery is on by default. The superpowers package's mandatory-use skills (brainstorming, using-superpowers) could make a headless run ask questions or brainstorm instead of executing. Print mode would then return a question as the "SUMMARY".
  - Mitigation: `--no-skills`. If a skill is really needed, pass `--skill <path>` explicitly; it works even with `--no-skills`.
- The skills XML is only injected when `read` is enabled, so tool allowlists change skill visibility.

### Tool safety (unrestricted bash)
- No sandbox, no permission gate and no write confinement. This is the same class as the opencode and cursor lanes, already accepted in `NO_HARD_SANDBOX_CLIS` (`commands.py:276`).
- pi's own docs recommend a container or VM for unattended work (`docs/security.md:39-53`), and a Gondolin micro-VM pattern exists (`docs/containerization.md`).
- Mitigations, in order of cost:
  1. Run in a **git worktree** per plan. GSD already has `dispatch-isolation`; see handoff "Isolation guard".
  2. Keep the prompt guard rails (`xai_exec.sh:26`: no push, no branches, no installs, no `git add -A`, no `--no-verify`, no config-dir edits).
  3. A small `tool_call` permission-gate extension via `-e`, the documented pattern ("Permission gates and path protection", README:385). It could block `git push`, `rm -rf /`, and writes outside `$ROOT`, `~/.claude`, `~/.pi` and `~/.config/opencode`. Since MCP calls flow through the same hook in 1.x, one gate covers both.
  4. A container (podman is present: `rootlessport`) with only the worktree mounted. This is the strongest option and the most setup.
- Prompt injection from repo files is "expected local-agent risk" per pi (`docs/security.md:37`).
- Inherited `PI_CODING_AGENT=true` changes runtime detection for child processes. Tests are hermetic (verified), but gsd-tools invoked inside the run may report pi as host. Low impact, inference.

### Model routing
- The router is the documented failure source (16-HANDOFF.md:123-127). Changing the CLI from opencode to pi does not change router availability. Prefer Option B, or add router-to-OAuth fallback in the wrapper.
- User defaults are `openai-codex/gpt-5.6-terra` + `xhigh`. Omitting `--model` or `--thinking` silently burns a premium model at max effort.
- pi's built-in retry (3 tries, about 14 s) is too short for router cool-downs and does not match the router's "cooling down" or "is locked" strings. The wrapper retry is still needed.
- A `length` stop exits 0 on 0.82.1, which can truncate a SUMMARY silently. Fixed in 1.2.0, where it exits 1. On 0.82.1 the wrapper's structural SUMMARY check is the only guard.
- `router-env` models declare `contextWindow` 200k for `my-coding`. pi compacts automatically on overflow (`docs/compaction.md`). Compaction mid-plan could drop task context. Inference, not tested.

## 13. Comparison with other executors

### pi (`pi -p`)
- Startup: `--version` 0.35 s and `--help` 0.47 s. **Full one-token prompt 3.9-5.3 s** wall at 179-188 MB RSS. Measured.
- Prompt overhead: about 0.5k own tokens, plus `AGENTS.md`, plus the router's 11.8k. Measured: 12.3k-16.9k total.
- Permissions: none exist, so no flag is needed. No sandbox. Read-only is possible via `--tools read,grep,find,ls`.
- stdin: yes, merged into the prompt. **Blocks without EOF.**
- Output: final text only. JSON events and RPC are also available.
- Resume: `--session-id` (create or open by exact ID), which is ideal for retries.
- MCP: none in 0.82.1; native from 0.99.0.

### opencode (`opencode run`)
- Startup: `--version` 0.27 s. **Full one-token prompt 16.5 s** at 668 MB RSS on the same router model. Measured.
- Prompt overhead: about 32.6k uncached input tokens for the same prompt. Measured.
- Permissions: `--auto` auto-approves. There is no write confinement; `--dir` only sets the cwd (`commands.py:243-268`).
- stdin: yes. Output needed ANSI stripping and heading extraction (`xai_exec.sh:64-67`).
- Resume: `-s <session>`, but the ID had to be scraped from `opencode session list` (`xai_exec.sh:50`).
- MCP: native.

### cursor-agent (`cursor-agent -p`)
- Startup: `--version` 0.25 s. Prompt cold start not measured.
- Permissions: `--force/--yolo` allows commands. `--trust` is required for a fresh workspace. `--sandbox enabled` does **not** confine writes, as confirmed live in `commands.py:224-242`. Builder: `cursor-agent --sandbox enabled --workspace <dir> -p --output-format text --model <m> --trust --force`.
- stdin: yes with `-p`. Output: `text`, `json`, `stream-json`. Resume: `--resume [chatId]`.
- Source: `cursor-agent --help` grep.

### codex (`codex exec`)
- Startup: `--version` returns in about 0 s (native binary). Prompt cold start not measured.
- Permissions: `--sandbox workspace-write -C <dir>` is **real OS write confinement**, but it always allows writes to `/tmp` and `$TMPDIR` (`commands.py:151-176`). `--dangerously-bypass-approvals-and-sandbox` exists.
  - Unverified: whether `git commit` works inside workspace-write in this version.
- stdin: yes when no prompt arg is given, or appended as a `<stdin>` block.
- Output: `-o/--output-last-message <FILE>`, `--json`, `--output-schema`. Resume: `codex exec resume`. `--ephemeral` is available.
- Model range: OpenAI only.

### claude (`claude -p`)
- Startup: `--version` returns in about 0 s. Prompt cold start not measured.
- Permissions: ai-kit's builder uses `--restricted --permission-mode acceptEdits`, which confines writes but **strips Bash** (`commands.py:205-223`). That builder therefore cannot run make or git commit for GSD plans. `--dangerously-skip-permissions` restores bash with no confinement.
- Output: `--output-format text|json|stream-json`. Resume: `--resume <id>`.
- Model range: Claude only.

### Net assessment
- On startup cost, prompt overhead, clean SUMMARY capture and retry ergonomics, pi beats opencode.
- On safety, pi ties opencode and cursor (none) and is behind codex (real write sandbox).
- pi is the most model-flexible headless option the user has: router, ChatGPT OAuth and Claude OAuth in one CLI.
- **Confidence: medium-high.** The timing comparison is n=1, and the other CLIs' prompt-level cold start was not measured.

## 14. Verified versus inferred

- **Verified** (command output or source):
  - Package, owner and version facts.
  - Print-mode stdout and exit-code behaviour.
  - The stdin block-until-EOF hang, reproduced.
  - Session-id flags and the session JSONL usage record.
  - The MCP timeline (0.82.1 none; 0.99.0 native).
  - Retry classifier patterns.
  - gsd-core's pi runtime registry entry.
  - "pi is not a lane".
  - Test hermeticity with `PI_CODING_AGENT`.
  - All timings listed in section 8.
- **Inferred:**
  - The router injecting about 11.7k tokens.
  - The opencode overhead attribution.
  - Superpowers skills derailing headless runs.
  - The router error strings not matching pi's retry regex.
  - MCP `codemode` exposure being underused by models.
  - Compaction risk.
  - Option B reliability, since it was not run.
- **Not tested:**
  - A real end-to-end GSD plan through pi (edits, make, commit).
  - The pi 1.x upgrade path.
  - Prompt cold start for cursor-agent, codex and claude.
