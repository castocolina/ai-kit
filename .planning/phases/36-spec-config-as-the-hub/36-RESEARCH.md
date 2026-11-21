# Phase 36: spec-config as the hub - Research

Researched 2026-11-20 on branch `gsd/phase-36-spec-config-as-the-hub` (phase 35 code in the tree). Section 0 is the cross-area contract and WINS over sections A to D where they differ. Sections A to D are four read-only code studies: A config layer and lane settings, B proposal and free models, C refusals, effort forms and the hardcoding guard, D skill text, docs, evals and the judge loop. Paths in `P` form are under `skills/ai-kit-spec-review/ai_kit_spec/`.

## 0. Cross-area contract

Sources: `tmp/p36-plan/research-a.md` (config layer), `research-b.md` (proposal and free models), `research-c.md` (refusals, effort,
guard), `research-d.md` (skills, docs, evals, judge). Where this contract and a research file differ, THIS FILE wins. Where the
code differs from this file, write a line into `tmp/p36-plan/planner-notes-<letter>.md` and follow the code only if the contract
is impossible.

### 1. Plan map (29 plans, 11 waves). Same-wave plans share no file; a plan lists every file it edits in `files_modified`

Package dir `P` = `skills/ai-kit-spec-review/ai_kit_spec/`. SPEC numbers are R1..R12 of `36-SPEC.md`; R13 = the data-use clause
(HUB-10, ROADMAP criterion 9, REQUIREMENTS HUB-10) that plan 02 adds to the SPEC; D-20..D-23 are added to CONTEXT by plan 02.

| id | wave | planner | title and main files | depends_on | covers |
|----|------|---------|----------------------|------------|--------|
| 36-01 | 1 | P6 | stub every new test module + regenerate lists: `tests/<stubs>`, `tools/run_unittest_parallel.py` (E2E_MODULES), `Makefile`, `.pre-commit-config.yaml` | - | layout |
| 36-02 | 1 | P6 | planning amendments: `36-SPEC.md` (R13, R12 clauses, grok), `36-CONTEXT.md` (D-20..D-23), `ROADMAP.md` (review skill joins the judge bar here) | - | amend |
| 36-03 | 2 | P1 | `config_status.py` + `cli.py` wiring + `tests/test_config_status.py` | 01 | R1 |
| 36-04 | 2 | P1 | `role_orders.py`, `config_io.py` (`cfg_combine`), `quota.py`, `dispatch_injection.py`, `tests/test_role_orders.py` | 01 | R3 (read) |
| 36-05 | 2 | P5 | `lane_effort.py` (forms, levels, `effort_problem`, `offered_levels`, `write_problems`) + `tests/test_lane_effort.py` | 01 | R4 |
| 36-06 | 2 | P3 | `lane_pool.py` + `tests/test_lane_pool.py` | 01 | R6 |
| 36-07 | 3 | P3 | `lane_price.py`, `lane_data_use.py` + `tests/test_lane_price.py`, `tests/test_lane_data_use.py` | 01 | R12 a, R13 |
| 36-08 | 3 | P4 | `detection.py` (`ExecFormula`, `Advice`, `has_exec_formula`, `advice_line`; additive) + `tests/test_ai_kit_spec_exec_formula_e2e.py` + `tests/test_ai_kit_spec_runtimes_table.py` | 01 | R7 |
| 36-09 | 3 | P3 | `jev_names.py` (`score_item`, `score_judge`), `lane_order.py` + `tests/test_lane_order.py` | 01, 06 | R6 |
| 36-10 | 3 | P1 | migration default: `config_migrate.py`, `config_io.py` (`_migrate`), `cli.py` (`render-toml --keep-backup`), edited tests | 03, 04 | R9 |
| 36-11 | 4 | P2 | `lane_settings.py` (validators, normaliser, `MODEL_BOUND`) + `config_io.py` hooks + `tests/test_lane_settings.py` (part 1) | 04, 05, 07 | R5, R12 b, R13 |
| 36-12 | 4 | P4 | route `no_formula`: `routing.py`, `detection.py` (delete `review_only`), `commands.py`, `dispatch_injection.py`, `cli.py:817` detail, mechanical test rewrites | 08 | R7 |
| 36-13 | 5 | P3 | `propose_cmds.py` + `cli.py` (`propose-lanes`, `CliDeps.score_judge_fn`) + `tests/test_propose_cmds.py` | 06, 07, 09, 10 | R6, R12 a, c |
| 36-14 | 5 | P4 | `execute_selection.py`, `config_io.py` (save message), `tests/test_no_seed_refusal.py` (Python only), edited tests | 12 | R7 |
| 36-15 | 5 | P4 | referee rule in the guard: `tests/test_arch_hardcoded_models.py`, `tests/fixtures/no_hardcoded_models_baseline.json` | 01 | R8 |
| 36-16 | 5 | P6 | review skill: `ai-kit-spec-review/SKILL.md`, `references/cross-ai-dispatch.md`, `references/cli-profiles/claude.md`, `tests/test_spec_chain_text.py`, `tests/test_ai_kit_spec_runtimes_table.py` | 03, 12 | R2, R7 text, R11 |
| 36-17 | 6 | P2 | `lane_settings.py` readers + all-flagged warning in `cfg_combine` + source-scan guard + `tests/test_lane_settings.py` (part 2), `config_io.py` | 11, 04 | R5, R12 d |
| 36-18 | 6 | P5 | effort wiring: `runner_dispatch.py`, `execute_dispatch.py`, `cli.py` (`build-command`, `render-command`, help), tests | 05, 12, 13 | R4, R7 preview |
| 36-19 | 6 | P6 | adapter skill: `ai-kit-spec-execute-superpowers/SKILL.md`, `references/config-check.md` (new), `escalation.md`, `design-notes.md`, `resolution-stops.md`, `tests/test_spec_chain_text.py` | 16 | R2, R7 text, R11 |
| 36-20 | 7 | P2 | per-role writer: `config_io.py` writer functions + explicit-none warning, `role_orders.split_policy` use, edited old tests, `tests/test_config_role_write.py` | 04, 11, 17 | R3 (write), R12 c |
| 36-21 | 7 | P5 | `effort_probe.py`, `cli.py` (`check-reviewer --effort`, `render-toml` `write_problems`), `tests/test_effort_probe.py` | 05, 18, 20 | R4 |
| 36-22 | 8 | P1 | `probe-quota --role`: `cli.py`, `skills/ai-kit-spec-config/references/check-only.md`, tests | 04, 21 | R3 |
| 36-23 | 8 | P2 | wizard JSON example in `skills/ai-kit-spec-config/references/config-file.md` + `tests/test_spec_config_lane_json.py` + `tests/test_config_herdr_identity.py` | 13, 17, 20, 21 | R12 f, R3 |
| 36-24 | 8 | P7 | `references/wizard-flow.md`, `free-lanes.md` (new), `cli-model-selection.md` rewrite + `tests/test_spec_config_flow_text.py` | 13, 20, 21, 22 | R6, R4, R5, R12, R13 text |
| 36-25 | 9 | P7 | spec-config `SKILL.md` skeleton, `references/headless.md`, `references/config-file.md` | 23, 24 | R10, R11, R9 text |
| 36-26 | 10 | P7 | spec-config evals + trigger queries + id-list test edit | 25, 15 | R10, R11 |
| 36-27 | 10 | P7 | review and adapter evals (`evals.json`, `trigger-queries.json`, files; delete the 4 old `.md` scenarios) | 16, 19 | R2, R11 |
| 36-28 | 10 | P7 | docs: `README.md`, `docs/config/design.md`, `AGENTS.md:104`, markdown scan in `tests/test_no_seed_refusal.py` | 16, 19, 25 | R11, R7 |
| 36-29 | 11 | P6 | judge loop for the three skills (orchestrator action: `cross_ai: false`, `autonomous: false`) | all | R11 |

### 2. Cross-cutting decisions (chosen here; the executor decides nothing)

1. `config-status` prints, on stdout, FIRST LINE exactly `active`, `pending` or `none`, then one line per checked file:
   `checked <project|user> <absolute path> <missing|empty|lanes|untrusted|pending-migration|skipped-local-only>`, project first.
   Exit 0; a malformed file propagates `ConfigError` (exit 2 via `cli.main`). It writes and migrates nothing. Research A's JSON line is dropped.
2. Pool key: lane key `pool`, value `<provider>:free` (string shape `^[A-Za-z0-9._-]{1,64}:[a-z]{1,16}$`; the tier is always `free`
   in this phase). It is price-derived (a zero price), written by the wizard on EVERY lane whose price state is `zero`, and valid on any lane.
   `usage_limited = true` stays the owner's yes only. `propose-lanes` rows print the same string as `pool_key`. Reported grade (the
   shared pool is user-reported; the wizard says so). Research B's `free_pool` and `:free`-only pattern, and A's `<provider>/<tier>`, are dropped.
