---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 02
subsystem: config
tags: [jev, laya, consent, config-toml, probe, key-sources, stdlib]

# Dependency graph
requires:
  - phase: 34-01
    provides: skills/jev-fast-decision/scripts/jev_config.py (config_set, laya_url_setting, valid_url, JEV_KEYS)
provides:
  - jev_review.py reads the Laya address in D-01 order (session env, project [jev], user [jev], legacy loopback JEV_API_URL, default)
  - `jev_review.py config set <key> <value>` saves the first-run answer through the copied atomic writer
  - Host-bound consent for a Laya off loopback (`_needs_consent`), and the probe's needs_answer question
  - TypeSafe key labels in resolution order with ~/.mycreds last, and a key_hint when the key is not in the environment
affects: [34-04 (knob wiring reads the same probe), 34-07 (SKILL.md and reference.md: credential guidance and the recorded home-file reason)]

# Actuals (#2632) — chars/4 over the realized diff (33462 bytes), not a harness token count.
actuals:
  tokens: 8365
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A row's optional `learn` adapter adds probe-only fields and questions; the probe merges them generically"
    - "One consent predicate (`_needs_consent`) covers every row: remote rows always, local rows only when their address is off loopback"
    - "A refused URL reason (insecure_url, invalid_url) answers before consent, because a row with no parsed host has no record to bind"

key-files:
  created: []
  modified:
    - skills/jev-fast-decision/scripts/jev_review.py
    - tests/test_jev_config.py
    - tests/test_jev_fast_decision.py
    - tests/test_secret_shapes_copy_install.py

key-decisions:
  - "A Laya off loopback is gated by a consent record bound to its current host; JEV_ALLOW_REMOTE opens remote rows only (Resolved Open Question 2, T-34-39)"
  - "A keyed Laya over plain http off loopback is refused as insecure_url before any socket: the bearer never crosses in cleartext (T-34-40)"
  - "needs_answer [laya_url] only when the address comes from the default and nothing answers; a configured address, even one equal to the default, never asks"
  - "config set writes only the user config.toml [jev] table; the project layer stays hand-edited"

patterns-established:
  - "TABLE rows carry optional `learn` (probe-only fields) and `key_hint` (fixed text, shown only when the key is not from the environment)"

requirements-completed: [JEV-01]

coverage:
  - id: D1
    description: "The Laya address comes from config set, then the env override wins over config, in D-01 order"
    requirement: JEV-01
    verification:
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_config_set_then_probe_finds_laya_there"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_env_override_beats_config"
        status: pass
      - kind: unit
        ref: "tests/test_jev_fast_decision.py#TestProbe.test_probe_laya_url_sources"
        status: pass
    human_judgment: false
  - id: D2
    description: "An off-loopback Laya needs host-bound consent; the session gate never opens it; a consented host answers; a revoked one is refused"
    requirement: JEV-01
    verification:
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_off_loopback_laya_needs_consent_and_sends_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_consented_off_loopback_laya_answers"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_session_gate_never_opens_an_off_loopback_laya"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_every_off_loopback_row_is_refused_before_a_socket"
        status: pass
    human_judgment: false
  - id: D3
    description: "The first-run question is asked once when nothing names or answers for Laya, and a declined answer is saved and not asked again"
    requirement: JEV-01
    verification:
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_first_run_question_answered_and_declined"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_configured_default_counts_as_configured"
        status: pass
    human_judgment: false
  - id: D4
    description: "A malformed Laya address is a probe error named by its key and never a crash"
    requirement: JEV-01
    verification:
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_malformed_url_is_a_probe_error"
        status: pass
    human_judgment: false
  - id: D5
    description: "A keyed Laya off loopback over plain http is refused before any socket; the key never reaches the probe output"
    requirement: JEV-01
    verification:
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_off_loopback_http_laya_never_gets_a_key"
        status: pass
    human_judgment: false
  - id: D6
    description: "TypeSafe key sources list ~/.mycreds strictly last, and a remote key not from the environment carries the multiplexer hint without a value"
    requirement: JEV-01
    verification:
      - kind: unit
        ref: "tests/test_jev_fast_decision.py#TestKeys.test_probe_reports_mycreds_fallback_and_expected_sources"
        status: pass
      - kind: unit
        ref: "tests/test_jev_config.py#TestClientSettings.test_probe_key_hint_without_env_key"
        status: pass
    human_judgment: false
  - id: D7
    description: "A jev_review.py copied without jev_config.py fails with an ImportError that names it"
    requirement: JEV-01
    verification:
      - kind: unit
        ref: "tests/test_secret_shapes_copy_install.py#TestCopyInstall.test_jev_review_copied_without_jev_config_fails_with_import_error"
        status: pass
    human_judgment: false

