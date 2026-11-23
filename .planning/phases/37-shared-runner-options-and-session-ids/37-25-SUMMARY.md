# 37-25 Summary: hosted transport failure paths

Status: complete in two per-task lanes (pi `router-env/my-coding`) plus one orchestrator fix, verified by the orchestrator.

## Lanes

- fix-a (Tasks 1 and 2 in one lane): `status=ok exit=0 elapsed=591s attempts=1`, commit d915d1d (hook 128/128).
- fix-b (Task 3): `status=ok exit=0 elapsed=633s attempts=1`, commit 2dfed2a (hook 128/128).
- Prompts were built from the plan's own task blocks plus anchor notes checked against 45aa34d (`tmp/run-2026-11-19/c10-notes-37-25.md`).

## Commits

- d915d1d `test(37-25): fake herdr failure switches, the signal path and the admission, pid, launcher and create failure cases`
- 2dfed2a `test(37-25): unsafe state home, overlapping hosted calls and the signal guard cases`
- 31602d9 (orchestrator fix, hook 128/128) `test(37-25): admission cases expect the headless run when the state home is unsafe (custom-tmpdir environment)`

## What was done

- Fake herdr: a state lock (`$HOME/herdr-state.lock`, 400 tries of 5 ms, removed on exit and before the self-kill) and the `FAKE_HERDR_FAIL` switches `create`, `create-lost`, `run`, `run-after`, `run-lost`, `nolaunch` (with its `nolaunch` log line) and `close`.
- Fake pi mode `killparent` (kills a shell parent so the launcher never writes `rc`; exits 3 under a node parent).
- Self-test helpers `keptRecords(c)`, `fakeTabs(c)`, plus `hostCalls(c)` and `hostSafety(calls)` (the verbs and foreign-tab checks every new case runs).
- Eleven cases: `host-signal`, `host-failed-run`, `host-run-error-started`, `host-run-unclear`, `host-no-pid`, `host-dead-launcher`, `host-overlap` (runtime); `host-create-refused`, `host-create-lost`, `host-unsafe-path`, `host-signal-guard` (logic).
- `hostedChild`: `finalize` reads the `pid` file when the poll has not seen it yet, so a signal that arrives after the launcher started but before the first 250 ms poll still kills the verified launcher group (the `host-signal` case exposed it).

## Evidence

Orchestrator re-run, `tmp/run-2026-11-19/c10-verify-37-25.sh 45aa34d 3`:

- `node --check` exit 0; every acceptance grep at its count (each new case name once; `herdr-state.lock`, `killparent:` present).
- `--self-test-list` 626 cases, 18 `host-` lines, the eleven new cases with the planned kinds.
- The eleven new cases plus the seven 37-20 host cases: `self-test ok`.
- `--print-argv` output equal to 45aa34d for 14 calls (no runtime argv change).
- Modules: runner_host_protocol, arch, arch_hardcoded_models 3/3; the eight self-test shards plus runner_e2e 9/9.
- The eleven cases with a TMPDIR that holds a space (the six-environment proof's custom-tmpdir environment): `self-test ok` after the fix below.
- No grok line; tests/fixtures/no_hardcoded_models_baseline.json and detection.py unchanged; only cross-ai.mjs changed.

## Deviations

- Plan gap (fixed by the orchestrator): the plan's live fact says `host-run-unclear` and `host-no-pid` take the `host_failed` branch under an unsafe state home, but it fixed their exit at 1 and their lane-call count at 0. Under an unsafe home the runner falls back before any herdr call and runs the lane headless once, so the run exits 0 with one `pi ok` call. The cases now expect the headless run (exit 0, ok status, one lane call, `host_failed` and no herdr log) when the self-test root is not a safe path (`hostedHere`); in this checkout they assert the hosted behaviour as written.
- `hostedChild` change above (the plan allows fixing `hostedChild` where a case shows it breaks the written behaviour).
- The six `fake/ok` failure cases are built from one small table with `.map()`; each is still one object with its own `name:` in the `cases` array.
- `host-overlap` also checks the background runner's exit code (0) besides its status line.
