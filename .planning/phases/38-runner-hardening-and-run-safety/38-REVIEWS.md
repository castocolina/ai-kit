---
phase: 38
cycle: 1
reviewers: [referee-one]
reviewed_at: 2026-11-21T23:46:29-03:00
plans_reviewed: [38-01-PLAN.md, 38-02-PLAN.md, 38-03-PLAN.md, 38-04-PLAN.md, 38-05-PLAN.md, 38-06-PLAN.md, 38-07-PLAN.md, 38-08-PLAN.md, 38-09-PLAN.md, 38-10-PLAN.md, 38-11-PLAN.md, 38-12-PLAN.md, 38-13-PLAN.md, 38-14-PLAN.md, 38-15-PLAN.md, 38-16-PLAN.md, 38-17-PLAN.md, 38-18-PLAN.md, 38-19-PLAN.md, 38-20-PLAN.md, 38-21-PLAN.md, 38-22-PLAN.md, 38-23-PLAN.md, 38-24-PLAN.md, 38-25-PLAN.md, 38-26-PLAN.md, 38-27-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
model_sources:
  referee-one: "pinned"
---

# Cross-AI Plan Review — Phase 38

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Note: one reviewer lane only (referee-one, owner instruction 2026-11-20); its findings are single-reviewer.

## Cycle 1 (referee-one)

### Review conditions (cycle 1)

### Cycle 1 triage (orchestrator, 2026-11-21)

Every batch (A to H) was reviewed by referee-one; each planner applied the correct HIGH and MEDIUM findings and recorded one
line per finding in `tmp/p38-review/c1/dispositions-<batch>.md` (fixed / rejected with evidence / `DECISION:`). Orchestrator
decisions given to the fix passes (locked):

- Lock not taken for a reason other than EEXIST: the run proceeds with a note (the lock is advisory, like R4's in-memory baseline).
- `planSettings` and the review-argv check move above the lock and the first snapshot, so no usage error follows the lock.
- Stale-lock clearing runs under a `<lock>.clearing` mkdir mutex with a dev/ino and content re-check; invalid records are
  unreadable and never cleared.
- `--baseline` tree = `<sha>^{tree}`; stored baselines are validated; a failed ancestor probe keeps the record.
- Tracer tasks count as planned tasks (any type not starting with `checkpoint`).
- Idle expiry on a polled execute lane waits for an in-flight read; one idle seam `{ reset, recheck }` on `performance.now()`
  shared by 38-11, 38-16 and 38-19.
- Execute checks fail closed: a failed or overflowing git read on a would-be-ok run ends with `gitFailStatus()`.
- `--plan-id` ports gsd-core's subject rule; CommonMark fences; `--forbid` refuses unsafe shapes without echoing them.
- 38-05: the CLI JSON contract and the reference consumer land in one commit.
- 38-06: the gsd-core node call runs only after destination binding, via curated-config's host-first resolver; split into
  38-06 and the new 38-27.
- 38-24 owns the two curated-config SKILL.md passages about the router rule and the skipped-skill check; 38-26 decides the
  judge set by diff materiality.
- Frontmatter: 38-06 depends on 38-03 and 38-04; 38-23 on 38-01; 38-24 on 38-05, 38-23 and 38-27.

### referee-one

#### Batch B (38-04, 38-05, 38-06)

#### 38-04

**Summary.** The plan puts the router decision in the right layer and preserves the distinction between an explicit owner refusal and missing evidence. It covers all four R6 edge categories on paper and owns the R10 argument-list cleanup. It is not ready for unattended execution: Task 2 leaves an existing inventory test red, and the matrix exercises only one catalog row per runtime/model pair, so it cannot establish agreement when the callers select different rows.

##### Strengths

- The tri-state result is useful, not speculative. `resolve_route` already returns `router`, `unknown`, or `None`; the runner treats explicit `unknown` differently from falling through to name inference. The plan preserves that distinction and keeps purpose eligibility in the execute consumers. (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:252–266`; `skills/ai-kit-spec-review/references/cross-ai.mjs:2758–2775`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:89–100`.)
- Sharing the alias-source constant preserves the existing import used by `lane_pool`. The plan also reuses the existing cache writer pattern and keeps the hint-parity test rather than copying the hint list again. (`skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py:215–225`; `skills/ai-kit-spec-review/ai_kit_spec/lane_pool.py:7–11`; `tests/test_ai_kit_spec_runner_dispatch.py:1133–1148`; `tests/test_ai_kit_spec_runtimes_table.py:702–715`.)

##### Concerns

- **HIGH — Task 2 leaves its own inventory verification red.** The new predicate requires `fallback_quota is True`, but the inventory tracer feeds a cached entry with `is_router=True` and no `fallback_quota`, then asserts `router_confirmed=True`. Its fake refresh returns success without repopulating the cache. Task 2 updates the plan-edit fixture and replaces the old matrix, but misses this tracer. (`.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md:189–195`; `tests/test_curated_config_inventory.py:110–139`, `:359–378`, `:404–407`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:159–163`.)
- **MEDIUM — One predicate does not guarantee one answer if two catalog rows name the same lane.** Dispatch walks cache order until it finds a non-`None` statement; inventory takes the first matching key in sorted order without checking whether it has a statement. An unconfirmed row and a confirmed alias row for the same runtime/model can therefore disagree. The proposed matrix assigns distinct model IDs and cannot catch that. (`.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md:169–191`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:259–266`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:332–344`.)
- **MEDIUM — The older-sibling path does not fail closed as claimed.** The loader handles a missing module, but an installed older `model_heuristics` imports successfully and has no `is_confirmed_router`. The proposed call raises `AttributeError`; inventory catches only `ImportError` on this path. A completely missing sibling already fails earlier in `build_candidates`. (`.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md:189`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py:28–42`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:284–291`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:160–169`.)
- **MEDIUM — Same-wave collision and an unowned docs handoff.** 38-04 and 38-06 both modify `tests/test_curated_config_plan_edit.py` and stage the whole file. Their edits are in different regions; that helps a merge, not two commits in one checkout. Separately, 38-04 says 38-24 will recheck the router wording, but 38-24 explicitly changes only the curated skill’s exit paragraph. The current router paragraph still describes the inventory fields correctly, but does not explain the newly sufficient alias assumption. (`.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md:36`, `:95`, `:155–156`; `.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:147–148`; `.planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md:133–145`; `skills/ai-kit-gsd-curated-config/SKILL.md:108–115`.)

##### Suggestions

- Name the inventory tracer fixture in Task 2, and keep a separate missing-quota row that asserts **not confirmed**. Pin duplicate-row precedence through both consumers, or identify the enforced uniqueness invariant if duplicate rows are impossible.
- Reuse the adapter’s once-per-build sibling loading pattern. Specify what happens when the module exists but the new API does not, and test that exact case.
- Serialize the shared-file tasks or isolate their commits in separate worktrees with a named merge order. Assign the router wording to a specific docs task, or explicitly record why the current wording is sufficient.

##### Ponytail findings

- **LOW — Task 1:** Needed for R6/D-17. The tri-state rule and boolean projection earn their keep. Reuse `_write_catalog` and `_resolve`, but add one test using the shipped alias producer rather than proving only a hand-built row. (`tests/test_ai_kit_spec_runner_dispatch.py:1133–1148`; `skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py:215–225`.)
- **MEDIUM — Task 2:** Needed to reach curated-config, but do not load the same sibling module per candidate. `build_candidates` already loads its shared modules once and passes dependencies through the join context. This plan spans seven files overall, above the review’s sizing guideline, though no single task exceeds four. (`.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md:7–14`, `:189`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:284–302`.)
- **LOW — Task 3:** Required by R10/D-21 and correctly limited to returning the existing list. The inputs, flags and timeout math stay unchanged; no new wrapper or fixture is needed. (`.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md:208–232`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:269–277`.)

**Risk assessment: MEDIUM.** The design is sound, but the named Task 2 gate will fail as written, and caller parity is not yet demonstrated for competing catalog rows or mixed installation versions.

#### 38-05

**Summary.** The plan makes the right distinction between a quota owner stop and a one-shot wait. It also correctly keeps `locked` and `partial` out of quota handling. The Python status-map change can land early; the classifier’s wire-format change cannot safely land before its caller migration. The final caller instructions also classify the same result twice.

##### Strengths

- The status-name check runs before exit-code and quota handling, and the table includes a contradictory `locked` result carrying quota tokens. Preloading the reason map is safe: the drift test checks only for runner statuses missing from Python, not extra Python entries. (`.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:146–155`, `:175–197`; `tests/test_ai_kit_spec_runtimes_table.py:718–741`.)
- The plan distinguishes a present zero from a missing token, rejects booleans and floats, and leaves the persisted `quota` **reason** alone. That matters because resume exclusions drop only keys recorded with that reason; `quota_cycle` is a dispatch **class**, not a new persisted reason. (`.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:130–150`, `:216–218`; `skills/ai-kit-spec-execute-superpowers/references/state-management.md:137–145`, `:163–171`.)

##### Concerns

- **HIGH — Task 1 publishes a breaking CLI contract before its consumer is migrated.** It commits JSON output and new expectations while the shipped reference still branches on a bare class and extracts retry fields separately. The proposed unit tests can pass at that intermediate commit while the actual caller instructions are wrong. Task 3 then leaves the first classifier invocation in place and adds a second one under **Read tokens**, contrary to the one-call claim. (`.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:157–171`, `:213–220`, `:245`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:357–360`; `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:109–121`, `:164–189`.)
- **MEDIUM — The normalization adds a crash case and leaves a malformed-token precedence decision unpinned.** The old code recognizes digit strings without converting them. The proposed `int(token)` can raise `ValueError` on an overlong decimal string under the supported Python. Also, the unconditional `reason == "quota"` fallback returns `quota` for malformed tokens, despite the plan’s broader claim that negative or float tokens give `real_error`. The table only tests those malformed tokens with `reason="capacity"`. The rail that matters—malformed tokens must never schedule a wake—should hold for both reasons without a traceback. (`.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:27–30`, `:137–155`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:437–456`; `pyproject.toml:9`.)
- **MEDIUM — Task 3 misses other live instructions for the same branch.** `escalation.md` and `state-management.md` still list only `quota` and `real_error` for Step 3. The latter is where the agent learns which branch writes the pinned injection before the wake. Update the branch labels, not the persisted reason. Also make clear that exit 69 alone does not mean quota: the existing auth case is `real_error`. (`.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:203–222`; `skills/ai-kit-spec-execute-superpowers/references/escalation.md:101–109`; `skills/ai-kit-spec-execute-superpowers/references/state-management.md:188–193`; `tests/test_ai_kit_spec_superpowers.py:1048–1056`.)
- **MEDIUM — The downstream status gates rely on wave order without declaring the prerequisite.** No Wave 1 plan overlaps 38-05’s edits. Later, 38-13 and 38-18 explicitly need its Python map entries, and 38-24 tests them, but none declares 38-05 in its dependency chain as written. A partial run that omits Wave 1 cannot satisfy those gates. Task 3 also changes an operational SKILL.md branch, which 38-26’s materiality rule will select for judging; that is a required handoff, not an optional call left to the executor. (`.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:6`, `:29`; `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:6`, `:31`; `.planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md:45`, `:115`; `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:25–30`, `:156`.)

##### Suggestions

- Land the CLI, reference, SKILL.md and contract tests in one buildable change. Classify once, persist that object using the existing scalar writer, then use that one object for the branch and wake delay. On a failed or unreadable classifier result, schedule nothing.
- Test the actual reference block with a fake shim and the existing scalar loader. Assert one invocation, values surviving a fresh shell, and no wait for `locked`, exit 69, or malformed tokens. Run the CLI-output assertion across the table, not only the two selected rows.
- Pin overlong token handling, both single-token directions, and malformed input with a quota reason. Record the 38-05 prerequisite for the later status gates and the superpowers skill in the judge handoff.

##### Ponytail findings

- **MEDIUM — Task 1:** Required for R7/D-18. Reuse the existing nested-status and numeric-token logic, but normalize each token once rather than in both the class function and the object builder. Keep the existing string-returning Python entry point only as a projection if needed. (`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:424–456`; `.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:154–158`.)
- **LOW — Task 2:** Required status plumbing and a small, safe early commit. Strengthen the existing map test with `returncode=None` or a fallback code that would return a different reason without the map; the proposed 75 and 1 examples already fall back to `real_error`. (`skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:121–128`; `tests/test_ai_kit_spec_runtimes_table.py:754–771`.)
- **MEDIUM — Task 3:** Necessary caller migration, not a prose-only follow-up. Reuse `_ref_block` at its actual location and the existing scalar round-trip tests; a second regex extractor and exact occurrence counts do not prove the caller contract. The plan spans seven files overall; keep the map commit separate and make the orchestrator own the combined caller migration if it cannot fit with hooks under the task cap. (`.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:7–14`, `:208–243`; `tests/test_ai_kit_spec_superpowers.py:3289–3298`, `:3495–3523`.)

**Risk assessment: HIGH.** The intermediate commit breaks the shipped caller contract. The final plan also lacks a test proving that one classifier result controls the full wait-or-stop path.

#### 38-06

**Summary.** Calling GSD’s exported builder is the right way to remove duplicate skill-resolution rules. The plan correctly distinguishes a skip from a successful resolution that writes a note. But the proposed child does not reliably use the installation, environment, or effective runtime that apply uses. The rollout also deletes code before its dependent tests are migrated, so it cannot meet the green-commit requirement as written.

##### Strengths

- The library function takes a candidate config directly; the query verb instead loads live config. The return block is a better verdict than warning text: a trusted-root acceptance emits a note and still returns a nonempty block. (`.claude/gsd-core/bin/lib/init.cjs:3828–3853`, `:3898–3907`, `:3945–3966`.)
- Passing JSON as an argument without a shell and using the existing process-group timeout helper are appropriate. Keeping `locate`, `reference_for`, `needed_root` and the fix builders preserves responsibilities that still belong to ai-kit. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:29–32`, `:127–130`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:951–970`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:92–115`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:725–795`.)

##### Concerns

- **HIGH — The child can consult the wrong GSD install and the wrong skills directory.** Task 1 uses the generic resolver, which can fall back to HOME/PATH and omits curated-config’s host-first project-local install entries. It also inherits the process environment instead of using the environment apply resolves and passes to GSD. Task 2 supplies `plan.host` as `config.runtime`, even where the plan does not write a runtime and GSD honors an explicit project runtime. These differences can change a skip verdict. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:130`, `:166`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:21–29`, `:122–139`; `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:86–134`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:193–207`, `:450–481`; `.claude/gsd-core/bin/lib/config-loader.cjs:1096–1131`.)
- **HIGH — Apply would load project-local executable code before binding the destination.** `prepare` currently calls the Python-only skip check *before* `resolve_target` and `_config_binding_error`. Replacing that check in place with Node `require()` turns a filesystem check into executing a module selected from an inventory-derived location, before apply confirms the inventory belongs to the requested project. JSON quoting does not protect this boundary. Plan editing also needs an explicit rule for when it may load project-local code. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:127–130`, `:166`, `:232–238`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:174–207`, `:897–918`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:595–606`, `:617–631`.)
- **HIGH — The test migration is red as sequenced and misses live fixtures.** Task 2 deletes helpers whose tests remain until Task 3. In addition, the new missing-reference case specifies `value` for a `keep`, but `entry_effective_value` reads `existing`. The trusted-roots decline test at line 1198 is not in the migration list, and `_write_pair` uses a golden inventory whose filesystem has already gone away and whose paths are replaced with `<scratch>`. Patching the Node binary and module path does not restore that tree. For apply, the existing fixture uses a Codex host and supplies a separate HOME through `env_fn`; moving files to `.claude/skills` does not exercise the intended symlink check. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:156–179`, `:185–204`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:561–570`; `tests/test_curated_config_plan_edit.py:57–70`, `:1198–1221`; `tests/test_curated_config_golden.py:129–136`, `:200–207`; `tests/test_curated_config_apply.py:540–567`, `:617–629`, `:750–807`, `:2682–2795`.)
- **HIGH — The tracer and lint gates cannot prove the stated outcomes as written.** The normal parallel command hides passing-module output, so it cannot report that the named tracer skipped; a green module is not evidence that the real library answered. The prescribed `gsd_skill_verdicts` body has at least nine returns against the cap of six. Task 2 also introduces `sys.stderr` without adding `sys`; the new test instructions use `contextlib` and `mock` without naming the needed imports or reuse of the existing `redirect_stderr`. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:130–136`, `:166–168`; `tools/run_unittest_parallel.py:497–500`, `:926–933`; `pyproject.toml:70–80`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:9–17`; `tests/test_curated_config_plan_edit.py:4–13`.)
- **MEDIUM — Acceptance and disclosure gaps.** Task 3 deletes, rather than replaces, checks for symlinked roots, `~/`, overbroad roots, malformed names, and absolute paths. R9 requires equivalent cases; its ordering row also needs a multi-entry assertion, not just a retained join. Returned warnings interpolate raw reference text, yet the plan strips only a prefix and suffix and even asks for raw child stderr in the failure summary. The curated SKILL.md still promises an unconditional refusal and describes the old snapshot-only check. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:129–132`, `:156–168`, `:191–199`, `:238`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:408–410`, `:655–658`; `.claude/gsd-core/bin/lib/init.cjs:3919–3940`; `tests/test_curated_config_apply.py:2698–2746`, `:2774–2795`; `skills/ai-kit-gsd-curated-config/SKILL.md:307–318`.)
- **MEDIUM — Two same-wave collisions.** 38-06 shares `plan_io.py` with 38-03 and `tests/test_curated_config_plan_edit.py` with 38-04. The edits are in different regions, but all three plans stage whole paths. Task 3 also imports a helper from a second test module, which widens staged-test selection. The four-path plan is within the file-count guideline; the corrective fixture migration, helper deletion and hook runs make Tasks 2–3 poor candidates for the roughly 1,800-second cap unless the plan spells out a smaller, green sequence. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:8–11`, `:86`, `:147–148`, `:185–200`; `.planning/phases/38-runner-hardening-and-run-safety/38-03-PLAN.md:98–100`, `:119–131`; `.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md:155–156`; `tools/staged_mapper.py:2–12`; `AGENTS.md:185–199`.)

##### Suggestions

- Resolve and bind the trusted target before loading GSD code. Reuse apply’s resolved tools and environment; specify the corresponding trusted, project-local resolver for plan edits. Derive the runtime from the candidate config and test a host/runtime mismatch. Keep the named no-GSD note.
- Use a fake child for always-on caller, refusal and failure tests. Put the real builder tracer in the existing curated-config e2e module and require named execution evidence on a checkout where the dependency is present. Keep scratch HOME, project, and skill fixtures alive through the call; assert the precise missing-file versus containment cause.
- Migrate tests before removing their helpers, or make the switch and migration one atomic commit. Give the executor exact imports, fixture fields, a lint-budgeted split between resolution and reply parsing, and a skip-visible command. Sanitize diagnostics with the repository’s existing bounded-error pattern before printing; keep raw child stderr out of summaries. Assign the now-stale skill text to a docs task and include it in materiality detection.

##### Ponytail findings

- **MEDIUM — Task 1:** The direct builder call and bounded child are required by R9/D-20; a new gsd-core resolver is not. Reuse `host.resolve_gsd_core`, `run_in_own_group`, and the checkout-local e2e pattern rather than building a second route that the integration test patches away. (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:122–141`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:951–978`; `tests/test_curated_config_e2e.py:62–85`.)
- **MEDIUM — Task 2:** Delegation and deletion are warranted. Keep the existing fix builders; build the `(name, reference)` pairs once and reuse them for the query and message. The proposed second pass repeats inventory lookups, and its fallback calls `skip_reason`, which itself calls `locate` again. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:164–166`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py:136–167`, `:226–244`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:725–795`.)
- **HIGH — Task 3:** The apply refusal proof is necessary; deleting the old test cases without moving their behavioral assertions is not. Reuse `_tree_snapshot` and `_assert_no_writes`, keep that proof independent of a gitignored installation, and land it with the production switch. (`tests/test_curated_config_apply.py:632–644`, `:681–715`, `:2698–2795`; `.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:191–204`.)

