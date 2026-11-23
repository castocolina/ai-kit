---
phase: 36
cycle: 1
reviewers: [referee-one]
reviewed_at: 2026-11-20T21:06:40-03:00
plans_reviewed: [36-01-PLAN.md, 36-02-PLAN.md, 36-03-PLAN.md, 36-04-PLAN.md, 36-05-PLAN.md, 36-06-PLAN.md, 36-07-PLAN.md, 36-08-PLAN.md, 36-09-PLAN.md, 36-10-PLAN.md, 36-11-PLAN.md, 36-12-PLAN.md, 36-13-PLAN.md, 36-14-PLAN.md, 36-15-PLAN.md, 36-16-PLAN.md, 36-17-PLAN.md, 36-18-PLAN.md, 36-19-PLAN.md, 36-20-PLAN.md, 36-21-PLAN.md, 36-22-PLAN.md, 36-23-PLAN.md, 36-24-PLAN.md, 36-25-PLAN.md, 36-26-PLAN.md, 36-27-PLAN.md, 36-28-PLAN.md, 36-29-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
model_sources:
  referee-one: "pinned"
---

# Cross-AI Plan Review — Phase 36

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Note: one reviewer lane only (referee-one, owner instruction 2026-11-20); its findings are single-reviewer.

## Cycle 1 (referee-one)

### Review conditions (cycle 1)

One reviewer lane (referee-one, owner instruction 2026-11-20; lane probe at 20:07 answered READY). Seven batches, one per planning agent (A: 36-03 36-04 36-10 36-22; B: 36-06 36-07 36-09 36-13; C: 36-05 36-18 36-21; D: 36-11 36-17 36-20 36-23; E: 36-08 36-12 36-14 36-15; F: 36-01 36-02 36-16 36-19 36-29; G: 36-24 to 36-28), each reviewed as first written (batches reviewed 20:49 to 21:03; plans 36-27 and 36-28 did not exist yet when batch F ran). The plan-checker (sonnet) passed all 29 plans with no blocker or warning at 21:05. Dispositions of the findings are in the orchestrator triage (ledger `[plan-36]` lines): real findings were fixed in the plans by their authors; rejected with reason: same-wave verification interference (the orchestrator integrates waves in order), no timing evidence for the 1800 s cap (recorded risk), scratch cleanup, a dispatch-time model-list check (SPEC R4 refuses at write), SUMMARY creation outside the executor payload (the orchestrator writes each SUMMARY after the lane run).

### referee-one

#### Batch A (36-03, 36-04, 36-10, 36-22)

#### 36-03

**Summary:** The plan provides the required read-only status command and covers the principal trust, layer and malformed-file cases. Its proposed status calculation does not, however, cover all states it claims to report, and the executor is instructed not to change those rules.

##### Strengths

- Reuses the project trust digest and trust store rather than inventing a separate trust decision: `.planning/phases/36-spec-config-as-the-hub/36-03-PLAN.md:127-132`; the existing trust inputs are in `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:445-463`.
- Tests exercise the real CLI and include a whole-tree no-write comparison: `36-03-PLAN.md:158-173`.

##### Concerns

- **HIGH — An old roster can be missed when the same layer already has lanes.** Both `_project_status` and `_user_status` return `lanes` before checking the old roster (`36-03-PLAN.md:128-130`), despite the plan saying an old roster in either layer makes the result `pending` (`36-03-PLAN.md:24`). Such a state can arise after publication but before old-file retirement; the existing migration has a `completed` recovery path (`skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py:300-304`). Add project and user fixtures for this state and define how `config-status` reports it without writing.
- **HIGH — Local-only is not honored when the project’s old roster is pending.** The proposed skip applies only when project status is `lanes` or `empty` (`36-03-PLAN.md:131`); an empty local-only project with an old roster becomes `pending-migration`, causing the user layer to be read. That conflicts with the actual resolver’s local-only boundary (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:682-691`) and can turn an irrelevant malformed user file into an error. Test this combination and derive the skip from the project strategy independently of its pending status.
- **MEDIUM — Task 1’s test gate can prevent reaching the authorized fixes.** It runs existing `test_config_layers` only in Task 2, but the plan restricts Task 2 code changes to deviations from Task 1’s rules (`36-03-PLAN.md:170-177`). The two missing combinations above therefore cannot be repaired by the executor without departing from the plan.

##### Suggestions

- Specify precedence and checked-line statuses for an active new roster beside a pending old roster, and for local-only plus a pending project migration.
- Include those combinations in the no-write tests, including a malformed user file that must not be read under local-only.

**Risk assessment: HIGH** — incorrect status can bypass a migration decision or cause a read outside the selected layer.

##### Ponytail findings

- **LOW — Needed and appropriately factored.** R1 requires the command, and the plan reuses `cfg_project_trust_bytes`, `cfg_lanes_table` and the existing CLI factory. No same-wave file overlap is listed with 36-04, 36-05 or 36-06. The new module and tests are justified; the missing state combinations are completeness issues, not a request for more abstraction.

---

#### 36-04

**Summary:** The role-order helper and legacy split address the required file shape, but the actual review selection still uses a flat, key-deduplicated roster. The planned tests do not exercise the critical case where both roles use the same key for different lanes.

##### Strengths

- Preserves the existing shallow, per-role policy layering (`36-04-PLAN.md:135-140`), matching `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:630-644`.
- Provides explicit tests for legacy order, duplicate order keys, dangling keys and project-over-user policy (`36-04-PLAN.md:165-181`).

##### Concerns

- **HIGH — A review can select the wrong role’s lane when keys collide across layers.** The plan changes the ladder but keeps `config["reviewers"]` and the purpose filter in `quota.resolve_reviewers` (`36-04-PLAN.md:140-141`). The existing flat roster is merged by key across layers (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:630-642`), and `resolve_ladder_pick` finds its entry by key in that flat roster (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:34-38,86-92,168-172`). Thus, for example, a project execute lane can override a user review lane with the same key in the flat view even though the separately merged `review` list still contains the review lane. The test at `36-04-PLAN.md:172` checks `ordered_lanes` alone, not actual review dispatch.
- **HIGH — The plan exceeds the stated cross-AI execution envelope.** It lists eight modified files (`36-04-PLAN.md:7-15`) and prescribes a new module, consumer changes and 15 tests (`36-04-PLAN.md:132-142,179-186`). That exceeds the review’s approximately five-file threshold for a single unattended 1,800-second plan, with hooks included. Split the work at a buildable boundary or provide measured evidence it fits.
- **MEDIUM — Task 1 can fail before Task 2 is allowed to adjust existing expectations.** Task 1 already runs `test_config_layers` and `test_ai_kit_spec` (`36-04-PLAN.md:144-146`), while the only permission to update their legacy-warning or selection assertions appears in Task 2 (`36-04-PLAN.md:183`). Move the permitted assertion updates before the first gate or make the tracer independent of those changed expectations.

##### Suggestions

- Resolve review candidates from the merged **review** list, not the flat list, and exercise actual selection with the same key assigned different models in both roles and layers.
- Split or time-box the implementation and tests while retaining a green, buildable checkpoint.

**Risk assessment: HIGH** — the central role-isolation guarantee is not established on the real selection path.

##### Ponytail findings

- **MEDIUM — Required functionality, but the flat-view compatibility path is incomplete.** `cfg_lanes_view` already preserves separate role lists (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:400-417`); reuse the review list at the consumer instead of adding another identity layer. No same-wave file overlap is listed with 36-03, 36-05 or 36-06.

---

#### 36-10

**Summary:** The plan implements the locked delete-by-default decision and retains an explicit backup opt-in. Its destructive path has a time-of-check/time-of-use gap, and one prescribed test edit does not affect the environment actually used by the CLI.

##### Strengths

- Reuses the existing migration value check, atomic publication and recovery states (`36-10-PLAN.md:118-123`; `skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py:290-310,363-390`).
- Includes failed-delete retry and failed-value-check cases (`36-10-PLAN.md:145-154`).

##### Concerns

- **HIGH — The guard does not guarantee the file deleted is the snapshot checked.** `_retire_guard` reads the old path and `_delete_old` subsequently calls `os.remove(old)` (`36-10-PLAN.md:120`). Another writer can replace or modify the path between those operations; the new bytes are then irrecoverably deleted, contrary to the plan’s concurrency claim (`36-10-PLAN.md:30`). The existing rename path has the same check/use gap (`skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py:343-354`), but deletion removes the recovery copy. Specify and test a safe coordination or retirement protocol, including a mutation immediately after the guard; do not claim an atomic guarantee from two separate calls.
- **MEDIUM — The test environment patch is incomplete.** `TestTrustLocalRevokeLegacy` invokes `cli.main` using `os.environ` (`tests/test_config_layers.py:445-460`), while the plan instructs adding the backup variable only to `self.env` (`36-10-PLAN.md:184`). `_LayerCase.setUp` has already copied that dictionary into `os.environ` (`tests/test_config_layers.py:46-53`), so later mutation of `self.env` does not update the process environment. Explicitly patch the environment used by the call, or inject the same environment into the CLI.
- **MEDIUM — Plan size exceeds the stated executor envelope.** Six files and three tasks are specified (`36-10-PLAN.md:7-13,20-22`), including migration, CLI wiring and several test suites. Split at a green boundary or provide a measured run under the 1,800-second cap.
- **LOW — Confirmation status is stale.** The objective and threat register say owner confirmation remains open (`36-10-PLAN.md:61,216`), whereas the review instructions state the owner accepted the decision. Update the wording so the executor and summary do not report conflicting status.

##### Suggestions

- Add a deterministic interleaving test at the boundary between snapshot verification and retirement, and define how a changed source remains recoverable.
- Make the backup test’s environment explicit for both direct reader and CLI calls.

**Risk assessment: HIGH** — an untested race can destroy the only copy of a concurrent edit.

##### Ponytail findings

- **LOW — The change is required, and the existing migration machinery is the right reuse point.** The extra backup flag is locked behavior, not speculative flexibility. No same-wave file overlap is listed with 36-07, 36-08 or 36-09.

---

#### 36-22

**Summary:** The plan uses one helper for the command and the write-risk display, which is a useful consistency measure. However, it chooses keys by role while routing and probing still resolve those keys through a flat roster, so the actual lane probed can differ from the requested role.

##### Strengths

- Keeps the review default and makes the broader check-only probe explicit (`36-22-PLAN.md:111-119,142-149`).
- Tests the documented write-risk snippet rather than checking text alone (`36-22-PLAN.md:142-149`), building on `tests/test_ai_kit_spec_check_providers.py:424-452`.

##### Concerns

- **HIGH — `--role execute` can probe the review lane with the same key.** The plan’s own fixture assigns `both1` different review and execute models (`36-22-PLAN.md:120`), but `_route_reviewers` routes the flat `reviewers` view (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:807-814`), and `refresh_quota_cache` also retrieves the entry from that flat view (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:287-303`). The flat view retains the review entry for a shared key (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:400-412`). The test records only `spec.key`, so it passes while the wrong model or command is called. The check-only display can likewise describe the wrong command to the owner. Preserve the locked one-probe-per-key rule only where the two role entries actually identify the same lane; specify safe handling for conflicting entries and test model, command and consent display, not just keys.
- **MEDIUM — Same-wave dependency is contradictory.** 36-22 and 36-24 are both wave 8, but 36-24 explicitly depends on 36-22 (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:5-6`). A scheduler that starts a wave in parallel cannot guarantee that dependency. Move 36-24 to a later wave or otherwise serialize it. Their listed edited files do not overlap.
- **MEDIUM — The claimed quota-spend cap is too broad.** The one-hour TTL applies to entries already present in the particular cache passed to `refresh_quota_cache` (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:287-299`). Check-only deliberately uses a throwaway quota path (`skills/ai-kit-spec-config/references/check-only.md:47-57`), so repeated check-only runs can each spend another probe. The unconditional cap stated in `36-22-PLAN.md:25,178` should be qualified, and the warning should make repeated-run spend clear.

##### Suggestions

- Test distinct commands and models under the same key across roles, including the exact lane shown in the risk prompt and passed to the fake probe.
- Correct the wave ordering and describe the TTL as cache-specific.

**Risk assessment: HIGH** — the command can invoke a different lane from the one requested and presented for consent.

##### Ponytail findings

- **MEDIUM — Role-aware probing is required, but changing only the key list does not reach the lookup.** Reuse the role lists already returned by `cfg_combine` and the existing probe machinery; ensure routing, display and invocation use the same resolved lane. No additional same-wave file overlap is listed with 36-23 or 36-24.

---

##### Overall status

**Issues found — revise before execution.** The most consequential cross-plan issue is that role-specific orders coexist with a flat, key-deduplicated lookup; both review selection and probing need end-to-end tests with colliding keys and different lane identities.

This was a read-only review. No test suite or make target was run, and no scratch files were created. The review did not exhaustively verify every phase-wide edge, prohibition, named path or command outside these four plans; no claim of complete phase coverage is made.

#### Batch B (36-06, 36-07, 36-09, 36-13)

#### 36-06

##### Summary

The pool split is needed for HUB-07 and gives downstream plans a clear, testable interface. The main implementation risk is that its stated handling of malformed catalog input is incomplete; the planned validation can still raise instead of treating a bad fact as unknown.

##### Strengths

- **Task 1:** Reuses the existing catalog fact vocabulary and validation rather than introducing a second classification system. The closed lists are defined in `skills/ai-kit-spec-review/ai_kit_spec/catalog_bands.py:10-20`, and `fact_problem` is in `skills/ai-kit-spec-review/ai_kit_spec/catalog_labels.py:28-45`.
- **Tasks 2–3:** Reuses the host-disabled, stale-listing, and stale-provider logic in `skills/ai-kit-spec-review/ai_kit_spec/catalog_report.py:81-112,122-137`; router aliases are kept separate from ranked candidates.

##### Concerns

- **HIGH — Malformed fact labels can crash the proposal.** The plan treats the catalog as possibly hand-edited and calls `fact_problem` for every fact (`.planning/phases/36-spec-config-as-the-hub/36-06-PLAN.md:115-116,208-214`). But `fact_problem` performs `value["label"] not in LABELS` without first requiring a string (`skills/ai-kit-spec-review/ai_kit_spec/catalog_labels.py:28-35`). A JSON array or object label is unhashable, so the prescribed call raises `TypeError` instead of returning “unknown.” The tests cover a missing label, not a wrong-type label.
- **MEDIUM — Dependency on the planning amendment is implicit.** The executor is told to read the locked D-20–D-23 decisions (`.planning/phases/36-spec-config-as-the-hub/36-06-PLAN.md:55-57`), but those are added by 36-02 (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:23-25,53-56`); 36-06 declares only 36-01 as a dependency (`.planning/phases/36-spec-config-as-the-hub/36-06-PLAN.md:5-6`). Wave ordering may prevent the race, but the dependency graph does not express the input.
- **MEDIUM — Same-wave verification can observe partially edited dependencies.** The plan runs the shared architecture test (`.planning/phases/36-spec-config-as-the-hub/36-06-PLAN.md:185-190`) while same-wave plans 36-03, 36-04, and 36-05 can modify code in the same checkout. No declared edited file overlaps, but a full-tree test is not isolated from those changes.

##### Suggestions

- Make malformed fact types safely resolve to unknown, with tests for object/list labels and other malformed JSON values.
- Declare the 36-02 dependency, or explicitly state that wave completion—not only `depends_on`—is the scheduling barrier.
- Run shared full-tree checks after the wave is integrated, or execute plans in isolated worktrees.

##### Risk Assessment

**MEDIUM–HIGH.** Normal catalog data follows the intended shape, but a malformed cache can terminate the entire read-only proposal.

##### Ponytail findings

- **LOW — Tasks 1–3 are justified by R6.** The small pure module and existing `catalog_report` helpers are appropriate reuse; no additional abstraction is needed to fix the malformed-input gap.
- **LOW — Generated listings are covered by 36-01.** The plan fills its registered stub rather than regenerating `Makefile` or `.pre-commit-config.yaml` (`.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:114-115,130-140`).

---

#### 36-07

##### Summary

The price and data-use modules address required free-lane behavior and establish useful validator seams. The main concern is that the prescribed price result can associate an unsourced figure with a different sourced observation, producing a misleading zero-price display.

##### Strengths

- **Tasks 1–2:** Correctly reuse `catalog_bands.is_num`, which excludes booleans and non-finite numbers, and the existing exact-zero banding logic (`skills/ai-kit-spec-review/ai_kit_spec/catalog_bands.py:23-28,55-66`).
- **Task 3:** Reuses the existing secret-shape detector and redactor (`skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:94-117`) and requires an explicit `true` confirmation for a populated data-use record.

##### Concerns

- **HIGH — The displayed figures can contradict the source and zero-price state.** `_models_dev_reading` takes the `free_or_local` fact as its source but copies figures from the separate, unsourced `entry["pricing"]` field (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:117-119`). The shipped catalog builder can populate or preserve that field from another source (`skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py:489-505`), while the band is independently produced by `md_facts` (`skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py:66-88`). A valid-looking zero band beside a positive preserved price can therefore be reported as `state="zero"` with positive figures and a models.dev source. This violates the requested honest sourcing and exact-zero display.
- **HIGH — “No real writes” is not established for the data-use path end to end.** This plan’s validator accepts an entirely absent record (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:173-186`); the downstream writer likewise invokes it only when a data-use key exists (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:162-165`). That is a reasonable consistency-only interface, but it means the safety requirement relies entirely on the wizard identifying and processing every free selection. Tests limited to validator consistency cannot prove the prohibition that a declined or skipped free lane is not written. The handoff needs an explicit end-to-end test.
- **MEDIUM — Wrong-type fact labels can also abort price detection.** The proposed `_models_dev_reading` calls `fact_problem` on cached data (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:118`); the wrong-type-label failure described for 36-06 applies here too (`skills/ai-kit-spec-review/ai_kit_spec/catalog_labels.py:28-35`).
- **MEDIUM — 36-02 is an undeclared input dependency.** The objective requires reading R13 and D-20–D-23 (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:52-60`), which 36-02 adds, but `depends_on` names only 36-01 (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:5-6`).
- **MEDIUM — Runtime budget is at risk.** Three tasks create two runtime modules and two substantial test modules (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:97-120,133-150,164-187`), with several architecture/lint runs plus commit hooks. The plan gives no measured basis for fitting the 1,800-second unattended cap; four files alone do not prove it will exceed the cap.

##### Suggestions

- Do not attribute unsourced figures to the band’s source. Either retain only the sourced zero classification without figures, or return per-source figures only when their provenance is established; test a zero band paired with positive or stale `pricing`.
- Add a wizard-to-render test for zero-price selection, yes/no/skip, and the resulting file; keep the pure validator’s documented consistency-only contract.
- Include 36-02 in dependencies and record an estimated line count and timed execution evidence, or split the plan at the data-use module boundary.

##### Risk Assessment

**HIGH.** Misrepresenting price provenance can undermine the owner’s selection and the free-lane safety flow; the planned unit tests do not cover that mismatch.

##### Ponytail findings

- **LOW — All three tasks serve R12/R13.** The two pure modules have distinct consumers, and reuse `catalog_bands` and `secret_shapes`; the split is justified.
- **MEDIUM — The safety handoff is incomplete.** Validator tests alone cannot establish the owner-confirmation workflow across 36-13, 36-24 and the writer; add one integrated test rather than another abstraction.

---

#### 36-09

##### Summary

The plan sensibly reuses the existing ranker and jev client and makes the fallback reason visible. Two important gaps remain: the fact-summary filter is not actually a closed vocabulary, and the specified error handling does not cover a judge that raises.

##### Strengths

- **Tasks 1 and 3:** Reuses `model_ranker.score_candidates` and the existing `jev_names.ask_items` client instead of introducing another client copy (`skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:266-296`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:127-158`).
- **Tasks 1–2:** Scores each runtime row separately and names the scorer/jev reason, making the bounded window visible to callers (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:124-129`).

##### Concerns

- **HIGH — Arbitrary catalog strings can be sent to jev despite the closed-facts claim.** `lane_pool` retains every string from `rt_row["efforts"]` (`.planning/phases/36-spec-config-as-the-hub/36-06-PLAN.md:115-116`), and `facts_summary` accepts any string matching `[A-Za-z0-9._-]{1,16}` (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:124,127`). That pattern also accepts short model names, IDs, and arbitrary tokens from a hand-edited catalog; it is not a closed effort vocabulary. The existing host parser accepts any string variant ID (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:821-824`). The tests check a few sentinel strings, not this boundary. Thus the assertion that no model ID or other arbitrary value reaches jev is not established.
- **HIGH — An unexpected judge exception aborts ranking instead of falling back.** The plan calls `judge(...)` without a specified exception boundary (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:128-129`). The existing adapter catches subprocess errors inside `ask_items` (`skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:127-143`), but not every possible exception from an injected or future judge. This contradicts the stated “error … leaves the deterministic order” guarantee (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:23`).
- **MEDIUM — One-batch proof does not exercise JSON escaping.** The test uses a repeated simple-character summary (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:180-187`). `score_item` accepts arbitrary printable text (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:121-122`), whereas `ask_items` sizes the serialized JSON (`skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:93-105,127-130`). Printable non-ASCII characters can expand under `json.dumps`, so the test does not prove that every accepted 12-item payload is one batch. A truly closed ASCII fact schema would also address this.
- **MEDIUM — Undeclared amendment dependency and shared-check race.** The plan reads D-20–D-23 but depends only on 36-01 and 36-06 (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:5-6,64-66`); 36-02 supplies those amendments. Its architecture checks can also run while same-wave 36-08 and 36-10 edit other project files (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:189-194`).
- **MEDIUM — Unattended time cap is unproven.** The plan creates a ranker, extends the jev client, adds 15 tests and runs multiple shared gates (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:120-130,144-160,173-199`). Its low-confidence estimate does not show that the work and commit hooks fit 1,800 seconds.

##### Suggestions

- Define an allowlist or another provenance-preserving representation of effort *levels* before constructing jev summaries; test a short ID-like or secret-like token in the catalog.
- Catch and label judge failures at the seam, then test a raising fake judge and verify scorer order.
- Test worst-case serialized payloads actually admitted by the production summary builder, including escaping.
- Add 36-02 as a dependency and measure or split the execution workload.

##### Risk Assessment

**HIGH.** The most significant risk is information crossing the jev boundary under a weaker filter than the plan claims.

##### Ponytail findings

- **LOW — Tasks 1–3 are required for R6.** Existing ranking and jev helpers are reused rather than copied.
- **MEDIUM — Reuse must preserve the error contract.** The current `ask_items` catches known subprocess failures, not arbitrary failures of the new judge seam; a small boundary check is preferable to another client layer.

---

#### 36-13

##### Summary

This is the required integration point and has a concrete output schema. However, its “read-only” claim and test do not match the actual effects of the real `--detect --jev` path, which is the path the wizard is instructed to use.

##### Strengths

- **Task 1:** Reuses the existing catalog-report snapshot construction rather than duplicating detection logic (`skills/ai-kit-spec-review/ai_kit_spec/catalog_cmds.py:178-195`).
- **Task 2:** Makes runtime filters, zero-price group order, and malformed filter errors explicit (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:160-180`).

##### Concerns

- **HIGH — The real command writes state despite the read-only guarantee.** The wizard invokes `--detect --jev` (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:148-153`). The proposed command calls the real jev factory and judge (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:139-143`); the jev client appends an answer log under the user’s state directory for dispatched items (`skills/jev-fast-decision/scripts/jev_review.py:1937-1956,2007-2023,2335-2360`). Detection can also create its cache directory for a private runtime cwd (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:884-896`). Task 3 uses a fake judge and cached snapshot (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:193-204`), so it cannot detect either effect. Resolve the contract explicitly and test the real side-effect boundary with controlled fakes: either prevent these writes or narrow the claim with owner-approved wording.
- **HIGH — `--detect` has no command-level test.** Every proposed command fixture uses `--runtimes-json` (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:131-145,167-180`), while the wizard’s normal path uses `--detect` (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:148-153`). Consequently, fresh stale filtering, the `stale_checked` claim, snapshot seam wiring, and the no-real-host/network guarantee are not verified together.
- **HIGH — Ranker integration can fail on malformed cached numeric values.** The command accepts dict-valued catalog entries and passes their `pricing`, `scores`, and runtime rows into the planned ranker (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:142`; `.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:126`). The shipped ranker performs arithmetic and comparisons on these values without validating every input axis (`skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:190-193,196-214,217-229`). A hand-edited `ctx_window` or price string can therefore raise instead of producing the promised JSON/error response. Existing command tests use only clean fixtures.
- **MEDIUM — A same-wave test dependency is shared with 36-14.** 36-13 runs `tests.test_ai_kit_spec` (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:147-149`), while same-wave 36-14 edits that test module (`.planning/phases/36-spec-config-as-the-hub/36-14-PLAN.md:5-14`). The plans do not edit the same declared files, but a parallel run in one checkout can see a partially modified test file.
- **MEDIUM — Executor-cap risk.** The integration task prescribes several helpers, CLI wiring and a comprehensive fixture before adding 11 further tests and full architecture/lint checks (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:123-155,160-216`). No timing or line-count evidence demonstrates completion within 1,800 seconds including hooks.

##### Suggestions

- Add a hermetic `--detect --jev` integration case that injects detection, process, network, and jev seams and checks all filesystem effects—not just catalog bytes.
- Specify the allowed jev logging and detection-cache effects consistently with the read-only requirement; if strict no-write behavior is required, implement and test that boundary.
- Validate or safely normalize the scorer inputs before calling the existing ranker, with malformed price, score, and context fixtures.
- Isolate same-wave work or defer the shared test until integration; split or time the integration plan.

##### Risk Assessment

**HIGH.** The normal wizard path differs materially from the only planned read-only proof, and malformed cache data can prevent a proposal.

##### Ponytail findings

- **LOW — The command and JSON integration are required by R6/R12.** Reusing `catalog_cmds` and `model_ranker` is appropriate.
- **MEDIUM — The existing helpers bring side effects and input assumptions.** Reuse is not sufficient by itself: test their real boundaries rather than adding another wrapper that merely claims the command is pure.

---

##### Cross-plan coverage and status

**Status: Issues found — revise and re-review.** I checked the four manifest plans and their directly relevant handoffs; I did **not** complete an exhaustive audit of every phase-wide edge/prohibition, every referenced path, or every other plan. Same-wave **declared file edits** do not overlap for these four plans under the supplied wave map; shared verification against a concurrently modified checkout remains a risk as noted above.

No files were created or changed, and no test suites or make targets were run. The 1,800-second risks are estimates, not measured failures.

#### Batch C (36-05, 36-18, 36-21)

#### 36-05

**Summary.** The plan provides the shared effort-form and validation logic required by HUB-05. Its main risks are model-ID ambiguity and a handoff that does not expose its filtered level list to the wizard.

##### Strengths

- The runtime forms and closed-set mirrors are centralized, with a drift test against the runner template (`36-05-PLAN.md:123-132`; `skills/ai-kit-spec-review/references/cross-ai.mjs:5253-5254`).
- The plan reuses existing catalog lookup and suffix helpers rather than introducing another catalog reader (`36-05-PLAN.md:185-190`; `skills/ai-kit-spec-review/ai_kit_spec/usability.py:45-57`).

##### Concerns

- **HIGH — A real model ID can be mistaken for an effort suffix.** `_carried` treats every recognized trailing pi suffix as an effort without checking whether the whole ID is a listed model (`36-05-PLAN.md:126-129`). The runner explicitly documents that pi tries the complete ID first (`skills/ai-kit-spec-review/references/cross-ai.mjs:1299-1301`), and the existing name parser preserves known IDs before splitting (`skills/ai-kit-spec-review/ai_kit_spec/model_names.py:116-130`). A listed ID ending in `:high` can therefore be treated as already carrying `high`, causing a requested `low` to be ignored or an untested `high` to appear accepted.
- **HIGH — The wizard does not consume the safe level offer.** This plan filters name words, malformed tokens and unsupported levels in `offered_levels` (`36-05-PLAN.md:203-209`), but plan 36-24 instead takes raw proposal-row efforts and tests them with `build-command` (`36-24-PLAN.md:165-174`). Plan 36-06 copies string efforts from the catalog into those rows (`36-06-PLAN.md:113-116`). For example, cursor’s `thinking` passes the runtime preview’s token check but is explicitly refused by `offered_levels`; it can be offered to the owner and then rejected at write.
- **MEDIUM — The successful summary handoff is outside the executor prompt.** The objective identifies only the module and test as output (`36-05-PLAN.md:55-59`); the instruction to create `36-05-SUMMARY.md` is outside `<objective>` and `<tasks>` (`36-05-PLAN.md:263-265`). Plan 36-18 requires that summary (`36-18-PLAN.md:76`). Under the stated prompt construction, the executor is not instructed to create it on success.
- **MEDIUM — Model-level validation is not applied to hand-written lanes at dispatch.** `write_problems` checks the catalog only at write (`36-05-PLAN.md:208-209`), while the planned runtime form checks token shape and runtime closed sets only (`36-05-PLAN.md:126-130`). A hand-edited lane can therefore pass a syntactically valid but model-unlisted level to the runner, contrary to the R4 prohibition. The existing dispatch reaches the runner without a catalog effort check (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:583-600`).

##### Suggestions

- Resolve exact listed IDs before interpreting suffixes, and add a regression case for a listed pi ID ending in an effort word.
- Expose the same `offered_levels` result to the wizard and use it for both display and write validation.
- Put the success-summary instruction in the executor-visible objective or tasks, and validate known model levels on the run path before dispatch.

##### Risk Assessment

**HIGH.** The shared helper can misinterpret model identity, and its validation is not consistently used by its consumers.

##### Ponytail findings

- **MEDIUM — Tasks 1–3 are needed for R4**, and the helper reuse is appropriate. The filtered offer currently has no wizard caller, however, while the wizard duplicates part of its filtering. Wire the existing helper through rather than keeping two definitions of an offerable level.
- **LOW — Same-wave check:** no declared file overlap or same-wave output dependency was identified between 36-05 and 36-03, 36-04 or 36-06 (`36-05-PLAN.md:5-9`; `36-04-PLAN.md:5-15`; `36-06-PLAN.md:5-9`).

---

#### 36-18

**Summary.** The plan correctly targets the shared runner-spec construction and both command previews, but its tests use a fake trailer rather than proving the composed ID against a real runner invocation, and its runtime path inherits the model-level validation gap above.

##### Strengths

- Composing the model before trailer comparison addresses the existing exact-match check (`36-18-PLAN.md:130-134`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:559-565`).
- Reusing `review_spec` reaches both review dispatch and quota probes (`skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py:69-74`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:247-253`).

##### Concerns

- **HIGH — The no-unsupported-effort guarantee is not enforced on dispatch.** `spec_with_effort` invokes only `effort_form` (`36-18-PLAN.md:130-133`), which does not consult a model’s listed levels (`36-05-PLAN.md:126-130`). A hand-written pi, cursor or opencode lane can send a valid-looking but unlisted effort. The matrix checks that a value was composed or ignored, not that the model supports it (`36-18-PLAN.md:161-165`).
- **MEDIUM — The trailer test assumes the runner’s result.** The proposed test makes the fake child print `spec.model` (`36-18-PLAN.md:122-123`); it cannot detect a difference between the actual runner’s reported model and the Python expectation. The real runner constructs and reports its own `c.model` (`skills/ai-kit-spec-review/references/cross-ai.mjs:12581-12588`, `:12823`). A hermetic integration test should exercise that boundary with a fake host.
- **MEDIUM — The next plan’s required summary is not requested in the executor-visible text.** The success-output instruction is only in the excluded output block (`36-18-PLAN.md:262-264`), but plan 36-21 requires `36-18-SUMMARY.md` (`36-21-PLAN.md:68`).
- **MEDIUM — The changed-ID assertion preserves an explicitly disallowed fixture.** The plan directs changing `"x/y"` to `"x/y#high"` (`36-18-PLAN.md:135-136`), while its own executor rules restrict new model IDs to placeholder forms (`36-18-PLAN.md:96`). The existing assertion is at `tests/test_ai_kit_spec_runner_dispatch.py:835-849`. Use an allowed synthetic ID in both the input and expected result.

##### Suggestions

- Validate an explicitly set effort against known per-model levels before dispatch, while retaining an honest path for unknown support.
- Add one fake-host runner integration case that checks the actual argv and trailer, rather than generating the expected trailer in the test.
- Include the successful summary step in the piped task text.

##### Risk Assessment

**HIGH.** The central wiring is sound in shape, but it can pass an effort that the model listing says is unsupported.

##### Ponytail findings

- **MEDIUM — All three tasks implement R4 or the locked R7 preview.** The existing `review_spec` and `run_runner` are appropriate reuse points; the missing catalog-aware guard needs to be shared rather than copied into each caller.
- **LOW — Same-wave check:** 36-17 edits `config_io.py` and `lane_settings.py`, not this plan’s declared files (`36-17-PLAN.md:5-10`; `36-18-PLAN.md:5-11`). No declared same-wave file overlap was found.

---

#### 36-21

**Summary.** The plan adds a focused probe and correctly prevents the new explicit `--effort` option from recording model usability. The existing `--extra-json` route bypasses that protection, and the proposed error extraction can show runner diagnostics instead of the host’s error.

##### Strengths

- It reuses the existing one-call quota probe and error sanitizer (`36-21-PLAN.md:121-125`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:256-284`; `skills/ai-kit-spec-review/ai_kit_spec/usability.py:15-24`).
- The proposed explicit-option conflict is checked before the probe or catalog write (`36-21-PLAN.md:161-165`).

##### Concerns

- **HIGH — `--extra-json` bypasses the catalog-write safeguard.** The conflict check only tests `args.effort` (`36-21-PLAN.md:163-164`). Existing `check-reviewer` accepts arbitrary `--extra-json` and sends it to the quota probe before recording usability (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:1156-1167`); after plan 36-18, `extra.effort` reaches the runner through `review_spec` (`36-18-PLAN.md:130-133`). Thus `--extra-json '{"effort":"..."}' --catalog-path ...` can still record a rejected effort probe as a rejected model.
- **HIGH — The reported “host first error line” can be a runner status message.** The plan sanitizes the first line of the whole collected `detail` (`36-21-PLAN.md:124-125`). The probe collects every relayed line (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:228-244`, `:256-265`), and the real runner emits its own deadline and retry diagnostics before running the host (`skills/ai-kit-spec-review/references/cross-ai.mjs:12616-12625`). The fake rejection test emits only the host-like error (`36-21-PLAN.md:150-151`), so it misses this ordering.
- **MEDIUM — The write check can use a different catalog from the proposal.** `render-toml` always reads the default cache paths (`36-21-PLAN.md:183-195`), while `propose-lanes` accepts a required caller-selected catalog and snapshot (`36-13-PLAN.md:139-142`). If the wizard selected from another catalog, write-time validation may use stale or absent evidence and either refuse a valid selection or treat known support as unknown.
- **MEDIUM — Same-wave dependency is not a parallel-safe schedule.** Plan 36-21 is in wave 7 and depends on 36-20 (`36-21-PLAN.md:5-6`); 36-20 is also wave 7 and changes the writer and tests that 36-21 expects (`36-20-PLAN.md:5-12`; `36-21-PLAN.md:183-195`). If the wave runs in parallel as stated, 36-21 may run before its required writer exists. Put it in a later wave or explicitly guarantee dependency-aware serialization within the wave.

##### Suggestions

- Reject catalog recording whenever the *effective* probe input contains an effort, including `--extra-json`; test both entry paths.
- Preserve or identify the actual host error separately from runner diagnostics, then sanitize it. Add a fake sequence containing a runner preamble followed by the host error.
- Carry the proposal’s catalog and snapshot into write validation, or explicitly constrain both commands to the same sources.
- Move 36-21 after 36-20 in the wave schedule.

##### Risk Assessment

**HIGH.** A rejected effort can still poison model-usability data, and the reported rejection may not explain what the host rejected.

##### Ponytail findings

- **MEDIUM — Tasks 1–3 are needed for R4.** Reusing `probe_reviewer_quota` and `sanitize_error` is preferable to another process or sanitizer; the existing `--extra-json` input and runner preamble must be included in that reuse boundary.
- **LOW — No extra dependency is needed.** The planned runtime imports are stdlib or existing project modules (`36-21-PLAN.md:121`).

##### Review status

**Issues found — revise before execution.** I reviewed the three manifest plans and the cited dependency/source paths; this is not an exhaustive verification of every phase-wide SPEC edge or every referenced path. No tests or make targets were run, and no scratch files were created.

#### Batch D (36-11, 36-17, 36-20, 36-23)

#### 36-11

##### Summary

The plan addresses the required write-side validation and protects model-specific settings during layered merges. Two cross-plan contradictions would prevent a reliable unattended execution, including one that can break every config resolution path.

##### Strengths

- The model-change tests exercise the existing per-key merge rather than introducing a second merge mechanism: `.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:187-198`; existing merge at `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:361-385`.
- The writer reuses `validate_reviewer_fields` and the existing rejection/warning path: `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:749-794`.

##### Concerns

- **HIGH — Task 1 removes a required import from plan 36-04.** The prescribed replacement import omits `role_orders` (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:123`). Plan 36-04 adds that import and calls `role_orders.role_orders` from `_combine_roles` (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:140`). Following both instructions produces a `NameError` when resolving config. Preserve the earlier import instead of replacing the whole line.
- **MEDIUM — Two plans own conflicting validation for `effort_source`.** This plan says no other plan validates it and adds its own regex and error (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:31,154,164`), but 36-05 explicitly validates it first, with different errors (`.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:160-167`). The second check is largely unreachable through the prescribed validator chain. The direct unit tests can pass while the writer emits a different message.
- **MEDIUM — Task 2’s test-count criterion is inconsistent.** Task 1 specifies five tests (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:128`); Task 2 specifies eight more (`:166`), so 13 is consistent. Task 3 adds five (`:198`), giving 18. However, Task 1 also says “one test per behavior line” while assigning the first four behaviors to four tests and the fifth to one; keep that explicit interpretation to prevent a coding executor from splitting subtests differently. This is an executor-clarity issue, not a demonstrated failure.
- **MEDIUM — Scratch cleanup is not specified for the executor’s own HOME.** The objective requires a fresh scratch HOME (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:83`) but does not give a cleanup-on-failure procedure. The repository’s mandatory temporary-file rule requires one; the test runner’s own isolation does not clean the separately created executor HOME (`tools/run_unittest_parallel.py:51-53`).

##### Suggestions

- Amend Task 1’s import to retain `role_orders`.
- Assign `effort_source` validation to one module, and pin the error observed **through the writer**, not just the helper.
- Give the executor a concrete scratch-directory lifecycle compatible with the local shell rules.

##### Risk assessment

**HIGH** — the prescribed import replacement breaks a dependency’s config-resolution code.

##### Ponytail findings

- **HIGH — Task 1:** The validation is required, but replacing an already-extended import does not reach the existing caller safely.
- **MEDIUM — Task 2:** Reuse 36-05’s planned effort validator rather than duplicate its regex and semantics.
- **LOW — Task 3:** The model-bound merge guard is justified by the consent requirement and reuses the existing merge; no extra abstraction is needed.

#### 36-17

##### Summary

The planned readers and warnings cover the locked pool-aware fallback rule, but the warning integration does not match the code that its prerequisite will produce. The structural guard also provides weaker assurance than its stated prohibition.

##### Strengths

- The fallback tests include same-pool, missing-key and duplicate-key cases (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:117-123`).
- Strict public flag readers are separated from the non-throwing warning path (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:127-131`).

##### Concerns

- **HIGH — Task 1 assumes a `cfg_combine` shape that plan 36-04 explicitly does not produce.** This plan instructs the executor to bind `review` and `execute` in `cfg_combine` (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:132`). Plan 36-04 instead moves those bindings into `_combine_roles`, specifically because `cfg_combine` is already at the locals cap (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:140`). The permitted edit is restricted to `cfg_combine` (`36-17-PLAN.md:91`), leaving the executor to choose between duplicate merges, a pylint violation, or breaking the prior helper contract.
- **HIGH — Warning calculation ignores the declared role order.** `lane_fallback` requires its input already ordered (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:130`), but the warning hook passes raw merged `review` and `execute` arrays (`:132`), not `orders`. The existing role merge preserves global-array order followed by new local keys (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:361-385,668-679`). A lane omitted from the role ladder can therefore suppress a warning even though it is not a selectable fallback. Add a test where roster order, ladder order, and an omitted lane differ.
- **MEDIUM — Task 3’s scanner is not a proof that flags cannot be set.** It bans exact string constants outside one module (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:185-194`), but a setter can construct a key dynamically or mutate an entry through a helper. Its planted test proves detection of one literal spelling, not the broader prohibition. Keep the guard as a backstop and test owner-answer-to-written-config behavior independently.
- **MEDIUM — Task 1’s no-raise claim is too broad.** `_keyed` only checks that keys are strings; it does not validate `role_lanes` itself before iteration (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:129-131`). State the input precondition or cover malformed role collections before claiming warnings “never raise.”
- **MEDIUM — Dependency ordering is implicit.** The objective assumes plan 36-14 has edited `config_io.py` (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:91`), but `depends_on` names only 36-04 and 36-11 (`:6`). Add 36-14 if its output is required; otherwise remove the assumption.

##### Suggestions

- Integrate warning generation into or immediately after the existing `_combine_roles` result, with an explicit permitted edit and pylint-safe implementation.
- Derive warning candidates from the same ordered lane set future consumers will use.
- Add behavioral tests for skipped/no answers and the actual saved flags; do not present the AST scan alone as comprehensive.

##### Risk assessment

**HIGH** — the planned integration conflicts with its prerequisite, and the warning can misrepresent the available fallback.

##### Ponytail findings

- **HIGH — Task 1:** The warning is required; reuse 36-04’s `_combine_roles` and `ordered_lanes` rather than recomputing role merges.
- **LOW — Task 2:** Separate target selection is justified because an entry alone cannot reveal its role’s order.
- **MEDIUM — Task 3:** The custom scanner is useful as a narrow regression guard, but should not replace behavior tests for the owner’s explicit opt-in.

#### 36-20

##### Summary

The writer plan has strong coverage of legacy and byte-preserving cases, but its explicit precondition creates a dependency cycle that prevents the phase from reaching this plan as written.

##### Strengths

- The plan uses the existing verified TOML splicer and atomic publisher instead of adding a second writer (`skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py:429-448,780-792`).
- Tests cover legacy ladders, inline role tables, rejected keys and unrelated-text preservation (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:156-169`).

##### Concerns

- **HIGH — Tasks cannot start: the probe switch is scheduled after the writer.** Task 1 requires the switch before any edit and says to stop otherwise (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:108`). The current code reads the flat ladder (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:795-798`); the switch belongs to 36-22 (`.planning/phases/36-spec-config-as-the-hub/36-22-PLAN.md:116-119`), which depends on 36-21 (`:6`), and 36-21 depends on 36-20 (`.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:5-6`). This is a real cycle, not merely a missing dependency.
- **HIGH — Same-wave execution contradicts the dependency graph.** The wave map places 36-20 and 36-21 in wave 7, but 36-21 explicitly depends on 36-20 (`.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:5-6`). They do not share a declared edited file, but cannot safely run concurrently: 36-21 requires the completed writer.
- **MEDIUM — Task 1 instructs a prohibited model fixture.** Its replacement test embeds model `"m1"` (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:131`), contrary to the plan’s own allowed placeholder forms (`:86`). Replace both occurrences with an allowed placeholder.
- **MEDIUM — Task 3 repeats the unordered-fallback issue from 36-17.** The writer passes role arrays directly to `fallback_warnings` (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:195`), while the fallback contract requires role order. A configured but unlisted lane can make a role appear to have a usable fallback.
- **MEDIUM — Execution budget is risky, not demonstrated sufficient.** Task 1 alone prescribes changes across five files plus multiple helpers and eight test modules (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:105-137`); the plan estimates 75,000 tokens (`:17-21`) and also requires a hook-running commit. There is no timing evidence that this fits the 1,800-second cap.

##### Suggestions

- Split out the minimal default-review probe switch into an earlier prerequisite, or otherwise reorder the plans so 36-20’s precondition is true without depending on 36-22.
- Move 36-21 to a later wave and preserve its explicit dependency.
- Use the written ladder when computing preview warnings and add a lane-excluded-from-ladder test.
- Split the writer work into independently buildable, bounded commits/plans if timing cannot be demonstrated.

##### Risk assessment

**HIGH** — the dependency cycle deterministically stops unattended execution before the writer is implemented.

##### Ponytail findings

- **HIGH — Task 1:** Separate role orders are required; reuse `toml_splice.set_table`, but fix the prerequisite before adding writer machinery.
- **LOW — Task 2:** The legacy and byte-preservation tests are necessary for a config-writing change.
- **MEDIUM — Task 3:** Reuse the ordered-lane helper rather than adding a second interpretation of fallback eligibility.

#### 36-23

##### Summary

The doc-to-writer test is valuable, but the planned herdr test exercises command outputs rather than the owner-facing wizard questions it claims to cover. The added prose also contains an internally contradictory description of unknown data-use records.

##### Strengths

- Rendering the actual documented JSON through `cfg_render_lanes` is a useful drift test (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:103-121`).
- A logging fake and a planted invocation give the herdr-call check a non-vacuity test (`tests/herdr_fakes.py:12-38`; `.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:148-151`).

##### Concerns

- **HIGH — Task 2 does not verify identical wizard questions.** It invokes four CLI commands with hardcoded input and compares output/config bytes (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:149-151`). It never executes or compares the owner-facing question flow, although the plan claims the prohibition is resolved (`:28-31`) and the actual flow is specified separately in `.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:136-142`. A herdr-dependent change to those questions would pass this test.
- **MEDIUM — Task 1’s data-use prose contradicts the validator.** It says the six keys “are written together” and also says `data_use_label` is present only when the value is not unknown (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:119`). Plan 36-07 requires the label to be **absent** for `unknown` (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:174-177,185-186`). Describe the five required fields plus the conditional label explicitly.
- **MEDIUM — The example enables an escalation with no possible target.** The execute ladder puts `execute-main` last while setting `escalate_model` on it (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:114`). The planned target algorithm searches only subsequent entries (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:164`). The example renders, but teaches a setting that cannot take effect; the test only checks that the key survives.
- **MEDIUM — Same-wave test dependencies are not the same as the wizard integration.** Plans 36-22, 36-23 and 36-24 have no declared same-wave file overlap, but 36-23’s claimed wizard-identity proof does not consume 36-24’s question-flow artifact. The separate text-contract tests may pin wording, but the listed 36-23 test cannot establish identical questions with and without herdr.

##### Suggestions

- Add a behavioral or replayable question-flow test under both environments, or narrow this plan’s claim and assign that proof explicitly to the wizard/eval plan.
- Correct the conditional data-use wording.
- Give the example’s model-escalation flag a later same-runtime, different-model target, or omit that flag from the example and test it separately.

##### Risk assessment

**MEDIUM** — the writer example is tested, but the stated owner-interaction guarantee is not.

##### Ponytail findings

- **LOW — Task 1:** A single executable documentation example is warranted and reuses `cfg_render_lanes`; fix the example rather than adding another documentation schema.
- **HIGH — Task 2:** The existing `tests/herdr_fakes.py` helper is appropriate, but command-byte equality is not a substitute for checking the required wizard interaction.

##### Status: Issues Found — fix and re-review

**Coverage and limits:** All four manifest plans received a section. The review identified no declared same-wave file overlap for these four; 36-20/36-21 have the dependency conflict noted above. I did not establish exhaustive coverage of every phase-wide SPEC edge or prohibition across all 29 plans, nor verify every named path and command. No tests or make targets were run, and no files or scratch artifacts were created.

#### Batch E (36-08, 36-12, 36-14, 36-15)

#### 36-08

##### Summary

The plan implements the locked formula-mirror decision before routing consumes it. Its principal risks are verification of the real-node check and the missing explicit dependency on an earlier plan whose tests it runs.

##### Strengths

- The drift test checks the runner’s own `--print-argv` output rather than trusting the Python mirror alone. The runner builds that output from its runtime formula at `skills/ai-kit-spec-review/references/cross-ai.mjs:12629-12639`.
- Non-vacuity cases cover a changed head, a missing mirror, and the null-formula case (`.planning/phases/36-spec-config-as-the-hub/36-08-PLAN.md:163-168`).
- The plan reuses `runner_env` and the existing test runner rather than introducing another subprocess harness (`tests/cross_ai_selftest.py:39-100`).

##### Concerns

- **MEDIUM — The drift gate can pass with its only live check skipped.** The test skips when `_real_node_executable()` returns `None`, while Task 1 rejects only a zero-test report and Task 2 expects five tests including four non-vacuity tests (`.planning/phases/36-spec-config-as-the-hub/36-08-PLAN.md:136-141,177-192`). A skipped test still contributes to unittest’s `Ran` count; the runner reports success from the process return code (`tools/run_unittest_parallel.py:925-930`). The separate `node --version` precondition does not prove `_real_node_executable()` succeeded.
- **MEDIUM — Dependency and execution budget.** Task 1 runs `tests.test_ai_kit_spec_routing` and `tests.test_ai_kit_spec`, both modified by 36-04, but the plan names only 36-01 as a dependency (`36-08-PLAN.md:5-12,139-141`; `.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:5-15`). The wave barrier orders them, but the dependency graph alone does not. The five-file plan also requires two commits and several test runs, including a full staged unit-and-arch run (`36-08-PLAN.md:177-179`): completion within 1,800 seconds is a **risk**, not established by a timing measurement.

##### Suggestions

- Make absence or failure of the resolved Node executable fail this particular drift gate; retain a separately named optional skip only if another required gate proves the live check ran.
- Declare 36-04 as a dependency for the tests consumed here, and time the complete plan—including hooks—against the executor cap.

##### Risk Assessment

**MEDIUM.** The design is traceable, but the central drift check can report green without checking the runner.

##### Ponytail findings

- **LOW — Needed, with an existing seam.** The mirror and drift check are required by D-08; reusing `runner_env` is appropriate. No extra runner implementation is needed. The plan reaches the table, its direct tests, and the recorded E2E timing (`36-08-PLAN.md:121-136,171-179`).

---

#### 36-12

##### Summary

The route replacement preserves the important native-before-formula ordering and gives skipped lanes a sourced reason. Its main execution risk is that the plan reads and edits output of 36-04 without declaring that dependency.

##### Strengths

- The proposed `no_formula` branch remains after native selection, matching the current load-bearing route order (`skills/ai-kit-spec-review/ai_kit_spec/routing.py:167-179`; `.planning/phases/36-spec-config-as-the-hub/36-12-PLAN.md:130-136`).
- It reuses `SKIP_ROUTES` and `unroutable_quota`, so a permanent route failure remains distinguishable from quota exhaustion (`routing.py:35-40,188-200`).
- It updates the executable documentation snippet when deleting the field (`36-12-PLAN.md:176-180`).

##### Concerns

- **MEDIUM — Missing explicit dependency on 36-04.** Task 1 explicitly says that 36-04 edits `dispatch_injection.py` earlier, and both plans edit that file and `tests/test_ai_kit_spec_routing.py` (`36-12-PLAN.md:113-119`; `.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:7-15`). Yet 36-12 depends only on 36-08 (`36-12-PLAN.md:5-6`). Wave ordering supplies the intended order only if the orchestrator enforces it independently of dependencies.
- **MEDIUM — The grok directive is not consistently respected.** The plan says to change every occurrence of the old route in the superpowers tests (`36-12-PLAN.md:142`), including an existing fake route for a grok candidate and its assertion (`tests/test_ai_kit_spec_superpowers.py:518-544`). That is consistent with the plan’s stated narrow exception, but conflicts with this review’s explicit instruction not to extend or verify grok content. Resolve that instruction conflict before unattended execution.
- **MEDIUM — Executor budget.** Seven files, two commits, and repeated multi-module verification exceed the request’s approximate five-file warning threshold (`36-12-PLAN.md:7-14,143-146,180-185`). There is no evidence that the complete sequence fits 1,800 seconds.

##### Suggestions

- Add 36-04 to `depends_on`.
- Specify how to preserve the existing grok behavior without expanding its test coverage, consistent with the owner directive.
- Measure the two-commit path with its hooks, or split it at a buildable boundary if it exceeds the cap.

##### Risk Assessment

**MEDIUM.** The route mechanics are well grounded, but dependency ordering and the instruction conflict can block an unattended executor.

##### Ponytail findings

- **LOW — Needed and mostly reuses existing machinery.** The route, skip overlay, and native exception are required by R7. Reusing `SKIP_ROUTES`, `unroutable_quota`, and the existing walk avoids a second routing system (`routing.py:188-200`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:323-346`).

---

#### 36-14

##### Summary

The plan reaches the save validator, selection screen, direct dispatch refusal, and adapter tests. It has a concrete hardcoding-rule violation in a new fixture, an undeclared predecessor, and same-wave verification interference.

##### Strengths

- The screen retains the existing custom-command handling and changes only the runtime refusal predicate (`skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py:78-112`; `.planning/phases/36-spec-config-as-the-hub/36-14-PLAN.md:131-133`).
- The planned end-to-end lane check covers validation, selection, routing, and the displayed reason (`36-14-PLAN.md:170-175`).
- The planted source-scan cases exercise the token boundary rather than relying only on an empty real-tree scan (`36-14-PLAN.md:175,181-187`).

##### Concerns

- **HIGH — A new fixture violates the plan’s own hardcoding rule.** Task 1 instructs the executor to add a candidate with `"model": "m"` (`36-14-PLAN.md:137`), while its objective permits only the listed placeholder forms for newly written model names (`36-14-PLAN.md:93`). Existing fixtures with `"m"` do not authorize adding another. Use `placeholder-model-1`.
- **MEDIUM — Missing dependency on 36-11.** Task 2 expects the validator chain that 36-11 installs and tells the executor not to alter it (`36-14-PLAN.md:163-164`; `.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:5-10,27-30`). The only declared dependency is 36-12 (`36-14-PLAN.md:5-6`). Add 36-11 even though the wave map currently places it earlier.
- **MEDIUM — Same-wave test/read interference with 36-16.** This plan runs `tests.test_ai_kit_spec_runtimes_table` (`36-14-PLAN.md:145-146`); 36-16 edits that module and the review documents its existing wording test reads (`tests/test_ai_kit_spec_runtimes_table.py:882-888`; `.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:214-233`). During separate file edits, the test can see old assertions against new text, or vice versa. The plans do not share a declared modified file, but their verification is not independent.
- **MEDIUM — The grok restriction is internally inconsistent.** The plan directs replacement of a test method with exact grok expectations and retains a grok dispatch subtest (`36-14-PLAN.md:124-127,134-137`), whereas the review instruction says not to add, extend, probe, **or verify** grok content. Clarify the permitted treatment before execution.
- **MEDIUM — Executor budget.** Seven modified files, two commits, repeated test runs and pylint exceed the approximate five-file threshold (`36-14-PLAN.md:7-14,143-146,188-193`). No end-to-end timing establishes the 1,800-second bound.

##### Suggestions

- Replace the new `"m"` fixture value with an allowed placeholder.
- Add 36-11 as a dependency and serialize 36-14 verification against 36-16’s wording change, or otherwise make the document-and-test transition atomic from the test’s perspective.
- Resolve the grok instruction conflict explicitly; measure the complete hook-inclusive run.

##### Risk Assessment

**HIGH.** The fixture instruction directly contradicts a mandatory constraint, and the undeclared dependency and same-wave test race can stop unattended execution.

##### Ponytail findings

- **LOW — The affected surfaces are needed.** R7 requires the validator, screen, dispatch reason, and guard; the plan reuses `_validate_pair_fields` and the existing selection pipeline rather than adding another one (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:712-746`; `execute_selection.py:78-112`). The new whole-tree token scan is broader than checking a reader, but it implements the plan’s stated regression rule.

---

#### 36-15

##### Summary

Reusing Phase 35’s scanner, marker rules, baseline, and non-vacuity pattern is the right integration point. However, the new scanner makes an existing test fail, and the plan does not instruct the executor to update it.

##### Strengths

- The existing baseline tracks hit counts and reports both new and removed violations, which supports the requested shrink-only guard (`tests/test_arch_hardcoded_models.py:229-269`).
- The plan adds planted tests for an unmarked default, a skill, marker scope, and baseline removal (`.planning/phases/36-spec-config-as-the-hub/36-15-PLAN.md:103-105,139-149`).
- The scanner already constrains marker exemptions by file/line type and scope (`tests/test_arch_hardcoded_models.py:134-140,178-180`).

##### Concerns

- **HIGH — The specified guard breaks an existing allowed-form test.** The proposed `_referee_hits` exempts only paths beginning `tests/` (`36-15-PLAN.md:110-112`). The existing `test_allowed_forms_pass` calls `scan_text("x.py", 'model = "router-env/x"')` and expects no hit (`tests/test_arch_hardcoded_models.py:408-421`). Under the proposed rule, `x.py` is not exempt and yields a `referee` hit. Task 1’s required verification therefore fails, but the plan says not to change other scanner behavior and does not update this existing test. Change its synthetic path to a test path where appropriate, and retain a separate planted non-test-path failure.
- **MEDIUM — The generator’s fixed snapshot is fragile against concurrent edits.** It exits unless the referee hits are exactly the nine named files and total 57 (`36-15-PLAN.md:114-115`). The scanner includes tracked **and untracked** eligible files (`tests/test_arch_hardcoded_models.py:185-205`), so unrelated pre-existing untracked work or parallel changes can block the plan. The exact-set check is valuable, but the plan needs a read-only preflight and a stated stop/report procedure for pre-existing work, not an instruction to clean it.
- **MEDIUM — Scratch cleanup is not planned.** The generator is explicitly left under `tmp/p36-15/` (`36-15-PLAN.md:98,114,195`), while the mandatory session rule requires run-owned scratch cleanup on every exit path. Add a cleanup and verification step that removes only this run’s scratch.
- **LOW — Budget remains unproven.** Two commits and repeated scans/hooks are required (`36-15-PLAN.md:115-119,149-153`). The plan is below the approximate file threshold, but no hook-inclusive measurement proves it meets the 1,800-second cap.

##### Suggestions

- Update the existing allowed-form test and add a non-vacuity check that distinguishes `tests/...` from a shipped `skills/...` path.
- Preflight the scanner’s eligible file set; if it differs from the expected snapshot, report the exact differences without deleting or baselining unrelated work.
- Use a unique run-owned scratch directory and specify cleanup on success and failure.

##### Risk Assessment

**HIGH.** The first verification cannot pass as written because an existing test contradicts the new rule.

##### Ponytail findings

- **LOW — Needed and correctly placed, apart from the missed caller.** R8 requires the new referee hit; extending `scan_text` and `baseline_problems` reuses the existing guard rather than adding another mechanism (`tests/test_arch_hardcoded_models.py:155-182,229-269`). The existing test call site at `:408-421` must be included in the change.

##### Status: Issues Found — fix and re-invoke

**Coverage limit:** This is a bounded review of the four manifest plans and their cited dependencies, not an exhaustive audit of every phase edge or prohibition. No tests or suites were run, and no files or scratch artifacts were created.

#### Batch F (36-01, 36-02, 36-16, 36-19, 36-29)

#### 36-01

##### Summary

The stub-and-regenerate approach supports the phase’s test-layout decision and gives later plans a consistent module to fill. The main risk is not the stub generation itself: the plan assumes exclusive use of the working tree and Git index while its declared wave also permits plan 36-02 to commit.

##### Strengths

- **Reuses the existing generator.** `tools/gen_test_groups.py:25-35` derives listings from the runner, and `tools/gen_test_groups.py:72-103` renders and atomically writes the generated output rather than requiring a second hand-maintained list.
- **Keeps existing tests safe.** The stub script is instructed not to overwrite an existing module and to stop if it finds one (`.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:115-117`).
- **Correctly identifies the runner registration points.** The e2e group and its time table exist at `tools/run_unittest_parallel.py:115-122` and `tools/run_unittest_parallel.py:151-165`.

##### Concerns

- **HIGH — Same-wave Git and status race with 36-02.** Plan 36-01 requires the entire porcelain status to contain *exactly* its 20 paths and then commits them (`.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:137-140`). Plan 36-02, in the same wave, modifies and commits the SPEC, CONTEXT and ROADMAP (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:109-122`, `:252-264`). If they share a checkout, normal progress by 36-02 makes 36-01 stop; concurrent staging or commits also share the Git index. The “last commit” acceptance check at 36-01 line 152 is similarly race-prone.
- **MEDIUM — Executor size exceeds the requested heuristic.** Although there are only two tasks, the plan changes 20 tracked paths and runs a shared-machinery commit hook (`.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:114-117`, `:137-140`). It exceeds the review’s approximately-five-file heuristic. The plan supplies no timing evidence that generation, verification and the hook fit the 1,800-second cap.

##### Suggestions

- Serialize the two wave-1 plans in the shared checkout, or explicitly use isolated worktrees and a controlled integration step. Scope the status check to this plan’s paths while separately reporting pre-existing changes.
- Measure or budget the shared-machinery hook and leave time for one failure/retry within the executor cap.

##### Risk Assessment

**HIGH** — The work is straightforward, but the declared parallel schedule can stop or contaminate the commit before later plans start.

##### Ponytail findings

- **LOW — Needed infrastructure, with appropriate reuse.** The stubs implement the locked test-layout decision; using `tools/gen_test_groups.py:72-103` avoids a second listing mechanism. Do not remove the generated-listing checks merely to reduce the diff.

#### 36-02

##### Summary

This plan gives the downstream executors explicit text for the pool and data-use requirements and retains the existing edge-floor checker. However, its proposed R13 record is internally contradictory for unknown data use, and the wave-1 commit schedule conflicts with 36-01.

##### Strengths

- **Uses the existing phase verification mechanism.** The plan calls `edge_floor.py check` and requires the expected floor and table counts (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:109-121`, `:229-238`).
- **Makes the fallback pool rule explicit.** Its proposed R12 clause states both the different-pool rule and the acceptance checks (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:149-160`).

##### Concerns

- **HIGH — R13 cannot represent its required unknown case consistently.** The proposed SPEC says all six keys, including `data_use_label`, are written “all or none,” and that a record missing one of six is refused (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:170-183`). The same text says an unknown record carries no label (`:172-174`), and the proposed CONTEXT explicitly says the label is absent for unknown (`:316-320`). A no-label unknown record is thus both required and invalid. This affects the privacy-confirmation path, not just documentation.
- **HIGH — Same-wave shared-checkout race with 36-01.** The two commits in this plan (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:121-122`, `:262-264`) can overlap 36-01’s exact-status and last-commit checks (`.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:137-152`). Explicit `git add` does not isolate concurrent users of one index.
- **MEDIUM — The amendment records accepted decisions as awaiting confirmation.** The request states the owner accepted D-20 through D-23, but the prescribed text repeatedly says confirmation is still needed (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:131-133`, `:286-307`). The **shared-pool fact** can remain reported and unverified without implying the owner’s decision is still pending.
- **MEDIUM — The plan instructs adding the very Grok documentation it forbids.** The objective says to add no Grok doc or list entry (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:81`), while T2 and T7 add new Grok lines (`:140-143`, `:191-194`). An unattended executor told to stop when the plan cannot be followed has no consistent literal instruction.
- **MEDIUM — Executor time risk.** The plan requires 20 exact edits, a custom checker, two commits and a dogfood check (`.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:108-122`, `:252-264`), with no evidence that these fit the 1,800-second cap.

##### Suggestions

- State a precise conditional record contract: for example, five required fields plus a label required only for known values, and test unknown-without-label separately from partial records.
- Record the owner’s acceptance separately from the confidence of the underlying pool evidence.
- Resolve the documentation prohibition explicitly, and serialize commits with 36-01.

##### Risk Assessment

**HIGH** — The contradictory privacy-record contract can produce incompatible validators and wizard output.

##### Ponytail findings

- **MEDIUM — The amendments are needed, but must form one usable contract.** Reuse the existing edge-floor checker as planned; do not add a separate validator merely to reconcile two contradictory descriptions. The plan must reach the downstream data-use validator and wizard tests, not only the SPEC count.

#### 36-16

##### Summary

The review-side chain is placed in the existing dispatch procedure and includes a sensible no-config fixture. Its strongest checks pin text and command ordering, but those checks do not execute the agent’s three-answer flow. There is also an unhandled prerequisite when the review tool itself is absent.

##### Strengths

- **Reuses the existing error boundary.** `cli.main` already maps `ConfigError` to the named stderr message and exit 2 (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:1210-1217`); the plan tests that contract rather than introducing a second handler.
- **Places the check before snapshot refresh.** The current reference refreshes the snapshot at `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:123-145`; the replacement explicitly distinguishes the snapshot from lane config (`.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:177-192`).
- **Same-wave file check.** The supplied wave map does not show an overlapping `files_modified` path between 36-16 and plans 36-13, 36-14 or 36-15.

##### Concerns

- **HIGH — A missing review shim bypasses the required missing-config behavior.** The existing reference treats missing `TOOLS_PY` exactly like `--no-cross-ai` and goes straight to the session default (`skills/ai-kit-spec-review/references/cross-ai-dispatch.md:51-54`, `:110-122`). The plan deliberately preserves that short circuit (`.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:179-180`, `:194-198`). Thus, when the shim is absent, neither `config-status` nor the missing-spec-config diagnostic can run, even if no config and no setup skill exist. The plan needs to reconcile that install-failure case with HUB-01 rather than claim the missing-wizard case is covered.
- **MEDIUM — The fixture tests state, not the chain’s behavior.** The prescribed tests assert `none`, `active` and malformed output and assert that literal text is present (`.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:112-124`). They do not exercise an answer of setup/once/stop, a missing wizard, or a headless host. The stated fixture result “reaches the chain” is therefore a text-and-status inference, not an end-to-end check.
- **MEDIUM — Executor cap risk.** Three commits, five modified files and several multi-module verification runs are specified (`.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:120-125`, `:170-174`, `:226-233`). This is at the requested file/task threshold without a measured hook or test budget.

##### Suggestions

- Specify and test the behavior when the review shim is missing, distinguishing an intentional `--no-cross-ai` request from a broken installation.
- Add executable scenario/eval coverage for all three answers, a missing wizard and a host unable to ask; keep the text-contract tests as complementary checks.
- Record a time budget or split the work at a buildable boundary if the three hook runs cannot reliably fit.

##### Risk Assessment

**HIGH** — The common path is well described, but an installation failure can silently bypass the required diagnostic and the tests would not detect that behavioral gap.

##### Ponytail findings

- **MEDIUM — Needed chain, incomplete behavioral proof.** Reusing the dispatch reference and `cli.main` is appropriate. The smallest complete check should exercise the actual outcome selection, not add another text assertion that merely repeats the proposed prose.

#### 36-19

##### Summary

The adapter plan reuses the existing scalar-file path and tests its new shell blocks against a stub. The proposed session-model answer, however, is recorded without being connected to the existing dispatch decision, so the primary no-config outcome can still stop instead of executing on the session model.

##### Strengths

- **Reuses the adapter’s scalar path.** The proposed path calculation (`.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:157-163`) matches the existing task-path block at `skills/ai-kit-spec-execute-superpowers/SKILL.md:123-127`.
- **Tests the re-invocation guard mechanically.** The plan calls for real shell execution against a fake tool and checks that a recorded decision avoids a second `config-status` call (`.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:220-232`).
- **Same-wave file check.** The supplied wave map shows no shared modified path between 36-19 and 36-17 or 36-18.

##### Concerns

- **HIGH — `once`/`notice` never select a session-default injection.** The new text says to continue on the session model and records only `CONFIG_CHECK=once` or `notice` (`.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:137-146`, `:175-190`). The unchanged adapter subsequently calls `resolve-injection` (`skills/ai-kit-spec-execute-superpowers/SKILL.md:163-179`), whose candidates come from the configured roster (`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:165-189`). With no candidates, the existing CLI can return `no_candidate` (`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:189-197`), and the adapter stops on that mode (`skills/ai-kit-spec-execute-superpowers/SKILL.md:206-208`). No specified branch constructs or forces a native session-default injection. The stub tests verify the scalar, not dispatch.
- **HIGH — A prior run’s scalar can suppress a fresh decision indefinitely.** The guard accepts *any* existing `CONFIG_CHECK=` for a hash of only CWD and plan-file path (`.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:160-166`). The existing path is stable for the same plan (`skills/ai-kit-spec-execute-superpowers/SKILL.md:123-127`); the proposed plan does not distinguish a wake/resume from a new invocation or specify retirement of this new decision. A later fresh run can reuse an old `once`, `notice` or `active` after config changes without checking or asking. The existing wake path identifies a resume through a state file (`skills/ai-kit-spec-execute-superpowers/references/quota-wake.md:16-20`); the new guard does not use that evidence.
- **MEDIUM — The “nothing written” headless notice conflicts with the prescribed write.** The no-question path prints “nothing written” (`.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:145-146`) and then records `notice` by creating/appending a scalar file (`:175-186`). If the intended promise means “no config written,” say that; as written it is factually broader.
- **MEDIUM — Executor cap risk.** The plan changes six tracked files, specifies three commits, and adds a substantial shell-block test class (`.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:116-120`, `:229-233`, `:260-267`). No measured timing demonstrates completion within 1,800 seconds.

##### Suggestions

- Define an explicit session-default injection path for `once` and `notice`, including its behavior on each task and on resume; test it through `resolve-injection`/dispatch, not just the scalar file.
- Tie reuse of the recorded decision to a verified live resume, and define when a fresh plan invocation clears or replaces it. Test fresh reruns and changed config.
- Narrow the notice to “no config written” if the scalar write is intentional.

##### Risk Assessment

**HIGH** — The plan can promise session-model execution while the existing adapter stops at `no_candidate`, and its persisted guard can reuse a stale choice.

##### Ponytail findings

- **HIGH — The scalar mechanism is justified only if it carries the behavior.** Reusing the existing scalar file is simpler than introducing another state store, but recording a label without wiring the dispatch path is a half feature. Extend the existing injection/resume path and test the actual caller.

#### 36-29

##### Summary

The plan provides a structured judge-record workflow and a regression comparison, but it cannot currently start as written: it depends on two absent plan files and their summaries, and it requires a second reviewer contrary to the request’s explicit reviewer selection. Its multi-round procedure also conflicts with its own stale-digest handling.

##### Strengths

- **Uses the existing judge record machinery.** The proposed regression threshold matches `tools/judge_loop.py:1614-1635`, and the plan separately reports the computed comparison (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:180-181`).
- **Protects the review snapshot.** The plan calls for a frozen tracked tree and records lane failures rather than silently substituting a reviewer (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:89`, `:146-157`).
- **Same-wave file check.** The supplied wave map lists no other wave-11 plan.

##### Concerns

- **HIGH — Wrong reviewer pool.** The request explicitly settles on **referee-one only**, and `.planning/config.json:67-69` confirms `default_reviewers` contains only referee-one. The plan instead requires and probes both referee-one and referee-two (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:28`, `:59-60`, `:121`, `:137-139`). The existence of a referee-two instance in `.planning/config.json:58-60` does not authorize using it for this review.
- **HIGH — Missing prerequisite plans make the last wave unreachable.** The plan depends on 36-27 and 36-28 (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:6`) and requires all summaries 01–28 (`:113`). The phase directory contains plans 01–26 and 29, but no `36-27-PLAN.md` or `36-28-PLAN.md`. The research map assigns those missing plans review/adapter evals and documentation (`.planning/phases/36-spec-config-as-the-hub/36-RESEARCH.md:43-47`); 36-29 itself depends on the review evals from 36-27 (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:32`). These are not declared artifacts of another existing plan.
- **HIGH — A mixed-result second round can fail on an intentionally stale first-round fix.** Step 12 permits one skill to receive a fix commit with a deliberately stale digest while another proceeds to a later round (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:188`). The copied `check.py` checks the **round-one skill set** with `--require-current` (`tmp/judge-35/check.py:18-20`, `:33-46`), and step 3 requires that check to pass in every round (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:177-180`). A later round therefore encounters the earlier skill’s intentionally stale digest and stops.
- **MEDIUM — Scratch driver availability is an environmental dependency.** The plan copies untracked `tmp/judge-35/` drivers and, if missing, refers to recreating them from the preceding phase (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:103-105`, `:113-122`). The copied driver itself depends on `tmp/judge-34/` (`tmp/judge-35/copy_drivers.py:10-24`), and the earlier plan points further back (`.planning/phases/35-model-discovery-and-catalog/35-26-PLAN.md:93`). The workflow is not reproducible from committed inputs alone.
- **MEDIUM — Later-round deferred clearing uses the wrong set.** `clear_deferred.py` is to clear review’s deferral whenever review is absent from the current `unmet.txt` (`.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:180-182`), while later rounds restrict `skills.txt` to skills advancing (`:188`). The procedure does not specify preserving review’s prior unmet state when review is not in that later-round set.

##### Suggestions

- Make the judge pool and associated count/report checks use referee-one only, consistently throughout the plan and copied-driver checks.
- Create and review plans 36-27 and 36-28, including their wave/file interactions, before treating 36-29 as executable; alternatively, explicitly assign their required work and change dependencies.
- Scope current-digest checks to the skills being judged in the current round, while separately recording intentional stale digests from finished skills. Carry each skill’s latest bar result across rounds before changing deferral state.
- Provide a reproducible committed driver or a complete reconstruction procedure that does not depend on a chain of disposable scratch directories.

##### Risk Assessment

**HIGH** — The plan currently violates the selected reviewer constraint, has missing prerequisites, and can dead-end after a valid mixed-result round.

##### Ponytail findings

- **MEDIUM — The judge loop is required; its scratch-driver chain is fragile.** Reuse `tools/judge_loop.py` and its existing bar calculation, but remove the dependency on several generations of untracked copies. Keep the frozen-tree and record-integrity checks.

##### Status: Issues Found — fix and re-review

**Coverage:** All five manifest plans received a section. Same-wave comparisons used the supplied wave map; the absence of plans 36-27 and 36-28 limits verification of their handoffs and phase-wide edge/prohibition coverage.

**Not checked:** No test suites, make targets, external reviewers or write operations were run, as requested. The review does not establish exhaustive coverage of every SPEC edge or every referenced symbol across the other plans.

#### Batch G (36-24, 36-25, 36-26, 36-27, 36-28)

#### 36-24

##### Summary

The plan puts the required wizard questions in focused references and reuses the CLI parser for command checks. It is **not ready for unattended execution**: the proposed flow assumes every selected candidate has fields that some valid proposal paths do not provide.

##### Strengths

- The data-use confirmation precedes the usage-limit question, and a decline removes the lane (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:319-346`).
- The command-contract test reuses the existing parser-test pattern in `tests/test_spec_config_catalog_text.py:17-39`.

##### Concerns

- **HIGH — Alias and manually entered candidates lack the row fields the flow requires.** The wizard permits an owner-defined alias or a manually named model (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:157-167`), then unconditionally reads `model_id`, `efforts`, and `efforts_source`. Plan 36-13’s alias object has only `key`, `runtime`, `model_id`, `label`, and `purpose_note`, with no price or effort fields (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:137-145`). A manually entered model has no proposal row at all. The plan does not specify how either path establishes price, data-use consent, or effort support.
- **HIGH — The allowance notice comes after an effort probe can already spend the allowance.** The unknown-effort call occurs in step 5 (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:169-175`), while the notice is only required before the separate step-6 test (`:179-181`). This misses the stated “before the call” protection for that earlier real call.
- **MEDIUM — The retained code-index alternative check becomes unreachable.** The new flow follows only items 1–4 of `cli-model-selection.md` (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:144-146`), while the plan retains and renumbers the pre-finalization check as item 6 (`:211-212`). The current check is at `skills/ai-kit-spec-config/references/cli-model-selection.md:204-216`; no later call to the retained item is specified.
- **MEDIUM — Executor handoff omits the successful summary instruction.** Downstream plan 36-25 requests this plan’s summary (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:72`), but the creation instruction is only in 36-24’s `<output>` block (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:450-452`), which the stated cross-AI pipeline does not send. The objective mentions a summary only when blocked (`:99`).

##### Suggestions

- Specify a concrete candidate representation and evidence-gathering path for aliases and manually named models, including unknown price and effort handling.
- Put the allowance notice before **every** real free-lane probe, including the effort probe; explicitly handle a declined write-risk question.
- Either invoke the retained alternative check after selection or explicitly retire it with its affected tests and rationale.
- Put summary creation and its exact path inside `<objective>` or `<tasks>`.

##### Risk Assessment

**HIGH** — valid selection paths can lead to missing-field decisions, and a real probe can precede the allowance warning.

##### Ponytail findings

- **LOW — Needed and mostly reusable.** The references implement locked R3–R6 and R12–R13 behavior, and parser reuse is appropriate. The retained but unreachable check adds maintenance without delivering its existing behavior; either wire it or remove it deliberately.

---

#### 36-25

##### Summary

The skeleton, per-role config documentation, and headless stop are required, but the migration-consent path has a destructive edge case and some exact instructions conflict with the plan’s own constraints.

##### Strengths

- The stop is placed before the existing `--check-only` and snapshot-save branches (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:173-175`; existing ordering at `skills/ai-kit-spec-config/SKILL.md:84-109`).
- The plan reuses the role writer’s documented JSON example and its render-through-writer test rather than inventing a separate serialization (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:103-121`).

##### Concerns

- **HIGH — Global replacement consent bypasses the backup choice.** The existing global-target question treats “replace” as prior replacement consent, and the subsequent gate runs only when that consent has not already been given (`skills/ai-kit-spec-config/SKILL.md:154-158`). The new keep-backup option is inserted only into that later gate (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:230-231,261-266`). Thus a user selecting replacement of an old global roster may never be offered the backup option before the default deletes it.
- **HIGH — The prescribed new skill text violates the plan’s hardcoding rule.** Block T12 explicitly adds real model aliases and a concrete model ID (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:299-301`), despite the rule at `:92` limiting new model names to the specified placeholders. These names already appear in the old text (`skills/ai-kit-spec-config/SKILL.md:328-333`), but this plan replaces and writes that paragraph anew.
- **MEDIUM — The headless text claims “nothing was written” after creating scratch state.** Step 0 creates `$SCRATCH` with `mktemp -d` before detection (`skills/ai-kit-spec-config/SKILL.md:31-43`); the new headless block then says nothing was written and removes the directory (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:126-147`). The intended no-persistent-config/cache guarantee is reasonable, but the absolute claim is inaccurate and the text-only test does not exercise it.
- **MEDIUM — Successful summary creation is outside the executor payload.** Plan 36-26 reads its summary (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:54`), but the creation instruction is only in 36-25’s `<output>` (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:460-462`).

##### Suggestions

- Make the keep/delete decision available on **every** old-roster replacement route, including prior global consent; add a test for that exact branch.
- Replace newly written real model examples with the permitted placeholders, while preserving necessary runtime-selection behavior.
- Say “no config, cache, or trust record was written” and test cleanup of the owned scratch directory.
- Move the successful summary instruction into the executor-visible task.

##### Risk Assessment

**HIGH** — the global path can delete the old roster without presenting the promised backup choice.

##### Ponytail findings

- **MEDIUM — Required change, incomplete reach.** Reuse the existing replacement gate and migration switch, but cover both ways the existing global selection can reach the writer; a second independent consent mechanism is unnecessary.

---

#### 36-26

##### Summary

The new eval cases and baseline cleanup are appropriate for the rewritten skill. The plan needs a clearer execution boundary and a practical timeout check before it can be treated as reliable evidence.

##### Strengths

- The alias fixture is paired with removal of its old baseline entry (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:103-115,203-204`), matching the guard’s shrink-only design (`tests/test_arch_hardcoded_models.py:155-181`; planned extension at `.planning/phases/36-spec-config-as-the-hub/36-15-PLAN.md:110-119`).
- The six new cases address the major rewritten flows, including headless operation and data-use consent (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:138-200`).

##### Concerns

- **MEDIUM — The drift test proves matching phrases, not that the eval can execute the scenario.** The proposed assertion checks a substring in an eval assertion and concatenated Markdown (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:235-246`). The existing shape checker is likewise explicitly structural and calls no skill or model (`tests/test_skill_evals_shape.py:1-5`). In particular, the data-use case asserts both a decline and a yes path without providing either answer (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:181-189`).
- **MEDIUM — Successful summary creation is not sent to the executor.** The objective only instructs writing a summary on a block (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:70-72`); successful creation appears solely in `<output>` (`:298-300`).
- **MEDIUM — The plan sits at the stated execution-size threshold.** It changes five files (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:7-12`), runs multiple verification modules, and commits with hooks. The plan has no measured evidence that these steps fit the 1,800-second cap; that is a risk, not a demonstrated timeout.

##### Suggestions

- Give the data-use yes and decline paths separate actionable scenarios with explicit owner answers and expected final config.
- Put summary creation in the executor-visible task.
- Measure the targeted checks and commit-hook duration or split the plan if the cap is not comfortably met.

##### Risk Assessment

**MEDIUM** — the tests can pass while important interactive behavior is not actually exercised.

##### Ponytail findings

- **LOW — Needed; reuse is appropriate.** New-shape evals and the existing `tests/test_skill_evals_shape.py` are required. Keep the phrase check as a drift backstop, not as a substitute for scenario execution.

---

#### 36-27

##### Summary

The plan covers the principal chain situations for both skills and preserves routing intent, but several evals do not supply the actual filesystem state their expected commands need. Its size also exceeds the requested unattended-executor guideline.

##### Strengths

- The review and adapter cases distinguish the adapter’s lack of `--no-cross-ai` support (`.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:30-36`).
- Notice strings are checked against the planned shared block rather than copied without a comparison (`.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:370-392`; source block in `.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:128-142`).

##### Concerns

- **HIGH — Several evals describe files/configuration rather than providing them at the paths the skill reads.** For example, the “active” eval places a roster under `evals/files/active-roster/config.toml`, but expects `config-status` to read it as the project’s `.aikit/config.toml` (`.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:135-147,224-232`). The GSD case names a plan but supplies no plan file (`:182-190`), and the ambiguous case similarly names an absent document (`:202-210`). The review skill requires actual input paths and grounds the reviewer with files (`skills/ai-kit-spec-review/SKILL.md:129-145`); the shape checker only establishes that *listed* fixture paths exist (`tests/test_skill_evals_shape.py:57-65`). The expected outcomes therefore depend on an unstated fixture-installation or simulation mechanism.
- **MEDIUM — The claimed three-answer coverage does not exercise all exits.** The review no-config case selects only “once” (`.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:213-222`), and the adapter case selects setup (`:319-329`). Neither skill has an explicit “stop” answer case, nor does each exercise setup continuation and once behavior. Listing the three options is not equivalent to testing each outcome.
- **MEDIUM — Executor size exceeds the requested limit.** The plan modifies twelve paths (`.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:7-19`), more than the approximately five-file threshold, with two substantial data-generation tasks and a hooked commit. No timing evidence establishes completion within 1,800 seconds.
- **MEDIUM — Successful summary creation is outside the piped payload.** It appears only under `<output>` (`.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:444-446`), while the objective’s summary instruction addresses only a block (`:78-80`).

##### Suggestions

- Define an isolated project fixture layout and copy/setup procedure so the named document and `.aikit/config.toml` exist where the commands actually look; specify how interactive answers and absent installation are supplied.
- Add separate cases for setup, once, and stop, including no-write/no-dispatch assertions for stop.
- Split review eval conversion from adapter evals, or provide measured execution time within the cap.
- Move the summary instruction into executor-visible text.

##### Risk Assessment

**HIGH** — evals can be structurally valid while the real skill cannot reach the expected branches.

##### Ponytail findings

- **MEDIUM — Required coverage, but the fixture setup is incomplete.** Reuse the existing eval shape checker (`tests/test_skill_evals_shape.py:27-68`), while adding only the isolated filesystem and answer setup needed for meaningful execution.

---

#### 36-28

##### Summary

The top-level documentation updates are required and the new scan has a non-vacuity case. One prescribed assertion cannot pass against the prescribed output.

##### Strengths

- The plan updates the README, design record, and agent guidance together and reuses the existing config design-record fitness test (`tests/test_config_design_record.py:190-203`).
- The Markdown scan includes a planted violation (`.planning/phases/36-spec-config-as-the-hub/36-28-PLAN.md:216-218`).

##### Concerns

- **HIGH — The AGENTS.md assertion contradicts the exact replacement.** Block A1 splits `seed` and `advice text` across a newline (`.planning/phases/36-spec-config-as-the-hub/36-28-PLAN.md:135-140`), but `test_agents_names_the_seed_advice` requires the contiguous substring `seed advice text` (`:153-156`). Following both instructions makes the verification fail.
- **MEDIUM — The migration documentation overstates what happens on every verified migration.** The planned wording says the old file is deleted once the value check passes (`.planning/phases/36-spec-config-as-the-hub/36-28-PLAN.md:130-132,206-209`), while plan 36-10 explicitly preserves a changed file or a `.retiring` file on certain failures (`.planning/phases/36-spec-config-as-the-hub/36-10-PLAN.md:29-32`). The user-facing wording should distinguish the normal default from these recovery cases.
- **MEDIUM — Successful summary creation is outside the executor payload.** Only `<output>` directs it (`.planning/phases/36-spec-config-as-the-hub/36-28-PLAN.md:272-274`); the objective mentions a summary only when blocked (`:71-73`).

##### Suggestions

- Put `seed advice text` on one line or make the test whitespace-aware.
- Describe deletion as the normal verified path and mention that a changed file or deletion failure is retained and reported.
- Move summary creation into the executor-visible task.

##### Risk Assessment

**HIGH** — the exact planned test and exact planned documentation cannot both pass.

##### Ponytail findings

- **LOW — Needed; reuse the existing guard.** The documentation and scan address locked R7/R9/R11. The existing non-vacuity pattern is sufficient; the immediate fix is a one-line consistency correction rather than a new abstraction.

---

##### Cross-plan assessment

- **Same-wave files:** The manifest shows no direct `files_modified` overlap among plans 36-22, 36-23, and 36-24, or among 36-26, 36-27, and 36-28. However, several verification modules scan the shared skills tree, so concurrent partial edits can still make results timing-dependent; isolate worktrees or run whole-tree checks after the wave settles.
- **Handoff risk:** Plans 36-24 through 36-28 all put their successful `SUMMARY.md` creation in `<output>`, which the stated executor payload excludes. At least 36-25 and 36-26 explicitly depend on prior summaries. Put these instructions inside each executor-visible objective or task.
- **Coverage limitation:** I reviewed all five manifest plans and the cited dependencies, but did **not** exhaustively map every SPEC edge/prohibition across all 29 plans, verify every named symbol, or prove wall-clock timings. Those remain open checks; I have not treated them as passed.
- **Read-only verification:** No tests, make targets, writes, or scratch files were run or created. The review did not check live host behavior or network-dependent data-use sources; those remain execution-time risks.

##### Status: Issues Found — fix and re-invoke

## Cycle 2 (referee-one)

### Review conditions (cycle 2)

Cycle 2 (the last one, owner time rule): referee-one only, all 29 plans again in the same seven batches, reviewed 21:10 to 21:19 against the plans as fixed after cycle 1 (the cycle 1 triage was part of the prompt). Every finding was triaged by the orchestrator; real findings were fixed in one targeted pass by the plans' authors (checked afterwards by the plan-checker and the structural script), the rest is recorded in the ledger lines `[plan-36]`. There is no cycle 3. Findings that remain open are listed in the planning report (severity and plan); the main ones are the unmeasured 1800 s budget of the larger plans (36-01 stubs, 36-04, 36-10, 36-12, 36-13, 36-14, 36-27), the known flat-merge limit under locked decision D-04, a pi model id that ends in an effort word (accepted limit until Phase 37), and the key-only quota cache of an unchanged quota.py.

### referee-one

#### Batch A (36-03, 36-04, 36-10, 36-22)

##### Review basis

GSD implementation plans, reviewed read-only against the current source and the referenced handoffs. The findings below concern only plans **36-03, 36-04, 36-10, and 36-22**. No test suites or make targets were run.

#### 36-03

##### Summary

The read-only status command is needed for HUB-01 and has a well-specified CLI contract. The main remaining risk is that its `pending` classification does not always match what the existing migration path can actually do.

##### Strengths

- **Read-only and trust-aware by design.** The plan reuses `cfg_project_trust_bytes` and `trust.is_trusted` rather than inventing a separate trust rule (`.planning/phases/36-spec-config-as-the-hub/36-03-PLAN.md:129-134`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:456-463`).
- **Useful fixture coverage.** It covers both layers, trust, local-only, malformed input, and a scratch-tree before/after comparison (`.planning/phases/36-spec-config-as-the-hub/36-03-PLAN.md:160-180`).
- **Wave check.** Its declared wave-2 files do not overlap the declared files of 36-04, 36-05, or 36-06.

##### Concerns

- **HIGH — `pending-migration` can persist when the resolver refuses migration.** The plan marks an old roster beside a config whose `[lanes]` table has no lane as pending, including the local-only fixture (`.planning/phases/36-spec-config-as-the-hub/36-03-PLAN.md:129-133,166-174`). But `_publish_lanes` treats *any* existing `[lanes]` table that differs from the old roster as `kept-new`; it does not migrate into an empty or policy-only table (`skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py:296-304`). The downstream chain says `pending` means “continue; the trust and migration steps handle it” (`.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:134-137`). Consequently, that fixture can repeatedly report pending without reaching either setup or a completed migration.
- **MEDIUM — An active new roster hides a malformed old roster that the next resolver still reads.** The plan deliberately skips the old file whenever the new layer contains a lane (`.planning/phases/36-spec-config-as-the-hub/36-03-PLAN.md:131-132,171-172`). Normal resolution nevertheless calls migration first (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:614-625`), and migration parses the old roster before deciding that the new roster wins (`skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py:376-384`). A malformed old file can therefore produce `active` followed by a named resolver error. The current combination tests use only a valid old roster.

##### Suggestions

- Specify a status and downstream action that matches the existing `kept-new` case, and test it through both `config-status` and the subsequent resolver.
- Add a new-roster-plus-malformed-old-roster fixture and specify whether status reports the error or the downstream chain must handle it explicitly.

##### Risk Assessment

**HIGH** — The status is the control point for setup and migration; a persistent false `pending` state can prevent the user from reaching either path.

##### Ponytail findings

- **LOW — Needed and appropriately scoped.** Task 1 implements R1; Task 2 supplies the necessary behavioral coverage. Reusing the existing parser and trust helpers is preferable to a second configuration reader (`config_io.py:332-355,456-463`).
- **MEDIUM — Reachability needs an end-to-end check.** The proposed tests assert the status, but not the resolver action that follows it. The fix should cover that handoff rather than add another status abstraction.

---

#### 36-04

##### Summary

The plan implements the necessary per-role read path and addresses the previously identified cross-role key collision in the principal consumers. Its remaining issue is that later routing still uses the flat view until 36-22, so the collision test here does not establish the behavior of the actual review CLI during the intervening waves.

##### Strengths

- **Separate role lists are grounded in existing code.** `_combine_role` already merges within one role, unlike the flat cross-role merge (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:630-644,668-679`).
- **Compatibility is explicit.** The plan specifies the legacy ladder split, dangling-key warnings, duplicate handling, and a fallback for hand-built configurations (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:132-141,166-179`).
- **Wave check.** The declared files do not overlap the other wave-2 plans.

##### Concerns

- **HIGH — The new collision test bypasses CLI routing, leaving an incorrect route between waves 2 and 8.** The plan tests `quota.resolve_reviewers` directly and the adapter separately (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:177-183`). Yet the real review CLI first routes the flat `reviewers` view and overlays those decisions onto quota before it calls the resolver (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:807-830`). A project execute lane sharing a user review lane’s key can therefore cause the review lane to be skipped or assigned the execute lane’s route until 36-22 changes `_route_reviewers` (`.planning/phases/36-spec-config-as-the-hub/36-22-PLAN.md:127-129`). This matters because the plan requires a buildable, tested commit, not merely a correct final phase tree.
- **MEDIUM — `_keep` must handle valid TOML values that are unhashable.** The plan says non-string ladder entries are dropped with a warning (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:133-136`). TOML arrays can contain inline tables or arrays; an implementation using a set to track already-dropped values would raise `TypeError` instead. The specified tests cover strings and malformed tables, not unhashable ladder members (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:166-175`).

##### Suggestions

- Move the role-correct review routing change into this plan, or sequence it in the same buildable logical change; test `resolve-reviewers --cross-ai` through the CLI with distinct colliding lanes and route outcomes.
- Add a ladder containing an inline table or nested array and assert a warning rather than a crash.

##### Risk Assessment

**HIGH** — Role separation is correct at selection but not yet at the preceding routing decision.

##### Ponytail findings

- **LOW — Both tasks are required by R3.** The small pure order helper and existing `_combine_role` reuse are justified; no extra configuration surface is introduced.
- **HIGH — The smallest complete change reaches the CLI caller too.** Deferring the routing half leaves the principal review path inconsistent even though the unit-level selector passes.

---

#### 36-10

##### Summary

The migration change is required by the owner-confirmed R9 decision, and the new mutation tests improve on a simple check-then-delete. The retirement protocol still has a collision window that can overwrite a concurrent or pre-existing recovery file.

##### Strengths

- **Value checking remains ahead of source retirement.** The existing publisher validates the generated text before publishing (`skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py:290-309`), and the plan tests a failed check (`.planning/phases/36-spec-config-as-the-hub/36-10-PLAN.md:152-165`).
- **The opt-in reaches implicit migration.** Passing the setting through `_migrate` uses the shared path already called by project and user migration (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:483-509`).
- **Wave check.** No declared file overlap with 36-07, 36-08, or 36-09.

##### Concerns

- **HIGH — Retirement destination selection is not exclusive.** The plan calls `_retired_name` and then `os.rename(old, retiring)`; its recovery path similarly chooses a `.migrated` name and then renames (`.planning/phases/36-spec-config-as-the-hub/36-10-PLAN.md:127`). The existing `_retired_name` checks availability with `os.path.exists` before returning a name (`skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py:334-340`). On Linux, another process can create that destination after the check, and `os.rename` can replace it. This can destroy another retirement/recovery copy, including changed bytes. The planned tests mutate the source but do not create the selected destination between name selection and rename (`.planning/phases/36-spec-config-as-the-hub/36-10-PLAN.md:155-160`).
- **MEDIUM — Executor cannot meet Task 1’s fixture as written without an unstated setup step.** `MigrationCase.setUp` only assigns `self.project`; it does not create that directory (`tests/test_config_migrate.py:68-79`). The new test must write `LOCAL_ROSTER` before calling `migrate()` or `os.listdir(self.project)` (`.planning/phases/36-spec-config-as-the-hub/36-10-PLAN.md:121-130`). The behavior implies the roster exists, but the action should explicitly call the existing `write` helper so the unattended executor has a mechanical setup.

##### Suggestions

- Use an exclusively reserved retirement destination or another no-clobber protocol; test competing destination creation for both the delete and changed-copy recovery paths.
- State the fixture setup explicitly: `self.write(self.local_old, LOCAL_ROSTER)` before migration.

##### Risk Assessment

**HIGH** — This path intentionally deletes an unrecoverable source. A destination-overwrite race is therefore a data-retention risk, not only a cosmetic concurrency issue.

##### Ponytail findings

- **LOW — The migration and opt-in are required.** Reusing `_migrate`, the existing value check, and `MigrationCase` is appropriate (`config_io.py:483-493`; `tests/test_config_migrate.py:65-106`).
- **HIGH — Do not simplify away no-clobber protection.** The rename-and-verify machinery is justified only if it also protects the recovery destination; otherwise it adds steps without delivering the stated safety property.
- **LOW — Probe-order switch is a justified handoff.** Plan 36-20 explicitly requires that switch before removing the flat ladder (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:108`).

---

#### 36-22

##### Summary

The plan correctly recognizes that routing and probing must use role-specific lane records, and it improves the consent listing. Its shared-key policy, however, can make an explicit execute probe run a different review command, and the cache cannot distinguish those two lanes.

##### Strengths

- **The consent snippet and probe share lane selection.** The plan uses `_probe_lanes` in both places and tests the printed model and command (`.planning/phases/36-spec-config-as-the-hub/36-22-PLAN.md:126-130,152-165`).
- **The check-only quota-spend statement is qualified by the throwaway cache.** The existing cache reuses entries only within the supplied quota data (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:287-303`).
- **Wave check.** The declared files do not overlap 36-23 or 36-24; the required role-order and CLI predecessors are named directly or transitively.

##### Concerns

- **HIGH — `--role execute` can execute the review command instead of the requested execute lane.** The prescribed helper always selects `review.get(key) or execute.get(key)`, even for `--role execute` (`.planning/phases/36-spec-config-as-the-hub/36-22-PLAN.md:121,127`). For a review custom command and a different execute command sharing a key, the execute-only request runs the review command. A warning does not make the resulting quota observation evidence about the execute lane; the plan’s objective says the probe names the exact lane for the role asked (`.planning/phases/36-spec-config-as-the-hub/36-22-PLAN.md:63-66`). This is particularly consequential because custom probes invoke the configured command (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:247-253`).
- **HIGH — Key-only quota reuse can apply one lane’s result to another.** `refresh_quota_cache` reuses a fresh record by key without comparing runtime, model, or command (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:287-303`). The plan permits distinct role lanes with the same key and writes only one record (`.planning/phases/36-spec-config-as-the-hub/36-22-PLAN.md:23-26`). A review lane’s cached available/unavailable result is therefore not a valid quota result for a different execute lane, nor necessarily for a lane changed under the same key. The proposed warning tests argv but not cache identity or reuse.

##### Suggestions

- For an execute-only request, probe the execute lane or explicitly refuse the ambiguous probe without launching a different command. For `both`, define how distinct same-key lanes are represented rather than reporting one lane’s result as the other’s.
- Bind cached observations to lane identity, or otherwise prevent reuse across differing runtime/model/command identities; add tests with a pre-existing fresh row and a shared key.

##### Risk Assessment

**HIGH** — The current design can run a command other than the requested lane and can present another lane’s quota as its own.

##### Ponytail findings

- **LOW — Both tasks are needed for the per-role probe and consent handoff.** Reusing `routing.probe_keys` and the existing probe seam is appropriate (`skills/ai-kit-spec-review/ai_kit_spec/routing.py:182-185`; `quota.py:247-253`).
- **HIGH — Role separation must include cache identity.** Reusing the existing key-only cache unchanged is smaller, but incomplete when the same key denotes different executable lanes.

##### Status: Issues Found — fix and re-invoke

**Not checked:** No test suites, make targets, live hosts, or filesystem mutation were run; verification here is source and plan inspection. The wider phase’s complete edge/prohibition coverage and every named path were not exhaustively audited in this four-plan batch.

#### Batch B (36-06, 36-07, 36-09, 36-13)

#### 36-06

**Summary.** The pool module is needed for the locked proposal rules and gives later plans a shared, testable set of rows. Its filtering design largely reuses the existing catalog report. One malformed-snapshot path remains insufficiently guarded.

**Strengths**
- Reuses `catalog_report.usability_state`, `stale_state`, and `stale_providers` rather than duplicating their definitions (`skills/ai-kit-spec-review/ai_kit_spec/catalog_report.py:81–112`, `:122–137`).
- The revised `checked_fact` type-checks labels before invoking the existing fact validator, and tests malformed facts (`.planning/phases/36-spec-config-as-the-hub/36-06-PLAN.md:107–109`, `:117`).

**Concerns**
- **MEDIUM — Malformed snapshot can crash a fresh proposal.** The plan passes each snapshot CLI record directly to `catalog_report.stale_providers` (`.planning/phases/36-spec-config-as-the-hub/36-06-PLAN.md:151–152`). That helper checks the listing state but then iterates `cli_row["models"]` without confirming it is a list (`skills/ai-kit-spec-review/ai_kit_spec/catalog_report.py:96–112`). For `{"listing": "ok", "models": null}`, it raises `TypeError`. The planned `snapshot_cli` only validates the enclosing dictionaries (`36-06-PLAN.md:116`). This matters for the hand-edited/corrupt snapshot boundary, though normal detected listings use lists.

**Suggestions**
- Guard the `models` value before calling `stale_providers`, or harden the shared helper with a targeted test. An invalid listing should be “not checked,” not evidence of staleness.

**Risk assessment: MEDIUM.** Normal catalog inputs are well covered; a malformed listing can prevent the proposal entirely.

##### Ponytail findings
- **LOW — Needed, with reuse:** all three tasks implement R6 grouping and filtering; the `catalog_report` reuse is appropriate. The plan declares its new module and stub test, and I found no same-wave file overlap in the supplied wave map.

#### 36-07

**Summary.** The price and data-use modules implement required free-lane behavior and appropriately separate price evidence from the owner’s usage-limit answer. The multi-tier price display can, however, report a misleading figure.

**Strengths**
- `checked_fact` reuse and provider-scoped cost-band handling avoid treating an unrelated provider’s band as a host price (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:119–121`).
- Data-use validation reuses the existing secret-shape scanner (`skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:94–103`) and keeps an unknown value distinct from a safe value.

**Concerns**
- **MEDIUM — A nonzero multi-tier price can be displayed as zero.** `_host_reading` must classify the whole record as nonzero if *any* tier is positive, but return figures from the *first* numeric tier (`.planning/phases/36-spec-config-as-the-hub/36-07-PLAN.md:118–121`). Thus `[{"input": 0, "output": 0}, {"input": 2, "output": 2}]` yields state `nonzero` with displayed figures `0, 0`. The planned test checks only the state (`36-07-PLAN.md:147`), despite the source parser retaining all cost items (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:829–837`). The row gives the owner contradictory pricing evidence.

**Suggestions**
- Preserve tier-specific figures, or select and label a positive tier for a nonzero reading; test the displayed figures as well as the state.

**Risk assessment: MEDIUM.** The state keeps this example out of the free group, but the displayed evidence is misleading.

##### Ponytail findings
- **LOW — Needed, with reuse:** Tasks 1–2 implement sourced price and pool rules; Task 3 implements the data-use consistency contract. The shared `secret_shapes` functions are the right existing mechanism. No same-wave file overlap is apparent from the wave map; plan 36-06 is an explicit dependency.

#### 36-09

**Summary.** The plan implements the agreed bounded jev seam while retaining the existing scorer and keeping item text to closed facts. Its fallback behavior needs one more malformed-answer boundary check.

**Strengths**
- Uses the existing jev client and answer mapping instead of introducing another lookup copy (`skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:108–158`, `:186–198`).
- The plan tests low, missing, timed-out and raising judge responses, plus closed-fact payloads (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:152–164`).

**Concerns**
- **MEDIUM — Answer parsing errors occur outside the planned fallback boundary.** The plan catches exceptions around `judge(...)`, then maps and interprets answers afterward (`.planning/phases/36-spec-config-as-the-hub/36-09-PLAN.md:130–131`). A judge returning a malformed element such as `None`, a short tuple, or an unhashable reason can raise during unpacking or `_ANSWER_REASONS.get`, rather than giving the promised scorer fallback. The existing subprocess seam normally returns triples (`skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:127–158`), but the injected judge is explicitly an interface and the plan claims malformed answers degrade safely (`36-09-PLAN.md:223–225`).
- **MEDIUM — Numeric sanitization does not cover very large JSON integers.** The plan relies on `catalog_bands.is_num` for every score input (`36-09-PLAN.md:128`), but that helper calls `math.isfinite(value)` directly (`skills/ai-kit-spec-review/ai_kit_spec/catalog_bands.py:23–28`). A sufficiently large integer can raise `OverflowError` during conversion rather than being treated as missing. The planned malformed-number test covers strings, booleans and a negative context, not this case (`36-09-PLAN.md:157`).

**Suggestions**
- Validate each returned answer’s shape and types inside the fallback boundary; add a malformed-element test.
- Treat `OverflowError` from numeric validation as an invalid value and test an oversized integer without changing normal scorer behavior.

**Risk assessment: MEDIUM.** Ordinary jev responses follow the existing seam, but malformed input can defeat the stated fallback.

##### Ponytail findings
- **LOW — Needed, with reuse:** all three tasks support R6’s ranked proposal and advisory jev behavior. Reusing `model_ranker.score_candidates` (`skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:266–296`) and `jev_names` avoids a second scoring or client stack. No same-wave file overlap is apparent; plan 36-06 is explicitly named as a dependency.

#### 36-13

**Summary.** The command stitches the earlier units into the required proposal and gives the wizard a stable, inspectable output. Its per-row effort lookup has a scaling risk for the large catalogs this command is meant to process.

**Strengths**
- Reuses the existing CLI registration pattern and injects the jev factory, so tests can avoid the real client (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:143–148`).
- Tests cover source-labelled zero-price rows, runtime filtering, alternative filters, and the no-write boundary (`36-13-PLAN.md:171–186`, `:205–211`).

**Concerns**
- **MEDIUM — Effort collection repeatedly scans the entire catalog.** `_offers` calls `offered_levels` once for every candidate and wider row (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:146`). That function rebuilds `listed_ids` from every catalog entry on each call, and its catalog lookup uses `find_runtime_key`, which sorts and searches the entries (`.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:208–213`; `skills/ai-kit-spec-review/ai_kit_spec/usability.py:45–56`). This makes a broad proposal at least quadratic in catalog size, with repeated sorting, before ranking or jev. No proposed test measures a realistic catalog. I have not established that it exceeds the executor’s cap, but it can make the interactive wizard noticeably slow.
- **MEDIUM — The command inherits the malformed-listing crash from 36-06.** Its `--runtimes-json` path accepts a dictionary snapshot (`36-13-PLAN.md:144`) and its `--detect` path passes the fresh snapshot into the pool; the latter reaches the unchecked `stale_providers` iteration described under 36-06. Add command-level coverage so this failure is not hidden by unit-only tests.

**Suggestions**
- Precompute reusable runtime-ID/effort lookup data once per proposal, or extend the existing effort helper with an indexed input; retain the current per-row output contract. Add a representative-size, non-network test or timing measurement.
- Add a command-level malformed-listing case after fixing the shared boundary.

**Risk assessment: MEDIUM.** The component interfaces are explicit, but repeated whole-catalog work and malformed input can affect the owner-facing command.

##### Ponytail findings
- **MEDIUM — Needed, but repeated work is not:** Tasks 1–3 deliver R6/R12 and use existing parsing, ranking and detection helpers; however, invoking a full-catalog effort scan for every row is avoidable. The supplied wave map shows no same-wave edits to its declared files, and the plans whose new modules it reads are explicit dependencies.

##### Review status

**Issues found — revise and re-review.** All four manifest plans received a section. I checked the supplied wave map for declared same-wave file overlap and the cited dependency relationships; I did not exhaustively verify every phase-wide edge, prohibition, or referenced path outside this batch.

No files were changed and no test suites or make targets were run. The performance concern is source-based, not a measured runtime.

#### Batch C (36-05, 36-18, 36-21)

##### Document type

GSD · implementation plans. Review is limited to the three manifest plans and their relevant handoffs.

#### 36-05

##### Summary

The plan centralizes effort formatting and write-time validation, as required by R4. The cycle-1 fix recognizes listed pi IDs when building the offer, but that information is not carried into the later probe or dispatch. In one case that creates a false acceptance, not merely the documented ignored-effort warning.

##### Strengths

- Reuses the runtime suffix definitions and existing catalog lookup rather than introducing another model parser: `skills/ai-kit-spec-review/ai_kit_spec/detection.py:95` and `skills/ai-kit-spec-review/ai_kit_spec/usability.py:45`.
- Separates listed levels from levels the runner cannot pass, with explicit refusal reasons: `.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:210`.
- The listed-ID lookup added after cycle 1 reaches both offer and write validation: `.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:213`.

##### Concerns

- **HIGH — A probe can falsely certify a listed pi model name as an effort.** The plan treats a suffix equal to the requested effort as already applied, with no `ignored` line, when `known_ids` is absent: `.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:118`, `.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:130`. Plan 36-21 calls it without known IDs and labels an answered call accepted: `.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:126`. But pi matches a *whole listed ID* before splitting a thinking suffix: `skills/ai-kit-spec-review/references/cross-ai.mjs:1299`. Thus a listed model ending in `:high`, probed with `high`, can answer as the bare model while the wizard records that effort as accepted. The documented cycle-1 residual covers a *different* requested effort, not this false-positive case.
- **MEDIUM — Invalid effort values can be echoed unsanitized.** The proposed `ignored:` message interpolates an arbitrary non-string or invalid string from a hand-edited lane: `.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:130`. Plan 36-18 prints it on dispatch and previews. A malformed value containing control characters or a key-shaped secret can therefore reach logs; `usability.sanitize_error` already provides a bounded, redacted display pattern at `skills/ai-kit-spec-review/ai_kit_spec/usability.py:15`.

##### Suggestions

- Carry authoritative listed IDs into the probe and formatting decision, and test a listed `:high` model probed with both `high` and a different level. An answer may be labeled accepted only when the requested level was actually included as an effort override.
- Sanitize and bound rejected values before displaying them, while retaining a useful reason.

##### Risk assessment

**HIGH.** An apparently successful probe can cause the wizard to persist an unverified setting.

##### Ponytail findings

- **LOW — Required scope, appropriate reuse.** The three tasks implement R4’s formatting, validation and offer requirements. Reusing `strip_model_suffix` at `skills/ai-kit-spec-review/ai_kit_spec/routing.py:123` and `find_runtime_key` avoids a parallel catalog scanner. No same-wave file overlap is declared with 36-03, 36-04 or 36-06.

#### 36-18

##### Summary

The shared constructor gives review, execute and preview paths one effort-formatting point. Its tests cover the Python wiring, but a fake runner cannot establish that the unchanged runner’s model-list preflight accepts all composed IDs.

##### Strengths

- Preserves the existing argv-list boundary and codex flag handling: `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:199`.
- Plans to print ignored-effort notices before the Node availability check: `.planning/phases/36-spec-config-as-the-hub/36-18-PLAN.md:133`.
- Covers the principal constructors and call paths in a common matrix: `.planning/phases/36-spec-config-as-the-hub/36-18-PLAN.md:163`.

##### Concerns

- **HIGH — The listed-pi-ID fix is not executable through the unchanged runner.** Plan 36-05 expects a listed ID ending in `:high` to be composed as `…:high:low`: `.planning/phases/36-spec-config-as-the-hub/36-05-PLAN.md:122`. Plan 36-18 passes no known IDs at all: `.planning/phases/36-spec-config-as-the-hub/36-18-PLAN.md:133`. Even if they were supplied, the actual runner unconditionally strips one suffix and then checks that result against the listing: `skills/ai-kit-spec-review/references/cross-ai.mjs:12733`. A fake status line and `model_id_ok` check only syntax, not that preflight or actual argument reaches pi. The plan acknowledges the missing real-runner test at `.planning/phases/36-spec-config-as-the-hub/36-18-PLAN.md:250`, but the source shows a concrete failure mode.
- **MEDIUM — Confirmed routing can be lost for listed IDs with an effort-looking suffix.** `run_runner` resolves the route using the composed model: `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:598`. The current resolver strips a suffix unconditionally before matching the catalog: `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:235`. For a genuinely listed pi ID ending in a level word, that can miss the owner-confirmed route and fall back to the runner heuristic. The planned constructor and matrix do not test this boundary: `.planning/phases/36-spec-config-as-the-hub/36-18-PLAN.md:133`.

##### Suggestions

- Specify a safe, tested behavior for a listed ID whose final component looks like a pi effort. Exercise the real runner with fake host binaries and a synthetic listing, including preflight and the host argv—not just the Python grammar and a fabricated trailer.
- Preserve the original model identity for confirmed route lookup, with a regression test for the listed-suffix case. Coordinate any runner-side change with the stated Phase 37 boundary rather than silently claiming this case works now.

##### Risk assessment

**HIGH.** The affected edge can prevent a selected lane from running or change its confirmed routing behavior. The broader runtime matrix is useful but does not detect either failure.

##### Ponytail findings

- **LOW — The shared constructor is justified.** R4 requires one form across callers, and `review_spec` already centralizes review and probe construction at `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:99`. The declared files do not overlap the other wave-6 plans, 36-17 and 36-19.

#### 36-21

##### Summary

The plan correctly guards the two effort-input paths from writing usability records and reuses the existing probe and error sanitizer. Its error extraction and evidence-file handling still allow misleading results at important boundaries.

##### Strengths

- The cycle-1 guard checks both `--effort` and an effort in `--extra-json` before a catalog write: `.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:167`.
- Reuses the existing single-call quota probe and its injectable seams: `skills/ai-kit-spec-review/ai_kit_spec/quota.py:247`.
- Reuses bounded secret-shape redaction for the selected host line: `skills/ai-kit-spec-review/ai_kit_spec/usability.py:15`.

##### Concerns

- **HIGH — A wrapper failure is classified as an effort rejection.** The plan maps every `configuration` and `real_error` to rejected: `.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:124`. Those categories include `bad_model`, `bad_prompt`, `permission_blocked`, `usage`, `crash`, `signal` and `git_error`, not just host rejection of an effort: `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:42`. The runner’s `bad_model` preflight can occur *before the host call*: `skills/ai-kit-spec-review/references/cross-ai.mjs:12733`. Filtering wrapper lines does not establish that the host rejected the level; when there is no host line, the plan explicitly displays the wrapper line as the rejection. This contradicts the stated distinction between an effort rejection and an inconclusive stop.
- **MEDIUM — The first host error can be truncated away before filtering.** The plan selects the first non-wrapper line from `probe["detail"]`: `.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:128`. But `_probe_entry` truncates the combined relayed output to 300 characters *before* returning it: `skills/ai-kit-spec-review/ai_kit_spec/quota.py:27`, `skills/ai-kit-spec-review/ai_kit_spec/quota.py:214`. Enough wrapper output means the actual first host error is unavailable, so the proposed fallback reports a wrapper line instead. The tests use short wrapper lines and do not cover that boundary.
- **MEDIUM — Explicit evidence-file errors silently become “unknown support.”** The new options are passed through `cache_read_json`: `.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:200`. That helper returns `None` for both missing and malformed files: `skills/ai-kit-spec-review/ai_kit_spec/cache.py:15`. A typo or broken explicitly supplied catalog/snapshot therefore permits the write as unknown rather than telling the owner the requested evidence was not read. The wizard’s planned render command also does not pass the proposal’s explicit evidence paths: `.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:248`.

##### Suggestions

- Preserve enough runner status or host-error provenance to distinguish an effort rejection from preflight and infrastructure failures; classify failures without that evidence as inconclusive. Add a fake-runner `bad_model` case proving no host was invoked.
- Capture the first host line before the aggregate detail limit, then sanitize and bound it; test wrapper output longer than 300 characters.
- Fail visibly for an unreadable explicitly supplied evidence path, and make the wizard pass the same catalog and snapshot used for its proposal. Keep the intentional “no cached evidence means unknown” behavior distinct.

##### Risk assessment

**HIGH.** The wizard can tell the owner that an effort was rejected when no effort-bearing host call occurred; evidence failures can also evade the intended write-time check.

##### Ponytail findings

- **MEDIUM — Reuse is appropriate, but the existing probe result is too lossy for the promised diagnostic.** The issue is not a need for a second sanitizer; it is preserving provenance before `quota.py` truncates detail. The declared wave-7 files do not overlap 36-20’s files, and 36-21’s required production dependencies are reachable through 36-18.

##### Status: Issues Found — fix and re-invoke

**Not checked:** I did not run test suites or make targets, or exhaustively audit the other 26 plans. The review was read-only; no scratch files were created.

#### Batch D (36-11, 36-17, 36-20, 36-23)

##### Document Type

GSD implementation plans · read-only review · cycle 2

#### 36-11

**Summary:** The plan implements the required lane-setting validation and reuses the existing writer and layered merge. Two details still prevent it from meeting its stated guarantees: false flags survive rendering, and one acceptance criterion contradicts the prescribed module text.

**Strengths**
- It chains effort validation into the existing validator and uses the existing rejection path rather than creating a second writer (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:125`, `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:749`).
- It makes the data-use check write-only and explicitly tests that a hand-written pooled lane can still load (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:161`–`170`).
- The model-bound merge hook is placed before the existing update, where it can remove inherited settings before applying the project entry (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:202`–`204`, `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:371`–`379`).
- No files overlap with same-wave plan 36-12 (`.planning/phases/36-spec-config-as-the-hub/36-12-PLAN.md:5`–`14`).

**Concerns**
- **HIGH — False flags are written.** The validator accepts both Boolean values, but `normalise_lane_settings` only cleans notes; it never removes false escalation or usage-limit flags (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:116`–`120`, `:166`–`170`). The existing writer retains accepted lane fields (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:782`–`804`). This contradicts the locked requirement that false flags are not written.
- **MEDIUM — Task 2 has an impossible literal acceptance criterion.** It says `lane_settings.py` must not contain `effort_source` outside `MODEL_BOUND`, but Task 1 requires a module docstring containing that exact text, and `MODEL_BOUND` is only introduced in Task 3 (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:124`, `:181`, `:202`).

**Suggestions**
- Keep false valid on load, but remove false flag keys on the write normalization path; test all three flags through `cfg_render_lanes`.
- Change the Task 2 criterion to prohibit an **effort validation implementation**, not every occurrence of the word.

**Risk assessment: HIGH.** The write behavior is a direct mismatch with the configuration contract, and the contradictory gate can halt unattended execution.

##### Ponytail findings
- **LOW:** The work is required by R5, R12 and R13 and appropriately reuses `validate_reviewer_fields`, `_cfg_partition_reviewers`, and `cfg_merge_reviewers`; no additional writer abstraction is needed.
- **MEDIUM:** The false-key fix belongs in the already-planned normalizer, with one focused writer test—not another config option.

#### 36-17

**Summary:** The plan gives later phases a single set of lane-setting readers and uses role-ordered warnings. Its warning assumptions do not match the existing execute selection pipeline, so a reader can report “no fallback” while the adapter can actually select an omitted lane.

**Strengths**
- The same-pool and flagged-lane cases are explicit, including malformed lane collections (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:118`–`127`).
- The warning hook is localized to the role-combining helper produced by 36-04, avoiding another local in `cfg_combine` (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:136`, `.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:140`).
- The AST scan includes planted non-vacuity cases (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:190`–`199`). No files overlap with same-wave plans 36-18 or 36-19.

**Concerns**
- **HIGH — “Outside the ladder is never picked” is false for execute lanes.** The warning deliberately excludes lanes absent from the execute ladder (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:127`–`137`). Plan 36-04 feeds **all** execute-role candidates to the adapter and passes the ladder as `top_n_keys` (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:138`–`141`, `:182`). The existing selector ranks unlisted candidates after listed ones rather than excluding them, and converts the ranked list into the dispatch ladder (`skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py:138`–`160`, `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:265`–`291`). Thus the warning and the proposed fallback model can disagree with actual execution.
- **MEDIUM — Duplicate fallback candidates do not consistently keep their first place.** `lane_fallback` skips duplicate copies only when their key is the *source* key. An earlier flagged or same-pool `B` followed by an unflagged duplicate `B` can be returned as the fallback, contrary to the first-occurrence rule (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:123`, `:133`–`135`). The planned test covers only a duplicate of `A`, not of a candidate.

**Suggestions**
- Align the warning’s input with actual execute selection, or change execute selection to enforce the declared order; add an integration test with an omitted unflagged execute lane.
- Deduplicate candidate keys before checking their eligibility and test a duplicate whose later copy changes the flag or pool.

**Risk assessment: HIGH.** The warning affects an owner decision about quota fallback, but it can describe a different candidate set from the adapter’s.

##### Ponytail findings
- **MEDIUM:** The readers and warning are required, and `role_orders.ordered_lanes` is the right existing helper for an order-enforced path. First reconcile that path with the adapter rather than adding another warning-specific ordering rule.
- **LOW:** The source guard reuses the AST pattern cited by the plan; its non-vacuity cases are worthwhile.

#### 36-20

**Summary:** The plan covers the per-role writer and reuses the TOML splicer. Its writer warning inherits 36-17’s incorrect assumption about execute lanes, and the prescribed Task 1 verification conflicts with an earlier plan’s still-active test.

**Strengths**
- It splits parent policy keys from child role tables instead of passing nested tables to `set_table`; the existing splicer explicitly excludes child-table keys when editing a parent (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:127`–`130`, `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py:451`–`462`).
- It tests legacy rewrite, inline tables, dangling keys, duplicate order keys and byte preservation (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:156`–`169`).
- The plan names 36-10 as a dependency and checks the moved `probe-quota` switch before editing (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:6`, `:108`). There is no file overlap with same-wave 36-21.

**Concerns**
- **HIGH — Task 1’s gate runs before the warning implementation but includes a test that later becomes incompatible.** Plan 36-17’s Task 1 adds a reader warning for a flagged lane in the written order (`.planning/phases/36-spec-config-as-the-hub/36-17-PLAN.md:125`–`138`). Here Task 1’s verify includes `tests.test_lane_settings`, but the writer warning is not added until Task 3 (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:136`–`138`, `:181`–`198`). In particular, the earlier plan’s round-trip test expects empty stderr for a flagged lane with **no policy order** (`.planning/phases/36-spec-config-as-the-hub/36-11-PLAN.md:160`), while this plan’s final warning also processes only an explicit written order. This leaves the required “every preview” warning untested and absent for such hand-built writer input; the executor cannot fix it without deciding how an omitted order is interpreted.
- **HIGH — The warning assumes omitted execute lanes cannot be selected.** The writer intentionally warns when an unflagged execute lane is outside the written order (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:192`–`197`), but the selector retains unlisted execute candidates as described under 36-17. The warning can therefore be false.
- **MEDIUM — Broad write validation is not covered by the stated fallback test.** A role table whose valid entries all disappear is removed by design (`.planning/phases/36-spec-config-as-the-hub/36-20-PLAN.md:127`), but the tests do not establish what happens to a flagged role with no supplied order. The reader also produces an empty order when no role table or legacy ladder exists (`.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:135`–`138`).

**Suggestions**
- Specify and test the no-order case end to end: writer output, reader warning and actual execute selection. Keep the reader and writer warnings identical for that case.
- Resolve the execute candidate-set discrepancy jointly with 36-17 before pinning the warning text.

**Risk assessment: HIGH.** The central writer design is grounded, but the no-fallback guarantee is not reliable across writer, reader and execution.

##### Ponytail findings
- **LOW:** The per-role splice is required by R3 and appropriately reuses `toml_splice.set_table`, `remove_table`, and the existing post-splice comparison (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:898`–`905`, `:931`–`934`).
- **MEDIUM:** Avoid a separate writer-only interpretation of eligibility; reuse a single reconciled role-selection rule.

#### 36-23

**Summary:** The plan usefully ties its example to the real renderer and narrows the herdr check to the specified commands. Its executable comparison, however, leaves an important wizard probe path untested and contains a portability hazard in the fake-herdr setup.

**Strengths**
- The example is parsed from the shipped documentation and rendered through `cfg_render_lanes`; it also checks that escalation flags have configured targets (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:104`–`110`, `:123`).
- It reuses the logging fake in `tests/herdr_fakes.py:12`–`29` and checks the fake itself is non-vacuous.
- The wave-8 files do not overlap with plans 36-22 or 36-24 (`.planning/phases/36-spec-config-as-the-hub/36-22-PLAN.md:5`–`10`, `.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:5`–`11`).

**Concerns**
- **MEDIUM — The identity test never exercises the effort-probe form used by the wizard.** Its only `check-reviewer` call has no `--effort` (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:152`). Plan 36-21 adds a distinct `--effort` branch and probe path (`.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:165`–`168`). Identical behavior on the ordinary branch does not prove the new probe branch is independent of herdr.
- **MEDIUM — The test relies on the inherited PATH to establish the “without herdr” case.** `_env(False)` retains `self.base_path`, rather than constructing a PATH without herdr (`.planning/phases/36-spec-config-as-the-hub/36-23-PLAN.md:152`–`153`). Although `herdr_available` returns absent when `HERDR_ENV` is unset (`skills/ai-kit-spec-review/ai_kit_spec/herdr_source.py:25`–`32`), code that accidentally invokes `herdr` directly could reach a real binary instead of the logging fake. That undermines the zero-call and no-real-host test boundary.

**Suggestions**
- Include `check-reviewer --effort` with the same fake runner and compare its output in both environments.
- Put a logging fake or a fail-closed stub on PATH in **both** cases; vary only the herdr signal and assert the log remains empty.

**Risk assessment: MEDIUM.** The documentation-to-renderer check is valuable, but the executable herdr claim is broader than the exercised paths.

##### Ponytail findings
- **LOW:** Both tasks support locked requirements and reuse existing renderer and fake-herdr helpers; no production wrapper is needed.
- **MEDIUM:** Extending the existing identity session with one probe case and a controlled PATH is smaller and stronger than a separate test harness.

##### Status: Issues Found — fix and re-review

No files were changed and no test suites were run, as requested. I checked the cited dependencies and source paths, but did not exhaustively validate every phase-wide edge row or every referenced path; the execute-order mismatch is the principal cross-plan risk.

#### Batch E (36-08, 36-12, 36-14, 36-15)

#### 36-08

##### Summary

This plan supplies the formula fact required by D-08 before routing consumes it. Its dependency on 36-04 is present, and its drift test is designed to fail rather than skip when Node is unavailable.

##### Strengths

- The runner is checked offline through its existing `--print-argv` path, which explicitly avoids migration writes: `skills/ai-kit-spec-review/references/cross-ai.mjs:12621–12639`.
- The plan reuses the hermetic runner environment and real-Node lookup in `tests/cross_ai_selftest.py:39–100`, and adds non-vacuity cases for missing and mismatched formula records: `.planning/phases/36-spec-config-as-the-hub/36-08-PLAN.md:164–179`.

##### Concerns

- **MEDIUM — The drift check proves only the prefix, not the usable execution formula.** `.planning/phases/36-spec-config-as-the-hub/36-08-PLAN.md:124–137` checks only the leading tokens. For example, the pi head ends at `--model`, while the model and subsequent execution arguments occur after it in `skills/ai-kit-spec-review/references/cross-ai.mjs:1372–1376`. A malformed or incomplete suffix could pass while the plan describes the formula as confirmed.

##### Suggestions

- Keep the small prefix mirror, but narrow the claim to **prefix and formula-presence drift**. Add a check that the expected model follows the model flag and that any other execution-critical arguments the plan relies on are present.

##### Risk assessment

**MEDIUM** — The approach is grounded in the existing runner, but the test currently gives broader confidence than its assertions warrant. No same-wave file overlap was identified from the supplied wave map.

##### Ponytail findings

- **LOW** — The mirror and offline check implement locked D-08, rather than speculative flexibility. They reuse the existing runner harness; the main simplification is to state exactly what the prefix check proves.

---

#### 36-12

##### Summary

The plan replaces the seed-flag route with the formula predicate while preserving the native route’s precedence. Its dependencies on 36-04 and 36-08 are explicit, and its scope includes the shipped snippet that otherwise would reference the removed field.

##### Strengths

- The proposed placement preserves `host_can_select` before the formula check, matching the existing route ordering in `skills/ai-kit-spec-review/ai_kit_spec/routing.py:167–179`.
- It updates the superpowers skip path as well as the route and the snippet, rather than changing the table in isolation: `.planning/phases/36-spec-config-as-the-hub/36-12-PLAN.md:132–144,178–185`.

##### Concerns

- **MEDIUM — The task instructions conflict about adding a candidate.** The executor is told never to “add … a candidate dict” in existing tests at `.planning/phases/36-spec-config-as-the-hub/36-12-PLAN.md:96`, but is then instructed to add a new `_entry(...)` row at line 142. `_entry` constructs a candidate dictionary in `tests/test_ai_kit_spec_routing.py:286–291`. The row is needed for the native-execution acceptance case, but the executor has a stop-on-conflict instruction at plan line 94.

##### Suggestions

- Explicitly exempt the specified native-route test row from the restriction, while retaining the prohibition on adding model literals or unrelated candidates.

##### Risk assessment

**MEDIUM** — The routing design is well specified, but the conflicting test-edit instruction can stop an unattended executor. No same-wave file overlap was identified from the supplied wave map.

##### Ponytail findings

- **LOW** — Both tasks are needed for D-08. They reuse `host_can_select`, `SKIP_ROUTES`, `unroutable_quota`, and the existing `skip_note` path in `skills/ai-kit-spec-review/ai_kit_spec/routing.py:45–57,188–200,224–226`; no new routing framework is needed.

---

#### 36-14

##### Summary

This plan completes the refusal-message and selection changes after 36-11 and 36-12. It exercises acceptance by config and selection before the route walk, and keeps direct dispatch’s pre-spawn refusal.

##### Strengths

- It retains the existing validator membership boundary and changes the explanation rather than expanding what can be saved: compare `.planning/phases/36-spec-config-as-the-hub/36-14-PLAN.md:180–182` with `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:712–725`.
- It uses the existing screen and route walk rather than duplicating dispatch logic: `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py:78–112` and `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:323–346`.

##### Concerns

- **MEDIUM — The plan adds checks to the excluded runtime’s existing subtest.** `.planning/phases/36-spec-config-as-the-hub/36-14-PLAN.md:138` adds two `assertNotIn` calls inside the entire existing loop, including its excluded-runtime iteration at `tests/test_ai_kit_spec.py:5299–5304`. That goes beyond changing its expected message text, despite the explicit restriction at plan line 95 and the settled no-new-assertion rule.
- **LOW — The plan exceeds the stated approximate file-count budget.** Its frontmatter lists seven modified files at `.planning/phases/36-spec-config-as-the-hub/36-14-PLAN.md:7–14`. This is a concrete executor-size risk, not proof that the 1,800-second cap will be exceeded.

##### Suggestions

- Apply the two new negative assertions only to the permitted cases, while changing the excluded case’s existing expected-message assertion only.
- If execution timing or context becomes a problem, split at the existing task boundary while keeping each commit’s production change and covering tests together.

##### Risk assessment

**MEDIUM** — The implementation path is specific, but the subtest instruction violates the stated exclusion and needs correction before unattended execution. No same-wave file overlap was identified from the supplied wave map.

##### Ponytail findings

- **LOW** — Both tasks implement R7: named factual refusals and a guard against reintroducing the seed flag. The existing validator and selection pipeline should remain the implementation points; no additional abstraction is needed.

---

#### 36-15

##### Summary

The plan extends the existing hardcoding guard rather than creating a second scanner. Its read-only preflight now checks both the expected file set and the total before updating the baseline.

##### Strengths

- The new hit kind reuses `scan_text`, the marker rules, and the shrink-only baseline comparison in `tests/test_arch_hardcoded_models.py:134–140,155–181,229–269`.
- I independently reproduced the current preflight’s **nine files and 57 hits** with a read-only calculation. The proposed stop condition is specified at `.planning/phases/36-spec-config-as-the-hub/36-15-PLAN.md:118–120`.

##### Concerns

- **LOW — The preflight pins the current snapshot, not just the rule.** `.planning/phases/36-spec-config-as-the-hub/36-15-PLAN.md:118–120` intentionally stops if an eligible hit is cleaned or added before execution. That is safe against silently baselining unexpected work, but requires the orchestrator to reconcile a legitimate source change rather than letting the executor proceed.

##### Suggestions

- Keep the fail-closed preflight. If it stops, review the reported file and hit differences before revising the expected snapshot; do not automatically baseline the difference.

##### Risk assessment

**LOW** — The plan’s guard integration and planted cases are concrete, and its current snapshot was reproducible. No same-wave file overlap was identified from the supplied wave map.

##### Ponytail findings

- **LOW** — Both tasks are required by R8 and reuse the existing scanner and baseline machinery. The temporary generator is justified by the need to preserve existing entries and avoid hand-editing 57 hits.

---

##### Review status

**Issues found — revise and re-review.** The four manifest plans were reviewed against their current on-disk text and targeted source paths. This was not an exhaustive phase-wide verification of every SPEC edge, prohibition, path, or generated listing.

**Not run:** test suites, make targets, or plan execution, as requested. No files were intentionally created or changed; the remaining risk is that unexecuted commands may expose additional failures.

#### Batch F (36-01, 36-02, 36-16, 36-19, 36-29)

#### 36-01

##### Summary

The stub-first layout is justified by the phase’s generated test-group listings and gives later plans named test modules without repeated regeneration. I found no same-wave file overlap with 36-02. **Risk: MEDIUM**, principally because the unattended execution unit is unusually broad.

##### Strengths

- The plan uses the existing test runner and listing generator rather than a second registration mechanism: `tools/run_unittest_parallel.py:113-165` and `tools/gen_test_groups.py:72-79`.
- The scoped status and commit checks avoid treating 36-02’s planning-document changes as this plan’s work: `.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:138-152`.

##### Concerns

- **MEDIUM — Oversized cross-AI execution unit.** The executor must create 17 modules, change the runner, regenerate two files, run shared-machinery hooks, and make a commit: `.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:114-140`. That is 20 tracked paths, well beyond the requested approximately-five-file sizing heuristic. This is a concrete size risk, not a claim that the 1,800-second cap will necessarily be exceeded.
- **LOW — Verification checks the stub, not the eventual drift test.** The one-second recording is appropriate for the skipped stub, but it says nothing about the real Node-based test until 36-08 replaces it: `.planning/phases/36-spec-config-as-the-hub/36-01-PLAN.md:115-125`; `.planning/phases/36-spec-config-as-the-hub/36-08-PLAN.md:23-30`.

##### Suggestions

- Preserve the single listing-generation boundary, but make the orchestrator’s execution budget account for the full 20-path operation and shared hook. Ensure 36-08 records the completed test’s actual time.

##### Ponytail findings

- **LOW — Needed, with deliberate boilerplate.** The stubs serve the locked no-listing-churn contract and reuse the existing generator; the 17 near-identical modules are temporary scaffolding rather than a new runtime abstraction. All declared generated listings are reached.

---

#### 36-02

##### Summary

This plan is needed to put the owner-accepted pool and data-use decisions into the documents later executors consume. Its exact text blocks and edge-floor check make the amendments auditable. I found no same-wave file overlap with 36-01. **Risk: MEDIUM**, because one handoff leaves contradictory acceptance text in place.

##### Strengths

- The proposed R13 record distinguishes the five mandatory fields from the conditional label and preserves `unknown` rather than presenting it as safe: `.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:164-189`.
- The existing edge-floor checker is reused rather than introducing a second coverage mechanism: `.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:119-122`.

##### Concerns

- **MEDIUM — Old fallback and warning wording remains alongside the pool amendment.** T4 explicitly replaces the first-unflagged fallback in R12 clauses (c) and (d), but the plan leaves R12’s acceptance and edge-coverage rows describing the older first-unflagged rule: `.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:114-120`, `:153-162`; the pre-amendment acceptance and ordering row are in `.planning/phases/36-spec-config-as-the-hub/36-SPEC.md` R12. A verifier following those existing rows can approve a same-pool fallback that D-21 now excludes.
- **LOW — The amendment is sizable for one unattended plan.** It requires 20 exact anchor edits across three documents and two commits: `.planning/phases/36-spec-config-as-the-hub/36-02-PLAN.md:109-123`, `:257-269`. Exact anchors help, but a mismatch intentionally stops the run.

##### Suggestions

- Amend the R12 acceptance and ordering-edge wording to explicitly incorporate the different-pool rule, while preserving the historical text as history where useful.
- Keep the same edge-floor check and add a mechanical assertion for the amended fallback wording.

##### Ponytail findings

- **LOW — Required alignment, no runtime abstraction.** The work is demanded by HUB-05/HUB-10 and reuses `edge_floor.py`; the remaining issue is completeness of the amended acceptance surface, not an argument for a smaller feature.

---

#### 36-16

##### Summary

The review-side check has a clear three-state contract and correctly separates a missing runtimes snapshot from missing lane configuration. Its dependency chain reaches 36-01 through 36-03 and 36-12; I found no direct same-wave file overlap in the manifest. **Risk: HIGH**, because the check’s global state does not establish that a reviewer exists, and its downstream eval handoff is inconsistent.

##### Strengths

- The plan reuses 36-03’s read-only `config-status` and existing session-default reviewer shape rather than adding another config reader: `.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:125-146`, `:183-198`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:110-122`.
- It specifies a visible missing-helper notice and preserves the `--no-cross-ai` short circuit: `.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:168-179`.

##### Concerns

- **HIGH — `active` can mean only execute lanes exist, so review still falls back silently.** Plan 36-03 returns `active` for a lane in *either* role: `.planning/phases/36-spec-config-as-the-hub/36-03-PLAN.md:126-134`. Plan 36-16 treats every `active` as “continue and ask nothing”: `.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:134-140`. But 36-04 deliberately changes review resolution to the review-role list: `.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:140-141`; an empty review order then reaches the existing session-default fallback in `skills/ai-kit-spec-review/ai_kit_spec/quota.py:164-190`. An execute-only roster therefore bypasses setup without explicitly choosing a session reviewer.
- **HIGH — The later eval plan cannot pass its own notice check.** The 36-16 block says `no config written`: `.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:140-145`. Its dependent 36-27 instead writes and tests `nothing written`, then expressly stops if the block lacks that exact string: `.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:255-261`, `:379-392`. This remains in the current plan text despite the cycle-1 claim.
- **MEDIUM — Missing-helper and exit behavior are only partially exercised.** The fixture tests call `config-status` and check document strings, but do not execute the review workflow’s missing-helper or non-2 failure paths: `.planning/phases/36-spec-config-as-the-hub/36-16-PLAN.md:116-128`, `:168-179`. The new block defines outcomes for state lines and exit 2, but not a nonzero exit other than 2.

##### Suggestions

- Keep the single read-only check if desired, but expose or separately check role availability and specify what review does when only execute lanes exist.
- Make 36-27 consume the exact notice from the 36-16 block and add a workflow-level missing-helper/non-2 case.

##### Ponytail findings

- **HIGH — The shared check needs the role distinction at its consumers.** Reusing `config-status` is appropriate, but treating “some lane exists” as “this role is configured” leaves the requested user-facing flow incomplete. The existing role lists in `config_io`/36-04 are the relevant source; no duplicate roster implementation is needed.

---

#### 36-19

##### Summary

The plan puts the adapter’s question before the unit start and tests its shell blocks against a stub. However, the session-model path does not fully integrate with the adapter’s existing state and dispatch instructions. I found no same-wave file overlap with 36-17 or 36-18. **Risk: HIGH**.

##### Strengths

- The new reference is placed before `fold.py start`, whose current start step can move the plan onto a unit branch: `.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:119-123`; `skills/ai-kit-spec-execute-superpowers/references/start-step.md:6-12`.
- The planned tests cover fresh versus resumed scalar handling and run both documented shell blocks against a stub: `.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:237-250`.

##### Concerns

- **HIGH — A review-only roster suppresses setup but has no execute candidate.** The shared status command reports `active` for either role, and the adapter accepts `active` without asking: `.planning/phases/36-spec-config-as-the-hub/36-03-PLAN.md:126-134`; `.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:142-148`. Plan 36-04 switches adapter selection to execute lanes, while the existing adapter emits `quota_exhausted` when there are no candidates: `.planning/phases/36-spec-config-as-the-hub/36-04-PLAN.md:140-141` and its execute-reader task; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:266-273`. The session-model branch is entered only for `once` or `notice`, not this `active` case.
- **HIGH — Session-model instructions conflict with the unchanged dispatch flow.** T8 records three scalar values and says to skip resolution, but the existing Step 2 subsequently reads `$RUN_DIR/INJECTION_JSON.json`, and Step 3’s native instructions rely on the selected model/dispatch state: `.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:285-300`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:153-179`, `:190-211`, `:245-254`. T9 also says no ladder escalation, while the unchanged Step 3 says escalation is mandatory for qualifying rounds and Claude-native dispatch may bump the model: `skills/ai-kit-spec-execute-superpowers/SKILL.md:217-229`, `:247-253`. A text-presence test does not establish a coherent execution route.
- **HIGH — The promised downstream eval handoff is not present.** 36-19 says 36-27 will test `once`, native model omission and resume/fresh behavior: `.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:29-33`. The four actual adapter evals in 36-27 cover setup, active, missing wizard and headless notice; they do not assert the `once` path, skipped resolution, omitted model, or fresh/resume behavior, and use the wrong notice: `.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:319-360`.
- **MEDIUM — Resume detection trusts any matching filename.** The new guard treats the presence of any matching JSON file plus any nonempty last scalar as a resume, without validating its contents or allowed scalar value: `.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:175-180`. The existing restore path explicitly verifies framework, plan path and task index before trusting state: `skills/ai-kit-spec-execute-superpowers/references/state-management.md:69-85`.

##### Suggestions

- Define the adapter’s behavior when only review lanes exist, using role-aware evidence.
- Specify a complete session-model dispatch path, including how it bypasses later JSON reads and both forms of escalation, then exercise a real multi-task/fix-round flow.
- Align 36-27’s exact notices and add the promised `once`, headless, resume and fresh-start evals. Validate resume identity before suppressing the question.

##### Ponytail findings

- **HIGH — The guard is needed; duplicating partial dispatch state is not enough.** Reuse the existing scalar loader and validated resume-state pattern in `skills/ai-kit-spec-execute-superpowers/SKILL.md:80-88` and `references/state-management.md:69-85`. The new path must reach every downstream consumer, not just set `INJECTION_MODE`.

---

#### 36-29

##### Summary

The judge loop is correctly marked as an orchestrator action and reuses the existing judge-record tooling. It includes explicit no-substitution and current-digest checks. **Risk: HIGH**, because the multi-round control rules are internally inconsistent and the copied lane machinery does not enforce all claimed judge coverage.

##### Strengths

- The plan scopes current-digest checks to the current round and separately records intentionally stale digests after permitted fixes: `.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:33-36`, `:121-122`.
- It derives and checks the changed skill set using the existing Git-based driver pattern: `.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:121-123`; `tmp/judge-35/judged.py:20-44`.

##### Concerns

- **HIGH — More than three findings can terminate without another round, contrary to the plan’s own rule.** The truth at `.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:31` says more than three findings go to the next round; Task 3 row (3) instead records a met bar with more than three findings and stops for that skill: `:188-189`. This also conflicts with the three-round handling described in `AGENTS.md`’s judge rule. The result depends on which instruction the orchestrator follows.
- **HIGH — The copied driver can omit a required judge without making the plan fail.** `cmd_judges` skips a missing configured instance and returns success, and `cmd_assign` slices the pool to each skill’s computed count, merely printing a warning when a second judge is unavailable: `tmp/judge-35/lanes.py:313-326`, `:391-415`. The planned loop-record check verifies only a nonempty member list and integer counts: `tmp/judge-35/loop_record_check.py:27-50`. Yet the plan describes counting findings across both judges and accepting the two named lanes: `.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:28-31`, `:138-141`. A one-member pool or a count of one can therefore leave a purported two-judge review without both verdicts.
- **MEDIUM — The 36-27 handoff can block the loop before judging begins.** 36-29 depends on all previous plans and requires all 28 summaries: `.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:6`, `:114`. The exact-notice mismatch between 36-16 and 36-27 described above makes 36-27’s own test/stop condition fail: `.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:379-392`.
- **MEDIUM — Real-config audit is narrower than its “unchanged” label.** It compares only modification times for six named paths: `.planning/phases/36-spec-config-as-the-hub/36-29-PLAN.md:124`. It cannot establish that other config paths were unchanged, nor detect every replacement that preserves an mtime. The line should not be interpreted as a comprehensive real-home integrity check.

##### Suggestions

- Make Task 3’s decision table match the stated finding-count rule and test the `met, n > 3` case.
- Before launching, require the intended two configured, usable judge identities and specify whether **each skill** must receive both; enforce the chosen contract in assignment and record checks rather than relying on a warning.
- Label the audit as an mtime check of the listed paths, and resolve the 36-27 handoff before the final wave.

##### Ponytail findings

- **MEDIUM — Reuse is appropriate, but copied machinery needs explicit gates.** `tools/judge_loop.py` and the existing drivers already provide record validation; adding checks at their assignment boundary is preferable to another judging system. The extensive scratch-driver copying is a portability risk, explicitly handled by the owner-question precondition rather than hidden.

---

##### Status: Issues Found — fix and re-invoke

**Coverage:** all five manifest plans have been reviewed. This was a targeted, read-only source-grounded review, not an exhaustive verification of every referenced symbol or every phase-wide SPEC edge. No test suites or make targets were run, and no scratch files were created.

#### Batch G (36-24, 36-25, 36-26, 36-27, 36-28)

#### 36-24

##### Summary

The plan gives the wizard an explicit, largely testable question order, but the alternative-lane procedure can miss a valid fallback and the promised “nothing written” boundary does not match the commands the flow invokes.

##### Strengths

- Separates review and execute proposals and preserves the owner’s choice rather than treating rank as selection (`.planning/phases/36-spec-config-as-the-hub/36-24-PLAN.md:150-163`).
- Places data-use consent before the remaining free-lane questions and specifies that a decline removes the lane (`36-24-PLAN.md:338-350`).
- Reuses the existing command-parser test pattern rather than introducing a second CLI grammar (`36-24-PLAN.md:293-296`; `tests/test_ai_kit_spec_check_providers.py:393-400`).

##### Concerns

- **HIGH — The alternative search excludes valid fallbacks.** The plan passes *every* flagged lane’s pool to `--avoid-pool` in one role-wide search (`36-24-PLAN.md:366-372`). The locked rule is per lane: a fallback must be outside **that lane’s** pool (`36-17-PLAN.md:29-31`). With flagged lanes in pools A and B, an unflagged lane in B can be a valid fallback for A, but the proposed search excludes it. The wizard can consequently report no candidate when one exists.
- **HIGH — The no-write promise conflicts with the flow.** The proposed text says “Nothing is written before Step 3” (`36-24-PLAN.md:140,161`), but its catalog-input step retains `confirm-model` writes (`skills/ai-kit-spec-config/references/cli-model-selection.md:63-70`), and Step 2.5’s `check-reviewer --catalog-path` records usability (`skills/ai-kit-spec-config/SKILL.md:269-276`). The owner-facing claim and the prohibition are therefore broader than the actual boundary.
- **MEDIUM — A newly added alternative is not explicitly confirmed as part of its purpose set.** The owner may add or name an alternative after the two set confirmations (`36-24-PLAN.md:161,197-203,366-372`), but the plan does not say to reconfirm the amended set or establish that the explicit “add” answer is that confirmation. This is material because the alternative is selected after the stated confirmation gate.

##### Suggestions

- Evaluate fallback availability and proposal filters separately for each flagged lane, using the same per-lane rule as `lane_fallback`; include a two-pool fixture.
- State precisely that **lane configuration** is not written before confirmation, while identifying catalog and usability writes that can happen earlier.
- Specify the confirmation semantics for an added or manually named alternative and test that path.

##### Risk Assessment

**HIGH** — The fallback procedure can mislead the owner about whether an alternative exists; the write-boundary wording also overstates the wizard’s behavior.

##### Ponytail findings

- **MEDIUM:** The references are needed for R4–R6 and R12–R13 and appropriately reuse `propose-lanes` and the parser. Reuse the existing per-lane fallback rule as the single decision mechanism rather than adding a role-wide approximation.
- **LOW:** No same-wave file overlap identified with 36-22 or 36-23 from the supplied wave map. The plan’s dependencies cover its stated command inputs.

---

#### 36-25

##### Summary

The skeleton and headless stop address the required skill flow, but the exact edits leave contradictory effort instructions and omit the evidence paths that the write-time validation plan expects the wizard to pass.

##### Strengths

- Places the headless stop before snapshot persistence and other branches (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:153-177`; current ordering in `skills/ai-kit-spec-config/SKILL.md:84-109`).
- Offers the migration backup choice at both replacement gates (`36-25-PLAN.md:239-241,271-280`).
- Keeps the existing `split_by_purpose` contract and its regression test rather than changing the role-splitting interface (`tests/test_ai_kit_spec_check_providers.py:414-421`).

