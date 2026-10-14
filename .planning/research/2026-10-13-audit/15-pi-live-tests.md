# 15 - pi 1.2.0 live tests as a cross-AI executor

Date: 2026-10-13. Binary: `~/.bun/bin/pi` → `~/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js`, version **1.2.0**.

Scope and rules:
- Every run happened in a fresh throwaway git repo under scratchpad `pi-live/repos/<run>/`. Each repo is built by `pi-live/bin/mkrepo.sh`; the harness is `pi-live/bin/run.sh`.
- Every run used `timeout 240`, except the hang test (20 s) and the bad-model runs (60 s).
- Sessions went to `--session-dir pi-live/sessions/`. The cross-ai.mjs run used `PI_CODING_AGENT_SESSION_DIR=pi-live/sessions-crossai`.
- Nothing under `~/.pi`, `~/.config/opencode` or `~/.claude` changed.
  - Only the mtime of the `~/.pi/agent` directory moved, because pi takes a transient lock file on every run.
  - `auth.json`, `settings.json`, `models.json` and `models-store.json` all kept their pre-test mtimes (11:57 or earlier).
  - Sessions under `~/.pi/agent/sessions/--…-scratchpad-stall-probe-pi--` (13:11-13:12) are **not** from these tests; another agent wrote them.
- The opencode key was passed in the env of the pi process only. It was never printed or written anywhere.
- Logs: `pi-live/logs/<run>.{meta,stdout,stderr}`. `.meta` holds the argv, exit code, wall time, commits made, `git status` and the diff stat.

There were 12 pi invocations. 9 of them reached a model; the other 3 hung or failed before any inference. Total spend:
- router: $0;
- opencode-go: about $0.0017 at its notional price;
- one openai-codex probe, billed to the subscription.

## TL;DR

1. **pi 1.2.0 works as an unattended GSD executor.** Read, edit, verify and `git commit` all passed on `router-env/my-coding` and on `opencode-go/glm-5.3-flash`, with exit 0 each time.
   - stdout carried only the final SUMMARY markdown.
   - Nothing waited for approval.
   - Every model staged only `calc.py`, leaving the untracked `__pycache__/` alone.
2. **The opencode key carries over with zero config.** Setting `OPENCODE_API_KEY` from `~/.local/share/opencode/auth.json` in the process env does two things:
   - it adds 83 `opencode/*` and 31 `opencode-go/*` models to `pi --list-models`;
   - the Go model ran both tests.
3. **opencode's free Zen models cannot be used from pi.** `opencode/big-pickle` failed in 0.99 s with exit 1 and `403 FreeTierError: "OpenCode's free tier can only be used from within OpenCode"`.
   - This voids report 11's plan to add `cat-jam-free` and every other `*-free` model.
4. **The stdin hang is confirmed on 1.2.0.** With the prompt passed as an **argument** and stdin left open, pi produced no output and no session file, and `timeout 20` killed it with exit 124.
5. **Skills on is expensive.** The cross-ai.mjs pi block (skills and extensions on) did complete the edit plan end to end, with exit 0 and a commit.
   - But the model first read 3 skill files: superpowers `executing-plans`, `test-driven-development` and `commit-work`.
   - It took 11 turns, **278k tokens and 54.8 s**. The stripped formula did the same plan in 5 tool calls, 16.9k tokens and 16.6 s.
   - **Add `--no-extensions --no-skills` to the cross-ai.mjs pi block.**
6. **openai-codex is not quota-blocked in pi.** The one probe (`openai-codex/gpt-5.6-luna`, read test) answered correctly: exit 0, 7.3 s, 2.6k tokens. pi's own ChatGPT OAuth is valid until 2026-10-23.
7. **anthropic was skipped.** pi's anthropic OAuth access token expired on 2026-07-26. Any run would refresh it and rewrite `~/.pi/agent/auth.json`, which the rules forbid.
   - `pi auth check --no-refresh` still reports it `ready`, because that check does not look at expiry.
8. **The inventory finds no skill-collision warnings.** pi dedupes symlinked skills by realpath, silently. The 6 dangling volta symlinks remain; with extensions on, the subagent extension fails to load without any message in print mode.

## 1. Flags (pi --help, 1.2.0): `logs/help.txt`