**Risk assessment: HIGH.** As written, the plan can validate against the wrong installation and load project code before apply’s destination check. Its staged rollout also cannot stay green, and an optional integration test can conceal missing proof.

##### Batch coverage and verification limits

All three manifest plans were reviewed at `9f7a3c5`. The R6, R7 and R9 edge rows have named owners in this batch; the findings above distinguish ownership from effective proof. The R10 cleanup is split between 38-02, 38-03 and 38-04. No additional Wave 1 write collision was found in the listed files.

One phase-wide proof remains unverified: `38-09-PLAN.md` was unavailable in this checkout. 38-08 owns the harness move and runs the existing arch and render-sync modules, but 38-10 cites 38-09 for the **new** export guard. I could not confirm a durable owner for the R8 missing-export mutation, the rendered-copy smoke/refusal tests, or explicit application of the no-`.planning/` prohibition to those new tests. The existing prohibition itself is enforced in `tests/test_arch.py:979–981`, `:2335–2345`. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:24–34`, `:494`; `.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:6`, `:131`.)

This was a source-only review. No files were written and no tests, make targets, host CLIs, or live probes were run.

#### Batch E (38-13, 38-14, 38-15)

#### 38-13

**Summary.** The plan puts the execute lock before the checkout snapshot and model preflight, keeps review lanes nonblocking, and gives callers a distinct bare `locked`/75. That is the right shape for RUN-07. It is not ready for unattended execution: lock creation and child-group publication can both fail without stopping the lane, and one usage-validation path still runs after acquisition.

##### Strengths

- The lock path and atomic update reuse `stateHome`, `sha16`, and `writeCycleState` rather than inventing a separate storage convention. The lane-only spawn hook is also the right seam: the existing `noteChildPgid` runs for Git children as well as executor children. See `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:127–139,175–177` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4453–4461,4501–4513,4634–4644`.
- The bare-75 handoff is concrete. Plan 38-05 adds both Python mappings before the runner adds `locked`, and the existing drift test checks that every template status is mapped. See `.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:154–155,182–188` and `tests/test_ai_kit_spec_runtimes_table.py:718–741`.

##### Concerns

- **HIGH — An execute lane can run without the lock or without a durable child-group record.** Task 1 turns non-`EEXIST` acquisition errors into `{ ok: true }`. Task 2 logs and continues if publishing the child group fails. In the second case, a hard-killed runner can leave a live executor behind with `child_pgid: null`; 38-14 then has no recorded group to protect. There is also an interval between detached spawn and group publication. R4 permits an **in-memory baseline** when persistence fails; that does not waive R3’s lock. See `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:133,175–177`, `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:117–124`, and `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:258–275,299–303`.
- **HIGH — A late usage error takes a lock and can be masked by `locked`.** The plan acknowledges the exception in its frontmatter, but its task still acquires before `planSettings`. A declared argv missing a required effort or session slot is a real `usage` path: with a held lock it would get 75 instead of 2. The unknown-flag test only exercises the early parser. See `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:28–33,139,172` and `skills/ai-kit-spec-review/references/cross-ai.mjs:1713–1718,15026–15055`.
- **MEDIUM — The root test pins a filesystem heuristic, not the checkout identity.** The repository version walks to the nearest `.git` entry and returns the invocation directory whenever `GIT_DIR` is set. Two invocations from different directories in one explicitly configured worktree can therefore take different locks. The new fixture uses a `.git` file pointing at `/nowhere`, so it cannot prove real linked-worktree behavior. The pasted plan used Git discovery instead; 38-15 Task 3 still names that older `await` anchor. See `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:130,139,204`, `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:179`, and `skills/ai-kit-spec-review/references/cross-ai.mjs:5151–5163`.
- **MEDIUM — The prohibition tests miss the failure they claim to catch.** The held-lock test checks for no `pi ok`; the race test counts only `pi slowok`. Both would still pass if the loser ran model discovery, which the fake logs separately as `pi rpc`. The file-mode assertion covers freshly created state only, not a symlinked `locks` directory; the proposed `chmodSync` follows that link. Neither test plants a key shape or a control character in a lock diagnostic. See `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:37–43,120,131–134,170,202` and `skills/ai-kit-spec-review/references/cross-ai.mjs:6813–6826`.
- **MEDIUM — Task 2’s record probe is Linux-only, but its shard is not.** `lockpeek` unconditionally reads `/proc/self/stat`. The existing shard checks for Node and Git, not `/proc`, so that fake—and 38-15’s dependent cases—would fail on a host without `/proc`. See `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:170,178` and `tests/cross_ai_selftest.py:291–305`.

##### Suggestions

- Specify a non-spawning result for acquisition failure. For child identity, require a launch protocol that prevents checkout work before the group is durably registered, or a fail-closed recovery rule for an incomplete registration. Test publication failure and runner death during startup, not just normal SIGTERM.
- Move pure settings validation ahead of acquisition, without moving model listing. Test an invalid declared argv against a held lock; it must remain `usage` with the record unchanged.
- Use one canonical checkout resolver and test a real linked worktree, its subdirectory, and a symlink alias. In the refusal fixture assert **zero** fake runtime calls; add an unsafe state-path and a redaction case.

##### Risk Assessment

**HIGH.** The primary promise is one execute lane per checkout. The specified error paths allow exactly the overlap the feature is meant to prevent.

##### Ponytail findings

- **HIGH — Task 1:** R3 needs atomic acquisition and D-08 needs an exit backstop. Reuse `writePrivate` for the exclusive write and `exitFlushed` for the exit path; don’t treat the checkout walk as a second, weaker authority or make three literal `releaseLock()` call sites the proof of cleanup. See `skills/ai-kit-spec-review/references/cross-ai.mjs:1334–1364,4735–4738` and `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:130–156`.
- **HIGH — Task 2:** The lane-only hook is needed and is not over-engineered. Its failure result must reach supervision, not just the log; the probe should reuse the existing process-group convention without making every baseline case depend on Linux. See `skills/ai-kit-spec-review/references/cross-ai.mjs:4634–4644,4749–4755` and `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:175–178`.
- **MEDIUM — Task 3:** Reuse `runCaseProcess` and `waitFor` for deterministic contention. Starting both calls in one tick is not proof the loser reached acquisition before the winner exited: `slowok` gives it only 2.5 seconds. Hold the fake winner until the loser reports, and verify the shared call log. See `skills/ai-kit-spec-review/references/cross-ai.mjs:6518–6521,7325–7347` and `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:202–214`.

#### 38-14

**Summary.** The stale, orphan, foreign-host, and unreadable cases are the right decomposition for R3. The trouble is in the stale-clear operation: it can remove a *fresh* lock before discovering it moved the wrong record. The current tests do not prove that window is safe.

##### Strengths

- The verdict matrix separates process identity from host identity and does not use tab existence as liveness. Reusing `procStartTime` and `groupMembers` is appropriate: the latter looks for non-zombie members in the recorded group **and** session. See `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:109,115–119` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4740–4746,4766–4780`.

##### Concerns

- **HIGH — Stale recovery can temporarily remove a live owner’s lock.** A clearer can read the old record, pause, and then rename a fresh lock installed by another runner. The post-rename check notices too late: another acquire can succeed before `linkSync` restores the live owner. The plan explicitly leaves that window uncovered, and the patched test checks only the restored end state, not whether admission stayed closed throughout. See `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:123–124,182–183,231`.
- **HIGH — Invalid and unreadable are not fail-closed states.** Any JSON object passes `readLockRecord`; a same-host object missing identity fields can be judged stale, and comparing two absent `run_id` values can authorize removal. `statSync` failures all become `gone`; the synchronous read has no regular-file or size check; and a future or repeatedly refreshed mtime can keep the loop alive beyond two seconds. `lockSince` can also throw for a finite number outside the valid Date range. See `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:118–124` and `skills/ai-kit-spec-review/references/cross-ai.mjs:3391–3412,4446`.
- **HIGH — Task 3’s `ps` check is incompatible with the shard environment.** The case forces the `ps` branch and requires a non-`-` result without skipping, but the Python shard supplies a restricted PATH with Node, Git, and optional `mkfifo`, not `ps`. Also, Task 1 adds runner exports for `lockVerdict` and `lockGroupAlive` without explicitly directing the sibling to import them before running `pure-lock-verdict`. See `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:109,126–132,181–195` and `tests/cross_ai_selftest.py:60–84,266–287`.
- **MEDIUM — Liveness fallback and reread verification are incomplete.** `procReadable()` tests existence, not readability; `pidAlive` treats any signal-probe error as death; and `groupMembers` returns the same empty array if `/proc` cannot be scanned or if the group really is empty. Task 2’s 500 ms fixture can pass without testing a reread if the contender first sees the already-written record. See `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:115–121,151–155` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4712–4715,4768–4778`.

##### Suggestions

- Keep the locked rename-then-`wx` design, but serialize the identity check, rename, and replacement against **all** acquisitions for that key. Add a deterministic test that a delayed clearer cannot hide a fresh owner from a third contender.
- Validate the record version, identity fields, timestamp, and nullable group fields before any verdict. Treat unprobeable state as refusal, not death. Bound the entire reread by elapsed time and the call’s signal/deadline budget. Test malformed objects as well as empty files.
- Use a controlled `ps` fixture on scratch PATH for fallback, timeout, and absent-tool cases. Make the reader fixture acknowledge the first empty read before publishing the record. Preserve the hosted handoff to the shipped `launcherVerified`/`groupMembers` rule, not tab state.

##### Risk Assessment

**HIGH.** The current recovery can void the mutual-exclusion guarantee under contention. The fallback gate would also stop a literal executor on the normal hermetic shard path.

##### Ponytail findings

- **HIGH — Task 1:** The verdict and stale recovery are required. The rename/check/link-back sequence is extra code that still cannot prove exclusion. Keep one guarded transition and reuse the repository’s bounded-record-reading pattern rather than layering recovery onto `readOr`. See `skills/ai-kit-spec-review/references/cross-ai.mjs:3391–3412,4446` and `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:121–127`.
- **MEDIUM — Task 2:** The refusals are required; the sleeper and reread need reliable cleanup and synchronization. Put the sleeper under `c.repo` and ensure teardown runs even if status validation fails before `check`. The existing harness reaps by cwd and only invokes `check` after status validation. See `skills/ai-kit-spec-review/references/cross-ai.mjs:7403–7422,7564–7569` and `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:151–159`.
- **HIGH — Task 3:** The race and fallback proofs are necessary, but the real `ps` dependency is not. Reuse the existing fake-bin setup and test the actual missing-path and fallback outcomes. The source’s `patchRenameOnce` runs its callback **after** rename, not at the pre-rename point the new case needs. See `skills/ai-kit-spec-review/references/cross-ai.mjs:7511–7521,7604–7607` and `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:176–187`.

#### 38-15

**Summary.** The plan correctly reuses the existing checkout snapshot and keeps baseline deletion inside the lock. Its record and flag semantics are not yet safe for the watchdog and execute-check consumers. The accompanying regression checks also contain two contradictions a literal executor would encounter.

##### Strengths

- No second snapshot is needed. The existing `treeState` uses a private index and produces the composite tree signature the plan records. Keeping the baseline until `ok` and deleting it before release are the right lifecycle for fix rounds. See `skills/ai-kit-spec-review/references/cross-ai.mjs:5165–5183,5202–5221` and `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:119–125`.
- The normal handoff is explicit: 38-12 owns `baseline_replaced` formatting, 38-16 reads the effective baseline for progress, and 38-18 uses it for commit ranges and path diffs. See `.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:124–130`, `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:128–130`, and `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:129–131`.

##### Concerns

- **HIGH — `--baseline` gives downstream checks two different starting points.** The flag wins by replacing only `head`; `tree` still comes from this invocation’s fresh snapshot. If a prior round touched a forbidden path and the caller supplies a commit from before that round, 38-18 counts the prior commits but compares paths only from this invocation’s tree. A forbidden change already present at invocation can disappear from that check. The flag test adds an **empty** commit, so it cannot expose the mismatch. The flag branch also leaves the old task record unchanged on failure, so a subsequent flagless fix round may resume from a different baseline. See `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:121,184,193` and `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:129–130`.
- **HIGH — A stored baseline can pass validation without usable Git evidence.** The plan accepts any string as `head` or `tree`, ignores the record version, and accepts future timestamps. The equal-head fixture actually requires acceptance of `planted-tree`, which cannot be used as the proposed tree object ID. When the diff fails, 38-18 falls back to committed paths, losing evidence of uncommitted changes. Separately, a timed-out or failed ancestor probe is called “rebased” and overwrites otherwise usable history. See `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:149–158` and `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:126–130`.
- **HIGH — The specified regression checks cannot all pass as written.** Task 1 fills `rec.baseline` for every Git execute spawn but reruns 38-13’s `lock-record-fields`, which requires it to be `null`. After Task 2, the `ENOTDIR` fixture triggers the read-error note first; `baselineNoted` then suppresses the write-error note that Task 3 requires. See `.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:170` and `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:120–130,158,187`.
- **MEDIUM — Task identity can include more than the caller’s plan.** The plan passes composed `prompt` into `taskDigest`, but `composePrompt` adds skills and prepended guidance. For a prompt without an objective, changing that guidance can select another baseline; an earlier objective in the guidance can also win the regex. The fixture only uses a single objective and no guidance. See `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:121–125` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4463–4470,6123,14976–14986`.
- **MEDIUM — The tests overstate what they prove.** `runTwice` checks the first exit code but not the first status regex; the reuse case proves the old HEAD was retained, not that the execute verdict consumes its commits. And the bad-flag case’s “no `.json` afterward” would pass if the runner took and released a lock. See `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:150,185,188` and `skills/ai-kit-spec-review/references/cross-ai.mjs:7385–7409`.

##### Suggestions

- Give the flag a single documented contract for commit history, path comparison, and retention after failure. Preserve both the selected task baseline and the current invocation snapshot where the consumers need different facts. Test a nonempty historical change and a flagged failure followed by a flagless retry.
- Validate the version, timestamp, and actual Git object IDs before reuse. Distinguish a proven non-ancestor from an unavailable Git read; on unavailable evidence, retain the durable record and label the in-memory fallback honestly.
- Fix both contradictory assertions in the tasks that change the behavior. Hash the caller section explicitly, add a guidance/no-objective seam case, and pin actual commit consumption in 38-18.

##### Risk Assessment

**HIGH.** A mismatched or invalid baseline can omit evidence from an execute verdict, and the specified Task 1 and Task 3 checks would stop a literal unattended run before delivery.

##### Ponytail findings

- **MEDIUM — Task 1:** R4 needs two records, not two snapshots. Reuse `before` and the private index, and update the inherited fixture in the same commit. The explicit `flag` branch is temporary until Task 3 and should not create a second meaning for `tree`. See `skills/ai-kit-spec-review/references/cross-ai.mjs:5165–5183` and `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:121–130`.
- **HIGH — Task 2:** Keep the deterministic age/ancestry decision and `runTwice`, but use a real planted tree and assert the first status from `both.first`. The immediate handoff to 38-18 needs an end-to-end result test, not another copy of the coverage algorithm in this harness. See `skills/ai-kit-spec-review/references/cross-ai.mjs:7385–7409` and `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:149–160`.
- **MEDIUM — Task 3:** The flag, unborn HEAD, and dirty-index cases are required. Reuse the Git argv and private-index pattern; replace the stale `await checkoutRoot` read anchor with the actual shipped line, and test that invalid input never creates the lock directory in fresh state. See `skills/ai-kit-spec-review/references/cross-ai.mjs:5169–5183,6211` and `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:179–194`.

#### Batch assessment

**Issues found — revise before dispatch.** All three manifest plans were reviewed. Waves 8, 9, and 10 have no same-wave peer in the supplied map or the plans on disk. The direct chain is correct, but 38-13’s `locked` gate depends on 38-05’s mapping without declaring it in `depends_on`; the gate will fail if wave order is not enforced separately. The checkout could not corroborate the referenced 38-08, 38-09, or 38-21 plan files, so the harness move and hosted lock/state-home handoffs were checked against the locked map, the available downstream plans, and the shipped source—not marked verified.

The batch assigns the R3/R4 edge rows, but assignment is not proof: R3 ordering, checkout identity, stale-clear concurrency, and unreadable-record handling remain incomplete. The compound record confinement/redaction prohibition is only partially tested, and the no-listing assertion is missing. The R4 flag and fallback cases need the corrections above. I found no third-party runtime dependency, new provider/model literal, or change to the shipped hosted-record field names in these three plans; Python complexity caps do not apply to their proposed JavaScript edits.

**Executor gate risk:** All three final tasks prescribe bare `node` plus four all-files `make` targets (`38-13-PLAN.md:214–229`, `38-14-PLAN.md:191–206`, `38-15-PLAN.md:198–213`). The targets exist, and the module runner does report `FAILED (rc=…)` and return nonzero (`tools/run_unittest_parallel.py:887–901,925–933`). But only the named Bash self-test helper explicitly sets a scratch HOME; the Make targets invoke `uv run pre-commit`, so offline, pre-provisioned tooling and the scratch environment need to be explicit. Use the existing bounded Node helper and an exact offline wrapper, and avoid repeating unrelated Python gates inside each JavaScript task’s 1,800-second window. The scratch render matrix proves template/copy parity, not byte stability against the Phase 37 output (`tests/test_cross_ai_render_sync.py:179–195`). Keep an explicit old-output comparison that allows only the locked deltas.

No files were changed and no tests, make targets, or live hosts were run. The blocking risks are source-traced; runtime timing and the unavailable handoff plans remain unverified.

#### Batch F (38-16, 38-17, 38-18)

#### 38-16

**Summary — revise before execution.** This GSD plan owns RUN-03’s execute-progress check (R2). Reusing the private-index snapshot and the existing child shutdown path is sound. The main blocker is that the idle timer can still kill an executor before the Git read that would prove progress has finished.

**Strengths**

- The plan keeps background Git reads out of `current` and `currentFinalize`, which the signal handler uses to stop the lane. It also carries the background option through nested snapshots instead of writing a second tree reader. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:122–124` and `skills/ai-kit-spec-review/references/cross-ai.mjs:5165–5221,5262–5279`.
- The plan names all four R2 edge rows and both relevant prohibitions. The private-index check measures the owner’s actual `.git/index`, and the heartbeat uses the last read rather than launching Git on every heartbeat. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:22–39,133,169–171` and `skills/ai-kit-spec-review/references/cross-ai.mjs:5174–5183`.

**Concerns**

- **HIGH — Task 1: a pending or failed read can still end a silent lane.** The poller resets the clock only after its asynchronous read succeeds; it never tells `onIdle` whether a read is pending, failed, or confirmed unchanged. At the minimum one-second setting the first poll and idle expiry are due together. Starting a poll first does not make its Git result available before expiry. Task 3 does not prove the prohibition: the failure fake answers before expiry and the hang fake starts printing before expiry. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:125–132,192–201`, `.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md:119–120`, and `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:243–255`.
- **HIGH — Task 1: cleanup stops the current Git command, not the whole read.** `stop('stop')` can arrive while a successful `write-tree` is already draining. Its result can still be successful, allowing `treeState` to launch the next `ls-files`, recurse, or reach `rev-list` after the one-time walk of `bg.stops`. An exception such as private-index creation failure also rejects the poll promise, which has no rejection handler. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:122–132` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4597–4626,5174–5215`.
- **MEDIUM — Tasks 1–2: the busy-lane cadence and hosted handoff disagree with their consumers.** The plan intentionally runs a diagnostic read during continuous output; the locked R2 text and 38-23’s proposed documentation say reads happen only without output. Separately, 38-16 requires `hostedChild` to register `idleResetter`, but 38-19 tells its executor to mirror 38-11’s byte reset, which does not register that callback. A hosted silent committer can therefore still time out. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:29,125–130`, `.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:169–187`, and `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:151`.
- **MEDIUM — Tasks 1–3: some acceptance checks cannot establish what they claim.** Task 1 still requires the obsolete literal `if (opts.bg) opts.bg.stops.add(finalize);`, but the current action gives it an `else` branch. Task 2 checks for absent log lines, not absent mid-run Git reads, for review. Task 3 checks that recorded Git PIDs are gone, but does not prove a mid-run `write-tree` hit the hang branch; ordinary snapshots also record Git PIDs. The claimed “commit with unchanged tree” and “one change then stall” edges likewise have no discriminating case. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:22–25,122,145,163,193–201` and `skills/ai-kit-spec-review/references/cross-ai.mjs:6432–6455,7420–7422`.

