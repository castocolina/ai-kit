# 39-11 Summary: lens selection, the runner pre-checks, the budget loop and the MCP pick

Status: complete. Commits b800830 (`feat(39-11): select and pre-check lens skills against the runner's limits`, Task 1, with the
regenerated test-group listings), 7268c2d (`feat(39-11): pick code-index MCP servers and write the run-scoped file`, Task 2) and
abaeddd (`test(39-11): pin lens pre-checks, the budget loop and the lens-note lists`, Task 3). Executed through three cross-AI lanes
(pi router-env/my-coding), each status=ok on its first run (616 s, 254 s, 224 s).

## What changed

- `lens_delivery.py` (new): `LENS_NOTES` (closed list of five), `UI_EXTENSIONS`, `UI_ROLE`, the mirrored runner limits
  `FILE_READ_MAX` and `SKILL_NAME_RE`, `FRONTMATTER_RE`, `FM_NAME_RE`, `MCP_FILE_NAME`; `_seed_rows` (tolerant seed read);
  `lens_set(table_host, files, role, native_host)` (table order, UI rule, first row per name, built-in seed rows by name only for their
  native host, else `built_in_no_file`); `check_lens` (the runner's whole-lane refusals mapped to `not_present` or `path_rejected`, the
  raw-descriptor regular-file check before the bounded read, strict UTF-8, byte-order mark, `</skill>` in the body, R8 checks of the
  directory and of the real `SKILL.md`; returns the runner name, aliases, real path, sha256 and prose bytes); `prose_block_bytes`;
  `plan_lenses` (alias collisions `path_rejected`, whole-lens `over_window` skips, later lenses still tried, inputs not mutated);
  `mcp_pick` (seed `launch` rows whose role, host row first then `resolve_role`, is `code_index` and whose binary resolves on the given
  child PATH only); `write_mcp_file` (O_EXCL, mode 0600, None and no file for no pick).
- `tests/test_lens_delivery.py` (new, 11 tests: `TestRunnerSync` through the real node, `TestMcpPick`, `TestLensChecks`, `TestPins`);
  `Makefile` and `.pre-commit-config.yaml` list the module.

## Verification (run by the chunk agent)

- Acceptance greps: `LENS_NOTES` 1, `def plan_lenses(` 1, `tests.test_lens_delivery` in Makefile 1, the O_EXCL 0600 open 1,
  `path=child_path or "")` 1, `capability_block` no match, `ai_kit_spec_superpowers` no match, `def test_` 11.
- Under the scratch-HOME wrapper (node ok): tests.test_lens_delivery (11), test_capability_block (15), test_runner_preview (16),
  test_arch_hardcoded_models (23), test_gate_scope (62), test_arch (118), test_skill_table (61), test_prompt_guard (27) pass; the
  real-node tests fail visibly in `setUp` when node is missing (no skip). Lanes: ruff, pyright, vulture, pylint exit 0; the Task 1 hook
  ran the full unit and arch groups (205/205).
- Patches in the tests are only the plan-named ones: `load_seed` raising `ValueError`, the scratch HOME for `--describe`, the parent PATH
  of the MCP pick. `detection.py`, `capability_block.py`, the model-literal baseline and both runner copies unchanged.

## Deviations

- Task 1 added two tests beyond the behavior block (rejection and alias-collision cases) to the tracer commit; Task 3 then added the six
  planned tests (11 in total, the plan asks at least 9).
- Docstrings and comments are shorter than the plan's texts; Task 1 left out the `json` and `shutil` imports until Task 2 used them.
- `_read_raw` reads with a size-tracked loop (`os.read(fd, FILE_READ_MAX + 1 - size)`) instead of summing the chunk list each round
  (same bound); the frontmatter name lookup is a helper `_frontmatter_name` shared by `_runner_name` and the aliases.
- A pathless row that is not delivered by name keeps `skill_name` None (the plan text is ambiguous there); such a row is never passed as
  a runner flag.
