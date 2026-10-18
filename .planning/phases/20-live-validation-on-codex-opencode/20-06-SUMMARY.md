---
phase: 20-live-validation-on-codex-opencode
plan: 06
subsystem: testing
tags: [codex, opencode, detection, curated-config, skill-judge]
requires:
  - phase: 20-05
    provides: Headless Codex and opencode smoke evidence
provides:
  - Codex host-signal labels and dated requirements/context/spec amendments based on recorded names-only evidence
  - GSD-generated gitignore-prefix follow-up notes and evidence-bounded installer/effort labels
  - Skill-judge gate PASS on digest 2663ee4bf6433cc1 (in-session 109 0/0, pi 116 0/0), completed by the orchestrator
 affects: [20-07, ai-kit-gsd-curated-config, ai-kit-spec-review]
actuals:
  tokens: 0
  tasks: 2
  commits: 5
tech-stack:
  added: []
  patterns: [Evidence-bounded detection labels; follow-up notes report generated path prefixes without editing gitignore]
key-files:
  created:
    - .planning/phases/20-live-validation-on-codex-opencode/20-SKILL-JUDGE.md
    - .planning/phases/20-live-validation-on-codex-opencode/skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md
    - .planning/phases/20-live-validation-on-codex-opencode/skill-judge/in-session.md
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
    - .planning/REQUIREMENTS.md
    - .planning/phases/20-live-validation-on-codex-opencode/20-SPEC.md
    - .planning/phases/20-live-validation-on-codex-opencode/20-CONTEXT.md
requirements-completed: [EVAL-04, EVAL-05]
coverage:
  - id: D1
    description: Codex signal labels, their table tests, and dated source-of-truth amendments reflect headless names-only evidence while leaving TUI confirmation pending.
    requirement: EVAL-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_spec_runtimes_table and tests.test_ai_kit_spec
        status: pass
      - kind: other
        ref: node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test
        status: pass
    human_judgment: false
  - id: D2
    description: Curated-config reports GSD gitignore prefixes and updates evidence-supported notes without editing .gitignore.
    requirement: EVAL-05
    verification:
      - kind: unit
        ref: tests.test_curated_config_followups, tests.test_curated_config_cross_ai, tests.test_curated_config_apply, tests.test_curated_config_recommend, tests.test_curated_config_golden
        status: pass
    human_judgment: false
  - id: D3
    description: SKILL.md judge gate PASS (in-session 109/120 0/0, pi 116/120 0/0 on digest 2663ee4bf6433cc1).
    verification:
      - kind: other
        ref: .planning/phases/20-live-validation-on-codex-opencode/20-SKILL-JUDGE.md
        status: unknown
    human_judgment: true
    rationale: The executor left the in-session row as the pending marker (no Skill tool); the orchestrator ran it, made two more SKILL.md fix commits (dd1ab1e, c7089ff) and re-ran both judges; see 20-SKILL-JUDGE.md.
duration: 18min
completed: 2026-10-18
status: halted
---

# Phase 20 Plan 06 Summary

**Codex headless detection and curated-config follow-up guidance now reflect the recorded evidence; the skill-judge gate passed after the orchestrator's in-session judge and fix round.**

## Performance

