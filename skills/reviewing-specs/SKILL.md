---
name: reviewing-specs
description: Use when a design, spec, requirements, or plan document has been produced and needs review before the next step. Framework-aware — classifies each document into one of four archetypes (intent, requirements, design, plan) and reviews it with the matching checklist plus the source framework's own conventions (EARS, RFC-2119 SHALL, Given/When/Then, OpenSpec delta sections, Spec Kit [NEEDS CLARIFICATION]/[P], constitutional gates). Works on superpowers, OpenSpec, GitHub Spec Kit, Kiro, BMAD, GSD, or generic (docs/rfcs, docs/designs). Accepts a pre-resolved FRAMEWORK_PROFILE_PATH + ARCHETYPE from the orchestrator; falls back to its own framework detection + archetype heuristics when none provided.
---

# Reviewing Specs

Semantic correctness checker for spec-driven-development documents. Catches what linters
cannot: contradictions, omissions, wrong sequencing, missing definitions, untestable
requirements, spec-plan gaps — and violations of the *source framework's own rules*.

**Audit only — never edit the document under review.** Report findings; fixes are a separate
task (`applying-review-feedback`). The only "write" allowed is persisting an in-context
document to disk verbatim so you can `Read` it.

This skill assumes you are a clean-context reviewer. If you wrote (or watched the writing of)
the document, don't invoke it yourself — the orchestrator (`/review-spec`) dispatches a fresh
subagent first.

## Before reviewing

1. **Confirm every input is a real file path on disk.** If the caller passed inline content
   or a chat description, STOP: `### Status: Failure — input not on disk. Caller must persist
   the document and re-invoke with a path.` Reviewing in-memory content guarantees the next
   iteration reads different state and contradicts this report.
2. `Read` every document under review fresh from disk. Re-read even if you wrote it moments ago.
3. **Resolve framework + archetype.**
   - **If the orchestrator passed `FRAMEWORK_PROFILE_PATH` and `ARCHETYPE`** (the normal
     path), `Read` the profile from disk and trust the archetype — the orchestrator has
     project context you don't. Apply that archetype's checklist (below) **plus** the
     framework conventions the profile encodes (see *Framework conventions*). For a `fused`
     doc the orchestrator may pass several archetypes — apply each one's checklist.
   - **Else (fallback)**: detect the framework from path markers and read its seed profile at
     `references/frameworks/<id>.md` **resolved against this skill's own directory** (the seeds
     ship with the skill; never against the CWD, which is the user's repo) if one matches;
     classify the archetype from the profile's `doc_types` glob, or by content shape (below). If
     nothing resolves, ask the user.

Record framework + archetype(s) on the output's `### Document Type` line.

### Archetypes

Every reviewable document is one of four (a framework may **fuse** several into one file —
review it against each fused checklist):

| Archetype | What it is | Content-shape tell (fallback) |
|---|---|---|
| `intent` | why + what; scope, motivation, success | prose stating a problem/goal, no testable clauses or tasks |
| `requirements` | testable behavior the system must exhibit | numbered requirements, SHALL/EARS/user-stories, acceptance criteria |
| `design` | how — architecture, data flow, contracts | components, interfaces, data models, diagrams; no step-by-step tasks |
| `plan` | ordered, actionable work items | `### Task N`, `- [ ]` checkboxes, exact files/commands |

`constitution` and `state` documents are **context** — `Read` them for grounding, don't
review them.

## Intent checklist

Intent's job is to make the *why* and *what* unambiguous and worth doing — not the how.

**CRITICAL:** purpose self-contradictory (two valid readings → different systems); scope
includes mutually exclusive goals; contradicts an existing spec it refines.
**HIGH:** motivation not grounded in a real need (solution looking for a problem / YAGNI);
success stated only as activity, never as an outcome; material unstated external assumption;
scope unbounded ("and anything else useful").
**MEDIUM:** vague success metric with a reasonable default; redundant restatement.

## Requirements checklist

Requirements must be **individually testable, unambiguous, and in the framework's syntax**.

**CRITICAL:** a requirement with two readings that imply opposite behavior; requirements that
contradict each other; (delta frameworks) a `MODIFIED`/`REMOVED` entry that doesn't match any
existing requirement in the stable spec.
**HIGH:**
- **Not testable** — "fast", "user-friendly", "robust" with no measurable criterion.
- **Wrong/absent requirement syntax for the framework** — e.g. Kiro requirement not in an
  EARS shape; OpenSpec requirement missing "SHALL"; one clause bundling several behaviors.
- **Acceptance criteria missing** when the framework expects them (Given/When/Then, EARS).
- **Implementation detail leaking into a spec** when the framework forbids it (OpenSpec:
  `spec.md` is behavior, not how).
- **Unresolved ambiguity markers** left in (Spec Kit `[NEEDS CLARIFICATION: …]`).
- Missing error/edge behavior the requirement implies.
**MEDIUM:** thin coverage; numbering/ID gaps; minor ambiguity with a safe default.

## Design checklist

A design's job is intent, architecture, and codebase grounding — not implementation detail.
Missing file paths/code/step detail is **not** a defect here.

**CRITICAL:** architecture components can't coexist (logical circularity); contradicts a hard
codebase constraint (e.g. sync API where the layer is strictly async); contradicts an
existing spec it refines.
**HIGH:** a major component has no stated responsibility; data flow between components
unspecified (what crosses the boundary, not wire format); testing approach absent (at least
*how*); architectural error-handling absent; scope creep / YAGNI; material unstated external
assumption. Plus the **codebase-grounding** rules below.
**MEDIUM:** thin sections, minor ambiguity with a default, internal redundancy.

## Plan checklist

A plan must be executable by an engineer with zero project context: exact files, exact code,
exact commands.

