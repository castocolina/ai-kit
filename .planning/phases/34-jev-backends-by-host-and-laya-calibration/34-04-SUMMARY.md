---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 04
subsystem: jev-fast-decision
tags: [jev, config, session-override, knob, probe, ladder, precompact, judge-loop]

# Dependency graph
requires:
  - phase: 34-jev-backends-by-host-and-laya-calibration
    provides: "jev_config.knob (plan 34-01) and the [jev] URL/consent client (plan 34-02), both merged in the base"
provides:
  - "[jev] enabled as the jev knob: GSD_PATH_JEV as a session override both ways, then project over user, then on by default"
  - "Probe report carries settings (enabled, enabled_source, problem, notice) and lists enabled in needs_answer while unanswered"
  - "No internal caller forces GSD_PATH_JEV: ladder child env, judge_loop ask_jev and the PreCompact client env forward only the user's own value"
affects: [34-07 (docs owner for reference.md and backends/laya.md), 34-08 (JEV-07 requirement amendment)]

# Actuals (#2632): same estimateTokens scale (chars/4 over the realized diff)
actuals:
  tokens: 7246
  tasks: 3
  commits: 4
# Measured from the spawn base (git rev-list --count base..HEAD), not narrated.
plan_head_before: 01d8509165a7d5d920f71638bc60a2bac6fc4e10
plan_head_after: 728983c011729bae6570eea18d83dc2fc9aa880f

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Knob gate read per call through one seam (_knob), before stdin or any socket"
    - "Control variables scrubbed from child envs; the user's own GSD_PATH_JEV is the single forwarded exception"

key-files:
  created: []
  modified:
    - skills/jev-fast-decision/scripts/jev_review.py
    - skills/jev-fast-decision/scripts/jev_ladder.py
    - skills/jev-fast-decision/scripts/eval_cases.py
    - tools/judge_loop.py
    - tools/hooks/precompact_core.py
    - tests/test_jev_config.py
    - tests/test_jev_fast_decision.py
    - tests/test_judge_loop.py
    - tests/test_precompact_core.py
    - tests/test_claude_precompact.py

key-decisions:
  - "The knob follows Resolved Open Question 1: a non-empty GSD_PATH_JEV wins both ways, then [jev] enabled (project over user), then on by default with needs_answer enabled"
  - "The client's _KILL_SWITCH constant is removed; _knob() is the single gate for screen and _send"
  - "With the knob off, --probe returns status disabled with settings and needs_answer [] without probing any row"
  - "child_env, ask_jev and client_env forward GSD_PATH_JEV only when set and non-empty; every other GSD_PATH_JEV* and JEV_* variable stays scrubbed (T-34-13)"
  - "The unanswered-knob notice is one fixed string (_ENABLED_NOTICE) in the probe settings, asked once through the agent"

patterns-established:
  - "Consumer knob-off outcome is pinned by test_ladder_knob_off_is_own_reasoning: decided_by own_reasoning, no own_reasoning choice column, detect status disabled with backends {}"

requirements-completed: [JEV-07]

# Metrics
duration: "not recorded (no plan start timestamp was captured in this worktree run)"
completed: 2026-11-15
status: complete

