---
name: review-spec
description: Use when a design, spec, requirements, or plan document needs a clean-context review-and-fix loop before the next step. Orchestrates a reviewer subagent (reviewing-specs), then routes the rewrite by the document's originating framework — superpowers docs back to brainstorming/writing-plans, GSD plans to /gsd-plan-phase --reviews then gsd-plan-checker, everything else to the applying-review-feedback fixer. Persists in-memory docs to disk first; worktree- and framework-aware; scopes each doc to its lifecycle stage; loops until approved or the iteration cap. Triggered by "review-spec", "review my spec/plan", or passing document path(s).
---

## Your Task

You are the orchestrator running as the `review-spec` skill (invocable via `/review-spec`, by asking to review a spec/plan, or programmatically). You were given one or more document paths. Your job: drive a review-and-fix loop using clean-context subagents (a reviewer, and a rewrite handler chosen by framework), surface the outcome to the user, and never edit the document yourself.

## Inputs

- **Document path(s):** taken from the user's invocation arguments. If absent, ask the user for absolute paths and stop.
- **Codebase root:** the worktree that contains the document — resolved in Step 0.1, **not** assumed to be your CWD. With worktrees, the spec/plan and the code it grounds against live in a checkout that is often *not* where you were invoked.

## Step 0 — Persist before dispatch (ALWAYS)

Before any subagent dispatch, every document under review **must exist on disk** at a stable path. Subagents run in isolated contexts and read inputs via the `Read` tool; an in-memory document does not survive the dispatch boundary, and the next iteration would re-read the unfixed file and contradict itself.

| Caller state | Action |
|---|---|
| User passed real file path(s) that exist on disk | Continue to Step 1. |
| Doc was just produced in this session by `brainstorming` / `writing-plans` and SAVED to a path | Confirm the file exists on disk via a `Read` call before Step 1. Do not assume. |
| Doc only exists in chat (in-memory, not yet persisted) | STOP. Tell the user: "The document is not on disk. To run `/review-spec` I need to persist it first to a stable path." Offer a default location appropriate to the framework in use (superpowers → `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` or `.../plans/YYYY-MM-DD-<feature>.md`; Spec Kit → `specs/<NNN>-<feature>/spec.md` or `plan.md`; OpenSpec → `openspec/changes/<id>/proposal.md` or `tasks.md`; otherwise ask). After the user confirms, write the document verbatim to the chosen path, then continue. |
| Path was given but file does not exist | STOP. Surface a Failure: `Path does not exist: <path>. Persist the document first.` |

Do not paraphrase the document into the subagent prompt as a workaround — that defeats the clean-context guarantee. The subagent must `Read` the file from disk.

## Step 0.1 — Resolve the codebase root (worktree-aware)

Plans and designs are routinely written/executed in an **isolated worktree** (superpowers
`using-git-worktrees` puts them under `.worktrees/<name>/`, `worktrees/`, or a sibling `../<name>/`),
while you may have been invoked from the main checkout. A clean-context subagent has no way to know
this — if you hand it the wrong root, its codebase-grounding checks read the *main* branch's files
instead of the worktree's, producing phantom "X doesn't exist / contradicts the code" findings (or
silently passing real ones). The root **must be the worktree that owns the document**, derived from
the document's own location:

1. **Derive from the doc, not CWD.** For the first document path, take its directory and run
   `git -C "<doc-dir>" rev-parse --show-toplevel`. That toplevel is the authoritative codebase root —
   it resolves to whichever worktree the file physically lives in. Use it as `<CODEBASE_ROOT>`.