These flags all exist and behave as documented:
- `-p/--print`
- `--mode text|json|rpc`
- `--session-id <id>`, described as "exact project session ID, creating it if missing"
- `--session-dir`, `--no-session`
- `--thinking off|minimal|low|medium|high|xhigh|max`, and the `--model provider/id[:thinking]` suffix
- `--no-extensions/-ne`: "Disable extension discovery and built-in extensions (explicit -e paths still work)"
- `--no-mcp`: "no servers connect and no MCP tools"
- `--no-skills/-ns`, `--no-context-files/-nc`, `--no-prompt-templates/-np`
- `--tools/-t`, `--exclude-tools/-xt`, `--no-tools/-nt`, `--no-builtin-tools/-nbt`
- `--approve/-a`, `--no-approve/-na`
- `--offline`, the same as `PI_OFFLINE=1`

There are **no approval or sandbox flags**, and none are needed.

`ask_question` appears only as an example in the help text (`--exclude-tools ask_question`). It is not among the default tools; this run's `toolsAdded` lists only read, bash, edit and write.

New subcommands:
- `pi auth check --provider X [--no-refresh] [--json]` is a no-inference readiness probe.
  - It exits 0 with `{"status":"ready"}`, or exits 1 with `credentials_not_configured`.
  - Logs: `logs/auth-help.txt`.
- `pi mcp …`
- `pi update [self|pi]`

Report 06's Option A works unchanged on 1.2.0 (t2a, t3a):
`pi -p --model router-env/my-coding --thinking off --no-extensions --no-skills --no-approve --offline`.

Every fresh `--session-id` writes one stderr line: `Warning: No project session found with id '<id>'; creating a new session with that id.` It is harmless, but it lands in GSD's error log.

## 2-4. Read and edit tests

The base argv for every row below is:
`pi -p --model <M> [--thinking off|low] --no-extensions --no-skills --no-approve --offline --session-dir … --session-id <id>`.
The prompt was piped on stdin (`prompts/read.md`, `prompts/edit.md`).

### t2a: read, router-env/my-coding
- Exit 0, 23.7 s.
- stdout was exactly `heron-42\n3\n`, which is correct.
- 1 tool call (read), 3.8k tokens, $0.
- Log: `logs/t2a-read-router.*`

### t3a: edit, router-env/my-coding
- Exit 0, 16.6 s. Commit `5da1f48 feat(01-01): add mul helper`.
- Tool calls: read, edit, then bash three times (verify, `git status --short`, then `git add calc.py && git commit`). 16.9k tokens.
- stdout was a clean 12-line SUMMARY.
- Log: `logs/t3a-edit-router.*`

### t2b: read, opencode/big-pickle (free Zen)
- **Exit 1 after 0.99 s**, with `403: {"type":"FreeTierError",...}` on stderr.
- Log: `logs/t2b-read-opencode.*`

### t2b2: read, opencode-go/glm-5.3-flash
- Exit 0, 5.7 s. stdout was correct.
- 3.2k tokens, $0.0005.
- Log: `logs/t2b2-read-opencode-go.*`

### t3b: edit, opencode-go/glm-5.3-flash
- Exit 0, 23.3 s. Commit `ffec6c1 feat(01-01): add mul helper`.
- 10.0k tokens, $0.0012. stdout was a clean 14-line SUMMARY.
- Log: `logs/t3b-edit-opencode-go.*`

### anthropic haiku: skipped
- The OAuth token expired on 2026-07-26. A run would refresh it and write `~/.pi/agent/auth.json`.

### t4d: read, openai-codex/gpt-5.6-luna (the single probe)
- Exit 0, 7.3 s. stdout was correct.
- 2.6k tokens. No quota error occurred, so there is no error text to record.
- Log: `logs/t4d-read-codex.*`

### t7: resume, router (`--session-id gsd-live-t2a-read`, prompt as an argument, `< /dev/null`)
- Exit 0, 9.4 s.
- It answered `heron-42` from the history, and its turns were appended to the **same** session file.
- This confirms that cross-ai.mjs's "same `--session-id` continues" resume works.
- Log: `logs/t7-resume.*`

The carried-key invocation (b) needs no config:
```
OPENCODE_API_KEY="$(jq -r '.opencode.key // empty' ~/.local/share/opencode/auth.json)" pi -p --model opencode-go/glm-5.3-flash ...
```
- `pi auth check --provider opencode` without the env returns `not_ready`/`credentials_not_configured`.
- With the env set, `--list-models` shows 83 + 31 models (`logs/list-models-with-opencode-key.txt`).

## 5. Edge cases

### t5a: stdin left open (`sleep 23 | pi -p … "<prompt as argv>"`, `timeout 20`)
- **Exit 124**, 0 bytes on stdout, and no session file was created.
- The hang is real, and it happens even when the prompt is passed as an argument.
- Note: the Claude Code harness's own stdin is `/dev/null`, so in this harness the hang only shows when stdin is a real open pipe.

