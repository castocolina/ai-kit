# Phase 37: Shared runner options and session ids - Research

**Researched:** 2026-11-21
**Domain:** one stdlib-only Node runner (`cross-ai.mjs`, 12,839 lines) plus its Python layer (`ai_kit_spec`, `ai_kit_gsd_curated_config`)
**Confidence:** HIGH on code anchors and decomposition (read this session); MEDIUM on host forms (help text only until the spike); LOW on anything the spike must answer

## Summary

The runner is one 12.8k-line file with no planner: every setting is a field read inside a per-runtime formula closure
(`RUNTIMES.<id>.exec/review/resume`), reached through a `ctx` object that `runCli` builds (`codexEffort`, `piThinking`,
`cursorMode`, `sid`, `profileFlags`). That `ctx` seam is the lever: the new pure `planSettings` computes argv additions and the
settings report, `main`/`runCli`/`--print-argv` hand the additions to the formulas through `ctx`, so `rt.review(model, ctx)`
stays the single source of the review argv and `reviewArgvProblem` (compares the argv prefix to `rt.review(model, ctx)`) keeps
working unchanged.

Phase 36 is in the tree as code (`exec_formula`/`ExecFormula` in `detection.py`, `effort_form` in `lane_effort.py`, `lane_escalation`
in `lane_settings.py`) but `36-VERIFICATION.md` does not exist on this branch, so the plans must re-read the files they delete or
change, not trust a verification note. The Python layer today composes effort into the model id (`spec_with_effort`,
`effort_form`, `build_cursor_agent_model_id`) and mirrors the runner grammar (`_MODEL_ID_SRC`, `model_id_ok`); both go, and the
runner takes the bare model plus `--effort`.

Two facts the SPEC does not state and the plans must carry: (1) the hook builder and `runner_flags` will emit `--role`/`--host
auto`/`--effort`, which template 8 rejects as `unknown argument`, so the readiness floor `_READY_TEMPLATE` and `TEMPLATE_VERSION`
(8 today) must be bumped in the same plan that makes the builders emit them; (2) the status line must keep printing the model as
called (bare), not the composed id, or `_trailer_counts` (Python) rejects the trailer once Python passes bare model + `--effort`.

**Primary recommendation:** build the planner as data-on-rows plus one pure function, land it in small serial runner plans (the
runner file serializes the waves), put the help fixtures and flag test first, keep every Python deletion behind the runner feature
that replaces it, and run the live spike (plan 01) natively by the orchestrator, not through the pi lite lane.

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions
D-01 to D-29 and D-31 to D-34 of `37-CONTEXT.md` are locked (read in full). Verbatim headlines the planner must honor:
- D-01 the runner owns every effort form; Python only passes the flag; `build_reviewer_model_id` and `build_cursor_agent_model_id` deleted once `build-model-id` and the wizard preview read `--print-argv`.
- D-02 `--role` documented, `--mode` alias, disagreement is exit 2. D-04 no provider flag. D-07 a level is a token (`^[a-z][a-z0-9_-]{0,15}$`), `CODEX_EFFORTS` and `PI_THINKING` go, `CONFIG.effort.<runtime>` sits beneath the call for every runtime.
- D-03 one `--session-id`; row says `chosen` or `minted`; opencode `minted` until the spike records the shape rule. D-05 argv-file lane. D-06 id floor + advisory. D-08 escalation `recorded_only`. D-09 claude execute+resume formula, unverified. D-10 `--describe` keyed by template content hash; routing reads the stored fact.
- D-11 rows carry data; one pure `planSettings(row, role, call)`. D-12 one new status group after `attempts= cycles=`, before `retry_after_s=`. D-13 tests split by cost (argv/describe in Python through `--print-argv`/`--describe`; spawn-level behaviour as self-test cases; shard times re-recorded). D-14 closed reason list. D-15 `--context <label>` (`^[a-z0-9][a-z0-9._-]{0,15}$`). D-16 only `ai-kit-cross-ai/SKILL.md` changes and meets the judge bar. D-17 spike first. D-18 sync test renders through `ensure_runner`. D-19 hardcoding cleanup limited to rewritten code.
- D-22 to D-28 herdr transport inside the runner (`tab create`, `pane run`, `tab close` only; `--host auto|none`, default `none`; `AIKIT_HOST`; files + `rc` verdict). D-29 no class added for a free-lane limit.
- D-31 to D-34 skills (`--skill-path`, `--skill-name`; forms name, path, prose), MCP (`--mcp-config <file>`), grok not a target.

### Claude's Discretion
The size cap number; the exact `--describe` shape; the hosted-launcher internals; plan decomposition; which self-test cases are
`logic` versus `runtime`; conversion rule for codex token labels (see Assumptions).

### Deferred Ideas (OUT OF SCOPE)
Idle watchdog, run lock, tree baseline, plan-versus-commits (38); error classes and retry policy (38.1); capability block, window
check, lens selection, role table (39); lane switching, routing custom lanes through the runner (40); adapter resume (41); jev
choosing effort (42); interactive agent TUI transports and pane reuse; any grok work (39.1 removes the runtime).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RUN-01 | Shared call vocabulary, settings report, effort forms, argv-file lane, id floor, claude execute formula, `--describe`, escalation flags, skills (R13), MCP (R14), docs and judge bar | Sections 1.1-1.12, 1.15-1.17; plans P03-P13, PY1-PY4, DOCS |
| RUN-02 | Session id in and out, resume | Section 1.7; plans P05, P07 |
| RUN-06 | Rendered copy matches the template (unit test) | Section 1.8; plan SYNC |
| RUN-12 | Optional herdr hosting | Section 1.13; plans P14, P15 |
</phase_requirements>

## Project Constraints (from CLAUDE.md / AGENTS.md)