2. **If that fails or feels ambiguous** (doc outside any repo, multiple docs in different roots, or
   you're unsure which checkout is "live"), run `git -C "<doc-dir>" worktree list` and inspect the
   output: each line is `<path>  <sha>  [<branch>]`. Match the document's path prefix to a worktree
   `<path>`; that path is the root. If several docs map to *different* worktrees, that's a red flag —
   stop and ask the user which checkout to ground against (do not silently pick one).
3. **Pass the resolved worktree root** as `<CODEBASE_ROOT>` to **both** the reviewer and the fixer.
   Never default to your CWD or the main repo root when the document lives in a worktree.

**The plan's declared paths win — do not normalize them to convention.** A plan may
deliberately declare a worktree/target outside the ambient convention (e.g. a cross-repo
execution that creates `../.worktrees/target-repo/<wt>` even though `CLAUDE.md` /
`CLAUDE.local.md` recommend `.claude/worktrees/`). For *this* review, authority runs:
**(1) the explicit paths in the plan/spec under review → (2) `CLAUDE.local.md` → `CLAUDE.md`
→ (3) Claude's default recommendation.** The reviewer grounds against the paths the plan
declares, AS DECLARED; it must not flag them merely for diverging from convention, and must
not "correct" them toward `.claude/worktrees`. Carry this precedence into the reviewer prompt.

**Cross-repo plans have more than one root.** If the document references files in a second
repo/worktree (a target repo it acts on), don't force a single `--show-toplevel`. Capture each
**declared** root from the plan, label which references belong to which root, and pass the set
so the reviewer grounds each claim against the right checkout instead of chasing references
across both. If the roots are unclear, run `git worktree list` in each repo and ask once.

Record the result as `CODEBASE_ROOT` (one root, or a labeled set for cross-repo plans).

## Step 0.5 — Detect framework, resolve its profile, classify archetype

The reviewer/fixer are clean-context subagents — give them the framework's rules as a **file
path**, not prose. You (orchestrator, in the user's session, with web access) do the detection
and any research; they just `Read` the profile. Three sub-steps:

First resolve `SEEDS_DIR` and `CACHE_DIR` to absolute paths (see Constants) — every profile path
below and the `FRAMEWORK_PROFILE_PATH` you pass to subagents must be absolute, never a bare
relative `references/frameworks/…`.

**A. Detect the framework.** Match the document path + nearby project markers against the
`detection_signals` of the known profiles (bundled seeds in `SEEDS_DIR`). Conversation signal
wins: if the user just used a framework's skill (superpowers `brainstorming`/`writing-plans` →
`superpowers`), use it. If markers are ambiguous, ask once.

**B. Resolve the profile** (an **absolute** path on disk), in order:
1. `CACHE_DIR/<id>.md` if it exists and isn't stale → use it.
2. else the bundled seed `SEEDS_DIR/<id>.md` → use it.
3. else **unknown framework** → research it (web: official repo/docs), write a new profile to
   `CACHE_DIR/<id>.md` following `SEEDS_DIR/SCHEMA.md` (frontmatter + conventions), set
   `last_updated` to today, then use it. Tell the user one line: "Learned framework `<id>`;
   cached its profile."

Staleness: a cached profile for a known-to-drift framework (`bmad`, `gsd`) older than ~180 days
is a refresh candidate — you may re-research and rewrite the **cache** copy (bump
`last_updated`). Never overwrite a bundled seed in place. Record the resolved path as
`FRAMEWORK_PROFILE_PATH` (or `none` if you genuinely can't resolve a framework, e.g. generic
`docs/rfcs/` — the reviewer then uses generic checklists).

**C. Classify the archetype** from the resolved profile's `doc_types` (glob → archetype).
Conversation signal still wins (`brainstorming` → a fused `intent+requirements+design` design
doc; `writing-plans` → `plan`). A `fused` doc yields several archetypes — pass them all. If the
path matches no `doc_types` glob, fall back to content shape (see the reviewer skill's archetype
table) or ask. Record as `ARCHETYPE` (one or more of: `intent`, `requirements`, `design`, `plan`).

**Low-confidence detection → generic.** If the framework stays ambiguous and the user cannot
disambiguate, set `FRAMEWORK_PROFILE_PATH = none` and route every archetype through the generic
`applying-review-feedback` fixer (Step 3a). State this in the final Surface message ("Framework
ambiguous — used the generic fixer.") so routing stays transparent.

Pass both `FRAMEWORK_PROFILE_PATH` and `ARCHETYPE` to the reviewer and fixer below.

## Step 0.6 — Scope the review to the project's lifecycle stage

Frameworks have stages (GSD: context/discussion → requirements → roadmap → research → plan →
status; OpenSpec: proposal → design → specs → tasks; superpowers: design → plan). Reviewing an
early-stage document as if it were a finished plan is the most common failure — e.g. invoked in
GSD with only `PROJECT.md`/CONTEXT present, the reviewer demands tasks and exact files that the
*intent* stage does not have yet. Don't. Resolve scope before dispatch:

1. **See what exists.** Glob the profile's `doc_types` against the project root. The
   furthest-along present archetype (per the profile's `lifecycle_order`) is the **current
   stage**.
2. **Review each existing document at its own archetype** — the `ARCHETYPE` from Step 0.5 is
   per-document and is the ceiling. Never escalate an upstream doc to a downstream checklist:
   a bare `intent`/CONTEXT is judged on why/what clarity and scope, **not** on missing tasks,
   files, or interfaces. (The reviewer skill enforces this too; set the right `ARCHETYPE` so it
   never has to guess.)
3. **Missing required prerequisites are gaps, not defects.** A `required: true` doc-type absent
   at or before the current stage → note it to the user as a prerequisite to produce next, not
   as a finding inside an existing document.
4. **Insufficient-info guard.** If the user asked to review an artifact a later stage hasn't
   produced (e.g. "review the plan" but only `intent` exists), STOP and surface:
   `Only <existing docs> exist; the project is at the <stage> stage. There is no <requested
   archetype> to review yet. I can review <existing> as <archetype>, or wait until <next
   stage> is produced.` Do not invent a deeper review or ask for downstream detail.

When the user passed explicit path(s), review exactly those at their archetypes — do not pull
in downstream scope. When the user passed none ("review my specs"), review every existing doc
at its archetype and list the gaps.

5. **Supply complementary grounding to the reviewer.** A document under review is usually
   derived from upstream context the reviewer should read but NOT review. When reviewing a
   `plan` (or `design`), gather the framework's sibling context/research for that same unit of
   work and pass them as `GROUNDING_DOCS` (Step 1): for GSD, the phase's `NN-CONTEXT.md`
   (intent) and `NN-RESEARCH.md` (research) — plus `NN-PATTERNS.md`/`NN-UI-SPEC.md` if present —
   from the same `.planning/phases/<phase>/` dir; for superpowers, the sibling `*-design.md` for
   a plan. The reviewer grounds the document against these to catch drift (plan contradicts its
   own intent/research) but emits **no findings about the grounding docs themselves**. Context/
   state archetypes (`state`, discussion logs, verification, summaries) are grounding-only, never
   reviewed. If no sibling context exists, pass `none`.

## Constants

- **Reviewer skill:** `reviewing-specs`
- **Fixer skill:** `applying-review-feedback`
- **Subagent type for both:** `general-purpose`
- **Subagent model for both:** `sonnet` (Haiku misses subtle defects; Opus burns tokens for no extra review-quality signal)
- **Iteration cap:** 3 (configurable per invocation if user requests)
- **Loop state file (optional):** `/tmp/review-spec-<doc-basename>-<timestamp>.log` — append iter# + status line each round, for debugging only.
- **Framework profile seeds dir** (`SEEDS_DIR`) — resolve once to an **absolute** path. As a skill
  you are not guaranteed a `CLAUDE_PLUGIN_ROOT`; take the **first existing** of, in order:
  1. `${CLAUDE_PLUGIN_ROOT}/skills/reviewing-specs/references/frameworks/` (when set)
  2. `~/.claude/skills/reviewing-specs/references/frameworks/` (symlinked install — what `tools/install.sh` creates)
  3. the sibling of this skill: `<dir-of-this-SKILL.md>/../reviewing-specs/references/frameworks/`

  ```bash
  # SKILL_DIR = the directory containing this SKILL.md (the review-spec skill)
  for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/reviewing-specs/references/frameworks}" \
           "$HOME/.claude/skills/reviewing-specs/references/frameworks" \
           "$SKILL_DIR/../reviewing-specs/references/frameworks"; do
    [ -d "$d" ] && { SEEDS_DIR="$d"; break; }
  done
  ```
  If none of the three fallbacks resolves to an existing directory, STOP and surface to the user: `The reviewing-specs skill is not installed (no framework profiles found). Install ai-kit and re-invoke.` — do not invent a path or proceed.

  It holds the curated seed profiles `<id>.md` and `SCHEMA.md`. **Never reference these as a bare
  relative `references/frameworks/…`** — your CWD is the user's repo (often a worktree), not the kit.
- **Framework profile cache** (`CACHE_DIR`): `~/.claude/cache/framework-profiles/*.md` (absolute,
  user-global) — learned/refreshed profiles the orchestrator writes for frameworks not covered by a
  seed. Create the dir on first write.

## NEVER (hard landmines)

These are the failures that have actually bitten this loop. Violating any one silently corrupts the review:

- **NEVER dispatch any subagent before every document under review is saved on disk** (Step 0). Subagents read via `Read`; an in-memory doc does not survive the dispatch boundary.
- **NEVER run the generic fixer before the reviewer's report is written to its temp file** (Step 3). The fixer has nothing to `Read` otherwise.
- **NEVER paraphrase the document (or prior reports, or the conversation) into a subagent prompt** as a workaround — pass paths only. Inlining defeats the clean-context guarantee.
- **NEVER default `CODEBASE_ROOT` to your CWD.** Always derive it from the document's own worktree via `git` (Step 0.1); the wrong checkout yields phantom findings.
- **NEVER edit the document yourself, and never reuse a subagent across iterations.** Orchestrator is dispatch + parse; a fresh subagent each round keeps the audit clean.

The `## Hard rules for the orchestrator` table near the end carries the full list with reasons.

## Loop

Run this loop. Each iteration is one reviewer dispatch followed by (conditionally) one fixer dispatch.

```dot
digraph review_spec {
    "Start" [shape=doublecircle];
    "Dispatch reviewer subagent (fresh)" [shape=box];
    "Parse Status line" [shape=diamond];
    "Approved" [shape=box, style=filled, fillcolor=lightgreen];
    "Issues Found?" [shape=diamond];
    "Iter < cap?" [shape=diamond];
    "Resolve route per archetype" [shape=diamond];
    "Step 3a generic fixer" [shape=box];
    "Parse fixer Status" [shape=diamond];
    "Step 3b-skill native revise" [shape=box];
    "Step 3b-cmd native command" [shape=box];
    "Slash tool available?" [shape=diamond];
    "Step 3b-surface" [shape=box];
    "Native revise handed off" [shape=box, style=filled, fillcolor=orange];
    "Step 3c validate?" [shape=diamond];
    "Cap reached" [shape=box, style=filled, fillcolor=orange];
    "Surface to user" [shape=doublecircle];

    "Start" -> "Dispatch reviewer subagent (fresh)";
    "Dispatch reviewer subagent (fresh)" -> "Parse Status line";
    "Parse Status line" -> "Approved" [label="Approved"];
    "Parse Status line" -> "Issues Found?" [label="Issues Found"];
    "Issues Found?" -> "Iter < cap?" [label="yes"];
    "Issues Found?" -> "Surface to user" [label="no"];
    "Iter < cap?" -> "Resolve route per archetype" [label="yes"];
    "Iter < cap?" -> "Cap reached" [label="no"];

    "Resolve route per archetype" -> "Step 3a generic fixer" [label="direct edit"];
    "Resolve route per archetype" -> "Step 3b-skill native revise" [label="skill:<name>"];
    "Resolve route per archetype" -> "Step 3b-cmd native command" [label="slash_command"];
    "Resolve route per archetype" -> "Step 3b-surface" [label="surface"];

    "Step 3a generic fixer" -> "Parse fixer Status";
    "Parse fixer Status" -> "Dispatch reviewer subagent (fresh)" [label="Edits Applied (next iter)"];
    "Parse fixer Status" -> "Surface to user" [label="Escalation Required"];
    "Parse fixer Status" -> "Surface to user" [label="No Edits"];

    "Step 3b-skill native revise" -> "Step 3c validate?" [label="Edits Applied (route has validate)"];
    "Step 3b-skill native revise" -> "Dispatch reviewer subagent (fresh)" [label="Edits Applied (no validate, next iter)"];
    "Step 3b-skill native revise" -> "Step 3b-surface" [label="Needs Input"];
    "Step 3b-skill native revise" -> "Surface to user" [label="No Edits"];

    "Step 3b-cmd native command" -> "Slash tool available?" ;
    "Slash tool available?" -> "Step 3c validate?" [label="yes (route has validate)"];
    "Slash tool available?" -> "Dispatch reviewer subagent (fresh)" [label="yes (no validate, next iter)"];
    "Slash tool available?" -> "Step 3b-surface" [label="no"];

    "Step 3c validate?" -> "Dispatch reviewer subagent (fresh)" [label="sound (next iter)"];
    "Step 3c validate?" -> "Surface to user" [label="blocking"];

    "Step 3b-surface" -> "Native revise handed off";
    "Native revise handed off" -> "Surface to user";

    "Approved" -> "Surface to user";
    "Cap reached" -> "Surface to user";
}
```

### Step 1 — Dispatch reviewer (every iteration)

Use the `Agent` tool with these exact parameters:

- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `description`: `review-spec iter N reviewer` (substitute N)
- `prompt`: (template below)

Reviewer prompt template — use VERBATIM, substitute only `<DOC_PATHS>`, `<ARCHETYPE>`, `<FRAMEWORK_PROFILE_PATH>`, `<CODEBASE_ROOT>`, and `<GROUNDING_DOCS>`:

```
You are the reviewer.

Step 1: Invoke the Skill tool with skill name "reviewing-specs" and follow it exactly.

Step 2: The orchestrator has pre-resolved:
- ARCHETYPE = <ARCHETYPE>  (one or more of: intent, requirements, design, plan)
- FRAMEWORK_PROFILE_PATH = <FRAMEWORK_PROFILE_PATH>  (a file path on disk, or "none")
Trust these — the orchestrator has project context you don't; skip the skill's own
detection/classification. If FRAMEWORK_PROFILE_PATH is a path, Read it: it encodes this
framework's doc archetypes and review conventions (requirement syntax, delta sections,
ambiguity/parallel markers, constitutional gates) — apply them. If "none", use the generic
archetype checklists.

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

**CRITICAL:** never include the document content, prior reports, the conversation, or the author's intent in the reviewer prompt. Paths only.

### Step 2 — Parse reviewer Status

Locate the line beginning `### Status:` in the reviewer's output.

| Status | Action |
|---|---|
| `### Status: Approved` | Loop ends. Go to Surface (success). |
| `### Status: Issues Found — fix and re-invoke` | Continue to Step 3 if iter < cap, else go to Surface (cap reached). |
| Any other text on the Status line | Treat as Issues Found (be conservative); log the anomaly. |
| No Status line | Loop ends. Surface failure: "Reviewer did not emit a Status line." |

### Step 3 — Apply findings (when Issues Found, iter < cap)

Save the reviewer's report to a temp file (`/tmp/review-spec-report-iter<N>.md`) so downstream subagents/skills can `Read` it.

**Resolve a revise route per flagged archetype.** A report may flag findings across more than one archetype (a fused superpowers design doc, or a doc set). For each archetype with at least one CRITICAL/HIGH/actionable finding, resolve its route from the profile's `revise_protocol`:

1. `revise_protocol.routes` exists → pick the entry whose `archetype` equals the flagged archetype.
2. Else a flat `revise_protocol` exists (shorthand `mode`/`invoke`/`command`/`applies_to`) and `applies_to` contains the archetype → treat it as one route `{archetype, invoke, command, validate: null}`.
3. Else (no `revise_protocol`, `mode: direct_edit`, or the archetype isn't covered) → the route is **direct edit**.

Dispatch per the route's `invoke`:

| `invoke` | Handler |
|---|---|
| (direct edit / archetype not covered) | **Step 3a** — generic `applying-review-feedback` fixer |
| `skill:<name>` | **Step 3b-skill** — hybrid native-skill revise; surface if it stalls |
| `slash_command` | **Step 3b-cmd** — invoke it if the command/backing skill is installed this session (e.g. global GSD), else surface |
| `surface` | **Step 3b-surface** — always hand the user the pre-filled command, then stop |

If findings span a native-owned archetype AND a direct-edit archetype, handle the direct-edit ones via 3a and the native one via the appropriate 3b variant (3b-skill / 3b-cmd / 3b-surface per the route's `invoke`) in the same iteration, then re-review once; note both in the eventual Surface message. Dispatch these **sequentially, never in parallel**: run the Step 3a generic fixer to completion first, then the 3b native revise. Two handlers editing the same document concurrently would corrupt it. If they target entirely separate files you may still keep them sequential for simplicity. After ANY successful native revise (3b-skill / 3b-cmd) whose route declares `validate: agent:<name>`, run **Step 3c** before re-reviewing.

#### Step 3a — Generic fixer (direct edit)

Use the `Agent` tool, fresh subagent:

- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `description`: `review-spec iter N fixer`
- `prompt`: template below

Fixer prompt template — use VERBATIM:

```
You are the fixer.

Step 1: Invoke the Skill tool with skill name "applying-review-feedback" and follow it exactly.

Inputs:
- Document(s) to edit: <DOC_PATHS>
- Review report: <REPORT_TEMP_PATH>
- Codebase root: <CODEBASE_ROOT>
- FRAMEWORK_PROFILE_PATH: <FRAMEWORK_PROFILE_PATH>  (a file path on disk, or "none"). If a path,
  Read it and respect the framework's conventions while editing — keep EARS phrasing / RFC-2119
  SHALL, the task-checkbox format, delta section headers; never introduce implementation detail
  into a spec/requirements doc the framework keeps behavior-only.

Apply the skill. Edit the document(s) in place. Emit the structured Fix Summary at the end.

Do not assume any context outside what you read. Do not edit the review report.
```

Then parse the fixer's Status (Step 4).

#### Step 3b-skill — Hybrid native-skill revise (surface if it stalls)

The document was authored by a framework skill that owns its house style (superpowers `brainstorming` for design docs, `writing-plans` for plans). Revise through that skill so the structure survives — but those skills can expect human input, so fall back to surfacing if the subagent stalls.

Dispatch a fresh subagent:

- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `description`: `review-spec iter N native-revise (<SKILL_NAME>)`
- `prompt`: VERBATIM, substitute `<SKILL_NAME>` (the route's `invoke` minus the `skill:` prefix, e.g. `superpowers:writing-plans`), `<DOC_PATHS>`, `<REPORT_TEMP_PATH>`, `<CODEBASE_ROOT>`:

```
You are revising an existing document to address review findings, using its own authoring skill.

Step 1: Invoke the Skill tool with skill name "<SKILL_NAME>" and follow it.

Step 2: This is a REVISE, not a fresh authoring pass. Your inputs:
- Document(s) to revise (edit in place, SAME path): <DOC_PATHS>
- Review report (the findings to resolve): <REPORT_TEMP_PATH>
- Codebase root for grounding: <CODEBASE_ROOT>
Treat the existing document plus the findings as your brief. Regenerate or edit the document so
every CRITICAL and HIGH finding is resolved, preserving the skill's required structure and house
style. Write the result to the same path(s).

Step 3: If you cannot proceed without interactive input a human must provide (the skill needs a
decision you cannot infer from the document or the findings), DO NOT guess. Stop and emit:
### Status: Needs Input
followed by the one or two questions you would ask.
Otherwise, when done, emit exactly one of:
### Status: Edits Applied
### Status: No Edits

Do not assume any context beyond what you read.
```

Parse the subagent's `### Status:` line:

| Status | Action |
|---|---|
| `### Status: Edits Applied` | If the route has `validate`, run Step 3c; then increment iter and re-review (Step 1). |
| `### Status: Needs Input` | The authoring skill stalled. Go to **Step 3b-surface**, including the subagent's questions, and stop the loop. |
| `### Status: No Edits` | Loop ends. Surface (escalation — the authoring skill made no progress). |
| No Status line | Loop ends. Surface failure: "Native-revise subagent did not emit a Status line." |

#### Step 3b-cmd — Native slash-command revise

Following the route's `command` (substitute `{phase_id}`/ids from the doc path or roadmap):

**A `slash_command` route is "available" when the command — or the skill/agent backing it — is
installed and invocable this session.** This is decided by what is INSTALLED, not by whether the
project itself uses that framework: GSD installed at the user/global level (its `gsd-*` skills and
`/gsd-plan-phase` command present this session) makes the route invocable even when reviewing a
plan in an unrelated repo. Check for the backing skill/command (e.g. `gsd-plan-phase`) before
deciding.

- **Available** → invoke it, passing the findings: substitute the report path for a `{report_path}`
  placeholder if the `command` has one; otherwise append a trailing `(findings: <REPORT_TEMP_PATH>)`
  note. Invoke via the slash command if a slash-command tool exists, else via its backing skill
  through the Skill tool (e.g. `gsd-plan-phase`). Then if the route has `validate` run **Step 3c**,
  then re-review (Step 1).
- **Not installed this session** (no command and no backing skill) → fall back to **Step 3b-surface**.

#### Step 3b-surface — Surface the native command

Hand the user the pre-filled `command` + the report path and **stop the loop** (do not edit files yourself). Use the Surface "Native revise handed off" row. Example: `This plan is owned by the GSD planner. Run: /gsd-plan-phase 2 --reviews  (findings: /tmp/review-spec-report-iter<N>.md), then re-run /review-spec.`

#### Step 3c — Validate the regenerated doc (route has `validate: agent:<name>`)

The native planner regenerated the doc; validate with the framework's own checker before spending another review iteration. Dispatch the named agent:

- `subagent_type`: `<name>` (from `validate: agent:<name>`, e.g. `gsd-plan-checker`)
- `description`: `review-spec iter N validate (<name>)`
- `prompt`: `Validate the regenerated document(s) at: <DOC_PATHS>. Codebase root: <CODEBASE_ROOT>. Report whether the plan is sound and ready, or list the blocking problems.`

- Validator reports **sound** → proceed to re-review (Step 1).
- Validator reports **blocking problems** → **surface** to the user with the validator's reasons + the report path, and stop the loop (do not burn a review iteration on a plan its own checker rejects). Do **not** feed the validator's text into the reviewer prompt — the reviewer stays clean-context. (use the Step 5 "Validator blocked" row)

### Step 4 — Parse fixer Status

*(Reached only from Step 3a — the generic direct-edit fixer. The native-revise paths 3b-skill / 3b-cmd parse their own status inline and do not pass through here.)*

Locate the `### Status:` line in the fixer's Fix Summary.

| Status | Action |
|---|---|
| `### Status: Edits Applied` | Increment iter. Go back to Step 1 (re-review with fresh reviewer). |
| `### Status: Escalation Required` | Loop ends. Go to Surface (escalation). |
| `### Status: No Edits` | Loop ends. Go to Surface (escalation — fixer made no progress). |
| No Status line | Loop ends. Surface failure: "Fixer did not emit a Status line." |

### Step 5 — Surface to user

Emit one short message in the user's terminal. Do NOT paste full reports unless the user is at cap or escalation.

| Outcome | Message shape |
|---|---|
| Approved on iter 1 | `Approved on first review. <DOC_PATHS> ready for next step.` |
| Approved after N iters | `Approved after N iteration(s). Doc edited and re-reviewed clean.` |
| Cap reached | `Hit iteration cap (N). Last review still has issues. Final report:\n\n<paste full last reviewer report>\n\nDecide manually.` |
| Escalation Required | `Fixer escalated on iter N. Reason: <fixer's escalation message>. Decide manually.` |
| Native revise handed off | `Findings ready. This <archetype> is owned by <framework>'s planner — run: <pre-filled command>  (findings: <report path>), then re-run /review-spec.` |
| Insufficient info (stage gap) | `Only <existing docs> exist; project is at the <stage> stage. No <requested archetype> to review yet. Reviewed <existing> as <archetype>; produce <next stage> before reviewing it.` |
| Validator blocked (Step 3c) | `Regenerated <archetype> was rejected by <validator> — <reasons>. Findings: <report path>. Fix manually and re-run /review-spec.` |
| Failure | `<failure mode message>. Last available output: <quote brief>.` |

After surfacing, the orchestrator's job is done. Do NOT continue to "next steps" — the user decides whether to invoke `writing-plans`, edit manually, or re-invoke `/review-spec` after their own edits.

## Hard rules for the orchestrator

| Rule | Reason |
|---|---|
| Never edit the document yourself. | Orchestrator is dispatch + parse, not author or fixer. |
| Resolve `CODEBASE_ROOT` from the document's own worktree (Step 0.1), never from your CWD. Use `git worktree list` when unsure. | Grounding the review against the wrong checkout (main vs. the worktree the doc lives in) yields phantom findings and misses real ones. |
| Never include conversation/intent/document-content in subagent prompts. | Subagents must form their own reading from disk. |
| Always dispatch a NEW subagent each iteration. Do not reuse. | Reuse contaminates context with prior round's findings. |
| Reviewer and fixer are separate subagents, never the same. | Fixer must edit; reviewer must not. Separation = audit integrity. |
| Stop at the iteration cap. | Avoid infinite review↔fix loops on irreconcilable disagreement. |
| If reviewer and fixer disagree on a finding's severity across iterations, surface to user. | Orchestrator does not arbitrate. |

## Routing table — who rewrites what

Routing is data-driven from each profile's `revise_protocol.routes`. Seed-profile snapshot (FR-1.5):

| Framework (detected) | Archetype | Rewrite handled by | Mechanism |
|---|---|---|---|
| superpowers | design | `brainstorming` skill | hybrid subagent → surface if it stalls (Step 3b-skill) |
| superpowers | plan | `writing-plans` skill | hybrid subagent → surface if it stalls (Step 3b-skill) |
| GSD | plan | `/gsd-plan-phase {phase_id} --reviews`, then `gsd-plan-checker` | slash-command or surface (3b-cmd) + validate (3c) |
| GSD | intent / requirements / design | `applying-review-feedback` | direct edit (3a) |
| any other framework, generic, or `none` | all | `applying-review-feedback` | direct edit (3a) |
| ambiguous / low-confidence detection | all | `applying-review-feedback` | direct edit (3a) — Surface notes the ambiguity |

The reviewer (`reviewing-specs`) is identical for every framework; only the **rewrite** stage is
routed. To change routing, edit the framework profile's `revise_protocol.routes` — never hard-code
tools here.

**This table is a convenience snapshot. The authoritative routing is each framework profile's `revise_protocol.routes` — when in doubt, read the profile, not this table.** Adding a framework or changing a route means editing its profile, after which this snapshot may lag.

## Cleanup

After the loop ends (any outcome), delete the temp report file(s) from `/tmp/`. They are debugging artifacts, not deliverables.
