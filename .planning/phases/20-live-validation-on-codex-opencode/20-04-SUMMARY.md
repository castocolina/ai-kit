---
phase: 20-live-validation-on-codex-opencode
plan: 04
subsystem: testing
tags: [codex, cross-ai, smoke, evidence]
requires:
  - phase: 20-live-validation-on-codex-opencode
    provides: "Template-4 runner and host-aware smoke harness with Codex-local install support"
provides:
  - "Headless Codex smoke evidence, names-only host environment, and smoke artifacts"
  - "Codex JSON event, controlled-PATH enumeration, and signal-probe results"
affects: [20-05, 20-06, 20-07]
actuals:
  tokens: 9900
  tasks: 3
  commits: 4
tech-stack:
  added: []
  patterns:
    - "Headless host smoke dispatched through the repo's cross-AI runner with a single preferred CLI"
    - "Names-only environment evidence and temporary controlled PATH for runtime enumeration"
key-files:
  created:
    - .planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-CODEX.md
    - .planning/phases/20-live-validation-on-codex-opencode/20-04-SUMMARY.md
  modified: []
key-decisions:
  - "Accept no_change with cli_rc=0 as the expected healthy result for a clean-tree evidence-only dispatch; independently require the smoke's exit 0 and full evidence."
  - "Record the failed-listing and immediate second-signal behaviors as unverified when the chosen probes did not provoke them."
requirements-completed: [EVAL-04]
coverage:
  - id: D1
    description: "Codex headless smoke, env names, 420-check matrix, planned/baked comparison, protected-set guard, and generated artifacts are recorded."
    requirement: EVAL-04
    verification:
      - kind: e2e
        ref: "tmp/p20/headless/codex-smoke.log and tmp/p20/headless/codex-artifacts"
        status: pass
      - kind: other
        ref: "python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/plan04.before.json --scratch-root /tmp/smoke-2ioanybo"
        status: pass
    human_judgment: true
    rationale: "This is a headless iteration; the phase requires the user's own interactive Codex session for EVAL-04 acceptance."
  - id: D2
    description: "Codex event sequence, controlled-PATH enumeration, and signal handling probes are preserved with honest unprovoked/deviated outcomes."
    verification:
      - kind: other
        ref: "20-SMOKE-CODEX.md Deferred-in items"
        status: pass
    human_judgment: true
    rationale: "The failed model-listing path and second-signal immediate-kill timing were not successfully provoked."
duration: 12min
completed: 2026-10-18
status: complete
---

# Phase 20 Plan 04: Codex headless validation summary

**Codex smoke evidence records a successful host-detected 420-check run, names-only env signals, protected configuration state, and deferred runner probes.**

## Performance

- **Duration:** About 12 minutes
- **Started:** 2026-10-18T08:59:38Z
- **Completed:** 2026-10-18T09:15:00Z
- **Tasks:** 3
- **Files modified:** 1 evidence file (plus this summary)

## Accomplishments
- Dispatched the Codex smoke from the repository root through template-4 `cross-ai.mjs` with `--no-preamble`, one preferred CLI, and `workspace-write`; recorded healthy `no_change` semantics and the independent `smoke exit=0` evidence.
- Captured names only from Codex's tool environment, verified the four-set signal rule, confirmed both `CODEX_THREAD_ID` and `CODEX_VERSION`, and recorded inherited Claude/PI environment names without values.
- Recorded all smoke steps green, local Codex installs at 1.17.0, 420 matrix checks, planned == baked, generated paths, eight artifacts, and an unchanged protected set.
- Recorded one scrubbed Codex JSON event sequence and a codex-only unseeded inventory under a controlled PATH.
- Probed SIGTERM after observing `codex exec` and its `sleep 170` descendant; recorded process-group and run-owned TMPDIR cleanup for both probes.

## Task Commits

1. **Task 1: Codex headless smoke evidence** - `af00a94` (`docs(20-04): record codex headless smoke evidence`)
2. **Task 2: Codex enumeration and stream probes** - `194eef1` (`docs(20-04): record codex enumeration and stream probes`)
3. **Task 3: Codex signal probe results** - `5e3e70f` (`docs(20-04): record codex signal probe results`)

**Plan metadata:** summary commit follows.

## Files Created/Modified
- `.planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-CODEX.md` - Codex headless smoke, env names, artifact index, enumeration and signal-probe evidence.
- `.planning/phases/20-live-validation-on-codex-opencode/20-04-SUMMARY.md` - This execution summary.

