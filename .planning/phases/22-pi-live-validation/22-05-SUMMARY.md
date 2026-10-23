---
phase: 22-pi-live-validation
plan: 05
subsystem: testing
tags: [pi, smoke, snapshots, curated-config]
requires:
  - phase: 22-pi-live-validation
    provides: Pi inventory, recommendation flow, matrix harness, and request hook probe
provides:
  - Pi smoke path with generated-path reporting, project-local hook verification, seeded provider, and protected-home coverage
  - Headless pi smoke evidence with R7 fixes ledger and owner-only acceptance explicitly pending
affects: [22-06, 22-07, curated-config]
actuals:
  tokens: 4900
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [pi hook-only post-apply validation, names-and-hashes protected snapshots]
key-files:
  created: [.planning/phases/22-pi-live-validation/22-SMOKE-PI.md]
  modified: [tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py]
key-decisions:
  - "Pi's project-local smoke chain checks only agent-file absence and the installed hook's wire value; tier agreement remains the matrix's responsibility."
  - "Snapshot protects pi settings/trust and selected agent trees, excluding credentials, model stores and sessions entirely."
  - "Headless evidence does not satisfy the owner's interactive R4 acceptance."
requirements-completed: [EVAL-08, APP-05]
coverage:
  - id: D1
    description: Pi smoke harness checks installer-generated paths, absence of agent files, and the project's installed hook against the plan while using the seeded session provider.
    requirement: EVAL-08
    verification:
      - kind: unit
        ref: tests.test_gsd_curated_eval#TestSmoke
        status: pass
      - kind: e2e
        ref: scratch-HOME `smoke --host pi` evidence: 10 steps, 420 matrix checks, 5/5 hook probes
        status: pass
    human_judgment: false
  - id: D2
    description: Pi settings/trust and selected agent trees are guarded without snapshotting credentials, model stores or sessions.
    requirement: EVAL-08
    verification:
      - kind: unit
        ref: tests.test_gsd_curated_eval#TestSnapshot
        status: pass
      - kind: other
        ref: real-home snapshot --out/--check guard pair
        status: pass
    human_judgment: false
  - id: D3
    description: Headless evidence records the harness run and fixes ledger; interactive R4 remains owner-only.
    requirement: EVAL-08
    verification:
      - kind: other
        ref: 22-SMOKE-PI.md single green headless verdict and owner pending row
        status: pass
    human_judgment: true
    rationale: The required interactive pi session is an owner-only action and is explicitly left pending.
metrics:
  duration: 75min
  completed: 2026-10-23
  status: complete
orchestrator_verify: "VERIFY 22-05: 2/2 passed (cmd 1 after its full-output grep fix; cmd 2 after the scratch smoke dir was removed, as Task 2 intends)"
---

# Phase 22 Plan 05: Pi headless smoke and protected snapshot Summary

**The curated-config smoke now runs on pi with a project-local hook assertion, pi-specific generated paths, seeded provider context, and credential-safe protected-home checks.**

## Performance

- **Duration:** approximately 75 min
- **Started:** 2026-10-23
- **Completed:** 2026-10-23
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added pi snapshot coverage for settings/trust and the agent, extension, skill, and gsd-core trees while intentionally excluding credential, model-store, and session files.
- Added pi install-path reporting and the post-apply chain that asserts no generated GSD agent files and checks the project extension's wire model against `pi.sonnet`; no per-agent loop duplicates the matrix checks.
- Seeded `PI_PROVIDER` for pi smoke inventory, surfaced matrix hook-probe counts, and recorded ten passing headless smoke steps plus the R7 fixes ledger.

## Task Commits

1. **Task 1: pi harness and headless smoke** - `4eb8863`
2. **Task 2: headless evidence and R7 ledger** - included with this summary commit.

## Files Created/Modified

- `tests/gsd_curated_eval.py` - pi snapshot protection, generated paths, hook-only chain, seeded provider and evidence rendering.
- `tests/test_gsd_curated_eval.py` - hermetic pi snapshot, chain, generated-path, host-rewrite and provider tests.
- `.planning/phases/22-pi-live-validation/22-SMOKE-PI.md` - scratch-HOME evidence and fixes ledger.

## Decisions Made

- The per-project pi check verifies the hook's project-specific effect and agent-file absence only; the matrix already owns the independent per-agent tier and cached-hook checks.
- `settings.json` and `trust.json` are strict by default but can be individually exempted for the owner's interactive run; credentials, models and session data are never traversed.
- Headless harness verification is not the R4 interactive acceptance, which remains `not run (owner)`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Deleted tests

None.

## Verification

- `python3 -m unittest tests.test_gsd_curated_eval` — 314 tests passed.
- Scratch pi smoke — exit 0; all 10 steps passed, including `matrix ran: 420 checks, 5 hook probes`, hook probes 5/5, no agent files, second apply unchanged with one backup, and forced-failure restore.
- Real-home snapshot guard output: `snapshot ok`; scratch HOME and pi agent directory were verified under `/tmp`, owned by the current user, then removed (`test ! -e` passed).
- `python3 tests/gsd_curated_eval.py secret-scan .planning/phases/22-pi-live-validation/22-SMOKE-PI.md` — clean; `$HOME` grep found nothing.
- Leak checks printed nothing for the smoke/resolve-model/installer pattern and the detached-grandchild pattern.
- `uv run ruff check tools skills tests`, `uv run pyright`, `uv run vulture`, `make test`, and `make validate` — passed.

Smoke log's last five lines:

```text
smoke evidence written to <worktree>/tmp/p22/smoke/pi-smoke.md
scratch work dir: /tmp/smoke-2qkdlsvk (deleted)
smoke exit=0
```

(The log contains three final lines; the complete ending is quoted.)

Real-home check output:

```text
snapshot ok
```

Scratch-dir guard result: verified path under `/tmp`, real directory, not a symlink, current-user owner; removed after snapshot guard; absent afterwards.

Leak-check command:

```text
ps -eo pid=,args= | awk 'NR==FNR{b[$1];next} !($1 in b) && /gsd_curated_eval[.]py smoke|[ \/]gsd-tools[.]cjs resolve-model|install[.]js --pi/' tmp/pids-22-05.before -
```

Printed nothing. The separate `gc-late|node -e while` scan also printed nothing.

## Next Phase Readiness

The owner's S1-S5 interactive run and live-provider work remain pending as specified; the headless smoke and matrix harness are ready for that kit.

---
*Phase: 22-pi-live-validation*
*Completed: 2026-10-23*
