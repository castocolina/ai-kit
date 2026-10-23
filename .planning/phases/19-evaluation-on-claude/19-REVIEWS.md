---
phase: 19
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-17T14:54:00Z
plans_reviewed: [19-01-PLAN.md, 19-02-PLAN.md, 19-03-PLAN.md, 19-04-PLAN.md, 19-05-PLAN.md, 19-06-PLAN.md, 19-07-PLAN.md, 19-08-PLAN.md, 19-09-PLAN.md, 19-10-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
cycle: 3
reviewed_revision: 19991e8
---

# Cross-AI Plan Review — Phase 19 (convergence cycle 3)

Cycle 1 is in git history at `291d253`, cycle 2 at `830c029`; the plans were revised in
`19991e8`. This cycle's reviewer verified the Round 1 and Round 2 ledgers and raised only new or
open findings: 3 HIGH and 4 MEDIUM.

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review (opencode-plan-review)

Reviewed revision `19991e8` against repository source and both previous reviews. This is a **GSD implementation-plan review**, not execution verification: “resolved” below means the revised implementation contract addresses the finding.

For brevity, plan citations use `19-NN-PLAN.md`; all are under `.planning/phases/19-evaluation-on-claude/`.

## 19-01

**Summary:** The Claude matrix has converged. Its independent oracle, controls and environment propagation now provide a credible APP-05 test contract.

**Prior HIGH verification**
- The shared digest-layout concern is addressed by the explicit digest-row schema, required columns and exact expectation-row validation in `19-03-PLAN.md:327–350`.
- Full-plan delivery is now an explicit requirement rather than an assumption about stock GSD delegation. See `19-01-PLAN.md:135–144`. The common dispatch assessment appears after the ten plan sections.

**Strengths**
- One environment is passed through both apply seams (`19-01-PLAN.md:307–313`), matching the actual last-merge behavior in `tests/test_curated_config_apply_e2e.py:88–91`.
- The oracle uses plan entries rather than applied config, with negative controls (`19-01-PLAN.md:281–319`).
- Non-Claude mapping is explicitly deferred and refused rather than producing false failures (`19-01-PLAN.md:261–268`; `19-CONTEXT.md:128–133`).

**Concerns:** No additional NEW or OPEN finding.

**Suggestions:** Retain the specified environment-identity and control non-vacuity tests; no additional abstraction is needed.

**Risk Assessment: LOW.** Remaining uncertainty is implementation correctness, not an unresolved matrix design decision.

## 19-02

**Summary:** The original fixture and entrypoint HIGHs are addressed. Two new contract inconsistencies remain in fixture isolation and process cleanup.

**Prior HIGH verification**
- **E’s impossible choice — resolved.** The scripted answer permits disabling execution, and the fixture must prove that this closes all choices (`19-02-PLAN.md:321–327`). This matches `plan_edit.py:172–173,299–307`.
- **B/D inventory mismatch and catalog preservation — resolved for the original freshness mechanism.** The sidecar, serializer fixed point, Claude-row repair and real-inventory self-check are specified at `19-02-PLAN.md:265–305`. These match `ai_kit_spec/cli.py:485–495,530–541` and `routing.py:240–247`.
- **Historical entrypoint shadowing — resolved.** Only the resolver block is pinned, the plugin-root override is removed, and wrong entrypoints become harness failures (`19-02-PLAN.md:331–341,356–358,388–390`).
- **Command/result pairing and D’s coverage — resolved.** The event contract retains full paired results (`19-02-PLAN.md:394–405`), and D includes `full_diff_shown` (`:246–248`).

**Strengths**
- Failed turns now stop scripted continuation instead of becoming behavioral verdicts (`19-02-PLAN.md:374–392`).
- Cache freshness is checked before ordinary inventory refresh, not merely after a possible prohibited write (`:289–300`).

**Concerns**
- **MEDIUM · NEW — The fixed-point fetch still consumes ambient review configuration.**  
  `19-02-PLAN.md:269–271,284–286` inherits the real environment without fixing `XDG_CONFIG_HOME`. The fixture marks Grok installed without a `models` field (`tests/fixtures/curated_config_v2/runtimes.json:111–113`). That makes `_discovered_catalog_candidates()` call `cfg_resolve()` **before** fetch freshness is checked (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:466–477,597–618`). The global TOML path then follows the ambient config directory (`config_io.py:268–291,435–444`). A malformed or different user review configuration can therefore change or abort supposedly controlled fixture construction despite fresh caches. This is separate from the explicitly permitted inventory backend-presence read.
- **MEDIUM · NEW — Ancestor-safe reaping requires data absent from its interface.**  
  `ps_fn` returns `pid,pgid,args` (`19-02-PLAN.md:349–351`), but `_reap_strays` must discover every ancestor through a **PPID column** (`:365–370`). That column does not exist. The prescribed tests cover self, immediate parent and own group, not a higher ancestor in another group (`:455–459`). Literal implementation cannot establish the claimed protection before group-wide SIGKILL.

**Suggestions**
- Give fetch/inventory a scratch review-config location, or remove irrelevant installed-without-models rows from the controlled fixture. Test that ambient TOML cannot affect construction.
- Include PPID in the process snapshot and test a higher ancestor in another process group.

**Risk Assessment: MEDIUM.** Both issues can derail or endanger the harness independently of skill behavior.

## 19-03

**Summary:** Most grading HIGHs are closed. The execution-target predicate still misclassifies the actual v1 hook shape, leaving a central cycle-2 finding open.

**Prior HIGH verification**
- **Zero approvals/grouped question, post-write disclosure, failed/unrelated previews — resolved** by paired reports, pre-write text boundaries and matching preview targets (`19-03-PLAN.md:257–279`).
- **Baseline workflow bias and no-op `ensure-project` handling — resolved** (`:205–228`). The distinction matches the existing direct-write v1 workflow in `references/v1-path.md:10–17`.
- **Bare Cursor vendor classification — resolved** through the existing vendor inference (`19-03-PLAN.md:234–245`).
- **Required follow-up execution results — resolved** by matching IDs/fingerprint and zero return codes (`:273–278`), consistent with `followups.py:396–420,448–481`.
- **D’s full-diff coverage and incomplete evidence gates — resolved in the specified contract** (`19-03-PLAN.md:291–295,327–350`).
- **Effective execution target — still OPEN**, below.

**Strengths**
- Outcome checks no longer require v2 intermediate artifacts in baseline cells (`19-03-PLAN.md:205–215`).
- Required evidence columns and exact row sets fail closed on missing material (`:334–350`).

**Concerns**
- **HIGH · OPEN — The prefix test still misclassifies the actual v1 execution hook.**  
  `19-03-PLAN.md:246–251` reads CONFIG whenever the hook starts with `node .planning/scripts/cross-ai.mjs`, assuming model-bearing v1 hooks use the other branch. They do not: `cross_ai_build.py:87–92` calls `project_runner_command()`, which produces that same prefix followed by `--prefer` and `--model-<runtime>` (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:157–176`). The runner gives those CLI overrides precedence over CONFIG (`references/cross-ai.mjs:2766–2769`).  
  Thus a correct v1 hook can fail with empty CONFIG, while a hook overriding pi to the wrong model can pass because CONFIG still contains the expected router. The proposed synthetic non-runner positive case does not exercise this shape (`19-03-PLAN.md:406–408`).

**Suggestions**
- Distinguish the **bare** v2 hook from flagged hooks, then evaluate effective preference/model after command-line overrides.
- Use the actual v1 builder shape in both positive and negative tests.

**Risk Assessment: HIGH.** The remaining predicate can manufacture both false RED and false GREEN execution-target results.

## 19-04

**Summary:** The smoke procedure now addresses the previously identified choice-resolution, serialization and rollback defects.

**Prior HIGH verification**
- **Skill-reference readback — resolved.** The independent serialized-reference comparison replaces raw equality (`19-04-PLAN.md:248–260`), matching `skills.py:156–167`.
- **Derived command overwritten by placeholder — resolved.** Artifact choices are resolved first, the plan is reloaded, and an unresolved hook is refused (`19-04-PLAN.md:237–247`). This matches `plan_edit.py:374–384`.
- **Vacuous rollback experiment — resolved.** A preceding real write must appear in the recorder, and byte restoration must undo it (`19-04-PLAN.md:263–279`).
- **Ordinary live-inventory safety — addressed** by the seeded-cache and pre-probe checks (`:211–220`).

**Strengths**
- Both scratch paths receive explicit validation with different backup expectations (`19-04-PLAN.md:248–283`).
- The fault experiment now tests restoration rather than merely marker cleanup (`:263–279`), consistent with the existing nth-key failure test in `tests/test_curated_config_apply_e2e.py:322–347`.

**Concerns:** No additional strong NEW or OPEN finding.

**Suggestions:** Preserve the actual-write requirement in the rollback test; do not weaken it to restored hashes alone.

**Risk Assessment: LOW.** The design is now sufficiently specific for implementation and live verification.

## 19-05

**Summary:** The smoke orchestration is coherent after revision. Snapshot lifetime, failure attribution and ordinary inventory safety are addressed.

**Prior HIGH verification**
- **Live inventory rewriting Cursor configuration — resolved for this smoke path.** Every smoke inventory uses controlled cache freshness, with strict Cursor-config detection as a backstop (`19-05-PLAN.md:137–147`; `19-04-PLAN.md:211–220`). This prevents the ordinary detection path that calls the mutating Cursor listing documented in `detection.py:304–311`.
- Product-provenance and dispatch concerns have explicit obligations (`19-05-PLAN.md:106–118,64–80`).

**Strengths**
- The triage table distinguishes harness, environment and demonstrated product failures (`19-05-PLAN.md:180–185`).
- The snapshot required by post-plan verification is retained until phase close (`:236–249`).

**Concerns:** No additional NEW or OPEN finding specific to this plan.

**Suggestions:** Keep `## Caches` and the written-then-undone fault detail in the recorded evidence, as acceptance already requires (`19-05-PLAN.md:214–216`).

**Risk Assessment: LOW.** Successful live execution remains to be demonstrated; the procedure itself no longer contains the earlier safety contradiction.

## 19-06

**Summary:** Baseline grading is materially fairer, and state retention is improved. However, the historical v1 baseline invokes a separate, uncached enumeration path that the new inventory protections do not isolate.

**Prior HIGH verification**
- **Baseline failure by construction — resolved.** Workflow checks become `n/a`, and the comparison uses outcome rows (`19-06-PLAN.md:223–246`; producer contract in `19-03-PLAN.md:205–215`).
- **Entrypoint shadowing — addressed** by the pinned historical resolver and harness-failure handling (`19-02-PLAN.md:331–341`; `19-06-PLAN.md:158–165`).
- Digest layout and product-revision replay obligations are explicit (`19-06-PLAN.md:228–239,305–307`).

**Strengths**
- Configuration absence is preserved as a fact instead of requiring C to create a config (`19-06-PLAN.md:207–216`).
- Each cell retains its grading record and supporting state before cleanup (`:202–216`).

**Concerns**
- **HIGH · NEW — RED-b bypasses cache protection and can execute the mutating real Cursor listing.**  
  This plan requires following historical v1 instructions (`19-06-PLAN.md:298–301`), whose steps require `detect-execution-candidate` and `detect-review-candidate` (`7009d22^:skills/ai-kit-gsd-curated-config/SKILL.md:95–109`). Those commands call `_detect_candidate_pool()` (`cli.py:186–213`), which invokes **bare `detect-runtimes`, without `--if-stale`** (`model_detect.py:51–63`). The spec CLI consequently builds a fresh runtime snapshot (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:425–434`), including Cursor enumeration. That listing explicitly rewrites real Cursor configuration (`detection.py:304–311`).  
  Fresh seeded caches do not intercept this path. The strict snapshot detects the prohibited change afterward but cannot make the required baseline safe beforehand. This is a normal historical-flow operation, not the already-registered hypothetical Bash escape.

**Suggestions**
- Isolate RED-b’s runtime listings through run-scoped fixture-backed CLI wrappers or equivalent per-runtime configuration isolation.
- Add a test proving that following the required v1 detect steps cannot execute a listing against real Cursor configuration.

**Risk Assessment: HIGH.** The required baseline can violate the no-real-config-write constraint before it is graded.

## 19-07

**Summary:** The evidence-gated editing policy has converged. Its earlier ordering, advisory-failure and incomplete-evidence concerns are addressed.

**Prior HIGH verification**
- Required digest columns and strict row extraction now gate the GREEN evidence (`19-07-PLAN.md:334–338,374–378`).
- Product changes invalidate earlier behavioral runs (`:329–331`).
- Oversized/invalid advisory packets have explicit bounded-input and unavailable handling (`:242–258`).
- The accepted dispatch mitigation is explicit (`:90–106`).

**Strengths**
- The six-label order assertion is specified independently of wording pins (`19-07-PLAN.md:217–221`); the current six labels match it in `SKILL.md:69–148`.
- Advisory failures remain visible without triggering repair or blocking completion (`19-07-PLAN.md:45,257–258,378`).
- Existing rules do not get restated merely because a no-skill baseline failed (`:166–175`).

**Concerns:** No additional NEW or OPEN finding specific to this plan. The OPEN grading issue in 19-03 must be corrected before its results license prose edits.

**Suggestions:** Retain the no-edit branch when existing instructions already state the behavior.

**Risk Assessment: MEDIUM.** The editing process is disciplined, but it depends on the grader producing trustworthy evidence.

## 19-08

**Summary:** Conflicting available judges can no longer be discarded by aggregation. Invalid-attempt handling remains incomplete because classification uses status without checking the accompanying tree result.

**Prior HIGH verification**
- **One pi PASS concealing another available judge’s findings — resolved** by the all-live-rows rule (`19-08-PLAN.md:31,216–225`).
- **Contract failures treated as unavailability — partially resolved.** Explicit contract/git statuses are invalidated, but timeout/signal outcomes retain the loophole below.
- Evidence completeness and pre-move scanning are addressed (`:202–225,283`).

**Strengths**
- Reports are scanned recursively before their first tracked move (`19-08-PLAN.md:202–214`).
- Scores remain digest-bound, and an available failing judge yields PENDING rather than PASS (`:216–225`).

**Concerns**
- **HIGH · OPEN — Timeout/signal can still convert invalid review execution into waiver-compatible unavailability.**  
  `19-08-PLAN.md:189–197` classifies timeout and signal as unavailable after retry without examining `tree`. The runner returns timeout **before** its dirty-review and failed-final-snapshot checks (`skills/ai-kit-spec-review/references/cross-ai.mjs:2897–2901,2915–2918`). Signal handling likewise preserves the observed tree field (`:2928`); its self-test explicitly expects `status=signal ... tree=dirty` (`:1823–1828`).  
  A timed-out or signalled attempt with `tree=dirty` or `tree=unknown` can therefore become an allowed unavailable row beside another passing judge. Matching the skill digest does not prove the rest of the reviewed tree stayed unchanged.

**Suggestions**
- Require a dispatched attempt’s verified `tree=clean` before treating its failure as provider/environment unavailability.
- Route dirty or unverifiable trees through invalid-attempt handling regardless of timeout/signal status.

**Risk Assessment: HIGH.** Review-integrity failures can still be excluded from the aggregate as ordinary unavailability.

## 19-09

**Summary:** The fix loop now handles score-only findings, bounded advisory input and missing GREEN evidence. One new acceptance contradiction prevents its explicitly permitted product-fix branch from completing.

**Prior HIGH verification**
- **Judge fixes introducing GREEN regressions — resolved** by the combined stop rule and rerouting (`19-09-PLAN.md:214–224,325–331`).
- **Owner packet exceeding `decide.py` limits — resolved** by a local full packet plus bounded, fence-free summary (`:233–255`), matching `decide.py:224–233`.
- **Harness-failed GREEN accepted as success — resolved** through retry and explicit PASS rejection (`19-09-PLAN.md:281–284,325–330`).
- Invalid judge handling inherits the remaining OPEN finding from 19-08 (`:164–165`); it is not a separate duplicate finding.

**Strengths**
- Rejected findings retain their original score and require source-backed reasoning (`19-09-PLAN.md:199–211`).
- Every prose fix precedes its GREEN and judge reruns (`:199–224`).

**Concerns**
- **MEDIUM · NEW — Acceptance forbids the product-fix commits the plan explicitly permits.**  
  Run rule 6 permits regression-tested product fixes (`19-09-PLAN.md:131–143`), and Task 3 requires replay after a `fix(19-09)` commit (`:348–350`). Yet acceptance requires **every commit made by this plan** to leave the entire curated-config product package unchanged (`:369`). A legitimate fix to `apply.py`, for example, cannot satisfy both instructions.

**Suggestions**
- Apply the unchanged-product assertion to judge/prose commits only. Exempt separately recorded product-fix commits with their regression tests and required evidence replay.

**Risk Assessment: HIGH until 19-08 is corrected; otherwise MEDIUM.** The new local issue is an execution contradiction, not a reason to discard the bounded loop.

## 19-10

**Summary:** Product provenance, RED replay and the withdrawn isolation allegation are now correctly handled. A remaining acceptance clause conflicts with the required late-fix evidence refresh.

**Prior HIGH verification**
- **Late product fixes leaving behavioral evidence stale — resolved in the replay contract** (`19-10-PLAN.md:179–202`).
- **Concrete procedure omitting RED — resolved.** RED-b always reruns; product-running RED-a cells are selected from retained command records (`:187–198`). This reflects v1’s shared wrappers in `cli.py:85–108`.
- **False v1 isolation allegation — resolved and formally withdrawn** (`19-10-PLAN.md:235–238`), consistent with temporary HOME and explicit subprocess environments in `tests/test_curated_config_e2e.py:51–78,117–140`.
- Strict evidence columns and per-file ignored-file comparison are now specified (`19-10-PLAN.md:204–215,266–272`).

**Strengths**
- Product revision is checked separately from the skill digest (`19-10-PLAN.md:179–202`).
- Unresolved decisions and failed gates remain owner-visible rather than silently passing (`:224–233`).

**Concerns**
- **MEDIUM · NEW — Acceptance forbids committing the required late-fix pressure refresh.**  
  The late-fix branch requires replacing pressure results, superseding rows, refreshing the v1 comparison and updating `product_commit` (`19-10-PLAN.md:184–199`). Those files are included in the plan’s final evidence commit (`:245,301–302`). Task 2 acceptance nevertheless requires that commit to leave **all of `19-PRESSURE-TESTS.md` unchanged** (`:314`). The authorized replay branch cannot satisfy that check.

**Suggestions**
- Keep the no-change assertion for `ROADMAP.md`. Check specifically that the withdrawn isolation allegation was not added, rather than forbidding legitimate pressure-evidence updates.

**Risk Assessment: MEDIUM.** The provenance design is sound, but the late-fix branch has contradictory completion criteria.

## Cross-plan disposition audit

| Previously raised HIGH | Cycle-3 assessment |
|---|---|
| Stock dispatch ignores `executor:` | **Addressed by the accepted orchestration contract:** explicit orchestrator-only guards and a session dispatcher restricted to 19-01–04. Stock behavior remains as previously reported in `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:63–68`. I did not independently execute the session-owned dispatcher. |
| Delegated prompts omit interfaces | **Addressed:** whole-plan delivery and explicit full-plan-read requirements replace reliance on stock extraction. Stock extraction is still objective/tasks only (`elaboration.md:84–87`). |
| Digest checker and pressure layout disagree | **Addressed:** one table schema, required digest columns, exact scenario row sets and negative parser tests (`19-03-PLAN.md:327–350,462–478`). |
| Late product changes invalidate earlier evidence | **Addressed in replay obligations:** separate product provenance plus RED/GREEN/opus/smoke replay (`19-10-PLAN.md:179–202`). The new acceptance contradictions in 19-09/10 must not obstruct that replay. |

## Overall assessment

**Status: Changes requested. Coverage: 10/10 plans. Overall risk: HIGH.**

The revisions close most prior findings. The remaining actionable set is **3 HIGHs and 4 MEDIUMs**:

1. **OPEN HIGH:** effective v1 hook grading still ignores command-line overrides.
2. **NEW HIGH:** historical RED-b detection bypasses cache isolation and can rewrite real Cursor configuration.
3. **OPEN HIGH:** dirty/unverifiable timeout or signal reviews can still become waiver-compatible unavailable rows.
4. **NEW MEDIUMs:** ambient review-config dependency, missing PPID data, and the two contradictory late-fix acceptance assertions.

These require narrow contract/test corrections, not another framework or dependency.

**Not checked:** live AI CLIs, real home configuration/credentials, full project gates, or execution of the proposed helper. No files were modified; the working tree remains clean.  
**Residual risk:** headless Bash is still protected mainly by detective controls, not a filesystem sandbox.
