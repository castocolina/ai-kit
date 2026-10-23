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

DIGEST fd6afc654e0c4f76
TREE 605c224074237b4bb8817fe9ed2c68553caa4508

# Skill evaluation: ai-kit-gsd-spec-discuss

Evaluated committed tree `e34499eae26a0cd73ddf5e39e458b1d821c80f70` using `tmp/judge/rubric.md`. Read the complete skill, all four references, all three bundled scripts, the shared client, and relevant installed GSD workflows. Files larger than 50 KB were read in chunks. No files were edited.

**Pattern:** Process, with Tool-style decision routing.  
**Estimated knowledge ratio:** Expert 85% / Activation 12% / Redundant 3%.  
**Assessment:** Strong domain-specific guidance, but the bundled Edge Coverage gate can report success after extracting no requirements.

## PART 1 — Dimensions

D1 18/20 — 90.0%. Substantial knowledge delta: GSD routing traps, advisory confidence handling, immutable user decisions, and cross-phase amendment rules. Improvement: move historical phase identifiers and repeated empirical anecdotes into the worked examples (`SKILL.md:145–150`, `173–179`).

D2 14/15 — 93.3%. The evidence-first mindset connects well to concrete procedures, including neutral questions, second opinions, and blocking-versus-ledger decisions (`SKILL.md:12–16`, `144–152`; `references/decision-table.md:17–55`). Improvement: make successful repair verification part of the incompatible-client recovery procedure.

D3 15/15 — 100.0%. The NEVER list names specific failure modes and explains their consequences: listing instead of writing CONTEXT, unwanted plan advancement, cross-item contamination, lost locked decisions, and coverage drift (`SKILL.md:188–205`).

D4 15/15 — 100.0%. Valid frontmatter and matching directory/name. The description specifies WHAT, WHEN, searchable invocation examples, backend-free operation, and exclusions (`SKILL.md:1–4`). The 500-word cap was not applied.

D5 14/15 — 93.3%. Explicit mandatory loading points, conditional worked examples, and “Do NOT load” guidance provide effective layering (`SKILL.md:64`, `106`, `110–111`, `214–224`). Improvement: keep historical supporting evidence in the conditional examples rather than the core recipe.

D6 13/15 — 86.7%. Appropriately constrains consent, data disclosure, workflow routing, and locked decisions while preserving agent judgment. Improvement: enforce the promised fail-closed behavior when requirement extraction produces an empty input (`scripts/edge_floor.py:36–43`, `169–184`).

D7 9/10 — 90.0%. A clear Process pattern covers setup, phase progression, decision resolution, logging, amendments, and stopping. Improvement: consolidate repeated ladder/logging guidance to sharpen the primary execution path.

D8 11/15 — 73.3%. **Below floor 12.** Common-case guidance is actionable, with useful fallback and error handling, but the coverage gate has a verified false-success path. Improvement: reject missing, empty, or unparseable Requirements before invoking the engine; add a regression check proving malformed input cannot yield a successful gate. Also make the client-repair recipe locate its installer and verify compatibility afterward.

## Findings

### Important — Empty requirement extraction can pass the coverage gate

**Sources:** `skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py:36–43`, `146–157`, `169–184`; `skills/ai-kit-gsd-spec-discuss/SKILL.md:76–82`.

The extractor recognizes only numbered entries beginning with bold text under `## Requirements`. A missing section or an entry such as `1. Parse rows` produces an empty requirement list. Nothing rejects that list before engine execution.

Read-only checks confirmed:

- Both malformed examples extract `[]`.
- The installed engine accepts `[]` and returns an empty floor.
- Comparing that floor with an absent coverage table returns `ok: true`.

The skill presents `check` as the coverage gate, so this can appear successful without checking any requirement.

**Required improvement:** fail closed on zero extracted requirements and detect unsupported requirement formatting. Add regression coverage for missing and malformed Requirements sections.

### Minor — Incompatible-client recovery assumes an installer location and source

