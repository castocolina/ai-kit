# 37-18 Summary: routing and execute refusals read the runner's recorded `--describe` fact

Status: complete in three per-task lanes (pi `router-env/my-coding`), verified by the orchestrator; one open item for code review (see Deviations).

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=656s attempts=1`, commit 40791cf (hook 134/134).
- fix-b (Task 2): `status=ok exit=0 elapsed=535s attempts=1`, commit 9eee4ea (hook 131/131).
- fix-c (Task 3): `status=ok exit=0 elapsed=516s attempts=1`, commit a8f9e5b (full-group hook 198/198, uv subset 19/19).
- Prompts were built from the plan's own task blocks plus orchestrator anchor notes checked against e99bfa6 (`tmp/run-2026-11-19/c7-notes-37-18.md`; several test line numbers had moved).

## Commits

- 40791cf `feat(37-18): the runner's --describe recorded in the runtimes snapshot and read by routing`
- 9eee4ea `feat(37-18): execute_cli_error reads the recorded runner fact`
- a8f9e5b `refactor(37-18): delete the exec_formula mirror, SUPPORTED_EXECUTE_CLIS and the drift test`

## What was done

- New `ai_kit_spec/runner_facts.py` (`DESCRIBE_TIMEOUT_S`, `FACT_SOURCE`, `template_sha256`, `read_runner_describe`, `fact_is_current`, `refresh_fact`, `runner_has_exec`, `stored_fact`), stdlib plus the cache helpers and the template resolver.
- routing.py: `Inventory.runner`; `no_formula` only from a current fact; a string runtime outside the table routes `unverified`; `no_inventory` gone from routes and `SKIP_ROUTES`; `no_formula_detail` names `FACT_SOURCE`; `load_runtimes_snapshot` refreshes a stale fact on the fresh path and the build path. cli.py `detect-runtimes` refreshes the fact in the `--if-stale` early return and on the build path.
- commands.py `execute_cli_error(cli, fact=None)`; cli.py `_cmd_dispatch_execute` and execute_dispatch.py `_refuse_candidate` pass `runner_facts.stored_fact(dict(os.environ))`.
- Task 3: the `exec_formula` mirror (`ExecFormula`, `Runtime.exec_formula`, `has_exec_formula`, `NO_RUNNER_ENTRY`, `exec_formula_source`), `SUPPORTED_EXECUTE_CLIS` and `tests/test_ai_kit_spec_exec_formula_e2e.py` deleted with their runner entries and regenerated listings; `TestNoRunnerFormulaMirror` added.
- tests/test_runner_facts.py (replaces the 37-02 stub): 10 tests, no node or host spawned (synthetic `node-bin`).

## Evidence

Orchestrator re-run, `tmp/run-2026-11-19/c7-verify-37-18.sh 193d4ca 3`:

- Acceptance greps: six runner_facts functions and the exact `FACT_SOURCE`; routing has no `has_exec_formula`, `exec_formula_source` or `no_inventory`; 10 test methods in tests/test_runner_facts.py, grok 0; dispatch_injection no `no_inventory`; commands.py has `def execute_cli_error(cli, fact=None)` and `runner_facts.FACT_SOURCE`; no mirror name in skills, tools, Makefile, .pre-commit-config.yaml or tests (outside tests/test_no_seed_refusal.py); the drift e2e module is deleted and listed nowhere; grok lines added 0; baseline json unchanged.
- Modules 12/12 (runner_facts, ai_kit_spec_routing, gate_scope, no_seed_refusal, ai_kit_spec_legacy_config, ai_kit_spec_runtimes_table, ai_kit_gsd_curated_config, arch_hardcoded_models, ai_kit_spec, ai_kit_spec_superpowers, ai_kit_spec_runner_dispatch, run_unittest_parallel); verbose test_runner_facts 10 ok, none skipped.
- Diffs of every non-test file reviewed against the plan: as written, except the route_all floor line below.

## Deviations

- routing.route_all reads `_within_floor` before `load_runtimes_snapshot` (fix-a): a fact refresh on the fresh path rewrites the cache, which would otherwise make the targeted-refresh floor look freshly hit. Root fix, behaviour of the floor unchanged.
- Test edits outside the task lists (lesson 4, the old behaviour is what this plan replaces): tests/test_ai_kit_spec.py `--if-stale` fresh-path asserts now expect one `which("node")` lookup; the routing test helper `_snapshot` seeds a current empty fact so refreshes call no fake; tests/test_ai_kit_spec_superpowers.py's claude execute candidate now routes `not_installed` (no fact, not in that inventory); tests/test_ai_kit_gsd_curated_config.py's rejected-executor test (claude, grok, Claude) was replaced by one positive no-fact claude test (the rejection no longer exists; the grok variant went with it).
- OPEN ITEM (not resolved here): `execute_selection.screen_execute_clis` (the plan keeps execute_selection.py unchanged) still refuses an execute lane whose runtime is outside the table or a runner-less row, and builds its reason from `execute_cli_error(cli)`, which now returns None without a fact, so that refusal carries an EMPTY reason; fix-b changed `TestExecuteLadderScreen` to assert `"reviewer 'p1' sets purpose = \"execute\": "`. Under R9 a string runtime outside the table is served by the runner, so either the screen's refusal goes or it names its own fact; this is a design decision for code review, and the test assertion must not stay weakened.
