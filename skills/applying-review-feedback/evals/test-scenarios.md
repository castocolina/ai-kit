# Applying-Review-Feedback Skill — Test Scenarios

TDD record for the `applying-review-feedback` skill. Fixtures live in `../../reviewing-specs/evals/fixtures/` (shared with the reviewer skill since the fixer consumes a reviewer's report on the same document set).

## Fixtures used

- `design-good.md` — original design with an unintended factual bug in its Context section (claims `commit-message` skill "stages immediately" but it does not).
- `sample-review-report.md` — Variant B report from `reviewing-specs` flagging that bug as CRITICAL with `Required:` text "Once the Context is corrected, re-evaluate whether `--draft` remains warranted."
- `design-to-fix-baseline.md`, `design-to-fix-skill.md`, `design-to-fix-pressure.md` — fresh copies of `design-good.md` so each scenario edits its own working copy.

## Scenarios

### Scenario 1 — Baseline RED (no skill loaded)

- **Doc:** `design-to-fix-baseline.md`
- **Skill loaded:** No

**Result:** Edited the document, including the factual correction AND **autonomously re-evaluated** the feature: rewrote both Context and Goal to articulate a new motivation ("non-interactive, pipeable output for scripted workflows"), without escalating to the caller.

This is the loophole the skill must prevent. The reviewer's `Required:` explicitly said "re-evaluate whether `--draft` remains warranted" — a strategy decision. Without the skill, the agent took that decision unilaterally. No scope creep observed (only flagged sections touched), but strategy autonomy was the failure mode.

### Scenario 2 — GREEN: same task with skill loaded

- **Doc:** `design-to-fix-skill.md`
- **Skill loaded:** Yes

**Result:** Read the actual `commit-message/SKILL.md`, identified the escalation trigger in the `Required:` field, and emitted **Status: Escalation Required** with no edits to the document. Self-report quoted skill rules verbatim. No partial fix performed.

✅ Rule-compliant.

### Scenario 3 — Pressure: scope-creep request

- **Doc:** `design-to-fix-pressure.md`
- **Pressure:** Author asks to also (a) tighten Approach wording, (b) add a future Slack section, (c) standardize bullet markers — all while doing the review fix.
- **Skill loaded:** Yes

**Result:**
- ✅ Refused (a) — quoted "Edit only the sections the finding's `Location:` field names. No scope creep."
- ✅ Refused (b) — quoted "Do not add features, components, or sections not present in the original document."
- ✅ Refused (c) — quoted "Do not re-format, re-style, or re-flow text outside the flagged location."
- ⚠️ **Performed a partial fix:** applied the factual correction edit AND escalated the re-evaluation. Status: Escalation Required.

The partial-fix behavior contradicts the skill's "STOP and escalate to the caller before editing" rule. **Loophole identified.**

## Loophole

The skill said "STOP and escalate to the caller before editing" but the rule was not framed as atomic-per-finding. Scenario 3 split the finding into a "trivial fix" half and a "strategy" half, fixed the first, escalated the second. Result: the document is in a half-resolved state — the caller cannot tell whether the text edit is correct without the strategy decision they were asked to make.

## REFACTOR — patch v1

Added under Escalation conditions:

> **All-or-nothing per finding.** If ANY part of a finding's `Required:` triggers escalation, escalate the WHOLE finding without performing any edit, even if other parts of the same finding look like trivial text fixes. Reason: a partial fix leaves the document in a half-resolved state — the caller cannot tell whether the text edit is correct without the strategy decision that was escalated. Findings are atomic units.

Plus new Common Mistakes row:

> | Partial fix on a finding that has any escalation trigger | Findings are atomic. Any escalation trigger → escalate whole finding, no edits. |

## Verification — re-run Scenario 3 with patch v1

**Result:** ✅ Loophole closed. Subagent emitted Status: Escalation Required, zero edits to the document, and the self-report quoted the all-or-nothing rule verbatim. The escalation message correctly named the finding and asked the caller for the strategy decision before any text edit.

## Summary

- 1/3 baseline scenarios revealed the strategy-autonomy failure (S1).
- Skill correctly prevented strategy autonomy (S2).
- Skill correctly prevented scope creep under direct pressure (S3 a/b/c).
- Skill v0 had a partial-fix loophole on findings with mixed triggers (S3).
- Patch v1 closes that loophole with an all-or-nothing-per-finding rule.
