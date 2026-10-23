# ai-kit audit and research synthesis (2026-10-13)

This combines 9 parallel Opus research reports (`01`–`09` in this folder). All of them read the v1.3 tip at 0acbd06; none changed anything.

The orchestrator re-checked the top findings independently:
- `core.hooksPath` points at a missing directory.
- The dashboard escape is case-sensitive (`dashboard.py:2040`).
- `quota.py:237` runs reviewer commands with `shell=True`.
- `codex exec --help` has no `--full-auto`.
- The usage-metrics store is 3.1 GB.

One correction to report 02: v1.3 is not "on no remote". It was pushed to `gitlab` at 1ccdc1e and is now 2 commits behind. GitHub `origin` does not have it.

## A. Fix first: safety and correctness (small, high value)

Each item gives the report it comes from.

1. **No quality gate ever runs** (02, 03). `.git/config` `core.hooksPath=/home/user-zero/.../.git/hooks` does not exist, so git runs no hooks. pre-push was never installed, and CI only scans for secrets.
2. **The gate scope is wrong even when hooks run** (02, 03).
   - The ruff and py-compile regexes skip 36 of 191 Python files, including all of `ai_kit_spec/` and superpowers.
   - `make validate` never runs 6 test modules.
   - pylint covers only 3 files.
   - 12 ruff and 6 pylint findings have been re-deferred for 3 milestones.
3. **Branch code imports main's code** (03, 05). curated-config `model_detect.py` and rules-all `dispatch.py` resolve `~/.claude/skills`, which symlinks to main, before their own siblings. So v1.3 tests exercise main's `ai_kit_spec`, which differs by 842 lines. **This must be fixed before any v1.3 verification can be trusted.**
4. **Security: a cloned repo can run commands** (03). A local `.aikit/review-spec.toml` reviewer `command` runs with `shell=True` during the default `--cross-ai` `probe-quota`.
5. **Security: script breakout in the dashboard** (05). `</SCRIPT` escapes the case-sensitive filter, on a page holding the full command history. One-line fix: escape `<` as `<`.
6. **A failed review can read as Approved** (04). `Status: Failure` merged with an approved report in double mode yields Approved.
7. **The claude and grok execute command strings are broken** (04, 08). Their nested `sh -c` quoting breaks on spaces and allows `;` injection. GSD also word-splits the command without a shell, so they can never run there.
8. **Misclassified quota errors** (04). Any output containing "quota" counts as a quota failure, so a real failure is retried on another CLI over a half-edited tree.
9. Smaller safety items:
   - **Codegraph probe** (04): no timeout, and a silent `codegraph install --location=global --yes`.
   - **Config parsing** (04): a `review-spec.toml` parse error silently disables cross-AI.
   - **Installer** (03): `install.sh --branch` is ignored on an existing clone, and `--dry-run` still pulls.
   - **Writes** (03): the cache `.tmp` name is fixed, so concurrent writes can race; uninstall writes `settings.json` non-atomically.
   - **Checkers** (05): the AGENTS.md checker crashes on image links; `cst-refactor` rename over-matches and has no tests.
10. **The usage-metrics raw store is 3.1 GB** (05). Every record is stored twice, and refine loads everything into RAM (about 7 GB estimated).

## B. Promised vs delivered

**v1.0 and v1.1 (report 01):** mostly delivered and tested. Partial, regressed or lost items:
- **Nested-session runtime detection is wrong on main.** It is fixed only on v1.3, and the live install runs main.
- **The usage-metrics `classify` pass never ran on real data.** There are 0 of 92.5k inferred rows, because `run` excludes `classify`.
- **Config Doctor applies 4 of 25 rows**, against about 10 in the PRD. The missing ones include the security rows: opencode `permission` and codex `sandbox_mode`. This is a lost deferral.
- **The status-line quota formula changed 3 times.** The current gap format adds a sign and so breaks the "color-only" criterion. PROJECT/REQ were not updated, and the spec is still a draft.
- **Python tool recommendations were orphaned** by the v1.2 cache rename.
- **`claude_md_path` points at `./CLAUDE.md`**, which does not exist; the file is `AGENTS.md`.
- **6 Config Doctor safety tests skip silently** when textual is missing.
- **Stale docs:**
  - the README skill table and its `commands/` dir;
  - the architecture doc, which names 7 missing functions;
  - no v1.0 audit, and 8.1 never audited.

**v1.2 (report 02):** holds up. Its audit debt is closed except the lint findings. The mmdc item is stale: that test now passes.

