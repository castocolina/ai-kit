# 39-14 Summary: the opt-in after-approval edit pass

Status: complete. Commits cc51b0a (`feat(39-14): Tracer: opt-in edit pass with a claimed record, diff summary and byte restore`,
Task 1, with the regenerated test-group listings) and 5324572 (`feat(39-14): edit pass no-pass paths, lock versus quota, accept,
owner-safe reject and the edit-lens-pass command`, Tasks 2 and 3 in one lane and one commit). Executed through two cross-AI lanes (pi
router-env/my-coding), each status=ok on its first run (579 s, 408 s).

## What changed

- `edit_pass.py` (new): off unless `[review] edit_lens_pass` `is True` (project over user); the message constants and `EDIT_PROMPT` of the
  plan; `PassSeams`/`DEFAULT_PASS_SEAMS`, `PassRequest`, `record_path` (`$XDG_STATE_HOME/ai-kit/edit-pass/<16 hex>/record.json`); the
  record claimed by `os.link` of a complete 0600 temp file in a 0700 directory, published by `os.replace`; `_state` (a running record whose
  pid is gone is `interrupted`); the `O_EXCL` decision lock; `_git_state` (HEAD and porcelain `-z`); `_approved` (R8 on the repository
  only, rejected paths skipped by name); `pick_lane` (the first configured execute lane whose `--print-argv` shows `write` `workspace` or
  `full`; per decision D7 that is a codex lane today); `run_pass` = `_preflight` + `_execute` (39-12's `compose_for_lane` with
  `lens_role="edit_lens"`, the final preview's `write` checked before the claim, one execute-role run, `locked` status read from the
  status, never the exit number, drops the record and returns 75; any other result keeps it), the diff summary, `MSG_OUTSIDE` for
  unapproved changes, `MSG_SCOPE` and the hint; `accept`; `reject` (re-validates every recorded path, checks the stored digest, never
  overwrites a file changed after the pass, restores bytes and mode, retry-safe, keeps the record while an outside change remains); the
  `edit-lens-pass` command (`--cwd`, `--files`, `--accept` | `--reject`, `--timeout`).
- `cli.py`: `edit_pass` registered beside `capability_block`.
- `tests/test_edit_pass.py` (new, 19 tests, fake run and preview seams only; no real runner); `Makefile` and `.pre-commit-config.yaml`
  list the module.

## Verification (run by the chunk agent)

- Acceptance greps: `def run_pass(req: PassRequest, seams: PassSeams) -> int:` 1, `get("edit_lens_pass") is True` 1, `os.O_EXCL` 1,
  `def test_` 19 (18 after Task 2 plus the CLI test), `returncode == 75` none, `edit_pass.register_parsers(sub)` 1,
  `def test_cli_run_accept_reject` 1.
- Under the scratch-HOME wrapper: test_edit_pass (19), test_config_status (25), test_capability_entry_points (10), test_cli_help_flags (15),
  test_arch_hardcoded_models (23), test_arch (118), test_gate_scope (62) pass. Lanes: ruff, pyright, vulture, pylint exit 0; hooks 208/208
  (Task 1, Makefile staged) and 141/141 (the curated-config matrix deferred to push). `detection.py`, the model-literal baseline and both
  runner copies unchanged.

## Deviations

- Tasks 2 and 3 ran in one lane with one commit (the plan asks one commit per task).
- `_approved` keeps the plan's `scan` parameter unused (`del scan`); a duplicate approved path is recorded once.
- A failed claim reports `MSG_RUNNING` when the existing record is still running, else `MSG_PENDING` (the plan names `MSG_PENDING` only).
- `_decision_lock` creates the record folder (mode 0700) when it is missing, so an `accept` or `reject` with nothing waiting leaves an empty
  folder under the state directory (open item for review).
- Rejection rows from 39-03's validator carry `position`; `MSG_SKIPPED` is formatted from the row's `shown` and `reason` keys.
- Test names the plan's truths and threat table cite that do not exist: `test_diff_summary_then_accept_hint` (its assertion, the diff lines
  then the hint last, is in `test_reject_restores_non_utf8_bytes`) and `test_pending_record_blocks_a_second_run` (covered by
  `test_second_pass_cannot_claim`).
- Test pin: `skill_table.skill_roots` patched to the scratch root (plan-named). No other patch beyond the plan's `DEFAULT_PASS_SEAMS`.
