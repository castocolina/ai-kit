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

DIGEST 4e0a4fcbf5ef4634
TREE 675622459707a4131f602cdae8d17ba668def16d

# Skill evaluation: jev-fast-decision

Using **skill-judge** with `tmp/judge/rubric.md`. Evaluated commit `e34499e`; the working tree is clean. No files were edited.

## Activation picks

Listed all 22 `skills/*/SKILL.md` files and extracted only their frontmatter `name` and `description` before opening the judged body. `typesafe-ai` is not in this checkout, so its installed frontmatter supplied that candidate’s description.

The activation fixture resolves to `.planning/phases/21.1-atomic-reusable-decision-system-skills/skill-judge/activation.jsonl`.

| Line | Single skill to load | Frontmatter-only reasoning |
|---|---|---|
| 1 | `jev-fast-decision` | Yes/no triage of supplied evidence is an advisory typed judgment, with no editing required. |
| 2 | `jev-fast-decision` | Selecting one of three named titles matches its `choice` trigger. |
| 3 | `jev-fast-decision` | Scoring supplied report text against a severity rubric matches its `score` trigger. |
| 4 | `jev-fast-decision` | Screening existing grep evidence against a false-positive criterion matches its description. |
| 5 | none | Editing a shell script and tests is explicitly outside its scope; no listed specialist matches. |
| 6 | none | Tracing a call chain requires investigation and reasoning, not a snap judgment over supplied evidence. |
| 7 | none | Running diagnostics and fixing failures is not advisory screening. |
| 8 | none | Planning and implementing a migration is multi-step code work, explicitly excluded. |
| 9 | `typesafe-ai` | Building product-facing TypeSafe routing matches programmable application judgments. |
| 10 | `typesafe-ai` | Its description explicitly covers brainstorming AI-powered product features. |
| 11 | `typesafe-ai` | Its description explicitly covers replacing prompt-and-parse with structured application decisions. |
| 12 | `typesafe-ai` | An in-app ranker with backend integration matches its ranking and application-building scope. |

All four expected positive cases select `jev-fast-decision`; none of the eight negative cases selects it.

## Part 1 — Dimensions

D1 18/20 — 90%. Strong backend-specific knowledge: measured state contamination, truncation guards, moving aliases and confidence semantics. Some repetition dilutes the otherwise high knowledge delta.

D2 14/15 — 93.3%. Transfers the advisory mindset and a concrete probe → backend-read → call → interpret workflow. A compact instruction to split compound judgments into independently answerable items would strengthen question design.

D3 14/15 — 93.3%. Specific prohibitions cover consent inference, raw-source disclosure, unsupported-answer dismissal and Laya batching. The batching rationale is excellent in the backend notes; several body prohibitions leave their rationale implicit.

D4 15/15 — 100%. Valid frontmatter, compliant name, specific capabilities and triggers, and explicit exclusions distinguishing agent screening from application integration.

D5 13/15 — 86.7%. The 66-line entry point routes to backend notes and conditionally loads the reference for richer shapes. It lacks explicit “do not load unselected backends” guidance, and the unconditional external reading list weakens otherwise selective loading.

D6 15/15 — 100%. Appropriate constraints around transmission, consent and typed contracts, while preserving the agent’s own judgment. `needs_fallback` never authorizes an automatic verdict.

D7 9/10 — 90%. Clear Navigation/Tool hybrid: concise routing, executable client and detailed backend resources. Repeated warning sections slightly fragment the entry point.

D8 13/15 — 86.7%. Covers partial results, missing IDs, unavailable backends, unsupported features and provenance. Minor documentation discrepancies remain in the HTTP error taxonomy.

**Total: 111/120 (92.5%, A).** Estimated knowledge ratio: Expert 80%, Activation 15%, Redundant 5%.

### Findings

**Critical:** none.

**Important:** none.

**Minor**
1. **Repeated warning content.** `skills/jev-fast-decision/SKILL.md:46`, `:53`, and `:57` repeat consent or batching warnings already present in the workflow/NEVER list. Consolidate the duplicate reminders while retaining the measured rationale in the backend reference.
2. **Loading boundaries could be sharper.** `skills/jev-fast-decision/SKILL.md:59–66` requires four external documents without scenario-specific loading conditions. Make feature-specific documents conditional and explicitly exclude unselected backend notes.
3. **HTTP error tables overgeneralize client behavior.** `skills/jev-fast-decision/backends/typesafe.md:43` says other 4xx responses are final caller errors, but `scripts/jev_review.py:767–769` classifies only 400/404/413/422 that way and escalates others. Likewise, `backends/opencode.md:27` generalizes other 4xx responses, while `scripts/jev_review.py:830–832` uses the caller-error classification only for 400. Align the tables with the implemented classifications.

### Required fallback recipe

Present at `skills/jev-fast-decision/SKILL.md:38`:

> “`needs_fallback: true` → **you decide that item with your own reasoning**”

This is an actionable recipe, not merely a field definition.

### Evidence and limitations

Read the complete skill body, reference, all three backend notes, both bundled scripts and evaluation cases. The 88 KB client was read in chunks. Also checked the four required external pages and recomputed the recorded evaluation metrics.

No live inference or test suite was run. The recorded Laya evaluation reports **50% accuracy among non-fallback, unambiguous cases**; the skill correctly discloses this and requires independent verification.

CURRENT 111/120
CRITICAL 0
IMPORTANT 0
FLOORS ok
ACTIVATION ok
CITE_PROBE skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

CITE_BACKEND skills/jev-fast-decision/SKILL.md:12
> From this skill's directory, run `python3 -B scripts/jev_review.py --probe` before the first call of a session; read `backends/<selected>.md` before the first call with that backend.

VERDICT pass
