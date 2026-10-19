---
phase: 21-cursor-live-validation
plan: 05
subsystem: testing
tags: [cursor, label-lift, skill-judge, evidence, curated-config]
requires:
  - phase: 21-03
    provides: The green cursor matrix (`matrix ok (420 checks)`) that is R2 of the lift condition
  - phase: 21-04
    provides: The headless smoke evidence (`21-SMOKE-CURSOR.md`) with the single one-attempt `headless verdict: green` line the lift keys on
  - phase: 21-07
    provides: The template-5 runner through which the pi judge dispatch ran
provides:
  - The cursor Limits row split (`pi hosts` keeps `not live-validated`; cursor row reads `validated headless ... **pending**`, citing 21-SMOKE-CURSOR.md)
  - The README skill row update and the `test_cursor_label_lifted_with_evidence_pointer` pin
  - The dated two-step-lift amendment in 21-SPEC.md R3 and ROADMAP Phase 21 SC2, in the same commit as the evidence
  - The skill-judge evidence (`21-SKILL-JUDGE.md`, `skill-judge/*.md`) with an explicit BLOCKED verdict
affects: [21-06]
actuals:
  tokens: 2100
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "Two-step label lift: headless evidence earns only the qualified `validated headless ... interactive confirmation pending` wording; the `pending` note is removed only in the commit recording the user's interactive run (Phase 20 codex precedent, written into SPEC R3 and ROADMAP SC2 in the evidence commit)"
    - "Judge reports carry a `DIGEST <digest>` line stating which tree they scored; a pending in-session marker is a BLOCKED verdict that 21-06's precondition refuses, never a soft note"
key-files:
  created:
    - .planning/phases/21-cursor-live-validation/skill-judge/in-session.md
    - .planning/phases/21-cursor-live-validation/skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md
    - .planning/phases/21-cursor-live-validation/21-SKILL-JUDGE.md
  modified:
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - README.md
    - tests/test_curated_config_apply.py
    - .planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md
    - .planning/phases/21-cursor-live-validation/21-SPEC.md
    - .planning/ROADMAP.md
key-decisions:
  - "Task 1 took the LIFT branch: exactly one `headless verdict: green (attempt 1: ...)` line in 21-SMOKE-CURSOR.md, `matrix ran: 420 checks` in the smoke body and 21-03's `matrix ok (420 checks)` — the condition keyed on one identified attempt, never on success strings found anywhere."
  - "The lift is qualified, never bare: the cursor row names the headless session evidence and keeps the user's interactive confirmation (`21-INTERACTIVE-CURSOR.md`) as **pending**, a mandatory human-verification item; the phase ends `human_needed` until that run is recorded."
  - "The rule permitting the two-step lift was amended formally (review cycle 2, orchestrator decision on the Phase 20 codex precedent) into 21-SPEC.md R3 and ROADMAP SC2 in the same commit as the evidence, per AGENTS.md's amend-formally rule; ROADMAP diff is 1 added/1 removed line in the Phase 21 entry only."
  - "The pi judge hit `status=quota` (subscription sharing usage limit) on both attempts (one retry after 60 s per plan), so the pi row records `judge unavailable` verbatim; the verdict is `BLOCKED: in-session judge pending (orchestrator)`, which 21-06 Task 2's precondition refuses until the orchestrator replaces the marker with a real report."
patterns-established:
  - "Label-branch selection is read from the evidence file at execution time and recorded in tmp/p21/label-branch.txt; the verify re-implements the same condition (one verdict line, R2 lines) and asserts SKILL.md/README/test state matches the branch."
  - "Judge attempt accounting records every `AIKIT-XAI` line verbatim in `## Judge attempts`, including quota failures, so an unavailable judge is explicit evidence rather than an absence."
