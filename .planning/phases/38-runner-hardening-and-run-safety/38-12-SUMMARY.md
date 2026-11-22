# 38-12 Summary: finding list and status-line check group

Status: complete. One commit for both tasks, 05b2af9 (`feat(38-12): finding list and status-line check group`), through one cross-AI lane
(pi router-env/my-coding), status=ok on its first run (461 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: the closed ordered `FINDING_CODES`, `FINDING_ITEMS_MAX` (10), module state `liveCheck`
  (reset in `main`), `addFinding` (refuses a code outside the list), `findingText` (redact, strip C0/DEL/C1 and U+2028/U+2029, redact again),
  `findingDetail` (dedupe, sort, cap at 10 then `(+N more)`, empty gives `-`), `findingLines`, `checkGroup`; `finish` prints the finding lines
  before the status line and appends `coverage=<c/p|n/a|-> findings=<codes|->` after `escalate=` (two separate tries; the `statusGroup`
  fallback is unchanged). Export list gains `FINDING_CODES`, `addFinding`, `checkGroup`, `findingDetail`, `findingLines`, `liveCheck`.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: `STATUS_HEAD_RE` gains the optional check group (retry group moves to
  `parts[6]`), `statusTail` returns `coverage` and `findings`, `status-group-before-retry` expects the group, and logic cases
  `check-group-no-spawn`, `pure-finding-format`, `pure-status-head-re`, `finding-lines-through-finish`; `pathToFileURL` imported.
- tests/test_runner_status_group.py: `CHECK_KEYS`, `TestStatusGroup.test_check_group_follows_escalate`, `TestCheckGroupLine` (two tests).

## Verification (run by the chunk agent)

- Acceptance greps: every named line once, the `statusGroup` fallback line still once, regex group and `parts[5], parts[6]]` once, the four
  cases once, the three Python tests once; `--self-test-list` 645 lines, the four new cases `logic`.
- Nine cases (the four new ones, `planner-status-group`, `status-group-before-retry`, `backoff-deadline`, `ladder-timeout-no-budget`,
  `vocab-role-alias`) print `self-test ok`.
- `--print-argv` delta against the 38-11 tip (pi exec, codex review, a usage error): only ` coverage=- findings=-` appended to the status
  line, every other line and stdout equal (`delta ok`).
- detection.py and the model-literal baseline unchanged; hook 129/129; runner, sibling and test diffs reviewed against the plan.
  Wave gates: see the ledger (c38-3, waves 5-7).

## Deviations

- One commit for both tasks (the chunk's lane prompt) instead of one per task.
- The plan's scratch `delta.py` compared the pi rung2 preview with its random session uuid; the orchestrator's copy normalises uuids.
- `finding-lines-through-finish` also asserts the child exits 0 (stricter than the plan, passes).
