# Synthesis Summary

Entry point for downstream consumers (e.g. `gsd-roadmapper`). Read this first,
then the per-type intel files below, then `.planning/INGEST-CONFLICTS.md` for
full conflict detail.

This is the second re-run of a prior blocked ingest. Run 1 found a 3-node
cross-reference cycle (`ai-kit-config-doctor` →
`ai-kit-tool-substitution-awareness-hook` → `ai-kit-usage-metrics-dashboard`
→ `ai-kit-config-doctor`) and withheld all 3 PRDs. Run 2 (user removed
`ai-kit-usage-metrics-dashboard`'s back-reference to `ai-kit-config-doctor`)
unblocked `ai-kit-config-doctor` but found a residual 2-node cycle between
`ai-kit-tool-substitution-awareness-hook` and `ai-kit-usage-metrics-dashboard`.
This run, the user removed `ai-kit-usage-metrics-dashboard`'s two remaining
named back-references to `ai-kit-tool-substitution-awareness-hook`. Cycle
detection was re-run fresh against the current source files (not cached
classification state) and found no cycles — the cross-reference graph is now
a DAG. All 5 PRDs are synthesized below.

## Doc counts by type

- PRD: 5 classified (all `confidence: high`, none `locked`)
  - Synthesized: 5 (ai-kit-config-doctor, ai-kit-multi-cli-runtime-support,
    ai-kit-opencode-provider-management, ai-kit-tool-substitution-awareness-hook,
    ai-kit-usage-metrics-dashboard)
  - Withheld: 0
- ADR: 0
- SPEC: 0
- DOC: 0
- UNKNOWN / low-confidence: 0

## Decisions locked

0 — no ADR-type documents in this ingest set. See `decisions.md`.

## Requirements extracted

14, from all 5 PRDs:
- REQ-config-doctor-diagnostic-checks
- REQ-config-doctor-review-screen
- REQ-config-doctor-apply-flow
- REQ-multi-cli-install-single-branch
- REQ-multi-cli-runtime-detection
- REQ-multi-cli-opencode-ui-research
- REQ-opencode-provider-list-remove
- REQ-opencode-provider-cross-reference-check
- REQ-tool-substitution-detection-composition
- REQ-tool-substitution-hook-wiring
- REQ-usage-metrics-raw-capture
- REQ-usage-metrics-refinement-pipeline
- REQ-usage-metrics-dashboard-ui
- REQ-usage-metrics-classification-refinement-loop

See `requirements.md`.

## Constraints

0 — no SPEC-type documents in this ingest set. See `constraints.md`.

## Context topics

0 — no DOC-type documents in this ingest set. See `context.md`.

## Conflicts

- Blockers: 0 (prior residual 2-node cycle resolved this run — see INFO entry)
- Competing variants: 0
- Auto-resolved: 0

Full detail: `.planning/INGEST-CONFLICTS.md`

## Per-type intel files

- `.planning/intel/decisions.md`
- `.planning/intel/requirements.md`
- `.planning/intel/constraints.md`
- `.planning/intel/context.md`

## Status

READY — 0 blockers, 0 competing variants. All 5 PRDs synthesized this run;
safe to route to `gsd-roadmapper`.