### t5b: unknown model on a known provider (`router-env/does-not-exist`)
- Exit 1, 0.22 s.
- stderr: `Warning: Model "does-not-exist" not found for provider "router-env". Using custom model id.`, then the router's `400 … "Unable to determine provider for model" … invalid_request_error`.
- So **pi forwards unknown ids to the provider** rather than failing locally.

### t5b2: unknown provider (`nosuchprovider/foo`)
- Exit 1, 0.14 s, with no network call.
- stderr: `Error: Model "nosuchprovider/foo" not found. Use --list-models to see available models.`

### t5c: `--no-mcp` only (extensions and skills on, `--verbose`)
- Exit 0, 24.1 s, correct output.
- **Nothing on stderr except the session warning.** Print mode suppresses resource diagnostics: collisions are reported only in `interactive-mode.js`.
- The system prompt carried 57 skills (25 KB; first-turn input 11.9k tokens against 1.7k stripped).
- `toolsAdded` stayed read, bash, edit and write, the same as with `-ne`. So:
  - the dangling subagent extension registered nothing, silently;
  - codemode and tool-search are not default tools.
- No `~/.pi/agent/mcp.json` exists, so `--no-mcp` is a no-op today. `-ne` already disables the built-in MCP.

### cross-ai.mjs classifier on the captured strings
- The FreeTier 403 classifies as `fatal`, which is correct.
- Both bad-model strings classify as `other`. That is acceptable: runCli does not retry `other` either, and the repo is untouched, so it falls through to the next CLI.

## 6. cross-ai.mjs pi block, live (t6)

Command:
```
node research/cross-ai.mjs --prefer pi --model-pi router-env/my-coding --timeout 220 < prompts/edit.md
```
It ran in `repos/t6-crossai`. Its `--print-argv` and `--self-test` both pass (header pristine).

Result:
- **It works end to end.** Exit 0, 54.8 s, commit `ce9e361 feat(01-01): add mul helper`.
- stdout was a clean SUMMARY, and the heartbeat appeared at 30 s.
- argv: `-p --model router-env/my-coding --session-id <uuid> --no-approve --offline`.

Cost of leaving skills and extensions on:
- 11 turns and **278,464 tokens**, against 16.9k for t3a.
- The model `read` three files before acting: `superpowers/skills/executing-plans/SKILL.md`, `superpowers/skills/test-driven-development/SKILL.md` and `~/.pi/agent/skills/commit-work/SKILL.md`.
- It did not derail into questions, but it was 16x the tokens and 3.3x the wall time.

Thinking level:
- Without `--thinking`, the session recorded `thinking_level_change: off`. pi clamps the `xhigh` default to off for a model whose `reasoning` is false.
- On codex, Zen or Go models, the `xhigh` default **would** apply.

Log: `logs/t6-crossai.*`; session in `sessions-crossai/`.

## 7. Read-only inventory: `logs/inventory.txt`

### 6 dangling symlinks into the deleted volta 0.82.1 `examples/`
- `~/.pi/agent/extensions/subagent/{index,agents}.ts`
- `~/.pi/agent/agents/{planner,reviewer,scout,worker}.md`
- The new bun install has the same examples at `~/.bun/install/global/node_modules/@earendil-works/pi-coding-agent/examples/extensions/subagent/`; repointing the symlinks there is the user's or tools-installer's call.
- With extensions on, the subagent tool silently does not exist.

### No name-collision warnings
- All 33 `~/.pi/agent/skills/*` entries resolve to the same realpath as `~/.agents/skills/*`.
- pi skips a skill whose realpath it has already loaded, "silently" (`dist/core/skills.js:328-333`).
- The 42 `~/.agents/skills` names and the 15 superpowers names do not overlap: 57 loaded, 0 collisions.
- Deleting `~/.pi/agent/skills` is cosmetic.

### Providers
- Without the env, the providers are anthropic (17 models), openai-codex (9) and router-env (3).
- With `OPENCODE_API_KEY`, pi adds `opencode` (83) and `opencode-go` (31).
- `xai` stays `credentials_not_configured`. opencode holds xai only as OAuth, so there is no key to carry, and the login is left to the user.

## Recommended pi block for cross-ai.mjs