**v1.3 (report 02):**
- **Phase 16 is delivered but not closed.**
  - No VERIFICATION file.
  - STATE, REQUIREMENTS and ROADMAP are stale.
  - The live checks never ran: `runtimes.json` has no `schema_version`, and `model-catalog.json` does not exist.
- **None of v1.3 is live**, because the installed symlinks point at main.
- **The environment has drifted.**
  - Only Claude still has gsd-core, at 1.16.0; the spec assumed 1.14.
  - The GSD agent folders for opencode, codex and cursor are empty, so the preconditions for Phases 20–22 are gone.
  - `~/.gsd/defaults.json` has `runtime: codex`.
- **The docs contradict each other:**
  - SKL-03 vs REQ:77;
  - the spec header says "draft", REQUIREMENTS says "approved";
  - 18-CONTEXT still says ponytail is not installed;
  - with no Artificial Analysis key, the ranking falls back to price only.

**Backlog and todos:**
- 999.1 is partly done; 999.2 has not started.
- **999.4 is defined 3 different ways across 3 branches.**
- The ponytail 999.4 is mostly covered by the Phase 18 design.
- The System One todo has not started; its prerequisite service answers (`/health` 200, no models loaded).
- The Cursor POC todo is open.
- The `context-tools-manager-plan1` worktree holds 21 unmerged commits that overlap the host-split work.

## C. Ponytail lens: delete, merge and split

- **Spec family (04):**
  - about 180 dead lines, and about 1,300 removable lines; roughly 40% of the library is comments and review history;
  - delete the `ai-kit-spec-execute` router;
  - merge the 2 `assemble_candidates`, the 2 reviewer prompts and the 5 copies of the path-lookup shell block.
  - Token weight: the review orchestrator loads about 14.8k tokens before any work, plus about 5k per reviewer and 3.2k per fixer per iteration. Superpowers execute loads about 16.3k, and config about 13.3k.
- **Rules family (05):**
  - the 7 skills total about 24k tokens of instructions; merge them into one `ai-kit-project-rules` with a domain option;
  - the checkers use contradictory category vocabularies;
  - `remediate` drops the fix text;
  - the docker skill duplicates YAML helpers, and its description runs over 1024 characters.
- **curated-config v1 (05):** label it legacy now, and delete about 600 lines after Phase 19 has used it as a baseline.
- **Smaller cuts (03, 05):**
  - delete `commit-message`, which overlaps `commit-work`;
  - remove the mermaid bash fallback, the 7 re-export shims, the 2 near-identical session-start hooks, about 10 copies of an atomic-write helper, and the superseded wizard prototype;
  - move the dashboard's 1,950-line HTML string into a template file;
  - split the 663-line `ai_kit_spec/cli.py:main`.
- **Architecture (03):**
  - the real shared library, `ai_kit_spec`, lives inside a skill and is reached by 3 different path tricks;
  - no test checks import direction (the 999.3 gap).
  - Proposed: promote it to `skills/_shared`, use one bootstrap, and add an import-direction arch test.

## D. Pi as the cross-AI executor (report 06)

**Measured** (single runs, same router model):
- pi: 3.9 s, 188 MB, 16.9k tokens.
- `opencode run`: 16.5 s, 668 MB, 36.5k tokens.
- pi is therefore about 4× faster to answer and uses about 3.5× less memory.

**MCP is now native:**
- pi gained built-in MCP in 0.99.0 (2026-09-29); `--no-mcp` exists from 1.0.4.
- The installed 0.82.1 is older and has no MCP.
- The latest release is 1.2.0, which also fixes exit code 0 on truncated output. The npm package is now `@earendil-works/pi-coding-agent`.
- GSD plan tasks do not need MCP.

**The router errors** (capacity, 402, credential gate) come from `router-env`, not from opencode. Prefer pi's direct OAuth providers: `openai-codex` and `anthropic` are already logged in.

**Gotchas:**
- pi blocks if stdin stays open, so resume calls need `< /dev/null`.
- `-p` prints only the final text and exits 1 on error. Avoid `--mode json`, which exits 0 on error.
- `--session-id` gives deterministic retries.
- The user's pi defaults (gpt-5.6-terra at xhigh, plus superpowers skills and extensions) need overriding with `-ns -ne`, an explicit model and an explicit thinking level.
- There is no sandbox; use a worktree per plan.

**Candidate command:**
`pi -p --model openai-codex/gpt-5.6-terra:medium --no-extensions --no-skills --no-approve --offline`

