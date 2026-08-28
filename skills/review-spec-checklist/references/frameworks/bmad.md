---
id: bmad
display_name: BMAD-METHOD
source_url: https://github.com/bmad-code-org/BMAD-METHOD
last_updated: 2026-06-04
version_pinned: null
detection_signals:
  - "docs/prd.md"
  - "bmad-modules.yaml"
  - ".bmad-core/"
root_globs: ["docs/"]
unit_of_work: story
doc_types:
  - { glob: "docs/brief.md",          archetype: intent,       required: false }
  - { glob: "docs/project-brief.md",  archetype: intent,       required: false }
  - { glob: "docs/prd.md",            archetype: requirements, fused: [intent, requirements], required: true }
  - { glob: "docs/architecture.md",   archetype: design,       required: true }
  - { glob: "docs/epics/**/*.md",     archetype: plan,         required: false }
  - { glob: "docs/stories/**/*.md",   archetype: plan,         required: false }
lifecycle_order: [intent, requirements, design, plan]
requirement_syntax: user-story
acceptance_criteria_format: gwt
task_checkbox_format: "- [ ] <desc>"
parallel_task_marker: null
ambiguity_markers: []
delta_model: false
filename_date_prefix: false
---
# BMAD-METHOD — reviewer profile

PRD-centric (not a `spec.md` model). Planning docs (`prd.md`, `architecture.md`) are
**sharded** into per-epic and per-story files; story files are self-contained context
bundles (rationale, constraints, tests, links back to PRD/architecture).

Review notes:
- The `prd.md` fuses intent+requirements (FRs, NFRs, epics, draft stories) — apply both
  checklists.
- **Story files** are the executable unit — review them as `plan` archetype: they must embed
  enough context (acceptance criteria, constraints, test notes, source links) to be built
  without re-reading the whole PRD. A story that just restates a title is a finding.
- **Version drift**: canonical filenames differ between v4 and the v6 rewrite. Verify the
  installed version's paths before hard-relying on these globs; bump `version_pinned` if you
  detect a specific version.
