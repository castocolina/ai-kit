# 39-08 Summary: `classify-skills` with jev as advisory, `confirm-skill-role`, the shared config lock

Status: complete. Commits 6f3854f (`feat(39-08): classify-skills lists unsorted skills with advisory jev proposals`, Task 1),
45b1b82 (`feat(39-08): confirm-skill-role writes one owner-confirmed role under the shared config lock`, Task 2) and 89580ee
(`test(39-08): sorter edges and the plan gates`, Task 3). Executed through three cross-AI lanes (pi router-env/my-coding), one per
task, each status=ok on its first run (559 s, 337 s, 177 s).

## What changed

- `skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py` (new): `PROPOSABLE`, `NONE_KEY`, `ROLE_QUESTION`, `ROLE_HINTS`, `Proposal`,
  `unsorted_skills`, `not_addressable`, `role_item` (name plus at most 300 printable, redacted description characters; a SKILL.md whose
  real path leaves every scanned root sends the name alone), `classify` (read only; jev found at run time; only a confident role answer
  proposes), `confirm_role` (read-splice-publish under the shared folder lock; a linked `.aikit` folder or a linked or escaping project
  file is a ConfigError), `cmd_classify_skills`, `cmd_confirm_skill_role`, `register_parsers`, `COMMANDS`.
- `jev_names.ask_items` gains `strict=False`: with `strict`, a non-zero client exit proposes nothing even with a valid-looking stdout.
- `config_io.cfg_folder_lock(path)` (exclusive `fcntl.flock` on the config's folder, no lock file); `cfg_write_toml` (render-toml)
  now runs inside it, so render-toml and confirm-skill-role cannot lose each other's write (orchestrator decision).
- `cli.py`: `skill_classify` imported, parsers registered, commands added.
- Tests: `tests/test_skill_table.py` `TestClassifyTracer`, `TestConfirmRole`, `TestClassifyEdges` (61 tests in the module);
  `tests/test_config_role_write.py` `TestConfigFolderLock`.

## Verification (run by the chunk agent)

- Acceptance greps: `def classify(...)` 1, cli wiring 2, `["mcp"]` reads 0, the `set_table` call 1, writes in skill_table.py 0,
  the three test classes 3; the lock helper and its use in `cfg_write_toml` 2, its use in `confirm_role` 1.
- tests.test_skill_table (61), tests.test_catalog_jev_names (13), tests.test_config_role_write (16), tests.test_arch (118),
  tests.test_ai_kit_spec (688), tests.test_arch_hardcoded_models (23): pass with `report check: ok`. Lanes: ruff, pyright, vulture,
  pylint exit 0; hooks 136/136 each.
- detection.py, the model baseline and the live runner copy unchanged.

## Deviations

- pylint `max-args = 5`: `ask_items` gained only `strict`; the plan's `cwd` parameter is replaced by binding the project into the
  runner at the call site (`functools.partial(run, cwd=cwd)`), so jev still starts in the scanned project and the fake records it.
- `test_secret_in_description_redacted_and_unaddressable_listed` asserts both not-offered rows in scan order (the secret-shaped
  directory and `lens.x`); the plan text listed only `lens.x` while also creating the secret-shaped directory.
- The description is redacted before and after the control-character removal; the splice and publish are two statements (line length).
- An extra Task 1 test `test_failed_client_stdout_is_not_a_proposal` beside the planned Task 3 one.
