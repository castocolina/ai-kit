# Phase 19 — live smoke from the claude host (EVAL-03, APP-05)

## Session
- date: 2026-10-17T20:00:42Z; re-run 2026-10-17T22:34:48Z after the code-review fixes (fd80e5e): step 7 now fails on a failing matrix and the controls print ok/FAILED (19-REVIEW H2). Every step and the protected set came out the same; the first run's evidence printed `recorded` for both controls
- host detected: claude (inventory `host_source: detected`, no `--host` flag; step 1 detail below)
- claude --version: 2.1.302 (Claude Code)
- gsd-core: version 1.17.0 at `<worktree>/.claude/gsd-core` (the matrix pins `GSD_CORE_PREFIXES` 1.16./1.17.; tables verified key-identical, 19-01)
product_commit: deb85b3
- helper command: `python3 tests/gsd_curated_eval.py smoke --evidence-out tmp/smoke/body.md`
- scratch projects: `<scratch-a>` (project a, copy of this repo's config) and `<scratch-b>` (project b, empty), both under one `mktemp -d` dir removed after the run

## Steps
- step 1 ai-kit inventory, recommend, dry run: pass — dry run wrote nothing; host claude (detected)
- step 2 project (a) inventory, recommend, choices: pass — forced placeholders: none
- step 3 project (a) dry run, apply, validation: pass — apply and validation passed
- step 4 project (a) second apply: pass — second apply: writes 0, bytes identical, backups +1
- step 5 project (a) forced failure restores: pass — forced failure: exit 1, intel.enabled written then undone, restored
- step 6 project (b) empty project, apply, validation: pass — reconciled 1 key paths
- step 7 matrix on the selected host: pass — matrix ran: 420 checks
- step 8 protected set unchanged: pass — unchanged

## gsd-core
- version: 1.17.0
- path: <worktree>/.claude/gsd-core

## Matrix
- checks: 420; agents: 35
- control_1: ok
- control_2: ok
- informational runtime row: model gpt-5.6-sol, tier opus

## Protected set
- unchanged
- host-managed changed: none

## Project (b) key paths
- plan_review.source_grounding_authority

## Caches
- seeded scratch cache; no runtime enumeration; byte-identical after every inventory

## Defect fixes
- none (no product defect; product paths unchanged during the plan)

## Harness fixes
- 3ada8c6 step 1 (whole run aborted before any step): `_smoke_ai_kit` applied the real-apply repo-root refusal to the dry-run step; regression test `test_ai_kit_step_runs_on_the_repo_root`
- 91c243d steps 1-6 (`plan-set` refused `trusted_global_roots`): `resolve_choices` sent `str()` of the candidate dict and read runner choices as a bare list; regression test `test_resolve_choices_encodes_product_candidate_shapes`, unit fixtures moved to the product shape
- c5033cd step 1 (EVAL-03 not exercised): `smoke` forced `--host claude`; it now lets inventory detect the host and fails on a mismatch; regression test `test_inventory_without_host_flag_lets_the_product_detect`

## Decisions routed through jev