##### Concerns

- **HIGH — The final skill contradicts itself about cursor effort.** The plan changes the cursor-specific instructions (`36-25-PLAN.md:243,296-303`) but leaves the earlier codex paragraph saying cursor “effort/fast/context ARE baked into the model-id string” (`skills/ai-kit-spec-config/SKILL.md:224-228`). An agent following the resulting skill receives opposite instructions for the same field.
- **HIGH — The write command does not pass the selected evidence files.** Plan 36-21 says the wizard will pass `render-toml --catalog-path` and `--runtimes-json` (`.planning/phases/36-spec-config-as-the-hub/36-21-PLAN.md:199-204`). Plan 36-25 adds only `--keep-backup` to the existing command (`36-25-PLAN.md:248`; `skills/ai-kit-spec-config/SKILL.md:393-395`). If the proposal used evidence other than the default cache, write-time validation can use different or absent evidence and accept an effort outside the list shown to the owner.
- **MEDIUM — Recovery documentation promises a later automatic finish too broadly.** The proposed config reference says an undeletable old file is kept and its migration finishes on a later read (`36-25-PLAN.md:410-411`). Plan 36-10 also describes a failed final removal that leaves a `.retiring` copy requiring manual removal (`.planning/phases/36-spec-config-as-the-hub/36-10-PLAN.md:157,247`). The reference should distinguish these recovery outcomes.

