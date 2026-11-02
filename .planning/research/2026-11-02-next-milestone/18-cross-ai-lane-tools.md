# Cross-AI lanes: what tools and skills each lane really has

Read-only research, 2026-11-02. Sources are file:line in this checkout, `--help` output of the
installed CLIs (saved in `18-help/`), the runner's own `--print-argv` dry run
(`18-print-argv.sh` / `.out`), and a scan of local Claude transcripts (`18_pi_argv_scan.py` /
`.out`). Marks: **[verified]** = seen in code, help text or a dry run on this machine;
**[inferred]** = reasoned, not run; **[unverified]** = vendor behavior not checked here.

Installed versions: pi 1.3.0, opencode 2.0.31, cursor-agent 2026.10.22, codex-cli 0.162.1,
Claude Code 2.1.316, Copilot CLI 1.0.105.

## 1. How the runner launches each runtime

Template: `skills/ai-kit-spec-review/references/cross-ai.mjs` (template 8). The rendered copy
`.planning/scripts/cross-ai.mjs` differs only in the CONFIG block (models, router flags, some
leftover keys); the runtime table is the same, shifted by 19 lines (template `RUNTIMES` at 1330,
rendered at 1349).

How the flags are put together (template lines):
- `--mode exec|review` picks the formula; `--tools-profile exec|review|none` picks a named
  tool set from the row's `profiles`; with no `--tools-profile` the mode is the profile
  (`main`, 10187-10201). Only pi and copilot have profiles; every other runtime refuses
  `--tools-profile` unless it equals the mode.
- Review mode refuses a `CONFIG.extraArgs` entry outside the row's `reviewExtras` allowlist
  (`reviewArgvProblem`, 3654). Only pi allows one: `--skill <path>` (1385).
- The prompt goes on stdin (copilot: argv). Unless `--no-preamble`, the runner appends
  `EXEC_PREAMBLE` (115) or `REVIEW_PREAMBLE` (124). `--prepend-file` puts a file before the prompt
  (10243-10252).
- The Python callers (`ai_kit_spec/runner_dispatch.py` `runner_flags` 202, `build_runner_argv`
  255) never pass `--tools-profile`, so every ai-kit dispatch uses the mode's default profile.
  **[verified]**

Resolved argv (from `--print-argv`, model ids are examples) **[verified]**:

pi (1367-1386)
- exec: `-p --model M --session-id SID --no-skills --no-extensions --no-approve --offline`
  - Tools: pi's default set, which is `read, bash, edit, write` (pi `--help`: grep, find and ls
    are "off by default").
  - Skills: none discovered. Extensions: none (this also drops ai-kit's own pi
    `ai-kit-tool-advisor.ts` and `ai-kit-tool-reminder.ts` and the `subagent` extension).
  - AGENTS.md/CLAUDE.md: loaded (no `--no-context-files` in exec). MCP: pi has no MCP servers
    configured on this machine (`pi mcp list`).
- review: the same plus `--tools read,grep,find,ls --no-mcp --no-context-files` (1382).
  - No bash, so no shell tool of any kind (rg, fd, bat, codegraph CLI, rtk) is reachable.
  - pi's own `grep` and `find` tools run its bundled rg and fd (`~/.pi/agent/bin/{rg,fd}`;
    pi `dist/core/tools/grep.js:52`, `find.js:119`).
  - No AGENTS.md, so the lane does not see the repo's rules or tool notes.
- `--tools-profile none`: `--no-tools --no-mcp --no-context-files` (1383). No tool at all, not
  even `read`. Nothing in ai-kit's code selects it; only a manual caller can.
- Effort: `--thinking` only when `CONFIG.effort.pi` is set (`piThinkingArgs`, 1460); the
  rendered copy sets none, so pi runs the user's default (`defaultThinkingLevel: xhigh` in pi's
  settings).

opencode (1354-1366)
- exec: `run --model M --auto --format json --standalone`. review: `run --model M --agent plan
  --format json --standalone`.
- Env: `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` (1365) stops `~/.claude/skills` loading; opencode
  still loads `~/.agents/skills` and `~/.config/opencode/skills` (runner comment 1349-1353, Phase
  18 spec amendment). On this machine `~/.agents/skills` holds 12 skills (skill-judge,
  reducing-entropy, writing-clearly-and-concisely, ...).
- opencode `run --help` has no tool or skill flag; the tool set comes from the agent (`plan`
  in review). What the 2.x `plan` agent allows for bash, and whether "ask" permissions are
  auto-denied in `run` without `--auto`, is **[unverified]**.
- MCP: none configured (`opencode mcp list`: "No MCP servers configured"), so no codegraph MCP.