**CRITICAL:** circular dependencies; wrong execution order; spec↔plan contradiction;
components/interfaces referenced but never defined; unresolvable ambiguity (two readings,
opposite outcomes).
**HIGH:** design choices tooling can't see (raw strings where enums belong); missing
error/failure paths; interface contracts unspecified; non-actionable steps ("handle errors
appropriately"); a `[P]`/parallel-marked task that actually shares state or has an ordering
dependency; material unstated assumption; scope creep.
**MEDIUM:** undefined success criteria, missing rollback, test-coverage gaps, cross-section
inconsistency.
**LOW / Tooling-Catchable:** mechanical lint only. If it's actually a design decision (enums
vs strings), rate HIGH — the agent is the only line of defense.

## Framework conventions (apply via the profile)

The profile turns generic checks into framework-specific ones. Key fields:

- `requirement_syntax`: `ears` → check WHEN/WHILE/IF…THEN + SHALL shapes, one behavior each;
  `rfc2119-shall` → SHALL/MUST/SHOULD/MAY present and used correctly; `user-story` → "As a…,
  I want…, so that…" + acceptance criteria; `freeform` → judge testability, no fixed shape.
- `acceptance_criteria_format`: `gwt` (Given/When/Then) or `ears` expected on requirements.
- `delta_model: true` (OpenSpec): delta specs must use `## ADDED/MODIFIED/REMOVED
  Requirements`; verify MODIFIED/REMOVED target a real existing requirement.
- `ambiguity_markers` (e.g. `[NEEDS CLARIFICATION]`): any left unresolved → HIGH.
- `parallel_task_marker` (e.g. `[P]`): verify marked tasks are truly independent.
- `constitution` docs present: a design/plan violating a stated constitutional gate → finding.
- Folder-name traps the profile notes (Spec Kit `plan.md` is *design*; superpowers `specs/`
  holds *design* docs) — classify by the profile, not the folder name.

If no profile is available, review with the generic archetype checklists and say so.

## Codebase grounding (Design & Requirements)

Ground against the **codebase root the caller gave you** — with worktrees that root is often not
your CWD. Resolve every relative path the document mentions against that root before `Read`ing it;
a file that looks "missing" may simply live in the worktree you weren't pointed at.

**Declared paths are authoritative — don't normalize them to convention.** When the document
declares concrete locations (worktree/target dirs, cross-repo references), treat them as the
source of truth for this review. A plan may deliberately place a worktree outside the ambient
convention (e.g. `../.worktrees/target-repo/<wt>` for a cross-repo execution even though
`CLAUDE.md`/`.claude/worktrees` say otherwise) — the user's plan outranks the convention. Flag a
declared path only if it's **internally inconsistent** (two paths for the same thing) or violates
a hard constraint; never "correct" it toward the convention, and don't chase references across
repos — ground each claim against the specific root it belongs to.

- **Missing** — introduces new code/patterns without referencing existing reusable code,
  utilities, or conventions. Name the specific existing file/function/pattern → HIGH.
- **Unverified factual claim** — the doc claims something about an existing file/function/
  skill (behavior, interface, location). You MUST `Read` the referenced file and confirm.
  Confirming a file *exists* is not enough — read its content.

  > **No downgrade on wrong factual claims.** A wrong premise about existing code → CRITICAL,
  > always. Do not demote to MEDIUM with "works regardless" / "logic still coherent" — a false
  > premise means two readers form different mental models and the doc's motivation may
  > collapse once corrected.

## Linter-silencing exceptions (`# nosec`, `# noqa`, `type: ignore`)

Acceptable only when the justification explains *why the rule doesn't apply* (e.g. `# nosec
B310` on a URL from app config, not user input). "Required for functionality" or no comment → HIGH.

## Output

Minimal and structured — the reader may be an agent. No narration or summaries. State required
*outcomes*, not suggested edits.

Per issue: `- **<title>** — Location: <section/lines>. Required: <verifiable outcome>. Why: <reason>.`

### Approved

```
## Review: <file(s)>
### Document Type
<framework> · <archetype(s)>
### Files Read
- <path> (N lines)
### Status: Approved
```

Optionally one `### Non-blocking notes` (≤3 bullets). No empty severity headings, no
fixed-issue history.

### Issues Found

```
## Review: <file(s)>
### Document Type
<framework> · <archetype(s)>
### CRITICAL
- ...
### HIGH
- ...
### MEDIUM            (optional)
### Cross-Document Consistency   (if 2+ files)
- ...
### Status: Issues Found — fix and re-invoke
```

On re-review, evaluate current state fresh; if blocking issues are resolved, switch to the
Approved shape — don't carry "previously flagged, now fixed" forward.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Editing the document under review | Never. Audit only. |
| Classifying by folder name | Use the profile's `doc_types`; folder names mislead (Spec Kit `plan.md` = design). |
| Plan-level strictness on a design or intent | Missing code/file paths isn't a defect there. An `intent`/CONTEXT doc is judged on why/what clarity — never demand tasks or exact files. |
| "Correcting" a declared worktree/target path to match `.claude/worktrees` / `CLAUDE.md` | The plan's declared paths win. Only flag internal inconsistency or hard-constraint violations. |
| Ignoring the framework's requirement syntax | A non-EARS Kiro requirement / SHALL-less OpenSpec requirement is a real finding. |
| Leaving `[NEEDS CLARIFICATION]` unflagged | Unresolved ambiguity marker → HIGH. |
| Confirming a referenced file exists without reading it | Read its content. Wrong claim → CRITICAL. |
| Reviewing a `constitution`/`state` doc as if it were a spec | Those are context — read, don't review. |
| Reviewing in the same context that wrote the doc | Stop. Clean-context reviewer only; dispatch via `/review-spec`. |
