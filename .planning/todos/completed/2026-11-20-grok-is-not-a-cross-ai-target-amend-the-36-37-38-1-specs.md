---
created: 2026-11-20T04:57:00.000Z
title: Grok is not a cross-AI target: amend the 36, 37 and 38.1 specs and keep the grok code until Phase 39.1
area: planning
severity: minor
files:
  - .planning/phases/36-spec-config-as-the-hub/36-SPEC.md
  - .planning/phases/37-shared-runner-options-and-session-ids/37-SPEC.md
  - .planning/phases/37-shared-runner-options-and-session-ids/37-CONTEXT.md
  - .planning/phases/38.1-runner-error-classification-and-retry-policy-inserted/38.1-SPEC.md
  - .planning/phases/38.1-runner-error-classification-and-retry-policy-inserted/38.1-CONTEXT.md
---

## Problem

Owner directive during the 2026-11-19 autonomous run (translated): do not consider grok as a possible cross-AI runtime
target; it is reachable through opencode or pi and may be replaced by cursor-agent. A second message asked for a sub-phase
that removes it: inserted as Phase 39.1 (RUN-15, no SPEC yet).

The Phase 36, 37 and 38.1 documents still mention grok: 36-SPEC (5 mentions), 37-SPEC (8), 37-CONTEXT (3), 38.1-SPEC (1),
38.1-CONTEXT (1). The Phase 37 amendment listed grok 1.0.52 among the hosts with recorded help and a stale-flag test.

## Solution

TBD. When each unit is planned or executed: add a dated amendment saying grok is out of scope (no help fixture, no
form, no probe, no list entry for grok), without removing the existing grok code (detection row, `build_grok_command`,
tests, `cursor-agents/grok-worker.md`), which Phase 39.1 deletes. The grok MODELS reached through cursor-agent,
opencode or pi are unaffected. Plans for 36, 37 and 38.1 must not add grok work.

Severity is the orchestrator's suggestion from an unattended run; confirm it at triage.

Resolved 2026-11-23 by Phase 39.1: the five documents carry the 39.1 amendment and the grok runtime code is removed.
