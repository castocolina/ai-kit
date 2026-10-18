---
phase: 20-live-validation-on-codex-opencode
plan: 05
subsystem: testing
tags: [opencode, cross-ai, smoke, evidence]
requires:
  - phase: 20-live-validation-on-codex-opencode
    provides: "Template-4 standalone runner and host-aware smoke harness"
provides:
  - "Headless opencode smoke and host environment evidence"
  - "Effort suffix, controlled-path enumeration, and signal-probe findings"
affects: [20-06, 20-07]
actuals:
  tokens: 25500
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - "Headless opencode dispatch through template-4 cross-ai runner with standalone server"
    - "Evidence-only success requires runner status plus host-written smoke outcome"
key-files:
  created:
    - .planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-OPENCODE.md
  modified: []
key-decisions:
  - "Accepted no_change with cli_rc=0 as healthy evidence-only dispatch, with smoke exit 0 as independent proof."
  - "Recorded the env-signal validation failure and unverified second-signal behavior rather than claiming clean outcomes."
requirements-completed: [EVAL-05]
coverage:
  - id: D1
    description: "Headless opencode smoke ran on a standalone server with a green host-detected 420-check harness run, local installs, planned-equals-baked results, artifacts, and protected-set guard."
    requirement: EVAL-05
    verification:
      - kind: e2e
        ref: "tmp/p20/headless/opencode-smoke.log and tmp/p20/headless/opencode-artifacts"
        status: pass
      - kind: other
        ref: "python3 tests/gsd_curated_eval.py snapshot --check tmp/p20/plan04.before.json --scratch-root <smoke scratch>"
        status: pass
    human_judgment: true
    rationale: "Headless evidence is preliminary; EVAL-05 acceptance requires the user's interactive opencode session and review-lane trials."
  - id: D2
    description: "Effort suffix acceptance, controlled-PATH enumeration, and signal handling probes have explicitly bounded findings."
    requirement: EVAL-05
    verification:
      - kind: other
        ref: "20-SMOKE-OPENCODE.md sections Effort suffix probe and Deferred-in items"
        status: pass
    human_judgment: true
    rationale: "The inherited PI_CODING_AGENT signal check failed, C-W12 failure was not provoked, and the double-signal timing was not established."
duration: 14min
completed: 2026-10-18
status: complete
---

# Phase 20 Plan 05: Opencode headless validation summary

**Opencode headless evidence records a green isolated smoke, accepted-but-unverified `#high` suffix, controlled enumeration, and signal-probe limits.**

## Performance

- **Duration:** About 14 minutes across two executor turns.
- **Started:** 2026-10-18T09:06:07Z
- **Completed:** 2026-10-18T09:21:01Z
- **Tasks:** 3
- **Files modified:** 2 (smoke evidence and this summary)

## Accomplishments
- Dispatched the host smoke through this repository's template-4 runner with `--prefer opencode` alone, `--no-preamble`, and the rendered `--standalone` argv. Continuation run finished healthy as `no_change` (`cli_rc=0`) and the independent smoke log recorded exit 0 and all ten steps passing.
- Recorded the 420-check matrix, two local 1.17.0 installs, planned == baked for 35 agents, idempotent reinstall, generated paths, retained artifacts, and protected configuration guard.
- Probed `router-env/my-coding#high`: opencode accepted the suffix in the model id, but whether effort was applied remains unverified.
- Ran unseeded inventory with controlled PATH exposing only opencode and confirmed `runtime_enumeration.opencode: ok`; the shared service listing was read-only and its pre-existing process remained untouched.
- Ran two signal probes with `sleep 170`, run-owned TMPDIRs, and runner pgid files; readiness and process-group cleanup were recorded.

## Task Commits

1. **Task 1: Opencode headless smoke evidence** - `589dba3` (`docs(20-05): record opencode headless smoke evidence`)
2. **Task 2: Effort and enumeration probe evidence** - `9171426` (`docs(20-05): record effort and enumeration probes`)
3. **Task 3: Final signal-probe evidence** - included in `589dba3` because all three tasks shared one evidence artifact and task 1 had committed the initial complete evidence; subsequent completion was recorded in this summary. (No separate task-3 commit was made.)

**Plan metadata:** summary commit follows.

## Files Created/Modified
- `.planning/phases/20-live-validation-on-codex-opencode/20-SMOKE-OPENCODE.md` - headless smoke, environment names, effort probe, enumeration and signal findings.
- `.planning/phases/20-live-validation-on-codex-opencode/20-05-SUMMARY.md` - this execution summary.

## Decisions Made
- Treated `no_change` with `cli_rc=0` as healthy for an evidence-only run, while requiring the harness smoke exit and full evidence independently.
- Preserved the PI detection-signal leakage and unsuccessful second-signal delivery as explicit failures/unverified outcomes rather than relabeling them clean.

## Deviations from Plan

### Probe limitations and continuation