coverage:
  - id: D1
    description: "[jev] enabled and GSD_PATH_JEV decide the knob: session wins both ways, project over user, absent is on and asked once, broken config fails closed"
    requirement: "JEV-07"
    verification:
      - kind: unit
        ref: "tests/test_jev_config.py#test_knob_off_in_config_disables_probe_and_screen"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#test_session_switch_wins_both_ways"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#test_knob_absent_is_on_and_asked_once"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#test_project_knob_wins_over_user"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#test_broken_config_fails_closed_with_a_reason"
        status: pass
    human_judgment: false
  - id: D2
    description: "Internal callers stop forcing GSD_PATH_JEV: ladder child env, judge_loop ask_jev and the PreCompact client env forward only the user's own value"
    requirement: "JEV-07"
    verification:
      - kind: unit
        ref: "tests/test_jev_fast_decision.py#test_ladder_forwards_only_the_session_switch"
        status: pass
      - kind: unit
        ref: "tests/test_judge_loop.py#test_ask_jev_sends_one_item_with_the_fixed_environment"
        status: pass
      - kind: unit
        ref: "tests/test_precompact_core.py#test_client_env_forwards_only_the_session_switch"
        status: pass
      - kind: unit
        ref: "tests/test_claude_precompact.py#test_tracer_precompact_then_inject"
        status: pass
    human_judgment: false
  - id: D3
    description: "With the knob off, each consumer takes its no-jev outcome (ladder own_reasoning, judge own_reasoning, PreCompact no request)"
    requirement: "JEV-07"
    verification:
      - kind: unit
        ref: "tests/test_jev_config.py#test_ladder_knob_off_is_own_reasoning"
        status: pass
      - kind: unit
        ref: "tests/test_judge_loop.py#test_ask_jev_knob_off_returns_own_reasoning"
        status: pass
      - kind: unit
        ref: "tests/test_precompact_core.py#test_session_switch_off_turns_the_hook_off"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dead non_loopback_url key source removed from the ladder allowlist (coordinator item)"
    verification:
      - kind: unit
        ref: "tests/test_jev_fast_decision.py"
        status: pass
    human_judgment: false
---

# Phase 34 Plan 04: [jev] enabled as the jev knob, GSD_PATH_JEV as a two-way session override, no caller forces jev on

**[jev] enabled and GSD_PATH_JEV now decide whether jev runs (session wins both ways, then project over user, then on by default), and the ladder, judge loop and PreCompact hook no longer force it on**

## Performance

- **Duration:** not recorded
- **Completed:** 2026-11-15
- **Tasks:** 3 plan tasks plus 1 coordinator-requested item
- **Files modified:** 10

## Accomplishments

- `jev_review.py` gates `screen` and `_send` on `_knob()`, which reads `jev_config.knob` (session variable, then `[jev] enabled`, then default on). The `_KILL_SWITCH` constant is gone.
- With the knob off, `--probe` reports `status: disabled` with `settings` and probes no backend; `screen` returns `{"status": "disabled"}` before stdin is read.
- With the knob on, the probe report carries `settings` (`enabled`, `enabled_source`, `problem` when a config is broken, `notice` while unanswered) and lists `enabled` in `needs_answer` until the user answers.
- `child_env`, `judge_loop.ask_jev` and `precompact_core.client_env` no longer force `GSD_PATH_JEV=1`; they forward the parent's value only when it is set and non-empty.
- Each consumer's knob-off outcome is pinned by a test (ladder own_reasoning, judge own_reasoning, PreCompact zero requests, `detect` status disabled with `backends {}`).

## Task Commits

1. **Task 1: [jev] enabled = false switches the probe and every call off** - `aaf1cf1` (feat)
2. **Task 2: knob order holds, ladder forwards only the session switch** - `3fbe44b` (feat, tests and code in one commit; RED observed locally first)
3. **Task 3: judge_loop and the PreCompact hook stop forcing jev on** - `91d201c` (fix, tests and code in one commit; RED observed locally first)
4. **Coordinator item: drop the dead non_loopback_url key source** - `728983c` (fix)

**Plan metadata:** committed in the SUMMARY commit that follows this file.

## Files Created/Modified

- `skills/jev-fast-decision/scripts/jev_review.py` - `_knob`, `_settings`, `_ENABLED_NOTICE`; knob gate in `probe_report`, `_send`, `screen`; `_KILL_SWITCH` removed
- `skills/jev-fast-decision/scripts/jev_ladder.py` - `child_env` forwards the session switch only; `_KEY_SOURCES` loses `non_loopback_url`
- `skills/jev-fast-decision/scripts/eval_cases.py` - docstring describes the knob
- `tools/judge_loop.py` - `ask_jev` uses the parent env as it is
- `tools/hooks/precompact_core.py` - `client_env` forwards the session switch only
- `tests/test_jev_config.py` - knob tests through the client and the ladder; imports shared helpers from `tests.test_jev_fast_decision`
- `tests/test_jev_fast_decision.py` - session-off tests pin `GSD_PATH_JEV=0`; `test_probe_works_with_the_switch_unset` (renamed); child env tests updated; `test_ladder_forwards_only_the_session_switch`
- `tests/test_judge_loop.py` - `ask_jev` env cases and `test_ask_jev_knob_off_returns_own_reasoning` (imports `closed_port_url`)
- `tests/test_precompact_core.py` - loopback env no longer forces the switch; `test_session_switch_off_turns_the_hook_off`, `test_client_env_forwards_only_the_session_switch`
- `tests/test_claude_precompact.py` - the hook test asserts no forced switch

