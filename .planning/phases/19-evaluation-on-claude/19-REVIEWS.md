---
phase: 19
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-17T10:00:00Z
plans_reviewed: [19-01-PLAN.md, 19-02-PLAN.md, 19-03-PLAN.md, 19-04-PLAN.md, 19-05-PLAN.md, 19-06-PLAN.md, 19-07-PLAN.md, 19-08-PLAN.md, 19-09-PLAN.md, 19-10-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
cycle: 2
reviewed_revision: b10ff51
---

# Cross-AI Plan Review — Phase 19 (convergence cycle 2)

Cycle 1's review is in git history at `291d253`; the plans were revised in `b10ff51`. This
cycle's reviewer verified the Review Dispositions Ledgers and raised only new or open findings.

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review (opencode-plan-review)

## 19-01

**Summary:** The default Claude matrix is soundly designed, and the cycle-1 corrections for environment merging and the informational runtime case are reflected in the revised contract. The remaining concern is the advertised non-Claude reuse.

**Strengths**
- Passing the **same environment through both apply seams** fixes the actual last-merge problem: `_real_run` merges per-call values over its child environment. See [19-01-PLAN.md:294–300](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L294) and `tests/test_curated_config_apply_e2e.py:88–91,200–215`.
- Explicitly seeding and reading back `runtime: codex` creates the condition the informational row examines. This correctly accounts for `config-new-project` excluding runtime from defaults. See [19-01-PLAN.md:307–313](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L307) and `.claude/gsd-core/bin/lib/config.cjs:401–414`.

**Concerns**
- **MEDIUM · NEW — Host parameterization does not extend to the oracle or controls.**  
  [19-01-PLAN.md:254–279,302–306](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L254) exposes `--host`, but `promised()` returns tier aliases without applying `model_profile_overrides.<host>.<tier>`. The real resolver uses those mappings on non-Claude runtimes: `.claude/gsd-core/bin/lib/model-resolver.cjs:106–135,597–617`. Consequently, a correct Codex model ID can fail against expected `"opus"`, and the Claude omit control does not retain the same meaning.

**Suggestions**
- Separate expected **tier** from expected **model**, including runtime-tier mappings and runtime-specific controls.
- Alternatively, explicitly restrict this matrix to Claude and defer non-Claude support rather than presenting it as ready for Phase 20.

**Risk Assessment: MEDIUM.** The default Claude proof is credible; the advertised cross-host reuse can produce false defect reports.

## 19-02

**Summary:** E now has a supported resolution, and the event contract preserves command/result pairing. B/D’s cache-preservation mechanism remains only partially corrected. Historical entrypoint selection and runner failure handling also need changes before paid pressure runs.

**Strengths**
- E’s answer authorizing execution to be disabled matches the product mechanism: setting `workflow.cross_ai_execution false` strips the dependent command and artifact. See [19-02-PLAN.md:226–230,297–303](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L226) and `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:140–177,299–307`.
- The revised transcript contract retains tool IDs, result IDs, error status and full result text, enabling meaningful grading rather than command-presence checks. See [19-02-PLAN.md:345–355](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L345).

**Concerns**
- **HIGH · PARTIALLY-RESOLVED — B/D’s catalog preservation check still rejects normal inventory behavior.**  
  [19-02-PLAN.md:258–277,294–296](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L258) seeds two files and requires byte identity afterward. However, catalog fetch freshness uses the separate `model-catalog.json.fetch-meta.json` sidecar, which `seed_cache` does not create. Fetch also rewrites the catalog on every invocation, including skipped fetches, with different formatting. See `tests/test_curated_config_inventory.py:64–72`, `skills/ai-kit-spec-review/ai_kit_spec/cli.py:485–501,530–541,606–626`, and `ai_kit_spec/cache.py:23–24`. Fixing the Claude runtime row therefore does not prevent external fetching or the expected catalog rewrite.

- **HIGH · NEW — RED-b can select an installed entrypoint instead of the worktree script.**  
  Materializing adjacent symlinks and testing their `--help` does not control the historical discovery loop ([19-02-PLAN.md:248–253,307–310](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L248)). At `7009d22^`, `skills/ai-kit-gsd-curated-config/SKILL.md:40–45` searches plugin and installed locations **before** its own directory. The runner retains real `HOME`; `child_env` does not remove `CLAUDE_PLUGIN_ROOT` (`skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:130–140`). A shadow installation can therefore make RED-b exercise another product revision.

- **MEDIUM · NEW — Failed model turns can be reported as successful harness runs.**  
  [19-02-PLAN.md:332–343](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L332) records `result.is_error`, but only contamination and timeout determine failure. Process return codes and missing terminal results are not gated. A clean init followed by a provider error can proceed into grading as a skill failure. Existing supervision preserves and interprets return codes: `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:476–486,504–516`.

- **MEDIUM · PARTIALLY-RESOLVED — Primary-group cleanup misses known detached descendants.**  
  The new group ownership addresses ordinary descendants, but inventory refresh creates children with `start_new_session=True`: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py:199–214`. Those children are outside Claude’s group and can survive its timeout cleanup ([19-02-PLAN.md:325–331](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L325)). Existing supervision separately reaps recorded groups: `ai_kit_spec/runner_dispatch.py:318–324,377–388`.

- **LOW · NEW — E’s self-check calls the wrong module.**  
  [19-02-PLAN.md:300–303](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L300) names `plan_io.needs_choice_keys`; that function is defined in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:61–73`, not `plan_io.py`. Following the contract literally raises `AttributeError`.

**Suggestions**
- Seed catalog fetch metadata and establish the catalog’s normal serialized fixed point before preservation checks.
- Pin RED-b’s entrypoint explicitly at the harness level, with a shadow-install negative test.
- Require successful process exit, valid init/result events and `is_error == false`; stop scripted continuation on infrastructure failure.
- Add detached-grandchild cleanup coverage and correct the helper reference.

**Risk Assessment: HIGH.** Otherwise fixture and infrastructure behavior can be mistaken for instruction-quality failures.

## 19-03

**Summary:** The original zero-approval and post-write-disclosure loopholes are substantially improved. Several remaining predicates still certify less than the stated requirements, and the evidence parser does not fail closed on missing material.

**Strengths**
- Pairing commands with results now supports the product’s structured apply reports. See [19-03-PLAN.md:206–219](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L206) and `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:744–764`.
- Required follow-ups now distinguish zero-required from nonempty-required cases. The source provides both required rows and fingerprint-bound approval arguments: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:332–357,380–387`.

**Concerns**
- **HIGH · PARTIALLY-RESOLVED — Baseline disclosure is still measured before a non-mutating command.**  
  `first_write` includes `ensure-project` ([19-03-PLAN.md:213–217,236–238](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L213)). B/D already have configs, and `config-new-project` returns immediately without writing when one exists: `.claude/gsd-core/bin/lib/config.cjs:458–465`. A baseline that runs the required no-op, then discloses removals before its first actual mutation, incorrectly fails. The kept v1 flow explicitly requires this initial command: `skills/ai-kit-gsd-curated-config/references/v1-path.md:10–12`.

- **HIGH · NEW — B’s model checks do not establish the effective vendor or execution target.**  
  The proposed vendor rule treats a bare Cursor model’s vendor as `"cursor"` ([19-03-PLAN.md:223–231](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L223)). Thus `claude-opus-5-5-high` passes despite being Anthropic; the existing inference recognizes `claude-` correctly (`skills/ai-kit-spec-review/ai_kit_spec/vendor.py:20–27,38–48`). Separately, a router string anywhere in the runner—or only in `.new`—does not prove pi uses it. V1 can legitimately supply its model through hook arguments instead (`ai_kit_gsd_curated_config/cross_ai_build.py:87–92`), while `.new` is explicitly inactive (`SKILL.md:199–202`).

- **HIGH · PARTIALLY-RESOLVED — “Successful approval” does not require successful required follow-ups.**  
  [19-03-PLAN.md:247–253](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L247) checks tool-level success and absence of `"refused"`, not matching approval arguments or result rows. A failed `followups …; true` shell command can pass. Actual output includes per-follow-up `returncode`, and failures return CLI exit 1: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:396–420,448–481`; `cli.py:739–741`.

- **HIGH · NEW — D can pass without showing the promised full diff.**  
  D checks removal-key mentions and final policy removal, but not disclosure of additions, changes or kept settings ([19-03-PLAN.md:243–244,265–268](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L243)). An assistant can show only removal names and pass all five checks. That does not satisfy `19-SPEC.md:54–56`; the product exposes the four row kinds and before/after values in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:119–145`.

- **HIGH · PARTIALLY-RESOLVED — Incomplete evidence can still pass the digest/cell gates.**  
  The section check requires only one live digest-bearing row; `cells` silently omits absent columns or rows ([19-03-PLAN.md:288–303,395–403](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L288)). A correct sonnet digest beside a pending/missing opus digest still supplies that row. Removing an expectation or requested GREEN column can yield no failing output at all. Consumers then accept the empty extraction, for example [19-09-PLAN.md:306](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L306).

**Suggestions**
- Distinguish actual mutations from write-capable no-ops.
- Grade the effective hook and active runner configuration, using sourced vendor classification.
- Match approval targets, IDs and fingerprint; require expected result IDs with zero return codes.
- Add full-diff disclosure coverage.
- Validate exact scenario row sets, required columns and required digest cells; missing material must be an error.

**Risk Assessment: HIGH.** Tests faithfully implementing these predicates could still manufacture false GREEN results.

## 19-04

**Summary:** The skill-reference serialization and first-run backup corrections match source. Choice resolution and the forced-failure experiment still need stronger semantics.

**Strengths**
- The revised skill readback comparison recognizes the documented serialized forms instead of comparing bare names directly. See [19-04-PLAN.md:229–234,293–296](.planning/phases/19-evaluation-on-claude/19-04-PLAN.md#L229), `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:92–115`, and `skills.py:156–167`.
- Both scratch paths now receive validation, with no prior backup expected for an absent config. This matches `config_backup.py:110–120` and [19-04-PLAN.md:235–250](.planning/phases/19-evaluation-on-claude/19-04-PLAN.md#L235).

**Concerns**
- **HIGH · NEW — Generic choice resolution can replace a derived runner command with a placeholder.**  
  [19-04-PLAN.md:223–226](.planning/phases/19-evaluation-on-claude/19-04-PLAN.md#L223) forces a placeholder into every empty-candidate entry. But an unresolved runner model also produces an empty-candidate `workflow.cross_ai_command` entry: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:873–884`. Resolving the artifact afterward clears its status but does not restore the command value (`plan_edit.py:374–384`). Apply can consequently succeed with a forced, unusable `smoke-placeholder` hook.

- **HIGH · NEW — The forced failure does not require anything to be restored.**  
  The experiment runs after the successful idempotent reapply and changes only the reviewer entry to an invalid value ([19-04-PLAN.md:240–247](.planning/phases/19-evaluation-on-claude/19-04-PLAN.md#L240)). Unchanged writes are omitted (`apply.py:809–817`), and gsd-core rejects the invalid reviewers before mutation (`.claude/gsd-core/bin/lib/config.cjs:1045–1050`). A broken restore routine that merely clears the marker could therefore pass this smoke. The existing nth-key test supplies a stronger pattern: `tests/test_curated_config_apply_e2e.py:322–347`.

- **MEDIUM · NEW — Smoke drops the selected host when invoking the matrix.**  
  [19-04-PLAN.md:252–253](.planning/phases/19-evaluation-on-claude/19-04-PLAN.md#L252) omits the host argument, whose upstream default is Claude ([19-01-PLAN.md:254–255](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L254)). Thus `smoke --host codex` produces mixed-host evidence.

**Suggestions**
- Resolve artifact choices first, reload the plan, and let the derived command close automatically.
- Force failure only after a successful, observably different write in the same transaction; assert that mutation was undone.
- Pass the selected host through to `run_matrix`, with an injected propagation test.

**Risk Assessment: HIGH.** The smoke can otherwise pass with the wrong execution hook or a rollback experiment that never exercised restoration.

## 19-05

**Summary:** The retained snapshot and three-class failure triage resolve the cycle-1 concerns. A remaining safety claim overlooks a known side effect of live runtime enumeration.

**Strengths**
- Snapshot retention now matches post-plan verification: [19-05-PLAN.md:229–242](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L229) retains its input until phase close.
- Triage now distinguishes documented serialization from product failure, consistent with the conversion in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:104–115`. See [19-05-PLAN.md:174–179](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L174).

**Concerns**
- **HIGH · NEW — Live inventory can write real Cursor configuration outside the protected set.**  
  The plan permits real-cache refresh but claims no other writes outside scratch ([19-05-PLAN.md:136–138](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L136)). With a stale runtime cache, inventory invokes detection; `build_runtimes_snapshot` enumerates installed runtimes (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:986–1010`). Cursor enumeration explicitly documents rewriting `~/.cursor/cli-config.json`’s `privacyCache` (`detection.py:304–311`). The snapshot contract does not cover that file ([19-01-PLAN.md:229–239](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L229)). This is a known normal-path side effect, not hypothetical agent escape.

**Suggestions**
- Preserve the required real GSD-defaults read while isolating mutating non-Claude enumeration.
- Add a stale-cache safety case. Merely hashing Cursor config afterward would detect—but not prevent—the prohibited write.

**Risk Assessment: HIGH.** The current smoke can alter real tool configuration while reporting its protected set unchanged.

## 19-06

**Summary:** Separating baseline outcomes from v2 workflow checks is a substantial improvement. State preservation is better, but its procedure assumes a config exists in a scenario intended to stop before creating one, and the committed record still omits some verdict inputs.

**Strengths**
- The baseline table no longer automatically fails v1 for lacking `plan.json`, matching v1’s direct-write interface. See [19-06-PLAN.md:224–238](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L224) and `skills/ai-kit-gsd-curated-config/references/v1-path.md:27–38`.
- Copying state before deleting each run directory addresses much of the earlier evidence-loss problem ([19-06-PLAN.md:197–205](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L197)).

**Concerns**
- **MEDIUM · NEW — A correct C stop cannot satisfy the required config-copy assertion.**  
  C’s fixture does not seed a project config ([19-02-PLAN.md:255–257,284–288](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L255)); `scratch_inventory` only saves inventory (`tests/test_curated_config_apply.py:471–484`). C is expected to make no real write. Nevertheless, the cell procedure copies `config.json` unconditionally and acceptance requires one per graded cell ([19-06-PLAN.md:202–205,316](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L202)).

- **MEDIUM · PARTIALLY-RESOLVED — Some committed verdicts remain impossible to recompute after cleanup.**  
  The compact record retains command error flags and plan-entry triples, but not effective runner configuration, candidate sets, parsed dry-run facts, required follow-up rows/fingerprint or approval result rows ([19-03-PLAN.md:278–286](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L278)). Result heads are limited to 200 characters; actual follow-up reports contain materially later data (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:881–893`). The state-copy list also omits the runner, and final cleanup deletes retained scratch state ([19-10-PLAN.md:300–302](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L300)).

**Suggestions**
- Preserve an explicit “config absent” fact for C instead of requiring a nonexistent file.
- Extend the compact record only with the additional facts needed to recompute execution, preview, candidate and approval checks.

**Risk Assessment: MEDIUM.** The comparison is materially fairer, but correct stopping behavior and later evidence auditability remain vulnerable.

## 19-07

**Summary:** The ordered-step test and stable rule pins correctly address cycle 1. The final evidence gate accidentally turns a deliberately non-gating observation into a blocker.

**Strengths**
- The proposed six-label ordering assertion matches the current skill structure, which I independently checked. See [19-07-PLAN.md:214–218](.planning/phases/19-evaluation-on-claude/19-07-PLAN.md#L214) and `skills/ai-kit-gsd-curated-config/SKILL.md:69–148`.
- One pin per behavioral rule avoids the earlier sentence-by-sentence coupling while retaining command parsing and no-habitual-force checks. See [19-07-PLAN.md:209–212](.planning/phases/19-evaluation-on-claude/19-07-PLAN.md#L209) and `tests/test_curated_config_apply.py:2320–2339`.

**Concerns**
- **MEDIUM · NEW — A non-gating disclosure failure cannot complete the plan.**  
  REFACTOR runs only for gating failures ([19-07-PLAN.md:344–350](.planning/phases/19-evaluation-on-claude/19-07-PLAN.md#L344)), but final verification rejects **every** bare `fail` and acceptance requires every cell to pass or become unresolved (`:364–368`). B’s `ensure_runner_disclosed` is expressly non-gating, including a test requiring its failure to preserve exit 0 ([19-03-PLAN.md:254–255,345–346](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L254)). All required behavior can pass while this advisory row prevents completion, with no authorized repair/routing branch.

**Suggestions**
- Preserve gating metadata in the evidence reader and apply the final predicate only to gating rows.
- Keep advisory failures visible without requiring skill edits or owner escalation.

**Risk Assessment: MEDIUM.** The editing discipline is strong, but final acceptance disagrees with the declared evaluation policy.

## 19-08

**Summary:** The revised aggregate correctly prevents one passing judge from concealing another available judge’s findings. Invalid review execution still needs to be distinguished from genuine provider unavailability.

**Strengths**
- Pi review mode really restricts tools to `read,grep,find,ls`: `skills/ai-kit-spec-review/references/cross-ai.mjs:284–294`.
- The all-live-rows aggregation now matches the cited precedent and preserves conflicting scores. See [19-08-PLAN.md:204–210](.planning/phases/19-evaluation-on-claude/19-08-PLAN.md#L204) and `.planning/phases/18.1-one-runtime-model/18.1-22-PLAN.md:39`.

**Concerns**
- **HIGH · NEW — Review-contract failures become waiver-compatible “unavailable” rows.**  
  [19-08-PLAN.md:187–189](.planning/phases/19-evaluation-on-claude/19-08-PLAN.md#L187) converts any non-retryable failure into `judge unavailable`, which the aggregate permits. The runner distinguishes `contract_violation`, `git_error` and `git_timeout` as stop conditions (`skills/ai-kit-spec-review/references/cross-ai.mjs:128–147`); a dirty review suppresses the answer entirely (`:2900–2913`). Such a failure invalidates the attempt—it is not evidence that the judge provider was unavailable.

- **MEDIUM · PARTIALLY-RESOLVED — The pre-move home-path check scans a directory non-recursively.**  
  The prescribed command passes `tmp/judge/out` directly to `grep` ([19-08-PLAN.md:193–197](.planning/phases/19-evaluation-on-claude/19-08-PLAN.md#L193)). I verified the equivalent operation returns exit 2, “Is a directory,” and no filenames. The secret scanner detects credential shapes, not arbitrary home paths ([19-03-PLAN.md:305–311](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L305)). Therefore “prints nothing” does not establish a clean pre-commit path scan; the later wildcard verification detects it only after the move/commit.

**Suggestions**
- Invalidate and investigate contract/tree-verification failures; reserve unavailable rows for defined provider/environment failures.
- Scan actual report files before moving them, distinguishing clean no-match from operational errors.

**Risk Assessment: HIGH.** An invalid review attempt can currently be excluded from the aggregate as ordinary unavailability.

## 19-09

**Summary:** Score-only failures, rejected findings and ordinary GREEN regressions now have defined paths. The newly added owner packet exceeds the advisory tool’s input contract, and the GREEN guard still accepts unproven harness outcomes.

**Strengths**
- Fixes remain committed before pressure and judge reruns, with the existing command-document tests retained. See [19-09-PLAN.md:164–175,199–211](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L164) and `tests/test_curated_config_apply.py:2320–2339`.
- Source-backed rejection no longer changes a judge’s score; the row remains blocked until rerun or owner disposition ([19-09-PLAN.md:193–215](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L193)).

**Concerns**
- **HIGH · NEW — The full owner packet is invalid input to `decide.py`.**  
  [19-09-PLAN.md:223–238](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L223) requires complete historical/current sections and sends the packet’s full text as context. `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:45,224–258` limits a field to 1,500 characters and rejects code fences. The current v2-flow section alone is over 7,100 characters and contains fences. A pure local validation returned `too_long_context`; a short fenced example returned `code_fence_context`. Rejected items contain no `choice` or `top` (`decide.py:371–383`).

- **HIGH · PARTIALLY-RESOLVED — Harness-failed GREEN cells can pass the stop guard.**  
  The inherited procedure permits terminal `harness-failed` cells ([19-06-PLAN.md:157–160](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L157)). The zero-round shortcut and automated guards reject bare `fail`/`pending`, not `harness-failed` ([19-09-PLAN.md:264–266,306](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L264)). Thus passing judges plus an ungraded E cell can carry PASS forward. The reader contract supplies only section, row and cell—not gating/provenance metadata ([19-03-PLAN.md:300–303](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L300)).

**Suggestions**
- Keep the complete packet locally for the owner; send the ladder a fence-free summary within its limit, and handle invalid/unavailable advisory outcomes explicitly.
- Require every expected gating row to be `pass` or a specifically permitted, provenance-checked carried `fail/unresolved`. Treat harness failure as missing behavioral evidence, not success.
- Apply the non-gating correction from 19-07 here as well.

**Risk Assessment: HIGH.** The loop can accept unproven behavior, while its post-cap route cannot reliably produce the answer shape it requires.

## 19-10

**Summary:** Final gate recording and separate product provenance are improved. Close-out still mandates a false source claim, omits RED from the concrete late-fix rerun procedure, and overstates what its ignored-file comparison detects.

**Strengths**
- The aggregate gates and absent-container-engine error match actual repository targets. See [19-10-PLAN.md:222–225](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L222) and `Makefile:74,128,133–138`.
- Product provenance is correctly separate from the skill digest: executable apply behavior changes independently of documentation (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:784–818`). The revised check recognizes this ([19-10-PLAN.md:188–204](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L188)).

**Concerns**
- **HIGH · NEW — The required v1 isolation finding is false against current source.**  
  [19-10-PLAN.md:233–244](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L233) mandates evidence and a backlog goal asserting real-environment `ensure-project` tests at two ranges. The first contains mocked imports, fake subprocesses and temporary paths (`tests/test_ai_kit_gsd_curated_config.py:180–217`); the second contains candidate/instruction/frontend unit tests (`:1179–1274`). Actual real integration calls use temporary HOME and explicit child environments in `tests/test_curated_config_e2e.py:51–78,117–140`. Executing the task literally would commit an unsupported defect statement.

- **HIGH · PARTIALLY-RESOLVED — The concrete late-fix procedure refreshes the product header without refreshing RED.**  
  Run rule 6 requires all previous RED/GREEN/opus cells, but [19-10-PLAN.md:193–204](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L193) reruns only matrix, smoke, GREEN and opus before updating the shared pressure-file header. RED-b uses shared product helpers too: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:85–108` and `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:262–286`. A late shared-wrapper fix can change the baseline while its old result is presented under the new product revision.

- **MEDIUM · PARTIALLY-RESOLVED — Directory-level ignored status hides new files within existing ignored directories.**  
  [19-10-PLAN.md:206–213,308–315](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L206) fixes the original false positives, but default ignored status reports `.claude/`, `.codegraph/` and `.venv/` as directory entries, matching `.gitignore:4,8–9`. I confirmed this read-only. Adding `.claude/leaked-run.json` need not change either baseline entry, so `comm` detects nothing.

**Suggestions**
- Formally reconcile the stale isolation claim before copying it into evidence or backlog.
- Include previous RED cells in late-fix reruns, or record per-cell product revisions and withhold final-revision comparison claims.
- Compare individual ignored-file names, at least within writable ignored directories.

**Risk Assessment: HIGH.** Final evidence can otherwise misstate both an existing defect and which revision the baseline comparison describes.

## Disposition audit and overall assessment

**Coverage: 10/10 plans reviewed against revision `b10ff51`. Document type: GSD implementation plans.**

| Plan | Cycle-1 disposition verification |
|---|---|
| 19-01 | HOME merging and runtime diagnostic seeding are resolved. Full-plan delivery has an explicit read requirement. Digest schema is coordinated, but completeness remains partial through 19-03. |
| 19-02 | E’s terminal state and command/result pairing are resolved. B/D cache preservation and descendant cleanup remain partial. |
| 19-03 | Zero-approval and post-write cases are addressed. Baseline fairness, successful approval, evidence completeness and preserved verdict inputs remain partial as detailed above. |
| 19-04 | Serialized skill readback and absent-config validation are resolved. |
| 19-05 | Snapshot lifetime and failure triage are resolved. Product provenance/rerun obligations are present. |
| 19-06 | Workflow-versus-outcome separation is incorporated. End-state preservation remains partial. |
| 19-07 | Ordered-step testing and stable rule pins are resolved. Product provenance and rerun obligations are incorporated. |
| 19-08 | Conflicting-judge aggregation is resolved. Pre-move secret scanning is incorporated; the path-scan command remains partial. |
| 19-09 | Score-only repair, local v1 comparison packet and unchanged rejected scores are incorporated. GREEN-result acceptance remains partial. |
| 19-10 | Original ignored-directory false positives and premature snapshot deletion are resolved. Late-fix invalidation remains partial because the concrete procedure omits RED. |

The explicit full-plan-read requirements and orchestrator-only guards are accepted mitigations; I am **not re-raising** the stock dispatcher findings. The session-owned dispatcher implementation itself was not available for independent inspection.

**Status: Changes requested. Overall risk: HIGH.**

The highest-priority corrections are:
1. Make fixture construction reproducible and pin RED-b’s actual entrypoint.
2. Make grading establish effective configuration, completed approvals and complete evidence.
3. Prevent live enumeration from writing real tool configuration.
4. Make rollback evidence non-vacuous and review-contract failures invalidate attempts.
5. Correct close-out provenance and the stale isolation statement.

**Not checked:** live AI runs, real user configuration/credentials, full project gates, or execution of the not-yet-created helper. No repository files were changed.  
**Residual risk:** unrestricted headless Bash remains detective-controlled, not a filesystem sandbox.

---

## Consensus Summary

Only one reviewer lane ran (`opencode-plan-review`), so the consensus gate does not engage and
every HIGH below counts. Each finding was checked against the plan text and repo source; the
orchestrator's verification notes follow.

### Agreed Strengths
Single reviewer, no cross-reviewer agreement. The reviewer confirmed the cycle-1 fixes for HOME
merging (19-01), the informational runtime row (19-01), E's terminal state and command/result
pairing (19-02), skill-reference readback and absent-config validation (19-04), snapshot lifetime
(19-05), outcome-versus-workflow baselines (19-06), ordered-step pins (19-07), all-live-rows judge
aggregation (19-08) and separate product provenance (19-10).

### Agreed Concerns (single reviewer; all verified against source)
HIGH, still unresolved after verification (14):
- 19-02 B/D: the seeded cache has no `model-catalog.json.fetch-meta.json`, so `inventory`'s
  `fetch-model-catalog --if-stale` (`catalog_adapter.py` `_fetch_argv`; `cli.py` `_fetch_catalog_external_sources`;
  `cache.py` `cache_is_stale` returns True for a missing file) always fetches and rewrites the catalog,
  so the byte-identity self-check cannot hold.
- 19-02 RED-b: the 7009d22^ SKILL.md entrypoint loop checks `CLAUDE_PLUGIN_ROOT` and `$HOME/.claude/skills`
  before its own directory, so an installed copy can shadow the worktree script; nothing pins the entrypoint.
- 19-03 `first_write` counts `ensure-project`, a no-op when a config exists (`config.cjs` `cmdConfigNewProject`
  returns `already_exists`), so B/D/E disclosure and `apply_after_scripted_answer` can fail a correct run.
- 19-03 B: a bare Cursor model's vendor is taken as the lane name, so `claude-*` passes
  `lane_vendors_differ_from_planner` (`vendor.py` infers `anthropic`); the router check accepts the string in
  `.new` or anywhere in the runner without proving the active hook uses it.
- 19-03 `grouped_followup_approval` accepts any non-error approval command without matching targets, ids,
  fingerprint or per-follow-up return codes.
- 19-03 D: the checks cover removal rows only, not the full diff (SPEC D: "the full diff is shown").
- 19-03/19-09 evidence gates: `check_digests` needs one live row per section and `cells` silently omits
  missing rows or columns, so incomplete evidence passes.
- 19-04: the forced `smoke-placeholder` goes into the empty-candidate `workflow.cross_ai_command` entry and
  later artifact resolution does not restore a derived command.
- 19-04: the rollback experiment changes only an entry that gsd-core rejects before any write, so a broken
  restore routine still passes.
- 19-05: real-cache `inventory` can run `cursor-agent models`, which rewrites the real Cursor config
  (`detection.py` `detect_cursor_agent_models` docstring); the plan claims no other writes and the snapshot
  does not cover it.
- 19-08: any non-retryable runner status (including `contract_violation`, `git_error`, `git_timeout`) becomes
  a waiver-compatible `judge unavailable` row.
- 19-09: the post-cap jev item embeds the full owner packet, which `decide.py` rejects (1500-character cap,
  no code fences).
- 19-10: the mandated v1 isolation finding is false against current source: the cited ranges are fake-run
  and unit tests; real-integration tests already use scratch HOME and explicit env.
- 19-10: the late-product-fix procedure refreshes `product_commit` in the pressure file without re-running
  RED cells that use the shared helpers.

Actionable MEDIUM/LOW (11): 19-01 host-parameterized oracle (tier versus model); 19-02 failed model turns
not gated on return code and terminal result; 19-02 detached `start_new_session` descendants outlive group
cleanup; 19-02 LOW `plan_io.needs_choice_keys` is defined in `apply.py`; 19-04 smoke drops `--host`; 19-06
C has no config to copy; 19-06 committed record omits recompute inputs; 19-07 a non-gating `fail` blocks
completion; 19-08 `grep -l` on a directory without `-r` prints nothing and does not scan; 19-09
`harness-failed` GREEN cells pass the stop guard (downgraded from HIGH: 19-10 lines 229 and 319 already index
every `harness-failed` cell as `human_needed`, so the gap is gating, not silent); 19-10 ignored-directory
entries hide new files in `.claude/`, `.codegraph/`, `.venv/`.

### Divergent Views
None (single reviewer). Orchestrator adjustment: the reviewer's 19-09 `harness-failed` HIGH is counted as
MEDIUM per the evidence above.

**Status: Changes requested.**