# Metrics
duration: "not measured (start time was not recorded at execution start)"
completed: 2026-11-15
status: complete
commits: 3
plan_head_before: 38a58f9625b1ea46e0ee39a0d74e0b13afea8b7b
plan_head_after: b761b6164a0363496fa909d44cdd0333f03d19f4
---

# Phase 34 Plan 02: Laya address from config, host-bound consent, and the home-file key order Summary

**Laya at any configured address (config set, env overrides), host-bound consent for a Laya off loopback, a first-run question saved once, and the home-file key last with a multiplexer hint**

## Performance

- **Duration:** not measured (start time was not recorded)
- **Tasks:** 3 of 3 committed
- **Commits:** 3 (`40365d5`, `5889e4b`, `b761b61`), measured with `git rev-list --count 38a58f9..HEAD`
- **Files changed:** 4 (0 created, 4 modified; 374 insertions, 44 deletions)

## Accomplishments

- `jev_review.py` reads the Laya address in D-01 order: `JEV_LAYA_URL`/`AI_KIT_LAYA_URL`, project `[jev] laya_url`, user `[jev] laya_url`, legacy loopback `JEV_API_URL`, then `LAYA_DEFAULT_URL`. The probe's Laya row names the source in `url_source`.
- `jev_review.py config set <key> <value>` saves one `[jev]` key through `jev_config.config_set` (atomic write, other bytes kept). An empty `laya_url` records the declined first-run answer.
- A Laya whose address is off loopback is gated by the same host-bound consent as a remote row. `JEV_ALLOW_REMOTE` never opens it; a record for the current host does, and a host change needs a new grant.
- `needs_answer: ["laya_url"]` appears in every probe report only when the address is the default and nothing answers there.
- Malformed addresses are probe errors named by their key (`invalid_url:laya_url`, `invalid_url:jev_laya_url`); the probe exits 0.
- A keyed Laya over plain http off loopback is refused as `insecure_url` before any socket, so `LAYA_API_KEY` never travels in cleartext.
- TypeSafe key sources list `~/.mycreds` strictly last, in `_typesafe_key`'s resolution order. A remote key that is not in the environment carries a fixed `key_hint` with the multiplexer advice and no value.

## Task Commits

1. **Task 1: config set saves the Laya address, and the probe finds it there** - `40365d5` (feat, tracer)
2. **Task 2: Laya at any address, with host-bound consent and the first-run question** - `5889e4b` (feat, TDD)
3. **Task 3: home-file key strictly last, with a multiplexer hint** - `b761b61` (feat, TDD)

## Files Created/Modified

- `skills/jev-fast-decision/scripts/jev_review.py` - `_load_sibling` loads `jev_config.py` beside the client (ImportError naming it when absent); `_cwd` seam; `_url_host`, `_laya_url_source`, `_laya_url` (rewritten), `_laya_learn`; `_needs_consent`; `_probe_fields`; the `config` subcommand; `key_hint` on the TypeSafe row; consent helpers switched to `_needs_consent`
- `tests/test_jev_config.py` - `TestClientSettings` (11 client-level tests: tracer, consent, first run, URL edges, session gate, key transport, key hint)
- `tests/test_jev_fast_decision.py` - `_ClientCase` pins the project layer to a temp folder; the Laya probe tests follow the new reasons and `url_source`; the key-order expectation follows JEV-01; `jev_config.py` copied beside the client in the two copy tests
- `tests/test_secret_shapes_copy_install.py` - the lone-copy ImportError check is one helper with two cases (jev_ladder, jev_review)

## Decisions Made

- The one predicate is `_needs_consent(row)`: a remote row always needs consent; a local row needs it only when its URL parses to an off-loopback host. A URL refused for its own reason (`insecure_url`, invalid) has no host, so that reason answers first and consent is not asked for it. `_row_probe` and `_send` keep their order.
- `config set` writes only the user `config.toml`. The project layer stays hand-edited.
- The probe names the question only from `_laya_learn`, and only for the default source. A configured address never asks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `config set` help text named the backend**
- **Found during:** Task 1 (`tests.test_jev_fast_decision.TestSeam`)
- **Issue:** The new subcommand's help string contained the backend name outside a `_laya_*` adapter or the TABLE literal, which the seam rule forbids.
- **Fix:** Reworded the help text to "the value; an empty string records the declined answer".
- **Files modified:** `skills/jev-fast-decision/scripts/jev_review.py`
- **Verification:** `tests.test_jev_fast_decision` 225/225 ok; the Task 1 commit gate passed.
- **Committed in:** `40365d5`

