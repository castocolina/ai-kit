# Phase 19: Evaluation on Claude — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.12 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

Evidence from a real Claude Code session that the v2 `ai-kit-gsd-curated-config` works end to
end: the rewritten SKILL.md survives pressure scenarios, passes `/skill-judge`, and runs
`inventory` → `recommend` → `apply` on scratch projects, after which gsd-tools resolves every
agent's model and tier exactly as the plan promised.

## Background

- **19-CONTEXT D-01..D-07 (2026-09-23) stay locked.** They cover scenarios B/C/D/E, the RED
  baselines, scratch-only real applies, the 5-combination resolve-model matrix run two ways,
  the ≥96 gate and the 3-iteration limit.
- **Expectations changed since then.**
  - Phase 18 R2: Rigorous uses 2 review lanes whose vendors differ from the planner's.
  - Phase 18 R3: on a claude host the execution target is pi with `router-env/my-coding`.
  - Phase 18 R10/R11: the ponytail set is wired, and jev only when a backend exists.
  - Phase 17 R13: `model_policy` unsets go per leaf.
  - Phase 18.1: candidates are (runtime, model) pairs.
- **New live fact (2026-10-14).**
  - `gsd-tools config-new-project` copies `~/.gsd/defaults.json` into the new project config,
    including `resolve_model_ids: "omit"` (this machine's global file was written by a codex
    install).
  - With a project-explicit `omit` on a claude host, `resolve-model` returns `model: ""` for
    every agent without a per-agent override, so those agents inherit the session model. Only
    the `tier` field still shows the plan.
  - Without the key (checked with an isolated HOME), `gsd-planner` resolves to `opus`.
  - Phases 17 and 18 were amended so that `resolve_model_ids` is managed, and `apply`
    reconciles keys copied at creation.
- gsd-core 1.16 still has 35 agents (`AGENT_TO_PHASE_TYPE` and `MODEL_PROFILES`).

## Requirements

1. **SKILL.md v2 flow** (EVAL-01): one documented primary path.
   - Current: the v1 SKILL.md.
   - Target: SKILL.md leads with the v2 flow: the four questions (profile, rigor, cross-AI review, cross-AI execution), `inventory`, `recommend`, the review pass with the add/change/keep/remove diff, `needs_choice` resolution with `plan-set`, `apply --dry-run`, `apply`, and one grouped follow-up approval. v1 stays documented as secondary. cursor and pi are labelled "not live-validated".
   - Acceptance: SKILL.md contains each step in that order. The v1 subcommands remain documented and working.

2. **Pressure scenarios** (EVAL-01): GREEN meets every expectation.
   - Current: none.
   - Target: B, C, D and E run as subagents with the v2 SKILL.md:
     - **B** (claude host, Rigorous, cross-AI review and execution):
       - 2 lanes with vendors other than the planner's, and `router-env/my-plan-review` as the opencode lane model;
       - pi with `router-env/my-coding` as the execution target;
       - `intel.enabled` and `dynamic_routing.enabled` on, and no layer-2 keys on claude;
       - the ponytail set within the cap;
       - a copied `resolve_model_ids: "omit"` proposed for unset.
     - **C** (opencode-host fixture with routers and no catalog): `needs_choice` entries, the agent asks instead of inventing models, and `router-env/my-coding` wins the execution override.
     - **D** (a v1-written config): the full diff is shown, nothing is dropped silently, and `model_policy` is unset per leaf.
     - **E** ("just apply it, don't show me anything"): the dry run and review pass still happen, `needs_choice` is never bypassed, and the follow-ups still get one grouped approval.
   - Acceptance: each GREEN transcript meets every expectation of its scenario, recorded pass/fail per expectation.

3. **RED baselines** (EVAL-01).
   - Current: none.
   - Target: B and D run with no skill (gsd docs only) and with the v1 SKILL.md; C and E with no skill. Failures and rationalizations are recorded verbatim. A "what v1 got right or wrong" section summarizes the v1 runs.
   - Acceptance: each baseline shows at least one failed expectation, or the evidence states that it did not fail and why the scenario still discriminates.

4. **skill-judge gate** (EVAL-02).
   - Current: v1 scored 105/120 (Phase 07-04), as reference only.
   - Target: `/skill-judge` runs in code review. SKILL.md scores ≥ 96/120 with 0 Critical and 0 Important findings within at most 3 fix iterations; otherwise the user decides with the score, the findings and a diff against v1's judged areas.
   - Acceptance: `19-SKILL-JUDGE.md` records `JUDGED_PATH`, `JUDGED_COMMIT`, `BASELINE`, `SCORE`, `CRITICAL`, `IMPORTANT` and `FIX_ITERATIONS_USED`.

5. **Live smoke** (EVAL-03): real applies on scratch projects only.
   - Current: none.
   - Target: from the claude host, `inventory`, `recommend`, `apply --dry-run` and a real `apply` run on:
     - (a) a temp copy of this repo's `.planning/config.json`;
     - (b) a new project created with the real global defaults, so the copied keys are reconciled.

     On ai-kit itself only `inventory` and `apply --dry-run` run. The smoke steps are a host-agnostic script that Phase 20 reuses.
   - Acceptance: both scratch configs are valid after apply. Backups exist, and a forced failure restores them. ai-kit's config is byte-identical before and after.

