# Phase 22 — pi smoke evidence (headless harness; R4 acceptance is the owner's interactive run)

## Session
- date: 2026-10-23
- gsd-core: 1.17.0; `--host pi` forced; `GSD_RUNTIME=pi`
- seeded `PI_PROVIDER`: `anthropic` (inventory reads the seeded cache; owner's S5 checks the real session provider)
- scratch `HOME` and scratch `PI_CODING_AGENT_DIR`; no pi binary and no AI CLI run
- paths are recorded as labels only

## Headless harness run (agent)
Command: `python3 tests/gsd_curated_eval.py smoke --host pi --home <scratch-home> --installer-dir <installer> --evidence-out <evidence> --artifacts-out <artifacts>` under scratch HOME and scratch PI_CODING_AGENT_DIR, with the resolved node binary in PATH.

Harness evidence:

# Smoke evidence

## Steps
- step 1 ai-kit inventory, recommend, dry run: pass — dry run wrote nothing; host pi (flag)
- step 2 project (a) local gsd-core install: pass — installed 1.17.0 into .pi/gsd-core
- step 3 project (a) inventory, recommend, choices: pass — forced placeholders: none
- step 4 project (a) dry run, apply, validation: pass — apply and validation passed
- step 5 project (a) second apply: pass — second apply: writes 0, bytes identical, backups +1
- step 6 project (a) forced failure restores: pass — forced failure: exit 1, intel.enabled written then undone, restored
- step 7 project (a) post-apply install and planned == baked: pass — 35 agents; no agent files; hook == plan; repeat install unchanged
- step 8 project (b) empty project, apply, validation: pass — reconciled 1 key paths
- step 9 matrix on the selected host: pass — matrix ran: 420 checks, 5 hook probes
- step 10 protected set unchanged: pass — unchanged

## gsd-core
- version: 1.17.0
- path: <worktree>/.claude/gsd-core

## Matrix
- checks: 420; agents: 35
- hook probes: 5/5 ok
- control_1: ok
- control_2: ok
- informational runtime row: not run (claude only)

## Local install
- project-a: scope local, root <scratch-a>/.pi/gsd-core, version 1.17.0 (from inventory)
- project-b: scope local, root <scratch-b>/.pi/gsd-core, version 1.17.0 (from inventory)
- seed: absent
- installer: <installer> --<host> --local --no-legacy-cleanup
- installer env: an allowlist plus HOME and XDG paths under <install-home>

## Planned vs baked
- project-a: no GSD agent files (pi installs none); hook steers claude-sonnet-5 == plan
- project-a: a repeat install left the agents dir unchanged
- project-b: no GSD agent files (pi installs none); hook steers claude-sonnet-5 == plan

## Generated paths
- in every project: `.pi/.gsd-profile`, `.pi/.gsd-staging/`, `.pi/extensions/gsd.js`, `.pi/gsd-core/`, `.pi/gsd-file-manifest.json`, `.pi/gsd-hooks/`, `.pi/gsd-install-state.json`, `.pi/scripts/`
- project-a only: none; project-b only: none
- gitignore decision: ignore these prefixes in the target project; curated-config reports, never edits .gitignore

## Artifacts
- project-a and project-b labelled plan, config, resolve-model and baked artifacts

## Protected set
- unchanged
- host-managed changed: none

## Project (b) key paths
- plan_review.source_grounding_authority

## Caches
- seeded scratch cache; no runtime enumeration; byte-identical after every inventory

headless verdict: green (attempt 2: smoke exit=0, matrix ran: 420 checks, 5 hook probes, protected set unchanged, real-home snapshot ok)

## Real-home guard
- `snapshot --check`: `snapshot ok`

## Interactive run (owner)
not run (owner): R4 acceptance is the user's interactive pi session, 22-INTERACTIVE-PI.md S1-S5 (run rule 3).

## R4 and R5 status
- R4: rehearsed headless; acceptance pending the owner's interactive run.
- R5: green headless and in `make test` through `TestResolveModelMatrixPi`.

## Fixes (R7)

| Fix | Module | Commit | Regression test | Evidence |
|---|---|---|---|---|
| Pi thinking-level mapping, exact token fields, and exactly-one-RPC-envelope handling | `detection.py` | `7cd26e5` | `TestPiRpcModels` | 22-02 parser/schema checks; fixture-backed |
| `_PI_SKILL_SKIP` citation updated after gsd-core 1.17.0 re-check | `apply.py` | `4dd0bd8` | apply pi skip regression coverage | canonicalization check recorded in 22-03-SUMMARY.md |

Findings needing no fix: `skills-root pi` does not include pi's additional `~/.agents/skills` location (upstream behavior; agent-bound settings are inert on pi); `resolve-model` is not a pi effect oracle under `resolve_model_ids: omit` (the matrix verifies tiers independently and the request hook effect directly). These are recorded in `22-SPIKE-PI-AGENTS.md`, Findings (R7).

No other fix was needed in this phase's automated part.

## Phase status

The automated part is complete (22-01..22-07): the skill-judge evidence reads `## Verdict: PASS`
(`22-SKILL-JUDGE.md`), the gates (ruff, pyright, vulture, `make test`, `make validate`) pass, the
22-01 verdict re-derives as `session-steer (static + mock evidence)`, and the headless smoke above
is green. The phase is `human_needed`: the owner runs `22-INTERACTIVE-PI.md` (C1, S1-S5 and D9
required, L3a-L3c optional) and then its `## Orchestrator close-out`. Until then the SKILL.md pi
label stays `not live-validated`, the verdict stays `session-steer (static + mock evidence)`,
EVAL-08 stays Pending, and SPEC-05's real-capture acceptance waits on C1.
