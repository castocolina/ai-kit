---
phase: 19-evaluation-on-claude
plan: 05
executor: orchestrator (live Claude Code session)
requirements-completed: [EVAL-03, APP-05]
product_commit: deb85b3
key-files:
  created:
    - .planning/phases/19-evaluation-on-claude/19-SMOKE.md
  modified:
    - tests/gsd_curated_eval.py (harness fixes, 3 test(19-05) commits)
    - tests/test_gsd_curated_eval.py
---

# Plan 19-05 Summary: live smoke from the claude host

The D-14 smoke ran from this live Claude Code session and passed 8/8: ai-kit inventory,
recommend and dry run (host `claude`, detected); project (a) apply, re-apply (0 writes, bytes
identical), forced failure restored (`intel.enabled` written then undone); project (b)
reconcile; the 420-check matrix on 35 agents; protected set unchanged. Evidence: `19-SMOKE.md`.

## Session
- `claude --version`: 2.1.302 (Claude Code); gsd-core 1.17.0 (project-local); product_commit `deb85b3`

## Defect fixes
- none

## Harness fixes
- 3ada8c6 `test(19-05)`: no repo-root refusal on the ai-kit dry-run step (the live smoke aborted before step 1)
- 91c243d `test(19-05)`: `plan-set` candidates in the documented value form (trusted roots; runner choices read in the product shape)
- c5033cd `test(19-05)`: live host detection instead of a forced `--host claude` (EVAL-03)

Each has a regression test proven red on the previous helper and green after; `--group unit` 42/42.

## Deviations
- The plan's acceptance names `version: 1.16.`; this checkout runs gsd-core 1.17.0 (uz's project-local
  update on 2026-10-17). The evidence records `version: 1.17.0` under the 1.16./1.17. prefix set
  verified in 19-01 (tables key-identical, full unit/e2e/arch suites green on 1.17.0).

## Environment
- none (node and gsd-core available; `~/.gsd/defaults.json` read by key path only)

## Host-managed changes
- none (`snapshot --check` printed `snapshot ok`)

## Leak check
- `ps` diff against the pre-plan pid list matched only (a) the check's own shell, whose argv contains
  the pattern, and (b) pids 864725/864727, `run-with-timeout ... pi` started 17:02 by another Claude
  session (cwd `tools-installer`, parent `run-wave.sh 20-04`); not started by this plan, left alone.
  No process started by this plan remains.
