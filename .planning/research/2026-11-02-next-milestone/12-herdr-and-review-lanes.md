# herdr, session reuse and code-review lanes (research, 2026-11-02)

Read-only research. No herdr pane, tab or agent was started, prompted or closed. Sources: the
installed herdr skill, `herdr --help` and per-subcommand `--help` (collected by
`12-herdr-help.sh` into `12-herdr-help.out` in this folder), the repo, and `.planning/`.
Runner line numbers are from the template `skills/ai-kit-spec-review/references/cross-ai.mjs`
(the rendered `.planning/scripts/cross-ai.mjs` differs and is offset by about 19 lines).

## 1. What herdr offers (herdr 0.9.3, installed at `~/.local/bin/herdr`)

Skill: `~/.agents/skills/herdr/SKILL.md` (`~/.claude/skills/herdr` is a link to it). The skill
says the installed binary is the authority for syntax and that most control commands return JSON.

Layout and lifecycle
- `workspace create|list|get|close`, `tab create|list|close`, `pane split|list|get|close|move`.
  IDs are opaque (`w1`, `w1:t1`, `w1:p1`) and never reused; read them from the JSON
  (`.result.pane.pane_id` after `pane split`). `--no-focus` keeps the user's focus.
- `pane split --cwd <dir> --env KEY=VALUE` sets cwd and extra env for the new pane;
  `tab create` and `workspace create` take the same `--cwd/--env/--label`.
- `worktree create|open|remove` makes Git-worktree-backed workspaces (needs
  `--trust-repository` only after the user verified the repo).
- `session list|attach|stop|delete` handles named persistent herdr sessions (a whole server),
  not agent sessions.

Agents
- `agent start <name> --kind <kind> --pane <id> [--timeout ms] [-- native args]`. Kinds include
  pi, claude, codex, cursor, opencode, copilot (and about 18 more). The pane must already be an
  idle shell; it returns only once herdr detects the agent ready for input (default 30 s,
  max 300 s). Names: `[a-z][a-z0-9_-]{0,31}`, unique among live agents, cleared when the agent
  exits.
- `agent prompt <target> <text> --wait [--until state] [--timeout ms]` sends text plus Enter.
  With `--wait` it requires observed `working`/`blocked` within 5 s, else
  `agent_prompt_stalled`; then waits for `idle`, `done` or `blocked`.
- `agent wait`, `agent get`, `agent list`, `agent read --source visible|recent|recent-unwrapped|detection --lines N`,
  `agent send-keys <target> esc|ctrl+c|...`, `agent explain` (why herdr classifies a state).
- States: `idle`, `working`, `blocked` (an approval or question UI), `done`, `unknown`.
- There is no `agent stop`/`agent kill`: an agent ends by `send-keys ctrl+c`/its own exit
  command, or by `pane close <id>` (kills the pane process).

Plain commands
- `pane run <id> <cmd>` (text plus Enter), `pane wait-output <id> --match|--regex [--timeout]`,
  `pane read`, `pane send-text`, `pane send-keys`, `pane process-info`.

Session identity
- Integrations (`integration install <kind>`; Claude's is the installed
  `~/.claude/hooks/herdr-agent-state.sh`) report state and agent session identity through
  `pane report-agent` / `pane report-agent-session --agent-session-id <id> -- <resume command>`.
  So herdr may know the CLI's own session id per pane. Not checked: whether `agent get` prints it.

