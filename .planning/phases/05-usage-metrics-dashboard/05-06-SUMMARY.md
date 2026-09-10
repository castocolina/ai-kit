---
phase: 05-usage-metrics-dashboard
plan: 06
subsystem: usage-metrics
tags: [usage-metrics, classification, pattern-mining, inferred-family]

requires:
  - "05-01 refined_commands schema with inferred_family/inferred_confidence columns"
  - "05-04 decomposer command_shape (simple | control_flow_script | unclassified) and family.family_of"
provides:
  - "classify_loop.py: normalize_skeleton, mine_recurring_shapes, infer_family_for_group, run_classification"
  - "refined_store.update_inferred_family (no commit; caller owns the transaction)"
  - "cli.py classify subcommand (never auto-triggered by run)"
affects: [05-usage-metrics-dashboard]

actuals:
  tokens: 115000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Reset-then-remine inside one BEGIN/commit/rollback: stale inferred_family is cleared when a group no longer qualifies"
    - "4-step lossy skeleton: $vars -> <VAR>, quoted spans -> <STR>, punctuation-aware tokenize, expect_command_name walk (skip existing placeholders)"
    - "Family inference via CURATED_SUBSTITUTIONS set membership, never family_of(token) != token"

key-files:
  created:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/classify_loop.py
    - .planning/phases/05-usage-metrics-dashboard/05-06-SUMMARY.md
  modified:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py
    - tests/test_ai_kit_usage_metrics.py

key-decisions:
  - "classify is reachable only via its own subcommand; run stays capture -> refine -> dashboard."
  - "DEFAULT_MIN_OCCURRENCES = 2 is a documented placeholder, not a researched constant (PRD: exact threshold TBD once real data volume is known)."
  - "infer_family_for_group uses a flat CURATED_SUBSTITUTIONS member set so a literal grep is recognized, not only rg."
  - "run_classification never writes family or command_shape; only inferred_family/inferred_confidence."
  - "SKILL.md is not edited by this plan; 05-05 (Wave 6) is the sole assembler of the final skill doc."

patterns-established:
  - "Pattern-mining is an explicit, user-initiated pass over already-refined SQLite, never a silent side effect of run."
  - "Transaction ownership lives at run_classification; update_inferred_family issues the UPDATE and does not commit."
  - "Gate registration is re-asserted after adding a new package module so Wave 1's Makefile/pre-commit/pyright wiring cannot silently drop it."

requirements-completed:
  - REQ-usage-metrics-classification-refinement-loop

coverage:
  - id: REQ-usage-metrics-classification-refinement-loop
    description: "Offline pattern-mining pass attaches LOW-confidence inferred_family to recurring control_flow_script/unclassified shapes"
    requirement: REQ-usage-metrics-classification-refinement-loop
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestClassifyLoop"
        status: pass
    human_judgment: false
  - id: PRD-EXAMPLE-CLASSIFY
    description: "PRD for-loop pair reduces to one skeleton and both rows get inferred_family=grep / inferred_confidence=LOW"
    requirement: REQ-usage-metrics-classification-refinement-loop
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestClassifyLoop.test_prd_for_loop_attaches_low_confidence_grep"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestClassifyLoop.test_normalize_skeleton_matches_prd_examples"
        status: pass
    human_judgment: false
  - id: PRD-CLASSIFY-TRIGGER
    description: "classify is never auto-triggered; run sequence stays capture -> refine -> dashboard"
    requirement: REQ-usage-metrics-classification-refinement-loop
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestClassifyLoop.test_run_subcommand_does_not_invoke_classify"
        status: pass
    human_judgment: false

completed: 2026-09-10
status: complete
---

# Phase 5 Plan 06: Classification Refinement Loop Summary

**Opaque `control_flow_script`/`unclassified` rows can now be mined for recurring structural shapes. Matching groups get a LOW-confidence `inferred_family`; `family`/`command_shape` stay as the decomposer set them. The pass is explicit (`classify`), never part of `run`.**

## Performance

- **Tasks:** 2
- **Files created:** 1 (plus this SUMMARY)
- **Files modified:** 3
- **Commits:** 3

## Accomplishments

- `classify_loop.normalize_skeleton` reduces both PRD for-loop examples (`for f in *.py; do rg pattern "$f"; done` and `for x in *.md; do rg other "$x"; done`) to the identical skeleton `for <VAR> in <ARG>; do rg <ARG> <STR>; done`. Step (4) of the walk leaves existing `<VAR>`/`<STR>`/`<ARG>` tokens untouched.
- `infer_family_for_group` treats a token as a candidate when it is a `CURATED_SUBSTITUTIONS` pair member (including a literal `grep`, not only `rg`) and is not a shell keyword. Exactly one candidate yields `(family_of(candidate), "LOW")`; zero or two+ yield `(None, None)`.
- `run_classification` runs inside one `BEGIN`/`commit` (`rollback` on exception): reset every opaque row's inference columns, remine, then `update_inferred_family` on every row in a successfully inferred group. A higher threshold on a later run clears stale annotations; a lower threshold reclassifies historical rows that previously fell short.
- `cli.py` gains a `classify` subcommand that opens the refined DB read-write and prints the summary dict. `run` is still exactly `capture` -> `refine` -> `dashboard`.
- Gate-registration regression test confirms `classify_loop.py` still matches Makefile, pre-commit ruff/py-compile, and pyright include. `SKILL.md` is untouched.

