---
phase: 37-shared-runner-options-and-session-ids
reviewed: 2026-11-21T21:10:00Z
reviewed_head: 8c6bb78
diff_range: "e400d38^..8c6bb78 (excluding .planning, tests/fixtures/cli_help, tests/fixtures/cross_ai_selftest_secs.json)"
depth: standard (deep on cross-ai.mjs and the runner-facing Python modules)
files_reviewed: 83
findings:
  critical: 0
  high: 0
  medium: 7
  low: 10
  info: 12
  total: 29
fixed: 9
deferred: 9
kept: 2
status: fixed_or_tracked
---

# Phase 37 code review

Two passes over `e400d38^..8c6bb78`: a `gsd-code-reviewer` pass over the whole phase diff (runner read in full around
every phase-37 block, Python as diffs, docs against code, added-line scans), and the review list carried by the run
ledger and the plan summaries, each item checked in the code by the review executor. Fixes went in as neutral-scope
`fix(37)` commits with their tests (hooks ran on each); the hosted-lane group kill went through the cross-AI lane
(pi, router-env/my-coding). The fix commits named below (6b7f23b, 96b5858) are pre-fold shas; the review checkpoint folds them into one
`fix(phase-37)` commit. Deferred items are tracked in
`.planning/todos/pending/2026-11-21-review-notes-left-open-by-phase-37.md`.

No SKILL.md changed in this review, so no judge record needs a `fixes.md`. The template changes made the project's
live runner copy (`.planning/scripts/cross-ai.mjs`) stale, which the pre-push `check-dogfood` refused; it was re-rendered
through `ensure-runner` (the 37-23 render script, dry run first) and `make check-dogfood` ends `check-dogfood: ok`.

## Findings

### MEDIUM-1: a hosted lane left its process group alive after a normal exit or a dead launcher (fixed, 96b5858)

`hostedChild.finalize` signalled the group only while the launcher shell was alive with an unchanged start time. On a
normal exit (rc written, launcher gone) or a dead launcher, a background process the CLI left in the launcher's group
kept running, while the headless path kills the group on every exit. Fix: the session id is recorded when the pid is
adopted; on every finalize the group is signalled (SIGTERM, wait unless `exit`, SIGKILL) while the verified leader lives
or any live member of that group and session remains (neither id is reused while a member lives); the fallback single-pid
kill now needs a verified live leader. A launcher already gone when its pid is first read (a fast lane) cannot be
verified; then only members of the session it made itself (session id = group id = its pid, from `setsid`) are
signalled. New fake mode `gcleft` and self-test case `host-group-left` (hosted then headless, every recorded `gc` pid
dead). The lane wrote the first version; its own new case failed on the fast-lane gap, which was then closed directly.

### MEDIUM-2: an argv-file lane printed its declared argv unredacted (fixed, 6b7f23b)

`cross-ai: argv=`, the `--print-argv` stdout line and the `rung1`/`rung2` lines printed caller-written argv raw, so a key
on that argv reached stderr and logs. Fix: `shownArgv` prints a redacted copy for an argv-file row (the spawned argv
stays raw). `argv-file-exec-ok` now plants an `--api-key` key (raw in the child, `<redacted>` in every printed line) and
`argv-file-print-argv` a `?token=` URL.

### MEDIUM-3: runner tests ran PATH `node` under a scratch HOME (fixed, 6b7f23b)

`tests/test_runner_mcp_argv.py`, `tests/test_runner_skills_argv.py`, `tests/test_runner_flags.py` and
`tests/test_curated_config_script.py` ran the bare `node` from PATH (a Volta shim here) with a temp HOME through a plain
`subprocess.run` timeout, which does not stop a shim fork chain. They now use `_real_node_executable()`. Product call
sites were checked: `--describe` and `--print-argv` children run through `run_in_own_group` (f17cb4a, inside the
`37-24` fold), `run_runner` is supervised with a deadline and a group kill, and `cli._display_argv` and
`detection._snapshot_node` only display the path.

### MEDIUM-4: the `planner-confirm-report` case no longer proved the middle-of-id prefix refusal (fixed, 6b7f23b)

37-04's lane replaced the plan's `other/fake/ok` id to pass the hardcoding guard, so nothing showed that a prefix found
inside the id is refused. The case now also requires `{ slotPrefix: 'ake/' }` to fail against `fake/ok` (allowed literal
forms only).

### MEDIUM-5: the trailer test passed on the `-` fallback (fixed, 6b7f23b)

`test_trailer_counts_unchanged` read a `--print-argv` status line, which carries `cli=- model=-`, so the cli and model
match was never exercised. It now pins the fallback and checks that a named lane must match this run's runtime and model.

### MEDIUM-6: a finalize before the first poll did not record the launcher (fixed, 6b7f23b)

When a signal arrived after the launcher wrote its pid but before the first poll, `finalize` read the pid without writing
`launcher_pid`/`launcher_pgid`/`launcher_start` into `run.json` or registering the group, so a kept record (tab close
not confirmed) named no launcher for the sweep. The poll and the finalize now share `adoptPid`.

### MEDIUM-7: `E2E_RECORDED_SECS` was stale (fixed, 96b5858)

