# Framework profiles

A **framework profile** tells the spec-review system how a given spec-driven-development
framework lays its documents on disk, which **archetype** each document is, and the
review-relevant **conventions** that framework uses. The orchestrator resolves a profile,
classifies each document's archetype from it, and passes the profile *path* (never inlined
content) to the reviewer and fixer subagents so they stay clean-context.

## The four archetypes

Every reviewable document maps to exactly one archetype. The reviewer applies the matching
checklist (see SKILL.md). Two non-reviewed context types may be `Read` for grounding.

| Archetype | Role | Reviewed with |
|---|---|---|
| `intent` | why + what; scope, motivation, success | Intent checklist |
| `requirements` | testable behavior the system must exhibit | Requirements checklist |
| `design` | how — architecture, data flow, contracts | Design checklist |
| `plan` | ordered, actionable work items | Plan checklist |
| `constitution` *(context)* | durable rules/principles — read, don't review | — |
| `state` *(context)* | progress/verification tracking — read, don't review | — |

Frameworks may **fuse** archetypes in one file (Spec Kit `spec.md` = intent+requirements;
superpowers `…-design.md` = intent+requirements+design). The profile says which, and the
reviewer applies every fused checklist to that file.

## Profile format

One file per framework, frontmatter + short prose. Required fields:

```yaml
---
id: kiro                       # canonical slug == filename
display_name: Kiro
source_url: https://kiro.dev/
last_updated: 2026-06-04        # ISO date; bump on any refresh
version_pinned: null            # set when a framework's layout is version-specific
detection_signals:              # globs/markers that uniquely identify this framework on disk
  - ".kiro/specs/*/requirements.md"
root_globs: [".kiro/"]
unit_of_work: feature-folder    # feature-folder | change-folder | phase | component | story
doc_types:                      # glob -> archetype (the classifier the reviewer keys off)
  - { glob: ".kiro/specs/*/requirements.md", archetype: requirements, required: true }
  - { glob: ".kiro/specs/*/design.md",       archetype: design,       required: true }
  - { glob: ".kiro/specs/*/tasks.md",        archetype: plan,         required: true }
lifecycle_order: [requirements, design, plan]
requirement_syntax: ears        # ears | rfc2119-shall | user-story | freeform
acceptance_criteria_format: ears # gwt | ears | none
task_checkbox_format: "- [ ] <desc>"
parallel_task_marker: null      # e.g. "[P]" (Spec Kit)
ambiguity_markers: []           # e.g. "[NEEDS CLARIFICATION]" (Spec Kit)
delta_model: false              # true if docs diff against a stable spec (OpenSpec)
filename_date_prefix: false     # YYYY-MM-DD- prefixed filenames (superpowers, GSD)
revise_protocol:                # OPTIONAL — how findings get applied for this framework
  mode: direct_edit             # direct_edit | native_command
  # the keys below only apply when mode: native_command
  command: null                 # human-facing invocation, e.g. "/gsd-plan-phase {phase_id} --reviews"
  invoke: surface               # slash_command | skill:<name> | surface  (how the orchestrator runs it)
  applies_to: []                # archetypes the native planner owns, e.g. [plan]
  notes: null                   # why the native path is preferred (keeps framework structure/state intact)
---
# <Framework> — reviewer profile
Short prose: lifecycle, what each doc means, and the 2-3 framework-specific things a
reviewer must check (e.g. EARS phrasing, delta section headers, parallel markers).
```

## `lifecycle_order` + `doc_types[].required` — scope, not just classification

These two fields are not decoration: the orchestrator uses them to scope a review to the
project's **current lifecycle stage**. Glob `doc_types` against the project root to see which
documents exist; the furthest-along present archetype (per `lifecycle_order`) is the current
stage. A reviewer must judge each existing document **at its own archetype** — never demand a
downstream archetype's detail (tasks, exact files) from an upstream document (a bare `intent`
is judged on why/what clarity, not on missing tasks). A `required: true` doc-type that is
absent at or before the current stage is a **gap/prerequisite to surface**, not a defect to log
inside an existing document. If the user asks to review an artifact a later stage hasn't
produced yet, the orchestrator stops and says so rather than fabricating a deeper review.

