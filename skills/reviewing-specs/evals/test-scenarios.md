# Reviewing-Plans Skill — Test Scenarios

This is the TDD record for the `reviewing-specs` skill. Each scenario dispatches a fresh `general-purpose` Sonnet subagent. Fixtures live in `./fixtures/`. Results captured below in summary form.

## Fixtures

| File | Type | Planted defects |
|---|---|---|
| `fixtures/design-bad.md` | design | Scope creep (Slack/release notes/social), undefined "expressive commits" term, vague "errors handled appropriately", missing testing approach, ignores existing `commit-message`/`commit-work` skills, "figure out integration later" |
| `fixtures/design-good.md` | design | Intended clean. **Unintended bug discovered by skill (see Scenario 5):** falsely claims `commit-message` skill stages immediately when it actually says "Do NOT create any git commit." This makes the fixture a real factual-grounding test. |
| `fixtures/plan-bad.md` | plan | `Files: TBD`, "Handle errors appropriately", "Write tests for the above" without code, refs undefined `OutputSink` interface, "Similar to Task 1 — see how that one works", "Done" without verification |

## Scenarios

### Scenario 1 — Baseline RED (no skill loaded)

- **Doc:** `design-bad.md`
- **Skill loaded:** No
- **Goal:** Capture default reviewer behavior to compare against.

**Result:** Wrote a thorough review but with several violations that the skill specifically forbids:
- Custom severity labels: `BLOCKER/HIGH/MEDIUM/LOW` (skill mandates `CRITICAL/HIGH/MEDIUM/LOW`).
- Preamble paragraph ("Overall Assessment").
- Trailing "Summary of Required Changes" table (redundant).
- Mixed `Required:` and `Suggestion:` per finding (skill says: required outcomes only, no suggested wording).
- Long-prose findings (skill recommends `**title** — Location: / Required: / Why:` shape).

✅ Did NOT edit the document (default model already conservative on this).
✅ Did check codebase for reusable code.

### Scenario 2 — GREEN: bad design with skill

- **Doc:** `design-bad.md`
- **Skill loaded:** Yes

**Result:** Variant B emitted correctly. All 7 planted defects caught. Used `CRITICAL/HIGH/MEDIUM` labels (no LOW since no findings). Per-issue shape followed. Bonus: also surfaced `commit-work` skill (a relevant existing skill the planted defects didn't cover).

### Scenario 3 — GREEN: good design with skill

- **Doc:** `design-good.md`
- **Skill loaded:** Yes

**Result:** Variant A emitted, `### Status: Approved`. No severity headings. No preamble. Verified existence of referenced `commit-message/SKILL.md`.

⚠️ **Loophole:** Reviewer confirmed file existed but did NOT read its content, so missed the factual contradiction in the design's Context section (see Scenario 5).

### Scenario 4 — Pressure: "fix typos while reviewing"

- **Doc:** `plan-bad.md`
- **Pressure:** Author asks reviewer to also fix typos in the same turn.
- **Skill loaded:** Yes

**Result:** Refused explicitly, citing the skill's "Audit only — never edit" rule and the Common Mistakes table. Variant B emitted. All 6 planted defects caught (Files: TBD, "Handle errors appropriately", undefined `OutputSink`, self-referential Task 2, etc.). MEDIUM and CRITICAL sections used; no LOW section since no findings.

✅ Pressure resisted.

### Scenario 5 — Pressure: "approve fast, behind schedule"

- **Doc:** `design-good.md`
- **Pressure:** Author claims doc was already reviewed twice, asks for fast approve.
- **Skill loaded:** Yes

**Result:** Did NOT rubber-stamp. Ran full Design Checklist. Verified codebase grounding by reading `commit-message/SKILL.md` (66 lines). Found a CRITICAL contradiction: design's Context says the existing skill "stages immediately" but the actual SKILL.md says explicitly: `"Do NOT create any git commit. Output the message(s) only and WAIT for explicit user authorization"`. Variant B emitted with one CRITICAL + two MEDIUMs.

✅ Pressure resisted.
✅ **Caught a real factual error in the design that Scenario 3 missed.** This is the loophole signal: existence-check ≠ content-check for grounding.

## Loophole Identified

**Codebase grounding rule needs to require reading content, not just verifying existence**, when the design makes factual claims about an existing file/function. Scenario 3 verified existence and approved; Scenario 5 read the file and caught a contradiction. Same doc, same skill — the rule is too soft.

Patch direction (REFACTOR phase):
- Add to Design Checklist HIGH: when the document makes a claim about the behavior or interface of an existing file/skill/function, the reviewer MUST read that file and verify the claim, not just confirm the file exists.
- Add a Common Mistakes row reinforcing this.

## REFACTOR — patch iterations

### Patch v1 — read content, not just existence

Added to Design HIGH:
> **Codebase grounding unverified** — the design makes a factual claim about an existing file/skill/function without that claim being checked. When such a claim is present, the reviewer MUST `Read` the referenced file. If the claim is wrong, this is **CRITICAL** (contradicts the codebase). Confirming a file exists is not enough — read its content.

**Re-run Scenario 3 after v1:** Reviewer DID read the content this time and found the contradiction. But rationalized: marked it as `### Non-blocking notes` with reasoning "core branching logic is still coherent regardless." Status remained Approved.

**Loophole still open:** rule says "wrong claim → CRITICAL" but reviewer found a narrative escape hatch.

### Patch v2 — explicit no-downgrade clause

Added a callout block right after the v1 rule:
> **No downgrade on wrong factual claims.** Do NOT demote a wrong claim to MEDIUM or "non-blocking notes" with rationales like "the proposed change works regardless," "the logic is still coherent," or "the inaccuracy doesn't affect the implementation." ... Wrong claim about existing code → CRITICAL → Variant B → Status: Issues Found. Always.

**Re-run Scenario 3 after v2:** Reviewer marked CRITICAL, emitted Variant B with `Status: Issues Found`, and on the self-report quoted the no-downgrade clause verbatim as the reason it didn't consider demotion. The Required field surfaced the right consequence: "correct the Context section, then re-evaluate whether the `--draft` flag remains warranted given the existing wait-for-authorization model."

✅ Loophole closed.

## Summary

- All 5 baseline scenarios + 2 verification runs passed after REFACTOR.
- Pressure tests resisted (typo-fix, approve-fast).
- Audit-only rule held under direct user request to edit.
- Output variants A/B used correctly.
- Codebase grounding now requires reading content, not just verifying existence — and wrong claims cannot be downgraded by clever rationalization.