Detection (how a script knows herdr is usable)
- `HERDR_ENV=1` (the skill's own gate), plus `HERDR_SOCKET_PATH` and `HERDR_PANE_ID`
  (the Claude hook requires all three), and `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`.
  `herdr` on PATH alone is not enough: the skill forbids controlling a session from outside a
  herdr pane. `herdr status` reports client/server versions (not run here).

Limits that matter for automation
- Output is terminal scraping, not structured: no JSON result, no exit code, no token or error
  record. `agent read` may miss part of a long answer (alternate-screen apps); the skill's
  fallback is asking the agent to write its answer to a file and reply with the path. For lanes,
  a report file should be the primary channel, not a fallback.
- Completion is lifecycle state from hooks or screen detection. `--wait` does not track turns
  (an already-working agent's current turn can satisfy it); `unknown` is not completion;
  a timeout or stall does not prove the prompt was not delivered (no blind resend).
- `blocked` means a permission or question dialog; an unattended lane must either start the CLI
  with no-prompt flags (same flags as the runner's formulas) or stop and report.
- No error classes: quota, 429 and auth errors in a pane are text on screen, so the runner's
  error catalog, retry ladder and hard tier (`retry_after_s`) do not apply as is.
- No tree-clean/dirty gate and no process-group supervision; the runner's
  `--child-pgid-file` cleanup does not cover panes.
- Environment: a long-lived herdr server keeps the env it started with, so new panes miss newly
  sourced variables until the server restarts (observed 2026-10-24, `.planning/ROADMAP.md:250`).
- Interactive login/trust screens block startup (the 2026-11-02 cursor-agent check stopped at
  the login screen, `.planning/milestones/v1.3-OWNER-FOLLOWUP.md:78`).
- Machine scope: IDs and names are per server; `--machine` targets saved SSH profiles only.

## 2. herdr in this repo and its planning history

No code, test or skill uses herdr (`rg --hidden herdr` hits only `.planning/`). Uses so far are
manual live checks:
- Phase 21.2 spike ran pi's compaction interactively in a herdr pane (2026-10-23,
  `.planning/milestones/v1.3-phases/21.2-.../21.2-SPIKE.md:162`).
- 2026-11-02 live closures: wake lifecycle, opencode `session list`, pi interactive (one tiny
  prompt; 182 models through RPC, only `PI_CODING_AGENT` exported)
  (`.planning/milestones/v1.3-OWNER-FOLLOWUP.md:62`, `:188`).
- The env-inheritance note above (`.planning/ROADMAP.md:250`, `v1.3-ROADMAP.md:1209`).
- Open items that name herdr as the tool: the live-checks todo
  (`.planning/todos/pending/2026-11-02-pending-live-checks-and-owner-decisions-from-v1.3.md:31`, `:52`),
  `NEXT-MILESTONE-INPUTS.md:80`, `:150`, `:171`, and the owner's round-3 wishes at `:517-528`
  (copilot `/models` through herdr; herdr as a lane transport).
- `~/.claude/settings.json` registers the herdr Claude hook (`herdr-agent-state.sh session`),
  noted in `.planning/research/2026-10-13-audit/12-gsd-per-repo-install.md:7`.

## 3. Session reuse without herdr (what the runner does today)

Per runtime (`RUNTIMES`, cross-ai.mjs:1330-1447):
- cursor: resume `--resume <sid>` (:1336); sid captured from the `result` event's `session_id` (:1342).
- opencode: resume `--session <sid>` (:1359); sid from `sessionID` in the JSON events (`parseOpencode`, :1488-1499).
- pi: the runner pre-assigns `--session-id <uuid>` (:1370, :1372, ctx at :3878); "resume" just reruns
  with the same id (:1374); a fresh session gets a new uuid (:3212); the sid used is `ctx.sid` (:4187).
- codex: `exec resume ... <sid>` (:1394), sid from `thread.started` (:1401); exec only — review mode
  and a sandboxed exec never resume because the resume argv has no read-only sandbox (:3204-3208).
- claude: `resume: null` (:1420) although `session_id` is parsed (:1425); claude is review-only
  here. The CLI itself has `--resume <id>` and `--session-id <uuid>` (checked in `claude --help`).
- copilot: `resume: null` (:1444), sid not parsed (:1445). The CLI has `-r/--resume [id]`,
  `--continue` and `--session-id <id>` (checked in `copilot --help`); error shapes unverified.

Where resume is used: only inside one call's retry ladder. Rung "same" resumes the captured
session with `RESUME_MSG` (:129, :4283-4284); after `max_retries` it does `session_resets`
(default 1, :3060) fresh sessions (`ladderNext`, :3171-3189). Across calls, one lane record per
(cwd, CLI, model, route) (`cycleFilePath`, :3273-3278) stores `last_sid` plus `task_digest`
(`saveCycle`, :4023-4030); a later call resumes `last_sid` only when the task digest matches
(:4069-4079), i.e. a re-entry after an exit-75 quota hint, never a new review round.

The runner has no flag to pass or return a session id (`parseArgs`, :4370-4430; header :21-51);
the sid shows only in stderr attempt lines (`logAttempt`, :3842-3847), not in the final
`AIKIT-XAI` line.

Skills:
- ai-kit-spec-review dispatches every reviewer fresh per round by design: "Edits Applied →
  re-review with fresh reviewer" (`skills/ai-kit-spec-review/SKILL.md:429`), clean-context
  subagents (`SKILL.md:8`). `dispatch_reviewer` builds a new runner spec each call
  (`ai_kit_spec/reviewer_dispatch.py:69-110`). Iteration cap is 3 (`SKILL.md:190`).
- ai-kit-spec-execute-superpowers, `external_cli` tasks: fix rounds 1-3 keep the same pair
  (`references/escalation.md:79`) but each round changes the objective (open findings appended),
  so the task digest changes and the runner starts a new session; the CLI picks up context from
  `$REPORT_FILE` (APPEND rule) and git, not from its own transcript
  (`references/dispatch-external-cli.md:44-52`). Native tasks keep superpowers' own behavior:
  rounds 1-3 resume the implementer, round 4+ is a fresh implementer on a more capable model
  (superpowers 7.0.0 `subagent-driven-development/SKILL.md:75`, `:375`).
- ai-kit-spec-execute-gsd: one runner call per plan through `workflow.cross_ai_command`; no
  cross-round state.

Context-growth trade-off
- For: a resumed reviewer skips re-grounding (re-reading the codebase and doc), so later rounds
  are faster and cheaper on providers with prompt caching; a resumed implementer keeps its own
  reasoning about the code it wrote.
- Against: every round adds the prior prompt and answer, so cost per round grows and long
  sessions hit compaction (lossy summaries); a reviewer that saw its own earlier findings tends
  to anchor on them (re-checks its list, misses regressions the fix introduced), which is the
  reason spec-review chose fresh reviewers; a stale session also hides changes made outside it.
- Superpowers' rule (resume up to 3 rounds, then fresh) is a ready precedent for "renew after N".

## 4. Code-review lanes today

- ai-kit-spec-execute-superpowers does not chain any code review. Step 4 states task review,
  fix loop and final whole-branch review run unmodified, and the skill's scope ends at Step 3
  (`skills/ai-kit-spec-execute-superpowers/SKILL.md:278-283`, also `:8-14`). Those reviews are
  superpowers' own native subagents (`requesting-code-review` dispatches a `general-purpose`
  subagent with `code-reviewer.md`; SDD's final review at its `SKILL.md:88`, `:445`). No
  `requesting-code-review` reference exists anywhere under `skills/` or `tools/`.
- ai-kit-spec-execute-gsd does not chain code review either; GSD's own `workflow.code_review`
  (on in `.planning/config.json:33`) runs `/gsd-code-review` with the native
  `gsd-code-reviewer` agent.
- ai-kit-spec-review has no code-review (diff) mode: archetypes are only intent, requirements,
  design, plan (`skills/ai-kit-spec-review/SKILL.md:97-101`); no diff handling in
  `ai_kit_spec/*.py` or the checklist skill.
- No ai-kit skill routes code review to cross-AI reviewers. Two GSD-side hooks exist and are
  unused by ai-kit:
  - `workflow.code_review_command` (null in `.planning/config.json:35`): `/gsd-ship` pipes the
    diff to it and expects JSON `{verdict: APPROVED|REVISE, ...}` with a 120 s timeout
    (`.claude/gsd-core/references/planning-config.md:306`, `workflows/ship.md:389-420`).
    ai-kit's curated-config never sets it (`ai_kit_gsd_curated_config/cross_ai.py:18`).
  - `/gsd-code-review` external reviewer lanes (`--codex`, `--agy`, ... from GSD's own lane
    roster) beside the native reviewer (`.claude/gsd-core/workflows/code-review.md:570-640`);
    these use GSD's dispatcher, not `cross-ai.mjs`.

## 5. Proposal outline (a proposal, not decided or verified)

Lane transport, one setting per lane entry or run: `subprocess` (today), `resumed` (subprocess
that resumes a stored CLI session), `herdr` (live pane). `auto` picks herdr only when
`HERDR_ENV=1` and the socket variables are set, else resumed when the runtime has a resume
formula, else subprocess. Detection is a new question, separate from
`detect_installed_clis()` and `detect_current_runtime()`.

Lifecycle per plan (one record per plan key + lane key + runtime + model)
- Create on the first round; store transport, session id, herdr pane id and agent name,
  round count, created time.
- Reuse on later rounds of the same plan: `resumed` passes the stored id; `herdr` prompts the
  live agent and asks for the answer in a report file.
- Renew after N rounds (default 3, following superpowers), on model or pair change, on a
  compaction notice, or when the stored session fails to resume; renew = close plus create,
  with a short handoff note (findings so far) instead of the transcript.
- Close at plan close (review approved, cap reached, execute final review done): `herdr`
  closes only panes it created (by recorded pane id), `resumed` just drops the record.
- Crash cleanup: agent names carry a plan-key prefix (fits the 32-char limit) and records carry
  pane ids, so a sweep at the next run start lists `herdr agent list` and closes stale owned
  panes; a time cap like the runner's `capS` drops stale records.
- Spec-review keeps "fresh reviewer" as its default; reuse is opt-in per lane because of the
  anchoring risk in section 3.

Runner contract needs
- Input: `--session <id>` (resume a given session; refuse when the runtime has no resume
  formula, or for codex review), and optionally `--session-id <uuid>` pre-assign for pi,
  claude and copilot.
- Output: the session id in the final `AIKIT-XAI` line (for example `session=<id>`) so the
  Python dispatch layer can store it without parsing attempt lines.
- Resume formulas for claude (review: `-p --resume <id> --permission-mode plan`, read-only
  still unverified) and copilot (`--resume <id>`), each live-checked before use.
- The per-plan session store and round counter live in the skills' Python layer
  (`runner_dispatch.py` / `reviewer_dispatch.py` / `execute_dispatch.py`), not in the runner,
  which stays one call per invocation.
- A herdr transport would be a separate launcher beside `run_runner`/`run_custom_command`,
  because it cannot provide the runner's error classes, retry ladder, exit-75 hints or tree
  gate. It must start each CLI with the same no-prompt and read-only flags as the runner's
  formulas (passed after `--` to `agent start`), wait with `--wait --timeout`, read a report
  file, and treat `blocked`, `unknown`, `agent_prompt_stalled` and timeout as failures for the
  caller to handle (never a blind resend).
- Code review: either add a diff mode to ai-kit-spec-review, or render a
  `workflow.code_review_command` adapter that runs cross-AI reviewers and returns GSD's
  `{verdict}` JSON (120 s ship timeout is short for a cross-AI lane). Superpowers' own reviews
  stay untouched unless the owner wants an extra cross-AI pass after the final review.
- Copilot `/models` through herdr: start copilot in a scratch pane, send `/models`, read the
  screen, close the pane. Screen parsing is fragile; compare with an online catalog first.

Open questions for a spike
- Does `herdr agent get` expose the CLI session id the integrations report?
- Can a herdr-hosted session be resumed later headless by the runner with the same id (and the
  other way round)?
- Real behavior of claude and copilot resume in print mode, including read-only enforcement.
