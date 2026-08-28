---
id: kiro
display_name: Kiro (AWS)
source_url: https://kiro.dev/
last_updated: 2026-06-04
version_pinned: null
detection_signals:
  - ".kiro/specs/*/requirements.md"
  - ".kiro/steering/"
root_globs: [".kiro/"]
unit_of_work: feature-folder
doc_types:
  - { glob: ".kiro/specs/*/requirements.md", archetype: requirements, required: true }
  - { glob: ".kiro/specs/*/design.md",       archetype: design,       required: true }
  - { glob: ".kiro/specs/*/tasks.md",        archetype: plan,         required: true }
  - { glob: ".kiro/steering/*.md",           archetype: constitution, required: false }
lifecycle_order: [requirements, design, plan]
requirement_syntax: ears
acceptance_criteria_format: ears
task_checkbox_format: "- [ ] <desc>"
parallel_task_marker: null
ambiguity_markers: []
delta_model: false
filename_date_prefix: false
---
# Kiro — reviewer profile

Canonical three-file triad per feature: `requirements.md` → `design.md` → `tasks.md`.
`steering/` holds always-on project guidance (read as context).

Review notes:
- Requirements use **EARS** (Easy Approach to Requirements Syntax). Valid shapes:
  "WHEN <trigger>, the system SHALL <response>"; "WHILE <state>, the system SHALL <response>";
  "IF <condition>, THEN the system SHALL <response>"; ubiquitous "The system SHALL <response>".
  A requirement that isn't in an EARS shape, or that bundles multiple behaviors into one
  SHALL, is a requirements-checklist finding. Each should be individually testable.
- `design.md` is expected to carry data-flow diagrams, interfaces (e.g. TypeScript), DB
  schemas, and API endpoints — a design missing the data flow / interface contracts is HIGH.
- Kiro is closed-source; treat paths as best-available and verify against the project.
