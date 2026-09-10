---
phase: 04-config-doctor
plan: 03
subsystem: config-doctor
tags: [config-doctor, apply-flow, atomic-write, confirm-modal, e2e-docker]

requires:
  - phase: 04-config-doctor
    provides: Wave 1 tracer engine + Wave 2 full 25-row Checks Catalog
provides:
  - "config_doctor_appliers.py — atomic JSON, TOML region-replace, and JSONC surgical-set writers"
  - "apply_row(row_id, ctx, dry) — generic dispatcher wired onto 4 representative rows, one per write-format concern"
  - "ConfirmApplyScreen — per-item confirm modal with literal-resulting-config display for security-relevant rows"
  - "Structural TestNoBulkApply guarantee — no apply_rows/apply_selected/apply_each-shaped bulk entry point exists"
affects: [04-config-doctor]

actuals:
  tokens: 88000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Cross-AI execution (opencode run --model router-env/my-coding) landed all 3 task commits correctly but died mid-verification — no EXECUTION COMPLETE marker, no SUMMARY.md, never reached its own make validate/e2e-docker gates. Completed directly per ONESHOT-RULES Rule 1 (never trust a self-reported pass without independent re-verification), matching the same truncation class seen closing Phase 03's plan 02."
    - "typing.cast on an object-typed NamedTuple field before calling it (mirrors tools/setup.py's existing cast(Selection, ...) / cast('_StdTty', ...) precedent) — needed once config_doctor_checks.py joined pyright's include list and CheckRow.apply's object typing became genuinely checked."
    - "Explicit isinstance(parsed, dict) narrowing instead of relying on a state-string comparison — pyright cannot correlate a 3-state reader's (state, data) tuple's two elements without it."

key-files:
  created:
    - tools/config_doctor_appliers.py
    - .planning/phases/04-config-doctor/04-03-SUMMARY.md
  modified:
    - tools/config_doctor_checks.py
    - tools/config_doctor_app.py
    - tests/test_config_doctor.py
    - tests/test_config_doctor_pty.py
    - pyproject.toml

key-decisions:
  - "The cleanupPeriodDays: 0 refusal returns {\"ok\": False, \"reason\": ...} from the applier rather than raising — Textual 8.x swallows an unhandled exception into a graceful app shutdown rather than a caught refusal, so apply_row's own try/except around the applier call is what actually converts any exception into a refusal dict."
  - "opencode-share-mode's JSONC write self-validates via strip+parse of the spliced text before committing; an invalid splice returns a refusal and performs no write, closing T-04-08's threat mitigation for real rather than as an unenforced claim."
  - "apply_row dispatches by row identity (row.apply), never by inspecting row.runtime — a generic engine, not four hand-wired per-runtime branches."
  - "TestNoBulkApply asserts, structurally, that no apply_rows/apply_selected/apply_each-shaped function or BINDINGS action exists — the no-bulk-apply guarantee (REQUIREMENTS.md Out of Scope, ROADMAP SC-4) is machine-checked, not just documented."

patterns-established:
  - "A per-item confirm modal shows the literal resulting config only for security_relevant rows; non-security rows show only the specific field diff — the security-relevant distinction from Wave 2's CheckRow.security_relevant field now drives UI, not just data."
  - "Every applier is reachable only through apply_row's single (row_id, ctx, dry) signature — the plan's own primary architectural guarantee, reworded in cycle-2 review to state this plainly rather than relying on TestNoBulkApply's name-pattern check alone."

requirements-completed:
  - REQ-config-doctor-apply-flow

coverage:
  - id: T3-WRITERS
    description: "Atomic JSON, TOML region-replace, and JSONC surgical-set writers round-trip correctly and leave the target byte-identical on injected os.replace failure"
    requirement: REQ-config-doctor-apply-flow
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestAppliers"
        status: pass
    human_judgment: false
  - id: T3-APPLY-ROWS
    description: "apply_row dispatches all 4 wired rows (claude-retention, claude-sandbox-enabled, opencode-share-mode, codex-history-persistence) correctly, refuses cleanupPeriodDays 0 unconditionally, and self-validates the JSONC splice before writing"
    requirement: REQ-config-doctor-apply-flow
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestApplyRows"
        status: pass
    human_judgment: false
  - id: T3-CONFIRM-MODAL
    description: "ConfirmApplyScreen shows literal_resulting_config for security-relevant rows only, surfaces refusal reason on ok:False, and cancelling calls ctx.apply zero times for writes"
    requirement: REQ-config-doctor-apply-flow
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestConfirmApplyScreen"
        status: pass
      - kind: integration
        ref: "tests.test_config_doctor_pty.TestConfigDoctorPty.test_apply_confirm_flow_writes_the_target_value"
        status: pass
    human_judgment: false
  - id: T3-NO-BULK-APPLY
    description: "No apply_rows/apply_selected/apply_each-shaped bulk entry point exists in config_doctor_checks.py, config_doctor_app.py, or config_doctor_appliers.py, nor as a BINDINGS action"
    requirement: REQ-config-doctor-apply-flow
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestNoBulkApply"
        status: pass
    human_judgment: false
  - id: T3-PHASE-GATES
    description: "make test, make lint, make validate, and make e2e-docker are all green with the full Config Doctor apply flow in place"
    requirement: REQ-config-doctor-apply-flow
    verification:
      - kind: integration
        ref: "make e2e-docker (clean-room container)"
        status: pass
    human_judgment: false