The self-test shards were recorded at 24 s while 37-23 measured 30 to 34 s alone and the phase-37 `make test` e2e group
39 to 40 s; `tests.test_ai_kit_gsd_curated_config_matrix` was recorded at 1 s and runs about 240 s since phase 35.
Every row was refreshed from the `=== <module>: ok in <s>` lines of that run (rounded up). The matrix is now over the
60 s commit budget, so the commit stage defers it to push; the AGENTS.md push-timing paragraph still says no e2e module
is over the budget (tracked).

### LOW-1 to LOW-6 (reviewer pass; deferred, tracked in the todo)

- LOW-1: a launcher that starts after the runner abandoned it (abandon right after `pane run`, or the pid grace ran out)
  runs unsupervised; the window is milliseconds because the env file is deleted first.
- LOW-2: a failed `--describe` fact is retried on every snapshot load (up to 30 s each; the group is killed, so a stall,
  not a leak).
- LOW-3: `print_argv_lines` reports every runner refusal as "node or the runner template is missing".
- LOW-4: `session=` can echo an ignored explicit id on a call that stops before the lane starts.
- LOW-5: ai-kit-cross-ai SKILL.md's `bad_value` row names only a context label. The hosting sentence ("a `setsid`
  grandchild survives the tab close, the same limit as a headless process-group kill") stays true after MEDIUM-1.
- LOW-6: the prose skill block does not escape its `path` attribute or a body holding `</skill>`.

### LOW-7: no test pinned that an integer effort becomes a string or that `RunnerSpec` lost `ignored` (fixed, 6b7f23b)

`tests/test_runner_flags.py` now checks `{"effort": 3}` gives `effort == "3"` and `--effort 3`, and that `ignored` is not
a `RunnerSpec` field.

### LOW-8: curated-config `apply-execution` comment and rejection test (comment fixed, 6b7f23b; refusal deferred)

The D-15 comment still said claude and grok are rejected. 37-18 made `reject_execute_cli` pass no runner fact (the plan
kept it that way), so it never refuses and the old claude/grok/`Claude` rejection test was replaced by a positive claude
test, as 37 R9 requires (no seed row or closed list refuses a lane). The comment now says so. Passing the stored fact, as
`dispatch-execute` does, and restoring a refusal test is tracked.

### LOW-9: 37-08 deviations (kept)

`cursor-bracket-other-rt` exits 0 because SPEC R5's universal floor accepts a bracket for every runtime; the
`--model may precede runtime selection` comment stays for a baseline hit; `${'--model'}` in the floor-case text only
keeps the guard's flag scan off a message string. Style only.

### LOW-10: plan-text drift (kept)

`lane_effort` docstrings and the 37-16 comment differ in wording from the plan text, behaviour as planned; the
`--skill-path` control-character case reports the parser's message before the loader's (both refuse, the message names
the flag).

### INFO (checked, no change)

- 37-09 fix 4559cfa: an argv-file retry keeps its explicit id without the pin (`attemptSid` from `opts.sessionId` on the
  new and reset rungs); covered by `argv-file-read-once` (two calls, `--session=placeholder-sid-2`, no fresh session).
- Claude execute formula: unprobed by design (no real-HOME consent); the runner labels it unverified and prints the note.
  The live probe is tracked.
- `RUNNER_AHEAD_OF_MIRROR` and its `# noqa: E501`: gone with the mirror (37-18).
- 37-12: the `tests/test_lane_settings.py` guard exemptions carry non-vacuity asserts; seven golden fixtures moved from
  template version 8 to 9 with the template; the `cross_ai.py` `--codex-effort` comment went with 37-26.
- `execute_dispatch._runner_spec` passes the whole candidate as knobs: only the escalation flags and the named knobs are
  read, and a non-boolean flag is a named `LaneSettingError` (pinned by `test_non_boolean_flag_is_a_named_error`).
- `_run_plan_set` (test helper) passes `--` before key and value for a leading-dash value; every caller passes.
- 37-17 `FORMULA_LABELS` is built with `Object.fromEntries`; the behaviour test recomputes every label.
- 37-18: `route_all` reads the refresh floor before loading the snapshot, which is right because the load may now write
  the cache when it refreshes the runner fact; the `screen_execute_clis` empty refusal reason is fixed by db99848 and
  pinned by its test.
- util-linux `setsid` forks when the launcher already leads its group (a pane job does); the pid file is written by the
  forked shell (`$$`), so the runner adopts and verifies the real launcher.
- 37-25 31602d9 (inside the 37-25 fold): under an unsafe self-test root the runner falls back headless, so
  `host-run-unclear` and `host-no-pid` expect the headless run there.
- 37-22 docs match the code except LOW-5.
- Generic checks passed: no added line names grok, no machine path in source or tests, runtime Python stdlib-only, no new
  config writer (the snapshot goes through `cache_write_json`), NUL refusal in `shQuote`, `runCli` and the argv-file
  loader, env and prompt files 0600 in a 0700 run directory, deleted by the launcher and again by the runner, the typed
  line holds only the checked launcher path, and every exit path tries to close only the runner's own tab.
- The fold subject `fix(37-24): 37-24` (8c6bb78) holds two neutral `fix(37)` commits (ad5823b, f17cb4a); history
  wording is for the later compaction step.

---

_Reviewed: 2026-11-21_
_Reviewers: Claude (gsd-code-reviewer) and the phase 37 review executor_
