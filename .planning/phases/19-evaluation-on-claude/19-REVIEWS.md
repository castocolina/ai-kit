---
phase: 19
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-17T09:14:29Z
plans_reviewed: [19-01-PLAN.md, 19-02-PLAN.md, 19-03-PLAN.md, 19-04-PLAN.md, 19-05-PLAN.md, 19-06-PLAN.md, 19-07-PLAN.md, 19-08-PLAN.md, 19-09-PLAN.md, 19-10-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 19

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review (opencode-plan-review)

## 19-01

**Summary:** The matrix design is sound: it compares the plan’s promise with the real resolver rather than reading expectations back from the applied config. Two environment/evidence details need correction.

**Strengths**
- The proposed oracle follows the resolver’s actual tier precedence: phase-specific `models` overrides the selected profile. The live exports needed for this comparison exist. See `.claude/gsd-core/bin/lib/model-resolver.cjs:376–403` and `.claude/gsd-core/bin/lib/model-profiles.cjs:10–16`.
- Reusing the existing bundle and registering the matrix in the e2e group matches the repository’s test organization. See `tests/test_curated_config_apply_e2e.py:152–197` and `tools/run_unittest_parallel.py:51–66`.

**Concerns**
- **MEDIUM — The real `HOME` override is overwritten during apply.** The plan changes `child_env`, but retains the bundle’s scratch `resolve_env` ([plan:266–277](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L266)). `_real_apply` supplies that scratch environment through `env_fn`; apply passes it to subprocesses, and `_real_run` merges the per-call environment **after** `child_env`. Thus those calls still receive scratch `HOME`, contrary to D-08. See `tests/test_curated_config_apply_e2e.py:88–91,200–215` and `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py:185–201`.
- **MEDIUM — The informational runtime case does not create the condition it claims to examine.** P2 only calls `config-new-project`; that command explicitly removes `runtime` from copied defaults. The proposed row therefore does not reproduce a retained project-level `runtime: codex`. See [plan:243–245,270–275](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L243) and `.claude/gsd-core/bin/lib/config.cjs:401–414`.

**Suggestions**
- Override `HOME` consistently in both environments and test the environment received by each subprocess.
- Seed `runtime: codex` explicitly in a separate diagnostic case; keep it outside the APP-05 gate.

**Risk Assessment: MEDIUM.** The core comparison is credible, but the isolation claim and runtime-gap evidence would be inaccurate.

## 19-02

**Summary:** Centralizing fixtures and the headless runner is appropriate. However, scenario E cannot reach its required successful apply with the supplied answers, and B/D’s self-checks do not exercise the inventory path used by the live sessions.

**Strengths**
- The existing `child_env` helper genuinely removes host signals before applying explicit additions. Reusing it avoids another scrub list. See `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:130–140`.
- Fixture self-checks before paid model calls are a useful safeguard ([plan:240–262](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L240)).

**Concerns**
- **HIGH — E has no first candidate to select.** Its inventory has no non-host runtime, but its answers request cross-AI execution. The product consequently emits `workflow.cross_ai_command` with `needs_choice` and `candidates: []`, and creates no runner artifact. “Take the first candidate” cannot resolve this. See [plan:208–209,260–264](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L208), `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py:843–872,1220–1226`, and `apply.py:896–905`.
- **HIGH — B/D’s seeded inventory is not the inventory the model uses.** Their self-check uses scratch `HOME` and `FakeRun`, while their live prompt causes a real inventory under real `HOME` ([plan:240–259,279–280](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L240)). Moreover, the seeded Claude runtime lists six model IDs while catalog metadata lists seventeen. This fails `claude_runtime_is_current`, triggering live re-detection and replacing the seeded runtime snapshot. See `tests/fixtures/curated_config_v2/runtimes.json:3–20`, `model-catalog.json:3–22`, and `skills/ai-kit-spec-review/ai_kit_spec/detection.py:1030–1051`.
- **MEDIUM — Timeout cleanup covers the CLI, not its descendants.** The proposed runner defaults to `subprocess.run(timeout=...)` without process-group ownership ([plan:279–282](.planning/phases/19-evaluation-on-claude/19-02-PLAN.md#L279)). Existing supervision explicitly creates a session and kills its group, including descendants after normal exit. See `runner_dispatch.py:251–262,415–424`.

**Suggestions**
- Give E an explicit answer authorizing execution to be disabled when no target exists, or formally revise its expected terminal state.
- Make B/D consume the controlled inventory, or prove the real inventory preserves the fixture’s required facts.
- Use process-group cleanup with a small descendant-cleanup test.

**Risk Assessment: HIGH.** Otherwise valid skill behavior can fail for fixture reasons rather than instruction quality.

## 19-03

**Summary:** Per-expectation grading and negative tests are worthwhile. Several specified predicates are weaker than the behaviors they claim to prove.

**Strengths**
- Keeping check names synchronized with scenario files prevents silent coverage drift ([plan:292–295](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L292)).
- Approval has a real binding mechanism to test: the product fingerprints the exact follow-up IDs, argv and cwd. See `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/followups.py:332–357`.

**Concerns**
- **HIGH — `grouped_followup_approval` passes when approval never happens.** “Every matching command is later, and there are at most one” is true for zero commands. It also never checks that the assistant asked a grouped question or showed the required rows. See [plan:200–203](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L200). The actual instruction requires the question and exact approval command when required follow-ups exist: `skills/ai-kit-gsd-curated-config/SKILL.md:141–148`.
- **HIGH — Post-apply disclosure can pass the removal checks.** `remove_rows_shown` and `nothing_dropped_silently` search all assistant text, including text after the write ([plan:200–215](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L200)). An agent can silently remove keys, explain afterward, and pass.
- **HIGH — A failed or unrelated dry run can satisfy ordering.** The grader takes the first command containing `--dry-run`, without requiring success or matching the subsequently applied plan ([plan:183–199](.planning/phases/19-evaluation-on-claude/19-03-PLAN.md#L183)). For example, an apply refused because choices remain can count as the required preview.

**Suggestions**
- Require the grouped question and one successful approval when follow-ups are required; test the zero-command case.
- Require removal disclosure before the successful real apply.
- Correlate commands with their results and target/plan. Use a documented manual semantic check where shell-string matching cannot establish this reliably.

**Risk Assessment: HIGH.** The current predicates can produce false GREEN results on the phase’s central safety expectations.

## 19-04

**Summary:** The smoke procedure targets the right failure modes, but its readback validator would reject valid skill wiring. First-run validation also needs an explicit exception and assertion path.

**Strengths**
- The repository already provides genuine backup, no-op and pruning tests to reuse. See `tests/test_curated_config_apply_e2e.py:417–506`.
- Backup copying preserves bytes and mode through the atomic writer. See `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/config_backup.py:49–54`.

**Concerns**
- **HIGH — Comparing every applied value directly with the plan is wrong for `agent_skills`.** The plan requires raw equality for every `set` entry ([plan:213–215](.planning/phases/19-evaluation-on-claude/19-04-PLAN.md#L213)). Apply deliberately converts bare skill names into references such as `global:ponytail:ponytail`. See `apply.py:92–115` and `skills.py:156–167`. The existing real-node test explicitly expects the converted form: `tests/test_curated_config_apply_e2e.py:278–288`.
- **MEDIUM — Project (b) lacks the promised validity checks.** Its specified steps only apply and record reconciliation keys ([plan:226–228](.planning/phases/19-evaluation-on-claude/19-04-PLAN.md#L226)); they do not invoke `validate_applied`. Conversely, the blanket “one new backup after each real apply” assertion cannot hold for a previously absent config: `config_backup.py:110–115` intentionally returns no backup.

**Suggestions**
- Compare skill entries against their documented serialized representation, while leaving the model oracle independent.
- Validate both scratch configs explicitly.
- Distinguish “existing config backed up” from “new config created without a prior backup.”

**Risk Assessment: HIGH.** The proposed validator can misclassify correct product behavior as a defect and trigger unnecessary product edits.

## 19-05

**Summary:** Running the real smoke before pressure testing is a sensible ordering choice. The plan’s post-run verification currently depends on an artifact it deletes itself.

**Strengths**
- Native host detection distinguishes detected identity from an explicit override: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:48–58`. The plan appropriately asks for that provenance in the session evidence ([plan:144–152](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L144)).
- Recording the checkout-local version prevents a global installation from silently standing in for the tested core ([plan:27–28](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L27)).

**Concerns**
- **MEDIUM — The orchestrator verification references a deleted snapshot.** Frontmatter requires checking `tmp/smoke/plan05.before.json` after the plan, but Task 2 deletes `tmp/smoke/` before committing. See [plan:14,205–210](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L205). A correct execution cannot satisfy that post-plan check.
- **MEDIUM — Failures are attributed to product code too broadly.** The procedure classifies inability to build the helper’s plan, as well as validation failures, as product defects ([plan:151–158](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L151)). The raw-plan-versus-serialized-value distinction in `apply.py:104–115` demonstrates why helper failures need separate triage.

**Suggestions**
- Retain verification inputs until the orchestrator has checked them.
- Separate harness failure, unavailable environment and demonstrated product failure before changing shared product code.

**Risk Assessment: MEDIUM.** The ordering is good, but false defect attribution and contradictory cleanup instructions can derail the smoke.

## 19-06

**Summary:** The six fresh-context baselines provide useful coverage. Their grading must distinguish functional failures from simply not using the v2 plan-file workflow.

**Strengths**
- The baseline allocation matches the intended comparison: no-skill B–E, plus historical v1 on B/D ([plan:34–38](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L34)).
- The historical workflow genuinely uses direct subcommands rather than v2 plan files. See `skills/ai-kit-gsd-curated-config/references/v1-path.md:10–18,27–38`.

**Concerns**
- **HIGH — The baselines are structurally biased toward failure.** The plan treats every grade row as a behavioral verdict ([plan:176–178,195–204](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L176)), but v1 legitimately configures GSD without producing `plan.json`; the direct write path exists in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py:85–115`. A correct outcome or disclosure must not be scored wrong solely because it lacks a v2 intermediate artifact.
- **MEDIUM — End-state evidence is discarded before later review.** The cell procedure retains transcripts and `run.json`, then deletes the entire run directory, including config, inventory and plan ([plan:179–182](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L179)). Those files determine many verdicts. The committed trimmed transcript is not enough to reproduce those checks.

**Suggestions**
- Grade outcome expectations from observable configuration and conversation; keep workflow-specific expectations separate.
- Preserve a compact, redacted grading record containing the relevant state facts, check results and command-result references.

**Risk Assessment: HIGH.** Otherwise the “what v1 got right or wrong” section can describe limitations of the grader rather than v1.

## 19-07

**Summary:** The evidence-gated editing policy is disciplined and limits scope creep. Its document tests should cover the promised ordering, not just phrase presence.

**Strengths**
- The edit table prevents no-skill failures from automatically licensing redundant v2 prose ([plan:148–160](.planning/phases/19-evaluation-on-claude/19-07-PLAN.md#L148)).
- Existing tests genuinely parse documented commands and reject habitual `--force` examples. See `tests/test_curated_config_apply.py:2320–2339`.

**Concerns**
- **MEDIUM — Phrase pins do not protect step order.** The plan promises an exact flow and treats re-reading it as a backstop ([plan:38–45](.planning/phases/19-evaluation-on-claude/19-07-PLAN.md#L38)). Existing tests check command validity, headings and substring presence—not relative ordering. See `tests/test_curated_config_apply.py:2320–2397`. Moving apply ahead of review could leave those tests green.
- **LOW — The editing scope is tightly coupled to particular prose.** Requiring one pin per added sentence encourages testing wording rather than the required contract ([plan:194–195](.planning/phases/19-evaluation-on-claude/19-07-PLAN.md#L194)).

**Suggestions**
- Add one ordered-step assertion to `TestSkillDocCommands`.
- Pin stable behavioral requirements rather than every sentence; retain the live pressure test as the actual behavior check.

**Risk Assessment: MEDIUM.** The editing discipline is strong, but reliable acceptance still depends on correcting the harness and grader.

## 19-08

**Summary:** The judge procedure has useful independence and byte-identity controls. Its pass aggregation can nevertheless ignore an available judge’s unresolved serious finding.

**Strengths**
- Pi review mode restricts tools to reading/searching: `skills/ai-kit-spec-review/references/cross-ai.mjs:284–289`.
- The runner’s tree signature includes HEAD and working-tree content, explaining why batching tracked writes after review is necessary. See `cross-ai.mjs:486–493,716–769`.

**Concerns**
- **HIGH — One passing pi judge can conceal another judge’s Critical/Important finding.** The phase rule only requires the in-session judge and one pi judge to pass ([plan:31,179–181](.planning/phases/19-evaluation-on-claude/19-08-PLAN.md#L179)). For example, GPT passes while GLM reports a valid Critical finding: the aggregate still becomes PASS. That does not establish the locked zero-findings bar.
- **MEDIUM — These reports are committed before the secret/path checks.** Task 2 moves and commits all reports without running the scanner or placeholder check ([plan:223–233](.planning/phases/19-evaluation-on-claude/19-08-PLAN.md#L223)). Restricting judge tools to reads does not sanitize their output.

**Suggestions**
- Adjudicate every available judge’s serious finding. A finding must be fixed or rejected with source-backed reasoning before PASS.
- Scan and sanitize all reports after the judges exit and before the first commit.

**Risk Assessment: HIGH.** Judge independence is valuable only if contradictory findings are not discarded by aggregation.

## 19-09

**Summary:** Re-running judges and pressure tests after edits is correct. The loop needs to act on pressure regressions and cover all ways the score gate can fail.

**Strengths**
- Each fix is committed before evaluation, and both judge and GREEN rows are superseded on a new digest ([plan:160–169](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L160)).
- The three-round cap bounds repeated model calls ([plan:170–175](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L170)).

**Concerns**
- **HIGH — A judge fix can introduce a GREEN failure without blocking PASS.** The loop re-grades B–E, but its stop decision checks only the judge phase rule; task verification checks document tests and digest equality, not passing GREEN results. See [plan:164–171,216–218](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L164). Matching bytes does not mean passing behavior.
- **MEDIUM — A score-only failure has no permitted repair path.** A judge may score 95 with no Critical/Important findings, but fixes are restricted to those finding classes ([plan:139–142](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L139)).
- **MEDIUM — The owner-decision packet is incomplete.** Post-cap routing records scores, findings and changed headings, but not the required diff against v1’s judged areas. Compare [plan:177–185](.planning/phases/19-evaluation-on-claude/19-09-PLAN.md#L177) with `.planning/phases/19-evaluation-on-claude/19-CONTEXT.md:100–103`.

**Suggestions**
- Require final gating GREEN checks independently of judge success.
- Define score-only failure handling.
- Continue independent evidence collection if desired, but keep unmet requirements blocked pending the actual owner decision, with the complete comparison packet.

**Risk Assessment: HIGH.** The loop can otherwise finish with a passing judge verdict and regressed skill behavior.

## 19-10

**Summary:** The final gate coverage is appropriate. Close-out must invalidate evidence affected by late product fixes and must not mistake expected ignored directories for task debris.

**Strengths**
- The chosen commands use the repository’s real aggregate gates: `Makefile:74,128,133–138`.
- Filling `JUDGED_COMMIT` only after checking judged paths are clean correctly ties documentation evidence to committed bytes ([plan:146–152](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L146)).

**Concerns**
- **HIGH — Late product fixes leave earlier behavioral evidence stale.** Task 1 permits a product fix followed only by rerunning the failed gate ([plan:198–200](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L198)). A change to apply, recommendation or follow-ups can invalidate smoke/pressure results without changing the skill digest. Those are distinct behaviors in `apply.py:784–818,850–893`; a skill-only digest cannot bind them.
- **MEDIUM — The stray-file assertion fails on required local state.** It asks `git status --porcelain --ignored` to show nothing outside this plan’s modified files ([plan:232–235](.planning/phases/19-evaluation-on-claude/19-10-PLAN.md#L232)). `.claude/`, `.codegraph/` and `.venv/` are intentionally ignored by `.gitignore:3–9`. Running that read-only status command already lists them.

**Suggestions**
- After a late product fix, rerun affected smoke and pressure cases, recording the product revision alongside the skill digest.
- Compare ignored/untracked state with a start-of-plan baseline instead of requiring it to be empty.

**Risk Assessment: HIGH.** Final gate success alone cannot establish that earlier evidence still describes the final product.

## Cross-plan compatibility

These are additional execution blockers spanning the plan set:

1. **HIGH — `executor: orchestrator` is not a supported dispatch filter.**  
   Every plan has `cross_ai: true`, but the installed GSD workflow selects cross-AI plans using that flag and configuration—not `executor`. See `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:63–68`. Consequently, the declared rule in [19-05:66–69](.planning/phases/19-evaluation-on-claude/19-05-PLAN.md#L66) does not prevent Claude-only plans from being sent to pi. Define an explicit supported invocation/dispatch sequence for plans 05–10; do not rely on this metadata alone.

2. **HIGH — Delegated prompts omit the contracts the tasks require.**  
   The installed workflow extracts only `<objective>` and `<tasks>`, then adds project context: `.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:84–87`. Plans 01–04 put critical contracts in separate `<interfaces>` sections while tasks say “per `<interfaces>`”; for example [19-01:207–285,302–309](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L207). Require the executor to read the full named plan, or include those sections in the dispatched prompt.

3. **HIGH — The digest checker and pressure-evidence layout disagree.**  
   The checker only recognizes pipe-prefixed table rows containing a digest ([19-01:232–239](.planning/phases/19-evaluation-on-claude/19-01-PLAN.md#L232)). Pressure evidence specifies pass/fail tables with separate `Digest` lines ([19-06:195–198](.planning/phases/19-evaluation-on-claude/19-06-PLAN.md#L195)). That layout produces `no live row`; alternatively, an incidental digest-bearing row could pass without proving all four required cells exist. Define one schema and test the parser against complete, missing-cell, stale-cell and superseded-round examples.

## Overall assessment

**Status: Changes requested. Overall risk: HIGH. Coverage: 10/10 plans reviewed.**

The phase has strong foundations: a plan-derived oracle, scratch-only application, real rollback tests, bounded evaluation loops and explicit evidence provenance. The main risk is **trusting the evaluation machinery**: impossible fixture choices, weak grading predicates, dispatch assumptions and incompatible evidence formats can manufacture failures or false passes.

Fix the dispatch/input contracts, E’s terminal state, smoke readback semantics, grader predicates and digest schema before execution. No new framework or dependency is needed.

**Not checked:** live AI runs, real user configuration or credentials, or execution of the proposed helper, which does not yet exist. No repository files were changed.  
**Residual risk:** unrestricted headless Bash remains a detective-control setup, not a filesystem sandbox.

---

## Orchestrator Verification

Every finding was checked against the plan text and the repo source before counting. None was
rejected. Evidence per finding:

HIGH (13, all confirmed):
- 19-02 E: `cross_ai._cross_ai_exec_entries` emits `workflow.cross_ai_command` with
  `status="needs_choice", candidates=[]` when `exec_targets` is empty (`recommend.py:858-868`);
  E's fixture marks every CLI except claude `installed: false`, so the scripted "take the first
  candidate" has nothing to take, `prepare` refuses apply while `needs_choice` remains
  (`apply.py:899-903`), and any `plan-set` of that key fails E's `no_invented_values`.
- 19-02 B/D: running `detection.claude_runtime_is_current` on the shipped fixtures
  (`tests/fixtures/curated_config_v2/runtimes.json`, `model-catalog.json`) returns `False`, so
  `routing.runtimes_cache_is_fresh` rejects the seeded cache and a live `inventory` rebuilds the
  runtimes snapshot from the real machine (`routing.py:240-262`); B/D self-checks use a hermetic
  inventory the live session never sees.
- 19-03 `grouped_followup_approval`: the rule ("every such command later, at most one") holds
  vacuously with zero approvals; the negative tests cover only "two `--approve`" and "in the apply
  turn", not zero approvals when follow-ups are required (SKILL.md step 6).
- 19-03 `remove_rows_shown` / `nothing_dropped_silently`: both read `text_all`, not
  `text_before(real_apply)`.
- 19-03 `dry_run_before_apply`: `first_bash(events, "--dry-run")` matches the command string only;
  a refused dry run (`apply refused while needs_choice remains`) still satisfies the ordering.
- 19-04 `validate_applied`: compares each `set` value with `plan_io.same_value` on the raw plan
  value, but apply serializes `agent_skills.*` names to references (`apply.py:_planned_to`,
  `skill_value`), so correct output reads as a product defect and routes to Run rule 6.
- 19-06: plan-based checks fail with `no plan.json` for red-a/red-b by construction (v1 has no
  plan file), so "What v1 got right or wrong" mixes grader structure with behavior; the
  `### Discrimination` section fires only when a baseline column has no `fail`.
- 19-08: the phase rule "in-session passes and at least one pi judge passes" lets a failing
  second pi judge's Critical/Important stand. It is also weaker than the 18.1-22 rule it cites,
  which additionally requires "every non-superseded row for that digest passes or is judge
  unavailable" (18.1-22-PLAN.md line 39).
- 19-09: fix-round step 4 stops on the judge phase rule only; Task 2 verify checks doc tests and
  digests, never that the re-run GREEN rows pass.
- 19-10: Task 1 step 2 routes a product defect through Run rule 6 and re-runs only the failed
  gate; the skill digest covers only SKILL.md and `references/`, so a Python fix leaves smoke and
  pressure evidence unbound to the final product.
- Cross-plan dispatch: `execute-phase/detail/elaboration.md` step 2.5 selects plans by
  `cross_ai: true` plus `workflow.cross_ai_execution` (live value `true` in this repo); the
  `executor:` key is never read. All ten plans carry `cross_ai: true`, so the stock workflow would
  send orchestrator plans 05-10 to pi.
- Cross-plan prompt: the same step builds the delegated prompt from `<objective>` and `<tasks>`
  only; plans 01-04 put their contracts in `<interfaces>` and no task or objective tells the
  executor to read the full plan file.
- Cross-plan digest schema: 19-01's `check_digests` takes `|`-prefixed rows carrying a 16-hex
  token; 19-06 specifies "a `Digest` line per column" without fixing it as a table row, and no
  test pins the 19-PRESSURE-TESTS.md layout against the parser.

MEDIUM/LOW (13, all confirmed): 19-01 HOME override (`_real_run` merges the per-call env, which
apply builds from `env_fn` = scratch `resolve_env`, over `child_env`); 19-01 informational row
(`config.cjs:409-410` deletes `runtime` from copied defaults, so the row never contains the
D-30 `runtime: codex` it is meant to record); 19-02 timeout kills only the direct child; 19-04
project (b) has no validation although SPEC line 116 requires "both scratch applies leave valid
configs" (and `create_backup` returns no backup for an absent config); 19-05 `orchestrator_verify`
reads `tmp/smoke/plan05.before.json`, which Task 2 deletes; 19-05 treats every step 2-5 failure as a
product defect; 19-06 `rm -rf "$RUN"` discards the config/plan/inventory the verdicts came from;
19-07 no ordered-step test; 19-07 (LOW) one phrase pin per sentence; 19-08 no `secret-scan`
before its commit (0 occurrences in the plan); 19-09 no repair path for a score-only failure;
19-09 the jev context omits D-07's "diff against v1's judged areas"; 19-10 `git status
--porcelain --ignored -- . ':!tmp'` lists the intentionally ignored `.claude/`, `.codegraph/`,
`.venv/` and `.review-diagnostics/` entries today.

---

## Consensus Summary

One reviewer ran (opencode-plan-review, router-env/my-plan-review), with source citations
and full 10/10 plan coverage. With a single reviewer the consensus gate does not apply, so its
HIGHs count as raised. The orchestrator confirmed each finding against source (above).

### Agreed Strengths
- (single reviewer) The plan-derived APP-05 oracle is independent of the applied config and
  follows the resolver's real precedence (`model-resolver.cjs`, `model-profiles.cjs`).
- Scratch-only applies, real rollback tests, bounded fix/REFACTOR loops and digest-bound
  evidence rows.

### Agreed Concerns
Highest priority, in this order: the evaluation machinery can make up failures or report
passes that did not happen.
1. Dispatch and prompt contracts: `executor:` is not honored, and `<interfaces>` is not delivered
   to delegated executors.
2. Fixtures: E cannot reach a real apply, and B/D live inventory is not the seeded inventory.
3. Grader predicates can pass vacuously (zero approvals, disclosure after apply, failed dry run).
4. Smoke readback misreads `agent_skills` serialization as a product defect.
5. Gate aggregation: one pi judge's PASS can override the other judge's findings, GREEN
   regressions do not block, and late product fixes leave the evidence stale.
6. The digest-check parser and the pressure-evidence layout are not pinned to each other.

### Divergent Views
None (single reviewer).
