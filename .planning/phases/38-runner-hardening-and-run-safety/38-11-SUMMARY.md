# 38-11 Summary: headless idle watchdog

Status: complete. Two commits through two cross-AI lanes (pi router-env/my-coding), both status=ok on their first run:
0ef29b9 (`feat(38-11): headless idle watchdog`, 244 s) and 0695ff9 (`test(38-11): idle watchdog runtime cases`, 446 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `runChild` gains the opt-in idle hook (`opts.idleMs`, one timer re-armed from the last
  child byte on `performance.now()`, a `setImmediate` re-check at expiry so a queued byte wins the tie, `opts.onIdle` may defer, finalize
  reason `idle` through the existing kill path, result field `idle`, the `{ reset, recheck }` seam for plan 38-16); `runOnce` passes
  `idleMs` and an `onIdle` that skips while a live limit hit is pending and prints the redacted fire line; `runCli` passes `idleS`, prints the
  cannot-fire note once per call against the live attempt cap, and the attempt line reads `rule=idle-watchdog` for an idle-ended attempt;
  `main` passes `idleS: idlePlan.idleS`; the header sentence replaces the old "No idle watchdog" line.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: fake pi mode `ticker` (in `STICKY_FAKE`, a euro sign split across two
  stdout writes) and eight runtime cases `idle-silent-ended`, `idle-keeps-printing`, `idle-slow-quiet-default`, `idle-off-never-fires`,
  `idle-then-resume`, `idle-loses-to-deadline`, `idle-loses-to-limit`, `idle-loses-to-signal`.

## Verification (run by the chunk agent)

- Acceptance greps: every named line once, `lastByteMs = performance.now();` 4, `lastByteMs = Date.now()` 0, `ticker` once in the fake and the
  sticky list; `--self-test-list` 641 lines, the eight new cases `runtime`.
- The eight idle cases print `self-test ok` (22 s in one run); Task 1 also with `hang`, `ladder-timeout-then-ok`, `live-limit-kill`, `ok`.
- `--print-argv` of six calls (pi, codex review, opencode with effort, `--idle-timeout default`, claude review with `--idle-timeout 30`,
  cursor with a bad value) byte-equal to the 38-10 tip (uuid normalised): this plan adds no print-argv delta.
- The eight self-test shards pass one at a time under the guard: logic 33.3, 31.9, 30.3, 31.7 s; runtime 32.6, 34.8, 35.4, 41.4 s (all under
  the 60 s commit budget; the new cases have no recorded seconds yet and weigh the median). skill_text, status_group, arch,
  arch_hardcoded_models pass. Runner diff reviewed against the plan.

## Deviations

- None in the code. The Task 2 commit touches only the sibling (no runner fix was needed).