completed: 2026-09-10
status: complete
---

# Phase 4 Plan 03: Config Doctor Apply Flow Summary

**Per-item, explicitly confirmed writes for 4 representative rows (one per write-format concern), reusing the atomic-write pattern ported from opencode-provider-management, with a structural no-bulk-apply guarantee.**

## Performance

- **Tasks:** 3
- **Files created:** 1 (plus this SUMMARY)
- **Files modified:** 5

## Accomplishments

- `tools/config_doctor_appliers.py` provides `atomic_write_json`, a TOML minimal-region-replace writer (enumerating existing-key-replace / new-key-in-existing-table / create-table sub-cases), and `set_jsonc_value` — a string-level surgical JSONC setter reusing `jsonc_edit.py`'s brace-counting discipline without cross-importing from `skills/`. All three round-trip correctly and leave the target byte-identical when `os.replace` is patched to fail mid-write.
- `apply_row(row_id, ctx, dry)` in `config_doctor_checks.py` dispatches by row identity via `row.apply`, wired onto `claude-retention` (JSON), `claude-sandbox-enabled` (JSON, nested key), `opencode-share-mode` (JSONC, self-validating splice), and `codex-history-persistence` (TOML) — one row per write-format concern. Any exception an applier raises is converted to `{"ok": False, "reason": "applier error: ..."}` inside `apply_row`'s own `try`/`except`, since Textual 8.x swallows an unhandled exception into a graceful shutdown rather than surfacing it as a caught refusal.
- `ConfirmApplyScreen` in `config_doctor_app.py` shows the current/recommended/citation for the row being applied, surfaces `literal_resulting_config` only when `row.security_relevant` is true, shows the refusal `reason` and leaves the table row unchanged on `ok: False`, and never calls `ctx.apply` on cancel (verified by a call-count spy).
- `TestNoBulkApply` structurally asserts no `apply_rows`/`apply_selected`/`apply_each`-shaped function or `BINDINGS` action exists across all three `config_doctor_*.py` modules — the no-bulk-apply requirement (REQUIREMENTS.md Out of Scope, ROADMAP SC-4) is machine-checked.
- `tools/config_doctor_appliers.py` was added to `[tool.pyright] include` in `pyproject.toml`, with `TestGateRegistration` extended to assert it — closing cycle-1 review's MEDIUM finding that the most safety-critical new module (the writers) was escaping type checking.
- The cross-AI execution run (opencode/router-env) completed all 3 task commits correctly and ran `make test`/`make lint` for real, but was cut off — no `EXECUTION COMPLETE` marker, no `04-03-SUMMARY.md` — partway through checking whether its own `make validate` findings were pre-existing baseline or new. Independent re-verification (ONESHOT-RULES Rule 1) found 17 genuine new pyright errors (an `object`-typed `CheckRow.apply` field called directly, plus two appliers whose `dict`/`None` narrowing pyright could not correlate with the reader's state string) and 6 ruff findings (RUF015, SIM105×2, SIM117, UP035, SIM108), all confirmed via the diff to originate from this task's own new code. Fixed directly and committed as `153eb09` — see Task Commits below.

## Task Commits

1. **Task 1: Atomic JSON/TOML/JSONC apply writers** — `df40754` (feat)
2. **Task 2: Wire four apply-eligible rows behind `apply_row`** — `859af15` (feat)
3. **Task 3: Per-item confirm apply screen** — `d4e8d77` (feat)
4. **Gap closure: pyright/ruff findings from the cross-AI execution run** — `153eb09` (fix, this segment)

## Files Created/Modified

- `tools/config_doctor_appliers.py` — atomic JSON/TOML/JSONC writers
- `tools/config_doctor_checks.py` — `apply_row` dispatcher, 4 wired appliers, `typing.cast` on the `object`-typed `apply` field call site
- `tools/config_doctor_app.py` — `ConfirmApplyScreen`
- `tests/test_config_doctor.py` — `TestAppliers`, `TestApplyRows`, `TestNoBulkApply`, `TestConfirmApplyScreen`
- `tests/test_config_doctor_pty.py` — `test_apply_confirm_flow_writes_the_target_value`
- `pyproject.toml` — `config_doctor_appliers.py` added to `[tool.pyright] include`

## Decisions Made

None beyond the plan. Followed the locked Round 1/Round 2/Round 3(polish) review dispositions on the Cursor-precedence-agnostic apply scope, the refusal-as-return-not-raise contract, and the `ctx.apply(...)` seam wording.

## Deviations from Plan

None in the substantive implementation — all 3 tasks match the plan's `<action>` blocks. The only deviation was procedural: the cross-AI executor did not itself complete the final gate verification or write this SUMMARY.md before its own truncation; that closure was done directly in this segment, matching the precedent already established when closing Phase 03's plan 02.

**Total deviations:** 0 (implementation) / 1 (procedural — closure work completed by orchestrator, not by the cross-AI executor)
**Impact on plan:** None — same commits, same code, gates now independently confirmed green.

## Issues Encountered

Cross-AI execution run was cut off by an apparent session/stdin issue partway through its own final verification (identical failure signature to Phase 03's plan 02 closure: real work landed, final gate-check and SUMMARY.md never completed). Diagnosed via absence of the `EXECUTION COMPLETE` marker despite the wrapper process exiting 0, and confirmed via `git log`/`git status` that all 3 task commits were legitimate and the tree was otherwise clean. Two earlier attempts at plan 04-01 (both primary and one retry) failed identically before any commits landed at all; the documented fallback model (`xai/grok-4.6`) succeeded cleanly for 04-01, and the primary model (`router-env/my-coding`) then succeeded for 04-02 and landed real (if incomplete-at-the-edges) work for 04-03.

## User Setup Required

None. Applying any row requires an interactive `--config-doctor` session against a real runtime's config file — per ONESHOT-RULES Rule 5, this run never touched uz's real `~/.claude`/`~/.cursor`/`~/.config/opencode`/`~/.codex`; all apply-flow verification used scratch config-dir envs and the `make e2e-docker` clean-room harness.

## Next Phase Readiness

ROADMAP Phase 4 success criteria are now all true: the Checks Catalog spans all 4 runtimes plus the cross-runtime rtk-Cursor row (Wave 2), the review screen renders the full catalog under a real PTY (Wave 1+2), and the apply flow is per-item, explicitly confirmed, reuses the atomic-write pattern, and has no bulk-apply path (Wave 3). Ready for phase-level code review and goal-backward verification.

## Verification (captured, this segment)

```
$ python3 -m unittest tests.test_config_doctor tests.test_config_doctor_pty -v
Ran 83 tests in 4.331s
OK (skipped=6)

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py
# exit 0

$ make test
Ran 1411 tests in 17.852s
OK (skipped=25)

$ make validate
pylint: Your code has been rated at 9.98/10 (unchanged — same pre-existing tools/status-line.py / tools/wizard_app.py / tests/test_ai_kit_spec*.py baseline, confirmed via diff to predate this phase's own commits)
pyright...................................................................Passed
vulture....................................................................Passed
shellcheck.................................................................Passed
py-compile.................................................................Passed
unittest (core).............................................................Passed
unittest (wizard — uv)......................................................Passed

$ make e2e-docker
Ran 1411 tests in 24.225s
OK (skipped=26)
16 passed, 0 failed   # tests/test_install.sh
==> ai-kit clean-room E2E: PASS
```

## Self-Check: PASSED

- [x] Three atomic writers (JSON/TOML/JSONC) round-trip correctly and leave targets byte-identical on injected write failure
- [x] `apply_row` dispatches all 4 wired rows correctly, catches applier exceptions, and refuses `cleanupPeriodDays: 0` unconditionally
- [x] `opencode-share-mode`'s JSONC write self-validates via strip+parse before committing, refusing (never writing) on an invalid splice
- [x] `ConfirmApplyScreen` shows `literal_resulting_config` only for security-relevant rows, surfaces refusal reasons, and cancel calls `ctx.apply` zero times
- [x] `TestNoBulkApply` structurally confirms no bulk-apply entry point exists
- [x] `config_doctor_appliers.py` is inside pyright's `include` list, asserted by `TestGateRegistration`
- [x] `make test`, `make lint`, `make validate`, `make e2e-docker` all green (independently re-run this segment, not trusted from the cross-AI run's own truncated report)
- [x] Production commits exist (`df40754`, `859af15`, `d4e8d77`) plus this segment's gap-closure commit (`153eb09`)

---
*Phase: 04-config-doctor*
*Completed: 2026-09-10*
