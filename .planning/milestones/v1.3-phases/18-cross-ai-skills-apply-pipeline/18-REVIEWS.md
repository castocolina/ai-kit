---
phase: 18
cycle: 3
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-15T19:54:00Z
plans_reviewed: [18-01-PLAN.md, 18-02-PLAN.md, 18-03-PLAN.md, 18-04-PLAN.md, 18-05-PLAN.md, 18-06-PLAN.md, 18-07-PLAN.md, 18-08-PLAN.md, 18-09-PLAN.md, 18-10-PLAN.md, 18-11-PLAN.md, 18-12-PLAN.md, 18-13-PLAN.md, 18-14-PLAN.md, 18-15-PLAN.md, 18-16-PLAN.md, 18-17-PLAN.md, 18-18-PLAN.md, 18-19-PLAN.md, 18-20-PLAN.md, 18-21-PLAN.md, 18-22-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 18 (convergence cycle 3, final)

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Cycle 3 reviews the plans as revised in 7427ea6, which folded in cycle 2's review (bd1938f)
and plan-checker findings. As in cycle 2, the prompt carried the first 80 lines of PROJECT.md,
the ROADMAP Phase 18 section, the Phase 18 requirement lines and the plan coverage manifest. It
pointed the reviewer at the 22 PLAN.md files, CONTEXT, SPEC, RESEARCH, PATTERNS, VALIDATION and
the cycle-2 REVIEWS.md on disk (about 560 KB of plans, not inlined), and asked for a resolution
verdict on each cycle-2 item. The reviewer read them from the repo. Lane runtime was about 6
minutes, and plan coverage was 22 of 22.

## OpenCode Review (opencode-plan-review)

# Phase 18 — Convergence Cycle 3 Review

**Document type:** GSD · implementation plans  
**Coverage:** 22/22 plans, phase context/specification/research/patterns/validation, and the full cycle-2 review. Reviewed the revisions in `7427ea6` against `bd1938f`, with source-grounding passes across selection, runner, editing, apply, and follow-ups.

**No repository files changed.** “Resolved” means the revised plan adequately specifies the correction—not that its future implementation has passed tests.

## 18-01

**Summary:** The shared groundwork remains adequately specified and compatible with downstream revisions.

**Strengths**
- Failed enumeration differs from a valid empty listing, with parser/wrapper/snapshot cases (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-01-PLAN.md:194–207,250–254`).
- Serialization failures are refused before dispatch; secret presence has an explicit non-disclosure contract (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-01-PLAN.md:285–309`).

**Concerns:** No new actionable issue. `load_secret` internally reads a value, so the operative guarantee remains non-exposure, not “never holding a key” (`skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py:11–25`).

**Suggestions:** Preserve the narrower non-disclosure wording.

**Risk Assessment:** **LOW** — explicit boundary cases; no Round 4 interface conflict found.

## 18-02

**Summary:** Inventory expansion remains source-grounded, with discovery degradation distinguished from malformed persisted input.

**Strengths**
- Registry and skills-root discovery use gsd-core’s APIs, with validation and degradation cases (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-02-PLAN.md:184–210,304–310`).
- This matches the actual registry merge and runtime-root mechanisms (`.claude/gsd-core/bin/lib/review-lane-descriptor.cjs:509–559`; `.claude/gsd-core/bin/lib/runtime-homes.cjs:491–519`).

**Concerns:** No new blocker. The opencode local-root inference remains explicitly unverified.

**Suggestions:** Retain that confidence label until live validation.

**Risk Assessment:** **LOW** — the existing recorded config identity supports the revised destination binding.

## 18-03

**Summary:** Filesystem discovery and backend detection have clear containment, output-hygiene, and confidence boundaries.

**Strengths**
- Global escape checks include resolved `SKILL.md`, matching gsd-core’s gate (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-03-PLAN.md:160–168`; `.claude/gsd-core/bin/lib/init.cjs:3691–3702`).
- DNS/connect waiting is bounded and URL credentials are not emitted (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-03-PLAN.md:178–185,294–299`).

**Concerns:** No new issue. Plugin layering remains an acknowledged assumption.

**Suggestions:** Keep the unverified-layering note in emitted inventory, not merely comments.

**Risk Assessment:** **MEDIUM** — external plugin semantics remain a validation dependency.

## 18-04

**Summary:** Execution selection produces artifacts compatible with Round 4’s stricter validator.

**Strengths**
- Preferred targets already partition into selected models or unresolved choices; router flags belong to selected models (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-04-PLAN.md:153–162`).
- Purity allowlist changes accompany the new import in Task 1 (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-04-PLAN.md:215–225`), matching the actual AST guard (`tests/test_curated_config_recommend.py:1720–1740`).

**Concerns:** No new contradiction found.

**Suggestions:** Preserve same-commit purity updates and golden regeneration.

**Risk Assessment:** **LOW**.

## 18-05

**Summary:** Execution-selection edges and interruption safety remain well covered.

**Strengths**
- Host exclusion, preference ordering, router priority, timeout boundaries, and the default matrix have explicit cases.
- The injected replacement failure proves preservation of old plan bytes and temporary-file cleanup (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-05-PLAN.md:158–169`), rather than substituting determinism for interruption evidence.

**Concerns:** No new actionable issue.

**Suggestions:** Keep the interruption test separate from pure-selection failures for clear diagnostics.

**Risk Assessment:** **LOW**.

## 18-06

**Summary:** Registry-driven review selection remains coherent and reuses existing ranking machinery.

**Strengths**
- Eligibility requires candidates on the lane binary marked non-host (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-06-PLAN.md:143–147`).
- Actual candidate construction defines `is_host` from runtime identity, preventing a different lane slug from bypassing exclusion (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:380–390`).
- Ranking and second-lane reselection are explicit (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-06-PLAN.md:150–168`).

**Concerns:** No new blocker. Opencode effort forwarding remains a disclosed live-validation risk.

**Suggestions:** Retain the generated effect warning until Phase 20 supplies evidence.

**Risk Assessment:** **MEDIUM** — external invocation compatibility, not an unresolved selection design.

## 18-07

**Summary:** The affinity layer retains a useful pure-policy/I/O split.

**Strengths**
- CLI-side affinity loading preserves recommendation purity.
- The existing I/O guard is narrowly extended to permit and assert that specific read (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-07-PLAN.md:199–218`; `tests/test_curated_config_recommend.py:1783–1819`).
- Caps, gates, missing-skill silence, and reference precedence have targeted tests.

**Concerns:** No new issue.

**Suggestions:** Preserve file-order policy rather than introducing another ranking mechanism.

**Risk Assessment:** **LOW**.

## 18-08

**Summary:** Round 4 correctly preserves existing trusted roots in their recorded form while restricting newly approved roots.

**Strengths**
- The merged approval list explicitly retains existing absolute entries; the added fixture tests that behavior (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-08-PLAN.md:147–155,204–211`).
- Escaping project copies cannot automatically outrank usable alternatives.

**Concerns**
- **LOW:** Broad wording such as “nothing absolute … leaks into the plan” is now imprecise because already-configured absolute roots are deliberately retained (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-08-PLAN.md:207,240`). This is documentation inconsistency, not a new trust grant.

**Suggestions:** Qualify the claim as “no newly proposed absolute roots or incidental scratch paths.”

**Risk Assessment:** **LOW**.

## 18-09

**Summary:** The accumulated runner harness has sound isolation and initial-argv coverage.

**Strengths**
- Per-case HOME and call logs prevent contamination.
- Hermetic PATH and runtime parser/argv cases replace useful prototype coverage (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-09-PLAN.md:163–207,279–301`).

**Concerns:** No new blocking issue in this plan. Retry-specific permissions are now addressed in 18-12.

**Suggestions:** Keep initial-argv coverage here and retry coverage downstream.

**Risk Assessment:** **LOW**.

## 18-10

**Summary:** The unified finalizer adequately closes cycle 2’s timeout-pipe safety gap.

**Strengths**
- Exit, timer, error, and signal paths share guarded bounded cleanup, stream destruction, listener removal, and group termination (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-10-PLAN.md:142–168`).
- Escaped-descendant and output-finalization cases exercise the actual hazard (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-10-PLAN.md:262–281`).
- This directly replaces the prototype’s stderr callbacks and `process.exitCode` termination (`.planning/scripts/cross-ai.mjs:289–310,476–478`).

**Concerns:** No remaining HIGH from the original finalization finding.

**Suggestions:** Preserve the requirement that callbacks are stopped before the final status is emitted.

**Risk Assessment:** **LOW at plan level**, subject to the downstream harness conflict below.

## 18-11

**Summary:** Bounded preflight is correctly designed, but its fake listing conflicts with an accumulated self-test.

**Strengths**
- Listing uses the lifecycle deadline and the shared child supervisor (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-11-PLAN.md:109–119`).
- Hanging-listing and no-preflight-under-print cases are explicit.

**Concerns**
- **HIGH — Preflight rejects the existing parser-error fixture.** The fake Cursor listing contains only `fake-ok-cursor` (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-11-PLAN.md:55–59`). The preceding plan requires `fake-err-cursor` to run and finish as `auth` (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-10-PLAN.md:62–64,221`). Under the new preflight rule, that model instead finishes as `bad_model` without exercising the parser. The mandatory full self-test therefore fails (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-11-PLAN.md:117–119,158–164`).

**Suggestions**
- Include `fake-err-cursor` in the normal fake listing in Task 1.
- Preserve the deliberately empty listing variant; do not weaken the parser-error expectation.

**Risk Assessment:** **HIGH until this small fixture correction lands** — a deterministic verification contradiction, not a demonstrated production safety defect.

## 18-12

**Summary:** Fresh review retries now preserve preventive restrictions; shutdown-output testing also strengthens finalizer evidence.

**Strengths**
- Every review retry uses fresh review argv and the original prompt, never resume (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-12-PLAN.md:129–135,174–181`).
- Codex and Cursor retry argv are explicitly checked (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-12-PLAN.md:171`).

**Concerns**
- **MEDIUM — The no-preamble fixture needs an explicit mode.** `echo-len` only prints stdin length and makes no edit, but its behavior does not select review mode (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-12-PLAN.md:147–149,170`). Default exec mode classifies an unchanged tree as `no_change`; the prototype only publishes parsed answer text on success (`.planning/scripts/cross-ai.mjs:397–398`).

**Suggestions:** Run both length-comparison cases explicitly with `--mode review`.

**Risk Assessment:** **MEDIUM** — requested safety fixes are adequate; one fixture invocation remains ambiguous.

## 18-13

**Summary:** Renderer edit protection remains adequate within its disclosed concurrency limit.

**Strengths**
- Expected-byte rechecks, performed-operation reporting, and intervening-edit tests cover the identified race window (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-13-PLAN.md:140–159,212–224`).
- Atomic publication follows the shared writer pattern (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:27–46`).

**Concerns:** No new actionable finding. The recheck-to-replace window is correctly disclosed as not an atomic compare-and-swap.

**Suggestions:** Retain that limitation; no new locking design is required here.

**Risk Assessment:** **LOW within the stated concurrency limit**.

## 18-14

**Summary:** Round 4 closes exact target coverage and effective-keep validation without breaking native-default display.

**Strengths**
- Every preferred target has exactly one nonempty model or open choice; router IDs are constrained to selected models (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-14-PLAN.md:175–183`).
- Non-null-existing keeps must match their recorded existing value, with a justified native-default exception (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-14-PLAN.md:161–164`).
- Existing native-slot production supports that exception (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:207–212,250–264`).

**Concerns:** No new blocking contradiction.

**Suggestions:** Keep schema consistency distinct from live-state validation.

**Risk Assessment:** **LOW–MEDIUM** — substantial boundary logic, backed by concrete negative cases.

## 18-15

**Summary:** The Task 1 ordering failure is fully repaired without prematurely expanding CLI scope.

**Strengths**
- Task 1 explicitly tests pseudo-key unset through `plan_edit.plan_unset`; Task 2 owns CLI dispatch and its equivalence test (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-15-PLAN.md:174–183,208–221`).
- Effective keeps now use `existing`, not a displayed default (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-15-PLAN.md:145–156`).

**Concerns:** No new task-order or files-list contradiction found.

**Suggestions:** Keep the later CLI assertion comparing the complete resulting plan.

**Risk Assessment:** **LOW–MEDIUM**.

## 18-16

**Summary:** Recovery now distinguishes recorded operation and progress instead of prescribing universal snapshot restoration.

**Strengths**
- Branches cover committed, corrupt, vanished, backup-not-taken, absent-config, runner-add, runner-change, and no-runner states (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-16-PLAN.md:135–161`).
- Branch-specific tests assert required and forbidden recovery instructions.

**Concerns:** No independent new blocker. The combined commit-record failure discussed under 18-18 affects which branch remains durable.

**Suggestions:** Preserve the separation between message-unit tests here and apply failure-injection tests downstream.

**Risk Assessment:** **MEDIUM** — filesystem recovery remains sensitive despite improved state representation.

## 18-17

**Summary:** The node-call assertion now matches source, and destination binding is explicit.

**Strengths**
- Realpath identity checks prevent applying an inventory/plan pair to another destination (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-17-PLAN.md:146–155`).
- The tracer correctly permits `config-path` plus the tables query and prohibits write calls (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-17-PLAN.md:195–196`).

**Concerns**
- **MEDIUM — Golden fixture rebinding is underspecified.** The tracer combines a new scratch project with a golden inventory and expects successful destination binding (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-17-PLAN.md:195`). The actual golden helper replaces its temporary root with literal `<scratch>` before returning (`tests/test_curated_config_golden.py:132–142`). Used literally, that inventory fails binding.

**Suggestions:** Explicitly rebase the inventory’s destination and relevant scratch paths **before recommend and digest generation**, or build it directly for the tracer project with `FakeRun`.

**Risk Assessment:** **MEDIUM** until fixture construction is explicit.

## 18-18

**Summary:** The original rollback-assets safety defect is resolved: cleanup cannot roll back after destroying restoration assets.

**Strengths**
- The commit point separates rollback from warning-only cleanup.
- Failed commit recording retains restoration assets; ordinary discard/prune/clear failures cannot invoke rollback (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-18-PLAN.md:111–121,231–244`).

**Concerns**
- **MEDIUM — Recovery reporting disagrees after combined failures.** If recording `committed=True` and clearing the marker both fail, the invocation says “committed; … do not restore,” but the surviving uncommitted marker subsequently directs consistent pre-apply restoration (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-18-PLAN.md:117–121`; `.planning/phases/18-cross-ai-skills-apply-pipeline/18-16-PLAN.md:150–159`). Assets remain available, so this is not the previous HIGH data-recovery defect.

**Suggestions:** Specify one consistent operator instruction for that state and test both failures together, followed by another apply attempt.

**Risk Assessment:** **MEDIUM** — safe assets are retained, but terminal-state communication needs tightening.

## 18-19

**Summary:** The transaction evidence now covers genuinely fresh projects and meaningful re-apply behavior.

**Strengths**
- Absent-config backup creates no backup file, allowing fresh rollback to remove newly created directories (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-19-PLAN.md:129–132`; `.planning/phases/18-cross-ai-skills-apply-pipeline/18-16-PLAN.md:120–122`).
- Cleanup edge tests stay in the cheaper unit tier.

**Concerns**
- **MEDIUM:** The commit-record case assumes marker removal succeeds, missing the combined failure and subsequent recovery-message discrepancy (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-19-PLAN.md:132`).

**Suggestions:** Extend `TestCommitPointEdges`; permit corrections in `_cleanup_committed`, not only `_rollback`.

**Risk Assessment:** **MEDIUM** — terminal-state evidence remains incomplete, not ordinary write-failure restoration.

## 18-20

**Summary:** Follow-ups now bind to the correct destination, but the empty-block test contradicts that mandatory read.

**Strengths**
- `_cmd_followups` reuses `apply.resolve_target`, with A→B refusal cases covering approved and unapproved paths (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-20-PLAN.md:337–345`).

**Concerns**
- **HIGH — Empty-block verification rejects correct destination binding.** The empty-block case requires “no subprocess call” (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-20-PLAN.md:331`), while every invocation must perform destination resolution (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-20-PLAN.md:342–344`). The shared `config_path` implementation necessarily invokes node (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:243–251`).

**Suggestions:** Require **no follow-up execution**, permitting read-only `config-path`; prohibit installer, effort-apply, and unnecessary preview calls explicitly.

**Risk Assessment:** **HIGH until the assertion is corrected** — the new safety mechanism otherwise fails its own prescribed test.

## 18-21

**Summary:** Documentation remains operationally useful, especially around inactive `.new` output and scoped validation claims.

**Strengths**
- `.new` is not presented as active, and `--print-argv` is not presented as live model access.
- Judge evidence remains tied to the committed skill blob.

**Concerns**
- **MEDIUM:** The leftover-marker explanation assumes committed-state recording succeeded, which is not true in the combined failure above (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-21-PLAN.md:144–146`).

**Suggestions:** Align recovery documentation with the final combined-failure semantics.

**Risk Assessment:** **MEDIUM** — misleading operator recovery guidance, not missing ordinary usage documentation.

## 18-22

**Summary:** Final verification, success criteria, and supply-chain rules now distinguish passed gates from network-blocked Docker verification.

**Strengths**
- The container-only provisioning exception and explicit blocked outcome match actual Docker behavior (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-22-PLAN.md:76–80,286,289–299`; `Makefile:133–138`).

**Concerns**
- **LOW:** Task 1’s `<done>` still says “Every gate is green,” despite accepting a recorded Docker network block (`.planning/phases/18-cross-ai-skills-apply-pipeline/18-22-PLAN.md:166–171`).

**Suggestions:** Use “required host gates green; Docker passed or explicitly network-blocked.” Carry the final recovery wording into the planned amendments.

**Risk Assessment:** **LOW for this plan itself**, dependent on upstream corrections.

## Cycle-2 Resolution Matrix

All citations below point to operative plan text **outside the disposition ledgers**.

| Cycle-2 item | Resolution | Evidence and mechanism |
|---|---|---|
| **HIGH 1: timeout pipes and terminal output** | **FULLY** | One bounded finalizer covers every child end path, destroys streams, stops callbacks, and settles once; shutdown-output tests require final status last. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-10-PLAN.md:142–168,270–281`; `.planning/phases/18-cross-ai-skills-apply-pipeline/18-12-PLAN.md:151–154,212`. |
| **HIGH 2: Task 1 pseudo-key unset versus placeholder** | **FULLY** | Task 1 explicitly uses the pure editor; Task 2 removes the CLI placeholder and adds CLI equivalence coverage. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-15-PLAN.md:174–183,208–221`. |
| **HIGH 3: unsafe apply cleanup boundary** | **FULLY, with a MEDIUM residual** | No post-commit operation invokes rollback; failed commit recording preserves assets rather than deleting them. The remaining combined-failure concern is contradictory recovery reporting, not the original loss of rollback assets. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-18-PLAN.md:111–121,231–244`. |
| **(a): exact preferred-target coverage** | **FULLY** | Exact model-or-choice partition, nonempty model strings, and router IDs constrained to models. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-14-PLAN.md:175–183,279–280`. |
| **(b): misleading effective keep values** | **FULLY, with justified deviation** | Non-null-existing keeps require equality; native-default displays remain supported. Crucially, execution invariants use `existing` for all keeps, so the exception cannot manufacture a command dependency. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-14-PLAN.md:161–164`; `.planning/phases/18-cross-ai-skills-apply-pipeline/18-15-PLAN.md:145–156`. |
| **(c): review retries lose read-only argv** | **FULLY** | Review retries always use fresh review argv and original input; actual retry argv is checked. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-12-PLAN.md:129–135,171,174–181`. |
| **(d): recovery ignores runner operation/progress** | **FULLY** | Recovery branches on backup progress, original config existence, runner add/change/none, and committed state. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-16-PLAN.md:144–161,235–243`. |
| **(e): impossible dry-run node-call assertion** | **FULLY** | The assertion now permits exactly destination resolution plus tables query, with no writes. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-17-PLAN.md:195–196`. |
| **(f): follow-up destination binding** | **FULLY** | Shared resolution precedes block construction/execution; mismatched destinations are tested. The conflicting empty-block assertion is a separate new regression. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-20-PLAN.md:228–235,337–345`. |
| **(g): Docker/gate completion inconsistency** | **FULLY for the requested operative statements** | Final verification, success criteria, and threat disposition allow explicitly blocked Docker networking without calling it passed. One subordinate `<done>` sentence remains LOW. `.planning/phases/18-cross-ai-skills-apply-pipeline/18-22-PLAN.md:286,289–299`. |

## Overall Assessment

### Status: Issues Found — two narrow verification corrections required before execution

The three previous HIGH safety/order findings are resolved at plan level. No redesign is needed.

**Required before execution:**
1. **18-11:** Add `fake-err-cursor` to the normal fake model listing so the accumulated structured-error test still runs.
2. **18-20:** Replace “no subprocess call” with a read-only allowlist/no-follow-up-execution assertion.

The first is a newly discovered accumulated-harness inconsistency; the second is introduced by Round 4’s destination-binding correction. Both qualify as HIGH because a correct implementation fails the specified verification.

Also clarify the MEDIUM items: combined commit-record/marker-clear reporting, the no-preamble test’s review mode, and golden-inventory rebinding before digest generation.

**Overall risk: HIGH for execution readiness until those two test contradictions are corrected; MEDIUM afterward**, principally from recovery-state communication and the breadth of unimplemented runner/apply behavior.

Skipped implementation, test suites, installers, and live model calls; this was read-only plan/source review. Future runtime correctness remains unverified.

---

## Consensus Summary

One reviewer ran (`opencode-plan-review`, opencode adapter, pinned model
`router-env/my-plan-review`), so there is no cross-reviewer consensus. The review is
source-grounded, with `file:line` citations into the plans, the prototype
`.planning/scripts/cross-ai.mjs`, the curated-config and ai_kit_spec modules, the tests and the
checkout-local gsd-core. Coverage is 22 of 22. The orchestrator checked every concern below
against the PLAN.md text and, where a concern cites source, against that source.

Reviewer verdict: overall risk HIGH for execution readiness until two test-contradiction fixes
land, MEDIUM afterwards. All three cycle-2 HIGHs and all seven cycle-2 items (a) to (g) are
resolved at plan level, and no redesign is needed.

### Agreed Strengths

Single reviewer, so none are "agreed". Its main strengths: the Round 4 fixes live in the plan
bodies, not only in the ledgers. These include 18-10's single `finalize` with `process.exit`
after a flush, 18-12's `retryArgv` (review retries never resume), 18-14's prefer-coverage and
keep-equality validator rules, 18-16's branching `recovery_text`, 18-18's commit point and
`_cleanup_committed`, and 18-20's reuse of `resolve_target`.

### Agreed Concerns

None (single reviewer). Orchestrator triage follows.

**Cycle-2 status (reviewer, confirmed by the orchestrator against the plan bodies outside the
ledgers):**
- HIGH 1, 18-10 timeout finalization: fully resolved (`18-10-PLAN.md:142-168`,
  `18-12-PLAN.md:151-154,212`).
- HIGH 2, 18-15 Task 1 vs the placeholder: fully resolved (`18-15-PLAN.md:174-183,208`).
- HIGH 3, 18-18 commit boundary: fully resolved (`18-18-PLAN.md:111-121,236-240,286-288`). The
  remaining double-failure wording issue is item (e) below.
- Items (a) to (g): all fully resolved (18-14 `:161,175-183`; 18-15 `:145-156`; 18-12
  `:129-135,171`; 18-16 `:144-161`; 18-17 `:196`; 18-20 `:228-235`; 18-22 `:166,291,298`).
  Item (b)'s narrowing to keeps with a non-null `existing` holds up against the source:
  `recommend.py:207-212,250-264` emits native-slot keeps with `existing` None and the gsd
  default as `value`.

**HIGH, verified and still open (2):**

1. **18-11 preflight breaks the accumulated self-test** (existence-class, confirmed and wider
   than the reviewer said). In 18-11, preflight turns "listing ok, model absent" into
   `bad_model` without spawning (`18-11-PLAN.md:117-119`). Task 1's verify runs the full
   `--self-test`, which still holds every earlier case (`18-11-PLAN.md:159-164`). Two of
   those cases break:
   - The fake `cursor-agent` listing names only `fake-ok-cursor` (`18-11-PLAN.md:57-59`), so
     18-10's `cursor-error` case (`fake-err-cursor` -> 69 `status=auth`,
     `18-10-PLAN.md:62-64,221`) ends `bad_model` and never reaches the parser.
   - The fake `opencode` gets no `models` answer at all. Called as `opencode models`, it
     prints its three JSON event lines and exits 0 (`18-09-PLAN.md:200-205`). The
     one-id-per-line parser (`18-11-PLAN.md:51`) reads those lines as ids, so the listing is ok
     but `fake/ok` is missing, and 18-09's opencode parser case (`18-09-PLAN.md:284`) fails.
     The listing call also appends to `a.txt` before the run.
   The pi fake is fine, because it lists every `FAKE_MODES` key (`18-09-PLAN.md:194-198`).
   Fix: 18-11 Task 1's fake `cursor-agent models` lists every fake cursor model
   (`fake-ok-cursor`, `fake-err-cursor`). The fake `opencode` answers `models` with its fake
   ids (`fake/ok`) and makes no edit. The fake `codex` either answers `debug models` with a
   `slug`/`visibility: list` entry, or the plan states that its unparseable answer leads to
   the `model list unavailable` note.
2. **18-20 R14 empty case contradicts the new destination binding** (existence-class,
   confirmed). The R14 empty case requires that `followups --approve` "makes no subprocess
   call" (`18-20-PLAN.md:331`). But the same task makes `_cmd_followups` call
   `apply.resolve_target`, and it gives every followups CLI case a FakeRun that answers
   `config-path` (`18-20-PLAN.md:228-235,342-344`). `config_path` always spawns node
   (`skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:243-256`), and Task 3 says "never
   loosen a case". A correct implementation therefore fails the case. Fix: the case asserts
   that the recorded calls are exactly the `config-path` binding call, with no `npx`, no
   `effort sync` and no `--dry-run`. This matches the A-in-B case's wording at
   `18-20-PLAN.md:337`.

**MEDIUM/LOW, actionable (not yet in any PLAN.md):**
- (a) 18-12 M: the `--no-preamble` case with `fake/echo-len` names no mode
  (`18-12-PLAN.md:170`). The default is exec (`.planning/scripts/cross-ai.mjs:26`).
  `echo-len` makes no edit, so exec ends `no_change` and prints no answer
  (`cross-ai.mjs:397`, 18-10 exit classes), and there is no "printed length" to compare. Fix:
  run both length cases with `--mode review`.
- (b) 18-17 M: `TestDryRunTracer` builds its plan from the golden claude standard inventory
  (`18-17-PLAN.md:195`). `build_golden_inventory` replaces its deleted temp root with the
  literal `<scratch>` (`tests/test_curated_config_golden.py:138`), so `existing_config.path`
  is neither the tracer project's config nor absolute, and `resolve_target` refuses it
  (`18-17-PLAN.md:31,146-152`). Fix: build the tracer's inventory for its own scratch project
  with `FakeRun` (as `build_golden_inventory` does, without the `<scratch>` masking), before
  recommend and the digest.
- (c) 18-18/18-19/18-21 L (the reviewer rated it MEDIUM; downgraded because both instructions
  lead to a consistent state and the snapshot and backup are kept): when recording `committed`
  fails, the warning says "do not restore the backup" (`18-18-PLAN.md:117-121`). If
  `clear_marker` then also fails, the next apply refuses with `recovery_text`'s uncommitted
  branch, which says to restore (`18-16-PLAN.md:153-159`). 18-21's SKILL.md wording ("never
  restore its backup", `18-21-PLAN.md:144-146`) matches only the first of the two. And when
  `clear_marker` succeeds, the snapshot (never discarded) is left on disk unnamed. Fix: make
  the warning name the snapshot and tell the user to follow the next apply's recovery steps.
  Add the double-failure case to 18-19's `TestCommitPointEdges`, and align 18-21's sentence.
- (d) 18-08 L: Task 2 `<done>` says "nothing absolute ... leaks into the plan"
  (`18-08-PLAN.md:240`), but the same task's case keeps an absolute existing root verbatim in
  `existing` and in the merged list (`18-08-PLAN.md:207`). Fix: "no newly proposed absolute
  root".
- (e) 18-22 L: Task 1 `<done>` still says "Every gate is green over the whole phase"
  (`18-22-PLAN.md:171`), but its acceptance criteria accept `e2e-docker: blocked (network)`
  (`18-22-PLAN.md:166`). This is the one remaining line from cycle-2 item (g). Fix: "required
  host gates green; e2e-docker passed or explicitly blocked (network)".

**Not actionable (verified as covered or as accepted design):**
- 18-01 L "never holding a key" wording: classified as cosmetic in cycle 2, and the reviewer
  raises nothing new.
- 18-02 (opencode local root), 18-03 (plugin layering) and 18-06 (opencode effort
  forwarding): each is already disclosed as unverified, and the reviewer's suggestion is to
  keep the disclosure.
- 18-13 residual race: disclosed as a `shortcut:`, and the reviewer agrees.

### Divergent Views

None (single reviewer).

## Verification coverage

Source-grounding pass (`plan_review.source_grounding` true, authority `grep`):

- Method: the same classifier as cycles 1 and 2 was run over each plan body, excluding the
  Review Dispositions Ledger. 858 symbol and path references were checked against the repo
  (`skills/`, `tools/`, `tests/`, `Makefile`, config files and the checkout-local
  `.claude/gsd-core/`), up from 841 because of the Round 4 additions. 3,163 tokens were
  skipped as non-symbols.
- MISSING after cross-plan resolution: 0 hallucinated references to existing code. Tokens new
  since cycle 2 were all resolved. `RESUME_MSG` exists (`.planning/scripts/cross-ai.mjs:73`;
  the classifier does not index `.planning/`). `cache_write_bytes` is created by 18-13
  (`18-13-PLAN.md:124-126`, which creates the parent dir), so 18-18's "creates it" claim holds.
  `recovery_text`, `TestRecoveryText` and `update_marker` come from 18-16. `created_dirs` and
  `skill_check` come from 18-18, `discard_snapshot` and `prune_backups` from 18-16, and
  `apply.resolve_target` from 18-17. Every producer runs in an earlier wave (waves 1 to 22 are
  strictly serial).
- Every Round 4 ledger claim was spot-checked in the plan bodies, not just in the ledger:
  `finalize`/`finished`/`process.exit(code)`/`gcescape` (18-10), `retryArgv`/`argv-retry`/
  `gc-late` (18-12), the coverage and keep rules plus the recorded-form roots (18-14), the
  direct `plan_edit.plan_unset` call in Task 1 with cli.py only in Task 2 (18-15),
  `recovery_text`/`committed`/`makedirs` (18-16), the two-node-call assertion (18-17),
  `_cleanup_committed` and the commit-point fault cases (18-18), `resolve_target` in
  `_cmd_followups` (18-20), and the "passed or explicitly blocked" rule (18-22).
- Reviewer citations spot-checked and confirmed: `catalog_adapter.py:380-390` (`is_host`),
  `review-lane-descriptor.cjs:509-559`, `runtime-homes.cjs:491-519`, `init.cjs:3691-3702`,
  `tests/test_curated_config_recommend.py:1720-1740,1783-1819`,
  `tests/test_curated_config_golden.py:132-142`, `gsd_tools.py:243-251`,
  `recommend.py:207-212,250-264`, `.planning/scripts/cross-ai.mjs:289-310,397,476-478`, and
  `Makefile:133-138`.
- UNCHECKABLE: the runtime behavior of not-yet-written modules and live external CLI behavior
  (pi RPC, `opencode models`, `cursor-agent models`, `codex debug models`). None were run.

Cross-artifact fact-drift pass:

- Phase status: `drift-guard phase-status --phase 18` returned `uncheckable`
  (`phase_not_in_roadmap`; STATE.md says "Ready to execute"). Recorded, not read as consistent.
- Requirement IDs: the union of the 22 plans' `requirements` is APP-01 to APP-04, EVAL-06,
  SKL-01 to SKL-04, SPEC-05, XAI-01 and XAI-02, the same 12 IDs ROADMAP lists. No
  contradiction.
- CONTEXT.md glossary vs PLAN usage: not compared term by term (size). Partial coverage.
