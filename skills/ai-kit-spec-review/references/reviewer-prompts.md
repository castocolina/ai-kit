# Step 1 — Reviewer prompt templates

MANDATORY read before writing either reviewer prompt in SKILL.md's Step 1. Both templates carry
the same contract (grounding docs, declared paths authoritative, ARCHETYPE ceiling), so a
subprocess reviewer works from exactly what a native one gets, not a thinner version. Both load
the checklist by **file path** (`CHECKLIST_SKILL_MD`, Step 0.7 point 0), which every host and
every external CLI can do; no skill-invocation tool is assumed.

**Paths only, always:** never put the document content, prior reports, the conversation, or the
author's intent into either prompt.

**One archetype value or one line per document.** `<ARCHETYPE>` is the single value when every
document under review has the same archetype(s), always so for one document. When they differ,
substitute `per document:` followed by one line per DOC_PATHS entry, `<path>=<archetype(s)>`
(the form of the resume payload's `doc_archetypes`; a fused document joins its archetypes with
`+`, e.g. `intent+requirements+design`), so each file is reviewed only at its own
ceiling. `<FRAMEWORK_PROFILE_PATH>` stays one value: Step 0.5 resolves one framework per
invocation. Step 3 binds each finding to its document's archetype from the same lines, and a
resume restores them from `doc_archetypes`. With more than one file under review, both
templates make every finding's `Location` lead with the file's path, and on a fused document
(one or several files) they add the finding's archetype, `Location: <path> [<archetype>]:
<section/lines>`; the merge keys on the Location verbatim, so findings on different files never
fuse, and Step 3 surfaces a finding whose document or archetype it cannot tell instead of
dispatching it. Example, a GSD phase's context reviewed beside its
plan (the plan checklist never reaches the context file):

```
- ARCHETYPE = per document:
  /work/repo/.planning/phases/<phase>/NN-CONTEXT.md=intent
  /work/repo/.planning/phases/<phase>/NN-01-PLAN.md=plan
- FRAMEWORK_PROFILE_PATH = /abs/path/to/frameworks/gsd.md
```

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
with the ### Status: line. Whenever more than one file is under review,
start every finding's Location with that file's path; on a file
reviewed at several archetypes, also name the finding's archetype in
square brackets after the path, then a colon and the section or lines.
Do not edit any file under review.
```

## Native route (fresh-context delegation)

Use VERBATIM as the delegated agent's prompt, substituting only `<CHECKLIST_SKILL_MD>`,
`<DOC_PATHS>`, `<ARCHETYPE>`, `<FRAMEWORK_PROFILE_PATH>`, `<CODEBASE_ROOT>`, `<GROUNDING_DOCS>`,
`<SHARED_TOOLING_PATH>` and `<LENS_LINES>` (Step 0.7 point 0; `<LENS_LINES>` below). When
`CHECKLIST_SKILL_MD` does not exist (a partial install) and the host has a skill-invocation
tool, replace Step 1's sentence with "Invoke the `ai-kit-spec-review-checklist` skill and follow
it exactly"; with neither, STOP — the checklist is not installed.

```
You are the reviewer.

Step 1: Read the file at <CHECKLIST_SKILL_MD> and follow it exactly (it is the
ai-kit-spec-review-checklist skill).

Step 2: The orchestrator has pre-resolved:
- ARCHETYPE = <ARCHETYPE>  (one or more of: intent, requirements, design, plan; or "per document:" with one <path>=<archetype(s)> line per file)
- FRAMEWORK_PROFILE_PATH = <FRAMEWORK_PROFILE_PATH>  (a file path on disk, or "none")
Trust these — the orchestrator has project context you don't; skip the skill's own
detection/classification. If FRAMEWORK_PROFILE_PATH is a path, Read it: it encodes this
framework's doc archetypes and review conventions (requirement syntax, delta sections,
ambiguity/parallel markers, constitutional gates) — apply them. If "none", use the generic
archetype checklists.

Step 2b: The orchestrator has also pre-resolved this machine's tooling facts:
- SHARED_TOOLING_PATH = <SHARED_TOOLING_PATH>
- TOOL_AVAILABILITY = {}
- LENS LINES: <LENS_LINES>
Read SHARED_TOOLING_PATH for this repo's tool preferences. TOOL_AVAILABILITY is empty: this
dispatch makes no tool claim, so the checklist's legacy-tool-usage rule flags no legacy
invocation. Apply each skill the LENS LINES name as an advisory lens, loading it by name only
if your host provides it (unverified); a lens never changes what you review.

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

Step 5: Apply the checklist for each ARCHETYPE (Intent / Requirements / Design / Plan), to each
file only its own archetype(s) when ARCHETYPE reads "per document", plus
the framework conventions from the profile, plus Cross-Document Consistency if multiple files.
ARCHETYPE is the ceiling per document: judge an upstream doc (e.g. intent) only at its own
level — never demand downstream detail (tasks, exact files, interfaces) it isn't meant to have.

Step 6: Emit the report following the skill's output template strictly. Record `<framework> ·
<archetype(s)>` on the `### Document Type` line. Whenever more than one file is under review, start
every finding's Location with that file's path; on a file reviewed at several archetypes, also
name the finding's archetype: `Location: <path> [<archetype>]: <section/lines>`. End with the
`### Status:` line.

Do not assume any context outside what you read. Do not edit any file under review.
```

`<LENS_LINES>` is the stdout of `python3 "$TOOLS_PY" capability-block --runtime <the session's own runtime id> --model <the session model id> --role review --native --cwd <CODEBASE_ROOT> --files <each DOC_PATHS entry>` (the same lens selection the subprocess lanes get, lens lines only), or `none` when `TOOLS_PY` is missing (a partial install) or the command exits non-zero (quote its stderr in the surface message).
