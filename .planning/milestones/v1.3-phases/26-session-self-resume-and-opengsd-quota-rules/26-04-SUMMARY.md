---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 04
subsystem: session-wake
tags: [systemd, session-resume, cross-ai-refusal, permission-mode, python]
requires:
  - phase: 26-01
    provides: The AI_KIT_CROSS_AI_CHILD runner marker on every runner child
  - phase: 26-02
    provides: Session wake state, arm/fire/disarm primitives and fake seams
  - phase: 26-03
    provides: Idempotent arm refresh, matrix rows and CLI status/matrix
provides:
  - pi, opencode and codex HOSTS rows with per-host resume argv and evidence labels
  - Host-pid resolution order (flag, env var, bounded ancestor walk) with honest pid_source labels
  - Cross-AI child refusal (marker primary, unmarked cross-ai.mjs ancestor fallback, off-Linux note)
  - Permission-mode copy from the host command line with source labels and no implicit escalation
  - Per-host session-exists probes (exact-stem globs; opencode listing with truncation-aware unknown)
affects: [phase-26, phase-27, session-wake]
actuals:
  tokens: 10900
  tasks: 3
  commits: 4
tech-stack:
  added: []
  patterns: [exact-stem session-store matching, count-based listing completeness, service-env-scoped probes]
key-files:
  created: []
  modified: [skills/ai-kit-session-wake/ai_kit_session_wake/hosts.py, skills/ai-kit-session-wake/ai_kit_session_wake/liveness.py, skills/ai-kit-session-wake/ai_kit_session_wake/arm.py, skills/ai-kit-session-wake/ai_kit_session_wake/cli.py, tests/session_wake_fakes.py, tests/test_ai_kit_session_wake.py]
key-decisions:
  - "Host.store is (root, glob, stem_pattern): a file counts only when its stem fully matches the exact id, so a longer id never matches (review round 1)."
  - "The opencode probe lists with --max-count and treats a full-length listing as unknown (possibly truncated), never missing."
  - "The probe runs the host CLI under the service-env view, so test fixtures must sit beside the fake binary, never in the environment."
  - "pi, opencode and codex resumes take the prompt as the final positional; only claude wraps it in -p."
requirements-completed: [QTA-04]
coverage:
  - id: D1
    description: A pi session arms through the ancestor walk and fires one `pi -p --session-id` resume in its launch directory.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestPiTracer.test_arm_through_ancestor_walk_then_one_pi_resume
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestPiTracer.test_pi_store_exact_stem_and_resume_argv
        status: pass
    human_judgment: false
  - id: D2
    description: Host-pid sources with honest labels (--pid, env var, ancestor-unverified, refuse naming --pid).
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestHostProcess
        status: pass
    human_judgment: false
  - id: D3
    description: Cross-AI child refusal by marker and by unmarked runner ancestor; CLAUDE_CODE_CHILD_SESSION never a signal; off-Linux scan note.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestChildRefusal
        status: pass
    human_judgment: false
  - id: D4
    description: Permission mode copied from the host command line, printed with its source, never escalated on its own.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestPermissionMode
        status: pass
    human_judgment: false
  - id: D5
    description: Per-host session-exists probes with exact-stem matching and the opencode truncation-aware listing; fire splits missing from unknown.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestSessionProbe
        status: pass
    human_judgment: false
  - id: D6
    description: Resume argv rows for opencode and codex, unverified labelling, HOSTS keys inside RUNTIMES, cursor exit 3.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestResumeRows
        status: pass
    human_judgment: false
duration: 45min
completed: 2026-10-29
status: complete
orchestrator_verify: "VERIFY 26-04: 3/3 passed"
orchestrator_verify: "VERIFY 26-04: 3/3 passed"
---

# Phase 26 Plan 04 Summary

**Session wake beyond claude: pi/opencode/codex resume rows, honest host-pid sources, the cross-AI child refusal, permission-mode copy and per-host session-exists probes**

## Accomplishments
- `HOSTS` gained pi, opencode and codex rows; every store row matches only a file whose stem holds the exact session id (`re.fullmatch` with `re.escape`), and `Host.store` is a `(root, glob, stem_pattern)` triple.
- `arm` resolves the host pid from `--pid`, then the host's env var, then a 64-hop-bounded ancestor walk recorded `ancestor-unverified` with an `(unverified)` output note; with no source it exits 2 naming `--pid`.
- `arm` refuses inside a cross-AI runner child: `AI_KIT_CROSS_AI_CHILD` set (except empty/`0`) or an ancestor whose `cross-ai.mjs` script lacks the marker name (older copies); off Linux it prints `ancestor scan unverified off Linux`; `CLAUDE_CODE_CHILD_SESSION` is never read.
- The permission mode is copied from the host command line (`bypassPermissions`, `--permission-mode X`, `default`, `unknown` for `bg-spare`/unreadable), printed with its source and a not-applied note for hosts without a verified flag, and the resume adds `--permission-mode` only for modes other than `default`/`unknown`.
- Session-exists probes: exact-stem globs for claude/pi/codex under the service-env view, an opencode `session list --format json --standalone --max-count` probe where a full-length or invalid listing is `unknown` (never `missing`), arm refuses anything but `exists` saying a resume of a missing id would create a new session, and fire's missing/unknown split is driven by tests through the pi store and the opencode listing.