- **Duration:** 18 min (plan timer; excludes any earlier work summarized before this dispatch)
- **Started:** 2026-10-18T09:24:15Z
- **Completed:** 2026-10-18T09:42:29Z
- **Tasks:** Tasks 1-3 completed (Task 3's in-session judge and final verdict by the orchestrator)
- **Files modified:** 21 across task commits and judge evidence (including this summary is not included)

## Accomplishments

- Kept both `CODEX_THREAD_ID` and `CODEX_VERSION` as Codex detection signals because both appeared in the headless environment names; labels and docs explicitly leave TUI confirmation pending. Added the required dated amendments to REQUIREMENTS.md, 20-SPEC.md, and 20-CONTEXT.md. The runner template was not changed because neither signal was dropped.
- Added opencode/Codex gitignore-prefix follow-up reporting and documented that curated-config reports but never edits `.gitignore`. The opencode root and cached Codex installer notes claim only what the smoke exercised; the effort suffix was accepted, while whether effort is applied remains unverified. Effort sync with `--config-dir` remains unverified.
- Pi judge initially scored 115/120 with one Important finding. After one focused SKILL.md edit, it scored 114/120 with zero Critical/Important findings, meeting the Phase 19 pi floor. The required in-session judge was unavailable in this executor; the pending marker is explicitly not a pass.

## Task Commits

1. **Task 1: Align Codex detection with headless evidence** — `2e8aaff` (`fix(20-06): align Codex detection with headless evidence`)
2. **Task 2a: Report GSD gitignore prefixes** — `759fc35` (`feat(20-06): report GSD gitignore prefixes`)
3. **Task 2b: Update evidence-bound follow-up labels** — `785593c` (`fix(20-06): update follow-up evidence labels`)
4. **Judge fix round: Remove repeated host-lane reminder** — `94f4806` (`fix(20-06): remove repeated host-lane reminder`)
5. **Judge evidence** — `1b00336` (`docs(20-06): record skill judge evidence`)

**Plan metadata:** completed by the orchestrator (see Orchestrator completion).

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` — evidence-bound labels for the two observed Codex variables.
- `tests/test_ai_kit_spec_runtimes_table.py`, `tests/test_ai_kit_spec.py` — signal and scrub-set regression pins.
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py` — gitignore-prefix notes and evidence-bounded installer/root text.
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py`, `cross_ai.py` — evidence-bound root/effort wording.
- `skills/ai-kit-gsd-curated-config/SKILL.md` and tests/goldens — documented host-lane policy, gitignore notes, and updated evidence language.
- `.planning/REQUIREMENTS.md`, `20-SPEC.md`, `20-CONTEXT.md` — dated amendments.
- `20-SKILL-JUDGE.md` and `skill-judge/` — pi reports and the explicit in-session pending marker.

## Decisions Made

- Both observed headless Codex environment names remain detection signals; only interactive TUI evidence can settle later removal.
- Opencode effort-suffix acceptance is not evidence that effort takes effect. The note retains that uncertainty.
- The executor's pi report passed its floor after one fix. The orchestrator's later rounds are recorded in 20-SKILL-JUDGE.md.

## Deviations from Plan

The executor could not invoke the in-session `skill-judge` Skill tool. Following the plan's orchestrator fallback, the report contains a pending marker and the verdict is `BLOCKED: in-session judge pending (orchestrator)`. The plan is intentionally halted rather than claiming completion or PASS. The orchestrator must replace the marker with a real report, update the judge verdict, run Task 3 verification, and then re-summarize as complete if both judge rows pass.

The judge surfaced one Important finding in its initial review: a repeated host-lane reminder. It was removed in `SKILL.md`, committed in `94f4806`, and the judge was rerun on the unchanged skill digest. The final pi report found no Critical or Important issues.

## Issues Encountered

- Initial secret scans flagged the expected runner stderr path containing `$HOME`; the path was redacted to `<home>`. Subsequent secret and home-path scans passed.
- The pi judge's final status was `ok`, with `tree=clean`; the before/after digest remained `1a79713ef16f7bff`.
- The initial self-test iteration noted in prior progress had no remaining fake-grandchild process; the final planned test suites and template self-test passed.

## Verification

Passed:

- `python3 -m unittest tests.test_ai_kit_spec_runtimes_table` (48 tests)
- `python3 -m unittest tests.test_ai_kit_spec` (693 tests)
- `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` (`self-test ok`)
- `python3 -m unittest tests.test_curated_config_golden` (15 tests)
- `python3 -m unittest tests.test_curated_config_followups tests.test_curated_config_cross_ai tests.test_curated_config_apply tests.test_curated_config_recommend` (302 tests)
- Judge digest check and snapshot check (`digests ok`, `snapshot ok`)
- Secret scan and `$HOME` scan after redaction

The full `make test` aggregate was not run.

## User Setup Required

None.

## Next Phase Readiness

Ready for 20-07 (interactive scripts and gates).

---
*Phase: 20-live-validation-on-codex-opencode*
*Completed: 2026-10-18*


## Orchestrator completion

- In-session `skill-judge` run by the orchestrator (Skill tool). While judging it found stale
  runner.md text (template-3 flag line, no `--standalone`, readiness floor, timeout ladder) and
  fixed it in dd1ab1e. pi then flagged one Important, verified in code: the host-lane guarantee is
  v2-only (v1 `detect-review-candidate` has no host exclusion); fixed in c7089ff (docs only, v1
  behavior unchanged).
- Final: digest `2663ee4bf6433cc1`, in-session 109/120 0/0, pi gpt-6.1-sol xhigh 116/120 0/0,
  verdict `PASS`. Cap accounting and the jev call (Laya fallback, own reasoning) are in
  20-SKILL-JUDGE.md; owner-review item.
