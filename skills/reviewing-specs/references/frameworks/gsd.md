---
id: gsd
display_name: GSD — Get Sh*t Done (TÂCHES)
source_url: https://github.com/gsd-build/get-shit-done
last_updated: 2026-06-04
version_pinned: null
detection_signals:
  - ".planning/PROJECT.md"
  - ".planning/ROADMAP.md"
root_globs: [".planning/"]
unit_of_work: phase
doc_types:
  - { glob: ".planning/PROJECT.md",        archetype: intent,        required: true }
  - { glob: ".planning/REQUIREMENTS.md",   archetype: requirements,  required: true }
  - { glob: ".planning/ROADMAP.md",        archetype: design,        required: true }
  - { glob: ".planning/research/*.md",     archetype: design,        required: false }
  - { glob: ".planning/**/plan*.md",       archetype: plan,          required: false }
  - { glob: ".planning/STATE.md",          archetype: state,         required: false }
lifecycle_order: [intent, requirements, design, plan, state]
requirement_syntax: freeform
acceptance_criteria_format: none
task_checkbox_format: "- [ ] <desc>"
parallel_task_marker: null
ambiguity_markers: []
delta_model: false
filename_date_prefix: false
revise_protocol:
  mode: native_command
  command: "/gsd-plan-phase {phase_id} --reviews"
  invoke: slash_command
  applies_to: [plan]
  notes: "The GSD planner owns each phase's plan structure and STATE.md; regenerate the phase
    plan by passing review findings to its own command rather than hand-editing, so the
    framework's phase/state conventions stay intact. {phase_id} comes from the plan's path
    (.planning/<phase>/) or ROADMAP.md."
---
# GSD (Get Sh*t Done) — reviewer profile

Complexity lives in the filesystem (`.planning/`), not the context window; each phase runs
in a fresh context. `PROJECT.md` (vision) is loaded first; `REQUIREMENTS.md` carries IDs;
`ROADMAP.md` sequences phases; `STATE.md` tracks progress (read as context).

Review notes:
- Unit of work is the **phase**, not a story/sprint. Per-phase plan files are the `plan`
  archetype: each should be executable within one fresh context window.
- Requirements carry IDs but use freeform prose (no EARS/RFC-2119) — review for testability
  and unambiguous scope rather than a fixed syntax.
- **Moving target**: the canonical repo relocated (gsd-build → Open GSD / GSD Core). Verify
  the active repo/layout before hard-relying on paths; "GSD" can also refer to an unrelated
  methodology essay — this profile is the TÂCHES tooling framework.
