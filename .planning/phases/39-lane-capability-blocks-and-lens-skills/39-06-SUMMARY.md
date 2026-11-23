# 39-06 Summary: token estimate, the window accessor and the prompt-over-window refusal

Status: complete. Commits b2f8621 (`feat(39-06): add the window accessor and the prompt-over-window refusal`, Task 1) and
0fede4d (`test(39-06): pin window edges and prove refusal reasons disjoint from the runner lists`, Tasks 2 and 3 in one lane).
Executed through two cross-AI lanes (pi router-env/my-coding), each status=ok on its first run (367 s, 211 s).

## What changed

- `prompt_guard.py`: `BYTES_PER_TOKEN = 4`, `ESTIMATE_LABEL = "estimated, judged"`, `REFUSED_EXIT = 65`, `BRACKET_SUFFIX`;
  `estimate_tokens` (ceil of UTF-8 bytes over 4); `window_for(runtime, model, env, cwd, context_form_applied)` (the live
  `[[models.context]]` override labeled `user-stated`, else `unknown` with note `context_form_applied` for an applied context form or an
  id-carried bracket suffix, else the cached catalog runtime row's `context` fact through `find_runtime_key` with a label outside
  `catalog_labels.LABELS` shown as `unknown` and the source redacted, else `unknown`; an invalid value gives note
  `catalog_value_invalid`; a malformed config raises `ConfigError`); `refusal_record` (closed reasons only); `check_window` (refuses only
  above a known window, equal passes, unknown never capped).
- `tests/test_prompt_guard.py`: `TestWindowCheck` (11 tests) and `TestRefusalDisjoint` (2 tests through the real runner's
  `--describe`; a missing node fails `setUp`, never a skip).

## Verification (run by the chunk agent)

- Acceptance greps: `BYTES_PER_TOKEN = 4` 1, `REFUSED_EXIT = 65` 1, the `window_for` signature 1, `def test_` 27,
  `read_runner_describe(NODE, str(TEMPLATE))` 2.
- `node_check.py`: node ok. Under the scratch-HOME wrapper: tests.test_prompt_guard (27), test_runner_describe (20),
  test_arch_hardcoded_models (23), test_arch (118) pass. Lanes: ruff, pyright, vulture, pylint exit 0; commit hooks passed.
- No `patch`, `Mock` or stub in the test diff; `detection.py`, the model-literal baseline and both runner copies unchanged.

## Deviations

- Comments and docstrings are shorter than the plan's texts (same meaning).
- The id-bracket check is inlined in the `if` of `window_for` instead of a `carried` local (pylint's local-variable cap).
- `# noqa: E402` on the `_real_node_executable` import omitted (ruff reports it unused, RUF100).
- Tasks 2 and 3 ran in one lane with one commit (the plan names one commit per task; the fold joins them anyway).
