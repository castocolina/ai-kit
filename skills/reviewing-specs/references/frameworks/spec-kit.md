---
id: spec-kit
display_name: GitHub Spec Kit (Specify)
source_url: https://github.com/github/spec-kit
last_updated: 2026-06-04
version_pinned: null
detection_signals:
  - ".specify/"
  - "specs/[0-9][0-9][0-9]-*/spec.md"
root_globs: [".specify/", "specs/"]
unit_of_work: feature-folder
doc_types:
  - { glob: ".specify/memory/constitution.md",      archetype: constitution, required: false }
  - { glob: "specs/*/spec.md",        archetype: requirements, fused: [intent, requirements], required: true }
  - { glob: "specs/*/plan.md",        archetype: design, required: true }
  - { glob: "specs/*/research.md",    archetype: design, required: false }
  - { glob: "specs/*/data-model.md",  archetype: design, required: false }
  - { glob: "specs/*/contracts/**",   archetype: design, required: false }
  - { glob: "specs/*/tasks.md",       archetype: plan,   required: true }
lifecycle_order: [constitution, requirements, design, plan]
requirement_syntax: user-story
acceptance_criteria_format: gwt
task_checkbox_format: "- [ ] <desc>"
parallel_task_marker: "[P]"
ambiguity_markers: ["[NEEDS CLARIFICATION]", "[OPTIONAL]"]
delta_model: false
filename_date_prefix: false
---
# GitHub Spec Kit — reviewer profile

Numbered feature folders `specs/NNN-feature/`. Note the naming trap: **`plan.md` is a
design/architecture doc** (maps to `design`), not the task list — `tasks.md` is the plan.

Review notes:
- **Unresolved `[NEEDS CLARIFICATION: …]` or `[OPTIONAL]` markers are findings** — an
  unanswered clarification left in a spec going to implementation is HIGH (ambiguity with
  opposite outcomes can be CRITICAL).
- Tasks marked **`[P]`** claim to be parallel-safe — flag a `[P]` task that actually shares
  state / has an ordering dependency with another `[P]` task.
- `constitution.md` holds project principles (constitutional gates: simplicity,
  anti-abstraction, integration-first) — read it as context; a plan/design that violates a
  stated constitutional gate is a finding.
- `spec.md` fuses intent+requirements (user stories + Given/When/Then acceptance criteria).
