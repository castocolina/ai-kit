---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 09
subsystem: skills
tags: [jev, laya, calibration, typesafe, spike, records]

# Dependency graph
requires:
  - phase: 34-07
    provides: the skill text with the limit sentence and the `## Evidence` date (wave-5 fix)
  - phase: 34-08
    provides: the no-Zen, no-delegation guard the new text must pass
provides:
  - eval_cases.py --record saves the server identity (host, address source, version and its source, fingerprint, checkpoint revisions), the summary, the row's min_confidence and the date
  - reference.md `## Calibration how-to` and `## Shared-state spike (dated record)`
  - backends/laya.md `## Calibration record (2026-11-15, Laya fp:f46ef21b10a1)` and the limit sentence citing it
affects: [34-10 judge loop (re-judges jev-fast-decision with these records)]

# Actuals (#2632)
actuals:
  tasks: 3
  commits: 2       # 18e1253 (Task 1, executor), 9a1f654 (Task 3, orchestrator); Task 2 writes scratch only
plan_head_before: 07c7bedd909b00a410288fa7e44be53dcd186c02
plan_head_after: 9a1f654

key-files:
  created: []
  modified:
    - skills/jev-fast-decision/scripts/eval_cases.py
    - skills/jev-fast-decision/reference.md
    - skills/jev-fast-decision/backends/laya.md
    - skills/jev-fast-decision/SKILL.md
    - tests/test_jev_fast_decision.py

key-decisions:
  - "Calibration ran on the owner's Laya at the default address 127.0.0.1: version not exposed (no [jev] laya_version), fingerprint f46ef21b10a1, checkpoint english 55cf4c4ebb4e; n 32, accuracy 0.56, confident-answer accuracy 50%, fallback rate 0.69; --calibrate proposed null, so min_confidence stays 0.7 and jev_review.py is untouched."
  - "The shared-state spike ran on TypeSafe jev-1.14.0 under the owner's recorded consent (2026-10-14) and environment key: merged 8/8 (mean top 0.95), shared 8/8 (mean top 0.87), five requests. Eight questions is indicative only."
  - "SKILL.md keeps its limit sentence shape (32 cases, 50%) and carries the new date only in its trailing `## Evidence` (tests/test_skill_text_history.py); the how-to's step 4 says so. Body 499 words."
  - "The spike record notes that both shapes send choice options in sorted key order (the client encodes with sorted keys), a finding of the Task 1 executor."

requirements-completed: [JEV-03, JEV-11]

# Metrics
duration: about 50 minutes (Task 1 dispatch to the Task 3 commit)
completed: 2026-11-15
status: complete
---

# Phase 34 Plan 09: Laya calibration and the shared-state spike

**The owner's Laya was measured on the version it runs (fingerprint f46ef21b10a1): 50% of its
confident answers were right over 32 cases, so the limit sentence stands with a new date; the
TypeSafe shared-state spike answered 8 of 8 in both shapes.**

## Task Commits

1. **Task 1 (executor): the calibration record names its server; the how-to; the live driver** -
   `18e1253` (feat). eval_cases.py `_server_fields`; `test_eval_record_carries_server_fields`
   (RED `KeyError: 'server'`, then green); reference.md `## Calibration how-to`; the laya.md
   pointer; scratch `tmp/p34/09/live.py` with `selftest: ok`.
2. **Task 2 (orchestrator checkpoint): live runs in the main checkout** - no commit.
   `live.py check`: `laya: 127.0.0.1 (default)`, `laya usable: yes`,
   `typesafe consent: 2026-10-14`, `typesafe key source: env:TYPESAFE_API_KEY`.
   `live.py calibrate` and `live.py spike` wrote `tmp/p34/09/calibration.json` (run true) and
   `tmp/p34/09/spike.json` (run true); neither printed `real config changed`; the real ai-kit
   config, the jev state folder, `.aikit/` and `.planning/config.json` showed 0 changes; no
   tracked file changed.
3. **Task 3 (orchestrator): records, limit sentences, doc tests** - `9a1f654` (docs).

## Verification

- `python3 tools/run_unittest_parallel.py tests.test_jev_fast_decision tests.test_jev_fast_decision_guard tests.test_jev_config tests.test_jev_learn tests.test_skill_text_history`: 5/5 modules passed (jev_fast_decision 236 tests).
- `python3 -m unittest` of TestDocs `test_doc_body_words`, `test_doc_calibration_record`, `test_doc_spike_record`, `test_doc_limit_sentence_in_skill_and_laya_backend`: OK (4 tests).
- `make ruff`, `make pylint`: Passed. Commit hooks: 40/40 modules passed.

## Deviations

- **[Orchestrator] Tasks 2 and 3 ran inline in the main checkout** after Task 1 merged, not in the
  executor's worktree: `live.py`'s ROOT must be the checkout that holds the merged Task 1 code, and
  the run rule allows one executor per plan. `live.py` was copied out of the executor's worktree
  before the merge.
- **[Rule 3] SKILL.md date placement:** the plan puts the date on SKILL.md's limit sentence; the
  wave-5 fix keeps it in the trailing `## Evidence` (the main-flow no-date rule), so Task 3 updated
  the Evidence date and `test_doc_calibration_record` checks it there.
- **[Executor, Task 1] selftest stub:** the client encodes choice criteria with sorted keys, so the
  plan's "first option" stub gave 4 of 8; the selftest stub answers each choice with its expected
  option and still proves 7 of 8, 5 POSTs.

## Self-Check: PASSED

- backends/laya.md holds `## Calibration record (2026-11-15, Laya fp:f46ef21b10a1)`; reference.md
  holds `## Shared-state spike (dated record)`; commits 18e1253 and 9a1f654 are on the branch.
