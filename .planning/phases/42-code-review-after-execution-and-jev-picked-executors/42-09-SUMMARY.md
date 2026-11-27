---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 09
subsystem: ai-kit-spec-review (lane_transport, both dispatch commands), ai-kit-spec-execute-superpowers (adapter CLI, references)
tags: [transport, resume, pane, record, close-transports]
requires: [42-08]
provides:
  - "lane_transport: call_mode, lane_request, RoundStart, begin_round, end_round, _locked_update (record lock on <record>.lock, never removed)"
  - "lane_transport.pane_runner: a run_runner_tiers-shaped callable whose pane round is one runner_dispatch.run_runner call with spawn_fn=herdr_pane.pane_spawn(pane); busy, unopenable and retired panes fall back or end the round without a rerun"
  - "lane_transport.close_record and the adapter close-transports subcommand (exit 0, 1 on a failed close, 2 on a foreign or unreadable record with nothing written)"
  - "--transport-record on adapter dispatch-task and on dispatch-reviewer (default transport.json beside --lane-log, never offered a pane)"
  - "DispatchTaskRequest.session_id, ReviewerDispatchSpec.session_id; _runner_spec passes candidate session_id to the runner argv"
  - "references: dispatch-external-cli.md `## Lane transport`, the record flag on the dispatch and code-review blocks, close-transports in the fold block and the cap-stop answer"
affects: [42-10]
key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_transport.py
    - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
    - skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - skills/ai-kit-spec-execute-superpowers/references/code-review.md
    - skills/ai-kit-spec-execute-superpowers/references/fold-step.md
    - tests/test_lane_transport.py
    - tests/test_lane_settings.py
    - tests/test_adapter_single_definitions.py
    - tests/test_ai_kit_spec_superpowers.py
    - tests/test_dispatch_guidance_gates.py
decisions:
  - "Tasks 1 and 2 each ran as two lanes along their seams (functions and fields, then the CLI wiring; the pane branch, then close-transports) to stay inside the 1800 s lane limit; five commits for three tasks"
metrics:
  tasks: 3
  commits: 5
---

# Phase 42 Plan 09: lane transport wiring Summary