```js
pi: {
  bins: ['pi'],
  //   -ne -ns: measured 278k -> 17k tokens and 55 s -> 17 s on the same plan (t6 vs t3a); -ne also drops builtin MCP,
  //   the rtk bash rewriter and the (currently dangling) subagent extension. AGENTS.md still loads.
  exec:   (m, c) => ['-p', '--model', m, '--session-id', c.sid, '--no-extensions', '--no-skills', '--no-approve', '--offline'],
  review: (m, c) => ['-p', '--model', m, '--session-id', c.sid, '--no-extensions', '--no-skills', '--no-approve', '--offline',
    '--tools', 'read,grep,find,ls'],
  resume: (m, c, sid, mode) => RUNTIMES.pi[mode](m, c), // verified t7: same --session-id appends to the session
  parse: (out) => ({ text: out, sessionId: null, error: null }),
  env: {},
},
```

### Model strings must pin thinking
- Use a suffix such as `opencode-go/glm-5.3-flash:low` or `openai-codex/gpt-5.6-terra:medium`. Otherwise the `xhigh` default applies to reasoning models.
- `router-env/*` needs no suffix, because pi clamps it to off.
- The suffix form itself was not run live in this session; the `--thinking` flag was.

### Carrying the opencode key without a config write
In `runCli`, when `name === 'pi'` and the model starts with `opencode/` or `opencode-go/`, and `OPENCODE_API_KEY` is unset, read `~/.local/share/opencode/auth.json` `.opencode.key` into the child env only. That is about 3 lines; tested by hand in t2b2 and t3b, but not wired into the script yet.

### Model choice
- Do not configure any `opencode/*-free` or `big-pickle` model for pi: they are blocked with a 403.
- Optional FATAL additions (cosmetic, since `other` already stops retries): `FreeTierError`, `Unable to determine provider`, `not found\. Use --list-models`.

## Corrections to earlier reports

### Report 06
- **Install.** The Volta 0.82.1 install is gone. pi is now bun-global 1.2.0. `--no-mcp` and `-ne`-disables-builtins are both confirmed in the 1.2.0 help.
- **Option A** works verbatim on 1.2.0. `--thinking off` is redundant for router-env (pi clamps it) but harmless.
- **§8 "11,776 cached tokens in every router-env call"** was not reproduced. Today's router calls showed `cacheRead 0` and input 1.66k with `-ns -ne`. The "router injects ~11.7k tokens" inference does not hold now.
- **§9 / §14 "end-to-end GSD plan not tested"** is now tested: edit, verify, `git status` and commit passed on router, opencode-go and through cross-ai.mjs.
- **§2 hang:** add that the hang also occurs when the prompt is given as an argument. Only stdin EOF matters.
- **§10 Option B:** the openai-codex lane in pi answered (exit 0). It was not quota-blocked on this day.
- **§12 skills risk:** partly confirmed. With skills on, the model spends turns reading superpowers skills (16x tokens), but it did not ask questions.

### Report 10
- **§3.4** "pi not installed; NOT live-tested" is outdated: 1.2.0 is live-tested here.
- Change "the prototype leaves them on" to: **strip with `--no-extensions --no-skills`**. The measured cost is above.
- **`opencode/big-pickle` and `opencode/*-free`** work only inside opencode. From pi they fail with `403 FreeTierError`. Note this in §3.2 and in any pi model scoring.
- **pi error strings** were captured (FreeTier 403, unknown model, unknown provider; §5 above). The "pi error strings not captured" gap in §6 is closed for these cases. Router transient errors through pi are still uncaptured.

### Report 11
- **TL;DR 5 and step 1 ("33 collision warnings") are wrong.** pi dedupes by realpath silently and the names do not overlap, so there are zero warnings. Deleting `~/.pi/agent/skills` is cosmetic only.
- **The `opencode/cat-jam-free` addition is pointless.** The free tier is refused outside opencode. The sync should skip `*-free` and `big-pickle`, so the effective Zen model gap is 0.
- **TL;DR 4 "pi install is broken"** is now outdated: pi 1.2.0 is on PATH. The 6 dangling symlinks remain.
- **Credentials:** a per-process env injection of `OPENCODE_API_KEY` works (t2b2, t3b) and needs no `models.json` write. It is a lighter alternative to the `!jq` apiKey entry.
- **New:** `pi auth check --provider X --no-refresh --json` is a cheap preflight. Caveat: it reports an expired OAuth token as `ready`.
- **New:** pi's anthropic OAuth expired on 2026-07-26. It needs a re-login before any anthropic lane.

## Not tested
- The anthropic lane: skipped, because a run would write `auth.json`.
- An xai login: left to the user.
- An opencode Zen **paid** model through pi. Only Go was run; Zen paid usage appears in opencode's history.
- The `:thinking` suffix form, live.
- Router transient-error strings through pi.
- `--mode json` exit behaviour.
