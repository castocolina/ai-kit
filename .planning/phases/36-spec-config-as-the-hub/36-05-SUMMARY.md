---
phase: 36-spec-config-as-the-hub
plan: 05
subsystem: spec-config
tags: [lane-effort, effort-forms, write-checks]

requires: [36-01]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/lane_effort.py: effort_form, effort_problem, effort_source_label, listed_ids, offered_levels, write_problems, has_effort_path, EffortForm, LevelOffer and the runner mirrors RUNNER_CODEX_EFFORTS and RUNNER_PI_LEVELS"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_effort.py
  modified:
    - tests/test_lane_effort.py

requirements-completed: [HUB-05]

executor: "cross-AI lane: pi router-env/my-coding, two runs: run 1 (187 s, AIKIT-XAI status=ok exit=0, drafted both files, no commit, reported two defects); fix-up run (528 s, status=ok exit=0 attempts=1 cycles=0) fixed both, finished verification and committed"
---

# Phase 36 Plan 05: lane_effort

One commit, `f3d1da2 feat(36-05): lane_effort turns a lane effort into each runtime's form` (pre-fold; 2 files, +520 -4); the commit hook ran 115/115 modules green.

## Accomplishments

- New pure module `lane_effort.py`: one `effort_form` per runtime (codex flag, pi `:level`, opencode `#level`, cursor bracket, `ignored:` line for every other case), `effort_problem` (write-time check of `effort` and `effort_source`), `offered_levels` (catalog first, then runtimes snapshot, host order or canonical order, runner-refused levels with reasons) and `write_problems`.
- `tests/test_lane_effort.py`: 24 tests (TestEffortForm 9, TestEffortProblem 5, TestOfferedLevels 5, TestWriteProblems 5); the runner-set mirror is pinned against the template text.

## Deviations and notes

- Plan inconsistency, decided by the orchestrator (ledger): the plan's `_shown` order (remove control characters, then redact) cannot satisfy its own test for the effort `"x\x07" + key`, because the redactor's boundary rule needs a non-word character before the key. `_shown` now redacts, removes control characters, then redacts again (this also catches a key split by a control character); one test assertion added for the split case. The template test wraps the str path of `resolve_cross_ai_template_path()` in `pathlib.Path`.
- No file outside the plan's two paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_lane_effort tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 3/3 modules (24, 14 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on `lane_effort.py`: Passed. Read the whole `lane_effort.py` against the plan's rules.
- Real-config audit (marker-c2-p36-w2): host and other-agent files only plus session logs.

## Self-Check: PASSED
