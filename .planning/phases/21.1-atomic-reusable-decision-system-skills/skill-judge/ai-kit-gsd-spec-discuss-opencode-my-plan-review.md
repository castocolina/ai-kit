DIGEST 8d484b07e7d397df
TREE 13d2a9400afdcb361253344e86beeb43ceb63f36

# Skill Evaluation: ai-kit-gsd-spec-discuss

Using **skill-judge** with `tmp/judge/rubric.md` to evaluate the committed skill and its supporting files.

**Tree:** `07a1efc`; working tree clean. No pending-orchestrator marker found in the judged directory.  
**Pattern:** Process, with Tool-style decision routing.  
**Estimated knowledge ratio:** Expert 85% / Activation 12% / Redundant 3%.

## Dimension scores

D1 18/20 — 90%. High-value GSD routing traps, evidence-based overrides, consent handling and amendment rules. Some backend inventory duplicates shared-client documentation; shorten that inventory and defer changing details to detection output.

D2 14/15 — 93.3%. Strong decider mindset plus non-obvious procedures: bypass auto-advance, preserve locked decisions and compute the coverage floor. Tighten the dependency ordering for speculative analyzer starts.

D3 14/15 — 93.3%. Specific prohibitions explain concrete consequences: empty outputs, unintended planning, cross-item contamination and lost decisions (`SKILL.md:188–203`). Make the analyzer’s CodeGraph instructions respect existing-index and authorization boundaries too.

D4 15/15 — 100%. Valid matching name and frontmatter. The description supplies WHAT, WHEN, recognizable command examples, backend keywords and explicit exclusions (`SKILL.md:1–4`).

D5 14/15 — 93.3%. Mandatory reference triggers are embedded in the workflow, worked examples are conditional, and already-current phases have explicit “Do NOT load” guidance (`SKILL.md:64,106,110–111,212–222`). Backend/key-source detail could be disclosed through the shared client rather than repeated in the body.

D6 12/15 — 80%. Appropriate freedom for judgment and firm constraints for consent, evidence and artifact preservation. However, the analyzer brief authorizes index creation merely because the executable exists (`references/analyzer-brief.md:25–30`).

D7 9/10 — 90%. Clear Process pattern: setup, spec, discuss, ladder, ledger and amendments. The optional overlapping-phase schedule introduces a dependency exception that needs a sharper guard (`SKILL.md:179–184`).

D8 12/15 — 80%. Actionable item schemas, error paths, no-client behavior and logging formats align well with the scripts. Usability is weakened by discarded probe uncertainty and incomplete guidance for distinguishing forced-fallback causes.

**Total: 108/120 — 90%, Grade A.** No dimension is below its floor.

## Special check: `needs_fallback`

**Confirmed.** `SKILL.md:149–150` explicitly connects the client’s `needs_fallback` signal to the required action:

> “Every answering column low (`fallback: true`, the client's `needs_fallback`) or errored → **own reasoning** against the SPEC, earlier CONTEXT files and the live facts.”

This is an operational recipe, not merely a field description. The adapter implements the connection at `scripts/decide.py:326,343`. The references correctly explain local escalation, remote-low finality and evidence-based resolution (`references/decision-table.md:28–37`).

## Findings

### Critical

None.

### Important

1. **Analyzer instructions create an index without checking authorization.**  
   **File:** `skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md:25–30`  
   The block is enabled by `command -v codegraph` and explicitly directs `codegraph init` when no index exists. Having the executable installed does not establish that this repository should be indexed. This also conflicts with the supplied environment’s instruction that indexing is the user’s decision.  
   **Improvement:** Enable indexed exploration only when an index already exists; otherwise use ordinary read-only exploration. Require explicit authorization before creating or synchronizing an index.

2. **Detection discards the shared client’s uncertainty about credential verification.**  
   **File:** `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:45,210–223`  
   `_BACKEND_KEYS` omits `key_check`, although the shared client emits it. OpenCode’s probe establishes reachability rather than key validity and is expressly marked `key_check: "unverified"` (`skills/jev-fast-decision/scripts/jev_review.py:807–812,910,1247–1248`). The adapter can consequently present `status: "usable"` without preserving that qualification.  
   **Improvement:** Preserve the closed-set `key_check` label and explain that reachability is not verified authentication.

### Minor

1. **Early analyzer starts can precede their mandatory input.**  
   **File:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:181–184`  
   Starting phase K+1’s analyzer while writing phase K’s SPEC does not ensure K+1’s own SPEC exists. Its brief requires that SPEC to be read first (`references/analyzer-brief.md:10–11`).  
   **Improvement:** Permit overlap only after the target phase’s SPEC exists and its required upstream decisions are available.

2. **The body treats forced fallback too narrowly.**  
   **File:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:137–140`  
   The body calls above-threshold fallback “that size flag” and prescribes shortening. The decision table correctly says server-reported truncation can also force fallback (`references/decision-table.md:3–6`). TypeSafe’s cap also applies to the combined request state, not just each individual item.  
   **Improvement:** Name both causes and explain how to reduce aggregate batch state when individually short items still exceed the cap.

## Coverage and limits

Read all eight files in the judged directory: the 222-line skill, four references and three scripts. Reference sizes were 2,949–4,582 bytes; scripts were 5,747–23,422 bytes. Also inspected the shared client in chunks, its reference, relevant test sources and the installed GSD resolver/workflows.

No files were modified. Tests and live inference were not run; findings are based on source inspection, not newly verified runtime behavior.

CURRENT 108/120
CRITICAL 0
IMPORTANT 2
FLOORS ok
VERDICT pass
