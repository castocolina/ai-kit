# 38-10 Summary: idle watchdog setting and planIdle

Status: complete. One commit for both tasks, 21b3b92 (`feat(38-10): idle watchdog setting and planIdle`), through one cross-AI lane
(pi router-env/my-coding), status=ok on its first run (394 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: the `--idle-timeout <seconds|default>` flag (regex before `Number`, usage error
  `--idle-timeout must be an integer from 0 to 86400 or default`), CONFIG key `idleTimeoutS` (0), `IDLE_DEFAULT_S` (900, judged, D-03 evidence
  comment), `IDLE_MAX_S`, `idleBudgetNote`, pure `planIdle(call, config, role)`, `attemptCapMs`'s fourth parameter `deadlineMs`, and in `main`
  the locals `idleBudgetMs` and `idlePlan`, the notices and the one idle line (`cross-ai: idle watchdog off` / `on timeout=<N>s`, always on
  `--print-argv`, on a real run only when on). Export list gains `IDLE_DEFAULT_S`, `IDLE_MAX_S`, `idleBudgetNote`, `planIdle`.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: logic cases `pure-idle-plan`, `pure-idle-parse`, `idle-print-off`,
  `idle-print-default`, `idle-print-config`, `idle-print-notices`.
- tests/test_ai_kit_spec.py: the CONFIG pin expects `"idleTimeoutS": 0`.

## Verification (run by the chunk agent)

- Acceptance greps: every named line once; the six cases once each; `--self-test-list` 633 lines (627 + 6), the six new cases `logic`.
- `node --check` on both files; the six cases plus `planner-status-group` and `vocab-role-alias` print `self-test ok`.
- `--print-argv` delta against 0f1a314 (pi exec, codex review, opencode exec with effort): only the one added `cross-ai: idle watchdog off`
  line, stdout and every other stderr line equal (`delta ok`).
- detection.py and the model-literal baseline unchanged. Hook 129/129.

## Deviations

- One commit for both tasks (the chunk's lane prompt) instead of one per task; the checkpoint folds a plan into one commit anyway.
- The plan's scratch `delta.py` compared the pi rung2 preview, which carries a fresh random session uuid per run, so it could never print
  `delta ok`; the orchestrator's copy normalises uuids before comparing.
- `idleBudgetNote` also joins the export list (the pure case calls it).