Both dispatch commands now choose each lane's transport under a locked per-plan record: `dispatch-task
--transport-record` (execute lanes) and `dispatch-reviewer` (code-review lanes with an explicit record, spec-review
lanes with `transport.json` beside `--lane-log`). A verified, mode-allowed session of the same runtime, model and mode
is resumed with the recorded id (`--session-id` in the runner argv) and renewed after three rounds; every round is
counted back from the runner status `session=` token. With the shipped labels nothing resumes and no pane is chosen,
so every lane is a fresh subprocess with today's argv; patched-label fixtures exercise the resume and pane paths. A pane
round is one `run_runner` call with the pane as its spawn seam. `close-transports` closes recorded panes no live round
holds, keeps failed ones, sweeps once, and runs from the fold block and the code review's cap-stop answer.

## Commits

- `35db575` feat(42-09): lane transport request, round start and locked record update (Task 1, first half)
- `6eaf742` feat(42-09): choose, resume, lock and record the lane transport in both dispatch commands (Task 1, second half)
- `28160d2` feat(42-09): pane rounds through run_runner in both dispatch commands (Task 2, first half)
- `6b3e335` feat(42-09): close the plan's recorded panes and sweep once with close-transports (Task 2, second half)
- `c4ec36f` docs(42-09): pass the transport record and close the transports at plan close (Task 3)

## Lane history

All lanes pi `router-env/my-coding` through the project runner, per-task fix-up prompts, every one `status=ok`,
coverage 1/1, first attempt:
- `42-09-fix-a1` 664 s (hook 170/170, lane-reported); `42-09-fix-a2` 892 s (hook 170/170 + 22/22 uv, lane-reported);
  `42-09-fix-b1` 490 s; `42-09-fix-b2` 305 s; `42-09-fix-c` 304 s (b1, b2 and c did not quote hook counts; b1 ran ruff,
  pylint, pyright and vulture through uv on its files, b2 and c ran the make targets).
- Hooks deferred `tests.test_ai_kit_gsd_curated_config_matrix` and `tests.test_herdr_pane_sweep_e2e` to push. I ran both
  under the guard at the clean plan HEAD `c4ec36f`: matrix 35 tests ok in 158.1 s, sweep 1 test ok, `2/2 modules passed`
  (peak 0, no kill).

## Checks (own runs)

- Task 1 verify (nine modules): lane_transport 54, lane_settings 63, adapter_executor_switch 24, lane_failure_text 32,
  lane_switch 30, lane_ping 34, jev_review 59, fold_check 18, ai_kit_spec 705, all ok at `6eaf742`.
- Task 2 verify: lane_transport 63, arch 120, herdr_pane 41, dispatch_guidance_gates 33, runner_dispatch 81,
  compose_for_lane 28 at `28160d2`; lane_transport 74, adapter_executor_switch 24 at `6b3e335`: all ok.
- Task 3 verify and the plan verification modules at `c4ec36f`: adapter_single_definitions 11, ai_kit_spec_superpowers
  210, skill_text_history 45, flow_docs 46, dispatch_guidance_gates 33, lane_settings 63, herdr_pane 41, ai_kit_spec 705,
  all ok.
- Gates at `c4ec36f`: unit+arch `211/211 modules passed` (guard peak 8, no kill); `make ruff`, `make pyright`,
  `make vulture`, `make pylint`, `make check-dogfood` exit 0 (advisory stale-digest and facts-drift lines only).
- Acceptance greps all met (one expected difference below). The pane path names no `run_round`, `read_verdict`,
  `PaneRound`, `build_runner_argv`, `child_env` or `reason_for_status`, and `runner_dispatch.run_runner(` occurs once.
- Scope from `8f84cdf`: exactly the fourteen `files_modified` paths. Added shipped lines carry no phase, decision or
  requirement id, date or `.planning` path; the hardcoded-model baseline is unchanged; no SKILL.md changed.

## Deviations

- Tasks 1 and 2 split into two lanes and two commits each (see decisions).
- The adapter cli.py holds `"--transport-record"` twice (dispatch-task and close-transports); Task 1's acceptance line
  said 1, which held at `6eaf742`, and Task 2's subcommand adds the second by the plan's own text.
- No existing `dispatch-reviewer --lane-log` test needed adapting: their reviewer rows carry no runtime, so they write
  no record and print no transport line.
- `close_record` locks through a private `_under_record_lock` with the same lock lines as `_locked_update`, because
  `_locked_update` reads through `read_record`, which would read a foreign file as empty and rewrite it.
- The lanes put the round start and seams in small helpers (`_task_round_start`, `_task_pane_kwargs`,
  `_reviewer_round_start`, `_reviewer_seams`, the pane helpers in lane_transport) to stay inside pylint's caps;
  `_locked_update` uses `contextlib.suppress(FileNotFoundError)` (ruff SIM105).
- fold-step.md: the first placeholder loop now also lists `QUOTA_PATH` and `PROJECT_KEY`, which the second loop already
  checks (redundant, harmless).

## Open items for code review

- `begin_round` rewrites a foreign file at the record path as an empty record, while `close_record` refuses one.
- `dispatch-reviewer` starts the round before reading its prompt inputs, so an input failure leaves a begin with no end.
- `_prepare_pane` reads the entry outside the lock after the busy claim (the claim excludes other runs); a renewal close
  followed by a failed open leaves the closed pane in the entry until the next round.
- `_under_record_lock` and `_locked_update` repeat the lock lines; `_locked_update` could call `_under_record_lock`.
- `test_a_lane_log_record_never_opens_a_pane` ends with a vacuous assertion (the `opened == []` check carries the proof).