## Decisions Made
- Treated `no_change` with `cli_rc=0` as healthy for a clean-tree evidence-only runner call, while separately requiring the harness smoke exit and evidence to pass.
- Reported probes that did not reach their intended failure/signal state as unverified rather than inferring behavior.

## Deviations from Plan

### Auto-fixed/recorded probe limitations

**1. C-W12 failure probe did not provoke a listing failure**
- **Found during:** Task 2
- **Issue:** A fresh temporary `CODEX_HOME` still produced `runtime_enumeration.codex: ok`.
- **Handling:** Recorded the attempted probe as not provoked; did not claim failed-versus-empty behavior.
- **Files modified:** `.planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-CODEX.md`
- **Verification:** Controlled-PATH inventory reported only `codex`; snapshot remained `snapshot ok`.
- **Commit:** `194eef1`

**2. Second SIGTERM arrived after the supervised runner had exited**
- **Found during:** Task 3
- **Issue:** First signal produced the expected one `status=signal` line and exited within the runner's short signal window, before the second kill command could reach the wrapper.
- **Handling:** Recorded the 0.302-second attempted spacing and explicitly left immediate second-signal group-kill behavior unverified.
- **Files modified:** `.planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-CODEX.md`
- **Verification:** Both runs had exactly one signal status line; all recorded process groups were empty and both owned TMPDIRs had no runner temp directories.
- **Commit:** `5e3e70f`

**Total deviations:** 2 probe limitations recorded; no product or harness defect found. **Impact:** Smoke and single-signal findings are usable; the two unprovoked behaviors remain explicit follow-up evidence gaps.

## Issues Encountered
- A grep for the actual home directory found that scratch-only helper files inside the ignored `tmp/` tree contained temporary absolute paths. Those files were never copied into committed evidence; the tracked evidence passes both `secret-scan` and the exact-home grep.
- The outer ps diff contains concurrent pre-existing Codex/opencode/runner processes and the supervisor itself, so it is not an empty whole-system diff. The runner's own recorded child groups were checked individually and all were dead; no process from this plan remained. The user's managed opencode service was left untouched.
- EVAL-04 acceptance is not claimed: the interactive run is still pending for the user in `20-INTERACTIVE-CODEX.md`.

## Process proof

- Task 1 `ps-before.txt` and `ps-after.txt`: system-wide list includes concurrent pre-existing runner/Codex/opencode activity; no Codex smoke child remains. All 12 recorded groups in `codex-run1.pgid` had no members after the smoke.
- Task 2 ps records before and after each controlled inventory show only the pre-existing `opencode serve --service`; no new `detect-runtimes` process remained. Temporary PATH, XDG cache and CODEX_HOME directories were removed.
- Task 3: readiness was observed on live Codex child PIDs 105521 and 106788 with `sleep 170` descendants. Every pid group recorded in `codex-signal1.pgid` and `codex-signal2.pgid` was empty after the respective run. `cross-ai-*`/`xai-*` checks were empty; both run-owned TMPDIRs were removed.
- Final `ps -eo pid,args | grep -E 'gc-late|node -e while' | grep -v grep`: no output. No plan-started Codex, opencode, cross-ai or fake-grandchild process remains.

## Environment findings
- The Codex JSON and controlled-PATH inventory outcomes, unprovoked failure probe, and double-signal limitation are listed in `20-SMOKE-CODEX.md`; no permission, quota, capacity, or sandbox blocker occurred.

## Redactions
- No committed evidence redactions required. Evidence contains no home path or environment-variable values; raw scratch stays under gitignored `tmp/`.

## Verification
- Task 1 automated verification: passed, including smoke exit 0, host detection, local scope/root, all-equal baked models, protected-set unchanged, names-only env and signal check, artifact existence, secret scan, and snapshot check.
- Task 2 automated verification: passed, including event sequence and not-provoked recovery note, controlled PATH proof, secret scan, and snapshot check.
- Task 3 automated verification: passed for two readiness records, two signal status lines, pgid-file references, TMPDIR check, secret scan, snapshot guard, and no pending Task 3 placeholder.
- `secret-scan` on committed evidence: pass.
- `snapshot --check ... --scratch-root <smoke scratch>`: `snapshot ok`.
- Commit hooks: passed on all three task commits.

## Next Phase Readiness
- The codex headless evidence is available to plans 20-05 and 20-06. Interactive EVAL-04 proof remains assigned to the user's 20-07 run.

---
*Phase: 20-live-validation-on-codex-opencode*
*Completed: 2026-10-18*
