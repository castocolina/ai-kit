# 39-07 Summary: skill and MCP flags passed to the runner, lane facts parsed

Status: complete. Commits f63988f (`feat(39-07): pass lens skills and the MCP file to the runner and read the lane facts`, Task 1)
and 3582c1a (`test(39-07): pin lane facts and the skill flag order`, Task 2). Executed through two cross-AI lanes
(pi router-env/my-coding), one per task, each status=ok on its first run (517 s and 205 s).

## What changed

- `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py`: `RunnerSpec.skill_paths`, `skill_names`, `mcp_config`; `runner_flags`
  appends `--skill-name <n> --skill-path <dir>` per pair (`zip(..., strict=True)`) and then `--mcp-config <file>` after every existing
  flag; `SETTING_LINE_RE` names the value and gains the optional ` form=` group; `preview_setting` keeps its 2-tuple.
- `skills/ai-kit-spec-review/ai_kit_spec/capability_block.py` (new, part 1): `LaneFacts`, `unknown_facts`, `lane_facts`,
  `context_form_applied`, the closed value lists, the three reason constants; a None preview, a missing, duplicated or malformed
  capabilities line gives every capability `unknown` with the reason as its label; setting and skill-block lines are read whenever
  lines exist.
- Tests: `tests/test_runner_preview.py` `TestLaneFactsFromTheRunner` (real node: pi path form, copilot prose block sha256 and the MCP
  file applied as `call_file`) and `TestLaneFacts` (no preview, missing line, 15 malformed lines, well-formed normalization, setting
  and block lines); `tests/test_runner_flags.py` `TestSkillFlags` and the shared `golden(runtime)` helper.

## Verification (run by the chunk agent)

- Acceptance greps: the `zip` line 1, the `form` group 1, the `value` group 1, `def lane_facts` 1, `TestSkillFlags` 1, `TestLaneFacts(` 1,
  16 tests in test_runner_preview.
- tests.test_runner_preview (16), tests.test_runner_flags (19), tests.test_ai_kit_spec_runner_dispatch (80), tests.test_effort_probe (23),
  tests.test_arch_hardcoded_models (23), tests.test_arch (118): pass. Lanes: ruff, pyright, vulture, pylint exit 0; hooks 136/136 and 4/4.
- detection.py, the model baseline, the runner template (since 39-05) and the live runner copy unchanged by this plan.

## Deviations

- The module docstring of capability_block.py is wrapped over two paragraphs (line-length limit); its text reads split
  ("... --print-argv lines," / "and the block built from them ..."): a wording item for 39-10, which extends the module.
- Task 2's expected flag list uses iterable unpacking instead of list concatenation (ruff RUF005); the asserted equality is unchanged.