### Process deviations

- **TDD sequencing (Tasks 2 and 3):** the RED runs were observed locally, and the test and implementation were committed together, as the rails allow (a failing-test-only commit is blocked by the staged-tests hook). RED evidence, both before the implementation, run with `bash tmp/e34-02/run-tests.sh tests.test_jev_config tests.test_jev_fast_decision`:
  - Task 2: `tests.test_jev_config` 7 failing of 24 (3 errors, 4 failures); `tests.test_jev_fast_decision` 3 failing of 225. Exit 1.
  - Task 3: `tests.test_jev_config` 1 error of 25 (KeyError `key_hint`); `tests.test_jev_fast_decision` 1 failure of 225 (old home-file order). Exit 1.
- **Plan commit ledger (protocol 0c) was not written** before the first commit, so the base is taken from the worktree's start HEAD: `plan_head_before: 38a58f9625b1ea46e0ee39a0d74e0b13afea8b7b`. The commit count is measured against that base.
- **Lint fix before commit:** ruff SIM117 on a nested `with` in a new test helper, combined into one statement (caught by `make ruff` before the Task 2 commit).

**Total deviations:** 1 auto-fixed (blocking, seam rule), plus 2 process notes. **Impact:** none on scope; all acceptance criteria of the three tasks hold.

## Issues Encountered

- **JEV-01 stays open.** This plan covers the Laya address, consent, the first-run answer, the key order and the hint. JEV-01's text also requires credential guidance for non-interactive shells and the recorded reason for keeping the home-file fallback, and the plan assigns both to reference.md and SKILL.md in Plan 07. The `[ ]` checkbox and the `Pending` row in `REQUIREMENTS.md` are not changed here. `requirements-completed` copies the plan frontmatter verbatim, as the workflow requires (34-01 did the same).
- **Unit brief read.** A default-size read of `.aikit/brief/SKILL.md` exceeded the token limit; the first 40 lines were read instead (read-only, main checkout copy). The brief names unit phase-34, which is this unit.
- **Environment.** `make setup-env` created `.venv/` in the worktree. It is git-ignored and was left in place.
- **Residual name.** `skills/jev-fast-decision/scripts/jev_ladder.py` (about line 90) still lists `non_loopback_url` among its known reasons. No code path produces it now. It is outside this plan's files and was left alone.

## Verification

- `bash tmp/e34-02/run-tests.sh tests.test_jev_config tests.test_jev_fast_decision tests.test_secret_shapes_copy_install tests.test_arch` - `4/4 modules passed`, no error (exit 0), after Task 3.
- Commit gates on all three commits (ruff, pylint, py-compile, staged tests): `37/37 modules passed` each time, `4/4` under uv.
- `make ruff`, `make pylint`, `make pyright`, `make vulture`, `make arch-test` - each reports `Passed`, no error (exit 0). `tests.test_arch` 109 tests ok.
- `bash tmp/e34-02/run-tests.sh --group unit` - `123/123 modules passed` (python3 unit group, exit 0).
- Not run in this plan: `make check-dogfood`, `make e2e-test`, `make test-integration`, `make test-env-matrix`. The covering e2e modules (`test_jev_skill_install_e2e`, `test_flow_index_e2e`, `test_wizard_pty`) ran through the commit gate.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-34-05 to T-34-08, T-34-39 and T-34-40 are covered by the tests named in the coverage block.

## Next Phase Readiness

- Plan 04 (the `[jev] enabled` knob) can read the same `probe_report`; the new `needs_answer` field and `url_source` are already in place.
- Plan 07 must add the credential guidance for non-interactive shells and the recorded reason in `reference.md` before JEV-01 can be ticked.

---
*Phase: 34-jev-backends-by-host-and-laya-calibration*
*Completed: 2026-11-15*

## Self-Check: PASSED

- Task commits present in history: `40365d5`, `5889e4b`, `b761b61` (`git merge-base --is-ancestor` exit 0 for each).
- Files present in the worktree: `skills/jev-fast-decision/scripts/jev_review.py`, `tests/test_jev_config.py`, `tests/test_jev_fast_decision.py`, `tests/test_secret_shapes_copy_install.py`.
