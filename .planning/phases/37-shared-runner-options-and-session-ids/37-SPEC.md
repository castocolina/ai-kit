# Phase 37: Shared runner options and session ids — Specification

**Created:** 2026-11-16
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 11 locked; 12 locked after the 2026-11-16 re-run 2 (R12, optional herdr hosting) *(amended 2026-11-21, plan time, owner requests of 2026-11-19 and the grok directive of 2026-11-20, 37 D-31 to D-34: 14 locked; R13 (lane skills, runner side) and R14 (lane MCP servers, runner side) added under RUN-01; R1 to R12 unchanged; the grok mentions below are superseded history)*

## Goal

One runner (`cross-ai.mjs`) serves open-gsd cross-AI execution and ai-kit review and execute lanes. A call names the
runtime, model, effort, context, escalation flags, role and session id, taken from the config or from the calling
skill's decision. Every setting a call names is printed as applied, ignored (with a reason from a closed list) or
unknown, and the runner never feeds a runtime a setting it has no form for. No seed table decides what the runner may
run: an unknown runtime with a declared command, a model id of an unusual shape, an effort level a host lists and a
runtime with no seed formula are served or refused for a named fact, never for a table row. A second round with a
printed session id resumes the session, and a test fails when the rendered project copy drifts from the template.

## Background

Requirements RUN-01, RUN-02, RUN-06 (REQUIREMENTS.md "Shared runner"), the 2026-11-16 GSD lane-handling amendments
(settings reported as applied or ignored; a table never decides), and the items Phase 36 handed here (claude `--effort`,
copilot `--reasoning-effort`, the effort levels the runner's closed sets reject, `lane_escalation`, removing the
`no_formula` route and the `exec_formula` mirror with its drift test, `unknown_runtime`, `no_inventory`). Phase 35's
hardcoding guard and Phase 36's per-lane `effort` and escalation keys are inputs.

**The owner's decisions (highest priority):**

- A runtime table is seed data and examples only, each row labeled with its source (verified with date, or unverified);
  it never decides. What a runtime accepts is learned live (its own `--help` or listing, a probe call, the catalog) and
  live evidence beats a row. A runtime missing from the table and a custom command lane can still serve review or
  execute with each setting shown as unknown until learned. A setting a runtime cannot take is reported as ignored with
  the reason, never fed and never dropped silently (2026-11-16 directive, written into every phase it touches).
- Only `router-env/<x>` model names may be hardcoded; the runner's marked examples carry the guard's marker and no list
  in it decides anything (HUB-09, 35 D-16 to D-18). The runner's self-test harness and its baseline entries belong to
  Phase 38.
- Never switch harness, provider or model on failure unless the owner opted in per lane (escalation flags, off by
  default); the runner runs one lane per call and never switches on its own.
- GSD's own cross-AI execution runs a shell command under `run-with-timeout` with stdout redirected to a candidate
  summary. This runner is what gives that path exit codes, the `AIKIT-XAI` evidence line and heartbeats, so GSD and
  ai-kit lanes must use the same call vocabulary.
- jev and herdr only when available at the skill's runtime and never required; every path has a tested behavior
  without them.
- *(added 2026-11-16, re-run 2, owner directive "herdr hosting")*: where herdr is available at runtime (`HERDR_ENV=1` and the
  `herdr` CLI), the review and execute runner may always use it to open a tab or pane, start a lane in it and close what it
  opened when it is no longer needed. Never required: without herdr the headless path is unchanged and tested. This replaces
  "the runner never calls herdr" below with "the runner calls herdr only through one optional transport" (R12, D-22).

**Live facts checked for this spec (2026-11-16, this machine; claude 2.1.325, opencode 2.3.0, pi 1.5.2, cursor-agent
2026.11.13, codex 0.169.0, copilot 1.0.112, grok 1.0.52 *(grok superseded 2026-11-21, owner directive 2026-11-20: not a
cross-AI target; history only)*):**

- Today's runner (template 8, 12,840 lines; the rendered copy `.planning/scripts/cross-ai.mjs` is a pristine render,
  `tools/check_dogfood.py --skip-no-write` printed `ok`): `--runtime grok` *(superseded 2026-11-21: grok is not a target; the
  example stays as history of the parse gate)* fails with `unknown runtime: grok (known:
  cursor, opencode, pi, codex, claude, copilot)`; `--codex-effort max` fails with `must be minimal|low|medium|high|xhigh`;
  `--effort` and `--session-id` are `unknown argument`; `--runtime claude --mode exec` fails with `claude is review-only
  (no exec formula)`; `--model 'bad model'` fails the superset id charset at parse; `--print-argv` prints rung 1 (resume)
  and rung 2 (fresh) argv per runtime and exits 0 with no model call.
- Effort forms in each host's own `--help`: claude `--effort <level>` ("low, medium, high, xhigh, max"); codex `-c
  model_reasoning_effort=<x>`; pi `--thinking <off|minimal|low|medium|high|xhigh|max>` or a `:level` suffix on the
  model; cursor-agent a bracket on the model id (`[context=..,effort=..,fast=..]`, its own example); opencode
  `provider/model#variant` in `--model`; copilot `--reasoning-effort <none|minimal|low|medium|high|xhigh|max>` ("supported
  levels depend on the model"); grok `--reasoning-effort` (alias `--effort`; grok has no runner formula) *(superseded
  2026-11-21: grok is not a target; no form is recorded for it)*.
- Session forms in each host's own `--help`: pi `--session-id <id>` ("use the current directory's existing session with
  the ID, creating it otherwise"); copilot `--session-id <id>` ("resume an existing session or task by ID, or set the
  UUID for a new session"); claude `--session-id <uuid>` (a valid UUID for the conversation) and `--resume <id>`;
  opencode `--session <id>` ("session ID to continue, or to create if it does not exist"; the accepted id shape is
  unverified); cursor-agent `--resume [chatId]`; codex `exec resume <SESSION_ID>` (its resume form has no `--sandbox`
  flag); grok `--session-id` and `--resume` *(superseded 2026-11-21: grok is not a target; no session row for it)*. Resume behavior itself (that a second call continues the first) is
  verified by help text only; a live probe per installed host is unverified until recorded.
- Execute-permission flags of claude: `--permission-mode` (choices acceptEdits, auto, bypassPermissions, manual,
  dontAsk, plan) and `--dangerously-skip-permissions` ("recommended only for sandboxes with no internet access");
  the runner's review formula already uses `--permission-mode plan`. No execute formula exists.
- Existing code: the runner already resumes inside one run (`sameSessionArgv`, rung 1) and across runs through the
  quota-cycle record's `last_sid`; pi's id is chosen by the runner (`ctx.sid`), cursor, opencode, codex and claude mint
  theirs and the row's `parse` reads them; the status line has no session field. `runner_dispatch.py` builds the call
  (`RunnerSpec`, `runner_flags`) and passes effort only for codex; `build_reviewer_model_id` composes cursor brackets
  in Python for the `build-model-id` subcommand. There is no `--describe`, so Python mirrors the runner's tables
  (`RUNTIMES` in `detection.py`, `_MODEL_ID_SRC`, Phase 36's planned `exec_formula`). The sync check of the live copy
  exists only as `tools/check_dogfood.py` `check_runner_copy` (the one reader of `.planning/`); no unit test renders the
  template and compares it.

**Live facts added 2026-11-16 (re-run 2, herdr 0.9.5, `HERDR_ENV=1`, opencode 2.3.0; probes in a tab labeled `aikit-live37`,
closed after each run; the probe scripts and outputs are under `tmp/spec-discuss-35-39/`, not committed):**

- `herdr tab create --label <l> --no-focus --cwd <dir> --env K=V` returns JSON with `.result.tab.tab_id` and
  `.result.root_pane.pane_id`; `herdr pane run <pane> <line>` returns at once with empty output (admission only);
  `herdr tab close <tab>` returns `{"result":{"type":"ok"}}` and ended a running child (an `sh` launcher with a `sleep` below it:
  the `sleep` process was gone 1.5 s later). Detached grandchildren that leave the process tree were not tested (unverified).
- A pane has no exit code. `herdr pane wait-output <pane> --regex <re> --timeout <ms>` returns `matched_line` and the screen text;
  a regex ending in digits (`rc=[0-9]+`) does not match the typed command line that holds `rc=$?`, but a literal `--match` matched
  the typed command line itself (first live check). A timeout is exit 1 with a JSON error `timeout` on stderr. A launcher script run
  as `sh <path>` with stdout and stderr redirected to files and an exit-code file gave the exact exit code (7), both streams
  separately, a prompt delivered on stdin from a file, and the `--env` variable, all verified.
- `herdr agent prompt <agent> <text> --wait` returned in 0.8 s with only the agent's lifecycle record (`agent_status`), never the
  reply text; the status read `blocked` after the prompt although the screen showed no dialog, so `blocked` is ambiguous (a
  recognized approval or question UI, or an error). `herdr agent read` returns the rendered screen text. opencode 2.3.0's TUI has
  no `--model` flag (`herdr agent start ... -- --model x` printed `Unrecognized flag: --model` and timed out after 45 s with no
  agent); `opencode run` has it. `herdr agent start ... -- --session <id>` attached the TUI to an existing session in 3 s.
- opencode accepted a caller-chosen session id of the form `ses_` plus 16 letters or digits on a headless call (the events
  echoed it, the TUI then attached to that session; the shape rule is the host's and other shapes are unverified), which
  narrows D-03's open question for opencode (the planning spike still decides).
- A free opencode lane has reached its limit on this machine today: headless `opencode run --format json` ended in 0.4 s with
  exit 1 and a JSON event `{"type":"error","error":{"type":"provider.free-limit","status":429,"retryAfterMs":24229000,...}}` and the
  message `Free usage limit reached. Connect a provider or subscribe ... or switch models.` (about 6 h 44 min, longer than the
  4-hour hard tier). Phase 38.1's note that no free lane had reached its limit is therefore out of date (handoff to 38.1, 40).

**Amended 2026-11-21 (plan time).** Sources: the owner's requests of 2026-11-19 (skills handed to cross-AI lanes; MCP servers
for review and execution lanes) and the owner's directive of 2026-11-20 (grok is not a cross-AI target; Phase 39.1 removes the
runtime, RUN-15), recorded in the run's request notes; owner-directed, so decided here, not asked (37 D-31 to D-34 in
`37-CONTEXT.md`). Phase 37 builds only the runner side; which skills and servers a lane gets, by role and task kind, stays Phase
39's (REV-03, REV-05).

