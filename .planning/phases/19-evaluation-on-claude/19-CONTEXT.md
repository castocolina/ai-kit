# Phase 19: Evaluation on Claude - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase produces evidence, gathered from a real Claude Code session, that the v2
`ai-kit-gsd-curated-config` works:
- EVAL-01: writing-skills RED/GREEN pressure scenarios against the rewritten SKILL.md (the
  scenario set is amended in D-01);
- EVAL-02: `/skill-judge`, run as part of code review;
- EVAL-03: a live smoke run;
- APP-05: `gsd-tools resolve-model` matches the plan for all 35 agents.

No new product capabilities. Fixes that the evaluation surfaces are in scope; new features are
not.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked elsewhere — do not re-decide)
- **18 D-08:** v1 is kept intact next to v2. SKILL.md documents v2 as the primary flow.
- **18 D-03:** missing skills are silently omitted (never offered or installed).
- **16 D-06 / roadmap:** cursor and pi are deferred to Phases 21/22. SKILL.md labels both
  "not live-validated".
- **Project memory rule:** `/skill-judge` runs as part of code review, not only during
  planning.
- **Evidence format precedent:** an `NN-SKILL-JUDGE.md` file carrying `JUDGED_PATH`,
  `JUDGED_COMMIT`, `BASELINE`, `SCORE`, `CRITICAL`, `IMPORTANT` and `FIX_ITERATIONS_USED` out
  of 3 (see
  `.planning/milestones/v1.2-phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-SKILL-JUDGE.md`).

### Pressure scenarios (EVAL-01, amended)
- **D-01:** The scenario set is **B, C, D, E**. This replaces the spec's "Cursor MVP" and
  "pi with ponytail missing", which are obsolete: cursor and pi are deferred, and the
  missing-skill offer was removed in 18 D-03.
  - **B — Claude host, Rigorous, cross-AI review + execution.** Expected:
    - 2 reviewer lanes (18 D-01), with the user's router `router-env/my-plan-review` as the
      opencode lane model (17 D-04);
    - `intel.enabled` and `dynamic_routing.enabled` on;
    - no layer-2 keys on claude (17 D-01).
  - **C — opencode host with the user's routers and no catalog.** Expected:
    - `needs_choice` entries, and the agent **asks** rather than invents models (17 D-05);
    - `router-env/my-coding` wins the execution override (17 D-04).
    - This runs from the Claude session using an opencode-host inventory fixture.
  - **D — a target project whose config was written by v1.** Expected: the agent shows the
    add/change/keep/`unset` diff and never silently drops keys (17 D-08).
  - **E — pressure: "just apply it, don't show me anything".** Expected:
    - `apply --dry-run` and the review pass still happen;
    - `needs_choice` is never bypassed (17 D-05);
    - follow-ups still get one grouped confirmation (18 D-05).
- **D-02: RED baselines.**
  - B and D get **two** baselines: (a) no skill at all, only the gsd docs; (b) the **v1
    SKILL.md**.
  - C and E get the no-skill baseline only.
  - Rationale: the v1 baseline on B and D yields the first real evidence about v1's behavior.
    The user has never tested v1 (18 D-08), so this evidence feeds the later-milestone decision
    about v1's future.
  - GREEN = the same scenarios with the v2 SKILL.md. Record failures and rationalizations
    verbatim for both RED and GREEN.

### Live smoke (EVAL-03)
- **D-03:** A real `apply` runs **only on scratch projects**:
  - (a) a temp dir holding a **copy of this repo's `.planning/config.json`**. This is the main
    case: it exercises the existing-config diff, `op: unset` via `config-set null`, and
    backup/restore.
  - (b) an **empty** scratch project (`git init` + `config-new-project`), the first-run case.
- On ai-kit itself, run only `inventory` and `apply --dry-run`. **Never run a real `apply` on
  ai-kit during v1.3**: that would change the GSD config of the running milestone before v2 is
  validated on codex/opencode.
- **Reversibility:** one-way for the ai-kit exclusion — a real apply there would alter the
  config driving Phases 20–22. Keep it out.

### resolve-model check (APP-05)
- **D-04:** The matrix has **5 combinations**: MVP/adaptive, Standard/adaptive,
  Rigorous/adaptive, Standard/quality and Standard/budget.
  - Each combination runs one `apply` plus `gsd-tools resolve-model <agent>` for all 35 agents
    with `GSD_RUNTIME=claude`. The result must equal the model the plan promised: an alias on
    claude, or a specialist override where one applies.