ai-kit also needs a pi execute builder and a `KNOWN_CLIS` entry.

## E. What GSD subagents inherit (report 07)

**Claude, in-session:**
- Tools come from each agent's explicit `tools:` allowlist.
- MCP is granted only when the allowlist names a server. So 34 of 35 GSD agents run with **no MCP at all**, not even codegraph.
- Inherited wholesale: the CLAUDE.md/AGENTS.md hierarchy, all hooks, the git snapshot, and the skills listing through the Skill tool.
- Ponytail's SubagentStart hook already injects about 715 tokens into every subagent.

**`agent_skills`** adds prompt text and never restricts anything:
- `global:<plugin>:<skill>` works on Claude only, and needs the Skill tool, which 13 GSD agents lack.
- `@path` lines are not expanded inside `Agent()` prompts, so each listed skill costs one Read.
- It does not use Claude Code's native `skills:` preload field.

**Other hosts:**
- The GSD opencode and cursor converters **strip `tools:`**, so read-only checkers there get full write access.
- Codex keeps tools only as prose plus `sandbox_mode`.
- Cross-AI subprocesses get the target CLI's full default surface, with no `agent_skills` and no restricting flags.

**GSD's own payload dominates the cost:** about 12k tokens of system prompt plus about 32k of embedded workflow context for the executor.

**For the ponytail backlog item:** on Claude, the hook already covers every subagent. `agent_skills` matters only for non-Claude hosts.

## F. Curated cross-AI wrapper (report 08)

**Current state:**
- The wrapper exists (`ai-kit-spec-gsd.py dispatch-execute --stdout-only`), but only the execute-gsd skill writes it.
- curated-config v1 and the planned Phase 18 XAI-02 write raw builder strings.
- This repo's own config holds a third, hand-written shape without `--auto`.

**Verified bugs:**
- The raw claude and grok `sh -c` strings fail under GSD.
- codex 0.153.4 rejects `--full-auto`, yet `~/.claude/skills/codex/SKILL.md` still recommends it.
- The wrapper can orphan the CLI: it starts a new session and has no SIGTERM handler.
- Timeouts are paired by hand, and a timeout exits 247 instead of 124.
- Claude's execute builder (`--restricted`) removes Bash, so Claude cannot act as an executor. **User decision needed.**

**Smallest fix** (about 60–80 lines plus tests): one `xai --cli X --model Y` subcommand, emitted by both writers.
- Uses the current directory as the target.
- Derives its timeout from `cross_ai_timeout` minus 30 s.
- Forwards SIGTERM.
- Strips host environment signals from the child.
- Exit codes: 0, the CLI's own code, 124, 127 or 2. Stdout carries only the final answer.

**Increment 2:**
- Inline the role's skills from `gsd-tools query agent-skills <role>`.
- Switch off host skill discovery: pi `--no-skills`, claude `--disable-slash-commands`, opencode `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`.
- Retry only on transient errors, resuming the session.
- Lint existing raw `cross_ai_command` values.
- Add the pi builder.

Review lanes need no wrapper. Phase 18 XAI-02 should say "the xai wrapper" instead of "built by build_execute_command".

## G. Tool inventory and per-subagent curation (report 09)

- **No persistent cache is needed.**
  - A full scan (347 entries, frontmatter parsed) takes 5.6–19.4 ms, and a digest about 3 ms. Rescan on every run.
  - Persist only user-confirmed role mappings, keyed by description hash (`~/.config/ai-kit/skill-roles.json`).
  - Never cache MCP health.
- **The real problem is visibility, not token count.**
  - `ai-kit-*` and `gsd-*` skills exist only in `~/.claude/skills`, and plugin skills are Claude-only.
  - For any other CLI, an absolute SKILL.md path is the only channel. The inventory's job is a per-skill "visible to" list.
- **Smallest version:** `select_skills(role)` emits one `SKILL_HINTS` line in the existing `build_tooling_guidance` block, fed by Phase 18's `skill_affinity.json` re-keyed by role.
  - **Hard mode where a host allows it:** pi `--no-skills --skill <path>`; `claude -p --disable-slash-commands`, plus `--strict-mcp-config` when needed.
  - **Elsewhere:** prompt hints only.
- **Cut MCP curation from v1.** This machine has only 1–2 MCP servers per host. The large published gains (tool search: 85% fewer tokens; RAG-MCP: selection accuracy 13.6% → 43.1%) apply to large MCP tool sets.
- **jev-fast-decision:**
  - **Poor fit for per-dispatch routing:** it is advisory-only and answers single labels; the live script is still v1 (Zen only); Plan B has not been executed; its 0.6 threshold was calibrated on a stub.
  - **Good fit at config time only:** sorting unknown skills into role buckets, cached by description hash, with the user confirming.

