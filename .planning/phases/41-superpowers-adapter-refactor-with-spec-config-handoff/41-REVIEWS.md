---
phase: 41
cycle: 1
reviewers: [referee-one]
reviewed_at: 2026-11-25T22:55:48-03:00
plans_reviewed: [41-01-PLAN.md, 41-02-PLAN.md, 41-03-PLAN.md, 41-04-PLAN.md, 41-05-PLAN.md, 41-06-PLAN.md, 41-07-PLAN.md, 41-08-PLAN.md, 41-09-PLAN.md, 41-10-PLAN.md, 41-11-PLAN.md, 41-12-PLAN.md, 41-13-PLAN.md, 41-14-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
model_sources:
  referee-one: "pinned"
---

# Cross-AI Plan Review — Phase 41

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Note: one reviewer lane only (referee-one, `.planning/config.json` `review.default_reviewers`); its findings are single-reviewer.

## Cycle 1 (referee-one)

### Review conditions (cycle 1)

Reviewer referee-one (`router-env/my-referee-one`, opencode lane via `gsd-tools query review-lane invoke`), four batches:
A (41-01..03) 521 s, B (41-04..06) 608 s, C (41-07..10) 529 s, D (41-11..14) 601 s; every lane exit 0, every review read
and grounded in `path:line`. Prompts 206-231 KB (PROJECT, ROADMAP section, requirement rows, SPEC, CONTEXT, locked
decisions, planner rules, wave map, the batch's plans, instructions with verify-against-source, ponytail lens, executor
reality and same-wave overlap checks). Plan checker (sonnet) ran beside it: 1 blocker (fallback on a narrowed re-resolve),
2 warnings (ROADMAP criterion 3 / EXE-05 wording, amended by the orchestrator; 41-12 eval files lists), 4 info.
Orchestrator decisions: `tmp/p41-review/c1/fix-brief.md`, `fix-brief-B.md`, `fix-brief-CD.md` (F1-F3, A1-A13, B1-B17,
C1-C12, D1-D21, K1-K4). Rejected with reason and kept for the owner (MEDIUM): a checkout-supplied `.aikit/config.toml` can
turn the session fallback on (A10/B2: it keeps execution in the owner's own session; the trust gate covers executable
commands; spec-config's default target is the project file). Four opus fix planners applied the decisions; the
dispositions per batch follow.

### referee-one

#### Batch A (41-01, 41-02, 41-03)

#### 41-01

**Summary.** The plan puts the two definitions in the right files and preserves the no-config entry step and the quota-wake prompt. As written, though, it moves exact sentences rather than consolidating all the decisions those sentences express. It would leave broken links and competing stop instructions while its new tests still passed.

**Strengths**

- **Good choice of canonical homes.** `state-management.md` already owns Seed, Restore, and the saved injection; `resolution-stops.md` already owns selection-time stops and the state-write handoff. No runtime or schema change is needed (`skills/ai-kit-spec-execute-superpowers/references/state-management.md:53–125`, `skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md:8–55`).
- **Preserves a genuine exception to deduplication.** Task 1 keeps the literal wake prompt intact. That prompt is pasted into a fresh session and must bind paths before Restore; an existing test checks that order (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:119`, `skills/ai-kit-spec-execute-superpowers/references/quota-wake.md:8–36`, `tests/test_ai_kit_spec_superpowers.py:3363–3375`).

**Concerns**

- **HIGH — The owner-stop path still has multiple authorities.** Task 2 copies the dispatch outcome bullets into `## Owner stop`, then states the 69/one-shot decision again in SKILL.md and leaves the full decision in **Schedule-or-stop**. It also leaves the nonrecoverable escalation stop defined separately. The moved `ok` bullet refers to a “block above” that lives in SKILL.md, not in the destination reference. This is not just duplication: 41-11 inserts the flagged-quota exception in Classify, while the earlier text still says every 69 is an owner stop. A controller can stop before applying the authorized switch (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:156–162`, `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:175–205`, `skills/ai-kit-spec-execute-superpowers/references/escalation.md:115–134`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:133–139`).
- **MEDIUM — Links from inside `references/` point one directory too deep.** `references/state-management.md#pinned-resume` is a valid Markdown target from SKILL.md, but from a sibling reference it resolves to `references/references/state-management.md`. The same problem affects owner-stop links. The proposed test checks link text only in SKILL.md. It also misses paraphrases, and `rule_files` returns one entry per *file*, so two copies in the canonical file pass (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:118–122,158–162`). The repo already has a relative-link resolution pattern in `tests/test_spec_config_flow_text.py:117–120`.
- **MEDIUM — Evidence does not support “14 evals pass.”** The listed eval command checks JSON shape, fixture paths, and trigger queries, not the behavioral assertions. The closeout explicitly labels the *new* evals transcript-assessed; it does not provide execution evidence for the original 14. The no-config chain already has a closer fake-CLI test for absent configuration, the sibling wizard, and resumed runs, but this plan does not name it (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:127,168,200–204`, `tests/test_skill_evals_shape.py:130–152`, `tests/test_spec_chain_text.py:222–240,319–342`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:130`). This leaves R1’s behavioral eval acceptance unproved, not unassigned.
- **MEDIUM — Both unattended tasks are wider than the sizing rule.** Task 1 stages nine paths, including the generated listings that trigger the full unit/arch hook. Task 2 stages eight and asks the lane to discover which pins broke and make further prose edits until the line count fits. Those are real risks to the 1,800-second budget; the plan supplies no timing evidence. Task 2 also tells the executor to put details in a SUMMARY that the orchestrator owns (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:105,121–123,144,161–164,207–209`).

**Suggestions**

- Specify exact replacements and the expected final line count. Keep the executable mechanics in their existing references, but put the stop-versus-continue decisions in one place. Make 41-11 update that same decision path.
- Use sibling-relative Markdown targets inside `references/`, and assert that each required pointer resolves to the canonical heading. Keep the planted-copy test, but check duplicates within a file as well as across files.
- Add `tests.test_spec_chain_text` to the wave gate. Record separate evidence for eval shape, preserved behavior, and any evals actually executed.

**Risk assessment: MEDIUM.** The edits are reversible, but they govern what an unattended controller does at a stop. A green phrase-count test would not establish that the controller follows one unambiguous path.

##### Ponytail findings

- **MEDIUM — Task 1:** Needed for D-01. Reuse the existing Restore and its scratch-file tests, plus `tools/gen_test_groups.py:1–7`; no new runtime helper. Put the remaining operational instructions in the canonical home instead of adding links to restatements (`tests/test_ai_kit_spec_superpowers.py:3434–3458`).
- **MEDIUM — Task 2:** Needed for D-01. Move the decision, not a second copy of the procedure. Preserve the existing state writer and wake-close block, and replace the open-ended shortening pass with exact edits (`skills/ai-kit-spec-execute-superpowers/references/state-management.md:147–186`, `skills/ai-kit-spec-execute-superpowers/references/session-wake.md:56–71`).

#### 41-02

**Summary.** The candidate helper follows the locked direction and flag rules in isolation. The plan is not ready to dispatch: Task 2 conflicts with an existing test, and the exclusion-list handoff does not guarantee that the fresh resolver selects a lane the gate allowed.

**Strengths**

- **Reuses the right rule and keeps the right order.** The existing `escalation_target` walks forward from its anchor. The plan supplies the anchor followed by the lanes above it, nearest first, then returns matches in the original ranked order. Both-on preserves the old floor. It also extends the AST reader guard in the same task as the new caller (`skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:110–113,170–184`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:120–123`, `tests/test_lane_settings.py:257–267,480–486`).

**Concerns**

- **HIGH — Task 2’s verification cannot pass as written.** The task adds the exact `--injection-json "$INJECTION_JSON"` text that `TestJsonFilesAndOwnerNamedPair.test_no_block_pastes_json_into_a_command` forbids in `escalation.md`. It updates two other tests, not this one. It also replaces an executable success/refusal test with a line-order assertion, losing evidence about whether the real block leaves the output unwritten on failure (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:152–160`, `tests/test_ai_kit_spec_superpowers.py:3425–3432,3740–3755`). Explicitly label the shell snippet as file content, not a command for the lane to run; it contains constructs the objective forbids the executor from using.
- **HIGH — Allowed lanes are not enforced at the final pick.** The gate calculates exclusions from saved `ladder_keys`, but `resolve-injection` reloads the roster and subtracts only those excluded keys. A lane added or newly eligible since the saved list was produced is not excluded. The rule can therefore select a different lane even with both flags off. Separately, 41-04 can emit an empty-key native fallback from the narrowed re-resolve, even when the only problem is that the permitted lane is unavailable and another configured lane remains available. The existing prose then labels any `native` or `external_cli` result a bump, despite the new “normal fix round” sentence (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:121–122,152`, `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:213–230`, `skills/ai-kit-spec-execute-superpowers/references/escalation.md:101–109`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:167,197–199`).
- **MEDIUM — The CLI error contract and R2 edge evidence are incomplete.** JSON decoding and `.get()` run before the handler’s `try`; malformed JSON or valid non-object JSON can traceback because `main` catches only `ConfigError`. The proposed fixture checks malformed flags and no-target at the helper level, not the named exit-2 diagnostic or no-target owner notice through the CLI. Nor does it feed the gate’s output into the real resolver with fake lanes. At closeout, the installed-layout recipe describes giving `--injection-json` a filename, although the parser consumes JSON text (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:122–124`, `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:498–505`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:93`).
- **MEDIUM — Spec-config would solicit consent for the wrong action.** Task 3 changes the explanatory sentence but expressly retains “when it fails” and “next lane” in the question. It also leaves both config-reference definitions pointing to the next lane in order. The locked behavior is a pre-dispatch fix-round decision, strictly *above* the anchor, not a response to an actual dispatch failure (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:182–185`, `skills/ai-kit-spec-config/references/wizard-flow.md:71–73`, `skills/ai-kit-spec-config/references/config-file.md:139,148`, `skills/ai-kit-spec-execute-superpowers/references/escalation.md:23–28,106–109`).
- **MEDIUM — Task 1 is oversized; Task 2 omits concrete test setup.** The first lane has seven paths, a new module, three runtime edits, and a full unit/arch hook. The second tells the lane to add a doc-test class without specifying its path binding or placement before `unittest.main()`. The plan names the prior task, so this is not a missing wave dependency; it is missing detail in the prompt the executor actually receives (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:108–125,149–156`).

**Suggestions**

- Preserve the JSON-file safety invariant and the runnable test. Specify the exact CLI/file contract, malformed-input outcome, and matching 41-14 invocation. Test success and no-write refusal through the documented block using a fake shim or scratch roster.
- Check the final selected key against the gate’s `allowed` set before dispatch. Cover a stale ladder with a newly eligible lane, a permitted anchor that becomes unavailable, and the 41-04 session-fallback result. Keep “configured executor unavailable” distinct from “no candidate permitted for this fix round.”
- Rewrite the question, both config-reference definitions, and the eval assertions together. Keep the locked selection order and the native Claude Code exception unchanged.

**Risk assessment: HIGH.** There is a deterministic test conflict and a path that can dispatch a lane the gate did not authorize.

##### Ponytail findings

- **MEDIUM — Task 1:** Needed for D-02. Keep `_keyed`, `lane_escalation`, and `escalation_target`; repeated scans are not a meaningful performance risk for a personal roster. Spend test effort on the real CLI error branches rather than additional helper-only assertions (`skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:96–113,129–139,170–184`).
- **HIGH — Task 2:** Needed; a standalone gate does not control dispatch. Reuse the existing exclusion channel and the fake-resolver pattern that proves an owner-named key is picked. Do not add a second resolver or discard the executable check (`skills/ai-kit-spec-execute-superpowers/references/escalation.md:71–99`, `tests/test_ai_kit_spec_superpowers.py:3493–3518,3740–3755`).
- **MEDIUM — Task 3:** Needed because the old “informational” claim becomes false. Use the existing wizard/config/eval surfaces and phrase tests, but update the consent wording itself. No new wizard step is needed (`tests/test_spec_config_flow_text.py:151–157`, `skills/ai-kit-spec-config/evals/evals.json:177–183`).

#### 41-03

**Summary.** The split is sound: this plan owns storage and the wizard question; 41-04 owns runtime consumption. The writer change is small and uses the existing atomic path. The main gap is that the plan equates “the wizard only writes on yes” with “the effective flag can only be enabled by the owner,” which the current config trust model does not establish.

**Strengths**

- **Keeps the role policy separate from lane-entry flags.** The proposed reader reuses `_bool_setting`; the writer filters one role-table extra without adding a writer, dependency, or lane-entry flag. The existing CLI folder lock and atomic publication remain on the write path (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:99–101`, `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:28–33,96–107`, `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1123–1151`).
- **The downstream handoff is explicit.** 41-04 imports the reader and extends its allowlist when it adds the caller. It owns the no-fallback-off and jev prohibitions; 41-03’s empty `prohibitions` list does not leave them unassigned (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:96–101`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:33–42,166–169`).

**Concerns**

- **HIGH — Owner consent is not enforced at the config-read boundary.** The plan’s threat mitigation is a wizard instruction, but the reader accepts the merged policy regardless of source. A checkout-supplied `.aikit/config.toml` with ordinary lane entries needs no trust, and project policy overrides user policy. If that file supplies `session_fallback = true`, 41-04 can run a session-native task without the wizard ever asking. This does not require changing the locked key or its placement, but the plan needs to say how the project value’s authority is established and test that boundary (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:99,154–165`, `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:595–602,694–706`, `skills/ai-kit-spec-review/ai_kit_spec/trust.py:88–113`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:166–167`).
- **MEDIUM — “Ask once” is underspecified on an order retry.** Task 2 attaches the question to step 9. Step 3 sends the controller back to step 9 if the owner changes the order, but the plan does not say to retain the fallback answer or what to do if the execute role disappears. It also shows `true` in the copyable JSON example; the tests only search for that literal and the question, so they cannot distinguish yes-only writing from an accidental unconditional write (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:129–132`, `skills/ai-kit-spec-config/SKILL.md:352–358`, `tests/test_spec_config_flow_text.py:151–157,294–300`).
- **MEDIUM — Replacement behavior is not tested.** All new renderer cases start from empty text. They do not prove that replacing an existing opt-in roster with no/false clears the old key while retaining unrelated tables. The splicer appears to support the removal, but the later installed-layout check also writes true and false to separate fresh targets, so neither check proves revocation on the same file (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:100–101`, `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:1073–1094`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:97`).
- **LOW — The PTY suite is a regression gate, not evidence of spec-config consent.** It drives `tools/setup.py`, not the spec-config skill. On a cold cache it also executes `uv run --script`; the plan gives no offline/prewarmed prerequisite. Keep the required suite, but put it in the orchestrator’s verification steps with that prerequisite and use a wizard eval to check yes/no/skip behavior (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:169–179`, `Makefile:67–70`, `tests/test_wizard_pty.py:127–153`).
- **LOW — A hand-written `key` can change the diagnostic label.** In `{"key": "policy.execute", **table}`, an extra `key` in the role table overrides the intended label; `_bool_setting` uses it in the error. Put the fixed label last and pin it in the malformed-value test (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:99–101`, `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:96–100`).

**Suggestions**

- State which config sources can authorize this opt-in. Add a layered scratch fixture that distinguishes an owner-authorized true from a checkout-supplied true without widening the execution scope.
- Specify that an order retry reuses the answer and that no execute role means no fallback key. Test a same-target `render-toml --replace` round trip: true → omitted, then resolve false; assert unrelated config remains intact.

**Risk assessment: HIGH until the consent boundary is explicit.** The serialization is straightforward. The risk is not TOML corruption; it is treating a project-supplied value as permission to run on the session.

##### Ponytail findings

- **LOW — Task 1:** Needed and appropriately small. Reuse `_ScratchLayers` and the existing public CLI/atomic-write fixture rather than building another harness. One same-target replacement case gives more evidence than several fresh-render string checks (`tests/test_lane_settings.py:270–291`, `tests/test_config_role_write.py:75–94`).
- **MEDIUM — Task 2:** Needed and correctly placed in the existing wizard. Carry one answer across the existing order-retry branch; no extra question step or settings path is needed (`skills/ai-kit-spec-config/references/wizard-flow.md:67–77`, `skills/ai-kit-spec-config/SKILL.md:352–358`).

#### Cross-plan coverage and verdict

- **Wave check:** No same-wave file overlaps. The numbered dependencies cover the handoffs: 41-02 follows 41-01; 41-03 extends 41-02’s reader guard; 41-04 consumes 41-03’s reader. The issues are incompatible instructions and missing checks, not missing scheduling edges.
- **Coverage check:** R1–R3 and their non-dismissed edges have named owners, but R1’s behavioral eval evidence and R2’s no-target/invalid-flag controller evidence remain incomplete. The R3 blocked-lane case is split: 41-04 supplies a quota-unavailable fixture, and 41-10 supplies the blocked-status selection fixture. Add one combined case so the handoff itself is proved (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:157–169`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:179–186`). The later plans assign the remaining acceptance lines and all five prohibitions; the distinct linked-worktree fixture named in research is not separately exercised by 41-07’s root/subdirectory cases (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-RESEARCH.md:406–410`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:143–149`). The phase validation also calls for full unit and arch groups after each wave; the three explicit orchestrator handoffs name dogfood and the state-file cap, not those group runs (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-VALIDATION.md:30–35`).
- **Verdict: Revise before dispatch.** Fix the owner-stop authority in 41-01, the red test and final-pick enforcement in 41-02, and the owner-consent boundary in 41-03 first.

This was a read-only review of the three manifest plans and their relevant handoffs. No files were changed, and no tests, evals, or make targets were run.

#### Batch B (41-04, 41-05, 41-06)

#### 41-04

##### Summary

The plan covers the core of EXE-04: read the opt-in flag from 41-03, preserve an available executor, and use jev only to choose between the two approved native model aliases on Claude Code. The main gaps are at the controller boundaries: the fallback can be evaluated during a resolve whose result must not be dispatched, and Step 3 does not explicitly recognize the new fallback as session-model mode.

##### Strengths

- The hook points match the real resolver: an empty candidate set, a `QuotaExhaustedError`, and the specifically recognized narrowing error. The plan leaves other `ValueError`s and configuration errors alone. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:166-167` and `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:190-202,245-274`.
- The proposed jev request is small and contains no brief text or paths. The real classifier returns only fixed labels, and the shared jev client already handles invalid choices, low confidence, timeout, and subprocess failure. See `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/task_classification.py:24-34` and `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:121-174`.

##### Concerns

- **HIGH — The new mode is not wired through the fix-round and resume decisions.** Task 3 adds a Step 2 bullet and two `--fix-round` arguments, but leaves Step 3’s native bump and ladder-floor branches unchanged. The new injection has an empty key; treating it as ordinary non-Claude native execution at round 4 sends it to an empty-anchor stop. On Claude Code, the unchanged native bump wording competes with the new “no ladder escalation” direction. The opposite problem occurs on an unpinned round-4+ resume: the first Step 2 result is **only** a source of `ladder_keys`, but the new bullet says to dispatch the fallback, and the CLI can already call jev and announce that the task runs before the actual gated pick. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:167,197-200`, `skills/ai-kit-spec-execute-superpowers/SKILL.md:216-228,246-253`, and `skills/ai-kit-spec-execute-superpowers/references/state-management.md:111-125`.
- **HIGH — A project file can assert an owner-only opt-in without proving owner consent.** Task 2 reads the merged policy via `cfg_resolve_quiet`; a project’s execute policy can override the user policy. The existing project trust check authenticates command-bearing lane entries, not role-policy values, and accepts a roster with no command-bearing entries without a trust record. A checked-in roster can therefore enable the fallback even when the user never opted in. The wizard’s explicit-yes rule does not protect the read path. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:167-169`, `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:595-602,689-706`, and `skills/ai-kit-spec-review/ai_kit_spec/trust.py:88-113`.
- **MEDIUM — Jev can resolve settings from the wrong project.** `resolve-injection --cwd` selects the target roster, but the proposed code passes the raw `deps.run_fn` to `ask_items`. That client supplies no child `cwd`, and jev reads `[jev]` from its process working directory. The shim explicitly supports invocation from another directory; the target project’s jev disable setting can therefore be missed. The existing `skill_classify` caller binds `cwd` for this reason. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:129,167`, `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:140-153`, `skills/jev-fast-decision/scripts/jev_review.py:78-85`, and `skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py:121-128`.
- **MEDIUM — The fake-lane matrix does not prove the backstops it names.** Task 2’s “blocked” case is another prefilled quota row, not a blocked-until record; 41-10 tests a blocked primary with a second lane available, not a **sole** blocked lane with session fallback enabled. The empty-config unit case likewise does not exercise the Step 1 ask, and the new tests do not drive an opt-in through the `no_candidate` branch. Also, name the exact fake route `subprocess`: `external_cli` is the injection mode, not a probe route. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:155,169`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:185-190`, `skills/ai-kit-spec-review/ai_kit_spec/routing.py:36-41,186-189`, and `tests/test_ai_kit_spec_superpowers.py:1394-1440`.
- **LOW — Task 1 gives the executor a lint-failing import list and an inaccurate anchor.** `io` and `redirect_stderr` are needed by later CLI tests, not by Task 1’s picker tests; Ruff checks test files for unused imports. The cited existing header has `sys.path` bootstrapping but no `_REPO_ROOT` constant. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:119,130-135`, `tests/test_ai_kit_spec_superpowers.py:17-26`, and `pyproject.toml:34-48`.

##### Suggestions

- Specify the fallback branch in Step 3 **before** native bump or ladder handling. Define what the follow-up native call does with a selected alias versus an empty model. For ladder-only or forced-key resolution, specify whether fallback is suppressed or ignored; either way, do not call jev or announce a native dispatch for a result the controller will discard. Preserve the actual key check used by the owner-named replacement path (`skills/ai-kit-spec-execute-superpowers/references/state-management.md:261-266`).
- Keep the locked TOML key and writer. Document what proves consent when the key comes from the project layer, and add fixtures for a checked-in opt-in without owner authorization and an authorized opt-in. Bind jev’s subprocess to the resolver’s target directory with the existing `partial(run, cwd=cwd)` pattern.
- Give the executor exact fixture builders and add the missing cases: real narrowing to `no_candidate`, no `[lanes]` through the Step 1 fake, and a sole blocked pool through 41-10’s fake reader with the fallback flag on. Assert the dispatched model parameter or its omission, not just the injection JSON.

##### Ponytail findings

- **LOW — Task 1:** Required by D-03. One adapter-local picker is sufficient; reuse shared lookup, strict response parsing, and the threshold. The locked rules call for `class_item` reuse, while Task 1 gives a hand-built item. Make that discrepancy explicit before dispatch: `class_item` currently adds a model prefix and catalog criteria that must not leak into this request. See `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:96-103,140-174`.
- **MEDIUM — Task 2:** The three resolver exits need one common decision, not a second selector. The small helper is justified, but it should consume policy from the same authorized resolution as the roster rather than rereading it after the quota walk. The current assembly already reads that roster at `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:166-190`.
- **HIGH — Task 3:** The owner-stop reference is the right detailed home, but a Step 2 pointer is not enough. Reuse the existing native dispatch and restored-round decisions rather than adding a parallel session flow. Also update the stale “answer (2) is its only way” sentence in `skills/ai-kit-spec-execute-superpowers/references/config-check.md:6-11` without changing the ask.

##### Risk Assessment

**HIGH.** The ordinary quota-exhaustion path is straightforward, but the plan does not yet demonstrate that the owner alone authorizes fallback or that a fallback stays on the intended native path through rounds 4–5. Wave 4 has no same-wave peer; its direct dependency on 41-03 and transitive dependency on 41-02 cover the named code prerequisites.

#### 41-05

##### Summary

The shared builders, optional fields, and native print hook are a good fit for the amended EXE-05 scope. The plan preserves the old composer interface and does not need a runner change. Before execution, tighten the optional-input contract and make the tracer prove the real external composition path.

##### Strengths

- Trailing defaults preserve existing two-argument composer calls and `NamedTuple` construction. The known injected reinforcement fakes take positional variadic arguments, so the proposed positional forwarding is compatible. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:105-117`, `tests/test_ai_kit_spec.py:5236-5248`, and `tests/test_compose_for_lane.py:84-110`.
- The builders follow the existing caller-fed output-format pattern and put the format block last. The tail-grep fixture checks **verbatim framing**, not whether an unchanged caller pipeline passes with a banner. That is the locked amendment; it does not require rewriting commands or touching `EXEC_PREAMBLE`. See `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py:44-52,68-82` and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:179-184,203-215`.

##### Concerns

- **MEDIUM — The “end-to-end” tracer can pass without exercising the production path end to end.** Its `files=None` case never calls the proposed `compose_fn`; the production superpowers spec defaults to `files=()`. Its other test captures a spec, then calls the composer itself. Neither test proves that `dispatch-task` parses the new flags and emits both blocks in the prompt passed to the supervised runner. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:103-125`, `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:67-103,145-154`, and `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:386-396`.
- **MEDIUM — Missing files and special-character paths have no defined failure behavior.** The proposed `_read_optional` lets an explicit missing, unreadable, or invalid UTF-8 file escape as a raw exception; `main` only handles `ConfigError`. The repeatable `--owner-config` accepts arbitrary strings but the builder wraps each path in raw single quotes: an apostrophe breaks that shell quoting, and Git pathspec metacharacters can match more than the named path. The locked `.aikit/config.toml` call is safe as written; the public argument’s broader contract is not. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:115-118,151-152`, and `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:325-353,498-505`.
- **MEDIUM — Task 1 exceeds the executor’s stated file budget.** It spans seven files, including both generated listings. Those listings are explicitly `SHARED_MACHINERY`, so the commit triggers full unit and arch groups after the focused verify and four separate repo-wide tools. That is a cap risk, not proof that the task will time out. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:102-125`, `tools/run_unittest_parallel.py:229-232`, `Makefile:98-113`, and `AGENTS.md:186-201`.
- **LOW — The framework-neutrality claim is broader than the test.** The test checks new frames with neutral inputs and explicitly exempts the module docstring. The existing module and format-builder docstrings name frameworks, and caller-supplied text is deliberately passed through verbatim. The test can establish that **ai-kit’s new framing** introduces no framework wording, not that no framework name occurs anywhere in the module or output. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:33,175-180`, `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py:1-17,44-52`, and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:109-117`.

##### Suggestions

- Use one fixture that enters through `cli.main`, keeps real `dispatch_superpowers_task` and `dispatch_execute`, and fakes only tooling, capability composition, and the final runner. Assert the captured prompt includes the exact blocks once, in order. Reuse the capture pattern in `tests/test_compose_for_lane.py:84-99`.
- Give both new CLI paths the same named failure for an explicit unreadable guidance file, distinct from an omitted flag. Define the accepted owner-config path shape and test it. Preserve the locked example output for `.aikit/config.toml`.
- Use the existing `TestDispatchGuidance` and `TestCliDispatchTask` modules, or split the tracer while keeping every commit green. If moving tests, update 41-06 and the closing evidence list together.

##### Ponytail findings

- **MEDIUM — Task 1:** The two builders and the fields that carry caller input are required by D-04; a gate discovery subsystem is not. The test-only fake composer bypass is unnecessary when the repo already has a final-prompt capture seam (`tests/test_compose_for_lane.py:84-99`).
- **LOW — Task 2:** `print-guidance` is required for the native path, which does not go through `dispatch_execute`. Reuse the same builders, `_build_parser`/`_COMMANDS`, and one optional-file error path. No native dispatcher or additional runtime abstraction is needed (`skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:431-495`).
- **LOW — Task 3:** The braces and tail-grep backstops are required, but fit naturally beside the builder tests. A separate test-only lane and four more repo-wide checks add execution cost without adding coverage if those cases can land with the builder commit (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:167-186`).

##### Risk Assessment

**MEDIUM.** The design is small and compatible with the known callers. The remaining risks are a tracer that gives more confidence than it earns, optional-input errors, and task size. Wave 5 has no same-wave peer; the 41-04 dependency correctly sequences the shared `cli.py` and `dispatch_injection.py` edits.

#### 41-06

##### Summary

The plan correctly keeps `coverage=n/a` and avoids adding an ai-kit branch regex. It does not yet deliver identical guidance on all paths: the documented native command omits the optional guard input, while the test supplies that input by hand and bypasses the controller flow it claims to verify.

##### Strengths

- The coverage claim is grounded: the runner counts parsed task blocks and emits `n/a` when there are none. The current Compose template uses an objective and a files block; keeping that shape avoids changing commit-check behavior. See `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:37-56` and `skills/ai-kit-spec-review/references/cross-ai.mjs:6273-6291,6337-6355`.
- The external recipe uses one Bash array, quotes each optional filename, and preserves the existing `dispatch-task` entry point and report handling. No runner or framework-owned script needs to change. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:129-132` and `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:63-89`.

##### Concerns

- **HIGH — The shipped native instructions drop the caller’s commit guard.** The external recipe passes `--guard-file` when present. The proposed native recipe writes gates and passes only `--owner-config` plus optional `--gates-file`. With `guard.txt` present, native implementers see the config exclusion but not the caller’s guard rules. The native branch is explicitly told not to load the external reference, so it cannot pick up the missing instruction there. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:129-132` and `skills/ai-kit-spec-execute-superpowers/SKILL.md:244-262`.
- **HIGH — The uniformity test can pass with that bug and with a broken resume recipe.** Task 1 manually supplies all three flags to both CLIs and reconstructs guidance inside `capture` instead of observing the real composed prompt. Reading the same `injection.json` again is not the documented restore path. The real quota wake skips Compose and goes directly from Restore to Dispatch. Task 2 also gives no rule for whether stale `gates.txt` or `guard.txt` in the reused task directory must be retained, replaced, or treated as absent. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:100-104,129-132`, `skills/ai-kit-spec-execute-superpowers/references/quota-wake.md:16-29`, and `skills/ai-kit-spec-execute-superpowers/SKILL.md:124-128`.
- **MEDIUM — The no-task assertion checks documentation, not the final prompt the runner parses.** `parseTasks` scans the whole prompt, including the caller-fed guidance that 41-05 prepends verbatim. A literal task tag in copied verify or guard text can invalidate the blanket `coverage=n/a` claim while the Compose substring test still passes. The docs also say `dispatch-task` *keeps* config out of commits; it only supplies guidance, and the runner’s informational `uncommitted_edits` check is unchanged. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:129-132`, `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:87-103`, and `skills/ai-kit-spec-review/references/cross-ai.mjs:6274-6291,6348-6355,6420-6439`.
- **LOW — Task 2 leaves execution details for the coding lane to decide.** “If a test … runs this block, keep it green” does not name a test or any authorized edit to `tests/test_ai_kit_spec_superpowers.py`. The plan also shows `$(...)`, `&&`, and redirection beside a shell rule forbidding them without explicitly saying the commands are Markdown file content, not shell calls for this task. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:54-66,121-132`; `tests/test_ai_kit_spec_superpowers.py:2562-2582` already has a block extractor and `:3420-3423` has a scratch Bash fixture pattern.

##### Suggestions

- Specify one input recipe for both branches: exact gate-source precedence, optional guard source, and what happens when an input is absent on a fresh run versus a pinned resume. Both branches must pass the same three inputs when present, without making native dispatch read the external-only flow.
- Test the documented argv with a stub shim, the actual Restore-to-Dispatch sequence with scratch task files, and the final external prompt through the existing execute seams. Include the optional-guard-present case; assert real exit codes and captured-call counts so empty captures cannot pass. For R5(c), check the final prompt rather than only scanning the Markdown.
- Describe the config exclusion as an instruction to the implementer, not enforcement. Keep the locked tail-grep framing and `coverage=n/a` scope; do not add an invented progress count or branch policy.

##### Ponytail findings

- **HIGH — Task 1:** The parity test is necessary for R5(d/e), but three handcrafted invocations of the same path do not buy three-path coverage. Reuse the report-mode and restore fixtures in `tests/test_ai_kit_spec_superpowers.py:1805-1827,3434-3458`, and the final-prompt capture in `tests/test_compose_for_lane.py:84-99`.
- **HIGH — Task 2:** Wiring the controller is required; duplicating gate selection in the native paragraph and omitting guard selection makes it incomplete. Keep a single input recipe with a short Step 3 pointer, two small call sites, and the existing `RUN_DIR` rather than introducing a new store (`skills/ai-kit-spec-execute-superpowers/SKILL.md:80-95,124-130`).

##### Risk Assessment

**HIGH.** The normal external route should receive guidance, but native and restored routes are not proven to receive the same content. Wave 6 has no same-wave peer. Its dependency on 41-05 supplies the flags, builders and test module; 41-07 follows it explicitly.

##### Batch coverage and handoff

- **Coverage:** All three manifest plans were reviewed as GSD implementation plans. The R3–R5 edge rows are assigned, but the **actual blocked-pool-to-native case**, **same optional guard on native**, and **no task block in the final composed prompt** lack the evidence described above. The other phase acceptance lines and prohibitions have named owners in the closing checklist. One additional evidence gap: the requirement says the 14 existing evals still *pass*, while the validation map promises shape checks and the reused judge helper only checks that evals exist and parse. Record execution or explicitly distinguish judged text and shape evidence from executed results. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:255-266`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-VALIDATION.md:43-53`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:128-132`, and `tmp/judge-40/evals_gate.py:17-28`.
- **Verification:** The named unittest runner accepts module names; nonzero and `=== tests.<module>: FAILED` are real failure signals (`tools/run_unittest_parallel.py:884-913,938-945`). For 41-05 and 41-06, replace the placeholder `<plan base>` with a recorded pre-plan SHA and compare the changed paths against the plan allowlist. Checking only `.claude/` does not prove the full no-foreign-edits prohibition. Keep `make check-dogfood` explicitly orchestrator-only: it reads the live project consent record and invokes local GSD tooling via Node (`tools/check_dogfood.py:262-265,334-346`). The immediate 41-07 handoff already documents a deliberately red dogfood check until 41-08 re-renders; do not label that intermediate state green (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:219-228`, `tools/check_dogfood.py:106-116`).
- **Owner handoff:** Leave `EXEC_PREAMBLE` unchanged. Add the explicit owner follow-up to the 41-06 summary or closing checklist; the SPEC says to return that question, but neither handoff assigns it (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:179-184`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:176-179`).

**Verdict: revise before unattended execution.** This was a read-only review; no files were changed and no tests, gates, or live lanes were run.

#### Batch C (41-07, 41-08, 41-09, 41-10)

#### 41-07

**Summary.** The plan puts the real-home guard at the right boundary: the runner builds one child environment and reuses it for each attempt. The five fake-lane cases cover the main positive and negative paths. The plan is not ready to execute as written, though: the checkout detector can miss a real checkout, and the handoff to the native timing checkpoint needs to be explicit.

**Strengths**
- Setting the variable after `childEnv` means it overrides an inherited `0` and reaches the actual lane on retries as well as the first attempt. It does not change review mode or model listing. `skills/ai-kit-spec-review/references/cross-ai.mjs:5737–5751`, `:5997–5998`, `:7257`.
- The proposed fakes record only the one variable, in a per-case scratch HOME. The harness already isolates PATH and HOME and supports per-case cwd and environment overrides. `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:1691–1710`, `:2827–2832`, `:3057–3078`.

**Concerns**
- **HIGH — Git’s discovery ceiling can turn off the installer guard inside the checkout.** The proposed walk returns before checking markers at a ceiling directory. A lane started below the ai-kit root therefore misses the guard if that root is its ceiling, despite the marker contract in SPEC amendment 7. The instructions also quote an incomplete parser: `inGitTree` normalizes ceiling entries with `path.resolve`, while the quoted expression does not. The proposed cases put the ceiling *above* the fixture checkout, so they cannot catch the false negative. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:96–105`, `:143–147`; `skills/ai-kit-spec-review/references/cross-ai.mjs:5307–5318`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:216–222`.
- **HIGH — The mixed native/cross-AI sequence is not automatic.** The plan assigns Tasks 1–2 to the lane and Task 3 to the orchestrator. The checked-in stock GSD path delegates the entire `<tasks>` section for a `cross_ai: true` plan, then marks a successful plan handled before the wave executor. Unless the stipulated per-task driver is invoked explicitly, it will not enforce the native-only timing step. Separately, 41-07 knowingly leaves dogfood red; its no-push note must control the actual checkpoint path, not just the lane, because the fold capability can push after a wave. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:164–175`, `:226–228`; `.claude/gsd-core/workflows/execute-phase.md:439–444`; `skills/ai-kit-commit-fold/SKILL.md:189–190`; `tools/check_dogfood.py:105–117`.
- **MEDIUM — The timing verification does not enforce the claimed budget by itself.** `<verify>` runs `check_reports.py`, which checks return codes, tests run, and skips, but not elapsed seconds. The plan asks the operator to inspect the 60-second limit separately and expressly forbids updating the hook’s timing table even if measurements change. Hook selection reads that table, not the per-case fixture. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:171–186`; `tmp/run-2026-11-23/p39.1-11/check_reports.py:14–33`; `tools/run_unittest_parallel.py:656–665`; `AGENTS.md:195–202`.

**Suggestions**
- Keep the locked two-marker rule. Make fixture isolation independent of a production setting that can suppress the guard. Include the ceiling-at-root regression; a linked-worktree fixture would also make that promised checkout shape explicit.
- Name the per-task driver and dispatch boundary, and make the no-push rule an explicit checkpoint instruction through 41-08. Check for the exact expected dogfood error and recheck the final combined change before publishing.
- Name the preflight inputs and their actual thresholds, enforce elapsed time mechanically from fresh shard output, and say what to do if the rounded hook timings change.

**Risk assessment: HIGH.** The hook is small, but the current detector can silently omit the protection, and the default execution path does not implement the planned split.

##### Ponytail findings
- **Task 1 — MEDIUM:** The single `runCli` insertion is necessary and enough for spawned lanes; no Python-side guard is needed. Reuse the runner’s environment path, but do not import a Git-discovery exception into the installer guard. `skills/ai-kit-spec-review/references/cross-ai.mjs:5410–5415`, `:5997–5998`.
- **Task 2 — LOW:** Keep the positive, negative, and inherited-value cases. Reuse the existing fixture-cwd pattern rather than growing another harness. `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:3035–3078`, `:12040`.
- **Task 3 — MEDIUM:** Re-recording is warranted; regenerating shard modules is not. Membership already comes from the live case list and unchanged shard counts. Copy only helpers the task actually calls. `tests/cross_ai_selftest.py:258–281`, `:337–364`.

#### 41-08

**Summary.** A native maintenance step is appropriate for updating the runner that supervises the lanes. The plan correctly collects the version pins, uses the existing render path, and checks the approved bytes. Its key weakness is that committing the bump and render together does not guarantee that they stay together after folding.

**Strengths**
- The plan updates the caller’s documented floor and the golden fixtures without raising the unrelated readiness floor. The current text test explicitly ties the caller floor to `TEMPLATE_VERSION`. `tests/test_cross_ai_settings_text.py:193–195`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:23`, `:314–318`.
- The scratch dry run checks retained CONFIG and compares the final live digest to the preview. `ensure-runner` uses the existing atomic publisher and diverts a detected concurrent edit to `.new`. `tmp/run-2026-11-23/p39.1-11/render.py:127–168`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:214–218`, `:371–388`.

**Concerns**
- **HIGH — The one-commit guarantee stops before the fold.** Task 2 checks the immediate commit only. The repository records this exact failure on the previous bump: folding split the version change from the live render. The fold implementation removes paths classified as docs from early groups and assigns them to the last feature, so checking only the original commit or the folded tip cannot prove that intermediate commits are green. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:148–159`; `.planning/ROADMAP.md:1553`; `skills/ai-kit-commit-fold/scripts/fold_group.py:171–192`.
- **MEDIUM — The maintenance runbook leaves verification and recovery dependencies implicit.** Task 2 does not explicitly copy or write `dogfood.sh` before the orchestrator calls it. The predecessor did so in its Task 2 step 3, which this plan replaces with the commit step. The rollback also says to pin known bytes before committing but later says to revert “the one combined commit” without saying whether to use `render-commit.sha` or what to do after a fold changes the hash. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:145–154`, `:194–195`; `.planning/phases/39.1-remove-the-grok-runtime-inserted/39.1-11-PLAN.md:143–146`.

**Suggestions**
- Add a post-fold, pre-push assertion that the guard, version pins, and matching rendered runner land together. Check the relevant commit tree, not just the final tree. If the existing grouping cannot preserve that unit, stop for the orchestrator rather than publishing mismatched history.
- Inline the two-line dogfood helper creation and pin the rollback target. Keep the accepted maintenance-window limitation; do not introduce another renderer or locking protocol.

**Risk assessment: MEDIUM.** The render mechanism is sound and the native route avoids the lane cap. The known history-splitting failure still needs a gate.

##### Ponytail findings
- **Task 1 — LOW:** The file count is justified by the shipped-version contract. The existing golden writers and floor test are smaller and more reliable than another fixture updater. `tests/test_runner_describe.py:410–415`; `tests/test_cross_ai_settings_text.py:193–195`. The version-only curated-config edit has an explicit judge handoff; the material cross-AI change is judged. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:25`, `:109`.
- **Task 2 — MEDIUM:** Reuse `ensure_runner`, `check_runner_copy`, and the pinned preview. Add the missing helper and a fold check, not another copy of the installer logic. `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:358–368`; `tools/check_dogfood.py:91–117`.

#### 41-09

**Summary.** The fixed-list, stdlib audit is proportionate to the requirement. The plan specifies the ten files and the observation wording, and covers both adapter paths without adding a runner-wide audit. The missing piece is a reliable failure contract: an unusable audit must not stop a task or masquerade as a valid comparison.

**Strengths**
- The new result field does not need a classifier change: the classifier reads the existing status, return code, and reason, not unrelated result keys. The CLI can publish the observation alongside its existing JSON and stderr channels. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:442–469`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:346–362`.
- Reusing the cache writer gives the native snapshot an atomic write without a new storage mechanism. The proposed scratch-HOME fixtures cover changed and unchanged files, order, non-ASCII paths, and a listed path that is a directory. `skills/ai-kit-spec-review/ai_kit_spec/cache.py:15–46`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:115–117`, `:152–158`.

**Concerns**
- **HIGH — Audit I/O can become a stop, a missed observation, or a false observation.** `--snapshot` calls the writer without handling `OSError`, while CLI `main` catches only `ConfigError`. Even a bare filename fails in the current writer because it tries to create an empty parent path. `--compare` also accepts `{}` and partial objects, producing false changes for omitted files that already existed. Task 3 gives the controller one reused filename and no rule for a failed snapshot, so a later compare can use stale data. On the external path, an exception from the dispatch skips the after-snapshot altogether. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:114`, `:151–158`, `:182–183`; `skills/ai-kit-spec-review/ai_kit_spec/cache.py:23–45`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:498–505`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:570–595`.
- **MEDIUM — Existing fake dispatches acquire a filesystem side effect without an explicit scratch HOME.** Task 1 supplies the new seam only in its new tests; existing dispatch tests and the 41-06 uniformity fixture instantiate the real adapter wrapper without that seam. The parallel runner supplies an isolated HOME, but invoking those tests directly can stat the caller’s actual configs. The plan does not name these callers for update. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:102–118`; `tests/test_ai_kit_spec_superpowers.py:884–890`, `:937–944`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:104`; `tools/run_unittest_parallel.py:442–456`.
- **LOW — Test setup is not fully mechanical.** `_touch` relies on wall time instead of assigning distinct fixture mtimes. Task 3 uses `Path` but does not name the import; Task 2 says “same scratch-HOME `setUp`” without specifying reuse or cleanup. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:115`, `:152–158`, `:184`.

**Suggestions**
- Specify the exact ten-key snapshot shape and the non-gating response to an unusable snapshot. Compare only a fresh, successful snapshot for that lane, even when the lane fails. Preserve an original dispatch exception; an audit error must not replace it. Add tests for write failure, an incomplete snapshot, and an exceptional dispatch.
- Pass scratch HOME at every fake-wrapper call site and use two fixed nanosecond mtimes. Put the external relay instruction at the common post-dispatch point before any outcome branch; `ok`, quota, and `real_error` all need it. `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:84–123`, `:136–145`.

**Risk assessment: HIGH.** The ordinary path is straightforward, but this plan needs to prove the “observation, never a stop” guarantee on failure paths, not just on lanes returning result dictionaries.

##### Ponytail findings
- **Task 1 — MEDIUM:** Keep a single fixed-list stat helper at the adapter boundary. No directory scan, content read, or second runner is needed. Finish the existing fake callers in the same task. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:366–397`.
- **Task 2 — MEDIUM:** Keep the existing parser and cache seams. Exact shape validation and defined write-failure behavior are needed; a general snapshot format is not. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:70–94`, `:479–505`; `skills/ai-kit-spec-review/ai_kit_spec/cache.py:15–45`.
- **Task 3 — LOW:** One external reference section and a native command line fit the existing disclosure rule. Pin the order and failure behavior, not merely the presence of both command strings. `skills/ai-kit-spec-execute-superpowers/SKILL.md:246–263`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:130–133`.

#### 41-10

**Summary.** The pool field and role-aware switch are good reuse of Phase 40. The blocked-pool selection slice is not complete: it feeds the shared helper the ladder *before* exclusions, and the proposed test cannot demonstrate a once-only retry. The 41-11 handoff also needs to distinguish actual quota from transient errors.

**Strengths**
- Validating the pool at roster assembly and reusing `RunnerSpec.pool` avoids a second flag reader and a second argv builder. `runner_flags` already emits the pair, and capability composition preserves it. `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:116–126`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:90–91`, `:222–247`; `skills/ai-kit-spec-review/ai_kit_spec/capability_block.py:459–462`.
- The review default preserves the existing ping and switch call sites. The blocked-status reader uses the existing bounded subprocess path, and missing tooling, spawn errors, nonzero exits, and malformed records already have fail-open unit coverage. `skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py:173–177`, `:222`; `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:77–98`, `:154–179`, `:269–277`; `skills/ai-kit-spec-review/ai_kit_spec/detection.py:955–982`; `tests/test_lane_switch.py:93–113`.

**Concerns**
- **HIGH — An excluded lane can consume the expired pool’s one retry.** Suppose flagged A and B share an expired pool, A ranks first, and the current fix round or task excludes A. The proposed call passes `loaded.ladder_keys`, which still includes A. The shared helper gives A `expired-retry` and stamps B unavailable as `expired-wait`; the real selection cannot try A, so it tries neither. The call also includes native-routed entries, whose quota rows are subsequently dropped; such an entry can consume the subprocess pool’s retry without using that pool. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:173–188`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:166–187`, `:213–230`; `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:134–179`.
- **HIGH — The 41-11 handoff does not prove a quota-only switch.** The downstream handler accepts both adapter classes and normalizes them to `"quota"` before calling the shared switch. But the current classifier maps some `transient` outcomes to those same classes. A flagged lane can therefore switch on a transient failure even though authorization is quota-only. The helper tests in 41-10 and the CLI tests in 41-11 inject class labels directly; neither catches the misclassification at the boundary. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:143–153`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:101–106`, `:135–137`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:452–469`.
- **MEDIUM — The selection fixture cannot prove “once,” and the task unnecessarily resolves config twice.** The expiry test uses an empty cache, one flagged lane, and an identity refresh. It checks the returned key, not whether a stale entry was cleared, one pool read occurred, or exactly one eligible lane was probed. It also uses wall time despite the fake-clock validation contract. In production the second config read can repeat warnings or load different flags from the config that produced the ranked candidates. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:185–190`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-VALIDATION.md:51`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:176–190`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:299–316`.
- **MEDIUM — The cross-AI tasks leave avoidable choices to the executor.** Task 1 lists six files and triggers the full unit and arch hook by changing generated shared files. It should name the exact one-argument `runner_flags(spec)` call and the existing dispatch seam rather than ask the lane to infer defaults. Task 3 specifies a module helper with a `self` argument, then leaves fixture initialization and clock injection implicit. This is a budget risk, not a measured overrun. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:100`, `:114–117`, `:186`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:222`; `tools/run_unittest_parallel.py:226–232`.

**Suggestions**
- Apply `blocked_cache_entries` to the ranked, currently eligible subprocess keys. Keep the raw roster flags from the same resolution used to assemble candidates. Use a fixed clock, two flagged lanes in one pool, an excluded first lane, and a stale quota cache; assert the reader call and the eligible probe, not just the selection.
- At the 41-11 boundary, use typed runner evidence to distinguish quota from transient without changing the existing wait/stop classification. Exercise the full handoff with fake results: flagged quota switches, flagged transient does not, unflagged quota stops and reports, and no eligible fallback reports without dispatch.
- Give Task 1 the existing fake-runner seam so it observes the pool at the real dispatch boundary. Give Task 3 an exact fixture method signature and imports. `tests/test_ai_kit_spec_superpowers.py:905–949`.

**Risk assessment: HIGH.** The current plan can skip the only eligible retry and can hand off a switch on a failure that the owner did not authorize.

##### Ponytail findings
- **Task 1 — LOW:** Necessary. Reuse `lane_free_pool`, `RunnerSpec.pool`, and the existing fake runner. No additional flag reader, argv builder, or native injection field is needed. `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:116–126`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:245–247`.
- **Task 2 — LOW:** A defaulted role is the right scale. Retain the locked helper signatures and existing fallback walk; there is no need for an executor-specific copy. `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:30–61`, `:182–193`.
- **Task 3 — HIGH:** Reuse the Phase 40 cache helper, but give it the keys that can actually be tried. One authoritative roster read and the existing `probe_keys` filter solve more than an additional resolver or retry policy would. `skills/ai-kit-spec-review/ai_kit_spec/cli.py:946–959`; `skills/ai-kit-spec-review/ai_kit_spec/routing.py:186–189`.

**Batch coverage and verdict.** All four manifest IDs were reviewed. Waves 7–10 are serial, with no same-wave file overlap. The declared chain reaches the 41-06 predecessor and the 41-11 switch handoff; 41-12 through 41-14 name the documentation, eval, judge, and installed-layout follow-through. For this batch, the remaining acceptance gaps are the R6 checkout false negative, R7’s non-gating failure paths, and R8’s eligible once-only retry and quota-only switch. The prohibitions are allocated, but those last two behaviors are not yet demonstrated by the proposed tests.

**Request another review cycle before execution.** This was a read-only source and plan review. No files were changed, no tests or make targets were run, and lane timing was not measured.

#### Batch D (41-11, 41-12, 41-13, 41-14)

#### 41-11

**Summary:** The plan reuses the Phase 40 lane selector and puts the fallback decision before the quota wait. The CLI contract is largely specified, but the shipped workflow can switch on a non-quota failure, overwrite the failed lane’s resume state before a replacement is validated, and tell the agent both to switch and never to re-resolve.

**Strengths**
- The selection helper reuses the owner’s roster and order rather than introducing a second fallback policy. `flagged_replacement` checks the flag, and `lane_fallback` rejects same-pool and flagged replacements. The execute-role ordering and same-pool fixtures are in the immediate predecessor. See `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:46–61,182–193`, `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:146–167`, and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:148–154`.
- Task 3 targets the correct cross-AI sentence and updates its existing exact-text test in the same commit. See `skills/ai-kit-cross-ai/SKILL.md:358–362` and `tests/test_lane_failure_text.py:19–24,201–203`.

**Concerns**
- **HIGH — A transient capacity failure can authorize a switch.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:101,135–136` treats both `quota` and `quota_cycle` as proof of quota. The adapter classifies exit 75 with both retry tokens as `quota_cycle` regardless of reason; it can also classify a bare transient 69/75 as `quota`. The runner uses its hard tier for both quota and transient failures, and Python maps `transient` to `capacity`, not `quota`. A flagged lane that hits capacity can therefore switch outside the owner’s EXE-09 authorization. See `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:442–469`, `skills/ai-kit-spec-review/references/cross-ai.mjs:5949–5959,6091–6122`, and `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:39–48`.
- **HIGH — A failed replacement lookup can corrupt the pin or schedule the old wait.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:136–137` calls the existing re-resolve block, which writes the new `INJECTION_JSON.json` and mode *before* checking the new key. If the result is `no_candidate`, `quota_exhausted`, or the session fallback, the plan sends the agent to **Read tokens** with the old classification but the new injection file. The pinned writer reads that file, and an old `quota_cycle` can still reach the scheduler. Cleanup is only specified after a replacement dispatch returns. The same step also masks exit 2 with `|| true` and has no branch for empty or malformed JSON. See `skills/ai-kit-spec-execute-superpowers/references/escalation.md:83–105`, `skills/ai-kit-spec-execute-superpowers/references/state-management.md:188–216`, and `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:166–201`.
- **HIGH — The caller’s hard rules and wake path still forbid the new behavior.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:125,137–139` expressly keeps the next two NEVER lines, which forbid re-resolving after failure. It does not update the same-round ban or the unconditional 69 owner-stop wording carried forward by 41-01. The quota-wake path runs Classify as written but does not bind `BRIEF_FILE` for a re-resolve, and tells the agent not to resolve during the wake re-dispatch. The proposed test checks word order, not any of these branches. See `skills/ai-kit-spec-execute-superpowers/SKILL.md:31–33,195–201,216–218`, `skills/ai-kit-spec-execute-superpowers/references/quota-wake.md:8–34`, and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:156–162`.
- **MEDIUM — Candidate selection and task eligibility use different sets.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:101–103,137` selects from the role roster with `exclude=set()`, then tries to force the returned key through a re-resolve that still honors task narrowing and existing exclusions. If the first routable candidate was already tried or did not fit the task, the CLI can say `switched: true` even though the next step cannot dispatch it. The test fakes routing and stops at the proposed key. See `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:213–230` and `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:258–292`.
- **MEDIUM — Task 1 performs avoidable config migration and routing work on refusal paths.** The `migrate=False` read in `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:102` is followed by `assemble_candidates`, whose default config read can migrate. Full routing is also eager, even for an unflagged or unknown lane, and can refresh the runtime cache or invoke discovery. The fake `route_all_fn` masks these effects. See `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:166–178`, `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:671–691`, and `skills/ai-kit-spec-review/ai_kit_spec/routing.py:265–280,353–369`.

**Suggestions**
- Keep the locked switch API and same-round behavior, but require positive quota evidence from the validated dispatch result before calling it. Test transient 69/75, actual quota 69/75, and an unflagged lane.
- Make the forced lookup temporary. Keep the original injection and classification intact until the replacement validates; bind the replacement’s mode, key and runtime together only on success. Specify cleanup on every outcome and pin a fake flow in which the replacement cannot resolve. Say explicitly that the Bash snippets are Markdown file content, not shell calls for the coding lane.
- Update the existing NEVER, owner-stop and wake pins in the same task. Also reconcile spec-config’s “no run reads it yet” statements without changing the wizard’s questions (`skills/ai-kit-spec-config/references/free-lanes.md:31`; `skills/ai-kit-spec-config/references/config-file.md:140,149`).

**Risk assessment: HIGH.** This is the only plan in the batch that changes live dispatch decisions. The current tests could pass while the controller runs an unauthorized replacement or saves the wrong lane for resume.

##### Ponytail findings
- **MEDIUM — Task 1:** The outcome helper is justified by the named refusals; the second config read and eager routing are not. Reuse the lazy-lookup pattern in `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:230–239`, keeping the read-only roster as the source for both flag and route decisions.
- **HIGH — Task 2:** Same-round dispatch is required, but reimplementing state transitions in agent prose leaves too much to the executor. Reuse the forced-key and verification pattern in `skills/ai-kit-spec-execute-superpowers/references/state-management.md:220–267`; unlike an owner-named replacement, the automatic path must not clear permanent exclusions. Cover the wake and stopped-state callers, not just the new paragraph.
- **LOW — Task 3:** Required by amendment 9 and appropriately small. Keep the `EXCEPTION` pin and `SWITCH_RE` check rather than adding another policy test framework (`tests/test_lane_failure_text.py:201–203`; `tests/test_cross_ai_skill_text.py:248–254`).

#### 41-12

**Summary:** The four new evals and the single-home checks are the right deliverables. The plan needs deterministic eval inputs and a test that checks where the actual rules live, not merely where certain command names appear. The README also needs to match the limits of the implementation.

**Strengths**
- The proposed evals use the five-key schema and the existing convention of renaming a fixture `aikit/` directory to `.aikit/` in a scratch project. See `tests/test_skill_evals_shape.py:16–19,41–65` and `skills/ai-kit-spec-execute-superpowers/evals/evals.json:103–110`.
- The planted-second-copy test provides a useful negative control, and the README task is confined to an existing row. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:131–135,149–157` and `README.md:37`.

**Concerns**
- **MEDIUM — Two evals have no explicit `files` list, and the scripted outcomes are not specified.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:99–102` omits the lists for escalation and flagged quota. An empty list fails the reverse fixture check if the new files are unlisted; an omitted list fails the schema. The fallback and switch prompts also supply placeholder models and a claimed quota state without saying which calls are faked or which responses the scenario supplies. Conversely, the single all-unavailable scenario cannot demonstrate “Never replaces an available lane.” See `tests/test_skill_evals_shape.py:57–86` and `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:174–187,205–221`.
- **MEDIUM — Task 2 can stop before writing its tests, and the proposed checks miss duplicate rules.** In `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:130`, `rg -l -F <marker>` needs `-e` or `--` for `--gates-file`; its search scope also differs from the test’s. At lines 131–134, a command-name search lets a duplicate rule with different wording pass, while generic file links can satisfy the pointer test without pointing to the right topic. `--gates-file` is not a pin for the commit guard or the real-home guard. The existing 41-01 test already separates heading counts, rule text and pointers. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:122,162`.
- **MEDIUM — The README promises more than the planned caller does.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:156` says the project’s gates and guard reach *every* dispatch and that exec lanes get the guard without qualification. The gate file is optional; 41-06’s native recipe omits the optional `--guard-file` that the external recipe passes, even though the uniformity test supplies that flag directly to the native CLI. The real-home guard applies to spawned exec lanes in an ai-kit checkout, not native calls. This leaves SPEC R5(d/e) unproven on the actual native caller. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:104,129–132`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:182–184`, and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:201–222`.

**Suggestions**
- Specify the exact file lists and give each eval a deterministic scratch transcript or fake responses. Keep the “available lane is never replaced” claim in the existing fake-lane test unless the eval includes the complementary case. Use `-e` for literal patterns beginning with `-`.
- Pin the actual rule and topic anchor with the 41-01 helpers. Fix the native guard-file handoff in its owning slice before closing, then qualify the README by caller-supplied text and checkout scope.
- Record that 41-12 contributes verification to EXE-05 and EXE-09 as well as R9/JDG-04: its frontmatter omits those IDs while its truths pin the gate/guard and switch (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:16–22`).

**Risk assessment: MEDIUM.** No runtime changes are needed in this slice, but the preflight can halt for a mechanical reason, and the evals and text pins can give confidence without checking the claimed behavior.

##### Ponytail findings
- **MEDIUM — Task 1:** All four evals are required by R10. Reuse the existing scratch-project prompt and existing plan input; add only the fake responses each case needs (`skills/ai-kit-spec-execute-superpowers/evals/evals.json:103–110`).
- **MEDIUM — Task 2:** The single-home test is required by R9. Extend `docs`, `marker_files`, and `rule_files` from 41-01 rather than creating a second scanner with different semantics (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:122`).
- **LOW — Task 3:** The existing README row is the right scope. A qualified sentence is enough; no new section or command catalog is needed (`README.md:37`; `AGENTS.md:356–358`).

#### 41-13

**Summary:** Reusing the judge tooling, deriving the judged set from Git, and distinguishing sanctioned no-rejudge fixes from fresh verdicts are sound. However, the copied driver fails its own check as specified, and the inherited first-round ping policy conflicts with the current launch rule.

**Strengths**
- The Git-derived set rejects unexpected skills, and the curated-config exception is limited to the version-only change planned in 41-08. See `tmp/judge-40/judged.py:34–62,98–114` and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:115–117,195–196`.
- `closing.sh` is planned with `--gate`, which matters: plain dogfood validates record integrity, but `judge_loop.py` makes an unmet bar fatal only when asked to gate. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:109,144–152`, `tools/check_dogfood.py:604–619`, and `tools/judge_loop.py:1376–1389`.

**Concerns**
- **HIGH — The copied driver fails before paid work starts.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:105–107` changes the loop identifiers and paths but leaves the copied `checks()` logic intact. That logic requires `check.py` to contain `RUN / "skills.txt"` and not `RUN / "skills.r1.txt"`; the current source `check.py` contains both, the latter in its docstring. The copied driver prints `round scope: check failed` and exits 1. See `tmp/judge-40/copy_drivers.py:52–68` and `tmp/judge-40/check.py:1–5,19–21`.
- **HIGH — Inherited round-one handling allows a failed referee to launch.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:110–111` copies Phase 40’s round-one rule, which lets a failed referee go through the separate driver probe and proceed if that probe succeeds. `ping-lanes` exits 0 when *some* lanes survive, so checking only the command’s exit is not enough. `AGENTS.md` forbids launching a judge whose ping failed in that round, including round one. See `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:114–115`, `skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py:213–232,258–267`, and `AGENTS.md:80–83`.
- **MEDIUM — The required code-review handoff has no producer in the batch.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:96,186–188` requires `/gsd-code-review 41` and its fixes before Task 1, but the pre-run steps only initialize the judge ledger. The normal GSD code-review gate comes after wave execution. This is an orchestration gap between 41-12 and 41-13, not a missing transitive file dependency. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:196–203` and `.claude/gsd-core/workflows/execute-phase.md:1136–1169`.
- **MEDIUM — Task 2 mixes acceptance with informational diagnostics.** The dogfood failure rule at `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:139–145` names a `judge records:` problem line, but the tool uses that prefix for both problems and expected stale-digest notes. The instructions also call `prior_base` a `tools/judge_loop.py` anchor; the scoring gate uses `prior_worst`, which checks rubric compatibility. The scratch `regression.py` uses a separate comparison without that filter. These can disagree, and the plan’s “base” figures for loops 36 and 39.1.3 refer to their earlier comparisons, not the new loop’s inputs. See `tools/check_dogfood.py:604–619,635–648`, `tools/judge_loop.py:952–973,1367–1372`, `tmp/judge-40/regression.py:42–74`, and `.planning/judge/REJUDGE.md:34–40,95–101`.
- **MEDIUM — Mtime evidence does not mitigate disclosure.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:166–174` lists the real-HOME audits as a mitigation for information disclosure. They detect selected file modifications, not reads or transmission. The fixed check stats eight paths, and the broad check reports newer files and always exits 0. Keep the authorized live referee step, but label this as write-observation evidence, not a confidentiality control. See `tmp/judge-40/real_config_audit.py:9–24,27–43` and `tmp/run-2026-11-23/audit_real_config.py:14–46`.

**Suggestions**
- Keep the allowlisted copy, but make the preflight check executable code rather than matching a docstring. Require it to pass before any live ping or judge call.
- Put the code-review checkpoint explicitly between waves 12 and 13 and record the reviewed SHA. Apply the failed-ping rule before all launch paths, including the count-one advisory lane. Preserve the fixed pool and the authorized substitute policy; if they cannot be satisfied, return to the owner without recording a successful round.
- Use one authoritative regression result from `judge_loop.py check`. Treat dogfood exit status and its exact success marker as the gate; preserve stale notes as notes. Explicitly separate an owner-blocked result from a passing judge plan.

**Risk assessment: HIGH.** The current preflight can dead-stop the plan, and bypassing it would still leave a first-round branch that can disregard the owner’s ping requirement.

##### Ponytail findings
- **HIGH — Task 1:** The preflight, Git-derived set, ping and freeze are all necessary. Reuse the existing drivers, but don’t preserve a stale self-check just to keep the copy literal. Reuse `ping-lanes`’ per-key outcomes rather than treating a second probe as launch authorization (`tmp/judge-40/copy_drivers.py:52–68`; `skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py:213–232`).
- **MEDIUM — Task 2:** The records, fix rule and closing gate are necessary. Reuse `publish.py`’s destination conflict check and `judge_loop.py`’s gated result; a parallel scoring implementation adds disagreement without stronger evidence (`tmp/judge-40/publish.py:51–76`; `tools/judge_loop.py:1357–1396`). Declare the conditional skill/test edits in `files_modified`; the current frontmatter lists only record paths although Task 2 permits those edits.

#### 41-14

**Summary:** The closing plan has a useful evidence model: installed shims in a scratch HOME, one suite run per candidate, per-module reports, and a same-SHA gate before the live link step. Two installed-layout assertions cannot pass with the specified inputs, and the closeout currently gives more credit to several tests than they can prove.

**Strengths**
- The installed-layout check inherits a real tripwire and an environment that strips host configuration and credential overrides; the live-link helper refuses conflicting destinations rather than replacing them. See `tools/run_unittest_parallel.py:370–388,438–462` and `tmp/run-2026-11-23/p40-13/live_links.py:14–43`.
- Candidate-specific module reports and the explicit distinction between skipped and passed evidence are appropriate. The report reader rejects missing required modules, and the clean-room exception is grounded in the actual preflight skip conditions. See `tmp/run-2026-11-23/p40-13/evidence.py:28–53`, `tests/test_ai_kit_gsd_spec_discuss_e2e.py:78–92`, and `Makefile:65–89`.

**Concerns**
- **HIGH — The scratch fallback fixture has no routable fallback.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:92,96` says to keep the copied synthetic inventory exactly, but the copy seeds `"clis": {}`. Both new fixture lanes require a named external runtime. The fresh inventory marks that runtime `not_installed`, and `next_lane` rejects the route. Expected `switched: true` cannot follow. See `tmp/run-2026-11-23/p40-13/layout_check.py:52–75`, `skills/ai-kit-spec-review/ai_kit_spec/routing.py:104–123,154–183,353–365`, and `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:46–61`.
- **HIGH — `escalation-gate` takes JSON text, not a filename.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:93` gives a file path as the argument and then says to pass it as the reference does. The planned handler calls `json.loads(args.injection_json)` before its guarded escalation call. Passing the literal path raises instead of producing the stays-on result. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:122,152`. At line 97 of 41-14, also spell out `render-toml --json-config <file> --out <file>` and check the parsed execute table, not just a matching line (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:336–348,1107–1112`).
- **MEDIUM — “Every shard ran” needs an expected set, not a glob over available reports.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:128` does not say how to enumerate the expected shards. The inherited script checks for missing reports only for modules named in `STRICT`; matching only reports found on disk cannot detect a missing shard. A shard can also skip with exit 0. See `tmp/run-2026-11-23/p40-13/evidence.py:13–16,28–44`, `Makefile:11`, and `tests/cross_ai_selftest.py:309–331`.
- **MEDIUM — Closure needs a named route back to judge evidence after a suite fix.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:130,151,196` restarts Tasks 1–2 on a new HEAD, but does not say how to settle a new digest change before another expensive test run. `--require-current` exits 1 on a changed digest, and the inherited exception applies only to a recorded no-rejudge fix with no subsequent skill change. See `tools/judge_loop.py:1376–1389,1957–1962` and `.planning/phases/40-resilient-review-sized-by-jev/40-13-SUMMARY.md:125–129`.
- **MEDIUM — The requirement checklist overstates the evidence.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:132` credits the executor-switch module for the same-round switch and unflagged stop; 41-11’s tests stop at returning a key or refusal, and its doc test checks marker order. Likewise, the guard uniformity test calls the print command directly with the flag the native caller omits. The closeout should not equate these checks with a tested controller transition or an equivalent native brief. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:103–106,137–143` and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:104,129–132`.
- **MEDIUM — The mandated owner handoff does not reach closeout.** Nothing in the closeout checklist or artifact list records the `EXEC_PREAMBLE` question for the owner or the open-gsd note. Those are handoffs, not invitations to expand implementation scope. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:132,195–204` and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:179–184,238–240`.

**Suggestions**
- Keep the installed-layout test. Seed a fresh synthetic inventory with the fixture runtime, both placeholder models, and a current runner fact; assert the tripwire still records zero calls. Pass injection JSON text explicitly. Tie each expected exit to a named invocation, including the empty guidance case, audit snapshot and compare, and both TOML writes.
- Use the declared shard list as the expected report set and fail on missing, duplicate or skipped reports. Check judge digests before rerunning the expensive suites after a fix; send a newly stale judged skill to the existing judge/owner path rather than inventing an exception.
- Carry the pre-write SHA and owner-stop audit checks forward explicitly. The inherited live helper honors `CLAUDE_CONFIG_DIR`, while the broad audit scans fixed HOME paths; report that coverage limit and verify the link under the same root the installer used (`tmp/run-2026-11-23/p40-13/live_links.py:8–11`; `tmp/run-2026-11-23/audit_real_config.py:14–28`). Record the evidence and the two owner handoffs before the ROADMAP tick.

**Risk assessment: HIGH.** As written, the installed check blocks a valid build. Working around the fixture by weakening expectations would also weaken the final evidence.

##### Ponytail findings
- **HIGH — Task 1:** The linked-shim test is needed; another wrapper or a real host call is not. Keep the existing `baseline_env` and `write_tripwire`, and correct the input and cache fixtures (`tools/run_unittest_parallel.py:370–388,438–462`).
- **MEDIUM — Task 2:** The suites and dry run are required. Reuse `evidence.py`’s strict missing-report check with an explicit shard set; do not run a second suite to obtain evidence from the first (`tmp/run-2026-11-23/p40-13/evidence.py:28–53`).
- **LOW — Task 3:** The one-line ROADMAP tick and single-file commit check are appropriately small. The line exists exactly where expected; keep the same-SHA precondition rather than adding another completion mechanism (`.planning/ROADMAP.md:133`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:148–162`).

#### Cross-plan coverage

- **Waves:** No same-wave file overlap in this batch. The checked frontmatters form the serial chain `41-10 → 41-11 → 41-12 → 41-13 → 41-14`; the earlier producers are transitively ordered. The missing action is the explicit code-review checkpoint between 41-12 and 41-13, noted above.
- **Requirements and prohibitions:** All nine SPEC acceptance lines have named owners. D-01 through D-09 are cited across the phase. The five SPEC prohibitions land in 41-04 (fallback off and both jev restrictions), 41-10/11 (unflagged switch), 41-07/09/14 (real HOME and audit), and 41-05/06/14 (framework scope). The material gaps are the R1 claim that the original evals *pass* rather than remain unchanged and shape-valid, R5’s actual native guard-file handoff, and R8’s controller transition. Keep evals labeled transcript-assessed unless executed. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:257–266,323–327` and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:132`.
- **Edges:** The resolved, non-dismissed rows have planned owners, but two backstops are weaker than their labels. R6’s linked-worktree case is justified by the marker logic but not exercised alongside the root/subdirectory fixtures. R8’s expired-pool fixture checks one returned key, not that two lanes in the same expired pool result in exactly one retry. Add those cases to the existing suites or distinguish static reasoning from executed proof. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:298–308`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:143–149`, and `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:185–190`.
- **Intermediate green gate:** 41-07 explicitly leaves `make check-dogfood` red until 41-08 re-renders the committed runner copy. The checker really does reject that drift. This is a declared exception, not an intermediate green gate; reconcile it with the locked execution rules before relying on per-plan green or push evidence. See `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:180,226–228`, `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:145–148`, and `tools/check_dogfood.py:105–117`.

**Verdict: revise before execution.** Prioritize quota authorization and pin preservation in 41-11, the judge bootstrap and ping gate in 41-13, and the impossible installed-layout inputs in 41-14.

This was a static, read-only review of all four manifest plans. No tests, live host calls, edits, or commits were made; timing and planned green gates remain unverified.

### Triage of cycle 1 (planner fix pass after the cycle)

#### Batch A (41-01, 41-02, 41-03)

# Batch A dispositions (review cycle 1, referee-one)

- 41-01 HIGH owner stop has multiple authorities: fixed (A1: `## Owner stop` holds every stop-versus-continue decision; new Task 2 moves the dispatch-time decisions out of SKILL.md and Schedule-or-stop, new Task 3 moves the rounds 4-5 and resumable-state stops; the moved `ok` bullet names "Clear the resume state"; pins of `every RETURNCODE 69`, `is classified quota but is an owner stop` and `Only a classified "quota_cycle"` move to resolution-stops.md with assertNotIn at the origin; `stopped=hard-waits` stays in SKILL.md only as a mention because tests/test_quota_policy_text.py reads SKILL.md alone; artifacts tell 41-11 where its switch goes)
- 41-01 MEDIUM links inside references/ point one directory too deep: fixed (A2: link-form rule in the objective; sibling-relative links in Task 1 steps 3-5 and Tasks 2-3; `link_problems` resolves each home link to a file and heading, planted bad link caught; `rule_files` counts occurrences so a duplicate inside one file counts)
- 41-01 MEDIUM evidence does not support "14 evals pass": fixed (A3: tests.test_spec_chain_text in every gate and the verification; truth and success criteria say "the 14 evals keep their shape and the no-config chain tests pass")
- 41-01 MEDIUM unattended tasks wider than the sizing rule / open-ended shortening / SUMMARY owned by orchestrator: fixed (A4: exact replacements with HEAD-checked old strings and line counts 294, 286, 279 computed on a scratch copy; the old Task 2 is split into Task 2 (5 paths) and Task 3 (7 paths); "list in the SUMMARY" replaced by "stop and report")
- 41-01 ponytail MEDIUM Task 1 reuse / put instructions in the home: fixed (no new helper; the home carries the rule, others link)
- 41-01 ponytail MEDIUM Task 2 move the decision, not a second copy: fixed (A1, as above)
- 41-02 HIGH Task 2 verification cannot pass (`--injection-json "$INJECTION_JSON"` forbidden; executable floor test replaced): fixed (A5: `escalation-gate --injection-file "$RUN_DIR/INJECTION_JSON.json" --out-dir "$RUN_DIR"`; `test_no_block_pastes_json_into_a_command` unchanged; the floor-block test is adapted, not deleted, and runs the real block with the real shim and a scratch roster, proving success and the no-write refusal; shell text in Task 2 labelled as file content)
- 41-02 HIGH allowed lanes not enforced at the final pick: fixed (A6: `exclude` = live roster keys plus `ladder_keys` minus `allowed`; the doc block checks `$INJECTION_KEY` against the gate-written `ESCALATION_ALLOWED_JSON.json`, a key outside it is an owner stop listed in `## Owner stop`; escalate false is "the same lane, not a bump"; `TestGateFeedsTheResolver` feeds the gate's exclusion into the real `resolve-injection`: stale ladder with a new lane, anchor unavailable -> quota_exhausted)
- 41-02 HIGH (same finding) 41-04 session fallback from the narrowed re-resolve: deferred (to 41-04: F2/B1 make 41-04 refuse the fallback whenever escalation-excluded keys are given; 41-02 pins the quota stop, the function does not exist yet)
- 41-02 MEDIUM CLI error contract and R2 edge evidence incomplete: fixed (A7: `_read_injection_file` reads and decodes in its own guard; unreadable, malformed, non-object or non-list `ladder_keys` -> `ai-kit-spec: escalation-gate: unreadable injection file <path>` exit 2; CLI tests for exit 2 (non-boolean flag, unreadable file), exit 3 (unknown anchor, nothing written) and the no-target notice; 41-14 must pass `--injection-file`, named in the artifacts)
- 41-02 MEDIUM spec-config solicits consent for the wrong action: fixed (A8: the wizard question, both config-file.md definitions and the eval expected output and assertions say "at fix rounds 4 and 5 ... a more capable lane ranked above it"; flow-text test pins the question; no new step; no test pinned "next lane of another runtime")
- 41-02 MEDIUM Task 1 oversized; Task 2 omits test setup: fixed (A9: Task 1 stays at 5 paths plus the two generated listings; the new module has no `_super_text()`, so it defines a new `SUPER_DIR` path constant in Task 1 and Task 2's `TestEscalationDocs` uses it, placed before the `__main__` guard; the header anchor now quotes the real bootstrap lines, no `_REPO_ROOT`)
- 41-02 ponytail MEDIUM Task 1 spend test effort on real CLI branches: fixed (A7 CLI tests)
- 41-02 ponytail HIGH Task 2 reuse the exclusion channel and fake-resolver pattern: fixed (A6 test reuses the call shape of `test_owner_named_second_key_is_the_one_resolve_injection_picks`)
- 41-02 ponytail MEDIUM Task 3 update the consent wording: fixed (A8)
- 41-03 HIGH owner consent not enforced at the config-read boundary: rejected (A10: the fallback keeps execution in the owner's own session, no external CLI, no new process, no secret; `trust.py` guards executable custom commands, not policy values; the project-local file is spec-config's default write target, so a trust requirement would break the owner's normal path; recorded as MEDIUM for the owner: new threat row T-41-53 (accept) states that a checkout-supplied `.aikit/config.toml` can turn the fallback on and the impact, plus a trust-boundary row; T-41-08 no longer claims the wizard alone mitigates every path)
- 41-03 MEDIUM "ask once" underspecified on an order retry: fixed (A11: wizard step 9 keeps the answer on an order retry and writes no key when the execute role has no lane; flow-text test pins it; `test_no_execute_lane_writes_no_fallback` pins the writer)
- 41-03 MEDIUM replacement behaviour not tested: fixed (A11: `test_replace_drops_the_fallback_and_keeps_other_tables`, same target through the public `render-toml` CLI, true then `--replace` without it: key gone, `[skills.roles]` kept, resolve reads False)
- 41-03 LOW PTY suite is a regression gate, not consent evidence: fixed (A13: dropped from the plan's verification; named as plan 41-14's closing-gate regression with the prewarmed-uv note)
- 41-03 LOW hand-written `key` can change the diagnostic label: fixed (A12: `{**table, "key": "policy.execute"}`; the malformed-value test pins the exact label with a table holding its own `key`)
- 41-03 ponytail LOW Task 1 reuse `_ScratchLayers` and the public CLI fixture: fixed (tests reuse `_ScratchLayers` and the call shape of `test_render_toml_cli_holds_the_lock`)
- 41-03 ponytail MEDIUM Task 2 carry one answer across the order retry: fixed (A11)
- cross-plan MEDIUM R3 blocked-lane case split between 41-04 and 41-10: deferred (to 41-10, per B4)
- cross-plan MEDIUM linked-worktree fixture not exercised: deferred (to 41-07)
- cross-plan MEDIUM full unit and arch groups after each wave not in the orchestrator steps: deferred (to the orchestrator; not named in the fix brief for batch A)

#### Batch B (41-04, 41-05, 41-06)

# Dispositions, batch B (41-04, 41-05, 41-06), review cycle 1

- 41-04 HIGH fallback not wired through fix rounds and resume: fixed (Task 2 `_emit_or_fallback` plain-resolution guard: `--fix-round` >= 4, non-empty `--escalation-excluded-keys-json` or new `--no-fallback` -> today's output, no jev, no stderr line; Task 3 SKILL.md Step 3 "Session fallback" branch before the escalation and native rules, widened session-model sentence (F1), escalation.md "When it applies" sentence, escalation re-run block passes `--no-fallback`, state-management.md pinned-fallback and owner-named sentences; tests round-four, escalation-keys, owner-named-pair refusals) [B1, F1, F2]
- 41-04 HIGH project file can assert the owner-only opt-in: rejected (fallback stays in the owner's own session: no external CLI, no new process, no secret; trust.py guards executable commands, not policy values; spec-config writes the project-local file by default). Threat-model sentence added to T-41-11; recorded MEDIUM for the owner [B2]
- 41-04 MEDIUM jev resolves settings from the wrong project: fixed (Task 2 binds `functools.partial(deps.run_fn, cwd=args.cwd)`, the `skill_classify.classify` pattern; tests assert the recorded `cwd`) [B3]
- 41-04 MEDIUM fake-lane matrix does not prove its backstops: fixed (Task 2 adds the real narrowing to `no_candidate` with the flag on, fake route renamed `subprocess`, "blocked" test renamed to a sole quota-out lane; boundary truth names 41-10 for the sole blocked-until lane) [B4]
- 41-04 MEDIUM sole blocked pool with the fallback on: deferred (41-10, its fake blocked reader) [B4]
- 41-04 LOW lint-failing imports and wrong header anchor: fixed (Task 1 imports only what its tests use; Task 2 adds `io` and `redirect_stderr`; header anchor quotes the `sys.path.insert` bootstrap lines, no `_REPO_ROOT`) [B5]
- 41-04 ponytail LOW hand-built item vs `class_item`: fixed (Task 1 and the D-03 truth say the hand-built item is the locked contract and why `class_item` is not called) [B6]
- 41-04 ponytail MEDIUM policy should come from the same authorized resolution as the roster: rejected (the fallback branch reads the same merged `cfg_resolve_quiet` view the roster resolution uses, only after every lane is out; threading it through the candidate assembly would widen that signature for no behaviour change)
- 41-04 ponytail HIGH Step 2 pointer not enough; stale "only way" sentence: fixed (Task 3 Step 3 branch replaces the Step 2 bullet; config-check.md names both ways without typing the key, so 41-12's single-home check still holds) [B1, B7]
- 41-05 MEDIUM tracer does not exercise the production path: fixed (Task 1 `TestDispatchPath` enters through `cli.main(["dispatch-task", ...])` with real `dispatch_superpowers_task` and `dispatch_execute`, fakes only tooling, `compose_fn` and `runner_fn`, asserts both blocks once each and in order in `runner.call_args.args[1]`) [B8]
- 41-05 MEDIUM missing files and special-character paths undefined: fixed (`_read_optional(flag, path)`, `_owner_config_paths`, `_guidance_inputs`; exit 2 with `ai-kit-spec: <flag>: unreadable file <path>` / `ai-kit-spec: --owner-config: unsupported path <path>` in both `dispatch-task` and `print-guidance`; tests for each) [B9]
- 41-05 MEDIUM Task 1 exceeds the file budget: fixed (Task 1 stays at 5 paths besides the two generated listings; the braces, tail-grep and neutrality backstops moved into Task 1; old Task 3 dropped) [B10]
- 41-05 LOW neutrality claim broader than the test: fixed (truth and test name only ai-kit's new framing with neutral inputs) [B11]
- 41-05 ponytail MEDIUM test-only fake composer bypass: fixed (uses the `tests/test_compose_for_lane.py` capture seam) [B8]
- 41-05 ponytail LOW Task 2 should reuse builders and one error path: fixed (`print-guidance` reuses `_guidance_inputs` and the builders) [B9]
- 41-05 ponytail LOW Task 3 separate lane: fixed (merged into Task 1) [B10]
- 41-06 HIGH native instructions drop the guard: fixed (Task 1 one input recipe in SKILL.md Step 3 for both branches, native print block passes `--gates-file`/`--guard-file` when present and `--owner-config` always; fresh-start write, stale-file delete, fix round/quota wake/pinned resume reuse) [B12]
- 41-06 HIGH uniformity test bypasses the controller flow: fixed (Task 2 runs the documented native and Dispatch blocks and the real Restore block against a recording stub shim, replays the argv in-process through the real dispatch layers, guard-present case, exit codes and exact capture counts; tasks reordered so the docs land first) [B13]
- 41-06 MEDIUM no-task check reads docs, not the final prompt: fixed (Task 2 asserts no `<task` in the replayed final prompt; docs say caller text with a task tag would be counted and the owner-config line is an instruction, not enforcement) [B14]
- 41-06 LOW Task 2 leaves details open; shell text beside the shell rule: fixed (names `test_no_block_pastes_json_into_a_command` and that no test edit is allowed; shell lines labelled Markdown file content) [B15]
- 41-06 ponytail HIGH three handcrafted invocations: fixed (record-then-replay of the documented blocks, Restore fixture reused) [B13]
- 41-06 ponytail HIGH duplicated gate selection, missing guard: fixed (one recipe in SKILL.md, Compose points to it) [B12]
- batch HANDOFF placeholder `<plan base>`: fixed (each plan's Task 1 step 0 records `git -C . rev-parse HEAD` with the file-write tool into its scratch folder; verification diffs from that SHA against `files_modified`) [B16]
- batch HANDOFF `make check-dogfood` orchestrator-only: fixed (each verification marks it "orchestrator only")
- batch HANDOFF evals "pass" vs shape evidence: deferred (41-01 per A3, closing evidence in 41-14)
- batch HANDOFF 41-07 intermediate red dogfood: deferred (41-07, not in this batch)
- batch HANDOFF EXEC_PREAMBLE owner question: deferred (41-14 per B17)

#### Batch C (41-07, 41-08, 41-09, 41-10)

# Batch C dispositions (cycle 1)

- 41-07 HIGH git ceiling can turn off the guard inside the checkout: fixed (C1: truths, Task 1 action step 1 walks to the first `.git` entry, no environment variable; Task 1 and 2 cases set no ceiling; new acceptance pin on the `.git` line; threat rows T-41-30/32)
- 41-07 HIGH mixed native/cross-AI sequence is not automatic: fixed (C2: 41-07 `autonomous: true`, Tasks 1-2 only; Task 3 moved to 41-08 Task 1; window rule in the objective, truths, verification and orchestrator steps of both plans; exact expected dogfood problem line named)
- 41-07 MEDIUM timing verification does not enforce the budget: fixed (C3, in 41-08 Task 1: scratch `shard_secs.py` fails on a missing, duplicate or over-60 s module and prints `recorded change:` lines; `E2E_RECORDED_SECS` refreshed only then; shard modules regenerated only when `tests/cross_ai_selftest.py` reports a changed count)
- 41-07 ponytail Task 1 MEDIUM no git-discovery exception in the guard: fixed (C1: detector reads no `GIT_CEILING_DIRECTORIES`)
- 41-07 ponytail Task 2 LOW reuse the fixture-cwd pattern: fixed (Task 2 reuses `c.cwd`, the `host-overlap` repo lines and the `pure-lock-root` worktree line)
- 41-07 ponytail Task 3 MEDIUM re-record yes, regenerate no: fixed (41-08 Task 1 step 3; no shard regeneration unless the declared count changes)
- 41-07 K3 linked-worktree self-test case: fixed (Task 2 case `realhome-exec-linked-worktree`, real `git worktree add`, checks `.git` is a file)
- 41-08 HIGH one-commit guarantee stops before the fold: fixed (C4: named handoff `post-fold runner-version agreement` in truths and orchestrator steps; fix planner D writes the step into 41-14)
- 41-08 MEDIUM dogfood helper and rollback implicit: fixed (C5: Task 1 step 2 writes `dogfood.sh` before any call; Task 3 step 1 before-commit rollback per 39.1-11, step 5 reverts the SHA in `render-commit.sha`, after a fold the folded commit found by subject)
- 41-08 ponytail Task 1 LOW file count justified: rejected (no change needed; the reviewer endorses the existing writers)
- 41-08 ponytail Task 2 MEDIUM reuse ensure_runner, add helper and fold check: fixed (same as C4/C5; no new renderer)
- 41-08 K2 "17 hits in total, goldens included": fixed (truth and Task 2 step 1; recounted at HEAD: 17)
- 41-09 HIGH audit I/O can stop, miss or invent: fixed (C6: `snapshot` catches `OSError`/`ValueError` and never raises; external path `try`/`finally`, no return in `finally`; `--snapshot` write failure and any unusable `--compare` snapshot print the `audit unavailable` observation and exit 0; exact ten-key int-or-null check; abspath for a bare filename; native recipe uses a fresh `host-config-before.json` per dispatch and removes it; tests for write failure, incomplete snapshot, raising dispatch)
- 41-09 MEDIUM existing fake dispatches without a scratch HOME: fixed (C7: Task 1 step 4 names `TestDispatchSuperpowersTask` and every `SuperpowersDispatchSeams(` in tests/test_dispatch_guidance_gates.py (`TestDispatchPath`, `TestGuidanceUniformity`); AST `seams_check.py` gate; both files added to `files_modified`)
- 41-09 LOW test setup not mechanical: fixed (C8: fixed ns mtimes via `os.utime(path, ns=(t, t))`, exact imports, `_ScratchHome` base with `addCleanup`, `Path` import named; relay placed at the common post-dispatch point before `## Classify`, pinned by an order test)
- 41-09 ponytail Task 1 MEDIUM finish existing fake callers in the same task: fixed (C7, Task 1)
- 41-09 ponytail Task 2 MEDIUM exact shape validation and write-failure behaviour: fixed (C6, Task 2)
- 41-09 ponytail Task 3 LOW pin order and failure behaviour: fixed (Task 3 docs tests pin snapshot < compare < rm and section before `## Classify`; SKILL.md edit adds no line per the orchestrator's cap note)
- 41-10 HIGH excluded lane consumes the expired pool's retry: fixed (C9: `_blocked_pool_quota` passes only ladder keys still among the excluded-filtered candidates and spawned by `probe_keys`; raw entries from the same config read via `"roster_entry"`; native and excluded lanes never take part)
- 41-10 HIGH 41-11 handoff does not prove a quota-only switch: fixed (C10: 41-10 Task 2 adds `dispatch_injection.quota_evidence` with a table test including transient 69/75 results the classifier calls quota/quota_cycle; 41-11, already revised by fix planner D, calls it from `executor-fallback --dispatch-result` with the four boundary tests)
- 41-10 MEDIUM fixture cannot prove "once"; config resolved twice: fixed (C11: fixed clock `CliDeps.clock_fn`, two flagged lanes in one pool, excluded first lane, stale cache entry; asserts one reader call, dropped stale entry and the pick; `_execute_lanes`/`execute_lanes_fn` removed)
- 41-10 MEDIUM cross-AI tasks leave choices to the executor: fixed (C12: Task 1 names the one-argument `runner_flags(spec)` and observes `--pool` through the `ExecuteSeams(runner_fn=..., compose_fn=...)` seam; Task 3 gives the exact `_resolve` signature and imports; each task stays at 3-4 paths besides listings)
- 41-10 ponytail Task 1 LOW reuse pool helpers and fake runner: fixed (C12)
- 41-10 ponytail Task 2 LOW defaulted role is right: rejected (no change needed)
- 41-10 ponytail Task 3 HIGH give the helper only tryable keys, one roster read: fixed (C9)
- 41-10 K4 copy the existing candidate fixture shape: fixed (Task 3 `_resolve` runs the real `assemble_candidates` over a fake resolved config, the `test_purpose_field_is_threaded_through_from_config` pattern)
- 41-10 B4 sole blocked pool with session fallback on: fixed (Task 3 `test_sole_blocked_pool_with_session_fallback_runs_native`, 41-04's on-disk config fixture, non-Claude env, no `--no-fallback` flag)

#### Batch D (41-11, 41-12, 41-13, 41-14)

# Batch D dispositions (review cycle 1, referee-one)

- 41-11 HIGH transient capacity failure can authorize a switch: fixed (D1/C10: `executor-fallback --dispatch-result "$DISPATCH_BASE.json"`; `fallback_outcome` switches only on `status.status == "quota"` or `reason == "quota"`; tests for real quota 69/75, transient 69/75 (classes quota/quota_cycle asserted), unflagged, no fallback; truth 1, Task 1, T-41-41)
- 41-11 HIGH failed replacement lookup can corrupt the pin or schedule the old wait: fixed (D2: switch block writes only `SWITCH_INJECTION_JSON.json`, validates mode and key, then moves it and binds mode/key/runtime together; every other outcome removes the temp files and keeps the original classification and injection; no `|| true`; permanent exclusions never cleared; fake-flow tests for six failure shapes and the success path; Task 2 steps 2 and 6, T-41-61)
- 41-11 HIGH caller's hard rules and wake path still forbid the new behaviour: fixed (D3: NEVER bullet ends with one exception sentence linking `references/resolution-stops.md#owner-stop`, both pinned sentences kept; same-round ban gains the exception; flagged switch is the first item of `## Owner stop`; quota wake keeps its pinned sentence, adds the exception and binds `BRIEF_FILE` from `REPORT_FILE` (first option, no fifteenth placeholder); each pinned in a test; Task 2 steps 3-6)
- 41-11 MEDIUM candidate selection and task eligibility use different sets: fixed (D4: `--exclude-keys-file "$RUN_DIR/EXCLUDED_KEYS_JSON.json"` passed as `exclude`; a task-narrowing mismatch fails the key check and falls back to the original handling; test with an excluded key)
- 41-11 MEDIUM avoidable migration and eager routing on refusal paths: fixed (D5: one `cfg_resolve_quiet` read, no `assemble_candidates`; `lane_switch.lazy_routes(config, deps, routes_fn=...)` over the adapter's `_routes_for`; tests assert no router call on the three refusals)
- 41-11 ponytail MEDIUM Task 1 second config read and eager routing: fixed (same as D5)
- 41-11 ponytail HIGH Task 2 state transitions in prose: fixed (deterministic block mirroring the owner-named recipe minus clearing permanent exclusions, run by fake-flow tests)
- 41-11 ponytail LOW Task 3: fixed (kept the `EXCEPTION` pin and `SWITCH_RE`; Task 3 also takes D6/F3)
- 41-11 suggestion reconcile spec-config "no run reads it yet": fixed (D6/F3: free-lanes.md and both config-file.md definitions rewritten, wizard questions unchanged, new pin `test_usage_limited_names_its_readers`; Task 3)
- 41-11 (found while fixing) `printf 'SWITCH_JSON=%s'` would fail `test_no_block_pastes_json_into_a_command`: fixed (answer kept in `$RUN_DIR/SWITCH_JSON.json`, scalar `SWITCHED` only)
- 41-11 A1 note (flagged switch first in the `## Owner stop` decision list): fixed (Task 2 step 3; the subcommand literal stays out of resolution-stops.md so 41-12's single-home pin holds)
- 41-12 MEDIUM two evals have no explicit files list, scripted outcomes unspecified: fixed (K1/D7: exact `files` for all four evals; each prompt names the faked calls and their scripted responses; the "never replaces an available lane" assertion removed from the all-unavailable eval and left to `tests/test_adapter_session_fallback.py`; reverse-fixture check step)
- 41-12 MEDIUM Task 2 rg needs `-e`, command-name pins miss duplicate rules: fixed (D8: extends 41-01's `MARKERS`, `RULES`, `LINKS`, `HOMES` through `docs`/`marker_files`/`rule_files`/`link_problems`; rule sentences picked by a mechanical rule, never a command name alone; every `rg` fragment uses `-e`; `_files_naming`/`HOMES` dict dropped; non-vacuity for a second file and a second copy in the home)
- 41-12 MEDIUM README promises more than the caller does: fixed (D9: gates and guard "when the caller supplies them"; real-home guard on exec lanes the runner spawns inside an ai-kit checkout, native calls not covered). The native `--guard-file` handoff itself belongs to 41-06 (batch B), not changed here
- 41-12 suggestion record EXE-05 and EXE-09: fixed (D10: frontmatter requirements and a truth)
- 41-12 ponytail MEDIUM Task 1 reuse scratch prompt: fixed (prompts reuse the `precise-config-active-never-asks` set-up)
- 41-12 ponytail MEDIUM Task 2 reuse 41-01 helpers: fixed (D8)
- 41-12 ponytail LOW Task 3: fixed (one qualified sentence in the existing row)
- 41-13 HIGH copied driver fails before paid work starts: rejected as stated, gate added (recorded run `python3 tmp/p41-review/c1/fix-D/probe_checks.py`: `has RUN skills.txt: True`, `has RUN skills.r1.txt: False`, stale counts 1 and 1, so `checks()` passes on `tmp/judge-40/check.py`; the docstring holds `skills.r1.txt` but not `RUN / "skills.r1.txt"`). D11 applied as: `round scope: ok` and exit 0 required before any ping or judge, a failure is an owner question, `checks()` never edited to pass (Task 1 step 2, truth "Preflight")
- 41-13 HIGH inherited round-one handling allows a failed referee to launch: fixed (D12: per-key `ping judge-referee-<x>: ok|fresh` lines gate every launch in every round, pool, third lane and count-one advisory lane; failed three -> Opus substitute; failed one/two -> owner, no successful round recorded; truth, step 5, acceptance)
- 41-13 MEDIUM code-review handoff has no producer: fixed (D13: precondition names the orchestrator's code review and ponytail review with fixes committed and `p41-13 reviewed: <SHA>` in the ledger; orchestrator step between 41-12 and 41-13)
- 41-13 MEDIUM Task 2 mixes acceptance with diagnostics: fixed (D14: verdict only from `closing.sh` `--gate`; read_first names `prior_worst` and `bar_with_base`; dogfood gate = exit status plus `check-dogfood: ok`, stale-digest lines are notes; "base" figures dropped; conditional skill and test paths in `files_modified`)
- 41-13 MEDIUM mtime evidence does not mitigate disclosure: fixed (D15: T-41-47 relabels the audits as write-observation evidence, not a confidentiality control)
- 41-13 ponytail HIGH Task 1 stale self-check, ping outcomes: fixed (D11 gate, D12 per-key lines)
- 41-13 ponytail MEDIUM Task 2 parallel scoring, files_modified: fixed (D14)
- 41-14 HIGH scratch fallback fixture has no routable fallback: fixed (D16: fresh synthetic inventory with `codex` installed and both placeholder models plus the current runner fact; tripwire still zero)
- 41-14 HIGH escalation-gate takes JSON text, not a filename: fixed (D17/A5: `--injection-file`; `render-toml --json-config <file> --out <file>` spelled out with the parsed `[lanes.policy.execute]` table checked via `tomllib`; every exit tied to a named invocation a, b1, b2, c1, c2, d1, d2, d3, e1, e2; check (d) uses `--dispatch-result` and `--exclude-keys-file` with quota and transient files)
- 41-14 MEDIUM every shard ran needs an expected set: fixed (D18: expected set from `tests/cross_ai_selftest.py` `SHARD_COUNTS` loaded by path (the script itself prints only a usage line without `--record-times`); missing, duplicate, undeclared or skipped shard reports fail)
- 41-14 MEDIUM route back to judge evidence after a suite fix: fixed (D19: `judge_loop.py check --require-current` through `digests.sh` before any re-run; a newly stale skill goes to 41-13's judge path or the owner)
- 41-14 MEDIUM requirement checklist overstates the evidence: fixed (D20: each line names its evidence kind; controller transitions are doc contract plus unit evidence; evals transcript-assessed; guard test proves the print command)
- 41-14 MEDIUM owner handoff does not reach closeout: fixed (D21/B17: "Owner handoffs" SUMMARY section with the `EXEC_PREAMBLE` question and the open-gsd note, required by Task 3's precondition before the tick, copied into 41-VERIFICATION.md)
- 41-14 (C4) post-fold assertion: fixed (orchestrator Step 3 `post-fold runner-version agreement` with `postfold_check.py` before `ready`; names from 41-08's handoff truth)
- 41-14 ponytail HIGH Task 1 correct the input and cache fixtures: fixed (D16, D17)
- 41-14 ponytail MEDIUM Task 2 strict missing-report check with explicit shard set: fixed (D18)
- 41-14 ponytail LOW Task 3: fixed (kept; precondition gains the owner-handoffs section)
- 41-14 suggestion CLAUDE_CONFIG_DIR coverage limit of the live helper and audit: deferred (to the orchestrator's Step 2 report; no orchestrator decision named it)
- Cross-plan: code-review checkpoint between 41-12 and 41-13: fixed (41-13 orchestrator step and precondition)
- Cross-plan: R5 native guard-file handoff: deferred (to 41-06, batch B)
- Cross-plan: R6 linked-worktree case, R8 expired-pool fixture: deferred (to 41-07 and 41-10, batch C: K3, C11)
- Cross-plan: 41-07/41-08 dogfood window: deferred (to 41-07/41-08, batch C: C2)
- 41-11 (C10 alignment with batch C): `fallback_outcome` takes `quota_proven: bool`; the adapter passes 41-10's `dispatch_injection.quota_evidence(result)` (no second quota predicate, no review-side import of the adapter package)
- 41-11 (orchestrator note): the switch re-resolve passes 41-04's `--no-fallback`; SKILL.md edits extend existing lines only (line count unchanged, cap test in the verify)
- 41-14 D16 fixture: recorded run `python3 tmp/p41-review/c1/fix-D/probe_route.py` printed `fresh: True` and `routes: {'lane-a': 'subprocess', 'lane-b': 'subprocess'}` for the pinned cache
- Threat IDs: 41-11's new row is T-41-61 and 41-12's new row T-41-62, so no ID repeats across the phase (41-12 already used T-41-44, 41-13 T-41-46)

## Cycle 2 (referee-one)

### Review conditions (cycle 2)

Cycle 2 (the last; owner time rule: at most two cycles, cycle 2 reviews changed plans, here all 14, then one targeted fix
pass and no cycle 3). Reviewer referee-one, same four batches; A 459 s, B 878 s, D 994 s, C about 1300 s; every lane exit 0,
every review read and grounded in `path:line`. Prompts 287-313 KB with the cycle-1 triage (orchestrator decisions and
dispositions) inlined. Plan checker re-check after the cycle-1 fix: 0 blocker, 0 warning, 1 info. Orchestrator decisions
for the targeted pass: `tmp/p41-review/c2/fix-brief-A.md` (G1-G10), `-B.md` (H1-H10), `-C.md` (L1-L12), `-D.md` (J1-J17);
four opus fixers applied them; dispositions follow. Concerns not fixed in this pass stay open below with their severity.

### referee-one

#### Batch A (41-01, 41-02, 41-03)

#### 41-01

##### Summary
The plan puts resume and stop decisions in the right files, preserves the no-config entry check, and frees room under the 300-line cap. But the proposed edits still leave competing instructions for when to read the stop reference and what to do after dispatch. One of those edits also breaks a literal handoff to 41-11.

##### Strengths
- The pinned-resume move keeps the existing Restore code and leaves the pasted quota-wake prompt intact. The existing tests exercise Restore against scratch state and pin the wake prompt’s setup order. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:123–128`; `tests/test_ai_kit_spec_superpowers.py:3363–3375,3434–3458`)
- The new check resolves sibling-relative links and counts duplicate occurrences within a file, not just across files. The verification also distinguishes eval shape from behavior and adds the no-config chain tests. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:28–30,129,134`; `tests/test_spec_chain_text.py:222–240`)

##### Concerns
- **HIGH — Step 2’s load restriction conflicts with the new stop authority.** Task 3 retains “Do NOT load it for any other mode,” while Task 2 requires the same reference after a failed native or external dispatch. An external lane can resolve with clean stderr and then fail at dispatch. Also, the new `ok` decision sits in a reference the successful path is told not to read, and it omits the operation that records `LAST_DISPATCHED_KEY`; Classify still has its own complete `ok` decision and a separate `real_error` stop. The phrase-count test can pass with those copies intact. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:163–173,208`; `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:119–135,206–212`)
- **HIGH — Task 1 removes the text 41-11 needs to qualify.** The new quota-wake paragraph drops “it does not pick another candidate.” Plan 41-11 explicitly replaces that fragment to add the flagged-lane exception. Its executor will arrive at a missing anchor. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:126`; `skills/ai-kit-spec-execute-superpowers/references/quota-wake.md:49–54`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:156,175`)
- **MEDIUM — The link test validates links it finds, not all the links the plan requires.** `LINKS` checks SKILL.md only; deleting the quota-wake or escalation reference’s pointer leaves `link_problems()` nothing to reject. Task 3 also leaves the empty-anchor stop spelled out in SKILL.md and `escalation.md`, in addition to the new home. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:129,204–208`; `skills/ai-kit-spec-execute-superpowers/references/escalation.md:43–49`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:223–228`)

##### Suggestions
- Scope the load restriction to the **Step 2 mode check**. Make Classify route outcomes to one decision list, with links back to the existing mechanics. Keep the successful path’s scalar write, resume-state clear, and stdout-only status read in that order. Move the empty-anchor decision and its pin; leave only the owner-pick mechanics in `escalation.md`.
- Pin each required source-to-home link and make the quota-wake handoff use a sentence that survives 41-01. Keep the pasted wake prompt unchanged until 41-11.

##### Risk Assessment
**HIGH before dispatch.** These are reversible Markdown edits, but they govern unattended control flow. A green marker test would not catch the competing instructions or the broken downstream anchor.

##### Ponytail findings
- **MEDIUM — Task 1:** Needed for D-01. Reuse Restore and the existing config-before-start test; extend that test to include resume order instead of adding a second ordering scanner. The lane touches seven non-generated paths plus two listings that trigger the full unit/arch hook; keep the pin edits explicit rather than asking it to repair unnamed failures. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:112,128–130`; `tests/test_spec_chain_text.py:228–240`; `AGENTS.md:186–202`)
- **HIGH — Task 2:** Needed. Move the decisions, not the machinery. Reuse Classify’s status and scalar operations and the existing re-arm block; no new runtime helper is needed. (`skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:119–135,183–200`)
- **MEDIUM — Task 3:** Needed. Reuse the state writer and wake-close block. Move the old empty-anchor assertion to the home instead of keeping the old decision in SKILL.md to satisfy it. (`skills/ai-kit-spec-execute-superpowers/references/state-management.md:147–186`; `skills/ai-kit-spec-execute-superpowers/references/session-wake.md:56–71`; `tests/test_ai_kit_spec_superpowers.py:3652–3655`)

#### 41-02

##### Summary
The candidate helper implements the locked direction and flag rules, and the scheduled installed-layout call uses the new file-based CLI. The plan is not ready for unattended execution: Task 1 prescribes a test helper that breaks unittest, and Task 2 adds a gate check without defining how the shared owner-directed paths use it.

##### Strengths
- The helper reuses `lane_escalation` and `escalation_target` rather than duplicating the kind rules. Task 1 extends the AST allowlist with the new reader and plans a real-resolver test for a lane added since the ladder was saved. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:124–128`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:110–113,170–184`; `tests/test_lane_settings.py:235–267`)
- The gate now takes an injection **file**, so the existing JSON-on-argv guard can stay unchanged. The floor-block test still executes the documented block, and 41-14 names both required file/directory flags. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:160–165`; `tests/test_ai_kit_spec_superpowers.py:3425–3432,3740–3755`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:95`)

##### Concerns
- **HIGH — Task 1’s test module cannot pass as specified.** `TestEscalationGateCli.run(key, injection_file)` overrides `unittest.TestCase.run(result)`, so unittest calls the helper with the wrong arguments before running a test. The prescribed imports also include `re`, `shutil`, and `subprocess`, first used by Task 2; Ruff’s unused-import rule applies to tests. Finally, copying just the roster *path* is not enough: the cited fixture explicitly creates its parent directory before writing it. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:128–133,165`; `tools/run_unittest_parallel.py:512`; `pyproject.toml:34–48`; `tests/test_role_orders.py:34–44`)
- **HIGH — The final allowed-key check has no defined owner-directed path.** It applies to every real candidate in the shared re-resolve section and reads `ESCALATION_ALLOWED_JSON.json`, but the explicit owner pick after a missing anchor and the owner-named replacement recipe write only the exclusion file. A valid owner pick can hit a missing or stale allowed file; the earlier gate result is also absent, so there is no `escalate` value to drive the new prose. The proposed check test pre-seeds the file and cannot catch either case. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:159–165`; `skills/ai-kit-spec-execute-superpowers/references/escalation.md:43–49,71–109`; `skills/ai-kit-spec-execute-superpowers/references/state-management.md:253–266`)
- **MEDIUM — The file boundary still has uncaught error paths.** `_read_injection_file` checks that `ladder_keys` is a list, not that its entries are strings; malformed entries can reach `set()` or sorting and raise `TypeError`. A failed output write can likewise escape as `OSError`, leaving one of the two files updated. The CLI wrapper only handles `ConfigError`. Separately, the invalid-flag fixture leaves the diagnostic for the lane to discover, even though normalization preserves the flag and `_bool_setting` defines its exact message. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:125–128`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:498–505`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:153–180,792–803`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:96–113`)
- **MEDIUM — The no-target stop text and the wizard still describe broader behavior than the gate.** The old “cannot honor the capability bump” branch remains the stop explanation when the gate returned `off` or `no-target` and the anchor is unavailable. Separately, Task 3 retains the wizard’s per-role question but describes the *execute adapter’s* action as though it also applies to review lanes. A review-only roster with two lanes gets a consent question for a move the review path does not make. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:204`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:160–163,194–197`; `skills/ai-kit-spec-config/references/wizard-flow.md:71–73`; `skills/ai-kit-spec-review/references/cross-ai.mjs:2071–2074`)

##### Suggestions
- Name the helper `invoke_gate`, create its scratch directories explicitly, and add imports in the task that uses them. Assert the exact malformed-flag diagnostic and test a bad ladder element and an unwritable output destination.
- Define the final check per caller: the current gate’s allowed set for automatic escalation, and the owner’s exact named key for an explicit choice. Exercise gate → re-resolve → check in one fixture, including a stale allowed file on the owner-directed path. Use the existing Bash block extractor and scratch fixture rather than adding another one.
- Explain an unavailable **kept lane** as such in `## Owner stop`; reserve the capability-bump explanation for an attempted bump. Scope the wizard wording to execute behavior and distinguish review’s recorded-only flags.

##### Risk Assessment
**HIGH.** A prescribed test fails at collection/execution time, and an owner-authorized recovery can stop on state that only the automatic gate writes.

##### Ponytail findings
- **MEDIUM — Task 1:** Needed for D-02. Keep the shared flag and kind helpers; repeated scans are not a material cost for a personal roster. Reuse the existing scratch roster pattern and prioritize runnable CLI tests over separate helper-only cases if the five non-generated paths plus the full hook strain the lane budget. (`skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:129–139,170–184`; `tests/test_role_orders.py:24–47`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:112,124–129`)
- **HIGH — Task 2:** Needed; a gate that prints an answer is not enough. Reuse the existing exclusion channel, owner-key equality check, and `_ref_block`/scratch-Bash test pattern. The missing piece is the caller-specific check, not a second resolver or another shell-test harness. (`skills/ai-kit-spec-execute-superpowers/references/state-management.md:261–267`; `tests/test_ai_kit_spec_superpowers.py:3387–3423,3493–3518`)
- **MEDIUM — Task 3:** Needed. Keep the existing wizard step and phrase tests; distinguish what the execute adapter acts on from what the runner records. No extra wizard step or runner change is needed. (`skills/ai-kit-spec-config/references/wizard-flow.md:67–77`; `tests/test_spec_config_flow_text.py:151–157`)

#### 41-03

##### Summary
The storage slice is small and uses the existing atomic writer. The same-target replacement test and order-retry rule address the earlier findings. The remaining gap is explaining and testing what “off” means with both config layers present, and making the unattended wizard’s yes/no behavior visible in its own verification.

##### Strengths
- The flag stays out of `LANE_FLAG_KEYS`; the reader reuses `_bool_setting` and fixes the diagnostic label after expanding the table. The writer filters one key without changing the CLI’s lock and atomic publish path. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:102–104`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:96–100`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:1123–1152`)
- Task 1 tests replacement on the same file and preserves `[skills.roles]`; Task 2 keeps the answer on an order retry. The existing checkout-supplied-policy risk is explicitly recorded under the accepted A10 disposition; this review does not reopen that decision. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:104,134,171`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:1073–1094`)

##### Concerns
- **MEDIUM — The revocation test proves removal in one layer, not that the effective flag goes off.** The fixture rewrites only the user file. In `global-merge`, the project’s execute policy table replaces the user’s when present; if a project rewrite omits that entire table because it has no execute lane, the user table can supply `true` again. Conversely, removing a user opt-in cannot clear a project `true`. The plan’s “resolve then reads False” and wizard’s “no or skip writes nothing” should distinguish what was saved from what the adapter will read. This does not require changing the locked true-only format or trust policy. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:22–25,104,134–135`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:694–706,1040–1062`; `skills/ai-kit-spec-config/references/config-file.md:5–14`)
- **MEDIUM — The wizard checks cannot distinguish consent from copying the example.** Task 2 puts `true` in the primary JSON example and checks that the literal exists, but does not pin the nearby instruction to omit it on no/skip. The headless “Questions it would ask” list also omits the new question. The existing PTY suite is correctly left as a regression check; it does not exercise either wizard instruction. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:134–148,177`; `skills/ai-kit-spec-config/SKILL.md:352–358`; `skills/ai-kit-spec-config/references/headless.md:5–19`; `tests/test_spec_config_flow_text.py:251–300`)

##### Suggestions
- Keep the single-layer replacement test and add a two-layer case using `_ScratchLayers.write_user` and `write_project`. Document that removal revokes the setting in the file being written, while effective policy follows the existing layer rules.
- Pin the yes-only qualification next to the JSON example and add the fallback question to the headless list. Use a spec-config eval or existing transcript-assessment path to check yes, no/skip, and an order retry against the JSON the wizard would submit.

##### Risk Assessment
**MEDIUM.** The write mechanism is sound on inspection. The principal risk is reporting the fallback as off when another layer still enables it, or treating a phrase check as evidence of consent behavior.

##### Ponytail findings
- **LOW — Task 1:** Needed and lean. Use `_ScratchLayers` and the existing public CLI test pattern for the layered case; no new serializer, migration, or trust mechanism is needed. (`tests/test_lane_settings.py:270–291`; `tests/test_config_role_write.py:75–94`)
- **MEDIUM — Task 2:** Needed. Keep one question in step 9 and retain its answer on retry. Update the existing headless summary rather than adding another flow or trying to prove consent with PTY coverage. (`skills/ai-kit-spec-config/references/wizard-flow.md:67–77`; `skills/ai-kit-spec-config/references/headless.md:9–19`)

#### Cross-plan coverage and handoffs

- **Sequencing:** Waves 1–3 each contain one plan. No same-wave overlap or missing ordering edge found. The serial dependencies reach the reader consumer in 41-04, the stop-list consumer in 41-11, the doc-contract consumer in 41-12, and the CLI check in 41-14. The issues are incompatible handoff text, not parallel file ownership.
- **HIGH — Another known-red handoff:** 41-04 rewrites the exact no-ladder sentence that `test_spec_chain_text` pins. It runs that module but neither lists nor stages it for the required pin update. Fix the handoff in 41-04 rather than weakening 41-01’s chain gate. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:202,216,220–224`; `tests/test_spec_chain_text.py:411–414,435–442`)
- **MEDIUM — Wave gates are not assigned in the three orchestrator handoffs.** The validation contract requires full `--group unit` and `--group arch` after every wave. The handoffs name dogfood and the state-file cap, and the staged hook is selective on ordinary commits. Assign the full groups explicitly to the orchestrator. If B16 is intended to cover Batch A too, also assign the pre-plan SHA and changed-path check; only the downstream Batch B plans I checked implement that scope check. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-VALIDATION.md:30–35`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:247–257`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:237–247`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:176–186`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:133,262`)
- **Requirement coverage:** R1–R3 and their applicable edges have named owners; the sole blocked-pool case now has a combined fixture in 41-10. The other acceptance lines and all five prohibitions have named owners in the downstream plans and closeout. One evidence distinction remains: the original 14 evals are preserved and shape-checked, not shown to pass behaviorally. If that locked acceptance still requires execution, it needs an explicit verification owner; do not count shape or transcript assessment as execution. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:203`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:19–23`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:29–35,134`; `tests/test_skill_evals_shape.py:130–152`)

**Verdict: Revise before dispatch.** Fix the stop authority and wake handoff in 41-01, then the deterministic test failures and owner-directed re-resolution in 41-02. Clarify and test layered fallback behavior in 41-03.

Read-only review: no files changed, no tests, evals, or Make targets run. Runtime and timing claims remain unverified.

#### Batch B (41-04, 41-05, 41-06)

#### 41-04

**Summary.** The fallback belongs at the resolver’s existing no-pick exits, and the plan keeps jev advisory and off the non-Claude path. The round and owner-named-pair exclusions are now explicit. Two blockers remain: Task 3 breaks an existing test it is not allowed to update, and it introduces a second native dispatch path rather than making fallback an exception inside the existing one.

##### Strengths

- The three fallback entry points match the actual resolver: an empty post-exclusion set, a `QuotaExhaustedError`, and the specifically recognized affinity/context narrowing failure. A success or an unrelated configuration error does not enter the fallback. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:176–177`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:190–202,245–274`.
- The picker reuses the shared strict decoder, confidence threshold, and target-directory binding. The production task classifier emits only `frontend`, `backend`, `mixed`, or `None`; the outgoing context does not need task Markdown or paths. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:134,177`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:121–174`; `skills/ai-kit-spec-review/ai_kit_spec/skill_classify.py:121–128`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/task_classification.py:24–34`.

##### Concerns

- **HIGH — Task 3’s required verification cannot pass as written.** The task replaces the exact sentence in `NO_LADDER_SENTENCE`, then runs `tests.test_spec_chain_text`. That module asserts the old sentence in Step 3, and Task 3’s file list does not authorize changing the test. The earlier 41-02 edit only appends a sentence, so it does not remove this conflict. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:202,216,224`; `tests/test_spec_chain_text.py:411–414,435–442`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:163`.
- **HIGH — The fallback branch can bypass the shared native brief and lifecycle.** Task 3 says **“dispatch it natively”** before the escalation and native rules and directs restored pins through that branch “instead.” But the common brief, native agent identity, `LAST_DISPATCHED_KEY` write, and resume-state cleanup are specified later. 41-06 adds guidance to that later native branch, and 41-09 adds the audit there. The proposed text does not say to enter the common branch after skipping the bump, so an executor following the fallback branch can miss both later handoffs and the existing cleanup. The new doc test checks paragraph order, not this transition. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:216–220`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:235–253`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:102–103`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:195`.
- **MEDIUM — The refusal fixtures can pass without testing the jev boundary.** Task 2 explicitly supplies the Claude signal and patches jev discovery for the payload test, but does not require that setup for the round-four, escalation-key, and owner-named-pair refusals. With a non-Claude fixture, the picker would make no jev call even if entered. The output checks still catch a dispatched fallback, but do not prove that no advisory work was attempted. Also, existing resolver fixtures that fake candidate assembly but omit `env_fn` gain a real config read on these exits when run directly: `cfg_resolve_quiet` disables migration, not file reads. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:177–179`; `tests/test_ai_kit_spec_superpowers.py:1247–1277,1412–1436`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:89–94`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:689–691,721–730`.
- **MEDIUM — The accepted trust note understates the side effect, and the eval scripts a different notice.** T-41-11 says “no new process,” but on Claude Code this path can launch the existing jev client. That is not an external *executor* and does not reopen the rejected trust-gate decision. Separately, 41-12 scripts `fallback_note: "every execute lane is out of quota"`, which none of the four planned picker outcomes emits, and expects the controller to relay the notice without an explicit relay instruction on the successful fallback path. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:214–220,254,276`; `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:140–153`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:100`.

##### Suggestions

- Make `fallback == "session"` skip only the ladder escalation and native model bump. Then send it through the one native brief, invocation, and completion path. Preserve the saved injection on a pinned resume and explicitly relay the fallback notice on initial selection. Update `NO_LADDER_SENTENCE` in the same task and keep the no-config ask assertions unchanged.
- Give Task 2 one named scratch-roster fixture with a created config parent directory, an explicit `env_fn`, and a positive Claude control using the same fake jev as the refusal cases. That makes “no jev call” meaningful and removes guesswork from the fixture copied by 41-10.

**Risk assessment: HIGH.** The picker itself is small and bounded, but Task 3 has a deterministic verification failure and an ambiguous controller transition that affects later requirements.

##### Ponytail findings

- **LOW — Task 1:** Needed for EXE-04. Keep the small adapter-local picker and the shared `find_jev`/`ask_items` call. `class_item` already has a different job: it adds catalog criteria and a model-name prefix. `skills/ai-kit-spec-review/ai_kit_spec/jev_names.py:63–73,96–103,140–174`.
- **LOW — Task 2:** Keep the common emit helper; do not parse the exclusion JSON again. The resolver already carries the parsed set as `loaded.escalation_exclude`. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:107–129,224–230`.
- **HIGH — Task 3:** The fallback exception is needed; a second native launch recipe is not. Reuse the existing native path and keep the resume and owner-stop references as the authorities for their respective decisions. `skills/ai-kit-spec-execute-superpowers/SKILL.md:244–253`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:123,163–170`.

#### 41-05

**Summary.** The two builders and optional fields are a good fit for EXE-05. The revised tracer reaches the actual dispatch path and captures the prompt passed to the runner. The remaining problems are at the edges of the public input contract and in how the tests isolate and exercise that contract.

##### Strengths

- The composer keeps its existing section order when inputs are absent, and trailing defaults preserve existing construction. The known injected composer fakes accept extra positional arguments. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:120–122`; `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py:68–82`; `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:57–103`; `tests/test_compose_for_lane.py:84–110`.
- The tracer starts at `cli.main`, keeps both dispatch layers real, and asserts on the prompt at the runner seam rather than constructing the expected prompt inside a fake. This covers argument parsing and field forwarding without launching a host. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:124`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:346–362`; `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:139–156`.

##### Concerns

- **MEDIUM — The owner-config validator does not enforce the exact-file claim.** Task 1 rejects quotes, leading colons, and glob characters, but still accepts an empty value, `.`, and directory paths. The builder emits these as exclusion pathspecs. In particular, an exclusion of `.` can suppress the entire clean-tree check, not just a config file. The locked `.aikit/config.toml` caller is fine; the repeatable public option and threat mitigation make a broader promise. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:120,123,193`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:346–353`.
- **MEDIUM — The tracer still depends on ambient runner facts.** The real `dispatch_execute` reads a cached runner fact using `os.environ` **before** either fake composition or fake runner is reached. A direct test invocation can read the caller’s real cache, and a current fact reporting no exec formula can refuse the fixture. The plan’s instruction to stop and report that refusal is not a deterministic fixture. 41-06 repeats the same chain. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:115,124`; `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:112–125,138–145`; `skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py:63–79`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:141`.
- **LOW — The error tests do not cover the full B9 matrix.** `dispatch-task` exercises missing gates and invalid-UTF-8 guard text; `print-guidance` only exercises missing gates and a glob path. Both use `_guidance_inputs`, but a regression in the native parser’s `--guard-file` handling would not be caught by its error tests. Also, the verification block still omits the explicit **orchestrator only** label for dogfood; that check reads live project consent and invokes local GSD tooling through Node. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:34,123–124,158–162,199,206–208`; `tools/check_dogfood.py:262–265,334–346`.

##### Suggestions

- Define the supported `--owner-config` input as a nonempty, project-relative file path. Pin rejection of `.` and directory-wide exclusions, and verify that a supported path leaves unrelated dirty files visible. Keep the documented instruction distinct from enforcement.
- Isolate `HOME` and `XDG_CACHE_HOME` around the real tracer, or fake only the stored fact. Reuse the same invalid-input cases across the two subcommands where practical, including a guard-file error on the native side.

**Risk assessment: MEDIUM.** The normal path and default compatibility are well specified. The broader path contract can hide unrelated changes, and the tracer is not yet self-contained outside the parallel test runner.

##### Ponytail findings

- **MEDIUM — Task 1:** The builders and one real CLI tracer are needed. Keep the optional arguments and shared composer; no second prompt builder or runner change is needed. Put the test seam at the cached observation as well as the final spawn, not at the dispatch layer being verified. `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py:44–52,68–82`; `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:112–125,145–156`.
- **LOW — Task 2:** `print-guidance` is the locked native handoff. Reusing the builders and `_guidance_inputs` is the right size. Fill the remaining error-test gap with shared cases rather than a second validator. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:123,161–162`.

#### 41-06

**Summary.** Both command blocks now pass the optional guard file and the owner config path, and the record-and-replay fixture is stronger than manually assembling argv. The remaining blocker is when guidance inputs are first written: a real pre-dispatch quota stop can resume into the first dispatch without ever running the recipe.

##### Strengths

- The documented commands now use the same flags and preserve the existing file-backed injection and report-mode flow. The added lines do not trigger either of the actual JSON-paste checks. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:102–106`; `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:72–89`; `tests/test_ai_kit_spec_superpowers.py:3425–3432`.
- The `coverage=n/a` explanation matches the runner: it parses task blocks from the prompt and reports `n/a` when it finds none. The plan now distinguishes ai-kit’s own text from caller text and does not claim the owner-config instruction is enforced. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:104,136,142`; `skills/ai-kit-spec-review/references/cross-ai.mjs:6274–6291,6348–6355,6439`.

##### Concerns

- **HIGH — A first dispatch after an unpinned resume can silently omit both inputs.** The recipe initializes files only when `FIX_ROUND=0` **and** `RESUME_FOUND=0`. With fallback off, a recoverable quota stop in Step 2 writes a resume file before Step 3 has ever run. That state has no `injection_json`. When quota recovers, Restore sends the task through Step 2 and on to its first dispatch with `RESUME_FOUND=1`. The proposed recipe skips initialization, so both flags are omitted, or stale files from the reused task directory are passed. Task 2 pre-populates both files and tests only a state with a pin, so it cannot catch this case. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:102,141–142`; `skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md:48–55`; `skills/ai-kit-spec-execute-superpowers/references/state-management.md:69–78,173–181`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:122–128`.
- **MEDIUM — The native recipe does not stop on a print error.** Task 1 redirects `print-guidance` to `guidance.txt` and tells the controller to append it, but does not make a zero exit status a prerequisite to native dispatch. Redirection can leave an empty file when an explicit input fails. The external route returns exit 2 before launching, so the two routes can diverge on the same invalid input. The stub always exits zero. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:102–105,141–142`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:123,161`; `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:72–97`.
- **MEDIUM — Replay loses the first-dispatch input, and shell success is not shim success.** All recorded argv point at the same `prompt.txt`, which the fixture rewrites before replay. The purported first replay therefore reads the fix-round prompt. Also, Dispatch ends by writing `$?` to the `.exit` file, so a zero Bash return code can just mean that write succeeded. The action explicitly checks the file after the first dispatch only, despite claiming success for every invocation. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:135–142`; `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:72–85`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:309–322`.

##### Suggestions

- Initialize the files on the first **actual** dispatch, including a first dispatch after an unpinned resolve-time resume. Preserve existing files on fix rounds and pinned wakes. Add a fixture for the unpinned state and include the session-fallback path in the common native instructions from 41-04.
- Require successful printing before any native launch; relay a named input error through the existing stop path. Replay each external invocation before rewriting its input, assert the shim’s `.exit` value after each call, and assert the expected objective and `--report-mode` for that replay.

**Risk assessment: HIGH.** A supported resume can appear successful while silently dropping the required guidance. The current uniformity fixture cannot detect it.

##### Ponytail findings

- **HIGH — Task 1:** One recipe is needed; one keyed only to a fresh start is not enough. Use the existing Restore distinction between an unpinned continuation and a pinned re-dispatch, rather than adding another resume flow. `skills/ai-kit-spec-execute-superpowers/references/state-management.md:69–78,96–107`.
- **MEDIUM — Task 2:** Keep the real Bash blocks and fake runner. Reuse the existing block extraction and scratch-Bash pattern, and replay each call immediately. That proves more with less state to reconstruct, without pretending to execute a native host agent. `tests/test_ai_kit_spec_superpowers.py:3387–3423,3434–3458`; `tests/test_compose_for_lane.py:84–99`.

##### Batch handoff and coverage

- **No same-wave overlaps or missing scheduling edges found.** Waves 4, 5, and 6 have one plan each. The serial chain supplies the flag reader, the CLI and fixture changes, then the documented dispatch handoff. 41-07 starts after 41-06; the deliberate dogfood exception begins in 41-07, not in this batch. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:5–6`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:5–6`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:5–6`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:5–6`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:5–6,21`.
- **Coverage is assigned, but not all of it is demonstrated by these plans as written.** R3’s write/read and sole-blocked-pool backstops are assigned to 41-03 and 41-10. R4/R5’s builder and prompt checks are assigned to 41-05/06, with the resumed/native delivery gap above. The fallback-off and jev prohibitions are assigned to 41-04; the no-foreign-edit prohibition has per-plan scope checks and a closing check. 41-14 explicitly limits the native evidence to the print command and keeps the `EXEC_PREAMBLE` question with the owner. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md:102–104`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:203`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:102,134–135`.
- **Orchestrator follow-through:** The named module commands and `FAILED` signal are real, but focused gates and staged hooks do not replace the full unit and arch groups required after every wave. That previously deferred item still needs an orchestrator checkpoint; the three plan handoffs name dogfood and the state-file cap only. `tools/run_unittest_parallel.py:888–913,938–945`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-VALIDATION.md:30–35`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:269–271`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md:206–208`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:186–188`.

**Verdict: revise before unattended execution.** Fix the pinned test and route all native dispatches through the same preparation step, including the first dispatch after an unpinned resume.

Read-only review: no files edited, no suites or make targets run, and no live host or jev behavior claimed.

#### Batch C (41-07, 41-08, 41-09, 41-10)

#### 41-07

**Summary.** The runner change implements the refined checkout rule in the right place. The main remaining risk is orchestration: the plan states the no-checkpoint window, but does not specify how the actual execution path will honor it.

**Strengths**
- The guard is set after the runner builds the lane environment. The same environment reaches every attempt, including the hosted and headless paths; model listing stays separate. That makes this one runner change, not a requirement every caller must remember. `skills/ai-kit-spec-review/references/cross-ai.mjs:5751`, `:5997–5998`, `:5544–5546`, `:5627–5637`, `:7257–7258`.
- The linked-worktree and nested-plain-repo fixtures exercise the two sides of the first-`.git` rule. The existing harness supplies a separate HOME and fake CLI per case, and really does fail on unknown or failing cases. `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:3035–3078`, `:12177–12193`.

**Concerns**
- **HIGH — The no-checkpoint window is not wired to the executor.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:192–194` assigns two per-task launches and a direct handoff to 41-08, but does not name the driver or explicitly bypass stock wave execution for this pair. Stock cross-AI delegation sends the whole `<tasks>` section; the stock wave path dispatches `execute:wave:post`, where the installed capability registers `ai-kit-fold checkpoint`. Making both 41-07 tasks cross-AI fixes the old mixed-mode problem, not this sequencing problem. `.claude/gsd-core/workflows/execute-phase.md:439–442`, `:981–995`; `skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/capability.json:33–38`.
- **MEDIUM — The fixtures would not catch the original ceiling regression returning.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md:141–147` expressly gives every case no ceiling. Those cases can all pass if a future edit makes the guard depend on the existing `inGitTree` or `checkoutRoot` logic again: both check the ceiling *before* the `.git` entry. `skills/ai-kit-spec-review/references/cross-ai.mjs:4165–4177`, `:5307–5318`.

**Suggestions**
- Name the per-task orchestrator path, who writes and commits the SUMMARY, and the first permitted checkpoint. Make 41-07 and 41-08 one maintenance window without modifying GSD’s workflow files.
- Put the checkout root in `GIT_CEILING_DIRECTORIES` in the existing subdirectory case. Still assert that the child sees `1`; allow the runner’s separate tree check to report `tree=unknown`, as the existing non-git exec case does. `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:6307–6324`.

**Risk assessment: HIGH for execution sequencing; LOW for the guard logic itself.** The two-file tasks are reasonably sized. The intentional dogfood failure is acceptable only if the handoff actually prevents the normal checkpoint from running.

##### Ponytail findings
- **LOW — Task 1:** The env assignment and root tracer are needed for R6. Keep the small independent walk rather than reusing a Git-discovery helper with different semantics. Reuse `writeCaseFile` for the marker writes instead of repeating its mkdir/write pair. `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:2688–2692`.
- **LOW — Task 2:** The five remaining cases exercise distinct boundaries. Reuse the checked Git setup pattern so a failed worktree creation is reported as setup failure, not a guard failure. `skills/ai-kit-spec-review/references/cross-ai-selftest.mjs:2913–2922`, `:11595–11612`.

#### 41-08

**Summary.** Running the timing and live render natively is appropriate. The plan correctly couples the version bump to the rendered copy before folding, but its proposed post-fold check cannot prove that the guarded runner stays intact in published history.

**Strengths**
- The version search has **17 matches at HEAD**, including all eight goldens. The plan uses their existing writers and leaves the readiness floor at 9. `skills/ai-kit-spec-review/references/cross-ai.mjs:2–4`; `tests/fixtures/runner_describe_golden.json:935`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:23`, `:314–318`.
- The existing renderer checks both the project CONFIG and the rendered bytes, not just the header. Reusing it preserves the pristine-copy and no-downgrade rules. `tmp/run-2026-11-23/p39.1-11/render.py:127–168`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:265–289`.

**Concerns**
- **HIGH — The post-fold check misses the known red commits and can run after publication.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:234–238` hands 41-14 a check of three version numbers. A 41-07 commit containing the guarded template but an unguarded live copy passes **13 = 13 = 13**; dogfood fails because the bodies differ. The default GSD fold scopes commits by plan and preserves later commit trees when replaying them, so folding 41-08 does not repair 41-07’s tree. Also, the checkpoint can publish immediately after folding; the 41-14 check before `ready` is not a pre-push gate. `tools/check_dogfood.py:105–117`; `skills/ai-kit-commit-fold/scripts/fold_adapters.py:273–294`; `skills/ai-kit-commit-fold/scripts/fold_engine.py:397–425`; `skills/ai-kit-commit-fold/scripts/flow_unit.py:355–386`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:201`.
- **MEDIUM — Task 1 has an invalid command and an ambiguous handoff SHA.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:109`, `:118–120` requires HEAD to be the 41-07 test commit *after* the handoff through its SUMMARY, and then calls `python3 tests/cross_ai_selftest.py` to print shard counts. The normal metadata commit changes HEAD, and the bare Python command exits with usage; `shard_modules.py` already provides the list. The preflight also omits the `check_times.py` dependency of the copied `times.sh`. `.claude/gsd-core/workflows/execute-plan.md:530–547`; `tests/cross_ai_selftest.py:367–371`; `tmp/run-2026-11-23/p39.1-11/shard_modules.py:11–19`; `tmp/run-2026-11-23/p39.1-11/times.sh:9–10`.
- **MEDIUM — The post-fold rollback locator cannot match as written.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:190` searches `%s` for the full original render subject. That title alone exceeds the fold engine’s 60-character limit. The original message survives in the body, not necessarily as the subject. `skills/ai-kit-commit-fold/scripts/fold_engine.py:31`, `:239–250`.

**Suggestions**
- Require a local, pre-publication proof that compares the runner bodies outside CONFIG and checks version 14 wherever the guard ships. Name how the existing fold flow will produce that history or stop for the owner if it cannot express the combined change. Do not wait until `ready` to discover an already-published mismatch.
- Use the declared module list once, preflight its transitive helpers, and record the 41-07 task tip separately from metadata HEAD. For recovery, identify the folded commit by its fold trailer, original message in the body, and verified changed paths; do not revert on a subject match alone.

**Risk assessment: HIGH.** The live render procedure is sound in isolation. The publication and recovery steps do not yet enforce the same guarantees.

##### Ponytail findings
- **LOW — Task 1:** Recalibration is needed, but the copied `check_log.py` already parses the log, rejects missing or duplicate expected lines, and enforces the 60-second budget. Extend that one checker to compare rounded times with `E2E_RECORDED_SECS`; don’t copy it unused and add a second parser. `tmp/run-2026-11-23/p39.1-11/check_log.py:13–51`.
- **LOW — Task 2:** The wide file list is justified by the existing header, goldens and version pins. Keep the regeneration tools; no new writer is needed. `tests/test_runner_describe.py:407–413`; `tmp/run-2026-11-23/p39.1-11/plan-golden.sh:9–12`.
- **HIGH — Task 3:** Keep `ensure-runner` and the dry/live digest comparison. Fix the fold handoff rather than adding another renderer or treating a green tip as proof that every published commit is green. `tools/check_dogfood.py:105–117`; `skills/ai-kit-commit-fold/scripts/flow_unit.py:355–386`.

#### 41-09

**Summary.** The fixed file list, stdlib-only audit, deterministic mtimes and atomic snapshot writer are a good fit for R7. The remaining defects are at the failure boundaries: the proposed audit can report a false change, mask a dispatch exception, or be skipped on a native path.

**Strengths**
- Using the existing atomic writer is appropriate. Exact key and value validation rejects incomplete snapshots, and the planned `finally` reaches the after-snapshot when a dispatch raises. `skills/ai-kit-spec-review/ai_kit_spec/cache.py:15–46`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:120–124`, `:161–169`.
- Task 1 names the existing direct dispatch tests and the 41-06 replay tests that need the new scratch-HOME seam. Fixed nanosecond timestamps avoid testing against wall-clock timing. `tests/test_ai_kit_spec_superpowers.py:884–903`, `:937–945`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:129–141`.

**Concerns**
- **HIGH — Audit I/O can still invent a change or replace the lane’s exception.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:117–120` maps all stat errors to `None`, then treats a transition from a known mtime to `None` as a change. A permission or I/O error after an unchanged file was observed therefore looks like a deletion. The same `finally` performs unguarded writes to stderr; a failed write can replace the dispatch exception. The planned raising-dispatch test uses a writable `StringIO`, so it proves neither boundary. `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:176–178` confirms this stderr path is an ordinary stream write.
- **HIGH — The fixed native snapshot filename can be stale, and the fallback branch can bypass the recipe.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:161`, `:195` has the snapshot command return 0 on write failure, then tells the controller to compare the same filename. If an earlier attempt was interrupted before cleanup, a failed atomic replacement can leave that old valid snapshot in place. Separately, 41-04 tells the session-fallback branch to dispatch **before** the ordinary native rules, including on fix rounds and pinned resume. Appending the audit only to the later native paragraph does not require that branch to run it. `skills/ai-kit-spec-review/ai_kit_spec/cache.py:27–45`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:214–219`.
- **MEDIUM — Task 3 does not produce the link that 41-12 requires.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:194–196` adds the reference heading and commands but no `references/dispatch-external-cli.md#host-config-audit` link in SKILL.md. 41-12 explicitly stops if that link is missing and forbids fixing it in that task. Its eval also asks for the exact observation sentence from the audit section, which currently only specifies the prefix and paraphrases the rest. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:103`, `:134–135`.

**Suggestions**
- Distinguish a known missing/non-file path from an unavailable stat. Report the latter as audit unavailable rather than as a change; keep reporting best-effort even if the output sink fails. Test both with injected failures.
- Use one native audit recipe for every native launch, explicitly including session fallback and failed launches. Compare only a snapshot created for that launch. Add the 41-12 anchor and exact observation wording in Task 3. For external exceptions, place the relay explicitly before the empty-result stop, which already precedes Classify. `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:84–109`.

**Risk assessment: HIGH.** The ordinary success path is well specified. The proposed failure paths do not yet uphold the non-gating and truthful-reporting requirements.

##### Ponytail findings
- **MEDIUM — Task 1:** The file list, audit seam and fixed mtimes are needed. The scratch AST checker only sees explicit calls, not CLI defaults; use the real replay fixture with scratch HOME as evidence for that path. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:70–81`, `:346–362`.
- **HIGH — Task 2:** Keep `cache_read_json` and `cache_write_json`. The missing piece is a reliable outcome for this snapshot attempt, not another storage implementation. `skills/ai-kit-spec-review/ai_kit_spec/cache.py:15–46`.
- **HIGH — Task 3:** One native recipe and one linked reference are enough. Point every native branch to that recipe and test the failure handoff, not merely the order of three strings. `skills/ai-kit-spec-execute-superpowers/SKILL.md:246–253`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:216–219`.

#### 41-10

**Summary.** Pool propagation and reuse of Phase 40’s switch code are sound directions. The main defect is that the blocked-pool check and the final selection can still operate on different candidate sets. The proposed expiry fixture also stops short of exercising the production refresh.

**Strengths**
- The pool is read at the roster boundary with `lane_free_pool`, then passed to the existing runner flag builder. This keeps the flag reader in its allowlisted module and avoids a second pool parser. `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:116–126`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:236–247`.
- The saved-result handoff to 41-11 separates real quota from the adapter’s wait-or-stop classes. That distinction is necessary: the adapter groups transient 69/75 into quota-like classes while the shared reason mapper calls transient `capacity`. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:123–130`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:442–469`; `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py:39–48`.

**Concerns**
- **HIGH — A lane can re-enter the final selection without a blocked-status check.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:195–196` intersects the *pre-exclusion* `loaded.ladder_keys` with the remaining candidates. The final builder instead **reruns** narrowing on those remaining candidates. Example: for a backend task, untagged A initially wins affinity over frontend-tagged B, so B is absent from `ladder_keys`. Exclude A and the never-empty affinity rule now keeps B. The pool overlay never reads B’s record, so the picker can select B while its pool is still blocked. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:213–230`, `:245–254`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:351–363`; `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py:37–59`, `:137–149`.
- **MEDIUM — The expiry fixture does not establish “tried once.”** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:197–200` excludes one of two pooled lanes, leaves only one eligible, and replaces refresh with an identity function. It proves stale-row removal and the pick, not that exactly one eligible pooled lane is probed. In production, refresh iterates its own candidate list, and a missing quota row is treated as available. `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:174–187`; `skills/ai-kit-spec-review/ai_kit_spec/quota.py:56–62`, `:299–316`.
- **HIGH — Task 2 cannot pass pylint with the specified signature.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:153`, `:161` expands `flagged_replacement` from five parameters to six without changing the call contract or explaining how the mandatory lint gate passes. Both argument caps are five for shipped Python. This needs a planner decision shared with 41-11, not a lane-local suppression. `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:182–193`; `pyproject.toml:70–80`; `.pre-commit-config.yaml:26–31`.
- **MEDIUM — The Task 1 tracer does not fully isolate HOME.** `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:117` supplies scratch HOME to the 41-09 audit seam, but the real `dispatch_execute` still reads the runner fact from `os.environ`. The parallel runner masks this; a direct run can read the caller’s cache and make admission depend on it. The same step’s “imports exactly” list also omits `os` and `sys` required by its copied bootstrap. `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:112–124`; `skills/ai-kit-spec-review/ai_kit_spec/runner_facts.py:75–79`; `tests/test_ai_kit_spec_superpowers.py:22–25`.

**Suggestions**
- Preserve the saved full ladder for resume and escalation, but give the pool check and final pick the same **post-exclusion, task-narrowed** keys. Add the affinity re-entry case.
- Keep the excluded-first regression, then add a second case with **two eligible** peers in an expired pool. Run the real quota refresh with a fake probe and assert one pool read, one pooled probe, and no probe of the peer. Keep the sole-blocked-lane session-fallback test; it covers a separate requirement.
- Settle the five-argument interface in both plans and make the tracer independent of the caller’s cache.

**Risk assessment: HIGH.** As written, the plan can select a blocked lane, and its exact Task 2 implementation cannot clear the prescribed lint gate.

##### Ponytail findings
- **MEDIUM — Task 1:** Pool transport is needed; `_replace(pool=…)` and `runner_flags(spec)` already do the work. Make the existing dispatch tracer hermetic rather than adding another launcher. `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:153–154`; `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:245–247`.
- **HIGH — Task 2:** One shared fallback policy and one quota predicate are enough. Resolve the argument cap in the shared interface while keeping existing review callers green. `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:46–61`, `:182–193`.
- **HIGH — Task 3:** Keep the single roster read and the shared blocked-status reader. Reuse the final ranking for the pool check; don’t maintain a second approximation of eligibility or a second record parser. `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:77–98`, `:134–179`.

#### Batch handoff and coverage

- **Waves and dependencies:** No same-wave file overlap or missing plan dependency found. The on-disk chain is serial from 41-06 through 41-14. The audit-link failure is a missing artifact in an ordered handoff, not a missing dependency.
- **Coverage:** R6’s two held-out edges are assigned to 41-07, with the installed runner copy in 41-08. R7’s acceptance and edges are assigned to 41-09, with installed CLI evidence in 41-14. R8’s selection and ordering evidence is assigned to 41-10, with the quota-stop transition in 41-11. All five SPEC prohibitions have named owners; the material evidence gaps are the non-gating audit and the first eligible retry identified above. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:301–330`.
- **MEDIUM — Wave gates still need an orchestrator owner.** Validation requires the full `unit` and `arch` groups after each wave, not just targeted modules and whatever the commit hook selects. Name those runs explicitly, with the accepted dogfood exception for 41-07/08 and caller-HOME dogfood assigned only to the orchestrator. `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-VALIDATION.md:30–35`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:233–235`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md:248–250`.

**Verdict: revise before execution.** This was a read-only review of the current plans and source. No tests, make targets, live lanes, or file edits were performed.

#### Batch D (41-11, 41-12, 41-13, 41-14)

#### 41-11

**Summary.** The quota-switch design correctly separates runner-proven quota from the adapter’s broader wait-or-stop classification. It also validates a replacement in a temporary file before changing the pinned injection. The plan still has a definite CLI error-path failure and gaps in how a replacement is selected and handed back to the controller.

**Strengths**
- Task 1 reuses 41-10’s quota predicate and the existing role-order and different-pool rules. That distinction matters: a transient exit 75 can classify as `quota_cycle` without being quota evidence. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:123–131`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:442–469`; `skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py:146–167`)
- Task 2’s temporary lookup addresses the original pin-overwrite defect for failed or nonmatching resolver output. The tests exercise the documented Bash block, not a copy of it. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:170–181`; `tests/test_ai_kit_spec_superpowers.py:3387–3423`)

**Concerns**
- **HIGH — The promised exit-2 tests cannot pass as specified.** Task 1 constructs `ConfigError` with one argument. Its constructor requires `path` and `message`; the resulting `TypeError` is not caught by the adapter’s `main`. Both invalid-input cases therefore miss the named diagnostic. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:125–131`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:309–322`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py:498–505`)
- **HIGH — The first routable fallback can hide a later eligible one.** Task 1 selects from the live role roster without the task’s narrowed candidate set. Task 2 then forces that single key and returns to the original stop if it cannot resolve. For example, with failed A, context-ineligible B, and eligible C in role order, B can route successfully, fail the forced lookup, and prevent C from being considered. The key check prevents a wrong dispatch but does not deliver the first eligible fallback. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:125,172–173`; `skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:46–61`; `skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py:62–66,137–149`)
- **HIGH — A successful switch is not yet a reliable controller transition.** The block sets `SWITCHED=1` even if `mv` or the following state write fails. Its success paragraph also sends a native replacement to the generic Step 3 native path, which resumes the prior agent in rounds 1–3; a failed external dispatch supplies no native agent to resume. The success fixture covers only a writable filesystem and an external replacement. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:172–181`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:246–258`)
- **MEDIUM — Two caller instructions still contradict the switch.** Task 2 updates the top-level NEVER and wake text but not `escalation.md`’s unconditional “a failed dispatch stops” in the same round. Task 3 widens section 8 of the cross-AI contract while explicitly leaving section 6’s review-only precedence unchanged. The adapter tells the controller to read both sections before acting. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:152–176,215`; `skills/ai-kit-spec-execute-superpowers/references/escalation.md:30–38`; `skills/ai-kit-cross-ai/SKILL.md:297–302,358–362`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:41–43`)
- **LOW — The scope-check setup does not reach the coding lane.** The base-SHA write is only in `<context>`, and the closing check uses a prose placeholder. The task receives neither. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:94–101,122–132,256–257`)

**Suggestions**
- Pin the exact exit-2 diagnostic using the existing two-argument error contract or the adapter’s local validation pattern. Retain the invalid JSON and wrong-shape tests.
- Feed the task’s eligible keys into the existing ordered selector. Add an A/B/C fixture where B routes but cannot serve the task and C is selected. Keep the final key check for changes between selection and resolution.
- Reuse Classify’s existing quota fold rather than writing the same three wave files again. Require successful replacement publication before setting `SWITCHED=1`; test a failed move and a fresh native fallback in a fix round. Put the base-SHA step in Task 1.

**Risk assessment: HIGH.** The malformed-input test is blocked as written. Even after that is fixed, the current recipe can miss an available fallback or report a switch that was not published.

##### Ponytail findings
- **MEDIUM — Task 1:** The named refusal results are needed for EXE-09. Keep the lazy lookup and existing selector; give that selector the right candidate set rather than adding a second fallback walker. (`skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py:46–61,182–193,230–239`)
- **HIGH — Task 2:** The temporary pin and wake handoff are necessary. The extra wave-state writer is not: Relay already folds the failed key and reason before the switch. Use the existing fold and test the native caller as well as the external one. (`skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:143–164`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:246–258`)
- **MEDIUM — Task 3:** The spec-config and cross-AI text edits are required. Keep the existing wording tests, but make section 6 point to the same exception as section 8 rather than leaving two rules. (`tests/test_spec_config_flow_text.py:79–81,228`; `tests/test_lane_failure_text.py:201–203`; `skills/ai-kit-cross-ai/SKILL.md:297–302`)

#### 41-12

**Summary.** The four scenarios, explicit fixture lists, and reuse of the single-definition test module are the right scope. However, Task 2 depends on an anchor no preceding plan writes, and several scripted eval responses do not match the contracts the controller will actually read.

**Strengths**
- The fixture lists are explicit and use the existing scratch-project convention. The shape test really does reject an unlisted fixture; it is not presented as a behavioral run. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:95–108`; `skills/ai-kit-spec-execute-superpowers/evals/evals.json:104–107`; `tests/test_skill_evals_shape.py:71–94`)
- The README change stays in the existing row and now qualifies both caller-supplied guidance and the runner-spawned real-home guard. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:155–165`; `README.md:37`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:102–105`)

**Concerns**
- **HIGH — Task 2’s preflight stops on a missing upstream link.** It requires `references/dispatch-external-cli.md#host-config-audit` in `SKILL.md` and forbids fixing doc text here. 41-09 creates the heading and appends the native commands, but its exact replacement adds no link. The generic external-reference link is not enough for this check. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:133–135`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:194–196`; `skills/ai-kit-spec-execute-superpowers/SKILL.md:260–264`)
- **MEDIUM — The eval transcripts omit outputs needed to follow the documented flow.** The escalation fixture fakes stdout and a successful dispatch but not the gate’s two scratch files or the forced re-resolve between them. The fallback uses an invented `fallback_note`; the audit gives one line when a change produces a second, coverage-limit line. The audit section Task 1 says to quote does not contain the exact message suffix; 41-09 specifies it in `OBSERVATION`. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:100–103`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md:160–161`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md:134,177`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:115–119,194`)
- **MEDIUM — Exact-string checks can pass without proving the claimed documentation structure.** Task 2 asks the executor to choose the first unique sentence, rather than pinning a named rule in its section. In particular, 41-06 deliberately puts the gates/guard *input recipe* in `SKILL.md` and the framing explanation in Compose. A unique Compose sentence can pass even if the recipe is duplicated. The preflight uses line-based `rg -c` over the references directory, whereas the inherited test counts occurrences in flattened text and excludes `design-notes.md`. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:21,134–137`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md:102–106`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:130`)

**Suggestions**
- Add the audit link in 41-09 on the same physical line as its native recipe; keep 41-12 test-only for this topic.
- Script the exact gate files, re-resolve result, fallback notice and both audit lines. State which host and jev condition supplies the fallback notice. Keep the scenarios transcript-assessed.
- Give the executor exact rule fragments and their expected sections. Use the inherited scanner for both the check and its negative control; pin the gates input recipe in `SKILL.md` and the Compose framing separately.

**Risk assessment: HIGH.** The missing anchor blocks an unattended wave. The other gaps undermine the evidence rather than directly changing runtime behavior.

##### Ponytail findings
- **MEDIUM — Task 1:** All four evals are required for JDG-04. Reuse the existing plan input and scratch-project setup; add the missing fake outputs, not a new eval harness. (`skills/ai-kit-spec-execute-superpowers/evals/evals.json:104–107`)
- **HIGH — Task 2:** Reusing 41-01’s helpers is the right design. Fix the producer’s missing anchor and pin the agreed rule text; another scanner is unnecessary. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md:130`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:195`)
- **LOW — Task 3:** The README row is sufficient. Keep the scope qualifiers and say the adapter *tries* the configured fallback: validation can still send the original outcome to the owner. (`README.md:37`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:173`)

#### 41-13

**Summary.** The Git-derived judge set, reviewed-SHA handoff, and canonical regression gate fit JDG-04. The remaining risks are in the orchestration: the failed-third-referee branch still names a command that calls that referee, and the substitute can be selected by the executor’s mechanics in a different role than the plan intends.

**Strengths**
- The plan derives the judged set from Git, checks it against the registry, and limits the curated-config exception to a version-only edit. It also names the producer of the reviewed SHA. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:113,126,205`; `tmp/judge-40/judged.py:34–62,95–114`)
- The final bar and regression authority is `judge_loop.py check --gate`, not a scratch score comparison. The mtime checks are now correctly described as write observations, not confidentiality controls. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:155–163,190–192`; `tools/judge_loop.py:1370–1396`)

**Concerns**
- **HIGH — The failed-third-referee branch still has a paid probe.** Task 1 step 5 says a failed third referee goes directly to the substitute, then still lists `advisory.py probe`. That command invokes referee-three, and its wrapper returns 0 even if the runner probe did not. Step 6 also inherits the phase-40 launch instructions rather than explicitly bypassing all third-referee commands in round one. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:127–129`; `tmp/judge-40/advisory.py:179–199`; `.planning/phases/40-resilient-review-sized-by-jev/40-12-PLAN.md:114–115`)
- **HIGH — A secondary pool probe can defeat the fixed two-referee policy after a successful ping.** The inherited `lanes.py pool` supplies `--native native:opus-high`; the pool tool can add that judge when a pool probe fails. The inherited instructions say to stop if that occurs, but `pool_check.py before` checks member *count*, not identity. The gate immediately before assignment must explicitly enforce the two expected pool members; otherwise the same native identity meant to replace only referee-three can enter a different role. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:127–128`; `tmp/judge-40/lanes.py:379–398`; `tools/judge_loop.py:1547–1559`; `tmp/judge-40/pool_check.py:30–45`)
- **MEDIUM — The leftover scan includes the new collision script.** Step 1 writes a shell file containing paths under `tmp/judge-40/`. Step 2 searches all scratch `.sh` and `.py` files for `judge-40/` and excludes only `copy_drivers.py`. If written as specified, the scan finds its own diagnostic driver. The older step-2 helper explicitly excluded its own file. The rejected `check.py` docstring finding need not be reopened; this is a separate preflight failure. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md:122–124`; `tmp/judge-40/step2_checks.sh:2–5`; `tmp/judge-40/copy_drivers.py:56–64`)

**Suggestions**
- Write a short launch table in Task 1: pool ping failure → no pool work; third ping failure → neither `advisory.py probe` nor `launch`, substitute only; third lane failure after its allowed retry → substitute only for the affected skills. Assert the exact pool IDs after the secondary probes and before allocating work.
- Run the leftover scan over the copied driver allowlist, not every future scratch script. Before any paid call, check the launch table with synthetic ping output and the existing one-third-verdict checker.

**Risk assessment: HIGH.** A preflight can stop on its own diagnostic file, or an ambiguous failure branch can start paid work that the round’s ping did not authorize.

##### Ponytail findings
- **HIGH — Task 1:** Reusing the drivers is appropriate for one maintainer and three judges. Make the existing ping output and pool member list authoritative at launch; do not add another probe or allow a probe result to override the ping decision. (`skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py:213–232,258–264`; `tmp/judge-40/lanes.py:379–398`)
- **LOW — Task 2:** Publishing records and applying the no-rejudge rule are required. Keep `publish.py`’s conflict checks and the canonical gated result. Treat the scratch score tables only as explanations, as the revised plan now says. (`tmp/judge-40/publish.py:51–76`; `tools/judge_loop.py:1370–1396`; `AGENTS.md:65–83`)

#### 41-14

**Summary.** The scratch installed-layout check is much better specified in this revision, and the closeout distinguishes test, transcript and owner-handoff evidence. The main remaining gap is that the post-fold gate can run after publication and can accept a runner copy without the guard. The live snapshot check also uses an exit status intentionally shared by success and failure.

**Strengths**
- The installed check now uses the file-based escalation API, a populated synthetic runtime inventory, parsed TOML and a zero-call tripwire. It exercises installed entry points without treating a CLI result as a full controller run. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:94–100,134`; `tools/run_unittest_parallel.py:370–388,438–462`; `skills/ai-kit-spec-review/ai_kit_spec/cli.py:336–348`)
- The shard check derives its expected set from the declared `SHARD_COUNTS`; a missing report cannot pass just because the other shards ran. The owner handoffs are explicitly required before the tick. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:130,135,154`; `tests/cross_ai_selftest.py:129`; `tmp/run-2026-11-23/p40-13/evidence.py:28–44`)

**Concerns**
- **HIGH — The post-fold check is too late and tests the wrong invariant.** It runs before `ready`, not necessarily before push. The registered wave-post checkpoint can fold and publish in the same call. Also, a guard-bearing template with three matching `13` version strings passes the numeric check even when the project copy still lacks the guard. This is the deliberate 41-07 intermediate state; dogfood rejects it by comparing bytes outside the config block, not just versions. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:201`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md:33–34,238`; `.gsd/capabilities/ai-kit-commit-fold/capability.json:33–38`; `skills/ai-kit-commit-fold/scripts/flow_unit.py:344–386,405–435`; `tools/check_dogfood.py:101–116`)
- **HIGH — The live re-check can record success without creating a snapshot.** Step 2 accepts `host-config-audit --snapshot` exit 0. By 41-09’s contract, a write failure also exits 0, prints `audit unavailable`, and creates no file. Conversely, on the default Claude config root, the inherited broad audit can flag the *new symlink itself* as a change: the helper creates it, and the audit `lstat`s newer entries without excluding `skills`. An authorized first install must not look like config corruption. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:200`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md:153–156,161`; `tmp/run-2026-11-23/p40-13/live_links.py:8–11,24–42`; `tmp/run-2026-11-23/audit_real_config.py:14–46`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-PLAN.md:194`)
- **MEDIUM — A known, sanctioned stale digest can block an unrelated suite retry.** Step 1 recognizes the no-rejudge exception, but Task 2’s restart rule requires the raw `--require-current` command to exit 0. It will still return nonzero for a previously approved stale digest after a test-only fix. The phase-40 closeout records exactly this outcome. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:132,199`; `tools/judge_loop.py:1376–1389`; `.planning/phases/40-resilient-review-sized-by-jev/40-13-SUMMARY.md:125–129`)
- **MEDIUM — The TOML smoke can pass after dropping a fixture lane.** Task 1 copies the wizard’s example JSON literally, including `accepted by a call on YYYY-MM-DD`. The writer rejects that placeholder as an invalid effort source and drops the entry, but can still exit 0 and write an execute policy table. Testing only `session_fallback` therefore misses fixture loss. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:99`; `skills/ai-kit-spec-config/references/config-file.md:109–126`; `skills/ai-kit-spec-review/ai_kit_spec/lane_effort.py:16–17,60–75`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:926–938,1147–1166`)
- **LOW — The evidence script points to the wrong truth.** Task 2b says “the modules of the third truth”; that truth is the owner-handoff requirement. The actual module list is the fifth truth. Name the list directly so the copied phase-40 `STRICT` list cannot accidentally survive. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:21–25,130`; `tmp/run-2026-11-23/p40-13/evidence.py:11–16`)

**Suggestions**
- Bind the history check to a **local, pre-publication** fold step. Require a nonempty checked range, the expected version bump, and matching template/project-copy bytes outside the config block for each guard-bearing commit. Reuse the dogfood comparison; do not move push consent or assume `ready` is the first publish operation.
- Require a newly written snapshot with the exact key set and no `audit unavailable` line. Resolve links under the root used by `live_links.py`, and distinguish exactly the authorized new symlinks from other writes. State which override directories the audit does not cover.
- Apply one digest decision rule at initial close and after a suite fix: allow only the recorded no-rejudge fix with no subsequent skill changes; send newly stale evidence back to the judge/owner path. Use the minimal two-lane roster already in Task 1 for TOML output and assert both lanes survive.

**Risk assessment: HIGH.** The gate can publish mismatched history before rejecting it, or attest a live check that did not produce its required artifact.

##### Ponytail findings
- **MEDIUM — Task 1:** The installed-layout check is necessary. Reuse the existing tripwire and scratch cache; reuse the minimal roster for the writer test instead of importing unrelated effort-policy examples into the smoke test. (`tmp/run-2026-11-23/p40-13/layout_check.py:52–75`; `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:1147–1166`)
- **MEDIUM — Task 2:** The closing suites, fresh report directory and dry run are needed. Reuse the existing report parser and one digest rule; neither issue needs a second full suite run to diagnose. (`tmp/run-2026-11-23/p40-13/evidence.py:28–53`; `tools/judge_loop.py:1376–1389`)
- **LOW — Task 3:** Keep the single-line ROADMAP tick and its same-SHA precondition. Put the missing evidence checks before the evidence is trusted, not inside the tick commit. (`.planning/ROADMAP.md:133`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:151–165`)

#### Cross-plan coverage

- **Waves and dependencies:** No same-wave file overlap in the four reviewed plans. Their frontmatter forms the serial chain `41-10 → 41-11 → 41-12 → 41-13 → 41-14`; the earlier producers are transitively ordered. The missing audit anchor is a producer-contract defect, not a missing dependency edge. (Each reviewed plan’s frontmatter, lines 5–6; `41-09-PLAN.md:194–196` in the same phase directory.)
- **Acceptance and prohibitions:** All nine acceptance items and all five prohibitions have named plan owners. The literal R1 claim that the original 14 evals *pass* still has no executed evidence: the plans preserve them, check their shape, and label the judge evidence transcript-assessed. Keep that distinction in verification. The material R8 gap is the task-eligible fallback and controller handoff described above. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-SPEC.md:258–269,320–330`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md:134`)
- **Intermediate gates:** 41-11 names targeted arch modules and 41-12 names targeted text and shape modules; neither verification lists the full unit and arch groups promised after each wave. The staged hook is selective, so a successful commit is not evidence those groups ran. Assign the full wave checks explicitly to the orchestrator; keep the documented 41-07/41-08 dogfood exception separate. (`.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md:256–257`; `.planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md:193–194`; `AGENTS.md:186–203`)

**Recommendation:** Revise before execution. Fix the 41-11 CLI and switch transition, the 41-09 → 41-12 anchor handoff, and 41-13’s launch gating before spending on executor or judge lanes. Make the fold assertion a pre-publication gate before relying on 41-14 to close the phase.

Read-only review: no files were changed, no suites or live lanes were run, and no passing test result is claimed.

### Triage of cycle 2 (planner fix pass after the cycle)

#### Batch A (41-01, 41-02, 41-03)

# Cycle 2 dispositions, batch A (41-01..03)

- 41-01 HIGH Step 2 load restriction conflicts with the new stop authority: fixed (G1; Task 2 step 1 `ok` bullet is the one line "not a stop; Classify continues", step 2 pointer line says `ok` continues in Classify, step 3(d) keeps Classify's `ok` order, step 3(e) turns Classify's `real_error` lead into a pointer; Task 3 step 5(b) scopes "Do NOT load it" to the Step 2 mode check; truth 1, RULES `not a stop; Classify continues`, new acceptance lines)
- 41-01 HIGH Task 1 removes the text 41-11 needs: fixed (G2; Task 1 step 4 ends the new quota-wake paragraph with HEAD's last sentence verbatim; `test_kept_handoff_text` pins the fragment `it does not pick another candidate.`)
- 41-01 MEDIUM link test checks found links only; empty-anchor stop left in SKILL.md and escalation.md: fixed (G3: `SOURCE_LINKS`, `missing_links`, `test_each_source_links_its_home`, `test_a_removed_pointer_is_caught`, extended in Tasks 2 and 3; G1: Task 3 step 1(a) moves the decision to `### Rounds 4–5 re-resolution`, step 2(a) leaves escalation.md the label plus owner-pick mechanics and a pointer, step 5(d) turns the SKILL.md sentence into a line-for-line pointer (link count 6, still 279 lines), step 6 moves the pin to `test_empty_anchor_stop_lives_in_the_owner_stop`, RULES `no pick is a verified bump`)
- 41-01 MEDIUM ponytail Task 1 (extend the existing config-before-start test instead of a new ordering check): recorded (open, for the orchestrator; not in the fix brief, the new position check stays)
- 41-01 HIGH ponytail Task 2 (move decisions, not machinery): fixed (G1; Classify keeps the `ok` mechanics and the `real_error` relay and fold block)
- 41-01 MEDIUM ponytail Task 3 (move the empty-anchor assertion to the home): fixed (G1; Task 3 step 6)
- 41-02 HIGH Task 1 test module cannot pass (helper `run`, early imports, roster parent folder): fixed (G4; helper `invoke_gate`, Task 1 imports only its own, `pathlib`/`re`/`shutil`/`subprocess` and `SUPER_DIR` move to Task 2 step 6, `os.makedirs` before both roster writes; acceptance `def invoke_gate`)
- 41-02 HIGH allowed-key check has no owner-directed path: fixed (G5; Task 2 step 1b owner pick deletes a stale allowed file and checks the picked key, step 2 scopes the check to the automatic round, step 3 bullet scoped, step 3b owner-named pair block removes the allowed file in state-management.md (added to `files_modified` and Task 2 `<files>`), step 5 fixture `test_owner_named_pair_removes_a_stale_allowed_file`, docs test `test_owner_pick_drops_a_stale_allowed_file`, truth 3)
- 41-02 MEDIUM file boundary uncaught error paths: fixed (G6; `_read_injection_file` refuses non-string entries, `_write_gate_files` writes temp names then renames, `cannot write <path>` exit 2, tests for a bad element and an unwritable out-dir, exact `lane-anchor: '<flag>' must be a boolean` from `LANE_FLAG_KEYS[1]`; truth 5)
- 41-02 MEDIUM no-target stop text and wizard describe broader behaviour: fixed (G7; Task 2 step 3 bullet "An unavailable kept lane" apart from the capability-bump bullets, without the capability-bump phrase; Task 3 step 1 wizard sentence splits execute (adapter acts) from review (recorded only), pinned phrase kept, new pin and acceptance line)
- 41-02 MEDIUM ponytail Task 1 (prioritize CLI tests if the lane budget strains): recorded (open, for the orchestrator)
- 41-02 HIGH ponytail Task 2 (caller-specific check, reuse the exclusion channel and owner-key equality): fixed (G5)
- 41-02 MEDIUM ponytail Task 3 (execute versus recorded-only wording): fixed (G7)
- 41-03 MEDIUM revocation proven in one layer only: fixed (G8; Task 1 `test_project_table_replaces_the_users` with `write_user`/`write_project`, Task 2 step 2 config-file row sentence on revocation and layer rules, truth 3, acceptance lines)
- 41-03 MEDIUM wizard checks cannot tell consent from copying the example: fixed (G9; Task 2 step 3 yes-only qualification next to the JSON example, step 3b headless.md item 7 (added to `files_modified` and Task 2 `<files>`), pins and acceptance lines); the eval-or-transcript check of yes/no/retry is recorded (open, for the orchestrator; not in the fix brief)
- 41-03 LOW ponytail Task 1 (use `_ScratchLayers` for the layered case): fixed (G8)
- 41-03 MEDIUM ponytail Task 2 (update the headless summary): fixed (G9)
- Cross-plan HIGH 41-04 known-red pin of the no-ladder sentence: recorded (open, for the orchestrator; handled by the batch B fixer per the brief)
- Cross-plan MEDIUM wave gates and scope check not assigned in batch A handoffs: fixed (G10; each plan's orchestrator step runs `--group unit` and `--group arch` beside `make check-dogfood`; Task 1 step 0 records the plan base; the last task's acceptance and `<verification>` hold the scope check against `files_modified`)
- Cross-plan MEDIUM the 14 evals are shape-checked, not executed: recorded (open, for the orchestrator; the brief says the acceptance wording already says shape-checked and transcript-assessed)

#### Batch B (41-04, 41-05, 41-06)

# Cycle 2 dispositions, batch B (41-04..06)

- 41-04 HIGH Task 3 verification breaks test_spec_chain_text: fixed (H1: Task 3 files and frontmatter add tests/test_spec_chain_text.py; new step 8 widens only `NO_LADDER_SENTENCE`, byte for byte with the en dash; config-check and no-config ask assertions unchanged; "seven paths"; new rg gate; artifacts)
- 41-04 HIGH fallback branch bypasses the shared native brief and lifecycle: fixed (H2: Task 3 step 3 SKILL.md line is now "an exception inside the native branch below, never a second launch path", skips only the ladder escalation and model bump, then "dispatches through the native branch below unchanged"; relays the stderr notice on first selection; pinned resume keeps the saved injection; resolution-stops and state-management sentences, TestFallbackDocs needles, truth, objective, done, artifacts and a new rg gate updated; kept anchors `**Session fallback (` and the widened sentence)
- 41-04 MEDIUM refusal fixtures can pass without testing the jev boundary: fixed (H3: Task 2 behavior and step 4: round 4, escalation keys and `--no-fallback` run with the Claude signal and the same patched find_jev and recording run as the positive control, each asserts no jev call; one named `_scratch_roster` helper creates the config parent folder; every cli.main call passes an explicit `env_fn`)
- 41-04 MEDIUM trust note understates jev; eval note differs: fixed in 41-04 (H4: T-41-11 says no external executor starts and the Claude Code path can start the existing local jev client; truth and artifacts state the four picker notes as the only `fallback_note` values; orchestrator step added); recorded (open, for the orchestrator): 41-12 line 100 still scripts `fallback_note` "every execute lane is out of quota", which is not one of the four notes; align 41-12 (for example `jev low: session model kept`)
- 41-04 ponytail HIGH Task 3 second launch recipe: fixed (same edit as H2)
- 41-05 MEDIUM owner-config validator does not enforce the exact-file claim: fixed (H5: `_owner_config_paths` rejects empty, `.` by equality, trailing `/`, absolute, `..`, `'`, leading `:`, `*?[`; `BAD_OWNER_CONFIGS` plus a temp-folder absolute case in both subcommands' tests; a supported control; `test_supported_path_excludes_only_that_file` asserts the exact composed pathspec line; truth, T-41-17 and an rg gate updated)
- 41-05 MEDIUM tracer depends on ambient runner facts: fixed (H6: module helper `isolated_dispatch_env` sets scratch HOME and XDG_CACHE_HOME via `mock.patch.dict(os.environ)` and patches `runner_facts.stored_fact` to None; TestDispatchPath setUp calls it; the "stop and report if pi is refused" escape removed; read_first names `_refuse_candidate`, `execute_cli_error`, `cache_base`; 41-06 reuses it)
- 41-05 LOW error tests miss the full matrix; dogfood label: fixed (H7: print-guidance error test covers a missing and a non-UTF-8 `--guard-file` and the owner-config cases; verification labels `make check-dogfood` "(orchestrator only)")
- 41-05 ponytail MEDIUM Task 1 test seam at the cached observation: fixed (same edit as H6)
- 41-06 HIGH first dispatch after an unpinned resume omits both inputs: fixed (H8: recipe keyed on the loaded scalar `GUIDANCE_READY` not being `$TASK_N`, recorded right after the writes, never on FIX_ROUND/RESUME_FOUND; value is the task number, not the brief's literal 1, because the scalar file is per plan and a 1 would leak into the next task; the session-fallback dispatch uses the same native instructions; tests `test_unpinned_resume_writes_the_files_on_first_dispatch`, `test_pinned_resume_keeps_the_task_scalar`, doc test `test_recipe_keys_on_the_task_scalar`; truth, T-41-19, artifacts, rg gates)
- 41-06 MEDIUM native recipe does not stop on a print error: fixed (H9: recipe says the native branch launches only when the print block exits 0, else owner stop naming the error; the block's exit is print-guidance's (last line); stub shim fails on `AI_KIT_FAKE_SHIM_EXIT`; `test_native_block_fails_when_print_fails`; new truth and rg gate)
- 41-06 MEDIUM replay loses first-dispatch input; shell success is not shim success: fixed (H10: `_dispatch_and_replay` replays each external call right after recording it, before prompt.txt is rewritten, asserts `.exit` 0 after each call, the run's objective and `--report-mode`; behavior, done and an rg gate updated)
- 41-06 ponytail HIGH Task 1 recipe keyed only to a fresh start: fixed (same edit as H8)
- 41-06 ponytail MEDIUM Task 2 replay each call immediately: fixed (same edit as H10)
- Batch follow-through: full `--group unit` / `--group arch` after each wave: fixed (handoff line copied from 41-01 into the orchestrator steps of 41-04, 41-05 and 41-06)

#### Batch C (41-07, 41-08, 41-09, 41-10)

# Cycle 2 dispositions, batch C (41-07..10)

- 41-07 HIGH no-checkpoint window not wired to the executor: fixed (L1: must_haves window truth, objective execution path, Commits paragraph points blockers at the lane report, orchestrator_steps per-task driver, no stock wave-post `ai-kit-fold checkpoint`, orchestrator writes the SUMMARY and records the task tip, first checkpoint after 41-08 and the 41-14 history gate)
- 41-07 MEDIUM fixtures would not catch the ceiling regression: fixed (L2: Task 2 behavior and `realhome-exec-checkout-subdir` set `c.env.GIT_CEILING_DIRECTORIES = c.repo`, still expect `1`, `tree=unknown` accepted as in `non-git-exec`; the stop rule exempts that case)
- 41-08 HIGH post-fold check misses red commits and can run after publication: fixed (L3: must_haves "Fold and history gate" truth, objective window rule, orchestrator_steps fold expectation and the named local pre-push history gate of 41-14 over a non-empty range, outside-config body equality plus version 14, stop before any push)
- 41-08 MEDIUM invalid command and ambiguous handoff SHA: fixed (L4: precondition keyed on `tmp/run-2026-11-23/p41-07/task-tip.sha`, step 1 writes `p41-07-tip.sha` and `start-head.sha` separately, preflight of `check_times.py`, module list from the copied `shard_modules.py`, `shard_secs.py` dropped and the copied `check_log.py` extended with `recorded_changes` against `E2E_RECORDED_SECS`; verify, acceptance, verification and artifacts updated)
- 41-08 MEDIUM post-fold rollback locator cannot match: fixed (L5: Task 3 step 5 and the orchestrator bullet find the folded commit by the `Ai-Kit-Fold: <unit>` trailer, the original message in the body and the verified changed paths; zero or several matches stop)
- 41-09 HIGH audit I/O can invent a change or replace the exception: fixed (L6: must_haves truths; `snapshot(env, stat_fn=os.stat)` gives None for FileNotFoundError/NotADirectoryError/non-file and `"unavailable"` for other stat errors; `changed` skips unavailable values, new `unavailable()` and `UNAVAILABLE_FOR` line; best-effort stderr via `contextlib.suppress(OSError)`; tests for an injected stat error, a failing stderr stream and a raising dispatch; `--compare` accepts the `unavailable` string; test count 12)
- 41-09 HIGH stale native snapshot and fallback bypass: fixed (L7: native recipe truth and the SKILL.md line delete the old snapshot first, compare a missing file as the unavailable observation, cover every native launch including the session fallback and a failed launch; docs test orders first `rm -f` < snapshot < compare < last `rm -f`)
- 41-09 MEDIUM Task 3 does not produce the 41-12 link: fixed (L8 / J6: link `references/dispatch-external-cli.md#host-config-audit` on the same physical SKILL.md line, acceptance gate HEAD=0; the section quotes the exact `OBSERVATION` sentence, pinned through `host_config.OBSERVATION.format`; the relay sits before the empty-result stop)
- 41-10 HIGH lane can re-enter final selection without a blocked check: fixed (L9: selection truth and Task 3 `_blocked_pool_quota(deps, loaded, request, existing_quota)` take keys from `deps.compute_ladder_keys_fn` on the post-exclusion request shared with the builder; `ValueError` defers to the build; affinity re-entry test added)
- 41-10 MEDIUM expiry fixture does not establish "tried once": fixed (L10: `test_expired_pool_probes_only_its_first_eligible_lane` with the real `quota.refresh_quota_cache`, a fake probe and both clocks pinned; test count 16)
- 41-10 HIGH Task 2 cannot pass pylint with six parameters: fixed (L11: new `flagged_lane(config, key, reason, role="review") -> dict | None`, `next_lane(..., role)` at five parameters, `flagged_replacement` keeps five and delegates; truths, Task 2 tests, acceptance, T-41-38 and artifacts updated; names passed to fixer D for 41-11)
- 41-10 MEDIUM Task 1 tracer does not isolate HOME: fixed (L12: `_dispatched_flags` runs under `mock.patch.dict(os.environ, HOME, XDG_CACHE_HOME)` and `runner_facts.stored_fact` faked to None; import list adds `os`, `sys`, `mock`, `runner_facts`)
- batch MEDIUM wave gates need an orchestrator owner: recorded (open, for the orchestrator; handoff line added to 41-07 and 41-08 orchestrator_steps and to 41-09 and 41-10 verification, dogfood orchestrator-only with the 41-07/08 exception)

#### Batch D (41-11, 41-12, 41-13, 41-14)

# Cycle 2 dispositions, batch D (41-11..14)

- 41-11 HIGH exit-2 tests cannot pass (one-argument ConfigError): fixed (truth 1; Task 1 read_first `main` note and step 3 `_read_json_file`/handler validation, stderr `ai-kit-spec: executor-fallback: unreadable <flag> file <path>`, exit 2; step 4 `test_unreadable_inputs_exit_two` pins the exact line for invalid JSON and wrong shape of all three files; artifacts list)
- 41-11 HIGH first routable fallback hides a later eligible one: fixed (new `--injection-file`; handler excludes roster keys outside its `ladder_keys` plus the exclude file; truth 1, key_links, parser, Task 2 block, `_switch_run` assertion, `test_first_eligible_fallback_skips_a_lane_outside_the_task` A/B/C fixture with control; 41-14 d1 passes the flag; final key check kept)
- 41-11 HIGH switch is not a reliable controller transition: fixed (Task 2 block: backup + checked `cp`/`mv` + checked scalar write before `SWITCHED=1`, backup restored on a failed write; second wave writer removed in favour of Relay's fold; native replacement is a fresh native subagent in any fix round; behavior bullets, truth 3, T-41-61, tests `test_flagged_switch_failed_move_keeps_the_original` and `test_flagged_switch_native_replacement_in_a_fix_round`)
- 41-11 MEDIUM escalation.md and cross-ai section 6 still contradict the switch: fixed (Task 2 step 4b escalation.md pointer, file added to files_modified, Task 2 files/git add/six-path check, pin in `test_flagged_switch_exception_in_every_rule`; Task 3 step 1b widens section 6 to name both skills, same exception as section 8; no pinning test existed at HEAD (rg), so a new pin `test_cross_ai_quota_precedence_names_both_skills` and an rg criterion were added; `Never switch harness, provider or model` kept; SWITCH_RE scan clean)
- 41-11 LOW scope-check setup does not reach the coding lane: fixed (Task 1 step 0 writes `tmp/run-2026-11-23/p41-11/base.txt`; verification reads that file by name)
- 41-11 ponytail MEDIUM Task 1 give the selector the right candidate set: fixed (with the `--injection-file` exclusion; no second walker; `fallback_outcome` now calls 41-10's `flagged_lane` and `next_lane` with role "execute", per the orchestrator's API note)
- 41-11 ponytail HIGH Task 2 extra wave-state writer: fixed (removed; Relay's fold reused)
- 41-11 ponytail MEDIUM Task 3 section 6 should point to the section 8 exception: fixed (Task 3 step 1b)
- 41-12 HIGH preflight stops on a missing upstream link: recorded (open, for the orchestrator: J6, fixer C adds the link in 41-09 on the native recipe line; 41-12's check is unchanged)
- 41-12 MEDIUM eval transcripts omit outputs the flow reads: fixed (Task 1 escalation eval scripts the gate stdout, both scratch files and the forced re-resolve; fallback eval states an opencode host and the real note `host takes no model`, no invented field; audit eval scripts both lines with the exact OBSERVATION and NOT_CHECKED texts)
- 41-12 MEDIUM exact-string checks can pass without proving structure: fixed (Task 2 step 1 names six fixed fragments with home and section, the gates input recipe pinned in SKILL.md and the Compose framing in dispatch-external-cli.md separately; the preflight script loads 41-01's helpers by path, flattened text, design-notes.md excluded)
- 41-12 ponytail MEDIUM Task 1 add the missing fake outputs: fixed (same edits as the eval-transcript concern)
- 41-12 ponytail HIGH Task 2 fix the producer anchor and pin agreed text: fixed for the pinned text (Task 2 step 1); the anchor is recorded (J6, fixer C in 41-09)
- 41-12 ponytail LOW Task 3 README says the adapter tries the fallback: fixed (Task 3 sentence `tries the configured fallback of a lane the owner flagged usage_limited`)
- 41-13 HIGH failed-third-referee branch still has a paid probe: fixed (Task 1 step 5 launch table; `advisory.py probe` only on an ok/fresh referee-three ping; step 6 overrides the inherited 40-12 launch instructions; synthetic launch-table check before any paid call)
- 41-13 HIGH secondary pool probe can defeat the two-referee policy: fixed (Task 1 step 5 pool identity gate `pool_identity.py`: members exactly `router-env/my-referee-one` and `router-env/my-referee-two`, `native:opus-high` only as the referee-three substitute, with a synthetic negative run; acceptance criterion added)
- 41-13 MEDIUM leftover scan includes the new collision script: fixed (Task 1 step 2 `leftover.sh` over the copied allowlist only; acceptance criterion updated)
- 41-13 ponytail HIGH Task 1 ping output and pool list authoritative at launch: fixed (launch table and pool identity gate)
- 41-13 ponytail LOW Task 2 keep publish checks and gated result: rejected (no change needed: Task 2 already keeps publish.py's checks and the gated result, and treats score tables as explanations)
- 41-14 HIGH post-fold check too late and tests the wrong invariant: fixed (orchestrator Step 3: local gate right after the fold and before any push, `fold.py consent`, publishing checkpoint or `ready`; non-empty range; outside-config equality through `check_dogfood._outside_config` loaded by path; the three versions equal 14; states it binds the fold step, not `ready`)
- 41-14 HIGH live re-check can record success without a snapshot: fixed (orchestrator Step 2: new file required, exactly the ten `HOST_CONFIG_FILES` keys, no `audit unavailable` line; created symlinks listed in `created-links.txt` and excluded by path, any other write flagged; override folders not covered are stated)
- 41-14 MEDIUM sanctioned stale digest blocks a suite retry: fixed (one digest rule in orchestrator Step 1, reused by Task 2 step 4: stale passes only as a recorded no-rejudge fix (`fixes.md` in the round folder) with no later change to that skill; raw exit code is not the gate)
- 41-14 MEDIUM TOML smoke can pass after dropping a lane: fixed (Task 1 e1/e2 use the minimal two-lane roster and assert both lanes survive)
- 41-14 LOW evidence script points to the wrong truth: fixed (Task 2 step 2b names the nine modules directly and replaces the copied `STRICT` list)
- 41-14 ponytail MEDIUM Task 1 reuse the minimal roster: fixed (e1/e2)
- 41-14 ponytail MEDIUM Task 2 one digest rule: fixed (Step 1 / Task 2 step 4)
- 41-14 ponytail LOW Task 3 keep the single-line tick: rejected (no change needed: the tick and its same-SHA precondition already stand; the evidence checks now run in Steps 1-3 before the tick)
- cross-plan MEDIUM full unit and arch groups after each wave are not assigned: fixed for the handoff (an `<orchestrator_steps>` line in 41-11 and 41-12 as in 41-01); the runs themselves are recorded (open, for the orchestrator)
- cross-plan note R1 original 14 evals have no executed evidence: recorded (open, for the orchestrator; 41-14's checklist already labels them transcript-assessed)

## Open concerns after cycle 2 (no cycle 3; owner time rule)

Fixed in the targeted pass: every HIGH of cycle 2 (G1-G10, H1-H10, L1-L12, J1-J17); the plan checker ran after the pass.
Still open, with severity:

- MEDIUM (owner): a checkout-supplied `.aikit/config.toml` can turn the session fallback on without the wizard (A10/B2,
  rejected with reason: the fallback keeps execution in the owner's own session; the trust gate covers executable commands;
  recorded in the 41-03/41-04 threat models).
- MEDIUM (orchestrator): the full `--group unit` and `--group arch` runs after each wave are an orchestrator step (handoff
  lines are in every plan; the runs themselves happen at execution).
- MEDIUM (orchestrator): the original 14 adapter evals are kept and shape-checked, and the new ones are transcript-assessed;
  none is executed. 41-14's checklist labels them so.
- MEDIUM (orchestrator): 41-07 and 41-08 form one maintenance window (no checkpoint between them; `make check-dogfood` is red
  in that window by design); 41-14's local history gate must pass after the fold and before any push.
- MEDIUM (ponytail, not in the briefs): 41-01 adds a new ordering check instead of extending the existing config-before-start
  test; 41-02 Task 1 is near the lane budget (prioritize the CLI tests if it strains); 41-03 has no eval or transcript check of
  the wizard's yes/no/retry behaviour (phrase pins only).
- OWNER QUESTION (SPEC amendment 1): does "the two briefs ai-kit ships" include the runner's `EXEC_PREAMBLE`? This phase
  leaves it unchanged.
