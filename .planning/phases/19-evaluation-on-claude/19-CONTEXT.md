# Phase 19: Evaluation on Claude - Context

**Gathered:** 2026-09-23 (interactive); updated 2026-10-14 (assumptions mode, after `19-SPEC.md`)
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
      opencode lane model (17 D-04) when the router is user-confirmed (`heuristic_confirmed`
    contains `is_router`; the fixture confirms both routers; Amended 2026-10-17 (19-RESEARCH R-4));
    - `intel.enabled` and `dynamic_routing.enabled` on;
    - extra, non-gating expectation: `ensure-runner` and the v2 full-permission disclosure are
      surfaced (jev 19-Q6, 2026-10-17);
    - no layer-2 keys on claude (17 D-01).
  - **C — opencode host with the user's routers and no catalog.** Expected:
    - `needs_choice` entries, and the agent **asks** rather than invents models (17 D-05);
    - `router-env/my-coding` wins the execution override (17 D-04).
    - This runs from the Claude session using an opencode-host inventory fixture.
  - **D — a target project whose config was written by v1.** Expected: the agent shows the
    add/change/keep/remove diff (plan op `unset` shows as `remove`) and never silently drops keys
    (17 D-08). Amended 2026-10-17 (19-RESEARCH R-3): dry-run row kinds are add/change/keep/remove.
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

### Added 2026-10-14 (assumptions-mode discuss, jev-screened)
- **D-08: Matrix isolation.**
  - Every gsd-tools subprocess in the matrix gets `GSD_HOME=<tmp>` holding a synthetic
    `.gsd/defaults.json` of `{"resolve_model_ids":"omit","runtime":"codex"}`, plus
    `GSD_RUNTIME=claude`. `HOME` stays real, because v1's search roots and the inventory are
    `$HOME`-relative.
  - The poison fixture carries no `model_policy`: a policy resolves before the omit gate and
    would hide the bug.
  - `GSD_HOME` does not cover `effort sync` or the installer, so the matrix never runs them.
- **D-09: The matrix runs 5 combinations × 2 start paths, plus 2 controls.**
  - P1: no config at start; `apply` creates it and reconciles.
  - P2: a pre-poisoned config; the plan carries the unset.
  - Control 1 skips the fix and must fail every agent that has no override.
  - Control 2 uses clean defaults and must pass.
  - Measured cost: about 30 s for 350 calls. TypeSafe 0.97.
  - Amended 2026-10-17 (19-RESEARCH R-11): the poison reaches the project config only as `resolve_model_ids`
    (`config-new-project` does not copy `runtime`); gsd-tools stderr warnings are not a failure
    signal. An informational P2 row without `GSD_RUNTIME` records the project-level `runtime`
    gap left by 18 D-30; it does not gate APP-05 (jev 19-Q1).
- **D-10: An independent oracle.**
  - It is built from the plan's set entries plus gsd-core's live `MODEL_PROFILES` and
    `AGENT_TO_PHASE_TYPE`, and asserts that the two tables have the same agent keys.
  - It is host-parameterized, so Phase 20 reuses it, and `recommend` emits no new field.
  - Amended 2026-10-17 (19-REVIEWS cycle 2, checker cycle-2 W6): Phase 19 keeps the host plumbing
    (`run_matrix(..., host=)`, `matrix --host`, `smoke --host`, `matrix_env(..., host)`) but the oracle
    mapping is Claude-only: `promised()` returns tier aliases, so a non-claude host exits 2 with a
    Phase 20 pointer instead of producing a wrong verdict. Mapping `model_profile_overrides.<host>.<tier>`
    and `RUNTIME_PROFILE_MAP` into `promised()` is Phase 20 work. The SPEC's host-agnostic smoke script
    stays host-agnostic in its steps; only its matrix step is Claude-only until then.
  - Module: `tests/test_ai_kit_gsd_curated_config_matrix.py`, added to `E2E_MODULES` in
    `tools/run_unittest_parallel.py` with `python3 tools/gen_test_groups.py` re-run (Amended 2026-10-17 (19-RESEARCH R-6));
    a hermetic helper test joins `unit` automatically; with `skipUnless` for real gsd-tools and node.
  - TypeSafe 0.79, over Laya expected_field 0.45 fb.
- **D-11: Fixtures are built at run time** by one builder from the real tools:
  - B: real `config-new-project` under the poisoned `GSD_HOME`;
  - C: 17 D-20's tables builder, opencode host, unscored, with both routers;
  - D: real v1 subcommands plus per-leaf `model_policy` keys;
  - E: B's answers with an empty `other_clis`, so a `needs_choice` is guaranteed.

  No absolute paths are committed. **Laya overridden** (frozen 0.82): a frozen fixture can stop
  matching real v1 output, and then the scenario cannot fail. TypeSafe second opinion
  runtime_builder 0.99.