**Suggestions**

- Specify one idle decision for both transports: recheck output after the due tree probe, let positive progress win, and do not kill on a pending or failed read. Keep the existing attempt/deadline cap. Make cancellation prevent **new** background Git spawns as well as stop the current one.
- Give the executor exact fake synchronization: record entry into the failing/hanging Git branch, keep the lane quiet past idle expiry, and assert the outcome and the specific PID. Add a HEAD-only change followed by a stall and count mid-run Git reads in review. Reconcile the chatty diagnostic cadence explicitly with the locked wording before handing it to 38-23.

**Risk assessment: HIGH.** The current plan can kill productive work and its named failure cases would not catch the key race.

##### Ponytail findings

- **HIGH — Task 1:** Keep `treeState` and `runChild.finalize`; both are needed for R2. Fix one activity/cancellation contract and carry it into 38-19 rather than adding another timer or kill path. `pollTreeRead` need not be exported unless the sibling actually calls it. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:124–136` and `skills/ai-kit-spec-review/references/cross-ai.mjs:4597–4626,5165–5221`.
- **MEDIUM — Tasks 2–3:** The cases are needed, but reuse `deadCheck` and the direct index-buffer comparison already specified by 38-15. Give the checks positive evidence rather than relying on missing logs or PIDs. See `skills/ai-kit-spec-review/references/cross-ai.mjs:7449–7457` and `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:188`.

#### 38-17

**Summary — revise the parser and flag validation.** This plan gives RUN-08 a useful pure policy layer, separate from Git and process supervision. The straightforward cases are well specified. Several ordinary input variants, however, can cause the checker to count the wrong commits, mistake code for an admission, or silently fail to apply a caller’s forbidden path.

**Strengths**

- It reuses `promptFiles` for the existing comma-list conventions and gives 38-18 the original caller text, not the composed prompt or the text cut by `taskDigest`. That fits GSD’s stdin contract and avoids turning the runner’s own instructions into tasks. See `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:29–30,119–122`, `skills/ai-kit-spec-review/references/cross-ai.mjs:4463–4470,5949–5959,14971–14986`, and `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:82–99`.
- The plan separates match policy from runtime selection, preserves CONFIG fallbacks, and labels the admission seed without claiming verified recall. The renderer’s upgrade path preserves owner-supplied CONFIG keys. See `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:161–172,265–269`, `.planning/phases/38-runner-hardening-and-run-safety/38-RESEARCH.md:169–171`, and `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:238–258`.

**Concerns**

- **HIGH — Tasks 1 and 3: plan-ID normalization accepts distinct IDs as equal.** `String(Number(d))` rounds long digit runs that the flag grammar accepts. It also strips padding from dotted or suffixed portions that GSD’s `paddedPattern` matches literally. The proposed tests cover only padding that should match. See `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:120,167,198` and `.claude/gsd-core/bin/lib/gate-evaluation-scope.cjs:109–147`.
- **HIGH — Task 2: the code-removal rule can create a false `partial`.** The fixed three-backtick matcher ends a four-backtick fence at an inner three-backtick line. Text still inside code then reaches `admissionHits` and can block completion. The tests cover only the simplest fence and span. See `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:147–150,170–172` and `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:322–324`.
- **HIGH — Task 3: `--forbid` can silently miss a path, and rejection can echo unsafe input.** `src//private.txt` and `src/./private.txt` pass validation but do not match Git’s `src/private.txt`. An invalid value is interpolated even when rejected for a control character; `main` logs `e.message` verbatim. The plan’s narrower regex also misses C1 controls covered by the existing `CONTROL_CHAR_RE`. See `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:117,201–206` and `skills/ai-kit-spec-review/references/cross-ai.mjs:6197,6273–6278,14840–14842`.
- **MEDIUM — Tasks 1–2: malformed tasks and failed runs lose useful distinctions.** `parseTasks` rejects checkpoint types only *after* adding an unchecked task for an unclosed block, so an unclosed checkpoint inflates the planned count. Repeated suffix searches for closers also rescan the input on malformed prompts. Separately, `planFindings` suppresses `task_uncovered` when there are zero commits and no answer, precisely when a failed run needs the missing-task list. Its test pins that omission, and the frontmatter incorrectly says 38-18 computes findings only inside `r.ok`. See `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:23,119,158,172` and `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:130–132`.

**Suggestions**

- Normalize only the leading digit runs the installed GSD subject rule treats as padded, using strings. Add a distinct-ID rejection case. Make the task scan forward-only and test an unclosed checkpoint next to a valid task.
- Keep the locked admission phrases; fix what counts as code. Test longer fences and multi-backtick spans. Use one canonical repo-relative spelling for forbid rules and named paths, with a safe diagnostic that does not echo rejected input. Add a runtime case in 38-18 so flag parsing alone is not mistaken for enforcing the flag.

**Risk assessment: HIGH.** These functions decide whether GSD may mark a plan done; false matches and missed matches both matter.

##### Ponytail findings

- **MEDIUM — Task 1:** The pure parser and coverage matcher are needed. Keep `promptFiles` and the shared `tag` fixture; use the existing GSD padding rule as the reference, not a second numeric interpretation. See `skills/ai-kit-spec-review/references/cross-ai.mjs:5949–5959` and `.claude/gsd-core/bin/lib/gate-evaluation-scope.cjs:109–132`.
- **LOW — Task 2:** One shared output formatter is enough. 38-12 already caps, sorts, and redacts detail arrays; keep list formatting there and pin the final output in 38-18. See `.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:123–132` and `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:169–173`.
- **MEDIUM — Task 3:** Both flags are required. Reuse `parseArgs` and `CONTROL_CHAR_RE`; 38-22/23 own discovery and docs. Prove actual enforcement and CONFIG replacement in the wired lane, not by adding another CLI layer. See `skills/ai-kit-spec-review/references/cross-ai.mjs:6197–6211,6273–6278` and `.planning/phases/38-runner-hardening-and-run-safety/38-22-PLAN.md:23–25`.

#### 38-18

**Summary — block execution until the verdict fails closed.** The plan puts the blocking decision in the right place: before the runner’s only answer write. But incomplete Git evidence can still produce exit 0. That is the exact failure RUN-08 is meant to prevent, because GSD uses the result to mark a plan complete.

**Strengths**

- The proposed `no_change` → `contract_violation` → `partial` ordering preserves D-15 and keeps an unsuccessful answer away from the SUMMARY path. The harness helper checks the **full** trailer because `statusLineOk` passes only its first group to the case regex. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:131–138`, `skills/ai-kit-spec-review/references/cross-ai.mjs:7192–7199,15140–15153`, and `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:103–119`.
- Reusing the baseline and giving the post-run Git reads `finalizeBy` rather than the lane deadline is appropriate. The owner-dirty fixture checks attribution rather than merely asserting exit 0. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:126–130,193` and `skills/ai-kit-spec-review/references/cross-ai.mjs:14994–14997,15111–15116`.

**Concerns**

- **HIGH — Task 1: unavailable evidence becomes success.** A failed `git log` returns `null` before either the forbidden-path or admission check runs. A failed end diff falls back to commit paths, losing precisely the uncommitted changes R5 must check. `main` then falls through to `ok` because neither condition established a blocker. No-Git execute calls also bypass the checker entirely, even for admissions that need no Git. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:128–132`, `skills/ai-kit-spec-review/references/cross-ai.mjs:15002–15006,15140–15153`, and `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:312–337`.
- **HIGH — Tasks 1–3: Git evidence can be incomplete even on exit 0.** `parseCommitLog` splits on a byte that can occur in Git pathnames or subjects, and strips the first newline from *every* path rather than the separator on the first path. `runChild` also keeps only the newest captured bytes and does not return an overflow indicator. The parser can therefore count an incomplete record set as valid. The simple linear-history fixture does not test merge-only changes either; the installed GSD reader treats merge diffs explicitly. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:119,126–130`, `skills/ai-kit-spec-review/references/cross-ai.mjs:4565–4574,4619–4626`, and `.claude/gsd-core/bin/lib/gate-evaluation-scope.cjs:758–770,842–848`.
- **HIGH — Task 1: SIGTERM during the new post-run reads can still publish an answer.** The only `aborting` check is **before** `await executeFindings`. The signal handler can stop a Git child, the new read can return `null`, and `main` can proceed to stdout and `ok` before the signal backstop. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:130–132` and `skills/ai-kit-spec-review/references/cross-ai.mjs:5262–5279,15118–15153`.
- **MEDIUM — Tasks 1–3: regressions are deferred to the wrong task.** Task 1 changes outcomes but Task 3 tells the executor to repair old assertions only if they pin stderr. `ladder-dirty-inside` is correctly a non-ok lane and can keep its existing status, but it does not assert the new missing-task finding. Nor is there a real owner-concurrency case: the fake spawning its own `git commit` is not an independent writer. The forbidden fixture tests a committed path only, and all blocking fixtures use one built-in runtime despite the seed prohibition’s explicit out-of-table test. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:23,143,162–170,199`, `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:639,688`, and `skills/ai-kit-spec-review/references/cross-ai.mjs:8167–8181,10616–10633`.
- **MEDIUM — Task 1: the Python prerequisite is not encoded.** 38-18 depends only on 38-17, but `partial` requires 38-05’s map change. Fixed wave order is sufficient when all waves run in sequence; dependency-based execution is not. The drift test checks every template status against the Python map. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:5–6,31`, `.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:175–188`, and `tests/test_ai_kit_spec_runtimes_table.py:718–733`.

**Suggestions**

- Distinguish “verified empty” from “unavailable” for each required input. Preserve the original failure on non-ok runs; on otherwise successful runs use the existing `git_error`/`git_timeout` vocabulary when required Git evidence cannot be obtained. Compute independent findings where possible and check `aborting` again before publishing.
- Add real-Git regressions for exact path framing, rejected truncated evidence, and merge semantics. Add a signal-during-check case, an uncommitted `--forbid` case, a two-round baseline case, and an independently made commit during a paused lane. Extend the existing `placeholder-cli-1` fixture for the seed-policy backstop.
- Put the known fixture changes in the task that introduces the behavior. Require 38-05 in the dependency or precondition; make 38-21 compare a **blocking** planned-task result across the two transports, not just `nochange` or informational findings. See `.planning/phases/38-runner-hardening-and-run-safety/38-21-PLAN.md:177–185`.

**Risk assessment: HIGH.** The current implementation can report completion when verification failed or was interrupted.

##### Ponytail findings

- **HIGH — Task 1:** The result gate is required. Reuse the existing Git failure reporting and status helpers; do not substitute commit paths for a working-tree diff. Export only `parseCommitLog` if that is the only new helper the sibling uses. See `skills/ai-kit-spec-review/references/cross-ai.mjs:5138–5146,5964–5975` and `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:126–133`.
- **MEDIUM — Task 2:** The verdict table is useful. One uncommitted forbidden edit and one failed lane with missing work cover distinct paths the current fixtures miss; no new test module is needed. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:162–170` and `skills/ai-kit-spec-review/references/cross-ai.mjs:7403–7422`.
- **LOW — Task 3:** Keep the owner-dirty and list-cap tests. Construct the owner-dirty case once; as written, its extra path assertion is redundant when `planCase` already rejects every finding line for `codes: '-'`. See `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:137,193–198`.

##### Batch checks

- **Waves and coverage.** Waves 11, 12, and 13 each have one plan; no same-wave file overlap. The sequential runner chain is appropriate. Within this batch, the unproven SPEC rows are R2 adjacency/ordering, R5 encoding/concurrency, and the out-of-table seed prohibition. R5 ordering and precision have an explicit owner in 38-12; discovery and the doc contract have owners in 38-22/23. The 38-08 source plan describes the sibling move and byte-equality gate, but `38-09-PLAN.md` was not readable at the specified path, so its promised export guard is unverified.
- **Executor isolation and timing — MEDIUM for all three plans.** The scratch scripts use PATH `node` without setting `TMPDIR`, and their standalone list and `make` commands are outside the scratch wrapper promised in the objective. Even the shipped `--self-test-list` path creates a temp root before listing. Reuse `tests/cross_ai_selftest.py:39–52,60–98,266–287` for the real Node executable and isolated env. Give the executor one exact wrapper for the remaining gates, with offline toolchain prerequisites and cleanup. The listed test modules and Make targets exist, and `tools/run_unittest_parallel.py:915–933` emits the named `FAILED` marker. Three tasks and two touched files per plan fit the structural budget, but the repeated all-files dev gates plus commit hooks have not been timed against the 1,800-second cap. See `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:121,205–218`, `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:115,210–223`, `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:124,202–215`, `skills/ai-kit-spec-review/references/cross-ai.mjs:7591–7607,14757–14759`, and `Makefile:98–113`.
- **Scope.** No new runtime package, network call, jev/herdr verb, real provider/model ID, Grok work, or Python runtime function is proposed in these three plans. The harness’s `.planning/STATE.md` fixture is inside its scratch repo. The hosted parity and live-copy re-render remain downstream; this review does not certify those plans.

**Verdict: revise all three before unattended execution.** Reviewed read-only against `9f7a3c5`; no files changed, and no test suite, make target, or live host was run.

#### Batch A (38-01, 38-02, 38-03)

#### 38-01

**Summary — GSD plan.** The split between scratch-only checks and consented live probes is right for D-23. The scratch path is not executable as specified, though, and the handoff does not reliably distinguish measurements from unverified behavior. Fix those before dispatching the spike.

##### Strengths