**1. First smoke dispatch was interrupted before runner completion**
- **Found during:** Task 1, first executor turn.
- **Issue:** Smoke produced exit 0 and ten passing steps, but the standalone runner remained active without a final AIKIT-XAI line; the executor session was terminated around 307 seconds.
- **Handling:** On continuation, repeated the plan's Task 1 runner command with a fresh pgid file in the background. It completed independently after 89 seconds with a healthy `no_change` line; original run's recorded child group was dead by the time of the continuation.
- **Files modified:** Smoke evidence.
- **Verification:** Continuation status and smoke log; snapshot guard.
- **Commit:** `589dba3`.

**2. Env four-set validation found inherited `PI_CODING_AGENT`**
- **Found during:** Task 1.
- **Issue:** The names-only dump included `PI_CODING_AGENT`, a detection/scrub signal not in opencode's own signal/scrub/generic allow set.
- **Handling:** Recorded the failed check verbatim; did not claim `signals clean`.
- **Files modified:** Smoke evidence.
- **Verification:** The four-set check returned `bad=['PI_CODING_AGENT']`.
- **Commit:** `589dba3`.

**3. Immediate second-signal behavior was not verified**
- **Found during:** Task 3.
- **Issue:** The wrapper completed after the first SIGTERM before the second kill could be delivered (`No such process`).
- **Handling:** Recorded the attempted 0.3-second interval and explicitly left the immediate-second-signal behavior unverified. All pgid groups were checked empty.
- **Files modified:** Smoke evidence.
- **Verification:** Both signal status lines and pgid-file cleanup checks.
- **Commit:** `589dba3`.

**Total deviations:** 3 recorded evidence limitations; no product/harness edits. **Impact:** Headless smoke and the suffix acceptance are supported; interactive EVAL-05, env-clean signal status, and immediate double-signal behavior remain unproven.

## Issues Encountered
- The first executor command was terminated by the outer session while the runner still waited after the smoke. The continuation rerun completed; the first run had no final status line and is retained as an incomplete attempt.
- The opencode env dump's four-set test failed on inherited `PI_CODING_AGENT`; this is not a clean env result.
- The shared-service `opencode models` preflight is read-only but is not standalone; no managed-service process was touched.
- EVAL-05 is not claimed: the interactive run and required two review-lane trials remain pending in `20-INTERACTIVE-OPENCODE.md`.

## Process proof

- Task 1 continuation: original `opencode-run1.pgid` child 118717 and its recorded children were no longer alive after the interrupted dispatch. Continuation `opencode-run2.pgid` listed six preflight/git groups and the opencode child 141396, followed by five later child groups; all were exited by runner finalization. The run completed with no plan-started CLI process left.
- Task 2: unseeded inventory's ps before/after `opencode serve` listings were identical and showed only the pre-existing managed `--service` process. The private `opencode serve --hostname 127.0.0.1 --port 0` image probe was gone after inventory. Controlled PATH and cache directories were removed.
- Task 3 run 1: readiness live child 159620 (`opencode run`), `sleep 170` observed; every recorded group from `opencode-signal1.pgid` was empty. No `cross-ai-*` or `xai-*` runner temp directory remained; run-owned TMPDIR removed.
- Task 3 run 2: readiness live child 162453 (`opencode run`), `sleep 170` observed; every recorded group from `opencode-signal2.pgid` was empty. No `cross-ai-*` or `xai-*` runner temp directory remained; run-owned TMPDIR removed. Second kill came after wrapper completion.
- Process listings before/after are preserved at `tmp/p20/headless/ps-before-05.txt` and `ps-after-05.txt`; unrelated pre-existing opencode service and host processes remain untouched. No fake `gc-late`/`node -e while` processes were listed.

## Environment findings
- Smoke continuation passed; first smoke runner stayed live after host smoke exit 0, with no final status. No managed-service port conflict.
- `PI_CODING_AGENT` was inherited and caused four-set validation to fail.
- C-W12 `runtime_enumeration.opencode` was `ok`; failure not provoked.
- Signal run 2's second SIGTERM was not delivered to a live wrapper. No billing/quota or external-directory denial observed.

## Verification
- Task 1 required automated evidence gates passed except the plan-required four-set check, which truthfully failed due to inherited `PI_CODING_AGENT`; this failure is recorded in the evidence and summary.
- Task 2 automated section, accepted/rejected verdict, controlled runtime enumeration, secret scan and snapshot checks passed.
- Task 3 final checks passed: at least two signal status lines and readiness lines, pgid references, no pending placeholder, secret scan clean, no home path, and snapshot `snapshot ok`.
- Secret scan on smoke evidence: pass.
- Snapshot check against 20-04 pre-plan snapshot with smoke scratch exemption: `snapshot ok`.
- Commit hooks passed on both commits.

## Next Phase Readiness
- Headless opencode evidence is available for 20-06 and 20-07. Interactive EVAL-05 evidence, precedence observation and required D-11 trials remain with the user's 20-07 script.

---
*Phase: 20-live-validation-on-codex-opencode*
*Completed: 2026-10-18*
