# Synthesis Summary

Entry point for downstream consumers (e.g. `gsd-roadmapper`). Read this first,
then the per-type intel files below, then `.planning/INGEST-CONFLICTS.md` for
full conflict detail.

This run classified 7 documents: the same 5 PRDs synthesized in a prior
ingest run (all already merged into `.planning/REQUIREMENTS.md`/`ROADMAP.md`
as Complete/Done v1 scope), plus 2 new documents — a SPEC and a DOC — for a
follow-on "ai-kit Rules Skill Family" epic that does not yet have a roadmap
phase. Cycle detection flagged a possible 3-node cycle from cached
classification state, but re-verification against the current source files
found it stale (the cycle was already broken by the user in a prior round);
no cycle holds. 2 content divergences were found between the re-ingested
PRDs and the already-shipped, amended `REQUIREMENTS.md` — see Conflicts
below.

## Doc counts by type

- PRD: 5 classified (all `confidence: high`, none `locked`)
  - Synthesized: 5 (ai-kit-config-doctor, ai-kit-multi-cli-runtime-support,
    ai-kit-opencode-provider-management, ai-kit-tool-substitution-awareness-hook,
    ai-kit-usage-metrics-dashboard)
  - Withheld: 0
- SPEC: 1 classified (`ai-kit Rules Skill Family — Design`, precedence `0`)
  - Synthesized: 1
- DOC: 1 classified (`ai-kit Rules Shared Package Implementation Plan`, precedence `1`)
  - Synthesized: 1
- ADR: 0
- UNKNOWN / low-confidence: 0

## Decisions locked

0 — no ADR-type documents in this ingest set. See `decisions.md`.

## Requirements extracted

14, from all 5 PRDs (all already present in `.planning/REQUIREMENTS.md` as
Complete/Done; 2 flagged as diverging from the shipped/amended text — see
Conflicts):
- REQ-config-doctor-diagnostic-checks
- REQ-config-doctor-review-screen
- REQ-config-doctor-apply-flow
- REQ-multi-cli-install-single-branch
- REQ-multi-cli-runtime-detection ⚠ diverges (native_runtime cursor value)
- REQ-multi-cli-opencode-ui-research
- REQ-opencode-provider-list-remove
- REQ-opencode-provider-cross-reference-check
- REQ-tool-substitution-detection-composition
- REQ-tool-substitution-hook-wiring
- REQ-usage-metrics-raw-capture
- REQ-usage-metrics-refinement-pipeline
- REQ-usage-metrics-dashboard-ui ⚠ diverges (Artifact/export vs. static HTML)
- REQ-usage-metrics-classification-refinement-loop

See `requirements.md`.

## Constraints

5 entries, from the 1 SPEC (`ai-kit Rules Skill Family — Design`):
checker-skill scope boundary (protocol), shared-package import convention
(protocol), stack-tooling cache schema + 180-day staleness convention
(schema), cross-skill remediation merging ownership (protocol), 6-category
tooling taxonomy (schema). See `constraints.md`.

## Context topics

1 topic, from the 1 DOC (`ai-kit Rules Shared Package Implementation Plan`):
implementation plan summary + 4 recorded, named deviations from the sibling
SPEC (auto-resolved in the SPEC's favor per precedence — see Conflicts).
See `context.md`.

## Conflicts

- Blockers: 0
- Competing variants (WARNINGS): 2 — both are re-ingested-PRD-vs-already-
  shipped-amended-REQUIREMENTS.md divergences (native_runtime cursor value;
  usage-metrics dashboard Artifact/export-import vs. static HTML). Both
  underlying requirements are already Complete; flagged for reconciliation
  awareness, not as new work.
- Auto-resolved (INFO): 3 — stale cached cross_refs cycle false-positive
  (re-verified clean against fresh source); 5 PRDs confirmed duplicate of
  already-merged v1 scope; SPEC > DOC on 4 named implementation deviations.

Full detail: `.planning/INGEST-CONFLICTS.md`

## Per-type intel files

- `.planning/intel/decisions.md`
- `.planning/intel/requirements.md`
- `.planning/intel/constraints.md`
- `.planning/intel/context.md`

## Status

AWAITING USER — 0 blockers, 2 competing variants need resolution (both
concern already-shipped work; likely resolution is "existing REQUIREMENTS.md
wording stands, no action" but a human should confirm before this intel is
used to re-plan Phases 1.2 or 5). The new SPEC/DOC content (ai-kit Rules
Skill Family) has 0 blockers/variants and is safe to route to
`gsd-roadmapper` for a new phase.