- The phase-specific, anchored consent check is a sound default. A missing consent line leaves four explicit `not probed` results rather than silently launching a host or treating missing evidence as an observation. I found no match in the current ledger. See [38-01-PLAN.md:130–155](.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md#L130) and `tmp/run-2026-11-19/ledger.md:326`.
- The Linux checks are tied to code that actually ships: `procStartTime` reads field 22 after the last `)`, and `buildLauncher` uses the `setsid` re-exec the spike intends to check. Keeping the probes outside the runner and test suite respects the phase’s isolation boundary. See `skills/ai-kit-spec-review/references/cross-ai.mjs:4740–4764,4798–4817`.

##### Concerns

- **HIGH — Task 1 never creates the output directory on the no-consent path.** [38-01-PLAN.md:108–113](.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md#L108) copies `capture.py`, then runs standalone scripts that write or poll files under `out/`. The directory is created when Python **executes** `capture.py`, not when the file is copied (`tmp/run-2026-11-19/p37-spike/capture.py:10–14`). The only explicit import is in consent-only Task 2. A fresh run can fail on the first shell redirection, before producing `38-SPIKE.md`.
- **HIGH — The optional live probe has no reliable failure-cleanup path.** [38-01-PLAN.md:77,140–144,168–170](.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md#L140) prescribes a stop on an unexpected failure, but defers cleanup to Task 3. Task 2 sets a limit on pipe reads without specifying a bounded wait after EOF, handling for launch or pipe failures, or cleanup on interruption. It also saves raw output it does not need and asks for a stderr excerpt cut **before** redaction. The shared redactor preserves everything outside recognized matches, including control characters (`skills/ai-kit-spec-review/ai_kit_spec/secret_shapes.py:99–117`). The audit has a similar boundary: its helper prints relative filenames verbatim, and the plan copies every `CHANGED` line into the committed record (`tmp/run-2026-11-19/p37-spike/audit.py:29–30,54–58`). Consent to run a host is not consent to publish its output or filenames.
- **MEDIUM — The scratch checks can produce passing evidence without proving the claim.** [38-01-PLAN.md:110–124](.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md#L110) calls the parenthesis case successful on two equal digit strings but never asserts that `/proc` actually reported a command name containing spaces and parentheses. It checks `ps` output without the `LC_ALL=C` that the downstream fallback uses ([38-14-PLAN.md:116](.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md#L116)). The document verifier checks line prefixes and counts, so malformed results or a final `pending` line can still pass the automated check. Task 1 also adds a content-specific scan that the review brief explicitly disallows.
- **MEDIUM — The 38-01 → 38-23 evidence handoff does not match.** [38-01-PLAN.md:24,169–171,220–227](.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md#L220) retains the committed `38-SPIKE.md` and removes raw captures. [38-23-PLAN.md:6,147,151–156](.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md#L147) depends only on 38-22 and tells its executor to read scratch result files through the summary. It also prewrites a claim about quiet `pi -p` output even if the spike was not consented. Likewise, 38-01 delegates per-host **hosted** timing to 38-26, but that plan specifies one hosted sweep scenario, not a timing run per primary host ([38-CONTEXT.md:176–183](.planning/phases/38-runner-hardening-and-run-safety/38-CONTEXT.md#L176); [38-26-PLAN.md:111–128](.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md#L111)).
- **MEDIUM — Execution mode is ambiguous in wave 1.** [38-01-PLAN.md:94,125,130–147](.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md#L130) requires a clean main checkout and says absent consent is an orchestrator-only skip, but uses a blocking `checkpoint:human-action`. The stock workflow surfaces that checkpoint to the user even in auto mode and can let same-wave agents continue (`.claude/gsd-core/workflows/execute-phase.md:1090–1100,1131`). There is no shared edited path with 38-02 through 38-05, but running any of them in the same checkout would invalidate 38-01’s global clean-tree and `HEAD` assertions.

##### Suggestions

- Make the scratch setup explicit and rerunnable: create private `out/` and the scratch environment first, verify the observed process name, and validate the final record values—not just their prefixes. Put the no-consent branch in an ordinary orchestrator step that cannot pause for an owner response.
- Keep only counts, timestamps, format, version and a closed failure reason. Bound and reap consented calls on every path, including version lookups. Report audit counts in the committed record rather than copying arbitrary filenames. Describe timing as one observation of the exact format used: the captured help distinguishes single-result JSON from live streaming (`tests/fixtures/cli_help/claude/help.txt:145–149`).
- Have 38-23 depend explicitly on 38-01 and consume `38-SPIKE.md` directly. Give the per-host hosted timing a named task and an explicit `unverified` outcome when not run. Schedule the scratch spike before other main-checkout work.

**Risk assessment: HIGH.** The default branch can fail before delivering evidence, and the optional branch can leave unsandboxed children or sensitive output behind after an error.

##### Ponytail findings

- **LOW — Task 1:** The process checks are needed for D-23. Reuse the shipped field parsing as the reference and make one scratch setup step own directory creation; a second capture framework adds nothing.
- **MEDIUM — Task 2:** The live timings are needed only with consent. Reuse the own-group and timeout pattern in `tmp/run-2026-11-19/p37-spike/capture.py:40–62`, but collect timing counters instead of raw transcripts. The version call belongs inside the same gate and timeout policy.
- **MEDIUM — Task 3:** Cleanup and a read-only audit are necessary. Reuse the existing listing pattern, but retain only counts and the committed evidence. The existing reaper sees only recorded groups with a member still under the scratch directory (`tmp/run-2026-11-19/p37-spike/leftovers.py:14–52`); its `none` message should not imply proof about detached or relocated descendants.

#### 38-02

**Summary — GSD plan.** The runtime refactor is narrow and behavior-preserving. The new cleanup case is appropriate and mostly reuses the right harness. The main gaps are how the test is launched, how it proves each exit path, and which downstream commit owns the existing tests broken by the harness move.

##### Strengths

- Both dead-code changes check out. `watchChunk` only pushes a chunk and has two callers; the relay callbacks still use `liveMatch` and `armLimit`. `quota` is already in `QUOTA_KEEP`, and none of the removed set’s members is in it. See `skills/ai-kit-spec-review/references/cross-ai.mjs:4450–4451,5287–5367,5623–5627`. The two retained clamp tests assert actual limits, not just function names (`:10994–11002,11078–11082`).
- The four scenarios reuse real harness behavior: fake auth exits 69, the hanging fake creates a readiness file, and the existing timeout and signal cases pin exits 124 and 143. Checking after each call is stronger than checking only after the fourth. See `skills/ai-kit-spec-review/references/cross-ai.mjs:7341–7422,8662–8668,9739–9745,10153–10162`.

##### Concerns

- **MEDIUM — Both tasks bypass the prescribed Node launcher and leave the outer temp root uncontrolled.** [38-02-PLAN.md:108–114,148–155](.planning/phases/38-runner-hardening-and-run-safety/38-02-PLAN.md#L108) invokes PATH `node` and does not set `TMPDIR`. `blackBoxSelfTest` creates its outer directory using `os.tmpdir()` before the per-case environment is built (`skills/ai-kit-spec-review/references/cross-ai.mjs:7594–7607`). The existing Python helpers already resolve real Node, provide a scratch `TMPDIR` and XDG config, and supervise the self-test as a process group (`tests/cross_ai_selftest.py:39–52,60–100,211–225,266–288`).
- **MEDIUM — Task 2 verifies exit numbers, not all three secondary outcomes.** [38-02-PLAN.md:138–149](.planning/phases/38-runner-hardening-and-run-safety/38-02-PLAN.md#L138) checks a status line only for success. Codes alone can conflate outcomes: auth and billing both use 69, and a timeout before the lane starts does not prove the fake lane’s timeout cleanup. `runCaseProcess` returns stderr, but direct calls bypass the standard `statusLineOk` check (`skills/ai-kit-spec-review/references/cross-ai.mjs:1189–1195,7192–7200,7353–7358,7403–7422`). The SIGKILL backstop proves the `cross-ai-*` prefix is observable, not that the `xai-idx-*` assertion is non-vacuous (`:10192–10211`).
- **HIGH — The 38-02 → 38-08 handoff has a known red intermediate test suite.** The ordering itself is correct: 38-07 depends on 38-02, and 38-08 depends on 38-07 and captures the actual pre-splice list ([38-07-PLAN.md:6](.planning/phases/38-runner-hardening-and-run-safety/38-07-PLAN.md#L6); [38-08-PLAN.md:6,235–241](.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md#L235)). But the move’s verify command includes `tests.test_cross_ai_runner_e2e`, whose existing tests mutate a case **in the template** and require `--self-test` to **succeed on a rendered copy** (`tests/test_cross_ai_runner_e2e.py:412–434,509–524`). Both assumptions become false in the split commit. Neither 38-08 nor 38-09 declares that test file for editing ([38-08-PLAN.md:7–11,494](.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md#L494); [38-09-PLAN.md:7–10](.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md#L7)).
- **LOW — The verify path does not explicitly establish per-commit byte stability.** Task 1’s filtered cases do not test `--print-argv`, and Task 2 names neither the existing render matrix nor a before/after byte check ([38-02-PLAN.md:111–117,152–168](.planning/phases/38-runner-hardening-and-run-safety/38-02-PLAN.md#L111)). The staged hook is useful, but its selection and time budget are not the same as an explicit test guarantee (`AGENTS.md:183–199`; `tests/test_cross_ai_render_sync.py:151–194`).

##### Suggestions

- Replace the duplicate shell-wrapper instructions with one exact scratch invocation of `list_cases` and `run_cases`. For each secondary call, check the corresponding status and evidence that the fake lane started; retain the immediate two-prefix check. If it exposes a real leak, stop and report it rather than changing cleanup under this proof-only plan.
- Move the two existing harness-test adaptations into the **same commit as the splice**. Keep the locked 38-25 live re-render and timing refresh where they are.
- Run the focused render/status checks explicitly. Leave whole-tree gates to the planned hooks and phase gate where they duplicate coverage; the one-file edit itself is small, and the source does not establish that it exceeds the 1,800-second cap.

**Risk assessment: MEDIUM for 38-02 itself; HIGH for its harness-move handoff until the existing tests move with it.**

##### Ponytail findings

- **LOW — Task 1:** Needed for R10/D-21. Change the named signature and its two callers, delete the redundant set, and keep the live helpers. The third dead item is correctly owned by 38-04 (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:269–277`; [38-04-PLAN.md:35](.planning/phases/38-runner-hardening-and-run-safety/38-04-PLAN.md#L35)).
- **MEDIUM — Task 2:** Needed for D-22; no new cleanup implementation is warranted. Reuse `runCaseProcess` and `statusLineOk` rather than inventing a runner. `split_cases` already assigns unrecorded names a median weight, so no interim fixture edit is needed (`tests/cross_ai_selftest.py:240–263`). The link to runtime shard **1** in [38-02-PLAN.md:37–41](.planning/phases/38-runner-hardening-and-run-safety/38-02-PLAN.md#L37) should name the dynamic runtime shards, not promise a fixed shard.

#### 38-03

**Summary — GSD plan.** The plan improves the existing recommendation without adding a new config-write path. The numeric boundary is well specified. The main omissions are real apply-diff evidence for idempotency, a complete documentation handoff, and a rule for displaying malformed values safely.

##### Strengths

- The helper placement preserves the purity boundary. `cross_ai.py` already owns the minimum and rejects booleans; `recommend.py` may import it but not `plan_io.py`. The alias preserves the existing validation callers, including `plan_edit`. See `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:173–179`, `plan_io.py:877–885`, `plan_edit.py:544–545`, and `tests/test_curated_config_recommend.py:2015–2019`.
- The planned test exercises real plan construction via existing fixtures. The fields are already populated by `make_entry`, and the seven timeout golden rows have `existing: null`, so keeping the unchanged reason for absent values avoids fixture churn. See `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:84–98,902–911`, `tests/test_curated_config_cross_ai.py:27–57`, and, for example, `tests/fixtures/curated_config_v2/golden/claude-standard-adaptive.json:316–322`.

##### Concerns

- **MEDIUM — The “second apply” test never exercises apply.** [38-03-PLAN.md:27,128](.planning/phases/38-runner-hardening-and-run-safety/38-03-PLAN.md#L128) feeds the first recommendation’s value into a second synthetic inventory. That proves the second recommendation’s text, but not that the apply path sees `1799 → 1800` as a change and `1800 → 1800` as a no-op. `diff_entries` reads the live config, and `_prepare_writes` skips `keep` rows (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:119–145,810–818`). The marker/backup concurrency backstop is unchanged and has an identified implementation (`apply.py:744–771`).
- **MEDIUM — The doc check can pass while a known obsolete claim remains.** [38-03-PLAN.md:33,158–161](.planning/phases/38-runner-hardening-and-run-safety/38-03-PLAN.md#L158) excludes `.planning/`, correctly for a test, but offers no executable handoff for the three stale base sentences still present at `.planning/ROADMAP.md:891,1593` and `.planning/REQUIREMENTS.md:391–398`. The research explicitly calls for rewriting them ([38-RESEARCH.md:173–174](.planning/phases/38-runner-hardening-and-run-safety/38-RESEARCH.md#L173)). The scan also misses a same-sentence claim split by a semicolon, and its glob-only reads do not select the test for a docs-only commit (`AGENTS.md:187–202`). Finally, the promised 38-24 curated-config wording is about runner exits and the watchdog, not what happens to a lower workflow timeout ([38-24-PLAN.md:141–145](.planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md#L141)).
- **MEDIUM — The new free-text reason repeats arbitrary malformed values.** [38-03-PLAN.md:116–118,129](.planning/phases/38-runner-hardening-and-run-safety/38-03-PLAN.md#L116) interpolates the raw value twice. Inventory validation checks that `values` is a dict, not that this leaf is a timeout (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py:301–306`). The structured `existing` field already carries the original value; copying it into prose widens where a misplaced credential or unsafe text can surface. The proposed cases cover ordinary invalid types, not that display boundary. An explicit JSON `null` is also reachable and currently indistinguishable from a missing key via `get_dotted` (`presets.py:210–218`); the plan should say whether it is treated as unset.
- **LOW — The supplied wave map is stale for the apparent 38-03/38-06 overlap.** Both plans edit `plan_io.py` ([38-03-PLAN.md:5–11](.planning/phases/38-runner-hardening-and-run-safety/38-03-PLAN.md#L5)), but the on-disk 38-06 now declares **wave 2** and `depends_on: [38-03, 38-04]` ([38-06-PLAN.md:5–11](.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md#L5)). That resolves the conflict if execution uses the plan frontmatter. Synchronize the map so it cannot schedule the older wave-1 layout. No other wave-1 write overlap surfaced for 38-03.

##### Suggestions

- Keep the recommendation test and add a two-state assertion at the existing `diff_entries` seam: `change` with `from=1799, to=1800`, then `keep` with `from=1800, to=1800`. This tests the rule used for both preview and writes without a second full apply setup.
- Give the orchestrator an explicit read-only closeout scan of the canonical planning docs and an owner for the wording changes. Keep the automated test out of `.planning/`; add a planted semicolon case and explicitly run the scan after 38-24’s doc changes.
- Retain the exact 1799/1800 text and structured fields. Define one safe display form for malformed values in prose and test it. The proposed Python helpers fit the configured complexity caps; no new dependency or validator layer is needed.

**Risk assessment: MEDIUM.** The timeout calculation stays unchanged, but the plan overstates what its tests prove about reapply and documentation, and it adds an avoidable display exposure.

##### Ponytail findings

- **LOW — Task 1:** Needed for R10/D-21. Moving `timeout_problem` beside `timeout_ok` and retaining the alias is enough. Reuse the existing `TestDiffKinds` pattern in `tests/test_curated_config_apply.py:1061–1101` for reapply evidence; do not build a second apply harness.
- **MEDIUM — Task 2:** The restore-claim scan is needed; a general Markdown parser is not. Keep the small matcher and its planted cases. Be explicit about its scope and run the canonical planning-doc check separately.

##### Batch coverage and disposition

Reviewed **3/3** requested plans. All seven R10 edge rows have named owners across 38-02, 38-03 and the 38-04 dead-item handoff; **R10 idempotency is assigned but under-tested**, and the no-restore acceptance lacks a complete handoff. The R10 clamp prohibition is directly owned by 38-02. The no-`.planning/` test prohibition is explicitly owned by 38-09 and backed by `tests/test_arch.py:2326–2344`. One phase-wide prohibition is only partly evidenced in the linked plans: SPEC line 694 covers **lock, finding and idle** diagnostic text, but the cited checks explicitly cover lock and finding text while the idle log in [38-11-PLAN.md:121](.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md#L121) interpolates the runtime directly. Record the input-validation proof or add a diagnostic test so that part has an explicit owner.

**Disposition: revise before execution.** Prioritize the 38-01 scratch and cleanup paths, the 38-08 intermediate-test break, and the 38-03 canonical-doc handoff.

Read-only review at `9f7a3c5`: no edits, test suites, make targets, or live host probes. Plans outside the manifest were read only for dependencies and handoffs, not independently approved.

#### Batch D (38-10, 38-11, 38-12)

#### 38-10

##### Summary

The opt-in settings design is sound: one planner resolves the call value over the baked value, and existing renders can omit the key. The plan is not ready to dispatch, though. Its required predecessor, **38-09**, is missing, and the proposed notice does not use the actual remaining attempt budget on real runs.

##### Strengths

- Task 1 updates the right contract in the same commit. The template test checks both the exact config keys and sorted JSON serialization; fresh renders inherit new keys from the template. There is no need for a second curated-config setting. (`tests/test_ai_kit_spec.py:11754–11785`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:93–113`)
- Task 2 covers missing, empty, signed, fractional, non-ASCII, and out-of-range values, plus explicit `0` overriding a baked value. The proposed branch reuses the existing missing-value and usage-error paths. (`.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:165–168`; `skills/ai-kit-spec-review/references/cross-ai.mjs:6211`, `:14838–14843`)

##### Concerns

- **HIGH — Missing dependency blocks the batch.** `38-10` requires `38-09` and relies on its export-list check. There is no `38-09-PLAN.md` in the phase directory at the reviewed checkout; `38-08` creates the sibling and export list but explicitly hands off the additional checks. The installed GSD records unresolved dependency tokens as missing evidence, so `38-10` is not ready even if the harness move succeeds. (`.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:5–6`, `:131`; `.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:24–31`, `:577–583`; `.claude/gsd-core/bin/lib/phase.cjs:979–1004`)
- **MEDIUM — Task 1 warns against a nominal budget, not the live one.** The plan calculates the notice before prompt handling, snapshots and preflight, with no quota-episode end. The runner calculates the actual cap later, in each attempt, using `episodeEnd()`. A slow preflight can leave an attempt with less time than the watchdog without the required warning; rounding down before comparing can also warn when a whole-second idle value is still below a fractional budget. (`.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:127–130`; `skills/ai-kit-spec-review/references/cross-ai.mjs:5402–5414`, `:5697–5711`, `:14994–15026`, `:15069–15091`)
- **MEDIUM — The preview tests do not prove the locked byte-level delta.** Task 2 compares one stdout line with the new flag on and off in the **same** runner; it does not compare pre-change and post-change stderr. The existing render matrix compares two copies of the current template, so an extra or changed line emitted by both passes that gate. (`.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:165–168`, `:184`; `tests/test_cross_ai_render_sync.py:179–189`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:236–238`)
- **MEDIUM — Tasks 1 and 2 lack a complete execution environment.** The scratch script sets `HOME` and state but not `TMPDIR`, and invokes PATH `node` after changing `HOME`. The harness creates its root with `os.tmpdir()` even for `list`; research requires the real Node executable. The bare lint commands also delegate to `uv run` without an offline/pre-provisioned environment specified. The Python module runner isolates its own children; that does not isolate these other commands. (`.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:121`, `:136–143`, `:178–193`; `skills/ai-kit-spec-review/references/cross-ai.mjs:7591–7606`; `.planning/phases/38-runner-hardening-and-run-safety/38-RESEARCH.md:184–188`; `Makefile:98–113`; `tools/run_unittest_parallel.py:574–587`)
- **LOW — One acceptance command fails as written.** The pattern passed to `rg -c -F` begins with `--idle-timeout`. I checked the exact read-only command: `rg` reports an unrecognized flag and exits 2. Task 2 also gives no recoverable setup instruction if its Task 1 wrapper is missing, beyond referring to the task block not included in its lane prompt. (`.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:147`, `:156–162`)

##### Suggestions

- Restore `38-09` as the locked wave-4 predecessor and verify GSD readiness before dispatch. Keep its export and rendered-copy checks; do not bypass it by dropping the dependency.
- Use `attemptCapMs` for both paths: a nominal, no-spawn preview and the actual remaining budget for a real attempt. Compare in milliseconds and round only for display. Pin a real attempt shortened by preflight or persisted episode state.
- Capture a hermetic pre-change preview and compare after the change, removing only the allowed idle line and normalizing the existing nondeterministic fields. Reuse the matrix helpers in `tests/test_cross_ai_render_sync.py:151–189`.
- Put the exact real-Node, scratch `TMPDIR`, and offline-tool setup in the objective shared by both tasks; add `--` before the `rg` pattern. Keep the lane gates focused and assign any broader gate explicitly to the orchestrator.

**Risk assessment: HIGH for execution readiness; MEDIUM for the runtime change.** The numeric parser and render path are straightforward. The missing dependency blocks dispatch, and the budget warning can be wrong once the watchdog controls real attempts.

##### Ponytail findings

- **LOW — Task 1:** Required by R1/D-01/D-03. Reusing `attemptCapMs` and inheriting the config key through the renderer is leaner than adding another budget formula or Python option. Keep one formula and use it at the right time. (`skills/ai-kit-spec-review/references/cross-ai.mjs:5402–5414`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:93–108`)
- **LOW — Task 2:** The parser and precedence cases are needed. Reuse `runCaseProcess` and `runTwice`, but spend the regression budget on a genuine before/after preview check rather than adding more same-build comparisons. No same-wave peer or write overlap was found. (`skills/ai-kit-spec-review/references/cross-ai.mjs:7341–7358`, `:7385–7409`; `.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:5–11`, `:165–168`)

#### 38-11

##### Summary

Reusing the existing process-group finalizer and retry ladder is the right implementation shape. The main gaps are what happens at the exact idle boundary, what the runner records when post-hoc classification finds an error, and whether the handoff lets an execute lane finish a tree read before the watchdog kills it.

##### Strengths

- Task 1 adds no second kill path. The current finalizer already owns one-shot settlement, TERM, grace, KILL and pipe drain. The plan’s silent fake creates a grandchild and checks it before harness cleanup, so that part of the test is meaningful. (`skills/ai-kit-spec-review/references/cross-ai.mjs:4597–4626`, `:6608–6612`, `:7450–7456`, `:7565–7569`)
- Task 2 reuses established fakes for quiet success, retry and live-limit handling. The short no-retry windows are consistent with the ladder’s 60-second admission reserve. (`skills/ai-kit-spec-review/references/cross-ai.mjs:4368–4386`, `:6518–6521`, `:6613–6616`, `:6717–6727`, `:10560–10585`)

##### Concerns

- **HIGH — The timer does not give an arriving byte the tie.** Task 1 calls `finalize('idle')` directly from the timer when `Date.now() - lastByteMs >= idleMs`. A byte ready at the boundary can still be waiting for its `data` handler. No final recheck lets that handler win, and a forward wall-clock adjustment can make a recheck fire early. The ticker fixture deliberately leaves margin and cannot prove the boundary. The same handoff is risky for hosted lanes: the separate timer can run before `tick` observes file growth or `rc`. (`.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md:22–28`, `:120`, `:153–154`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4629–4662`, `:5026–5039`; `.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:179–184`)
- **HIGH — The tree-poll handoff lets an execute lane die before the runner learns it made progress.** `38-11`’s only idle veto is a pending live limit. `38-16` adds a reset **after** a successful asynchronous read; it does not defer expiry while that read is pending. With a one-second idle timeout, the first tree poll is scheduled at the same threshold. It can start, then the watchdog can kill a lane that already edited or committed; a failed or hung read also never establishes the required lack of progress. `38-19` mirrors the timer but does not explicitly wire `idleResetter`, despite depending on it for the hosted quiet-commit case. (`.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md:120–123`; `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:125–132`; `.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:174–184`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:243–255`)
- **MEDIUM — An idle kill can lose its required attempt-line evidence.** Task 1 logs `idle-watchdog` only when `hit` is absent, but a non-terminal error line can survive live matching and classify post-hoc after the idle kill. The existing `post-hoc-timeout-429` case demonstrates this distinction. Preserve the existing classification/retry outcome, but do not let it erase the fact that the watchdog ended the attempt. (`.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md:121–122`; `skills/ai-kit-spec-review/references/cross-ai.mjs:5767–5779`, `:5814–5819`, `:10086–10096`)
- **MEDIUM — Task 2 does not prove all of the edges claimed.** Two `pi hangonce` call labels and `next=same` do not prove the same ID reached the second child, and filtering to `pi ` cannot detect another runtime. No new case covers signal/attempt-cap precedence, exact-boundary activity, or a split UTF-8 character resetting on raw bytes. The current fake already records session IDs and prompt type, and an existing case checks both. The new idle diagnostic also interpolates the caller-supplied runtime label without redaction; the allowed runtime-ID grammar is not a secret filter. (`.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md:121`, `:153–159`; `skills/ai-kit-spec-review/references/cross-ai.mjs:6184–6186`, `:6825–6844`, `:7459–7465`, `:10510–10524`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:608–615`, `:693–694`)
- **MEDIUM — Both task gates repeat the incomplete scratch setup.** The wrapper runs PATH `node`, does not pin `TMPDIR`, and has no exit trap. Task 2 also runs all eight shards and four repository-wide lint targets before a hooked commit. The recorded shard times make the gate plausible, not a proven fit under the unattended cap on a loaded host. (`.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md:118`, `:169–184`; `tests/cross_ai_selftest.py:266–288`; `tools/run_unittest_parallel.py:154–175`; `Makefile:98–113`)

##### Suggestions

- Specify the timer contract before implementation: monotonic elapsed time, activity wins the boundary recheck, one finalizer, and an explicit execute-poll decision that cannot mistake a pending or failed read for confirmed inactivity. Have the hosted poll check both output and `rc` before deciding idle.
- Use the fake’s `FAKE_SIDS` evidence and full call log. Add a deterministic boundary test for the decision and targeted fake cases for raw-byte reset and signal/cap precedence. Verify that the attempt reason and final classification can both be reported correctly.
- Use the existing sanitizer for the runtime label. Give both tasks a reproducible scratch wrapper, a focused pre-commit gate, and a clear owner for the full wave gate. Update the `38-23` handoff to state the actual timing bound; its proposed text says “at the idle time” but does not give the bound. (`.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:151`)

**Risk assessment: HIGH.** These gaps can end an active lane, and the existing cases would not reliably detect it. No same-wave peer or undeclared same-wave dependency was found; the missing `38-09` blocks this plan transitively through `38-10`.

##### Ponytail findings

- **MEDIUM — Task 1:** Required by R1/D-01/D-04. Keep the existing finalizers and raw-byte callbacks. One shared activity/expiry decision is justified by the two transports and the tree-poll handoff; a new supervisor or second group-kill routine is not. Avoid reading the clock on every git/listing chunk when the watchdog is off. (`skills/ai-kit-spec-review/references/cross-ai.mjs:4597–4626`, `:4963–4971`, `:4994–5008`, `:5351–5377`)
- **LOW — Task 2:** The runtime cases are necessary. Extend the existing `hangonce` and session-log checks rather than inventing a second fake framework. Move only gate duplication, not behavioral coverage, out of the capped task. (`skills/ai-kit-spec-review/references/cross-ai.mjs:6717–6727`, `:6830–6839`, `:10519–10524`)

#### 38-12

##### Summary

The status-line placement and parser changes are well specified. The risk is in the diagnostics contract: this plan promises one sanitized, bounded formatter, but the downstream producers preformat lists, and Task 2 never exercises a populated finding through `finish` itself.

##### Strengths

- The insertion point is correct: the existing settings group comes immediately before the optional retry fields. The harness must shift its retry capture from 5 to 6, while Python’s token parser and result attribution need no code change. The proposed tests exercise both old and new trailer shapes. (`skills/ai-kit-spec-review/references/cross-ai.mjs:1299–1309`, `:7187–7200`, `:7241–7252`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:280–286`, `:616–622`)
- The plan updates the existing hard-pinned retry-order case in the same task and leaves the closed Phase 37 settings vocabulary alone. The new Python methods are small, use existing imports and helpers, and introduce no Python runtime change or complexity-cap issue. (`skills/ai-kit-spec-review/references/cross-ai.mjs:14389–14397`; `tests/test_runner_status_group.py:12–24`, `:35–63`; `.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:135–138`, `:174–179`)

##### Concerns

- **MEDIUM — The 10-item cap and sorting have two owners.** Task 1 caps and sorts only array details. `38-17` builds the actual path, phrase and task details as strings via `listDetail`, then `38-18` passes them straight through. Thus the formatter tested here does not enforce the list contract on production data. A second producer can bypass it, and sorting or sanitization can drift between the two implementations. (`.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:127–130`, `:172`; `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:172`; `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:130`)
- **MEDIUM — The redaction test does not prove its stated defense or a single output line.** A BEL **before** a synthetic key already satisfies the current key regex’s non-word boundary, so the test passes even with the second redaction removed. The proposed strip also leaves Unicode line separators that Python’s `splitlines()` treats as new records. Finally, the combined `try` around `findingLines` and `checkGroup` means a formatting failure can erase the status codes along with the details. (`.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:128–133`, `:172`; `skills/ai-kit-spec-review/references/cross-ai.mjs:1835–1842`, `:1911–1933`; `tools/judge_loop.py:425–428`)
- **MEDIUM — The tests leave the populated output path unproved.** Task 1 proves the empty trailer; Task 2 calls formatters directly and feeds synthetic trailers to Python. Neither fails if `finish` stops printing populated finding lines or puts them after the trailer. `38-18` checks exact finding text and trailer fields, but its shared case helper does not explicitly assert their relative order. The fixed stderr-delta claim also has no before/after check. (`.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:116–119`, `:133–137`, `:172–174`; `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:137–138`; `skills/ai-kit-spec-review/references/cross-ai.mjs:7192–7199`)
- **MEDIUM — Both tasks have the same gate-isolation gap.** The scratch wrapper leaves `TMPDIR` ambient and uses PATH `node`; the lint commands leave offline/tool-cache setup implicit. Task 2 repeats all eight shards before a hooked commit. The commands and failure signals exist, but the task does not provide a bounded, isolated recipe for running them as written. (`.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:122`, `:142–149`, `:184–199`; `tests/cross_ai_selftest.py:39–52`, `:266–288`; `tools/run_unittest_parallel.py:898–901`, `:915–933`; `Makefile:98–113`)

##### Suggestions

- Make the `38-12`/`38-17` interface explicit: pass structured items to one formatter, keeping explanatory count or plan-ID text separate. Test an actual downstream finding with more than ten items.
- Keep validated trailer codes independent of detail rendering. Exercise the real emission path with a populated finding, a synthetic key split inside its shape, and a Unicode line separator; assert exactly one finding line before the single final trailer.
- Keep Python token parsing unchanged. Pin the precise preview delta in the same before/after check recommended for `38-10`, and use the same scratch and offline setup in both tasks.

**Risk assessment: MEDIUM.** The parser changes are small and backward-compatible by inspection. The main risk is incomplete or misleading evidence when a blocking result reaches callers. No same-wave peer or undeclared same-wave dependency was found; the missing `38-09` remains a transitive execution blocker.

##### Ponytail findings

- **MEDIUM — Task 1:** R5 needs a closed list, a recorder, and one trailer group. Reuse the existing `finish`/`log` path and `redactSecrets`; share one list formatter with `38-17` rather than keeping two. (`skills/ai-kit-spec-review/references/cross-ai.mjs:1262–1288`, `:1911–1933`; `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:172`)
- **LOW — Task 2:** Existing harness and Python parser tests are the right homes. Keep the compatibility cases, but add one real populated-trailer check rather than another parser or fixture. The source/`--describe`/SKILL comparison is explicitly owned by `38-22` and `38-23`. (`tests/test_runner_status_group.py:19–24`, `:48–63`; `.planning/phases/38-runner-hardening-and-run-safety/38-22-PLAN.md:23`, `:113–114`; `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:24`, `:125`)

#### Batch coverage and handoffs

Reviewed **3/3** manifest plans against checkout `9f7a3c5`. Waves 5, 6 and 7 have no same-wave overlaps. The three plans add no runtime dependency, Python product subprocess, record-format change, or new herdr call. The live-copy re-render and shard-time refresh are explicitly deferred to `38-25`, not silently omitted. (`.planning/phases/38-runner-hardening-and-run-safety/38-25-PLAN.md:31–36`)

Coverage gaps that remain after following the batch’s handoffs:

- **R1:** Boundary/encoding and concurrency have named owners, but the exact tie, split-byte reset, signal/cap precedence, and documentation of timing precision are not proved as written. (`.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:608–615`; `.planning/phases/38-runner-hardening-and-run-safety/38-11-PLAN.md:114–124`, `:152–159`; `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:151`)
- **R5:** The seed-list prohibition calls for a fake runtime absent from every table. `38-10` uses pure planner checks and `pi`; the downstream `38-18` spawn helper also hardwires `pi`. The same downstream plan claims the human-edit concurrency backstop via commits made **by the fake lane**, which does not verify that a separate writer’s commit is counted. Neither proof has an adequate task in the inspected handoff. (`.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:639`, `:688`; `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:23`, `:36`, `:137`)
- **R8 dependency:** The missing `38-09` leaves its independent export-list check, rendered-copy smoke case, and test-source guard handoff unverified. `38-08` does own the byte-equal case-list check and missing-sibling refusal. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:24–31`, `:36`, `:573–583`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:650–654`, `:696`)

No files were changed, and no test suites, make targets, or live hosts were run. Test duration and runtime behavior remain unverified; the missing predecessor and the watchdog’s expiry decision are the first issues to resolve.

#### Batch H (38-22, 38-23, 38-24, 38-25, 38-26)

#### 38-22

**Summary.** The three additive `--describe` keys are the right interface for the docs and Python readers. The implementation fits a small lane. The main weakness is that the proposed tests can certify flags that no longer parse and finding results that no longer match runtime decisions.

**Strengths**

- Extending the existing serializer keeps schema 1 and the existing keys intact. `describeValue` already sorts object keys without reordering arrays, and the Python reader retains the whole object once it sees a `runtimes` dictionary. No Python product change or new dependency is needed. `skills/ai-kit-spec-review/references/cross-ai.mjs:14799–14829`; `skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py:30–44`.
- The existing golden writer and fake-herdr marker are good reuse: one pins the emitted bytes; the other verifies that availability detection does not invoke herdr. `tests/test_runner_describe.py:205–219,239–252`.

**Concerns**

1. **MEDIUM — The flag test does not test flag parsing.** Counting quoted names across the template does not establish that `parseArgs` accepts them. Removing a parser branch can leave the name in the new constant and a diagnostic string. The proposed mutation only removes a name from the JSON, not from the parser. `.planning/phases/38-runner-hardening-and-run-safety/38-22-PLAN.md:143–152`; `skills/ai-kit-spec-review/references/cross-ai.mjs:6199–6280`.
2. **MEDIUM — The contract can drift from enforcement while all three copies agree.** Task 1 adds a result map used only by `--describe`; Task 2 pins it to another literal map; 38-23 will copy it into the docs. The blocking decision is still independently encoded in `planFindings`. A change there can leave the wire output, golden and docs green. Also, `statuses` contains **default** exits: `finish` lets a call override them. `.planning/phases/38-runner-hardening-and-run-safety/38-22-PLAN.md:112–116,145–152`; `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:171`; `skills/ai-kit-spec-review/references/cross-ai.mjs:1288–1292`.
3. **LOW — The executor instructions conflict.** The objective supplies a three-path `git add` for both tasks, while Task 2 accepts only the test module. Task 1 also asks `git diff --stat` to prove that existing values did not change; a stat cannot establish that. `.planning/phases/38-runner-hardening-and-run-safety/38-22-PLAN.md:82,115,135–137,170`.

**Suggestions**

- Pin actual parser behavior with valid values for the four value flags and the existing hermetic sweep case for `--sweep`. Give each task its exact stage list. Compare old and new parsed JSON after deleting the three new keys, in addition to the byte golden.
- Give the finding-to-result mapping one owner at the blocking decision, and have `--describe` read it. Keep behavioral cases independent of that map. Call the status numbers “default exits” in the consumer docs.

##### Ponytail findings

- **LOW — Task 1:** Required by R5/R11/R12. Reuse `describeValue` and the golden writer; no new formatting layer or Python reader change is warranted.
- **MEDIUM — Task 2:** The compatibility test is useful. Reuse `source_list` and the `run_fn` seam rather than adding another list parser and mutating `sys.path` inside the test. The test module already imports the node helper, which adds the review package path. `tests/test_runner_describe.py:14–20,50–54`; `tests/cross_ai_selftest.py:33–36`; `tests/test_runner_facts.py:55–75`.

**Risk assessment: MEDIUM.** The runtime change is small and additive; the risk is making a machine-readable promise the actual parser or evaluator does not keep.

#### 38-23

**Summary.** This plan reaches the right skill, launch examples and evals. It needs to tell callers how to resume without losing coverage, and distinguish “sweep ran” from “cleanup succeeded.” Otherwise the new instructions can make unattended execution less trustworthy.

**Strengths**

- The three proposed sample edits target the actual fenced examples, including the hinted 75 example where the new fields must precede the retry fields. `skills/ai-kit-cross-ai/SKILL.md:125,220`; `skills/ai-kit-cross-ai/references/launch-and-wait.md:37`; `.planning/phases/38-runner-hardening-and-run-safety/38-12-PLAN.md:133–138`.
- The two new cases use the existing eval shape and target different caller decisions. The existing cases already supply input files, so two new text-only cases do not violate the skill-level input-file requirement. `skills/ai-kit-cross-ai/evals/evals.json:25–34,47–56`; `tests/test_skill_evals_shape.py:136–150`.

**Concerns**

4. **HIGH — The recommended `partial` resume can lose both the baseline and the plan.** Task 2 tells the caller to send only the missing tasks or the matched phrase as the new prompt. The baseline key hashes the objective or, without one, the prompt body; a phrase-only follow-up also has no task blocks for the coverage check. The existing skill already says `session=-` is possible, and its GSD branch says to abort on exit 1. Task 3’s eval rewards the incomplete recipe rather than resolving these cases. `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:154,181`; `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:121–123`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4463–4470`; `skills/ai-kit-cross-ai/SKILL.md:200–212,248–256`.
5. **MEDIUM — Task 2 requests timing files 38-01 does not leave.** The on-disk dependency on 38-01 is present, but the handoff is the committed `38-SPIKE.md`. The upstream plan records first-byte times and streaming classifications there; it does not retain raw results. The proposed single “first output” number also discards the distinction between stderr, stdout and the JSON streaming result. `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:147,151,156`; `.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md:140–143,220–225`.
6. **MEDIUM — The operational limits are incomplete or overstated.** “The lock is released on every exit” includes a hard kill as written. “Next runner call of any kind” includes previews that never sweep. The sweep prose omits the null-tab-ID exception and the sweep’s own two-second reread, distinct from the lock reread. The watchdog prose omits the R1 timing limitation and that a failed tree read cannot justify a kill. None of these omissions fails the proposed substring checks. `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:151–157`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:248–254,491–511,613,671`; `.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:127`.
7. **MEDIUM — The doc lock misses duplicate statuses and stale samples.** `status_rows` writes straight into a dictionary, so a duplicate status with the same exit silently passes. Task 1 adds the sample fields but does not extend `group_problem`; removing the new pair from every sample still passes the existing sample test. `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:124–125`; `tests/test_cross_ai_settings_text.py:70–93,186–209`.

**Suggestions**

- Keep the original objective and plan blocks in a same-session fix round, and add the missing-work instruction to them. State what to do when the session is absent or unsupported, and distinguish a caller-managed follow-up from GSD’s retry prompt. Make that distinction part of the `partial` eval.
- Read the committed spike rows directly. Include the stream classification or mark it unverified. Pin uniqueness before converting statuses to a dictionary; extend the existing sample parser to require `coverage=` and `findings=` in place.
- Document the baseline’s reuse window, ancestry check and deletion on `ok`, not just the override flag. State the cleanup limits once in the hosted section and link to them.

##### Ponytail findings

- **MEDIUM — Task 1:** The tables are required; separate copies of the runner parsers are not. Reuse `describe_json`, `runner_list` and the existing sample parser, with one focused negative case per invariant. `tests/test_cross_ai_settings_text.py:31–56,70–93`.
- **MEDIUM — Task 2:** The caller rules and limits are required. Five long additions make the key decisions harder to find, while repeating the existing hosted section. Keep the stop/resume and cleanup decisions in the skill; consolidate protocol detail with the existing hosted text rather than duplicating it. `skills/ai-kit-cross-ai/SKILL.md:97–110,206–212`.
- **MEDIUM — Task 3:** Both evals earn their place. Keep the current fixture pattern, but give the `partial` eval a usable session and original task context, or explicitly test the owner-stop branch when either is missing. `skills/ai-kit-cross-ai/evals/evals.json:25–34`.

**Risk assessment: HIGH.** A caller can follow the proposed instructions exactly and then treat an unchecked fix round as completion.

#### 38-24

**Summary.** Updating the secondary docs and root README is appropriately scoped. The status mapping is straightforward, but the proposed operational prose overpromises cleanup and does not deliver the promised timeout wording.

**Strengths**

- The dispatch table is the correct place to describe the Python mapping. Adding `locked` and `partial` without removing legacy names preserves the contract for older runners. `.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:71`; `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:30–55`; `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:353–371`.
- The two root README rows already point to the skills. Updating those rows instead of creating a new quick start keeps the change proportional. `README.md:32,46`; `tests/test_cross_ai_docs_text.py:99–108`.

**Concerns**

8. **MEDIUM — The reference prose gives the wrong watchdog and sweep guarantees.** The dispatch text says the watchdog needs the flag even when the baked setting enables it. The sweep text says the next run removes the directory, but a live launcher keeps it and an unreachable or disabled herdr can leave a record. The proposed runner reference also retains the unconditional “removed after the lane” claim. R11 calls for the hosted lock, file-based activity, output bound and secret lifetime to be documented, not just the tab match. `.planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md:111–114,141–142`; `skills/ai-kit-gsd-curated-config/references/runner.md:42`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:445–449,496–511`.
9. **MEDIUM — The timeout handoff is not implemented in the docs.** 38-03 assigns the curated-config skill wording to 38-24, but Task 2 only changes the exit sentence. It never says the plan shows the existing timeout and proposed value before a below-minimum timeout is raised. Task 1’s literal `CONFIG retains` replacement also crosses a real line break that the instruction does not show. `.planning/phases/38-runner-hardening-and-run-safety/38-03-PLAN.md:24–33`; `.planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md:113,143–144`; `skills/ai-kit-gsd-curated-config/references/runner.md:55–57`; `skills/ai-kit-gsd-curated-config/SKILL.md:40–45`.
10. **MEDIUM — The supplied execution graph differs from disk.** The on-disk plan explicitly depends on 38-05, 38-23 and **38-27**, not just 38-23. On disk 38-27 exists and owns the apply-time skipped-skill migration, but it is absent from the supplied 26-plan map. The executor cannot tell which set the orchestrator will schedule. `.planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md:5–6,59`; `.planning/phases/38-runner-hardening-and-run-safety/38-27-PLAN.md:3–15,24–28`. This is a manifest finding, not a review of 38-27.

**Suggestions**

- Put the effective idle default and the sweep’s keep conditions in the references. Keep the README brief and link readers to the full safety contract. Qualify that `partial` and `locked` are runner outcomes mapped to `real_error`, not statuses a normal review lane itself emits.
- Add the narrow timeout disclosure and pin it. If that edit changes caller behavior outside the exempt paragraph, let 38-26’s materiality check decide the result rather than widening the exemption.
- Reconcile the dispatch manifest with the actual dependencies before execution. Supply a multiline anchor for the CONFIG sentence.

##### Ponytail findings

- **LOW — Task 1:** Required. Extend the current doc test and reuse the runner status extractor instead of adding a third version. Compare documented reasons to `STATUS_TO_REASON`, preserving its legacy entries; the existing proposed test checks reasons for only two rows. `tests/test_cross_ai_docs_text.py:51–86`; `tests/test_ai_kit_spec_runtimes_table.py:718–741`.
- **MEDIUM — Task 2:** The README changes and exit wording are useful and small. Extend the existing README test instead of reading the rows in a second class. Do not omit the timeout disclosure merely to keep the judge set small. `tests/test_cross_ai_docs_text.py:99–108`; `.planning/phases/38-runner-hardening-and-run-safety/38-24-PLAN.md:143–144`.

**Risk assessment: MEDIUM.** The edits are simple; the risks are a stale dispatch map and owner-facing assurances the runner does not make.

#### 38-25

**Summary.** The plan correctly separates the shipped version from the builder readiness floor and uses the product renderer. Task 1 cannot pass its own gate, and Tasks 2–3 contain live-environment operations that should be owned by the orchestrator.

**Strengths**

- The dry/live/check helper tests CONFIG preservation, the pristine stamp and byte equality against the dry run. The product renderer keeps owner-edited copies and writes `.new` instead. `tmp/run-2026-11-19/p37-23/render.py:127–168`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:265–295`.
- The timing recorder already runs each current case and atomically replaces the fixture; missing weights in earlier waves affect balance, not case membership. `tests/cross_ai_selftest.py:240–257,319–345`.

**Concerns**

11. **HIGH — Task 1’s version test deterministically fails.** It is explicitly in the verify command, but `test_template_version_constants_match_the_shipped_template` asserts both `_READY_TEMPLATE == shipped` and `shipped == 9`. With the planned floor of 9 and shipped version 10, both are false. The exact seven-path commit forbids fixing the test, and the version grep cannot see either assertion. `.planning/phases/38-runner-hardening-and-run-safety/38-25-PLAN.md:111–140`; `tests/test_curated_config_script.py:82–87`.
12. **HIGH — Task 2 uses live consent from an unattended lane and has an incomplete rollback.** Even `--skip-no-write` still runs the flow capability check, which reads consent under `GSD_HOME` or HOME. In the required scratch HOME it can fail; with caller HOME it is not the plan’s one named exception. After the live write, the plan restores the file only on unexpected render JSON, not on a failed live comparison or dogfood check. The old helper also deletes and rewrites its **Phase 37** scratch directory, contrary to the current task’s scratch boundary. `.planning/phases/38-runner-hardening-and-run-safety/38-25-PLAN.md:89,147–170`; `tools/check_dogfood.py:334–372,627–646`; `tmp/run-2026-11-19/p37-23/render.py:18–22,127–149,164–168`.
13. **MEDIUM — Task 3’s time and environment are not closed over.** The planned quiet wait, serial recording and full-hook commit can consume 25 minutes before diagnostics, duplicate shard runs, lint or a hook retry. The quiet helper also requires more than 8 GiB of available RAM, omitted from the task. The record script replaces HOME without preserving the Volta environment as its predecessor did; the shard script leaves scratch HOME/TMPDIR setup implicit. `.planning/phases/38-runner-hardening-and-run-safety/38-25-PLAN.md:181–204`; `tmp/run-2026-11-19/p37-23/wait_quiet.py:8–34`; `tmp/run-2026-11-19/p37-23/record.sh:8–16`; `tools/run_unittest_parallel.py:400–449`.

**Suggestions**

- Add the version test to Task 1’s scope. Assert shipped version 10 and readiness floor 9 separately, including that an edited 9 remains builder-ready but does not supply the new supervision contract.
- Hand the live render and dogfood check to the orchestrator explicitly. Use owned Phase 38 scratch, and define rollback for every failing step after the write. Run only the runner-copy check under scratch HOME; keep live consent validation as the separate named step.
- Preflight quiet-machine and toolchain prerequisites before recording. Run the shard measurement once and verify that saved log instead of measuring twice. Budget the full-hook commit as an orchestrator operation. Task 1 already exceeds the five-file review heuristic even before adding the missing test.

##### Ponytail findings

- **HIGH — Task 1:** Required version bump; no new helper needed. Fix the existing `TestRender` pin in the same logical change.
- **MEDIUM — Task 2:** Required live-copy proof. Reuse `ensure_runner` and `check_runner_copy`; the old scratch driver is a useful model, not a portable dependency. `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:358–368`; `tools/check_dogfood.py:91–117`.
- **MEDIUM — Task 3:** Required calibration. Reuse `record_times` and the existing per-module output; a second measurement adds time without protecting the values derived from the first. `tests/cross_ai_selftest.py:319–345`; `tools/run_unittest_parallel.py:915–930`.

**Risk assessment: HIGH.** One deterministic red gate, one live mutation without complete rollback, and little margin under the unattended cap.

#### 38-26

**Summary.** The live proof and the judge loop belong with the orchestrator, as planned. The current live procedure does not prove process ownership before signaling, and the closing checks can report success without a passing judge bar.

**Strengths**

- The plan uses the pinned record fields and separates process liveness from tab matching. Using a fake lane through real herdr is enough to test the transport path without using real model credentials. `tests/fixtures/runner_host_protocol.json:15–26`; `tmp/spec-discuss-35-39/probe38d.py:13–34`; `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:110–128`.
- The frozen-tree checkpoint, two-judge pool check and current-digest check before fixes are worth retaining. The pool check inspects a verdict file for each assigned judge rather than trusting a worker’s status line. `tmp/judge-37/pool_check.py:30–59`; `tmp/judge-37/check.py:33–51`; `tools/judge_loop.py:167–169`.

**Concerns**

14. **HIGH — The live probe can signal the wrong process and leave its own hosted lane behind.** Task 1 writes a shell PID before `exec node` and kills that PID without matching it to `run.json.runner_pid` and `runner_start`. The PATH `node` shim is a known extra-process risk. For the launcher, the probe checks one start tick but does not use the shipped verified-leader/group-and-session rule or verify that identity again before escalation. On failure, `close` only closes the outer spike tab and deletes the state home; the hosted launcher runs in a separate session, and its tab and cleanup record can be lost. `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:121–127`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4766–4780,4808,4835,4973–5006`; `.planning/phases/37-shared-runner-options-and-session-ids/37-24-SUMMARY.md:42`.
15. **HIGH — The advertised scratch variant is not fully isolated.** It inherits the entire environment then changes only a few paths. The probe neither strips inherited credentials/config overrides nor pins the same herdr socket and toolchain in the controller and pane. An inherited `AIKIT_HOST=none` defeats `--host auto`. The real-config audit runs after Task 1, so it cannot bracket an authorized real-HOME live probe. `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:85,121–127,157–161`; `tools/run_unittest_parallel.py:426–449`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4848–4855`; `tmp/judge-37/real_config_audit.py:16–42`.
16. **HIGH — The closing check can accept an unmet bar.** With one to three findings and a failed bar, Task 3 records the failed result, makes fixes, then checks without `--gate`. The checker only fails an unmet bar when `opts.gate` is true. Refutations written in the final fix step also stay in scratch: the inherited publisher only reads refutations staged before the round. Missing evals are checked after publication, and the copied eval gate only requires a nonempty list. `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:185–195,212–216`; `tools/judge_loop.py:817–829,1376–1389`; `tmp/judge-37/stage.py:21–30`; `tmp/judge-37/publish.py:20–31`; `tmp/judge-37/evals_gate.py:17–28`.
17. **MEDIUM — Two verification commands do not work at their scheduled point.** Task 1 performs `sweep` and `close`, then asks verification to perform them again: the second sweep cannot close one already-closed tab, and cleanup may have removed the evidence. Task 3 copies the added-line scan to a shallower directory but changes only `PLAN`; the inherited `parents[3]` then resolves above the repo. It also inherits Phase 37’s path and message exceptions, so it is not a strict Phase 38 scan. `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:125–134,196,208–209`; `tmp/run-2026-11-19/p37-23/added_line_scan.py:9–17,52–64,85–101`.
18. **MEDIUM — The live timing handoff has no producer.** D-23 asks for one hosted timing call per primary host. 38-01 explicitly defers those to 38-26, while 38-26 claims to read a hosted record from 38-01 and runs only one killed lane. Also, nothing in that live scenario exercises the error envelopes 38-19 says it confirms. `.planning/phases/38-runner-hardening-and-run-safety/38-CONTEXT.md:176–183`; `.planning/phases/38-runner-hardening-and-run-safety/38-01-PLAN.md:25,220–222`; `.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:33`; `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:67,121–128`.

**Suggestions**

- Record and verify identities for both processes before any signal. Keep the state and owned-tab evidence until cleanup is confirmed; on a failed probe, stop and report what remains rather than deleting the evidence. Verify by reading a saved result after the one live run. Bracket real-HOME work with the audit and retain only redacted evidence.
- Check eval shape before dispatch; distinguish `bar met`, `fixed under the no-rejudge rule`, and `unmet—owner decision`. Publish and validate final-round refutations before drawing the conclusion. Use the official same-rubric comparison rather than treating the scratch regression script as a second authority.
- Fix and self-check the scan’s repo root, remove the inherited exceptions that do not apply, and specify the hosted timing deliverable or record it as unverified. Do not count a killed fake lane as evidence of host output timing.

##### Ponytail findings

- **HIGH — Task 1:** The live proof is needed; a separate, weaker process-identity scheme is not. Follow the runner’s existing identity rules and the observed `tab list` shape. A read-only verification of captured results is enough after cleanup. `skills/ai-kit-spec-review/references/cross-ai.mjs:4738–4780`; `tmp/spec-discuss-35-39/probe38d.py:13–34`.
- **MEDIUM — Task 2:** Git-derived materiality and the fixed judge pool are needed. The inherited selector starts from the judge registry, so a changed, unregistered skill can disappear before materiality is tested. Discover changed `SKILL.md` paths first, then validate registry membership; explicitly expect the superpowers skill when 38-05’s behavior change lands. `tmp/judge-37/judged.py:84–100`; `.planning/phases/38-runner-hardening-and-run-safety/38-05-PLAN.md:235`.
- **HIGH — Task 3:** Reuse the canonical gated checker for the bar and treat stale digests separately. The scratch regression script chooses the last available round without filtering by rubric pin, an already observed disagreement. Give fixes the round that produced the findings before advancing `round.txt`. `tools/judge_loop.py:952–965,1376–1389`; `tmp/judge-37/regression.py:42–54`; `.planning/phases/37-shared-runner-options-and-session-ids/37-24-SUMMARY.md:68`; `.planning/phases/38-runner-hardening-and-run-safety/38-26-PLAN.md:192–194`.

**Risk assessment: HIGH.** Keep the live probe blocked until it proves ownership and preserves recovery evidence. Keep phase close blocked until the judge outcome is explicit and enforceable.

#### Cross-plan coverage and sequencing

- **Same-wave overlap:** None among the five reviewed plans: waves 17–21 each have one owner. Shared edits to the template, golden and docs are serialized. The on-disk 38-23 dependency on 38-01 and 38-24 dependency on 38-05 are present; the extra 38-27 dependency is the manifest discrepancy noted above. 38-26’s claimed hosted evidence dependency is a missing deliverable, not an ordering fix.
- **SPEC edges and prohibitions:** I found owners for the R1–R12 areas, but not complete proof for several claimed rows. R1’s timing disclosure and R11’s uniqueness/reread checks are incomplete in 38-23. The R5 human-concurrency backstop is assigned to 38-18, but lane-owned Git subprocesses do not exercise a second writer (`38-18-PLAN.md:23`). The R12 crash-during-sweep ordering edge is described by 38-20’s claim-directory design, but its listed crash test kills the **runner**, not the **sweeper** (`38-20-PLAN.md:26,206–214`). The prohibition on changing hosted answers is assigned to 38-19/21, but the flood case exercises **stderr** while stdout stays short (`38-19-PLAN.md:213–219`); it does not cover the SPEC’s oversized stdout case or the acknowledged read/truncate loss window. Also, 38-20’s proposed record reader accepts incomplete JSON objects as readable, allowing missing identity fields to become “not alive” rather than “unreadable and kept” (`38-20-PLAN.md:124–132`; `38-SPEC.md:698–702`). That prerequisite needs to fail closed before the live probe.
- **Compatibility evidence:** 38-08 specifies the byte-equal harness list, and 38-09 keeps the template/render comparison. The latter compares **two current copies**, so it cannot by itself prove that old `--print-argv` output changed only in the two allowed places. Use the existing normalized matrix against the pre-change template, stripping only the locked deltas. `tests/test_cross_ai_render_sync.py:151–213`; `38-08-PLAN.md:241–247`.

**Verdict: Revise before dispatch.** Fix the version-test blocker, the `partial` caller contract, the sweep proof and the judge close gate first.

**Not checked live:** No suites, Make targets, host calls or pane operations were run. Intermediate green commits, timing budgets and live cleanup remain execution evidence, not results of this review.

#### Batch G (38-19, 38-20, 38-21)

#### 38-19

##### Summary

The protocol update is well scoped: it adds `tab list` without adding a second herdr spawn site, and it routes hosted idle termination through the existing cleanup path. Tasks 2 and 3 are not ready to execute as written. The watchdog uses the wrong interface from 38-16, the timed fakes exit before their timers run, and the flood test does not exercise the stdout path whose answer parity it claims to prove.

##### Strengths

- Task 1 updates the runner allowlist, architecture check, and ordered protocol fixture together. The checks are substantive: `tests/test_arch.py:1898–1927` checks literal verbs and the single spawn site; `tests/test_runner_host_protocol.py:174–205` independently checks the refusal text and order.
- Task 2 keeps the existing hosted `finalize` path for signalling, draining, and cleanup. That preserves the process-group checks and avoids a second kill routine (`skills/ai-kit-spec-review/references/cross-ai.mjs:4973–5013`).
- Task 3 aims to distinguish *exactly* twice the cap from one byte over. That is a useful boundary test, even though its current fixture does not prove the full requirement (`.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:211–219`).

##### Concerns

- **HIGH — Task 2 calls the wrong idle interface.** `.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:170,183` supplies a function to `idleResetter`. 38-16 supplies an object and invokes `idleCtl.reset()` and `idleCtl.recheck()` on it (`.planning/phases/38-runner-hardening-and-run-safety/38-16-PLAN.md:125–136`). On hosted tree progress, the proposed callback will throw instead of resetting the clock. An idle check can also run before the next file poll observes bytes or `rc` already on disk; the proposed callback does not sample either before deciding to kill. The current poll is the only place that reads those files and settles a normal exit (`skills/ai-kit-spec-review/references/cross-ai.mjs:5026–5039`).
- **HIGH — Tasks 2 and 3 cannot pass their named cases as written.** The new `hdrip`, `hcommit`, and `hflood` modes schedule timers, but neither task adds them to `STICKY_FAKE` (`.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:187–193,218–223`). The fake dispatcher calls `process.exit(0)` immediately after a non-sticky mode returns (`skills/ai-kit-spec-review/references/cross-ai.mjs:6474–6479,6841–6844`). Changing the hosted hook cannot make those timers run. `hcommit` also ignores Git failures; even after fixing stickiness, its edits alone can reset the watchdog and make the “keeps committing” test pass.
- **HIGH — Task 3 can miss the disk bound and change the answer.** The truncate runs only after the existing synchronous read loop reaches EOF (`.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:217`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4963–4972`). A sustained writer can keep that loop busy and delay both the cut and timers. Truncating by pathname also need not target the inode being read if the path changes; a truncate error can recur in the final read and interrupt cleanup (`cross-ai.mjs:5007–5011,5028–5035`). Finally, `pushCapped` drops whole chunks, so different pipe and file chunk boundaries can retain different stdout tails even without a read/truncate race (`cross-ai.mjs:4568–4574,4653–4660,4963–4970`). The proposed case floods **stderr** with identical bytes and supplies a short stdout answer, so it cannot expose that difference or prove R12’s `3×` **`out`** case (`38-19-PLAN.md:213`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:524–529`).
- **MEDIUM — Task 1 pins a fake more tightly than the observed protocol.** `.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:33–34,128,135` acknowledges that the two exact error messages were not captured, but the test compares both messages byte for byte. The existing extracted-function test checks a generic exit and the verb refusal, not failure-code extraction (`tests/test_runner_host_protocol.py:174–191`). Treat the message strings as synthetic. I could not verify the cited scratch captures in this checkout; 38-26’s successful live sweep also does not by itself verify the two error replies.
- **MEDIUM — The executor cannot follow the isolation and gate instructions literally.** The objective requires the scratch wrapper for every test/helper, but the wrapper only runs `--self-test`, leaves outer `TMPDIR` unset, and invokes PATH `node`; Tasks 1 and 3 give bare test, list, and lint commands (`.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:96,133,147–153,223–238`). The harness creates a directory even in list mode (`skills/ai-kit-spec-review/references/cross-ai.mjs:7601,14757–14760`), and the lint recipes reach `uv run` without an offline guarantee (`Makefile:98–113`). The named Python modules and their `FAILED` banners are real (`tools/run_unittest_parallel.py:127–134,925–933`); the missing piece is a runnable, offline command path. Task 1 is at the five-file limit, and Task 3 repeats the full shard pass before a hook that can run selected shards again; there is no measured margin for retries under the task cap (`AGENTS.md:183–199`).

##### Suggestions

- Match 38-16’s `{ reset, recheck }` contract. Test output and `rc` at the expiry boundary before firing, and require positive evidence that the quiet fake made commits, not merely that it exited.
- Bound each poll’s work independently of the writer, truncate the same file being read, and specify the failure path so it still finalizes. Test a distinguishable stdout tail and expected verdict above the cap, not just a stderr size sequence. Use a poll acknowledgement rather than assuming a 700 ms sleep will observe the cut under load.
- Give every task one exact scratch command that can run its case list or named gate. Reuse the real-Node and grouped-run helpers (`tests/cross_ai_selftest.py:39–52,211–224,266–288`), and make offline lint prerequisites explicit.

##### Risk assessment

**HIGH.** The protocol slice is sound in structure, but the watchdog handoff and fake lifecycle are deterministic blockers. The output test can go green without proving hosted answer or status parity.

##### Ponytail findings

- **LOW — Task 1:** Required by D-27. Reuse `herdrCall` and the ordered fixture; no new client is needed. Also rename the stale `three_verbs` test label if 38-09 has not already done so (`tests/test_arch.py:2478`).
- **HIGH — Task 2:** Required by D-28. Reuse the existing timer/progress contract and `hostedChild.finalize`, not a parallel interpretation of the tree reset. The current `hostPair` is a useful pattern, but its status regex is applied automatically only to the second run (`cross-ai.mjs:7403–7409,7683–7701`); assert the first run’s trailer too.
- **MEDIUM — Task 3:** Truncation is required; the ambient `AIKIT_XAI_CAPTURE_MAX_BYTES` setting is not. It changes every `runChild` capture, including Git reads, not just the flood fixture (`cross-ai.mjs:4566–4574,4653–4660,5189–5194`). Prefer a harness-only reduced-cap copy or an internal test seam. If the ambient option stays, it is a product setting and needs an explicit contract and docs handoff.

#### 38-20

##### Summary

The sweep has the right shape: prove the run dead, claim its directory, remove secrets independently of herdr, then close only a matching tab. The proposed proof is too permissive for destructive cleanup. The plan also lacks a reliable startup bound and leaves several test contracts for an unattended executor to resolve.

##### Strengths

- The plan keeps the 15-field record and one `herdrCall` spawn site. Its tests distinguish wrong ID, wrong full label, null ID, hosting switched off, and server unavailable rather than using pane text as evidence (`tests/fixtures/runner_host_protocol.json:15–24`; `.planning/phases/38-runner-hardening-and-run-safety/38-20-PLAN.md:169–180`).
- It explicitly plans recovery of an abandoned claim. That is needed for the locked ordering edge: a sweep killed after deleting secrets must leave a record the next sweep can use (`38-20-PLAN.md:123,129–134`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:677`).

##### Concerns

- **HIGH — Task 1 can treat an unproven run as dead and delete outside the intended directory.** The proposed `readRunRecord` accepts a token, a label suffix and a host string, but not a valid version, complete label, runner or launcher identity, or a well-formed tab ID. Missing identity fields then fall through as dead. The scan does not require a real directory or a bounded regular `run.json`; `readOr` follows links and reads synchronously. Renaming a directory symlink does not make its target safe: child-path cleanup through that link still follows it. These are gaps in the proposed trust boundary, not the shipped writer (`.planning/phases/38-runner-hardening-and-run-safety/38-20-PLAN.md:124–133`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4446,4835,4871–4877`; `tests/fixtures/runner_host_protocol.json:16–24`). Likewise, malformed list entries or multiple full-label matches for a null ID must not be treated as proof of absence or ownership.
- **HIGH — Liveness differs from the lock contract.** Task 1 uses `pidAlive` and `/proc`-only start times, despite 38-14 already supplying the R3 start-time fallback and treating permission-denied probes conservatively. The claim probe can also treat an unreadable current start as a mismatch. For launchers, an empty `groupMembers` result can mean `/proc` was unreadable, not that the group is gone; after a verified start mismatch, the fallback can count the replacement leader itself. These are distinct from finding a surviving member after the original leader exited (`38-20-PLAN.md:124–131`; `cross-ai.mjs:4712–4715,4741–4779,4890–4893`; `.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:116–122`).
- **HIGH — Cleanup errors and the startup bound are under-specified.** Task 1 catches deletion errors as “best effort,” then can close the tab and count the directory as secret-free or omit a failure to remove it from the report. It also uses directory mtime as its only reread clock; repeated updates or future timestamps can prolong the wait. The claimed maximum of one two-second wait is not a sweep-wide bound: a successful list and earlier closes can precede a slow close, and `herdrCall` uses synchronous spawn with a timeout but no forced kill signal (`38-20-PLAN.md:123,128–135`; `cross-ai.mjs:4677–4685,4871–4877`). `sweep-herdr-hang` tests only a list that sleeps and exits, not a close failure or an occupied startup budget (`38-20-PLAN.md:208`).
- **MEDIUM — Tasks 1 and 2 leave flag precedence and fixture semantics ambiguous.** Inserting a bare `else if` *before* `} else if (a === '--describe')` places it inside the path-option branch unless the executor repairs the braces. In `main`, `--sweep` can also override `--print-argv` or `--classify-only` and mutate state on a supposed no-sweep call. The plan must specify mixed-flag behavior and add a planted-record negative test; a syntactically valid but nonexistent `--baseline` is another useful no-sweep case (`38-20-PLAN.md:136–137`; `cross-ai.mjs:6263–6280,14844–14852,14935–14970`; `.planning/phases/38-runner-hardening-and-run-safety/38-15-PLAN.md:197`). The Task 2 row mapper also asserts `expect.dirs` and call counts even where the row gives no value, and its `close-notfound` fake leaves a matching tab marked open, unlike the event it represents (`38-20-PLAN.md:171–184`).
- **MEDIUM — Task 3’s timing tests can pass without the advertised proof, and its kill target is not verified.** An `age 2s` line can result from late startup without any reread; two launched sweepers can run sequentially. Neither case tests takeover after a sweeper dies. The SIGKILL setup assumes a five-second delay is enough to publish the group, then signals a group read from disk without first checking its identity. The existing harness has readiness predicates and scratch-checkout-scoped reaping (`38-20-PLAN.md:207–213`; `cross-ai.mjs:7290–7334,7366–7375`). Use these rather than guessing readiness in a no-sandbox run.
- **MEDIUM — Execution budget and task inputs need tightening.** Task 1 spans argument parsing, startup, process proof, destructive cleanup, and new harness helpers; Tasks 2–3 add 15 more scenarios. The three-task/two-file count passes the structural limit, but this is the batch plan most likely to exceed roughly 300 new lines once its missing cases are added. Lines 121 and 217–232 repeat the scratch-wrapper and bare-gate mismatch from 38-19; Task 2 also relies on Task 1’s regexes and helper defaults instead of carrying exact test inputs in its own block (`.planning/phases/38-runner-hardening-and-run-safety/38-20-PLAN.md:121,169–184,217–232`).

##### Suggestions

- Specify validation against the shipped record and label grammar before claiming anything. Keep invalid records untouched; use regular, bounded reads, verify containment, require a unique valid tab match, and keep/report records when deletion or tab proof fails.
- Reuse the R3 identity probes and define one conservative interpretation of an unavailable probe. State exact precedence for `--sweep` and non-mutating modes, plus an overall startup budget that the code and tests can actually enforce.
- Replace time-based guesses with observable barriers: publish a fresh record during reread; hold the winning claim while the second sweeper runs; kill a sweeper after secret removal and prove takeover. Put those checks and the exact defaults in the owning task blocks.

##### Risk assessment

**HIGH.** This runs automatically and deletes files and tabs. Fail-closed validation, positive evidence of death, and honest cleanup reporting are prerequisites, not follow-up hardening.

##### Ponytail findings

- **HIGH — Task 1:** D-27 requires the sweep, including abandoned-claim recovery. Reuse `hostRunDir`, `hostLabel`, `HOST_FILES`, and the 38-14 probe behavior instead of independently defining the same identities (`cross-ai.mjs:4703–4709,4723–4733`; `38-14-PLAN.md:116–122`). Export only names the sibling actually imports for a test.
- **MEDIUM — Task 2:** The denial and recovery cases are required. Reuse `runCaseProcess`, `fakeTabs`, `hostCalls`, and `keptRecords` (`cross-ai.mjs:7341–7382,7703–7721`). Give simple rows explicit defaults and keep second-run recovery cases separate rather than growing a general-purpose case mapper.
- **MEDIUM — Task 3:** The crash and race tests are required; fixed sleeps and a case that passes for either serial or concurrent execution add time without establishing the race. Reuse `waitFor` and the tracked child pattern (`cross-ai.mjs:7325–7337,14632–14639`). Hand the verified timeout and claim behavior to 38-23 and 38-26, not the current stronger claims.

#### 38-21

##### Summary

Excluding only the runner-owned state subtree is a sensible reading of D-29: it avoids hiding the checkout when `XDG_STATE_HOME` is the repo root. The remaining blockers are more serious than the snapshot mechanics: there is a window where a live hosted executor is absent from the lock, and the proposed parity cases do not exercise a hosted blocking finding or a watchdog polling in-checkout state.

##### Strengths

- Task 1 reuses the private-index snapshot and covers both a literal special-character state path and the checkout-root case, with controls for tracked and ignored edits outside the state subtree (`skills/ai-kit-spec-review/references/cross-ai.mjs:5165–5218`; `.planning/phases/38-runner-hardening-and-run-safety/38-21-PLAN.md:112–125`).
- Task 2 targets the existing atomically rewritten lock and uses process liveness, not tab existence. Task 3 checks secret-file lifetime **from inside the lane**, where Phase 37 already deletes `env` and `prompt` before invoking it (`cross-ai.mjs:4810–4817,4982–4993`; `38-21-PLAN.md:149–156,179–187`).

##### Concerns

- **HIGH — Task 2 leaves a hard-kill window in which a second execute can start.** `pane run` can start the launcher before the runner’s first poll. The launcher writes `pid` before starting the lane, but the proposal records token, tab and group in the checkout lock only after runner-side adoption and after a separate `run.json` rewrite. A runner killed before either publication can leave an active lane with no recorded group; a kill between the rewrites can leave the sweep protecting a group the lock cannot see (`.planning/phases/38-runner-hardening-and-run-safety/38-21-PLAN.md:149–155`; `cross-ai.mjs:4815–4817,4943–4953,4982–4993,5026–5039`). The five-second setup deliberately arrives after normal adoption and cannot catch either case. A failed `lockUpdate` also continues without durable publication under 38-13’s contract (`.planning/phases/38-runner-hardening-and-run-safety/38-13-PLAN.md:181`). This violates the no-second-executor guarantee, not just the reporting requirement.
- **HIGH — The pre-lock sweep does not guarantee the stale holder was swept.** 38-21 assumes identical verdicts at two different times. A group can be live during the sweep and gone by the lock check, so the lock clears but that run’s directory was never cleaned. Another case is differing identity evidence between `run.json` and the lock. Preserve the hosting-off and unreachable exceptions, but specify targeted reconciliation when clearing a stale hosted lock (`38-21-PLAN.md:27,149–156`; `.planning/phases/38-runner-hardening-and-run-safety/38-20-PLAN.md:124–137`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:465–472`). The inherited orphan line also names the headless `child_pgid`, which the proposed hosted record leaves null; emit one accurate hosted refusal instead of following a misleading group line with a correction (`.planning/phases/38-runner-hardening-and-run-safety/38-14-PLAN.md:128`; `38-21-PLAN.md:154–156`).
- **MEDIUM — Task 1 leaves the Git edit set for the executor to infer.** Its fallback search names `git status` and `git diff`, but 38-18’s actual `diffNames` uses `diff-tree` on two tree-ish IDs, including a compare to `HEAD` for uncommitted changes. A snapshot-only exclusion can look like a deletion against a `HEAD` that already contains a tracked entry there. For subdirectory callers, make the pathname basis consistent across the whole-tree add, ignored listing and findings. Name the exact calls to change and explicitly decide what happens with tracked state and an older stored baseline, rather than silently broadening the exclusion (`38-21-PLAN.md:108,122–123`; `.planning/phases/38-runner-hardening-and-run-safety/38-18-PLAN.md:126–130`; `cross-ai.mjs:5177–5218`). The recorded subdirectory `git add` probe is useful evidence for that one command, not for the end-to-end path.
- **MEDIUM — Tasks 1 and 3 do not demonstrate the claimed R12 parity.** The state-home pairs do not enable the watchdog, so they cannot prove state writes never reset it. They also supply no task list; with no named `<files>`, 38-17 suppresses `outside_plan_files` by construction. The new findings pair uses `fake/nochange` and the harness’s default `prompt\n`, so both transports can agree on empty findings without exercising any blocking check (`38-21-PLAN.md:112–125,179–187`; `cross-ai.mjs:6506,7366–7367,7699–7701`; `.planning/phases/38-runner-hardening-and-run-safety/38-17-PLAN.md:171`). Running both halves in one repo and state home also lets the second run inherit changes or a baseline from the first; the existing `runTwice` does not reset either (`cross-ai.mjs:7385–7400`).
- **MEDIUM — Task 2’s test safety and Task 3’s verification wrapper need explicit instructions.** The stale case asks the unattended executor to signal recorded `pi`/`gc` PIDs without checking they still belong to this scratch case, and the “same setup” description is ambiguous about when to preserve or end the launcher. Use start identities, child handles, and scratch-scoped reaping (`38-21-PLAN.md:149–158`; `cross-ai.mjs:7290–7323`). The Task 3 commands repeat the bare list/lint issues (`38-21-PLAN.md:82,121,191–206`). Three tasks and two files fit the structural limit, but neither the repeated gate time nor time to resolve these integration gaps is demonstrated within the cap.

##### Suggestions

- Specify what the lock publishes **before** issuing `pane run` and how another runner safely resolves pending launcher identity. Test both interruption windows with readiness barriers, and preserve the lock when publication fails or liveness is unknown.
- Add one watchdog-on test that changes only runner state and still expires, and one hosted/headless execute pair with a nonempty blocking result and exact trailer, finding lines, exit, and empty stdout. Use separate equivalent checkouts, and reuse 38-18’s `planPrompt` and `fake/plan-commit` rather than adding another commit fake (`38-18-PLAN.md:134–138`).
- Pass the exact exclusion scope, hosted orphan message, and cleanup limits to 38-23/24. They should document the implemented guarantees, not assume that an automatic sweep always closed a stale holder’s tab.

##### Risk assessment

**HIGH.** The lock race can allow simultaneous edits on the same checkout. The parity tests would not establish the core safety guarantees even if they passed.

##### Ponytail findings

- **MEDIUM — Task 1:** D-29 requires the exclusion. Keep it centralized in `treeState` and the exact path consumers that need it, reusing the existing private-index and `diffNames` paths. Do not instruct the executor to add pathspecs to unknown future Git calls (`cross-ai.mjs:5165–5222`; `38-18-PLAN.md:126–130`).
- **HIGH — Task 2:** D-26 requires durable hosted identity. Reuse `writeCycleState`, `lockUpdate`, and one launcher-proof rule used by both sweep and lock. The missing work is making their publication and recovery agree across crashes, not adding another lock or a tab-based liveness check (`cross-ai.mjs:4501–4513,4982–4993`; `38-21-PLAN.md:153–156`).
- **MEDIUM — Task 3:** Secret and result parity checks are required; `host-findings-nochange` is a weak duplicate of existing no-change pairs. Replace it with a real plan-result case using the existing fixtures; keep the inside-lane scan and require a nonempty planted sentinel before asserting it was absent from files (`38-21-PLAN.md:179–187`; `cross-ai.mjs:7555–7560`).

##### Batch coverage and handoffs

- **Same wave:** No overlap. Waves 14, 15, and 16 each have one plan. The direct chain is 38-18 → 38-19 → 38-20 → 38-21 → 38-22; the earlier harness, lock and polling producers are transitive dependencies. The broken `idleResetter` handoff is an **interface mismatch**, not a missing dependency edge.
- **R12 edge/prohibition coverage:** All R12 rows have a stated owner in 38-19–21 or the 38-22–26 handoffs, but several are not closed by the proposed tests: the idle/output boundary and actual `3× out` parity (38-19); fresh-record reread, abandoned-claim takeover, and fail-closed cleanup on incomplete proof (38-20); watchdog isolation from in-checkout state, positive blocking-finding parity, and the pre-adoption live-group prohibition (38-21). The existing creation-order and mode pins are retained (`tests/test_runner_host_protocol.py:249–267`); `--describe` and the doc contract are downstream (`.planning/phases/38-runner-hardening-and-run-safety/38-22-PLAN.md:107–116`; `.planning/phases/38-runner-hardening-and-run-safety/38-23-PLAN.md:153–157`).
- **Intermediate gates:** The changes stay within stdlib Node and the fake-herdr path as proposed, and no new real model or provider names or Python complexity-cap violations were found in the three plans’ edits. Add an explicit pre-batch/post-batch `--print-argv` comparison allowing only the locked deltas: the existing matrix compares a template with a copy rendered from that **same** template, so both can drift together and still pass (`tests/test_cross_ai_render_sync.py:179–195`). Keep that separate from 38-25’s intentionally deferred live-copy refresh.

**Not checked live:** No files were changed, no tests or make targets ran, and no live host or herdr was contacted. The findings are from static inspection at `9f7a3c5`; exact live herdr failure envelopes and actual executor wall time remain unverified.

#### Batch C (38-07, 38-08, 38-09)

#### 38-07

**Summary.** The sequencing is right: remove the guard hits before moving the harness, and shrink the baseline in the same commits. Task 1 is a narrow, behavior-preserving cleanup. Task 2 needs revision: it directs the executor to carry real model names forward, and one of its acceptance commands cannot produce the stated result.

##### Strengths

- **The two-commit split matches the guard.** The baseline contains two identical `flag wins;` entries, and the guard compares per-path hit counts. Removing one occurrence with the runtime rewrite, then deleting the entry after the harness cleanup, avoids both a stale baseline and a new hit at the sibling path. (`tests/fixtures/no_hardcoded_models_baseline.json:727–746`; `tests/test_arch_hardcoded_models.py:265–286`)
- **The runtime messages can stay unchanged.** The parser already binds `a` to the flag, and the neighboring per-runtime branch uses the same `${a} must match` form. Splitting the other message at the string boundary preserves what callers see. (`skills/ai-kit-spec-review/references/cross-ai.mjs:6210–6231,14884–14886`)

##### Concerns

- **HIGH — Task 2 equates passing the scanner with meeting HUB-09.** The replacement instructions copy a real provider/model ID into two new lines, preserve a real model fragment in the constructed multi-slash ID, and explicitly leave real-ID examples in the grammar cases. A zero-hit scan does not make these acceptable: the guard’s slash regex does not cover every valid ID shape. (`.planning/phases/38-runner-hardening-and-run-safety/38-07-PLAN.md:147–152,179`; `tests/test_arch_hardcoded_models.py:48–56`; `skills/ai-kit-spec-review/references/cross-ai.mjs:8084–8096`)
- **MEDIUM — Task 2’s whole-file count cannot be zero.** The edit changes the two reads in the `no-second-cli-` map, but unrelated matches remain in `row.modelSuffix` and in the classifier-fixture serializer’s `row.model` assignment. An unattended lane could stop on a correct edit or change an unrelated caller to satisfy the count. Task 2 also uses Task 1’s `st.sh` and `list-before.txt` without naming them as prerequisites in its action. (`.planning/phases/38-runner-hardening-and-run-safety/38-07-PLAN.md:104–105,139–164`; `skills/ai-kit-spec-review/references/cross-ai.mjs:1629,13583–13595,13769–13775`)
- **MEDIUM — The verification does not directly prove both message contracts.** `--self-test-list` prints only case names and kinds; Task 1 runs the alias-precedence test but omits the existing `model-floor-refuses-*` cases that assert the exact error. The render matrix compares two copies of the *current* code, not before versus after. (`.planning/phases/38-runner-hardening-and-run-safety/38-07-PLAN.md:119–124,201`; `skills/ai-kit-spec-review/references/cross-ai.mjs:7936–7941,14757–14759`; `tests/test_cross_ai_render_sync.py:179–189`)

##### Suggestions

- Use invented **nonmatching** IDs for the provider test, preserving the three assertions: prefix match, prefix mismatch, and router bypass. Use entirely invented segments for the two-slash case, and assert the full ID reaches preview argv. Scope the renamed-field check to the two map expressions.
- Name the Task 1 scratch handoff in Task 2. Add the existing floor-refusal cases to Task 1’s focused check and use the resolved Node executable rather than the PATH shim, as R8 requires. (`.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:393–397`; `tests/cross_ai_selftest.py:39–52`)

##### Ponytail findings

- **LOW — Task 1:** Needed for R8 and minimal. Keep the existing parser idiom and shrink the fixture alongside the source. Reuse the exact-message cases rather than adding another parser test. (`skills/ai-kit-spec-review/references/cross-ai.mjs:6231,7846–7858,7936–7941`)
- **MEDIUM — Task 2:** Needed before the move. Keep the existing case table and the shrink-only guard; neither a new exception nor an obfuscated real identifier is needed. The renamed fixture field is local to the map, and the classifier and grammar cases can use synthetic inputs without losing coverage. (`skills/ai-kit-spec-review/references/cross-ai.mjs:2011–2017,8081–8096,13556–13604`; `tests/test_arch_hardcoded_models.py:265–286`)

**Risk assessment: MEDIUM.** Two tasks and two files are within the execution envelope, but the false acceptance check and the HUB-09 conflict can stop the lane or ship the wrong result. Wave 2 peer 38-06 has no write overlap or output dependency with 38-07; 38-02’s added case is correctly upstream. (`.planning/phases/38-runner-hardening-and-run-safety/38-06-PLAN.md:5–12`; `.planning/phases/38-runner-hardening-and-run-safety/38-02-PLAN.md:132–147`; `.planning/phases/38-runner-hardening-and-run-safety/38-07-PLAN.md:5–10`)

#### 38-08

**Summary.** The four-block splice is a sound way to move the harness without changing the render contract. The plan accounts for the mutable bindings, the signal handlers, and both tests that run a copied template. Its main blocker is an execution recipe that cannot be rerun as written. The generated export list also misses part of the locked R8 handoff.

##### Strengths

- **The module boundary is well chosen.** The four cut ranges leave runtime routing and liveness in place. One trailing export list preserves the host protocol test’s function extractor, which expects declarations to begin with `function` or `async function`. The setter and abort-hook seam keeps the behavior of the existing mutable bindings and signal handling. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:118–120,277–285`; `skills/ai-kit-spec-review/references/cross-ai.mjs:1354–1365,2758–2778,5262–5279`; `tests/test_runner_host_protocol.py:30–41`)
- **It follows the important copy callers.** The missing-kind mutation has to alter the sibling; the old rendered smoke test has to supply the sibling explicitly. Ordinary rendering still writes only the runner, and the installer already links the entire skill directory. (`tests/test_cross_ai_runner_e2e.py:412–434,509–524`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:265–272,358–366`; `tools/setup.py:1806–1819,4531–4534`)

##### Concerns

- **HIGH — Task 2 executes the splice twice.** Action step 2 runs `splice.py`, then step 4 says to run the verify commands, whose first command is `splice.py` again. The script exits immediately when the sibling already exists. The prescribed rerun after an import/export repair has the same problem. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:246–252,425–427,502–504`)
- **MEDIUM — The generated export list does not deliver all five locked liveness exports.** The script exports only names referenced in the moved text; `KEPT` checks presence in the runner, not export membership. Applying the plan’s transformations in memory to the checked-out source yielded 95 names, with only `pidAlive` among the five. The downstream plans explicitly add `procStartTime` and `groupMembers` when needed, but that does not make the 38-08 handoff conform to R8. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:325–328,384–412`; `.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:393–397`; `.planning/phases/38-runner-hardening-and-run-safety/38-20-PLAN.md:138`)
- **MEDIUM — The write-and-rollback path is not safe under the lane’s execution rules.** It writes both worktree paths before validation, does not catch interruption, and on handled failure deletes the sibling outside `tmp/`, which the plan forbids. Task 2 adds roughly 9,500 lines by *moving* them, not writing them by hand, but the 25-attempt loop, subprocess timeouts, full shard verification, global lint, and commit hook have no combined budget. Task 3 separately budgets 10–13 minutes for its hook alone. This is a cap risk, not a measured overrun. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:80–90,413–465,502–509,540–554`)
- **MEDIUM — Tasks 1 and 2 do not use one hermetic Node recipe.** The shell probes invoke PATH `node` after replacing `HOME`; `splice.py` separately resolves the shim before it constructs the scratch environment, uses a bare subprocess timeout for that lookup, and leaves `node --check` outside the scratch env. The repo specifically documents the shim’s re-exec/process-chain failure mode. Task 2 also consumes Task 1’s `st.sh` without stating that handoff in the action. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:118,336–357,415–418,479–507`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:951–969`; `tools/run_unittest_parallel.py:400–423`)
- **LOW — Task 3’s mapper check proves selection, not the reason stated in the new comment.** The mapper matches the skill folder for any file under it; it does not require a `SIBLING` reference to select the shards. The installer command also needs to point at the actual `link_one` call, not just the delegating headless function. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:538–545`; `tools/staged_mapper.py:129–154,223–240`; `tools/setup.py:1814–1819,4531–4534`)

##### Suggestions

- Make the splice a **one-time action**. Build and validate the candidate pair under `tmp/` before publishing it; make all subsequent verification read-only and rerunnable. Explicitly include and check the five required liveness exports. Keep 38-25 as the owner of the live-copy refresh and timing re-record.
- Put the exact scratch environment, real-Node resolution, output evidence, and remaining time before commit in each task that uses them. Use the existing shard runner for the full pass instead of prescribing repeated full passes on a repair.
- Tie the missing/empty/unreadable behavior to a regular-file check and handle file-read failures at import as refusal, while preserving syntax or module errors as failures. The current access/stat precheck cannot cover a file that disappears or becomes unreadable before `import()`. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:294–310`; `skills/ai-kit-spec-review/references/cross-ai.mjs:15169–15176`)

##### Ponytail findings

- **LOW — Task 1:** The setters, abort hook, and runner filename are needed for the split. Reuse the existing handlers and `writeCopy` rather than introducing a new lifecycle object; the plan does that. (`skills/ai-kit-spec-review/references/cross-ai.mjs:1354–1365,5262–5279,6399–6429`)
- **MEDIUM — Task 2:** The scripted cut is needed; repeatedly writing the worktree and interpreting Node errors to rebuild it is not. Keep the marker checks and byte comparison, and make the existing shard and copied-runner tests the validation of one candidate pair. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:365–381,425–465`; `tests/cross_ai_selftest.py:260–288`)
- **LOW — Task 3:** Keep the named path and mapper evidence requested by the plan map. Use the constant in the harness-aware callers and describe the existence assertion as a shipping check, not a mapper feature. No installer or renderer change is needed. (`tests/cross_ai_selftest.py:55–57,211–226`; `tools/staged_mapper.py:146–154`; `tools/setup.py:1814–1819`)

**Risk assessment: HIGH for unattended execution.** The second splice invocation is a definite stop as written. There is no same-wave file conflict: 38-08 is alone in wave 3 in the supplied manifest; the checkout also contains a wave-3 38-27 outside the manifest, whose declared writes are disjoint. The locked final re-render and timing handoff is present in 38-25. (`.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:5–12`; `.planning/phases/38-runner-hardening-and-run-safety/38-27-PLAN.md:5–12`; `.planning/phases/38-runner-hardening-and-run-safety/38-25-PLAN.md:145–169,175–189`)

#### 38-09

**Summary.** The rendered-copy test and the port of the config-write guards are useful. The main gap is in what the new architecture checks claim to prove: their regexes catch the demonstrated spelling, not the full import/export and host-call contracts.

##### Strengths

- **The fake-lane test exercises the right path without loading the harness.** It uses the real `ensure_runner` path, a scratch checkout, and the existing fake’s model listing and JSON answer. The runner’s review formula does not pass the write-triggering `--auto` flag. The locked byte-sync check remains unchanged. (`tests/test_cross_ai_render_sync.py:101–148`; `tests/test_cross_ai_runner_e2e.py:70–145`; `skills/ai-kit-spec-review/references/cross-ai.mjs:1405–1416,15070–15085`)
- **The config-write scan gets a positive control.** Requiring the moved `runSelfTestCase` label means that forgetting to scan the sibling now fails the test. This reuses the existing scanner and the scratch-config write, rather than broadening the allowlist. (`.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md:194–197`; `tests/test_config_callers.py:139–155,219–230`; `skills/ai-kit-spec-review/references/cross-ai.mjs:7524–7540`)

##### Concerns

- **MEDIUM — Task 2’s import check can pass a second valid list.** It counts only the exact multiline format in its regex, so a second one-line named import or export is invisible. Its mutation table has no two-list case, despite the threat register claiming that coverage. It also cannot detect a symbol removed from both lists but still referenced in a case body; that is a runtime `ReferenceError`, not a load error. Downstream 38-10 says the arch rule fails if either side is omitted. (`.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md:23–24,158–168,233`; `.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:133`; `skills/ai-kit-spec-review/references/cross-ai.mjs:14757–14769`)
- **MEDIUM — The sibling host-call guard is narrower than “never spawns herdr.”** It inherits single-line matching for specific spawn spellings. For example, a normal multiline call whose first argument is on the next line is not matched. The existing test-module tripwire does not independently stub herdr. Treat this as a structural check for the supported call forms, and keep fake-only PATH as the execution boundary. (`.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md:164–168,235`; `tests/test_arch.py:1864–1885`; `tools/run_unittest_parallel.py:228–235`; `skills/ai-kit-spec-review/references/cross-ai.mjs:6377–6396`)
- **MEDIUM — Task 1’s timeout can leave the fake lane behind.** `subprocess.run(..., timeout=120)` can kill Node without giving its signal handler a chance to finalize the detached child. The test helper already has group-aware timeout cleanup. The fallback “use the form `_dispatch` produces” also leaves the executor to translate a Python dispatch wrapper back into a direct invocation of the rendered copy; the source supports specifying that direct invocation now. (`.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md:124–127`; `skills/ai-kit-spec-review/references/cross-ai.mjs:4633–4645,5262–5279`; `tests/cross_ai_selftest.py:176–208`; `tests/test_cross_ai_runner_e2e.py:564–572`)
- **LOW — Task 1’s size thresholds and Node prerequisite are unnecessarily brittle.** The 4,096-byte and half-copy ratios can fail after legitimate config or runtime growth; neither proves how many bytes were removed. The new tests also hard-fail when Node is unavailable, while the adjacent preview matrix and existing fake-lane tests use named skips. (`.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md:117,124–125`; `tests/test_cross_ai_render_sync.py:101–125,179–189`; `tests/test_cross_ai_runner_e2e.py:555–562`)

##### Suggestions

- Mutate the import/export check with a second list and a missing export. State explicitly that the shards, not the structural check or `--self-test-list`, catch missing imports used only in case bodies. Keep the architecture check source-only; do not add a JS parser dependency for this.
- Keep the byte-sync and harness-marker checks. Use 38-08’s before/after byte counts for the size-reduction evidence. Pin the direct fake-lane argv and use the existing process-group cleanup pattern, with stdin supplied explicitly and scratch HOME/state/config set for the child.

##### Ponytail findings

- **MEDIUM — Task 1:** Needed for R8. Reuse `render_copy`, the fake opencode writer, and the existing group cleanup pattern. The smoke test should prove the rendered runner works by itself, not enforce a long-term size ratio or add another dispatch layer. (`tests/test_cross_ai_render_sync.py:128–148`; `tests/test_cross_ai_runner_e2e.py:118–145`; `tests/cross_ai_selftest.py:176–208`)
- **MEDIUM — Task 2:** Needed for R8 adjacency and the no-client guard. Reuse `runner_jev_hits` and the existing non-vacuity pattern; keep the new import/export check small, but make its mutations cover what it promises. (`tests/test_arch.py:1889–1927,3501–3537`)
- **LOW — Task 3:** Needed to preserve coverage across the file move. Reusing `enclosing_function` and `js_gsd_write_sites` is enough. Keep the positive `runSelfTestCase` assertion; no production changes or new test module are needed. (`tests/test_config_callers.py:66–80,139–155,203–230`)

**Risk assessment: MEDIUM.** This is a three-task, three-file test-only plan with no wave-4 peer. It depends explicitly on 38-08; 38-10 consumes its export check and 38-19 later widens the runner’s verb guard, so both should inherit the corrected scope of the test. (`.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md:5–10`; `.planning/phases/38-runner-hardening-and-run-safety/38-10-PLAN.md:5–6,133`; `.planning/phases/38-runner-hardening-and-run-safety/38-19-PLAN.md:124,137`)

#### Coverage and disposition

**Revise before dispatching.** Fix the 38-07 fixture and acceptance instructions and the 38-08 double invocation first. The three plans assign all five R8 edge rows: 38-08 owns ordering, concurrency, encoding, and the loader’s empty-file behavior; 38-09 owns adjacency and the rendered-copy refusal tests. The uncovered **evidence** is the unreadable/import-time refusal case and the overclaimed parts of the structural checks. The R8 no-live-`.planning/` prohibition and the no-real-host/client prohibition are assigned to 38-09; 38-08’s `prohibitions: []` should also carry the latter where it actually runs the migrated harness. The remaining phase rows have owners in the supplied map; their implementation coverage was outside this batch. (`.planning/phases/38-runner-hardening-and-run-safety/38-SPEC.md:650–654,695–696`; `.planning/phases/38-runner-hardening-and-run-safety/38-08-PLAN.md:25–40`; `.planning/phases/38-runner-hardening-and-run-safety/38-09-PLAN.md:23–38`)

**Verification limit:** Read-only source inspection and an in-memory splice check at `9f7a3c5`; no files changed, and no suites, hooks, live hosts, or herdr calls ran. End-to-end behavior and task wall times remain unverified.