- **D-12 (refines D-01/D-02's "subagent" wording): Pressure runs are headless, fresh-context
  `claude -p` sessions.**
  - Each runs from a scratch cwd with a tool allowlist (`Read,Bash,Glob,Grep`, no Skill tool),
    limited `--setting-sources` and `--output-format stream-json`, under the `child_env`
    scrub (now `ai_kit_spec/runner_dispatch.child_env`, Amended 2026-10-17 (19-RESEARCH R-19)).
  - The skill and CLI are pinned to the worktree by a path discovered at run time.
  - Any Skill-tool call counts as a harness failure.
  - Grading is per expectation: scripted end-state checks, ordering read from the documented
    transcript, and rationalizations quoted verbatim.
  - The scenario files live in `skills/ai-kit-gsd-curated-config/evals/NN-*.md`.
  - RED-b uses the v1 SKILL.md frozen from git at `7009d22^`, the last v1 file users had
    (Amended 2026-10-17 (19-RESEARCH R-5), jev 19-Q2); the commit is recorded in the evidence.
  - Sampling: REFACTOR cap 3 rounds, 1 sample per cell, re-sample only an ambiguous cell
    (jev 19-Q4). Model: `sonnet` at medium effort for every cell, plus one `opus` high
    confirmation run of the v2 GREEN cells; the model id is recorded from the run (jev 19-Q5).
  - Runs use the real Claude login from scratch project dirs. The only allowed writes under
    `~/.claude` are the session transcripts; protected `~/.claude` config files are snapshotted
    and diffed before and after every batch, and the scratch-project transcript dirs are deleted
    afterwards (jev 19-S1).
  - Why: in-session subagents inherit this repo's AGENTS.md and a global skill listing that
    includes the v1 skill, which contaminates the no-skill baseline. TypeSafe 0.99.
- **D-13: The smoke and matrix share one dev-only stdlib helper**, `tests/gsd_curated_eval.py`
  (`smoke`, `matrix`, `fixture`, `snapshot`).
  - It resolves the skill from its own repo location, never the installed symlink, and evidence
    paths use placeholders.
  - It is not shipped and is not a skill subcommand (R8).
  - Precedent: `tests/wizard_fixtures.py`.
  - Own reasoning; both models were low (Laya bash 0.40 fb, TypeSafe tests_helper 0.59 fb).
    Provisional, so it is on the ledger.
- **D-14: The smoke steps.**
  1. Snapshot sha256 of the protected set: ai-kit's `config.json`, its backups,
     `cross-ai.mjs*`, and the real `~/.gsd/defaults.json` (read only). Not all of `.planning/`,
     because STATE changes during a session.
  2. On ai-kit, run only inventory, recommend and the dry run.
  3. Project (a): resolve `needs_choice` with the first listed candidate where one exists, else
     a `--force` pin of a placeholder model id (helper only, recorded as such), dry run, then
     apply. Validate, then check that a second apply writes no config keys and leaves the config
     bytes identical; it adds one backup, pruned at `KEEP = 3` (Amended 2026-10-17 (19-RESEARCH R-8, R-9)).
  4. Forced failure on a copy: a copy of the plan with the `review.default_reviewers` entry
     edited to `op: set`, `value: "notarray"` (the helper edits the copy; `plan-set` refuses it);
     expected exit 1, config bytes restored, no marker (Amended 2026-10-17 (19-RESEARCH R-10)). The real gsd-tools
     rejects it (verified; most other garbage values are accepted).
  5. Project (b): created with the real `GSD_HOME`. The reconcile is family-wide (17 D-08),
     and only key paths are recorded, never values.
  6. Run the matrix.
  7. Re-snapshot, and exit 1 on any change.

  TypeSafe real_rejection 1.00.
- ~~**Finding, not fixed here:** the v1 integration tests run `ensure-project` without isolation
  (`tests/test_ai_kit_gsd_curated_config.py:182-219,1188-1274`), so they copy the developer's
  real global defaults.~~ **Withdrawn 2026-10-17 (19-REVIEWS cycle 2, verified by the
  orchestrator):** the v1 `ensure-project` tests drive `cli.main` with a fake `run_fn`
  (`make_fake_run`), a fake install root and `tempfile` project dirs; no real gsd-tools runs, so
  no real global defaults are copied. Nothing goes to the evidence or the backlog.

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
- `<checkout>/.claude/gsd-core/bin/gsd-tools.cjs` (project-local 1.16.x; Amended 2026-10-17 (19-RESEARCH R-7)):
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
*Context gathered: 2026-09-23; updated 2026-10-14*
