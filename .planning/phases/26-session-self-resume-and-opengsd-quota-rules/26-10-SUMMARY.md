---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 10
subsystem: infra
tags: [session-wake, skill-doc, systemd-user-timer, pi-link, executor-wiring, rules-checker]

# Dependency graph
requires:
  - phase: 26-02
    provides: the ai-kit-session-wake package (arm/disarm/fire/done CLI, state, units)
  - phase: 26-04
    provides: per-host resume rows, the cross-AI child refusal and the pi session-id refusal
  - phase: 26-07
    provides: the opt-in StopFailure hook and arm --only-if-armed
provides:
  - skills/ai-kit-session-wake/SKILL.md: a discoverable Agent Skill whose resolve-and-arm block runs as written under a scratch env
  - doc_block_env and stub_shim test helpers that run SKILL.md blocks with the real systemctl unreachable
  - PI_SKILLS member ai-kit-session-wake, so pi can discover the skill an AGENTS.md rule names
  - Session wake arm, re-arm and close steps in ai-kit-spec-execute-gsd and ai-kit-spec-execute-superpowers, gated on WAKE_OWNED
affects: [26-11, 26-12, 27]

actuals:
  tokens: 16768  # chars/4 over the realized diff (12 files, +1063/-8); the plan estimate was 120000
  tasks: 3
  commits: 8  # three task commits, three follow-up test/feat commits, two docs commits

tech-stack:
  added: []
  patterns:
    - "A SKILL.md bash block is extracted by marker and run under an explicit scratch env, never os.environ"
    - "Ownership gate: a wake is re-armed or closed only after this run's own armed line (WAKE_OWNED=1)"
    - "Stub shim mirrors the real arm contract (armed/refreshed lines, pi refusal exit 2) for executor tests"

key-files:
  created:
    - skills/ai-kit-session-wake/SKILL.md
  modified:
    - README.md
    - tools/setup.py
    - tests/session_wake_fakes.py
    - tests/test_ai_kit_session_wake.py
    - tests/test_setup.py
    - tests/test_ai_kit_spec_gsd.py
    - tests/test_ai_kit_spec_superpowers.py
    - skills/ai-kit-spec-execute-gsd/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/SKILL.md

key-decisions:
  - "The stop re-arm and the close are fenced, WAKE_OWNED-guarded blocks, so the guard is part of the text an agent runs, not only prose beside it"
  - "The superpowers arm step sits before Step 2 and its close step after Step 4, matching SPEC R8 ordering (arm before the first dispatch, done after the final review)"
  - "Only claude needs no session id; pi and opencode arm only with the exact id the owner or host gave, and a refusal is relayed, never swallowed"
  - "The doc names the residual risk that a subagent running done or disarm is prevented by text only (T-26-32, accepted)"

patterns-established:
  - "Executor steps record WAKE_SHIM, WAKE_OWNED, WAKE_HOST and WAKE_ID once and re-substitute them literally"
  - "Test non-vacuity: removing the WAKE_OWNED guard from the SKILL.md block fails the single-run stop test"

requirements-completed: [QTA-04]

coverage:
  - id: D1
    description: "The ai-kit-session-wake SKILL.md; its resolve-and-arm block arms a scratch claude session as written, with the fake systemctl log proving the real one was never reached"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestSessionWakeSkillText"
        status: pass
    human_judgment: false
  - id: D2
    description: "PI_SKILLS gains ai-kit-session-wake; the claude selection mirrors it into the pi skills dir and a name outside the set does not"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_setup.py#TestSyncPiLinks.test_session_wake_skill_links_on_pi"
        status: pass
      - kind: e2e
        ref: "tests/test_jev_skill_install_e2e.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "ai-kit-spec-execute-gsd arms the wake for a multi-plan phase, re-arms it after a cross-AI stop only when it owns it, and closes it at the end; a single-plan run arms nothing"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_spec_gsd.py#TestSessionWakeStep"
        status: pass
    human_judgment: false
  - id: D4
    description: "ai-kit-spec-execute-superpowers arms the wake for a multi-task plan before Step 2, and closes it after Step 4 only when it owns it"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_spec_superpowers.py#TestSessionWakeStep"
        status: pass
    human_judgment: false
  - id: D5
    description: "pi and opencode refuse arm without an exact session id; the executor relays the refusal and runs with no wake, and the owner confirms the pi link in 26-12"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_spec_gsd.py#TestSessionWakeStep.test_two_plans_on_pi_without_an_id_relays_the_refusal_and_goes_on"
        status: pass
    human_judgment: true
    rationale: "The stub shim mirrors the real refusal text; the live pi refusal and the pi discovery of the skill are confirmed only by the owner's captures in 26-12."

# Metrics
duration: n/a
completed: 2026-10-30
status: complete
orchestrator_verify: "VERIFY 26-10: 3/3 passed"
---

# Phase 26 Plan 10: Session wake skill and executor wiring Summary

**The session wake ships as a discoverable skill whose own arm block runs as written, and both multi-unit executors arm it before their first dispatch and close it when their job ends.**

## Performance

- **Duration:** not measured
- **Tasks:** 3 (three task commits, three follow-up commits, this summary)
- **Files modified:** 12 (+1063 / -8 lines)

## Accomplishments

