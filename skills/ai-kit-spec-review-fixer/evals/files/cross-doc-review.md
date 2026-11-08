## Review: design-good.md and plan-bad.md

### Document Type
design and plan (cross-document review)

### Files Read (fresh from disk)
- design-good.md (50 lines)
- plan-bad.md (51 lines)

### HIGH

- **The --draft behaviour is stated differently in the design and the plan** — Location: the Context section of design-good.md (the sentence that says the flag "prints the message to stdout without staging") and the Goal line of plan-bad.md. Required: call the flag `--draft` in both documents, with the same one-sentence behaviour: the generated message is printed to stdout and nothing is staged or committed. Why: a reader of the plan cannot tell from its Goal what the design promises, so the two documents disagree about the same flag.

### Status: Issues Found — fix and re-invoke
