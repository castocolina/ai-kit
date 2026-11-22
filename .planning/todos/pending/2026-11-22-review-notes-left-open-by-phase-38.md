---
created: 2026-11-22T00:00:00.000Z
title: Review notes left open by phase 38
area: tooling
severity: minor
files:
  - .planning/phases/38-runner-hardening-and-run-safety/38-REVIEW.md
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py
  - tools/staged_mapper.py
---

## Problem

The phase 38 code review left these items open. None loses data, prints a secret or leaves a process running; each is
a narrow window, a message that names too little, or a rule that needs an owner decision first.

## Goal

Close each item below when the named module is next changed, with a test for each behaviour change, and record the
owner's answer for the three decision items before any code changes.

## Notes

- Decision (owner): curated-config `apply` recomputes its writes from the live config and does not compare them with
  the preview the user approved; the skill tells the agent to rerun the dry run first. Binding apply to the approved
  preview (a digest of the planned writes stored with the plan and checked before the first write) is a design change
  of the plan format, outside 38-06's design (the gsd-core skill check). Decide whether the plan carries that digest.
- Decision (owner): `router_statement` confirms a router when the owner confirmed only `is_router` and the
  `fallback_quota` heuristic is true but unconfirmed; 38 D-17 reads the rule on `fallback_quota` with its label. Decide
  whether an `is_router`-only confirmation should give the router quota cycles, then narrow the rule or amend D-17.
- Decision (owner): `parseTasks` counts every task type that is not a checkpoint (an orchestrator decision during
  planning), while SPEC R5 and D-12 name absent, `auto`, `tdd` and `tracer`. Amend R5/D-12 to the code, or narrow the
  code to that list and count other types as unchecked.
- The state-home exclusion (`stateExcludeRel`) is computed against the working directory, so a runner started in a
  subdirectory of a checkout whose state home sits elsewhere inside the checkout snapshots the state dir. Resolve the
  path against the work-tree top and use a `:(top,exclude,literal)` pathspec.
- After three lost create-or-clear rounds `acquireLock` prints `run lock held by pid -`, naming no holder; print a
  distinct "not acquired after 3 attempts" line instead.
- `lockVerdict`'s `own` branch cannot be reached (a fresh run id is never read back); delete it or name the case it
  guards.
- The admission seed phrase `remaining work` also matches "no remaining work", which ends an otherwise complete run
  `partial`; add a negation guard or a recorded self-test case for that sentence.
- Hardcoded-model guard at commit time: the staged mapper now selects `tests.test_arch_hardcoded_models` for any staged
  file under skills/; a staged `.md`, `.json` or `.sh` under tools/, tests/ or docs/ (paths the guard also scans) still
  reaches it only at push.
- Older tests outside the phase 38 diff still run a bare PATH `node` (for example `tests/test_ai_kit_commit_fold_e2e.py`
  and `tests/test_ai_kit_usage_metrics.py`) under the runner's temporary HOME; check that the forwarded tool caches keep a
  Volta shim from looping there, or switch them to `_real_node_executable()`.
- Live proof owner items, unchanged by the review: the real-herdr sweep of 38-26 part (1) (no consent line), and the
  per-host idle output timing (not measured).
- Long lines in the curated-config and superpowers SKILL.md files (38-05 line 263 and three 38-24 lines): the files have
  no wrap rule and dozens of longer lines; rewrap them only together with a wrap rule.