##### Suggestions

- Replace the surviving cursor-effort sentence and add a negative assertion against the old claim.
- Pass the exact catalog and snapshot used by the proposal to `render-toml`; pin the command and a mismatched-cache case.
- Document the actual warning and recovery action for each retained-file case.

##### Risk Assessment

**HIGH** — The documented write path can validate against different evidence from the proposal, and the resulting skill gives contradictory instructions.

##### Ponytail findings

- **MEDIUM:** The skeleton and focused references are required by the locked flow and line limit. Reuse 36-21’s existing validation inputs rather than creating another validation mechanism.
- **LOW:** No same-wave editing overlap identified. The dependency on 36-23 and 36-24 covers the reference files the skeleton reads.

---

#### 36-26

##### Summary

The added eval cases cover useful owner decisions, but two prescribed assertions do not describe the planned runtime behavior and can give the judge an incorrect oracle.

##### Strengths

- Splits acceptance and decline of data use into separate cases (`.planning/phases/36-spec-config-as-the-hub/36-26-PLAN.md:180-199`).
- Keeps the existing eval shape and case-ID test, and ties selected eval phrases to the skill text (`36-26-PLAN.md:213-214,245-258`; `tests/test_skill_evals_shape.py:27-68`).

##### Concerns

- **HIGH — The alias eval supplies a roster, but expects a catalog proposal.** The fixture is a Markdown rendering of a lane (`36-26-PLAN.md:107-115`), and the prompt says only that the project config holds it (`36-26-PLAN.md:125-129`). Plan 36-13 obtains aliases from catalog entries and its snapshot, not from this Markdown fixture directly (`.planning/phases/36-spec-config-as-the-hub/36-13-PLAN.md:140-147`). The case does not establish the catalog/snapshot state needed for its expected alias group. A judge may reward an invented proposal or penalize a correct run.
- **MEDIUM — The headless eval requires no file writes, although the planned skill creates scratch.** Its assertion says “writes no file” (`36-26-PLAN.md:140-146`), whereas the headless contract explicitly permits Step 0’s scratch folder and removes it afterward (`.planning/phases/36-spec-config-as-the-hub/36-25-PLAN.md:129-150`). The assertion is stronger than the intended behavior.
- **LOW — Case count is inconsistent within the plan.** The artifact says 18 cases (`36-26-PLAN.md:32-35`), while the action and acceptance criteria require 19 (`36-26-PLAN.md:213-214,223`).