## Classification refinement loop

This section is finished prose for 05-05 to copy into `SKILL.md`. Do not re-derive the wording.

The `classify` subcommand exists and is tested against synthetic fixtures reproducing the PRD's own for-loop example. It is NEVER run automatically by `run`. `run` stays exactly three steps: `capture` -> `refine` -> `dashboard`.

The PRD's own intended trigger is "after the first real end-to-end runs of the capture->refine pipeline against actual historical session logs... not on a fixed schedule, and not before real data exists to mine". Invoking `classify` for real, against a user's own accumulated history, is a separate, later, user-initiated action, not something this phase's own automated delivery performs on the user's behalf.

`DEFAULT_MIN_OCCURRENCES` (currently `2` in `classify_loop.py`) is a documented placeholder, not a researched constant. The PRD's own framing is "exact threshold TBD once real data volume is known". A future tuning pass should change that constant once real volume is known; do not treat `2` as a measured optimum.

`classify` updates SQLite only — it does NOT regenerate `dashboard.html`. Seeing updated `inferred_family`/`inferred_confidence` values in the dashboard after a `classify` run requires a subsequent, separate `dashboard` subcommand invocation. The exact two-step sequence is:

```
ai-kit-usage-metrics.py classify
ai-kit-usage-metrics.py dashboard
```

An `inferred_family` value is a LOW-confidence annotation on matching `control_flow_script`/`unclassified` rows. It never overwrites the row's own `family` or `command_shape` columns, which stay exactly as the mechanical decomposer originally set them. Ambiguous groups (two or more equally plausible curated-tool tokens in the sample body) are left unclassified rather than guessed.

## Task Commits

1. **Task 1: Pattern-mining pass** — `2b97bbc` (feat)
2. **Task 2: Gate-registration regression test** — `a659614` (test)
3. **This SUMMARY** — (docs)

## Files Created/Modified

- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/classify_loop.py` — new
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py` — `update_inferred_family` only
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py` — `classify` subcommand; `run` unchanged
- `tests/test_ai_kit_usage_metrics.py` — `TestClassifyLoop` + `TestPhaseGateRegistration`
- `skills/ai-kit-usage-metrics/SKILL.md` — **not modified** (05-05 exclusive)

## Decisions Made

None beyond the plan. Followed Round 1's 4-step skeleton, Round 1's curated-member set lookup, Round 1's reset-then-remine transaction, Round 2's placeholder-skip guard, and Round 1's wave reorder (no `SKILL.md` edits).

## Deviations from Plan

None.

**Total deviations:** 0
**Impact on plan:** None. Public behavior matches the spec.

## Issues Encountered

Pylint `too-many-return-statements` on `cli.main` after adding the fifth subcommand. Collapsed the four single-command branches into one `if/elif` chain that shares a final `return 0`; `run` stays its own early-return block so it cannot pick up `classify`.

## User Setup Required

None. Do not run `classify` against real session history as part of this plan. Real invocation is user-initiated later, after capture->refine has ingested actual logs.

## Next Phase Readiness

Ready for 05-05 (Wave 6). 05-05 is the sole assembler of the final `SKILL.md` and owns the phase-close `make test`/`make lint`/`make validate` run. Copy the "Classification refinement loop" section above into `SKILL.md` verbatim.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_usage_metrics -v
Ran 93 tests in 0.016s
OK

$ grep -c '"classify"' skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py
1

$ grep -c "BEGIN" skills/ai-kit-usage-metrics/ai_kit_usage_metrics/classify_loop.py
1
```

## Self-Check: PASSED

- [x] Both PRD for-loop examples share one skeleton; `<STR>` is retained, not rewritten to `<ARG>`
- [x] Literal curated member `grep` is recognized as a family-inference candidate
- [x] Recurring rows get `inferred_family="grep"` / `inferred_confidence="LOW"`; singleton stays `None`
- [x] `family` and `command_shape` are unchanged after classification
- [x] Partial failure rolls back; no inferred columns persist
- [x] Higher threshold clears stale annotations; lower threshold reclassifies historical rows
- [x] Ambiguous two-tool group returns `(None, None)`
- [x] `run` does not invoke `classify`
- [x] `SKILL.md` not modified by this plan
- [x] 93 tests, 0 failures
- [x] Production commits exist (`2b97bbc`, `a659614`)

---
*Phase: 05-usage-metrics-dashboard*
*Completed: 2026-09-10*