- The `ai-kit-session-wake` SKILL.md documents the six subcommands, the per-host session-id sources with their certainty, exit codes 0, 2 and 3, the inferred reset flags, the opt-in StopFailure hook, the one-shot companion at the printed time (a fire inside a limit is lost, spike 004), and every unverified item.
- Its resolve-and-arm block is extracted by marker and run under `doc_block_env`. The test proves the arm reached the fake systemctl (`daemon-reload`, `enable --now`) and that `systemctl` resolves only under the scratch bin dir.
- `PI_SKILLS` gains `ai-kit-session-wake`; README names it in the skills table, the pi-link sentence and the `--skills` note.
- `ai-kit-spec-execute-gsd` arms the wake before `/gsd-execute-phase` when the phase holds two or more `*-PLAN.md` files, re-arms it after a cross-AI stop only when it owns it, and closes it at the end, never on the exit-75 `retry_after_s=` branch.
- `ai-kit-spec-execute-superpowers` arms the wake before Step 2 when the plan has two or more `### Task` headings, and closes it after Step 4 under the same ownership gate.
- Ownership: `WAKE_OWNED=1` only after this run's own `armed` line. A single-plan run, a refusal, exit 3 and a `refreshed` wake all leave `WAKE_OWNED=0`, and the re-arm and close blocks then call nothing.

## Task Commits

1. **Task 1: the session-wake SKILL.md with a runnable arm block** - `5615f26` (docs)
2. **Task 2: link the skill for pi through PI_SKILLS** - `a72641d` (feat)
3. **Task 3: executors arm the session wake for multi-unit runs and close it at the end** - `92254c1` (feat)
4. **Test: pin `doc_block_env`'s unresolved-command raise and the scratch-only `systemctl`** - `64a08dc` (test), verified red against a mutant that skips unresolved names
5. **Pin both executors' session-wake close to their job-end conditions** - `3ae9887` (feat): the superpowers close now names its own stop vocabulary ("STOP this wave" or an owner stop), and both close steps are asserted by test
6. **Plan completion summary** - `ad0bdbe` (docs)
7. **Summary correction** - `77af570` (docs)
8. **Wizard HOOKS-row match** - `1bad074` (test): the PTY test matched `session-wake` as a bare substring, which the new skill name `ai-kit-session-wake` also contains; it now matches the bulleted HOOKS row. This was the `make validate` wizard-uv failure.

## Files Created/Modified

- `skills/ai-kit-session-wake/SKILL.md` - created: the skill doc with the resolve-and-arm block
- `README.md` - skills table row, pi-link sentence, `--skills` note
- `tools/setup.py` - `PI_SKILLS` gains `ai-kit-session-wake`
- `tests/session_wake_fakes.py` - `doc_block_env` and `stub_shim` helpers
- `tests/test_ai_kit_session_wake.py` - `TestSessionWakeSkillText`
- `tests/test_setup.py` - pi-mirror test for the new member
- `tests/test_ai_kit_spec_gsd.py` - `TestSessionWakeStep` (gsd)
- `tests/test_ai_kit_spec_superpowers.py` - `TestSessionWakeStep` (superpowers)
- `skills/ai-kit-spec-execute-gsd/SKILL.md` - arm, re-arm and close steps
- `skills/ai-kit-spec-execute-superpowers/SKILL.md` - arm and close steps, re-arm in point 3

## Decisions Made

- The stop re-arm and the close are fenced, `WAKE_OWNED`-guarded blocks. An early draft put the re-arm in prose; the test could not extract it, and prose gives an agent no guard to run. The fence makes the gate part of the runnable text.
- The superpowers re-arm is a fenced block under numbered point 3, not an inline span, for the same reason.
- Only claude reads its session id itself. pi and opencode arm only with an exact id from the owner or the host; `arm` refuses otherwise and the run continues with no wake.
- A subagent running `done` or `disarm` is prevented by this text alone (T-26-32, accepted, stated in the NEVER list).

## Deviations from Plan

- The plan's `estimate.tokens` was 120000; the realized diff is about 13,151 tokens by chars/4. The estimate was far too high for this scope, recorded in `actuals` so future estimates calibrate.
- The plan's SKILL.md blocks were first written as prose. Two tests (the single-run stop tests) found no fenced block to run, so the re-arm and close were converted to guarded fenced blocks. This is a fix to the doc's runnability, not a scope change.
- The Task 3 non-vacuity check was run on a scratch copy: removing the `WAKE_OWNED` guard fails both single-run stop tests. The check is recorded here, not committed.

## Issues Encountered

- `uv run pyright --version` prints a "new version available" notice; it is a notice only, the checker runs (1.1.410) and reports 0 errors.
- The live pi refusal and pi discovery of the skill are not exercised here: this plan uses fakes and the stub shim only. Those are confirmed by the owner's captures in 26-12, as the plan states.

## Verification

Run on HEAD `1bad074` (before this summary's own commit):

- `make validate` (all hooks, all files): rc=0. ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest (core) and unittest (wizard, uv) all Passed. The wizard-uv hook had failed on `tests.test_wizard_pty` until commit `1bad074`.
- `make test-unit` (run rule 13): rc=0; `unit` 61/61 modules, `unit-uv` 1/1.
- `uv run pyright` (whole tree, tests included): 0 errors, 0 warnings, rc=0; also `make pyright` (the pre-commit hook target): Passed.
- Each plan `<verify>` command re-run verbatim: Task 1 and Task 2 pass; Task 3's `TestSessionWakeStep` classes pass and its `make test-unit` gate passes.
- Red-first pins: the `doc_block_env` raise test, the superpowers close-condition test and the wizard HOOKS-row test were each run red before their fix. The raise test was also run red against a mutant with the raise removed.
- Non-vacuity: removing the `WAKE_OWNED` guard from the gsd and superpowers re-arm blocks in a scratch copy fails the single-run stop tests.
- Clean-tree pyright: `git archive HEAD` exported to `/tmp` with `uv sync --frozen` and `uv run pyright`: 0 errors. The same export nested under the repo reported spurious errors (its project root resolved to the worktree); recorded so it is not mistaken for a result.
- No runner-spawned grandchildren left running; no `gc.pid` in the repo root; the working tree is clean.
