---
created: 2026-11-16
title: opencode free models, classification of the research findings and the checks still open
area: runner
severity: major
resolves_phase: 38.1
files:
  - .planning/research/2026-11-16-opencode-free-models.md
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/references/cross-ai-errors.json
---

## Problem

The owner wants free opencode models usable as lanes, with a fallback and a retry the next day after a usage-limit
error. The web research (`.planning/research/2026-11-16-opencode-free-models.md`, read 2026-11-16) settled some facts
and left others open. Every finding was classified with the jev ladder on 2026-11-16 (14 items, one question each,
four classes). Laya answered "none of these" for all 14 with about 0.9 confidence, which says nothing, so it was set
aside. The remote TypeSafe second opinion discriminated, and the decision below is the orchestrator's own reasoning
checked against the evidence.

## Classification

**Requirement now** (verified; written into the specs):
- The free-limit error is a typed error with an optional retry-after in milliseconds taken from the HTTP header
  (jev 0.99, agreed). It feeds the "blocked until" record of Phase 38.1.
- Free models work only through the real opencode client; a direct call gets a different error that is not a usage
  limit and must not be retried (jev 0.97, agreed).
- A `-free` suffix is not a reliable marker of a free model (jev 0.94, agreed); Phase 36 already makes the owner
  declare a lane usage-limited.
- Data use differs per free model and only four are listed as zero-retention, so project content may reach a third
  party (jev 1.0, agreed). Phase 36's wizard shows a data-use note and asks the owner to confirm.

**Provisional requirement and still to verify** (the design acts on it now, the owner confirms):
- Stated resets are under 24 hours, the reset is unreliable, and free models seem to share one pool per account or IP.
  Jev classed all three as "to verify" (0.98, 0.99, 0.99). The orchestrator kept them as provisional rules because
  the runner must do something safe before the checks finish: block by pool, wait the stated time plus 120 seconds,
  and use a 24-hour floor after a second failure in a row. Keying the block by pool errs on the safe side if the pool
  turns out to be per model.
- The free list is volatile (jev low 0.75, own reasoning): a removed model gives a terminal model-not-found error and
  never a blocked-until record, and no free model name is hardcoded. The exact headless error is a check below.

**Backlog** (a worthwhile feature outside the current phases; jev 0.84, agreed): free-tier lanes beyond opencode,
meaning OpenRouter free models and Gemini's free tier. It is a ROADMAP backlog entry with a goal statement.

## Checks still open (no requirement until checked)

1. **The reset rule.** Is the free quota reset at a fixed daily time (which time zone) or a rolling window, and what is
   it keyed on (account, IP, model)? How to check: when a free-limit event happens in normal use, the runner keeps the
   raw secret-free event with the local clock; three or more days of events answer it. No deliberate quota burning.
2. **Exit code and event order after the limit in version 2.3.0.** How to check: read opencode's run loop at the 2.3.0
   tag (primary source), then confirm with one natural capture. Phase 38.1's plan runs it.
3. **The headless error of a removed free model on version 2.** How to check: run a placeholder model id headless;
   it fails before inference, so no quota is spent (the same method as Phase 38.1's error fixtures).
4. **Are the `opencode` and `opencode-go` free pools shared?** How to check: events from both providers on the same
   day, or the vendor page if it states it.
5. **No official "free models, limits and privacy" page was found.** Every limit figure comes from issues and secondary
   sources. How to check: look again at opencode's docs at the start of each phase that reads these figures, and ask
   the maintainers through an issue if it is still missing. Treat every figure as reported until then.

## Owner confirmations needed

*(Accepted as written by the owner on 2026-11-16; see `.planning/docs/OWNER-DECISIONS-2026-11-16.md`. The three items below
stay listed for traceability.)*

- Which wins for the first retry time: the stated reset plus 120 seconds (provisional, backed by the evidence) or a hard
  24-hour minimum (the owner's rule of thumb). Provisional rule: stated time first, 24-hour floor after a second
  failure in a row.
- Block by pool (provider plus free tier) instead of by model (provisional: by pool).
- Confirm the data-use note each time a free lane is chosen (provisional: yes, every time it is chosen).

## Solution

Phase 38.1 writes the blocked-until record and the error classes; Phase 36's wizard shows the data-use note and the
pool warning; Phase 40 and Phase 41 skip a blocked lane and use the fallback of another pool. The five checks above are
recorded as spikes or fixtures in those plans.
