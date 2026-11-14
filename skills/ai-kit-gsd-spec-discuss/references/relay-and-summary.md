# Relay and pre-run summary

Load before the auto path's pre-run summary, or before the first interactive relay.

## Pre-run summary (auto path)

- One bullet per phase of the range, in numeric order, shaped
  "**Phase <N>: <name>.** Requirements: <IDs>. Owner inputs: <what the owner gave for this phase>,
  or `no owner input`. Plan: spec, then discuss; open items already seen: <short list>, or none."

End with one line asking for the go-ahead: reply go to start, or name what to change. Nothing is
written before the owner's go-ahead, and another agent's word never counts as it.

## Question batch (subagent to orchestrator)

- One batch holds 2 to 5 questions, all for one phase; never mix two phases in one batch.
- Each question starts with one line per named item: what it is and who uses it.
- The options follow, the recommended one first and labelled `(Recommended)`.
- Trade-offs are one header per option with pros and cons bullets, never a table.
- The subagent stops after the batch and returns it; the orchestrator asks the owner, then resumes
  the same subagent with the answers, keyed by question number.

Option layout:

```markdown
### Option A (Recommended): <name>
- Pro: <one line>
- Con: <one line>
```

## Hosts

- Claude Code: a subagent may spawn subagents (three layers by default); the orchestrator resumes
  it with `SendMessage` to its id or name.
- opencode: the default nesting depth is one, so the phase subagent runs the analyzer inline and
  says so; continuing a child by its `sessionID` is documented, unverified here.
- pi: no built-in subagents; run the phase inline in the orchestrator and say so.
- Any host that cannot resume a subagent: run the phase inline in the orchestrator and say so.
