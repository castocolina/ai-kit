# 39-03 Summary: the embedded-value validator, the refusal reasons and the control-character fixture

Status: complete. Commits 90cf3a7 (`feat(39-03): add the prompt value validator and refusal reasons`, Task 1) and d320997
(`test(39-03): pin the shared control-character fixture and validator edges`, Task 2). Executed through two cross-AI lanes
(pi router-env/my-coding), one per task, each status=ok on its first run (433 s and 211 s).

## What changed

- `skills/ai-kit-spec-review/ai_kit_spec/prompt_guard.py`: `REFUSAL_REASONS` (`prompt_over_window`, `value_control_char`,
  `path_outside_roots`, `path_unresolvable`), `is_control_char` (Cc, Zl, Zp and the listed format points, no normalization),
  `escape_value` (display only), `repo_root(cwd, run_fn)` (git top level through `gsd_tools.project_root({}, ...)`, else the real path),
  `validate_values(values, repo, skill_roots, extra_roots=(), base=None)` returning every rejection `{position, reason, shown}` in input
  order; `shown` redacts secret shapes before escaping; a value is never rewritten; a not-yet-existing path resolves non-strictly.
- `tests/fixtures/prompt_control_chars.json` (87 rejected, 15 accepted pairs, written by the plan's generator from the SPEC ranges).
- `tests/test_prompt_guard.py`: `TestValidateValues` (the eight SPEC R8 fixtures and nine edges), `TestControlCharFixture` (fixture
  matches the rule, exhaustive over U+0000..U+10FFFF, escape), `TestRepoRoot` (fakes only); the unit listings in `Makefile` and
  `.pre-commit-config.yaml` gain the module.

## Verification (run by the chunk agent)

- Acceptance greps: `REFUSAL_REASONS = (` 1, the `project_root({}, cwd, run_fn)` call 1, Makefile listing 1, 102 fixture pairs,
  14 tests; the test source is ASCII only.
- tests.test_prompt_guard (14), tests.test_arch_hardcoded_models (23), tests.test_gate_scope (62), tests.test_secret_shapes (27): pass
  under a scratch HOME. Lanes: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0; hooks 203/203 (full unit and arch) and
  3/3.
- detection.py and the model baseline unchanged.

## Deviations

- No `# noqa: E402` on the test import (RUF100 flags it as unused in tests); docstrings shorter than the plan's text (same content).
- `test_extra_roots_cover_their_call_only` annotates its value list as `list[tuple[str, object]]` (pyright list invariance).
