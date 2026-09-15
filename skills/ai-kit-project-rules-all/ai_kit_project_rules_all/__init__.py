"""Cross-domain rules orchestrator.

Subprocess-fans-out to the 6 sibling `ai-kit-project-rules-*` checkers and
merges their findings into one criticality-ordered report. Cross-domain
merging is scoped to this package per D-05 of `.planning/intel/constraints.md`'s
"Cross-skill remediation merging ownership" protocol -- this skill never
imports `skills/_shared/` directly.
"""