requirements-completed: [EVAL-07]
coverage:
  - id: D1
    description: "Cursor's `not live-validated` label is replaced by the qualified `validated headless ... interactive confirmation pending` wording, bound to one identified headless attempt and the recorded 420-check matrix, with `pi hosts` keeping the label."
    requirement: EVAL-07
    verification:
      - kind: unit
        ref: tests/test_curated_config_apply.py#test_cursor_label_lifted_with_evidence_pointer (with test_required_statements; 8 tests OK)
        status: pass
      - kind: other
        ref: "Task 1 verify consistency check: branch LIFT == one `headless verdict: green (attempt N` line + `matrix ran: 420 checks` + `^matrix ok (420 checks)$`; combined row absent; `pending` in the lifted row; Limits heading date `2026-10-18` unchanged"
        status: pass
      - kind: other
        ref: "python3 tests/gsd_curated_eval.py secret-scan 21-SMOKE-CURSOR.md; `$HOME` grep; snapshot --check tmp/p21/plan05.before.json -> snapshot ok"
        status: pass
    human_judgment: false
  - id: D2
    description: "The two-step lift rule is written into the sources it departs from: 21-SPEC.md R3 amendment blockquote and ROADMAP Phase 21 SC2 amendment, both dated 2026-10-18, in the same commit as the evidence, quoted in the `## Label lift` section."
    requirement: EVAL-07
    verification:
      - kind: other
        ref: "Task 1 verify greps: `Amended 2026-10-18 (review cycle 2, 21-05` in 21-SPEC.md; `validated headless (interactive confirmation pending)` in ROADMAP.md; old SC2 sentence absent; amendment quoted in 21-SMOKE-CURSOR.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Phase 21 SKILL.md change has its skill-judge evidence: both judge rows attempted, every report carries a `DIGEST` line, verdict derived from the decision table and re-checked by the verify."
    requirement: EVAL-07
    verification:
      - kind: other
        ref: "21-SKILL-JUDGE.md: BLOCKED verdict, JUDGED_COMMIT 3a36abdbbf5c, digest --check ok, both reports' DIGEST lines equal the current tree digest b924ac84e1d6d3c9, secret-scan and $HOME grep clean, snapshot ok"
        status: pass
    human_judgment: false
  - id: D4
    description: "The in-session judge row and the pi judge's real score — the gate cannot pass until the orchestrator's real in-session report (score >= 109, pi >= 116, CRITICAL 0, IMPORTANT 0, matching digest) replaces the pending marker and the pi judge re-runs past the quota window."
    verification: []
    human_judgment: true
    rationale: "The in-session judge requires the orchestrator's Skill tool (a cross-AI executor has none, by design); the pi judge's quota state is external to this repo and cannot be forced. The pending marker is an explicit BLOCKED hand-off that 21-06 Task 2's precondition refuses — automation cannot certify a judge that did not run."
duration: 10min
completed: 2026-10-19
status: complete
---

# Phase 21 Plan 05: Cursor label lift Summary

**Cursor's `not live-validated` label lifted to the qualified `validated headless ... interactive confirmation pending` wording on one identified green headless attempt plus the 420-check matrix, with the two-step-lift rule amended into 21-SPEC.md R3 and ROADMAP SC2 in the evidence commit, and the skill-judge gate recorded as `BLOCKED: in-session judge pending (orchestrator)` after the pi judge hit quota on both attempts.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-10-19T02:24:05Z
- **Completed:** 2026-10-19T02:33:35Z
- **Tasks:** 2
- **Files modified:** 8 (+3 created)

