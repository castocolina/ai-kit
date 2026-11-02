# 19-03 Summary: D-12 grader for the pressure harness

## Delivered

- `tests/gsd_curated_eval.py`: scripted checks for B, C, D and E. Subcommands `grade`
  (`--trimmed-out`, `--record-out`), `secret-scan` (with a canary self-check) and `cells`;
  `digest --check` gained `--section` and `--column` refinement.
- `tests/test_gsd_curated_eval.py`: `TestGrader`, `TestScenarioPredicates`, `TestSecretScan`,
  `TestEvidenceTable`, `TestScenarioFiles`. Every check has a passing case and a failing
  counterpart built from one wrong input.

## Verified

- `python3 -m unittest tests.test_gsd_curated_eval`: 209 tests pass (includes `test_arch`).
- `python3 tools/run_unittest_parallel.py --group unit`: 42/42 modules. `--group arch`: 1/1.
- The five cycle-3 v1-hook tests pass by name: `test_v1_hook_overrides_config_positive`,
  `test_v1_hook_model_override_negative`, `test_v1_hook_prefer_override_negative`,
  `test_non_runner_hook_fails`, `test_effective_exec_mirrors_runner_merge`.
- `secret-scan tests/fixtures` exits 0. A planted `token: sk-` line under a temp dir exits 1.
- `digest` is unchanged: `551234cc5f4f55cc`.
- ruff check and format clean; pyright 0 errors on both modules.
- `grade B` on a synthetic run dir exits 0; `--trimmed-out` and `--record-out` contain no run,
  home or worktree paths.
- Leak check `[g]sd_curated_eval` prints nothing outside `tests/` and `tmp/`.

## Changed outside the grader (19-02 eval files)

The grader is the source of truth for check kinds. Thirteen `kind` labels in the four eval
files were aligned to it; check names and gating were not touched:

- 01: `nothing_dropped_silently`, `ensure_runner_disclosed` → outcome
- 02: `needs_choice_present`, `router_wins_execution` → workflow
- 03: `nothing_dropped_silently` → outcome
- 04: `apply_after_scripted_answer`, `asks_despite_pressure`, `review_pass_shown` → outcome

`TestScenarioFiles` pins names, kinds and gating against the grader, so the two cannot drift.

## Fixed during execution

- `check_digests` gained `sections` and `columns` (section-aware digest check).
- `_position` returns a sentinel (`len(evs)`) for a missing point so ordering comparisons type
  check; `text_before` keeps the explicit `None → ""` guard so a missing write cannot pass a
  prose check vacuously (a regression the test suite caught).
- `if __name__ == "__main__"` moved to the end of `tests/test_gsd_curated_eval.py` (test_arch
  rule 12).

## Open / not verified here

- The orchestrator-run `make` gates (`make validate`, `make test`) were not run by the executor.
- No `claude` runs, no apply or ensure-runner against the repo, no push.
