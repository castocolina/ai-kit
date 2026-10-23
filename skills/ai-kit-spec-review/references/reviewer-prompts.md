# Step 1 — Reviewer prompt templates

MANDATORY read before writing either reviewer prompt in SKILL.md's Step 1. Both templates carry
the same contract (grounding docs, declared paths authoritative, ARCHETYPE ceiling), so a
subprocess reviewer works from exactly what a native one gets, not a thinner version. Both load
the checklist by **file path** (`CHECKLIST_SKILL_MD`, Step 0.7 point 0), which every host and
every external CLI can do; no skill-invocation tool is assumed.

**Paths only, always:** never put the document content, prior reports, the conversation, or the
author's intent into either prompt.

## Subprocess route (`subprocess`, `unverified`, `custom`)

Write this text to `$RUN_TMP_DIR/iter<N>-<key>-prompt.txt` with the host's file-write tool,
substituting every `<…>`; `dispatch-reviewer` prefixes the tooling lines itself:

```
Read the file at <CHECKLIST_SKILL_MD (Step 0.7 point 0)>
and follow it exactly, substituting:
- ARCHETYPE = <ARCHETYPE>
- FRAMEWORK_PROFILE_PATH = <FRAMEWORK_PROFILE_PATH>
Read every file under review fresh from disk: <DOC_PATHS>
Complementary grounding documents (Read for context — DO NOT review,
score, or emit findings about these): <GROUNDING_DOCS>
These are the upstream context/research the document under review is
derived from. Use them to detect drift — where the document under
review contradicts or omits what its own intent/research established —
and fold that into findings about the REVIEWED document only. If
"none", there are none.
Codebase root(s) for grounding: <CODEBASE_ROOT>
The paths the document itself declares (worktree/target locations,
cross-repo references) are AUTHORITATIVE for this review — do not flag
them or "correct" them just because they differ from CLAUDE.md /
.claude/worktrees convention; only flag a path if it's internally
inconsistent or violates a hard constraint.
ARCHETYPE is the ceiling per document: judge an upstream doc (e.g.
intent) only at its own level — never demand downstream detail
(tasks, exact files, interfaces) it isn't meant to have.
Emit the report following that skill's Output template strictly, ending
with the ### Status: line. Do not edit any file under review.
```

## Native route (fresh-context delegation)

Use VERBATIM as the delegated agent's prompt, substituting only `<CHECKLIST_SKILL_MD>`,
`<DOC_PATHS>`, `<ARCHETYPE>`, `<FRAMEWORK_PROFILE_PATH>`, `<CODEBASE_ROOT>`, `<GROUNDING_DOCS>`,
`<SHARED_TOOLING_PATH>` and `<TOOL_AVAILABILITY_JSON>` (Step 0.7 point 0). When
`CHECKLIST_SKILL_MD` does not exist (a partial install) and the host has a skill-invocation
tool, replace Step 1's sentence with "Invoke the `ai-kit-spec-review-checklist` skill and follow
it exactly"; with neither, STOP — the checklist is not installed.

```
You are the reviewer.

Step 1: Read the file at <CHECKLIST_SKILL_MD> and follow it exactly (it is the
ai-kit-spec-review-checklist skill).

Step 2: The orchestrator has pre-resolved:
- ARCHETYPE = <ARCHETYPE>  (one or more of: intent, requirements, design, plan)
- FRAMEWORK_PROFILE_PATH = <FRAMEWORK_PROFILE_PATH>  (a file path on disk, or "none")
Trust these — the orchestrator has project context you don't; skip the skill's own
detection/classification. If FRAMEWORK_PROFILE_PATH is a path, Read it: it encodes this
framework's doc archetypes and review conventions (requirement syntax, delta sections,
ambiguity/parallel markers, constitutional gates) — apply them. If "none", use the generic
archetype checklists.

Step 2b: The orchestrator has also pre-resolved this machine's tooling facts:
- SHARED_TOOLING_PATH = <SHARED_TOOLING_PATH>
- TOOL_AVAILABILITY = <TOOL_AVAILABILITY_JSON>
Read SHARED_TOOLING_PATH for this repo's confirmed tool preferences and apply them during your
own grounding work (prefer rg/fd/bat/sd/eza and codegraph_explore where confirmed available,
over broad reads/legacy tools). TOOL_AVAILABILITY is the authoritative map of which of those
tools are actually installed here — it is what the checklist's legacy-tool-usage rule is gated
on, so never flag a legacy invocation whose modern replacement is not `true` in it.

Step 3: Read every file under review fresh from disk:
<DOC_PATHS>

Step 3b: Complementary grounding documents (Read for context — DO NOT review, score, or emit
findings about these): <GROUNDING_DOCS>
These are the upstream context/research the document under review is derived from (e.g. a GSD
phase's CONTEXT/RESEARCH, or a superpowers design doc behind a plan). Use them to detect drift —
where the document under review contradicts or omits what its own intent/research established —
and fold that into findings about the REVIEWED document only. If "none", there are none.

Step 4: Codebase root(s) for grounding checks: <CODEBASE_ROOT>
Ground claims against these root(s). The paths the document itself declares (worktree/target
locations, cross-repo references) are AUTHORITATIVE for this review — do not flag them or
"correct" them just because they differ from CLAUDE.md / .claude/worktrees convention; only
flag a path if it's internally inconsistent or violates a hard constraint. For cross-repo
input, ground each reference against the root it belongs to; don't chase references across
repos.

Step 5: Apply the checklist for each ARCHETYPE (Intent / Requirements / Design / Plan), plus
the framework conventions from the profile, plus Cross-Document Consistency if multiple files.
ARCHETYPE is the ceiling per document: judge an upstream doc (e.g. intent) only at its own
level — never demand downstream detail (tasks, exact files, interfaces) it isn't meant to have.

Step 6: Emit the report following the skill's output template strictly. Record `<framework> ·
<archetype(s)>` on the `### Document Type` line. End with the `### Status:` line.

Do not assume any context outside what you read. Do not edit any file under review.
```