## Accomplishments
- LIFT branch selected from the evidence at execution time: exactly one `headless verdict: green (attempt 1: ...)` line, `matrix ran: 420 checks`, and 21-03's `matrix ok (420 checks)`; recorded in `tmp/p21/label-branch.txt` and re-checked by the verify.
- SKILL.md Limits row split: `pi hosts` keeps `**not live-validated**`; the `cursor host` row cites `21-SMOKE-CURSOR.md` (local install, apply, resolve-model-only chain, 420-check matrix) and names the user's interactive confirmation (`21-INTERACTIVE-CURSOR.md`) as **pending** — never a bare lift.
- README skill row updated (`pi not live-validated; cursor validated headless (interactive confirmation pending)`) and `test_cursor_label_lifted_with_evidence_pointer` pins the wording so a future edit cannot silently re-label or over-claim; `test_required_statements` still requires the pi `not live-validated` literal.
- The dated two-step-lift amendment (review cycle 2, Phase 20 codex precedent) written into 21-SPEC.md R3 and ROADMAP Phase 21 SC2 in the same commit, quoted in 21-SMOKE-CURSOR.md's `## Label lift` section; ROADMAP diff is 1+/1- in that entry only.
- Skill-judge evidence: pi judge ran through this repo's template-5 runner under the 1800 s budget (1712 s and 1615 s remaining before the two attempts); both attempts returned `status=quota` (one retry per plan), so the pi row records `judge unavailable` verbatim with its `DIGEST` line; the in-session row is the executor's pending marker with `DIGEST b924ac84e1d6d3c9`.
- Verdict `BLOCKED: in-session judge pending (orchestrator)` — an explicit hand-off, not a pass; 21-06 Task 2's precondition refuses any `pending (orchestrator)` marker, so the phase cannot close until the orchestrator replaces it with a real report and the pi judge re-runs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Conditional qualified lift in SKILL.md and README with the test pin, and the SPEC R1/R3 + ROADMAP SC2 amendment, in one commit with the evidence section** - `3a36abd` (docs)
2. **Task 2: skill-judge loop on the committed SKILL.md; 21-SKILL-JUDGE.md** - `6398361` (docs)

## Files Created/Modified
- `skills/ai-kit-gsd-curated-config/SKILL.md` - Limits row split (pi keeps the label; cursor row qualified-headless, `pending` interactive confirmation)
- `README.md` - skill row: `pi not live-validated; cursor validated headless (interactive confirmation pending)`
- `tests/test_curated_config_apply.py` - `test_cursor_label_lifted_with_evidence_pointer`
- `.planning/phases/21-cursor-live-validation/21-SMOKE-CURSOR.md` - `## Label lift` section quoting the verdict line, the R2 lines, the changed files and the amendment
- `.planning/phases/21-cursor-live-validation/21-SPEC.md` - dated amendment blockquote under R3's Acceptance line
- `.planning/ROADMAP.md` - Phase 21 SC2 amended to the two-step wording (1+/1-)
- `.planning/phases/21-cursor-live-validation/21-SKILL-JUDGE.md` - judge decision table, rounds, attempts, single BLOCKED verdict
- `.planning/phases/21-cursor-live-validation/skill-judge/in-session.md` - pending marker + `DIGEST b924ac84e1d6d3c9`
- `.planning/phases/21-cursor-live-validation/skill-judge/ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh.md` - `judge unavailable` report + `DIGEST` line

## Decisions Made
- LIFT over KEEP: the evidence condition (one green verdict line + both R2 lines) held; the branch was read from the files, never from memory.
- The amendment text is quoted verbatim in `## Label lift` so the evidence names the rule it was lifted under.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The pi judge returned `status=quota` (ChatGPT subscription sharing usage limit) on both attempts; the plan's one retry after 60 s was used, after which the plan mandates `judge unavailable`. The verdict precedence then selects `BLOCKED: in-session judge pending (orchestrator)`. This is the plan's designed hand-off, not a failure to work around.
- `$HOME` paths appeared in the scratch `.err` files (spawn argv echo, not the reports); they were redacted to `<home>` before the batch move and are listed here per the plan. The committed reports under `skill-judge/` and the evidence pass the `$HOME` grep.
- The initial 21-SKILL-JUDGE.md wrote `JUDGED_COMMIT` with the sha inside backticks, which the verify's `JUDGED_COMMIT: [0-9a-f]{7,}` grep cannot match; fixed by removing the backticks and amending the evidence commit before the verify ran.

## Next Phase Readiness
- 21-06 can proceed on the label/evidence side; its Task 2 precondition blocks phase close until the orchestrator replaces the in-session pending marker with a real report and the pi judge re-runs past the quota window.
- The digest under judgment is `b924ac84e1d6d3c9` (post-LIFT tree); any SKILL.md fix from a future judge round re-keys the digest.

---
*Phase: 21-cursor-live-validation*
*Completed: 2026-10-19*
