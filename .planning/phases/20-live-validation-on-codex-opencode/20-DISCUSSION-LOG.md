# Phase 20: Live Validation on Codex + Opencode - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 20-live-validation-on-codex-opencode
**Mode:** --analyze. The discussion was held in Spanish; this log is in English per the project
constraint.
**Areas discussed:** Driving the hosts, Nesting and codex, opencode local vs global, Fix policy

**Findings presented before the questions:**
1. gsd-core bakes opencode agent models at install time, and only a project-local install reads
   the project's `.planning/config.json`.
2. Under 16 D-01's order, a codex launched from Claude would read as claude, because
   `CLAUDECODE` is inherited.

---

## Driving the hosts
- headless iteration, then a final interactive run as the evidence ✓
- interactive only
- headless only

## Nesting and codex
- claude last: pi > opencode > cursor > codex > claude (amends 16 D-01); headless runs also
  clean the env ✓
- keep the order and clean the env
- process-tree detection

## opencode local vs global
- local install as the follow-up; the global alternative is explained, not run ✓
- local only
- global defaults plus a global reinstall

## Fix policy
- a threshold: small local fixes happen in 20; decision or multi-module changes become 20.x ✓
- everything in 20
- everything in 20.x

## Propagated amendments
- 16-CONTEXT D-01, 17-CONTEXT, REQUIREMENTS SPEC-01, the ROADMAP Phase 16 success criteria and
  PROJECT.md now use the new order.
- 18-CONTEXT D-05 gets the opencode local-install note.
- A spec §11 Errata section was added, collecting every discussion-time deviation from the
  approved spec.

## Deferred Ideas
- Process-tree host detection.
