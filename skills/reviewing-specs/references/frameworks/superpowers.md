---
id: superpowers
display_name: Superpowers (obra/superpowers)
source_url: https://github.com/obra/superpowers
last_updated: 2026-06-04
version_pinned: null
detection_signals:
  - "docs/superpowers/specs/*.md"
  - "docs/superpowers/plans/*.md"
root_globs: ["docs/superpowers/"]
unit_of_work: feature-folder
doc_types:
  - { glob: "docs/superpowers/specs/*-design.md", archetype: design, fused: [intent, requirements, design], required: true }
  - { glob: "docs/superpowers/plans/*.md",        archetype: plan,   required: true }
lifecycle_order: [design, plan]
requirement_syntax: freeform
acceptance_criteria_format: none
task_checkbox_format: "- [ ] **Step N: ...**"
parallel_task_marker: null
ambiguity_markers: []
delta_model: false
filename_date_prefix: true
revise_protocol:
  mode: native_command
  routes:
    - archetype: design
      invoke: "skill:superpowers:brainstorming"
      command: "Re-run the brainstorming skill on this design doc, addressing the review findings"
      validate: null
      notes: "The design doc (intent+requirements+design fusion) is authored by brainstorming;
        revise it there so its structure and house style stay intact rather than hand-editing
        with the generic fixer."
    - archetype: plan
      invoke: "skill:superpowers:writing-plans"
      command: "Re-run the writing-plans skill on this plan, addressing the review findings"
      validate: null
      notes: "Plans are authored by writing-plans; regenerate the plan addressing findings so the
        bite-sized TDD step structure and exact-paths discipline are preserved."
---
# Superpowers — reviewer profile

Two-doc model from the `brainstorming` (→ design) and `writing-plans` (→ plan) skills.
Despite the folder name, `specs/` holds **design** docs (intent + architecture; `*-design.md`),
and `plans/` holds **implementation plans**. Filenames are `YYYY-MM-DD-`-prefixed.

Review notes:
- The design doc fuses intent+requirements+design — apply all three checklists, but do NOT
  demand exact file paths/code there (that's plan-level).
- Plans must be executable by a zero-context engineer: exact files, exact code, exact
  commands, bite-sized steps (`- [ ] **Step N**`), frequent commits. Vague steps
  ("handle errors appropriately") are HIGH.
- This is the framework the bundled checklists were originally written for.