## Decisions Made

- The knob follows Resolved Open Question 1 exactly: non-empty `GSD_PATH_JEV` wins both ways; then `[jev] enabled`, project over user; then on by default with `needs_answer: enabled`.
- Internal callers stop forcing the variable, because a forced `1` would defeat `enabled = false`.
- Hooks see only the project layer, since their `XDG_CONFIG_HOME` is never created. Plan 07 documents this limit.

## Deviations from Plan

### Coordinator-requested

**1. [Coordinator item] Dropped the dead `non_loopback_url` key source**
- **Found during:** final coordinator item, after Task 3
- **Issue:** `_KEY_SOURCES` in `jev_ladder.py` still listed `non_loopback_url`, which plan 34-02 removed the only producer of.
- **Fix:** removed that one name; the other names stay.
- **Files modified:** `skills/jev-fast-decision/scripts/jev_ladder.py`
- **Verification:** `tests.test_jev_fast_decision` (226 tests) and `tests.test_jev_config` (31 tests) exit 0.
- **Commit:** `728983c`
- **Doc mentions left alone:** `reference.md` and `backends/laya.md` still name the reason code `non_loopback_url` (a documented reason, not a key source). Both files belong to plan 07 and were not edited.

### Auto-fixed Issues

**2. [Rule 1 - Bug, test input] Score item in the judge knob-off test lacked `context`**
- **Found during:** Task 3 GREEN run
- **Issue:** the plan's example item (`{"id", "type": "score", "instructions", "criteria"}`) has no `context`. The ladder refuses a score item with an empty context (`invalid_input`, `empty_context`) before any client call, so no `client_status` was produced and the knob-off assertion could not be reached.
- **Fix:** added a one-line `context` to that test's item only. The production path is unchanged.
- **Files modified:** `tests/test_judge_loop.py`
- **Commit:** `91d201c`

**3. [Rule 1 - test expectation] Three `needs_answer` assertions now include `enabled`**
- **Found during:** Task 2 RED run
- **Issue:** the plan's rule that an unanswered knob is asked once changes what these pre-existing tests see: `test_configured_default_counts_as_configured` (`[]` becomes `["enabled"]`), and `test_first_run_question_answered_and_declined` (`["laya_url"]` becomes `["enabled", "laya_url"]`, then `[]` becomes `["enabled"]`). The plan's Task 2 text did not list these tests.
- **Fix:** updated the three expectations to the exact new lists.
- **Files modified:** `tests/test_jev_config.py`
- **Commit:** `3fbe44b`

### Process notes (not deviations in behaviour)

- Task 1's first commit attempt was blocked by ruff (E501) and pylint (C0301) on a docstring line I lengthened in `jev_review.py`. I rewrapped it and committed again. No hook was skipped and `--no-verify` was not used.
- While inserting the Task 2 test, one edit landed inside an existing test body; the GREEN run showed it and I moved the new method before committing. The committed diff was reviewed in full before the commit.

**Total deviations:** 1 coordinator-requested, 2 auto-fixed (1 test input, 1 test expectation).
**Impact:** no change to the designed behaviour. The three test expectations and the one test input follow the new behaviour the plan specifies.

## Issues Encountered

- **Stale docs outside this plan's ownership (not edited):** these still say `GSD_PATH_JEV=1` is required, or describe unset as off:
  - `skills/jev-fast-decision/reference.md:78` (`disabled` means `GSD_PATH_JEV` unset) and `:104` (`exactly 1 enables screening (kill switch)`); `:36` example. Plan 07 owns this file.
  - `skills/jev-fast-decision/backends/laya.md:14` example. Plan 07 owns this file.
  - `skills/jev-fast-decision/SKILL.md:12` and `:26` examples prefix `GSD_PATH_JEV=1`.
  - `docs/config/design.md:173` calls `GSD_PATH_JEV` the kill switch.
  - `skills/ai-kit-gsd-curated-config/SKILL.md:324` says the session also needs `GSD_PATH_JEV=1`.
  - `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:1094-1095` text says jev is inert unless `GSD_PATH_JEV=1`. This is user-facing text and needs an owner decision on wording.