## Proposed sequencing

0. **Housekeeping**, done by the orchestrator with consent:
   - fix `core.hooksPath` and install the pre-commit and pre-push hooks;
   - renumber the ponytail backlog item to 999.5;
   - push to GitLab, and decide about GitHub.
1. **Insert Phase 16.1 "Hardening"**, before Phase 17:
   - A2 gate scope and lint debt;
   - A3 sibling-first imports (a prerequisite for the rest);
   - A4–A9 security and correctness;
   - A10 store compaction, optional.
   - Then close Phase 16: VERIFICATION, run the live checks, and update STATE/REQ/ROADMAP.
2. **Refresh the v1.3 facts before planning Phase 17:**
   - gsd-core is now 1.16;
   - the GSD installs on other hosts are gone (reinstall them before 20–22);
   - `~/.gsd/defaults.json` has `runtime: codex`;
   - there is no AA key, so the ranking is price-only;
   - fix the stale ponytail and skill-count statements.
3. **Amend Phase 18:**
   - F, the `xai` wrapper with a pi builder;
   - the G-minimal skill hints;
   - ponytail mapping for non-Claude hosts;
   - the Claude executor decision.
   - Optionally add Phase 23, "skill hints in dispatch guidance", wired across execute-gsd, superpowers and review.
4. **Execute Phases 17 → 19 through the new wrapper.** Pilot pi with a direct OAuth model as the primary executor, with opencode as the fallback.
5. **Next milestone, "lean" (v1.4):**
   - the C deletions and merges;
   - the lost deferrals (Config Doctor security rows, `classify` in `run`, the Python cache migration);
   - the status-line formula decision and its docs;
   - host-split 999.4, after v1.3 merges to main;
   - the System One todo, which is independent.

---

## Wave 2 (2026-10-13 afternoon): the user's scope clarifications

**Scope:**
- ai-kit owns our own skills, the Claude and Cursor status lines, and the GSD config helpers.
- tools-installer owns third-party plugin and skill-set installs, and GSD installs.
- Claude is the main agent and is not a cross-AI target.
- cursor, grok, opencode and pi must run plans with full permissions.

### H. Runtime reference and cross-ai.mjs (reports 10, 08)

**Live-verified unattended execution.** Prompt on stdin; each run creates a file, runs a command and commits.
- cursor (`auto`): `cursor-agent -p --trust --force --sandbox disabled --approve-mcps --model auto`. 46 s.
- opencode (free `opencode/big-pickle`): `opencode run --auto --model …`. 27 s.
- grok (`grok-4.7-build-fast`, about $0.07 per run): `grok --prompt-file /dev/stdin --always-approve --permission-mode bypassPermissions`. 12–25 s.
  - grok's `-p` cannot work under GSD, which word-splits the command without a shell.
  - grok loads the whole Claude setup (191 skills, 5 plugins, 21 hooks, MCP), and no per-run switch was found.
- **Read-only review modes held:** cursor `--mode ask` and opencode `--agent plan` made no writes and did not stall.
- **codex:** login expired (401), although `codex login status` says logged in.
- **pi:** not installed right now, so it was not live-tested.

**The global house style leaks into every headless run:** the "Skipped/Risk" trailer appeared in all three replies.

**Project configs:** 5 of the 6 `cross_ai_command` values are wrong; only kitty-setup is correct.

**Prototype `research/cross-ai.mjs`** (477 lines, stdlib Node):
- `--prefer pi,cursor,opencode,grok` with a model per CLI.
- Falls back to the next CLI only when git HEAD and status are unchanged.
- Inner deadline set below GSD's timeout; exits 124 on its own timeout; leaves no orphan process.
- Retries only transient errors, resuming the session.
- `--self-test` passes (re-checked by the orchestrator).

**Generator design:**
- curated-config writes `.planning/cross-ai.mjs` and sets `cross_ai_command = node .planning/cross-ai.mjs`.
- A sha256 header protects user edits: an edited file is never overwritten, and the new version goes to `.mjs.new`.
- It replaces the Python wrapper proposed in report 08. XAI-02's wording needs amending.

### I. pi models and assets (report 11, prototype `pi-sync/`)