##### Suggestions

- Supply a deterministic catalog and runtime snapshot, or explicitly arrange discovery from the fixture, so the alias-group expectation follows from executable inputs.
- Change the headless assertion to prohibit persistent config, cache and trust writes while allowing cleaned-up scratch.
- Correct the artifact count.

##### Risk Assessment

**MEDIUM** — The implementation can be correct while the eval or judge rejects it, and the alias case does not demonstrate the claimed path.

##### Ponytail findings

- **MEDIUM:** The eval updates are required for R10/R11. Extend the existing shape checks and proposal fixtures rather than relying on prose-only representations of runtime state.
- **LOW:** No same-wave files overlap with 36-27 or 36-28 in the supplied map; 36-25 and 36-15 are declared dependencies.

---

#### 36-27

##### Summary

The plan covers the major chain exits, but its fixture layout is not the layout the real reader consumes, so the central “active config” evals cannot establish the stated result.

##### Strengths

- Covers setup, once, stop, missing setup skill and headless behavior for both relevant skills (`.planning/phases/36-spec-config-as-the-hub/36-27-PLAN.md:256-325,403-464`).
- Aligns the adapter’s once path with native session-model dispatch rather than invoking lane resolution (`36-27-PLAN.md:455-463`; `.planning/phases/36-spec-config-as-the-hub/36-19-PLAN.md:159-163`).
- Keeps fixture files listed in eval cases, using the existing shape-check convention (`tests/test_skill_evals_shape.py:57-65,77-86`).