3. `lane_fallback(role_lanes, key)` (role_lanes already in the role's order): skip `key` itself, every flagged lane, and every lane whose
   non-empty `pool` equals the key lane's non-empty `pool`; return the first key left, else `None`.
4. Data-use record on a lane: six flat keys, none nested: `data_use` (`zero_retention`|`may_be_kept_or_trained`|`unknown`), `data_use_line`
   (one display line, <= 200 chars, control characters removed, passed through `secret_shapes.redact`), `data_use_source` (`https://...` <= 300 chars
   or the literal `none`), `data_use_read` (`YYYY-MM-DD`), `data_use_label` (`verified`|`reported`: required when `data_use` is not `unknown`, absent
   when `unknown`), `data_use_confirmed` (boolean, only `true` is storable: a no or a skip writes no lane). The record is five required keys (`data_use`, `data_use_line`, `data_use_source`, `data_use_read`, `data_use_confirmed`) plus `data_use_label` present exactly when `data_use` is not `unknown`; a partial record is refused (amended at review cycle 1: the earlier "all six or none" contradicted the unknown case). `lane_data_use.py`
   exports `DATA_USE_VALUES`, `DATA_USE_LABELS`, `DATA_USE_KEYS`, `validate_note(entry) -> str | None` (consistency only) and `clean_line(text) -> str`.
   No rule requires `read == today` (a program cannot verify it); the label is set by the calling skill, which labels `verified` only for the vendor's own
   documentation page read in that run, else `reported`; a missing or unreadable source is `unknown` and is never defaulted to a safe value. There is NO
   data-use CLI command: the wizard composes the keys, `render-toml` validates them.
5. Effort: lane key `effort` (validated by `lane_effort.effort_problem`, token `^[a-z][a-z0-9_-]{0,15}$`, closed sets for codex and pi, refused on a
   `command`-only lane) and `effort_source` (one line, written only after an accepted probe call: `accepted by a call on <YYYY-MM-DD>`). `lane_settings`
   does NOT validate `effort`; `validate_reviewer_fields` chains `lane_effort.effort_problem(entry) or lane_settings.validate_lane_settings(entry, key)
   or _validate_pair_fields(entry, key)` with no new `return` (it is at the pylint return cap).
6. `lane_settings.MODEL_BOUND` = `effort`, `effort_source`, `usage_limited`, `usage_limit_note`, `pool`, `escalate_runtime`, `escalate_model`,
   `data_use`, `data_use_line`, `data_use_source`, `data_use_read`, `data_use_label`, `data_use_confirmed`. `cfg_merge_reviewers` drops every one a project
   entry does not restate when it restates `runtime`, `command` or a different `model`.
7. Per-role orders exactly as research A 4.2 and 4.4 (`role_orders.py`: `ROLES`, `role_orders`, `role_order`, `ordered_lanes`, `split_policy`;
   `cfg_combine` adds `"orders"`; the raw `policy` stays the shallow merge). The writer writes only flat policy keys plus `[lanes.policy.review]` and
   `[lanes.policy.execute]` tables; a role without a lane or without a non-empty ladder gets no table and an old one is removed.
8. `probe-quota --role review|execute|both`, default `review`; the `--check-only` reference passes `--role both`. A flagged lane is probed like any other.
9. Migration: environment variable `AI_KIT_KEEP_MIGRATION_BACKUP` (value `1` keeps the `.migrated` rename), read only by
   `config_migrate.keep_backup_from_env(env)`, passed from `config_io._migrate`; `render-toml --keep-backup` sets it in the env dict. A verified migration
   deletes the old file by default; a failed check deletes nothing; the changed-during-run guard is kept (research A 4.5).
10. R7: `Runtime` gains `exec_formula: ExecFormula | None = None` and `advice: Advice | None = None`; `review_only` is deleted in plan 12 (not before).
    `has_exec_formula(row)`; route `no_formula` is returned only for a row with `runner` True and no formula (a `runner=False` row keeps its existing
    route: grok behaviour stays exactly as today). `execute_cli_error(cli)` returns `None` for a runtime with a formula; for a table row without one:
    `'<cli>' has no exec formula in the runner (route no_formula): <source>`; for a runtime outside the table: `'<cli>' is not a runtime in the table;
    store it as a custom `command` lane (custom lanes run in review mode only)`. `dispatch-execute` keeps exit 2 for these pre-spawn refusals (the
    message names the formula, never a seed flag). `screen_execute_clis` refuses only runtimes outside the table. The config save error for a runtime
    outside the table: `<key>: runtime '<r>' is not in the runtime table; store a custom `command` lane instead (no 'runtime')`; for a row with
    `runner=False`: `<key>: runtime '<r>' has no runner formula; store a custom `command` lane instead (no 'runtime')`.
11. R7 acceptance "grok as a custom command lane" becomes "a placeholder CLI named `placeholder-cli-1` stored as a custom `command` lane". No plan
    adds a grok test, fixture, doc line or list entry. The exec-formula drift test iterates only rows with `runner` True. Existing tests that already
    name grok are edited only where their expected message text changes. The grok row in `detection.py` is not edited.
12. Effort forms: `lane_effort.effort_form(runtime, model, effort) -> EffortForm(model, flags, ignored)` exactly as research C 4.2; composed into `spec.model`
    BEFORE `RunnerSpec` is built; `RunnerSpec.ignored` is printed by `run_runner` and by `build-command`/`render-command`. `cross-ai.mjs` is NOT edited.
13. `propose-lanes` exactly as research B 4.5 (flags `--purpose`, `--catalog-path`, `--detect`|`--runtimes-json`, `--runtime`, `--jev`, `--avoid-pool`,
    `--skip`; one JSON object with `pool`, `zero_price`, `aliases`, `wider`, `alternative`, `default_view`). jev only through `jev_names.score_judge` (levels
    `SCORE_LEVELS`, `JEV_WINDOW = 12`, `STABLE_TOP = 0.80`, `NEUTRAL_LEVEL = 2`); the item holds closed facts only. Rows drop `rejected`, `listed disabled by
    host`, stale (only with `--detect`), stale provider and unmatched. Zero price: models.dev reading from `facts.cost_band` (`free_or_local`, source
    `models.dev`, date `fetched_at`) and host reading from the snapshot `model_records[model_id].cost`; both zero or one zero and none positive; locality
    is always `zero price (local or hosted not known)`. The catalog is never written. `--avoid-pool KEY` and `--skip RUNTIME:KEY` feed `alternative`.
    No new third-party code; no change to `LOOKUP_COPIES`.
14. Skill text (research D): one shared R2 block (D 4.1, ASCII, pinned verbatim by `tests/test_spec_chain_text.py`), the adapter variant has no
    `--no-cross-ai` line and uses the `CONFIG_CHECK=` scalar guard in `references/config-check.md`; spec-config SKILL.md stays <= 500 lines (move the question
    flow into `references/wizard-flow.md`, `free-lanes.md`, `headless.md`); `ai-kit-spec-review` joins the judge bar in this phase and gets new-shape evals.
    No `D-<n>`, phase name, ISO date, `router-env/` or `referee-` text in any shipped `.md` outside `evals/`; models in skill text and evals are placeholders.
15. The guard rule (plan 15): research C 4.5 (`REFEREE_RX`, kind `referee`, tests/ exempt, baseline entries generated by a one-off script under `tmp/`,
    marker `model-example:`); `detection.py` keeps its existing baseline entry (its hits are the native-selector seed list, which R7 keeps) and the plan
    records that carry-over in its SUMMARY; the spec-config evals plan (26) removes its own baseline entry in the same commit.
16. Test modules (all created as stubs by plan 01, so no later plan regenerates `Makefile` or `.pre-commit-config.yaml`; the stub shape is the one of
    `35-01-PLAN.md` task 2): `test_config_status`, `test_role_orders`, `test_lane_settings`, `test_config_role_write`, `test_spec_config_lane_json`,
    `test_config_herdr_identity`, `test_lane_pool`, `test_lane_price`, `test_lane_data_use`, `test_lane_order`, `test_propose_cmds`, `test_lane_effort`,
    `test_effort_probe`, `test_no_seed_refusal`, `test_spec_chain_text`, `test_spec_config_flow_text` (unit group) and `test_ai_kit_spec_exec_formula_e2e`
    (e2e group: `E2E_MODULES`, `E2E_RECORDED_SECS` in `tools/run_unittest_parallel.py`; plan 08 refreshes its recorded seconds). A plan that fills a stub
    keeps its `sys.path` preamble and removes the `skipTest` stub method. A plan may not add a test module that is not in this list.
17. Plans that fill the same stub in different waves: `test_lane_settings` (11 then 17), `test_spec_chain_text` (16 then 19 then 27), `test_spec_config_flow_text`
    (24, 25, 26, 28), `test_no_seed_refusal` (14 then 28).
18. `to_resolved` puts unknown lane keys into `extra`; nothing outside `effort`, `service_tier`, `cursor_mode` reads them. `propose-lanes`, jev items and
    anything sent to jev never read `extra`, `usage_limit_note` or `data_use_line`.
19. Herdr: the wizard's write-path commands (`config-status`, `render-toml`, `propose-lanes`, `check-reviewer`) print and write identical bytes with and
    without `HERDR_ENV=1` and open no pane (fake herdr logs zero calls); `herdr-names` is excluded from that test by name (the owner-announced catalog step).
20. Lane key `purpose` stays written (the role split input); the SKILL sentence pinned by `test_session_default_purpose_matches_the_writer` stays unless plan 25 changes it
    together with that test.

### 3. Standing rules for every plan (also in `planner-common.md`)

- Every `files_modified` path is tracked or a new file; new runtime modules are stdlib-only, import nothing from `cli`, and keep pylint caps (max-args 5, max-locals 15,
  max-branches 12, max-returns 6, max-statements 50); `lane_settings`, `role_orders`, `lane_effort`, `lane_data_use`, `lane_pool`, `lane_price`, `lane_order` must not import
  `config_io` or `cli`.
- Fixture model ids: `placeholder-model-<n>`, `placeholder-alias-<n>`, `fake/<token>`, `fake-<token>`, provider `fake`; `router-env/<x>` only for the alias group under test;
  pool fixtures `fake:free`; placeholder CLI `placeholder-cli-1`; no grok anywhere.
- Tests run in a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`, never touch `.planning/`, the network, a real host or the real home.
- Each plan commits with `git add <explicit paths>` and `git commit -m "<type>(36-NN): <subject>"`, English, no attribution line.

### 4. Amendments at review cycle 1 (2026-11-20; these win over sections 1 to 3)

1. The one-line `_cmd_probe_quota` switch to `role_orders.role_order(config, "review")` moved from plan 36-22 into plan 36-10 (wave 3), so plan 36-20 (wave 7) stops writing a flat ladder without breaking `probe-quota`; plan 36-22 only adds `--role`.
2. Dependency changes: 36-21 depends on 36-05 and 36-18 only; 36-22 depends on 36-04, 36-10 and 36-21; 36-24 no longer depends on 36-22; 36-06, 36-07 and 36-09 depend on 36-02 (36-07 also on 36-06); 36-08 and 36-12 depend on 36-04; 36-14 depends on 36-11; 36-13 depends on 36-05, 36-06, 36-07, 36-09 and 36-10; 36-20 depends on 36-10; 36-28 depends on 36-10, 36-14, 36-16, 36-19 and 36-25.
3. `propose-lanes` rows print `efforts` (the levels `lane_effort.offered_levels` returns, runner-filtered), `efforts_refused` (list of [level, reason]) and `efforts_source`; the wizard offers only `efforts`.
4. Data-use record: five required keys plus `data_use_label` exactly when `data_use` is not `unknown` (item 4 above amended). A writer-only check `lane_settings.write_problem` refuses a lane that carries `pool` without a complete confirmed record (hand-written files still load).
5. `effort_source` is validated only by `lane_effort.effort_problem`.
6. Price figures: a models.dev zero comes only from the `free_or_local` band; figures print as `0` only when `pricing` holds both exactly 0; a positive `pricing` beside a zero band is state `conflict`; no stored `pricing` prints `figure not stored`. jev facts use only a closed ASCII vocabulary (`EFFORT_FACT_LEVELS`); a judge error falls back to the scorer (`scorer: jev error`).
7. Role-aware selection: review selection reads `config["review"]`, the adapter reads `resolved["execute"]`, each falling back to the flat view; the flat merge by key across roles and layers (`config_io.py:630-644`) is a recorded known limit under locked decision D-04.
8. Adapter `once` and `notice` answers dispatch every task natively on the session model (no `resolve-injection`, model omitted, no rounds 4 and 5 escalation); a stale `CONFIG_CHECK=` is ignored unless the plan's resume state file exists. A missing review `ai-kit-spec.py` prints a visible notice and continues on the session model.
9. Judge loop (36-29): the judges are referee-one and referee-two (AGENTS.md); only the plan reviews use referee-one alone.

Amendments at review cycle 2 (2026-11-20):

10. `config-status` takes an optional `--role review|execute` (unset = any role, so SPEC R1 is unchanged); the review skill's block runs it with `--role review` and the adapter's with `--role execute`, so an execute-only roster does not silence the review check and a review-only roster does not silence the adapter check.
11. The lanes that can be picked: review role = the lanes named in its order only; execute role = the ordered lanes first, then every remaining lane of the role in roster order (the selector ranks unlisted candidates after listed ones). The reader warning, the writer warning and the fallback warning share one helper (`selectable_lanes`).
12. `probe-quota --role execute` probes the execute lane; under `--role both` a key that names different lanes in the two roles probes the review lane and skips the execute lane with a stderr line. Role-correct review routing (`_route_reviewers` reads the review list) lands in 36-10, not 36-22.
13. A verified migration retires the old roster by an exclusive no-clobber link (`os.link`), verifies the linked bytes, then unlinks; a changed or undeletable file is kept and reported.
14. An effort probe is `accepted` only when the effort was actually composed into the call; a wrapper failure (preflight, crash, quota, auth, timeout) is `inconclusive`, `rejected` needs a host error line; `render-toml --catalog-path/--runtimes-json` fail with a named error when an explicit file is unreadable.
15. The writer drops false escalation and usage-limited flags; the judge plan enforces two judge verdicts per skill and carries the finding-count rule of AGENTS.md (more than three findings means the next round, at most three rounds).


## Part A

## Phase 36 research A: config layer and lane settings (R1, R3, R5, R9, R12 b-f)

All paths are under `skills/ai-kit-spec-review/ai_kit_spec/` unless a leading `tests/`, `docs/` or `skills/` says otherwise.
The unit brief `.aikit/brief/SKILL.md` is only a name list (symbol and file names), no facts: not used.
There is no `tools/ai-kit-spec.py`; the CLI entry is `skills/ai-kit-spec-review/ai-kit-spec.py` (7 lines, calls `cli.main`).
There is no `docs/config/config-file.md`; the config-file doc is `skills/ai-kit-spec-config/references/config-file.md`
(line 21 describes `[lanes.policy]`); the design record is `docs/config/design.md` (lines 37-44 name Phase 36).

### 1. FACTS

**Layered reader.** `config_io.py`:
- `cfg_load_layers(cwd, env)` 540: parsed (project, user) TOML, no migration, no trust.
- `cfg_resolve(cwd, env, warn_fn=None, migrate=True)` 614: migrates the project layer, reads project lanes through the trust gate
  (`_project_lanes` 599, `_trusted_lanes` 570, `_pending_project_lanes` 580), then `cfg_combine`.
- `cfg_combine(local, env, warn_fn, local_path, migrate)` 682: `local_only = bool(local) and local.get("strategy") == "local-only"` (690:
  the user file is not read then); returns `{"policy", "reviewers" (flat), "review", "execute"}`.
- Policy merge is shallow, `_combine_layers` 630-644: `{**DEFAULT_POLICY, **global.policy, **local.policy}`. `DEFAULT_POLICY` (17) =
  `{"mode": "single", "ladder": [], "timeout_tiers": [600, 1200, 1800]}`. A nested `review`/`execute` table in the project policy
  replaces the user's whole role table, so "project over user per role table" is already what the merge does.
- `cfg_merge_reviewers` 361-385: per `key`, `by_key[key].update(r)`; only `runtime` and `command` (`_VARIANT_FIELDS`) are popped when the
  local entry restates one. Every other field (effort, any new flag, pool, data-use) is inherited across a runtime/model change.
- `cfg_lanes_view` 400: role lists plus the flat `reviewers` view (review lanes, then execute lanes whose key no review lane has).
- Dangling keys today: the reader never checks them (`resolve_ladder_pick` quota.py:86-91 skips a key with no entry). Only the writer
  drops a ladder key, and only when that key's entry was rejected by the validator (`_cfg_lanes_policy` 856-870, message
  `policy.ladder: dropped dangling reference(s) to rejected reviewer key(s) [...]`). A key naming no lane at all is kept and ignored.

**Validator and writer.**
- `validate_reviewer_fields(entry)` 749-779: refuses `route`, any dict value, bad `purpose`, non-bool `is_router`/`fallback_quota`, then
  `_validate_pair_fields` 716 (runtime must be in `_RUNNER_RUNTIMES` 713 = rows with `row.runner`; message at 722 prints the table).
  Every other field is accepted untouched, so `effort`, flags and pool already pass today without checks.
- `cfg_render_lanes(config, existing_text)` 909: JSON `{"strategy"?, "policy"?, "lanes": [...]}`; `_cfg_render_reviewers` 797 (legacy
  normalisation), `_cfg_partition_reviewers` 782, `config_migrate.split_by_purpose` (role by `purpose`), `_cfg_lanes_policy` 856,
  `_splice_roster` 881, verify by re-parse against `_expected_lanes` 898. `cfg_write_toml` 941 publishes through `toml_splice.publish`.
- `_splice_roster` 888-892 does `toml_splice.set_table(text, ("lanes","policy"), policy, remove=gone)` with the WHOLE policy dict.
  `toml_splice.set_table` 429-462 writes inline values only (`toml_value` 56: bool, int, float, str, list, dict as inline table;
  `_basic_string` 86 escapes control chars, so a string is always one line) and `_splice_table` 457-461 never writes a key that has a
  child block (`_child_keys`). A nested `review` dict inside `policy` would therefore be written as an inline table on a fresh file, and
  fail `_verify` (SpliceError) when `[lanes.policy.review]` already exists. The writer MUST split flat keys from role tables.
- `remove_table(text, path)` 756 and `set_table` accept a path of any depth; `set_array` 727 handles `[[lanes.review]]`.
- `_refresh_ladder_comment` 829 / `_ladder_comment_lines` 814: generated `# Priority fallback order ...` comment above `[lanes.policy]`
  from `policy["ladder"]`; pinned by `tests/test_config_layers.py:576-596` and `tests/test_ai_kit_spec.py:405-430`.
- The runner template reads only `[runner]` tables; `[lanes.*]` headers (any depth) are opaque to it (`cross-ai.mjs:3287-3316`):
  a `[lanes.policy.review]` table is safe for the runner.
- Trust: `trust.command_lanes_bytes(lanes, keys)` 88 digests only role LISTS (`roles = sorted(role for role, items in lanes.items() if
  isinstance(items, list))`), so policy tables never change trust; every new lane field on a command-bearing lane is inside the digest.

**Consumers of the order today.**
- `quota.resolve_reviewers` quota.py:170 `ladder = policy.get("ladder", [])` then `_filter_ladder_by_purpose(reviewers, ladder, "review")`
  (103, falls back to the full ladder with a warning when the filter empties it).
- `cli._cmd_probe_quota` 795-805: `routing.probe_keys(config["policy"]["ladder"], routes)` (routing.py:182 keeps routes in
  `PROBE_ROUTES` = subprocess, unverified, custom) then `quota.refresh_quota_cache` (287; 1 h TTL, 30 s probe per key,
  `_probe_call` 247 uses `review_spec`).
- Execute adapter: `ai_kit_spec_superpowers/dispatch_injection.py:188` `top_n_keys = resolved.get("policy", {}).get("ladder", [])`;
  candidates come from the FLAT `reviewers` view (177-187: key, model, runtime, vendor, command, task_affinity, context_limit, purpose,
  effort, service_tier). `execute_selection.resolve_execute_candidates` 115 ranks by `top_n_keys` then affinity (`ExecuteResolveOptions.top_n_keys`).
  The adapter quota-probes ALL candidate keys itself (`ai_kit_spec_superpowers/cli.py:179-184`), not through `probe-quota`.
- `probe-quota` has two callers: the review flow (`skills/ai-kit-spec-review/references/cross-ai-dispatch.md:152`, SKILL.md Step 0.7)
  and spec-config `--check-only` (`skills/ai-kit-spec-config/references/check-only.md:50`).
- `to_resolved` quota.py:41-51: every entry field not in `_KNOWN_REVIEWER_FIELDS` (key, model, vendor, runtime, command; config_io:19)
  lands in `extra`; `review_spec` runner_dispatch.py:99 reads only `effort`, `service_tier`, `cursor_mode` from it. New flat lane keys
  are therefore carried in `extra` and ignored by every run today (printed inside `resolve-reviewers` JSON `extra`).

**Migration.** `config_migrate.py`: `MIGRATED_SUFFIX = ".migrated"` 16; `_check_new_text` 267 is the value check (runs BEFORE publish);
`_retire_old(old, new_path, raw, state, warn_fn)` 343-360 is the rename guard (rename only while `_read_bytes(old) == raw`, else warn
`... changed during its migration ...` and return `"deferred"`) and already has 5 parameters; `_retired_name` 334 avoids a clash.
`migrate_layer(new_path, *, warn_fn, trust_dir=None, trust_bytes_fn=None)` 363 has ONE caller: `config_io._migrate` 483-493 (line 490).
All implicit migrations reach it through `_migrate`: `cfg_migrate_project` 496 (called by `cfg_resolve` 624, `cfg_trust_project` 527,
`_cmd_trust_local` cli.py:995), `cfg_migrate_user` 504 (called by `_user_lanes` 661), `cfg_migrate_target` 512 (`render-toml` cli.py:906).
`_migrate` receives `env` (a dict, never `os.environ`); `config_migrate` imports only `trust` and `toml_splice`.
Env-only settings are documented in `docs/config/design.md` "Environment-only settings" (174-191); names like `AI_KIT_LAYA_URL` exist.

**Wizard to writer hand-off today** (`skills/ai-kit-spec-config/SKILL.md`): Step 3 (371-412) writes `$SCRATCH/config.json` shaped
`{"strategy"?: "local-only", "policy": {"mode", "ladder": [keys], "timeout_tiers"?}, "lanes": [entry,...]}` and runs
`python3 "$TOOLS_PY" render-toml --json-config "$SCRATCH/config.json" --out <target> [--replace] > rendered.toml 2> render-toml-stderr.txt`
(`TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/ai-kit-spec.py"`, line 37). Each lane is a flat object: `key`, `runtime`+`model` (or neither, or a
custom `command`), `purpose` (review|execute|both; `both` writes one entry per role), optional `is_router`/`fallback_quota` (only when
true), flat `timeout_tiers`, `strength`. Step 2.5 (270-283) runs `check-reviewer --key --model --vendor --runtime --catalog-path
[--extra-json]` before a save. `render-toml` (cli.py:895-920): refuses an existing `[lanes]` without `--replace` (`_render_toml_refusal`
877), migrates the sibling old roster first for a `config.toml` target (906), prints `WARNING: N issue(s) found and NOT written: ...`
for rejected lanes (config_io:936). So every new field travels as a FLAT key on a lane object, and the per-role orders travel as nested
objects under `policy`. The validator refuses dict values on a LANE, so no nested record can sit beside a lane.

**Herdr.** `herdr_source.herdr_available(env, which_fn)` herdr_source.py:25 (needs `HERDR_ENV == "1"` and `herdr` on PATH).
`tests/herdr_fakes.py` has `write_herdr_fake(bin_dir, answers, log_path)` and `herdr_calls(log_path)` (missing log = no calls).
Phase 35 shipped `herdr-names` (`catalog_cmds.cmd_herdr_names` 233): with `HERDR_ENV=1` it starts copilot in a herdr pane
(`skills/ai-kit-spec-config/references/catalog.md:23-27`, announced to the owner first).

### 2. CONTRADICTIONS (spec/context vs code that exists)

1. R3 "a key in the order that names no lane of that role is dropped with a warning, as dangling keys are today": today only a key whose
   entry was REJECTED is dropped (writer only, config_io:856-870). A key naming no lane is kept and silently ignored by readers. This is
   new behaviour in both reader and writer.
2. R3 "the wizard keeps writing `purpose`": the writer splits roles by `purpose` (`split_by_purpose`), so `purpose` is not "kept for old
   readers" only: it is the input of the role split. Dropping it later needs a different role selector in the JSON.
3. R1 acceptance mentions a malformed file giving a named error, exit 2: `cli.main` (1210-1217) already maps `ConfigError` to
   `ai-kit-spec: config error: <path>: <msg>`, exit 2; the new command only has to let it propagate. `cfg_config_base` raises `ConfigError`
   for a missing absolute HOME, whereas `docs/config/design.md` "Resolver rule" step 4 says every reader treats the user layer as absent.
   Code raises; `config-status` will exit 2 in that case unless the planner wants otherwise.
4. SPEC says `lane_escalation(entry)` reports "no target" for a one-lane role, and `lane_fallback(role_lanes, key)` has no order
   argument. Neither can be answered from `entry` alone / without the role's order. (Resolved in section 4.)
5. R12 f / D-19 / prohibition "the wizard opens no pane": Phase 35's `herdr-names` (a wizard catalog step) DOES open a pane when
   `HERDR_ENV=1`. The identity test must be scoped to the write path (`config-status`, `render-toml`, `propose-lanes`, `check-reviewer`)
   and name `herdr-names` as the owner-announced exception, or the spec text needs the one-line amendment.
6. ROADMAP criterion 8 / D-20: "the flag is written with the lane's pool". For "neither flagged nor in the same pool" to exclude an
   UNFLAGGED sibling (owner answered "no" for a second free model of the same provider), the pool must also be on unflagged free lanes.
   The text only says the flagged lane carries it. Chosen below: `pool` is allowed on any lane.
7. D-04 "`probe-quota` probes the keys of both" vs the facts: `probe-quota` is called only by the review flow and `--check-only`; the
   execute adapter probes its own candidates. Probing both on every review run would spend calls (and allowance of free lanes) for lanes
   the review never uses.
8. `design.md` and `config-file.md` still say the old roster "stays recoverable as `.migrated`" (design.md 132, 144, 156-157;
   config-file.md; README.md:63; SKILL.md Step 2.1 line 158). All change with R9. `tests/test_config_migrate.py`,
   `test_config_layers.py`, `test_ai_kit_spec_legacy_config.py` assert the `.migrated` file (listed in 4.5).
9. SPEC Background says new per-role tables are replaced "as a whole by the project layer": true, and also means a project review order
   that names only project lanes leaves user lanes unordered, and `resolve_ladder_pick` only walks ordered keys, so they are never picked.

### 3. OPEN QUESTIONS answered

- **D-10 backup opt-in.** Environment variable `AI_KIT_KEEP_MIGRATION_BACKUP` (value `1` keeps; anything else deletes), read in
  `config_migrate.py` only through `keep_backup_from_env(env: dict) -> bool`. It is passed from the one seam, `config_io._migrate`, as
  `keep_backup=` to `migrate_layer`, so `probe-quota`, `resolve-reviewers`, `trust-local` and `render-toml` all honour it (verified
  above: `_migrate` is the only caller). `render-toml --keep-backup` sets the same variable in the env dict it passes (`env = {**env,
  KEEP: "1"}`), so there is one mechanism. No `--keep-backup` on the other commands (YAGNI: the variable covers them).
- **D-04 probe-quota scope.** Add `--role review|execute|both` to `probe-quota`, default `review` (its only runtime caller is the review
  flow); `--check-only` (`check-only.md`) passes `--role both`; `both` = review order then execute order, de-duplicated by key (the quota
  cache is keyed by `key`, one probe covers a key in both roles). Unordered lanes are never probed (as today).
- **Flagged lane in probe-quota.** Probe it like any lane, no special case. Skipping would leave no quota row and `_has_quota` (quota.py:54)
  treats "no entry" as available, which would send a review to a capped lane unchecked; the 1 h TTL already caps the spend at one 30 s
  call per hour per lane. The wizard's own test call says in one line that it spends part of the allowance (R12 e, SKILL text).
- Not mine (other researchers): jev score stability (D-07), catalog class/effort names (D-05, D-07), local-vs-hosted price record (D-18).

### 4. DESIGN PROPOSAL

Decisions in one line each; no choice is left to the executor.

#### 4.1 R1 `config-status` (new `config_status.py`)
```
def config_status(cwd: str, env: dict) -> dict
def register_parsers(sub) -> None          # adds "config-status" with required --cwd
def cmd_config_status(args, deps) -> int   # prints one JSON line, returns 0
COMMANDS = {"config-status": cmd_config_status}
```
Same factory shape as `catalog_cmds.py` (`register_parsers`, `COMMANDS`); `cli.py` gets 3 lines: import, `config_status.register_parsers(sub)`
in `_build_parser` (453-456), `**config_status.COMMANDS` in `_COMMANDS` (1198). Output (stdout, one line, ASCII):
`{"state": "active"|"pending"|"none", "checked": [{"layer": "project"|"user", "path": "<abs>", "status": "<s>"}, ...]}` with `checked`
ordered project then user, `status` one of `missing`, `empty`, `lanes`, `untrusted`, `pending-migration`, `skipped-local-only`.
Logic (read only; reuse `cfg_local_path`, `cfg_global_path`, `cfg_read_bytes`, `cfg_parse_toml_bytes`, `cfg_lanes_table`,
`cfg_project_trust_bytes`, `trust.is_trusted`, `config_migrate.pending/read_legacy`; no migration, no write):
1. Project file exists: parse (a malformed file raises `ConfigError`, exit 2 via `main`). A layer "has a lane" when `review` or `execute`
   is a list holding at least one dict with a str `key` (so a session-default lane counts; empty arrays or a bare `[lanes]` are `empty`).
   Has a lane: `canonical = cfg_project_trust_bytes(lanes, env)`; `None` or `trust.is_trusted(cfg_trust_store_dir(env),
   os.path.realpath(path), canonical)` gives `lanes`, else `untrusted`.
2. No project file or `empty`, and `config_migrate.pending(path)`: `pending-migration` (the old roster is read with `read_legacy` only to
   surface a malformed old file as exit 2).
3. User layer is read unless the project `[lanes]` table is non-empty with `strategy == "local-only"` (then `skipped-local-only`,
   mirroring `cfg_combine` 690, including the empty-roster local-only case which stays `none`). Same lane/pending test, no trust.
4. State: any `untrusted` or `pending-migration` gives `pending` (a pending item needs an owner decision, and the untrusted warning path
   of the reader still runs); else any `lanes` gives `active`; else `none`. Chosen over "active wins" because a cloned project roster
   with commands must reach the trust flow even when the user layer works.
Estimate 110 lines code, 170 lines test. Test module `tests/test_config_status.py` (new): scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1` set by
the runner; cases = SPEC R1 list (none; active user only; active project only; pending untrusted command lane; pending old roster at
each layer; local-only with empty roster beside full user roster = none; malformed project and malformed user file exit 2) plus a no-write
check (hash every file in HOME and project before/after) and both-layers-active (paths listed project first).

#### 4.2 R3 per-role orders: reader (new `role_orders.py`)
```
ROLES = ("review", "execute")
def role_orders(policy: dict, role_lanes: dict, warn_fn) -> dict            # {"review": [keys], "execute": [keys]}
def role_order(config: dict, role: str) -> list                              # consumer reader
def ordered_lanes(config: dict, role: str) -> list                           # lane dicts of the role in order, first place wins
def split_policy(policy: dict) -> tuple[dict, dict]                          # (flat keys, {role: table}) for the writer
```
- `role_orders`: for each role, the table `policy.get(role)` (a dict) with a list `ladder` wins; else the legacy shared `policy["ladder"]`
  filtered to the role's lane keys. A role table from EITHER layer beats a legacy ladder from either layer (the shallow merge already
  makes project replace user per role table). Keys are kept in order, duplicates keep the first place, keys outside the role are dropped:
  - table `ladder`: a key naming no lane of the role warns `ai-kit-spec: [lanes.policy.<role>] ladder names no <role> lane: [<keys>]; dropped`.
  - legacy ladder: once, `ai-kit-spec: the shared [lanes.policy] ladder loads as one order per role (review: <n> keys, execute: <m> keys);
    the next write replaces it with [lanes.policy.review] and [lanes.policy.execute]`; a key naming no lane in either role warns with
    the same dangling text (`[lanes.policy] ladder names no lane: [<keys>]; dropped`).
  - a non-list `ladder` or non-dict role table is ignored with one warning naming the table.
- `role_order(config, role)` returns `config["orders"][role]` when `"orders"` is in `config`, else falls back to
  `config.get("policy", {}).get("ladder", [])`: the 100+ existing hand-built configs in tests keep passing (the fallback goes when
  Phases 37/41 retire `purpose`).
- `cfg_combine` (config_io:682-705) adds `"orders": role_orders(policy, {"review": review_lanes, "execute": execute_lanes}, emit_warn)`;
  `policy` stays the raw merge (so `test_config_layers.py:114` `resolved["policy"] == DEFAULT_POLICY` and the reads of
  `resolved["policy"]["ladder"]` in `test_ai_kit_spec_legacy_config.py:240`, `test_ai_kit_spec.py:551` still hold).
- Consumers switched: `quota.py:170` to `role_order(config, "review")`; `cli.py:798` to `role_order`/`--role` (4.3);
  `dispatch_injection.py:188` to `role_order(resolved, "execute")`, and its candidate loop (177) reads `resolved.get("execute",
  resolved.get("reviewers", []))` so a review-only lane is no longer an execute candidate (fallback keeps the fake `cfg_resolve` dicts
  of the adapter tests working). `import` direction: `role_orders` imports nothing from the package (pure), so `quota` and `config_io`
  may import it.
- Tests (new `tests/test_role_orders.py`, ~150 lines): both orders read, legacy split with note, dangling warning, duplicate key,
  project-over-user per role (project review table replaces the user's, user execute table survives), role with no lane, `role_order`
  fallback for a config with no `orders`. Existing tests to edit: none for the reader alone (raw `policy` unchanged).

#### 4.3 `probe-quota --role` (in `cli.py`, 12 lines)
`p_quota.add_argument("--role", choices=["review", "execute", "both"], default="review")`; `_cmd_probe_quota` builds
`keys = role_order(config, "review")` (and execute for `execute`/`both`, appended, de-duplicated) before `routing.probe_keys`.
`check-only.md` line 50 command gets `--role both`; its text at lines 15 and 66 (`policy.ladder`) is rewritten to per-role orders.
Tests: add 3 cases in `tests/test_role_orders.py` using `cli.main(["probe-quota", ...], ...)` with the fake runner seam as
`tests/test_ai_kit_spec_routing.py::test_probe_quota_probes_only_dispatchable_routes` does.

#### 4.4 R3 per-role orders: writer (`config_io.py`)
- JSON `policy` shape: `{"mode"?, "timeout_tiers"?, "review": {"ladder": [keys]}?, "execute": {"ladder": [keys]}?}`; a flat `ladder`
  is still accepted (old wizard wiring) and is split by role with one stderr note, never written flat.
- `_cfg_lanes_policy(policy, dropped_keys, rejections, role_keys)` (4 args; `role_keys = {"review": set, "execute": set}` from the valid
  lanes after `split_by_purpose`): builds the nested dict to write. Per role: ladder minus `dropped_keys` (existing rejection line,
  now `policy.<role>.ladder: dropped dangling reference(s) to rejected lane key(s) [...]`), minus keys naming no lane of the role
  (`policy.<role>.ladder: dropped key(s) naming no <role> lane [...]`), de-duplicated; the role table is written only when it has at
  least one lane AND a non-empty ladder after filtering (a role the owner did not configure gets nothing; an old table is removed).
  Other keys inside a role table are kept as given.
- `_splice_roster` (881-895) becomes: `flat, roles = role_orders.split_policy(policy)`; `set_table(("lanes","policy"), flat,
  remove=gone_flat)` where `gone_flat` = current policy names not in `flat` AND not in `ROLES` (`ladder` is therefore removed on the
  rewrite of a legacy file); then for each role `set_table(("lanes","policy",role), table, remove=gone_role)` or, when the role is
  absent but present in the file, `remove_table(("lanes","policy",role))`; then the arrays as before; then the comment refresh.
  `_expected_lanes` is unchanged (the parsed policy is the nested dict).
- Comment refresh generalised: `_refresh_ladder_comment(text, path, ladder, double)` called for `("lanes","policy")` with `[]` (removes a
  generated block left from a legacy file) and for each role path; the role block starts `# Priority fallback order, <role> lanes (first
  available wins the` (keeps `_LADDER_COMMENT_HEAD`), the `double` clause only for review. A user's own comment above a header stays.
- Tests that break and must be edited in the same plan (flat `ladder` in the JSON now renders per role): `tests/test_config_layers.py`
  474-530, 540-550, 560-596, 606-631; `tests/test_ai_kit_spec.py` 349-355, 405-430 (comment text), 474-496, 533-552;
  `tests/test_ai_kit_spec_legacy_config.py` 554-561 (`ladder = []`). Keep one legacy-flat-input case per behaviour. New
  `tests/test_config_role_write.py` (~200 lines): both orders written, read-back through `cfg_resolve`, byte preservation (comments,
  `[runner.retry]`, unrelated tables identical before/after a second write with a changed order; only the order lines and the generated
  comment differ), legacy file rewritten (flat `ladder` gone, role tables present), dangling key warning, role with no lane (no table; an
  existing table removed), no order written for an unconfigured role, writer rejects what the validator rejects.

#### 4.5 R9 migration default (`config_migrate.py`, `config_io.py`, `cli.py`)
```
KEEP_BACKUP_ENV = "AI_KIT_KEEP_MIGRATION_BACKUP"
def keep_backup_from_env(env: dict) -> bool                      # env.get(KEEP_BACKUP_ENV) == "1"
def _unchanged(old, new_path, raw, warn_fn) -> bool              # the snapshot guard shared by both retire paths
def _keep_old(old, new_path, raw, state, warn_fn) -> str         # today's rename (renamed from _retire_old)
def _delete_old(old, new_path, raw, state, warn_fn) -> str       # os.remove(old) while bytes equal the snapshot
migrate_layer(new_path, *, warn_fn, trust_dir=None, trust_bytes_fn=None, keep_backup=False)  # 5 args, at the cap
```
`migrate_layer` picks `retire = _keep_old if keep_backup else _delete_old` (no 6th argument anywhere). `_delete_old` messages:
`ai-kit-spec: migrated <old> to <new>; the old file was deleted (set AI_KIT_KEEP_MIGRATION_BACKUP=1 or pass --keep-backup to keep a
.migrated copy next time)`; an `os.remove` OSError warns `... migrated <old> to <new> but could not delete the old file (<exc>); the
next run finishes it` and returns `state` (same recovery as the rename failure). The "completed" state deletes too. The value check
`_check_new_text` still runs before publish, so a failed check deletes nothing (existing `LegacyRosterError`). `config_io._migrate`
passes `keep_backup=config_migrate.keep_backup_from_env(env)`. `render-toml` gets `--keep-backup` (store_true) and sets the variable in
the env dict before `cfg_migrate_target(args.out, env)` (cli.py:906). Old trust records under `review-spec-trust/` are left as today.
Tests to change: `tests/test_config_migrate.py` (`MigrationCase.migrate` helper 97 gets class attribute `keep_backup = True` so lines 135,
292-295, 313, 356, 451 and the rename-failure tests 372-390 keep their meaning; new class `TestDefaultDelete` with `keep_backup=False`:
passing migration leaves no old file and no `.migrated`, `keep_backup=True` leaves the rename, failed value check leaves the old file
byte-identical, old file changed during the run (counting_reader pattern 396-415) left in place with `changed during its migration`,
`os.remove` failure then `completed`); `tests/test_config_layers.py` 263, 462, 666 and `tests/test_ai_kit_spec_legacy_config.py:125`
(set the env switch where they assert `.migrated`, add one default-delete case through `cfg_resolve` and one through `render-toml
--replace`). Docs: design.md rows 132, 144, 156-157, Environment-only settings (add the variable), config-file.md, README.md:63,
SKILL.md Step 2.1 line 158 wording. Estimate 70 lines code, 130 test lines.

#### 4.6 R5/R12 `lane_settings.py` (validators, normaliser, readers)
Flat keys on any lane (either role), exact names:
`effort` (str, `^[a-z0-9][a-z0-9_.-]*$`, empty string = named error), `escalate_runtime`, `escalate_model`, `usage_limited` (bool),
`usage_limit_note` (str), `pool` (str `^[a-z0-9][a-z0-9._-]*(/[a-z0-9][a-z0-9._-]*)?$`, form `<provider>/<tier>`), and the data-use record as
five flat keys (a nested record is refused by the validator): `data_use` (`zero_retention` | `may_be_kept_or_trained` | `unknown`),
`data_use_note` (display line), `data_use_source` (str), `data_use_read` (`YYYY-MM-DD`), `data_use_label` (`verified` | `reported`),
`data_use_confirmed` (bool, only `true` is storable: a no or skip writes no lane).
```
class LaneSettingError(ValueError)                                   # message starts with the lane key and names the setting
class Escalation(NamedTuple): runtime: bool; model: bool
class UsageLimit(NamedTuple): limited: bool; note: str
LANE_FLAG_KEYS = ("escalate_runtime", "escalate_model", "usage_limited")
MODEL_BOUND = ("effort", "usage_limited", "usage_limit_note", "pool", "data_use", "data_use_note", "data_use_source",
               "data_use_read", "data_use_label", "data_use_confirmed")
def clean_note(text: str) -> str                                     # control chars removed, one line, capped at 200 chars
def normalise_lane_settings(entry: dict) -> dict                     # writer-side: clean_note on both note keys; nothing else changes
def validate_lane_settings(entry: dict, key) -> str | None           # same str|None contract as validate_reviewer_fields
def lane_escalation(entry: dict) -> Escalation                       # absent = False; non-bool raises LaneSettingError
def escalation_target(role_lanes: list, key: str, kind: str) -> str | None   # kind "runtime"|"model"; role_lanes already in the role's order
def lane_usage_limit(entry: dict) -> UsageLimit                      # non-bool raises LaneSettingError naming 'usage_limited'
def lane_fallback(role_lanes: list, key: str) -> str | None          # role_lanes already in the role's order
def all_flagged(role_lanes: list) -> bool                            # lenient (value is True), for the reader warning
```
- Error text: `"<key>: '<name>' must be a boolean"` (the existing `is_router` wording, config_io:778), `"<key>: 'usage_limit_note' needs
  'usage_limited = true'"`, `"<key>: 'effort' must be a non-empty lowercase token"`, `"<key>: 'data_use' must be one of
  ['may_be_kept_or_trained', 'unknown', 'zero_retention']"`, `"<key>: 'data_use_confirmed' must be true when present (a lane whose
  owner declined is not written)"`, and a data-use key without the others: `"<key>: data-use record needs data_use, data_use_source,
  data_use_read, data_use_label and data_use_confirmed"`. `false` flags are valid input (a hand-written file); the wizard never writes one.
- `escalation_target`: the lane list starts after `key`; `runtime` kind returns the first later lane whose `runtime` differs, `model`
  kind the first later lane with the same `runtime` and a different `model`; no later match or a role with one lane gives `None`
  (adjacency edge). "Never a model that is not a configured lane" holds by construction.
- `lane_fallback`: scan the WHOLE role order (D-16 "first lane of the role in the role's order"), skip `key` itself, any flagged lane
  (`lane_usage_limit(...).limited`), and any lane whose non-empty `pool` equals the key lane's `pool`; return the first key left or `None`
  (also `None` for an unknown `key`). Duplicate keys: `ordered_lanes` (4.2) already keeps the first place.
- Hooks in `config_io.py` (each 2-8 lines): `validate_reviewer_fields` calls `lane_settings.validate_lane_settings` before
  `_validate_pair_fields`; `_cfg_render_reviewers` maps `normalise_lane_settings` over entries; `cfg_merge_reviewers` pops every
  `MODEL_BOUND` field the local entry does not restate when it restates `runtime`, `command` or a different `model` (otherwise a
  data-use confirmation or flag given for one model silently rides along to another through the layered merge: tested); `cfg_combine`
  warns once per role holding lanes where `all_flagged` is true: `ai-kit-spec: every <role> lane is marked usage_limited (<keys>); no
  lane to fall back to` (reader warning for a hand-written file; `render-toml` prints the same line on stderr after a write, so the
  explicit-none write succeeds with its warning; nothing refuses).
- Source-scan guard (spec "a test that fails when a writer, ranking or default path sets a flag"): in `tests/test_lane_settings.py`,
  read every `ai_kit_spec/*.py` and assert the literals `escalate_runtime`, `escalate_model`, `usage_limited` occur only in
  `lane_settings.py` (plus `config_status`-free modules: none), and that `cfg_render_lanes` on lanes without flags emits none.
- Non-vacuity: the same test plants a fake module text containing the literal and asserts the scanner flags it.
- Tests (`tests/test_lane_settings.py`, ~230 lines): every validator error above, `clean_note` (control chars, newline, 200 cap, not
  parsed), `lane_escalation` on a layered merge (via `cfg_resolve` with project over user), both flags true, non-bool refused with key,
  `escalation_target` (runtime kind, model kind, one-lane role, order), `lane_usage_limit` on a layered merge and non-bool, `lane_fallback`
  (first unflagged in order, skips same pool, skips an unflagged same-pool sibling, none when all flagged, none for unknown key),
  `all_flagged` warning from `cfg_combine` for a hand-written file, merge drops model-bound fields on a model change, byte-preserving
  write of every new key through `cfg_render_lanes` (comments and unrelated tables kept), dict-valued data-use record refused.

#### 4.7 R12 f herdr identity test (no production code beyond 4.6's warning)
`tests/test_config_herdr_identity.py` (~120 lines). Scratch HOME and project; fake herdr via `tests/herdr_fakes.write_herdr_fake`
(empty answers table, so any call exits 1 and is logged). Run the wizard's write-path commands twice through `cli.main(argv,
env_fn=...)`: env A without `HERDR_ENV`, env B with `HERDR_ENV=1` and the fake first on PATH: `config-status`, `render-toml` (a JSON with
both roles, per-role orders, a flagged zero-price lane with pool and data-use record), `resolve-reviewers --no-cross-ai`-free path is
not needed. Assert identical captured stdout, identical stderr, byte-identical written `config.toml`, and `herdr_calls(log) == []`.
`herdr-names` is excluded and named in a comment (contradiction 5). `propose-lanes` (other researcher) joins the same loop when it lands.

#### 4.8 Wizard write-path extension (doc plus contract test)
The JSON the wizard writes (SKILL Step 3, `references/config-file.md`) gains: per-role `policy.review.ladder` / `policy.execute.ladder`
(no flat `ladder`), lane keys `effort`, `escalate_runtime`, `escalate_model` (only when true), `usage_limited` (only on a yes),
`usage_limit_note`, `pool`, and the five `data_use*` keys (only with the owner's yes), and the `render-toml --keep-backup` flag. Add
one example block to `references/config-file.md` marked as an example (`router-env/<x>` or `placeholder-model-1` ids only) and
`tests/test_spec_config_lane_json.py` (~90 lines): extract that fenced JSON, run it through `cfg_render_lanes`, parse the result, assert
every key survives and no `WARNING:` line. This keeps doc and writer in step. SKILL.md edits themselves belong to the skill-text plans.

#### 4.9 Unit cut (plans of at most 3 tasks, ~5 files, ~300 lines; wave order matters because most edit `config_io.py`)
- **U1 config-status**: `config_status.py`, `cli.py` (3 lines), `tests/test_config_status.py`; regenerate lists. ~280 lines. Independent.
- **U2 migration default** (R9): `config_migrate.py`, `config_io.py` (`_migrate`), `cli.py` (`--keep-backup`), edited tests (4.5), docs
  rows. ~200 lines. Independent of U1; run after U1 (both touch `cli.py`).
- **U3 role orders reader** (R3 read): `role_orders.py`, `config_io.py` (`cfg_combine`), `quota.py`, `dispatch_injection.py`,
  `tests/test_role_orders.py`. ~260 lines.
- **U4 probe-quota `--role`**: `cli.py`, `check-only.md`, 3 tests. ~60 lines. Can join U3 as its third task.
- **U5 lane_settings validators** (R5, R12 b/d/data-use shape): `lane_settings.py` (validate, clean, normalise, MODEL_BOUND),
  `config_io.py` (3 hooks), `tests/test_lane_settings.py` part 1. ~300 lines. After U3.
- **U6 lane_settings readers** (`lane_escalation`, `escalation_target`, `lane_usage_limit`, `lane_fallback`, `all_flagged`, reader
  warning in `cfg_combine`, source-scan guard): `lane_settings.py`, `config_io.py`, tests part 2. ~220 lines. After U5 and U3.
- **U7 role orders writer** (R3 write): `role_orders.split_policy` already in U3; `config_io.py` writer functions, comment refresh,
  the edited old tests, `tests/test_config_role_write.py`. ~300 lines. After U3, U5.
- **U8 wizard write-path and herdr identity**: `references/config-file.md` example, `tests/test_spec_config_lane_json.py`,
  `tests/test_config_herdr_identity.py`, explicit-none warning line in `cfg_render_lanes`. ~260 lines. Last (needs U5-U7).
- Generated lists: new test modules are `test_config_status`, `test_role_orders`, `test_lane_settings`, `test_config_role_write`,
  `test_spec_config_lane_json`, `test_config_herdr_identity`: all join the `unit` group; run `python3 tools/gen_test_groups.py` and
  commit `Makefile` (line 12 `# unit:` list) and `.pre-commit-config.yaml`; `tests/test_gate_scope.py` checks them. None needs uv or a
  PTY. U2 adds no module. New runtime modules (`config_status`, `role_orders`, `lane_settings`) are stdlib-only and import nothing from
  `cli`; `lane_settings` and `role_orders` must not import `config_io` (config_io imports them).