**Source:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:40–43`.

The replacement command is supported, but `python3 tools/setup.py …` assumes a working directory containing that script. Inspection also confirmed that setup selects its source through `AI_KIT_DIR` or the configured installation location, not automatically from the script’s checkout. The command relinks content; it does not fetch an updated client.

An agent following the recipe from a consuming GSD project may therefore fail to locate the installer or relink an unchanged client.

**Improvement:** identify the ai-kit installation first, state the source requirement, and rerun `detect` to confirm compatibility rather than treating command completion as repair.

## Special check — `needs_fallback` recipe

**Confirmed present.** `skills/ai-kit-gsd-spec-discuss/SKILL.md:151–152` explicitly maps answering columns carrying `fallback: true`—the client’s `needs_fallback`—to the agent’s **own reasoning** against the SPEC, earlier CONTEXT files, and live facts, followed by logging and appropriate ledgering.

This is an actionable recipe, not merely a mention of the field. No Critical finding applies.

## Verification limits

Skipped end-to-end workflow execution, network calls, and the test suite to preserve read-only evaluation. The demonstrated empty-input gate remains the material risk.

CURRENT 109/120
CRITICAL 0
IMPORTANT 1
FLOORS fail
VERDICT fail

DIGEST fd6afc654e0c4f76
TREE f0f23f4b8c1f617c34bf6950671c01b0a3a937b0

# Skill evaluation: ai-kit-gsd-spec-discuss

Evaluated committed tree `beb51f75f352fb09b3f812b6765b75d520c41f2f` using `tmp/judge/rubric.md`. Working tree is clean; no `pending-orchestrator` marker was found in the judged skill.

**Pattern:** Process, with Tool-style decision routing.  
**Estimated knowledge ratio:** Expert 85% / Activation 10% / Redundant 5%.  
The 500-word body cap was not applied.

## Dimension scores

D1 18/20 — 90%. Strong domain knowledge: misleading GSD flags, context preservation, backend-specific escalation and engine-derived coverage. Some historical examples repeat lessons already established in the workflow and references (`SKILL.md:144–150`, `references/worked-examples.md:6–29`). Trim repeated anecdotes while retaining the operational rules.

D2 15/15 — 100%. Transfers both judgment and procedures: evidence outranks model confidence, blocking means dependencies within this run, and scope deferral requires feasibility checking (`SKILL.md:12–16`; `references/decision-table.md:46–65`).

D3 15/15 — 100%. Specific prohibitions explain consequential failure modes: accidental plan-phase dispatch, silent loss of locked decisions, cross-item contamination and fabricated coverage (`SKILL.md:188–205`).

D4 15/15 — 100%. Valid frontmatter and matching name. The description identifies capabilities, explicit triggering requests, backend terminology and exclusions (`SKILL.md:1–4`).

D5 14/15 — 93.3%. The 224-line entry point has mandatory, workflow-embedded reference triggers and explicit skip guidance (`SKILL.md:64`, `106–111`, `214–224`). Reduce duplication between the ladder narrative and decision-table reference for full marks.

D6 14/15 — 93.3%. Appropriately strict around consent, remote payloads, locked decisions and coverage; appropriately flexible around provisional reasoning and host limitations (`SKILL.md:51–59`, `151–164`, `207–212`). Clarify completion behavior when GSD deliberately skips commits.

D7 9/10 — 90%. Clear setup → spec → discuss → decision → persistence process, supported by conditional references. Repeated reference navigation and historical detail slightly dilute an otherwise well-chosen pattern (`SKILL.md:18–224`).

D8 12/15 — 80%. Actionable request shapes, malformed-item recovery, second opinions, size guards and no-client behavior agree with the inspected scripts (`SKILL.md:123–152`; `scripts/decide.py:128–202`, `381–447`). Commit-success handling and inconsistent log-column rules prevent a higher score.

**No dimension is below its floor.**

## Findings

### Important

1. **Committed-output promises omit GSD’s supported commit-skipping behavior.**  
   **Source:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:83`, `110–114`.  
   The skill says the workflow commits the SPEC and prescribes subsequent phase/state commits without requiring inspection of their outcomes. The installed `spec-phase.md:520` explicitly says `commit_docs: false` produces `skipped`, leaving the SPEC uncommitted. An unattended run can therefore produce the artifacts without delivering the promised committed tree.  
   **Improvement:** Check each commit result; explicitly report skipped or failed commits instead of treating the phase as committed.

### Minor

1. **Backend-column inclusion rules disagree.**  
   **Sources:** `skills/ai-kit-gsd-spec-discuss/references/decision-table.md:74–75`; `skills/ai-kit-gsd-spec-discuss/references/log-formats.md:29–30`.  
   The ledger includes backends that answered; the log retains backends that were available, even if never called. These can intentionally differ, but that distinction is not explained. State the artifact-specific rule explicitly.

2. **The discussion-log template asserts CodeGraph use unconditionally.**  
   **Source:** `skills/ai-kit-gsd-spec-discuss/references/log-formats.md:71`.  
   The analyzer brief correctly makes CodeGraph conditional (`references/analyzer-brief.md:25–32`), but the log’s Mode line always includes it. Make that token conditional to avoid unsupported provenance claims.

## Special check: `needs_fallback`

**Confirmed.** `skills/ai-kit-gsd-spec-discuss/SKILL.md:151–152` explicitly maps answering columns carrying `fallback: true`—identified as the client’s `needs_fallback`—to **own reasoning against the SPEC, earlier CONTEXT files and live facts**, followed by logging and appropriate ledgering. The recipe is present; no missing-recipe Critical finding applies.

Read-only review covered every file in the judged skill, the shared client and backend notes, relevant tests, and the directly named installed GSD workflows/resolver/engine. No files were changed.
Tests and live backend calls were not run; runtime success and external-service behavior remain unverified.

CURRENT 112/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
VERDICT pass
