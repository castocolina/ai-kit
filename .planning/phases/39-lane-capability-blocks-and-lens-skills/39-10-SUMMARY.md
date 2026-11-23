# 39-10 Summary: the lane capability block and its summary line

Status: complete. Commits 5a578a3 (`feat(39-10): build each lane's capability block from its own facts`, Task 1, with the
regenerated test-group listings in `Makefile` and `.pre-commit-config.yaml`) and dff2c24 (`test(39-10): pin code index routes,
child PATH tools and lens lines`, Task 2). Executed through two cross-AI lanes (pi router-env/my-coding), each status=ok on its first
run (523 s, 220 s).

## What changed

- `capability_block.py` (part 2): the constants `SECTIONS`, `UNKNOWN_TEXT`, `HOST_CANNOT_LOAD`, `ACCESS_TEXT`, `NO_SHELL_LINE`,
  `NO_TOOL_LINE`, `NO_INDEX_LINE`, `SHELL_IF`, `ENABLED_INDEX_LINE`; `BlockInput` (13 fields, NamedTuple for pylint's argument cap);
  `child_path(path_value, cwd)` (absolute entries kept, relative ones joined onto the child's cwd or dropped); `build_block(lane)` with
  the sections LANE (plus `note:` lines), ACCESS (the soft-confinement sentence only for an execute lane with `write` full or unknown,
  D-04 as written), TOOLS (tools resolved with `shutil.which(name, path=<child PATH>)`, the `SHARED_TOOLING_PATH`,
  `AGENTS_TOOLING_PATH` and `TOOL_AVAILABILITY` names kept, `<NAME>: omitted (<reason>)` lines), CODE INDEX (three routes, first match
  wins, never two; present-not-enabled lines for host `code_index` rows), SKILLS, SETTINGS; a native lane gets its lens lines only;
  `summary_line(facts, runtime, model, role, notes=())`.
- `tests/test_capability_block.py` (new, 15 tests); `Makefile` and `.pre-commit-config.yaml` list the module (gen_test_groups).

## Verification (run by the chunk agent)

- Acceptance greps: `def build_block(lane: BlockInput) -> str:` 1, `path=path)` 1, `tests.test_capability_block` in Makefile 1,
  `def test_` 15, `OS_SANDBOXED_EXEC` no match.
- Under the scratch-HOME wrapper: tests.test_capability_block (15), test_runner_preview (16), test_ai_kit_spec (688),
  test_arch_hardcoded_models (23), test_gate_scope (62), test_arch (118) pass. Lanes: ruff, pyright, vulture, pylint exit 0; the Task 1
  commit hook ran the full unit and arch groups (204/204).
- The only patches in the tests are the plan-named parent-PATH `patch.dict(os.environ, ...)` cases; `detection.py`, the model-literal
  baseline and both runner copies unchanged.

## Deviations

- Every value from outside the module is shown through `_shown` (redact, then escape), including the role, the label state and source
  (orchestrator anchor note: Task 2 expects `<redacted>` in an ACCESS line), the MCP server name, the lens note and the setting name
  (the plan text named `escape_value` alone for some of them).
- The code-index route choice lives in a helper `_index_route` (pylint branch and return caps); the tooling lines are built in one loop
  over the two names; docstrings are shorter than the plan's texts.
- Open item (found after the fold, not changed): `child_path` joins an empty PATH entry onto `cwd`
  (`child_path("", "/x") == "/x/"`, `child_path("/usr/bin:", "/x") == "/usr/bin:/x/"`), so with `cwd` set an absent PATH or an empty
  segment resolves tools and the MCP command from the child's working directory; the plan says an empty PATH finds nothing and the
  test for it leaves `cwd` unset. 39-12 is the first caller that passes `cwd`; dropping empty entries is the orchestrator's call.
- Two newline expectations in Task 2 were written as the escaped form `\u000a` that `escape_value` prints (the plan said "escaped on one
  line" without the literal).
