# 39-01 Summary: the skill role table, the seed file and the `[skills.roles]` reader

Status: complete. Commits b9bc167 (`feat(39-01): add the skill role table seed and resolver`, Task 1) and 2fc2fca
(`feat(39-01): check seed rows and read confirmed skill roles from the layered config`, Tasks 2 and 3 in one lane). Executed through
two cross-AI lanes (pi router-env/my-coding), each status=ok on its first run (447 s and 399 s).

## What changed

- `skills/ai-kit-spec-review/references/skill-roles.json`: schema 1, the eight roles, the 14 D-07 seed rows in D-07 order; `simplify`
  carries `built_in: "claude"`, `codebase-memory-mcp` (kind `mcp`) carries the one `launch` form (`--tool-profile=analysis`, labelled
  effect unverified).
- `skills/ai-kit-spec-review/ai_kit_spec/skill_table.py`: `ROLES`, `KINDS`, `BUILT_IN_HOSTS`, `SEED_PATH`, `load_seed` (strict),
  `seed_problems(rows, literal_hits=None)` (label, role, kind, launch, built_in, duplicate and injected model-literal checks),
  `user_roles(cwd, env)` (layered `[skills.roles]`, project over user, `ConfigError` on a non-table or a role outside the seven stated
  roles), `table_inputs(cwd, env, seed_path=None)` (the one never-raising loader: notes `skill seed ignored: ...` and
  `skills.roles ignored: ...`), `resolve_role` (user-stated over seed over none, exact names, damaged rows skipped).
- `tests/test_skill_table.py`: `TestSkillTableSeed`, `TestResolveRole`, `TestSeedProblems`, `TestUserRoles` (13 tests); the generated
  unit listings in `Makefile` and `.pre-commit-config.yaml` gain the module.

## Verification (run by the chunk agent)

- Acceptance greps: 14 names, 1 launch, 1 built_in, `ROLES = (` 1, Makefile listing 1, 13 tests, the `seed_problems` signature 1,
  the `cfg_layered_table(cwd, env, "skills", "roles")` call 1, no whole model literal in the test file.
- tests.test_skill_table (13), tests.test_arch_hardcoded_models (23), tests.test_gate_scope (62): 3/3 modules passed under a scratch
  HOME. The lanes ran `make ruff`, `make pyright`, `make vulture`, `make pylint` (exit 0); hooks 202/202 (full unit and arch, Makefile
  staged) and 135/135.
- detection.py and the hardcoded-model baseline unchanged.

## Deviations

- The test module's `from ai_kit_spec import skill_table` carries no `# noqa: E402`: the repository's ruff config flags it as an
  unused noqa (RUF100) in tests.
- `user_roles` and `table_inputs` docstrings are shorter than the plan's text (same content); the `table_inputs` test clears the
  project role file before planting an invalid user role, since a valid project value correctly wins over the user layer per key.