- **JEV-07 is shared** with plans 34-01, 34-07 and 34-08. Under the shared-ID gate, `REQUIREMENTS.md` was not marked complete by this plan. The orchestrator should run `requirements.mark-complete JEV-07` once the last declaring plan finishes.
- **Unit brief:** `.aikit/brief/SKILL.md` (unit phase-34, head `cf12ec3658e8`) was read, first 200 lines only, from the main checkout. Its head differs from this worktree's base `01d8509`; it was used as context only.
- `STATE.md` and `ROADMAP.md` were not modified, per the orchestrator.

## Verification

Commands run from the worktree through `tmp/e34-04/run-tests.sh` (sets `AI_KIT_REFUSE_REAL_HOME=1`):

| Command | Exit | Result |
|---|---|---|
| `run-tests.sh tests.test_jev_config tests.test_jev_fast_decision tests.test_judge_loop tests.test_precompact_core tests.test_claude_precompact tests.test_decision_probe tests.test_arch` (final state) | 0 | 7/7 modules passed: jev_config 31, judge_loop 152, decision_probe 6, arch 109, precompact_core 61, claude_precompact 23, jev_fast_decision 226 |
| `run-tests.sh tests.test_jev_config tests.test_jev_fast_decision` (after Task 1) | 0 | 2/2: 26 and 225 |
| `make ruff` (final) | 0 | Passed |
| `make pyright` (before Task 3 commit, and final) | 0 | Passed |
| `make pylint` | 0 | Passed |
| `make vulture` (before Task 3 commit, and final) | 0 | Passed |
| `make arch-test` | 0 | 1/1 modules passed (test_arch 109) |

Each commit also ran the pre-commit hooks (ruff, pylint, py-compile, staged-tests) with no failures: 38/38 modules for `aaf1cf1`, 38/38 for `3fbe44b`, 8/8 for `91d201c`, 26/26 for `728983c`.

**TDD RED evidence (observed locally before each implementation; the test and code were committed together):**
- Task 2 RED: `tests.test_jev_config` 5 of 31 failing (2 FAIL, 3 ERROR); `tests.test_jev_fast_decision` 2 of 226 failing (`test_ladder_child_env_scrubbed`, `test_ladder_forwards_only_the_session_switch`).
- Task 3 RED: `tests.test_judge_loop` 2 of 152 failing (1 FAIL from the forced `"1"`, 1 ERROR from the item missing `context`, deviation 2); `tests.test_precompact_core` 3 of 61 failing; `tests.test_claude_precompact` 1 of 23 failing.

**Plan-level checks:** `tools/judge_loop.py` `ask_jev` contains `env = dict(os.environ)`; `tools/hooks/precompact_core.py` no longer assigns the literal `"1"` and contains `parent.get("GSD_PATH_JEV", "")`; `jev_ladder.child_env` contains `seams.env.get("GSD_PATH_JEV", "")` and no forced pair. `test_probe_works_with_the_switch_unset` replaces the old kill-switch probe test name.

## Threat Flags

None. The forwarded `GSD_PATH_JEV` is the user's own value and no new trust boundary is introduced (T-34-13 mitigated as planned: `JEV_*` and other `GSD_PATH_JEV*` variables stay scrubbed, pinned by tests).

## Known Stubs

None.

## Next Phase Readiness

- Plan 07 can document the knob. Its inputs are the stale list above plus the hook project-layer-only limit.
- JEV-07 is ready for the shared-ID mark-complete once plans 34-01, 34-07 and 34-08 finish.

---
*Phase: 34-jev-backends-by-host-and-laya-calibration*
*Completed: 2026-11-15*

## Self-Check: PASSED

All 11 created or modified files exist on disk; commits aaf1cf1, 3fbe44b, 91d201c and 728983c are ancestors of HEAD; the SUMMARY path is not gitignored.