- R13 is added: the runner records, per host, how a lane can be handed a skill (by name, by path, or as inlined prose), each
  form with a source label, delivers what the caller passes in the best form the host has, and reports each skill like any
  setting. R14 is added: the runner passes MCP servers from a run-scoped file the caller writes, through the host's
  per-invocation form only, and reports each server. Both extend RUN-01 (a dated note there); the REQUIREMENTS total is unchanged.
- Live help facts for R13 and R14, read on 2026-11-21 from the installed hosts' own `--help` (read-only, no model call, no host
  config file read; claude 2.1.330, codex 0.170.0, opencode 2.3.2, pi 1.5.2, copilot 1.0.112, cursor-agent 2026.11.13):
  - Skills. pi `--skill <path>` ("Load a skill file or directory (can be used multiple times)") beside `--no-skills` ("Disable
    skills discovery and loading"); that an explicit `--skill` still loads under `--no-skills` is from pi's own docs (Phase 39's
    live facts). claude: "Skills still resolve via /skill-name" appears only inside the `--bare` text, and `--add-dir`
    ("More directories Claude can access") and `--plugin-dir` (a plugin, not a skill) name no skill loading. copilot:
    `--add-dir <directory>` "load its .github/skills and .github/agents as trusted configuration", and `copilot skill --help`
    lists discovery roots (`.github/skills/`, `.agents/skills/`, `.claude/skills/`, `~/.copilot/skills/`, `~/.agents/skills/`)
    with no per-invocation load-by-name form. cursor-agent (`--add-dir` a workspace root, `--plugin-dir` a plugin), codex
    (`--add-dir` a writable directory) and opencode (`run --file` attaches a file to the message) name no skill form. Prose
    needs no host form: the runner already sends the prompt on stdin (copilot: as the `-p` argument, under the existing
    `ARGV_PROMPT_MAX` check); claude and pi also list `--append-system-prompt`, recorded as a fact and not used.
  - MCP servers. claude `--mcp-config <configs...>` ("Load MCP servers from JSON files or strings") and `--strict-mcp-config`
    ("Only use MCP servers from --mcp-config, ignoring all other MCP configurations"); copilot `--additional-mcp-config <json>`
    ("JSON string or file path (prefix with @) ... augments config from ~/.copilot/mcp-config.json for this session"), plus
    `--disable-mcp-server`, `--enable-mcp-server` and `--disable-builtin-mcps`; pi `--no-mcp` only turns MCP off, and `pi mcp
    --help` says servers come from `~/.pi/agent/mcp.json` and, in trusted projects, `.pi/mcp.json` (the runner passes
    `--no-approve`); cursor-agent `--approve-mcps` only approves servers from `.cursor/mcp.json` or `~/.cursor/mcp.json` (its
    `mcp --help`); codex has an `mcp` subcommand and a generic `-c key=value` override of `~/.codex/config.toml` whose help names
    no MCP key; opencode has an `mcp` subcommand and no flag on `run`. The help facts of the owner's note of 2026-11-19 (claude
    2.1.328, codex 0.170.0, opencode 2.3.2, pi 1.5.2, copilot 1.0.112, cursor-agent 2026.11.13) hold unchanged on these versions.
  - Existing runner behavior these touch (template on this branch): pi's exec and review formulas pass `--no-skills`, its review
    and `none` profiles add `--no-mcp`, and `reviewExtras` already admits `--skill` from `CONFIG.extraArgs`; cursor's exec formula
    passes `--approve-mcps`, so an execute lane approves every server in the user's cursor config today; copilot's review profile
    passes `--disable-builtin-mcps`; opencode's env sets `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`.
