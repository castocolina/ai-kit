DIGEST 8539e9d42a797883
TREE 4e0b112816d8f3cd409dcc8866a68b099e8b7999

# Skill evaluation: jev-fast-decision

Using **skill-judge** with `tmp/judge/rubric.md`. Evaluated commit `07a1efc`; working tree clean. No files edited.

## Activation picks — frontmatter only

Listed all 22 `skills/*/SKILL.md` files and extracted their `name` and `description`. `typesafe-ai` is absent from that checkout list; its installed frontmatter supplies the application-building alternative.

The activation fixture was found at `.planning/phases/21.1-atomic-reusable-decision-system-skills/skill-judge/activation.jsonl`, not the root-relative `skill-judge/activation.jsonl`.

| Line | Single skill picked | Reason |
|---|---|---|
| 1 | jev-fast-decision | Bounded yes/no judgments about supplied findings, without investigation or editing. |
| 2 | jev-fast-decision | Picks one of three named options. |
| 3 | jev-fast-decision | Scores supplied evidence against an ordered severity rubric. |
| 4 | jev-fast-decision | Screens existing evidence with per-item yes/no judgments. |
| 5 | none | Requests code and test edits, explicitly excluded by the description. |
| 6 | none | Requires call-chain investigation and explanation, not a supplied-evidence snap judgment. |
| 7 | none | Requires running checks and fixing code. |
| 8 | none | Requires multi-step migration planning and implementation. |
| 9 | typesafe-ai | Builds TypeSafe routing into a product. |
| 10 | typesafe-ai | Brainstorms user-facing product features using System One primitives. |
| 11 | typesafe-ai | Replaces application prompt-and-parse logic with a typed judgment. |
| 12 | typesafe-ai | Implements an in-app ranker and backend API integration. |

All 12 satisfy the stated activation pass rule.

## Part 1 — Dimensions

D1 18/20 — 90%. Strong knowledge delta: measured Laya contamination, truncation guards, backend-specific capabilities and consent semantics. Some repetition across the body, reference and backend notes.

D2 14/15 — 93.3%. Combines advisory-only reasoning with a concrete probe → backend reading → call → interpret workflow. A compact distinction between local low-confidence escalation and remote terminal fallback would improve completeness.

D3 14/15 — 93.3%. Specific prohibitions cover consent rationalizations, raw-source transmission, unsupported-answer dismissal and Laya batching. The body could attach the measured contamination reason directly to its batching prohibition.

D4 15/15 — 100%. Valid frontmatter; description clearly states capabilities, activation conditions, typed primitives and exclusions. Activation cases distinguish judgment assistance from product integration.

D5 13/15 — 86.7%. A 66-line body routes to selected-backend notes and conditionally loads the reference. Unconditional external required reading adds avoidable context; explicit “do not load unselected backend notes” guidance is absent.

D6 14/15 — 93.3%. Transport, consent and input shapes are constrained while final judgment remains with the agent. Backend error documentation has small inconsistencies with the implementation.

D7 9/10 — 90%. Effective compact Navigation/Tool hybrid: backend selection, executable request shape, result recipe and deeper reference material. Red Flags and Common Mistakes partially repeat adjacent guidance.

D8 13/15 — 86.7%. Actionable request/result contracts, partial-result handling, fallback recipes and backend failure notes. Copied placeholders require substitution, and some error classifications are described too broadly.

**Total: 110/120 (91.7%), grade A.** Estimated knowledge ratio: Expert 85%, Activation 10%, Redundant 5%. No dimension is below its floor.

### Findings

- **Minor — `skills/jev-fast-decision/backends/typesafe.md:43` and `skills/jev-fast-decision/backends/opencode.md:27`:** “Other 4xx” errors are described as final caller errors, but the implementation classifies only selected codes that way. For example, TypeSafe 429 escalates (`scripts/jev_review.py:767–769`); Zen 404 also escalates (`scripts/jev_review.py:830–832`). Document the actual classifications so agents can predict retry/escalation behavior.
- **Minor — `skills/jev-fast-decision/SKILL.md:59–64`:** Unconditional required reading includes image documentation even though the client cannot build image requests. Make these readings conditional on the relevant question or capability.
- **Minor — `skills/jev-fast-decision/SKILL.md:27`:** The quoted heredoc sends `"<git rev-parse HEAD>"` literally unless manually replaced; validation requires 40 lowercase hexadecimal characters (`scripts/jev_review.py:345–346`). Explicitly instruct substitution before running the example.

### Required fallback check

Present at `skills/jev-fast-decision/SKILL.md:38`:

> `needs_fallback: true` → **you decide that item with your own reasoning**

This is an explicit behavioral recipe, not merely a field definition.

### Read coverage

Read the complete body, `reference.md`, all three backend notes, the complete 88,313-byte client in chunks, the eval script and 32-case fixture, the linked recorded eval artifact, and all four directly linked web pages. Recomputed the recorded metrics: accuracy **55.56%**, fallback rate **68.75%**, and non-fallback accuracy **50%**, matching the backend disclosure.

Not checked: live backend execution, test reruns or independent reproduction of recorded measurements. Advisory-only verification remains essential given the disclosed non-fallback accuracy.

CURRENT 110/120
CRITICAL 0
IMPORTANT 0
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

VERDICT pass