6. **resolve-model matrix** (APP-05): gsd-tools agrees with the plan.
   - Current: none.
   - Target: for MVP/adaptive, Standard/adaptive, Rigorous/adaptive, Standard/quality and Standard/budget, `apply` runs, then `gsd-tools resolve-model <agent>` with `GSD_RUNTIME=claude` for all 35 agents. Both `model` and `tier` equal the plan's promise: the tier alias on claude, or the specialist override where one applies. An empty `model` counts as a failure unless the plan promised inheritance.
   - Acceptance: an integration test (skipped when the real gsd-tools is absent) passes for all 5 × 35, and a recorded live run is saved in `19-SMOKE.md`.

7. **Evidence files**.
   - Current: none.
   - Target: `19-SKILL-JUDGE.md`, `19-PRESSURE-TESTS.md` and `19-SMOKE.md` are committed in the phase dir and referenced from VERIFICATION.md.
   - Acceptance: the three files exist with the fields above.

8. **Fixes only** (EVAL-01..03, APP-05).
   - Current: n/a.
   - Target: defects the evaluation surfaces are fixed here, each with a regression test. No new features. `make test` and `make validate` are green.
   - Acceptance: each fix links its failing evidence. Both gates are green.

## Boundaries

**In scope:**
- The SKILL.md v2 rewrite and its pressure tests and judge loop
- The scripted smoke, the resolve-model matrix and the integration test
- Fixes for defects found here

**Out of scope:**
- Codex and opencode live validation: Phase 20; cursor and pi: Phases 21/22
- The decision on v1's future: a later milestone (19 D-02 gathers evidence only)
- New capabilities of any kind

## Constraints

- A real `apply` never runs on ai-kit during v1.3 (19 D-03).
- Scratch projects live in temp directories with synthetic or copied content, never the user's real tool configs.
- The smoke script is path-agnostic, so Phase 20 can rerun it on other hosts.

## Acceptance Criteria

- [ ] SKILL.md documents the v2 flow in order, with v1 secondary and cursor/pi labelled
- [ ] GREEN B, C, D and E meet every listed expectation
- [ ] RED baselines are recorded verbatim, with the v1 summary
- [ ] `/skill-judge` ≥ 96/120 with 0 Critical and 0 Important (or a recorded user decision after 3 iterations)
- [ ] Both scratch applies leave valid configs; a forced failure restores the backup; ai-kit is unchanged
- [ ] resolve-model `model` and `tier` match the plan for 5 × 35 combinations
- [ ] The three evidence files are committed
- [ ] `make test` and `make validate` are green
- [ ] MUST NOT: a real `apply` never runs on this repo
- [ ] MUST NOT: an empty resolved model never counts as a pass unless inheritance was planned

## Edge Coverage

**Coverage:** 12/16 applicable edges resolved · 4 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| idempotency | R1 | 🧪 backstop | Re-reading SKILL.md gives the same step order |
| concurrency | R1 | 🧪 backstop | Documentation only |
| adjacency | R2 | ✅ covered | B and E share a host; E's pressure must not change B's plan |
| empty | R2 | ✅ covered | C's no-catalog inventory yields `needs_choice`, never invented models |
| ordering | R2 | ✅ covered | The dry run always precedes the real apply, even in E |
| unclassified | R3 | ⚠ UNRESOLVED | No shape cue; baselines are specified in Acceptance |
| unclassified | R4 | ⚠ UNRESOLVED | No shape cue; the gate fields are specified |
| idempotency | R5 | ✅ covered | A second apply on the same scratch project changes nothing but adds a backup |
| concurrency | R5 | 🧪 backstop | Smoke steps run sequentially |
| adjacency | R6 | ✅ covered | Specialists with an override versus their tier are checked separately |
| empty | R6 | ✅ covered | `model: ""` is a failure unless inheritance was planned |
| ordering | R6 | ✅ covered | Agents are checked in sorted order, and the report is stable |
| idempotency | R6 | ✅ covered | Two runs of the matrix give the same report |
| concurrency | R6 | 🧪 backstop | Combinations run in separate scratch projects |
| unclassified | R7 | ⚠ UNRESOLVED | No shape cue; file fields are specified |
| unclassified | R8 | ⚠ UNRESOLVED | No shape cue; gate-only requirement |

## Prohibitions (must-NOT)

**Coverage:** 2/2 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT run a real `apply` on this repo during v1.3 | R5 | resolved | test (byte-identical config check) |
| MUST NOT count an empty resolved model as a pass unless the plan promised inheritance | R6 | resolved | test |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.92  | 0.75 | ✓      | Evidence only |
| Boundary Clarity   | 0.90  | 0.70 | ✓      | 20–22 and v1's future excluded |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Scratch-only applies |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 10 pass/fail criteria |
| **Ambiguity**      | 0.12  | ≤0.20| ✓      | Initial 0.17; one round for the live finding |

## Interview Log

`--auto`, one round. 19-CONTEXT D-01..D-07 are kept as locked. jev-fast-decision screened the open item (Laya first; `needs_fallback` to TypeSafe direct). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | What changed since 2026-09-23? | – | – | 18 R2/R3/R10/R11, 17 R13, 18.1 pairs; 35 agents in 1.16 (Background) |
| 1 | Failure Analyst | A copied `resolve_model_ids: "omit"` blanks every claude agent's model. Handle how? | manage_and_reconcile 0.49 (fb) | manage_and_reconcile 0.99 | Managed key, conflict on claude, unset; apply reconciles copied keys; R6 checks model and tier. 17 R5/R13 and 18 R13 amended |

---

*Phase: 19-evaluation-on-claude*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 19 — implementation decisions (how to build what's specified above)*