- **Models:** pi 1.2.0 already includes opencode Zen (38/39), opencode Go (31/31), xAI (API key, or SuperGrok/X Premium login) and Codex (ChatGPT login). What is missing is credentials: one `OPENCODE_API_KEY`, plus `/login xai`.
- **Cursor cannot be a pi or opencode model,** because Cursor has no inference API. Delegate to `cursor-agent -p` instead.
- **router-env** is already synced by llm-env, which has two defects: it writes the API key as plain text, and it overwrites `enabledModels` on every run.
- **pi is uninstalled,** leaving 6 dangling symlinks (the subagent extension and 4 agents).
- **Skills:** pi reads `~/.agents/skills` but not `~/.claude/skills`. `~/.pi/agent/skills` holds 33 duplicate symlinks that cause name collisions; delete it.
- **MCP:** pi has only its own `mcp.json`; the prototype converts opencode's MCP servers.
- **The sync prototype** reads key values by command and never copies them, is dry-run by default, and changes nothing on a second run. It belongs in tools-installer.
- **Upgrade:** `pnpm add -g --ignore-scripts @earendil-works/pi-coding-agent@1.2.0`, or 1.1.0 if pnpm refuses a release under a day old. Then re-point the symlinks and run `/login xai`.

### J. GSD per repo (report 12, plus an orchestrator correction)

- **Graphify:** every GSD hook checks for `.planning/config.json` first, so the hooks are inert in non-GSD repos. The likely graphify blocker is the global `gsd-graphify` skill, which answers with GSD setup text.
- **Duplicate hooks:** at 12:40 something re-registered 15 GSD hooks in the global `~/.claude/settings.json`. ai-kit's `.claude/settings.local.json` holds the same 15, so they run twice there.
- **Migration:**
  - local, gitignored `--claude --local` installs in the GSD repos (gitid, home-mobility, kitty-setup, wezterm-setup still lack one);
  - then the global uninstall.
  - Owner: tools-installer. Its registry already lists opengsd; its status check has 2 bugs.
- **ai-kit prerequisite:** `gsd_catalog.py:16-62` and `ai-kit-spec-execute-gsd/SKILL.md:238,247` assume a global gsd-core.

### K. Claude Code noise (report 14)

- `disableClaudeAiConnectors: true`, or `ENABLE_CLAUDEAI_MCP_SERVERS=false`, turns off claude.ai connectors in the CLI only.
- `syncClaudeAiSkills: false` stops the synced `anthropic-skills:*` set.
- **Costs:** deferred MCP costs only names and instructions up front, but every skill description is in context on every turn.
- **Subagents:** one with no `tools` list inherits all MCP, including claude-in-chrome and playwright. GSD agents have fixed allowlists, so they don't.
- **The two browser MCPs are independent.** Verify claude-in-chrome with `/chrome`.

### L. Status lines (report 13)