## `revise_protocol` — apply findings the framework's own way

Some frameworks own plan/spec generation through a dedicated authoring tool (superpowers authors
designs via `brainstorming` and plans via `writing-plans`; GSD regenerates a phase plan via
`/gsd-plan-phase <id> --reviews`). For those, editing files directly with the generic fixer can
desync the framework's state or break its conventions. When `mode: native_command`, the
orchestrator routes findings to the native tool instead of the direct-edit fixer.

Routing is **per archetype** via a `routes:` list — different archetypes of the same framework can
go to different tools (a superpowers `design` doc → `brainstorming`; a `plan` → `writing-plans`):

```yaml
revise_protocol:
  mode: native_command
  routes:
    - archetype: design                          # intent | requirements | design | plan
      invoke: "skill:superpowers:brainstorming"  # skill:<name> | slash_command | surface
      command: null                              # required when invoke: slash_command
      validate: null                             # optional "agent:<name>" run after a successful revise
      notes: "why the native path is preferred"
    - archetype: plan
      invoke: "skill:superpowers:writing-plans"
```

Route fields:
- `archetype` — which archetype this route handles. A report may flag findings in more than one
  archetype (fused docs, doc sets); each is routed independently.
- `invoke` —
  - `skill:<name>` — dispatch a subagent that invokes that skill to revise the doc; if the skill
    stalls on interactive input, the orchestrator **surfaces** the command instead (hybrid).
  - `slash_command` — run `command` via a slash-command tool if one is available this session; else
    **surface** the pre-filled command for the user to run.
  - `surface` — always hand the user the pre-filled `command` + findings report; never auto-run.
- `command` — the human-facing invocation (required for `slash_command`; shown when surfacing).
- `validate` — optional `agent:<name>`; after a successful native revise the orchestrator runs that
  agent to validate the regenerated doc before re-review.
- `notes` — why the native path is preferred.

An archetype **without** a matching route falls back to the direct-edit fixer
(`applying-review-feedback`). `mode: direct_edit` (or no `revise_protocol`) keeps the direct-edit
fixer for every archetype — most frameworks (generic) want this.

**Shorthand (flat) form** — still accepted for single-archetype profiles and learned cache
profiles: `mode` + `invoke` + `command` + `applies_to: [<archetype>, …]`. The orchestrator treats
it as one route per listed archetype. Prefer the explicit `routes:` list in curated seeds.

## Resolution order (orchestrator)

1. **Detect** the framework from the document path + `detection_signals` of all known profiles.
2. **Resolve** the profile, in order:
   - `~/.claude/cache/framework-profiles/<id>.md` if present and not stale → use it.
   - else the bundled seed `references/frameworks/<id>.md` → use it.
   - else **unknown framework** → research it (web), write a new profile to the cache with
     `last_updated = today`, then use it.
3. **Staleness**: a cached profile older than ~180 days for a fast-moving framework
   (`version_pinned: null` + known to drift, e.g. bmad, gsd) is a refresh candidate — the
   orchestrator may re-research and rewrite it (bumping `last_updated`). Curated seeds are
   never auto-overwritten in place; refreshes always land in the cache.

The orchestrator owns detection, resolution, and any web research — subagents only `Read`
the resolved profile from its path.

## Adding / updating a framework

- New seed (curated, ships with the plugin): add `references/frameworks/<id>.md` following
  the format above and add its `detection_signals` so it can be matched.
- Learned at runtime: the orchestrator writes `~/.claude/cache/framework-profiles/<id>.md`.
  Promote a good cache profile to a seed by copying it here and curating it.
