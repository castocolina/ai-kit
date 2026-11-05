---
phase: 29
cycle: 2
reviewers: [referee-one, referee-two, referee-three]
reviewed_at: 2026-11-04T18:40:04-03:00
plans_reviewed: [29-01-PLAN.md, 29-02-PLAN.md, 29-03-PLAN.md, 29-04-PLAN.md, 29-05-PLAN.md, 29-06-PLAN.md, 29-07-PLAN.md, 29-08-PLAN.md, 29-09-PLAN.md, 29-10-PLAN.md, 29-11-PLAN.md, 29-12-PLAN.md, 29-13-PLAN.md, 29-14-PLAN.md, 29-15-PLAN.md, 29-16-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
  referee-two: "router-env/my-referee-two"
  referee-three: "router-env/my-referee-three"
model_sources:
  referee-one: "pinned"
  referee-two: "pinned"
  referee-three: "pinned"
plan_coverage:
  referee-one:
    total: 16
    missing: ["29-01", "29-02", "29-03", "29-04", "29-05", "29-09", "29-10", "29-11", "29-12", "29-13", "29-14", "29-15", "29-16"]
---

# Cross-AI Plan Review — Phase 29

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Note: referee-one, referee-two and referee-three share the opencode adapter; their consensus is cross-model, not cross-tool.

History: cycle 1 (9531d7d, plans at 01922d6) had referee-one only, covered 29-01 and 29-06, 2 HIGH + 1 actionable, revised in f3db283.

## Review conditions

Cycle 2, over the sixteen plans at `97aa95b` (revision f3db283). Each configured reviewer was probed once with a
one-word prompt (18:24). The prompts were rebuilt and split into seven batches, one per execution wave (w1 29-01 to
29-05, w2 29-06 to 29-08, w3 29-09 to 29-11, w4 29-12, w5 29-13 and 29-14, w6 29-15, w7 29-16), each inlining
PROJECT.md (first 80 lines), the ROADMAP Phase 29 section, FLOW-01 and JEV-06, 29-SPEC.md, 29-CONTEXT.md, the
cycle-1 findings and fixes, the batch's plans, the source-grounding instructions, the ponytail lens and the batch's
plan coverage manifest. Each batch ran through the opencode lane (`review-lane invoke --slug opencode --as
<instance>`), at most two at a time; a failed batch was retried once.

- **referee-one** (`router-env/my-referee-one`): probe OK in 10 s. One batch of seven produced a review:
  - w2 (29-06, 29-07, 29-08): OK, 673 s, full per-plan sections with `file:line` evidence.
  - w1 (29-01 to 29-05): failed twice (110 s, then 629 s). Each time opencode stopped after an opening paragraph,
    and the lane marked it `[reviewed-without-source-citations]`. The retry's paragraph says the cleanup fix is
    incomplete in these plans too (see below); no per-plan sections.
  - w3 (29-09 to 29-11): failed twice (0 s, then 31 s, the retry giving only an opening paragraph).
  - w4, w5, w6, w7: failed twice each, within 0 to 15 s, with "returned no assistant text ... exited with status 1".
  - The opencode log gives the cause for each failed call: `AI.Error: Combo has no executable targets` (the router
    combo had no target free; the owner's `audit.py run-evals` job shares this combo). No `AIKIT-XAI` line and no
    `retry_after_s` were printed.
- **referee-two** (`router-env/my-referee-two`): **failed** at the probe after 81 s (exit 1):
  `Error: Model grok-cli/grok-4.7-xhigh is unavailable`. Not dispatched; no substitute.
- **referee-three** (`router-env/my-referee-three`): **failed** at the probe after 87 s (exit 1):
  `Error: Model anthropic/claude-opus-5-5-xhigh is unavailable`. Not dispatched; no substitute.

Only one reviewer produced a review, so the consensus gate does not apply: every finding counts once the
orchestrator confirms it against the plan text and the source.

## OpenCode Review (referee-one)

### Batch w1 (29-01 to 29-05): incomplete

Two attempts stopped after the opening paragraph. The retry's text, verbatim:

> Two cycle-1 changes look sound on paper: checking the folded segment before replay, and preserving a reused
> backup tag. The cleanup fix is still incomplete: most plans run `close` before GSD commits the last task, and
> only the final full-suite run receives the per-run `TMPDIR`.

### Batches w3 to w7 (29-09 to 29-16): not reviewed

Every attempt failed (`Combo has no executable targets`).

### Batch w2 (29-06, 29-07, 29-08)

Using the plan-review checklist and ponytail lens to review 29-06, 29-07, and 29-08 against the source. I’ll check the cycle-1 fixes and shared `scope.py` procedure without changing files or running tests.
Confirmed two blockers: 29-07’s replacement text exceeds the renderer’s 200-character line cap, and its old-client check cannot see argparse’s error because `gp_host._run` returns stdout only. The shared `scope.py close` also runs before the final task commit, so it would flag that task’s intended edits as leftovers.
##### Document type
GSD implementation plans · read-only, source-grounded review

#### 29-06

##### Summary
The revised tree-proof and backup-tag handling address the specific cycle-1 regressions correctly at the design level. The main remaining safety gap is merge ownership: matching GSD’s generic merge subject cannot establish that a merge belongs to the current unit. The grouping rules also do not establish the promised intermediate-commit buildability. Finally, the shared cleanup procedure is not executable in the prescribed task order.

##### Strengths
- **The segment proof now precedes replay.** Comparing the folded segment against `end` before replay prevents a later tracking commit’s original tree from hiding a bad fold. The positive replay case and patched-segment refusal case distinguish these paths explicitly: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-06-PLAN.md:131–139`.
- **The worktree merge-back premise is verified.** Installed GSD really uses `merge --no-ff` with the specified subject: `.claude/gsd-core/bin/lib/worktree-safety.cjs:1345`. Supporting these merges is necessary, not scope creep.
- **[ponytail] Verification reuses existing infrastructure.** Keeping engine cases in one test module and using the existing per-module runner avoids another test harness. That runner already provides temporary environments and host-call tripwires: `tools/run_unittest_parallel.py:520–538`.

##### Concerns
- **HIGH — The foreign-merge guard accepts another unit’s GSD merge.**  
  The guard accepts any merge whose subject starts with an `own_merge_subjects` entry, while the fixture uses the generic prefix `chore: merge executor worktree (`: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-06-PLAN.md:130,139`. Every actual GSD merge-back uses that prefix, regardless of unit (`.claude/gsd-core/bin/lib/worktree-safety.cjs:1345`), and the downstream adapter supplies that same generic prefix (`.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-09-PLAN.md:105`). Consequently, a foreign GSD merge inside the segment passes. Tree equality preserves content but cannot prove ownership of rewritten history.

- **MEDIUM — Shared-path and Python test-name checks do not prove buildable feature commits.**  
  The grouping action merges shared paths and `p.py`/`test_p.py` pairs, but otherwise preserves first-commit order: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-06-PLAN.md:140`; `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-01-PLAN.md:136,140`. For example, feature A’s final `a.py` can import feature B’s later-added `b.py`; the paths do not overlap, yet the first folded commit is broken while the final tree proof passes. This leaves D-09’s “never writes an unbuildable commit” promise unverified: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-CONTEXT.md:97–98`.

- **HIGH [ponytail] — `scope.py close` blocks the final task before its required commit, and is not repeat-safe.**  
  Task 2 runs `close` before completing verification: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-06-PLAN.md:142–150`. The shared procedure treats every new status line as a leftover and deletes its temp directory on success: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-01-PLAN.md:105`. However, GSD verifies a task **before** committing its intended edits (`.claude/agents/gsd-executor.md:155–160`), so those edits necessarily fail this check. The plan also repeats `test`/`close` in overall verification (`29-06-PLAN.md:179–180`), after a successful close would have removed the directory.

##### Suggestions
- Establish merge ownership using unit-specific identity and parent/range checks; add a refusal fixture containing a **different unit’s GSD merge with the same generic prefix**.
- Add a fixture whose features have a cross-file dependency. Require inseparable features to merge with a reason, rather than accepting final-tree equality as evidence that each feature commit builds.
- Separate pre-commit resource checks from post-commit clean-tree checks, and make repeated closeout verification well-defined.

##### Cycle-1 assessment
- **Segment proof:** correct and complete for the reported replay-masking defect.
- **Reused backup tag:** the `created` flag and explicit reused-tag regression case correctly address the reported deletion defect: `29-01-PLAN.md:137`; `29-06-PLAN.md:103–104`.
- **`scope.py`: not complete.** Besides the ordering issue, process ownership is inferred from start time and cwd, not actual run identity. Earlier targeted tests also run outside the per-run TMPDIR; their leaked temp entries would merely be reported as “not this run” under the shared definition (`29-01-PLAN.md:104–105`).

##### Risk assessment
**HIGH.** Merge ownership affects history-rewrite safety, and the cleanup gate currently prevents normal completion.

#### 29-07

##### Summary
This is a justified migration with good caller coverage, including the previously missed pointer/objective imports. Reusing `jev_status`’s fixed output mapping is sensible. However, the exact replacement text cannot pass the current renderer, the old-client diagnostic is invisible through the production subprocess seam, and the golden harness migration is scheduled after the task that needs it.

##### Strengths
- **The migration preserves a narrow result contract.** Existing `jev_status` reduces detection output to fixed usability reasons instead of exposing arbitrary client text: `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:466–488`.
- **The dependent test imports are now included.** `DECIDE_REL` is genuinely imported by the objective and pointer modules: `tests/test_ai_kit_spec_goal_prompt_objective.py:25`; `tests/test_ai_kit_spec_goal_prompt_pointer.py:28`. The plan explicitly updates both: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-07-PLAN.md:99`.
- **[ponytail] The file count is justified by existing coupling.** Reusing `HostSeams`, `CliSeams`, and stand-in client files avoids inventing a second detection/testing interface: `gp_host.py:45–50`; `tests/test_ai_kit_spec_goal_prompt_cli.py:94–98,124–127`. The lookup copies are a locked D-13 decision, not unnecessary duplication to remove here.

##### Concerns
- **HIGH — Both prescribed replacement sentences exceed the renderer’s line cap.**  
  The exact strings in `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-07-PLAN.md:120` are **203 and 257 characters**, respectively—**205 and 259** after the renderer adds `- `. The cap is 200 (`skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:52,456–462`), and exceeding it produces a guard failure (`skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:223–230,687–695`). The existing fixed-text branches do not call `fit_line`. Simply truncating the longer sentence would also remove its trailing fallback instruction.

- **MEDIUM — The production seam cannot expose the old-client error the plan tests.**  
  The plan detects an old client using exit 2 plus `invalid choice` in the returned output: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-07-PLAN.md:88,96`. But `gp_host._run` captures stderr and then returns **only stdout** (`skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:53–72`). The existing client uses standard argparse (`skills/jev-fast-decision/scripts/jev_review.py:2010–2022`), whose invalid-subcommand diagnostic goes to stderr. The fake therefore passes a diagnostic through a channel the real seam discards; production returns `detect failed`, not the promised update instruction.

- **MEDIUM [ponytail] — Golden harness changes belong with Task 1, and the diff allowlist overlooks a predictable change.**  
  Production detection changes in Task 1, but the golden stand-in moves in Task 2: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-07-PLAN.md:97,121`. Until then, the golden harness still creates only the old spec-discuss client (`tests/test_ai_kit_spec_goal_prompt_golden.py:188–192`), so it observes “not installed” instead of its previous “no usable backend” state. Furthermore, replacing that stand-in removes the `ai-kit-gsd-spec-discuss` directory used by `_candidate_skills` (`skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:38–43,439–440`). That changes a non-jev “Candidate skills” line in the golden (`tests/fixtures/goal_prompt/golden/opengsd-goal-pointer.md:114`), which the proposed `golden_diff.sh` rejects.

- **HIGH — The shared close check cannot pass at the prescribed point.**  
  Task 2 invokes `close` before its commit and repeats it in later verification: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-07-PLAN.md:122–137,159–160`. Its intended source and golden edits become new status lines, which the shared definition rejects (`.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-01-PLAN.md:105`), while GSD commits only after verification (`.claude/agents/gsd-executor.md:155–160`).

##### Suggestions
- Shorten the fixed sentences to fit the existing cap **without truncating advisory/fallback semantics**; pin both meaning and rendered length.
- Exercise the old-client path with a synthetic argparse script through the real subprocess seam. Expose stderr for failed jev detection without contaminating successful JSON parsing.
- Move all affected stand-in updates into Task 1. Either preserve the independent spec-discuss candidate directory or explicitly accept and review that intended golden change.
- Correct the shared cleanup timing and repeated-invocation contract.

##### Cycle-1 assessment
- **`scope.py`: not complete**, for the ordering and repeatability reasons above.
- **Golden safeguard: useful but incomplete.** It adds an independent diff check, but token presence alone does not validate wording, and its current allowlist rejects the candidate-directory consequence. Retaining the manual diff review is appropriate.

##### Risk assessment
**HIGH.** The literal text change prevents rendering, while fixture sequencing and cleanup introduce additional execution blockers.

#### 29-08

##### Summary
The documentation/lookup contract and consent ownership are well aligned with the phase. The ordered-table comparison, executable example, and generic eval validation are valuable. Two source mismatches need correction: the generic hygiene scan rejects calibration data the plan explicitly preserves, and the consent instructions assume raw probe rows have a field they do not contain. This plan also inherits the cleanup-order blocker.

##### Strengths
- **The documented lookup order matches the existing implementation.** Own root, Claude, `.agents`, opencode, Cursor, and pi are searched in that order today: `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:89–108`. Parsing the table and testing a swapped order provides meaningful drift protection: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-08-PLAN.md:88,97–98`.
- **Remote access remains fail-closed.** The real client checks URL, key, and permission before dialing a remote: `skills/jev-fast-decision/scripts/jev_review.py:1213–1231`. Moving the consent instructions does not require weakening that boundary.
- **[ponytail] Registration reuses the existing generator.** `tools/gen_test_groups.py:25–35,72–79` already derives listings from runner discovery. Using it is preferable to maintaining another module list.

##### Concerns
- **HIGH [ponytail] — The generic hygiene test necessarily fails on untouched calibration data.**  
  Task 2 says `evals/cases.jsonl` stays untouched, then requires scanning **every file under `evals/`** with a regex that rejects `~/`: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-08-PLAN.md:119,124`. Existing `skills/jev-fast-decision/evals/cases.jsonl:1` contains the synthetic input `~/.config/llm-env/models.yml`. Thus the new test fails immediately despite the six new evals being valid. Changing unrelated backend-calibration inputs just to satisfy the new skill-eval checker would be unnecessary scope expansion.

- **MEDIUM — The consent flow confuses raw `--probe` rows with normalized `detect` rows.**  
  The new instructions trigger on a remote row’s `status: consent_required_for_remote` for either command: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-08-PLAN.md:96,123`. Raw `--probe` rows contain **`reason`**, not `status` (`skills/jev-fast-decision/scripts/jev_review.py:1288–1303`). The ladder’s `public_backends` adds normalized `status` (`skills/ai-kit-gsd-spec-discuss/scripts/decide.py:322–349`). Since the current first-call flow uses `--probe` (`skills/jev-fast-decision/SKILL.md:12`), an agent following the new field test can miss the consent ask. A synthetic probe fixture containing the nonexistent row field would conceal that mismatch.

- **HIGH — The shared close check runs before the final eval/test changes can be committed.**  
  The final action and acceptance criteria require `close` to report clean: `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-08-PLAN.md:126–140`. At that point, the new eval files, test module, and generated listings are intended uncommitted work. The shared checker rejects those new status lines (`.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-01-PLAN.md:105`), but the executor commits only after verification (`.claude/agents/gsd-executor.md:155–160`).

##### Suggestions
- Limit new-shape hygiene validation to `evals.json`, `trigger-queries.json`, and their fixture files, or explicitly separate existing calibration data from that contract.
- Document the two actual response shapes—or consistently use normalized `detect` output. Make the consent fixture faithful to the chosen command and assert backend, host, permission, and revoke behavior.
- Apply the shared cleanup timing/repeatability correction before execution.

##### Cycle-1 assessment
**`scope.py`: partially improved, not complete.** The per-run directory and self-test are useful, but the prescribed close timing still rejects intended edits. The procedure also does not attribute earlier targeted-test temp files to this run, since only its `test` subcommand sets the per-run TMPDIR.

##### Risk assessment
**HIGH.** The new generic test has a deterministic conflict with preserved data, and closeout is blocked. The consent issue is a functional gap, although the underlying client still prevents unauthorized remote calls.

#### Overall disposition

**Status: Issues Found — revise before execution.**

All three manifest plans were covered. The cycle-1 **segment-proof** and **reused-tag** corrections are sound as specified; the shared **cleanup correction is not yet complete**. Prioritize cleanup ordering, merge ownership, renderer-safe text, and the eval/calibration boundary before smaller documentation refinements.

Not run: test suites, live backends, or Git-rewrite experiments; no files changed.  
Residual risk: the fold-engine files do not exist yet, so its safety assessment concerns the proposed algorithms, not a verified implementation.

---

## OpenCode Review (referee-two)

opencode review failed or returned empty output (probe failed; full run not dispatched). stderr:

```
> build · my-referee-two
Error: Model grok-cli/grok-4.7-xhigh is unavailable
```

---

## OpenCode Review (referee-three)

opencode review failed or returned empty output (probe failed; full run not dispatched). stderr:

```
> build · my-referee-three
Error: Model anthropic/claude-opus-5-5-xhigh is unavailable
```

---

## Consensus Summary

One reviewer (referee-one) covered three plans (29-06, 29-07, 29-08); thirteen plans got no review this cycle, so
there is no cross-reviewer consensus. The orchestrator checked each finding against the plan text and the source
(and asked jev-fast-decision for an advisory classification of each; every answer came back `needs_fallback`, so
the verdicts below are the orchestrator's):

1. **The close check fails on the task's own edits and is not safe to re-run (all plans; raised on 29-06, 29-07,
   29-08, and in the w1 paragraph for 29-01 to 29-05) — confirmed, HIGH.** 29-01's close check counts every
   `git status --short` line new since the start snapshot as a leftover (29-01-PLAN.md:105), and each plan runs
   `close` inside its last task's action (29-01-PLAN.md:175, 29-06-PLAN.md:142, 29-07-PLAN.md:122,
   29-08-PLAN.md:126), while the executor verifies a task and only then commits it
   (.claude/agents/gsd-executor.md:155-160). That task's own edits are uncommitted, so `close` exits 1. The
   recovery line (29-01-PLAN.md:107) lets an executor commit and re-run, but the verify blocks and the
   `<verification>` sections run `test` and `close` again (for example 29-06-PLAN.md:146-150 and 180) after a
   clean `close` has removed R, so `test` points TMPDIR at a deleted directory and `close` lists a missing one.
2. **29-07: both prescribed replacement sentences pass the 200-character rule-line cap — confirmed, HIGH.** The
   sentences at 29-07-PLAN.md:120 measure 203 and 257 characters; `_rule_problems` reports any rule line over
   `LINE_CAP` = 200 (skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:228,
   skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:52), and the existing lines are fixed strings without
   `fit_line` (gp_sections.py:346-353, 394-398). The plan cannot pass its own render tests as written.
3. **29-08: the new eval-shape test fails on the untouched calibration file — confirmed, HIGH.** Task 2 keeps
   `evals/cases.jsonl` untouched and then forbids any file under `evals/` matching a pattern that includes `~/`
   (29-08-PLAN.md:119,124); `skills/jev-fast-decision/evals/cases.jsonl` holds one such synthetic path today.
4. **29-06: the foreign-merge guard accepts another plan's executor merge — partly handled, downgraded to
   MEDIUM.** The engine accepts any merge whose subject starts with an `own_merge_subjects` entry
   (29-06-PLAN.md:139), and the GSD adapter passes the generic `chore: merge executor worktree (` prefix
   (29-09-PLAN.md:105), the subject every GSD merge-back carries
   (.claude/gsd-core/bin/lib/worktree-safety.cjs:1345). But 29-09's `_owner` gives a merge the plan scope of its
   merged commits and `gsd_checkpoint` refuses `plan_not_contiguous` when another plan's commit sits in the run
   (29-09-PLAN.md:105), so a merge owned by another plan is refused. The gap left: a merge whose merged commits
   carry no single plan scope gets no owner and is not refused.
5. **29-07: the old-client check reads the wrong stream — confirmed, MEDIUM.** The plan maps exit 2 plus
   `invalid choice` "in the output" to the too-old reason (29-07-PLAN.md:88,96); `gp_host._run` returns only
   stdout (skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:53-72), and argparse prints that error on stderr. The
   fake-seam test passes; production returns `detect failed`.
6. **29-07: the golden stand-in change alters a non-jev golden line and lands a task late — confirmed, MEDIUM.**
   Replacing `DECIDE_REL` (`ai-kit-gsd-spec-discuss/scripts/decide.py`, tests/test_ai_kit_spec_goal_prompt_golden.py:51,
   188-192) with the jev path removes the `ai-kit-gsd-spec-discuss` folder from the fake skills tree, so
   `_candidate_skills` (skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py:439-440) drops it from the
   "Candidate skills" golden line (tests/fixtures/goal_prompt/golden/opengsd-goal-pointer.md:114), which has
   neither `jev` nor `decide`, so the plan's `golden_diff.sh` exits 1. Task 1 changes detection while the golden
   stand-in moves only in Task 2.
7. **29-08: the consent rule names `status` for `--probe` rows — confirmed, MEDIUM.** The plan triggers the
   consent ask on a remote row "with status `consent_required_for_remote`" for `--probe` or `detect`
   (29-08-PLAN.md:96,123); `--probe` rows carry that value under `reason`
   (skills/jev-fast-decision/scripts/jev_review.py:1288-1303), while `detect` gives a top-level `status`
   (29-03-PLAN.md:90). The synthetic probe fixture would hide the mismatch.
8. **29-06: rule grouping cannot show each folded commit builds — confirmed as a gap, MEDIUM.** The rules merge
   on shared changed paths and code/test name pairs only (29-06-PLAN.md:140); a feature importing a file another
   feature adds later stays separate, and the tree proofs check only the segment end and the tip. D-09 promises
   "never writes an unbuildable commit" (29-CONTEXT.md:97-98). Building every folded commit is not asked for;
   stating the limit in the policy and report, or a cheap dependency rule, is enough.
9. **Shared close check: targeted test runs are outside the per-run TMPDIR — confirmed, LOW.** Only `scope.py
   test` sets TMPDIR to R (29-01-PLAN.md:104), so a temp entry leaked by an earlier targeted run is reported as
   "not this run" instead of failing.

The reviewer judged the cycle-1 segment proof and the reused-tag fix correct and complete; the orchestrator agrees
(29-01-PLAN.md:137-138, 29-06-PLAN.md:139).

### Agreed Strengths

Single reviewer; no agreement possible. Referee-one's strengths: the segment proof now precedes the replay, the
merge-back premise matches the installed GSD, 29-07 updates the previously missed test importers, 29-08's lookup
table matches the existing order and keeps remote calls fail-closed, and every plan reuses the existing runner
and generator.

### Agreed Concerns

None (single reviewer). Its confirmed findings count.

### Divergent Views

None this cycle.

## Current HIGH Concerns

Gate: only referee-one ran, so the consensus gate is skipped and its confirmed HIGHs count.

1. **All plans (spec in 29-01): the close check fails on the last task's own uncommitted edits and breaks when
   run again** (referee-one; confirmed). Needed: run `close` after the task commit (or exclude the paths the plan
   commits), let `test` recreate R and `close` accept a missing R, so the repeated verify and verification runs
   stay valid.
2. **29-07: the two fixed sentences pass the 200-character cap** (referee-one; confirmed). Needed: shorter
   sentences that keep the advisory and fallback meaning, each pinned under the cap.
3. **29-08: the eval-shape scan covers the calibration file it must leave untouched** (referee-one; confirmed).
   Needed: limit the machine-path scan to `evals.json`, `trigger-queries.json` and `evals/files/`.

## Current Actionable Non-HIGH Concerns

- 29-06 with 29-09 (referee-one HIGH, orchestrator MEDIUM): an executor merge whose merged commits carry no single
  plan scope gets no owner and folds; treat it as foreign (`plan_not_contiguous`) and add a fixture with another
  plan's merge under the same generic subject.
- 29-07 (MEDIUM): detect the old client from stderr through the real `_run` seam (or have `_run` return stderr on
  a failure), tested with a synthetic argparse script.
- 29-07 (MEDIUM): keep the `ai-kit-gsd-spec-discuss` stand-in folder in the golden harness (or allow that line in
  `golden_diff.sh`), and move the golden stand-in update into Task 1.
- 29-08 (MEDIUM): name `reason` for `--probe` rows and `status` for `detect` in the consent rule, and make the
  probe fixture match the real row shape.
- 29-06 (MEDIUM): state in the policy and the report that rule grouping merges only on shared paths and test
  pairs, or add a cheap import rule.
- All plans (LOW): run the targeted test commands with TMPDIR set to R too, or say that their leaks are only
  reported.

Not reviewed this cycle: 29-01 to 29-05 (w1 stopped twice after its opening paragraph), 29-09 to 29-16 (every
call failed with `Combo has no executable targets`). 29-01 to 29-05 share finding 1 by the w1 paragraph and the
orchestrator's reading of 29-01-PLAN.md:105-107 and 175.

## Cycle summary

```yaml
cycle: 2
reviewers_ok: [referee-one]
reviewers_failed:
  referee-two: "Error: Model grok-cli/grok-4.7-xhigh is unavailable"
  referee-three: "Error: Model anthropic/claude-opus-5-5-xhigh is unavailable"
batches_uncovered:
  referee-one: [w1, w3, w4, w5, w6, w7]  # "AI.Error: Combo has no executable targets", each retried once
high: 3
actionable_non_high: 6
not_counted: 0
open_conflicts: 0
plan_coverage_incomplete: [referee-one]
```
