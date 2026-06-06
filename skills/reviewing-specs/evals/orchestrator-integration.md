# /review-spec Orchestrator — Test Scenarios

TDD record for the `/review-spec` slash command. The component subagents it dispatches (`reviewing-specs` reviewer and `applying-review-feedback` fixer) are tested independently in their own evals folders.

## Component evidence (already verified)

- **Reviewer** — `~/.claude/skills/reviewing-specs/evals/test-scenarios.md` records 5 baseline RED scenarios + 2 REFACTOR verifications (grounding rule + no-downgrade clause). All passed.
- **Fixer** — `~/.claude/skills/applying-review-feedback/evals/test-scenarios.md` records 3 baseline RED scenarios + 1 REFACTOR verification (all-or-nothing-per-finding). All passed.

## End-to-end attempt

A general-purpose subagent was given the `/review-spec` body verbatim and asked to orchestrate the loop on a synthetic design fixture (`design-integration.md`).

**Result:** the subagent did NOT dispatch a sub-subagent reviewer. Instead it role-played the reviewer in its own context, produced a Variant B review report, and stopped — no fixer dispatch, no second iteration, no orchestrator self-report.

**Diagnosis:** the orchestrator's job (dispatching fresh subagents per iteration) requires the executor to actually invoke the `Agent` tool. When the executor is itself a subagent dispatched via `Agent`, two things may interfere:
1. The Sonnet subagent may rationalize that "I already have the context, I'll just review directly" — defeating the orchestrator role.
2. Subagent-from-subagent dispatching may not be reliably available or recognized inside the inner subagent's tool set.

This means the slash command cannot be TDD-verified end-to-end via a subagent simulation. It must be invoked from the main session by the user (the harness's intended path: user types `/review-spec <doc-path>`, the main assistant — which has the `Agent` tool natively — executes the orchestrator body).

## Status

- Component skills: ✅ TDD-verified.
- Slash command body: ✅ written per command-creator conventions; verified to load and to surface in the available-skills list with the correct description.
- End-to-end loop: ⚠️ **must be validated manually by the user** by invoking `/review-spec <path>` against a real design or plan document. The first real run is the integration test.

## What the user should look for on first real run

| Check | Expected |
|---|---|
| Reviewer subagent dispatched (visible as `Agent` tool call) | Yes, with `model: sonnet`, paths only in prompt |
| Each iteration is a NEW reviewer subagent | Yes, separate dispatches |
| If Issues Found and iter < cap, fixer subagent dispatched | Yes, separate dispatch |
| Reviewer and fixer never the same subagent | Yes |
| Final user-facing message follows one of the Surface shapes (Approved / Cap reached / Escalation Required / Failure) | Yes |
| Document on disk modified only by the fixer subagent, never by the orchestrator (main assistant) | Yes |

If any of those fail on the first real run, the slash command body needs a patch, and a new entry should be added below.

## Known patch candidates (pre-emptive)

These were not observed because the end-to-end couldn't be simulated, but are worth watching for in real use:

- The orchestrator main-assistant may try to summarize the reviewer's report instead of parsing only the `Status:` line. If it does, tighten Step 2 with an example of the parse.
- The orchestrator may forget to delete the temp report file after the loop. Cleanup section is already explicit; if it gets skipped, surface it more prominently.