- **The Claude gap commits cherry-pick cleanly onto main** (326 tests pass in a scratch clone). They wait on the user approving the gap rendering.
- **The Cursor POC must not be promoted as code:**
  - it fetches quota inside the render (1.9 s against Cursor's 300 ms kill), so the cache is never written;
  - it keeps showing stale quota indefinitely;
  - it uses the old 50/80 color scale instead of the gap rule;
  - about 620 of its lines are copies of `status-line.py`;
  - its `git` calls have no timeout;
  - it shows the reset date in UTC;
  - any `https://` value in `CURSOR_API_ENDPOINT` receives the Cursor token.
- **Target shape: 6 files.** `common_statusline.py`, `claude_statusline.py`, `cursor_statusline.py`, and `cursor_quota.py` (the only network and token code), plus two thin entry scripts. A background fetch runs behind a lock file.
- **Ready-to-apply 999.4 and todo text** is in report 13 §5, together with 9 decisions for the user.

---

## Wave 3 (2026-10-13 evening)

### M. pi 1.2.0 live tests (report 15)

- **Unattended edits and commits work:**
  - `router-env/my-coding`: 16.6 s;
  - `opencode-go/glm-5.3-flash`: 23.3 s, about $0.002;
  - nothing waited for approval.
- **Carrying the opencode key works with no config change.** With `OPENCODE_API_KEY` set for that process only, pi lists 83 Zen and 31 Go models.
  - Free Zen models return 403 FreeTierError: they work only inside opencode.
- **`cross-ai.mjs` + pi works end to end, but skills must be off.** With skills on, the same plan took 278k tokens and 55 s; with them off, 17k tokens and 17 s.
- **Formula:** `-p --model <m> --session-id <uuid> --no-extensions --no-skills --no-approve --offline`.
  - `--session-id` resume is tested.
  - Reasoning models need a `:low`-style suffix, or pi defaults to xhigh.
- **Open stdin hangs pi even when the prompt is an argument.**
- **User actions:**
  - 6 dangling symlinks point into the deleted Volta install, so the subagent extension does not load;
  - pi's Anthropic login expired on 2026-07-26;
  - `/login xai`.
- openai-codex in pi answered fine; it is not out of quota there.

### N. Playwright/Chrome on Bazzite (report 16)

- **Broken everywhere, subagents included.** `@playwright/mcp` 0.0.83 defaults to `/opt/google/chrome/chrome`, but Chrome exists only as a Flatpak.
- **Tested fix:** settings `env` `PLAYWRIGHT_MCP_EXECUTABLE_PATH=/var/lib/flatpak/exports/bin/com.google.Chrome` (path verified). A throwaway `claude -p` run with it got "Example Domain". cursor-agent needs the same variable in its own MCP config.
- **Subagents receive both browser MCPs** (deferred, loaded via ToolSearch). `gsd-dom-verifier` names chrome-devtools, which is not installed, plus claude-in-chrome, so it has no working browser.
- claude-in-chrome reports "extension not connected".
- **Setup script:** better as 3 Config Doctor rows (connectors, synced skills, Playwright path) plus a `.bak` backup, about 60 lines.
- An upstream issue for microsoft/playwright-mcp is drafted, not filed.

### O. GSD config → agent sync (report 17)

- **There is no automatic sync.** `config-set` only writes, and the config-reload hook only injects a text summary.
- **Baked at install time:**
  - Claude `effort:` lines need `gsd-tools effort sync --apply`. curated-config v1 writes `effort.agent_overrides` and never syncs, so those overrides are inert. Syncing would lower the heavy agents from xhigh to high, which needs a decision.
  - codex, opencode and kilo bake models into their agent files and need a reinstall or `/gsd-update --reapply`.
  - Claude models resolve at spawn time; cursor and pi bake nothing.
- **Project-local `.claude/agents` take precedence,** so sync must target the project's own install. ai-kit's `gsd_catalog.py` always uses the global copy.
- **Phase 18 D-05** already plans post-write follow-ups. Extend it to codex and kilo, and look for the local gsd-core first.

### P. Runtime detection and subprocess supervision (report 18, 17 live probes)

- **No CLI hangs on a permission prompt when stdin is not a TTY; they fail silently instead.**
  - opencode without `--auto` auto-rejects the write and exits 0 with empty output.
  - grok without `--always-approve` returns `stopReason:"cancelled"` and exits 0. `cross-ai.mjs` would count this as a success.
  - pi with an empty prompt exits 0 with no output.
  - Only cursor fails loudly: exit 1, "Workspace Trust Required".
  - The only real hang is an open stdin.
- **Output growth cannot tell slow from stuck.** Open network sockets can.
- **Bad model ids are worded differently by every CLI**, and opencode's error never names the model. Pre-validate against each CLI's model list, which takes 0.2–1.5 s and costs no model call.
- **Both classifiers read the model's own answer text.** That is the root cause of the quota misclassification, and `cross-ai.mjs` would retry on a `503` inside an answer. Match only stderr and structured error fields.
- **Simplify "native":**
  - `native_runtime` is written and validated but never read by routing. Delete it.
  - Model candidates as (runtime, model) pairs: a native subagent when the runtime is the current host and the host can select that model; otherwise a subprocess.
  - Remove the `native_claude` naming and the cursor/cursor-agent split.
  - Add `GROK_AGENT`, add pi to `KNOWN_CLIS`, and scrub the inherited `AI_AGENT`.
- **Supervision contract:**
  - prevention first: finite stdin, model and prompt pre-checked, explicit flags, kill the whole process group;
  - an idle timeout gated on "no network sockets", separate from the wall timeout;
  - an error table matched on stderr and structured fields only;
  - exit codes 0, 1, 2, 69, 75, 124, 127;
  - one mandatory `AIKIT-XAI status=… action=fallback|retry-later|stop` line;
  - exec success requires evidence: HEAD moved or the tree changed.
- **Recommendation: one implementation.** The Python dispatchers call `cross-ai.mjs`, which makes node a dependency of the review path (user decision).
- **Phase mapping:** 16.1 (classifier and env-signal fixes), 18 (the runner contract), and a new 18.1 "one runtime model" (schema and skill rewrite, plus `/skill-judge`).
