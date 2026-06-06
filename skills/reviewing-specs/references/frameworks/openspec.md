---
id: openspec
display_name: OpenSpec (Fission-AI/OpenSpec)
source_url: https://github.com/Fission-AI/OpenSpec
last_updated: 2026-06-04
version_pinned: null
detection_signals:
  - "openspec/changes/*/proposal.md"
  - "openspec/specs/*/spec.md"
root_globs: ["openspec/"]
unit_of_work: change-folder
doc_types:
  - { glob: "openspec/changes/*/proposal.md",       archetype: intent,       required: true }
  - { glob: "openspec/changes/*/design.md",         archetype: design,       required: false }
  - { glob: "openspec/changes/*/specs/**/spec.md",  archetype: requirements, required: true }
  - { glob: "openspec/changes/*/tasks.md",          archetype: plan,         required: true }
  - { glob: "openspec/specs/**/spec.md",            archetype: requirements, required: true }
lifecycle_order: [intent, design, requirements, plan]
requirement_syntax: rfc2119-shall
acceptance_criteria_format: gwt
task_checkbox_format: "- [ ] N.N <desc>"
parallel_task_marker: null
ambiguity_markers: []
delta_model: true
filename_date_prefix: false
---
# OpenSpec — reviewer profile

Two-tier model: **stable specs** (`openspec/specs/<domain>/spec.md`, source of truth) vs
**change deltas** (`openspec/changes/<id>/…`). `design.md` is optional for trivial changes.

Review notes:
- Requirements use RFC-2119: `### Requirement: <Name>` + "The system SHALL/MUST/SHOULD…",
  scenarios as `#### Scenario:` with GIVEN/WHEN/THEN. Non-testable "should be fast" → HIGH.
- **Delta specs** use section headers `## ADDED Requirements`, `## MODIFIED Requirements`,
  `## REMOVED Requirements`. A delta that edits a requirement without the right header, or
  whose MODIFIED block doesn't match an existing requirement in the stable spec, is a defect.
- Implementation detail belongs in `design.md`/`tasks.md`, **never** in `spec.md` — leaking
  impl detail into a spec is a real finding here.
- Tasks are hierarchical `- [ ] 1.1`.