- English only in every written artifact. Runtime code stays stdlib-only (the runner is plain Node; Python modules stdlib). Atomic writes for every config write (this phase writes none; the describe snapshot goes through the existing atomic cache writer).
- No hardcoded absolute path in source, tests or assets. No model name other than `router-env/<x>`, `placeholder-model-<n>`, `placeholder-alias-<n>`, `fake/<token>`, `fake-<token>` (HUB-09); marked examples carry `model-example:`.
- Tests: scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`, no network, no real host CLI, no `.planning/` read (arch rule). `tests/fixtures/cli_help/` is in the guard's `SKIP_PARTS` [VERIFIED: tests/test_arch_hardcoded_models.py:31-36, quote `"tests/fixtures/cli_help/",`], so captured help text with real model names there is exempt; the new test module is not.
- Pylint caps (max-args 5, max-locals 15, max-branches 12, max-returns 6, max-statements 50), ruff line length 100, pyright basic, vulture 80: pyright and vulture run only at push, so every plan's verify runs `make ruff`, `make pyright`, `make vulture`, `make pylint`.
- Run rails: GROK IS NOT A TARGET (no grok fixture, form, probe, session row, test or list entry; existing grok code untouched). Execution is cross-AI (pi, `router-env/my-coding`, unattended, prompt on stdin, lane timeout 1800 s): about 3 tasks per plan, no design decision left to the executor; a heredoc or `$(...)` in plan text means FILE CONTENT written with the file-write tool. Plans that stage `tools/run_unittest_parallel.py` trigger the full unit+arch groups at commit. A plan that replaces a model literal of an existing test names `tests/fixtures/no_hardcoded_models_baseline.json` (shrink-only).
- Local shell rules (copied word for word into every executor brief): one simple command per call, never `cd`, no heredocs/`$(...)`/backticks/subshells/`eval`/long chains, no `sed -i`, delete only under `tmp/`, write files with the file-write tool. Scratch only under `tmp/run-2026-11-19/...`.
- Every new or materially updated SKILL.md passes `skill-judge` (no critical/high, or grade B+, no regression); three rounds max; at most three open findings are fixed without a new round.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Call vocabulary parse, settings planning, report | Runner (`cross-ai.mjs`) | Python builders emit flags only | A GSD hook has no Python layer (D-01) |
| Per-host forms (effort, session, context, skills, mcp) | Runner rows (data) | `--describe` exposes them | One place holds each form (D-11) |
| Routing facts for `no_formula` | Python `routing.py` reading a stored `--describe` snapshot | Runner refuses at run time | An absent fact never refuses (D-10) |
| Render/sync check | Python unit test through `ensure_runner` | `tools/check_dogfood.py` (live copy) | Unit tests may not read `.planning/` |
| Hosted lane transport | Runner (`runChild` sibling) | herdr CLI (3 verbs) | Result channel is files, `rc` is the verdict |
| Help fixtures + flag lock | Python tests over `tests/fixtures/cli_help/<host>/` | Runner rows are the checked text | A flag a form uses must appear in recorded help |

## Section 0. What the code is today

Counts and anchors verified by reading or ripgrep this session (line numbers on this branch at HEAD `345fdce`).

### 0.1 cross-ai.mjs (12,839 lines; header `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=8 sha256=UNSTAMPED` at line 2)

| Symbol | Line | Note |
|--------|------|------|
| flag doc comment | 22-54 | must gain every new flag |
| `const CONFIG = {...}` between `// <config>` (78) and `// </config>` (114) | 79 | keys: attemptTimeoutS, capS, effort `{}`, extraArgs, heartbeatS, models, outerTimeoutS, retry, routerBacked, runtime, scrubEnv |
| `EXEC_PREAMBLE` / `REVIEW_PREAMBLE` | 119 / 128 | appended to the prompt in `main` (12669) |
| `STATUS_TABLE` | 1163 | status to exit |
| `reportAndFinish` / `finish` | 1249 / 1269 | `finish` builds the one status line (see 0.3) |
| id grammars `MODEL_ID`, `CURSOR_MODEL_ID`, `PI_MODEL_ID`, `OPENCODE_MODEL_ID` | 1296-1304 | declared above `RUNTIMES` (temporal dead zone note at 1293) |
| `RUNTIMES` | 1336-1461 | rows: cursor 1337, opencode 1359, pi 1372, codex 1394, claude 1420 (`exec: null`, `resume: null`), copilot 1441 (`argvPrompt: true`, `errorsUnverified: true`, `resume: null`); no grok row |
| `piThinkingArgs`, `withCodexKnobs`, `codexExecArgv` | 1465 / 1469 / 1478 | read `ctx.piThinking`, `ctx.codexEffort`, `ctx.codexServiceTier`, `ctx.codexSandbox` |
| `KEY_SHAPES` (one JSON line, pinned equal to the Python table by a test) | 1530 | never touch |
| `redactSecrets` | 1600 | applies to every setting value |
| `routeOf` | 2449 | |
| `resolveBin` | 3005 | |
| `logDeadline` | 3456 | |
| `ladderNext` / `sameSessionArgv` / `newSessionArgv` | 4057 / 4090 / 4097 | `sameSessionArgv` returns null for no sid, no `rt.resume`, codex review or sandboxed codex exec; pi gets `ctx.sid = randomUUID()` on rung 2 |
| `ARGV_PROMPT_MAX = 102400`, `argvPromptElement`, `argvPromptProblem` | 4108 / 4112 / 4117 | copilot prompt on argv |
| `stateHome()` | 4135 | `XDG_STATE_HOME` or `~/.local/state`; the host run dir goes under it |
| `killGroup` / `runChild` | 4224 / 4259 | the one spawn seam; result `{code, signal, timedOut, limited, spawnErr, stdout, stderr}`; `opts.input === null` means stdin `ignore` |
| `listModels` | 4421 | |
| `childEnv`, `withExtra`, `reviewArgvProblem` | 4524 / 4532 / 4540 | `CONFIG.extraArgs[cli]` appended; review argv must equal `rt.review(model, ctx)` prefix |
| `logReport` | 4736 | the `cross-ai: report ...` line |
| `runCli` | 4753 | builds `ctx` (4762-4769: `sid: crypto.randomUUID()`, `codexEffort`, `codexServiceTier`, `cursorMode`, `piThinking`, `codexSandbox`, `profileFlags`, `promptArg`); argv at 4784; `last_sid` saved at 4912, loaded and resumed at 4954-4964, `sid` read after an attempt at 5075 |
| `promptFiles`, `rung2Gate` | 5203 / 5235 | |
| `CODEX_EFFORTS` / `PI_THINKING` / `CURSOR_MODES` / `ROUTE_VALUES` | 5253-5256 | first two go (D-07); the last two stay (the runner's own vocabulary) |
| `parseArgs` | 5258-5329 | unknown runtime at 5320-5322, unknown cli for prefer/model/route at 5324-5327, superset id charset at 5275 and 5284 |
| `resolveRuntime` | 5333 | `known()` gate at 5350-5357 (CONFIG runtime/prefer) |
| `runClassifyOnly` | 5365 | `Object.hasOwn(RUNTIMES, cli)` gate at 5385-5388 |
| `writeFakePi` / `writeFakeCursor` / `writeFakeOpencode` / `writeFakeCopilot` / `writeFakeClaude` / `writeFakeCodex` | 5502 / 5870 / 5930 / 5999 / 6037 / 6047 | fakes live in the runner file (the claude fake prints `{type:'result', result:'ok', session_id:'x'}` only) |
| `STATUS_HEAD_RE` | 6099 | `^(.* action=stop)(?: (route=\S+ rule=\S+ pattern=\S+))?(?: (attempts=\S+ cycles=\S+))?(?: (retry_after_s=\S+ cycle=\S+))?(?: upstream=\S+)?$` |
| `statusLineOk` | 6104 | one AIKIT-XAI line, last stderr line, `pattern.test(parts[1])` |
| `runSelfTestCase` | 6422 | scratch repo, hermetic env, `spec.setup` or `checkCase` |
| `checkCase` | 6301 | |
| `blackBoxSelfTest(listOnly)` | 6488 | `const cases = [` at 6537; each case is an object literal with a REQUIRED `kind: 'logic' \| 'runtime'` (12513 refuses an unkinded case: `cases.filter((c) => c.kind !== 'logic' && c.kind !== 'runtime')`); `--self-test-list` prints `name<TAB>kind` (12523-12524); `AIKIT_XAI_SELFTEST_CASES=a,b` filters (12527) |
| `main` | 12551-12827 | order: parseArgs, selfTest/classifyOnly, resolveRuntime, model gate `rt.modelId.test` (12582), `knobs` (12592), exec-null refusal (12596), profile (12600-12614), `--print-argv` branch (12629-12651: prints `name\tbin\targv-json` on stdout and `rung1`/`rung2` argv on stderr), stdin read (12652), `--prepend-file` (12658-12668), `ARGV_PROMPT_MAX` check (12670), listing preflight (12735-12749), `runCli` (12755), classification and `reportAndFinish` |

Pylint caps do not apply to the `.mjs` file. `main` is already about 275 lines, so a plan must extract helpers (`planCall`, `emitSettings`) instead of growing it.

### 0.2 Python layer

| File (lines) | Symbols (line) |
|--------------|----------------|
| `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py` (680) | `PROJECT_RUNNER_PATH` 33; `HOOK_TOKEN_RE` 36 (`^[A-Za-z0-9._:/@+=,#-]+$`); `MODEL_ID_SRC`..`OPENCODE_MODEL_ID_SRC` 53-59; `_MODEL_ID_SRC` 60; `model_id_ok` 76; `model_id_src` 82; `RunnerSpec` NamedTuple 87 (runtime, model, mode, timeout_s, cwd, effort, service_tier, cursor_mode, codex_sandbox, route, ignored); `spec_with_effort` 102; `review_spec` 113; `EXEC_NOTES` 195; `project_runner_command` 198 (refuses when runtime not in `SUPPORTED_EXECUTE_CLIS` or `not model_id_ok`); `runner_flags` 213-229 (`--runtime --model --mode`, route, codex effort/tier/sandbox, cursor mode); `build_runner_argv` 266; `parse_status_line` 277; `_trailer_counts` 573 (`status["model"] in ("-", spec.model)`); `run_runner` 597 (prints `spec.ignored`, refuses with `model_id_ok` at 609) |
| `.../commands.py` (138) | `SUPPORTED_EXECUTE_CLIS` 63 (derived from `has_exec_formula`); `execute_cli_error` 68; `build_cursor_agent_model_id` 83; `build_reviewer_model_id` 103; `render_reviewer_command` 114 |
| `.../detection.py` (1583) | `ExecFormula` 75 (docstring says "Phase 37 deletes this mirror"); `Runtime` NamedTuple 94 (fields binaries, host_signals, scrub_signals, list_argv, native_selectors, model_suffix, multi_provider, runner, exec_formula, advice); `RUNTIMES` 110 (pi, opencode, cursor, codex, claude, copilot, grok; grok has `runner=False`, left alone); `has_exec_formula` 173; `exec_formula_source` 183; `NO_RUNNER_ENTRY` 180; `runtimes_schema_is_current` 1172; `build_runtimes_snapshot` 1278; runtimes cache path 213 (`runtimes.json`) |
| `.../routing.py` (373) | `SKIP_ROUTES` 37 (bad_model, no_inventory, not_installed, unknown_runtime, no_model, no_formula); `_route_shape` 137 (`unknown_runtime` at 144); `_route_inventory` 153 (`no_inventory` at 159); `route` 169 (`unknown_runtime` at 176, `no_formula` at 180-181) |
| `.../lane_effort.py` (288) | `RUNNER_CODEX_EFFORTS` 17, `RUNNER_PI_LEVELS` 18 (mirrors of the runner sets), `EffortForm` 31, `_codex_form` 80, `_pi_form` 88, `_opencode_form` 99, `_cursor_form` 104 (calls `build_cursor_agent_model_id`), `effort_form` 121, `effort_problem` 173, `_effort_runtime_problem` 150 (closed-set checks) |
| `.../lane_settings.py` | `lane_escalation` 110 returns `Escalation(escalate_runtime, escalate_model)` |
| `.../cli.py` (1368) | `build-model-id` parser 369, `_cmd_build_model_id` 1185 (calls `build_reviewer_model_id` at 1187), `execute_cli_error` use 1209, `_display_spec` 1037 |
| `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py` (389) | `HEADER_RE` 17; `_READY_TEMPLATE = 8` 23; `_CONFIG_START/_END` 24-25 (`// <config>`, `// </config>`); `script_state` 49 (`pristine` iff header sha256 equals the sha256 of the body after the two header lines); `template_version` 64; `_replace_config` 116; `_stamp` 128; `render` 141; `plan_runner_upgrade` 265; `ensure_runner(project_dir)` 358 (renders into the project, writes `.planning/scripts/cross-ai.mjs`) |
| `.../cross_ai.py` | `TEMPLATE_VERSION = 8` line 46 |
| `.../cross_ai_build.py` (124) | imports `execute_cli_error`, `model_id_ok`, `HOOK_TOKEN_RE`, `project_runner_command`, `RunnerSpec` under a guarded import (lines 29-59), uses them at 70, 88-90, 110-124 |
| `tools/check_dogfood.py` (652) | `check_runner_copy` 91-117 (version equal, `script_state == pristine`, bytes equal outside the config block); `_fingerprint` 120; only reader of `.planning/` |
| `tools/record_cli_help.py` | records opencode only (`OUT = .../cli_help/opencode`, line 17; scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`); tests never run it |
| `tests/test_opencode_help_flags.py` | the phase-35 model to generalize: extracts the `  opencode: {` block from the template, flags regex `(?<![\w-])--[a-z][a-z0-9-]*(?![\w-])`, planted-stale-flag and whole-token tests |
| `tests/cross_ai_selftest.py` | `SHARD_COUNTS = {"logic": 4, "runtime": 4}`; `list_cases` runs `--self-test-list`; `split_cases` deals names heaviest-first by `tests/fixtures/cross_ai_selftest_secs.json`; a name missing from the table weighs the median; `record_times()` runs every case alone and rewrites the JSON (about 4 minutes, `python3 tests/cross_ai_selftest.py --record-times`); shard modules `tests/test_cross_ai_selftest_{logic,runtime}_{1..4}_e2e.py` |

### 0.3 Status line today

`finish` (cross-ai.mjs:1280-1283) writes exactly one `process.stderr.write` of:
`AIKIT-XAI status=<s> cli=<c> model=<m> exit=<n> cli_rc=<n> elapsed=<n>s out=<n> tree=<t> action=stop route=<r> rule=<x> pattern=<p> attempts=<n> cycles=<n>` then, only when set, ` retry_after_s=<n> cycle=<n>` (and `upstream=` is appended elsewhere). Python `parse_status_line` (runner_dispatch.py:277) splits on whitespace and `=` so any new `key=value` token with no whitespace parses; `_trailer_counts` (573) reads only `exit`, `cli`, `model`. GSD's `run-with-timeout` runs the command with inherited stdio and never reads or rewrites lines [VERIFIED: .claude/gsd-core/bin/gsd-tools.cjs:4793-4798, quote "stdio is inherited so shell pipes ... and redirects keep working"], so the longer line cannot be truncated by it; the one-last-line rule holds if the line stays one `write` (resolves the CONTEXT open question).

### 0.4 After phase 36 (what exists to delete)

`exec_formula`/`ExecFormula`/`has_exec_formula`/`exec_formula_source`/`NO_RUNNER_ENTRY` (detection.py), `SUPPORTED_EXECUTE_CLIS` and `execute_cli_error` (commands.py), `no_formula` route (routing.py:180-181) and its drift test `tests/test_ai_kit_spec_exec_formula_e2e.py` (reads `row.exec_formula.head` against the template's `--print-argv`), `unknown_runtime`/`no_inventory` routes (routing.py:38,144,159,176).

### 0.5 Callers (file:line), from ripgrep over `skills/ tools/ tests/` (`*.py`, `*.mjs`)

- `build_reviewer_model_id`: `cli.py:47,1187`; `commands.py:103`; tests `tests/test_ai_kit_spec.py:65,3176,3181`, `tests/test_ai_kit_spec_runtimes_table.py:445,446,449`.
- `build_cursor_agent_model_id`: `commands.py:83,110`; `lane_effort.py:10,111`; tests `tests/test_ai_kit_spec.py:63,3166,3172`.
- `model_id_ok`: `runner_dispatch.py:76,205,609`; `cross_ai_build.py:33,42,58,70`; tests `tests/test_ai_kit_spec_runner_dispatch.py:36,270-279`, `tests/test_lane_effort.py:122`.
- `_MODEL_ID_SRC`: `runner_dispatch.py:60,78,84` (no other file).
- `SUPPORTED_EXECUTE_CLIS`: `commands.py:63`; `runner_dispatch.py:24,205`; tests `test_ai_kit_spec_runner_dispatch.py:24,886,901`, `test_ai_kit_spec.py:5323`, `test_ai_kit_spec_runtimes_table.py:162,489`.
- `execute_cli_error`: `commands.py:68`; `cli.py:48,1209`; `execute_dispatch.py:20,114`; `execute_selection.py:104`; `cross_ai_build.py:29,37,54,88-90`; tests `test_ai_kit_spec.py:5252-5262`, `test_ai_kit_spec_runtimes_table.py:438-440`, `test_ai_kit_gsd_curated_config.py:555`.
- `unknown_runtime`: `routing.py:38,144,176`; `config_io.py:163` (message text); tests `test_ai_kit_spec_routing.py:323-334`, `test_ai_kit_spec_legacy_config.py:329`, `test_ai_kit_spec_superpowers.py:376,380`.
- `no_inventory`: `routing.py:38,159`; `dispatch_injection.py:109` (docstring); test `test_ai_kit_spec_routing.py:318`.
- `no_formula`: wide: `routing.py`, `commands.py:79`, `execute_selection.py:82`, `dispatch_injection.py:109`, tests `test_no_seed_refusal.py:74-91`, `test_ai_kit_spec_routing.py:311-359`, `test_ai_kit_spec_superpowers.py` (many), `test_spec_chain_text.py:176,426`, `test_ai_kit_spec_runtimes_table.py:921`.
- `effort_form`: `runner_dispatch.py:27,105`; `effort_probe.py:8,54`; tests `test_lane_effort.py`, `test_effort_probe.py`, `test_ai_kit_spec_runner_dispatch.py:815,926,953`.
- `runner_flags`/`project_runner_command`/`RunnerSpec`: `runner_dispatch.py`, `cross_ai_build.py`, `execute_dispatch.py:99`, `cli.py:1037`, tests `test_ai_kit_spec_runner_dispatch.py`, `test_cross_ai_runner_e2e.py`, `test_curated_config_script.py:454-474`, `test_ai_kit_spec_env_scrub.py`, `test_ai_kit_spec.py:5083,5207,11769`, `test_ai_kit_spec_superpowers.py:927`.

### 0.6 Docs and samples

`skills/ai-kit-cross-ai/SKILL.md` (191 lines; sample status lines at 85 and 134), `references/launch-and-wait.md` (36), `skills/ai-kit-spec-review/references/cross-ai-dispatch.md` (388; status line prose at 345), `skills/ai-kit-gsd-curated-config/references/runner.md` (97), `skills/ai-kit-gsd-curated-config/SKILL.md` (template 8 mentions at 213, 222, 266, 353). `tests/test_cross_ai_skill_text.py:347-359` (`test_status_examples_parse`) parses every fenced `AIKIT-XAI ` line in SKILL/POLICY/LAUNCH with `parse_status_line` and asserts keys `status`, `exit`, `action`, every token has `=`, ASCII only; it does not compare to self-test output byte for byte. The same file pins "template 8" at line 203 and `tests/test_curated_config_script.py:62-65` pins `cross_ai.TEMPLATE_VERSION == shipped` and `cross_ai_script._READY_TEMPLATE == shipped`; `tests/test_ai_kit_spec.py:11806` reads `TEMPLATE_VERSION = (\d+)` from the version source.

### 0.7 Help captures (read-only, from `tmp/run-2026-11-19/p37-help/`)

`claude-help.txt` 22 KB, `codex-help.txt`, `codex-exec-help.txt`, `codex-mcp-help.txt`, `copilot-help.txt` 16 KB, `copilot-skill-help.txt`, `cursor-help.txt`, `cursor-mcp-help.txt`, `opencode-help.txt`, `opencode-run-help.txt`, `opencode-mcp-help.txt`, `pi-help.txt`, `pi-mcp-help.txt`, plus `*-version.txt`. Scrub: `index.txt` holds `which` paths with the owner's home directory and user name, so it is NEVER copied; `copilot-version.txt` is 71 bytes (read it before copying, it may carry extra text); `copilot-help.txt` has the generic example `/home/user/projects` (keep); help text names env vars (`CURSOR_API_KEY`, `*_API_KEY`) and no values; no email found. A fixture scrub test must fail on `/(home|Users)/<name>/` other than `/home/user/`, on any `@host.tld`, and on a key shape (reuse the Python `secret_shapes` table). Subcommand helps NOT yet captured: `codex exec resume --help` (the codex resume formula), `copilot` has none needed, `cursor-agent models --help`, `pi --help` is enough for the session flag. The existing opencode fixtures (`tests/fixtures/cli_help/opencode/{help,run-help,models-help,version}.txt`, `meta.json` with `version`, `recorded`, `commands`) stay as they are.

## 0b. Amendments from later units (locked, quoted)

Three commits on the units stacked above this one amend this phase's own SPEC and CONTEXT. They live only on those branches
(read here with `git -C REPO show <hash> -- .planning/phases/37-shared-runner-options-and-session-ids/` and
`git -C REPO show <hash>:<path>`, read-only), so 37-SPEC.md and 37-CONTEXT.md on this branch do not carry them, and they are
NOT edited in here (that would conflict at the next restack). They are locked decisions that this phase's plans MUST satisfy:
the 37 plans are the only place they are implemented. Where a later statement and today's 37 amendment (commit 345fdce: R13,
R14, D-31 to D-34) disagree, today's 37 amendment wins, and the item says so. Every plan's `<objective>` names the 0b items it
carries; the `Carried by` line names the plan.

### From 6eed2d0 (Phase 38: runner hardening and run safety)

- **0b-1. The sync test compares every byte; nothing is relaxed.** 37-CONTEXT D-18, amended: "*(amended 2026-11-16, 38 D-19:
  Phase 38 moves the harness to a sibling file the render does not carry, so the render stays a plain config splice and this
  test's byte comparison is never relaxed)*". 37-SPEC R8, amended: "*(amended 2026-11-16, 38 D-19: the harness leaves the runner
  file for a sibling file the render does not carry, so a rendered copy stays the template's bytes with the config block
  replaced and nothing is relaxed)*". Effect here: the R8 sync test compares every byte outside the config block with no
  relaxation hook and no "part the render keeps" logic. Carried by: 37-11.
- **0b-2. Secret files live only for the launcher's start.** 37-CONTEXT D-25, amended: "*(amended 2026-11-16, 38 D-31: the
  launcher sources the env file, opens the prompt on a file descriptor and deletes both as its first steps, so a key touches disk
  for about the launcher's start, not the lane's duration; the runner removes any remainder on every exit path it controls and
  Phase 38's sweep removes it after a hard kill; what is not guaranteed is stated in 38 R12)*". Effect here: the R12 launcher's
  first steps are: source `env`, open `prompt` on a file descriptor, delete both; the runner removes any remainder on finish,
  deadline, signal, spawn error and the `exit` handler. Carried by: 37-19 (the launcher text and its first steps), 37-20 (remainder removal on every exit path).
- **0b-3. The run record is `run.json`, written first.** 37-CONTEXT D-26, refined: "*(refined 2026-11-16, 38 D-25 to D-27, D-33:
  the record is the file `run.json` in the run directory (fields in 38 R12), written before the env file and the tab; the sweep
  adds the read-only `herdr tab list` to the three verbs of D-22 and closes a tab only when a dead run's record and a listed tab
  agree on id and complete label; the label grammar is unchanged)*". The fields, 38-SPEC R12 "Run record": "Before any other
  file of a run directory, the runner writes `run.json` (UTF-8 JSON, mode 0600, by temp file and rename): version, run token,
  runner pid, runner start time (read as R3 reads it, `-` when neither source reads), host name, checkout root, role, runtime,
  the label `aikit:<role>:<runtime>:<token>` of 37 R12, the tab id and pane id (null until `tab create` answers), the launcher
  pid and its start time (null until the `pid` file appears) and the creation time. The runner rewrites it the same way when
  `tab create` answers (before the launcher line is typed) and when the launcher pid is first read. Order of creation: record,
  then env file and prompt, then the tab. The record never holds a secret." Decision (plan time): 37 writes `run.json` with
  this field set, because D-26 makes the record 37's ("37 writes the record and closes by id") and a tab 37 opens without the
  record could not be swept; the start times are read from `/proc/<pid>/stat` (field 22) and written as `-` when unreadable.
  Phase 38 adds the lock, the sweep and `herdr tab list`, which read it; 37 calls only `tab create`, `pane run` and `tab
  close`. Carried by: 37-19 (`run.json` writer, fields, creation order), 37-20 (the rewrites when `tab create` answers and when the launcher pid is first read).
- **0b-4. Live answers for the hosted lane.** 37-CONTEXT open questions, answered: "*(Answered or narrowed 2026-11-16, 38 re-run
  2, live on herdr 0.9.5: `tab close` ended the launcher and its plain and `nohup` children but a `setsid` grandchild survived,
  the same limit as a headless group kill; polling the files costs 0.18 % of a core at 100 ms and 0.08 % at 250 ms, so 250 ms
  is the starting interval; the `pid` file holds the launcher's pid, which is also its process group id, with its start time
  read by the runner from `/proc`; fish, nushell, a pane not at a prompt and macOS stay open for the plan.)*" Effect here: poll
  interval 250 ms; `pid` holds the launcher pid (= its process group id); the lane's own kill path signals that group; the
  `setsid` limit is stated in the SKILL text; fish, nushell and macOS stay unverified and stated. Carried by: 37-20 (250 ms poll, group kill), 37-21 (the stated limits in the SKILL text).
- **0b-5. The status-line group and the self-test interface stay where 38 can extend them.** 37-CONTEXT handoff to Phase 38,
  amended: "*(amended 2026-11-16, 38 D-15, D-19: the move is a sibling file, the planner's report lines stay the settings report
  and the watchdog and lock print their own notices; this phase adds the status line keys `coverage=` and `findings=` after the
  37 group)*"; 38-SPEC R8: "The case list, names, kinds and order, `STATUS_HEAD_RE`, the sample lines in
  `skills/ai-kit-cross-ai/SKILL.md` and `launch-and-wait.md`, and `tests/cross_ai_selftest.py`'s interface stay as Phase 37
  leaves them". Effect here: the 37 group (`session= applied= ignored= unknown= escalate=`) sits after `attempts= cycles=` and
  before `retry_after_s=` (D-12), so 38 appends after it; new self-test cases are declared in the existing case table with the
  existing shape (no second registration path), so 38 can move the harness as a block. Carried by: 37-06 (group position and `STATUS_HEAD_RE`), and every plan that adds a self-test case.
- **0b-6. The runner's herdr verbs.** 37-SPEC Constraints, amended: "*(amended 2026-11-16, 38 D-27: Phase 38's sweep of a killed
  run's directory also calls the read-only `tab list`; a live lane's screen, status and wait output are still never read)*".
  Effect here: 37's transport calls exactly `tab create`, `pane run`, `tab close`; an arch or unit rule that pins the verbs pins
  these three and 38 extends it with `tab list`. Carried by: 37-19 (the arch rule pins the three verbs), 37-20 (the transport).

### From 4014a05 (Phase 38.1: runner error classification and retry policy)

- **0b-7. Per-host context forms (supersedes D-15's "every other runtime no_form").** 37-CONTEXT D-15, refined: "**Refined
  2026-11-16 (38.1 D-17):** the per-host context forms, checked live against each host's own help and one zero-token config
  parse (...): copilot `--context <tier>` with the values `default` and `long_context` (verified from its help; the earlier
  "copilot context form unknown" is stale); codex `-c model_context_window=<integer tokens>` (the key is real and typed: `-c
  model_context_window=abc` is rejected as "expected i64" by the config parser, an unknown key is accepted silently; verified
  key, the effect on a given model's window unverified); cursor the bracket `context=<label>` key (verified help example, its
  meaning per model unverified); claude has no model-context flag in its help (`--autocompact <auto|tokens>` sets the
  auto-compact window, a different thing, and the `[1m]` model suffix is not in the help, so it stays an `unverified_form`);
  opencode, pi and grok show no context form (`no_form`)." Today's 37 D-34 wins on grok: no grok row, form or fixture is
  added. Carried by: 37-05.
- **0b-8. `bad_value` joins the closed setting-reason list.** 37-CONTEXT D-14 and 37-SPEC R2, amended: "*(amended 2026-11-16,
  38.1 D-17, D-30: and `bad_value`, a context label outside the form's value kind)*". The locking test counts it (with
  `no_herdr`, `host_failed`). Carried by: 37-04 (the list), 37-05 (first emitter), 37-21 (the SKILL.md table and the three-way lock).
- **0b-9. Recorded help for every host, and a flag test (D-30).** 37-CONTEXT D-30 (added by 4014a05, renumbered by ab50e41;
  absent on this branch): "Every host's setting forms are recorded help, labeled, and a test fails when a row names a flag the
  record lacks. ... **Executed by this phase's plan** (it adds the row fields and `--describe`; Phase 35's plan builds the
  opencode-only help-fixture test first, this plan extends it, and Phase 39 only reads the forms). The plan: (1) records
  `tests/fixtures/cli_help/<host>.txt` (and the subcommand helps the formulas use: codex `exec`, `exec resume`, opencode `run`)
  for every host that has a runner row or a recorded form (claude, codex, cursor-agent, copilot, opencode, pi, grok), each with
  its version and date in a header, no account, key or path; (2) extends 35's flag test so every flag a row's effort, session or
  context form uses must appear in that host's recorded help, a planted stale flag fails it, and a host with no recorded help
  fails the test rather than passing silently; (3) adds the context form per host from the D-15 refinement: the row names the
  flag or key, its value kind (`label`: cursor passes the label into the bracket; `enum`: copilot takes `default` or
  `long_context`; `tokens`: codex takes integer tokens, accepting `<n>`, `<n>k` or `<n>m` and converting), and its label
  (...); a label outside the form's value kind is reported `ignored` with the new reason `bad_value` (...) and never fed (...).
  The phase's spike (D-17) refreshes the recorded helps and the codex key probe (`-c model_context_window=<non-integer>` against
  a scratch `CODEX_HOME`, zero tokens)." 37-SPEC acceptance (added): "Every host's effort, session and context forms are checked
  against its recorded help with a source label, and a stale flag, a missing record or an out-of-kind context label fails a
  test (R2)." Today's 37 wins in three places: (a) no grok fixture (D-34); (b) the flag test also covers the skill and MCP forms
  of R13 and R14 (`--skill`, `--mcp-config`, `--strict-mcp-config`, `--additional-mcp-config`; 37-DISCUSSION-LOG update
  2026-11-21, handoff 38.1 item 3); (c) LIVE FACT for the layout: phase 35's fixtures are a directory per host
  (`tests/fixtures/cli_help/opencode/help.txt`, `run-help.txt`, `models-help.txt`), so the plan follows that layout
  (`tests/fixtures/cli_help/<host>/help.txt` plus `<sub>-help.txt`) instead of D-30's `<host>.txt` wording. Carried by:
  37-02 (fixtures and the test, before the row forms), 37-01 (refresh and the codex key probe).
- **0b-10. `--describe` stays open to a later `classes` key; the status line does not grow from 38.1.** 37-CONTEXT handoff to
  38.1, amended: "*(amended 2026-11-16, 38.1 D-21: the status line gets no new key from 38.1; the report line gains `check=`;
  the runner's `--describe` gains a `classes` list; 38.1 adds the class `bad_request`, apart from this phase's setting
  reasons.)*" Effect here: `--describe` prints one JSON object whose top-level keys 38.1 can extend (37 emits no `classes`
  key); the setting-reason list stays disjoint from error class names (38.1 D-02 checks disjointness). Carried by:
  37-17.
- **0b-11. The spike records claude's execute output channel.** 37-CONTEXT open question, added: "*(added 2026-11-16, 38.1
  D-20)* Which stream and format does claude's execute formula print a usage limit on (the review formula uses
  `--output-format json`, where a limit is a JSON result on stdout; a text format would put it on stdout as plain text)? Record
  it in the spike so Phase 38.1's stdout rows match the formula this phase chooses." Carried by: 37-01 (records it), 37-10 (the formula's output format).

### From ab50e41 (Phase 39: lane capability blocks and lens skills)

- **0b-12. The planner stays open to one more result and one more row field.** 37-CONTEXT handoff to Phase 39, amended:
  "*(amended 2026-11-16, 39 D-02, D-11: Phase 39's plan, which runs after this one, adds to the planner a `capabilities` result
  (write, shell, skills, mcp, each with a label) printed as one more `--print-argv` line and listed by `--describe`, and one
  more setting `--skill-path`; this phase's planner must stay open to a row field per setting so that addition is a row field
  and a function, not a rewrite. A context form applied by this phase's rows makes the lane's window `unknown` for 39's size
  check unless the user stated one.)*" 39-SPEC R3: "Phase 37's pure planner (D-11) also returns `capabilities`, computed by one
  pure function over the row, the role and the final argv (including flags added by `extraArgs`)". Effect here: `planSettings`
  dispatches one handler per setting name over a row field per setting; the final argv (formula + settings + `extraArgs`) is
  assembled in one place that a later pure function can read; `--print-argv` output is line-oriented with a named prefix per
  line so one more line does not break its readers; `--describe` lists row fields generically. Today's 37 wins on `--skill-path`:
  it is 37's setting now (R13, D-31), so 39 adds only `capabilities`. Carried by: 37-04 (the planner shape), 37-17 (`--describe` keyed by setting).
- **0b-13. Skill delivery format and the split with 39 (39 R5, R6, D-10, D-11 superseded in part).** 39-SPEC R6: "a repeatable
  runner setting `--skill-path <dir>` joins Phase 37's settings report: it is `applied` only where the row has a form with a
  source label, `ignored` with `no_form` or `unverified_form` otherwise, and the path must lie inside the working tree or a skill
  root (the same check as R8). Forms: pi `--skill <path>` (...); claude, copilot and cursor-agent `--add-dir <path>` (...
  `unverified_form` ...); codex, opencode and the others none." 39 D-11: "the runner holds a plain-Node copy of the
  control-character and root rules, and one shared fixture pins it equal to the Python validator (D-13)." 39-SPEC R5 / D-10:
  inlined "from its file (SKILL.md body), inside a delimited section with its path and sha256", "byte-equal to the file".
  Today's 37 wins: R13 and D-31/D-32 take the setting (plus `--skill-name` and the prose form) into this phase; cursor-agent's
  skill forms are `unknown` (`no_form`), not `unverified_form`; the repository-or-skill-root check stays the caller's
  validator (37 R13: "the repository-or-skill-root check is the caller's validator, Phase 39 R8"; 39 D-11's plain-Node copy is
  39's choice), so the runner checks only the control character, the directory, `SKILL.md`, strict UTF-8 and the size cap; the
  inlining moves from 39's composer into the runner in 39 D-10's format, and 39 reads `form=`. Carried by: 37-13.
- **0b-14. Grok fixtures and forms in later amendments are superseded.** 38.1's carried amendment lists grok in the help
  fixture list (D-30), in the D-15 refinement and in the R2 host list. Today's 37 D-34: "no grok help fixture, form, probe,
  session row, test or list entry is added, including in a recorded-help fixture list a later unit's carried amendment names
  (38.1 D-30 lists grok for `tests/fixtures/cli_help/`; that entry is superseded too, handed to 38.1 below)." Carried by: every
  plan (no grok line added; verified in the phase verification by counting added lines naming grok outside `.planning/`).

## 0c. Orchestrator corrections to sections 1 to 3 (plan time, 2026-11-21; these win over the text below)

- **Plan numbering.** Section 3's labels map to plan ids: P01 37-01 (spike, orchestrator), P02 37-02, P03 37-03, P04 37-04,
  P05 37-05, P06 37-06, P07 37-07, P08 37-08, P09 37-09, P10 37-10, SYNC 37-11, PY1 37-12, P11 37-13, PY2 37-14, P12 37-15,
  PY3 37-16, P13 37-17, PY4 37-18, P14 37-19, P15 37-20, DOCS split into 37-21 (`skills/ai-kit-cross-ai/SKILL.md`,
  `references/launch-and-wait.md`, the doc-contract tests and the three-way reason lock) and 37-22 (`cross-ai-dispatch.md`,
  curated-config `references/runner.md`, READMEs, the hardcoding baseline shrink), SHIP split into 37-23 (installer re-render of
  the live copy, `make check-dogfood`, the shard time re-record; cross-AI) and 37-24 (the judge loop, orchestrator, `cross_ai:
  false`, `autonomous: false`, mirroring 36-29). The new arch rule (no jev client; only the three herdr verbs) moves from P15
  into 37-19, so 37-20 stays inside the lane budget. Waves as in section 3 with 37-21 and 37-22 in wave 16, 37-23 in wave 17 and
  37-24 in wave 18.
- **copilot session (rejects Assumption A3).** SPEC R7 is locked: "For a `chosen` host the runner uses the given id, or a
  generated UUID when none is given." copilot is `chosen` (D-03), so it gets a generated UUID when the call names none, exactly
  like pi, and `session=` prints that id. Section 1.0's seed row and 1.7's copilot sentence are superseded.
- **claude context (corrects section 1.0).** 0b-7 quotes the locked refinement: the `[1m]` model suffix "stays an
  `unverified_form`". The claude row records `context: { kind: 'id-suffix', ..., label: { state: 'unverified', source: ...
  '[1m] suffix not in --help' } }` and a claude `--context` is reported `ignored reason=unverified_form` and never fed (not
  `no_form`).
- **Runtime id charset (corrects section 1.4).** SPEC R4 edge: "Runtime ids match exactly and case-sensitively: `Claude` is an
  unknown id and needs `--argv-file`". So `--runtime` accepts `^[A-Za-z0-9][A-Za-z0-9-]{0,31}$` (uppercase allowed) and an id
  absent from `RUNTIMES` (such as `Claude`) without `--argv-file` gets the named refusal, never a charset error.
- **Spike and the real HOME (Open Questions 1 and 2, Assumption A4).** The run rail forbids touching the real `~/.claude`,
  `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi`, `~/.gsd`; D-17 asks for live calls "in a scratch repository". 37-01 is
  written strict by default: the `--help`/`--version` refresh (no model call) and the codex key probe against a scratch
  `CODEX_HOME` always run; the probes that make a host read or write its real config (claude, opencode and pi session resume,
  claude permission and skill probes, the copilot skill probe) run only when the orchestrator has written a ledger line
  `p37-spike real-home: allowed` before 37-01 starts (owner consent); otherwise each is recorded `not probed` and its labels stay
  `unverified`. 37-10's default permission flag, when the probe did not run or both flags worked, is `--permission-mode
  bypassPermissions` labelled unverified (R6 allows an unverified formula with the note); a probe in which neither flag wrote
  the file keeps `exec: null` and stops 37-10 with a report.
- **Accepted assumptions:** A1 (`k` = 1000, `m` = 1000000), A2 (`FILE_READ_MAX = 65536`), A5 (claude `minted`, D-03), A6
  (`--role` emitted by Python, D-02), A7.
- **Plan 37-26 (added 2026-11-21).** Curated-config's own closed effort set (`cross_ai.EFFORT_LEVELS`, used by `exec_effort` and `plan_io._validate_effort`) goes in 37-26 (wave 13, after 37-14 and 37-16); the `RUNNER_IDS` gates stay an owner-recorded deferral.
- **Other SKILL.md files.** D-16: `skills/ai-kit-cross-ai/SKILL.md` is the one SKILL.md that changes. 37-22 edits another
  SKILL.md only where a sentence there becomes false, and lists it so it joins the judge loop of 37-24.


## Section 1. Design per requirement

### 1.0 Cross-cutting data shapes (decide once; every plan copies from here)

**Row additions** (JS, inside each `RUNTIMES.<id>` row, beside the formula closures; label strings carry `model-example:` only if they name a model, which they must not):

```js
forms: {
  effort:  { kind: 'flag'|'config'|'id-suffix'|'id-bracket'|'none', flag: '--effort', key: null,
             label: { state: 'verified'|'unverified'|'unknown', source: '<host> <version> --help <date>: "<help line>"' } },
  session: { style: 'chosen'|'minted'|'none', flag: '--session-id' /* chosen only */, resumeFlag: '--resume' /* doc only */,
             label: {...} },
  context: { kind: 'flag'|'config'|'bracket'|'none', flag: '--context', key: 'model_context_window',
             valueKind: 'enum'|'tokens'|'label'|null, values: ['default','long_context'] /* enum only */, label: {...} },
  skills:  { name:  { form: '/<name>', state, label }, path: { flag: '--skill', state, label }, prose: { state: 'verified', label } },
  mcp:     { flag: '--mcp-config', after: ['--strict-mcp-config'], state, label } | null,
},
```
The formulas stay closures; additions travel as `ctx.adds = { session: [], effort: [], context: [], skills: [], mcp: [] }`, and each formula spreads the relevant arrays at a FIXED position (so golden argv is stable and `reviewArgvProblem` still compares against `rt.review(model, ctx)`). With no setting named every array is empty and the argv is byte-equal to today (acceptance of R13/R14 and of "no flag gives byte-equal argv").

**Seed values** (all `state` and `source` strings below are labels written into the rows; none decides anything):

| Host | effort | session | context | skills name / path | mcp |
|------|--------|---------|---------|--------------------|-----|
| claude | flag `--effort <level>` verified (help: "low, medium, high, xhigh, max") | minted; resume `--resume <id>`; state `unverified` until spike | none (`no_form`; the `[1m]` suffix is not in help: `unverified_form` is NOT used because no form is recorded; report `no_form`) | name `/<name>` unverified; path unverified | `--mcp-config <file>` + `--strict-mcp-config` verified |
| codex | config `-c model_reasoning_effort=<level>` verified | minted; `exec resume <id>`; `mode_forbids` for review and `--codex-sandbox` | config `-c model_context_window=<tokens>` value kind `tokens`; key verified by 38.1's config parse, effect on a window unverified | unknown / unknown | `unverified` (`unverified_form`) |
| copilot | flag `--reasoning-effort <level>` verified | chosen `--session-id <id>`, fed only when the caller passes an id (no generated id; `session=-` otherwise); help-only | flag `--context <tier>` value kind `enum` `default|long_context`, verified from help | name unverified; path unverified (`--add-dir <dir>` with `<dir>/.github/skills`) | `--additional-mcp-config @<abs file>` verified |
| cursor | id-bracket `[effort=<level>]` merged into the id's own bracket; verified (help example) | minted; `--resume <id>` (present in `resume`) | bracket `context=<label>` value kind `label`; meaning per model unverified | unknown / unknown | none (`no_form`) |
| opencode | id-suffix `#<variant>` | minted `--session <id>` until the spike rule says otherwise | none | unknown / unknown | none |
| pi | flag `--thinking <level>` (skipped when the id carries `:level`) | chosen `--session-id <id>` (runner always feeds one: caller's or generated UUID) | none | name unknown (reported `mode_forbids`: formulas pass `--no-skills`); path `--skill <dir>` verified | none |

Prose (inlined block) is `verified` for every runtime. A label's `source` string names the host version and date from the 2026-11-21 help read of the SPEC (claude 2.1.330, codex 0.170.0, opencode 2.3.2, pi 1.5.2, copilot 1.0.112, cursor-agent 2026.11.13) [CITED: 37-SPEC.md "Live help facts for R13 and R14"].

**Closed lists** (JS consts, exact spelling, one `SETTING_REASONS` array and one `SETTING_NAMES` array, both printed by `--describe`):
- reasons: `no_form`, `id_carries`, `unverified_form`, `mode_forbids`, `no_slot`, `recorded_only`, `no_provider_form`, `bad_value`, `no_herdr`, `host_failed` (ten; `bad_value` from the 38.1 amendment, `no_herdr`/`host_failed` from D-28).
- names: `model`, `provider`, `role`, `effort`, `context`, `session`, `escalate_runtime`, `escalate_model`, `host`, `skill`, `mcp` (eleven).
- states: `applied`, `ignored`, `unknown`.

**Settings line format** (stderr, before the spawn, one per entry, each passed through control-character strip `/[\x00-\x1f\x7f-\x9f]/g` then `redactSecrets`):
- generic: `cross-ai: setting <name>=<value> <state>` then ` reason=<code>` when state is `ignored` (an `unknown` entry also carries `reason=` when one applies, for example provider on codex: `cross-ai: setting provider=- unknown reason=no_provider_form`).
- skill: `cross-ai: setting skill=<name> applied form=<name|path|prose>` or `cross-ai: setting skill=<name> ignored reason=<code>`.
- mcp: `cross-ai: setting mcp=<server> applied` or `cross-ai: setting mcp=<server> ignored reason=<code>`.
- host (D-28): `cross-ai: setting host=<herdr|none> applied` / `... ignored reason=no_herdr|host_failed`, plus the separate line `cross-ai: host herdr tab=<id> label=<label>`.
- order: fixed name order of the list above; `skill` lines in call order; `mcp` lines in the file's key order. `model` and `role` always print; every other setting prints only when the call (or, for `effort`, `CONFIG.effort.<runtime>`) names it.

**Status line group** (D-12): inserted after ` attempts=<n> cycles=<n>` and before ` retry_after_s=`: ` session=<id|-> applied=<csv|-> ignored=<csv|-> unknown=<csv|-> escalate=<runtime,model|->`. List members are setting names; skill and mcp members are `skill:<name>` and `mcp:<server>` (their charsets, `[a-z0-9-]` and `[A-Za-z0-9._-]`, hold no whitespace or comma). The group is ALWAYS present like `attempts`/`cycles`. New `STATUS_HEAD_RE`: add `(?: (session=\S+ applied=\S+ ignored=\S+ unknown=\S+ escalate=\S+))?` between the attempts group and the retry group (group 1 stays `(.* action=stop)`, so every self-test status pattern that tests `parts[1]` is untouched). The status model stays the model AS CALLED (bare), see Pitfall 2.

**Size cap** (R4, R13, R14: "one cap for every file the runner reads for a call"): `FILE_READ_MAX = 65536` bytes. Reason: it equals the existing `INPUT_CAP = 65536` (cross-ai.mjs:1524), so no new magic number; a SKILL.md body under 64 KiB sits below `ARGV_PROMPT_MAX = 102400`, so one inlined skill still fits a copilot prompt; an argv file or MCP file is a few hundred bytes. Several skills over the copilot argv limit get the existing refusal.

**Strict readers** (one helper `readCallFile(flag, relPath, {cwdOnly, mode})` used by all three): open the path, `fstat` the fd (regular file only), read at most `FILE_READ_MAX + 1` bytes from the fd (over the cap is a usage error naming the flag), decode with `new TextDecoder('utf-8', { fatal: true, ignoreBOM: true })` and refuse a leading U+FEFF byte-order mark explicitly. `--argv-file` resolves relative to the cwd and must stay inside the cwd tree (`fs.realpathSync` both, then `path.relative` must not start with `..`). `--mcp-config` additionally requires `(st.mode & 0o077) === 0` (not group or world readable). A hand-rolled duplicate-key check is needed because `JSON.parse` keeps the last duplicate: a ~40-line scanner `strictJson(text)` (no dependency; the AGENTS.md precedent is the hand-rolled JSONC scanner) rejects a repeated key in any object; it is required for R14's "duplicate key is refused" and for the argv file.

**The pure planner** (JS, no fs, no env, no spawn, no clock):

```js
// planSettings(row, role, call) -> { model, adds, sessionId, resume, report, provider }
// row  : RUNTIMES[name] (or the synthesized argv-file row, see 1.4)
// role : 'review' | 'exec'            (internal; --role execute maps to 'exec')
// call : { model, effort, configEffort, context, escalateRuntime, escalateModel,
//          sessionId, skills: [{ name, path, dirName, sha256, body }], mcp: { file, servers: [name] },
//          hostSetting: { value: 'auto'|'none'|null, available: bool }, sandbox: bool }
// model   : the id the formulas receive (composed with effort/context where the row's form is an id form)
// adds    : { session: [], effort: [], context: [], skills: [], mcp: [] }  argv fragments
// sessionId: the id to use (caller's, or a generated UUID for a `chosen` row with pi semantics) or null
// resume  : true when the call's id continues a session through row.resume (role and sandbox allow it)
// report  : [{ name, value, state, reason?, form? }] in the fixed order
```
A second pure function `confirmReport(report, argv, promptPrefix)` runs after the argv and prompt prefix are built and sets `applied` only when the argv holds the flag/value (or the prefix holds the block); a planner claim the argv does not support throws an internal error (the "computed from the built argv, never from the request" rule; R13/R14 prohibition). `reportLines(report)` renders the stderr lines; `statusGroup(report, sessionId, escalation)` renders the status tail. These four are the only new top-level units besides parse helpers, so Phase 39 later adds a `capabilities` result and a row field per setting without a rewrite.

### 1.1 R1 call vocabulary

JS `parseArgs` additions (all values validated at parse; an empty value is a usage error naming the flag):
- `--role review|execute` (maps to `o.mode` `review`|`exec`); `--mode review|exec` stays; if both are given and disagree, `cross-ai: --role and --mode disagree` exit 2.
- `--effort <level>`, shape `^[a-z][a-z0-9_-]{0,15}$` (1 and 16 chars pass, 17 fails); `--codex-effort` stays as an alias (it no longer checks `CODEX_EFFORTS`); both given with different values is exit 2.
- `--context <label>`, `^[a-z0-9][a-z0-9._-]{0,15}$`.
- `--escalate-runtime`, `--escalate-model`: valueless booleans; a following non-flag token is `unknown argument` as today (a "valued escalation flag" is a usage error because the parser treats the token as an unknown argument).
- `--session-id <id>`: `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`.
- `--host auto|none`; `AIKIT_HOST` read in `main` when the flag is absent or `auto` (`none` from either source wins).
- `--skill-path <dir>` (repeatable), `--skill-name <name>` (repeatable, `^[a-z0-9][a-z0-9-]{0,63}$`), `--mcp-config <file>`, `--argv-file <path>`, `--describe` (boolean).
Python: `RunnerSpec` gains defaults-at-the-end fields `role`, `context`, `escalate_runtime`, `escalate_model`, `session_id`, `host`, `skill_paths`, `skill_names`, `mcp_config`, `argv_file` (positional callers like `RunnerSpec("opencode", "p/m", "exec", 0)` keep working). `runner_flags` becomes table-driven (a tuple of `(attribute, flag, kind)` rows and one loop) to stay under `max-branches 12`; it emits `--role execute|review` (not `--mode`), `--effort`, `--context`, `--escalate-runtime`, `--escalate-model`, `--session-id`, `--host auto` (always, per D-23), and keeps `--codex-service-tier`, `--codex-sandbox`, `--cursor-mode`, `--route-<runtime>`. It reads escalation only through `lane_settings.lane_escalation`. The hook builder (`cross_ai_build.py`) and `build-command` both go through `project_runner_command`, so one lane gives one flag list (acceptance "build-command and the hook builder emit the same flags"). `HOOK_TOKEN_RE` stays the only check in `project_runner_command` (hook-string safety).

### 1.2 R2 settings report

State rules (decided here; executors do not choose):

| name | applied | ignored (reason) | unknown |
|------|---------|------------------|---------|
| model | always `applied` (value = the model as called); if the id was composed with effort/context the value stays the called id | never | never |
| provider | pi/opencode: the part before the first `/` of the called id, `applied` | never | codex, cursor, claude, copilot: `unknown reason=no_provider_form`; `--argv-file` lane: `unknown` with no reason |
| role | always `applied` (value `review` or `execute`) | never | never |
| effort | form fed; or composed into the id | id carries a value: `id_carries` (cursor bracket `effort=`, pi `:level`, opencode `#variant`; equal values also `id_carries`); host has no form: `no_form`; argv-file lane without `{effort}`: `no_slot` | argv-file lane: never |
| context | form fed (flag, config pair or bracket key) | no form: `no_form`; label outside the value kind: `bad_value`; id already holds `context=`: `id_carries` | never |
| session | explicit id and a resume/create-or-continue form fed | resume has no form for this role/option (codex review, codex with `--codex-sandbox`): `mode_forbids`; host with `style: none`: `no_form` | never |
| escalate_runtime / escalate_model | never | always `recorded_only` | never |
| host | `--host none` or `AIKIT_HOST=none` (value `none`); herdr transport used (value `herdr`) | `auto` without herdr: `no_herdr`; hosted start failed before typing: `host_failed` | never |
| skill | `form=name|path|prose` per 1.11 | `no_form`, `unverified_form`, `mode_forbids`, `no_slot` | never |
| mcp | argv holds the flag pair | `no_form`, `unverified_form`, `mode_forbids`, `no_slot` | never |

`--print-argv` prints the same stderr lines plus one new line `cross-ai: model-id <composed id>` (used by Python `build-model-id` and the wizard preview; D-01) and exits through the normal status line. Settings lines print in the runtime path before the listing preflight and the spawn.

### 1.3 R3 effort forms

Composition (planner, per `row.forms.effort.kind`): `flag` appends `[flag, level]` to `adds.effort` (claude `--effort`, copilot `--reasoning-effort`, pi `--thinking`); `config` appends `['-c', 'model_reasoning_effort=<level>']` (codex); `id-bracket` merges `effort=<level>` into the existing bracket (cursor: `base[a=1]` becomes `base[a=1,effort=<level>]`, `base` becomes `base[effort=<level>]`; existing keys keep order, never lost); `id-suffix` appends `#<level>` (opencode) unless the id already ends in `#variant`. pi: when the called id carries a known `:level` suffix the effort is `id_carries` (the existing `piThinkingArgs` rule), else `--thinking <level>`. Precedence: call `--effort` or `--codex-effort` over `CONFIG.effort[<runtime>]` (the baked default, now valid for every runtime). The level is opaque: compared exactly, never numeric. `CODEX_EFFORTS` and `PI_THINKING` are deleted along with `knobs.codexEffort/piThinking` gating (main 12591-12595). The composed id is passed to the formulas and to the preflight; the preflight strips `modelSuffix` before the listing check as today. Old hook strings with `--codex-effort high` still work (alias).

### 1.4 R4 unknown runtime and `--argv-file`

`parseArgs` stops refusing: `--runtime <id>` accepts any id matching `^[a-z0-9][a-z0-9-]{0,31}$`; `--prefer`, `--model-<cli>`, `--route-<cli>` accept any `[a-z0-9-]+` name (only the selected runtime's value is read). `resolveRuntime` drops the `known()` gates. In `main`, an id absent from `RUNTIMES` without `--argv-file` is refused: `cross-ai: no formula for <id> in the runner; pass --argv-file, or use a runtime it has a formula for` (exit 2, status `usage`). With `--argv-file` the runner synthesizes an in-memory row `{ bins: [argv[0]], exec/review: argv from the file with placeholders replaced, list: null, parse: plain text, profiles: null, reviewExtras: [], env: {}, forms: { all none, slots from placeholders } }`. Only `{model}`, `{effort}`, `{session}` are placeholders (any `{` that is not one of the three placeholders is a usage error; there is no escape for a literal brace). The prompt goes on stdin (never argv). Settings: `{effort}` present is `applied`, absent is `ignored no_slot`; same for session and model; provider `unknown`. The file must be a non-empty JSON array of non-empty strings (empty array and empty-string element are named usage errors); element order is kept. `--classify-only` on an unknown cli uses the rows that match every cli (replace `Object.hasOwn(RUNTIMES, cli)` at 5385 and `RUNTIMES[cli].errorsUnverified` at 5400 with a guarded lookup). The Python custom launcher (`run_custom_command`) is untouched.

### 1.5 R5 model id floor

Floor regex in the runner (one const `MODEL_ID_FLOOR`): exactly today's superset `CURSOR_MODEL_ID` (cross-ai.mjs:1298: no leading dash, no whitespace, no shell character, one optional trailing `[k=v,...]` bracket), already applied at parse by `--model`; `--model-<cli>` stops choosing between `MODEL_ID` and `CURSOR_MODEL_ID` by cli name and uses the floor for every cli. The per-runtime row `modelId` grammars become the advisory: when `!rt.modelId.test(model)` print `cross-ai: note: model id shape is unusual for <runtime> (seed shape: <source>)` and continue. Remove the refusal at main:12582-12585. The live-listing `bad_model` stays (12741-12746). Python: delete `model_id_ok`, `_MODEL_ID_SRC`, `model_id_src`, the `*_MODEL_ID_SRC` constants; `project_runner_command` keeps `HOOK_TOKEN_RE` only; `run_runner` drops the 609-614 refusal (the runner's floor answers with exit 2 and a named line). `cross_ai_build.py` loses its `model_id_ok` import and the 70 branch.

### 1.6 R6 claude execute and resume

Row additions (shape in 1.0): `exec: (m, c) => ['-p', '--model', m, '--output-format', 'json', <PERMISSION>, ...adds]` where `<PERMISSION>` is fixed by the spike rule in Section 2 (Q3); `resume: (m, c, sid, mode) => [...RUNTIMES.claude[mode](m, c), '--resume', sid]`; `review` byte-equal to today's `['-p', '--model', m, '--output-format', 'json', '--permission-mode', 'plan']` (golden test pins it). The row keeps `errorsUnverified: true` until a probe record exists; the runner prints on every claude execute call `cross-ai: note: claude execute formula is unverified (no live probe record)`; a test pins the note and fails once `tmp`-recorded evidence is referenced without removing the label (the "label test": it reads a constant `CLAUDE_EXEC_PROBE_RECORD` that is `null` until the spike plan writes the date). The prompt goes on stdin as for review (`-p` reads stdin). Also remove the `exec` null refusal text path only for rows that have `exec` (main 12596 stays for rows with none).

### 1.7 R7 sessions

- Charset/length per 1.1. `chosen` rows (pi, copilot): the id is the caller's; pi additionally gets a generated UUID when none is given (`ctx.sid` already random at 4763); copilot feeds `--session-id` only when the caller names one. `minted` rows (cursor, opencode, codex, claude): first call fresh; the id printed is parsed by the row's `parse` (`sessionId`); a call WITH `--session-id` goes through `sameSessionArgv(name, rt, model, ctx, id, mode, prompt)` as the FIRST argv (prompt, not `RESUME_MSG`, is the input: "the call's own prompt is the next message").
- `mode_forbids`: codex review and codex exec with `--codex-sandbox` start fresh, print the new id and report `session ignored mode_forbids` (the `sameSessionArgv` null cases at 4092).
- Rejected id: a failed call with the host's first error line (existing classification; no silent fresh session): when the resumed first attempt fails, the runner must NOT take rung 2 (fresh) silently for an explicit id; the ladder's `canResume`/rung-2 transition is bypassed for an explicit id (one named test).
- Precedence: explicit id beats `persisted.last_sid` (4954-4964); the quota record saves the id actually used (4912 `last_sid: sid`).
- Status: `session=<id|->` is the id used, or the id the host minted (after the attempt, 5075), or `-`. A host-printed id outside the charset prints `-` with a note and is never passed back.
- Pi rung 2 (`newSessionArgv` 4098) still mints a fresh UUID, which is right for retry and wrong to hide: the status line reports the LAST id used (edge: ordering).

### 1.8 R8 sync test

New module `tests/test_cross_ai_render_sync.py` (unit group, auto-joined): scratch project dir under `tempfile.TemporaryDirectory`, call `ai_kit_gsd_curated_config.cross_ai_script.ensure_runner(project_dir)` (the installer's function, `cross_ai_script.py:358`) with `AI_KIT_REFUSE_REAL_HOME=1` and a scratch HOME, then assert `script_state(copy) == "pristine"`, `template_version` equal, bytes equal outside the config block (use the same splitter as `tools/check_dogfood.py:_outside_config`; import it by path, do not read `.planning/`), then run template and copy through the same `--print-argv` matrix (one call per runtime x role from `{pi, opencode, cursor, codex, claude, copilot}` x `{review, execute}` where a formula exists, plus an effort call, a session call, an `--argv-file` call) and require equal stdout+stderr (after dropping nothing: both run with the same cwd and env). Non-vacuity: a copy with one changed byte outside the config block fails; a copy whose config block hides a code change (insert code between `// <config>` and `// </config>`) fails; a config-only edit passes. The test needs node; skip with `skipTest` when absent like the shard modules. No grok entry in the matrix.

### 1.9 R9 `--describe` and the Python facts

`--describe` JSON (stdout; the status line still ends stderr; no stdin read; no model call; offline):
```json
{ "schema": 1, "template_version": 9,
  "settings": ["model","provider","role","effort","context","session","escalate_runtime","escalate_model","host","skill","mcp"],
  "reasons": ["no_form","id_carries","unverified_form","mode_forbids","no_slot","recorded_only","no_provider_form","bad_value","no_herdr","host_failed"],
  "states": ["applied","ignored","unknown"],
  "runtimes": { "<id>": { "formulas": {"exec": true, "review": true, "resume": true},
      "listing": ["models"], "source": "<row label>",
      "effort": {"kind": "...", "flag": "...", "label": {"state": "...", "source": "..."}},
      "session": {"style": "chosen|minted|none", "label": {...}},
      "context": {"kind": "...", "valueKind": "...", "label": {...}},
      "skills": {"name": {...}, "path": {...}, "prose": {...}},
      "mcp": {...} | null } },
  "host": {"available": false} }
```
Keys sorted; runtime ids sorted; `host.available` read from `HERDR_ENV` and PATH without calling herdr. The 38.1 amendment says `--describe` gains a `classes` list: 37 emits NO `classes` key (an empty list would assert "no classes", a false fact; 38.1 adds the key); the golden file test pins the absence with a comment. Golden file `tests/fixtures/runner_describe_golden.json` is generated by the plan and compared in a unit test.
Python: new module `ai_kit_spec/runner_facts.py` (keeps `detection.py` at 1583 lines out of it): `read_runner_describe(node, template_path)` runs `node <template> --describe`, `fact = {"template_sha256": sha256(template bytes), "describe": <json>}`; `build_runtimes_snapshot` stores it under `snapshot["runner"]`; refresh when the stored sha differs (D-10) as well as by age; routing gets pure helpers `runner_has_exec(fact, runtime)`; `route()` maps "fact present and says no exec formula and the lane has no command" to `no_formula`; an absent/unreadable/stale fact never refuses. `unknown_runtime` and `no_inventory` stop refusing at routing: `_route_shape`'s unknown-runtime branch returns the normal inventory walk (a runtime outside `RUNTIMES` with a command is served; without a command the runner's named refusal applies at run time), `no_inventory` becomes `unverified`. Delete `exec_formula`, `ExecFormula`, `has_exec_formula`, `exec_formula_source`, `NO_RUNNER_ENTRY`, the drift test file, `SUPPORTED_EXECUTE_CLIS` derivation and rewrite `execute_cli_error` to read the fact (returns a refusal only when a fact says no exec formula; unknown or absent fact returns `None`). The grep-style test of phase 36 R7 extends to the new routes (`tests/test_no_seed_refusal.py` is the file to extend).

### 1.10 R10 escalation

Flags parse (1.1); planner reports each `recorded_only`; status `escalate=<runtime,model|->` lists runtime before model; the runner never spawns a second lane (existing "no automatic fallback" notice at main 12695 stays). `runner_flags` reads `lane_escalation(entry)` only. Test: a failing call carrying both flags ends after one spawn with the same exit codes (FAKE_CALLS count).

### 1.11 R13 skills

Parse: `--skill-path <dir>` repeatable; each resolved with `fs.realpathSync`, no control char in the raw or resolved path, directory holds `SKILL.md` (non-empty; read once; strict UTF-8; <= `FILE_READ_MAX`; sha256 over the file bytes); `dirName` = basename; frontmatter `name` read from the first `---` block when present. `--skill-name <name>` shape `^[a-z0-9][a-z0-9-]{0,63}$`. A name and a path are ONE skill when the name equals the path's `dirName` or frontmatter `name`; two paths resolving to one directory apply once; names compare exactly. Per skill, apply the first form the row has `verified` and the input supplies, order name, path, prose: `name` only for a `--skill-name` (with a matching path the order still tries name first; if the row's name form is not verified, continue to path then prose when a path exists); `path` or `prose` only with `--skill-path`. Delivery: path form adds `[flag, dir]` to `adds.skills` (pi `--skill <dir>`); prose form builds one block per skill, in call order, placed BEFORE the `--prepend-file` content and the prompt:
```
<skill name="<name>" path="<resolved dir>" sha256="<hex>">
<SKILL.md body, byte-equal>
</skill>
```
(the block text is a plan-fixed constant; the sha256 is over the file bytes). Copilot's `-p` argument carries the block under the existing `ARGV_PROMPT_MAX` check (`argvPromptProblem` runs after the block is added). pi name form is reported `mode_forbids` (formulas pass `--no-skills`) even though no name form is recorded; claude/copilot name `unverified_form`; cursor/codex/opencode name `no_form`; an `--argv-file` lane reports `no_slot` for a name and `form=prose` for a path. `reportLines` skill lines print in call order after the fixed names. The prompt composition seam is `main` 12657-12669 (`body`/`prompt`): the prose prefix goes before `prepended`. The `--print-argv` path does not read stdin, so the skill lines print there too and a prose skill prints its block size, never the body.

### 1.12 R14 MCP

`--mcp-config <file>` read once via `readCallFile` (mode check). Parse with `strictJson`; top-level object with a non-empty object `mcpServers`; server names `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`; the file itself is never rewritten; only its ABSOLUTE path reaches argv (claude `--mcp-config <abs> --strict-mcp-config`, copilot `--additional-mcp-config @<abs>`); the JSON never reaches argv, stderr or the status line; names print one per line in the file's key order. Hosts: claude applied (both review and execute; the variadic `--mcp-config` is always followed by `--strict-mcp-config`, pinned by a golden argv); copilot applied and review keeps `--disable-builtin-mcps` (the argument is added AFTER the profile flags so `reviewArgvProblem` still sees the profile prefix: add `--additional-mcp-config` to `reviewExtras` for copilot and `--mcp-config`, `--strict-mcp-config` for claude, because extras are flag + one value); pi exec `no_form`, pi review `mode_forbids` (its profile passes `--no-mcp`); codex `unverified_form`; cursor and opencode `no_form`; `--argv-file` lane `no_slot`. A planted key shape in a server's `env`, `args` or `headers` appears in no stderr line, status line or argv (test). No approval flag is ever added (cursor exec keeps its existing `--approve-mcps`; no change).

### 1.13 R12 herdr hosting (outline over `runChild`)

Functions (all new, all in the runner): `hostAvailable(env, whichFn)` (`HERDR_ENV === '1'` and `herdr` on PATH, no herdr call); `shQuote(s)` (single-quote quoting, a NUL element is a usage error); `buildLauncher(argv, paths)` returns the POSIX `sh` text; `writeRunDir(token, lane)` creates `<stateHome()>/ai-kit/spec/host/<token>/` mode 0700 holding `launch.sh`, `env` (0600), `prompt` (0600), `run.json` (written FIRST, before the env file and the tab; fields from 38 R12: read them in the quoted 0b section the orchestrator inserts), and the launcher's `out`, `err`, `pid`, `rc`; `hostedChild(bin, argv, opts)` returns the SAME result object as `runChild` (`code, signal, timedOut, limited, spawnErr, stdout, stderr`). Launcher steps in order (38 D-31): write `$$` to `pid`; source the env file; `exec 3<prompt`; `rm` env and prompt; run the argv with `<&3 >out 2>err`; write `rc` by rename (`printf '%s' "$?" > rc.tmp && mv rc.tmp rc`; a signal death writes the signal name). The runner polls `out`, `err`, `rc` every 250 ms into the same capture buffers (so the caps, heartbeat/idle clock and redaction apply unchanged), takes the exit code ONLY from `rc`, treats a dead launcher pid with no `rc` as killed by a signal, and closes the tab by id on every exit path (finish, deadline, signal, spawn error) then removes the run directory. herdr calls use `spawnSync('herdr', [...], { timeout: 5000 })` with exactly three verbs: `tab create --label aikit:<role>:<runtime>:<token> --no-focus --cwd <cwd>`, `pane run <pane> "sh <launch path>"`, `tab close <tab>`. A state-home path with a character outside `[A-Za-z0-9._/-]` gives `host_failed` before any herdr call. Failure before typing: `host ignored host_failed` and one headless run; after typing: never rerun. The status line is unchanged. The fake `herdr` for tests is a node script on the test PATH that replays the JSON shapes in 37-SPEC "Live facts added 2026-11-16 re-run 2" (`.result.tab.tab_id`, `.result.root_pane.pane_id`, `{"result":{"type":"ok"}}`) and executes the typed line; it logs every argv to a file. A new arch rule: the template names no jev client (no `jev` token outside comments) and the only `herdr` verbs it spawns are the three above; non-vacuity counterpart for each.

### 1.14 Later-unit items

- **Help fixtures + flag test (38.1 D-30).** Fixtures `tests/fixtures/cli_help/<host>/` for claude, codex, copilot, cursor, opencode (existing), pi: `help.txt` (+ `exec-help.txt` and `exec-resume-help.txt` for codex, `run-help.txt` for opencode, `skill-help.txt` for copilot where a form uses it), `version.txt`, `meta.json` (`version`, `recorded`, `commands`). No grok directory. One module `tests/test_cli_help_flags.py` generalizes `tests/test_opencode_help_flags.py`: for each host, extract the row block from the template (`  <host>: {` to the next `  },`, with the leading `//` comment lines), take every `--flag` in it, and require each to appear in the union of that host's recorded help files; a host with no recorded help directory fails (not silently passes); a planted stale flag fails; whole-token matching (reuse `FLAG_RX`). Because rows carry the forms as data, every later flag a form uses is covered automatically. A scrub test enforces 0.7. Keep `tests/test_opencode_help_flags.py` (its semantic checks stay).
- **Context forms and `bad_value`.** Value kinds: `label` (cursor: label passes into the bracket if it matches D-15), `enum` (copilot: `default` or `long_context`; anything else is `bad_value`), `tokens` (codex: `<n>`, `<n>k`, `<n>m`, converted to an integer, k=1000 and m=1000000, `1..1000000000`; else `bad_value`). `bad_value` is never fed. cursor `context=` merged like effort (keys kept). Tests: the three kinds applied, one out-of-kind label per kind ignored `bad_value`, a bracket with an existing `context=` is `id_carries`.
- **Launcher secret-file order, `run.json`, 250 ms poll, `pid` file** all per 1.13; the spike records claude's execute output channel (Section 2 Q3).
- **Capabilities openness (39 D-02, D-10, D-11).** Nothing in 37 may close the door: rows hold a field per setting (`forms.<setting>`), `planSettings` returns an object (not a bare list) so a `capabilities` member can be added, `--describe` is keyed by setting, and `--print-argv` prints settings lines through `reportLines` only (so 39 adds one more line type). `--skill-path` is 37's (R13); the inlining moved from 39's composer to the runner.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Node stdlib (`node:fs`, `node:crypto`, `node:child_process`, `node:path`, `node:os`, `TextDecoder`) | the host node (not pinned by the repo) | runner implementation | the runner is stdlib-only, rendered into projects [VERIFIED: skills/ai-kit-spec-review/references/cross-ai.mjs:69-76 imports] |
| Python stdlib (`json`, `hashlib`, `subprocess`, `tempfile`, `re`, `unittest`) | the dev env python | Python layer and tests | AGENTS.md stdlib-only runtime rule |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hand-rolled duplicate-key JSON scanner | a JSON library | forbidden (stdlib only, no dependency for a few lines) |
| herdr `wait-output` | poll files | SPEC D-24 chose files; screen text is never a verdict |

**Installation:** none. No external package is added by this phase.

## Package Legitimacy Audit

No external packages are installed or added (runner is plain Node stdlib; Python modules stdlib). `uv.lock` and `pyproject.toml` untouched. **Packages removed due to [SLOP]:** none. **Packages flagged [SUS]:** none. Audit table intentionally empty: nothing to verify.

## Architecture Patterns

### System architecture (data flow)

```
GSD hook / Python builder / caller
        |  flags: --runtime --role --model --effort --context --session-id
        |         --escalate-* --host --skill-* --mcp-config --argv-file
        v
  parseArgs  --(usage error)-->  status=usage exit 2
        v
  resolveRuntime --> row (RUNTIMES.<id> | argv-file row | refusal "no formula")
        v
  readCallFile x3 (argv-file, SKILL.md bodies, MCP file) -- strict UTF-8, cap, mode
        v
  planSettings(row, role, call) --> { model', adds, sessionId, resume, report }
        v
  build argv: formulas read ctx.adds  +  prompt = skill blocks + prepend + stdin + preamble
        v
  confirmReport(report, argv, promptPrefix)  --> settings lines (stderr, redacted)
        v
  --print-argv / --describe: print and finish        |   run: preflight listing -> spawn
                                                      v
                          runChild (headless)   or   hostedChild (herdr tab + launcher + files, rc verdict)
                                                      v
                          classify, ladder (never switches lane), parse session id
                                                      v
                          finish: AIKIT-XAI ... attempts= cycles= session= applied= ignored= unknown= escalate= [retry_after_s=]
```

### Recommended structure
```
skills/ai-kit-spec-review/references/cross-ai.mjs      # rows + forms + planner + transports (one file, serialized plans)
skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py  # NEW: describe fact reader + pure helpers
skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py  # RunnerSpec fields, table-driven runner_flags
tests/fixtures/cli_help/<host>/                          # recorded help (guard-exempt)
tests/fixtures/runner_describe_golden.json               # golden --describe
tests/test_cli_help_flags.py, test_cross_ai_render_sync.py, test_runner_describe.py,
tests/test_runner_settings_argv.py, tests/test_runner_vocabulary.py (new, unit group)
```

### Pattern: forms as data, one pure planner
Rows hold forms; `planSettings` is pure; formulas stay closures reading `ctx.adds`. Anti-patterns: a runtime-specific branch for effort in `runner_flags` (R1 forbids it); reading the host's config; deciding `applied` from the request instead of the built argv; printing an MCP value; composing an id in Python.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret redaction of setting values | a new redactor | `redactSecrets` (1600) after a control-char strip | one table kept equal to the Python one by a test |
| Render the project copy in tests | a manual splice | `cross_ai_script.ensure_runner` | the installer's own path (R8) |
| Status line parse in Python | a new parser | `parse_status_line` | keys by name, group-safe |
| Help flag extraction | a new regex | `FLAG_RX` from `tests/test_opencode_help_flags.py` | whole-token rule already proven |
| Strict UTF-8 | manual byte checks | `TextDecoder('utf-8', {fatal: true})` | stdlib |
| Process-group supervision of a hosted lane | a second supervisor | reuse the `runChild` result shape and capture buffers | classification stays one code path |

## Common Pitfalls

1. **Pylint caps on the Python plans.** `runner_flags` has to grow by about ten flags: build it from a tuple of rows and one loop (max-branches 12, max-statements 50). `RunnerSpec` is a NamedTuple (field count is not limited by `max-args`) but any function taking its pieces separately is; pass the spec. New `runner_facts.py` functions stay under 15 locals. Verify with `make pylint`, not by eye.
2. **The status `model=` must stay the model as called.** `_trailer_counts` (runner_dispatch.py:573-579) compares `status["model"]` to `spec.model`. Today `spec.model` is the composed id (Python composes). After PY1, Python passes the bare id; if the runner printed the composed id, every cursor/opencode/pi effort lane would print `ignoring a runner status line that does not match this run`. `liveFields.model` stays the called id; only argv carries the composed id.
3. **Status-line regex consumers.** `STATUS_HEAD_RE` (6099) is the only anchored consumer; self-test patterns test group 1 only. Python `parse_status_line` splits on `=`: a list value with `=` inside would break it, so member names never contain `=` (use `skill:<name>`). Update the two sample lines in `SKILL.md` and the `launch-and-wait.md` line from REAL self-test output (copy a line printed by a self-test case; never hand-write one), and keep them ASCII with every token `key=value` (`test_status_examples_parse`).
4. **One last line.** `finish` writes the line once; the hosted path and `--describe` must still end with exactly one `AIKIT-XAI` line as the LAST stderr line (`statusLineOk`). Settings lines print before the spawn; a skill line printed late would break the last-line rule.
5. **Template version.** New flags are rejected by template 8 as `unknown argument`. The plan that makes builders emit them (PY1) must bump `TEMPLATE_VERSION` (`cross_ai.py:46`), `_READY_TEMPLATE` (`cross_ai_script.py:23`), the header and comment (cross-ai.mjs:2, 4), `tests/test_cross_ai_skill_text.py:203` and the "template 8" doc text (`ai-kit-cross-ai/SKILL.md:44`, curated-config SKILL/runner.md). Do it once, in PY1, alone in its wave (it edits two mjs lines).
6. **Baseline shrink-only.** Any plan that rewrites a test line holding a model literal listed in `tests/fixtures/no_hardcoded_models_baseline.json` must remove the entry in the same commit ("fixed, remove from baseline" is a test failure). The baseline lists one `cross-ai.mjs` entry [VERIFIED: ripgrep count 1]; plans that rewrite the runner's example names update it. New tests use only `router-env/<x>`, `placeholder-model-<n>`, `fake/<token>`, `fake-<token>`.
7. **Hook token regex.** `HOOK_TOKEN_RE` allows `[A-Za-z0-9._:/@+=,#-]`: a context label with `_` (`long_context`) and a session id with `:` pass; `[` `]` do not, so a cursor bracket id stays argv-only and now stops mattering for bare ids. A skill path or MCP file path with a space or a glob character cannot ride a hook string: the builder must not emit `--skill-path`/`--mcp-config` into a hook (Phase 39 passes them argv-only).
8. **review confinement.** `reviewArgvProblem` compares the argv prefix to `rt.review(model, ctx)`: every addition must come through `ctx.adds` inside the formula or through `reviewExtras` (flag + one value). Adding after-the-fact breaks the prefix check and exits `usage`.
9. **Duplicate keys.** `JSON.parse` silently keeps the last duplicate; the strict reader needs the scanner.
10. **MCP file mode.** `fstat` the opened fd, never `stat` then `open` (TOCTOU), and check mode bits before reading.
11. **Self-test shard times.** A new case missing from `cross_ai_selftest_secs.json` weighs the median, so shards stay balanced but unmeasured; re-record once at the end (SHIP plan). A case that waits on a real clock (hosted poll, retry) is `kind: 'runtime'`; everything else `logic`. Each shard must stay under the commit budget (60 s).
12. **Self-test fakes live in the runner file** (writeFakeClaude etc.): extending a fake for session ids edits the same file, so it serializes with the other mjs plans.
13. **`cross-ai.mjs` diffs.** Plans that edit it cannot share a wave; keep each diff to one feature and keep `make test-unit`, the self-test shards, and `tests/test_cli_help_flags.py` green after each.
14. **Execute-lane unattended runs.** The live spike is not a pi-lane job (credentials, judgement); see Section 2.

## Code Examples

Sources are this repo's own code (read this session).

### Existing review-confinement seam the planner must preserve
```js
// Source: cross-ai.mjs:4540-4560 (reviewArgvProblem) and 4773-4777 (reviewProblem in runCli)
const base = sid ? rt.resume(model, ctx, sid, mode) : rt.review(model, ctx);
return reviewArgvProblem(argv, base, rt.reviewExtras || []);
```

### Formula reading additions (target shape, plan-fixed)
```js
// claude row, target (permission flag per the spike rule in Section 2, shown as <PERMISSION>)
exec: (m, c) => ['-p', '--model', m, '--output-format', 'json', ...<PERMISSION>, ...(c.adds?.effort || []),
  ...(c.adds?.session || []), ...(c.adds?.mcp || [])],
review: (m, c) => ['-p', '--model', m, '--output-format', 'json', '--permission-mode', 'plan',
  ...(c.adds?.effort || []), ...(c.adds?.session || []), ...(c.adds?.mcp || [])],
```

### Python runner_flags, table-driven (target)
```python
# Source: shape of runner_dispatch.py:213 runner_flags, rewritten as a table
_VALUE_FLAGS = (("role", "--role"), ("effort", "--effort"), ("context", "--context"),
                ("session_id", "--session-id"), ("host", "--host"))

def runner_flags(spec: RunnerSpec) -> list[str]:
    flags = ["--runtime", spec.runtime, "--model", spec.model]
    for attr, flag in _VALUE_FLAGS:
        value = getattr(spec, attr)
        if value:
            flags += [flag, value]
    ...
```
(The executor writes the real body; plan text gives the full function as FILE CONTENT.)

## State of the Art

| Old | Current | When | Impact |
|-----|---------|------|--------|
| Python composes effort into ids | runner composes from `--effort` | this phase (D-01) | hook strings can carry effort; Python composers deleted |
| closed effort sets | token shape only | this phase (D-07) | host rejects what it cannot take |
| `--mode` only | `--role` documented, `--mode` alias | this phase (D-02) | old hooks keep working |
| Python mirrors of runner tables | `--describe` fact in the runtimes snapshot | this phase (D-10) | drift test deleted |

## Runtime State Inventory

Not a rename/refactor/migration phase. One adjacent fact: the live `.planning/scripts/cross-ai.mjs` is a stored copy that must be re-rendered after the template changes (installer, then `make check-dogfood`): that is a SHIP-plan task, not an inventory category.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | codex token label conversion: `k` = 1000, `m` = 1000000 (decimal, not binary) | 1.14 | wrong window value fed to codex; owner may prefer 1024-based |
| A2 | `FILE_READ_MAX = 65536` fits every real SKILL.md the owner passes | 1.0 | a larger body is a usage error; raise the one constant |
| A3 | A copilot `--session-id` fed only when the caller names an id (no generated id) is the right reading of "chosen" for copilot | 1.7 | SPEC text allows either; status would print `-` for a plain copilot call |
| A4 | A real-HOME spike is allowed: hosts write only their own session stores; the marker audit lists them | Section 2 | rail "never touch ~/.claude..." read strictly would forbid the three primary-host probes |
| A5 | `claude` stays `minted` even though its help lists `--session-id <uuid>` | 1.0 | a chosen form would let the runner print a known id without parsing JSON |
| A6 | `--role execute` maps to internal `exec` and Python emits `--role` instead of `--mode` | 1.1 | tests asserting `--mode` in golden flags need updating (PY1) |
| A7 | Hosts' help text from the 2026-11-21 read is current for every row label | 1.0 | label dates are re-checked by the spike's help refresh |

## Open Questions

1. **Does the spike run against the real HOME?** (routed to the orchestrator before P01) A session-resume probe makes each host write its own session store under its real config directory; credentials live there too. Recommendation: run the three primary-host probes with the real HOME, `AI_KIT_REFUSE_REAL_HOME=1`, a marker file under `tmp/` and a `find -newer` audit that lists (never removes) host-owned session files; if the owner reads the rail strictly, P01 records `not probed` and every dependent label stays `unverified` (the plans still work; only labels change).
2. **Copilot skill probe.** D-17 keeps copilot fake-only; the 2026-11-21 note asks for one cheap call. Reconciliation: P01 attempts it only when `copilot` is installed and authenticated through an environment token without touching `~/.copilot`; otherwise it records `not probed` and the `skills.name` and `skills.path` labels stay `unverified` (so nothing is fed). Routed to the orchestrator: confirm "optional".
3. **Does an unattended cursor execute lane block without `--approve-mcps`?** Needs a live cursor call and a configured server; not probed, flag stays (D-33 rail). Recorded in the spike file as open for Phase 39.
4. **Do claude plan mode and copilot's review profile still run the given MCP servers' tools, and which server wins on a copilot name collision?** Needs a configured server; not probed; labels stay as the SPEC seeds. Recorded open for Phase 39.
5. **Does `tab close` end a `setsid` grandchild?** Answered by 38 re-run 2: no (same limit as a headless group kill) [CITED: 37-CONTEXT.md amendment text, 38 re-run 2]. fish, nushell and macOS stay unverified; the typed line is `sh <path>`, which any shell runs, so the risk is low.
6. **Do cursor bracket keys apply to every model it lists?** Only the help example shows them; P01 may read `cursor-agent models` (read-only listing) for variants; otherwise label stays `meaning per model unverified`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | runner, self-test, render-sync, describe | not probed here (no host/network commands per run rules); the shard modules `skipTest` when absent | the machine's node | tests skip |
| git | self-test cases | assumed present (hooks and shards already require it) | — | shard skip |
| herdr | spike only (not tests) | `HERDR_ENV=1` was set on the 2026-11-16 SPEC run | 0.9.5 then | tests use a fake herdr |
| claude, opencode, pi, copilot, cursor-agent, codex | spike only | present on this machine per `tmp/run-2026-11-19/p37-help/` captures | versions in `*-version.txt` | rows stay `unverified` |

Missing with no fallback: none. Tests never call a real host.

## Section 2. The spike (D-17) for the first plan (P01)

**Who runs it:** the orchestrator natively, NOT the pi lite lane (live credentials, judgement on outputs). Frontmatter `cross_ai: false` for this plan alone, a documented exception to the run rail ("every PLAN.md carries `cross_ai: true`") that the orchestrator must confirm (Open Question 1).

**Method (all hosts):** scratch dir `tmp/run-2026-11-19/p37-spike/` with a fresh `git init` repo `r/`; a marker file `tmp/run-2026-11-19/p37-spike/marker`; every command exports `AI_KIT_REFUSE_REAL_HOME=1`; one script per probe under `tmp/.../p37-spike/*.sh`, run as `bash <file>`; outputs to `tmp/.../p37-spike/out/`; after the run `find` over `~/.claude`, `~/.config/opencode`, `~/.pi` `-newer marker` lists new files into `out/audit.txt` (list only; host-owned session stores are expected, anything else is reported). Router-env model for pi and opencode: `router-env/my-coding` (the only literal name allowed; never print keys). Findings go to `tmp/.../p37-spike/out/` AND a committed `37-SPIKE.md` in the phase dir (the plans read this file) with, per question: command shape (no model name beyond `router-env/<x>`), observed result, date, host version, and the label that flips. Close every process and herdr tab opened; delete scratch under `tmp/` only.

| # | Live question | Probe (one cheap call each) | Answer flips |
|---|---------------|-----------------------------|--------------|
| Q1 | pi: does a second call with the same `--session-id` continue the session? | call 1: `pi -p --model router-env/my-coding --session-id <uuid> --no-skills --no-extensions --no-approve --offline` with prompt "Remember the word placeholder-token-1 and reply OK"; call 2 same id, prompt "What word did I ask you to remember?" | yes: `forms.session` label for pi `verified` (version, date); no: stays `help-only`, style stays `chosen` |
| Q2 | opencode: resume, and which caller ids are accepted | call 1 `opencode run --model router-env/my-coding --format json --standalone`, parse `sessionID`; call 2 with `--session <id>` and the memory prompt. Id shapes, each as a caller-chosen first call: `ses_` + 16 alphanumerics, a UUID, a plain `placeholder-id-1`; record accepted/rejected and the behaviour on a rejected id (error line versus silent new session) | resume works: label verified. Rule (plan-fixed): the row becomes `chosen` with an `idShape` only if ALL THREE shapes are accepted and a rejected id (a fourth shape such as `bad id!`... run only if shapes pass) is visible; otherwise it stays `minted`; the matrix is recorded either way |
| Q3 | claude: resume, permission flag under `-p`, execute output channel | (a) call 1 `claude -p --model <alias> --output-format json` (alias from the owner's session default; never printed), parse `session_id`; call 2 with `--resume <id>`. (b) in `r/` ask "create file a.txt containing ok and stop" under `--permission-mode bypassPermissions`, then under `--dangerously-skip-permissions`; record whether the file exists, the refusal text if any, and whether `-p` refuses either flag in any setting (e.g. a root or sandbox check). (c) a zero-token bad-model call `--model not-a-real-model` to see the stream and format of an error (stdout JSON versus stderr text) | resume: label verified/stays unverified. Permission flag rule (plan-fixed): the first of [`--permission-mode bypassPermissions`, `--dangerously-skip-permissions`] that wrote the file unattended; both work: `--permission-mode bypassPermissions` (named mode, parallel to the review formula's `--permission-mode plan`; the other flag's help says "recommended only for sandboxes"); neither works: the claude row keeps `exec: null`, report to the orchestrator (R6 blocked). Output channel recorded for 38.1 (answers the 2026-11-16 open question) |
| Q4 | claude: does `/<name>` resolve an installed skill in `-p`? | scratch project skill `r/.claude/skills/placeholder-skill-1/SKILL.md` ("reply with the word placeholder-token-2"), call `claude -p "/placeholder-skill-1"` in `r/` | yes: claude `skills.name` `verified`; no: stays `unverified` |
| Q5 | copilot: does `--add-dir <dir>` load `<dir>/.github/skills`? | optional (Open Question 2): one cheap `copilot -p ... --add-dir <scratch>` when installed and authenticated by env token | yes: copilot `skills.path` `verified`; otherwise `unverified` |
| Q6 | codex: is `model_context_window` a typed key? | `CODEX_HOME=<scratch dir> codex -c model_context_window=abc debug models`, zero tokens (the 38.1 parse is `expected i64`); scratch `CODEX_HOME` empty | records the error text; the `context.codex` label stays "key verified, effect unverified" |
| Q7 | help captures refresh | `<host> --version`, `<host> --help` for claude, codex, copilot, cursor-agent, opencode, pi; subcommand helps `codex exec --help`, `codex exec resume --help`, `opencode run --help`, `copilot skill --help`; no model call. Copy to `tests/fixtures/cli_help/<host>/` happens in P02, from `out/`, after the scrub of 0.7 | label dates and versions in the rows |
| Q8 | cursor bracket keys | optional read-only `cursor-agent models` listing | context/effort label wording only |
| Q9 | herdr hosting (optional) | with `HERDR_ENV=1`: a `tab create` + `pane run "sh <launch>"` + `tab close` round trip using a throwaway launcher under `tmp/`, confirm `rc` and tab closure; also check `sh <path>` typed into the pane's own shell | confirms D-24 shape; no row label |

Not probed, recorded as open (Open Questions 3-4): cursor `--approve-mcps` necessity; claude plan-mode and copilot review-profile MCP behaviour; copilot MCP name collision. The spike writes the planned label flips as a table (`row.field -> new state, source`) that P04, P05, P10, P11, P12 read when writing label strings; their plan text carries the DEFAULT (unverified) label and a one-line rule "if 37-SPIKE.md says X, use label Y", so the executor chooses nothing.

## Section 3. Proposed plan decomposition

Plans are small: about 3 tasks, one logical feature, tree green after each; every plan's verify runs `make ruff`, `make pyright`, `make vulture`, `make pylint` plus its quick commands. `[mjs]` = edits `cross-ai.mjs` (cannot share a wave with another `[mjs]` plan). 21 plans; P04+P05 and PY2+PY3 are the merge candidates if the planner needs 19.

| Plan | Wave | Feature | Files | Carries |
|------|------|---------|-------|---------|
| P01 | 1 | Live spike + `37-SPIKE.md` + help capture refresh (orchestrator-run, `cross_ai: false`) | `tmp/run-2026-11-19/p37-spike/*`, `37-SPIKE.md` | D-17, open questions |
| P02 | 2 | Help fixtures for six hosts + `tests/test_cli_help_flags.py` + scrub test; extend `tools/record_cli_help.py`? NO (tool untouched; captures come from P01) | `tests/fixtures/cli_help/<host>/*`, `tests/test_cli_help_flags.py` | 38.1 D-30, R13/R14 fixture lock |
| P03 | 2 | `[mjs]` parse the whole vocabulary + strict file readers + usage-error self-test cases (parse-only: values stored in `o`, not yet acted on); remove the closed effort sets' parse check | `cross-ai.mjs` | R1, R4 parse, R13/R14 parse, R3 shape |
| P04 | 3 | `[mjs]` planner v1: `SETTING_REASONS`/`NAMES`, `forms.effort` + `forms.escalate`, `planSettings` for model, provider, role, effort, escalation, `confirmReport`, `reportLines`, formulas read `ctx.adds`, `--print-argv` prints lines and `model-id` | `cross-ai.mjs`, `tests/test_runner_settings_argv.py` (new) | R2, R3, R10 |
| P05 | 4 | `[mjs]` planner v2: `forms.context` with value kinds and `bad_value`, `forms.session` (chosen/minted, resume formulas incl. copilot `--session-id`), codex/cursor/opencode/pi/claude seeds | `cross-ai.mjs`, `tests/test_runner_settings_argv.py` | R2, R7 forms, 38.1 context |
| P06 | 5 | `[mjs]` wire the planner into `main`/`runCli`: settings lines before spawn, status group, `STATUS_HEAD_RE`, status model stays as called, `CONFIG.effort` for every runtime; self-test cases (applied/ignored/id_carries/escalate) | `cross-ai.mjs` | R2, R3, R10 |
| P07 | 6 | `[mjs]` sessions at runtime: first-argv resume, `last_sid` precedence, minted id out, rejected id never falls to a fresh session, `mode_forbids`; extend fakes with session ids | `cross-ai.mjs` | R7 |
| P08 | 7 | `[mjs]` gates become facts: id floor + advisory, `--prefer`/`--model-<cli>`/`--route-<cli>` any name, `resolveRuntime` without `known()`, `--classify-only` generic, named refusal without argv file | `cross-ai.mjs` | R4, R5 |
| P09 | 8 | `[mjs]` argv-file lane: synthesized row, placeholders, `no_slot`, supervision, tree check, self-test cases | `cross-ai.mjs` | R4 |
| P10 | 9 | `[mjs]` claude exec + resume formula, unverified note, label test, byte-equal review argv | `cross-ai.mjs` | R6 |
| SYNC | 9 | render-sync test (parallel with P10: Python-only) | `tests/test_cross_ai_render_sync.py` | R8 / RUN-06 |
| PY1 | 10 | Python vocabulary: `RunnerSpec` fields, table-driven `runner_flags` (`--role`, `--effort`, `--context`, `--escalate-*`, `--session-id`, `--host auto`), builder parity, template + readiness version bump to 9 (alone in its wave; edits mjs header only) | `runner_dispatch.py`, `cross_ai_build.py`, `cross_ai.py`, `cross_ai_script.py`, header lines 2 and 4 of `cross-ai.mjs`, affected tests | R1, R3 handoff, Pitfall 5 |
| P11 | 11 | `[mjs]` skills (R13): row skills forms, `--skill-*` delivery, prose block, pi `--skill`, report lines, copilot cap | `cross-ai.mjs` | R13 |
| PY2 | 11 | delete Python composers and closed sets: `build_*_model_id`, `effort_form`, `RUNNER_*` mirrors, `effort_probe` and `build-model-id` read `--print-argv` `model-id`; grep-style test | `commands.py`, `lane_effort.py`, `effort_probe.py`, `cli.py`, `runner_dispatch.py` (`spec_with_effort`), tests | R3, D-01 |
| P12 | 12 | `[mjs]` MCP (R14): rows mcp, strict reader mode check, claude/copilot flags, redaction tests | `cross-ai.mjs` | R14 |
| PY3 | 12 | delete the grammar mirror: `model_id_ok`, `_MODEL_ID_SRC`, `*_MODEL_ID_SRC`, `model_id_src`; `run_runner`, `cross_ai_build.py`, tests | `runner_dispatch.py`, `cross_ai_build.py`, tests | R5 |
| P13 | 13 | `[mjs]` `--describe` + golden file + reason/name lock between runner source and `--describe` | `cross-ai.mjs`, `tests/fixtures/runner_describe_golden.json`, `tests/test_runner_describe.py` | R9 runner side |
| PY4 | 14 | `runner_facts.py`, snapshot field with sha, routing reads the fact, delete `exec_formula`/drift test/`unknown_runtime`/`no_inventory`/`SUPPORTED_EXECUTE_CLIS` derivation, rewrite `execute_cli_error` | `runner_facts.py`, `detection.py`, `routing.py`, `commands.py`, tests | R9 |
| P14 | 14 | `[mjs]` herdr launcher builders + run dir (pure: quoting, launcher text, modes, run.json, label grammar, fixture test of file names) | `cross-ai.mjs`, `tests/test_runner_host_protocol.py` | R12 part 1, D-27 |
| P15 | 15 | `[mjs]` hosted transport + fake herdr self-tests (hosted == headless, every exit path closes the tab, modes, secret never in typed line) + arch rule with non-vacuity counterparts | `cross-ai.mjs`, `tests/test_arch.py` | R12 part 2 |
| DOCS | 16 | `ai-kit-cross-ai/SKILL.md` (vocabulary, report, `session=`, groups, reasons table, argv-file, `--host`, skills, MCP, trailing provenance), `references/launch-and-wait.md`, `cross-ai-dispatch.md`, curated-config `runner.md` and SKILL.md, README rows, doc-contract tests incl. the reason-list lock (runner source, `--describe`, SKILL.md table), baseline shrink | docs + tests | R11 |
| SHIP | 17 | installer re-render of `.planning/scripts/cross-ai.mjs` into a scratch HOME dry run then the live copy, `make check-dogfood`, `python3 tests/cross_ai_selftest.py --record-times` (about 4 min), judge loop record in `37-VERIFICATION.md` (orchestrator-run) | `.planning/scripts/cross-ai.mjs`, `tests/fixtures/cross_ai_selftest_secs.json`, `37-VERIFICATION.md` | R8 live, R11 judge bar |

**Same-wave overlap check:** W2 = P02 (tests/fixtures only) + P03 (mjs): disjoint. W9 = P10 (mjs) + SYNC (new test file): disjoint. W11 = P11 (mjs) + PY2 (Python files, no mjs): disjoint. W12 = P12 (mjs) + PY3 (`runner_dispatch.py`, `cross_ai_build.py`): PY2 touched `runner_dispatch.py` in W11, different wave: no overlap. W14 = PY4 (Python) + P14 (mjs): disjoint. Waves 1, 3-8, 10, 13, 15-17 hold one plan. No two `[mjs]` plans share a wave.

**Dependencies:** P04 after P03; P05 after P04; P06 after P05; P07 after P06; P08 after P06 (not P07: independent, but serialized by the file); P09 after P08; P10 after P09 and P01 (permission flag); SYNC after P09 (needs argv-file case); PY1 after P10 (settings real and claude formula); P11 after PY1; PY2 after PY1 and P06 (`model-id` line from P04); P12 after P11; PY3 after P08; P13 after P12; PY4 after P13; P14 after P13; P15 after P14; DOCS after P15 and PY4; SHIP last.

**Green-after-each check:** P03 stores values only (no behaviour change); P04-P06 keep today's argv for calls naming nothing; Python keeps composing until PY1/PY2, and the runner accepts a pre-composed id (the floor allows brackets), so the transition has no broken commit; PY3 lands after the runner already ignores the grammar.

**Task shape per plan (3 tasks):** (1) code change in file content the plan gives in full or as an exact diff-by-anchor; (2) the unit test module or self-test cases; (3) verify gates and the baseline/doc touch if any. Any heredoc or `$(...)` in plan text is file content for the file-write tool.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` through `tools/run_unittest_parallel.py` (one subprocess per module; groups `unit`, `unit-uv`, `integration`, `e2e`, `arch`); the runner's own `--self-test` for spawn-level behaviour (shards `tests/test_cross_ai_selftest_{logic,runtime}_{1..4}_e2e.py`) |
| Config file | `tools/run_unittest_parallel.py` (exception sets are commented in it); `pyproject.toml` ruff/pylint/pyright/vulture config |
| Quick run command | `python3 -m unittest tests.test_cli_help_flags` (per module) or `python3 tools/run_unittest_parallel.py --group unit` |
| Full suite command | `make test` |

### Phase Requirements to Test Map
| Req | Behavior | Test type | Automated command | File exists? |
|-----|----------|-----------|-------------------|--------------|
| RUN-01 R1 | each flag parses, each conflict is exit 2, golden `runner_flags` per runtime, hook tokens allowed, builder parity | unit + self-test | `python3 -m unittest tests.test_runner_vocabulary tests.test_ai_kit_spec_runner_dispatch` | new + existing (update) |
| R2 | settings lines per runtime (applied/ignored/unknown, reasons), reason lock, status group parses | unit (`--print-argv`) + self-test | `python3 -m unittest tests.test_runner_settings_argv` | new |
| R3 | argv per runtime per level; `max`/`ultra` pass; bad levels exit 2; id-carried wins; cursor bracket merge; `CONFIG.effort` yields; no Python composer (grep test) | unit | `python3 -m unittest tests.test_runner_settings_argv tests.test_lane_effort` | new + existing (shrinks) |
| R4 | argv-file lane serves review and execute; refusals named; classify-only generic | self-test | `AIKIT_XAI_SELFTEST_CASES=<case> node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` | cases new |
| R5 | unusual shape reaches spawn with advisory; dash/space/control refused; listing omission `bad_model`; no per-runtime grammar in Python | self-test + unit grep | self-test cases + `python3 -m unittest tests.test_ai_kit_spec_runner_dispatch` | new + existing |
| R6 | claude execute/resume argv, fake claude serves a commit and a resume, unverified note pinned, review argv byte-equal | unit + self-test | `python3 -m unittest tests.test_runner_settings_argv` | new |
| R7 / RUN-02 | first call prints `session=X`, second resumes the same fake session; rejected id fails; `mode_forbids`; explicit beats `last_sid` | self-test (fakes) | self-test cases `session-*` | new |
| R8 / RUN-06 | render == template, matrix equal, mutations fail | unit | `python3 -m unittest tests.test_cross_ai_render_sync` | new |
| R9 | `--describe` golden, snapshot fact, routing cases (formula, no formula, absent, outside table with command) | unit | `python3 -m unittest tests.test_runner_describe tests.test_ai_kit_spec_routing tests.test_no_seed_refusal` | new + existing (update) |
| R10 | both flags echoed `recorded_only`, one spawn on failure | self-test | self-test case `escalate-*` | new |
| R11 | SKILL.md doc-contract: fields, reasons table equal to runner and `--describe`; guard passes; judge bar | unit + judge | `python3 -m unittest tests.test_cross_ai_skill_text tests.test_arch_hardcoded_models` | existing (extend) |
| RUN-12 R12 | hosted == headless for ok/error/timeout; off-switches; `host_failed`; tab closed on every path; modes; planted key absent; hostile argv intact; closed list pin | self-test (fake herdr) + unit | self-test cases `host-*`, `python3 -m unittest tests.test_runner_host_protocol` | new |
| R13 | per-runtime skill forms, byte-equal block, usage errors, copilot cap | unit (`--print-argv`) + self-test | `python3 -m unittest tests.test_runner_settings_argv` | new |
| R14 | claude/copilot argv, others unchanged, usage errors, planted key never printed, host config dir untouched | unit + self-test | same | new |
| 38.1 D-30 | every flag in rows appears in recorded help; stale flag, missing record, out-of-kind label fail | unit | `python3 -m unittest tests.test_cli_help_flags` | new |

### Sampling Rate
- Per task commit: the plan's quick command above plus `make ruff`.
- Per plan: `make ruff`, `make pyright`, `make vulture`, `make pylint`; for `[mjs]` plans the covering self-test cases by name.
- Per wave merge: `python3 tools/run_unittest_parallel.py --group unit` and the affected shard modules.
- Phase gate: `make test`, then `make check-dogfood`, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_cli_help_flags.py`, `tests/fixtures/cli_help/<host>/` (P02)
- [ ] `tests/test_runner_vocabulary.py`, `tests/test_runner_settings_argv.py` (P03-P05)
- [ ] `tests/test_cross_ai_render_sync.py` (SYNC)
- [ ] `tests/test_runner_describe.py`, `tests/fixtures/runner_describe_golden.json` (P13)
- [ ] `tests/test_runner_host_protocol.py` (P14)
- [ ] Self-test cases in `cross-ai.mjs` (P03, P06-P10, P12, P15); `tests/fixtures/cross_ai_selftest_secs.json` re-recorded once by SHIP
- Framework install: none.

## Security Domain

| ASVS category | Applies | Standard control |
|---------------|---------|------------------|
| V2 Authentication | no | the runner holds no credentials |
| V3 Session management | no (host sessions are opaque ids) | ids charset-checked, printed redacted |
| V4 Access control | yes | MCP file mode check; argv-file inside the cwd tree; hosted run dir 0700, env/prompt 0600; review lane keeps confinement flags and the tree check |
| V5 Input validation | yes | one strict reader (UTF-8 fatal, BOM refused, duplicate keys refused, size cap); closed shapes for level, label, id, name |
| V6 Cryptography | yes (hash only) | `crypto.createHash('sha256')`, never hand-rolled |
| V7 Error handling and logging | yes | every value through `redactSecrets`; MCP values and env never printed |

| Threat | STRIDE | Mitigation |
|--------|--------|------------|
| key in a setting value, `session=`, advisory or MCP server env/args/headers | Information disclosure | control-char strip then `redactSecrets`; MCP values never printed; test with a planted key shape |
| hostile argv element in a hosted launcher (quote, newline, `$`, backtick) | Tampering / injection | single-quote quoting; NUL refused; typed line holds only the launcher path |
| argv-file outside the cwd or symlink escape | Tampering | `realpath` both, `path.relative` must not start with `..` |
| env file left on disk after a hard kill | Information disclosure | launcher sources and deletes env and prompt as first steps; Phase 38 sweep covers the rest |
| a prompt on argv in the process table | Information disclosure | argv-file lane sends the prompt on stdin only; copilot's existing argv prompt keeps its `ARGV_PROMPT_MAX` check and warning |
| silent fresh session on a rejected id | Repudiation | rejected id is a failed call with the host's first line |

## Sources

### Primary (HIGH confidence)
- `skills/ai-kit-spec-review/references/cross-ai.mjs` (read this session: lines 1-130, 1225-1665, 4057-4135, 4259-4318, 4524-4560, 4753-4890, 5225-5440, 6037-6140, 6422-6610, 12551-12839)
- `skills/ai-kit-spec-review/ai_kit_spec/{runner_dispatch,commands,routing,detection,lane_effort,lane_settings}.py`, `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py`, `tools/check_dogfood.py`, `tests/cross_ai_selftest.py`, `tests/test_opencode_help_flags.py`, `tests/test_arch_hardcoded_models.py`, `tests/test_cross_ai_skill_text.py`
- `37-SPEC.md`, `37-CONTEXT.md`, `git show 4014a05 ab50e41 6eed2d0` for the later-unit amendments
- `.claude/gsd-core/bin/gsd-tools.cjs:4773-4836` (run-with-timeout: inherited stdio)

### Secondary (MEDIUM confidence)
- Help captures in `tmp/run-2026-11-19/p37-help/` (the host's own help, 2026-11-20/21), as quoted in 37-SPEC.md

### Tertiary (LOW confidence)
- Host behaviour not yet probed (resume, permission flag, `/<name>`, `--add-dir` skills): the spike decides; labels `unverified` until then

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (stdlib only, no package)
- Architecture: HIGH (ctx seam and review-prefix check read in code)
- Pitfalls: HIGH for code-derived (status model, version floor, review prefix, baseline); MEDIUM for hosted-lane shell behaviour

**Research date:** 2026-11-21
**Valid until:** 2026-12-05 (hosts' CLIs move weekly; re-read the help fixtures date)