## Task Commits
1. Task 1 — `93a145e` (`feat(26-04): pi session wake through the ancestor walk`)
2. Task 1 follow-up (the end-to-end pi tracer test) — `d1a3f59` (`test(26-04): pi tracer end to end through the ancestor walk`)
3. Task 2 — `31a5eaa` (`feat(26-04): host pid sources, the cross-AI child refusal and the permission copy`)
4. Task 3 — `a7f40ad` (`feat(26-04): session-exists probes and the opencode and codex resume rows`)

## Files Created/Modified
- `skills/ai-kit-session-wake/ai_kit_session_wake/hosts.py` — pi/opencode/codex rows, `OPENCODE_LIST_MAX`, `permission_from_cmdline`, prompt placement per host row, exact-stem probes with the service-env listing.
- `skills/ai-kit-session-wake/ai_kit_session_wake/liveness.py` — `ancestors` (64-hop bound), `find_host_ancestor`, `cross_ai_ancestor`.
- `skills/ai-kit-session-wake/ai_kit_session_wake/arm.py` — pid-source order, refusal-first cross-AI checks, permission copy and printed labels, unverified resume-argv and pid notes.
- `skills/ai-kit-session-wake/ai_kit_session_wake/cli.py` — optional session-env rows in the target picker.
- `tests/session_wake_fakes.py` — fake host arm/sleep modes, log-path fallback in the shared prelude, `pi_session`, `codex_session`, fixture-reading `fake_opencode`.
- `tests/test_ai_kit_session_wake.py` — TestPiTracer, TestHostProcess, TestChildRefusal, TestPermissionMode, TestSessionProbe, TestResumeRows.

## Decisions Made
- The fire-time truncation scenario models new sessions arriving after the arm: the fixture is rewritten so the armed id sits beyond the patched window, making the listing provably incomplete (`unknown`) at fire time.
- The opencode probe and the glob rows read HOME/PATH through the service-env view, so the fake opencode reads its fixtures from files beside itself and the shared prelude falls back to `<bin parent>/fake.log`.

## Deviations from Plan

### Auto-fixed Issues

**1. Task 1's feat commit landed before its tracer test was complete**
- **Found during:** post-commit review of Task 1
- **Issue:** commit `93a145e` shipped the host-row/ancestor scaffolding and a narrowed store/argv test, but not the planned end-to-end `TestPiTracer` tracer
- **Fix:** added the full tracer test (fake pi host in arm mode, ancestor-unverified pid, one `pi -p --session-id` resume, full removal with the done marker) plus the runtime gaps it exposed
- **Files modified:** tests/test_ai_kit_session_wake.py, tests/session_wake_fakes.py, skills/ai-kit-session-wake/ai_kit_session_wake/{arm,hosts}.py
- **Verification:** `tests.test_ai_kit_session_wake.TestPiTracer` and the parallel module run pass
- **Committed in:** `d1a3f59` (`test(26-04)`)

**2. cli.py target picker needed the optional session-env rows**
- **Found during:** Task 1 (whole-tree pyright)
- **Issue:** making `Host.session_env` optional left `env.get(row.session_env, "")` typing invalid for pi/opencode
- **Fix:** guard the env lookup when the row carries no session variable
- **Files modified:** skills/ai-kit-session-wake/ai_kit_session_wake/cli.py
- **Verification:** `uv run pyright` 0 errors
- **Committed in:** `93a145e` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 incomplete-task follow-up, 1 typing guard)
**Impact on plan:** Both necessary for the plan's own acceptance criteria. No scope creep.

## Issues Encountered
- The CLI's `_pick_target` refuses an unknown host before `arm` runs, so tests that exercise host-level behavior pass `--host` explicitly rather than relying on detection in the scratch env.
- The subprocess arm runs on the real clock, so the pi tracer fires at `time.time() + 120` to sit past the real `not_before` window.
- Two pre-existing claude-tracer expectations asserted `permission_mode: unknown (unknown)`; with the host-command-line copy the sleep stand-in now records `default (host-cmdline)`, and the expectations were updated to match the new (planned) behavior.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Every host with a resume row now checks that its session exists where the service will look, and nothing resumes into a freshly created session; 26-05 can build fire-path tests on the same fakes, and 26-06/26-07 extend arm's flags and hooks on the resolved pid-source/permission plumbing.

---
*Phase: 26-session-self-resume-and-opengsd-quota-rules*
*Completed: 2026-10-29*