cursor (1331-1348)
- exec: `-p --output-format json --model M --trust --force --sandbox disabled --approve-mcps
  --workspace CWD`. review: `-p ... --mode ask --trust --workspace CWD` (or `--mode plan` via
  `--cursor-mode`).
- `--help`: `-p` "has access to all tools, including write and shell"; `ask` and `plan` are
  described as read-only. No flag to turn skills or rules off. Cursor loads its own skills
  (`~/.cursor/skills-cursor`: review, review-security, shell, ...) and rules **[unverified which
  load headless]**. codegraph MCP: `ready` (`cursor-agent mcp list`); in review there is no
  `--approve-mcps`, so whether MCP tools run in review is **[unverified]**.

codex (1389-1414, `codexExecArgv` 1473)
- exec: `exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C CWD -m M --json
  -o OUT -` (ai-kit's Python callers add `--codex-sandbox workspace-write`, so they get
  `--sandbox workspace-write`). review: `exec --sandbox read-only ...`.
- Tools: shell plus patch edits under the sandbox policy. Skills: none in `~/.codex/skills`.
  `--ignore-user-config`, `--ignore-rules`, `--disable <feature>` exist but are not passed.
  codegraph MCP: listed `enabled` (`codex mcp list`).

claude (1415-1434), review only
- `-p --model M --output-format json --permission-mode plan`.
- Loads everything the user has: CLAUDE.md, all skills and plugins (ponytail, superpowers, GSD
  project skills), hooks (ai-kit's tool advisor and reminder), and MCP (codegraph `Connected`).
  The richest lane. Flags that would strip it exist (`--bare`, `--disable-slash-commands`,
  `--tools`, `--strict-mcp-config`, `--append-system-prompt`) but are not passed. Read-only
  enforcement of plan mode is marked not live-verified in the runner (1414).

copilot (1436-1455), all shapes **[unverified]** by a real run
- exec: `-p PROMPT -s --no-ask-user --model M --allow-all-tools`.
- review: adds `--available-tools=view,grep,glob --excluded-tools=bash,create,edit,apply_patch
  --deny-tool=shell --deny-tool=write --disable-builtin-mcps` (1450). No shell in review.
- The runner clears `COPILOT_ALLOW_ALL` (1447). `--no-custom-instructions` exists (drops
  AGENTS.md) but is not passed.

Environment of every child (`childEnv`, 3638-3644): the parent env, minus the host-signal names in
`CONFIG.scrubEnv` (`CLAUDECODE`, `OPENCODE`, `PI_CODING_AGENT`, ...), plus the row's `env`, plus
`AI_KIT_CROSS_AI_CHILD=1`. **PATH and HOME pass through unchanged** **[verified]**, so whatever is
on the caller's PATH is on the lane's PATH. Whether the lane can *use* it depends only on whether
its tool profile has a shell.

## 2. Where "pi without skills" came from, and why

- 2026-10-13 audit, `.planning/research/2026-10-13-audit/06-pi-cross-ai-executor.md:200-215`:
  the pi executor formula `-p ... --no-extensions --no-skills --no-approve --offline`. Reasons
  given: keep superpowers and personal skills out of an unattended run; drop the `rtk.ts`
  extension (it rewrote `make` and test output) and the `subagent` extension (nested pi
  processes); `--offline` for no startup network calls. The repo AGENTS.md still loads.
- Measured cost, `15-pi-live-tests.md:30-36`: with skills and extensions on, the same plan took
  11 turns, 278k tokens and 54.8 s (the model first read three superpowers skills); stripped, 5
  tool calls, 16.9k tokens, 16.6 s. Conclusion: "Add `--no-extensions --no-skills` to the
  cross-ai.mjs pi block."
- Owner rule (memory `project_cross_ai_runtimes_full_permission.md`, 2026-10-13): "start from a
  bare agent (no skills or MCP, to save tokens). Opt into specific skills or MCP only when the
  plan needs them."
- Phase 18 decision (`v1.3-phases/18-.../18-CONTEXT.md:52-53`): bare tool profile by default;
  "specific skills by SKILL.md path or MCP servers are opt-in".
- Phase 25.1 decision (`25.1-CONTEXT.md:169-177`): named profiles; pi review =
  `--tools read,grep,find,ls --no-mcp --no-context-files`, none = `--no-tools --no-mcp
  --no-context-files`; no raw passthrough so a caller cannot widen review's read-only set.

So the reasons were **token cost and determinism**, for **both exec and review** (`--no-skills
--no-extensions` sit in both formulas). **Read-only safety** is the separate reason for the
review tool allowlist (no bash), review only. Removing AGENTS.md in review
(`--no-context-files`) came with the 25.1 profiles; the record gives no reason beyond the
profile design.

Where "no tools and no skills" was seen (transcript scan, `18_pi_argv_scan.out`):
- 33 + 13 direct `pi -p ... --no-skills --no-extensions [--no-session]` calls (probes, the
  2026-10-15 judge lanes run straight through pi, the Phase 27 "PONG" probe in
  `27-12-PLAN.md:78`).
- A handful of direct `pi ... --no-tools` probes on 2026-10-13/14.
- The skill-judge lanes (`27-12-PLAN.md`) embed every file and tell the model "nothing else may
  be read", which is "no tools" by prompt even though the review profile has read/grep/find/ls.
- The scan counts every mention of the runner in a command, not only launches, so its "runner"
  numbers are an upper bound.

## 3. The shell tools this repo knows

Sources: `.claude/cli-environment.md`, `~/.agents/AGENTS-TOOLING.md`,
`skills/ai-kit-spec-review/references/tooling-guidance.md`, `tools/hooks/README.md` (the session
briefing's flag hints). Presence on this machine from `18-probe-tools.sh` (all under
`~/.local/bin` unless noted).

- **rtk 0.44.1**: output-filtering proxy (`rtk git`, `rtk grep`, `rtk test`, `rtk err`, ...).
  Check: `command -v rtk`. Caveats: `cli-environment.md` says a Claude Code hook rewrites
  commands through it, but **no rtk hook is wired now** in `~/.claude/settings.json`, pi's
  extensions or opencode's plugins (only ai-kit's own advisor hooks); `.claude/settings.local.json`
  only allow-lists `rtk git *` and `rtk grep *`. That doc line is stale. A lane would have to
  call `rtk <cmd>` explicitly; its output is summarized, which can hide the detail a test or
  review needs.
