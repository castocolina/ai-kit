# Phase 42 Research

Researched 2026-11-26 on the phase branch. Read-only; no live host run. Paths are repo-relative. "unknown" = not
established in the time box. Locked decisions D-01..D-09 are not re-discussed.

Path fact: the runner template is `skills/ai-kit-spec-review/references/cross-ai.mjs` (the brief's
`skills/ai-kit-cross-ai/references/cross-ai.mjs` does not exist).
Package fact: `ai_kit_spec` = `skills/ai-kit-spec-review/ai_kit_spec/`; adapter = `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/`
(files: `cli.py`, `dispatch_injection.py`, `task_classification.py`). `tests/test_arch.py:1568`
`CROSS_SKILL_ALLOWLIST: dict[tuple[str, str], str] = {` is frozen (`test_cross_skill_allowlist_is_frozen`, :2469); per the
orchestrator note only adapter `cli.py` and `dispatch_injection.py` may import `ai_kit_spec` (not re-verified here). So new
logic goes into `ai_kit_spec` (new modules there, called from the adapter's two files), never into a new adapter module that
imports it.

## A1 Code review loop (R1, D-01, D-03)

How spec review runs a round (`skills/ai-kit-spec-review/SKILL.md`, all `ai-kit-spec.py` subcommands):
- `size-review` (:191, once), `ping-lanes` (:284, before each round; exit 3 = no lane, 2 = config error),
  `resolve-timeout-tiers` (:314), `dispatch-reviewer` (:322-330), `switch-lane` (:346, flagged lane only, one at a time),
  `check-fold-step` (:357), `merge-reports` (:367, partial report with `--lane-log ... --round <N>`),
  `classify-disagreements` (:404, :426, at cap or after a fixer summary). Review log = `--lane-log "$RUN_TMP_DIR/lanes.jsonl"`.
- `dispatch-reviewer` flags (`ai_kit_spec/cli.py:466-497`): `--reviewers-json` (req), `--index` (req), `--prompt-file` (req, `-` = stdin),
  `--timeout-tiers` (req), `--tool-availability-json` (ignored), `--files` (nargs `*`), `--agents-tooling-path`, `--cwd`,
  `--stdout-only`, `--lane-log`, `--round`.
- Cap and pass rule live in SKILL PROSE, not code: `SKILL.md:202` "**Iteration cap:** 3 (configurable per invocation if user requests)";
  Step 2 table `SKILL.md:403` "`### Status: Approved` | Loop ends." and `:404` "`### Status: Issues Found — fix and re-invoke` | Continue to Step 3 if iter < cap, else ...".
  The pass rule in spec review is the report's `### Status:` line (Approved vs Issues Found), parsed by
  `review_reports.report_status` (`review_reports.py:33`); there is NO code that computes "no CRITICAL or HIGH open". The
  code review needs a new small pure function over `review_reports.parse_findings` (`:47`) for that rule (see contradictions).
- Severity vocabulary of the reports ai-kit parses: `review_reports.py:9-10` `^### (CRITICAL|HIGH|MEDIUM|LOW|Cross-Document Consistency)\s*$`;
  bullet shape `review_reports.py:11-13` `^- \*\*(.+?)\*\* — Location: (.+?)\. Required: (.+?)\. Why: (.+?)\.`. `jev_review.SKIPPABLE = ("MEDIUM", "LOW")` (`jev_review.py:38`).
- Superpowers vocabulary differs: `requesting-code-review/code-reviewer.md` output headings "#### Critical (Must Fix)", "#### Important (Should Fix)",
  "#### Minor (Nice to Have)" and "### Assessment" (superpowers 7.0.2 plugin cache, lines 113-131). So a review lane
  run through ai-kit lanes must be given a code-review prompt that asks for the ai-kit shape (`### CRITICAL/HIGH/MEDIUM/LOW`,
  `- **title** — Location: ... Required: ... Why: ...`, `### Status:`), otherwise `parse_findings`/`merge-reports` read nothing.
  A mapping Critical->CRITICAL, Important->HIGH, Minor->MEDIUM/LOW is a design choice for the planner (not stated by either project).
- Inputs of `requesting-code-review` (SKILL.md lines 26-40): `BASE_SHA`, `HEAD_SHA`, `{DESCRIPTION}`, `{PLAN_OR_REQUIREMENTS}`; reviewer runs
  `git diff --stat [BASE_SHA]..[HEAD_SHA]` and `git diff [BASE_SHA]..[HEAD_SHA]` (code-reviewer.md:29-30). Stop-and-discuss in
  `receiving-code-review` SKILL.md: line 44 "STOP - do not implement anything yet" (unclear item) and line 82-83
  "IF conflicts with your human partner's prior decisions: Stop and discuss with your human partner first".
- What a lane receives: prompt text (`--prompt-file`) plus `--files` paths. `ReviewerDispatchSpec(reviewer_entry, prompt, timeout_tiers, tool_availability, agents_tooling_path, cwd, files)` (`reviewer_dispatch.py:43`);
  `dispatch_reviewer(spec, seams=None) -> dict` (`:95`) composes via `compose_for_lane` then `run_runner_tiers` / `run_custom_command`.
  `--files` values are validated by `prompt_guard.validate_values` against repo, skill roots, worktrees, profile cache
  (`capability_block.py:567-578`); a path outside is refused exit 65 `path_outside_roots`. `RUN_TMP_DIR` is `mktemp -d` (outside the repo,
  `references/cross-ai-dispatch.md:93`), so a diff file there cannot go in `--files`. No prompt size cap in the CLI reader
  (`cli.py:1414-1418` reads the file whole); the window check is `prompt_guard.check_window` in `capability_block._final` (:650).
  Recommendation: do NOT pass the diff as a file through `--files`. Pass the changed paths (in repo) as `--files` and have the prompt
  name `BASE..HEAD` so the reviewer runs `git diff` itself (same as superpowers' reviewer), or write the diff under repo `tmp/`.
  A diff file is therefore not "unchanged through the seam" from RUN_TMP_DIR; from repo `tmp/` it would pass.
- Adapter hook point: `SKILL.md:275-284` Step 4 ends "the final whole-branch review run unmodified"; Step 5 (:282) starts
  "## Step 5: Fold the finished plan (after the final review, before the finishing step)". New step goes between them
  (D-01). SKILL.md is 293 lines and `tests/test_ai_kit_spec_superpowers.py:3876` `self.assertLessEqual(len(text.splitlines()), 300)`: 7 lines
  of headroom, so the step must be a few lines pointing to `references/code-review.md` (every reference needs an explicit load trigger,
  :3874-3879).
- Narrowest hook (recommended): a new `ai_kit_spec` module (e.g. `code_review_loop.py`, in `ai_kit_spec`, with register_parsers/COMMANDS
  like `jev_review.py:403-441`) exposing a subcommand on `ai-kit-spec.py` that does the pure parts (pass rule over `parse_findings`, cap
  stop, owner-items), while lane dispatch/ping/switch/merge stay the existing subcommands called from `references/code-review.md`.
  Reason: the loop's lane steps are already subcommands; only the pass rule and the code-review prompt/lens inputs are missing.
  The adapter shim only gets a thin subcommand if it needs adapter-only functions (pick, lite file).

## A2 jev routing (R1, D-03, R7, D-08)

`ai_kit_spec/jev_review.py` public API:
- `CLASSIFY_QUESTION`, `CLASSES = {"owner_decision": "a strategy or scope choice only the document's author can make", "mechanical": "a plain text edit can satisfy the finding", "reviewer_wrong": "the finding is mistaken or does not apply"}` (:32-36).
  These descriptions are document-edit worded ("document fixer", "plain text edit"): code review needs its own question/criteria text.
- Exception: `SKIPPABLE = ("MEDIUM", "LOW")` (:38) and `route_for` (:199): "only a confident answer on a MEDIUM or LOW finding moves it";
  `if finding.severity not in SKIPPABLE or not confident or choice == "owner_decision": return Route(*head, "owner", "")`.
- `Finding(title, severity, source, reason, matched)`, `Route(title, severity, source, klass, confidence, route, note)`, `Classified(jev, routes)`.
- Summaries-only builder: `finding_item(index, finding) -> dict` (:182) using `_summary_text` (:174: strips backtick/quote spans to `[omitted]`, tokens with `/ \ =` or hex 8+ to `[omitted]`, redacts secrets, caps `TITLE_CHARS = 80`, `REASON_CHARS = 160`).
- `STABLE_TOP = 0.80` in `ai_kit_spec/lane_order.py:14`; `_confident(answer)` (:194) `reason == "" and choice is not None and top is not None and top >= STABLE_TOP`.
- No-jev path: `classify_disagreements(items, env, run=subprocess.run, *, own_root=None, limits=(None, None)) -> Classified` (:216): `entry = jev_names.find_jev(env, own_root)`; None -> status "absent", every route "owner" with note "jev absent".
- CLI exposure: `classify-disagreements` (`--cwd --report --fix-summary --cap-reached --iteration --cap --owner-out`) and `size-review` (:403-436), registered in `cli.py:535` and `_COMMANDS` `cli.py:1563`.
- `jev_names.ask_items(entry, items, env, run=subprocess.run, strict=False) -> dict` (`jev_names.py:140`): per-item `(choice, top, reason)`; `_column_answer` (:121) maps `needs_fallback|forced|fallback` to `(None, top, "low")`, so the SPEC row "`needs_fallback` true counts as low" is already the behaviour. `find_jev(env, own_root=None)` (:63).
- Two new classifiers fit the same pattern: pure `*_items` builder (tokens, no names: see `sizing_items`, :305, which uses `p1..pN` tokens and criteria "candidate lane N"), `ask_items(..., strict=True)`, a `route_for`-style function with `_confident`, a `COMMANDS` entry. Existing `CLASSIFY_QUESTION`/`CLASSES` cannot be reused unchanged for code (wording).
- Execute outcomes today: `dispatch_injection.dispatch_classification(dispatch_result) -> {"class", "retry_after_s", "cycle"}` with classes `ok`, `quota_cycle`, `quota`, `real_error` (`dispatch_injection.py:546-573`); `RUNNER_ONLY_STATUSES = ("locked", "partial")` (:529) read as `real_error`. Implementer status `implementer_status(stdout) -> str` (:512) regex `(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)`, no/ambiguous declaration -> `BLOCKED`. Adapter CLI: `classify-dispatch-failure`, `implementer-status` (`cli.py:770-776`).
- Deterministic default for `done|partial|another_round` (proposal, not in code): `DONE` and class `ok` -> done; `DONE_WITH_CONCERNS` -> partial; `NEEDS_CONTEXT`/`BLOCKED`/non-ok class -> another_round (or owner stop for quota/real_error per existing Step 3). The planner must fix this mapping; the code has no `partial` execute outcome except runner status `partial` (read as real_error).

## A3 Lenses (R2, D-02)

- `lens_delivery.py`: `LENS_NOTES = ("built_in_no_file", "over_window", "path_rejected", "not_present", "host_cannot_load")` (:17); `UI_EXTENSIONS = (".tsx", ".jsx", ".css", ".vue", ".scss")` (:20, PUBLIC, already in `ai_kit_spec`); `UI_ROLE = "ui_lens"`;
  `lens_set(table_host, files, role="review_lens", native_host=None) -> list` (:73) adds `ui_lens` when any file `.lower().endswith(UI_EXTENSIONS)`; `check_lens`, `plan_lenses`.
- Caller today: `capability_block._checked` (`capability_block.py:581-584`) `lens_delivery.lens_set(lane.host, list(files or ()), role=lane.req.lens_role, ...)`, driven by the `--files` of `dispatch-reviewer`; `LaneRequest.lens_role = "review_lens"` default (:418).
- `task_classification._FRONTEND_EXTENSIONS = (".tsx", ".jsx", ".css", ".vue", ".scss")` (`task_classification.py:15`), PRIVATE, used only by `classify_task` (:26). Pinned by `tests/test_lens_delivery.py:163-171` `test_ui_extensions_match_the_adapter` (AST-reads the private name `_FRONTEND_EXTENSIONS`; comment `lens_delivery.py:19` "no import either way: tests/test_arch.py frozen allowlist"). Making it public/renaming would break that test unless updated.
- FINDING: D-02's "made public, one source" is unnecessary. UI detection over changed paths already happens in `lens_set` when the changed paths are passed as `--files`; nothing needs the adapter tuple. Recommend: pass the diff's changed paths as `--files`, leave `_FRONTEND_EXTENSIONS` as is, keep the drift test. Tuple members: `.tsx .jsx .css .vue .scss`. Note the matching differs: `classify_task` uses substring-in-Files-block, `lens_set` uses endswith.
- `skill-roles.json` entries for `ponytail-review`/`impeccable` roles: NOT opened this session (SPEC cites `review_lens`/`ui_lens`); unknown here, planner to read `skills/ai-kit-spec-review/references/skill-roles.json`.

## A4 Executor pick (R3, D-04)

`ai_kit_spec/execute_selection.py`:
- `filter_by_purpose(candidates: list, purpose: str) -> list` (:28); `filter_by_affinity(candidates, task_type, affinity_table) -> list` (:37); `filter_by_context(candidates, required_context: int) -> list` (:62); `resolve_execute_candidates(candidates, options: ExecuteResolveOptions) -> list` (:114) (screen, purpose, affinity, context, then sort by `(context_limit is None, rank in top_n_keys, task_affinity != task_type)`); `candidates_to_ladder(candidates) -> list` (:153) `[c["key"] for c in candidates]`.
- Caller: `dispatch_injection._narrow_and_rank(request, routes)` (:337) calls `resolve_execute_candidates`; shared by `build_dispatch_injection` (:434) and `compute_ladder_keys` (:356) with the docstring "the two must never compute the narrowed/ranked candidate order via two independently-drifting code paths". Slot: inside `_narrow_and_rank` after `resolve_execute_candidates`, before `candidates_to_ladder` is applied by both callers (one place). Caveat: `_narrow_and_rank` runs twice per `resolve-injection` (once in `_blocked_pool_quota` via `compute_ladder_keys`, `cli.py:307`, once in the build, `cli.py:327`) so a jev call there would ask twice; the pick must be computed once and passed in (e.g. as a request field) or memoised.
- Candidate dict (`assemble_candidates`, `dispatch_injection.py:190-198`): keys `key, model, runtime, vendor, command, task_affinity, context_limit, purpose, effort, service_tier, pool, roster_entry`. No catalog class on it; reaching the class needs a catalog read (`entries[key]["facts"]["class"]["value"]`, see A5) by `provider/model` key.
- Analog: `SESSION_PICKS = ("haiku", "sonnet")` (:208), `PICK_QUESTION` (:210), `pick_session_model(summary, env, run=subprocess.run) -> tuple[str, str]` (:216): returns `("", "jev absent")` with no jev, `("", "jev low: session model kept")` when not confident, else `(choice, f"jev {choice} ({top:.2f})")`; uses `reason == "" and choice in SESSION_PICKS and confident` with `lane_order.STABLE_TOP`. Its test: unknown (not located in the time box; `tests/test_ai_kit_spec_superpowers.py` is the likely home).
- "Owner's roster" in code = `assemble_candidates(...)`: `resolved.get("execute", resolved.get("reviewers", []))` from `cfg_resolve` (`dispatch_injection.py:187`), ranked by `role_order(resolved, "execute")`. A pick must return a key from that list only.
- Model-name guard: `tests/test_arch_hardcoded_models.py` ALLOWED forms are `router-env/...`, `placeholder-model-N`, `fake/...` (:48-49); baseline file `tests/fixtures/no_hardcoded_models_baseline.json` "only shrinks"; marker `model-example:` exempts doc/comment/docstring lines only (:39, :149). New code must not add literals "haiku"/"sonnet"/"composer"; build jev criteria from tokens (`p1..pN`) like `sizing_items`, or reuse `SESSION_PICKS`/RUNTIMES. Open: whether model names/effort in a jev summary violate "never config values" (SPEC prohibition 3); safest = tokens plus class/effort/affinity labels, no names.

## A5 Lite class (R4, D-05)

- No class literally called "lite". Facts: `catalog_bands.CLASSES = ("flagship", "coding", "general", "fast", "small", "router", "unknown")` (`catalog_bands.py:12`), `TIERS = ("frontier", "strong", "capable", "light", "unknown")` (:10), `COST_BANDS = ("low", "medium", "high", "premium", "free_or_local", "unknown")` (:11). Rules: `_is_small` = `tier == "light" and cost_band in ("low", "free_or_local")` (:153); `_is_fast` = tier in strong/capable/light with `tps >= tps_cut` (:144).
- Where stored: catalog entry `["facts"]["class"]` = `{value, label, source, fetched_at}` (`catalog_labels.fact`, `catalog_labels.py:17-25`; `catalog_tiers._entry_facts` :247 `facts = {"class": cls}`; reader `model_heuristics.router_statement` :51 `klass = facts.get("class")`). Also `facts["tier"]`.
- Proposal for the selector: lite = `facts.class.value in ("small", "fast")`, any other value or a missing/`unknown` class = not lite (R4 held-out rows). The choice is the planner's (SPEC says fixed at plan time).
- Real key names in `tests/fixtures/curated_config_v2/model-catalog.json` (fixture, no `facts` in the two entries I read): `anthropic/claude-haiku-5-5` (:88), `openai/gpt-5.6-luna-low` (:438). That fixture entry has no `facts` block (it carries `tokens_per_sec`, `pricing`, `scores`), so a real class value for it is unknown; test fixtures must add `facts.class` themselves with placeholder-model names.
- Rail: `AGENTS.md:319` "Before a superpowers plan exists, run `python3 <fold skill>/scripts/fold.py boundary --next --point plan` ... and hand `.aikit/brief/SKILL.md` to the plan writer." The adapter itself never briefs: `skills/ai-kit-spec-execute-superpowers/SKILL.md:103` "A project that briefs its superpowers plan writer does that before the plan exists, from its own instruction file." `ai-kit-commit-fold/references/adapter-guide.md` has no brief hand-over text (only :30 boundary timing). CONSEQUENCE: the lite file is produced before the adapter skill runs, so it needs its own project-rail line (AGENTS.md, or the adapter shim called from it) to be written and handed over; SKILL.md cannot do it.
- Gitignore: `git check-ignore -v .aikit/brief/x` -> `.gitignore:12:	.aikit/	.aikit/brief/x` (whole `.aikit/` ignored). Brief path constant `BRIEF_REL = Path(".aikit") / "brief" / "SKILL.md"` (`flow_brief.py:21`); `write_brief` replaces atomically in the same folder. Propose `.aikit/brief/lite-executor.md` (same folder, not written by `fold.py`).

## A6 Spike (R5, D-06)

- `detection.RUNTIMES` ids/binaries (`detection.py:98-134`): `pi` ("pi"), `opencode` ("opencode"), `cursor` ("cursor-agent", "agent"), `codex` ("codex"), `claude` ("claude"), `copilot` ("copilot"). `KNOWN_CLIS = tuple(RUNTIMES)`; `detect_installed_clis(which_fn=shutil.which, ...)` (:232).
- `which` here (2026-11-26): claude, codex, opencode, pi, cursor-agent, copilot all on PATH (also herdr, node). Versions not run (no consent line, `--version` would still be a host call; Phase 37 recorded versions: claude 2.1.330, codex 0.170.0, copilot 1.0.112, cursor 2026.11.13, opencode 2.3.2, pi 1.5.2 on 2026-11-21 in `.planning/phases/37-shared-runner-options-and-session-ids/37-SPIKE.md:10-15`).
- Resume forms in `cross-ai.mjs`: cursor `resume: ... '--resume', sid` (:1768, label :1784 unverified "resume not live-probed"); opencode `'--session', sid` (:1799, label :1810 unverified, "a ses_ id was accepted live on 2026-11-16"); pi `resume: (m, c, sid, mode) => RUNTIMES.pi[mode](m, c)` with `--session-id` chosen id (:1819-1823, label :1840 unverified); codex `exec resume` (:1852, `resumeFlag: null, noResume: ['review','sandbox']`, label :1875 unverified); claude `'--resume', sid` (:1888, label :1907 unverified; `execLabel` unverified, `CLAUDE_EXEC_FORMULA_RECORD === null`); copilot `resume: null` (:1923), session style `chosen` `--session-id` (:1938 unverified).
- DANGER: a second vocabulary exists: `FORMULA_LABELS` (:1947-1956) marks `resume` "verified: ... help recorded ..." for claude/codex/cursor/opencode/pi. That is help-text provenance, not a live resume run. The chooser must read `forms.session.label.state` (all `unverified` today), not `FORMULA_LABELS`, or "verified resume" would be true with no spike. SPEC R6 wording "(or the runner's verified label)" is ambiguous on this.
- Session id source: `style: 'minted'` (host makes the id: claude, cursor, opencode, codex) vs `'chosen'` (caller passes `--session-id`: pi, copilot) (`session` setting, :2053-2069). How a minted id is read back from output: not examined (unknown).
- Phase 37 already has the spike precedent but all resume probes "not probed (no ledger consent line)" (`37-SPIKE.md:21-33`, `:35-40`). Convention: `NN-SPIKE.md` in the phase folder (also `38-SPIKE.md`); sections "Host versions" table `| host | version | --version text | date |`, "Questions" Qn with command shape / host version and date / observed / verdict, "Label flips", "Real config audit", "Cleanup". Older folders: `.planning/spikes/001-claude-timer-resume` etc. and `.planning/milestones/v1.3-phases/21.2-.../spike/`. D-06's "script under the phase's `spike/` folder" matches the milestone-21.2 form, not 37/38.
- Proposed record: `.planning/phases/42-.../42-SPIKE.md`, header lines `consent line:` and `spike-run:`; table columns `| host | version command | version | date | session id source | headless resume result | label |`; a row with no run reads `not run` / `unverified`.

## A7 Transport (R6, D-07)

- `runner_dispatch.RunnerSpec(runtime, model, mode, timeout_s, cwd, effort, service_tier, cursor_mode, codex_sandbox, route, context, session_id, escalate_runtime, escalate_model, host="auto", skill_paths, skill_names, mcp_config, pool)` (`runner_dispatch.py:69-91`); comment :84 "D-23: ai-kit calls host by default; the runner's own default stays none". Flags built by `runner_flags(spec)` (:222) from a table with `("session_id", "--session-id", "value")`, `("host", "--host", "value")`, and `--pool` (:246). `build_runner_argv(spec, runner_path, node)` (:279). Runner entry points `run_runner(spec, prompt, seams)` (:649), `run_runner_tiers(spec, tiers, prompt, seams)` (:679).
- Runner flags: `--session-id <id>` (cross-ai.mjs:38), `--host auto|none` (:39), `--sweep` (:49, "remove dead run directories, secrets and tabs and exit (no spawn, no lock)"). There is NO `--resume` flag: resume is applied inside the runner when `--session-id` is given and the runtime row has a resume form (`session` setting :2053-2069 sets `plan.resume = true`; `sameSessionArgv`, :3938-3940). A same-session retry already resumes within one call (:3846, :5895). So "resumed session across rounds" = pass the same `--session-id` (minted styles need the id read from the earlier run: source unknown).
- herdr hosting (runner): availability `hostAvailable(env)` = `env.HERDR_ENV === '1'` plus herdr on PATH (cross-ai.mjs:4646-4648); verbs `HERDR_VERBS = ['tab create', 'pane run', 'tab close', 'tab list']` (:4651); label `hostLabel` = `` `${HOST_LABEL_PREFIX}:${role}:${runtime}:${token}` `` with prefix `'aikit'` (:4708-4709, :4685); run dir `path.join(home, 'ai-kit', 'spec', 'host', token)` where `home = stateHome()` (:4712-4714); files `HOST_FILES = { run: 'run.json', launcher: 'launch.sh', env: 'env', prompt: 'prompt', out: 'out', err: 'err', pid: 'pid', rc: 'rc' }` (:4687); verdict = `rc` (`parseRc`, :4670: integer 0-255 or signal name, else crash). Python-side detection: `herdr_source.herdr_available(env, which_fn=shutil.which)` (:25) returns `None, "herdr absent: HERDR_ENV is not 1"` otherwise.
- A pane today is created by the runner per call and closed by the runner (D-27, 37 spike Q9). A herdr "lane" that survives across rounds ("pane closes at plan close") is NOT something the runner does: it closes its tab per call. So R6's persistent pane needs either new runner behaviour (contradicts "protocol is Phase 37's, not redefined") or the "pane" transport means "the runner's hosted run, one per call"; the planner must decide. Result-file reader: the `rc` file is already the verdict in the runner; a Python reader for `run.json`/`rc` does not exist (unknown).
- Chooser seam proposal: new `ai_kit_spec/transport_choice.py` (in `ai_kit_spec`, imported by `execute_dispatch`/`reviewer_dispatch`/adapter code), pure `choose_transport(lane, verified, herdr_ok, interactive, round_no, record) -> transport`, plus record read/write. Per-plan record location: the adapter's `$RUN_DIR` is `"$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-task-${TASK_N}"` (`SKILL.md:125`), per task; the runner's dir is per call under `<stateHome>/ai-kit/spec/host/<token>`. A per-plan record therefore needs a plan-level dir (e.g. beside the task dirs, keyed by `PROJECT_KEY`), not either existing dir.
- Lane settings: readers in `lane_settings.py` (`lane_usage_limit` :105, `lane_escalation` :121, `lane_free_pool` :127, `lane_session_fallback` :112). `LANE_FLAG_KEYS = ("escalate_runtime", "escalate_model", "usage_limited")` (:11). Writer: `normalise_lane_settings` pops a flag when `result.get(name) is False` (:33-35) and is called at `config_io.py:949`; validation `_problems` requires bool (:46-48). A new `interactive` flag = add to `LANE_FLAG_KEYS`; that gives write-only-when-true and bool validation for free.
- Guard impact (`tests/test_lane_settings.py:234-248`): `FLAGS = frozenset(lane_settings.LANE_FLAG_KEYS) | {SESSION_FALLBACK_KEY}`; the scan (`SCANNED` = `ai_kit_spec` and the adapter package) fails on any string literal equal to a flag name outside `lane_settings.py`, and reader names (`READERS`, :238) may only be used by modules in `ALLOWED_READERS` (:241). So a new reader `lane_interactive` must be added to `READERS` and the module that calls it to `ALLOWED_READERS`; "interactive" is not currently a literal in either package (rg: no hits). Also `MODEL_BOUND` (:15) and its test (:201) list the pair-bound settings; add if `interactive` should drop on pair change. Test for write-when-true analog: `tests/test_lane_settings.py:133-136` (False flags dropped by `normalise_lane_settings`).

## A8 Edge rows

`python3 skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py check .planning/phases/42-.../42-SPEC.md` output:
```
{"ok": true, "floor_rows": 34, "table_rows": 34, "missing": [], "unmarked_extra": [], "unclassified_not_unresolved": []}
```
Input: `{floor,check} spec` and `--engine` (path to gsd-core `edge-probe.cjs`). The check passes; R2 and R3 are "unclassified" rows already marked UNRESOLVED (no shape cue matched). Treat R2 (lens) and R3 (pick) as assumptions; suggested held-out cases from the facts above: R2 `.TSX` upper-case path (lens_set lowercases, test :323), a path list with no UI path, lens file missing; R3 pick returning a non-roster key, pick with all candidates filtered, jev double-ask.

## B9 Guards that bind new code

- `tests/test_lane_settings.py:234-248, 577-620`: flag-literal and reader allowlists (A7).
- `tests/test_arch.py`: `LOOKUP_COPIES` (:1688) lookup-order copies compared (:2478, :2492 `uncompared_lookup_files`): any new file that assigns a jev/skills lookup order must be listed/compared (`jev_names.SKILLS_ROOTS`-style); reuse `jev_names.find_jev` and add none. `CROSS_SKILL_ALLOWLIST` frozen (:1568, :2469). `_HOST_IMPORTERS` (:481). Host-literal rule detail: not read (unknown).
- `tests/test_arch_hardcoded_models.py` (A4).
- `tests/test_skill_text_history.py:1-10`: SKILL.md main flow above `## Evidence` holds no ISO date, no "as of", no run log, no tool version outside a conditional; shipped skill Python strings/comments must not name a phase file or folder. So no D-ids, phase ids or dates in SKILL text or in `ai_kit_spec*` code comments. Phase-id/D-id rule beyond that: not verified.
- `tests/test_skill_evals_shape.py`: ids `^(casual|precise|edge)-[a-z0-9-]+$` (:17); at least a casual, precise and edge case; `trigger-queries.json` 16-24 entries, 8-12 true, 8-12 false, each at least 30 characters (:97-116); no machine path.
- Adapter doc tests: `tests/test_ai_kit_spec_superpowers.py` (only module; `fd superpowers tests/` lists just it); SKILL line cap 300 (:3876). SKILL.md now 293 lines. `tests/test_lens_delivery.py` (pin :163-171), `tests/test_role_orders.py` (imports `dispatch_injection`, `role_orders`; role-order readers).
- Evals now: 18 (`evals.json`: `skill_name`, `evals` list of 18; ids from `casual-run-superpowers-plan` to `precise-host-config-audit-observation`), NOT 14 as SPEC R8 states. New ones must be `casual|precise|edge-` prefixed.

## B10 Shim and registration

- Adapter `ai_kit_spec_superpowers/cli.py` subcommands (`_COMMANDS`, :817-828; parsers :699-812): `resolve-injection`, `dispatch-task`, `print-guidance`, `classify-dispatch-failure`, `implementer-status`, `resume-exclusions`, `write-resumable-state`, `escalation-gate`, `executor-fallback`, `host-config-audit`. Shim file `skills/ai-kit-spec-execute-superpowers/ai-kit-spec-superpowers.py`.
- `ai-kit-spec.py` subcommands relevant to review (`ai_kit_spec/cli.py`, `_COMMANDS` :1530-1564): `dispatch-reviewer` (:466), `dispatch-execute` (:424), `merge-reports` (:321), `resolve-reviewers` (:308), `resolve-timeout-tiers` (:367), plus module-registered `ping-lanes`, `switch-lane`, `classify-disagreements`, `size-review`, `check-fold-step` (`register_parsers` :533-536, `COMMANDS` :1561-1564).
- Registering a new command: a module defines `register_parsers(sub)` and `COMMANDS = {...}` (analog `lane_switch.py:312-323`, `jev_review.py:403-441`), then `cli.py` adds the `register_parsers` call (~:536) and `**module.COMMANDS` (~:1564). Adapter commands: add `p = sub.add_parser(...)` and a `_COMMANDS` entry. Analog tests: `tests/test_role_orders.py` calls `cli.main` with fakes; a dedicated analog for `switch-lane`/`classify-disagreements` not located (unknown).

## Contradictions and corrections for the SPEC (the planner amends)

1. R8/Current: "the adapter carries 14 evals" -> 18 evals now.
2. D-02/R2: "made public" tuple is unnecessary; `lens_delivery.UI_EXTENSIONS` is already public and `lens_set` detects UI from `--files`. Making the adapter's tuple public would need the pin test at `tests/test_lens_delivery.py:163-171` changed.
3. R1 pass rule: spec review's pass rule is the report `### Status:` line, with cap 3 only in SKILL prose (`SKILL.md:202`); "no CRITICAL or HIGH open" has no code. Also superpowers' reviewer severities are Critical/Important/Minor, not CRITICAL/HIGH/MEDIUM/LOW.
4. R4/D-05: the adapter skill runs after the plan exists (`SKILL.md:103`), so "written at plan time ... by a small adapter script" must be called from the project instruction rail (AGENTS.md:319), not from the adapter SKILL.
5. R5 "Current: no live resume run recorded": confirmed (`37-SPIKE.md` Q1-Q3 all "not probed"); but D-06's `spike/` folder differs from the 37/38 convention (`NN-SPIKE.md`).
6. R6: "the runner's verified label" is ambiguous: `FORMULA_LABELS` says resume "verified" (help text only) while `forms.session.label.state` is `unverified` for every host. Also the runner closes its herdr tab per call (37/38 D-27), so a pane that lives to plan close is a protocol change, which Out of scope forbids.
7. SPEC "Live facts": `cross-ai.mjs` is under `skills/ai-kit-spec-review/references/`; the resume form for cursor is at line 1768 (SPEC says 1769, label at 1784).

## Validation Architecture

Runner command for each: `python3 tools/run_unittest_parallel.py <module>`. New modules join the `unit` group automatically (AGENTS.md); one needing uv/PTY goes in the runner's commented exception set.

| Req | Test module | Notes |
|-----|-------------|-------|
| R1 | new `tests/test_code_review_loop.py` (fake lanes; pass rule, cap 3, MEDIUM never blocks, empty report) + doc-contract in `tests/test_ai_kit_spec_superpowers.py` (cap and pass rule pinned in `references/code-review.md`; SKILL line cap) | uses `review_reports.parse_findings` |
| R2 | `tests/test_lens_delivery.py` (existing, add `.tsx`/`.py`/absent-lens fixtures) + `tests/test_capability_block.py` | `lens_set` through `--files` |
| R3 | new `tests/test_executor_pick.py` (fake jev via `run` seam; pick outside roster discarded, filtered candidate never picked, default log) | adapter files only |
| R4 | new `tests/test_lite_block.py` (class fixture with placeholder models, brief bytes unchanged, diff-scope) + doc test pinning text and "unverified" | catalog `facts.class.value` |
| R5 | new `tests/test_spike_record.py` (rows per host, "not run"/unverified, scratch HOME in script) | spike run itself needs consent line |
| R6 | new `tests/test_transport_choice.py` (fake herdr, fake clock, renewal constant) + `tests/test_lane_settings.py` (new flag, allowlists) + `tests/test_arch.py` | runner `--sweep` untouched |
| R7 | new `tests/test_lane_result_jev.py` (each class routes, no-jev "default", needs_fallback low, payload-recording seam for summaries only) | `jev_review` pattern |
| R8 | `tests/test_skill_evals_shape.py`, `tests/test_skill_text_history.py`, `make check-dogfood` (judge records) | 4 new evals (18 -> 22) |

Must stay green: `make e2e-test` (includes `tests/test_install.sh` and the runner self-test shards), `make e2e-docker`, `python3 -m unittest tests.test_wizard_pty` (only if the `[lanes]` flag change touches spec-config wizard output; not verified). Also `make arch-test` for `test_arch.py` and the baseline of `tests/test_arch_hardcoded_models.py`.

## Unknowns (not established in the time box)

- `skill-roles.json` entries; spec-config writer test for the flag; the test of `pick_session_model`; how a minted session id is read back per runtime; whether a Python reader of the runner `run.json`/`rc` exists; host-literal rules in `test_arch.py`; wizard PTY impact.