- Grok is not a cross-AI target (owner directive 2026-11-20): the grok host in the live-facts lists above and the grok example in
  R4 are superseded history, marked in place. This phase adds no grok work: no help fixture, form, probe, session row, test or
  list entry, including in any recorded-help fixture list that a later unit's amendment to this phase names. Existing grok code
  (the detection row, `build_grok_command`, the runner's one mention, `cursor-agents/grok-worker.md`) is left alone; Phase 39.1
  removes the runtime (RUN-15).
- Free-lane pools (Phase 36 wrote `pool = "<provider>:free"` on zero-price lanes, 36 D-20 to D-22): this phase's text names no
  pool and adds none; the runner treats a pooled lane like any other.

**Findings (existing code paths that gate on a table; this phase removes the runner-side ones):**

- `cross-ai.mjs` `parseArgs`: `unknown runtime` (5321), `unknown cli` for `--prefer`, `--model-<cli>`, `--route-<cli>`
  (5326-5327), the superset id charset (5276, 5284); `resolveRuntime`: `unknown runtime` from CONFIG (5352, 5357);
  `runClassifyOnly`: `unknown cli` (5386); `main`: the per-runtime `modelId` gate (12583) and the `review-only` exec
  refusal for a null `exec` (12597); the closed effort sets `CODEX_EFFORTS` and `PI_THINKING` (5254-5255).
- `runner_dispatch.py`: `model_id_ok` and `_MODEL_ID_SRC` (the per-runtime grammar mirror), `project_runner_command`
  (returns `None` outside `SUPPORTED_EXECUTE_CLIS`), `runner_flags` (effort for codex only).
- Kept on purpose, because they are the runner's own vocabulary or a host flag's own value domain and not a verdict
  about a runtime: `--tools-profile exec|review|none`, `ROUTE_VALUES` (router, unknown), `CURSOR_MODES` (ask, plan, the
  values of cursor's own `--mode`), the status vocabulary and exit codes.

## Requirements

1. **One call vocabulary (RUN-01)**: a call names its settings with plain flags that a word-split GSD hook string can
   carry, and the Python layer builds the same flags.
   - Current: the runner takes `--runtime`, `--model`, `--mode exec|review`, `--codex-effort`, `--cursor-mode`; it has no
     generic effort, context, escalation, role or session flag, and `runner_flags` passes effort for codex only.
   - Target: new flags `--role review|execute` (the documented name; `--mode review|exec` stays an alias, and a call whose
     two values disagree is a usage error with exit 2), `--effort <level>` (generic; `--codex-effort` stays an alias and a
     call giving both with different values is a usage error), `--context <label>`, `--escalate-runtime` and
     `--escalate-model` (valueless booleans), `--session-id <id>` (R7). The provider is not a flag: it is the id prefix of the
     runtimes whose id form has one (pi, opencode) and is reported as a setting (R2). `RunnerSpec` gains `role`, `context`,
     `escalate_runtime`, `escalate_model` and `session_id`; `runner_flags` emits every named setting for every runtime (no
     runtime-specific branch for effort), reading the lane through `lane_escalation` (Phase 36 R5). An unset setting emits no
     flag. Hook tokens still pass `HOOK_TOKEN_RE`.
   - Acceptance: tests parse each flag and each conflict (role against mode, effort against codex-effort, a valued
     escalation flag); golden `runner_flags` output for a lane per runtime; a hook string for each runtime holds only allowed
     tokens; `build-command` and the hook builder emit the same flags for one lane.

2. **Every named setting is reported as applied, ignored or unknown (RUN-01)**: the runner says what it did with each.
   - Current: a setting a runtime cannot take is dropped without a line (for example `CONFIG.effort.pi` skipped on a `:level`
     suffix), and no line says what a call applied.
   - Target: before the runtime is spawned the runner prints one stderr line per named setting, `cross-ai: setting
     <name>=<value> <state> [reason=<code>]`, and always one for `model` and `role`. The names are `model`, `provider`,
     `role`, `effort`, `context`, `session`, `escalate_runtime`, `escalate_model`. `applied` means the value reached the
     runtime (a flag, or inside the model id the runtime receives); `ignored` means it was named and not fed, with a reason;
     `unknown` means the runner cannot tell (a custom command's provider, a provider on an id form with none). The reason
     codes are a closed list with a locking test: `no_form` (the runtime has no flag or id form for it), `id_carries` (the
     model id already holds it and wins), `unverified_form` (a form is known but unverified and is not fed), `mode_forbids`
     (the role's confinement forbids it, for example a session resume in codex review), `no_slot` (a custom command has no
     placeholder for it), `recorded_only` (escalation flags), `no_provider_form` *(amended 2026-11-16, 38.1 D-30: and `bad_value`,
     a context label outside the form's value kind)*. The last stderr line gains `session=<id|->`
     and the name lists `applied=`, `ignored=`, `unknown=` (comma lists, `-` when empty) beside the existing fields;
     `--print-argv` prints the same report. A setting the call does not name is not reported (except `model` and `role`).
     A runtime that takes no model flag, or no effort, is never fed one.
   - Acceptance: fake-CLI tests show, per runtime, an applied effort, an ignored effort with its reason, an `id_carries`
     case (cursor and opencode id with its own value, pi `:level`), a context ignored with `no_form`, an escalation pair
     `recorded_only`, a provider derived for pi and `no_provider_form` for codex; a locking test fails when the runner emits a
     reason outside the list or the list and the SKILL.md table differ; the status line parses with
     `parse_status_line` and `_trailer_counts` unchanged.
   - *Amended 2026-11-16 (37 D-28, R12):* a ninth setting name `host` (applied, or ignored with `no_herdr` or `host_failed`) and
     two reasons join the closed list; the status line and its group are unchanged.
   - *Amended 2026-11-16 (38.1 D-17, D-30, owner directive HOST SETTINGS FORMS):* the per-host context forms are recorded with
     labels, checked live (claude 2.1.325, codex 0.169.0, copilot 1.0.112, cursor-agent 2026.11.13, opencode 2.3.0, pi 1.5.2,
     grok 1.0.52, 2026-11-16): copilot `--context <tier>` (`default` or `long_context`, verified from its help; the earlier
     "unknown" is stale), codex `-c model_context_window=<integer tokens>` (key verified by the config parser, effect on a model's
     window unverified), cursor's bracket `context=` key (verified help example, per-model meaning unverified), claude none in its
     help (`--autocompact` is the auto-compact window, not the context size; the `[1m]` suffix stays unverified), opencode, pi and
     grok none. A context label outside a form's value kind is `ignored` with `bad_value`. Every flag a row's effort, session or
     context form uses must appear in that host's recorded help (`tests/fixtures/cli_help/<host>.txt` with version and date for
     claude, codex, cursor-agent, copilot, opencode, pi and grok); Phase 35's opencode-only help-fixture test is extended to
     every host, a planted stale flag and a host with no recorded help both fail it. This phase's plan executes it (it adds the row
     fields and `--describe`); the forms record how to pass a setting, never what a model supports.
     Acceptance: the help-fixture test over every host; a stale flag, a missing record and an out-of-kind label each fail;
     `--print-argv` shows copilot's and codex's context forms applied and a cursor bracket merge as before.

3. **Effort in each runtime's own form, decided in the runner, no closed level sets (RUN-01; takes Phase 36's handoff)**.
   - Current: codex takes `--codex-effort` against a closed set (`minimal` to `xhigh`, so a listed `max` or `ultra` is
     refused); pi takes `--thinking` from the baked `CONFIG.effort` against another closed set; claude and copilot have no
     path; cursor and opencode only through a model id composed elsewhere (Python `build_reviewer_model_id`).
   - Target: the runner composes the form from `--effort` (and `CONFIG.effort` as the default beneath the call): claude
     `--effort <level>`, copilot `--reasoning-effort <level>`, codex `-c model_reasoning_effort=<level>`, pi `--thinking
     <level>`, cursor a `[effort=<level>]` bracket merged into the id's own bracket, opencode a `#<variant>` suffix. An effort
     the model id already carries wins and is reported `id_carries`. A level is checked for shape only (`^[a-z][a-z0-9_-]{0,15}$`,
     no leading dash, no whitespace or control character) and never against a per-runtime set; the host rejects what it
     cannot take, and that failure is classified and reported by the existing rules. The levels the owner is offered come from
     the catalog and listings (Phases 35, 36). Each form carries a source label in the runner's seed data (verified with the
     date and the help line it came from, or unverified). The Python composers for the same ids (`build_reviewer_model_id`,
     `build_cursor_agent_model_id`) are deleted once the `build-model-id` subcommand and Phase 36's wizard preview read the
     runner's `--print-argv` instead, so one place holds each form.
   - Acceptance: argv tests per runtime with a dry run (`--print-argv`) for one level each, for codex `max` and `ultra`
     passing, for an uppercase, spaced, dash-leading or empty level refused with exit 2, for an id-carried effort winning,
     for cursor's bracket merging with an existing `context=` key without losing it, and for `CONFIG.effort` yielding to the
     call; a grep-style test that no Python module composes an effort into a model id; an old hook string with
     `--codex-effort` behaves as before.

4. **An unknown runtime with a declared command, and a named reason without one (RUN-01)**.
   - Current: a runtime outside the runner's table is refused at parse and in `resolveRuntime`, a `--prefer`, `--model-<cli>`
     or `--route-<cli>` naming one is refused, `--classify-only` refuses an unknown cli, and a claude or grok lane has no way
     in at all *(grok superseded 2026-11-21: not a target; an argv-file lane serves any unknown command, and no grok test,
     fixture or example is added)*.
   - Target: no parse-time refusal cites the table. `--runtime <id>` for an id with no formula needs `--argv-file <path>`:
     a JSON array of argv strings (read like `--prepend-file`, relative to the cwd, capped in size, parsed with a strict
     reader) in which `{model}`, `{effort}` and `{session}` are the only placeholders; the prompt goes on stdin. The runner
     supervises it like any lane (process group, deadlines, heartbeats, redaction, the tree check in review role, the status
     line, the generic error rows that apply to any cli). A setting whose placeholder is absent is `ignored` with `no_slot`,
     one whose placeholder is present is `applied`, and the provider is `unknown`. Without `--argv-file`, an id with no formula
     is refused with exit 2 and a named fact (`no formula for <id> in the runner; pass --argv-file, or use a runtime it has a
     formula for`), not a list of known runtimes as a verdict. `--prefer`, `--model-<cli>` and `--route-<cli>` accept any
     `[a-z0-9-]+` name; only the selected runtime's value is read. `--classify-only` classifies an unknown cli with the rows
     that match every cli. The Python custom launcher (`run_custom_command`) is unchanged here; routing custom lanes through
     the runner is a handoff to Phase 40.
   - Acceptance: tests with a fake CLI declared only through an argv file serve review and execute (status line, exit codes,
     tree check, an applied and an ignored setting each); an unknown id with no file gets the named refusal; a path outside
     the cwd tree, a non-array, a non-string element, an unknown placeholder and an oversize file are each refused with a
     named usage error; `--classify-only` on an unknown cli returns the generic class.

5. **The model id gate becomes a safety floor (RUN-01)**.
   - Current: each runtime row has a `modelId` grammar and `main` refuses a call whose id does not match (exit 2), with
     the grammars mirrored in Python (`_MODEL_ID_SRC`, `model_id_ok`).
   - Target: one universal floor stays a refusal: the id is non-empty, has no leading dash (read as an option), no
     whitespace and no control or shell character (the existing charset minus nothing it needs). The per-runtime shapes
     become a printed advisory (`cross-ai: note: model id shape is unusual for <runtime> (seed shape: <source>)`) that never
     refuses, and a live listing check that succeeded and does not list the id still stops with `bad_model` (live evidence).
     `model_id_ok` and `_MODEL_ID_SRC` are removed from Python with the grammar mirror; callers use the floor.
   - Acceptance: tests show an id of an unusual shape for each runtime reaching the spawn with the advisory printed, a leading
     dash, a space and a control character refused, a listing that omits the id still giving `bad_model`, and no Python module
     naming a per-runtime grammar.