### 5. GOTCHAS

1. `toml_splice.set_table` cannot take nested dicts for a key that has a child block, and `_verify` raises `SpliceError` when it tries:
   split flat keys and role tables before calling it, and exclude role names from the `remove` tuple (they go through `remove_table`).
2. `[lanes.policy]` may have no header of its own once only `[lanes.policy.review]` exists: `set_table(..., ("lanes","policy"), {})` is a
   no-op then (parsed `expected == current`), which is fine; do not force an empty header.
3. Legacy rewrite: the flat `ladder` line must be removed (it falls out of `gone_flat`) and the generated `# Priority fallback order`
   block above `[lanes.policy]` must be removed too, or the file keeps a stale list: the refresh call with `[]` does it only when the first
   comment line starts with `_LADDER_COMMENT_HEAD`; a user's own comment stays.
4. `to_resolved` puts all new flat keys into `extra`; nothing reads them yet, but `resolve-reviewers` prints `extra`, so `usage_limit_note`
   and data-use text appear in that JSON. Never pass `extra` to jev (the SPEC prohibition is about the proposal item text; check the
   proposal builder does not reuse `extra`).
5. `cfg_merge_reviewers` inheritance: without the `MODEL_BOUND` drop, a project entry that changes a user lane's model keeps the user's
   `usage_limited`, `pool`, `effort` and data-use confirmation. Trust digests include these fields on command-bearing lanes.
6. A lane key in both roles is two entries; `ordered_lanes` and `lane_fallback` work on one role's list only. The probe cache is keyed by
   `key`, so a key in both roles is probed once, and `_reviewer_by_key` uses the flat view (review entry wins).
7. `pylint` caps: `migrate_layer` is at 5 args (keyword-only counts), `_retire_old` already had 5: the keep/delete split avoids a 6th.
   `_cfg_lanes_policy` goes from 3 to 4 args. `cfg_combine` is near the statement cap: put the warning and orders in helpers.
8. `config_io.py` is edited by U2, U3, U5, U6, U7 and by the R7 researcher (`_RUNNER_RUNTIMES` 713, 721-722 and lines 104-105): serialize
   the plans in the wave order above to avoid merge conflicts; grok is only an existing row, add nothing for it.
9. Tests must never write into `.planning/` and must use placeholder ids (`placeholder-model-1`, `fake/<token>`); `router-env/<x>` only for
   alias cases. `tests/test_config_design_record.py` scans `[...]` table names in `docs/config/design.md` "Tables" for host and skill
   names: `[lanes.policy.review]` and `[lanes.policy.execute]` pass (the existing `[[lanes.review]]` already does); add both to the Tables
   section and the new environment variable to "Environment-only settings".
10. `os.remove` in `_delete_old` needs a mock target in tests (`config_migrate.os.remove`), replacing the `config_migrate.os.rename` mocks of
    `test_config_migrate.py:374, 384` for the default path; keep the rename mocks under `keep_backup=True`.


## Part B

## Phase 36 research B: proposal (R6), free-model group (R12 a), pool key, data-use note (HUB-10)

Read-only research. All paths are under `skills/ai-kit-spec-review/ai_kit_spec/` (call it PKG) unless written in full.
Nothing in the repo was changed; scratch probes live in `tmp/p36-plan/` (`b_item_size.py`, `b_modelsdev_keys.py`).
`.aikit/brief/SKILL.md` was not used.

### 1. FACTS (what phase 35 shipped)

Catalog shape (schema 4):
- `model_catalog.py:22` `CATALOG_SCHEMA_VERSION = 4`; `:31-50` `_FIELD_TYPES` (entry keys: `provider, source, confidence,
  last_verified, facts (dict), identity, confirmed_fields, pricing (dict input_per_1m/output_per_1m, :52-53), scores,
  tokens_per_sec, tool_calling, batch_mode, is_router, fallback_quota, name_declared_purpose, ...`).
- Runtime row keys, `:55-58`: `"model_id": str, "ctx_window", "usability": dict, "last_seen": str, "efforts": list,
  "context": dict, "listed_from": list, "ctx_note": str, "match": dict`. Efforts validated as list of str, `:248-251`.
- `:59` `USABILITY_STATES = ("verified", "rejected", "unverified", "listed disabled by host")`. Usability record
  `{state, at, via, error}` (`:221-229`).
- `catalog_bands.py:10-12` verbatim: `TIERS = ("frontier", "strong", "capable", "light", "unknown")`,
  `COST_BANDS = ("low", "medium", "high", "premium", "free_or_local", "unknown")`,
  `CLASSES = ("flagship", "coding", "general", "fast", "small", "router", "unknown")`; `:13-20` the closed strength list
  (`coding, math, hard_prompts, instruction_following, creative_writing, multi_turn`).
- Facts are `{value, label, source, fetched_at[, confidence]}` (`catalog_labels.py:17-25`), read as
  `entry["facts"]["tier"|"class"|"cost_band"|"strengths"]["value"]`. Class rules: `catalog_bands.py:157-171` (flagship =
  tier frontier; coding = strong/capable + coding edge; fast = tps cut; small; router only from `router_alias`, which
  `catalog_tiers.class_fact` always passes as `False`, `catalog_tiers.py:163-165`). A `router-env` alias entry gets class
  `router`, label `assumed`, source `ROUTER_SOURCE = "router-env alias naming"` (`catalog_facts.py:16, 217-221`);
  alias key is `router-env/<bare>` (`router_alias_key`, `:35-40`); a name-declared purpose sits in
  `entry["name_declared_purpose"]` (`:60-62`, `model_heuristics.py:47-62`).
- Match state: `runtimes[rid]["match"]` is a fact whose value is `"judged"` or `"unmatched"` (`catalog_facts.py:139-145`).
  Brand-new unmatched ids are NOT in the catalog at all (`catalog_build.py:658-663` returns them as `unmatched` records).
- Stale is NOT stored. It is computed per row from the runtimes snapshot: `catalog_report.stale_state(model_id, cli_row,
  last_seen, fresh) -> str` (`catalog_report.py:81-93`; `""` = present, `"not checked..."`, `"stale (...)"`) and
  `stale_providers(rid, entries, cli_row, fresh) -> set` (`:96-112`). Only `fresh=True` (a `--detect` run) can say stale
  (`:91-92`). `usability_state(rt_row, cli_row, model_id)` (`:122-137`) returns `"listed disabled by host"` when
  `snapshot.clis[rid].model_records[model_id].enabled is False`, else `verified ...`, `rejected ...`, `unverified`.
- `catalog_cmds.cmd_catalog_report` (`catalog_cmds.py:178-207`) is the model for snapshot input: mutually exclusive
  `--detect` (fresh snapshot, `deps.which_fn/run_fn/popen_fn/urlopen_fn`) or `--runtimes-json` (cached, not fresh).
  `register_parsers(sub)` (`:303-333`) and `COMMANDS` dict (`:336-343`) are the factory pattern; `cli.py:456`
  `catalog_cmds.register_parsers(sub)` and `cli.py:1198` `**catalog_cmds.COMMANDS` wire it. Handlers are `(args, deps)`.
- `CliDeps` (`cli.py:153-171`) is a NamedTuple of seams; `cli.main(argv, **overrides)` does `_replace(**overrides)`
  (`:1210-1213`). Existing jev wiring is opt-in: `--jev` store_true (`cli.py:226-229`) and
  `jev_names.name_judge(env) if args.jev else None` (`:719-720`); there is no jev field in `CliDeps`.
- Ranker: `model_ranker.score_candidates(entries, purpose, weights) -> list` (`:266-296`) reads per entry `e["key"]`,
  `pricing.input_per_1m` (ONLY input, `:219`), `tokens_per_sec`, `scores.*`, `tool_calling`, per-runtime `ctx_window` via
  `_max_context_window` (`:190`, max over `entry["runtimes"]`), `batch_mode`, `fallback_quota`. Axes normalise against
  the call's own entries (`:276-278` docstring); a missing axis scores 49.0 (`:51`). Returns copies sorted by rounded
  `score`, with `score_exact`. `execute` aliases `execution` (`:18-19`); execution weights price 0.25, review 0.15
  (`DEFAULT_WEIGHTS`, `:24-27`). Weights: `load_ranking_weights()` (`:163`), file `references/ranking-weights.toml`.
  Sort is by rounded score only and Python's sort is stable, so equal scores keep input order: the caller must feed rows
  in a fixed order (sorted by key then runtime) for the id tie-break the SPEC asks for.
- Callers today: `skills/ai-kit-spec-config/references/cli-model-selection.md:87-139` (inline `python3 -c`, drops
  runtimes with `row.review_only or not row.runner` at `:106-109`).

