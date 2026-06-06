---
name: applying-review-feedback
description: Use when a review report from `reviewing-specs` (or equivalent structured review feedback) has been produced for a design or plan document, and the document author needs to address each finding. Intended to be dispatched as a clean-context fixer subagent by an orchestrator (e.g. `/review-spec`). Edits the document in place, addresses every CRITICAL/HIGH finding, respects the source framework's conventions when a framework profile is provided, and produces a per-finding edit summary.
---

# Applying Review Feedback

Targeted editor for design/plan documents flagged by `reviewing-specs`. Reads the report, edits the document to satisfy each finding's `Required:` outcome, and reports back what was addressed and what was not.

**Scope rule — never expand.** This skill only touches what the report flags. No drive-by refactors, no "while we're here" cleanup, no new features, no rewriting unrelated sections. The report is the contract.

## Inputs

The orchestrator (or invoking caller) must provide:
- **Document path(s)** to edit — absolute paths to files that exist on disk.
- **Review report** — absolute path to a report file on disk. Inline report text is accepted only as a fallback; if given, the first thing this skill does is write it verbatim to a temp file and `Read` that file back, so the rest of the skill operates on a path.
- **Codebase root** for any `Read`-back verification.
- **Framework profile path** *(optional)* — `FRAMEWORK_PROFILE_PATH`, a path to the source framework's profile (or `none`). If a path, `Read` it before editing and respect its conventions (see Editing rules). If `none`, edit with generic conventions.

**Refuse if any document is not on disk.** If the caller passed inline content for a "document to edit," respond with a Fix Summary using `### Status: Failure — document not on disk. Caller must persist the document and re-invoke with a path.` and emit no edits. Editing in-memory content produces a fix that vanishes the moment this subagent ends — the next iteration of review/fix will read the unfixed file and contradict itself.

If any input is missing, stop and ask. Do not guess paths.

## Before editing

1. `Read` the document(s) under the report fresh from disk. Never trust in-context state.
2. `Read` the review report verbatim.
3. For every finding that references an external file (codebase grounding findings), `Read` that referenced file too — you cannot satisfy a "Context section must accurately describe X" finding without reading X. Resolve relative paths against the **codebase root the caller gave you** (with worktrees that root is often not your CWD), so you read the worktree's copy, not the main checkout's.
4. Build an internal checklist: every CRITICAL and every HIGH finding becomes a task. MEDIUM findings are tasks if trivial; otherwise they are escalation candidates.

## Editing rules

| Rule | Why |
|---|---|
| Address each CRITICAL and each HIGH. No silent skips. | The report is the contract. Skipping = approving the defect. |
| If a finding requires changing a load-bearing premise (e.g. "re-evaluate whether feature X is still warranted"), STOP and escalate to the caller before editing. | This is a design judgment, not a text edit. The author/orchestrator decides. |
| Edit only the sections the finding's `Location:` field names (or strictly necessary sibling text for coherence). | No scope creep. |
| Do not add features, components, or sections not present in the original document. | Design changes require a new design pass, not a fix pass. |
| Do not re-format, re-style, or re-flow text outside the flagged location. | Style changes hide real edits in the diff. |
| Do not edit the review report itself. | Report is read-only input. |
| If you disagree with a finding, do NOT silently ignore it. Address it AND note your disagreement in the output summary. | Disagreement is fine; silent rejection is not. |
| Preserve existing formatting conventions (heading levels, list style, code fences) of the document. | The author chose them. |
| If a framework profile was provided, keep its conventions: requirement syntax (EARS `WHEN…SHALL`, RFC-2119 SHALL), acceptance-criteria format (Given/When/Then), task-checkbox format and markers (`[P]`, `- [ ] N.N`), delta section headers (`## ADDED/MODIFIED/REMOVED`); never push implementation detail into a behavior-only spec. | The framework's rules are part of "correct" — a fix that satisfies the finding but breaks EARS or leaks impl detail just creates the next finding. |

## Escalation conditions

Stop and ask the caller (don't edit) when:
- A CRITICAL finding's `Required:` says or implies "re-evaluate whether the change is still warranted" — that's a strategy decision.
- The fix would require introducing new components or scope not in the original document.
- The report contradicts itself or contradicts the actual codebase you read.
- Two findings have mutually exclusive `Required:` outcomes.

**All-or-nothing per finding.** If ANY part of a finding's `Required:` triggers escalation, escalate the WHOLE finding without performing any edit, even if other parts of the same finding look like trivial text fixes. Reason: a partial fix leaves the document in a half-resolved state — the caller cannot tell whether the text edit is correct without the strategy decision that was escalated. Findings are atomic units.

Escalation output: a short message naming which finding, why it cannot be auto-fixed, and what decision the caller must make. No edit performed.

## Output

After editing, emit a structured summary. The orchestrator parses this to decide whether to re-invoke the reviewer.

```
## Fix Summary: <doc path>

### Document
<absolute path>

### Findings addressed
- **<finding title>** — Severity: <CRITICAL|HIGH|MEDIUM|LOW>. Status: addressed. Edit: <one-sentence description of the change made, e.g. "Rewrote Context paragraph to reflect the wait-for-authorization behavior of commit-message/SKILL.md."> Section: <heading or line range>.

### Findings escalated
- **<finding title>** — Severity: <X>. Reason for escalation: <one sentence>. Caller decision needed.

### Findings skipped (with disagreement noted)
- **<finding title>** — Severity: <X>. Reason: <why you disagree, one sentence>. NOT addressed in this pass.

### Findings not yet addressed
- **<finding title>** — Severity: MEDIUM/LOW. Deferred. Reason: <e.g. "non-trivial, separate pass recommended">.

### Status: Edits Applied | Escalation Required | No Edits (all skipped/escalated)
```

If `Status: Edits Applied` and the only un-addressed items are MEDIUM/LOW deferrals, the orchestrator can re-invoke the reviewer. If `Escalation Required`, the orchestrator must surface to the human.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Rewriting unflagged sections | Stop. Only edit what `Location:` names. |
| Adding new features/components/sections | Out of scope. Escalate instead. |
| Silently dropping a finding you disagree with | Address it OR document disagreement in the skipped list — never silent. |
| Editing the review report | Never. Report is read-only input. |
| Auto-fixing a "re-evaluate X" finding | Escalate. That's a strategy call. |
| Reformatting the whole document for "consistency" | Preserve the author's existing conventions. |
| Performing the fix without reading the file the finding references | A grounding fix needs the actual referenced file's content. Read first. |
| Partial fix on a finding that has any escalation trigger | Findings are atomic. Any escalation trigger → escalate whole finding, no edits. |