- **rg 15.2.0**: content search. Check `command -v rg`. Respects `.gitignore` (misses ignored
  files such as `tmp/` unless `-uu`). Hint: `rg -n`, `rg -l`, `--glob`.
- **fd 10.5.0**: file search. Check `command -v fd` (Debian names it `fdfind`; not present here).
  Syntax differs from `find`: pattern is a regex by default, `--glob` for globs, `-t f`, skips
  ignored and hidden files.
- **bat 0.26.1**: file viewer. Check `command -v bat` (Debian: `batcat`). Always
  `--plain --paging=never` in an agent, `-r N:M` for a slice; without them it pages or adds
  decoration.
- **sd 1.0.0**: find/replace. Check `command -v sd`. Not sed: `sd 'from' 'to' file` edits in
  place by default, regex is Rust syntax, `-F` for literal, `-p` to preview. Write tool, so
  never for a review lane.
- **eza**: listing. Check `command -v eza`. `--long --git` for status. Low value to an agent.
- **delta 0.19.2, difft 0.69.0**: diff viewers. Interactive pagers by default; low value
  headless.
- **codegraph 1.6.2**: code graph. CLI `codegraph explore "<names or question>"` works from any
  shell; it needs a `.codegraph/` index at or above the cwd (present in this checkout; a fresh
  git worktree has none until `codegraph init`/`sync`). MCP `codegraph_explore` is registered
  only for claude (connected), cursor (ready) and codex (enabled); not for pi or opencode.
- **graphify 0.9.54**: knowledge-graph indexing; needs `graphify-out/`. Not a per-lane tool.
- Also present: jq, uv, pnpm, node v24, git.

What a lane can actually use (PATH is inherited, so presence is the same as the caller's;
use needs a shell):
- pi exec, opencode exec, cursor exec, codex exec/review, copilot exec: have a shell, so all of
  the above are callable. Under codex `--sandbox read-only` the tools run but cannot write.
- pi review, copilot review: no shell; only the CLI's own read/search tools. pi's grep/find are
  already rg/fd underneath.
- opencode review (`plan` agent), cursor `ask`/`plan`, claude `plan`: shell access is the
  vendor's read-only policy **[unverified per vendor]**.

## 4. Existing tool-guidance blocks

- `ai_kit_spec/tooling_guidance.py` `build_tooling_guidance` (30-64) builds:
  `SHARED_TOOLING_PATH = <.../tooling-guidance.md>`, `AGENTS_TOOLING_PATH = <~/.agents/...>`, a
  `TOOL_AVAILABILITY = {"bat":true,...}` JSON line from `detect_tool_availability`
  (`detection.py:1127`, `shutil.which` for rg, sd, bat, eza, fd, codegraph in the caller), and a
  codegraph_explore line only when that CLI's MCP probe is healthy.
- Users: ai-kit-spec-review's reviewer dispatch (`reviewer_dispatch.py:46-59`, prefixed onto
  every review prompt), `dispatch-execute` (`execute_dispatch.py:70-95`, plus the soft
  "write only inside <dir>" sentence), the superpowers adapter, and the GSD adapter's
  `prepare-tooling` / `print-dispatch-guidance` (`ai_kit_spec_gsd/cli.py:324, 412`).