6. **claude learns an execute formula, labeled unverified until a live probe (RUN-01; takes Phase 36's handoff)**.
   - Current: `claude` has `exec: null` and `resume: null`; a claude execute lane is refused with `review-only`.
   - Target: the runner's claude row gains an execute formula in the form the other execute runtimes use (headless print
     mode, JSON output, the runtime's own full-permission flag, the model, effort and session forms of R3 and R7), and a resume
     formula (`--resume <id>`). The permission flag is chosen at planning from the two live candidates
     (`--permission-mode bypassPermissions` or `--dangerously-skip-permissions`) by a probe in a scratch repository. Until that
     probe is recorded, the row's source label reads unverified, the runner prints that note on every execute call, and the
     existing `errorsUnverified` treatment applies. The review formula is unchanged.
   - Acceptance: `--print-argv` shows the claude execute and resume argv; a fake claude serves an execute call with a commit and
     a resume call; a test pins the unverified label and its note until the probe record exists; the review argv is byte-equal to
     today's.

7. **A session id in and out, and a second round that resumes (RUN-02)**.
   - Current: sessions resume only inside a run (retry rung 1) and through the quota-cycle record; a caller cannot name one and
     the status line does not print the one used.
   - Target: `--session-id <id>` (charset `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`) runs the call inside that session of the selected
     runtime. Each row says how its host takes ids: `chosen` (the caller's id with one create-or-continue flag: pi, copilot) or
     `minted` (the host creates ids and the row's resume formula continues one it printed: cursor, opencode, codex, claude). A call
     without an id starts a fresh session as today. For a `chosen` host the runner uses the given id, or a generated UUID when none
     is given. Every run prints `session=<id>` in the status line: the id used, or the id the host minted, or `-` when the host
     printed none. On a resume the call's own prompt is the next message (the interruption text is for the retry rung only). An id
     the host rejects is a failed call with the host's first error line, never a silent fresh session. A role or option with no
     resume form (codex review, which has no read-only flag on `exec resume`, and a codex execute call with `--codex-sandbox`)
     starts a fresh session, prints the new id and reports the setting `ignored` with `mode_forbids`. An explicit id wins over the
     quota-cycle record's `last_sid`, and the record keeps the id actually used. Reviewers start fresh by default and executors
     opt in: the runner only provides the capability, and the review loop and the execute adapter adopt it in Phases 40 and 41.
   - Acceptance: a fake CLI per runtime shows the first call printing `session=X` and a second call with `--session-id X` building
     the resume or create-or-continue argv for that host and reaching the same fake session (fake sees the same id); a rejected
     id fails with the host's line and starts nothing; codex review and sandboxed codex execute print `mode_forbids`; an explicit id
     beats a stored `last_sid`; a call with no id prints a session for pi (generated) and `-` for a host that prints none.

8. **A test keeps the rendered copy in sync with the template (RUN-06)**.
   - Current: only `tools/check_dogfood.py` compares the live `.planning/` copy with the template; no unit test renders the template
     and compares, and a test may not read `.planning/`.
   - Target: a unit module renders the shipped template through the curated-config render path into a scratch project (the same
     `ensure_runner` the installer uses), and asserts that the result is `pristine`, carries the template's version and holds the
     same bytes as the template outside the config block; it then runs the template and the rendered copy through the same
     `--print-argv` matrix (one call per runtime and role, plus an effort, a session and a custom-file case) and requires equal
     output, so a render that corrupts code is caught behaviorally too. A one-byte edit outside the config block fails it
     (non-vacuity). `check_dogfood.py` stays the live-copy check; the new test reads no `.planning/` path. Phase 38 later removes
     the long self-test from rendered copies and relaxes the byte comparison to the part the render keeps. *(amended 2026-11-16,
     38 D-19: the harness leaves the runner file for a sibling file the render does not carry, so a rendered copy stays the
     template's bytes with the config block replaced and nothing is relaxed)*
   - Acceptance: the module passes on the shipped template, fails on a copy with one changed byte outside the config block, fails
     on a copy whose config block hides a code change, and passes after a config-only edit.

9. **The Python layer asks the runner, and the table mirrors go (RUN-01; takes Phase 36's handoff)**.
   - Current: Phase 36 mirrors the runner's exec formulas in a Python `exec_formula` field with a drift test and routes a runtime
     without one as `no_formula`; `routing.py` also has `unknown_runtime` (not in the table) and `no_inventory`.
   - Target: `cross-ai.mjs --describe` prints, with no model call, one JSON object: per runtime the formulas present (exec,
     review, resume), the listing command, the session style, the effort form, and a source label on each (verified with date or
     unverified). Runtime detection (spec-config Step 1) records it in the runtimes snapshot next to the listing facts. Routing
     reads that recorded fact: a runtime the snapshot says has no exec formula and no command routes `no_formula` (a named fact);
     an absent or unreadable fact never refuses, and the runner itself refuses with its own named reason at run time. `exec_formula`
     and its drift test are deleted; `unknown_runtime` and `no_inventory` stop refusing at routing (the former is the runner's named
     refusal of R4, the latter is `unverified`, since a host that cannot list models is a fact about verification, not a veto).
     `SUPPORTED_EXECUTE_CLIS` and `execute_cli_error` read the recorded fact, and the grep-style test of Phase 36 R7 extends to
     the new routes.
   - Acceptance: tests with a fixture snapshot cover a runtime with a formula, one without (`no_formula`), an absent fact (not
     refused), a runtime outside the table with a command (served), and `--describe` offline output matching a golden file whose rows
     carry source labels; the drift test and the `exec_formula` field are gone and no Python module mirrors a runner formula.

10. **Escalation flags are carried and reported, never acted on (RUN-01)**.
    - Current: no flag reaches the runner; Phase 36 stores the booleans and `lane_escalation` reads them.
    - Target: the runner accepts `--escalate-runtime` and `--escalate-model`, reports each as `recorded_only`, and adds
      `escalate=<runtime,model|->` to the status line so a caller sees what the owner allowed; the runner never starts another lane
      and the existing "no automatic fallback" notice stays. `runner_flags` reads the lane's flags only through `lane_escalation`,
      and no ranking, proposal or default sets one (Phase 36's test covers the source side).
    - Acceptance: tests show both flags reported and echoed, a failing call that carries them still ending after one lane with the
      same exit codes and no second spawn, and the flags absent when the lane has none.

11. **Skill text, docs, the cleanup of the runner file's examples and the judge bar (JDG-04, HUB-09)**.
    - Current: `ai-kit-cross-ai` (76.8 C at the Phase 32 baseline) and the runner docs describe flags and a status line without
      the new fields; the runner carries example model names and decision-making id and effort sets.
    - Target: `skills/ai-kit-cross-ai/SKILL.md` documents the vocabulary, the settings report, `session=`, `applied=`,
      `ignored=`, `unknown=` and `escalate=`, how to read them, and the argv-file lane; `references/cross-ai-dispatch.md`,
      curated-config `references/runner.md` and the READMEs match. The runner's marked examples carry the guard's `model-example:`
      marker and no code outside the self-test harness names a provider or model, and no list in the runner decides (the
      self-test entries stay in Phase 38's baseline). `ai-kit-cross-ai` reaches the judge bar here (new-shape evals and tests, no
      critical or high finding or grade B or better, no regression beyond variation), as the 32.1 amendment requires of the first
      of Phases 37-38 to change it. Optional helpers are conditional: the runner never calls jev or herdr (stdlib-only, rendered
      into projects) *(amended 2026-11-16, 37 D-22: the runner never calls jev; it calls herdr only through the optional hosting
      transport of R12, which a missing herdr leaves at the headless path)*; a calling skill may use herdr to watch a long lane or to drive a host for the live resume check and jev to
      size or classify, each only when present at its runtime, and the documented path without them is the one tested.
    - *Amended 2026-11-16 (37 D-22 to D-28, R12):* the skill text, `cross-ai-dispatch.md`, `runner.md` and the READMEs also document
      `--host`, `AIKIT_HOST`, the `host` setting with its two reasons and the hosted lane's run directory; the doc-contract tests pin them.
    - Acceptance: the judge loop for `ai-kit-cross-ai` ends with no critical or high finding or a B or better (recorded in
      37-VERIFICATION.md); doc-contract tests pin the new fields and the closed reason list in the SKILL.md; the hardcoding guard
      passes on every file this phase rewrites; `make test` passes.

12. **Optional herdr hosting of a lane (RUN-12; added 2026-11-16, re-run 2, owner directive)**: where herdr is available, the runner
    runs a lane's process in a tab it opens and closes that tab when the lane ends, and the lane's command line, settings,
    session id, classification and exit codes are identical to the headless run.
    - Current: the runner spawns every lane as a detached child with piped output and never calls herdr (D-20 as locked on
      2026-11-16 before the directive); a calling skill may drive herdr by hand.
    - Target: a call flag `--host auto|none`, default `none` (so an old hook string or rendered copy behaves as before); the Python
      layer and the hook builder emit `--host auto` by default, and the environment variable `AIKIT_HOST` (`auto` or `none`) is
      read when the flag is absent; `none` from either source wins over `auto`, which is how the owner switches hosting off
      (a shell profile makes it persistent); no config key records it. Availability is `HERDR_ENV` equal to `1` and a `herdr`
      executable on PATH, checked without calling herdr. Unavailable or switched off: the lane runs headless as today and a named
      `host` setting is reported `ignored` with `no_herdr` (`host=none` is reported `applied`). Available: the runner creates a run
      directory `<state home>/ai-kit/spec/host/<run token>/` (mode 0700) holding a POSIX `sh` launcher built from the lane's argv with
      single-quote quoting, the lane's environment as an env file (mode 0600), the prompt as a file (mode 0600, read on stdin), and
      the launcher's `out`, `err`, `pid` and `rc` files. It opens one tab with `herdr tab create --label aikit:<role>:<runtime>:<run
      token> --no-focus --cwd <lane cwd>`, reads the tab and pane ids from the JSON, and types `sh <launcher path>` with `herdr pane
      run`; the typed line holds only that path. The runner polls `out`, `err` and `rc` through the same capture buffers, size cap,
      heartbeats, idle clock and redaction as a piped child; `rc` (written by rename after the lane exits) is the only source of the
      exit code, and herdr's screen text, agent status and wait commands are never read as a verdict. A launcher that is gone with no
      `rc` ends the lane as killed by a signal. The runner closes the tab it opened, by id, on every exit path (finish, deadline, signal,
      spawn error), removes the run directory after closing, and never closes or reads any other tab or pane. A herdr call that fails
      before the launcher is typed reports `host` `ignored` with `host_failed` and runs the lane headless once; a failure after that
      never reruns the lane. Interactive agent TUIs, TUI apps, e2e runs and pane reuse across calls are not runner transports: they are
      the calling skills' and Phase 42's.
    - Acceptance: tests with a fake `herdr` on PATH (it replays the JSON shapes recorded live and runs the typed line) show a hosted
      call and a headless call giving the same argv, settings report, session, status line and exit code for success, a host error and
      a timeout; `--host none`, `AIKIT_HOST=none` over `--host auto`, no `HERDR_ENV` and no `herdr` on PATH each run headless with the
      right line; a fake that fails `tab create` gives `host_failed` and one headless run; a fake that fails after the line was typed
      never spawns a second lane; the tab is closed by id on every exit path and a second tab in the fake is never touched; the run
      directory and env file modes are pinned and the directory is gone after the call; a planted key shape in the env file never
      reaches stderr, the status line or the typed line; a hostile argv element (quote, newline, dollar, backtick) reaches the lane intact;
      `--print-argv` prints the `host` line without calling herdr; a locking test pins `host`, `no_herdr`, `host_failed` in the
      closed list.

13. **A lane is handed the skills the caller names, in the best form its host has (RUN-01; added 2026-11-21, plan time, owner
    request of 2026-11-19, 37 D-31, D-32)**: the runner records how each host takes a skill and delivers what the call passes.
    - Current: the runner has no skill input; pi's formulas pass `--no-skills` and only a hand-set `CONFIG.extraArgs` entry can add
      `--skill` (admitted by `reviewExtras`); no row records how a host takes a skill, and execute lanes get none.
    - Target: two repeatable call flags, `--skill-path <dir>` (a skill directory holding `SKILL.md`, resolved through symlinks,
      with no control character in the path; the repository-or-skill-root check is the caller's validator, Phase 39 R8) and
      `--skill-name <name>` (a skill the caller's table says is installed on this lane's
      host; name shape `^[a-z0-9][a-z0-9-]{0,63}$`). The runner never chooses a skill (Phase 39 does) and never scans a host. Each
      runtime row gains a `skills` field with three forms, each with a source label (verified with the host version, date and help
      line; documented with its source; or unknown) and a state (`verified`, fed; `unverified`, recorded and not fed; `unknown`,
      no form): `name` (the host loads an installed skill when the prompt names it), `path` (a flag loads a skill file or directory
      for this call) and `prose` (the skill's `SKILL.md` text inlined). Seed rows from the 2026-11-21 help read: pi path `--skill
      <dir>` verified, name unknown and in any case reported `mode_forbids` (its formulas pass `--no-skills`); claude name `/<name>` unverified (help states it only
      inside the `--bare` text), path unverified (`--add-dir` names no skill loading); copilot name unverified (help lists
      discovery roots, no load-by-name form), path unverified (`--add-dir <dir>` loads `<dir>/.github/skills`, which needs a
      directory layout whose effect is untested); cursor-agent, codex and opencode name and path unknown. Prose is the runner's own
      form on every runtime: one delimited block per skill (its name, path and sha256, the `SKILL.md` body byte-equal) placed
      before the `--prepend-file` content and the prompt, in call order; on copilot it rides the `-p` argument under the existing
      `ARGV_PROMPT_MAX` check. Per skill (a name and a path whose directory name or frontmatter `name` match are one skill) the
      runner applies the first form in the owner's order name, path, prose that the row has `verified` and the input supplies:
      a name only with `--skill-name`, a path or prose only with `--skill-path`. Two new setting names join R2's list, `skill`
      and (R14) `mcp`; each skill prints one line, `cross-ai: setting skill=<name> applied form=<name|path|prose>` or `ignored
      reason=<code>` with the closed reasons `no_form` (unknown form), `unverified_form`, `mode_forbids` and, on an `--argv-file`
      lane, `no_slot` for a name (prose still applies there, on stdin). The state is computed after the argv and the prompt prefix
      are built, from them, never from the request; `--print-argv` prints the same lines, and Phase 39's capabilities line reads
      them. `--describe` lists each row's three forms with label and state. A missing directory, a directory without `SKILL.md`,
      a path with a control character, a body that is not strict UTF-8 or over the size cap (one cap, set by the plan, for every
      file the runner reads for a call: the argv file, a skill body, the MCP file), and a name of the wrong shape are usage
      errors (exit 2) naming the flag. A form flips to `verified` only through a recorded help line, a
      documented source or the planning spike, with the help fixtures of this phase covering every flag a form uses.
    - Acceptance: `--print-argv` tests per runtime and role: pi with `--skill-path` adds `--skill <dir>` and reports `applied
      form=path`; claude, copilot, cursor-agent, codex and opencode with `--skill-path` leave the argv unchanged, put the delimited
      block in the prompt and report `applied form=prose`; a `--skill-name` alone reports `ignored` with `unverified_form` (claude,
      copilot), `mode_forbids` (pi) or `no_form` (the others) and adds nothing; a name and a matching path on pi report one line
      with `form=path`; an `--argv-file` lane reports `no_slot` for a name and `form=prose` for a path; the inlined block is
      byte-equal to the file body; each usage error is named; a copilot prompt pushed over `ARGV_PROMPT_MAX` by a block gets the
      existing refusal; the locking test of R2 covers the two new names; the help-fixture test fails when a `verified` form's flag
      is missing from that host's recorded help.

14. **A lane gets the MCP servers the caller names, only through its host's per-invocation form (RUN-01; added 2026-11-21, plan
    time, owner request of 2026-11-19, 37 D-33)**: the runner never enables a server on its own and never edits a host's config.
    - Current: nothing enables a server for a lane; host-config servers load or not by each formula's flags (pi review `--no-mcp`,
      copilot review `--disable-builtin-mcps`, cursor exec `--approve-mcps`, the rest the host's default), and no line reports it.
    - Target: one call flag, `--mcp-config <file>`: a run-scoped JSON file the caller writes (`{"mcpServers": {<name>: {...}}}`),
      read once (strict UTF-8 JSON, the size cap of R13, a regular file not readable by group or others because it may
      hold a key; server names of shape `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`) and never written. Without the flag no server is
      added and every argv is byte-equal to the R1 to R12 argv. Each runtime row gains an `mcp` field: the per-invocation form with
      a source label and state, or none. Seed rows from the 2026-11-21 help read: claude `--mcp-config <file> --strict-mcp-config`
      verified (strict, so only the given servers load; the variadic `--mcp-config` is always followed by another flag);
      copilot `--additional-mcp-config @<absolute file>` verified (it augments the user's own copilot servers; no strict form);
      codex `unverified` (a generic `-c` override exists, no MCP key in its help, and it would put server arguments on argv);
      pi, cursor-agent and opencode none (a config file only: pi's own `mcp.json`, cursor's `mcp.json`, opencode's config). Only
      the file path reaches argv, never the JSON (copilot's JSON-string form is not used). Each server prints one line,
      `cross-ai: setting mcp=<name> applied` or `ignored reason=<code>`: `no_form` (a host with a config file only), `unverified_form`
      (codex), `mode_forbids` (a review profile that turns MCP off, pi `--no-mcp`), `no_slot` (an `--argv-file` lane). The state is
      read from the final argv; a review lane keeps its confinement flags and the tree check, whatever tool changed the tree. The
      runner never prints a server's command, arguments, environment, URL or headers (names only, redacted), never writes or reads
      a host config file, and never adds an approval flag a formula lacks. Which servers a task kind needs (a docs or browser
      server for a frontend task, the code index for exploration), read-only by default, is the caller's choice (Phase 39).
    - Acceptance: `--print-argv` tests: claude review and execute with a two-server file add `--mcp-config <file>
      --strict-mcp-config` and report both `applied`; copilot adds `--additional-mcp-config @<file>` and keeps
      `--disable-builtin-mcps` in review; pi exec reports `no_form`, pi review `mode_forbids`, codex `unverified_form`, cursor-agent
      and opencode `no_form`, each with an unchanged argv; no flag gives byte-equal argv; a group-readable file, a non-object,
      a bad server name, invalid UTF-8 and an oversize file are named usage errors; a planted key shape in a server's `env` or
      `args` appears in no stderr line, status line or argv; a test with a fake host config directory shows it untouched.

## Boundaries

**In scope:**
- The call vocabulary and the settings report (R1, R2), effort forms in the runner (R3), unknown runtimes with a declared
  command and the named refusal (R4), the model id floor (R5), the claude execute formula (R6), session ids (R7), the sync test (R8),
  `--describe` and removing the Python table mirrors (R9), escalation flags carried (R10), skill text, docs, the runner's example
  cleanup and the judge bar (R11), the optional herdr hosting transport (R12, added 2026-11-16). *(amended 2026-11-21, plan
  time: also the per-host skill forms and the delivery of the skills a call names (R13), and the per-invocation MCP server
  forms and the delivery of the servers a call names (R14).)*

**Out of scope:**
- The idle watchdog, run lock, tree baseline, plan-versus-commits check, the Phase 25 cleanup, removing the self-test from
  rendered copies and the runner file's self-test baseline entries (Phase 38).
- The error catalogue, stdout limit matching, router cooldowns and the retry policy; the closed reason list of error classes
  (Phase 38.1; this phase's closed list covers setting reasons only).
- Capability blocks, the prompt-size refusal against a lane's window and lens skills (Phase 39); lane switching and resilient review,
  and routing custom lanes through the runner (Phase 40); the adapter's resume, stop paths and use of session ids (Phase 41);
  jev choosing effort by task (Phase 42).
- Any run acting on an escalation flag; the catalog and the wizard (Phases 35, 36).
- *(added 2026-11-16, re-run 2)* Hosting an interactive agent TUI, a TUI app or an e2e run, reusing a pane across calls and the
  per-plan transport chooser (Phase 42 and calling skills); the run lock, the start-of-run sweep of leftover tabs and the naming
  and ownership policy beyond the label of R12 (Phase 38); the error class of a free lane's usage limit (Phase 38.1); lane switching
  on it (Phase 40); the written config (no hosting key, Phase 36 D-19).
- *(added 2026-11-21, plan time)* Choosing which skills or MCP servers a lane gets by role and task kind, the role table, the
  host scan and lens selection, the window check of inlined text and the capabilities line (Phase 39); writing or editing any
  host's own MCP or skill configuration (never); a grok fixture, form, probe or test (never: Phase 39.1 removes the runtime).

## Constraints

- Runtime code stays stdlib-only (the runner is plain Node, no package; Python modules use the standard library).
- The runner never calls jev, herdr, the network or the catalog; it learns only from the call, its seed data and the host.
  *(amended 2026-11-16, 37 D-22: the runner never calls jev, the network or the catalog, and calls the `herdr` CLI only through the
  optional hosting transport of R12, with `tab create`, `pane run` and `tab close` and nothing else; it learns only from the call,
  its seed data, the host and, in a hosted lane, the lane's own files)* *(amended 2026-11-16, 38 D-27: Phase 38's sweep of a
  killed run's directory also calls the read-only `tab list`; a live lane's screen, status and wait output are still never read)*
- Every config write elsewhere stays atomic; this phase writes no config (the snapshot record in R9 goes through the existing
  atomic cache writer).
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`, read no `.planning/` path and call no real host; fake CLIs only.
  A live resume or claude probe is a spike recorded under `tmp/`, never part of `make test`.
- A seed table row carries its source label and never blocks a lane; a setting no form exists for is reported, never fed.
- English only; no provider or model name other than `router-env/<x>` in code, defaults, rails, skills, docs or tests (tests for
  pi and opencode only), and runtime ids only as marked examples.
- A SKILL.md describes behaviour; provenance and version history live in a trailing section.

## Acceptance Criteria

- [ ] A call names role, effort, context, escalation flags and session id with plain flags; the Python layer emits them for every
      runtime and conflicts are usage errors (R1).
- [ ] Every named setting prints applied, ignored with a closed-list reason, or unknown, and the status line carries the lists (R2).
- [ ] *(added 2026-11-16, 38.1 D-30)* Every host's effort, session and context forms are checked against its recorded help with a
      source label, and a stale flag, a missing record or an out-of-kind context label fails a test (R2).
- [ ] Effort is composed in the runner in each runtime's form, with no closed level set and an id-carried value winning (R3).
- [ ] An unknown runtime runs from a declared argv file and is refused for a named fact without one; no parse gate cites a table (R4).
- [ ] The model id floor refuses a dash, whitespace and control characters and nothing else; unusual shapes print an advisory (R5).
- [ ] claude runs execute through a labeled-unverified formula (R6).
- [ ] A printed session id resumes the session on a second call, a rejected id fails visibly, and codex review reports `mode_forbids`
      (R7).
- [ ] A unit test fails when the rendered copy drifts from the template and reads no `.planning/` (R8).
- [ ] `--describe` feeds routing; `exec_formula`, its drift test and the per-runtime grammar mirror are gone (R9).
- [ ] Escalation flags are reported and echoed and never start a second lane (R10).
- [ ] `ai-kit-cross-ai` meets the judge bar; docs updated; the guard passes on rewritten files; `make test` passes (R11).
- [ ] With herdr available a lane runs in a tab the runner opens and closes, with the same result as headless; without herdr, with
      `--host none` or with `AIKIT_HOST=none` the headless path is unchanged and tested (R12, added 2026-11-16).
- [ ] *(added 2026-11-21)* Each skill a call names reaches the lane by name, path or inlined prose in the first form its host has
      verified, each host's forms carry a source label, and every skill line says the form applied or the reason it was not (R13).
- [ ] *(added 2026-11-21)* Each MCP server a call names reaches the lane only through its host's per-invocation form, is
      reported applied or ignored with a reason, no server value is printed and no host config is touched (R14).

## Edge Coverage

**Coverage:** 72/72 applicable edges resolved · 0 unresolved (72 engine rows from `edge_floor.py floor`; the 8 R12 rows were added 2026-11-16, re-run 2; the 14 R13 and R14 rows were added 2026-11-21, plan time)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | `--role review` with `--mode review` (and execute with exec) agree and pass; any other pair is a usage error, exit 2 |
| empty | R1 | ✅ covered | An unset setting emits no flag; an empty value for any new flag is a usage error naming the flag |
| encoding | R1 | 🧪 backstop | Flag names are ASCII; each value follows its flag's charset (R3, R7) |
| ordering | R1 | ✅ covered | Flag order never changes the result; `runner_flags` emits a fixed order, pinned by a golden test |
| adjacency | R2 | ✅ covered | A value equal to the `CONFIG.effort` default is still reported from the call, `applied` |
| empty | R2 | ✅ covered | A call naming nothing prints the `model` and `role` lines only |
| encoding | R2 | ✅ covered | Values printed in a setting line pass the runner's redaction and lose control characters first |
| ordering | R2 | ✅ covered | Lines print in the fixed name order of the list above, so output is stable |
| boundary | R3 | ✅ covered | A level of 1 and of 16 characters passes, one of 17 is a usage error |
| adjacency | R3 | ✅ covered | Levels match as whole tokens (`high` is not `xhigh`); an id's own `:high` and a call's `high` agree as `id_carries` |
| empty | R3 | ✅ covered | No effort passes nothing and prints no effort line; an empty string is a usage error |
| encoding | R3 | ✅ covered | Levels are ASCII lowercase tokens; uppercase, space, dash-leading and control characters are refused |
| ordering | R3 | ✅ covered | A cursor bracket keeps its existing keys in their order and a merged `effort` key is appended, so no key is lost |
| precision | R3 | ✅ covered | A level is an opaque string compared exactly, never parsed as a number or rounded |
| adjacency | R4 | ✅ covered | Runtime ids match exactly and case-sensitively: `Claude` is an unknown id and needs `--argv-file` |
| empty | R4 | ✅ covered | An empty array, and an array with an empty-string element, are refused with a named usage error |
| encoding | R4 | ✅ covered | The argv file is read as strict UTF-8; invalid bytes and a BOM are refused |
| ordering | R4 | ✅ covered | Element order is kept and a placeholder is replaced in place |
| idempotency | R4 | ✅ covered | The file is never written; the same file gives the same argv on every call |
| concurrency | R4 | ✅ covered | The file is read once at start, so an edit during the call has no effect (as `--prepend-file`) |
| adjacency | R5 | ✅ covered | A leading `-` is refused, an interior `-` is allowed; the floor and the advisory are separate checks |
| empty | R5 | ✅ covered | An empty id keeps its `no_model` status (a fact about the call) |
| encoding | R5 | ✅ covered | The floor is ASCII; a non-ASCII id is refused as before, never normalized |
| ordering | R5 | 🧪 backstop | The floor runs before the advisory and the live listing check, as today |
| adjacency | R6 | ✅ covered | The execute and review formulas are separate rows of one runtime; the review argv stays byte-equal |
| empty | R6 | ✅ covered | An execute call with no model ends `no_model` like every other runtime |
| encoding | R6 | 🧪 backstop | The JSON output of the execute formula is parsed by the review formula's reader |
| ordering | R6 | ✅ covered | Formula flag order is fixed and pinned by a golden argv |
| boundary | R7 | ✅ covered | An id of 1 and of 128 characters passes, one of 129 is a usage error |
| adjacency | R7 | ✅ covered | An id belongs to one runtime: the same string on another runtime is the host's rejection, not a runner check |
| empty | R7 | ✅ covered | An empty id is a usage error; a host that prints no id gives `session=-` |
| encoding | R7 | ✅ covered | The charset is ASCII; a host-printed id outside it prints as `-` with a note and is never passed back |
| ordering | R7 | ✅ covered | When one run uses several ids (retry rungs), the status line reports the last one used |
| precision | R7 | ✅ covered | Ids are opaque strings, never normalized or truncated |
| idempotency | R7 | ✅ covered | Two calls with one id are two resumes of one session; the runner keeps no state beyond the quota record |
| concurrency | R7 | ✅ covered | Two calls on one id at once: the host decides, the runner takes no lock (Phase 38's run lock guards an execute checkout) |
| concurrency | R8 | ✅ covered | The test renders into its own scratch directory, so parallel modules share nothing |
| adjacency | R9 | ✅ covered | A stale recorded fact that still claims a formula: the runner refuses at run time with its named reason, and the next detection refresh replaces the fact |
| empty | R9 | ✅ covered | An absent or unreadable fact never refuses a lane |
| encoding | R9 | 🧪 backstop | `--describe` prints UTF-8 JSON with ASCII keys |
| ordering | R9 | ✅ covered | Rows are sorted by runtime id, so the golden file is stable |
| concurrency | R9 | ✅ covered | `--describe` is read-only; the snapshot is written by the existing atomic cache writer |
| adjacency | R10 | ✅ covered | The two flags are independent and both may be set; each is reported on its own line |
| empty | R10 | ✅ covered | No flag gives `escalate=-` |
| ordering | R10 | ✅ covered | The echo lists runtime before model |
| adjacency | R11 | ✅ covered | A marked example covers only its own region; a name beside it still fails the guard |
| empty | R11 | ✅ covered | A skill with no evals fails the judge bar |
| encoding | R11 | 🧪 backstop | Plain Markdown and test text |
| ordering | R11 | 🧪 backstop | The reason list's order is pinned by the doc-contract test |
| concurrency | R11 | 🧪 backstop | The judge loop runs per skill and shares no state |
| boundary | R12 | ✅ covered | (added 2026-11-16, re-run 2) The label is the fixed prefix plus role, runtime and a 12-character run token, so it stays under 64 characters; a state-home path with a character outside `[A-Za-z0-9._/-]` or a quote cannot be typed safely and gives `host_failed` before any herdr call |
| adjacency | R12 | ✅ covered | (added 2026-11-16, re-run 2) A tab id equal to another run's id never occurs (ids are not reused); the runner closes only the id it read from its own `tab create`, so a neighbouring `aikit:` tab of another run is untouched |
| empty | R12 | ✅ covered | (added 2026-11-16, re-run 2) An empty or missing `rc` file with a dead launcher ends the lane as killed by a signal; an empty `out` and `err` give an empty answer through the existing `empty_answer` rule, as headless |
| encoding | R12 | ✅ covered | (added 2026-11-16, re-run 2) `out` and `err` are read as bytes and decoded as UTF-8 like a pipe; argv elements and the env file use single-quote quoting that carries any byte except NUL, and an element with NUL is refused as a usage error |
| ordering | R12 | ✅ covered | (added 2026-11-16, re-run 2) The tab closes before the run directory is removed, and `rc` is written after `out` and `err` are closed, so the last bytes are read before the lane counts as ended |
| precision | R12 | ✅ covered | (added 2026-11-16, re-run 2) `rc` holds one decimal integer 0-255 or a signal name; anything else is read as a crash with the file's first line redacted, never coerced |
| idempotency | R12 | ✅ covered | (added 2026-11-16, re-run 2) Two calls make two run tokens, two directories and two tabs; closing an already closed tab (owner closed it) is a no-op that is not an error |
| concurrency | R12 | ✅ covered | (added 2026-11-16, re-run 2) Parallel lanes each open their own tab and directory and share nothing; a runner killed by a signal closes its tab in the signal path, and one killed hard leaves a recorded tab id that Phase 38's sweep closes |
| boundary | R13 | ✅ covered | (added 2026-11-21, plan time) A skill name of 1 and of 64 characters passes and one of 65 is a usage error; a `SKILL.md` at the size cap is inlined and one byte over is a usage error; a copilot prompt that a block brings to exactly `ARGV_PROMPT_MAX` passes and one byte over gets the existing refusal |
| adjacency | R13 | ✅ covered | (added 2026-11-21, plan time) A `--skill-name` and a `--skill-path` whose directory name or frontmatter `name` match are one skill with one line and one form; two paths that resolve to one directory apply once; names compare exactly |
| empty | R13 | ✅ covered | (added 2026-11-21, plan time) No skill flag leaves the argv and the prompt byte-equal and prints no `skill` line; an empty flag value, a directory without `SKILL.md` and an empty `SKILL.md` are usage errors naming the flag |
| encoding | R13 | ✅ covered | (added 2026-11-21, plan time) The path and the body are read as strict UTF-8 (invalid bytes and a BOM refused, as R4); the inlined body is byte-equal to the file and its sha256 is taken over the file's bytes |
| ordering | R13 | ✅ covered | (added 2026-11-21, plan time) Skills apply in call order; prose blocks come before the `--prepend-file` content and the prompt; path flags follow call order in the argv; `skill` lines print in call order after the fixed setting names |
| precision | R13 | ✅ covered | (added 2026-11-21, plan time) Sizes are counted in bytes; the body is never trimmed, re-wrapped or normalized; the delimited block's sha256 is exact, so a reader can check it against the file |
| concurrency | R13 | ✅ covered | (added 2026-11-21, plan time) Each skill file is read once at start, so an edit during the call has no effect (as `--prepend-file`); the runner writes nothing, so parallel calls share nothing |
| boundary | R14 | ✅ covered | (added 2026-11-21, plan time) A server name of 1 and of 64 characters passes and one of 65 is a usage error; a file at the size cap is read and one byte over is a usage error |
| adjacency | R14 | ✅ covered | (added 2026-11-21, plan time) Server names compare exactly as JSON keys and a duplicate key is refused by the strict reader; a server that is also in the host's own config is the host's business on copilot (it augments) and absent on claude (strict), and the line reports what the argv carries |
| empty | R14 | ✅ covered | (added 2026-11-21, plan time) No flag leaves every argv byte-equal and prints no `mcp` line; a file without `mcpServers`, or with an empty `mcpServers`, is a usage error naming the file |
| encoding | R14 | ✅ covered | (added 2026-11-21, plan time) The file is read as strict UTF-8 JSON (a BOM refused); names are ASCII by their shape; values are never printed, so their encoding stays the host's concern |
| ordering | R14 | ✅ covered | (added 2026-11-21, plan time) `mcp` lines print in the file's key order; claude's `--mcp-config <file>` is always followed by `--strict-mcp-config`, so the variadic option ends at a flag, pinned by a golden argv |
| precision | R14 | ✅ covered | (added 2026-11-21, plan time) The host gets the caller's file itself by its absolute path (copilot with the `@` prefix), never a re-serialised copy, so no value is reformatted |
| concurrency | R14 | ✅ covered | (added 2026-11-21, plan time) The file and its mode are read once at start; the runner never writes it or any host config, so parallel calls (each with its own run-scoped file) share nothing; a test shows a fake host config directory untouched |

## Prohibitions (must-NOT)

**Coverage:** 17/17 applicable prohibitions resolved · 0 unresolved *(was 9/9; four rows added 2026-11-16, re-run 2; four rows added 2026-11-21, plan time)*

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT feed a runtime a setting it has no form for, and MUST NOT drop a named setting without a printed `applied`, `ignored` or `unknown` line | R2, R3 | resolved | verification: test — a fake CLI that takes no model flag or no effort sees neither, and every named setting has its line |
| MUST NOT start a fresh session silently when a given session id is rejected or has no resume form | R7 | resolved | verification: test — the rejected-id failure with the host's line and the `mode_forbids` report |
| MUST NOT let a seed table row, its label or a closed list of runtimes, models or levels refuse a lane | R3, R4, R5, R9 | resolved | verification: test — an unknown runtime with a declared command, an unusual id shape and a listed level the old sets rejected all reach the spawn |
| MUST NOT start a second lane, runtime or model because an escalation flag is set | R10 | resolved | verification: test — a failing call with both flags ends after one spawn |
| MUST NOT run a declared command whose file lies outside the cwd tree, holds an unknown placeholder, or needs the prompt on argv | R4 | resolved | verification: test — each refusal named, the prompt arriving only on stdin |
| MUST NOT print a key, token or control character in a setting line, in `session=` or in the advisory note | R2, R5, R7 | resolved | verification: test — a planted key shape in a value comes out redacted, a control character removed |
| MUST NOT run claude's execute formula without the unverified note until a live probe record exists | R6 | resolved | verification: test — the note is on every execute call and the label test fails once the record exists without the label change |
| MUST NOT call a real host, the network, jev or herdr from the runner or from its tests | R1-R11 | resolved | verification: test — the module tripwire, fake CLIs only, and an arch rule that the template names neither client *(amended 2026-11-16, 37 D-22: the arch rule says the template names no jev client and calls `herdr` only inside the hosting transport; tests use a fake `herdr` on PATH, never a real one)* |
| MUST NOT read `.planning/` from the sync test | R8 | resolved | verification: test — the existing arch rule that no test reads `.planning/` |
| MUST NOT require herdr, or let its presence change a lane's argv, settings, session, classification or exit code *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — hosted and headless calls compared field by field, and every no-herdr path |
| MUST NOT close, read or type into a tab or pane the runner did not open, and MUST NOT leave the tab it opened *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — a second tab in the fake is untouched; the opened tab is closed on every exit path |
| MUST NOT read herdr's screen text, agent status or wait output as a verdict or liveness signal, or rerun a lane that already started *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — a fake whose screen shows success while `rc` says failure ends failed; a fake that fails after typing spawns nothing twice |
| MUST NOT put an environment value, a key shape or the prompt on herdr's command line, in the typed line or in any file readable by another user *(added 2026-11-16, re-run 2)* | R12 | resolved | verification: test — the fake records every herdr argv and the file modes; a planted key shape appears in none |
| MUST NOT feed a skill or MCP form whose state is not `verified`, and MUST NOT report a skill or server `applied` that the final argv or the sent prompt does not carry *(added 2026-11-21, plan time)* | R13, R14 | resolved | verification: test — unverified and unknown forms leave the argv unchanged and print their reason; the state is computed from the built argv and prompt |
| MUST NOT write, edit or read any host's own MCP or skill settings file (a skill directory the call names is read, never written), choose a skill or server for a lane, or add an approval flag a formula lacks *(added 2026-11-21, plan time)* | R13, R14 | resolved | verification: test — a fake host config directory is byte-equal after every call; golden argv per runtime and role with and without the flags |
| MUST NOT print an MCP server's command, arguments, environment, URL or headers, or put the MCP JSON on argv *(added 2026-11-21, plan time)* | R14 | resolved | verification: test — a planted key shape in a server's `env`, `args` or `headers` appears in no stderr line, status line or argv; only the file path is passed |
| MUST NOT add a grok help fixture, form, probe, session row, test or list entry *(added 2026-11-21, plan time, owner directive 2026-11-20)* | R1-R14 | resolved | verification: review — the phase verification counts added lines naming grok outside `.planning/` (as Phase 36's did) and finds none beyond expected-message edits of existing tests |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Roadmap goal, three requirements, the 2026-11-16 amendments and Phase 36's handoff list |
| Boundary Clarity   | 0.84  | 0.70 | ✓      | Watchdog, lock and error classes fenced to Phases 38 and 38.1; lane switching to 40 and 41 |
| Constraint Clarity | 0.82  | 0.65 | ✓      | stdlib-only runner, no jev or herdr in it, closed reason list, table never decides |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Eleven checks tied to fake-CLI tests, golden files, a sync test and the judge loop |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      | 1 − (0.35×0.88 + 0.25×0.84 + 0.20×0.82 + 0.20×0.82) |

## Interview Log

Interactive path, one round in the phase subagent; no owner question was unclear enough to relay (the owner answers only
unclear gray areas, 2026-11-16 run mode). The open items went through jev (one advisory answer per item; a low answer is
decided by own reasoning). Summaries only, advisory. Rule: `mvp-mode` inactive, so the best design wins over the smallest
diff.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | What does the runner accept and refuse today, and what does each host's help say about effort, sessions and permissions? | none; live runs of the template's dry-run and the hosts' `--help` | Facts in Background; the gating findings list (R1-R6) |
| 1 | Boundary Keeper | Where is the per-runtime effort form decided? | laya runner_owns_forms low 0.38; typesafe runner_owns_forms low 0.60 | **Own reasoning:** the runner, because a GSD hook cannot carry a cursor bracket (a glob class) and has no Python layer; amends 36 D-05 (R3, ledger) |
| 1 | Simplifier | What contract does a session id have across hosts that choose or mint ids? | laya resume_only_printed low 0.42; typesafe one_flag_row_decides low 0.79 | **Own reasoning:** one flag, the row says chosen or minted, a rejected id is a failed call (R7, ledger) |
| 1 | Boundary Keeper | What does the runner do with a runtime it has no formula for? | laya refuse_always low 0.43; typesafe refuse_always low 0.72 | **Own reasoning, jev overridden (low):** both low answers contradict the owner's directive that an unknown runtime and a custom command can still serve; a declared argv file serves, none gets a named refusal (R4, ledger) |
| 1 | Failure Analyst | What happens to the per-runtime model id grammars? | floor_plus_advisory, typesafe 0.95 (laya drop_all low 0.69) | Universal floor stays, per-runtime shapes become an advisory (R5) |
| 1 | Failure Analyst | Do closed effort sets stay? | laya catalog_check low 0.67; typesafe shape_only low 0.58 | **Own reasoning:** shape only; a catalog check in the runner would need the catalog in a standalone rendered script (R3, ledger) |
| 1 | Boundary Keeper | What does the runner do with escalation flags? | carry_and_report, typesafe 0.98 (laya act_in_runner low 0.45) | Carried, reported, never acted on (R10) |
| 1 | Simplifier | How does a call name the role? | laya keep_mode_only low 0.44; typesafe role_flag_mode_alias low 0.76 | **Own reasoning:** `--role` is the documented name, `--mode` an alias, a disagreement refused (R1, ledger) |
| 1 | Boundary Keeper | Does the runner learn claude's execute formula now? | add_formula_unverified_label, typesafe 0.89 (laya low 0.51 agrees) | Yes, labeled unverified until a live probe (R6) |
| 1 | Simplifier | A provider flag? | laya provider_flag low 0.63; typesafe derive_and_report low 0.57 | **Own reasoning:** no flag; the provider is the id prefix where the id form has one, reported as a setting (R1, R2, ledger) |
| 1 | Researcher | What gives the Python layer the runner's formulas without a mirror? | none | `--describe` recorded in the runtimes snapshot at detection and read by routing; the mirrors and the drift test go (R9) |
| 2026-11-16 amendment | Researcher | What do the hosts' own helps say about a context size, and which phase records the forms? | none; live `--help` of seven hosts and a zero-token codex config parse (Phase 38.1) | **Own reasoning:** per-host context forms with labels and the all-host help-fixture test, executed by this phase's plan (R2 amendment, 38.1 D-17, D-30, ledger) |
| 1 | Researcher | Why does RUN-06 need a new test when `check_dogfood.py` exists? | none | The live check reads `.planning/`; a unit test must not, so it renders into a scratch project and compares (R8) |
| 2 (re-run 2, 2026-11-16) | Boundary Keeper | Where does optional multiplexer hosting of a lane live? | inside_runner_transport, typesafe 0.89 (laya none_of_these low 0.51) | Inside the runner as one optional transport (R12, D-22) |
| 2 | Simplifier | What triggers hosting? | availability_with_flag, typesafe 0.89 (laya always_when_available low 0.39) | `--host auto\|none`, runner default none, builders emit auto (R12, D-23) |
| 2 | Failure Analyst | How does the runner learn a hosted lane's result? | laya forced; typesafe screen_scrape_marker low 0.63 | **Own reasoning, jev overridden (low):** screen text matched the typed line in a live check; a launcher with files and an exit file gave exact codes (R12, D-24, ledger) |
| 2 | Boundary Keeper | Does the runner host an interactive agent TUI too? | caller_transport_later_phase, typesafe 0.98 (laya none_of_these low 0.43) | No: Phase 42's transport chooser (R12, D-27) |
| 2 | Simplifier | How is hosting switched off? | laya none_of_these 0.83 (confident, no option); second opinion typesafe config_key low 0.67 | **Own reasoning:** flag value and `AIKIT_HOST`, no config key (R12, D-23, ledger, needs owner confirmation) |
| 2 | Failure Analyst | How does the lane's environment reach the pane? | laya none_of_these low 0.56; typesafe tab_env_arguments low 0.65 | **Own reasoning, jev overridden (low):** command-line arguments show in the process table; a 0600 file in a 0700 per-run directory (R12, D-25, ledger) |
| 3 (plan time, 2026-11-21) | Researcher | How does each installed host take a skill and an MCP server per call? | none; live `--help` of six hosts and their `skill`/`mcp` subcommand helps, read-only | Facts in the 2026-11-21 amendment of Background; only pi's `--skill` and claude's and copilot's MCP flags are fed (R13, R14) |
| 3 | Boundary Keeper | Where do skills and MCP servers for lanes split between the runner and Phase 39? | none (owner-directed) | Owner request: the runner records forms, delivers what the call passes and reports it; choosing by role and task kind stays Phase 39 (R13, R14, D-31, D-33) |
| 3 | Simplifier | Who falls back from name to path to prose? | none (owner-directed order) | **Own reasoning:** the runner, since it alone knows the host forms and a GSD hook has no Python layer; the caller passes a name when its table says the host has the skill (R13, D-32, ledger) |
| 3 | Failure Analyst | How does a server reach a host with only a config file? | none (owner-directed) | Owner rule: never edit the host's config; reported `ignored` `no_form`, file path only on argv, values never printed (R14, D-33) |
| 3 | Boundary Keeper | What happens to grok in this phase? | none (owner directive 2026-11-20) | Mentions superseded in place; no grok work; existing code left for Phase 39.1 (D-34) |

---

*Phase: 37-shared-runner-options-and-session-ids*
*Spec created: 2026-11-16*
*Amended: 2026-11-21 (plan time: R13 lane skills, R14 lane MCP servers, grok not a target)*