Price facts (the answer to the brief's question):
- The catalog holds the zero price ONLY as the band plus an unsourced figure. Band: `catalog_facts.md_facts`
  (`catalog_facts.py:66-91`) writes `facts["cost_band"] = fact(cost_band(price, free, cost_cuts), "judged", "models.dev",
  now, confidence="rule")` where `catalog_bands.price_per_million` (`catalog_bands.py:55-66`) returns `(0.0, True)` only when
  `input` and `output` are both finite numbers, both `>= 0` and both `== 0`; `cost_band(price, True, cuts)` then gives
  `"free_or_local"` (`:100-102`). Source is the string `models.dev`, date is `fetched_at` of that fact. So
  `facts.cost_band.value == "free_or_local"` means exactly "models.dev said input 0 and output 0, on fetched_at". Exact
  values: `fact(...)` keys `value,label,source,fetched_at,confidence`.
- Entry-level `pricing = {"input_per_1m", "output_per_1m"}` copies models.dev `cost.input/output` verbatim when models.dev
  matched (`catalog_build.py:496-498`), else Artificial Analysis pricing (`:499`, `:213-215`). It carries no source and no
  date, so it can show the figure but cannot prove the source. A zero in `pricing` alone is not a sourced zero price.
- The host listing's price is NOT in the catalog. `detection.parse_opencode_api_records` (`detection.py:808-838`) keeps
  `"cost": cost if isinstance(cost, list) else []` and `_opencode_fields` stores the records at
  `snapshot.clis.opencode.model_records[provider/id]` (`:1211-1213`, opencode major >= `OPENCODE_API_MIN_MAJOR` only).
  `catalog_facts` never reads it: `rg` for `"cost"` finds only models.dev readers (`catalog_bands.py:86`,
  `catalog_facts.py:81`, `catalog_build.py:496`). Item shape per 35-RESEARCH.md:113 (live, not re-read): a list whose
  items have keys `cache, input, output, tier`; empty for models with no price.
- Local versus hosted: the catalog does not say. `grep` for local/hosted in PKG finds none; the band name merges both
  (`free_or_local`); models.dev has no such field and no data-use field either: I fetched `https://models.dev/api.json`
  today (probe `b_modelsdev_keys.py`): 324 providers, provider keys `api, doc, env, id, models, name, npm`, model keys
  `attachment, canonical_model_id, cost, description, experimental, family, id, interleaved, knowledge, last_updated,
  limit, modalities, name, open_weights, provider, reasoning, reasoning_options, release_date, status, structured_output,
  temperature, tool_call, type`, no key containing retention, training, privacy, data_use or logging [VERIFIED live].
  opencode's `/api/model` item keys (35-RESEARCH.md:110) hold none either. Consequence: today NO source says local, so every
  zero-price row is `zero price (local or hosted not known)` and every zero-price lane needs the HUB-10 note.
- So for R12 a a plan must read: models.dev zero from `facts.cost_band` (source `models.dev`, date `fetched_at`, figure from
  `pricing`), and the host-listing zero from the runtimes snapshot `model_records[model_id].cost`, with source text from
  `clis[rid].listed_from` `{command, version, at}` (`catalog_report.py:63-78`). CONTEXT D-18 handoff allows this; record
  the difference in the plan summary.

jev contract (real client):
- Item keys `{id,type,instructions,context,criteria}` only; types `choice|noul|score`; a `score` item needs `criteria` =
  list of 2..10 level strings, each passing `_bad_text` (`jev_ladder.py:53-55, 198-222`); no ``` fence, no key shape, no
  48+ base64 run (`:186-195`); fields <= 1500 chars.
- The ladder wrapper DROPS the numeric score: `typed_answer` (`jev_ladder.py:502-541`) maps a score item to
  `choice = levels[int(level)]` (`:530-535`) and returns `{choice, top, fallback, forced, model}`. So via `jev_review.py
  ladder` a "score" is the winning level (an index 0..n-1, never fractional) plus `top` (its probability).
  `fill_columns` (`:544-571`) names the deciding backend in `decided_by`.
- `jev_names.py` (copied client, one of `LOOKUP_COPIES`, `tests/test_arch.py:1688-1698`): `find_jev(env, own_root)`
  (`:50-56`), `ask_items(entry, items, env, run) -> {id: (choice, top, reason)}` (`:127-158`), reasons `""`, `"low"`,
  `"no answer"`, `"timeout"`, `"old"`; `_column_answer` (`:108-124`) accepts `choice in item["criteria"]`, which works for a
  list; low means `needs_fallback`/`forced`/`fallback`. `_batches` splits at `BATCH_CHARS = 7000` (`:32, 93-105`), and
  jev's own TypeSafe guard forces every answer of a request over 8,000 chars (`skills/jev-fast-decision/reference.md:53`).
  `name_judge`/`class_judge` (`:161-198`) are the factory shape: `judge(pairs) -> list`, `None` when jev is absent.
  Row `min_confidence` values are 0.7 and 0.8 (`jev_review.py:1061, 1090`; Laya 0.7 per `backends/laya.md:69`).
- Item size probe (`tmp/p36-plan/b_item_size.py`): a score item with a 150-char purpose instruction, 5 short levels and a
  worst-case facts line is 455 to 461 chars; 12 items = 5,497 to 5,569 chars; 14 = 6,497; 15 = 6,961; 16 splits.

Test patterns to copy:
- Scratch: `tests/test_catalog_cmds.py:41-76` `_Scratch` (temp root, `AI_KIT_REFUSE_REAL_HOME`, `cli.main(argv,
  env_fn=...)`, `_entry(...)`, `_write_catalog`). Fixture catalogs and runtimes rows: `tests/test_catalog_stale.py:15-40`.
- Fake jev: `tests/test_ai_kit_commit_fold.py:76-110` `write_fake_jev(skills_root, table, log_path)` (answers every item
  type as `{"choice": value, "top": 0.9, "fallback": False}`, so a score table value must be a level text) and
  `tests/test_catalog_jev_names.py:28-36, 110-130` (injected `run` returning canned JSON for low/forced/malformed).
- Fixture ids: the guard `tests/test_arch_hardcoded_models.py:48-50` allows only `router-env/...`,
  `placeholder-(model|alias)-N`, `fake[/-]...`; `SLASH` (`:56`) flags other quoted `provider/model` strings. Use
  `fake/placeholder-model-N` keys and provider `fake`.

### 2. CONTRADICTIONS (SPEC / CONTEXT versus live code)

1. R12 a and D-18: "a price of zero from the host's own listing (opencode `/api/model`) ... in the Phase 35 catalog". The
   catalog never reads the host cost; only the snapshot does (`detection.py:831-837`). The D-18 handoff
   ("catalog keeps the raw zero-price fact with source and date beside the band") did not ship; only band plus unsourced
   `pricing`.
2. R6 pool "not stale or unmatched": neither is a catalog field. Stale needs a snapshot and `fresh=True`; unmatched is
   `runtimes[rid].match.value == "unmatched"` for catalogued rows only.
3. R6 "usability not `rejected`": a row can also be `listed disabled by host` (a snapshot fact, `catalog_report.py:123-126`;
   the state is also in `USABILITY_STATES`). It cannot run; the proposal should drop it too.
4. D-07 "one jev request per proposal ... scores each candidate": `ask_items` splits at 7,000 chars and jev forces a whole
   request over 8,000. A whole pool cannot be one request; a window can (section 4.3).
5. D-07 "jev scores": through the ladder a score is a winning level, not a number; the 0.74 versus 0.67 observation is the
   `top` of one answer (it can cross `min_confidence` 0.7), not a score difference.
6. CONTEXT "copied jev ladder client pattern": a second copy would join `LOOKUP_COPIES` and the drift test; add
   `score_item/score_judge` to `jev_names.py` instead (it already is the copy).
7. `cli-model-selection.md:106-109` filters execute candidates by `row.review_only or not row.runner`; SPEC R7 and the
   owner say claude is a normal execute choice and no code may read `review_only`. The new proposal code must not read
   `RUNTIMES[...].review_only` (R7 grep test) and the skill reference text must drop the inline call.
8. R12 "`router-env/<x>` aliases stay in their own group" but R6 says the group is "the purpose guessed by the name
   heuristic": aliases with no declared purpose exist (`infer_purpose_from_name` returns None). Decided in 4.4.
9. HUB-05 amendment (ROADMAP:743): fallback = first lane "neither flagged nor in the same pool". A not-flagged lane has no
   recorded pool, so the reader cannot know it shares one (section 4.6, open question for the writer researcher).
10. SPEC R12 mentions D-20..D-22 nowhere in `36-CONTEXT.md` (they exist only in ROADMAP:743 and REQUIREMENTS:240-243).

### 3. OPEN QUESTIONS answered

- Variance rule: 4.3 (one rule, numbers).
- How the catalog names classes and efforts: classes `catalog_bands.CLASSES`, effort list `runtimes[rid].efforts`
  (list of str, may be absent); levels come as the host spells them (pi/cursor/opencode suffix split in
  `model_names.split_effort`), so show them as stored.
- Does the cost record separate local from hosted: no (section 1). Stays open only as "a future source", not for this phase.
- `probe-quota` on a flagged lane: outside my area (config reader). One fact: a probe spends allowance (SPEC R12 e).
- Pool sharing between `opencode` and `opencode-go` free ids: not documented (research note open question 4). Treat as two
  pools (provider differs) and label the pool key `reported`, not verified.

### 4. DESIGN PROPOSAL

#### 4.1 New modules (cli.py only wires)
`lane_pool.py`, `lane_price.py`, `lane_order.py`, `lane_data_use.py`, `propose_cmds.py`; additions to `jev_names.py`.
No new third-party import; stdlib only.

#### 4.2 Pool and rows (`lane_pool.py`, `Row` NamedTuple)
```
class Row(NamedTuple):            # one per (catalog key, runtime id); the same model on two runtimes is two rows
    key: str; runtime: str; model_id: str; entry: dict; row: dict      # entry/row are the catalog dicts
    tier: str; klass: str; cost_band: str; strengths: tuple; efforts: tuple
    usability: str; provider_prefix: str | None

def build_rows(entries: dict, snapshot: dict, fresh: bool, runtimes: tuple | None) -> list[Row]
    # sorted by (key, runtime); skips "_meta", non-dict, entries/rows of a runtime not in `runtimes` when given.
def drop_reason(row: Row, snapshot: dict, entries: dict, fresh: bool) -> str | None
    # "rejected", "listed disabled by host", "stale", "stale-provider", "unmatched", else None.
    # rejected/disabled: catalog_report.usability_state(...) startswith "rejected" or == "listed disabled by host"
    # stale: catalog_report.stale_state(...).startswith("stale") or stale_providers(...) contains the row's provider
    # unmatched: (row.get("match") or {}).get("value") == "unmatched"
def split_pools(rows, purpose) -> PoolSplit(pool, unknown, wider, aliases)
```
- Classes per purpose: review `("flagship",)`, execute `("coding", "fast")` (constants `POOL_CLASSES`).
- `pool` = kept rows whose class is in the purpose classes; `unknown` = kept rows whose class is `"unknown"` or has no class
  fact (shown below every known row, labelled `class: unknown`). (Tier unknown with a known class cannot reach the pool:
  every pool class needs a measured tier, `catalog_bands.py:131-150`.) `wider` = kept rows with another class except
  `router` and `unknown`, with `class_label` = their class; sorted by the scorer, not scored by jev. Router-env
  aliases (`entry["provider"] == "router-env"`, `ROUTER_PREFIX` from `catalog_facts`) never enter pool, unknown or wider.
- `aliases` rows pass the same drop filters except unmatched (aliases carry no match fact). A row's purpose is
  `entry.get("name_declared_purpose")`; shown for purpose P when it equals P or is absent (then `purpose_note =
  "purpose unknown"`); label string `f"assumed: {catalog_facts.ROUTER_SOURCE}"` = `assumed: router-env alias naming`.
- Never read `RUNTIMES[...].review_only` or `.runner`.
- Decision (one line why): drop `listed disabled by host` too, because the host itself says it cannot be used.

#### 4.3 Order: scorer, jev window, stability rule (`lane_order.py`, `jev_names.py`)
```
SCORE_LEVELS = ("very poor fit", "poor fit", "fair fit", "good fit", "excellent fit")   # jev_names, 5 levels
JEV_WINDOW = 12            # max items per request (12 x ~460 chars = ~5.6k < 7000, one batch)
STABLE_TOP = 0.80          # a level counts only when top >= 0.80 (min_confidence is 0.7/0.8)
NEUTRAL_LEVEL = 2          # unanswered or low rows sort as "fair fit"

# jev_names.py additions (about 45 lines)
def score_item(index: int, purpose: str, summary: str) -> dict   # id f"c{index}", type "score", criteria list(SCORE_LEVELS)
def score_judge(env, own_root=None, run=subprocess.run)          # -> judge(summaries: list[(purpose, text)]) -> list[(level|None, top|None, reason)] or None when jev absent
# lane_order.py
def deterministic_order(rows: list[Row], purpose: str, weights: dict) -> list[tuple[Row, float]]
    # builds score entries {**row.entry, "key": str(i), "runtimes": {row.runtime: row.row}} over rows sorted by (key, runtime),
    # calls model_ranker.score_candidates(entries, purpose, weights), returns [(row, score_exact)] sorted by
    # (-round(score,1), -score_exact, key, runtime)   # ties by id for display only
def facts_summary(row: Row) -> str
    # "Facts: tier T; class C; cost band B; strengths a, b; effort levels x, y." Only values from closed lists
    # (tier/class/band/strengths) plus effort strings through jev_names._clean. NEVER name, id, runtime, path, config, note.
def rank(rows, purpose, weights, judge, zero_ids) -> list[Ranked]   # Ranked(row, score, level|None, ranked_by, reason)
```
Rules (choose, do not re-decide):
1. Score the known pool rows with `deterministic_order` in ONE call (pool plus unknown rows together so the zero group uses
   the same scores); `wider` rows are scored in their own call (their scores are not comparable with the pool's: say so in
   the row's `score_note`).
2. jev window = first 7 known pool rows of the deterministic order, plus the first 5 known zero-price rows, deduplicated,
   at most `JEV_WINDOW = 12` rows; unknown-class rows are never sent (no facts: "confident-looking, meaningless answer",
   `reference.md:52`). One `judge` call, so one request (assert one batch in the test).
3. A row uses jev when `choice` is a level and `top >= STABLE_TOP` and reason is `""`; its sort key is
   `(-level_index, -score_exact, key, runtime)`. Any other windowed row (low, error, timeout, old, none) takes
   `NEUTRAL_LEVEL = 2` and `ranked_by = "scorer"` with `reason` in `{"low", "no answer", "timeout", "old"}` (text:
   `scorer: jev gave a low answer` / `no answer` / `timed out` / `jev too old`). Rows outside the window and unknown rows
   follow all windowed rows (unknown last), in scorer order, `ranked_by = "scorer"`, reason `outside the jev window` /
   `class unknown`. No jev installed: `scorer: no jev`.
4. Row field `ranked_by` is `"jev"` or `"scorer"`; `ranker_reason` is the text above. Rows that jev ranked show its level
   text and `top` rounded to 2.
5. Why this is stable: the order key is a discrete level (5 buckets) with the scorer inside a bucket, so the observed
   `top` wobble (0.74 then 0.67, a 0.07 spread, CONTEXT D-07) cannot reorder anything; it can only flip a row between
   "jev" and "scorer" when `top` crosses a threshold, and `STABLE_TOP = 0.80` sits above the 0.7 `min_confidence` by more
   than that spread, so both observed values fall to the scorer every time. Residual instability: a level can still flip
   near a bucket border (inherent); the whole result is computed once per command and the wizard slices it
   (4.5), so show-more never re-asks jev.
6. Rejected alternative: a per-catalog-version cache of jev answers (a file write, forbidden by the read-only rule, plus
   invalidation work; stored answers would also hide a jev change). The 0.80/5-level numbers rest on one observed pair and
   the two `min_confidence` constants; a repeated live sample (say 5 runs of one real window) was NOT run here
   (no network or jev in research): list it as an optional spike, not a gate.
- Item text: instruction per purpose (one fixed sentence each, about 150 chars; review: "judging a plan or a code diff for
  flaws ... top quality and careful reasoning matter most; cost and speed barely"; execute: "writing code from a plan, many
  times ... coding skill, speed and low cost matter most"), `context` = `facts_summary`, `criteria` = `list(SCORE_LEVELS)`.

#### 4.4 Zero price, locality, pool key (`lane_price.py`)
```
class Price(NamedTuple):
    state: str          # "zero" | "nonzero" | "unknown" | "conflict"
    input: object; output: object            # as stored, no rounding (None when unknown)
    sources: tuple       # ({"source": "models.dev"|"<runtime> listing (<command> <version>)", "date": "<fetched_at or at>"}, ...)
    locality: str        # always "zero price (local or hosted not known)" for state "zero" until a source says (none does today)

def price_of(entry: dict, rid: str, model_id: str, cli_row: dict) -> Price
def pool_key(provider_prefix: str | None, entry_provider: str) -> str      # f"{prefix or entry_provider}:free"
```
- models.dev reading: zero when `entry["facts"]["cost_band"]` is a dict with `value == "free_or_local"` and
  `source == "models.dev"` (date `fetched_at`; figures `pricing.input_per_1m/output_per_1m` shown only when both are `== 0`,
  else shown `0` from the band meaning). Nonzero when the band is `low|medium|high|premium` from models.dev. Else no
  models.dev reading. `pricing` alone is never a source (no provenance, may be Artificial Analysis).
- host reading (only when `cli_row["model_records"][model_id]["cost"]` is a non-empty list): zero when EVERY item has
  `input` and `output` both numbers (not bool, finite) equal to 0; nonzero when any item has a positive number; any
  non-number means that item says unknown. Source text `f"{rid} listing ({listed_from.command} {listed_from.version})"`,
  date `listed_from.at`.
- Combine: any nonzero reading with a zero reading is `conflict` (not in the zero group; shown
  `price conflict: <src> zero, <src> nonzero`); zero only when at least one reading is zero and none nonzero; no reading
  is `unknown` (never zero). Name or id wording is never read (test: an id with `free` wording and `nonzero` price is not
  in the group; a zero-price id without it is).
- `pool_key`: provider prefix of the runtime row's `model_id` when it contains `/` (as `catalog_report.py:158`), else the
  entry's `provider`; tier is the literal `free` (zero price is the only tier this phase can establish). Example shape
  `fake:free`. It is `reported`-grade (shared pool across a provider's free ids is reported by users, not
  confirmed; research note section 2).
- Row JSON `price`: `{"state","input","output","sources":[...],"locality"}`; `pool_key` is set only when `state == "zero"`.
  `data_use_needed = (state == "zero")` (locality is never known today).

#### 4.5 Command (`propose_cmds.py`; cli.py gets two lines and one deps field)
`ai-kit-spec.py propose-lanes --purpose review|execute --catalog-path P (--detect | --runtimes-json P2) [--runtime R]...
[--jev] [--avoid-pool KEY]... [--skip RUNTIME:KEY]...` (read-only; same snapshot flags as `catalog-report`, `fresh = args.detect`).
- Handler `cmd_propose_lanes(args, deps) -> int`; `register_parsers(sub)`; `COMMANDS = {"propose-lanes": cmd_propose_lanes}`.
  cli.py: add `score_judge_fn: Callable[..., Any] = jev_names.score_judge` to `CliDeps` (after `urlopen_fn`),
  `propose_cmds.register_parsers(sub)` after `catalog_cmds.register_parsers(sub)` (`cli.py:456`), `**propose_cmds.COMMANDS`
  after `**catalog_cmds.COMMANDS` (`:1198`). jev is used only with `--jev` and only when `deps.score_judge_fn(env)` is not
  None (absent jev gives `scorer: no jev`). Default off keeps every existing and new cli test off the real client.
- Output (JSON, exit 0), keys in this order:
```
{"purpose": "review", "default_view": 5, "ranking": "jev"|"scorer",      # "jev" when any pool row has ranked_by jev
 "jev": {"asked": 12, "answered": 9, "window": 12, "stable_top": 0.8},   # {"asked": 0,...} without jev
 "pool": [Row...], "zero_price": [Row... at most 5], "aliases": [Row...], "wider": [Row...], "alternative": Row|null,
 "empty": false, "message": ""}
Row = {"rank": 1, "key": "fake/placeholder-model-1", "runtime": "pi", "model_id": "...", "tier": "frontier", "class": "flagship",
       "class_label": "flagship", "cost_band": "premium", "strengths": [...], "efforts": [...], "usability": "unverified",
       "score": 83.1, "ranked_by": "jev", "ranker_reason": "jev: good fit (top 0.91)", "price": {...}, "pool_key": null,
       "data_use_needed": false}
```
  `pool` holds ALL ranked pool rows (known, then unknown); the wizard shows the first `default_view = 5` and slices more in
  its own session: one command run, one jev request, so show-more never reorders. `zero_price` rows are copies of
  pool rows with price state zero, in pool order, `group_rank` 1..5. Alias rows: `{"key","runtime","model_id","label":
  "assumed: router-env alias naming","purpose_note"}` with no score, no jev. `wider` rows carry `class_label` and
  `ranked_by "scorer"`. `--runtime` drops every other runtime from every group (preferred runtimes first question).
- `alternative` (R12 c): the first row of `pool` (final order, known before unknown) whose `pool_key` is not in `--avoid-pool`
  and whose `(runtime, key)` is not in `--skip`; the pool key of a nonzero-price row is `null` so it is never avoided.
  Null when none. Resolves "best-ranked unflagged candidate" to "best-ranked candidate outside the flagged pools".
- Errors: catalog missing, unreadable or without model entries: stderr
  `model catalog is empty: run fetch-model-catalog first (the spec-config catalog step)`, exit 2. No snapshot readable with
  `--runtimes-json`: stderr `runtimes snapshot unreadable: <path>`, exit 2. Empty pool after filters: exit 0,
  `"empty": true`, `"message": "no candidates for this purpose"`, groups still printed (aliases, wider).
- Read-only: no `locked_catalog_update`, no `cache_write_*`, no `usability.record_usability` import (test: catalog bytes
  and mtime unchanged; no file under the scratch HOME created).

#### 4.6 Pool field on lanes (hand-off to the lane-settings researcher)
HUB-05's reader rule needs the pool of every candidate fallback lane, but only flagged lanes would carry it. Proposal:
the wizard writes `free_pool = "<provider>:free"` on EVERY lane it writes whose price state is zero (a price-derived fact,
not the owner's claim; `usage_limited` stays the owner's yes only), and `lane_fallback` skips lanes that are flagged or share
`free_pool` with the flagged lane. A lane with no `free_pool` has no pool. This is the writer researcher's validator
(string, pattern `^[A-Za-z0-9._-]{1,64}:free$`); flagged here because the data comes from `propose-lanes`' `pool_key`.

#### 4.7 Data-use note (`lane_data_use.py`, about 60 lines)
Honest source: neither the catalog nor models.dev nor opencode `/api/model` has a data-use field (verified above), a shipped
list is forbidden, and a stdlib program must not scrape vendor prose. So the program only validates and stores a note that
the CALLING SKILL read from the vendor's page in that run; with nothing passed the value is `unknown`.
```
DATA_USE_VALUES = ("zero_retention", "may_be_kept_or_trained", "unknown")
DATA_USE_LABELS = ("verified", "reported")
def validate_note(note: dict, today: str) -> str | None     # None = ok, else the problem text; used by the lane writer
def unknown_note(today: str) -> dict                        # {"data_use": "unknown", "data_use_source": "none", "data_use_read": today, "data_use_line": "not read"}
```
Flat lane keys (consistent with `usage_limited`; written together with `content_confirmed`):
`data_use` (one of the closed values), `data_use_line` (one line, control chars stripped, <= 200 chars, passed through
`secret_shapes.redact` like `usability.sanitize_error`, display only, never sent to jev), `data_use_source` (an `https://`
URL, <= 300 chars, or the literal `none`), `data_use_read` (`YYYY-MM-DD`, the regex of `model_catalog._LAST_VERIFIED_RE`),
`data_use_label` (`verified|reported`; REQUIRED when `data_use != "unknown"`, ABSENT when unknown), `content_confirmed`
(`YYYY-MM-DD` of the owner's yes). Rules: `unknown` needs source `none` or any URL and no label; `zero_retention` and
`may_be_kept_or_trained` need an https source, a read date and a label; `verified` additionally needs `data_use_read ==
today` (read in this run; the vendor-ownership of the URL cannot be checked by a program, so the label is asserted by the
skill and shown as such: "label set by the calling skill"); a no or a skip writes no lane, so nothing is stored for it.
Never defaulted to a safe value: the missing/invalid/stale note becomes `unknown`, never `zero_retention` (test). Error text:
`data_use: <problem>` e.g. `data_use must be one of: zero_retention, may_be_kept_or_trained, unknown`.
Note: the value list and the unknown-has-no-label rule are my proposal; ROADMAP:744 marks the closed list as needing owner
confirmation (decided by the owner on 2026-11-16 "accept all", `OWNER-DECISIONS-2026-11-16.md:22`, for the note, not the list).

#### 4.8 Existing tests that break or change
- `tests/test_ai_kit_spec.py`/`test_catalog_*` need no change (new modules; `CliDeps` gains a defaulted field, so positional
  uses are unaffected; verify with `rg "CliDeps\("`).
- `tests/test_arch.py` LOOKUP_COPIES: unchanged (no new jev copy). `tests/test_gate_scope.py`: new test modules must appear in
  the generated lists. Run `python3 tools/gen_test_groups.py` (it rewrites `Makefile:12` and `.pre-commit-config.yaml:15,71`).
- `skills/ai-kit-spec-config/references/cli-model-selection.md:87-139`: the inline `python3 -c` and `no_exec` filter are
  replaced by `propose-lanes` (skill-text researcher; guarded by `tests/test_spec_config_catalog_text.py`).

#### 4.9 Unit cut (each unit fits one plan: at most 3 tasks, 5 files, about 300 lines)
- B1 pool: `lane_pool.py` (about 140) + `tests/test_lane_pool.py` (about 150): fixture catalog and snapshot; rejected, disabled,
  stale (fresh and cached), stale-provider, unmatched out; unknown-class last; wider with class label; alias split; runtime
  filter; one model on two runtimes is two rows; no `review_only` read. Depends only on phase 35.
- B2 price and pool key: `lane_price.py` (about 110) + `tests/test_lane_price.py` (about 140): models.dev zero with source
  and date; host-listing zero; both-zero rule (one zero + one positive is nonzero); missing is unknown; conflict; `free`
  wording ignored both ways; `pool_key`; locality label; item with several cost tiers.
- B3 order and jev: `jev_names.py` (+45), `lane_order.py` (about 110), `tests/test_lane_order.py` (about 160): scorer order and
  id tie-break; confident jev (fake client table keyed by level), low (0.75 top), error, timeout, absent, old; window size and
  one batch (`len(payloads) == 1`); item text holds only closed facts (no id, no note, no path); unknown rows not sent; the
  `top` 0.74/0.67 pair stays scorer-ranked; input rows not mutated. Add the score cases to `tests/test_catalog_jev_names.py`
  only if short, else keep them in the new module.
- B4 command: `propose_cmds.py` (about 140) + `cli.py` (+3 lines) + `tests/test_propose_cmds.py` (about 180) + regenerate lists:
  groups, five-row default view field, zero group cap 5 and same scores (jev confident, low, absent), aliases group label, runtime
  filter, empty pool and empty catalog messages, `alternative` with `--avoid-pool`/`--skip`, catalog bytes unchanged, no write.
- B5 data-use: `lane_data_use.py` (about 60) + `tests/test_lane_data_use.py` (about 90); the writer researcher imports
  `validate_note`; stays a separate plan so the wizard unit can depend on it.
Order: B1, B2, B3 independent; B4 needs all three; B5 independent. Total new tests modules: `test_lane_pool`, `test_lane_price`,
`test_lane_order`, `test_propose_cmds`, `test_lane_data_use` (all join the unit group automatically; none needs uv).

### 5. GOTCHAS (cheap-model traps)
- `score_candidates` keys results by `e["key"]` and the sort is by rounded score: use `str(index)` keys over rows sorted by
  `(key, runtime)`, then re-sort with `(-round(score,1), -score_exact, key, runtime)`. Never feed a dict-order pool.
- A row's `runtimes` must be narrowed to the one runtime or `_max_context_window` takes another runtime's window.
- `pricing.input_per_1m` of 0 is a valid best price; `None` is unknown (not 0). Never test `if pricing`/`if cost`.
- `facts.cost_band.value == "free_or_local"` is not a local claim; never print "local" without a source.
- `ask_items` accepts a score answer only when `choice in item["criteria"]`; map back with `criteria.index(choice)` and keep the
  ids `c0..cN` for the index map. `write_fake_jev` returns the table value as `choice`: the table values must be level texts.
- Tests: the fake client must be injected through `CliDeps.score_judge_fn` or a `run` seam; a default `jev_names.find_jev(env)`
  checks the repo's own `skills/` root FIRST (`jev_names.py:45-56`) and would launch the real client. Never pass `--jev` in a
  test without `score_judge_fn`.
- Fixture ids must pass the hardcoding guard: `fake/placeholder-model-N`, provider `fake`, `router-env/placeholder-alias-N` only
  for the alias group; pool key fixtures `fake:free`. Do not write real provider names (including `opencode-go`) in code,
  docs or fixtures.
- Stale only shows with `--detect` (`fresh=True`); with `--runtimes-json` the proposal cannot drop stale rows and should print
  `stale: not checked` on the row's `usability`/note: the wizard must call with `--detect`.
- jev items: `_clean` strips non-printables and caps 80 chars (`jev_names.py:63-64`); efforts come from hosts, so clean them;
  never include `usage_limit_note`, `data_use_line`, keys, ids, runtimes or paths (tests assert the item JSON).
- pylint caps: `cmd_propose_lanes` will be long; split into `_load_inputs`, `_rank_groups`, `_render` (each under 12 branches).
- Scores of `wider` and `pool` are from different calls (relative normalisation): do not compare them or sort them together.
- Do not add grok anywhere; the runtime list in fixtures is `pi`, `opencode`, `codex`, `cursor`, `claude`, `copilot` only.


## Part C

## Phase 36 research C: refusals (R7), effort forms (R4), referee guard rule (R8)

Read-only research, 2026-11-20, branch gsd/phase-36-spec-config-as-the-hub, HEAD 22ba084. The unit brief
`.aikit/brief/SKILL.md` carries `head: 22ba084103c5`, so it is fresh. All paths are under
`skills/ai-kit-spec-review/ai_kit_spec/` unless a full path is given. Grok is not a target: nothing below adds grok.

### 1. FACTS

#### 1.1 Where `review_only` is read (the only three code reads)
- `detection.py:75-84` `class Runtime(NamedTuple)`: fields `binaries, host_signals, scrub_signals=(), list_argv=None,
  native_selectors=(), review_only=False, model_suffix=None, multi_provider=False, runner=True`. Only the claude row sets
  `review_only=True` (`detection.py:122`). Rows: pi, opencode, cursor, codex, claude, copilot, grok (`RUNTIMES`, line 90);
  grok is `runner=False` (line 130). `KNOWN_CLIS = tuple(RUNTIMES)` (line 134).
- `routing.py:137-138` (`_route_shape`): `return "review_only" if mode == "exec" else "custom"` for a custom `command` entry.
- `routing.py:177-178` (`route`): `if mode == "exec" and RUNTIMES[runtime].review_only: return "review_only"`. It sits AFTER
  `host_can_select` (native alias on the host runtime, line 175) and BEFORE `_route_inventory`, so on a Claude Code host an
  alias still routes `native` in exec mode. Keep that order.
- `commands.py:65-67` `SUPPORTED_EXECUTE_CLIS = tuple(sorted(rt for rt, row in RUNTIMES.items() if row.runner and not
  row.review_only))` = `("codex","copilot","cursor","opencode","pi")` (pinned by `test_ai_kit_spec.py:5313-5316`).
- `routing.py:35-37` `SKIP_ROUTES` literally contains `"review_only"`.
- NOT reading the field: `execute_selection.py:103-110` (uses `SUPPORTED_EXECUTE_CLIS` and `commands.execute_cli_error`),
  `execute_dispatch.py:114` (`_refuse_candidate` calls `execute_cli_error`), `cli.py:1071` (`_cmd_dispatch_execute` calls
  `execute_cli_error`, prints `ai-kit-spec: {rejection}`, returns 2). `dispatch_injection.py` (skills/ai-kit-spec-execute-superpowers/
  ai_kit_spec_superpowers/) names `review_only` only in a docstring (lines 108-109); its code imports `SKIP_ROUTES` (line 25)
  and uses it at line 335; the skip line is `skip_note(f"{candidate['key']} for execution", decision)` (line 320).
- `skip_note(subject, decision)` (`routing.py:224-226`) prints `ai-kit-spec: skipping {subject}: route {decision}`; callers:
  `cli.py:817` (review) and `dispatch_injection.py:320` (exec). `unroutable_quota` (188) turns a SKIP route into
  `{"available": False, "reason": decision}`.
- `execute_cli_error(cli)` (`commands.py:70-77`) today: `f"{cli!r} cannot be an execution CLI; supported execute CLIs: {', '.join(SUPPORTED_EXECUTE_CLIS)}"`.
  Other users: `runner_dispatch.py:24,191` (`project_runner_command` returns None for a runtime outside the set; keep that),
  `skills/ai-kit-gsd-curated-config/.../cross_ai_build.py:37,86-90` (`reject_execute_cli`, import with ImportError fallback).
- `screen_execute_clis` (`execute_selection.py:78-112`): custom `command` entry with purpose execute raises
  `ExecuteSelectionError` (lines 91-99, a custom lane fact: "custom entries run only as reviewers"); a table runtime outside
  `SUPPORTED_EXECUTE_CLIS` with purpose `execute` raises, with purpose `both`/unset is dropped with a warning (103-110). The
  superpowers `_screen_exempt` (`dispatch_injection.py:249-254`) exempts everything except an explicit `purpose="execute"`
  that is not native.
- `config_io.py:713` `_RUNNER_RUNTIMES = sorted(rid for rid, row in RUNTIMES.items() if row.runner)` (claude and copilot are
  `runner=True`, so claude already SAVES as a runtime lane; only grok is refused); `config_io.py:721-722` the save error:
  `f"{key}: 'runtime' must be one of {_RUNNER_RUNTIMES}"`. No test pins that text (rg over tests for "must be one of" finds
  only unrelated hits). `config_io.py:104-110` is the legacy-`cli` normaliser: `not row.runner` keeps a command entry or skips
  with "has no runner formula" (a fact, leave).
- Text naming `review_only` (non-test, non-historical): `skills/ai-kit-spec-config/references/cli-model-selection.md:107,149`
  (and prose "review-only" at 146); `skills/ai-kit-spec-review/SKILL.md:219-220,246`;
  `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:180`; `references/cli-profiles/claude.md:14-17`;
  `skills/ai-kit-spec-execute-superpowers/references/escalation.md:21`, `design-notes.md:31,81`, `resolution-stops.md:34`,
  `SKILL.md:277` (prose "review-only"); `AGENTS.md:104` ("native selectors and the review-only flag"); `README.md:34`.
  `docs/superpowers/**` is historical: leave. The review SKILL.md edits (219-220, 246) and the adapter SKILL.md (277) belong
  to the R11 skill-text units (judge loop); references, AGENTS.md and README can go with the code unit.
- Tests that read the strings (must change): `tests/test_ai_kit_spec_routing.py` `TestRouting.test_table` rows at lines 311,
  314, 331 (`"review_only"` expected); `tests/test_ai_kit_spec_runtimes_table.py:81`
  (`assertTrue(RUNTIMES["claude"].review_only)`), `:406-412` (`test_legacy_name_matches_the_runtime_id` asserts
  "cannot be an execution CLI"), `:882-888` (`test_review_only_label` requires the hyphenated word `review-only` in the review
  SKILL.md and `cli-profiles/claude.md`); `tests/test_ai_kit_spec.py:5247-5262` (`TestExecuteCliError`), `:5299-5304`
  (asserts stderr holds "codex, copilot, cursor, opencode, pi" for claude, grok and `Claude`), `:5503` (name only, check
  body); `tests/test_ai_kit_spec_superpowers.py:383-418, 481, 540-544, 1597, 1676, 1721-1735` (route string `review_only`;
  1731-1735 expects rc 2 and "cannot be an execution CLI" for an explicit `purpose="execute"` claude lane).

#### 1.2 The runner (`references/cross-ai.mjs`)
- Per-runtime `exec` entries (`RUNTIMES`, line 1336): cursor 1340 `['-p','--output-format','json','--model',m,...]`; opencode
  1362 `['run','--model',m,...]`; pi 1375 `['-p','--model',m,...piThinkingArgs,...]`; codex 1397 `withCodexKnobs(codexExecArgv(m,c),c)`
  with `codexExecArgv` (1478-1486) = `['exec', gate, '--skip-git-repo-check','-C',cwd,'-m',model,...]`; claude 1423 `exec: null`
  (review at 1424); copilot 1447 `['-p', c.promptArg,'-s','--no-ask-user','--model',m,...]`. There is NO `grok` key.
- `--print-argv` (12629-12639) prints one stdout line `<name>\t<bin or MISSING>\t<JSON argv>`, writes nothing, runs no model.
  PROBED LIVE this session (read-only, repo root cwd, `git status` stayed clean):
  `node cross-ai.mjs --print-argv --mode exec --runtime claude --model fake-ok` exits 2, stderr
  `cross-ai: claude is review-only (no exec formula)` (12596-12599, before the print path);
  `--runtime cursor --model fake-ok --mode exec` exits 0 and prints `cursor\t<path>\t["-p","--output-format","json","--model","fake-ok","--trust",...]`;
  `--runtime codex --mode review --codex-effort max --print-argv` exits 2, stderr `cross-ai: --codex-effort must be minimal|low|medium|high|xhigh`
  (5253 `CODEX_EFFORTS`, 5305-5307). `--runtime grok` is refused by the parser (`unknown cli`, 5319-5326).
- Effort in the runner: `CODEX_EFFORTS = {minimal,low,medium,high,xhigh}` (5253), `PI_THINKING = {off,minimal,low,medium,high,xhigh,max}`
  (5254, used only for baked `CONFIG.effort.pi`, 12594); pi skips `--thinking` when the model carries a `:level` suffix
  (1463-1467); cursor/opencode carry effort only inside the model id (grammars at 1296-1304; `modelSuffix` regexes 1344, 1366, 1382).
  claude and copilot have no effort path (`modelSuffix: null` for copilot, nothing for claude).
- The runner template is a pristine-render input for the dogfood copy: this phase must NOT edit `cross-ai.mjs` (Phase 37 owns it).

#### 1.3 Python effort path today
- `runner_dispatch.py:86-96` `RunnerSpec(runtime, model, mode, timeout_s, cwd=None, effort=None, service_tier=None,
  cursor_mode=None, codex_sandbox=None, route=None)`.
- `runner_dispatch.py:99-107` `review_spec(runtime, model, extra, timeout_s, cwd=None)` copies `extra["effort"]`; callers:
  `reviewer_dispatch.py:71` (dispatch), `quota.py:250` (probe: `_probe_call`), `cli.py:930` (`_display_argv`, used by
  `render-command`). `execute_dispatch.py:98-103` `_runner_spec` builds its own `RunnerSpec(..., effort=candidate.get("effort"))`.
  `cli.py:1028-1033` `_cmd_build_command` builds a third one with model placeholder `"{model}"`.
- `runner_dispatch.py:199-215` `runner_flags(spec)`: the ONLY place an effort becomes a flag, and only for codex
  (`--codex-effort`). For every other runtime `spec.effort` is dropped with no line (`cli.py:372-375` help even says "others
  silently ignore it": conflicts with R4).
- `run_runner` (583-614) checks `model_id_ok(spec.runtime, spec.model)`, builds argv with `build_runner_argv`, and
  `_trailer_counts` (558-565) accepts the runner's `AIKIT-XAI` status line only if `status["model"] in ("-", spec.model)`.
  So a composed model id MUST be in `spec.model` (composition before the `RunnerSpec`, see 4.2), not added inside `runner_flags`.
- `commands.py:80-108`: `build_cursor_agent_model_id(base, effort=, fast=, context=)` and `build_reviewer_model_id(cli, base, ...)`
  (cursor only) exist; `build-model-id` (`cli.py:341-347,1047`) uses them. `model_names.py:33-35,76-130` `split_effort` and the
  regexes `_PI_RX`, `_OPENCODE_RX`, `_BRACKET_RX` (Phase 35 D-04); `routing.strip_model_suffix` (123) strips by `RUNTIMES[rid].model_suffix`.
- First-error-line helper EXISTS: `usability.py:15-24` `sanitize_error(detail)`: first line, `[\x00-\x1f\x7f-\x9f]` removed,
  `secret_shapes.redact(line, "[redacted]")`, strip, cap 200 (`ERROR_MAX`). Reuse; do not write a second one.
  `cli.py:1156-1173` `_cmd_check_reviewer`: `extra = json.loads(args.extra_json)`, `probe_reviewer_quota(resolved, seams=deps.probe_seams())`,
  optional `--catalog-path` records usability (`usability.record_for`), then redacts `detail`/`reason`. Probe result shape
  (`quota.py:215-220`): `{"available": bool, "checked_at", "reason": str|None, "detail": str, "answered": bool}`.
  `check-reviewer` takes `--key --model --vendor --runtime/--cli --command --extra-json --catalog-path` (`cli.py:432-445`), no `--effort`.
- Catalog and snapshot level sources (Phase 35, shipped): catalog row `entries[key]["runtimes"][rid]["efforts"]` is a list of
  strings, validated at `model_catalog.py:248-251`, written at `catalog_facts.py:129-135` as `sorted(set(parts.efforts) | set(levels))`
  where `levels` merge snapshot `reasoning_modes[model_id]` and `model_records[model_id]["efforts"]` (opencode variants ids,
  `detection.py:821-824`; codex `detection.py:417`; pi `detection.py:497`). Find the row with
  `usability.find_runtime_key(entries, runtime, model_id)` (`usability.py:45-57`, returns the catalog key) and the file with
  `model_catalog.cache_catalog_path(env)` + `split_catalog_meta`. Snapshot: `snapshot["clis"][rid]["reasoning_modes"]` is
  `{model_id: [level, ...]}` (`detection.py:611-612`).
- `to_resolved(entry)` (`quota.py:41-51`) puts every non-known lane field into `ResolvedReviewer.extra`, so `effort` reaches
  `review_spec` for probe-quota and dispatch with no extra wiring.
- `config_io.py:749-779` `validate_reviewer_fields(entry)` is the writer-side validator (called per entry at `cfg_render_lanes`
  -> `_cfg_partition_reviewers`, 782-790; `render-toml` is `cli.py:895-920`, env at `deps.env_fn()`). Its return count is at
  the pylint cap of 6 (`_validate_pair_fields` 716-746 is at 6 too): add the effort check without a new `return`, e.g.
  `return lane_effort.effort_problem(entry) or _validate_pair_fields(entry, key)`.

#### 1.4 The guard (Phase 35)
- It is a TEST module, not a library: `tests/test_arch_hardcoded_models.py` (already in `ARCH_MODULES`,
  `tools/run_unittest_parallel.py:92`) + `tests/fixtures/no_hardcoded_models_baseline.json` (schema 2, `{"files":[{"path","cleaned_by","hits":[sorted "kind value"]}]}`,
  1-space indent). `scan_text(path, text) -> [(line, kind, value)]` (155-182) runs `_keyval_hits + _flag_hits + _slash_hits + _seedrow_hits`,
  NFKC-normalises, and drops hits when `MARKER = "model-example:"` is on the hit line or the previous line AND `_marker_exempt` holds
  (doc suffix `.md/.txt`, comment line, docstring, or `example` field; never code). `tracked_files` (185) scans `SCAN_ROOTS =
  ("skills/","tools/","tests/","docs/","README.md","AGENTS.md")`, so `.planning/` and `.aikit/` are never scanned.
  `CLEANED_BY = ("35","36","37","38","39","backlog")` (36 already allowed). `baseline_problems` (229-269) already yields
  "new violation", "fixed, remove from baseline", sorted/duplicate/`cleaned_by` rules. `ALLOWED` (48-50) lets `router-env/...`
  through every existing rule, so a referee rule is a NEW `kind`. Non-vacuity classes: `TestHardcodedModelsNonVacuity` (395+).
- `tests/test_skill_text_history.py:81` `REFEREE_RE = re.compile(r"router-env/|\breferee-[a-z0-9]")` guards SKILL.md main flow only; stays.
- Today's violators of "`router-env/<x>` or `referee-<x>` literal outside tests/, `.planning/`, `.aikit/`" (rg over the scan roots):
  - `skills/ai-kit-spec-config/evals/evals.json:100` (`router-env/my-coding-lite`; the eval tests the alias convention itself)
  - `skills/ai-kit-gsd-curated-config/evals/01-claude-rigorous-cross-ai.md` (lines 5, 14, 41, 51, 52) and `02-opencode-routers-no-catalog.md` (14, 35)
  - `skills/ai-kit-spec-review/references/cross-ai.mjs:2191` (`model: 'router-env/my-coding'`) and `:6831` (self-test) (baseline entry exists, `cleaned_by: "37"`)
  - `skills/ai-kit-spec-goal-prompt/evals/files/opengsd-mixed/project/planning/config.json:9` holds `"referee-one"` (bare, NO `router-env/`)
  - `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:132`, `specs/2026-09-05-router-name-purpose-heuristic-design.md:127,329,331`,
    `plans/2026-09-05-router-name-purpose-heuristic.md` (many), `plans/2026-09-02-ai-kit-model-discovery-config.md` (many)
  - Not violators: `catalog_facts.py:14` `ROUTER_PREFIX = "router-env/"` (no `<x>`), `tools/config_doctor_checks.py:1009,1018` (`"router-env"` without slash),
    `cli-model-selection.md:174-181` (`router-env-plan-review`, `anthropic/router-env`: no `router-env/<x>`). README.md, AGENTS.md, every SKILL.md main flow: none.
  - tests/ holds hundreds of uses (about 50 files); tests cannot be scanned for "pi and opencode only" (see CONTRADICTIONS).
- `baseline` today for the files this phase touches: `skills/ai-kit-spec-review/ai_kit_spec/detection.py` is `cleaned_by: "36"` with
  `seedrow` hits for `claude-fable-5-1, claude-haiku-4-5-20251001, claude-opus-5-5, claude-sonnet-5, fable, haiku, opus, sonnet`
  (the `native_selectors` tuple at line 121 and `CLAUDE_FALLBACK_MODEL_IDS` at 144); the comment at `detection.py:88-89` says "kept in
  the guard baseline for Phase 36". `cross-ai.mjs` is `cleaned_by: "37"`.

### 2. CONTRADICTIONS (spec/context vs shipped code; listed, not decided)
1. SPEC R7/Background lists `execute_selection.py`, `dispatch-execute` and `execute_dispatch.py` as readers of the flag; they read it
   only through `SUPPORTED_EXECUTE_CLIS`/`execute_cli_error`. `dispatch_injection.py` "route list" is a docstring only; the code uses `SKIP_ROUTES`.
2. SPEC R7 acceptance "claude ... accepted by config and selection": config already accepts claude (it is `runner=True`); selection
   (`screen_execute_clis`) does NOT: it raises for purpose `execute` (superpowers test line 1731-1735 pins rc 2). Selection must change.
3. R7 "no runtime-table flag refuses a lane" vs the `runner` flag, which still refuses grok at save (`config_io.py:721`), in `build-command`,
   and via `no_inventory` (`routing.py:156`). SPEC only moves `no_inventory`/`unknown_runtime` to Phase 37 and only rewords the save message.
4. R7 acceptance "grok as a custom command lane" vs the run rule "grok is not a target; add nothing about grok". Pending todo
   `.planning/todos/2026-11-20-grok-is-not-a-cross-ai-target-amend-the-36-37-38-1-specs.md` (named in the brief). Existing grok tests
   (`test_grok_keeps_its_custom_entry_generator`, `build-command --runtime grok`) already cover it.
5. R7 says `dispatch-execute` "no longer exiting 2 on the flag". A table runtime with no exec formula must still be refused before any spawn
   (the runner itself exits 2). Exit code after the change is not stated.
6. R8 baseline list names "the goal-prompt eval config": that file holds `referee-one`, not `router-env/<x>`; the rule only catches it if the
   pattern also matches `referee-<x>` (as `REFEREE_RE` does). SPEC also omits `skills/ai-kit-spec-config/evals/evals.json:100` and the docs plans
   as separate files (four docs files).
7. R8 "this phase cleans every file it rewrites" vs `detection.py` (cleaned_by 36, rewritten here): its baseline hits are the claude
   `native_selectors` and `CLAUDE_FALLBACK_MODEL_IDS`, which R7 keeps working ("aliases still run natively"). The SPEC does not say how to clean them.
8. R8 "in tests a `router-env/<x>` expected value stays allowed for pi and opencode": not checkable by a line scanner; tests/ is exempt wholesale.
   Also a marked example cannot live in a JSON eval (the marker exemption needs a doc file, comment line, docstring or an `example` field).
9. R4 edge row "levels are shown in the host's own order" vs the catalog's `efforts`, stored `sorted(set(...))` (alphabetical: high, low, medium, xhigh).
10. R4 "one function for the argv form" vs three `RunnerSpec` constructors (`review_spec`, `_runner_spec`, `_cmd_build_command`); pi/cursor/opencode
    forms are model-id text, not flags, and the trailer check compares `spec.model`.
11. R4 "check-reviewer ... stored labelled `accepted by a call on <date>`": no storage key is named. The lane has no place for the label today.
12. CONTEXT D-08 "SUPPORTED_EXECUTE_CLIS derived from rows that have a formula" and "execute_cli_error names the formula fact" are consistent,
    but the same function is also the selection gate today; it needs two behaviours (3.2).
13. `cli.py:372-375` `dispatch-execute --effort` help says other runtimes "silently ignore it" (R4 forbids a silent drop).

### 3. OPEN QUESTIONS (CONTEXT, my area) and answers
- "How the Phase 35 catalog names classes and efforts once executed" (D-05): efforts are per (runtime, model) in
  `entries[key]["runtimes"][rid]["efforts"]` (list of str, alphabetical, name-embedded efforts included, so `thinking`, `non-thinking`,
  `reasoning`, `off` can appear: filter them through the runtime's form grammar, 4.3); fallback source `snapshot["clis"][rid]["reasoning_modes"][model_id]`.
  Classes are not my area.
- Where support is unknown: opencode/cursor lists mostly empty today (opencode only from `/api/model` variants); claude/copilot have no path at all.
- Unanswered by code (decide in plan, see 4.4/4.5): the lane key that stores `accepted by a call on <date>`; the exit code of a no-formula
  `dispatch-execute`; whether a `command`-only lane may carry `effort` (its `{effort}` placeholder is a custom-template matter).

### 4. DESIGN PROPOSAL

#### 4.1 R7: exec_formula, advice, `no_formula` (units U1, U2, U3)
Table fields (detection.py), additive first, then `review_only` deleted in U2:
```python
class ExecFormula(NamedTuple):
    head: tuple[str, ...] | None   # leading fixed tokens of the runner's exec entry; None = the runner's exec entry is null
    source: str                    # label, e.g. "cross-ai.mjs RUNTIMES.claude.exec is null (read 2026-11-20)"
class Advice(NamedTuple):
    text: str                      # seed advice shown to the owner, never read by a branch
    source: str                    # e.g. "seed row, unverified"
# Runtime gains: exec_formula: ExecFormula | None = None   (None = the runner has no row at all: grok)
#                advice: Advice | None = None
def has_exec_formula(row: Runtime) -> bool: return row.exec_formula is not None and row.exec_formula.head is not None
def advice_line(runtime: str) -> str | None   # f"{text} [{source}, unverified]" or None
```
Heads (verified at the lines in 1.2; `<prompt>` is the literal `--print-argv` prints for copilot, 12634): cursor `("-p","--output-format","json","--model")`;
opencode `("run","--model")`; pi `("-p","--model")`; codex `("exec","--dangerously-bypass-approvals-and-sandbox","--skip-git-repo-check","-C")`;
copilot `("-p","<prompt>","-s","--no-ask-user","--model")`; claude `ExecFormula(None, ...)`; grok `exec_formula=None`. Claude advice:
`Advice("usually the main agent in this host", "seed row, unverified")`. Why heads and not a bool: a bool cannot drift; a head catches a changed flag.

Routing (routing.py): `SKIP_ROUTES` swaps `"review_only"` for `"no_formula"`. `_route_shape`: `return "no_formula" if mode == "exec" else "custom"`
(a custom lane runs in review only: fact, the launcher is review-only). `route`: `if mode == "exec" and not has_exec_formula(RUNTIMES[runtime]): return "no_formula"`
(same position as today). Side effect to test: grok in exec mode now routes `no_formula` (was `no_inventory`); review mode unchanged.
Detail text for the skip line (names mode and runtime): add
```python
def no_formula_detail(runtime: str | None, mode: str) -> str  # exec/claude: "the runner has no exec formula for claude (<source>)"; custom: "a custom command lane runs in review mode only"
def skip_note(subject: str, decision: str, detail: str = "") -> str  # appends f": {detail}" when detail
```
callers `cli.py:817` and `dispatch_injection.py:320` pass `detail` only when `decision == "no_formula"`. Docstring at `dispatch_injection.py:108` becomes `no_formula`.

commands.py: `SUPPORTED_EXECUTE_CLIS = tuple(sorted(rid for rid, row in RUNTIMES.items() if has_exec_formula(row)))` (same value, pinned by the existing test).
```python
def execute_cli_error(cli) -> str | None   # None if the runtime has an exec formula, else:
#  in table, no formula: f"{cli!r} has no exec formula in the runner (route no_formula): {source}"
#  not in table:         f"{cli!r} is not a runtime in the table; store it as a custom `command` lane (custom lanes run in review mode only)"
```
`dispatch-execute` keeps exit 2 (a pre-spawn refusal fact, same as the runner's own exit 2): the message names the formula, not the flag. Why: R7
acceptance only bans the flag as the reason. `execute_dispatch._refuse_candidate` and `cli.py` need no code change (message flows through).
`screen_execute_clis` (execute_selection.py:103-110) changes its condition to `runtime_id(cli) not in RUNTIMES` (out of table only), so a table runtime
without a formula passes the screen and the route walk records `no_formula` (explicit-execute claude lane: accepted by config and selection, skipped
with the reason). Update its docstring (it names "claude, grok"). Config save message (config_io.py:721-722), same predicate, two texts:
`f"{key}: runtime {runtime!r} has no runner formula; store a custom `command` lane instead (no 'runtime')"` for a row with `runner=False`, and
`f"{key}: runtime {runtime!r} is not in the runtime table; store a custom `command` lane instead (no 'runtime')"` otherwise (non-string included).
`_RUNNER_RUNTIMES` stays (a mirror, Phase 37 removes it).

Drift test, new `tests/test_ai_kit_spec_exec_formula_e2e.py` (e2e group: real `node`, so NOT a unit test; add to `E2E_MODULES` and a recorded
second count to `E2E_RECORDED_SECS` in `tools/run_unittest_parallel.py`, then `python3 tools/gen_test_groups.py`): for every `rid in RUNTIMES` run
`[node, TEMPLATE, "--print-argv", "--mode", "exec", "--runtime", rid, "--model", m]` with `m = "fake/ok"` for pi and opencode and `"fake-ok"` for the rest,
cwd a temp dir, env `runner_env(tmp)` (`tests/cross_ai_selftest.py`, as `test_cross_ai_runner_e2e.py:539-547`). Assert: `head is not None` implies rc 0 and
the JSON argv (third tab field of the stdout line) starts with `head`; `ExecFormula(None, _)` implies rc 2 and stderr contains `no exec formula`;
`exec_formula is None` (grok) implies rc 2 and stderr contains `unknown cli`. Also assert the codex closed set: each `RUNNER_CODEX_EFFORTS` level with
`--codex-effort` is rc 0 and one outside (`max`) is rc 2 with `minimal|low|medium|high|xhigh` (probed live). Skip with a named reason when `_real_node_executable()` is None.
Mirror drift for pi levels is not asserted (the runner only exposes it through a regex).

Grep-style no-refusal test, new unit `tests/test_no_seed_refusal.py`: AST-walk every `skills/**/*.py` (not tests): fail on any `Attribute.attr == "review_only"`, any
`Constant == "review_only"`, and scan `skills/**/*.md` and `AGENTS.md` for the token `review_only`; also assert `no_formula in routing.SKIP_ROUTES`,
`"review_only" not in SKIP_ROUTES`, `not hasattr(Runtime(("x",), ()), "review_only")`. (Docs keep the hyphenated word `review-only`, which `test_review_only_label` needs.)

Test edits (U2/U3): routing.py rows 311/314/331 -> `no_formula` (add: claude exec on a non-Claude host, custom exec, claude native alias on claude host stays `native`);
runtimes_table 81 -> assert claude `exec_formula.head is None` and `advice`; 406-412 -> new message ("has no exec formula"); `test_ai_kit_spec.py` 5247-5262 and 5299-5304
-> new texts (claude: "no exec formula"; `Claude`/`grok`/`nonexistent-cli`: "is not a runtime in the table" for the unknown, grok is in the table: "has no exec formula"
because its `exec_formula` is None); superpowers fake route strings -> `no_formula`; 1731-1735 explicit execute claude: rc becomes whatever the walk gives (executor runs it;
expect `reasons == {"c-full": "no_formula"}` and no "cannot be an execution CLI").

#### 4.2 R4: one argv-form function (units U4, U5)
New module `lane_effort.py` (stdlib; imports `detection.RUNTIMES`, `re`):
```python
RUNNER_CODEX_EFFORTS = ("minimal","low","medium","high","xhigh")            # mirror cross-ai.mjs:5253 (drift-tested)
RUNNER_PI_LEVELS = ("off","minimal","low","medium","high","xhigh","max")    # mirror cross-ai.mjs:5254 and RUNTIMES["pi"].model_suffix
LEVEL_RX = re.compile(r"[a-z][a-z0-9_-]{0,15}")                              # same token shape Phase 37 D-07 plans
class EffortForm(NamedTuple):
    model: str                  # the --model value (carries :level / [effort=..] / #variant for pi, cursor, opencode)
    flags: tuple[str, ...]      # codex only: ("--codex-effort", level)
    ignored: str | None         # the exact "ignored: <reason>" line, or None
def effort_form(runtime: str, model: str, effort: str | None) -> EffortForm
def has_effort_path(runtime: str) -> bool        # codex, pi, cursor, opencode only; claude, copilot (and anything else) False
def effort_problem(entry: dict) -> str | None    # pure write-time check (shape, closed sets); used by validate_reviewer_fields
```
`effort_form` rules (decided; one line why each): no/`None` effort -> `EffortForm(model, (), None)` (nothing passed, nothing printed). codex: level in
`RUNNER_CODEX_EFFORTS` -> flags, else ignored `ignored: codex effort '<x>' is outside the runner's closed set minimal|low|medium|high|xhigh`.
pi: level in `RUNNER_PI_LEVELS` -> `model + ":" + level`; else ignored `ignored: pi takes a thinking level from off|minimal|low|medium|high|xhigh|max, not '<x>'`.
opencode: `model + "#" + level` (grammar `[A-Za-z0-9._-]+`; the runner regex at 1304). cursor: merge into the model's own bracket (`m[context=1m]` -> `m[context=1m,effort=high]`;
none -> `m[effort=high]`; reuse `commands.build_cursor_agent_model_id` only when no bracket exists; a bare second bracket is invalid). If the stored id already carries
an effort suffix: same level -> unchanged, no line; different level -> the id wins (the runner does the same for pi) with
`ignored: the model id already carries effort '<y>'; lane effort '<x>' not applied`. claude, copilot, any other runtime:
`ignored: the runner has no effort flag for <runtime>` (exact SPEC text). A `command`-only lane (no runtime) is not routed here.
Why one function: all three entry points pass through it before a `RunnerSpec` exists, so `spec.model` already holds the composed id and `_trailer_counts` /
`model_id_ok` (which already accepts the pi, cursor and opencode suffix grammars, `runner_dispatch.py:50-63`) keep working.

Wiring (U5): `RunnerSpec` gains a last field `ignored: str | None = None`; `review_spec` and `execute_dispatch._runner_spec` and `_cmd_build_command` call
`effort_form(runtime, model, effort)` and build `RunnerSpec(runtime, form.model, ..., effort=<level only when form.flags>, ignored=form.ignored)` (so `runner_flags` keeps its
codex branch untouched and `spec.effort` is None for the others). `run_runner` prints `spec.ignored` first (before the node check) through `active.print_fn`; this covers
`dispatch-reviewer`, `dispatch-execute`, the `probe-quota` / `check-reviewer` probe (lines land in the probe `detail`). `build-command` and `render-command` print it to
stderr (`cli.py` `_cmd_build_command` after the argv, and `_cmd_render_command` via a small `review_spec`-returning helper). `render-command` also prints `advice_line(runtime)` when
set (preview, per R7). Fix the `--effort` help at `cli.py:372-375`. Tests: extend `tests/test_ai_kit_spec_runner_dispatch.py` (existing codex effort tests at ~191-195 and ~910-919
stay green) and `tests/test_ai_kit_spec.py` build-command tests; new matrix test "no path drops a set effort without a line" over runtimes x {build-command, render-command,
dispatch-reviewer, dispatch-execute, probe} with a fake runner: each either carries the level in argv or prints an `ignored:` line.

#### 4.3 R4: offered levels and write-time refusal (unit U4)
```python
class LevelOffer(NamedTuple):
    levels: tuple[str, ...]                 # what the wizard may offer, in display order
    source: str | None                      # "catalog" | "runtimes snapshot" | None (unknown)
    refused: tuple[tuple[str, str], ...]    # (level, reason) the runner or model rejects, named to the owner
def offered_levels(runtime: str, model: str, catalog: dict, snapshot: dict) -> LevelOffer
def write_problems(lanes: list[dict], catalog: dict, snapshot: dict) -> list[str]
```
`offered_levels`: no effort path (`not has_effort_path`) -> `LevelOffer((), None, ())` (the wizard asks nothing and says in one line why). Else bare id =
`routing.strip_model_suffix(runtime, model)`; catalog row via `usability.find_runtime_key(entries, runtime, bare)` -> `entries[key]["runtimes"][runtime]["efforts"]`; if empty or no row, the snapshot
`clis[runtime]["reasoning_modes"][bare]`; else source None. Then drop what the runner form rejects (codex outside the closed set, pi outside the seven levels, cursor/opencode failing the charset or
not matching `LEVEL_RX`) into `refused` with reason text (`codex lists '<x>' but the runner's closed set is minimal|low|medium|high|xhigh`). Order: snapshot order when the snapshot has the same set;
else the canonical order `none, minimal, low, medium, high, xhigh, max`, unknown tokens after, first-seen (the catalog stores alphabetical, contradiction 9; display only).
`write_problems` (called from `_cmd_render_toml` right after `json.load`, before rendering, reading catalog via `cache_read_json(cache_catalog_path(env))` and snapshot via `cache_read_json(cache_runtimes_path(env))`;
on any problem print `render-toml: <msg>` to stderr and return 1 with nothing written, the existing refusal pattern at `cli.py:903-904`): for each lane with `effort`, unknown list -> no problem
(unknown is learned by probe, never refused); known list and level not in it -> `f"{key}: effort '{x}' is not in the model's list ({', '.join(levels)}) [{source}]"`; level the runner rejects ->
`f"{key}: effort '{x}' cannot be passed: {reason}"`. `effort_problem(entry)` (pure, in `validate_reviewer_fields`) covers the empty string (`f"{key}: 'effort' must be a non-empty string"`), shape
(`f"{key}: 'effort' must match [a-z][a-z0-9_-]{{0,15}}"`), a closed-set runtime (codex/pi), and a `command`-only lane (`f"{key}: 'effort' needs a table runtime"`). A lane for claude/copilot
with `effort` is NOT refused at write (hand-written is allowed; it prints `ignored` at run time).
Tests: new `tests/test_lane_effort.py` (pure; fixture catalog and snapshot dicts with invented ids `placeholder-model-1`, `fake/ok`; `router-env/<x>` only if an alias is needed): forms per runtime incl. suffix merge,
first and last level accepted, one outside refused, `high` is not `xhigh`, codex `max` not offered and named, unknown source, claude/copilot empty offer, ordering.

#### 4.4 R4: learning unknown support by one probe (unit U6)
New module `effort_probe.py`:
```python
def probe_effort(resolved: ResolvedReviewer, effort: str, today: str, seams: ProbeSeams | None = None) -> dict
# -> {"state": "accepted"|"rejected"|"ignored"|"inconclusive", "level": effort, "label": str|None, "error": str|None, "reason": str|None}
```
Logic: `form = effort_form(runtime, model, effort)`; `form.ignored` -> `{"state":"ignored","reason":form.ignored}` with NO call. Else run
`probe_reviewer_quota(resolved._replace(extra={**resolved.extra, "effort": effort}), seams)`: available with `answered is True` and no reason -> `accepted`, `label = f"accepted by a call on {today}"`;
`available` but no answer -> `inconclusive`; not available with reason in (`real_error`, `configuration`) -> `rejected`, `error = usability.sanitize_error(result.get("detail") or result.get("reason"))`
(first line, control characters removed, key shapes redacted: existing helper); reason `quota`/`auth`/`timeout`/`dispatch_unavailable` -> `inconclusive` (a quota stop is not a rejected effort; Phase 38.1 adopts
the closed list later). Stores nothing itself. cli.py wiring (~12 lines): `check-reviewer --effort <level>` adds `result["effort_probe"] = probe_effort(...)` using `now_iso()[:10]`; `--effort` with `--catalog-path`
exits 2 with `check-reviewer: --effort cannot be combined with --catalog-path` (a rejected effort says nothing about the model's usability and must never write a `rejected` record). The wizard writes `effort` on the lane and,
when accepted by a call, `effort_source = "accepted by a call on <date>"` (flat string, one line, display only, never parsed; decided here because SPEC names no key; the validator accepts it only as a non-empty
single-line string, written only after a call, absent otherwise). Ask the planner to confirm the key name with R3/R5/R12 owners so the lane validator gets all new flat keys in one edit.
Tests: new `tests/test_effort_probe.py` with fake `ProbeSeams.runner_fn` (no host, no network): accepted, rejected (first line only, a planted key shape redacted, a control character removed), no-answer, quota -> inconclusive,
claude -> ignored with the exact line and zero runner calls, `--effort` + `--catalog-path` exit 2, a lane with no effort calls nothing.

#### 4.5 R8: referee rule in the same guard (unit U7)
Edit `tests/test_arch_hardcoded_models.py` only (plus its baseline). Add
```python
REFEREE_RX = re.compile(r"router-env/[A-Za-z0-9][\w.:#-]*|(?<![\w-])referee-[a-z0-9][\w-]*")
def _referee_hits(path: str, line: str) -> list[tuple[str, str]]:   # [] when path.startswith("tests/")
    return [("referee", m) for m in REFEREE_RX.findall(line)]
```
and add it to `hits = ...` in `scan_text` so the existing marker rule (`model-example:` same or previous line plus `_marker_exempt`), the baseline Counter logic, `CLEANED_BY` and sorting all apply unchanged. `tests/` is exempt wholesale
(decision: "pi and opencode only" cannot be scanned; the rule text in the test docstring says so). Prefix constants (`"router-env/"`) never match (needs one character after the slash). Planted fixtures in
`TestHardcodedModelsNonVacuity`-style new class `TestRefereeRuleNonVacuity`: (1) `skills/a.py` `DEFAULT_ALIAS = "router-env/x"` -> one `referee` hit; (2) `skills/s/SKILL.md` `Use router-env/x here.` -> hit;
(3) `skills/s/SKILL.md` `<!-- model-example: router-env/x -->\nrouter-env/x` -> no hit; and the third line `router-env/y` after two lines -> hit (marker covers its own region only); (4) `tests/test_x.py` `model = "router-env/x"` -> no hit;
(5) `baseline_problems({"skills/new.md": [(1,"referee","router-env/x")]}, {"schema":2,"files":[]}, {"skills/new.md"})` -> "new violation"; (6) baseline lists `referee router-env/x` for a path whose scan now finds nothing -> "fixed, remove from baseline";
(7) `skills/c.json` `"referee-one"` -> hit. Real baseline additions (generate, never hand-write: a one-off script under `tmp/` that imports the module, runs `scan_tree(REPO, tracked_files(REPO))`, and prints entries whose hits include `referee`; keep the file's
1-space JSON format and sort order): `skills/ai-kit-spec-config/evals/evals.json` -> `cleaned_by "36"`; `skills/ai-kit-spec-review/references/cross-ai.mjs` (existing entry, add 2 hits, stays `"37"`);
the two curated-config eval md files, the goal-prompt eval config JSON and the four `docs/superpowers/**` files -> `"backlog"` (no phase in 36-40 rewrites them; planner may pick another phase only if its plan rewrites them).
Cleaning rules for files this phase rewrites: the spec-config evals are rewritten in R11, so that unit rewrites line 100 with a marker (JSON cannot carry a comment: use a sibling `"example"` field plus a `"note": "model-example: ..."` line before it, or
a `placeholder-alias-1` stand-in if the eval does not need the prefix; the eval at line 99-106 exists to test the alias convention, so prefer the marked field) AND removes its baseline entry in the SAME commit (the test fails on "fixed, remove from baseline"
otherwise). `detection.py` (cleaned_by 36): decision needed (open question 1); recommended: leave the entry (its hits are the claude native-selector seed list that R7 keeps) and record it as the one deliberate carry-over in 36-VERIFICATION, re-targeting `cleaned_by`
to "37" only if the planner confirms. `tests/test_skill_text_history.py` unchanged.

#### 4.6 Unit cut (order matters: each unit leaves the tree buildable and green)
- U1 exec_formula + advice (additive; `review_only` still present) + e2e drift test + gate lists. Files: `detection.py`, `tests/test_ai_kit_spec_runtimes_table.py`, new `tests/test_ai_kit_spec_exec_formula_e2e.py`, `tools/run_unittest_parallel.py`, regenerated `Makefile`/`.pre-commit-config.yaml`. About 150 lines.
- U2 route `no_formula`: `routing.py` (SKIP_ROUTES, `_route_shape`, `route`, `skip_note` detail), `detection.py` (delete `review_only`), `commands.py` (SUPPORTED, `execute_cli_error`), `dispatch_injection.py` (docstring, detail arg), `cli.py:817` (detail arg),
  and the mechanical test rewrites (routing, runtimes_table, test_ai_kit_spec, superpowers). About 220 lines, 4 source and 4 test files (string edits; they cannot split off because the superpowers tests inject the `review_only` string).
- U3 selection and refusal facts: `execute_selection.py` (screen), `config_io.py` (save message), `cli.py` (dispatch-execute help text only), reference docs and `AGENTS.md:104`, `README.md:34`; new `tests/test_no_seed_refusal.py`; superpowers 1731-1735. About 170 lines. Review SKILL.md 219-220/246 and adapter SKILL.md 277 go to the R11 skill units.
- U4 `lane_effort.py` (`effort_form`, `has_effort_path`, `effort_problem`, `offered_levels`, `write_problems`) + `tests/test_lane_effort.py` + the one `config_io.py` line. About 260 lines.
- U5 wire the form: `runner_dispatch.py` (`RunnerSpec.ignored`, `review_spec`, `run_runner` print), `execute_dispatch.py` (`_runner_spec`), `cli.py` (`build-command`, `render-command`, help text, advice line), tests in `test_ai_kit_spec_runner_dispatch.py` and `test_ai_kit_spec.py`. About 170 lines.
- U6 `effort_probe.py` + `check-reviewer --effort` + `render-toml` `write_problems` wiring + `tests/test_effort_probe.py`. About 230 lines. Needs U4.
- U7 guard rule + baseline + planted fixtures (+ removal of any baseline entry a cleaned file owns). About 200 lines. Goes last so the baseline lists the real violators at that moment; the R11 evals rewrite removes its own entry.

### 5. GOTCHAS for a cheap coding model
- Do not edit `skills/ai-kit-spec-review/references/cross-ai.mjs`: the dogfood runner copy must stay a pristine render (`make check-dogfood`) and Phase 37 owns it. Only READ it (the drift test spawns node on it).
- Compose the effort into `spec.model` BEFORE building `RunnerSpec`. Adding the suffix inside `runner_flags` breaks `_trailer_counts` (status model vs `spec.model`) and the status line is silently ignored.
- A rejected effort probe must never write a usability record: `--effort` and `--catalog-path` are exclusive. Treat only `real_error`/`configuration` as a rejection; quota/auth/timeout are inconclusive.
- `config_io.py` return caps: `validate_reviewer_fields` and `_validate_pair_fields` are at 6 returns; chain with `or`, add no `return`. `cli.py`: only wire; logic lives in `lane_effort.py`, `effort_probe.py`.
- The drift test is an e2e module (real node): a new e2e module must be added to `E2E_MODULES` AND `E2E_RECORDED_SECS` in `tools/run_unittest_parallel.py`, then `python3 tools/gen_test_groups.py`; `tests/test_gate_scope.py` fails otherwise. Unit modules join automatically (`tests/test_lane_effort.py`, `tests/test_effort_probe.py`, `tests/test_no_seed_refusal.py`; still regenerate the lists).
- Keep the hyphenated word `review-only` in `skills/ai-kit-spec-review/SKILL.md` and `references/cli-profiles/claude.md` (`test_review_only_label`), or change that test with them; never write the token `review_only` anywhere under `skills/` once U3 lands (the grep test fails).
- Hardcoding rule: no host model names in new tests or fixtures; use `placeholder-model-<n>`, `fake/<token>`, `fake-<token>`; `router-env/<x>` only where the alias group itself is under test (tests/ is exempt from the referee rule). The new test files themselves are scanned by the 35 guard (tests/ is a scan root).
- Baseline JSON: hits sorted, paths sorted, no duplicates, `cleaned_by` in `CLEANED_BY`; a file that stops violating must lose its entry in the same commit ("fixed, remove from baseline"); `referee` hits sort before `seedrow` and `slash`.
- Marker exemption only works in `.md/.txt`, comment lines, docstrings, or an `example` field: a JSON string cannot be exempted any other way.
- `skip_note` text is pinned by tests as `...: route <decision>`; keep that prefix and append detail after it so existing substring asserts survive.
- `unroutable_quota` converts a skip route into `{"available": False, "reason": "no_formula"}`; the superpowers resume code treats route names as permanent reasons (never `quota`): `no_formula` must stay permanent.
- `execute_cli_error` is imported by `ai_kit_gsd_curated_config/cross_ai_build.py` with an ImportError fallback; keep the name and `str | None` return.
- `project_runner_command` must keep returning None for claude (it checks `SUPPORTED_EXECUTE_CLIS`); with the derived set this holds.
- A custom `command` lane receives `effort` through `extra` as a `{effort}` placeholder source (`render_reviewer_command`); do not route custom lanes through `effort_form`.
- Grok: do not add to forms, heads, fixtures or probes; its row only gets `exec_formula=None` (it has no runner key) and stays untouched otherwise.


## Part D

## Research D: skill text, docs, evals, doc-contract tests, judge loop (phase 36)

Read-only research, 2026-11-20, branch `gsd/phase-36-spec-config-as-the-hub`. Cites are `path:line` as read this session.
Grok is not a target: nothing below adds or extends grok text.

### 1. FACTS

#### 1.1 The three SKILL.md files and what each does today
- `skills/ai-kit-spec-config/SKILL.md` (485 lines; **a test caps it at 500**: `tests/test_ai_kit_spec_check_providers.py:347`
  `assertLessEqual(len(text.splitlines()), 500)`). Headings: Step 0 (locate TOOLS_PY, l.25), NEVER (l.61), Step 1 detect (l.84),
  Step 1.5 catalog (l.123, points at `references/catalog.md`), Step 2 ask (l.129, table of 2.1..2.8), 2.1 write target (l.152),
  2.2 pick CLIs (l.162, mixed-purpose, loads `references/cli-model-selection.md`), 2.3 vendor, 2.4 pair knobs (codex bare id, cursor
  `build-model-id`, grok custom), 2.5 test the pair (l.258), 2.6 strength + "`purpose` comes from Step 2.2" (l.287), 2.7 session default
  + purpose question (l.300), 2.8 `policy.mode`, one `policy.ladder`, strategy, timeout tiers (l.345), Step 3 write via `render-toml`
  (l.371), Step 4 report (l.414), `## Evidence` (l.481). `--check-only` lives in `references/check-only.md` (89 lines).
- `skills/ai-kit-spec-review/SKILL.md` (496 lines, no length test). Step 0.7 (l.149) is a pointer: "MANDATORY read
  `references/cross-ai-dispatch.md`"; the real procedure is points 0 to 6 in that file. `--no-cross-ai` skips points 3-6 only
  (SKILL.md l.153; dispatch.md l.110-122). Point 3 (dispatch.md l.123-145) is the old hint: it prints
  `No cross-AI config saved yet - run ai-kit-spec-config ...` only when the runtimes snapshot file is missing, then continues.
  Resume entry (SKILL.md l.234) skips Steps 0-0.7, so a chain ask never repeats on a resume. Constants l.219-221: "`claude` is
  review-only ... Routing skips an exec-mode `claude` candidate". Step 1 l.245-248 lists skip routes incl. `review_only`.
  `## Evidence` (l.494) holds a date: history is allowed only in that trailing section.
- `skills/ai-kit-spec-execute-superpowers/SKILL.md` (300 lines). Step 0 resolves SHIM/TOOLS_PY (l.47-78), Step 1 loads the plan
  under subagent-driven-development (l.97), start-step block (`references/start-step.md`), Task paths block (l.111) computes
  `PROJECT_KEY`, `SCALARS`, `RESUME_STATE_PATH` from `CWD` + `PLAN_FILE`; CWD and PLAN_FILE are only known after
  subagent-driven-development's Setup (l.99-101). No `--no-cross-ai` flag exists in the adapter (rg: only the cross-ai caller link,
  l.33 and l.41). l.277: "`claude` is review-only and never runs here".
- `skills/ai-kit-spec-execute/SKILL.md`: rg for `lane|config|ladder|resolve-injection|reviewer` finds nothing. CONFIRMED: the
  router needs no change (R2, D-03).
- `config-status`, `propose-lanes`, `--keep-backup`, `lane_escalation`, `usage_limited`, `no_formula` appear in no file under
  `skills/`, `tools/`, `tests/` yet (rg -l, empty). Skill text can only name commands that exist when its plan runs.

#### 1.2 Every place still naming `review_only` / "review-only" in skill text, references or docs (rg, outside `.planning/`, `tmp/`)
- `README.md:34` ("`claude` is review-only")
- `AGENTS.md:104` ("...native selectors and the review-only flag")
- `skills/ai-kit-spec-review/SKILL.md:219-221` (Constants) and `:246` (skip list `review_only`)
- `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:180` (`... or review_only`)
- `skills/ai-kit-spec-review/references/cli-profiles/claude.md:14` ("The runtime table sets `review_only`, routing skips ...")
- `skills/ai-kit-spec-execute-superpowers/SKILL.md:277`; `references/resolution-stops.md:34`; `references/escalation.md:21`;
  `references/design-notes.md:31` and `:81`
- `skills/ai-kit-spec-config/SKILL.md:340` ("That review-only default exists for legacy entries" = the `purpose` default, a different
  meaning: keep); `references/cli-model-selection.md:106-107` (Python snippet **reads `row.review_only`**), `:146-149`
- Not mine, same word in code or the runner (other researchers): `cross-ai.mjs` l.5318, 9747-9757, 12075-12085, 12597 (Phase 37 owns
  the runner); `tests/fixtures/cross_ai_selftest_secs.json:439-440` (self-test case names).

#### 1.3 Tests that pin skill text (a plan that edits the text must edit these in the same plan)
- `tests/test_spec_config_catalog_text.py` (the phase-35 doc-contract pattern, 86 lines): reads `SKILL.md` + `references/catalog.md`;
  `test_step_order` needs `### Step 1 —` < `### Step 1.5 — Catalog` < `### Step 2 —` and `references/catalog.md` between 1.5 and 2;
  `test_step_2_5_records_usability` needs `#### Step 2.5` ... `#### Step 2.6` headings and `--catalog-path` inside;
  `RUN_LINE` regex `^- Run: `...`$` lines are parsed with `cli._build_parser().parse_args` against an `ALLOWED` tuple (l.18-22);
  non-vacuity case `catalog-report --json`. Pattern to copy: a text file + a regex over one-line `- Run:` commands + a parser check.
- `tests/test_ai_kit_spec_check_providers.py` `TestSpecConfigStep` (l.337-421): `check-providers --cwd` in SKILL.md and check-only.md,
  link `(references/check-only.md)`, **<= 500 lines**, `auth.json` only inside `## NEVER`; **exactly 12 eval ids** (l.356-375,
  `test_skill_evals_have_the_twelve_cases`); write-risk ask (`read_only: unconfirmed`) before `check-reviewer --key` inside Step 2.5;
  `precise-global-write` eval prompt/assertion text (l.402-412); `"under `[[lanes.review]]` only (`split_by_purpose`)"` must stay in
  SKILL.md and `"matches both review and execute"` must not (l.414-421).
- `tests/test_ai_kit_spec_runtimes_table.py`: `PAIR_RULE_PARAGRAPH` (l.784-791) verbatim in review and spec-config SKILL.md
  (`test_pair_rule_paragraph`, l.869); `test_review_only_label` (l.882-888) **requires the string `review-only` in review SKILL.md and
  `cli-profiles/claude.md`: it breaks when R7 rewrites that text**; `test_forbidden_tokens` scans SKILL.md + references for
  `native`+`_runtime`, `native`+`_claude`, `cursor-agent.md`, `cli` is null forms (l.781-840); `test_exec_confinement_statement`
  tokens in the adapter SKILL.md (`--codex-sandbox`, `/tmp`, `$TMPDIR`, `full permissions`, `self-test`,
  `live verification is still open`); `test_node_floor` in review SKILL.md.
- `tests/test_cross_ai_skill_text.py:224-231`: spec-config SKILL.md has **exactly one line containing `ai-kit-cross-ai`**, and the
  lower-cased text must not match `retry_after_s|hard tier|wait .*second|exit code.*(?:69|75)` (a sentence like "wait for the second
  answer" fails it).
- `tests/test_skill_text_history.py`: main flow (above `## Evidence`) of every kept SKILL.md has no ISO date, no "as of", no run log,
  no `<tool> N.N` version; **every shipped `.md` (SKILL.md and references, not `evals/`) is scanned for pointers**: phase folders,
  phase files, `999.N`, `router-env/`, `referee-x`, and `D-<n>` decision ids (`pointer_hits`, l.142-156). Dated amendments therefore
  go in `.planning/`, never in skill text.
- `tests/test_ai_kit_spec_superpowers.py`: `_super_block(needle)` takes the FIRST fenced bash block of SKILL.md + dispatch +
  session-wake refs containing a needle; a new block must not contain these needles: `while IFS== read`, `RESUME_FOUND=`,
  `single-task plan: no session wake`, `TOOLS_PY="$REVIEW_SKILL_DIR/ai-kit-spec.py"`, `case "$d" in`, `PROJECT_KEY RESUME_STATE_PATH`,
  `IFS== read` (l.2472-2479, 2857, 3570, 3579). l.2987-2993 pin Step 4 < Step 5 order and the `## Step 1:` .. `## Task paths` slice.
  l.3221: the adapter text keeps the string `` `ai-kit-spec-config` and `ai-kit-spec-review` ``.
- `tests/test_skill_evals_shape.py` (generic, every `skills/*/evals/evals.json`): keys exactly `id, prompt, expected_output, files,
  assertions`; id `^(casual|precise|edge)-[a-z0-9-]+$`; >= 5 evals with all three prefixes; each >= 2 assertions of >= 20 chars; files
  under `evals/files/` and listed; at least one eval carries an input file; no machine path; `trigger-queries.json` 16 to 24
  entries, 8 to 12 `should_trigger` true and 8 to 12 false, unique, each >= 30 chars.
- `tests/test_config_callers.py:183-188`: docs/skills Markdown/JSON name `review-spec.toml` only on a line that also says `migrat`.
- `tests/test_config_design_record.py`: `SECTIONS` and `TABLE_NAMES` (l.40-43) must stay present in `docs/config/design.md`; a table
  or key may be ADDED freely (`[lanes.policy.review]` is not in `TABLE_NAMES`; adding it to the record breaks nothing).
- `tests/test_arch_hardcoded_models.py` (phase-35 guard, `SCAN_ROOTS = skills/, tools/, tests/, docs/, README.md, AGENTS.md`,
  l.15; marker `model-example:` l.39; placeholders `placeholder-model-<n>`, `placeholder-alias-<n>`, `fake-<x>`, `router-env/<x>` l.49;
  baseline `tests/fixtures/no_hardcoded_models_baseline.json`, schema 2, shrink-only, l.378-391). New skill text, evals and
  docs must use placeholders only. Baseline holds no entry for any spec-config/review/adapter SKILL.md or eval file today.

#### 1.4 Evals state
- `ai-kit-spec-config/evals/evals.json`: 12 cases (ids listed in `rg` output l.5-119), `trigger-queries.json` 17 (9 true, 8 false),
  one input file `evals/files/stale-opencode/config.toml`.
- `ai-kit-spec-execute-superpowers/evals/evals.json`: 7 cases (`casual-run-superpowers-plan`, `precise-external-cli-pair`,
  `precise-fold-after-review`, `precise-start-before-first-task`, `edge-plan-without-fold-step`, `edge-fold-refused`,
  `edge-executing-plans-out-of-scope`), `trigger-queries.json` 20; none mentions config or lanes.
- `ai-kit-spec-review/evals/` holds FOUR OLD-STYLE MARKDOWN scenarios (`01-superpowers-plan-routes-writing-plans.md` ...
  `04-ambiguous-detection-fallback.md`), **no `evals.json`, no `trigger-queries.json`**. Eval 04 step 7 says "in this eval's default
  no-config state, `REVIEWER_LIST` is the single-entry `NO_CONFIG_FALLBACK`": false after R2.
- `ai-kit-spec-execute/evals/evals.json` (76 lines): untouched.

#### 1.5 Judge machinery
- `tools/judge_loop.py` subcommands `prompt` (incl. `--probe`), `ingest`, `check`, `report`, `pool`, `count` (l.1974-2020).
  Records: `.planning/judge/{inputs.json,REJUDGE.md,facts.json,loops/<n>.json,verdicts/<n>/<skill>/r<N>/<judge>.json,refutations/}`.
- `.planning/judge/REJUDGE.md` rows (read by rg): `ai-kit-spec-config` loop 35, 88.8 B (referee-one) and 88.0 B (referee-two), bar met;
  `ai-kit-spec-execute-superpowers` loop 32, 86.4 B (the native substitute) and 87.2 B (referee-three); `ai-kit-spec-review` loop 32,
  **82.4 B and 75.2 C, lowest 75.2, bar "not met"**, evals "none", deferred "Phases 39-40" (`inputs.json:39-44`, `deferred` field,
  source `ROADMAP.md:520`).
- `check_dogfood.py:568-585` + `_JDG04` regex `(?<![A-Za-z0-9-])JDG-04(?![A-Za-z0-9])`, floor 32: a phase block that mentions
  `SKILL.md` needs `JDG-04` inside its `**Success Criteria**`. ROADMAP Phase 36 criterion 7 (l.742) contains "(JDG-04)": SATISFIED.
  Any amendment of Phase 36's criteria must keep that token inside the criteria block.
- Template `35-26-PLAN.md` (orchestrator action, `autonomous: false`, `cross_ai: false`, 3 tasks): scratch drivers copied from
  `tmp/judge-34/` to `tmp/judge-35/` (`copy_drivers.py`, `judged.py` with `CANDIDATES`/`FACT_ONLY`, `stage.py`, `lanes.py`, `publish.py`,
  `check.py`, `bar_table.py`, `verdict_facts.py`, `stale_before.py`, `stale_after.py`, `loop_record_check.py`; `substitute.py`
  not copied); `tmp/judge-35/` still exists on this machine (untracked). Judges referee-one and referee-two only, no substitute,
  fix rule after EVERY round (`findings.py`: 1-3 critical/important/high findings -> fix commit + `fixes.md`, no further round),
  base commit = the commit that added the phase's first plan, `evals_gate.py` with a non-vacuity case.
- 35-26 SUMMARY recorded as problems/notes (l.78-84): (a) the plan's must-have says both closing commands exit 0 but
  `check ... --require-current --gate` exits 1 after any fix commit (stale digest, by design): word the must-have correctly this time;
  (b) `facts drift` stays after the fix commit unless `judge_loop.py report` runs again (a further `.planning/judge` commit): decide it
  in the plan; (c) when the bar is met through the grade clause the tool prints no lowest-percent/base cell, so the regression
  comparison against the prior loop (loop 33: 83.2) was the executor's own arithmetic: make the plan compute and print it;
  (d) the real-config audit points to the ledger. Earlier loops (REJUDGE.md l.60): a judge verdict was rejected by ingest ("D3 is below
  its max but has no finding"), which forced a native substitute in loop 32: now forbidden, so a rejected verdict = failed lane =
  ledger line + owner question.

### 2. CONTRADICTIONS (listed, not decided)
1. **EXE-01 and Phase 41 criterion 1 are already amended.** CONTEXT D-03 says "made in this commit"; `REQUIREMENTS.md:319-322` and
   `ROADMAP.md:854` already carry the 2026-11-16 amendment. Nothing to write; the plan only verifies it (`rg "36 D-03"`).
2. **D-20..D-23 and HUB-10 exist only in ROADMAP/REQUIREMENTS.** `36-SPEC.md` (R1-R12, "12 locked") and `36-CONTEXT.md` (D-01..D-19)
   say nothing of pools, data-use or R13. ROADMAP criteria 8 and 9 and HUB-05/HUB-10 add: flag written with the lane's pool, fallback
   not flagged and not in the same pool, pool warning, data-use note with confirmation (yes records, no/skip writes no lane).
3. **Grok.** SPEC R7 acceptance names "grok as a custom command lane" (SPEC l.211-212) and the Background lists grok effort forms; the
   2026-11-20 directive says grok is out of scope in 36 (and Phase 39.1 removes it). The R7 test must use a placeholder CLI
   (`placeholder-cli-1` with a `command`) instead.
4. **SPEC/CONTEXT name `docs/config/config-file.md`; it does not exist.** The file is `skills/ai-kit-spec-config/references/config-file.md`;
   `docs/config/` holds only `design.md`.
5. **R11 vs the ROADMAP's own deferral of `ai-kit-spec-review`.** SPEC R11 and ROADMAP criterion 7 put review's SKILL.md in this
   phase's judge bar, but ROADMAP l.118, 469-475, 810 and `inputs.json:43` say review "reaches the bar ... in whichever of Phases 39-40
   first changes its SKILL.md". Review today is 75.2 C, bar "not met", no `evals.json`. Phase 36 changes it first.
6. **Adapter has no `--no-cross-ai`.** SPEC R2 lists an adapter eval for `--no-cross-ai`; the adapter never takes that flag
   (rg). For the adapter the only session-model route is the `once` answer.
7. **TOOLS_PY missing vs spec-config missing.** The reference says a missing `ai-kit-spec.py` degrades like `--no-cross-ai`
   (dispatch.md l.52-54); SPEC R2 says a missing spec-config skill stops. Different facts (the module vs the sibling skill folder).
8. **R3 vs the pinned `purpose` sentence.** `test_session_default_purpose_matches_the_writer` pins the "under `[[lanes.review]]` only
   (`split_by_purpose`)" sentence; CONTEXT D-04 says the writer keeps writing `purpose`. Decision below: keep the sentence if the code
   plans keep `split_by_purpose` for entries without `purpose`; else that test changes in the SKILL plan.
9. **Step 2.2 text vs D-07.** CONTEXT D-07 says the old Step 2.2 ranking "moves into Phase 35's catalog step": Phase 35's
   `catalog.md` has no ranking; the ranking script still sits in `cli-model-selection.md:90-137` and reads `row.review_only` (l.107).
10. **Old Markdown evals of review** contradict R2 (eval 04 step 7, above) and are not new-shape (JDG-04 asks "new-shape evals").

### 3. OPEN QUESTIONS from CONTEXT in my area, answered
- Q "How the catalog names classes/efforts once executed": other researchers; skill text must not name catalog fields: it shows
  `propose-lanes` rows "as printed" (the same rule `catalog.md` follows for `catalog-report`).
- Q "migration backup opt-in before any implicit migration" (D-10): code area; my text states only the user-visible rule and the exact
  command forms once chosen. The migration sentence belongs to `references/config-file.md` + SKILL Step 2.1/4 + README + design.md.
- Q "`probe-quota` union vs roles in use": code area. Skill text: unchanged wording "probes each ladder entry" in review SKILL.md l.157
  must become "probes the review order's lanes" only if the code plans narrow it; flag for the plan author.
- Answered here: the adapter re-invoke problem (section 5, gotcha G2) and where R2's block sits (section 4.1).

### 4. DESIGN PROPOSAL

#### 4.0 Decisions for the text units (so the executor decides nothing)
- One shared R2 block, written ONCE as a constant in the new test module and required verbatim in both SKILL.md files (no drift;
  two copies are needed because each skill must work without the other's files). Keep it ASCII, no host names, no model names.
- `config-status` output contract I need from the code plan (so skill text can parse it): FIRST line is exactly `active`, `pending` or
  `none`; paths follow on later lines; exit 2 + a named error line for a malformed file. Skill text says "read the first line".
- spec-config SKILL.md must SHRINK: it is at 485/500. Move the question flow out into three new references (below); SKILL.md keeps the
  step skeleton, the NEVER list, write and report. Do not raise or drop the 500 test.
- Data-use confirmation comes first for a chosen zero-price lane, before effort or usage-limit questions (HUB-10: "before anything else
  about the lane"); a decline drops the lane before any further question. Pool warning is shown once per provider with a chosen free
  lane, together with the usage-limit question.
- Spec-config missing is checked only on `none` (a user with an active roster is never blocked by a missing wizard). Owner-visible
  assumption A1.
- Review skill is judged in this phase (its SKILL.md is materially changed), and its four Markdown evals become `evals.json` +
  `trigger-queries.json`. ROADMAP/`inputs.json` deferral wording is amended. Owner-visible risk A2: it starts at 75.2 C.

#### 4.1 R2: the shared block (final text; pinned by test)
```
**No-config check** (skipped with `--no-cross-ai`). Run `python3 "$TOOLS_PY" config-status --cwd <CODEBASE_ROOT>` and read its first line.
1. `active`: continue and ask nothing.
2. `pending`: continue; the trust and migration steps handle it, never setup.
3. `none`: ask once, with the host's question tool or numbered plain text, and never answer for the user:
   (1) run ai-kit-spec-config now, (2) run once on the session model, (3) stop. An empty or unrecognised answer is (3).
   (1): follow the sibling ai-kit-spec-config skill to its end, run config-status again (it must print `active`), then continue the task.
   (2): continue on the session default and put the line `no cross-AI config: ran on the session model` in the surface message.
   (3): stop.
4. `none` and the host has no way to ask: print `no cross-AI config: run ai-kit-spec-config; continuing on the session model, nothing written`,
   continue on the session default and repeat that line in the surface message.
5. `none`, the answer is (1) and no ../ai-kit-spec-config/SKILL.md exists beside this skill: stop with
   `ai-kit-spec-config is not installed. Install ai-kit, then run ai-kit-spec-config.`
6. Exit code 2: show the named error line and stop.
```
Adapter variant: same six points; "surface message" becomes "the notice printed at the start and again after the final review"; there is
no `--no-cross-ai` line (G1). `once`/notice scalar: see 4.3.

#### 4.2 Unit D2 - review skill block (1 plan, 3 tasks, 5 files, ~140 new lines; depends on the config-status plan)
- `skills/ai-kit-spec-review/SKILL.md`: in Step 0.7 add the block (after l.155) as "**No-config check**" and a one-line `--no-cross-ai`
  sentence (point 2 of the reference already short-circuits before it); rewrite Constants l.219-221 to "The runner has no exec formula
  for `claude`: an exec-mode `claude` candidate off a Claude Code host is skipped with route `no_formula`; a Claude Code alias on a
  Claude Code host runs natively" and l.246 skip list `review_only` -> `no_formula`; keep the word `review-only` OUT of the file, so
  `test_review_only_label` must change.
- `references/cross-ai-dispatch.md`: replace point 3 (l.123-145): new point 3 = run `config-status`, act per the block, THEN
  `detect-runtimes --if-stale` (the snapshot refresh stays, the old `no-runtimes-snapshot-yet` check and hint are deleted);
  l.180 `review_only` -> `no_formula`; l.52-54 add one sentence: a missing spec-config is stopped only on `none` (point 3).
- `references/cli-profiles/claude.md:14`: rewrite to the `no_formula` fact, labelled "advice, unverified" (R7: the old flag becomes
  advice text, labelled with its source).
- `tests/test_ai_kit_spec_runtimes_table.py`: change `test_review_only_label` to `test_no_formula_wording` (the two files name
  `no_formula` and not `review_only`).
- NEW `tests/test_spec_chain_text.py` (joins the unit group; run `python3 tools/gen_test_groups.py`; commit Makefile + `.pre-commit-config.yaml`
  lists): `BLOCK` constant (4.1); tests: block present verbatim in review SKILL.md; point 3 of the reference runs `config-status` before
  `detect-runtimes --if-stale` and the string `no-runtimes-snapshot-yet` is gone; `--no-cross-ai` sentence precedes it; a fixture-project
  test runs `ai-kit-spec.py config-status --cwd <tmp project>` through `subprocess` with a scratch HOME and `AI_KIT_REFUSE_REAL_HOME=1`:
  no config -> first line `none`, a project with an active `[[lanes.review]]` roster -> `active` (R2 acceptance); a non-vacuity case:
  a SKILL text without point 6 fails the check. Commands in text parsed with `cli._build_parser().parse_args` (pattern of
  `test_spec_config_catalog_text.py:25-39`).
- Tasks: (1) SKILL + reference + claude.md, (2) test module + runtimes_table edit, (3) gen_test_groups + run the 5 pinning modules.

#### 4.3 Unit D3 - adapter block (1 plan, 2-3 tasks, 5 files, ~110 lines; depends on D2 for the test module)
- `skills/ai-kit-spec-execute-superpowers/SKILL.md`: new `### Step 1a` is NOT usable (tests slice `## Step 1:` .. `## Task paths`
  l.2993); add the block as a paragraph at the START of Step 1 after the "Follow its own Setup exactly" sentence and before the
  start-step paragraph, pointing to NEW `references/config-check.md` (MANDATORY read; the 6 points + one bash block). Reason: CWD and
  PLAN_FILE exist only after Setup, and the owner must be asked BEFORE `fold.py start` moves commits.
- `references/config-check.md` bash block (no needle of 1.3): runs `config-status --cwd "$CWD"`; computes `PROJECT_KEY` with the same
  python one-liner as the Task paths block and the same `SCALARS` path; appends `CONFIG_CHECK=<active|pending|once|notice|chained>`
  to it; on entry, if the file already holds a `CONFIG_CHECK=` line it prints nothing and skips the ask (quota-wake re-invokes start at
  Step 0 with no memory and the owner is away: G2). The `once`/`notice` text is printed at the start and again after the final
  whole-branch review (Step 5 sentence), because the adapter has no surface message of its own.
- Reword `claude` is review-only: SKILL.md l.277, `resolution-stops.md:34` (`review_only` -> `no_formula`), `escalation.md:21`,
  `design-notes.md:31,81` (state the runner-formula fact, not the seed flag). `test_exec_confinement_statement` tokens stay.
- Tests: append to `tests/test_spec_chain_text.py` (adapter block verbatim minus the `--no-cross-ai` line, references link resolves,
  `CONFIG_CHECK=` guard present, block bash passes `bash -n`, `config-check.md` has no needle of 1.3); update
  `tests/test_ai_kit_spec_superpowers.py` only if a `review_only` wording assertion reads these texts (the l.383-416, 540-544, 1597-1729
  hits are code-route tests, owned by the routing plan).

#### 4.4 Units D4b, D4c, D4a - spec-config skill rewrite in parts (order: references first, SKILL.md last)
- **D4b `references/wizard-flow.md` (NEW, ~120 lines) + rewrite `references/cli-model-selection.md`** (plan: 3 tasks, 4 files incl. tests).
  `wizard-flow.md` is the one place the question order lives, as numbered steps each with its `- Run:` command lines:
  1 preferred runtimes per purpose (review set, execute set; one question each; filters every later list);
  2 per purpose `- Run: `propose-lanes --purpose review|execute --catalog-path <catalog> --runtimes <ids>`` (final flags per the proposal plan),
    show the rows as printed with the ranker label per row, default view 5 + "show more", `router-env` group labelled
    `assumed: router-env alias naming`, ONE confirmation per set, nothing written before both confirmed;
  3 (free lanes: see `free-lanes.md` before this step for each chosen zero-price lane);
  4 effort per chosen lane: offered only from the levels the command prints; unknown support: one `check-reviewer --effort <level>`
    call, stored labelled `accepted by a call on <date>`, a rejection stores nothing and shows the host's first error line; claude and
    copilot: no question, one line "the runner has no effort flag for <runtime> yet, so none is stored";
  5 each role's order as a numbered list, default the ranking order, owner may reorder, reviewers and executors separately;
  6 escalation, only for a role with two or more lanes, default no, text "stored and informational: no run reads it yet";
  7 the test call (`check-reviewer`), preceded by the one-line allowance warning "this call spends part of the lane's allowance";
  8 write only the chosen lanes.
  `cli-model-selection.md`: delete items 5-7 (ranking script l.90-137, present-shape l.152-203) and every `review_only`/`no_exec`
  reference (a table row never decides); keep items 1-4 (snapshot, extra candidates, fetch, unmatched confirmation), 8 (code-index) and
  9 (router aliases); rename to keep the link; the test `test_cli_model_selection_keeps_no_shell_state_across_blocks` keeps its three
  assertions (`## Build and classify` link text, `caches each source by its own age`, no `narrowed to the ids chosen`).
  Tests (NEW `tests/test_spec_config_flow_text.py`): step order in `wizard-flow.md`; every `- Run:` line parses; text names
  `propose-lanes` before `check-reviewer`; the word `review_only` appears in no spec-config file; claude/copilot no-effort line.
- **D4c `references/free-lanes.md` (NEW, ~90 lines)** (plan: 2 tasks, 3 files). Text, in this order, for each chosen lane that is
  zero-price: (a) data-use note first: `- Run:` of the data-use command (name from the data-use plan); show `zero_retention`,
  `may_be_kept_or_trained` or `unknown` with source, read date and `verified`/`reported` label; "unknown is never treated as safe";
  say "a lane sends your project content to that vendor" and ask yes / no / skip; yes records note + confirmation beside the lane, no or
  skip writes NO lane and the lane leaves the set; (b) usage-limited question: yes (optional one-line note) / no / not sure; only yes
  writes the flag with the lane's pool (provider plus free tier); (c) pool warning: "Free models of <provider> appear to share one pool
  (reported, not confirmed by the vendor): another free model of <provider> is not a fallback for this one."; (d) fallback sentence:
  "a flagged lane's fallback is the first lane of the role that is neither flagged nor in the same pool; stored, read only by the
  lane-switching phase"; (e) alternative-lane step when a role holds only flagged lanes: propose the best-ranked unflagged candidate,
  write after the owner adds one or says explicitly there is none (then print the standing warning); (f) herdr: questions are always
  asked in the owner's session, never in a pane or by another agent. Tests: append to `test_spec_config_flow_text.py`: the six
  items present in order, "no or skip writes no lane" sentence pinned, no model name (guard passes).
- **D4a SKILL.md skeleton (LAST; plan 3 tasks, 4 files, net negative line count)**: Step 0/1 unchanged except the new headless stop
  (below); Step 1.5 unchanged; Step 2 table rewritten to point at `wizard-flow.md` and `free-lanes.md`; **keep the headings
  `#### Step 2.1`, `2.3`, `2.4`, `2.5`, `2.6`** (tests pin 2.5 and 2.6; 2.2, 2.7, 2.8 become short stubs or are folded into the
  references); 2.1 keeps the gates but the replace sentence loses "stays recoverable as `review-spec.toml.migrated`" (R9): new
  sentence "an old `review-spec.toml` migrates first and is deleted after the value check; run with `--keep-backup` to keep a
  `review-spec.toml.migrated` copy"; the wizard's migration line says the same; Step 2.7 session-default ask becomes a line in
  `wizard-flow.md` (a registered session-default lane counts as a roster: chain R2); Step 2.8's single `policy.ladder` becomes per-role
  `[lanes.policy.review]`/`[lanes.policy.execute]` orders; Step 3's JSON shape drops "`purpose` both"; Step 4 reads each role's
  `ladder` from the rendered file and prints two numbered lists; NEVER list: delete "placed last in `policy.ladder`", rewrite the
  session-default bullet per role, add "Never ask a wizard question in a pane or of another agent" and "Never write a lane whose
  data-use confirmation was declined or skipped". Description: replace "when ai-kit-spec-review warns no config exists" by "when
  ai-kit-spec-review or ai-kit-spec-execute-superpowers offers it because no lanes exist"; stay under 1024 chars
  (`test_skill_frontmatter.py:38`).
  **R10 headless stop (Step 1, after detection)**: "If the host has no structured-question tool and no plain conversation (a subagent
  or a print-mode run), STOP after Step 1: print the block in `references/headless.md`, write nothing, and say a person must run
  ai-kit-spec-config." NEW `references/headless.md` (~25 lines): fixed lines `ai-kit-spec-config cannot ask here; nothing was
  written.`, `Installed runtimes: <id: listing count, ...>` (from `detect-runtimes`/`catalog-report`), `Questions it would ask:` and the
  numbered list in wizard-flow order, `A person must run ai-kit-spec-config.`
  Tests: update `test_ai_kit_spec_check_providers.py` (twelve ids -> new id list; keep the other pins), add to
  `test_spec_config_flow_text.py`: headless stop sentence before Step 2 and `headless.md` fixed lines; SKILL.md <= 500 lines
  (existing); exactly one `ai-kit-cross-ai` line (existing).
  Also edit `references/config-file.md`: tables row `[lanes.policy]` `mode`, `timeout_tiers`; new rows `[lanes.policy.review]`,
  `[lanes.policy.execute]` (`ladder` each); lane keys add `escalate_runtime`, `escalate_model`, `usage_limited`, `usage_limit_note`,
  `pool`, `data_use` (final names from the code plans); Roles paragraph "the order of entries inside a role" -> the role's `ladder`;
  Migration section: old file deleted after the value check unless `--keep-backup`; `render-toml --keep-backup`; `config-status` and
  `propose-lanes` under a new "Read-only commands" bullet list.

#### 4.5 Unit D5 - evals (2 plans)
- **D5a spec-config evals** (3 files: `evals/evals.json`, `evals/trigger-queries.json`, one new file under `evals/files/`; plus the
  id-list test edit): keep the 12 existing cases except rewording these (they become false): `edge-declined-runtime-never-presented`
  ("narrows the discovered pairs before ranking" -> "the shortlist is limited to the preferred runtimes of the purpose"),
  `precise-global-write` (keep the pinned phrases `already has a [lanes] table`, `replacement consent`), `edge-existing-local-config-replace`
  (no "recoverable as .migrated"). Add (final count 18): `edge-no-way-to-ask-stops-after-detection` (R10: no write, pending block),
  `precise-per-role-orders` (two numbered lists, review and execute separate), `edge-claude-effort-not-asked` (one line why, none stored),
  `precise-escalation-only-with-two-lanes`, `edge-zero-price-usage-limit-and-data-use` (yes records, a decline writes no lane, no flag from
  price), `edge-migration-deleted-unless-keep-backup`. Trigger queries: grow 17 -> 20 (10 true, 10 false; add near-misses "run my review
  with the lanes I configured", "edit one lane's effort by hand in config.toml"). Input file: one fixture project config with a free lane
  placeholder (`placeholder-model-1`, `fake-provider`).
- **D5b review and adapter evals** (review: NEW `evals/evals.json`, `evals/trigger-queries.json`, 3-4 files under `evals/files/`, delete
  the 4 `.md` scenarios; adapter: 3 appended cases in `evals/evals.json` + 2 trigger queries, one new input file). Review cases (>= 6):
  `casual-review-my-plan`, `precise-no-config-asks-once`, `precise-config-active-never-asks`, `edge-no-cross-ai-never-checks`,
  `edge-spec-config-missing-stops`, `edge-no-way-to-ask-session-default`, `edge-ambiguous-framework-fallback` (from old 04, with the
  corrected step 7), plus the converted old 01-03 as `casual-superpowers-plan-routes-writing-plans`, `precise-gsd-plan-routes-native-cmd`,
  `edge-generic-doc-direct-edit` (10 cases, 20 trigger queries, 10 near-misses). Adapter cases: `precise-no-config-chains-spec-config`,
  `edge-spec-config-missing-stops`, `edge-no-way-to-ask-notice` (and `config present never asks` folded into an existing precise case).
  Tests: nothing new if shape tests pass; add to `test_spec_chain_text.py` a check that each of the three skills' evals name the five
  R2 situations (substring ids). `facts.json` counts update at the judge step, not by hand.

#### 4.6 Unit D6 - docs and READMEs (1 plan, 3 tasks, 5 files, ~90 lines; after D4)
- `README.md:34` (drop "`claude` is review-only", say routing refuses a pair only for a named fact such as a missing runner formula);
  `:35` (spec-config row: per-purpose shortlist via `propose-lanes`, `config-status` chain, per-role orders, free-lane notes); `:57`
  (`[lanes.policy.review]`/`[lanes.policy.execute]`); `:63` (delete-after-verify, `--keep-backup`, `review-spec.toml.migrated` only with
  the flag; the runner's `cross-ai.json.migrated` sentence unchanged).
- `docs/config/design.md`: l.38 (per-role ladders now delivered), l.39-44 (new lane keys), the Tables list gains `[lanes.policy.review]`
  and `[lanes.policy.execute]`; l.132, 144, 156-157 (the `.migrated` renamed/kept columns) for the two review-spec rows. `TABLE_NAMES`
  and `SECTIONS` stay valid. The "keep" column wording must keep the word `migrat` on every line naming `review-spec.toml`
  (`test_config_callers.py:183`).
- `AGENTS.md:104`: "the review-only flag" -> "the seed advice text". `references/config-file.md` is in D4a.
- Tests: extend `tests/test_spec_chain_text.py`? NO (docs): add `tests/test_config_docs_text.py`? Avoid a module: pin docs inside
  `test_spec_config_flow_text.py` (README row names `config-status`, `propose-lanes`, `--keep-backup`; `design.md` names both role
  tables and `usage_limited`). Pinning is by substring from a constant list.

#### 4.7 Unit D1 - planning amendments (1 plan, 2 tasks, 4 files, ~70 lines of text, no test; FIRST wave)
- `36-SPEC.md`: dated amendment block "Amended 2026-11-20": R12 gains clauses (g) pool recorded with the flag, fallback = first lane
  neither flagged nor in the same pool, pool warning; new R13 (HUB-10: data-use note, confirmation, yes/no/skip); R7 acceptance "grok as a
  custom command lane" -> "a placeholder CLI with a `command`"; Background note that grok stays out of scope (no new grok test, doc or
  fixture); counts "12 locked" -> "13 locked"; edge/prohibition rows for R13 (empty: unknown never safe; precision: no list decides;
  prohibition: MUST NOT write a lane whose data-use confirmation is declined or skipped).
- `36-CONTEXT.md`: D-20 (pool recorded with the flag; fallback from a different pool), D-21 (fallback rule text), D-22 (wizard pool
  warning; provisional, owner confirmation), D-23 (data-use note, confirmation, decline writes no lane; closed value list
  provisional), and a "Refined 2026-11-20" line under D-03 stating EXE-01/Phase 41 amendments are already made (contradiction 1).
  Copy wording from ROADMAP l.743-744 and REQUIREMENTS l.240-243, 262-270 verbatim.
- `ROADMAP.md`: Phase 36 criterion 5 grok-free wording is fine; ADD to l.118, 469-475, 810, 841 an amendment "ai-kit-spec-review
  reaches the bar in Phase 36, the first phase to change its SKILL.md; Phases 39-40 keep it" (contradiction 5, with owner-visible A2);
  keep `JDG-04` inside criterion 7. `.planning/judge/inputs.json:43` (`deferred`) is NOT edited by hand: it changes at the judge plan
  (D7) so `REJUDGE.md` stays reproducible.
- Verify command (script under `tmp/p36-plan/`, no repo test): `rg -c "D-20|D-23|HUB-10" 36-SPEC.md 36-CONTEXT.md` nonzero;
  `python3 tools/check_dogfood.py`-equivalent is `make check-dogfood` (run at the judge plan).

#### 4.8 Unit D7 - judge loop plan "36-NN" (orchestrator action; mirrors 35-26; LAST wave)
- Frontmatter: `type: execute`, `autonomous: false`, `cross_ai: false`, `requirements: [HUB-01, HUB-05, HUB-07, HUB-10]`, depends_on
  every other plan. 3 tasks as in 35-26 (tracer: drivers/judged set/probes/pool/count/lanes launched; checkpoint: wait for lanes;
  auto: publish, report, check, bar table, evals gate, fix rule).
- SKILL.md files this phase changes MATERIALLY (need the loop): `ai-kit-spec-config` (rewrite), `ai-kit-spec-review` (Step 0.7 block,
  Constants, claude wording; plus new evals), `ai-kit-spec-execute-superpowers` (Step 1 block + `config-check.md` + wording).
  NOT judged: `ai-kit-spec-execute` (unchanged, confirmed), `ai-kit-commit-fold`, project-rules skills. `judged.py`:
  `CANDIDATES = ["ai-kit-spec-config","ai-kit-spec-review","ai-kit-spec-execute-superpowers"]`, `FACT_ONLY = []`, base = parent of the
  commit that added this phase's first plan; guard exits 1 on a changed skill outside CANDIDATES. Drivers copied from `tmp/judge-35/`
  with `35` -> `36` (`copy_drivers.py` exists as the pattern; if `tmp/judge-35/` is gone recreate from `tmp/judge-34/` per 34-10).
- Bar per skill, from the tool: no critical/high or grade B or better, and no regression vs the prior loop: config 88.0 (loop 35 lowest),
  exec-superpowers 86.4 (loop 32), review 75.2 C (loop 32, bar currently unmet: an A2 risk: if still below B after round 3, record as it
  stands and return the owner question).
- Fix rule counted PER SKILL after every round (`findings.py` groups by skill): 1-3 critical/important/high findings of a skill ->
  fix commit limited to that skill's own files + the pinning test + `r<N>/fixes.md`; more than 3 -> next round (max 3).
- Corrections vs 35-26 (its problems): must-have says the plain `check` exits 0 and the `--require-current --gate` form runs only BEFORE a
  fix commit; the plan computes and prints the regression comparison (percent vs prior base) per skill when the tool prints no cell; the
  plan decides on `judge_loop.py report` after a fix commit: DO NOT regenerate (a stale digest is by design until the skill's next loop;
  record `facts drift` in the SUMMARY); an ingest-rejected verdict is a failed lane (ledger line + owner question, no native, no
  referee-three); `inputs.json` `deferred` for review is cleared in Task 3 step 0 BEFORE `report` (one `.planning/judge/` commit);
  `evals_gate.py` runs for ALL THREE skills (review must hold >= 1 case: contradiction 10).
- Closing: `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge` exit 0, `make check-dogfood` prints
  `check-dogfood: ok`, `stale_after.py` prints `stale ok`; results go to the SUMMARY block copied into 36-VERIFICATION.md.

#### 4.9 Wave order for these units
D1 (wave 1, text only) -> [code plans for config-status, propose-lanes, effort/escalation/usage-limit commands, data-use command,
`no_formula` route, migration flag: other researchers] -> D2 -> D3 (same test module, sequential) -> D4b -> D4c -> D4a -> D5a, D5b
(parallel with each other, after D4a; D5a edits the id-list test) -> D6 -> D7 (last). Plans that add a test module run
`python3 tools/gen_test_groups.py` and must not share a wave (the same generated Makefile line and `.pre-commit-config.yaml`).
New test modules from my area: `tests/test_spec_chain_text.py` (D2), `tests/test_spec_config_flow_text.py` (D4b). Both get
`gen_test_groups` and `tests/test_gate_scope.py` stays green.

### 5. GOTCHAS for a cheap coding model
- G1: the adapter has no `--no-cross-ai`; never copy that line or its eval into the adapter.
- G2: the adapter's quota-wake re-invoke starts at Step 0 with no memory and the owner is away: the `none` ask must not repeat; the
  `CONFIG_CHECK=` scalar guard in `references/config-check.md` is mandatory, and `once` still prints its notice at the end.
- G3: spec-config SKILL.md is 485/500 lines: write the references first, then delete before you add; run
  `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_check_providers` after each edit.
- G4: pointer rules: no `D-<n>`, no phase folder or file names, no `router-env/`, no `referee-x`, no ISO date or "as of" in any shipped
  `.md` outside `evals/`; the amendments and decision ids live in `.planning/` only.
- G5: models in skill text, references and evals JSON are placeholders only (`placeholder-model-1`, `placeholder-alias-1`,
  `fake-provider`); a `router-env/<x>` literal in a skill fails the guard unless marked `model-example:`.
- G6: `wait .*second` and `retry_after_s|hard tier|exit code.*(69|75)` are banned in spec-config SKILL.md by regex (lower-cased).
- G7: exactly ONE line containing `ai-kit-cross-ai` in spec-config SKILL.md, and `auth.json` only inside `## NEVER`.
- G8: the PAIR_RULE paragraph must stay verbatim in review and spec-config SKILL.md; do not reflow it.
- G9: `_super_block` returns the FIRST matching bash block: never reuse an existing needle in a new adapter block (list in 1.3);
  never add a bash fence before an existing one that tests index by position without checking their needles.
- G10: `trigger_problems` needs 16-24 queries with 8-12 of each polarity; an eval needs `evals/files/` input listed by an eval, and
  every file under `evals/files/` must be listed.
- G11: `test_skill_evals_have_the_twelve_cases` pins the id LIST: any eval id change edits that test in the same plan.
- G12: do not hand-edit `.planning/judge/REJUDGE.md` or `facts.json`: only `judge_loop.py report` writes them (`check-dogfood` compares bytes).
- G13: README/doc lines naming `review-spec.toml` must also contain `migrat` (`test_config_callers.py:183`).
- G14: the word `review-only` must be removed from review SKILL.md and `cli-profiles/claude.md` together with the test that requires it.
- G15: judge-loop plans write only under `tmp/judge-36/` and `.planning/judge/`; frozen tree while lanes run; no `make test`.

### 6. Owner-visible assumptions (for the Assumptions Log of the plan)
- A1: spec-config missing is a stop only when the state is `none` and the owner picks "run now" (not on `active`).
- A2: `ai-kit-spec-review` joins the judge loop in this phase (reverses the 39-40 deferral); it starts at 75.2 C and may need the
  three-round rule or an owner decision.
- A3: the first-line contract of `config-status` (`active|pending|none`) is requested from the code plan, not yet built.
- A4: new lane key names (`pool`, `data_use`, `usage_limit_note`, `escalate_*`) in `config-file.md` follow the code plans' final names.