- The GSD hook form with guidance is `node .planning/scripts/cross-ai.mjs ... --no-preamble
  --prepend-file .planning/scripts/cross-ai-guidance.md` (`runner_dispatch.py:185-199`); the file
  is written by ai-kit-gsd-curated-config `ensure-runner --guidance-file`
  (`cross_ai_script.py:306-318`).
- **This repo does not use it**: `.planning/config.json:46` is plain
  `node .planning/scripts/cross-ai.mjs` and no `cross-ai-guidance.md` exists. GSD exec lanes here
  get the GSD task prompt plus `EXEC_PREAMBLE` only, no tool hints.

Problems with the current block (the "hammer that does not exist" case) **[verified from code]**:
- Presence is checked in the caller and never matched to the lane's tool profile. A pi review
  lane (no bash) is told about rg/fd/bat/sd/eza it cannot run, and `tooling-guidance.md` lists
  `sd` for "in-place edits" to a read-only reviewer.
- The hints are names, not usage: nothing says `bat --plain --paging=never` or that `fd` takes a
  regex; the useful flag hints exist only in the Claude session briefing (`tools/hooks/README.md`).
- It sends two "Read <path>" lines pointing outside the project (the shared reference, and
  `~/.agents/AGENTS-TOOLING.md`); a pi review lane can read absolute paths, but a judge prompt
  that says "nothing else may be read" contradicts them.
- codegraph CLI is never suggested to a lane with a shell and an index; only the MCP line exists,
  and pi/opencode have no MCP.

## 5. Proposal (not decided): a per-lane capability block

Build one short block at dispatch time, inside the runner (which is the only place that knows
the final argv), and prepend it to the prompt. Keep it stdlib-only and fail-closed: a fact not
verified is left out, never guessed.

What goes in, per lane:
1. **Write access**, from the mode: "read-only review: do not edit or commit" or "exec: write only
   inside the project".
2. **Shell or not**, from the final argv per runtime (a small table next to each `RUNTIMES` row,
   e.g. `shell: {exec: true, review: false}` for pi and copilot; `'vendor'` for opencode, cursor
   and claude review, which means "say nothing about shell tools").
3. **Shell tools**, only when (2) is true: look each name up on the child env's PATH (the same
   `which` the runner already has, 2861) and emit one line per tool found, with a fixed hint:
   - `rg -n PATTERN [PATH]` for search (`--glob` to filter; ignored files need `-uu`)
   - `fd -t f --glob 'PATTERN'` to find files (regex by default without `--glob`)
   - `bat --plain --paging=never -r N:M FILE` to read a slice
   - `codegraph explore "<symbols or question>"`, only when `.codegraph/` exists at or above the
     cwd
   - `sd` only in exec, with `-p` to preview first
   - leave out rtk, eza, delta and difft by default: the first changes output a check may parse,
     the others add little headless. rtk can be opted in per project.
4. **Built-in tools** when there is no shell: for pi review, "use the grep and find tools (they
   run rg and fd)"; for `none`, "you have no tools; everything you need is in this prompt".
5. **MCP**: the codegraph_explore line only when the MCP probe says healthy *and* the argv does
   not pass `--no-mcp` (pi review always does).

Per-task skill selection:
- pi: `--skill <path>` is the only portable way in; it works with `--no-skills`, but pi loads
  skills by having the model `read` the file (`pi dist/core/skills.js:278-301`), so it is useless
  under `--tools-profile none`. Today it can only come from static `CONFIG.extraArgs`; a per-call
  `--skill` flag on the runner (allow-listed paths only) would make it per task.
- Runtimes that cannot load the needed skill (a Claude plugin such as ponytail-review, 5.1 KB
  SKILL.md, under `~/.claude/plugins/cache/ponytail/...`) get its text inlined in the prompt.
  `--prepend-file` already does this mechanically; the caller picks the file per task (review
  lane: ponytail-review; exec lane: nothing by default, which keeps the measured token saving).
- Claude review lanes already load every skill and hook; the block should say nothing about
  skills there.

Tests that would make it safe: a dry-run (`--print-argv`) case per runtime and mode showing the
block, a case where a tool is missing from PATH and its line disappears, and a review case where
no shell line appears.

---

Not checked: what the opencode 2.x `plan` agent and cursor `ask` mode actually allow for shell
(needs a real run), and whether cursor and copilot load `~/.agents/skills` headless. The rtk claim
in `.claude/cli-environment.md` looks stale (no rtk hook found), but plugin-provided hooks were
only searched by file name.