##### Concerns

- **HIGH — The active fixtures are not readable as project config.** The proposed files are under `project/aikit/config.toml`, with a prose instruction that `aikit/` “stands for” `.aikit/` (`36-27-PLAN.md:120-134,215-222,415-422`). The real reader constructs `<cwd>/.aikit/config.toml` (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:262-264`); no setup step copies or maps the fixture there. Running `config-status` against the named project root will not discover the stated active roster. The same problem affects `planning/` versus `.planning/` in the GSD case (`36-27-PLAN.md:225-232`).
- **HIGH — A specified test fails on the supplied setup case.** `test_config_situations_name_config_status` requires every case whose ID contains `no-config` to have an **assertion** containing `config-status` (`36-27-PLAN.md:492-498`). The review case `precise-no-config-setup-chains` has `config-status` only in `expected_output`, not in either assertion (`36-27-PLAN.md:278-285`). The plan’s own verify command therefore cannot pass unchanged.
- **MEDIUM — The adapter active fixture is not tied to the plan’s project root.** Its prompt points to a plan outside `active-execute/project` and separately names the supposed config (`36-27-PLAN.md:415-419`), without defining the working directory or arranging the file where `config-status --cwd` reads it. Even after correcting the dot-directory issue, the active-state precondition remains ambiguous.

##### Suggestions

- Define a repeatable fixture setup that copies the tracked, non-hidden source files into an isolated project’s actual `.aikit/` and `.planning/` paths before the eval; point the plan and config at that same project root.
- Add `config-status` to an assertion in the setup case, or narrow the test to the field it actually intends to inspect.
- Verify the fixture setup with the actual `config-status` command in a scratch home, not only path-string assertions.

##### Risk Assessment

**HIGH** — The stated active-config evals do not exercise the real config path, and a specified test is deterministically inconsistent with its case.

##### Ponytail findings

- **HIGH:** The evals are required, but the prose alias for hidden directories is not a substitute for the existing `cfg_local_path` reader. Reuse the reader’s real path in an isolated fixture setup.
- **MEDIUM:** This plan changes substantially more than five files (`36-27-PLAN.md:7-24`). Given the unattended 1,800-second cap, split fixture creation and eval conversion into independently verifiable units or provide measured evidence they fit. No same-wave file overlap is identified.

---

#### 36-28

##### Summary

The documentation updates cover the principal hub concepts and add a non-vacuous scan, but the migration recovery wording still conflates materially different failure cases, and the plan requires a targeted test while its own new test depends on a not-yet-updated design record.

##### Strengths

- Updates the README, design record and agent instructions together rather than leaving conflicting top-level guidance (`.planning/phases/36-spec-config-as-the-hub/36-28-PLAN.md:103-140,180-245`).
- Extends the existing refusal test module and includes a planted non-vacuity case (`36-28-PLAN.md:252-255`).
- Preserves the existing README quota-policy check (`tests/test_cross_ai_skill_text.py:235-243`).

##### Concerns

- **HIGH — Task 1’s verification cannot pass before Task 2.** Task 1 adds `TestConfigDocsText` and runs `tests.test_spec_config_flow_text` (`36-28-PLAN.md:143-160`). Its `setUp` reads the design record, but the Task 1 tests themselves only inspect README and AGENTS; that is fine. However, the preceding plan 36-25 already adds `test_skill_links_resolve`, and the broader sequence must be checked against the actual prior outputs rather than assuming all references exist. **No deterministic Task 1 failure is established from this evidence alone**; treat this as an execution check, not a blocking finding.
- **MEDIUM — Recovery prose masks where retained bytes live.** The proposed README and design wording says a changed or undeletable file is “kept and named in a warning” (`36-28-PLAN.md:131-133,190-215,240-245`). Plan 36-10 distinguishes the old pathname from a `.retiring` copy on final-removal failure and says that copy needs manual removal (`.planning/phases/36-spec-config-as-the-hub/36-10-PLAN.md:157,247`). Readers need the warning’s path and action, not an implication that every case behaves identically.
- **MEDIUM — The Markdown scan covers more than the stated cleanup ownership.** It scans every `skills/**/*.md`, including eval Markdown (`36-28-PLAN.md:252-255`), but on any hit instructs the executor to stop without editing and assumes plans 36-16, 36-19 and 36-24 own the files. The current hits are in those areas (`skills/ai-kit-spec-review/SKILL.md:246`; `skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md:34`), but the plan does not give a resolution owner if another tracked or untracked skill Markdown file is found.

##### Suggestions

- Document the retained path and manual action where the warning requires it, consistent with 36-10’s final implementation and tests.
- State whether the scan is intentionally over all eval Markdown and assign a remediation path for a hit outside the three named plans.
- Keep Task 1’s verification, but run it against the integrated preceding-wave outputs; the evidence above does **not** establish a failure.

##### Risk Assessment

**MEDIUM** — Documentation could obscure a recovery action, while the scan’s failure path can stop unattended execution without an assigned fix.

##### Ponytail findings

- **LOW:** The documentation changes are required by R7/R9/R11 and reuse the existing refusal and doc-contract test modules. No new production abstraction is proposed.
- **LOW:** No same-wave file overlap identified with 36-26 or 36-27 in the supplied map.

##### Status: Issues Found — fix and re-invoke

**Review limits:** Read-only review; no tests or make targets were run. I did not exhaustively verify every phase-wide edge or every referenced symbol, so the absence of a finding is not proof of full coverage. No scratch files were created.