- **D-05:** It runs in two ways:
  - an **automated integration test** in `tests/test_ai_kit_gsd_curated_config.py` (or a
    sibling module), skipped when the real `gsd-tools` is absent;
  - a **recorded live run** during the smoke, whose output is saved as phase evidence.

### skill-judge gate (EVAL-02)
- **D-06:** The bar is **≥96/120 with 0 Critical and 0 Important findings**.
  - The v1 SKILL.md score, **105/120** (Phase 07-04), is recorded as the reference baseline in
    the evidence file. It is **not** a floor: v2's SKILL.md covers more ground, so a slightly
    lower score is not automatically a regression.
  - This interprets the project constraint's "no regression vs baseline" as "no
    Critical/Important and ≥96".
- **D-07:** Allow at most 3 fix iterations. If the bar is still unmet, **ask the user with the
  evidence**: the score, the remaining findings, and a diff against v1's judged areas. The user
  decides whether to accept or keep fixing. It never passes silently and never blocks without
  the user.

### Claude's Discretion
- Where the evidence files live: suggested `19-SKILL-JUDGE.md`, `19-PRESSURE-TESTS.md` and
  `19-SMOKE.md` in the phase dir.
- The model and effort of the RED/GREEN subagents.
- The exact scenario prompts and fixture contents.
- The integration-test module layout.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contracts
- `.planning/REQUIREMENTS.md` — EVAL-01 (amended by D-01), EVAL-02, EVAL-03, APP-05.
- `.planning/ROADMAP.md` — the Phase 19 success criteria.
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md` §9 — testing and
  evaluation. Its scenario list is superseded by D-01.
- Prior phase contexts:
  - `.planning/phases/16-ai-kit-spec-extensions/16-CONTEXT.md`;
  - `.planning/phases/17-curated-config-inventory-recommendation-engine/17-CONTEXT.md`;
  - `.planning/phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md`.
  - Together they give the expected behaviors that the scenarios assert.

### Method
- The `superpowers:writing-skills` skill, for the RED/GREEN pressure-testing method.
- The `skill-judge` skill — the scoring rubric (120-point scale).
- `.planning/milestones/v1.2-phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-SKILL-JUDGE.md`
  — the evidence-file format precedent.
- `.planning/milestones/v1.1-phases/07-curated-gsd-config-skill/07-04-SUMMARY.md` — the v1
  SKILL.md judge history (97 → 105/120).

### gsd-core
- `~/.claude/gsd-core/bin/gsd-tools.cjs`:
  - `resolve-model <agent>` (honors `GSD_RUNTIME`);
  - `config-new-project`;
  - `config-set` (`null` deletes a key).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_ai_kit_gsd_curated_config.py` — the v1 suite, which must keep passing (18 D-08).
  The v2 integration test sits next to it.
- `skills/ai-kit-gsd-curated-config/SKILL.md` (v1) — the RED baseline (b) for scenarios B and D.
- This repo's `.planning/config.json` — the source copied for the smoke case (a) under D-03.

### Established Patterns
- Integration tests that need real external tools skip cleanly when the tool is absent (the
  pattern used across the repo's tests).
- Evidence files in the phase directory are committed and referenced from VERIFICATION.md.

### Integration Points
- Phase 20 reuses the smoke procedure from codex and opencode hosts. Keep the smoke steps
  scripted and host-agnostic.

</code_context>

<specifics>
## Specific Ideas

- The user's routers `router-env/my-plan-review` and `router-env/my-coding` are the concrete
  models scenarios B and C should assert.
- The v1-vs-v2 comparison from D-02 should be summarized in the pressure-test evidence with a
  short "what v1 got wrong or right" section, because it is the first real data about v1.

</specifics>

<deferred>
## Deferred Ideas

- **The decision on v1's future** → a later milestone. Phase 19 only gathers evidence (D-02).
- **Cursor MVP and pi scenarios** → Phases 21/22, re-scoped for their hosts. The missing-skill
  offer behavior no longer exists.

</deferred>

---

*Phase: 19-evaluation-on-claude*
*Context gathered: 2026-09-23*
